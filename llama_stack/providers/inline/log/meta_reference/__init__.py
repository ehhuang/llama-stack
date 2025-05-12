# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any

from llama_stack.distribution.datatypes import Api

from .config import LogConfig

__all__ = ["LogConfig"]


async def get_provider_impl(config: LogConfig, deps: dict[Api, Any]):
    from .log import LogAdapter

    impl = LogAdapter(config, deps)
    await impl.initialize()
    return impl
