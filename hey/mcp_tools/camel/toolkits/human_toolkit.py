# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import logging
from typing import List

from hey.mcp_tools.camel.toolkits.base import BaseToolkit
from hey.mcp_tools.camel.toolkits.function_tool import FunctionTool

logger = logging.getLogger(__name__)


class HumanToolkit(BaseToolkit):
    r"""A class representing a toolkit for human interaction."""

    def __init__(self):
        pass

    def ask_human_via_console(self, question: str) -> str:
        r"""Ask a question to the human via the console.

        Args:
            question (str): The question to ask the human.

        Returns:
            str: The answer from the human.
        """
        print(f"Question: {question}")
        logger.info(f"Question: {question}")
        reply = input("Your reply: ")
        logger.info(f"User reply: {reply}")
        return reply

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [FunctionTool(self.ask_human_via_console)]
