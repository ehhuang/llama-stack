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
    text,
)
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from llama_stack.distribution.access_control import check_access
from llama_stack.distribution.datatypes import AccessAttributes
from llama_stack.distribution.request_headers import get_auth_attributes

from .api import ColumnDefinition, ColumnType, SqlStore
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
        where_sql: str | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> list[dict[str, Any]]:
        async with self.async_session() as session:
            query = select(self.metadata.tables[table])
            if where:
                for key, value in where.items():
                    query = query.where(self.metadata.tables[table].c[key] == value)
            if where_sql:
                query = query.where(text(where_sql))
            if limit:
                query = query.limit(limit)
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
                        query = query.order_by(self.metadata.tables[table].c[name].asc())
                    elif order_type == "desc":
                        query = query.order_by(self.metadata.tables[table].c[name].desc())
                    else:
                        raise ValueError(f"Invalid order '{order_type}' for column '{name}'")
            result = await session.execute(query)
            return [dict(row._mapping) for row in result]

    async def fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        where_sql: str | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        rows = await self.fetch_all(table, where, where_sql, limit=1, order_by=order_by)
        if not rows:
            return None
        return rows[0]

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

    # SecureSqlStore implementation
    async def create_table_with_access_control(
        self, table: str, schema: Mapping[str, ColumnType | ColumnDefinition]
    ) -> None:
        """Create a table with built-in access control support."""
        # First, check if table already exists and needs migration
        # TODO: clean this up
        await self._migrate_access_attributes_column(table)

        # Add access_attributes column to schema if not present
        enhanced_schema = dict(schema)
        if "access_attributes" not in enhanced_schema:
            enhanced_schema["access_attributes"] = ColumnType.JSON

        # Create table with enhanced schema (will be no-op if table already exists)
        await self.create_table(table, enhanced_schema)

    async def _migrate_access_attributes_column(self, table: str):
        """Add access_attributes column to existing tables that don't have it.

        This is called before table creation to handle migration of existing tables.
        If the table doesn't exist, this method does nothing (table will be created with the column).
        If the table exists but lacks the access_attributes column, it adds the column.
        """
        engine = create_async_engine(self.config.engine_str)

        async with engine.begin() as conn:
            try:
                reflected_metadata = MetaData()
                await conn.run_sync(
                    lambda sync_conn: reflected_metadata.reflect(bind=sync_conn, only=[table], extend_existing=True)
                )

                if table not in reflected_metadata.tables:
                    return

                reflected_table = reflected_metadata.tables[table]

                if "access_attributes" in reflected_table.columns:
                    return

                # Use text() for safer SQL execution
                add_column_sql = text(f"ALTER TABLE {table} ADD COLUMN access_attributes JSON")
                await conn.execute(add_column_sql)

            except NoSuchTableError:
                return

    async def authorized_insert(
        self, table: str, data: Mapping[str, Any], capture_access_attributes: bool = True
    ) -> None:
        """Insert a row with automatic access control attribute capture."""
        enhanced_data = dict(data)

        if capture_access_attributes:
            auth_attributes = get_auth_attributes()
            access_attributes = AccessAttributes(**auth_attributes) if auth_attributes else None
            enhanced_data["access_attributes"] = access_attributes.model_dump() if access_attributes else None

        await self.insert(table, enhanced_data)

    def _build_access_control_where_clause(self) -> str:
        """Build SQL WHERE clause for access control filtering.

        This SQL filtering now matches check_access() logic exactly:
        - Records with no access control are always accessible (public)
        - Records with access control require the user to have ALL required attributes (AND logic)
        """
        current_user_attrs = get_auth_attributes()

        if not current_user_attrs:
            # User has no attributes, only show records with no access control
            # Handle both SQL NULL and JSON null (when None is stored)
            return "(access_attributes IS NULL OR access_attributes = 'null')"
        else:
            # Show records with no access control (public records)
            base_conditions = ["access_attributes IS NULL", "access_attributes = 'null'"]

            # For records with access control, user must satisfy ALL attribute categories (AND logic)
            # This matches the exact logic in check_access()

            # Build conditions for each attribute category the user has
            user_attr_conditions = []
            for attr_key, user_values in current_user_attrs.items():
                if user_values:
                    # For this attribute category, check if user has any of the required values
                    # (OR within category, since user might have multiple values)
                    value_conditions = []
                    for value in user_values:
                        # Use SQLite JSON functions to check if value exists in the array
                        value_conditions.append(f"JSON_EXTRACT(access_attributes, '$.{attr_key}') LIKE '%\"{value}\"%'")

                    if value_conditions:
                        # User satisfies this attribute category if they have any of the required values
                        user_attr_conditions.append(f"({' OR '.join(value_conditions)})")

            if user_attr_conditions:
                # Records are accessible if they're public OR user satisfies ALL attribute requirements
                # This creates: (public_records) OR (all_user_requirements_met)
                all_requirements_met = f"({' AND '.join(user_attr_conditions)})"
                base_conditions.append(all_requirements_met)
                return f"({' OR '.join(base_conditions)})"
            else:
                # User has no valid attributes, only show public records
                return f"({' OR '.join(base_conditions)})"

    async def authorized_fetch_all(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all rows with automatic access control filtering."""
        # Step 1: SQL-level filtering with secure AND logic for performance
        access_where = self._build_access_control_where_clause()
        rows = await self.fetch_all(
            table=table,
            where=where,
            where_sql=access_where,
            limit=limit,
            order_by=order_by,
        )

        # Step 2: Defense-in-depth validation using check_access()
        # This ensures security even if SQL logic has edge cases or bugs
        current_user_attrs = get_auth_attributes()
        filtered_rows = []

        for row in rows:
            stored_access_attrs = row.get("access_attributes")
            access_attrs_obj = AccessAttributes(**stored_access_attrs) if stored_access_attrs else None

            record_id = row.get("id", "unknown")
            if check_access(str(record_id), access_attrs_obj, current_user_attrs):
                filtered_rows.append(row)

        return filtered_rows

    async def authorized_fetch_one(
        self,
        table: str,
        where: Mapping[str, Any] | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch one row with automatic access control checking."""
        results = await self.authorized_fetch_all(
            table=table,
            where=where,
            limit=1,
            order_by=order_by,
        )

        return results[0] if results else None
