# SPDX-License-Identifier: AGPL-3.0-or-later
import codecs
import collections
import datetime
import http.cookiejar
import logging
import time
import uuid
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from urllib.parse import urlparse

import dateutil.parser
import falcon
import kopano
import requests
import validators
from MAPI.Struct import MAPIErrorNoSupport

from grapi.api.v1.resource import Resource, _dumpb_json

from . import utils
from .schema import subscription_schema, update_subscription_schema

try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS = True
except ImportError:  # pragma: no cover
    PROMETHEUS = False


# TODO don't block on sending updates
# TODO async subscription validation
# TODO restarting app/server?
# TODO list subscription scalability
# TODO use mulitprocessing

# GRAPI uses Base64, tell kopano module about it.
kopano.set_bin_encoding('base64')

# Requests has a default logger which is chatty. Only get interesting stuff.
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# threadLock is a global lock which can be used to protect the global
# states in this file.
threadLock = Lock()

# RECORDS hold the named tuple Record values for users which have active
# subscriptions.
RECORDS = {}
# RECORD_INDEX is incremented whenever a active subscription gets replaced
# and the incremented value is appended to the key of the record in RECRODS
# to allow it to be cleaned up later.
RECORD_INDEX = 0

# Global request session, to reuse connections.
REQUEST_SESSION = requests.Session()
REQUEST_SESSION.cookies = requests.cookies.RequestsCookieJar(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))
REQUEST_SESSION.max_redirects = 3
REQUEST_HTTPS_ADAPTER = requests.adapters.HTTPAdapter(pool_maxsize=1024)  # TODO(longsleep): Add configuration for pool sizes.
REQUEST_SESSION.mount('https://', REQUEST_HTTPS_ADAPTER)


# Record binds subscription and conection information per user for easy painless
# access to its members.
class Record:
    def __init__(self, server, user, store, subscriptions):
        self.server = server
        self.user = user
        self.store = store
        self.subscriptions = subscriptions


PATTERN_MESSAGES = (falcon.routing.compile_uri_template('/me/mailFolders/{folderid}/messages')[1], 'Message')
PATTERN_CONTACTS = (falcon.routing.compile_uri_template('/me/contactFolders/{folderid}/contacts')[1], 'Contact')
PATTERN_EVENTS = (falcon.routing.compile_uri_template('/me/calendars/{folderid}/events')[1], 'Event')


if PROMETHEUS:
    SUBSCR_COUNT = Counter('kopano_mfr_kopano_total_subscriptions', 'Total number of subscriptions')
    SUBSCR_EXPIRED = Counter('kopano_mfr_kopano_total_expired_subscriptions', 'Total number of subscriptions which expired')
    SUBSCR_ACTIVE = Gauge('kopano_mfr_kopano_active_subscriptions', 'Number of active subscriptions', multiprocess_mode='liveall')
    PROCESSOR_BATCH_HIST = Histogram('kopano_mfr_kopano_webhook_batch_size', 'Number of webhook posts processed in one batch')
    POST_COUNT = Counter('kopano_mfr_kopano_total_webhook_posts', 'Total number of webhook posts')
    POST_ERRORS = Counter('kopano_mfr_kopano_total_webhook_post_errors', 'Total number of webhook post errors')
    POST_HIST = Histogram('kopano_mfr_kopano_webhook_post_duration_seconds', 'Duration of webhook post requests in seconds')
    DANGLING_COUNT = Counter('kopano_mfr_kopano_total_broken_subscription_conns', 'Total number of broken subscription connections')
    QUEUE_SIZE_GAUGE = Gauge('kopano_mfr_kopano_subscription_queue_size', 'Current size of subscriptions processor queue', multiprocess_mode='liveall')
    PROCESSOR_POOL_GAUGE = Gauge('kopano_mfr_kopano_webhook_pools', 'Current number of webhook pools')


def _server(auth_user, auth_pass, oidc=False, reconnect=False):
    server = kopano.Server(auth_user=auth_user, auth_pass=auth_pass,
                           notifications=True, parse_args=False, store_cache=False, oidc=oidc, config={})
    logging.info('server connection established, server:%s, auth_user:%s', server, server.auth_user)

    return server


def _basic_auth(username, password):
        server = _server(username, password)
        user = server.user(username)
        return Record(server=server, user=user, store=user.store, subscriptions={})


