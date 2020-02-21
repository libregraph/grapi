# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii
import codecs
from contextlib import closing
import fcntl
import time
import logging
import os

from threading import Thread, Event, Lock
from collections import namedtuple

import falcon

import bsddb3 as bsddb

try:
    from prometheus_client import Counter, Gauge
    PROMETHEUS = True
except ImportError:
    PROMETHEUS = False

from MAPI.Util import GetDefaultStore
from MAPI.Struct import MAPIErrorNotFound, MAPIErrorNoAccess, MAPIErrorInvalidParameter, MAPIErrorUnconfigured
import kopano

from grapi.api.v1.resource import HTTPBadRequest
from grapi.api.v1.decorators import experimental as experimentalDecorator

PERSISTENCY_PATH = os.getenv('GRAPI_PERSISTENCY_PATH', '')

experimental = experimentalDecorator

HTTPNotFound = falcon.HTTPNotFound

# threadLock is a global lock which can be used to protect the global
# states in this file.
threadLock = Lock()

# DANGLE_INDEX is incremented whenever an active session gets replaced
# and the incremented value is appended to the key of the session data in
# TOKEN_SESSION to allow it to be cleaned up later.
DANGLE_INDEX = 0

# TOKEN_SESSIONS hold the cached session data from token authentications.
TOKEN_SESSION = {}
# TOKEN_SESSION_CACHE_TIME defines the time how long stale token cached session
# data should stay in the cache before it is purged.
TOKEN_SESSION_CACHE_TIME = 240  # TODO(longsleep): Add to configuration.
# TOKEN_SESSION_PURGE_INTERVAL is the interval in seconds how often the sessions
# should be checked if something needs to be purged.
TOKEN_SESSION_PURGE_INTERVAL = 30
# TOKEN_SESSION_PURGE_TIME is the time when the next token session data cache
# purge should happen.
TOKEN_SESSION_PURGE_TIME = time.monotonic() + TOKEN_SESSION_PURGE_INTERVAL
# PASSTHROUGH_SESSION hold the cached session data from pass through auths.
PASSTHROUGH_SESSION = {}

# Record is a named tuple binding subscription and conection information
# per user. Named tuple is used for easy painless access to its members.
Record = namedtuple('Record', ['server', 'store'])

_marker = object()

# metrics
if PROMETHEUS:
    SESSION_CREATE_COUNT = Counter('kopano_mfr_kopano_total_created_sessions', 'Total number of created sessions')
    SESSION_RESUME_COUNT = Counter('kopano_mfr_kopano_total_resumed_sessions', 'Total number of resumed sessions')
    SESSION_EXPIRED_COUNT = Counter('kopano_mfr_kopano_total_expired_sessions', 'Total number of expired sessions')
    TOKEN_SESSION_ACTIVE = Gauge('kopano_mfr_kopano_active_token_sessions', 'Number of token sessions in sessions cache')
    PASSTHROUGH_SESSIONS_ACTIVE = Gauge('kopano_mfr_kopano_active_passthrough_sessions', 'Number of pass through sessions in sessions cache')
    DANGLING_COUNT = Counter('kopano_mfr_kopano_total_broken_sessions', 'Total number of broken sessions')


try:
    import prctl

    def set_thread_name(name): prctl.set_name(name)
except ImportError:  # pragma: no cover
    def set_thread_name(name): pass


def _auth(req, options):
    auth_header = req.get_header('Authorization')

    if (auth_header and auth_header.startswith('Bearer ') and
            (not options or options.auth_bearer)):
        token = codecs.encode(auth_header[7:], 'ascii')
        return {
            'method': 'bearer',
            'user': req.get_header('X-Kopano-Username', ''),  # injected by kapi
            'userid': req.get_header('X-Kopano-UserEntryID', ''),  # injected by kapi
            'token': token,
        }

    elif (auth_header and auth_header.startswith('Basic ') and
            (not options or options.auth_basic)):
        user, password = codecs.decode(codecs.encode(auth_header[6:], 'ascii'),
                                       'base64').split(b':')
        return {
            'method': 'basic',
            'user': user,
            'password': password,
        }

    elif not options or options.auth_passthrough:
        userid = req.get_header('X-Kopano-UserEntryID')  # injected by proxy
        if userid:
            return {
                'method': 'passthrough',
                'user': req.get_header('X-Kopano-Username', ''),
                'userid': userid,
            }


def db_get(key):
    with closing(bsddb.hashopen(os.path.join(PERSISTENCY_PATH, 'mapping_db'), 'c')) as db:
        return codecs.decode(db.get(codecs.encode(key, 'ascii')), 'ascii')


def db_put(key, value):
    with open(os.path.join(PERSISTENCY_PATH, 'mapping_db.lock'), 'w') as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        with closing(bsddb.hashopen(os.path.join(PERSISTENCY_PATH, 'mapping_db'), 'c')) as db:
            db[codecs.encode(key, 'ascii')] = codecs.encode(value, 'ascii')


