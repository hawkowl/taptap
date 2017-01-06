import attr
import cattr
import json

from typing import List
from attr.validators import instance_of, optional


from twisted.python.filepath import FilePath
from twisted.internet.defer import ensureDeferred

from ._db import get_engine, counts_table, work_table

@attr.s
class WordCount(object):
    at = attr.ib(validator=instance_of(int))
    count = attr.ib(validator=instance_of(int))

    async def save_for(self, id, engine=None):

        if not engine:
            engine = get_engine()

        values = {
            "at": self.at,
            "count": self.count,
            "work": id
        }

        try:
            engine.execute(counts_table.insert().values(**values))
        except:
            pass

        return self

    @classmethod
    async def load_for(cls, for_id, engine=None):

        if not engine:
            engine = get_engine()

        f = await engine.execute(counts_table.select().
                                 where(counts_table.c.work == for_id))
        result = await f.fetchall()
        results = []

        for count in result:
            results.append(cls(
                at=count[counts_table.c.at],
                count=count[counts_table.c.count]))

        return results


@attr.s
class Work(object):
    user = attr.ib(validator=instance_of(int))
    name = attr.ib(validator=instance_of(str))
    counts = attr.ib(validator=instance_of(List[WordCount]))
    word_target = attr.ib(validator=instance_of(int))
    completed = attr.ib(validator=instance_of(bool), default=False)
    id = attr.ib(validator=optional(instance_of(int)), default=None)

    @classmethod
    async def _load_from_data(cls, data, engine):

        counts = await WordCount.load_for(data[work_table.c.id],
                                          engine=engine)

        return cls(
            id=data[work_table.c.id],
            name=data[work_table.c.name],
            user=data[work_table.c.user],
            word_target=data[work_table.c.word_target],
            completed=data[work_table.c.completed],
            counts=counts,
        )

    @classmethod
    async def load(cls, id, engine=None):

        if not engine:
            engine = get_engine()

        f = await engine.execute(work_table.select().
                                 where(work_table.c.id == id))
        result = await f.fetchone()
        return await self._load_from_data(result, engine)


    async def save(self, engine=None):

        if not engine:
            engine = get_engine()

        values = {
            "name": self.name,
            "word_target": self.word_target,
            "completed": self.completed,
            "user": self.user,
        }

        if self.id:
            values["id"] = self.id
            await engine.execute(work_table.update().
                                 where(work_table.c.id == self.id).
                                 values(**values))

        else:
            res = await engine.execute(work_table.insert().values(**values))
            self.id = res.inserted_primary_key[0]

        for count in self.counts:
            await count.save_for(self.id)

        return self



def dump_works(works):
    return json.dumps(cattr.dumps(works), separators=(',',':')).encode('utf8')


def save_works(works):
    dest = FilePath("works.json")
    dest.setContent(dump_works(list(works)))


def load_works():

    dest = FilePath("works.json")

    if not dest.exists():
        dest.setContent(b"[]")

    loaded = cattr.loads(
        json.loads(dest.getContent().decode('utf8')),
        List[Work])

    x = {}

    for y in loaded:
        y.counts.sort(key=lambda x: x.at)
        x[y.id] = y

    return x