def _record(req, options):
    """
    Return the record matching the provided request. If no record is found, a
    new one is created.
    """
    global RECORD_INDEX
    global RECORDS

    auth = utils._auth(req, options)

    auth_password = None
    auth_userid = None
    oidc = False
    if auth['method'] == 'bearer':
        auth_userid = auth['userid']
        auth_password = auth['token']
        oidc = True
    elif auth['method'] == 'passthrough':  # pragma: no cover
        auth_userid = auth['userid']
        auth_password = ''
    elif auth['method'] == 'basic':  # basic auth for tests
        return _basic_auth(codecs.decode(auth['user'], 'utf8'), auth['password'])

    with threadLock:
        record = RECORDS.get(auth_userid)
    if record is not None:
        try:
            user = record.server.user(userid=auth_userid)
            return record
        except Exception:  # server restart: try to reconnect TODO check kc_session_restore (incl. notifs!)
            logging.exception('network or session error while getting user from server, reconnect automatically')
            oldRecord = None
            oldSubscriptions = None
            with threadLock:
                oldRecord = RECORDS.pop(auth_userid, None)
                if oldRecord:
                    oldSubscriptions = oldRecord.subscriptions.copy()
                    oldRecord.subscriptions.clear()
                    RECORD_INDEX += 1
                    RECORDS['{}_dangle_{}'.format(auth_userid, RECORD_INDEX)] = oldRecord

            if oldSubscriptions:
                # Instantly kill of subscriptions.
                for subscriptionid, (subscription, sink, userid) in oldSubscriptions.items():
                    sink.unsubscribe()
                    logging.debug('subscription cleaned up after connection error, id:%s', subscriptionid)
                    if options and options.with_metrics:
                        SUBSCR_ACTIVE.dec(1)
                oldSubscriptions = None
            if oldRecord and options and options.with_metrics:
                DANGLING_COUNT.inc()

    logging.debug('creating subscription session for user %s', auth_userid)
    server = _server(auth_userid, auth_password, oidc=oidc)
    user = server.user(userid=auth_userid)
    store = user.store

    record = Record(server=server, user=user, store=store, subscriptions={})
    with threadLock:
        RECORDS.update({auth_userid: record})

        return RECORDS.get(auth_userid)


NotificationRecord = collections.namedtuple('NotificationRecord', [
    'subscriptionId',
    'clientState',
    'changeType',
    'resource',
    'dataType',
    'url',
    'id',
])


class LastUpdatedOrderedDict(collections.OrderedDict):
    '''Store items in the order the keys were last added.'''

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        collections.OrderedDict.__setitem__(self, key, value)


class SubscriptionProcessor(Thread):
    def __init__(self, options):
        Thread.__init__(self, name='kopano_subscription_processor')
        utils.set_thread_name(self.name)
        self.options = options
        self.daemon = True

    def _record(self, subscription, notification):
        return NotificationRecord(
            subscriptionId=subscription['id'],
            clientState=subscription['clientState'],
            changeType=notification.event_type,
            resource=subscription['resource'],
            dataType=subscription['_datatype'],
            url=subscription['notificationUrl'],
            id=notification.object.eventid if subscription['_datatype'] == 'Event' else notification.object.entryid,
        )

    def _notification(self, record):
        return {
            'subscriptionId': record.subscriptionId,
            'clientState': record.clientState,
            'changeType': record.changeType,
            'resource': record.resource,
            'resourceData': {
                '@data.type': '#Microsoft.Graph.%s' % record.dataType,
                'id': record.id,
            },
        }

    def run(self):
        # Store all pending records in their order.
        pending = LastUpdatedOrderedDict()
        # Ts is used to keep track of the last action, allowing debounce.
        ts = 0
        debounceDelay = 1
        while True:
            waitingItems = len(pending)
            try:
                # Get queue entries, either blocking or with timeout. A timeout is used when records
                # are already pending.
                store, notification, subscription = QUEUE.get(block=True, timeout=debounceDelay if waitingItems else None)
                record = self._record(subscription, notification)
                # Add record to pending sorted dict. This also changes the position of existing records to the end.
                pending[record] = True
                now = time.monotonic()
                if not waitingItems:
                    # Nothing was waiting before, reset ts and wait.
                    ts = now
                    continue
                if now - ts < debounceDelay:
                    # Delay is not reached, wait longer.
                    continue
                # If we get here, all pending records will be processed.
            except Empty:
                if not waitingItems:
                    continue
                # If we get here, it means items are pending and no more have been coming, pending records will be processed.

            verify = not self.options or not self.options.insecure
            with_metrics = self.options and self.options.with_metrics

            if with_metrics:
                PROCESSOR_BATCH_HIST.observe(len(pending))

            # Process pending records in their order.
            for record in pending:
                try:
                    if with_metrics:
                        POST_COUNT.inc()
                    logging.debug('subscription notification, id:%s, url:%s', record.subscriptionId, record.url)
                    # TODO(longsleep): This must be asynchronous or a queue per notificationUrl.
                    # TODO(longsleep): Make timeout configuration.
                    if with_metrics:
                        with POST_HIST.time():
                            REQUEST_SESSION.post(record.url, json=self._notification(record), timeout=10, verify=verify)
                    else:
                        REQUEST_SESSION.post(record.url, json=self._notification(record), timeout=10, verify=verify)
                except Exception:
                    # TODO(longsleep): Retry response errors.
                    if with_metrics:
                        POST_ERRORS.inc()
                    logging.exception('subscription notification failed, id:%s, url:%s', record.subscriptionId, record.url)

            # All done, clear for next round.
            pending.clear()
            ts = time.monotonic()