def _server(req, options, forceReconnect=False):
    global TOKEN_SESSION
    global TOKEN_SESSION_PURGE_TIME
    global PASSTHROUGH_SESSION
    global DANGLE_INDEX

    auth = _auth(req, options)
    if not auth:
        raise falcon.HTTPForbidden('Unauthorized', None)

    now = time.monotonic()

    if auth['method'] == 'bearer':
        token = auth['token']
        userid = req.context.userid = auth['userid']
        cacheid = token  # NOTE(longsleep): We cache per user even if that means that from time to time, the connection
        # breaks because the token has expired.
        with threadLock:
            sessiondata = TOKEN_SESSION.get(cacheid)
        if sessiondata:
            record = sessiondata[0]
            if not forceReconnect:
                server = record.server
                try:
                    server.user(userid=userid)
                except Exception:
                    logging.exception('network or session (%s) error while reusing bearer token user %s session, reconnect automatically', id(server), userid)
                    forceReconnect = True
            if forceReconnect:
                with threadLock:
                    oldSessiondata = TOKEN_SESSION.pop(cacheid)
                    DANGLE_INDEX += 1
                    TOKEN_SESSION['{}_dangle_{}'.format(cacheid, DANGLE_INDEX)] = oldSessiondata
                sessiondata = None
                if options and options.with_metrics:
                    DANGLING_COUNT.inc()
            else:
                sessiondata[1] = now  # NOTE(longsleep): Mutate is threadsafe in CPython - we do not care who wins here.
                if options and options.with_metrics:
                    SESSION_RESUME_COUNT.inc()

        if not sessiondata:
            logging.debug('creating session for bearer token user %s', userid)
            server = kopano.Server(auth_user=userid, auth_pass=token,
                                   parse_args=False, store_cache=False, oidc=True, config={})
            store = kopano.Store(server=server, mapiobj=GetDefaultStore(server.mapisession))
            record = Record(server=server, store=store)
            sessiondata = [record, now]
            with threadLock:
                if cacheid:
                    TOKEN_SESSION[cacheid] = sessiondata
                else:
                    DANGLE_INDEX += 1
                    TOKEN_SESSION['_dangle_{}'.format(DANGLE_INDEX)] = sessiondata
            if options and options.with_metrics:
                SESSION_CREATE_COUNT.inc()
                TOKEN_SESSION_ACTIVE.inc()

        return record

    elif auth['method'] == 'basic':
        logging.debug('creating session for basic auth user %s', auth['user'])
        server = kopano.Server(auth_user=auth['user'], auth_pass=auth['password'],
                               parse_args=False, store_cache=False, config={})
        store = kopano.Store(server=server, mapiobj=GetDefaultStore(server.mapisession))
        if options and options.with_metrics:
            SESSION_CREATE_COUNT.inc()

        return Record(server=server, store=store)

    # TODO(longsleep): Add expiration for PASSTHROUGH_SESSION contents.
    elif auth['method'] == 'passthrough':
        userid = req.context.userid = auth['userid']
        cacheid = userid  # NOTE(longsleep): We cache per user id.
        with threadLock:
            sessiondata = PASSTHROUGH_SESSION.get(cacheid)
        if sessiondata:
            record = sessiondata[0]
            if not forceReconnect:
                server = record.server
                try:
                    server.user(userid=userid)
                except Exception:
                    logging.exception('network or session (%s) error while reusing passthrough user session user %s, reconnect automatically', id(server), userid)
                    forceReconnect = True
            if forceReconnect:
                with threadLock:
                    oldSessiondata = PASSTHROUGH_SESSION.pop(cacheid)
                    DANGLE_INDEX += 1
                    PASSTHROUGH_SESSION['_dangle_{}'.format(DANGLE_INDEX)] = oldSessiondata
                sessiondata = None
                if options and options.with_metrics:
                    DANGLING_COUNT.inc()
            else:
                sessiondata[1] = time.monotonic()  # NOTE(longsleep): Array mutate is threadsafe in CPython - we do not care who wins here.
                if options and options.with_metrics:
                    SESSION_RESUME_COUNT.inc()

        if not sessiondata:
            logging.debug('creating session for passthrough user %s', userid)
            username = _username(userid)
            server = kopano.Server(auth_user=username, auth_pass='',
                                   parse_args=False, store_cache=False, config={})
            store = kopano.Store(server=server, mapiobj=GetDefaultStore(server.mapisession))
            record = Record(server=server, store=store)
            sessiondata = [record, now]
            with threadLock:
                PASSTHROUGH_SESSION[cacheid] = sessiondata
            if options and options.with_metrics:
                SESSION_CREATE_COUNT.inc()
                PASSTHROUGH_SESSIONS_ACTIVE.inc()

        return record


