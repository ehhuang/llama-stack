# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from llama_stack.distribution.utils.config_dirs import RUNTIME_BASE_DIR

from .api import SqlStore


class SqlStoreType(Enum):
    sqlite = "sqlite"


class SqliteSqlStoreConfig(BaseModel):
    type: Literal["sqlite"] = SqlStoreType.sqlite.value
    db_path: str = Field(
        default=(RUNTIME_BASE_DIR / "sqlstore.db").as_posix(),
        description="File path for the sqlite database",
    )

    @classmethod
    def sample_run_config(cls, __distro_dir__: str, db_name: str = "sqlstore.db"):
        return {
            "type": "sqlite",
            "db_path": "${env.SQLITE_STORE_DIR:" + __distro_dir__ + "}/" + db_name,
        }


SqlStoreConfig = Annotated[
    SqliteSqlStoreConfig,
    Field(discriminator="type", default=SqlStoreType.sqlite.value),
]


def sqlstore_impl(config: SqlStoreConfig) -> SqlStore:
    if config.type == SqlStoreType.sqlite.value:
        from .sqlite.sqlite import SqliteSqlStoreImpl

        impl = SqliteSqlStoreImpl(config)
    else:
        raise ValueError(f"Unknown sqlstore type {config.type}")

    return impl
