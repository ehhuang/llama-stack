# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
from tempfile import TemporaryDirectory

import pytest

from llama_stack.apis.agents import Order
from llama_stack.apis.agents.openai_responses import (
    OpenAIResponseInput,
    OpenAIResponseObject,
)
from llama_stack.providers.utils.responses.responses_store import ResponsesStore
from llama_stack.providers.utils.sqlstore.sqlstore import SqliteSqlStoreConfig


def create_test_response_object(
    response_id: str, created_timestamp: int, model: str = "test-model"
) -> OpenAIResponseObject:
    """Helper to create a test response object."""
    return OpenAIResponseObject(
        id=response_id,
        created_at=created_timestamp,
        model=model,
        object="response",
        output=[],  # Required field
        status="completed",  # Required field
    )


def create_test_response_input(content: str = "test input") -> OpenAIResponseInput:
    """Helper to create a test response input."""
    from llama_stack.apis.agents.openai_responses import OpenAIResponseMessage

    return OpenAIResponseMessage(
        id="input-id",
        content=content,
        role="user",
        type="message",
    )


@pytest.mark.asyncio
async def test_responses_store_pagination_basic():
    """Test basic pagination functionality for responses store."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Create test data with different timestamps
        base_time = int(time.time())
        test_data = [
            ("zebra-resp", base_time + 1),
            ("apple-resp", base_time + 2),
            ("moon-resp", base_time + 3),
            ("banana-resp", base_time + 4),
            ("car-resp", base_time + 5),
        ]

        # Store test responses
        for response_id, timestamp in test_data:
            response = create_test_response_object(response_id, timestamp)
            input_list = [create_test_response_input(f"Input for {response_id}")]
            await store.store_response_object(response, input_list)

        # Test 1: First page with limit=2, descending order (default)
        result = await store.list_responses(limit=2, order=Order.desc)
        assert len(result.data) == 2
        assert result.data[0].id == "car-resp"  # Most recent first
        assert result.data[1].id == "banana-resp"
        assert result.has_more is True
        assert result.last_id == "banana-resp"

        # Test 2: Second page using 'after' parameter
        result2 = await store.list_responses(after="banana-resp", limit=2, order=Order.desc)
        assert len(result2.data) == 2
        assert result2.data[0].id == "moon-resp"
        assert result2.data[1].id == "apple-resp"
        assert result2.has_more is True

        # Test 3: Final page
        result3 = await store.list_responses(after="apple-resp", limit=2, order=Order.desc)
        assert len(result3.data) == 1
        assert result3.data[0].id == "zebra-resp"
        assert result3.has_more is False


@pytest.mark.asyncio
async def test_responses_store_pagination_ascending():
    """Test pagination with ascending order."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Create test data
        base_time = int(time.time())
        test_data = [
            ("delta-resp", base_time + 1),
            ("charlie-resp", base_time + 2),
            ("alpha-resp", base_time + 3),
        ]

        # Store test responses
        for response_id, timestamp in test_data:
            response = create_test_response_object(response_id, timestamp)
            input_list = [create_test_response_input(f"Input for {response_id}")]
            await store.store_response_object(response, input_list)

        # Test ascending order pagination
        result = await store.list_responses(limit=1, order=Order.asc)
        assert len(result.data) == 1
        assert result.data[0].id == "delta-resp"  # Oldest first
        assert result.has_more is True

        # Second page with ascending order
        result2 = await store.list_responses(after="delta-resp", limit=1, order=Order.asc)
        assert len(result2.data) == 1
        assert result2.data[0].id == "charlie-resp"
        assert result2.has_more is True


