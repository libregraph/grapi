"""REST API endpoints."""
from grapi.api.common.api import API as BaseAPI

from . import middleware as grapi_middleware
from .api_resource import BackendResource
from .batch import BatchResource
from .config import PREFIX
from .healthcheck import HealthCheckResource
from .request import Request
from .utils import suffix_method_caller


class API(BaseAPI):
    """API implementation which contains all endpoints."""

    def __init__(self, options=None, middleware=None, backends=None, components=None):
        """Built-in Python method.

        Args:
            options (Option): deployment options. Defaults to None.
            middleware (list): list of middlewares which need be loaded. Defaults to None.
            backends (list): list of backends which need be loaded. Defaults to None.
            components (tuple): tuple of components which need to be loaded.
                None means all available components. Defaults to None.
        """
        if backends is None:
            backends = ['kopano']

        self.backends = backends

        if components is None:
            components = ('directory', 'mail', 'calendar', 'reminder', 'notification')

        name_backend = {}
        for name in backends:
            backend = self.import_backend(name)
            # Call initializer of a backend, should only be called once.
            if hasattr(backend, 'initialize'):
                backend.initialize(self, options)
            name_backend[name] = backend

        # TODO(jelle): make backends define their types by introducting a constant in grapi.api
        # And specifying it in backends.
        backend_components_categories = {
            'ldap': ['directory'],
            'kopano': ['directory', 'mail', 'calendar', 'reminder', 'notification'],
            'imap': ['mail'],
            'caldav': ['calendar'],
            'mock': ['mail', 'directory'],
        }

        default_backend = {}
        for component in components:
            for name, backend_components in backend_components_categories.items():
                if name in backends and component in backend_components:
                    default_backend[component] = name_backend[name]  # TODO type occurs twice

        # Middlewares which need be loaded.
        generic_middlewares = [
            grapi_middleware.RequestId(),
            grapi_middleware.RequestBodyExtractor(),
            grapi_middleware.ResponseHeaders(),
        ]

        middleware = (middleware or []) + [
            grapi_middleware.ResourcePatcher(name_backend, default_backend, options)
        ]
        middleware.extend(generic_middlewares)

        super().__init__(media_type=None, request_type=Request, middleware=middleware)

        self.req_options.strip_url_path_trailing_slash = True

        self.set_suffix_method_caller(suffix_method_caller)
        self.add_routes(default_backend, options)

    def add_routes(self, default_backend, options):
        """Add routes.

        Args:
            default_backend (Dict): list of default backends.
            options (Option): deployment option class.
        """
        healthCheck = HealthCheckResource()
        self.add_route('/health-check', healthCheck)

        batchEndpoint = BatchResource(None, self)
        self.add_route(PREFIX + '/$batch', batchEndpoint)

        directory = default_backend.get('directory')
        if directory:
            users = BackendResource(directory, 'UserResource')
            groups = BackendResource(directory, 'GroupResource')
            contactfolders = BackendResource(directory, 'ContactFolderResource')
            contacts = BackendResource(directory, 'ContactResource')
            photos = BackendResource(directory, 'ProfilePhotoResource')

            self.add_route(PREFIX + '/me', users)
            self.add_route(PREFIX + '/users', users)
            self.add_route(PREFIX + '/users/{userid}', users)

            self.add_route(PREFIX + '/groups', groups)
            self.add_route(PREFIX + '/groups/{groupid}', groups)

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/contactFolders/', contactfolders, suffix="contact_folders")
                self.add_route(user + '/contactFolders/{folderid}', contactfolders)
                self.add_route(user + '/contacts/', contacts, suffix="contacts")
                self.add_route(user + '/contacts/{itemid}', contacts)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}', contacts)

                self.add_route(user + '/photo', photos)
                self.add_route(user + '/photos/', photos, suffix="photos")
                self.add_route(user + '/photos/{photoid}', photos)

                self.add_route(user + '/contacts/{itemid}/photo', photos)
                self.add_route(user + '/contacts/{itemid}/photos/{photoid}', photos)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}/photo', photos)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}/photos/{photoid}', photos)

                self.add_route(user + '/memberOf', groups, suffix="member_of")

        mail = default_backend.get('mail')
        if mail:
            messages = BackendResource(mail, 'MessageResource')
            attachments = BackendResource(mail, 'AttachmentResource')
            mailfolders = BackendResource(mail, 'MailFolderResource')

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/mailFolders', mailfolders, suffix="mail_folders")
                self.add_route(user + '/mailFolders/delta', mailfolders, suffix="mail_folders_delta")
                self.add_route(user + '/mailFolders/{folderid}', mailfolders, suffix="mail_folder_by_id")
                self.add_route(user + '/mailFolders/{folderid}/childFolders', mailfolders, suffix="child_folders")
                self.add_route(user + '/mailFolders/{folderid}/childFolders/{childid}',
                               mailfolders, suffix="child_folder_by_id")

                self.add_route(user + '/sendMail', users, suffix="sendMail")

                self.add_route(user + '/mailFolders/{folderid}/copy', mailfolders, suffix="copy_folder")
                self.add_route(user + '/mailFolders/{folderid}/move', mailfolders, suffix="move_folder")

                self.add_route(user + '/messages', messages, suffix="messages")
                self.add_route(user + '/messages/{itemid}', messages, suffix="message_by_itemid")
                self.add_route(user + '/mailFolders/{folderid}/messages', messages, suffix="messages_by_folderid")
                self.add_route(user + '/mailFolders(\'{folderid}\')/messages',
                               messages, suffix="messages_by_folderid")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}',
                               messages, suffix="message_by_folderid")

                # Message attachments
                self.add_route(user + '/messages/{itemid}/attachments',
                               attachments, suffix="by_id")
                self.add_route(user + '/messages/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/messages/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_in_folder_by_id")

                # Message $value.
                self.add_route(user + '/messages/{itemid}/$value', messages, suffix="value")
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}/$value',
                    messages, suffix="value"
                )

                # Message item.
                self.add_route(
                    user + '/messages/{itemid}',
                    messages, suffix="item"
                )
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}',
                    messages, suffix="item"
                )

                # Message copy.
                self.add_route(
                    user + '/messages/{itemid}/copy',
                    messages, suffix="copy"
                )
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}/copy',
                    messages, suffix="copy"
                )

                # Message move.
                self.add_route(
                    user + '/messages/{itemid}/move',
                    messages, suffix="move"
                )
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}/move',
                    messages, suffix="move"
                )

                # Message createReply.
                self.add_route(
                    user + '/messages/{itemid}/createReply',
                    messages, suffix="createReply"
                )
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}/createReply',
                    messages, suffix="createReply"
                )

                # Message createReplyAll.
                self.add_route(
                    user + '/messages/{itemid}/createReplyAll',
                    messages, suffix="createReplyAll"
                )
                self.add_route(
                    user + '/mailFolders/{folderid}/messages/{itemid}/createReplyAll',
                    messages, suffix="createReplyAll"
                )

        calendar = default_backend.get('calendar')
        reminder = default_backend.get('reminder')
        if calendar:
            calendars = BackendResource(calendar, 'CalendarResource')
            reminders = BackendResource(reminder, 'ReminderResource')
            events = BackendResource(calendar, 'EventResource')
            attachments = BackendResource(calendar, 'AttachmentResource')

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/calendar', calendars, suffix="calendar")
                self.add_route(user + '/calendars', calendars, suffix="calendars")
                self.add_route(user + '/calendars/{folderid}',
                               calendars, suffix="calendar_by_folderid")

                self.add_route(user + '/events', events, suffix="events")
                self.add_route(user + '/events/{itemid}', events, suffix="by_eventid")
                self.add_route(user + '/events/{itemid}/accept', events, suffix="accept_event")
                self.add_route(user + '/events/{itemid}/decline', events, suffix="decline_event")
                self.add_route(user + '/events/{itemid}/instances', events, suffix="instances")

                self.add_route(user + '/calendar/events', events, suffix="events")
                self.add_route(user + '/calendar/events/{itemid}', events, suffix="by_eventid")
                self.add_route(user + '/calendar/events/{itemid}/accept', events, suffix="accept_event")
                self.add_route(user + '/calendar/events/{itemid}/decline', events, suffix="decline_event")
                self.add_route(user + '/calendar/events/{itemid}/instances', events, suffix="instances")

                self.add_route(user + '/calendars/{folderid}/events', events, suffix="by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/accept', events,
                               suffix="accept_event_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/decline', events,
                               suffix="decline_event_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/instances', events,
                               suffix="instances_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}', events, suffix="by_folderid_eventid")

                # Event attachments
                self.add_route(user + '/events/{itemid}/attachments',
                               attachments, suffix="by_id")
                self.add_route(user + '/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")

                self.add_route(user + '/calendar/events/{itemid}/attachments',
                               attachments, suffix="by_id")
                self.add_route(user + '/calendar/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/calendar/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")

                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_in_folder_by_id")

                self.add_route(user + '/calendars/{folderid}/calendarView', calendars,
                               suffix="calendar_view_by_folderid")
                self.add_route(user + '/calendarView', calendars, suffix="calendar_view")
                self.add_route(user + '/reminderView', reminders, suffix="reminder_view")

        notification = default_backend.get('notification')
        if notification:
            subscription_resource = BackendResource(notification, 'SubscriptionResource')

            self.add_route(PREFIX + '/subscriptions', subscription_resource)
            self.add_route(PREFIX + '/subscriptions/{subscriptionid}',
                           subscription_resource, suffix="subscriptions_by_id")

    def initialize_backends_error_handlers(self):
        """Call 'initialize_error_handlers' for all backends to setup erorr handlers.
        Should be called after the generic Exception handler has been set up.
        """
        for name in self.backends:
            backend = self.import_backend(name)
            if hasattr(backend, 'initialize_error_handlers'):
                backend.initialize_error_handlers(self)
