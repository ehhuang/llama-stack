# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import os
from pathlib import Path

import pytest
import yaml
from openai import OpenAI


@pytest.fixture(scope="session")
def verification_config():
    """Load the verification config file."""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        pytest.fail(f"Verification config file not found at {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def provider_metadata():
    return {
        "fireworks": ("https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY"),
        "together": ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
        "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
        "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    }


@pytest.fixture
def provider(request, provider_metadata):
    provider = request.config.getoption("--provider")
    base_url = request.config.getoption("--base-url")

    if provider and base_url and provider_metadata[provider][0] != base_url:
        raise ValueError(f"Provider {provider} is not supported for base URL {base_url}")

    if not provider:
        if not base_url:
            raise ValueError("Provider and base URL are not provided")
        for provider, metadata in provider_metadata.items():
            if metadata[0] == base_url:
                provider = provider
                break

    return provider


@pytest.fixture
def base_url(request, provider, provider_metadata):
    return request.config.getoption("--base-url") or provider_metadata[provider][0]


@pytest.fixture
def api_key(request, provider, provider_metadata):
    return request.config.getoption("--api-key") or os.getenv(provider_metadata[provider][1])


@pytest.fixture
def model_mapping(provider, providers_model_mapping):
    return providers_model_mapping[provider]


@pytest.fixture
def openai_client(base_url, api_key):
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
