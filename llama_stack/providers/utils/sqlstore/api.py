# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Protocol


class SqlStore(Protocol):
    """
    A protocol for a SQL store.
    """

    async def select(self, sql: str, params: tuple | None = None) -> list[dict]:
        """Run a SELECT query and return rows as list of dicts.

        Should support `?` and `:name` placeholders.
        """

    async def execute(self, sql: str, params: tuple | None = None) -> None:
        """Run a non-SELECT query (CREATE_TABLE,INSERT, UPDATE, DELETE).

        Should support `?` and `:name` placeholders.
        """
