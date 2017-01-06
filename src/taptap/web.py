import attr
import cattr
import json
import os
import time
import math
import datetime

from base64 import b64encode

from urllib.parse import urlparse, urlunparse

from typing import List
from attr.validators import instance_of, optional

from twisted.internet.defer import ensureDeferred
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
    async def user_GET(self, request):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        user = await User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        return json.dumps({"name": user.name}).encode('utf8')


    @app.route('/works/', methods=["GET"])
    async def works_root_GET(self, request):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        user = await User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        works = await user.load_works()

        works = [APIWork.from_work(x) for x in works]
        works.sort(key=lambda x: x.id)
        return _make_json(works)

    @app.route('/works/', methods=["POST"])
    async def works_root_POST(self, request):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        work_in = cattr.loads(json.loads(request.content.getvalue().decode('utf8')), APIWork)
        work = work_in.to_new_work(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        await work.save()

        return _make_json(APIWork.from_work(work))


    @app.route('/works/<int:id>', methods=["GET"])
    async def works_item_GET(self, request, id):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        user = await User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        work = await user.load_work(id)
        return _make_json(APIWork.from_work(work))


    @app.route('/works/<int:id>/counts', methods=["POST"])
    async def works_counts_POST(self, request, id):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        count = int(json.loads(request.content.getvalue().decode('utf8'))["count"])
        user = await User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        work = await user.load_work(id)

        work.counts.append(WordCount(at=math.floor(time.time()), count=count))
        await work.save()

        return _make_json(APIWork.from_work(work))

    @app.route('/works/<int:id>/daily', methods=["GET"])
    async def works_daily_GET(self, request, id):
        request.responseHeaders.addRawHeader("Content-Type", "application/json")

        user = await User.load(self._cookies[request.getCookie(b"TAPTAP_TOKEN")])
        work = await user.load_work(id)
        counts = {}

        for count in work.counts:
            dt = (datetime.datetime.utcfromtimestamp(count.at) -
                  datetime.timedelta(seconds=user.tzoffset))
            time = dt.strftime("%Y-%m-%d")
            ct = counts.get(time, [])
            ct.append(count.count)
            counts[time] = ct

        times, values, diffs = [], [], []

        for t, v in counts.items():
            times.append(t)
            mx = max(v)
            if values:
                diff = mx - values[-1]
            else:
                diff = mx
            diffs.append(diff)
            values.append(max(v))

        dates = {}

        for x in range(len(times)):
            dates[times[x]] = {
                "diff": diffs[x],
                "value": values[x]}

        best_day = max(diffs)
        best_days = [x for x, y in dates.items() if y["diff"] == best_day]

        if work.completed:
            start = (datetime.datetime.utcfromtimestamp(work.counts[0].at) -
                     datetime.timedelta(seconds=user.tzoffset))
            end = (datetime.datetime.utcfromtimestamp(work.counts[-1].at) -
                   datetime.timedelta(seconds=user.tzoffset))
            days = (end - start).days + 1
        else:
            start = (datetime.datetime.utcfromtimestamp(work.counts[0].at) -
                     datetime.timedelta(seconds=user.tzoffset))
            end = (datetime.datetime.now() -
                   datetime.timedelta(seconds=user.tzoffset))
            days = (end - start).days + 1

        until_target = work.word_target - values[-1]
        words_per_day = values[-1] // days
        words_per_writing_day = values[-1] // len(values)
        writing_days_until_target = math.ceil(until_target / words_per_writing_day)

        finished_at_pace = ((datetime.datetime.now() - datetime.timedelta(seconds=user.tzoffset)) + datetime.timedelta(days=math.ceil(until_target / words_per_day))).strftime("%Y-%m-%d")

        if not work.completed:
            dat = (datetime.datetime.now() -
                   datetime.timedelta(seconds=user.tzoffset)).strftime("%Y-%m-%d")

            if dat not in times:
                times.append(dat)
                values.append(values[-1])
                diffs.append(0)

        return json.dumps({
            "x": times,
            "y": values,
            "diffs": diffs,
            "stats": {
                "best_day": "{} ({} words)".format(",".join(best_days), best_day),
                "until_target": until_target,
                "words_per_day": words_per_day,
                "words_per_writing_day": words_per_writing_day,
                "writing_days_until_target": writing_days_until_target,
                "finished_at_pace": finished_at_pace
            }
        },separators=(',',':')).encode('utf8')


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
    async def go(self, request):

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


        resp = await get_request_token(self.consumer_key, self.consumer_secret,
                                       target_url)

        self.tokens[resp["oauth_token"][0]] = resp["oauth_token_secret"][0]
        to_url = "https://api.twitter.com/oauth/authenticate?oauth_token=" + resp["oauth_token"][0]
        request.redirect(to_url.encode('ascii'))
        return b''

    @app.route("/done")
    async def done(self, request):

        token = request.args[b"oauth_token"][0].decode('utf8')
        verifier = request.args[b"oauth_verifier"][0].decode('utf8')
        secret = self.tokens.pop(token, None)

        if not secret:
            request.redirect("/login/go")
            return

        resp = await get_access_token(self.consumer_key, self.consumer_secret,
                                      token, secret, verifier)

        token = resp["oauth_token"][0]
        secret = resp["oauth_token_secret"][0]

        details = await get_user_details(
            self.consumer_key, self.consumer_secret, token, secret)

        u = User(id=details["id"],
                 name=details["name"],
                 tzoffset=details["utc_offset"])
        await u.save()

        if request.getHost().port not in [80, 443]:
            port = ":" + str(request.getHost().port)

        key = _make_cookie_key()

        await add_cookie(key, u.id, 25200)
        cookies = await get_cookies()
        self._cookies.clear()
        self._cookies.update(cookies)

        request.addCookie("TAPTAP_TOKEN", key, path="/",
                          max_age=25200, httpOnly=True)

        request.redirect("/")
        return b''


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

        d = ensureDeferred(get_cookies())

        @d.addCallback
        def _(cookies):
            self._cookies.clear()
            self._cookies.update(cookies)

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
