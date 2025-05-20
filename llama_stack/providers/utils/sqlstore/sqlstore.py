# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from llama_stack.distribution.utils.config_dirs import RUNTIME_BASE_DIR

from .api import SqlStore


class SqlStoreType(Enum):
    sqlalchemy = "sqlalchemy"


class SqlalchemySqlStoreConfig(BaseModel):
    type: Literal["sqlalchemy"] = SqlStoreType.sqlalchemy.value
    engine_type: str = Field(
        default="sqlite+aiosqlite",
        description="SQLAlchemy engine type, e.g. sqlite+aiosqlite",
    )
    db_path: str = Field(
        default=(RUNTIME_BASE_DIR / "sqlstore.db").as_posix(),
        description="Database path, e.g. ~/.llama/distributions/ollama/sqlstore.db",
    )

    @property
    def engine_str(self) -> str:
        return self.engine_type + ":///" + Path(self.db_path).expanduser().as_posix()

    @classmethod
    def sample_run_config(cls, __distro_dir__: str, db_name: str = "sqlstore.db"):
        return cls(
            type="sqlalchemy",
            engine_type="sqlite+aiosqlite",
            db_path="${env.SQLITE_STORE_DIR:" + __distro_dir__ + "}/" + db_name,
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
