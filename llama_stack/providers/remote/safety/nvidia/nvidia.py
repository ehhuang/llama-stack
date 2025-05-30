# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import logging
from typing import Any

import requests

from llama_stack.apis.inference import Message
from llama_stack.apis.safety import RunShieldResponse, Safety, SafetyViolation, ViolationLevel
from llama_stack.apis.shields import Shield
from llama_stack.providers.datatypes import ShieldsProtocolPrivate
from llama_stack.providers.utils.inference.openai_compat import convert_message_to_openai_dict_new

from .config import NVIDIASafetyConfig

logger = logging.getLogger(__name__)


class NVIDIASafetyAdapter(Safety, ShieldsProtocolPrivate):
    def __init__(self, config: NVIDIASafetyConfig) -> None:
        """
        Initialize the NVIDIASafetyAdapter with a given safety configuration.

        Args:
            config (NVIDIASafetyConfig): The configuration containing the guardrails service URL and config ID.
        """
        self.config = config

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def register_shield(self, shield: Shield) -> None:
        if not shield.provider_resource_id:
            raise ValueError("Shield model not provided.")

    async def run_shield(
        self, shield_id: str, messages: list[Message], params: dict[str, Any] | None = None
    ) -> RunShieldResponse:
        """
        Run a safety shield check against the provided messages.

        Args:
            shield_id (str): The unique identifier for the shield to be used.
            messages (List[Message]): A list of Message objects representing the conversation history.
            params (Optional[dict[str, Any]]): Additional parameters for the shield check.

        Returns:
            RunShieldResponse: The response containing safety violation details if any.

        Raises:
            ValueError: If the shield with the provided shield_id is not found.
        """
        shield = await self.shield_store.get_shield(shield_id)
        if not shield:
            raise ValueError(f"Shield {shield_id} not found")

        self.shield = NeMoGuardrails(self.config, shield.shield_id)
        return await self.shield.run(messages)


class NeMoGuardrails:
    """
    A class that encapsulates NVIDIA's guardrails safety logic.

    Sends messages to the guardrails service and interprets the response to determine
    if a safety violation has occurred.
    """

    def __init__(
        self,
        config: NVIDIASafetyConfig,
        model: str,
        threshold: float = 0.9,
        temperature: float = 1.0,
    ):
        """
        Initialize a NeMoGuardrails instance with the provided parameters.

        Args:
            config (NVIDIASafetyConfig): The safety configuration containing the config ID and guardrails URL.
            model (str): The identifier or name of the model to be used for safety checks.
            threshold (float, optional): The threshold for flagging violations. Defaults to 0.9.
            temperature (float, optional): The temperature setting for the underlying model. Must be greater than 0. Defaults to 1.0.

        Raises:
            ValueError: If temperature is less than or equal to 0.
            AssertionError: If config_id is not provided in the configuration.
        """
        self.config_id = config.config_id
        self.model = model
        assert self.config_id is not None, "Must provide config id"
        if temperature <= 0:
            raise ValueError("Temperature must be greater than 0")

        self.temperature = temperature
        self.threshold = threshold
        self.guardrails_service_url = config.guardrails_service_url

    async def _guardrails_post(self, path: str, data: Any | None):
        """Helper for making POST requests to the guardrails service."""
        headers = {
            "Accept": "application/json",
        }
        response = requests.post(url=f"{self.guardrails_service_url}{path}", headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    async def run(self, messages: list[Message]) -> RunShieldResponse:
        """
        Queries the /v1/guardrails/checks endpoint of the NeMo guardrails deployed API.

        Args:
            messages (List[Message]): A list of Message objects to be checked for safety violations.

        Returns:
            RunShieldResponse: If the response indicates a violation ("blocked" status), returns a
            RunShieldResponse with a SafetyViolation; otherwise, returns a RunShieldResponse with violation set to None.

        Raises:
            requests.HTTPError: If the POST request fails.
        """
        request_messages = [await convert_message_to_openai_dict_new(message) for message in messages]
        request_data = {
            "model": self.model,
            "messages": request_messages,
            "temperature": self.temperature,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "max_tokens": 160,
            "stream": False,
            "guardrails": {
                "config_id": self.config_id,
            },
        }
        response = await self._guardrails_post(path="/v1/guardrail/checks", data=request_data)

        if response["status"] == "blocked":
            user_message = "Sorry I cannot do this."
            metadata = response["rails_status"]

            return RunShieldResponse(
                violation=SafetyViolation(
                    user_message=user_message,
                    violation_level=ViolationLevel.ERROR,
                    metadata=metadata,
                )
            )

        return RunShieldResponse(violation=None)
