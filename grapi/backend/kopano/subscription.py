# SPDX-License-Identifier: AGPL-3.0-or-later
import codecs
import falcon
import kopano
import datetime
import dateutil.parser
import requests
import logging
import uuid

from queue import Queue
from threading import Thread, Event, Lock
from collections import namedtuple

from . import utils

try:
    import ujson as json
except ImportError:  # pragma: no cover
    import json
try:
    import prctl

    def set_thread_name(name): prctl.set_name(name)
except ImportError:  # pragma: no cover
    def set_thread_name(name): pass

try:
    from prometheus_client import Counter, Gauge
    PROMETHEUS = True
except ImportError:  # pragma: no cover
    PROMETHEUS = False

from MAPI.Struct import (
    MAPIErrorNetworkError, MAPIErrorEndOfSession, MAPIErrorNoSupport
)

INDENT = True
try:
    json.dumps({}, indent=True)  # ujson 1.33 doesn't support 'indent'
except TypeError:  # pragma: no cover
    INDENT = False

# TODO don't block on sending updates
# TODO async subscription validation
# TODO restarting app/server?
# TODO list subscription scalability
# TODO use mulitprocessing

# GRAPI uses Base64, tell kopano module about it.
kopano.set_bin_encoding('base64')

logging.getLogger("requests").setLevel(logging.WARNING)

# threadLock is a global lock which can be used to protect the global
# states in this file.
threadLock = Lock()

# RECORDS hold the named tuple Record values for users which have active
# subscriptions.
RECORDS = {}
# RECORD_COUNT is incremented whenever a active subscription gets replaced
# and the incremented value is appended to the key of the record in RECRODS
# to allow it to be cleaned up later.
RECORD_COUNT = 0
# Record is a named tuple binding subscription and conection information
# per user. Named tuple is used for easy painless access to its members.
Record = namedtuple('Record', ['server', 'user', 'store', 'subscriptions'])

PATTERN_MESSAGES = (falcon.routing.compile_uri_template('/me/mailFolders/{folderid}/messages')[1], 'Message')
PATTERN_CONTACTS = (falcon.routing.compile_uri_template('/me/contactFolders/{folderid}/contacts')[1], 'Contact')
PATTERN_EVENTS = (falcon.routing.compile_uri_template('/me/calendars/{folderid}/events')[1], 'Event')

if PROMETHEUS:
    SUBSCR_COUNT = Counter('kopano_mfr_total_subscriptions', 'Total number of subscriptions')
    SUBSCR_EXPIRED = Counter('kopano_mfr_total_expired_subscriptions', 'Total number of subscriptions which expired')
    SUBSCR_ACTIVE = Gauge('kopano_mfr_active_subscriptions', 'Number of active subscriptions', multiprocess_mode='livesum')
    POST_COUNT = Counter('kopano_mfr_total_webhook_posts', 'Total number of webhook posts')
    DANGLING_COUNT = Counter('kopano_mfr_total_broken_subscription_conns', 'Total number of broken subscription connections')


def _server(auth_user, auth_pass, oidc=False, reconnect=False):
    server = kopano.Server(auth_user=auth_user, auth_pass=auth_pass,
                           notifications=True, parse_args=False, oidc=oidc)
    logging.info('server connection established, server:%s, auth_user:%s', server, server.auth_user)

    return server


def _record(req, options):
    """
    Return the record matching the provided request. If no record is found, a
    new one is created.
    """
    global RECORD_COUNT
    global RECORDS

    auth = utils._auth(req, options)

    username = None
    auth_username = None
    auth_password = None
    oidc = False
    if auth['method'] == 'bearer':
        username = auth['user']
        auth_username = auth['userid']
        auth_password = auth['token']
        oidc = True
    elif auth['method'] == 'basic':
        auth_username = codecs.decode(auth['user'], 'utf8')
        auth_password = auth['password']
    elif auth['method'] == 'passthrough':  # pragma: no cover
        auth_username = utils._username(auth['userid'])
        auth_password = ''

    if username is None:
        username = auth_username

    with threadLock:
        record = RECORDS.get(auth_username)
    if record is not None:
        try:
            user = record.server.user(username)
            return record
        except (MAPIErrorNetworkError, MAPIErrorEndOfSession):  # server restart: try to reconnect TODO check kc_session_restore (incl. notifs!)
            logging.exception('network or session error while getting user from server, reconnect automatically')
            with threadLock:
                oldRecord = RECORDS.pop(auth_username)
                RECORD_COUNT += 1
                RECORDS['{}_dangle_{}'.format(auth_username, RECORD_COUNT)] = oldRecord
            if options and options.with_metrics:
                DANGLING_COUNT.inc()

    server = _server(auth_username, auth_password, oidc=oidc)
    user = server.user(username)
    store = user.store

    record = Record(server=server, user=user, store=store, subscriptions={})
    with threadLock:
        RECORDS.update({auth_username: record})

        return RECORDS.get(auth_username)


