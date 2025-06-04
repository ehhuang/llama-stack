# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from collections.abc import Mapping
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel


class ColumnType(Enum):
    INTEGER = "INTEGER"
    STRING = "STRING"
    TEXT = "TEXT"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"
    DATETIME = "DATETIME"


class ColumnDefinition(BaseModel):
    type: ColumnType
    primary_key: bool = False
    nullable: bool = True
    default: Any = None


class SqlStore(Protocol):
    """
    A protocol for a SQL store with built-in access control functionality.
    """

    async def create_table(self, table: str, schema: Mapping[str, ColumnType | ColumnDefinition]) -> None:
        """
        Create a table.
        """
        pass

    async def insert(self, table: str, data: Mapping[str, Any]) -> None:
        """
        Insert a row into a table.
        """
        pass

    async def fetch_all(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        where_sql: str | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all rows from a table.

        :param table: Table name
        :param where: Simple key-value WHERE conditions
        :param where_sql: Raw SQL WHERE clause for complex queries
        :param limit: Maximum number of rows to return
        :param order_by: Ordering specification
        """
        pass

    async def fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        where_sql: str | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch one row from a table.
        """
        pass

    async def update(
        self,
        table: str,
        data: Mapping[str, Any],
        where: Mapping[str, Any],
    ) -> None:
        """
        Update a row in a table.
        """
        pass

    async def delete(
        self,
        table: str,
        where: Mapping[str, Any],
    ) -> None:
        """
        Delete a row from a table.
        """
        pass

    async def create_table_with_access_control(
        self, table: str, schema: Mapping[str, ColumnType | ColumnDefinition]
    ) -> None:
        """
        Create a table with built-in access control support.

        Automatically adds an 'access_attributes' JSON column for storing access control data.
        Handles migration if table already exists without the access control column.

        :param table: Table name
        :param schema: Column definitions (access_attributes will be added automatically)
        """
        pass

    async def secure_insert(self, table: str, data: Mapping[str, Any], capture_access_attributes: bool = True) -> None:
        """
        Insert a row with automatic access control attribute capture.

        :param table: Table name
        :param data: Row data to insert
        :param capture_access_attributes: Whether to automatically capture current user's access attributes
        """
        pass

    async def secure_fetch_all(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all rows with automatic access control filtering.

        Only returns rows that the current user has access to based on their auth attributes.

        :param table: Table name
        :param where: Simple key-value WHERE conditions
        :param limit: Maximum number of rows to return
        :param order_by: Ordering specification
        """
        pass

    async def secure_fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch one row with automatic access control checking.

        Returns the row only if the current user has access to it.

        :param table: Table name
        :param where: Simple key-value WHERE conditions
        :param order_by: Ordering specification
        """
        pass
