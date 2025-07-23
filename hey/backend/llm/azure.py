import os
import httpx
import hashlib
import logging
import traceback
from openai import AzureOpenAI
from hey.backend.llm.base import BaseLLM

_global_endpoints = {}


def _get_api_key():
    return os.getenv("AZURE_OPENAI_API_KEY")


def _get_endpoint(base_url, api_version):
    url_hash = hashlib.md5(base_url.encode()).hexdigest()

    global _global_endpoints
    if url_hash not in _global_endpoints:
        api_key = _get_api_key()
        _global_endpoints[url_hash] = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version,
            http_client=httpx.Client(
                verify=False  # important for company use
            )
        )

    return _global_endpoints[url_hash]


class AzureLLM(BaseLLM):
    def __init__(self, config):
        self.api_version = config.api_version
        self.base_url = config.base_url
        self.model_name = config.model_name

    def get_response(self, user_query, system_prompt=None,
                     image_url=None, verbose=True):
        payload = {"model": self.model_name, "messages": []}
        logging.debug(f"Getting response for messages:")
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
            logging.debug(f"System prompt:\n{system_prompt}")

        if image_url:
            payload["messages"].append({"role": "user", "content": [
                {"type": "text", "text": user_query},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]})
        else:
            payload["messages"].append({"role": "user", "content": user_query})
        logging.debug(f"User query:\n{user_query}")

        endpoint = _get_endpoint(self.base_url, self.api_version)

        try:
            completion = endpoint.chat.completions.create(**payload)
            response = completion.choices[0].message.content
        except Exception as e:
            response = f"{e}/{traceback.format_exc()}"

        if verbose:
            logging.info(f"Response got:\n{response}")
        else:
            logging.debug(f"Response got:\n{response}")
        return response
