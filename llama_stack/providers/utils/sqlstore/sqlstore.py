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
    sqlalchemy = "sqlalchemy"


class SqlalchemySqlStoreConfig(BaseModel):
    type: Literal["sqlalchemy"] = SqlStoreType.sqlalchemy.value
    engine_str: str = Field(
        default="sqlite+aiosqlite:///" + (RUNTIME_BASE_DIR / "sqlstore.db").as_posix(),
        description="SQLAlchemy engine string, e.g. sqlite:///{db_path}",
    )

    @classmethod
    def sample_run_config(cls, __distro_dir__: str, db_name: str = "sqlstore.db"):
        return cls(
            type="sqlalchemy",
            engine_str="sqlite+aiosqlite:///" + "${env.SQLITE_STORE_DIR:" + __distro_dir__ + "}/" + db_name,
        )


SqlStoreConfig = Annotated[
    SqlalchemySqlStoreConfig,
    Field(discriminator="type", default=SqlStoreType.sqlalchemy.value),
]


def sqlstore_impl(config: SqlStoreConfig) -> SqlStore:
    if config.type == SqlStoreType.sqlalchemy.value:
        from .sqlalchemy.sqlalchemy import SqlalchemySqlStoreImpl

        impl = SqlalchemySqlStoreImpl(config)
    else:
        raise ValueError(f"Unknown sqlstore type {config.type}")

    return impl
