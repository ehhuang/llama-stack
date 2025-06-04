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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from llama_stack.distribution.access_control.access_control import default_policy, is_action_allowed
from llama_stack.distribution.access_control.conditions import ProtectedResource
from llama_stack.distribution.access_control.datatypes import AccessRule, Action, Scope
from llama_stack.distribution.datatypes import User
from llama_stack.distribution.request_headers import get_authenticated_user
from llama_stack.log import get_logger

from .api import ColumnDefinition, ColumnType, SqlStore
from .sqlstore import SqlAlchemySqlStoreConfig

logger = get_logger(name=__name__, category="sqlstore")

TYPE_MAPPING: dict[ColumnType, Any] = {
    ColumnType.INTEGER: Integer,
    ColumnType.STRING: String,
    ColumnType.FLOAT: Float,
    ColumnType.BOOLEAN: Boolean,
    ColumnType.DATETIME: DateTime,
    ColumnType.TEXT: Text,
    ColumnType.JSON: JSON,
}

# Hardcoded copy of the default policy that our SQL filtering implements
# WARNING: If default_policy() changes, this constant must be updated accordingly
# or SQL filtering will fall back to conservative mode (safe but less performant)
#
# This policy represents: "Permit all actions when user is in owners list for ALL attribute categories"
# The corresponding SQL logic is implemented in _build_default_policy_where_clause():
# - Public records (no access_attributes) are always accessible
# - Records with access_attributes require user to match ALL categories that exist in the resource
# - Missing categories in the resource are treated as "no restriction" (allow)
# - Within each category, user needs ANY matching value (OR logic)
# - Between categories, user needs ALL categories to match (AND logic)
SQL_OPTIMIZED_POLICY = [
    AccessRule(
        permit=Scope(actions=list(Action)),
        when=["user in owners roles", "user in owners teams", "user in owners projects", "user in owners namespaces"],
    ),
]


class SqlRecord(ProtectedResource):
    """Simple ProtectedResource implementation for SQL records."""

    def __init__(self, record_id: str, table_name: str, access_attributes: dict[str, list[str]] | None = None):
        self.type = f"sql_record::{table_name}"
        self.identifier = record_id

        if access_attributes:
            self.owner = User(
                principal="system",
                attributes=access_attributes,
            )
        else:
            self.owner = User(
                principal="system_public",
                attributes=None,
            )


