from alchimia import TWISTED_STRATEGY

from sqlalchemy import create_engine, MetaData
from sqlalchemy import (
    Table, Column, Integer, String
)
from sqlalchemy.schema import CreateTable

from twisted.internet import reactor

metadata = MetaData()

_engine = None


def get_engine():

    global _engine
    if _engine is None:
        _engine = create_engine(
            "sqlite:///taptap.db", reactor=reactor, strategy=TWISTED_STRATEGY
        )

    return _engine




user_table = Table("users", metadata,
                    Column("id", Integer(), primary_key=True),
                    Column("name", String()),
)


if __name__ == "__main__":

    from twisted.internet.task import react
    from twisted.internet.defer import ensureDeferred

    async def main(reactor):
        engine = get_engine()
        await engine.execute(CreateTable(user_table))

    react(lambda r: ensureDeferred(main(r)))
