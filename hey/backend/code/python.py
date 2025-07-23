import os
import re
import sys
import time
import queue
import logging
import traceback
import threading
from jupyter_client import KernelManager


from hey.backend.code.base import Basic, extract_code_from_string


code_generation_system_prompt = """
You are a world-class programmer and your goal is to generate code code to complete a specific subtask.
The subtask is one of the necessary steps to complete the overall task.
While you should focus on the subtask, description for the overall task is also provided for your reference.
You could only respond with your code.

The returned Python code should be formatted as follows:
```python
Python code
```

Friendly note: 1. WHen downloading Youtube video, instead of using the pytube package that has its network functionality broken,
you should instead use the pytubefix package which has the same usage as pytube.
"""


class JupyterWarningFilter(logging.Filter):
    def filter(self, record):
        return not any(msg in record.getMessage() for msg in [
            "Parent appears to have exited, shutting down.",
            "Could not destroy zmq context"
        ])


def setup_jupyter_logging():
    filter_instance = JupyterWarningFilter()
    for logger_name in ['IPKernelApp', 'tornado', 'tornado.access', 'tornado.application', 'tornado.general']:
        logger = logging.getLogger(logger_name)
        logger.addFilter(filter_instance)


class JupyterPython():
    def __init__(self):
        self.finish_flag = False

    def iopub_message_listener(self, message_queue, km, kc):
        while True:
            if self.finish_flag:
                km.interrupt_kernel()
                return
            try:
                msg = kc.iopub_channel.get_msg(timeout=0.05)
            except queue.Empty:
                continue

            if (msg["header"]["msg_type"] == "status" and
                    msg["content"]["execution_state"] == "idle"):
                self.finish_flag = True
                return

            content = msg["content"]
            if msg["msg_type"] == "stream":
                line = content["text"]
                message_queue.put(
                    {"type": "console", "format": "output", "content": line}
                )
            elif msg["msg_type"] == "error":
                content = "\n".join(content["traceback"])
                # Remove color codes
                ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
                content = ansi_escape.sub("", content)
                message_queue.put({
                    "type": "console",
                    "format": "output",
                    "content": content,
                })

    def _run_code(self, code, km, kc):
        self.finish_flag = False
        try:
            message_queue = queue.Queue()
            listener_thread = threading.Thread(
                target=self.iopub_message_listener, args=(message_queue, km, kc)
            )
            listener_thread.start()

            kc.execute(code)

            while True:
                try:
                    output = message_queue.get(timeout=0.1)
                    yield output
                except queue.Empty:
                    if self.finish_flag:
                        break
                time.sleep(0.1)
        except GeneratorExit:
            raise  # gotta pass this up!
        except:
            content = traceback.format_exc()
            yield {"type": "console", "format": "output", "content": content}

    @staticmethod
    def get_kernel_and_client():
        setup_jupyter_logging()
        km = KernelManager(
            kernel_name='python3',
            kernel_cmd=[sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        )
        km.start_kernel(env=os.environ.copy())

        kc = km.client()
        kc.start_channels()
        while not kc.is_alive():
            time.sleep(0.1)
        time.sleep(0.5)

        return km, kc

    @staticmethod
    def stop_kernel_and_client(km, kc):
        kc.stop_channels()
        km.shutdown_kernel(now=True)

    def run_code(self, code):
        results = []
        errors = []

        km, kc = self.get_kernel_and_client()
        for res_dict in self._run_code(code, km, kc):
            content = res_dict['content']
            if 'Traceback' in content:
                errors.append(content)
            else:
                results.append(content)
        self.stop_kernel_and_client(km, kc)
        result = {
            'result': '\n'.join(results),
            'error': '\n'.join(errors)
        }
        if result['result'] == "" and result['error'] == "":
            result['result'] = "Execution succeeded"  # tweak
        return result


class Python(Basic):
    def __init__(self):
        super().__init__()
        self.python_kernel = JupyterPython()

    def generate_code(self, query):
        system_prompt = code_generation_system_prompt
        user_query = query
        response = self.coding_llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query
        )
        code = extract_code_from_string(response, 'python')
        return code

    def execute_code(self, code):
        result = self.python_kernel.run_code(code)
        return result
