import attr
import cattr
import json
import os
import time
import math

from base64 import b64encode

from urllib.parse import urlparse, urlunparse

from typing import List
from attr.validators import instance_of, optional

from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.web.server import NOT_DONE_YET
from twisted.python.filepath import FilePath

from klein import Klein

from .work import load_works, dump_works, WordCount, Work
from .users import get_request_token, get_access_token, get_user_details, User, add_cookie, get_cookies


@attr.s
class APIWork(object):
    name = attr.ib(validator=instance_of(str))
    word_target = attr.ib(validator=instance_of(int))
    completed = attr.ib(validator=instance_of(bool), default=False)

    id = attr.ib(validator=optional(instance_of(int)), default=None)
    counts = attr.ib(validator=optional(instance_of(List[WordCount])), default=None)
    word_count = attr.ib(validator=optional(instance_of(int)), default=None)

    @classmethod
    def from_work(cls, work):

        word_count = sorted(work.counts, key=lambda x: x.at)[-1].count

        return cls(id=work.id,
                   name=work.name,
                   counts=work.counts,
                   word_count=word_count,
                   word_target=work.word_target,
                   completed=work.completed)

    def to_new_work(self, user):

        counts = [WordCount(at=math.floor(time.time()), count=0)]

        return Work(
            name=self.name,
            counts=counts,
            word_target=self.word_target,
            completed=self.completed,
            user=user)


def _make_cookie_key():
    return b64encode(os.urandom(32))


def _make_json(item):
    return json.dumps(cattr.dumps(item), separators=(',',':')).encode('utf8')

class APIResource(object):

    app = Klein()

    def __init__(self, cookie_store):
        self._cookies = cookie_store

    @app.route('/user', methods=['GET'])
    def user_GET(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        d = User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])

        @d.addCallback
        def _(user):
            return json.dumps({"name": user.name}).encode('utf8')

        return d


    @app.route('/works/', methods=["GET"])
    def works_root_GET(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        d = User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])

        d.addCallback(lambda user: user.load_works())

        @d.addCallback
        def _(works):

            works = [APIWork.from_work(x) for x in works]
            works.sort(key=lambda x: x.id)
            return _make_json(works)

        return d

    @app.route('/works/', methods=["POST"])
    def works_root_POST(self, request):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        work_in = cattr.loads(json.loads(request.content.getvalue().decode('utf8')), APIWork)

        work = work_in.to_new_work(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        d = work.save()

        d.addCallback(lambda _: _make_json(APIWork.from_work(_)))

        return d


    @app.route('/works/<int:id>', methods=["GET"])
    def works_item_GET(self, request, id):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        d = User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        d.addCallback(lambda user: user.load_work(id))
        d.addCallback(lambda _: _make_json(APIWork.from_work(_)))
        return d


    @app.route('/works/<int:id>/counts', methods=["POST"])
    def works_counts_POST(self, request, id):

        request.responseHeaders.addRawHeader("Content-Type", "application/json")
        count = int(json.loads(request.content.getvalue().decode('utf8'))["count"])

        d = User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        d.addCallback(lambda user: user.load_work(id))

        @d.addCallback
        def _got_work(work):
            work.counts.append(WordCount(at=math.floor(time.time()), count=count))
            return work.save()

        d.addCallback(lambda _: _make_json(APIWork.from_work(_)))
        return d



class LoginResource(object):

    app = Klein()
    tokens = {}

    def __init__(self, cookie_store):
        if FilePath("secrets.json").exists():

            secrets = json.loads(FilePath("secrets.json").getContent().decode('utf8'))
            self.consumer_key, self.consumer_secret = secrets["key"], secrets["secret"]
        else:
            self.consumer_key = os.environ["TWITTER_KEY"]
            self.consumer_secret = os.environ["TWITTER_SECRET"]

        self._cookies = cookie_store

    @app.route("/go")
    def go(self, request):

        if not os.environ.get("WEB_PATH"):

            if request.getHost().port not in [80, 443]:
                port = ":" + str(request.getHost().port)

            if request.getHost().port == 443:
                proto = "https"
            else:
                proto = "http"

            web_path = request.getRequestHostname().decode('ascii') + port

            target_url = urlunparse([
                proto, web_path,
                "/login/done", '', '', ''])
        else:
            web_path = os.environ["WEB_PATH"]
            target_url = web_path + "/login/done"


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

            d = add_cookie(key, resp.id, 25200)
            d.addCallback(lambda _: get_cookies())
            d.addCallback(_cookie_done, key)

            return d

        def _cookie_done(cookies, key):
            self._cookies.clear()
            self._cookies.update(cookies)

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

        d = get_cookies()

        @d.addCallback
        def _(cookies):
            self._cookies.clear()
            self._cookies.update(cookies)

    def getChild(self, path, request):

        # ~auth check~
        if request.path[:7] != b"/login/" and request.path[:5] != b"/css/" and request.path[:4] != b"/js/":
            cookie = request.getCookie(b"TAPTAP_TOKEN")

            print(cookie, self._cookies)

            if not cookie or cookie not in self._cookies:
                return LoginRedirectResource()

        if request.path[:5] == b"/api/":
            return self._api

        if request.path[:7] == b"/login/":
            return self._login

        if request.path[:6] == b"/sass/":
            return None

        return super(CoreResource, self).getChild(path, request)
