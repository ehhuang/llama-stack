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
from llama_stack.providers.utils.kvstore import kvstore_dependencies


def available_providers() -> list[ProviderSpec]:
    return [
        InlineProviderSpec(
            api=Api.files,
            provider_type="inline::meta-reference",
            pip_packages=[] + kvstore_dependencies(),
            module="llama_stack.providers.inline.files.meta_reference",
            config_class="llama_stack.providers.inline.files.meta_reference.config.MetaReferenceFilesImplConfig",
        ),
    ]