class SessionPurger(Thread):
    def __init__(self, options):
        Thread.__init__(self, name='kopano_session_purger')
        set_thread_name(self.name)
        self.options = options
        self.daemon = True
        self.exit = Event()

    def run(self):
        quick = False
        timeout = 60
        while not self.exit.wait(timeout=timeout):
            with threadLock:
                now = time.monotonic()
                deadline = now - TOKEN_SESSION_CACHE_TIME
                count = 0
                quick = False
                for cacheid, (record, ts) in list(TOKEN_SESSION.items()):
                    if ts < deadline:
                        count += 1
                        logging.debug('purging cached token session for token (%s)', id(record.server))
                        del TOKEN_SESSION[cacheid]
                        if self.options and self.options.with_metrics:
                            SESSION_EXPIRED_COUNT.inc()
                            TOKEN_SESSION_ACTIVE.dec()
                        if count > 100:
                            # If lots of stuff got purged, stop here and and come back quickly.
                            quick = True
                            break
            timeout = 5 if quick else 60


# TODO remove
def _username(userid):  # pragma: no cover
    global SERVER
    reconnect = False
    try:
        SERVER
    except NameError:
        reconnect = True

    if reconnect:
        SERVER = kopano.Server(parse_args=False, store_cache=False, config={})
    return SERVER.user(userid=userid).name


def _server_store(req, userid, options, forceReconnect=False):
    try:
        try:
            record = _server(req, options, forceReconnect=forceReconnect)
        except MAPIErrorNotFound:  # no store
            logging.info('no store for user %s for request %s', req.context.userid, req.path, exc_info=True)
            raise falcon.HTTPForbidden('Unauthorized', None)

        server = record.server
        store = record.store

        try:
            if userid and userid != 'delta':
                try:
                    if userid.startswith('AAAAA'):  # FIXME(longsleep): Fix this poor mans check.
                        try:
                            user = server.user(userid=userid)
                        except (kopano.NotFoundError, MAPIErrorInvalidParameter):
                            user = server.user(name=userid)
                            userid = user.userid
                    else:
                        try:
                            user = server.user(name=userid)
                            userid = user.userid
                        except kopano.NotFoundError as ex:
                            # FIXME(longsleep): This just blindly retries lookup even
                            # if it does not make sense.
                            try:
                                user = server.user(userid=userid)
                            except MAPIErrorInvalidParameter:
                                raise ex
                except (kopano.NotFoundError, kopano.ArgumentError, MAPIErrorNotFound):
                    raise falcon.HTTPNotFound(description='No such user: %s' % userid)

                store = user.store
            else:
                # Ensure that the store can access its user.
                store.user
        except MAPIErrorUnconfigured:
            if forceReconnect:
                raise
            logging.exception('network or session (%s) error while getting store for user %s, forcing reconnect', id(server), userid)
            return _server_store(req, userid, options, forceReconnect=True)

        return server, store, userid

    except (kopano.LogonError, kopano.NotFoundError, MAPIErrorNoAccess, MAPIErrorUnconfigured):
        logging.info('logon failed for user %s for request %s', req.context.userid, req.path, exc_info=True)
        raise falcon.HTTPForbidden('Unauthorized', None)


def _folder(store, folderid):
    if store is None:
        raise falcon.HTTPNotFound(description='No store')

    name = folderid.lower()
    if name == 'inbox':
        return store.inbox
    elif name == 'drafts':
        return store.drafts
    elif name == 'calendar':
        return store.calendar
    elif name == 'contacts':
        return store.contacts
    elif name == 'deleteditems':
        return store.wastebasket
    elif name == 'junkemail':
        return store.junk
    elif name == 'sentitems':
        return store.sentmail
    else:
        try:
            return store.folder(entryid=folderid)
        except binascii.Error:
            raise HTTPBadRequest('Folder is is malformed')
        except kopano.errors.ArgumentError:
            raise falcon.HTTPNotFound(description=None)


def _item(parent, entryid):
    try:
        return parent.item(entryid)
    except kopano.NotFoundError:
        raise falcon.HTTPNotFound(description=None)
    except kopano.ArgumentError:
        raise HTTPBadRequest('Id is malformed')


def _get_group_by_id(server, groupid, default=_marker):
    for group in server.groups():  # TODO server.group(groupid/entryid=..)
        if group.groupid == groupid:
            return group
    if default is _marker:
        raise falcon.HTTPNotFound(description='No such group: %s' % groupid)
    return default


def _handle_exception(ex, req):
    try:
        raise ex
    except MAPIErrorNoAccess:
        logging.debug('access forbidden for user %s for request %s', req.context.userid, req.path, exc_info=True)
        raise falcon.HTTPForbidden('No access', None)
