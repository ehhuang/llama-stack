# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from enum import Enum
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from llama_stack.apis.inference import (
    ListOpenAIChatCompletionResponse,
    OpenAIChatCompletion,
    OpenAICompletionWithInputMessages,
    OpenAIMessageParam,
    Order,
)
from llama_stack.distribution.utils.config_dirs import RUNTIME_BASE_DIR


class InferenceStoreType(Enum):
    sqlite = "sqlite"


class SqliteInferenceStoreConfig(BaseModel):
    type: Literal["sqlite"] = InferenceStoreType.sqlite.value
    db_path: str = Field(
        default=(RUNTIME_BASE_DIR / "inference_store.db").as_posix(),
        description="File path for the sqlite database",
    )

    @classmethod
    def sample_run_config(cls, __distro_dir__: str, db_name: str = "inference_store.db"):
        return {
            "type": "sqlite",
            "db_path": "${env.SQLITE_STORE_DIR:" + __distro_dir__ + "}/" + db_name,
        }


InferenceStoreConfig = Annotated[
    SqliteInferenceStoreConfig,
    Field(discriminator="type", default=InferenceStoreType.sqlite.value),
]


class InferenceStore(Protocol):
    async def initialize(self) -> None: ...

    async def store_chat_completion(
        self, chat_completion: OpenAIChatCompletion, input_messages: list[OpenAIMessageParam]
    ) -> None: ...

    async def list_chat_completions(
        self,
        after: str | None = None,
        limit: int | None = 20,
        model: str | None = None,
        order: Order | None = Order.desc,
    ) -> ListOpenAIChatCompletionResponse: ...

    async def get_chat_completion(self, completion_id: str) -> OpenAICompletionWithInputMessages: ...


async def inference_store_impl(config: InferenceStoreConfig) -> InferenceStore:
    if config.type == InferenceStoreType.sqlite.value:
        from .stores.sqlite import SqliteInferenceStore

        impl = SqliteInferenceStore(config.db_path)
    else:
        raise ValueError(f"Unknown inference store type {config.type}")

    await impl.initialize()
    return impl
