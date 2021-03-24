# SPDX-License-Identifier: AGPL-3.0-or-later
"""Subscription implementation."""
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

from grapi.api.v1 import config
from grapi.api.v1.api import API
from grapi.api.v1.resource import Resource, _dumpb_json
from grapi.api.v1.schema import subscription as subscription_schema

from . import utils

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

# thread_lock is a global lock which can be used to protect the global
# states in this file.
thread_lock = Lock()

# RECORDS hold the named tuple Record values for users which have active
# subscriptions.
RECORDS = {}

# RECORD_INDEX is incremented whenever a active subscription gets replaced
# and the incremented value is appended to the key of the record in RECRODS
# to allow it to be cleaned up later.
RECORD_INDEX = 0

# Global request session, to reuse connections.
REQUEST_SESSION = requests.Session()
REQUEST_SESSION.cookies = requests.cookies.RequestsCookieJar(
    http.cookiejar.DefaultCookiePolicy(allowed_domains=[])
)
REQUEST_SESSION.max_redirects = config.SUBSCRIPTION_REQUEST_MAX_REDIRECT
REQUEST_HTTPS_ADAPTER = requests.adapters.HTTPAdapter(
    pool_maxsize=config.SUBSCRIPTION_REQUEST_POOL_MAXSIZE
)
REQUEST_SESSION.mount(
    config.SUBSCRIPTION_REQUEST_SESSION_PREFIX, REQUEST_HTTPS_ADAPTER
)

# API to get access to all routes.
_API = API()

NotificationRecord = collections.namedtuple('NotificationRecord', [
    'subscriptionId',
    'clientState',
    'changeType',
    'resource',
    'dataType',
    'url',
    'id',
])


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


class Record:
    """Record binds subscription and conection information per user."""

    def __init__(self, server, user, store, subscriptions):
        """Python built-in method.

        Args:
            server (Server): Kopano server instance.
            user (User): user object.
            store (Store): user's store object.
            subscriptions (Dict): subscriptions data.
        """
        self.server = server
        self.user = user
        self.store = store
        self.subscriptions = subscriptions


def _server(auth_user, auth_pass, oidc=False):
    """Connect to a Kopano server.

    Args:
        auth_user (str): authentication username.
        auth_pass (str): authentication password.
        oidc (bool): is it OIDC or not. Defaults to False.

    Returns:
        kopano.Server: a instance of the Kopano Server.
    """
    server = kopano.server(
        auth_user=auth_user,
        auth_pass=auth_pass,
        notifications=True,
        parse_args=False,
        store_cache=False,
        oidc=oidc,
        config={}
    )
    logging.info(
        "server connection established, server:%s, auth_user:%s", server, server.auth_user
    )
    return server


def _basic_auth(username, password):
    """Basic authentication.

    Args:
        username (str): authentication username.
        password (str): authentication password.

    Returns:
        Record: authenticated data (e.g. store, user, and ...)
    """
    server = _server(username, password)
    user = server.user(username)
    return Record(server=server, user=user, store=user.store, subscriptions={})


