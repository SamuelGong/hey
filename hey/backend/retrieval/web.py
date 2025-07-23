import logging
import tiktoken
import requests
import traceback
from munch import DefaultMunch
from bs4 import BeautifulSoup
from googlesearch import search
from hey.backend.llm.registry import get_llm
from hey.utils.misc import extract_json_from_string


summary_content_system_prompt = """You are an expert summarizer. 
Summarize the following text, preserving all key facts related to the user query, and omitting fluff.

Please strictly format your output in JSON as follows:
```json
{
    "summary": "A concise summary of how the text answers the user query"
    "complete": true or false (true if this text alone already contains all key facts needed, false otherwise.)
}
```
"""

meta_summary_content_system_prompt =  """You are an expert summarizer. 
Below are a list of summaries of different sections from an article.
Please do a meta-summary of them by extracting all key facts related to the user query, and omitting fluff.
"""

summary_content_user_query_template = """
User query: {query}
Text:

{content}
"""


class Web:
    def __init__(self, num_url_results=3, page_timeout=10, blacklist=None):  # avoid hard-coding
        self.num_url_results = num_url_results
        self.page_timeout = page_timeout

        llm_config = {
            "type": "openai",
            "api_key_type": "ark",
            "model_name": "ep-20250212105505-5zlbx",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3"
        }  # TODO: avoid hard-coding
        llm_config = DefaultMunch.fromDict(llm_config)
        self.summary_llm = get_llm(llm_config)

        self.blacklist = blacklist or [
            "camel-ai/owl",
            "benchmark_gaia"
            # avoid data polluting
        ]

    @staticmethod
    def url_search_via_google(query, num_results):
        urls = []
        error = ""
        try:
            for url in search(query, num_results=num_results):
                urls.append(url)
        except Exception as e:
            error = f"Error during Google search: {e}"
            logging.error(error)
        return urls, error

    @staticmethod
    def fetch_page_content(url, timeout=10):
        try:
            response = requests.get(url, timeout=timeout)
            content_type = response.headers.get('Content-Type', '')
            if "application/pdf" in content_type:
                logging.warning(f"Skipped fetching content online from {url} as it links to a PDF document. "
                                f"You can try downloading and reading the file instead.")
                return "Skipped: PDF document detected.", False

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Remove unwanted tags (scripts, styles)
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator=" ", strip=True)
                logging.info(f"Content fetched from {url} (length: {len(text)})")
                return text, True
            else:
                logging.error(f"Failed to fetch {url} as "
                              f"getting status code: {response.status_code}")
                tips = ("Tip: If the URL leads directly to a file download, receiving a 403 status code is expected. "
                        "Don't discard the URL—just try downloading the file later using another tool, "
                        "such as a Python script or a Bash command :)")
                return f"Status code: {response.status_code}" + tips, False
        except Exception as e:
            logging.error(f"Failed to fetch {url} due to {e}")
            return f"{traceback.format_exc()}", False

    @staticmethod
    def chunk_text(text, max_tokens, overlap=0):
        """Split `text` into token-limited chunks, with optional token overlap."""
        enc = tiktoken.encoding_for_model("gpt-4")
        tokens = enc.encode(text)
        chunks = []
        start = 0
        while True:
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(enc.decode(chunk_tokens))
            if end >= len(tokens):
                break

            # step forward but keep overlap
            start = end - overlap
        return chunks

    def summarize_text_hierarchical(self, original_query, text):
        # TODO: avoid hard-coding
        MAX_TOKENS_PER_CHUNK = 6000
        CHUNK_OVERLAP_TOKENS = 200

        # --- 1) Chunking ---
        chunks = self.chunk_text(text, MAX_TOKENS_PER_CHUNK, CHUNK_OVERLAP_TOKENS)

        # --- 2) Summarize each chunk ---
        chunk_summaries = []
        for chunk in chunks:
            summary_content_user_query = summary_content_user_query_template.format(
                query=original_query,
                content=chunk
            )
            raw = self.summary_llm.get_response(
                system_prompt=summary_content_system_prompt,
                user_query=summary_content_user_query
            )
            try:
                result = extract_json_from_string(raw)
                summary = result["summary"].strip()
                done_flag = bool(result.get("complete", False))
            except Exception as e:
                # fallback: if parsing fails, treat the whole raw as summary
                summary = raw
                done_flag = False

            chunk_summaries.append(summary)
            if done_flag:
                # we got everything we needed: stop fetching/summarizing further
                break

        # --- 3) Meta-summarize ---
        if len(chunk_summaries) > 1:
            combined = "\n\n".join(chunk_summaries)
            summary_content_user_query = summary_content_user_query_template.format(
                query=original_query,
                content=combined
            )
            final_summary = self.summary_llm.get_response(
                system_prompt=meta_summary_content_system_prompt,
                user_query=summary_content_user_query
            )
        else:
            final_summary = chunk_summaries[0]

        return final_summary

    def serve(self, query):
        urls, error = self.url_search_via_google(
            query, self.num_url_results
        )
        if error:
            return {"result": "", "error": error}

        result = []
        other = []
        for url in urls:
            if any(pattern in url for pattern in self.blacklist):
                result.append({
                    "url": url,
                    "fetched content": "Not fetched as the url is in the blacklist."
                })
                continue

            content, succeeded = self.fetch_page_content(
                url, self.page_timeout
            )
            if succeeded:
                summarized_content = self.summarize_text_hierarchical(query, content)
                result.append({"url": url, "fetched content (summarized)": summarized_content})
            else:
                other.append({"url": url, "error": content})

        return {"result": result + other, "error": ""}
