# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import threading
from typing import Any

from llama_stack.apis.log.log import (
    ChatCompletion,
    ListChatCompletionsResponse,
    Log,
)
from llama_stack.distribution.datatypes import Api
from llama_stack.providers.inline.log.meta_reference.sqlite_log_store import SQLiteLogStore

from .config import LogConfig

_global_lock = threading.Lock()


class LogAdapter(Log):
    def __init__(self, config: LogConfig, deps: dict[Api, Any]) -> None:
        self.config = config

        self.log_store = SQLiteLogStore(self.config.log_db_path)

        self._lock = _global_lock

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def store_chat_completion(self, chat_completion: ChatCompletion) -> None:
        await self.log_store.store_chat_completion(chat_completion)

    async def list_chat_completions(self) -> ListChatCompletionsResponse:
        return await self.log_store.list_chat_completions()

    async def get_chat_completion(self, completion_id: str) -> ChatCompletion:
        return await self.log_store.get_chat_completion(completion_id)
