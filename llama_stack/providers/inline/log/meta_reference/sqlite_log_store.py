# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import json
import os
import sqlite3
import threading
from typing import Protocol

from llama_stack.apis.log.log import ChatCompletion, ListChatCompletionsResponse


class LogStore(Protocol):
    async def store_chat_completion(self, chat_completion: ChatCompletion) -> None: ...

    async def list_chat_completions(self) -> ListChatCompletionsResponse: ...

    async def get_chat_completion(self, completion_id: str) -> ChatCompletion: ...


class SQLiteLogStore(LogStore):
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._local = threading.local()  # Thread-local storage for connections
        self.setup_database()

    def _get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn"):
            try:
                self._local.conn = sqlite3.connect(self.conn_string)
            except Exception as e:
                print(f"Error connecting to SQLite database: {e}")
                raise
        return self._local.conn

    async def store_chat_completion(self, chat_completion: ChatCompletion) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        data = chat_completion.model_dump()

        cursor.execute(
            """
            INSERT INTO chat_completions (id, created, model, messages)
            VALUES (?, ?, ?, ?)
            """,
            (
                data["id"],
                data["created"],
                data["model"],
                json.dumps(data["messages"]),
            ),
        )

        conn.commit()
        cursor.close()

    async def list_chat_completions(self) -> ListChatCompletionsResponse:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM chat_completions")
        rows = cursor.fetchall()
        return ListChatCompletionsResponse(
            data=[
                ChatCompletion(
                    id=row["id"],
                    created=row["created"],
                    model=row["model"],
                    messages=json.loads(row["messages"]),
                )
                for row in rows
            ]
        )

    async def get_chat_completion(self, completion_id: str) -> ChatCompletion:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM chat_completions WHERE id = ?", (completion_id,))
        row = cursor.fetchone()
        return ChatCompletion(
            id=row["id"],
            created=row["created"],
            model=row["model"],
            messages=json.loads(row["messages"]),
        )

    def setup_database(self):
        """Create the necessary tables if they don't exist."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.conn_string), exist_ok=True)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_completions (
                id TEXT PRIMARY KEY,
                created INTEGER,
                model TEXT,
                messages TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        cursor.close()
