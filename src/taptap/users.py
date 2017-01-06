import os
import treq
import time
import hashlib
import hmac
import attr

from attr.validators import instance_of

from base64 import b64encode

from urllib.parse import urlencode, quote as _quote, unquote, parse_qs

from twisted.internet.defer import ensureDeferred

from ._db import get_engine, user_table, cookie_table, work_table

quote = lambda x: _quote(x, safe='')


@attr.s
class User(object):
    id = attr.ib(validator=instance_of(int))
    name = attr.ib(validator=instance_of(str))
    tzoffset = attr.ib(validator=instance_of(int))

    @classmethod
    async def load(cls, id, engine=None):
        if not engine:
            engine = get_engine()

        e = await engine.connect()

        f = await e.execute(user_table.select().
                            where(user_table.c.id == id))
        result = await f.fetchone()

        await e.close()
        return cls(
            id=result[user_table.c.id],
            name=result[user_table.c.name],
            tzoffset=result[user_table.c.tzoffset])

    async def save(self, engine=None):
        if not engine:
            engine = get_engine()

        e = await engine.connect()

        try:
            await e.execute(user_table.insert().values(
                id=self.id,
                name=self.name,
                tzoffset=self.tzoffset))
        except Exception as exc:
            await e.execute(user_table.update().
                            where(user_table.c.id == self.id).
                            values(name=self.name,
                                   tzoffset=self.tzoffset))

        await e.close()
        return self

    async def load_work(self, id, engine=None):
        from .work import Work

        if not engine:
            engine = get_engine()

        e = await engine.connect()

        r = await e.execute(work_table.select().where(
            work_table.c.user == self.id).where(work_table.c.id == id))

        result = await r.fetchone()
        loaded = await Work._load_from_data(result, engine)

        await e.close()
        return loaded

    async def load_works(self, engine=None):

        from .work import Work

        if not engine:
            engine = get_engine()

        e = await engine.connect()

        r = await e.execute(work_table.select().where(work_table.c.user == self.id))

        results = await r.fetchall()

        done_results = []

        for result in results:
            done_results.append(await Work._load_from_data(result, e))

        await e.close()

        return done_results


async def add_cookie(cookie, id, time_to_expiry, engine=None):

    if not engine:
        engine = get_engine()

    e = await engine.connect()

    f = await e.execute(cookie_table.insert().values(
        cookie=cookie.decode('utf8'),
        id=id,
        expires=time.time() + time_to_expiry
    ))

    await e.close()

    return f


async def get_cookies(engine=None):

    if not engine:
        engine = get_engine()

    e = await engine.connect()

    await e.execute(cookie_table.delete().where(
        cookie_table.c.expires < time.time()))

    f = await e.execute(cookie_table.select())

    cookies = await f.fetchall()
    cookiedict = {}

    for cookie in cookies:
        cookiedict[cookie.cookie.encode('utf8')] = cookie.id

    await e.close()
    return cookiedict


def get_nonce():
    return b64encode(os.urandom(16)).decode('ascii').replace('=', '').replace('+', '').replace('/', '')


def get_timestamp():
    return "{:0.0f}".format(time.time())


def make_signature(method, url, content, key):

    signature_content = method + "&" + quote(url) + "&" + quote("&".join([
        "=".join([quote(y) for y in x]) for x in content
    ]))

    h = hmac.new(key.encode('ascii'), digestmod=hashlib.sha1)
    h.update(msg=signature_content.encode('ascii'))

    return quote(b64encode(h.digest()).decode('ascii'))


def get_request_token(consumer_key, consumer_secret, callback_url,
                      _url="https://api.twitter.com/oauth/request_token"):

    nonce = get_nonce()
    timestamp = get_timestamp()

    signature_details = [
        ("oauth_callback", callback_url),
        ("oauth_consumer_key", consumer_key),
        ("oauth_nonce", nonce),
        ("oauth_signature_method", "HMAC-SHA1"),
        ("oauth_timestamp", timestamp),
        ("oauth_version", "1.0")
    ]

    signing_key = quote(consumer_secret) + "&"
    signature = make_signature("POST", _url, signature_details, signing_key)

    headers = {
        'Authorization': (
            'OAuth oauth_callback="{}", oauth_consumer_key="{}", '
            'oauth_nonce="{}", oauth_signature="{}", '
            'oauth_signature_method="HMAC-SHA1", oauth_timestamp="{}", '
            'oauth_version="1.0"').format(quote(callback_url), consumer_key,
                                          nonce, signature, timestamp)}

    d = treq.post(_url, headers=headers, body=b'')
    d.addCallback(treq.text_content, encoding='utf8')
    d.addCallback(parse_qs)
    return d


def get_access_token(consumer_key, consumer_secret, token, token_secret,
                     verifier,
                     _url="https://api.twitter.com/oauth/access_token"):

    nonce = get_nonce()
    timestamp = get_timestamp()

    signature_details = [
        ("oauth_consumer_key", consumer_key),
        ("oauth_nonce", nonce),
        ("oauth_signature_method", "HMAC-SHA1"),
        ("oauth_timestamp", timestamp),
        ("oauth_token", token),
        ("oauth_verifier", verifier),
        ("oauth_version", "1.0")
    ]

    signing_key = quote(consumer_secret) + "&" + quote(token_secret)
    signature = make_signature("POST", _url, signature_details, signing_key)

    headers = {
        'Authorization': (
            'OAuth oauth_consumer_key="{}", oauth_nonce="{}", '
            'oauth_signature="{}", oauth_signature_method="HMAC-SHA1", '
            'oauth_timestamp="{}", oauth_token={}, '
            'oauth_version="1.0"').format(consumer_key, nonce, signature,
                                          timestamp, quote(token))}

    d = treq.post(_url, headers=headers, params={'oauth_verifier': verifier})
    d.addCallback(treq.text_content, encoding='utf8')
    d.addCallback(parse_qs)
    return d

def get_user_details(consumer_key, consumer_secret, token, token_secret,
                     _url="https://api.twitter.com/1.1/account/verify_credentials.json"):

    nonce = get_nonce()
    timestamp = get_timestamp()

    signature_details = [
        ("oauth_consumer_key", consumer_key),
        ("oauth_nonce", nonce),
        ("oauth_signature_method", "HMAC-SHA1"),
        ("oauth_timestamp", timestamp),
        ("oauth_token", token),
        ("oauth_version", "1.0")
    ]

    signing_key = quote(consumer_secret) + "&" + quote(token_secret)
    signature = make_signature("GET", _url, signature_details, signing_key)

    headers = {
        'Authorization': (
            'OAuth oauth_consumer_key="{}", oauth_nonce="{}", '
            'oauth_signature="{}", oauth_signature_method="HMAC-SHA1", '
            'oauth_timestamp="{}", oauth_token="{}", '
            'oauth_version="1.0"').format(consumer_key, nonce, signature,
                                          timestamp, quote(token))}

    d = treq.get(_url, headers=headers)
    d.addCallback(treq.json_content)
    return d
