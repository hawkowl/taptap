from twisted.web.resource import Resource
from twisted.web.static import File

from klein import Klein

from .work import load_works, dump_works

class APIResource(object):

    app = Klein()

    @app.route('/works/')
    def works_root(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        works = load_works()
        return dump_works(list(works.values()))

    @app.route('/works/<int:id>')
    def works_item(self, request, id):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        works = load_works()
        return dump_works(works[id])



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
