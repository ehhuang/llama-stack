# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any

from pydantic import BaseModel, Field

from llama_stack.distribution.utils.config_dirs import RUNTIME_BASE_DIR


class LogConfig(BaseModel):
    log_db_path: str = Field(
        default=(RUNTIME_BASE_DIR / "log_store.db").as_posix(),
        description="The path to the SQLite database to use for storing logs, e.g.chat completion history",
    )

    @classmethod
    def sample_run_config(cls, __distro_dir__: str, db_name: str = "log_store.db") -> dict[str, Any]:
        return {
            "history_db_path": "${env.HISTORY_STORE_DIR:" + __distro_dir__ + "}/" + db_name,
        }
