import attr
import cattr
import json

from typing import List
from attr.validators import instance_of


from twisted.python.filepath import FilePath


@attr.s
class WordCount(object):
    at = attr.ib(validator=instance_of(int))
    count = attr.ib(validator=instance_of(int))

@attr.s
class Work(object):
    id = attr.ib(validator=instance_of(int))
    name = attr.ib(validator=instance_of(str))
    counts = attr.ib(validator=instance_of(List[WordCount]))
    completed = attr.ib(validator=instance_of(bool), default=False)


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
        x[y.id] = y

    return x
