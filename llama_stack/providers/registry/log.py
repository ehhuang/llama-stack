# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from llama_stack.providers.datatypes import (
    Api,
    InlineProviderSpec,
    ProviderSpec,
)


def available_providers() -> list[ProviderSpec]:
    return [
        InlineProviderSpec(
            api=Api.log,
            provider_type="inline::meta-reference",
            pip_packages=[
                "sqlite3",
            ],
            module="llama_stack.providers.inline.log.meta_reference",
            config_class="llama_stack.providers.inline.log.meta_reference.config.LogConfig",
        ),
    ]
