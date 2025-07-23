import os
import dotenv
import logging
from mcp.server.fastmcp import FastMCP

from hey.utils.misc import set_log
from hey.backend.retrieval.web import Web
from hey.backend.code.read import SemanticRead
from hey.backend.code.general_shell import Shell
from hey.backend.code.python import Python
from hey.environments.basic import BasicEnv
from hey.agents.basic.const import INPUT_REQUIRED

mcp = FastMCP("native")
dir_path = os.path.dirname(os.path.realpath(__file__))


INPUT_TIMEOUT = 120


def common_init(log_path):
    dotenv_path = os.path.join(dir_path, '..', '..', '.env')
    dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
    set_log(log_path=log_path)


@mcp.tool()
def ask_user(log_path: str, question: str) -> str:
    """Asking the user to provide information necessary for completing the task (e.g., password) or to clarify some ambiguous points in the task description.

    Args:
        question: what you want the user to clarify
    """
    question += ' > '
    my_pid = os.getpid()
    common_init(log_path)

    agent_env = BasicEnv()
    agent_env.publish_a_message(
        channel=INPUT_REQUIRED,
        message={'prompt': question, 'target_pid': my_pid}
    )
    logging.info(f"[ASK USER] Published the prompt: {question}")
    user_answer = agent_env.get_data_from_main_process(
        target_pid=my_pid,
        blocked=True
    )
    logging.info(f"[ASK USER] Got the user input: {user_answer}")
    return user_answer




@mcp.tool()
def read_out_file_content(log_path: str, file_path_list: list) -> list:
    """Reading and extracting semantic content from a list of provided or downloaded files
    (supporting text, audio, video, and many other types of files).
    Extremely useful for analyzing file content in later tasks.

    Args:
        file_path_list: a list of paths to the files to be read
    """

    common_init(log_path)
    handler = SemanticRead()
    return handler.process(file_path_list=file_path_list)


@mcp.tool()
def do_googlesearch(log_path: str, query: str) -> dict:
    """Using Google Search when you need up-to-date information, recent news, or factual content from the web that is not already known or stored internally.

    Args:
        query: a combination of keywords to search for
    """
    common_init(log_path)
    handler = Web()
    return handler.serve(query)


@mcp.tool()
def shell_code_task(log_path: str, specific_goal: str) -> dict:
    """Using shell code to manage resources on the operating system level such as file handling, memory management, or network monitoring.

    Args:
        specific_goal: in natural language, specify what you want to achieve using shell code, with necessary context and details.
    """
    common_init(log_path)
    handler = Shell()
    return handler.serve(specific_goal)


@mcp.tool()
def python_code_task(log_path: str, specific_goal: str) -> dict:
    """Using Python code to create and run complex applications such as data handling, analysis, or machine learning

    Args:
        specific_goal: in natural language, specify what you want to achieve using Python code, with necessary context and details.
    """
    common_init(log_path)
    handler = Python()
    return handler.serve(specific_goal)


if __name__ == "__main__":
    mcp.run(transport='stdio')
