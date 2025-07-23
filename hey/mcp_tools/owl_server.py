import os
import sys
import dotenv
import asyncio
import logging
import traceback

from mcp.server.fastmcp import FastMCP

# from camel.toolkits import WebToolkit
from camel.toolkits import AsyncWebToolkit as WebToolkit
from camel.toolkits import DocumentProcessingToolkit
from camel.toolkits import VideoAnalysisToolkit
from camel.toolkits import AudioAnalysisToolkit
from camel.toolkits import CodeExecutionToolkit
from camel.toolkits import ImageAnalysisToolkit
from camel.toolkits import SearchToolkit
from camel.toolkits import ExcelToolkit
from camel.models import ModelFactory
from camel.configs import ChatGPTConfig
from camel.types import ModelPlatformType

from hey.utils.misc import set_log, set_loguru_log

dir_path = os.path.dirname(os.path.realpath(__file__))


def init_logging(log_path: str):
    dotenv_path = os.path.join(dir_path, '..', '..', '.env')
    dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
    set_log(log_path=log_path)
    set_loguru_log(log_path=log_path, log_level="DEBUG")


# def main(log_path):
async def main(log_path):
    init_logging(log_path)
    log_prefix = "[MCP Server]"

    # 2a) first create your model objects
    models = {
        "web": ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            azure_deployment_name="gpt-4o",
            model_config_dict=ChatGPTConfig(temperature=0, top_p=1).as_dict(),
        ),
        "planning": ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            azure_deployment_name="gpt-4o",
            model_config_dict=ChatGPTConfig(temperature=0, top_p=1).as_dict(),
        ),
        "video": ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            azure_deployment_name="gpt-4o",
            model_config_dict=ChatGPTConfig(temperature=0, top_p=1).as_dict(),
        ),
        "image": ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            azure_deployment_name="gpt-4o",
            model_config_dict=ChatGPTConfig(temperature=0, top_p=1).as_dict(),
        ),
        "search": ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            azure_deployment_name="gpt-4o",
            model_config_dict=ChatGPTConfig(temperature=0, top_p=1).as_dict(),
        ),
    }

    toolkits = {
        "web": WebToolkit(
            headless=True, web_agent_model=models["web"],
            planning_agent_model=models["planning"]
        ),
        "doc": DocumentProcessingToolkit(),
        "video": VideoAnalysisToolkit(model=models["video"]),
        "audio": AudioAnalysisToolkit(),
        "exec": CodeExecutionToolkit(sandbox="subprocess", verbose=True),
        "img": ImageAnalysisToolkit(model=models["image"]),
        "search": SearchToolkit(model=models["search"]),
        "excel": ExcelToolkit(),
    }

    mcp = FastMCP("owl")
    tool_count = 0
    import inspect
    for tk in toolkits.values():
        for tool in tk.get_tools():
            schema = tool.openai_tool_schema["function"]
            # logging.info(f"{schema['name']} {inspect.iscoroutinefunction(tool.func)}")
            mcp.add_tool(
                fn=tool.func,
                name=schema["name"],
                description=schema["description"]
            )
            tool_count += 1
    logging.info(f"{log_prefix} {tool_count} tool(s) registered.")

    # mcp.run(transport="stdio")
    # # run the async stdio server
    await mcp.run_stdio_async()


if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else None
    # main(log_path)
    asyncio.run(main(log_path))
