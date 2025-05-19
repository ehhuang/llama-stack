# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json

from llama_stack.apis.inference import (
    ListOpenAIChatCompletionResponse,
    OpenAIChatCompletion,
    OpenAICompletionWithInputMessages,
    OpenAIMessageParam,
    Order,
)
from llama_stack.distribution.utils.config_dirs import RUNTIME_BASE_DIR

from ..sqlstore.sqlstore import SqliteSqlStoreConfig, SqlStoreConfig, sqlstore_impl


class InferenceStore:
    def __init__(self, sql_store_config: SqlStoreConfig):
        if not sql_store_config:
            sql_store_config = SqliteSqlStoreConfig(db_path=(RUNTIME_BASE_DIR / "sqlstore.db").as_posix())
        self.sql_store = sqlstore_impl(sql_store_config)

    async def initialize(self):
        """Create the necessary tables if they don't exist."""
        await self.sql_store.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_completions (
                id TEXT PRIMARY KEY,
                created INTEGER,
                model TEXT,
                choices TEXT,
                input_messages TEXT
            )
        """
        )

    async def store_chat_completion(
        self, chat_completion: OpenAIChatCompletion, input_messages: list[OpenAIMessageParam]
    ) -> None:
        data = chat_completion.model_dump()

        await self.sql_store.execute(
            """
            INSERT INTO chat_completions (id, created, model, choices, input_messages)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["created"],
                data["model"],
                json.dumps(data["choices"]),
                json.dumps([message.model_dump() for message in input_messages]),
            ),
        )

    async def list_chat_completions(
        self,
        after: str | None = None,
        limit: int | None = 20,
        model: str | None = None,
        order: Order | None = Order.desc,
    ) -> ListOpenAIChatCompletionResponse:
        """
        List chat completions from the database.

        :param after: The ID of the last chat completion to return.
        :param limit: The maximum number of chat completions to return.
        :param model: The model to filter by.
        :param order: The order to sort the chat completions by.
        """
        # TODO: support after
        if after:
            raise NotImplementedError("After is not supported for SQLite")
        if not order:
            order = Order.desc

        where_clause = f"WHERE model = {model}" if model else ""
        sql = f"""
        SELECT * FROM chat_completions
        {where_clause}
        ORDER BY created {order.value}
        LIMIT {limit}
        """
        rows = await self.sql_store.select(sql)

        data = [
            OpenAICompletionWithInputMessages(
                id=row["id"],
                created=row["created"],
                model=row["model"],
                choices=json.loads(row["choices"]),
                input_messages=json.loads(row["input_messages"]),
            )
            for row in rows
        ]
        return ListOpenAIChatCompletionResponse(
            data=data,
            # TODO: implement has_more
            has_more=False,
            first_id=data[0].id,
            last_id=data[-1].id,
        )

    async def get_chat_completion(self, completion_id: str) -> OpenAICompletionWithInputMessages:
        rows = await self.sql_store.select("SELECT * FROM chat_completions WHERE id = ?", (completion_id,))
        row = rows[0]
        if row is None:
            raise ValueError(f"Chat completion with id {completion_id} not found")
        return OpenAICompletionWithInputMessages(
            id=row["id"],
            created=row["created"],
            model=row["model"],
            choices=json.loads(row["choices"]),
            input_messages=json.loads(row["input_messages"]),
        )