class SubscriptionPurger(Thread):
    def __init__(self, options):
        Thread.__init__(self, name='kopano_subscription_purger')
        utils.set_thread_name(self.name)
        self.options = options
        self.daemon = True
        self.exit = Event()

    def run(self):
        expired = {}
        purge = []
        while not self.exit.wait(timeout=60):
            # NOTE(longsleep): Periodically update some metrics since callbacks
            # do not get triggerd in multiprocess mode. To get the information
            # we trigger it manually.
            if self.options and self.options.with_metrics:
                QUEUE_SIZE_GAUGE.set(QUEUE.qsize())
                PROCESSOR_POOL_GAUGE.set(len(REQUEST_HTTPS_ADAPTER.poolmanager.pools.keys()))

            records = RECORDS
            for auth_username, record in records.items():
                subscriptions = record.subscriptions
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
                            sink.unsubscribe()
                            logging.debug('subscription cleaned up, id:%s', subscriptionid)
                            if self.options and self.options.with_metrics:
                                SUBSCR_EXPIRED.inc()
                                SUBSCR_ACTIVE.dec(1)
                        except Exception:
                            logging.exception('failed to clean up subscription, id:%s', subscriptionid)
                if len(subscriptions) == 0:
                    logging.debug('cleaning up user without any subscriptions, auth_user:%s', auth_username)
                    purge.append((auth_username, record))

            with threadLock:
                for (auth_username, record) in purge:
                    currentRecord = records[auth_username]
                    if currentRecord is record:
                        del records[auth_username]
                    # NOTE(longsleep): Clear record references to ensure that
                    # the associated objects can be destroyed and the notification
                    # thread is stopped.
                    record.user = None
                    record.store = None
                    record.server = None

            expired.clear()
            del purge[:]


class SubscriptionSink:
    def __init__(self, store, options, subscription):
        self.store = store
        self.options = options
        self.subscription = subscription
        self.expired = False

    def update(self, notification):
        if self.store is not None:
            while True:
                try:
                    QUEUE.put((self.store, notification, self.subscription), timeout=5)  # TODO(longsleep): Add configuration for timeout.
                    break
                except Full:
                    logging.warning('subscription sink queue is full: %d', QUEUE.qsize())
                    time.sleep(1)

    def unsubscribe(self):
        self.store.unsubscribe(self)
        self.store = None


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


