# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii
import codecs
from contextlib import closing
import fcntl
import time

import falcon

import bsddb3 as bsddb

from MAPI.Util import kc_session_save, kc_session_restore, GetDefaultStore
from MAPI.Struct import MAPIErrorNotFound, MAPIErrorNoAccess, MAPIErrorInvalidParameter
import kopano

from grapi.api.v1.resource import HTTPBadRequest
from grapi.api.v1.decorators import experimental as experimentalDecorator

USERID_SESSION = {}

TOKEN_SESSION = {}
LAST_PURGE_TIME = None

_marker = object()

experimental = experimentalDecorator


def _auth(req, options):
    auth_header = req.get_header('Authorization')

    if (auth_header and auth_header.startswith('Bearer ') and
            (not options or options.auth_bearer)):
        token = codecs.encode(auth_header[7:], 'ascii')
        return {
            'method': 'bearer',
            'user': req.get_header('X-Kopano-Username', ''),
            'userid': req.get_header('X-Kopano-UserEntryID', ''),
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

    # TODO remove
    elif not options or options.auth_passthrough:  # pragma: no cover
        userid = req.get_header('X-Kopano-UserEntryID')
        if userid:
            return {
                'method': 'passthrough',
                'user': req.get_header('X-Kopano-Username', ''),
                'userid': userid,
            }


def db_get(key):
    with closing(bsddb.hashopen('mapping_db', 'c')) as db:
        return codecs.decode(db.get(codecs.encode(key, 'ascii')), 'ascii')


def db_put(key, value):
    with open('mapping_db.lock', 'w') as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        with closing(bsddb.hashopen('mapping_db', 'c')) as db:
            db[codecs.encode(key, 'ascii')] = codecs.encode(value, 'ascii')


def _server(req, options):
    global LAST_PURGE_TIME
    auth = _auth(req, options)
    if not auth:
        raise falcon.HTTPForbidden('Unauthorized', None)

    if auth['method'] == 'bearer':
        token = auth['token']
        sessiondata = TOKEN_SESSION.get(token)
        if sessiondata:
            mapisession = kc_session_restore(sessiondata[0])
            server = kopano.Server(mapisession=mapisession, parse_args=False)
        else:
            server = kopano.Server(auth_user=auth['userid'], auth_pass=token,
                                   parse_args=False, oidc=True)
            sessiondata = kc_session_save(server.mapisession)
            now = time.time()
            TOKEN_SESSION[token] = (sessiondata, now)

            # expire tokens after 15 mins TODO make configurable?
            if LAST_PURGE_TIME is None or now > LAST_PURGE_TIME+10:
                for (token, (sessiondata, t)) in list(TOKEN_SESSION.items()):
                    if t < now - 15*60:
                        del TOKEN_SESSION[token]
                LAST_PURGE_TIME = now
        return server

    elif auth['method'] == 'basic':
        return kopano.Server(auth_user=auth['user'], auth_pass=auth['password'], parse_args=False)

    # TODO remove
    elif auth['method'] == 'passthrough':  # pragma: no cover
        userid = auth['userid']
        sessiondata = USERID_SESSION.get(userid)
        if sessiondata:
            mapisession = kc_session_restore(sessiondata)
            server = kopano.Server(mapisession=mapisession, parse_args=False)
        else:
            username = _username(auth['userid'])
            server = kopano.Server(auth_user=username, auth_pass='',
                                   parse_args=False, store_cache=False)
            sessiondata = kc_session_save(server.mapisession)
            USERID_SESSION[userid] = sessiondata
        return server


# TODO remove
def _username(userid):  # pragma: no cover
    global SERVER
    reconnect = False
    try:
        SERVER
    except NameError:
        reconnect = True

    if reconnect:
        SERVER = kopano.Server(parse_args=False, store_cache=False)
    return SERVER.user(userid=userid).name


def _server_store(req, userid, options):
    try:
        try:
            server = _server(req, options)
        except MAPIErrorNotFound:  # no store
            raise falcon.HTTPForbidden('Unauthorized', None)

        if userid and userid != 'delta':
            try:
                if userid.startswith('AAAAA'):
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
            store = kopano.Store(server=server, mapiobj=GetDefaultStore(server.mapisession))

        return server, store, userid

    except (kopano.LogonError, MAPIErrorNoAccess):
        raise falcon.HTTPForbidden('Unauthorized', None)


def _folder(store, folderid):
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
