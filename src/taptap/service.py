from twisted.python import usage
from twisted.application import service
from twisted.internet.endpoints import serverFromString

from taptap.web import CoreResource
from twisted.web.server import Site

class TapTapService(service.Service):

    def __init__(self, endpoint):
        self._endpoint = endpoint

    def startService(self):

        from twisted.internet import reactor

        resource = CoreResource('app')
        site = Site(resource)
        endpoint = serverFromString(reactor, self._endpoint)
        return endpoint.listen(site)



class Options(usage.Options):
    synopsis = "[options]"
    longdesc = "Personal writing stats."
    optParameters = [
        ["endpoint", "e", None, "Endpoint to listen on."],
    ]


def makeService(config):
    service = TapTapService(config['endpoint'])
    return service
