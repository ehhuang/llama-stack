# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json
import os

import aiosqlite

from llama_stack.apis.inference import (
    ListOpenAIChatCompletionResponse,
    OpenAIChatCompletion,
    OpenAICompletionWithInputMessages,
    OpenAIMessageParam,
    Order,
)

from ..inference_store import InferenceStore


class SqliteInferenceStore(InferenceStore):
    def __init__(self, conn_string: str):
        self.conn_string = conn_string

    async def initialize(self):
        """Create the necessary tables if they don't exist."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.conn_string), exist_ok=True)

        async with aiosqlite.connect(self.conn_string) as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_completions (
                    id TEXT PRIMARY KEY,
                    created INTEGER,
                    model TEXT,
                    choices TEXT,
                    input_messages TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            await conn.commit()

    async def store_chat_completion(
        self, chat_completion: OpenAIChatCompletion, input_messages: list[OpenAIMessageParam]
    ) -> None:
        data = chat_completion.model_dump()

        async with aiosqlite.connect(self.conn_string) as conn:
            await conn.execute(
                """
            INSERT INTO chat_completions (id, created, model, choices,input_messages)
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
            await conn.commit()

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
        if not order:
            order = Order.desc
        async with aiosqlite.connect(self.conn_string) as conn:
            conn.row_factory = aiosqlite.Row
            where_clause = f"WHERE model = {model}" if model else ""
            # TODO: support after
            cursor = await conn.execute(
                f"""
                SELECT * FROM chat_completions
                {where_clause}
                ORDER BY created_at {order.value}
                LIMIT {limit}
                """
            )
            rows = await cursor.fetchall()

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
        async with aiosqlite.connect(self.conn_string) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM chat_completions WHERE id = ?", (completion_id,))
            row = await cursor.fetchone()
        return OpenAICompletionWithInputMessages(
            id=row["id"],
            created=row["created"],
            model=row["model"],
            choices=json.loads(row["choices"]),
            input_messages=json.loads(row["input_messages"]),
        )