@pytest.mark.asyncio
async def test_responses_store_pagination_with_model_filter():
    """Test pagination combined with model filtering."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Create test data with different models
        base_time = int(time.time())
        test_data = [
            ("xyz-resp", base_time + 1, "model-a"),
            ("def-resp", base_time + 2, "model-b"),
            ("pqr-resp", base_time + 3, "model-a"),
            ("abc-resp", base_time + 4, "model-b"),
        ]

        # Store test responses
        for response_id, timestamp, model in test_data:
            response = create_test_response_object(response_id, timestamp, model)
            input_list = [create_test_response_input(f"Input for {response_id}")]
            await store.store_response_object(response, input_list)

        # Test pagination with model filter
        result = await store.list_responses(limit=1, model="model-a", order=Order.desc)
        assert len(result.data) == 1
        assert result.data[0].id == "pqr-resp"  # Most recent model-a
        assert result.data[0].model == "model-a"
        assert result.has_more is True

        # Second page with model filter
        result2 = await store.list_responses(after="pqr-resp", limit=1, model="model-a", order=Order.desc)
        assert len(result2.data) == 1
        assert result2.data[0].id == "xyz-resp"
        assert result2.data[0].model == "model-a"
        assert result2.has_more is False


@pytest.mark.asyncio
async def test_responses_store_pagination_invalid_after():
    """Test error handling for invalid 'after' parameter."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Try to paginate with non-existent ID
        with pytest.raises(ValueError, match="Record with id.*'non-existent' not found in table 'openai_responses'"):
            await store.list_responses(after="non-existent", limit=2)


@pytest.mark.asyncio
async def test_responses_store_pagination_no_limit():
    """Test pagination behavior when no limit is specified."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Create test data
        base_time = int(time.time())
        test_data = [
            ("omega-resp", base_time + 1),
            ("beta-resp", base_time + 2),
        ]

        # Store test responses
        for response_id, timestamp in test_data:
            response = create_test_response_object(response_id, timestamp)
            input_list = [create_test_response_input(f"Input for {response_id}")]
            await store.store_response_object(response, input_list)

        # Test without limit (should use default of 50)
        result = await store.list_responses(order=Order.desc)
        assert len(result.data) == 2
        assert result.data[0].id == "beta-resp"  # Most recent first
        assert result.data[1].id == "omega-resp"
        assert result.has_more is False


@pytest.mark.asyncio
async def test_responses_store_get_response_object():
    """Test retrieving a single response object."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Store a test response
        response = create_test_response_object("test-resp", int(time.time()))
        input_list = [create_test_response_input("Test input content")]
        await store.store_response_object(response, input_list)

        # Retrieve the response
        retrieved = await store.get_response_object("test-resp")
        assert retrieved.id == "test-resp"
        assert retrieved.model == "test-model"
        assert len(retrieved.input) == 1
        assert retrieved.input[0].content == "Test input content"

        # Test error for non-existent response
        with pytest.raises(ValueError, match="Response with id non-existent not found"):
            await store.get_response_object("non-existent")


@pytest.mark.asyncio
async def test_responses_store_list_response_input_items():
    """Test listing input items for a response."""
    with TemporaryDirectory() as tmp_dir:
        db_path = tmp_dir + "/test.db"
        store = ResponsesStore(SqliteSqlStoreConfig(db_path=db_path))
        await store.initialize()

        # Store a test response with multiple inputs
        response = create_test_response_object("test-resp", int(time.time()))
        input_list = [
            create_test_response_input("First input"),
            create_test_response_input("Second input"),
            create_test_response_input("Third input"),
        ]
        await store.store_response_object(response, input_list)

        # Test listing input items with default order (desc)
        result = await store.list_response_input_items("test-resp")
        assert len(result.data) == 3
        assert result.data[0].content == "Third input"  # Reversed for desc order
        assert result.data[1].content == "Second input"
        assert result.data[2].content == "First input"

        # Test listing input items with ascending order
        result_asc = await store.list_response_input_items("test-resp", order=Order.asc)
        assert len(result_asc.data) == 3
        assert result_asc.data[0].content == "First input"  # Original order for asc
        assert result_asc.data[1].content == "Second input"
        assert result_asc.data[2].content == "Third input"

        # Test with limit
        result_limited = await store.list_response_input_items("test-resp", limit=2)
        assert len(result_limited.data) == 2
        assert result_limited.data[0].content == "Third input"
        assert result_limited.data[1].content == "Second input"

        # Test error for unsupported features
        with pytest.raises(NotImplementedError, match="After/before pagination is not supported yet"):
            await store.list_response_input_items("test-resp", after="some-id")

        with pytest.raises(NotImplementedError, match="Include is not supported yet"):
            await store.list_response_input_items("test-resp", include=["some-field"])
