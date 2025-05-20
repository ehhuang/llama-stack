from tempfile import TemporaryDirectory

import pytest

from llama_stack.providers.utils.sqlstore.api import ColumnType
from llama_stack.providers.utils.sqlstore.sqlalchemy.sqlalchemy import SqlalchemySqlStoreImpl
from llama_stack.providers.utils.sqlstore.sqlstore import SqlalchemySqlStoreConfig


@pytest.mark.asyncio
async def test_sqlalchemy_sqlstore():
    with TemporaryDirectory() as tmp_dir:
        db_name = "test.db"
        sqlstore = SqlalchemySqlStoreImpl(
            SqlalchemySqlStoreConfig(
                engine_str="sqlite+aiosqlite:///" + tmp_dir + "/" + db_name,
            )
        )
        await sqlstore.create_table(
            table="test",
            schema={
                "id": ColumnType.INTEGER,
                "name": ColumnType.STRING,
            },
        )
        await sqlstore.insert("test", {"id": 1, "name": "test"})
        await sqlstore.insert("test", {"id": 12, "name": "test12"})
        rows = await sqlstore.fetch_all("test")
        assert rows == [{"id": 1, "name": "test"}, {"id": 12, "name": "test12"}]

        row = await sqlstore.fetch_one("test", {"id": 1})
        assert row == {"id": 1, "name": "test"}

        row = await sqlstore.fetch_one("test", {"name": "test12"})
        assert row == {"id": 12, "name": "test12"}

        # order by
        rows = await sqlstore.fetch_all("test", order_by=[("id", "asc")])
        assert rows == [{"id": 1, "name": "test"}, {"id": 12, "name": "test12"}]

        rows = await sqlstore.fetch_all("test", order_by=[("id", "desc")])
        assert rows == [{"id": 12, "name": "test12"}, {"id": 1, "name": "test"}]

        # limit
        rows = await sqlstore.fetch_all("test", limit=1)
        assert rows == [{"id": 1, "name": "test"}]