def _record(req, options):
    """Return the record matching the provided request.

    If no record is found, a new one is created.

    Args:
        req (Request): Falcon request object.
        options (Options): deployment options.

    Returns:
        Record: record matching the provided request.
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

    with thread_lock:
        record = RECORDS.get(auth_userid)
    if record is not None:
        try:
            user = record.server.user(userid=auth_userid)
            return record
        except Exception:
            # server restart: try to reconnect TODO check kc_session_restore (incl. notifs!)
            logging.exception(
                "network or session error while getting user from server, reconnect automatically"
            )
            old_record = None
            old_subscriptions = None
            with thread_lock:
                old_record = RECORDS.pop(auth_userid, None)
                if old_record:
                    old_subscriptions = old_record.subscriptions.copy()
                    old_record.subscriptions.clear()
                    RECORD_INDEX += 1
                    RECORDS['{}_dangle_{}'.format(auth_userid, RECORD_INDEX)] = old_record

            if old_subscriptions:
                # Instantly kill of subscriptions.
                for subscriptionid, (_, sink, _) in old_subscriptions.items():
                    sink.unsubscribe()
                    logging.debug(
                        'subscription cleaned up after connection error, id:%s', subscriptionid
                    )
                    if options and options.with_metrics:
                        SUBSCR_ACTIVE.dec(1)
                old_subscriptions = None
            if old_record and options and options.with_metrics:
                DANGLING_COUNT.inc()

    logging.debug('creating subscription session for user %s', auth_userid)
    server = _server(auth_userid, auth_password, oidc=oidc)
    user = server.user(userid=auth_userid)
    store = user.store

    record = Record(server=server, user=user, store=store, subscriptions={})
    with thread_lock:
        RECORDS.update({auth_userid: record})
        return RECORDS.get(auth_userid)


class LastUpdatedOrderedDict(collections.OrderedDict):
    """Store items in the order the keys were last added."""

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        collections.OrderedDict.__setitem__(self, key, value)


def new_record(subscription, notification):
    """Create and return a new notification record.

    Args:
        subscription (Dict): subscription info.
        notification (Notification): an instance of a notification.

    Returns:
        NotificationRecord: new notification record.
    """
    if subscription['_datatype'] == 'event':
        event_id = notification.object.eventid
    else:
        event_id = notification.object.entryid

    return NotificationRecord(
        subscriptionId=subscription['id'],
        clientState=subscription['clientState'],
        changeType=notification.event_type,
        resource=subscription['resource'],
        dataType=subscription['_datatype'],
        url=subscription['notificationUrl'],
        id=event_id,
    )


def gen_notification(record):
    """Return notification data structure based on record.

    Args:
        record (Record): an instance of a record.

    Returns:
        Dict: notification data.
    """
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


class SubscriptionProcessor(Thread):
    """Process tasks in background.

    This single worker thread is responsible for gathering all notifications
    from the subscription queue and debouncing them before posting these
    notifications to the corresponding notification url.

    The queue is filled with notifications by the SubscriptionSink.
    """

    _queue = None

    def __init__(self, options, queue):
        """Built-in Python method.

        Args:
            options (Namespace): deployment options.
            queue (Queue): task queue.
        """
        self.options = options
        self._queue = queue

        Thread.__init__(self, name='kopano_subscription_processor')
        utils.set_thread_name(self.name)
        self.daemon = True

    def run(self):
        # Store all pending records in their order.
        pending = LastUpdatedOrderedDict()
        # ts is used to keep track of the last action, allowing debounce.
        ts = 0
        debounce_delay = 1

        while True:
            waiting_items = len(pending)
            try:
                # Get queue entries, either blocking or with timeout. A timeout is used when records
                # are already pending.
                _, notification, subscription = self._queue.get(
                    timeout=debounce_delay if waiting_items else None
                )
                record = new_record(subscription, notification)

                # Add record to pending sorted dict.
                # This also changes the position of existing records to the end.
                pending[record] = True
                now = time.monotonic()
                if not waiting_items:
                    # Nothing was waiting before, reset ts and wait.
                    ts = now
                    continue
                if now - ts < debounce_delay:
                    # Delay is not reached, wait longer.
                    continue
                # If we get here, all pending records will be processed.
            except Empty:
                if not waiting_items:
                    continue
                # If we get here, it means items are pending and no more have been coming,
                # pending records will be processed.

            verify = not self.options or not self.options.insecure
            with_metrics = self.options and self.options.with_metrics

            if with_metrics:
                PROCESSOR_BATCH_HIST.observe(len(pending))

            # Process pending records in their order.
            for record in pending:
                try:
                    if with_metrics:
                        POST_COUNT.inc()
                    logging.debug(
                        'subscription notification, id:%s, url:%s',
                        record.subscriptionId, record.url
                    )
                    # TODO(longsleep): This must be asynchronous or a queue per notificationUrl.
                    if with_metrics:
                        with POST_HIST.time():
                            REQUEST_SESSION.post(
                                record.url,
                                json=gen_notification(record),
                                timeout=config.SUBSCRIPTION_NOTIFY_TIMEOUT,
                                verify=verify
                            )
                    else:
                        REQUEST_SESSION.post(
                            record.url,
                            json=gen_notification(record),
                            timeout=config.SUBSCRIPTION_NOTIFY_TIMEOUT,
                            verify=verify
                        )
                except Exception:
                    # TODO(longsleep): Retry response errors.
                    if with_metrics:
                        POST_ERRORS.inc()
                    logging.exception(
                        "subscription notification failed, id:%s, url:%s",
                        record.subscriptionId, record.url
                    )

            # All done, clear for next round.
            pending.clear()
            ts = time.monotonic()


class SubscriptionPurger(Thread):
    """Subscription purger.

    Cleans up expired subscriptions based on the subscriptions
    expirationDateTime. One worker thread is spawned per grapi worker.
    """

    _queue = None

    def __init__(self, options, queue):
        """Built-in Python method.

        Args:
            options (Namespace): deployment options.
            queue (Queue): task queue.
        """
        self.options = options
        self._queue = queue

        Thread.__init__(self, name='kopano_subscription_purger')
        utils.set_thread_name(self.name)
        self.daemon = True
        self.exit = Event()

    def run(self):
        """Built-in Thread method."""
        expired = {}
        purge = []
        while not self.exit.wait(timeout=config.SUBSCRIPTION_EXIT_WAIT_TIMEOUT):
            # NOTE(longsleep): Periodically update some metrics since callbacks
            # do not get triggerd in multiprocess mode. To get the information
            # we trigger it manually.
            if self.options and self.options.with_metrics:
                QUEUE_SIZE_GAUGE.set(self._queue.qsize())
                PROCESSOR_POOL_GAUGE.set(len(REQUEST_HTTPS_ADAPTER.poolmanager.pools.keys()))

            for auth_username, record in RECORDS.items():
                subscriptions = record.subscriptions
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                for subscriptionid, (subscription, sink, _) in subscriptions.items():
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
                            logging.exception(
                                'failed to clean up subscription, id:%s', subscriptionid
                            )
                if len(subscriptions) == 0:
                    logging.debug(
                        'cleaning up user without any subscriptions, auth_user:%s', auth_username
                    )
                    purge.append((auth_username, record))

            with thread_lock:
                for (auth_username, record) in purge:
                    currentRecord = RECORDS[auth_username]
                    if currentRecord is record:
                        del RECORDS[auth_username]
                    # NOTE(longsleep): Clear record references to ensure that
                    # the associated objects can be destroyed and the notification
                    # thread is stopped.
                    record.user = None
                    record.store = None
                    record.server = None

            expired.clear()
            purge.clear()


class SubscriptionSink:
    """Main observer class which needs to be passed to 'subscribe' method of a folder."""

    _queue = None

    def __init__(self, store, options, subscription, queue):
        """Built-in Python method.

        Args:
            store (Store): user store object.
            options (Option): deployment options.
        """
        self.store = store
        self.options = options
        self.subscription = subscription
        self._queue = queue

        self.expired = False

    def update(self, notification):
        """Update method will be executed in each notifying action.

        Args:
            notification (Notification): notification action.
        """
        if self.store is not None:
            while True:
                try:
                    self._queue.put(
                        (self.store, notification, self.subscription),
                        timeout=config.SUBSCRIPTION_SINK_UPDATE_TIMEOUT
                    )
                    break
                except Full:
                    logging.warning('subscription sink queue is full: %d', self._queue.qsize())
                    time.sleep(1)

    def unsubscribe(self):
        """Drop out an item from subscriptions list."""
        self.store.unsubscribe(self)
        self.store = None


def _detect_data_type(store, resource_name, folderid=None):
    """Return folder and category based on data type.

    Args:
        store (Store): user's store object.
        resource_name (str): resource name. It's something like URI (e.g. me/messages).
        folderid (Union[str,None]): folder ID.

    Returns:
        Tuple[Folder,list,str,list]: folder object, folder types,
            data type name, and object types names.

    Raises:
        ValueError: when resource is not found or is invalid.
    """
    if resource_name == "MessageResource":
        return (
            store.inbox if folderid is None else utils._folder(store, folderid),
            ["mail"], "message", ["item"]
        )
    elif resource_name == "EventResource":
        return (
            store.calendar if folderid is None else utils._folder(store, folderid),
            ["calendar"], "event", ["item"]
        )
    elif resource_name == "ContactResource":
        return (
            store.contacts if folderid is None else utils._folder(store, folderid),
            ["contact"], "contact", ["item"]
        )
    else:
        raise ValueError("Invalid resource name")


def _subscription_object(store, resource, subscription_id):
    """Return subscription object and info based on resource.

    Args:
        store (Store): user's store.
        resource (str): resource which needs to be tracked.
        subscription_id (str): generated subscription ID.

    Args:
        Tuple[Folder,list,str,list]: associated folder, folder types,
            data type name, and object types names.

    Raises:
        utils.HTTPBadRequest: when Subscription object is invalid.
    """
    # Specific mail/contacts folder.
    route_data = _API._router_search("{}/{}".format(config.PREFIX, resource))
    if route_data:
        try:
            return _detect_data_type(
                store, route_data[0].name, route_data[-2].get("folderid")
            )
        except ValueError:
            logging.error(
                "subscription resource is invalid, id:%s, resource:%s",
                subscription_id, resource
            )
            raise utils.HTTPBadRequest("Subscription resource is invalid.")
    else:
        raise utils.HTTPBadRequest("Subscription resource not found.")


def _export_subscription(subscription):
    """Export subscription.

    Args:
        subscription (Dict): list of subscriptions.

    Returns:
        Dict: generated an export subscription.
    """
    return {a: b for a, b in subscription.items() if not a.startswith('_')}


class SubscriptionResource(Resource):
    """Subscription resource."""

    _queue = None

    # Input schema validators.
    on_post_subscriptions_schema = subscription_schema.create_schema_validator
    on_patch_subscriptions_subscriptionid_schema = subscription_schema.update_schema_validator

    def __init__(self, options):
        """Built-in Python method.

        Args:
            options (Namespace): deployment options.
        """
        super().__init__(options)
        if self.__class__._queue is None:
            self.__class__._queue = Queue(config.SUBSCRIPTION_QUEUE_MAXSIZE)
            SubscriptionProcessor(self.options, self.__class__._queue).start()
            SubscriptionPurger(self.options, self.__class__._queue).start()

    @staticmethod
    def _clean_notification_url(notification_url, verify, subscription_id, auth_user):
        """Validate and return notification URL.

        Args:
            notification_url (str): notification URL.
            verify (bool): is secure or not.
            subscription_id (str): generated ID for the subscription.
            auth_user (str): authenticated username.

        Returns:
            ParseResult: parsed notification URL.

        Raises:
            utils.HTTPBadRequest: when the URL is invalid.
        """
        # Non-public URL in secure mode must be avoided.
        if not validators.url(notification_url, public=True):
            if verify:
                raise utils.HTTPBadRequest("Subscription notification url is invalid.")
            else:
                logging.warning(
                    "ignored notification url validation error (insecure enabled),"
                    " auth_user:%s, id:%s, url:%s",
                    auth_user, subscription_id, notification_url
                )

        notification_url = urlparse(notification_url)
        if notification_url.scheme != 'https':
            if not verify and notification_url.scheme == 'http':
                logging.warning(
                    "allowing unencrypted notification url (insecure enabled),"
                    " auth_user:%s, id:%s, url:%s",
                    auth_user, subscription_id, notification_url
                )
            else:
                # Must use HTTPS scheme.
                logging.debug(
                    "invalid subscription notification url, auth_user:%s, id:%s, url:%s",
                    auth_user, subscription_id, notification_url, exc_info=True
                )
                raise utils.HTTPBadRequest("Subscription notification url is invalid.")
        return notification_url

    @staticmethod
    def _validate_webhook(notification_url, verify, subscription_id, auth_user):
        """Webhook validation.

        Args:
            notification_url (ParseResult): parsed notification URL.
            verify (bool): is secure or not.
            subscription_id (str): generated ID for the subscription.
            auth_user (str): authenticated username.

        Raises:
            utils.HTTPBadRequest: when subscription validation request failed.
        """
        validation_token = str(uuid.uuid4())
        url = "{}?validationToken={}".format(notification_url.geturl(), validation_token)

        # Validate webhook.
        try:
            logging.debug(
                "validating subscription notification url, auth_user:%s, id:%s, url:%s",
                auth_user, subscription_id, notification_url
            )
            response = REQUEST_SESSION.post(
                url, timeout=config.SUBSCRIPTION_VALIDATION_TIMEOUT, verify=verify
            )
            if response.text != validation_token:
                logging.debug(
                    "subscription validation failed, validation token mismatch, id:%s, url:%s",
                    subscription_id, notification_url
                )
                raise utils.HTTPBadRequest("Subscription token validation failed.")
        except Exception:
            logging.exception(
                "subscription validation request error, id:%s, url:%s",
                subscription_id, notification_url
            )
            raise utils.HTTPBadRequest("Subscription webhook validation failed.")

    def _add_subscription(self, req, subscription_id, options, verify, json_data):
        """Add a new subscription.

        Args:
            req (Request): Falcon request object.
            subscription_id (str): generated subscription ID.
            options (Option): deployment option.
            verify (bool): secure mode is enabled or not.
            json_data (Dict): parsed request data in JSON format.

        Returns:
            Tuple[Record,SubscriptionSink]: tuple of processed data.
        """
        record = _record(req, options)

        notification_url = self._clean_notification_url(
            json_data['notificationUrl'], verify, subscription_id, record.server.auth_user
        )

        # Validate webhook.
        self._validate_webhook(
            notification_url, verify, subscription_id, record.server.auth_user
        )

        # Validate subscription data.
        folder, folder_types, data_type, object_types = _subscription_object(
            record.store, json_data['resource'], subscription_id
        )

        # Create subscription.
        json_data['id'] = subscription_id
        json_data['_datatype'] = data_type

        sink = SubscriptionSink(record.store, self.options, json_data, self._queue)
        event_types = json_data['changeType'].split(',')

        folder.subscribe(
            sink,
            object_types=object_types,
            event_types=event_types,
            folder_types=folder_types
        )

        record.subscriptions[subscription_id] = (json_data, sink, record.user.userid)
        logging.debug(
            "subscription created, auth_user:%s, id:%s, target:%s,"
            " object_types:%s, event_types:%s, folder_types:%s",
            record.server.auth_user, subscription_id, folder,
            object_types, event_types, folder_types
        )

        return record, sink

    def on_post(self, req, resp):
        """Handle POST request.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        subscription_id = req.context.request_id
        verify = not self.options or not self.options.insecure
        json_data = req.context.json_data

        max_retry = config.SUBSCRIPTION_INTERNAL_RETRY
        retry = 0
        while retry != max_retry:
            retry += 1
            try:
                self._add_subscription(
                    req, subscription_id, self.options, verify, json_data
                )
                break
            except MAPIErrorNoSupport:
                logging.exception(
                    "subscription not possible right now, trying %d/%d",
                    retry, max_retry
                )
                # A short nap for the resetting connection.
                time.sleep(0.5)
        else:
            raise falcon.HTTPInternalServerError(
                description="subscription is not possible, please retry"
            )

        # Prepare response.
        resp.status = falcon.HTTP_201
        resp.content_type = "application/json"
        resp.body = _dumpb_json(_export_subscription(json_data))

        if self.options and self.options.with_metrics:
            SUBSCR_COUNT.inc()
            SUBSCR_ACTIVE.inc()

    def on_get(self, req, resp):
        """Handle GET request - return all subscriptions.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        record = _record(req, self.options)
        userid = record.user.userid
        data = {
            '@odata.context': req.path,
            'value': [
                _export_subscription(subscription)
                for subscription, _, uid in record.subscriptions.values()
                if uid == userid
            ],  # TODO doesn't scale
        }

        resp.body = _dumpb_json(data)
        resp.status = falcon.HTTP_200

    def on_get_subscriptions_by_id(self, req, resp, subscriptionid):
        """Handle GET request - return by subscription ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            subscriptionid (str): subscription ID.
        """
        record = _record(req, self.options)
        try:
            subscription = record.subscriptions[subscriptionid][0]
        except KeyError:
            raise utils.HTTPNotFound()
        data = _export_subscription(subscription)
        resp.body = _dumpb_json(data)
        resp.status = falcon.HTTP_200

    def on_patch_subscriptions_by_id(self, req, resp, subscriptionid):
        """Handle PATCH request.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            subscriptionid (str): subscription ID.
        """
        record = _record(req, self.options)

        try:
            subscription, sink, _ = record.subscriptions[subscriptionid]
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        json_data = req.context.json_data

        for k, v in json_data.items():
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
        resp.body = _dumpb_json(data)
        resp.status = falcon.HTTP_200

    def on_delete_subscriptions_by_id(self, req, resp, subscriptionid):
        """Handle DELETE request for a specific subscription ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            subscriptionid (str): subscription ID.
        """
        record = _record(req, self.options)
        store = record.store

        try:
            sink = record.subscriptions.pop(subscriptionid)[1]
        except KeyError:
            resp.status = falcon.HTTP_404
            return

        store.unsubscribe(sink)

        logging.debug('subscription deleted, id:%s', subscriptionid)

        if self.options and self.options.with_metrics:
            SUBSCR_ACTIVE.dec(1)

        self.respond_204(resp)
