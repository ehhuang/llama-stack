# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
from tempfile import TemporaryDirectory

import pytest

from llama_stack.providers.utils.sqlstore.api import ColumnType
from llama_stack.providers.utils.sqlstore.sqlalchemy_sqlstore import SqlAlchemySqlStoreImpl
from llama_stack.providers.utils.sqlstore.sqlstore import SqliteSqlStoreConfig


@pytest.mark.asyncio
async def test_sqlstore_pagination_basic():
    """Test basic pagination functionality at the SQL store level."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = SqlAlchemySqlStoreImpl(SqliteSqlStoreConfig(db_path=db_path))

        # Create test table
        await store.create_table(
            "test_records",
            {
                "id": ColumnType.STRING,
                "created_at": ColumnType.INTEGER,
                "name": ColumnType.STRING,
            },
        )

        # Insert test data
        base_time = int(time.time())
        test_data = [
            {"id": "zebra", "created_at": base_time + 1, "name": "First"},
            {"id": "apple", "created_at": base_time + 2, "name": "Second"},
            {"id": "moon", "created_at": base_time + 3, "name": "Third"},
            {"id": "banana", "created_at": base_time + 4, "name": "Fourth"},
            {"id": "car", "created_at": base_time + 5, "name": "Fifth"},
        ]

        for record in test_data:
            await store.insert("test_records", record)

        # Test 1: First page (no cursor)
        result = await store.fetch_all(
            table="test_records",
            order_by=[("created_at", "desc")],
            cursor_column="created_at",
            limit=2,
        )
        assert len(result.data) == 2
        assert result.data[0]["id"] == "car"  # Most recent first
        assert result.data[1]["id"] == "banana"
        assert result.has_more is True

        # Test 2: Second page using cursor
        result2 = await store.fetch_all(
            table="test_records",
            order_by=[("created_at", "desc")],
            cursor_column="created_at",
            cursor_id="banana",
            limit=2,
        )
        assert len(result2.data) == 2
        assert result2.data[0]["id"] == "moon"
        assert result2.data[1]["id"] == "apple"
        assert result2.has_more is True

        # Test 3: Final page
        result3 = await store.fetch_all(
            table="test_records",
            order_by=[("created_at", "desc")],
            cursor_column="created_at",
            cursor_id="apple",
            limit=2,
        )
        assert len(result3.data) == 1
        assert result3.data[0]["id"] == "zebra"
        assert result3.has_more is False


@pytest.mark.asyncio
async def test_sqlstore_pagination_with_filter():
    """Test pagination with WHERE conditions."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = SqlAlchemySqlStoreImpl(SqliteSqlStoreConfig(db_path=db_path))

        # Create test table
        await store.create_table(
            "test_records",
            {
                "id": ColumnType.STRING,
                "created_at": ColumnType.INTEGER,
                "category": ColumnType.STRING,
            },
        )

        # Insert test data with categories
        base_time = int(time.time())
        test_data = [
            {"id": "xyz", "created_at": base_time + 1, "category": "A"},
            {"id": "def", "created_at": base_time + 2, "category": "B"},
            {"id": "pqr", "created_at": base_time + 3, "category": "A"},
            {"id": "abc", "created_at": base_time + 4, "category": "B"},
        ]

        for record in test_data:
            await store.insert("test_records", record)

        # Test pagination with filter
        result = await store.fetch_all(
            table="test_records",
            where={"category": "A"},
            order_by=[("created_at", "desc")],
            cursor_column="created_at",
            limit=1,
        )
        assert len(result.data) == 1
        assert result.data[0]["id"] == "pqr"  # Most recent category A
        assert result.has_more is True

        # Second page with filter
        result2 = await store.fetch_all(
            table="test_records",
            where={"category": "A"},
            order_by=[("created_at", "desc")],
            cursor_column="created_at",
            cursor_id="pqr",
            limit=1,
        )
        assert len(result2.data) == 1
        assert result2.data[0]["id"] == "xyz"
        assert result2.has_more is False


@pytest.mark.asyncio
async def test_sqlstore_pagination_ascending_order():
    """Test pagination with ascending order."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = SqlAlchemySqlStoreImpl(SqliteSqlStoreConfig(db_path=db_path))

        # Create test table
        await store.create_table(
            "test_records",
            {
                "id": ColumnType.STRING,
                "created_at": ColumnType.INTEGER,
            },
        )

        # Insert test data
        base_time = int(time.time())
        test_data = [
            {"id": "gamma", "created_at": base_time + 1},
            {"id": "alpha", "created_at": base_time + 2},
            {"id": "beta", "created_at": base_time + 3},
        ]

        for record in test_data:
            await store.insert("test_records", record)

        # Test ascending order
        result = await store.fetch_all(
            table="test_records",
            order_by=[("created_at", "asc")],
            cursor_column="created_at",
            limit=1,
        )
        assert len(result.data) == 1
        assert result.data[0]["id"] == "gamma"  # Oldest first
        assert result.has_more is True

        # Second page with ascending order
        result2 = await store.fetch_all(
            table="test_records",
            order_by=[("created_at", "asc")],
            cursor_column="created_at",
            cursor_id="gamma",
            limit=1,
        )
        assert len(result2.data) == 1
        assert result2.data[0]["id"] == "alpha"
        assert result2.has_more is True
