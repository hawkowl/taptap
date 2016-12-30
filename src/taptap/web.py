import attr
import cattr
import json
import os

from base64 import b64encode

from urllib.parse import urlparse, urlunparse

from typing import List
from attr.validators import instance_of

from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.web.server import NOT_DONE_YET
from twisted.python.filepath import FilePath

from klein import Klein

from .work import load_works, dump_works, WordCount
from .users import get_request_token, get_access_token, get_user_details, User


@attr.s
class APIWork(object):
    id = attr.ib(validator=instance_of(int))
    name = attr.ib(validator=instance_of(str))
    counts = attr.ib(validator=instance_of(List[WordCount]))
    word_count = attr.ib(validator=instance_of(int))
    word_target = attr.ib(validator=instance_of(int))
    completed = attr.ib(validator=instance_of(bool), default=False)

    @classmethod
    def from_work(cls, work):

        word_count = sorted(work.counts, key=lambda x: x.at)[-1].count

        return cls(id=work.id,
                   name=work.name,
                   counts=work.counts,
                   word_count=word_count,
                   word_target=work.word_target,
                   completed=work.completed)


def _make_cookie_key():
    return b64encode(os.urandom(32))


def _make_json(item):
    return json.dumps(cattr.dumps(item), separators=(',',':')).encode('utf8')

class APIResource(object):

    app = Klein()

    def __init__(self, cookie_store):
        self._cookies = cookie_store

    @app.route('/user')
    def user(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        d = User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])

        @d.addCallback
        def _(user):
            return json.dumps({"name": user.name}).encode('utf8')

        return d


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


class LoginResource(object):

    app = Klein()
    tokens = {}

    def __init__(self, cookie_store):
        secrets = json.loads(FilePath("secrets.json").getContent().decode('utf8'))
        self.consumer_key, self.consumer_secret = secrets["key"], secrets["secret"]
        self._cookies = cookie_store

    @app.route("/go")
    def go(self, request):

        if request.getHost().port not in [80, 443]:
            port = ":" + str(request.getHost().port)

        if request.getHost().port == 443:
            proto = "https"
        else:
            proto = "http"

        target_url = urlunparse([
            proto, request.getRequestHostname().decode('ascii') + port,
            "/login/done", '', '', ''])

        d = get_request_token(self.consumer_key, self.consumer_secret,
                              target_url)

        @d.addCallback
        def _(resp):
            self.tokens[resp["oauth_token"][0]] = resp["oauth_token_secret"][0]
            to_url = "https://api.twitter.com/oauth/authenticate?oauth_token=" + resp["oauth_token"][0]
            request.redirect(to_url.encode('ascii'))

        return d

    @app.route("/done")
    def done(self, request):

        token = request.args[b"oauth_token"][0].decode('utf8')
        verifier = request.args[b"oauth_verifier"][0].decode('utf8')

        secret = self.tokens.pop(token, None)

        if not secret:
            request.redirect("/login/go")
            return

        d = get_access_token(self.consumer_key, self.consumer_secret,
                             token, secret, verifier)


        @d.addCallback
        def _(resp):

            token = resp["oauth_token"][0]
            secret = resp["oauth_token_secret"][0]

            return get_user_details(self.consumer_key, self.consumer_secret,
                                    token, secret)

        @d.addCallback
        def _save(resp):

            u = User(id=resp["id"],
                     name=resp["name"])
            return u.save()

        @d.addCallback
        def _done(resp):

            if request.getHost().port not in [80, 443]:
                port = ":" + str(request.getHost().port)

            key = _make_cookie_key()
            self._cookies[key] = resp.id
            request.addCookie("TAPTAP_TOKEN", key,
                              path="/",
                              max_age=25200, httpOnly=True)

            request.redirect("/")
            request.write(b'')
            request.finish()

        return d


class LoginRedirectResource(Resource):

    isLeaf = True

    def render_GET(self, request):

        return b'<meta http-equiv="refresh" content="0; url=/login/go" />'


class CoreResource(File):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._cookies = {}
        self._api = APIResource(self._cookies).app.resource()
        self._login = LoginResource(self._cookies).app.resource()

    def getChild(self, path, request):

        # ~auth check~
        if request.path[:7] != b"/login/" and request.path[:5] != b"/css/" and request.path[:4] != b"/js/":
            cookie = request.getCookie(b"TAPTAP_TOKEN")

            if not cookie or cookie not in self._cookies:
                return LoginRedirectResource()

        if request.path[:5] == b"/api/":
            return self._api

        if request.path[:7] == b"/login/":
            return self._login

        if request.path[:6] == b"/sass/":
            return None

        return super(CoreResource, self).getChild(path, request)
