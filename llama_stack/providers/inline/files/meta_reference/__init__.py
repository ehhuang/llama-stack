# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any

from llama_stack.distribution.datatypes import Api

from .config import MetaReferenceFilesImplConfig
from .files import MetaReferenceFilesImpl

__all__ = ["MetaReferenceFilesImpl", "MetaReferenceFilesImplConfig"]


async def get_provider_impl(config: MetaReferenceFilesImplConfig, deps: dict[Api, Any]):
    impl = MetaReferenceFilesImpl(config)
    await impl.initialize()
    return impl
