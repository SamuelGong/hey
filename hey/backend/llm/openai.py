# Address the RuntimeWarning (which is brought by the use of `httpx`):
#
# You seem to already have a custom sys.excepthook handler installed.
# I'll skip installing Trio's custom handler, but this means MultiErrors will not show full tracebacks.
import sys
orig_hook = sys.excepthook          # save PyCharm/IPython hook
sys.excepthook = sys.__excepthook__ # restore default
import trio                          # Trio installs its hook
sys.excepthook = orig_hook          # put yours back

import os
import httpx
import hashlib
import logging
import traceback
from openai import OpenAI
from hey.backend.llm.base import BaseLLM

_global_endpoints = {}


def _get_api_key(api_key_type):
    if api_key_type == "ark":
        return os.getenv("ARK_API_KEY")
    elif api_key_type is None:
        return "PLACEHOLDER"  # Cannot be empty string!
    else:
        raise NotImplementedError(f"Unknown API key type {api_key_type}")


def _get_endpoint(base_url, api_key_type):
    url_hash = hashlib.md5(base_url.encode()).hexdigest()

    global _global_endpoints
    if url_hash not in _global_endpoints:
        api_key = _get_api_key(api_key_type)
        _global_endpoints[url_hash] = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(
                verify=False  # important for company use
            )
        )

    return _global_endpoints[url_hash]


class OpenAILLM(BaseLLM):
    def __init__(self, config):
        self.api_key_type = config.api_key_type
        self.base_url = config.base_url
        self.model_name = config.model_name

    def get_response(self, user_query, system_prompt=None, image_url=None, verbose=True):
        payload = {"model": self.model_name, "messages": []}
        logging.debug(f"Getting response for messages:")
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
            logging.debug(f"System prompt:\n{system_prompt}")

        if image_url:
            if not self.api_key_type == "ark":
                raise NotImplementedError
            payload["messages"].append({"role": "user", "content": [
                {"type": "text", "text": user_query},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]})
        else:
            payload["messages"].append({"role": "user", "content": user_query})
        logging.debug(f"User query:\n{user_query}")

        endpoint = _get_endpoint(self.base_url, self.api_key_type)

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
