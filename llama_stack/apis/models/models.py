# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from llama_stack.apis.resource import Resource, ResourceType
from llama_stack.log import get_logger
from llama_stack.providers.utils.telemetry.trace_protocol import trace_protocol
from llama_stack.schema_utils import json_schema_type, webmethod

logger = get_logger(name=__name__, category="core")


class CommonModelFields(BaseModel):
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Any additional metadata for this model",
    )


@json_schema_type
class ModelType(StrEnum):
    """Enumeration of supported model types in Llama Stack.
    :cvar llm: Large language model for text generation and completion
    :cvar embedding: Embedding model for converting text to vector representations
    """

    llm = "llm"
    embedding = "embedding"


@json_schema_type
class Model(CommonModelFields, Resource):
    """A model resource representing an AI model registered in Llama Stack.

    :param type: The resource type, always 'model' for model resources
    :param model_type: The type of model (LLM or embedding model)
    :param metadata: Any additional metadata for this model
    :param identifier: Unique identifier for this resource in llama stack
    :param provider_resource_id: Unique identifier for this resource in the provider
    :param provider_id: ID of the provider that owns this resource
    """

    type: Literal[ResourceType.model] = ResourceType.model

    @property
    def model_id(self) -> str:
        return self.identifier

    @property
    def provider_model_id(self) -> str:
        assert self.provider_resource_id is not None, "Provider resource ID must be set"
        return self.provider_resource_id

    model_config = ConfigDict(protected_namespaces=())

    model_type: ModelType = Field(default=ModelType.llm)

    @field_validator("provider_resource_id")
    @classmethod
    def validate_provider_resource_id(cls, v):
        if v is None:
            raise ValueError("provider_resource_id cannot be None")
        return v


class ModelInput(CommonModelFields):
    """A model input for registering a model.

    :param provider_model_id: The identifier of the model in the provider.
    :param provider_id: The identifier of the provider.
    :param model_type: The type of model to register.
    :param model_id: The identifier of the model to register. If model_id == provider_model_id, provider_id/provider_model_id will be used as the identifier. Otherwise,
        model_id will be used as the identifier.
        The behavior of this field will soon change to "always use model_id as the identifier".
    :param use_provider_model_id_as_id: Set to true to use provider_model_id as the identifier. Use model_id if you want to use a different identifier.
    """

    provider_model_id: str | None = None
    provider_id: str | None = None
    model_type: ModelType | None = ModelType.llm
    model_config = ConfigDict(protected_namespaces=())
    # TODO: update behavior of this field to always be the identifier
    model_id: str | None = None
    use_provider_model_id_as_id: bool = False

    def model_post_init(self, __context: Any) -> None:
        if self.model_id is None and self.provider_model_id is None:
            raise ValueError("provider_model_id must be provided")

        if self.model_id == self.provider_model_id:
            logger.warning(
                "`model_id` is now optional. The behavior of this field will change if model_id == provider_model_id. Please remove `model_id` and use `provider_model_id` instead."
            )

        if self.use_provider_model_id_as_id and self.model_id:
            raise ValueError("use_provider_model_id_as_id and model_id cannot be provided together.")


class ListModelsResponse(BaseModel):
    data: list[Model]


@json_schema_type
class OpenAIModel(BaseModel):
    """A model from OpenAI.

    :id: The ID of the model
    :object: The object type, which will be "model"
    :created: The Unix timestamp in seconds when the model was created
    :owned_by: The owner of the model
    """

    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class OpenAIListModelsResponse(BaseModel):
    data: list[OpenAIModel]


@runtime_checkable
@trace_protocol
class Models(Protocol):
    @webmethod(route="/models", method="GET")
    async def list_models(self) -> ListModelsResponse:
        """List all models.

        :returns: A ListModelsResponse.
        """
        ...

    @webmethod(route="/openai/v1/models", method="GET")
    async def openai_list_models(self) -> OpenAIListModelsResponse:
        """List models using the OpenAI API.

        :returns: A OpenAIListModelsResponse.
        """
        ...

    @webmethod(route="/models/{model_id:path}", method="GET")
    async def get_model(
        self,
        model_id: str,
    ) -> Model:
        """Get a model by its identifier.

        :param model_id: The identifier of the model to get.
        :returns: A Model.
        """
        ...

    @webmethod(route="/models", method="POST")
    async def register_model(
        self,
        model_id: str,
        provider_model_id: str | None = None,
        provider_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        model_type: ModelType | None = None,
    ) -> Model:
        """Register a model.

        :param model_id: The identifier of the model to register.
        :param provider_model_id: The identifier of the model in the provider.
        :param provider_id: The identifier of the provider.
        :param metadata: Any additional metadata for this model.
        :param model_type: The type of model to register.
        :returns: A Model.
        """
        ...

    @webmethod(route="/models/{model_id:path}", method="DELETE")
    async def unregister_model(
        self,
        model_id: str,
    ) -> None:
        """Unregister a model.

        :param model_id: The identifier of the model to unregister.
        """
        ...
