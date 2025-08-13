# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock

from llama_stack.apis.models import Model, ModelType
from llama_stack.apis.inference import (
    OpenAIUserMessageParam,
    OpenAIChatCompletion,
    OpenAICompletion,
)
from llama_stack.providers.remote.inference.tgi.tgi import TGIAdapter


@pytest.mark.asyncio
async def test_tgi_openai_chat_completion():
    """Test that TGI adapter properly implements OpenAI chat completion."""
    # Create adapter
    adapter = TGIAdapter()
    
    # Mock the HuggingFace client
    adapter.client = AsyncMock()
    adapter.max_tokens = 4096
    adapter.model_id = "meta-llama/Llama-3.2-1B-Instruct"
    
    # Mock model_store
    adapter.model_store = AsyncMock()
    test_model = Model(
        identifier="test-model",
        provider_resource_id="meta-llama/Llama-3.2-1B-Instruct",
        provider_id="tgi",
        model_type=ModelType.llm,
        metadata={}
    )
    adapter.model_store.get_model = AsyncMock(return_value=test_model)
    
    # Mock the register_helper's get_llama_model method
    adapter.register_helper.get_llama_model = Mock(return_value="meta-llama/Llama-3.2-1B-Instruct")
    
    # Set up the huggingface_repo_to_llama_model_id mapping
    adapter.huggingface_repo_to_llama_model_id = {
        "meta-llama/Llama-3.2-1B-Instruct": "Llama-3.2-1B-Instruct"
    }
    
    # Mock the HF client's text_generation response
    mock_response = MagicMock()
    mock_response.details.finish_reason = "stop"
    mock_response.details.tokens = [
        MagicMock(text="Hello! "),
        MagicMock(text="How "),
        MagicMock(text="can "),
        MagicMock(text="I "),
        MagicMock(text="help "),
        MagicMock(text="you?")
    ]
    adapter.client.text_generation = AsyncMock(return_value=mock_response)
    
    # Prepare OpenAI-formatted messages
    messages = [
        OpenAIUserMessageParam(role="user", content="Hello")
    ]
    
    # Call the OpenAI chat completion endpoint
    result = await adapter.openai_chat_completion(
        model="test-model",
        messages=messages,
        stream=False
    )
    
    # Verify the result
    assert result is not None
    assert isinstance(result, OpenAIChatCompletion)
    assert hasattr(result, 'choices')
    assert len(result.choices) == 1
    
    choice = result.choices[0]
    assert hasattr(choice, 'message')
    assert choice.message.role == "assistant"
    assert "Hello! How can I help you?" in choice.message.content
    assert choice.finish_reason == "stop"


@pytest.mark.asyncio
async def test_tgi_openai_completion():
    """Test that TGI adapter properly implements OpenAI completion."""
    # Create adapter
    adapter = TGIAdapter()
    
    # Mock the HuggingFace client
    adapter.client = AsyncMock()
    adapter.max_tokens = 4096
    adapter.model_id = "meta-llama/Llama-3.2-1B-Instruct"
    
    # Mock model_store
    adapter.model_store = AsyncMock()
    test_model = Model(
        identifier="test-model",
        provider_resource_id="meta-llama/Llama-3.2-1B-Instruct",
        provider_id="tgi",
        model_type=ModelType.llm,
        metadata={}
    )
    adapter.model_store.get_model = AsyncMock(return_value=test_model)
    
    # Mock the register_helper's get_llama_model method
    adapter.register_helper.get_llama_model = Mock(return_value="meta-llama/Llama-3.2-1B-Instruct")
    
    # Set up the huggingface_repo_to_llama_model_id mapping
    adapter.huggingface_repo_to_llama_model_id = {
        "meta-llama/Llama-3.2-1B-Instruct": "Llama-3.2-1B-Instruct"
    }
    
    # Mock the HF client's text_generation response
    mock_response = MagicMock()
    mock_response.details.finish_reason = "stop"
    mock_response.details.tokens = [
        MagicMock(text="This "),
        MagicMock(text="is "),
        MagicMock(text="a "),
        MagicMock(text="completion.")
    ]
    adapter.client.text_generation = AsyncMock(return_value=mock_response)
    
    # Call the OpenAI completion endpoint
    result = await adapter.openai_completion(
        model="test-model",
        prompt="Complete this sentence: The weather today",
        stream=False
    )
    
    # Verify the result
    assert result is not None
    assert isinstance(result, OpenAICompletion)
    assert hasattr(result, 'choices')
    assert len(result.choices) == 1
    
    choice = result.choices[0]
    assert hasattr(choice, 'text')
    assert "This is a completion." in choice.text
    assert choice.finish_reason == "stop"


@pytest.mark.asyncio
async def test_tgi_mro_resolution():
    """Test that TGI's MRO properly resolves OpenAI mixin methods."""
    # Verify that the mixin methods come before the protocol methods in MRO
    mro_classes = [cls.__name__ for cls in TGIAdapter.__mro__]
    
    # Check that OpenAI mixins come before InferenceProvider
    openai_chat_mixin_index = mro_classes.index("OpenAIChatCompletionToLlamaStackMixin")
    openai_completion_mixin_index = mro_classes.index("OpenAICompletionToLlamaStackMixin")
    inference_provider_index = mro_classes.index("InferenceProvider")
    
    assert openai_chat_mixin_index < inference_provider_index, "OpenAI chat mixin should come before InferenceProvider in MRO"
    assert openai_completion_mixin_index < inference_provider_index, "OpenAI completion mixin should come before InferenceProvider in MRO"
    
    # Verify that TGI has the OpenAI methods
    adapter = TGIAdapter()
    assert hasattr(adapter, 'openai_chat_completion')
    assert hasattr(adapter, 'openai_completion')
    
    # Verify the methods are callable
    assert callable(getattr(adapter, 'openai_chat_completion'))
    assert callable(getattr(adapter, 'openai_completion'))