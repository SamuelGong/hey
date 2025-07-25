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
from typing import Any

from hey.mcp_tools.camel.prompts.base import TextPrompt, TextPromptDict
from hey.mcp_tools.camel.types import RoleType


# flake8: noqa :E501
class VideoDescriptionPromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `VideoDescription`
    task.

    Attributes:
        ASSISTANT_PROMPT (TextPrompt): A prompt for the AI assistant to
            provide a shot description of the content of the current video.
    """

    ASSISTANT_PROMPT = TextPrompt(
        """You are a master of video analysis. 
        Please provide a shot description of the content of the current video."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update(
            {
                RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            }
        )
