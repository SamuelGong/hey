import os
import sys
import dotenv
import logging
from mcp.server.fastmcp import FastMCP

from hey.utils.misc import set_log
from hey.backend.retrieval.web import Web
from hey.backend.code.read import SemanticRead
from hey.backend.code.general_shell import Shell
from hey.backend.code.python import Python

from appworld import AppWorld, load_task_ids

mcp = FastMCP("native")
dir_path = os.path.dirname(os.path.realpath(__file__))


INPUT_TIMEOUT = 120


def common_init(log_path):
    dotenv_path = os.path.join(dir_path, '..', '..', '.env')
    dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
    set_log(log_path=log_path)


@mcp.tool()
def show_api_doc(app_name: str, api_name: str):
    """To get the specification of a particular api
    """

    with AppWorld(
            task_id=task_id,
            experiment_name=experiment_name
    ) as world:
        output = world.execute(f"apis.api_docs.show_api_doc(app_name={app_name})")
        return output


@mcp.tool()
def show_api_descriptions(app_name: str):
    """To get a list of apps that are available to you.
        """

    with AppWorld(
            task_id=task_id,
            experiment_name=experiment_name
    ) as world:
        output = world.execute(f"apis.api_docs.show_api_descriptions(app_name={app_name})")
        return output


@mcp.tool()
def show_app_descriptions() -> str:
    """To get a list of apps that are available to you.
    """

    with AppWorld(
            task_id=task_id,
            experiment_name=experiment_name
    ) as world:
        output = world.execute("apis.api_docs.show_app_descriptions()")
        return output


if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else None

    global task_id, experiment_name
    task_id, experiment_name = sys.argv[2] if len(sys.argv) > 2 else None

    common_init(log_path)
    mcp.run(transport='stdio')