class Processor(Thread):
    def __init__(self, options):
        Thread.__init__(self, name='processor')
        set_thread_name(self.name)
        self.options = options
        self.daemon = True

    def _notification(self, subscription, event_type, obj):
        return {
            'subscriptionId': subscription['id'],
            'clientState': subscription['clientState'],
            'changeType': event_type,
            'resource': subscription['resource'],
            'resourceData': {
                '@data.type': '#Microsoft.Graph.%s' % subscription['_datatype'],
                'id': obj.eventid if subscription['_datatype'] == 'Event' else obj.entryid,
            }
        }

    def run(self):
        while True:
            store, notification, subscription = QUEUE.get()

            data = self._notification(subscription, notification.event_type, notification.object)

            verify = not self.options or not self.options.insecure
            try:
                if self.options and self.options.with_metrics:
                    POST_COUNT.inc()
                logging.debug('subscription notification, id:%s, url:%s', subscription['id'], subscription['notificationUrl'])
                # TODO(longsleep): This must be asynchronous or a queue per notificationUrl.
                response = requests.post(subscription['notificationUrl'], json=data, timeout=10, verify=verify)
                # TODO(longsleep): Retry respons errors.
            except Exception:
                logging.exception('subscription notification failed, id:%s, url:%s', subscription['id'], subscription['notificationUrl'])


class Watcher(Thread):
    def __init__(self, options):
        Thread.__init__(self, name='watcher')
        set_thread_name(self.name)
        self.options = options
        self.daemon = True
        self.exit = Event()

    def run(self):
        while not self.exit.wait(timeout=60):
            records = RECORDS
            purge = []
            for auth_username, record in records.items():
                subscriptions = record.subscriptions
                expired = {}
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                for subscriptionid, (subscription, sink, userid) in subscriptions.items():
                    expirationDateTime = dateutil.parser.parse(subscription['expirationDateTime'])
                    if expirationDateTime <= now:
                        logging.debug('subscription expired, id:%s', subscriptionid)
                        expired[subscriptionid] = sink
                        sink.expired = True
                for subscriptionid, sink in expired.items():
                    if sink.expired:
                        try:
                            try:
                                del subscriptions[subscriptionid]
                            except KeyError:
                                continue
                            sink.store.unsubscribe(sink)
                            logging.debug('subscription cleaned up, id:%s', subscriptionid)
                            if self.options and self.options.with_metrics:
                                SUBSCR_EXPIRED.inc()
                                SUBSCR_ACTIVE.dec(1)
                        except Exception:
                            logging.exception('faild to clean up subscription, id:%s', subscriptionid)
                if len(subscriptions) == 0:
                    logging.debug('cleaning up user without any subscriptions, auth_user:%s', auth_username)
                    purge.append((auth_username, record))

            with threadLock:
                for (auth_username, record) in purge:
                    currentRecord = records[auth_username]
                    if currentRecord is record:
                        del records[auth_username]


class Sink:
    def __init__(self, options, store, subscription):
        self.options = options
        self.store = store
        self.subscription = subscription
        self.expired = False

    def update(self, notification):
        QUEUE.put((self.store, notification, self.subscription))


def _subscription_object(store, resource):
    # specific mail/contacts folder
    for (pattern, datatype) in (PATTERN_MESSAGES, PATTERN_CONTACTS, PATTERN_EVENTS):
        match = pattern.match('/'+resource)
        if match:
            return utils._folder(store, match.groupdict()['folderid']), None, datatype

    # all mail
    if resource == 'me/messages':
        return store.inbox, None, 'Message'

    # all contacts
    elif resource == 'me/contacts':
        return store.contacts, None, 'Contact'

    # all events
    elif resource in ('me/events', 'me/calendar/events'):
        return store.calendar, None, 'Event'


def _export_subscription(subscription):
    return dict((a, b) for (a, b) in subscription.items() if not a.startswith('_'))


