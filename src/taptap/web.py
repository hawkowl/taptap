import attr
import cattr
import json

from typing import List
from attr.validators import instance_of

from twisted.web.resource import Resource
from twisted.web.static import File

from klein import Klein

from .work import load_works, dump_works, WordCount


@attr.s
class APIWork(object):
    id = attr.ib(validator=instance_of(int))
    name = attr.ib(validator=instance_of(str))
    counts = attr.ib(validator=instance_of(List[WordCount]))
    word_count = attr.ib(validator=instance_of(int))
    completed = attr.ib(validator=instance_of(bool), default=False)

    @classmethod
    def from_work(cls, work):

        word_count = sorted(work.counts, key=lambda x: x.at)[-1].count

        return cls(id=work.id,
                   name=work.name,
                   counts=work.counts,
                   word_count=word_count,
                   completed=work.completed)


def _make_json(item):
    return json.dumps(cattr.dumps(item), separators=(',',':')).encode('utf8')

class APIResource(object):

    app = Klein()

    @app.route('/works/')
    def works_root(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        works = [APIWork.from_work(x) for x in load_works().values()]
        works.sort(key=lambda x: x.id)
        return _make_json(works)

    @app.route('/works/<int:id>')
    def works_item(self, request, id):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        works = load_works()
        return _make_json(APIWork.from_work(works[id]))



class CoreResource(File):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._api = APIResource().app.resource()

    def getChild(self, path, request):

        if request.path[:5] == b"/api/":
            return self._api

        if request.path[:6] == b"/sass/":
            return None

        return super(CoreResource, self).getChild(path, request)
