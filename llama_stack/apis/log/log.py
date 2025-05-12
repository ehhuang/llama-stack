# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import (
    Protocol,
    runtime_checkable,
)

from pydantic import BaseModel

from llama_stack.apis.inference import OpenAIMessageParam
from llama_stack.schema_utils import json_schema_type, webmethod


@json_schema_type
class ChatCompletion(BaseModel):
    id: str
    created: int
    model: str
    messages: list[OpenAIMessageParam]


@json_schema_type
class ListChatCompletionsResponse(BaseModel):
    data: list[ChatCompletion]


@runtime_checkable
class Log(Protocol):
    async def store_chat_completion(self, chat_completion: ChatCompletion) -> None: ...

    @webmethod(route="/log/openai_chat_completions", method="GET")
    async def list_chat_completions(self) -> ListChatCompletionsResponse:
        """List all chat completions.

        :returns: A ListChatCompletionsResponse.
        """
        ...

    @webmethod(route="/log/openai_chat_completions/{completion_id}", method="GET")
    async def get_chat_completion(self, completion_id: str) -> ChatCompletion:
        """Describe a chat completion by its ID.

        :param completion_id: ID of the chat completion.
        :returns: A ChatCompletion.
        """
        ...