class SubscriptionResource(Resource):
    def __init__(self, options):
        super().__init__(options)

        global QUEUE
        try:
            QUEUE
        except NameError:
            QUEUE = Queue(1024)  # TODO(longsleep): Add configuration for queue size.
            SubscriptionProcessor(self.options).start()
            SubscriptionPurger(self.options).start()

    def on_post(self, req, resp):
        record = _record(req, self.options)
        server = record.server
        user = record.user
        store = record.store
        fields = self.load_json(req)
        self.validate_json(subscription_schema, fields)

        id_ = str(uuid.uuid4())

        verify = not self.options or not self.options.insecure

        # Validate URL.
        try:
            # Enforce URL to valid and to be public, unless running insecure.
            if not validators.url(fields['notificationUrl'], public=True):
                if verify:
                    raise ValueError('url validator failed')
                else:
                    logging.warning('ignored notification url validation error (insecure enabled), auth_user:%s, id:%s, url:%s', server.auth_user, id_, fields['notificationUrl'])
            notificationUrl = urlparse(fields['notificationUrl'])
            if notificationUrl.scheme != 'https':
                if not verify and notificationUrl.scheme == 'http':
                    logging.warning('allowing unencrypted notification url (insecure enabled), auth_user:%s, id:%s, url:%s', server.auth_user, id_, fields['notificationUrl'])
                else:
                    raise ValueError('must use https scheme')
        except Exception:
            logging.debug('invalid subscription notification url, auth_user:%s, id:%s, url:%s', server.auth_user, id_, fields['notificationUrl'], exc_info=True)
            raise utils.HTTPBadRequest("Subscription notification url invalid.")

        # Validate webhook.
        validationToken = str(uuid.uuid4())
        try:  # TODO async
            logging.debug('validating subscription notification url, auth_user:%s, id:%s, url:%s', server.auth_user, id_, fields['notificationUrl'])
            r = REQUEST_SESSION.post(fields['notificationUrl']+'?validationToken='+validationToken, timeout=10, verify=verify)  # TODO(longsleep): Add timeout configuration.
            if r.text != validationToken:
                logging.debug('subscription validation failed, validation token mismatch, id:%s, url:%s', id_, fields['notificationUrl'])
                raise utils.HTTPBadRequest("Subscription validation request failed.")
        except Exception:
            logging.exception('subscription validation request error, id:%s, url:%s', id_, fields['notificationUrl'])
            raise utils.HTTPBadRequest("Subscription validation request failed.")

        # Validate subscription data.
        subscription_object = _subscription_object(store, fields['resource'])
        if not subscription_object:
            logging.error('subscription object is invalid, id:%s, resource:%s', id_, fields['resource'])
            raise utils.HTTPBadRequest("Subscription object invalid.")
        target, folder_types, data_type = subscription_object

        # Create subscription.
        subscription = fields
        subscription['id'] = id_
        subscription['_datatype'] = data_type

        sink = SubscriptionSink(store, self.options, subscription)
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
            raise falcon.HTTPInternalServerError(description='subscription not possible, please retry')

        record.subscriptions[id_] = (subscription, sink, user.userid)
        logging.debug(
            'subscription created, auth_user:%s, id:%s, target:%s, object_types:%s, event_types:%s, folder_types:%s',
            server.auth_user, id_, target, object_types, event_types, folder_types
        )

        resp.content_type = "application/json"
        resp.body = _dumpb_json(_export_subscription(subscription))
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
            user = record.user
            userid = user.userid
            data = {
                '@odata.context': req.path,
                'value': [_export_subscription(subscription) for (subscription, _, uid) in record.subscriptions.values() if uid == userid],  # TODO doesn't scale
            }

        resp.content_type = "application/json"
        resp.body = _dumpb_json(data)

    def on_patch(self, req, resp, subscriptionid=None):
        if not subscriptionid:
            raise utils.HTTPBadRequest('missing required subscriptionid')

        record = _record(req, self.options)

        try:
            subscription, sink, userid = record.subscriptions[subscriptionid]
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        fields = self.load_json(req)
        self.validate_json(update_subscription_schema, fields)

        for k, v in fields.items():
            if v and k == 'expirationDateTime':
                # NOTE(longsleep): Setting a dict key which is already there is threadsafe in current CPython implementations.
                try:
                    dateutil.parser.parse(v)
                    subscription['expirationDateTime'] = v
                except ValueError:
                    raise utils.HTTPBadRequest('expirationDateTime is not a valid datetime string')

        if sink.expired:
            sink.expired = False
            logging.debug('subscription updated before it expired, id:%s', subscriptionid)

        data = _export_subscription(subscription)

        resp.content_type = "application/json"
        resp.body = _dumpb_json(data)

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

        self.respond_204(resp)
