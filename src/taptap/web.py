from twisted.web.resource import Resource
from twisted.web.static import File


class CoreResource(File):

    def getChild(self, path, request):

        if request.path[0] == b"api":
            return File("app/")

        return super(CoreResource, self).getChild(path, request)