class SqlAlchemySqlStoreImpl(SqlStore):
    def __init__(self, config: SqlAlchemySqlStoreConfig):
        self.config = config
        self.async_session = async_sessionmaker(create_async_engine(config.engine_str))
        self.metadata = MetaData()

        # Validate that our hardcoded policy matches the actual default policy
        self._validate_sql_optimized_policy()

    def _validate_sql_optimized_policy(self) -> None:
        """Validate that SQL_OPTIMIZED_POLICY matches the actual default_policy().

        This ensures that if default_policy() changes, we detect the mismatch and
        can update our SQL filtering logic accordingly.
        """
        actual_default = default_policy()

        if SQL_OPTIMIZED_POLICY != actual_default:
            # Log a warning but don't fail - SQL filtering will use conservative mode
            # This is safe but less performant
            logger.warning(
                f"SQL_OPTIMIZED_POLICY does not match default_policy(). "
                f"SQL filtering will use conservative mode. "
                f"Expected: {SQL_OPTIMIZED_POLICY}, Got: {actual_default}",
            )

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
            is_nullable = True

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

        if table not in self.metadata.tables:
            sqlalchemy_table = Table(table, self.metadata, *sqlalchemy_columns)
        else:
            sqlalchemy_table = self.metadata.tables[table]

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

    async def create_table_with_access_control(
        self, table: str, schema: Mapping[str, ColumnType | ColumnDefinition]
    ) -> None:
        """Create a table with built-in access control support."""
        # TODO: clean this up
        await self._migrate_access_attributes_column(table)

        enhanced_schema = dict(schema)
        if "access_attributes" not in enhanced_schema:
            enhanced_schema["access_attributes"] = ColumnType.JSON

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
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
                    {"table_name": table},
                )
                table_exists = result.fetchone() is not None

                if not table_exists:
                    return

                result = await conn.execute(text("PRAGMA table_info(:table_name)"), {"table_name": table})
                columns = result.fetchall()
                column_names = [col[1] for col in columns]

                if "access_attributes" in column_names:
                    return

                add_column_sql = text(f"ALTER TABLE {table} ADD COLUMN access_attributes JSON")
                await conn.execute(add_column_sql)

            except Exception:
                # If any error occurs during migration, log it but don't fail
                # The table creation will handle adding the column
                pass

    async def authorized_insert(self, table: str, data: Mapping[str, Any]) -> None:
        """Insert a row with automatic access control attribute capture."""
        enhanced_data = dict(data)

        current_user = get_authenticated_user()
        if current_user and current_user.attributes:
            enhanced_data["access_attributes"] = current_user.attributes
        else:
            enhanced_data["access_attributes"] = None

        await self.insert(table, enhanced_data)

    def _build_access_control_where_clause(self, policy: list[AccessRule]) -> str:
        """Build SQL WHERE clause for access control filtering.

        Only applies SQL filtering for the default policy to ensure correctness.
        For custom policies, uses conservative filtering to avoid blocking legitimate access.
        """
        # Check if this is the default policy (empty policy defaults to default_policy in is_action_allowed)
        # or if it explicitly matches our hardcoded optimized policy
        if not policy or policy == SQL_OPTIMIZED_POLICY:
            # Safe to use optimized SQL filtering for default policy
            return self._build_default_policy_where_clause()
        else:
            # Custom policy - use conservative filtering only
            return self._build_conservative_where_clause()

    def _build_default_policy_where_clause(self) -> str:
        """Build SQL WHERE clause for the default policy.

        Default policy: permit all actions when user in owners [roles, teams, projects, namespaces]
        This means user must match ALL attribute categories that exist in the resource.
        """
        current_user = get_authenticated_user()

        if not current_user or not current_user.attributes:
            # User has no attributes, only show public records
            return "(access_attributes IS NULL OR access_attributes = 'null' OR access_attributes = '{}')"
        else:
            # Show public records (no access control)
            base_conditions = ["access_attributes IS NULL", "access_attributes = 'null'", "access_attributes = '{}'"]

            # For records with access control, check each attribute category the user has
            # Default policy logic: user must be in owners list for ALL categories that exist
            user_attr_conditions = []

            for attr_key, user_values in current_user.attributes.items():
                if user_values:  # User has values for this attribute category
                    # Build condition: "IF resource has this category, user must match"
                    value_conditions = []
                    for value in user_values:
                        # Check if user's value exists in the resource's array for this category
                        value_conditions.append(f"JSON_EXTRACT(access_attributes, '$.{attr_key}') LIKE '%\"{value}\"%'")

                    if value_conditions:
                        # Category condition: (category_missing OR user_matches_category)
                        # This implements default policy: missing category in resource = no restriction
                        category_missing = f"JSON_EXTRACT(access_attributes, '$.{attr_key}') IS NULL"
                        user_matches_category = f"({' OR '.join(value_conditions)})"

                        # If the category exists in the resource, user must match; if missing, allow
                        user_attr_conditions.append(f"({category_missing} OR {user_matches_category})")

            if user_attr_conditions:
                # Records are accessible if they're public OR user satisfies all attribute requirements
                all_requirements_met = f"({' AND '.join(user_attr_conditions)})"
                base_conditions.append(all_requirements_met)
                return f"({' OR '.join(base_conditions)})"
            else:
                # User has no valid attributes, only show public records
                return f"({' OR '.join(base_conditions)})"

    def _build_conservative_where_clause(self) -> str:
        """Conservative SQL filtering for custom policies.

        Only filters records we're 100% certain would be denied by any reasonable policy.
        """
        current_user = get_authenticated_user()

        if not current_user:
            # No authenticated user - conservative assumption is public-only access
            return "(access_attributes IS NULL OR access_attributes = 'null' OR access_attributes = '{}')"

        # User is authenticated - show everything, let policy decide
        # This eliminates the risk of SQL being more restrictive than policy
        return "1=1"

    async def authorized_fetch_all(
        self,
        table: str,
        policy: list[AccessRule],
        where: Mapping[str, Any] | None = None,
        limit: int | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all rows with automatic access control filtering."""
        access_where = self._build_access_control_where_clause(policy)
        rows = await self.fetch_all(
            table=table,
            where=where,
            where_sql=access_where,
            limit=limit,
            order_by=order_by,
        )

        current_user = get_authenticated_user()
        filtered_rows = []

        for row in rows:
            stored_access_attrs = row.get("access_attributes")

            record_id = row.get("id", "unknown")
            sql_record = SqlRecord(str(record_id), table, stored_access_attrs)

            if is_action_allowed(policy, Action.READ, sql_record, current_user):
                filtered_rows.append(row)

        return filtered_rows

    async def authorized_fetch_one(
        self,
        table: str,
        policy: list[AccessRule],
        where: Mapping[str, Any] | None = None,
        order_by: list[tuple[str, Literal["asc", "desc"]]] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch one row with automatic access control checking."""
        results = await self.authorized_fetch_all(
            table=table,
            policy=policy,
            where=where,
            limit=1,
            order_by=order_by,
        )

        return results[0] if results else None
