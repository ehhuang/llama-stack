# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


import os

import aiosqlite

from ..api import SqlStore
from ..sqlstore import SqliteSqlStoreConfig


class SqliteSqlStoreImpl(SqlStore):
    def __init__(self, config: SqliteSqlStoreConfig):
        self.db_path = config.db_path

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def select(self, sql: str, params: tuple | None = None) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(sql, params) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def execute(self, sql: str, params: tuple | None = None) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(sql, params)
            await conn.commit()
