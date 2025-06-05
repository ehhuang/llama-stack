# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
from collections.abc import Mapping
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .api import ColumnDefinition, ColumnType, PaginatedResult, SqlStore
from .sqlstore import SqlAlchemySqlStoreConfig

TYPE_MAPPING: dict[ColumnType, Any] = {
    ColumnType.INTEGER: Integer,
    ColumnType.STRING: String,
    ColumnType.FLOAT: Float,
    ColumnType.BOOLEAN: Boolean,
    ColumnType.DATETIME: DateTime,
    ColumnType.TEXT: Text,
    ColumnType.JSON: JSON,
}


class SqlAlchemySqlStoreImpl(SqlStore):
    def __init__(self, config: SqlAlchemySqlStoreConfig):
        self.config = config
        self.async_session = async_sessionmaker(create_async_engine(config.engine_str))
        self.metadata = MetaData()

    async def create_table(
        self,
        table: str,
        schema: Mapping[str, ColumnType | ColumnDefinition],
    ) -> None:
        if not schema:
            raise ValueError(f"No columns defined for table '{table}'.")

        sqlalchemy_columns: list[Column] = []

        for col_name, col_props in schema.items():
            col_type = None
            is_primary_key = False
            is_nullable = True  # Default to nullable

            if isinstance(col_props, ColumnType):
                col_type = col_props
            elif isinstance(col_props, ColumnDefinition):
                col_type = col_props.type
                is_primary_key = col_props.primary_key
                is_nullable = col_props.nullable

            sqlalchemy_type = TYPE_MAPPING.get(col_type)
            if not sqlalchemy_type:
                raise ValueError(f"Unsupported column type '{col_type}' for column '{col_name}'.")

            sqlalchemy_columns.append(
                Column(col_name, sqlalchemy_type, primary_key=is_primary_key, nullable=is_nullable)
            )

        # Check if table already exists in metadata, otherwise define it
        if table not in self.metadata.tables:
            sqlalchemy_table = Table(table, self.metadata, *sqlalchemy_columns)
        else:
            sqlalchemy_table = self.metadata.tables[table]

        # Create the table in the database if it doesn't exist
        # checkfirst=True ensures it doesn't try to recreate if it's already there
        engine = create_async_engine(self.config.engine_str)
        async with engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all, tables=[sqlalchemy_table], checkfirst=True)

    async def insert(self, table: str, data: Mapping[str, Any]) -> None:
        async with self.async_session() as session:
            await session.execute(self.metadata.tables[table].insert(), data)
            await session.commit()

    async def fetch_all(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
        cursor_column: str | None = None,
        cursor_id: str | None = None,
    ) -> PaginatedResult:
        async with self.async_session() as session:
            table_obj = self.metadata.tables[table]
            query = select(table_obj)

            if where:
                for key, value in where.items():
                    query = query.where(table_obj.c[key] == value)

            # Handle cursor-based pagination
            if cursor_id and cursor_column:
                cursor_query = select(table_obj.c[cursor_column]).where(table_obj.c.id == cursor_id)
                cursor_result = await session.execute(cursor_query)
                cursor_row = cursor_result.fetchone()

                if not cursor_row:
                    raise ValueError(f"Record with id '{cursor_id}' not found in table '{table}'")

                cursor_value = cursor_row[0]

                # Determine sort direction from order_by to apply correct cursor condition
                is_descending = True  # Default assumption
                if order_by:
                    for col_name, order_dir in order_by:
                        if col_name == cursor_column:
                            is_descending = order_dir == "desc"
                            break

                if is_descending:
                    query = query.where(table_obj.c[cursor_column] < cursor_value)
                else:
                    query = query.where(table_obj.c[cursor_column] > cursor_value)

            # Apply ordering
            if order_by:
                if not isinstance(order_by, list):
                    raise ValueError(
                        f"order_by must be a list of tuples (column, order={['asc', 'desc']}), got {order_by}"
                    )
                for order in order_by:
                    if not isinstance(order, tuple):
                        raise ValueError(
                            f"order_by must be a list of tuples (column, order={['asc', 'desc']}), got {order_by}"
                        )
                    name, order_type = order
                    if order_type == "asc":
                        query = query.order_by(table_obj.c[name].asc())
                    elif order_type == "desc":
                        query = query.order_by(table_obj.c[name].desc())
                    else:
                        raise ValueError(f"Invalid order '{order_type}' for column '{name}'")

            # Fetch limit + 1 to determine has_more
            fetch_limit = limit
            if limit:
                fetch_limit = limit + 1

            if fetch_limit:
                query = query.limit(fetch_limit)

            result = await session.execute(query)
            if result.rowcount == 0:
                rows = []
            else:
                rows = [dict(row._mapping) for row in result]

            # Always return pagination result
            has_more = False
            if limit and len(rows) > limit:
                has_more = True
                rows = rows[:limit]

            return PaginatedResult(data=rows, has_more=has_more)

    async def fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        result = await self.fetch_all(table, where, limit=1, order_by=order_by)
        if not result.data:
            return None
        return result.data[0]

    async def update(
        self,
        table: str,
        data: Mapping[str, Any],
        where: Mapping[str, Any],
    ) -> None:
        if not where:
            raise ValueError("where is required for update")

        async with self.async_session() as session:
            stmt = self.metadata.tables[table].update()
            for key, value in where.items():
                stmt = stmt.where(self.metadata.tables[table].c[key] == value)
            await session.execute(stmt, data)
            await session.commit()

    async def delete(self, table: str, where: Mapping[str, Any]) -> None:
        if not where:
            raise ValueError("where is required for delete")

        async with self.async_session() as session:
            stmt = self.metadata.tables[table].delete()
            for key, value in where.items():
                stmt = stmt.where(self.metadata.tables[table].c[key] == value)
            await session.execute(stmt)
            await session.commit()