class SubscriptionResource:
    def __init__(self, options):
        self.options = options

        global QUEUE
        try:
            QUEUE
        except NameError:
            QUEUE = Queue()
            Processor(self.options).start()
            Watcher(self.options).start()

    def on_post(self, req, resp):
        record = _record(req, self.options)
        server = record.server
        user = record.user
        store = record.store
        fields = json.loads(req.stream.read().decode('utf-8'))

        id_ = str(uuid.uuid4())

        # validate webhook
        validationToken = str(uuid.uuid4())
        verify = not self.options or not self.options.insecure
        try:  # TODO async
            logging.debug('validating subscription notification url, auth_user:%s, id:%s, url:%s', server.auth_user, id_, fields['notificationUrl'])
            r = requests.post(fields['notificationUrl']+'?validationToken='+validationToken, timeout=10, verify=verify)
            if r.text != validationToken:
                logging.debug('subscription validation failed, validation token mismatch, id:%s, url:%s', id_, fields['notificationUrl'])
                raise utils.HTTPBadRequest("Subscription validation request failed.")
        except Exception:
            logging.exception('subscription validation request error, id:%s, url:%s', id_, fields['notificationUrl'])
            raise utils.HTTPBadRequest("Subscription validation request failed.")

        subscription_object = _subscription_object(store, fields['resource'])
        if not subscription_object:
            logging.error('subscription object is invalid, id:%s, resource:%s', id_, fields['resource'])
            raise utils.HTTPBadRequest("Subscription object invalid.")
        target, folder_types, data_type = subscription_object

        # create subscription
        subscription = fields
        subscription['id'] = id_
        subscription['_datatype'] = data_type

        sink = Sink(self.options, store, subscription)
        object_types = ['item']  # TODO folders not supported by graph atm?
        event_types = [x.strip() for x in subscription['changeType'].split(',')]

        try:
            target.subscribe(sink, object_types=object_types,
                             event_types=event_types, folder_types=folder_types)
        except MAPIErrorNoSupport:
            # Mhm connection is borked.
            # TODO(longsleep): Clean up and start from new.
            # TODO(longsleep): Add internal retry, do not throw exception to client.
            logging.exception('subscription not possible right now, resetting connection')
            raise falcon.HTTPInternalServerError('subscription not possible, please retry')

        record.subscriptions[id_] = (subscription, sink, user.userid)
        logging.debug(
            'subscription created, auth_user:%s, id:%s, target:%s, object_types:%s, event_types:%s, folder_types:%s',
            server.auth_user, id_, target, object_types, event_types, folder_types
        )

        resp.content_type = "application/json"
        if INDENT:
            resp.body = json.dumps(_export_subscription(subscription), indent=2, ensure_ascii=False).encode('utf-8')
        else:
            resp.body = json.dumps(_export_subscription(subscription), ensure_ascii=False).encode('utf-8')
        resp.status = falcon.HTTP_201

        if self.options and self.options.with_metrics:
            SUBSCR_COUNT.inc()
            SUBSCR_ACTIVE.inc()

    def on_get(self, req, resp, subscriptionid=None):
        record = _record(req, self.options)

        if subscriptionid:
            try:
                subscription, sink, userid = record.subscriptions[subscriptionid]
            except KeyError:
                resp.status = falcon.HTTP_404
                return
            data = _export_subscription(subscription)
        else:
            userid = user.userid
            data = {
                '@odata.context': req.path,
                'value': [_export_subscription(subscription) for (subscription, _, uid) in SUBSCRIPTIONS.values() if uid == userid],  # TODO doesn't scale
            }

        resp.content_type = "application/json"
        if INDENT:
            resp.body = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        else:
            resp.body = json.dumps(data, ensure_ascii=False).encode('utf-8')

    def on_patch(self, req, resp, subscriptionid):
        record = _record(req, self.options)

        try:
            subscription, sink, userid = record.subscriptions[subscriptionid]
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        fields = json.loads(req.stream.read().decode('utf-8'))

        for k, v in fields.items():
            if v and k == 'expirationDateTime':
                # NOTE(longsleep): Setting a dict key which is already there is threadsafe in current CPython implementations.
                subscription['expirationDateTime'] = v

        if sink.expired:
            sink.expired = False
            logging.debug('subscription updated before it expired, id:%s', subscriptionid)

        data = _export_subscription(subscription)

        resp.content_type = "application/json"
        if INDENT:
            resp.body = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        else:
            resp.body = json.dumps(data, ensure_ascii=False).encode('utf-8')

    def on_delete(self, req, resp, subscriptionid):
        record = _record(req, self.options)
        store = record.store

        try:
            subscription, sink, userid = record.subscriptions.pop(subscriptionid)
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        store.unsubscribe(sink)

        logging.debug('subscription deleted, id:%s', subscriptionid)

        if self.options and self.options.with_metrics:
            SUBSCR_ACTIVE.dec(1)

        resp.set_header('Content-Length', '0')  # https://github.com/jonashaag/bjoern/issues/139
        resp.status = falcon.HTTP_204
