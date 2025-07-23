import os
import logging
import asyncio
import threading
from hey.mcp_tools.client import MCPClient  # Adjust the import based on your file structure


dir_path = os.path.dirname(os.path.realpath(__file__))
_mcp_client = None


def get_mcp_client(log_path=None, server_script_file=None):
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = SyncMCPClient(
            log_path=log_path,
            server_script_file=server_script_file
        )
        _mcp_client.connect_to_server()
    return _mcp_client


# import concurrent.futures, asyncio, traceback, sys, threading


class SyncMCPClient:
    def __init__(self, log_path=None, server_script_file=None):
        self._client = MCPClient(log_path=log_path)
        # Create a dedicated event loop.
        self._loop = asyncio.new_event_loop()

        # Start the event loop in a separate thread.
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        if server_script_file is not None:
            self.server_script_path = os.path.join(dir_path, server_script_file)
        else:
            self.server_script_path = os.path.join(dir_path, "server.py")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro):
        # if not (self._thread and self._thread.is_alive()):
        #     raise RuntimeError(
        #         "Event‑loop thread is not running in this process. "
        #         "Create a new SyncMCPClient inside the worker process."
        #     )
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def connect_to_server(self):
        """Synchronously connect to the server and return the list of tools."""
        self._run(
            self._client.connect_to_server(self.server_script_path)
        )

    def list_tools(self, return_dict=True):
        """Synchronously list available tools."""
        tools = self._run(
            self._client.list_tools()
        )
        if return_dict:
            tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools]

        return tools

    def call_tool(self, tool_name, tool_args):
        """Synchronously call a tool with provided arguments."""
        logging.info(f"[DEBUG] Calling tool {tool_name} with arguments {tool_args}")
        result = self._run(
            self._client.call_tools(tool_name, tool_args)
        )
        logging.info(f"[Sync MCP Client] Returning result: {result}")
        return result

    def cleanup(self):
        """Synchronously clean up resources."""
        return self._run(
            self._client.cleanup()
        )
