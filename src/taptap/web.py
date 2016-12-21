from twisted.web.resource import Resource
from twisted.web.static import File

from klein import Klein

class APIResource(object):

    app = Klein()

    @app.route('/works/')
    def works_root(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        return b'[{"id": 1}, {"id": 2}]'



class CoreResource(File):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._api = APIResource().app.resource()

    def getChild(self, path, request):

        if request.path[:5] == b"/api/":
            return self._api

        return super(CoreResource, self).getChild(path, request)
