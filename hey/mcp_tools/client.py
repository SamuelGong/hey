import os
import asyncio
import logging
from datetime import timedelta
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic


class MCPClient:
    def __init__(self, log_path):
        # Initialize session and client objects
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.log_path = log_path
        # self._server_process = None

    async def connect_to_server(self, server_script_path):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"

        args = [server_script_path]
        if self.log_path is not None:
            args += [f"{self.log_path}"]
        logging.info(f"[MCP Client] Staring MCP Server")
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=dict(os.environ)  # Important! Otherwise, environment variables (not from .env) cannot be inherited
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        # logging.info(f"[MCP Client] {self.stdio.__dict__}")
        # logging.info(f"[MCP Client] {self.session.__dict__}")
        # proc = self.stdio.get_extra_info("process")
        # self._server_process = proc

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logging.info(f"[MCP Client] Connected to server with tools: {[tool.name for tool in tools]}")

    async def list_tools(self):
        response = await self.session.list_tools()
        return response.tools

    async def call_tools(self, tool_name, tool_args):
        # logging.info(f"[Zhifeng] Calling tool {tool_name} with arguments {tool_args}")
        tool_call_result = await self.session.call_tool(tool_name, tool_args)
        # logging.info(f"[Client] Returning result: {tool_call_result}")
        return tool_call_result

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
        # proc = self._server_process
        # # if proc is not None and proc.returncode is None:
        # if proc is not None:
        #     logging.info(f"[MCP Client] Shutting down MCP Server")
        #     proc.kill()
        #     # proc.send_signal(signal.SIGTERM)
        #     # try:
        #     #     # give it up to 2 seconds to shut down cleanly
        #     #     await asyncio.wait_for(proc.wait(), timeout=2)
        #     # except asyncio.TimeoutError:
        #     #     # …otherwise, kill it
        #     #     proc.kill()
        #     #     await proc.wait()


async def main():
    if len(sys.argv) < 2:
        print("Usage: code client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level='INFO',
        format='[%(levelname)s][%(asctime)s.%(msecs)03d][%(process)d]'
               '[%(filename)s:%(lineno)d]: %(message)s',
        datefmt='(%Y-%m-%d) %H:%M:%S'
    )
    asyncio.run(main())
