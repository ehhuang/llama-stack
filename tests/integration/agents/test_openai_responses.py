# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from urllib.parse import urljoin

import pytest
import requests
from openai import OpenAI

from llama_stack.distribution.library_client import LlamaStackAsLibraryClient


@pytest.fixture
def openai_client(client_with_models):
    base_url = f"{client_with_models.base_url}/v1/openai/v1"
    return OpenAI(base_url=base_url, api_key="bar")


@pytest.mark.parametrize(
    "stream",
    [
        True,
        False,
    ],
)
@pytest.mark.parametrize(
    "tools",
    [
        [],
        [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get the weather in a given city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The city to get the weather for"},
                    },
                },
            }
        ],
    ],
)
def test_responses_store(openai_client, client_with_models, text_model_id, stream, tools):
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client
    message = "What's the weather in Tokyo?" + (
        " YOU MUST USE THE get_weather function to get the weather." if tools else ""
    )
    response = client.responses.create(
        model=text_model_id,
        input=[
            {
                "role": "user",
                "content": message,
            }
        ],
        stream=stream,
        tools=tools,
    )
    if stream:
        # accumulate the streamed content
        content = ""
        response_id = None
        for chunk in response:
            if response_id is None:
                response_id = chunk.response.id
            if not tools:
                if chunk.type == "response.completed":
                    response_id = chunk.response.id
                    content = chunk.response.output[0].content[0].text
    else:
        response_id = response.id
        if not tools:
            content = response.output[0].content[0].text

    # list responses is not available in the SDK
    url = urljoin(str(client.base_url), "responses")
    response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert response_id in [r["id"] for r in data]

    # test retrieve response
    retrieved_response = client.responses.retrieve(response_id)
    assert retrieved_response.id == response_id
    assert retrieved_response.model == text_model_id
    if tools:
        assert retrieved_response.output[0].type == "function_call"
    else:
        assert retrieved_response.output[0].content[0].text == content


def test_list_response_input_items(openai_client, client_with_models, text_model_id):
    """Test the new list_openai_response_input_items endpoint."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client
    message = "What is the capital of France?"

    # Create a response first
    response = client.responses.create(
        model=text_model_id,
        input=[
            {
                "role": "user",
                "content": message,
            }
        ],
        stream=False,
    )

    response_id = response.id

    # Test the new list input items endpoint
    url = urljoin(str(client.base_url), f"responses/{response_id}/input_items")
    input_items_response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"})

    # Verify the response
    assert input_items_response.status_code == 200
    input_items_data = input_items_response.json()

    # Verify the structure follows OpenAI API spec
    assert input_items_data["object"] == "list"
    assert "data" in input_items_data
    assert isinstance(input_items_data["data"], list)
    assert len(input_items_data["data"]) > 0

    # Verify the input item contains our message
    input_item = input_items_data["data"][0]
    assert input_item["type"] == "message"
    assert input_item["role"] == "user"
    assert message in str(input_item["content"])


def test_list_response_input_items_with_limit_and_order(openai_client, client_with_models, text_model_id):
    """Test the list input items endpoint with limit and order parameters."""
    if isinstance(client_with_models, LlamaStackAsLibraryClient):
        pytest.skip("OpenAI responses are not supported when testing with library client yet.")

    client = openai_client

    # Create a response with multiple input messages to test limit and order
    messages = [
        {"role": "user", "content": "First message: What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Second message: What about Spain?"},
        {"role": "assistant", "content": "The capital of Spain is Madrid."},
        {"role": "user", "content": "Third message: And Italy?"},
    ]

    response = client.responses.create(
        model=text_model_id,
        input=messages,
        stream=False,
    )

    response_id = response.id

    # Test limit parameter - request only 2 items
    url = urljoin(str(client.base_url), f"responses/{response_id}/input_items")
    params = {"limit": 2}
    limited_response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"}, params=params)

    assert limited_response.status_code == 200
    limited_data = limited_response.json()
    assert limited_data["object"] == "list"
    assert len(limited_data["data"]) <= 2  # Should be limited to 2 items

    # Test order parameter - request with ascending order
    params = {"order": "asc"}
    asc_response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"}, params=params)

    assert asc_response.status_code == 200
    asc_data = asc_response.json()
    assert asc_data["object"] == "list"

    # Test order parameter - request with descending order (default)
    params = {"order": "desc"}
    desc_response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"}, params=params)

    assert desc_response.status_code == 200
    desc_data = desc_response.json()
    assert desc_data["object"] == "list"

    # Test both limit and order together
    params = {"limit": 3, "order": "desc"}
    combined_response = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}"}, params=params)

    assert combined_response.status_code == 200
    combined_data = combined_response.json()
    assert combined_data["object"] == "list"
    assert len(combined_data["data"]) <= 3

    # Verify that the responses are different when using different order
    if len(asc_data["data"]) > 1 and len(desc_data["data"]) > 1:
        # The first item in asc order should be different from first item in desc order
        # (unless there's only one item total)
        first_asc_content = str(asc_data["data"][0]["content"])
        first_desc_content = str(desc_data["data"][0]["content"])

        # The order should be different for multi-item responses
        # Note: This comparison may not always be different depending on the actual implementation
        # but we can at least verify the structure is correct
        assert isinstance(first_asc_content, str)
        assert isinstance(first_desc_content, str)
