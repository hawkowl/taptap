import os
from alchimia import TWISTED_STRATEGY

from sqlalchemy import create_engine, MetaData
from sqlalchemy import (
    Table, Column, Integer, String, ForeignKey, Boolean, UniqueConstraint
)
from sqlalchemy.schema import CreateTable

from twisted.internet import reactor

metadata = MetaData()

_engine = None


def get_engine():

    global _engine
    if _engine is None:
        _engine = create_engine(
            os.environ["DATABASE_URL"], reactor=reactor, strategy=TWISTED_STRATEGY,
        )

    return _engine


user_table = Table("users", metadata,
                   Column("id", Integer(), primary_key=True),
                   Column("name", String()),
                   Column("tzoffset", Integer()),
)

cookie_table = Table("cookies", metadata,
                     Column("cookie", String(), primary_key=True),
                     Column("id", Integer(), nullable=False),
                     Column("expires", Integer(), nullable=False),
)

work_table = Table("works", metadata,
                   Column("id", Integer(), primary_key=True),
                   Column("user", Integer(), ForeignKey("users.id"), nullable=False),
                   Column("name", String(), nullable=False),
                   Column("word_target", Integer(), nullable=False),
                   Column("completed", Boolean(), nullable=False),
)

counts_table = Table("counts", metadata,
                     Column("work", Integer(), ForeignKey("works.id"), nullable=False),
                     Column("at", Integer(), nullable=False),
                     Column("count", Integer(), nullable=False),
                     UniqueConstraint("work", "at", "count"),
)




if __name__ == "__main__":

    from twisted.internet.task import react
    from twisted.internet.defer import ensureDeferred

    async def main(reactor):
        engine = get_engine()

        try:
            await engine.execute(CreateTable(user_table))
        except:
            pass

        try:
            await engine.execute(CreateTable(cookie_table))
        except:
            pass

        try:
            await engine.execute(CreateTable(work_table))
        except:
            pass

        try:
            await engine.execute(CreateTable(counts_table))
        except:
            pass

    react(lambda r: ensureDeferred(main(r)))
