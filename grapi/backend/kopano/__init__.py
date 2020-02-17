# SPDX-License-Identifier: AGPL-3.0-or-later

import kopano

from .user import UserResource  # noqa: F401
from .group import GroupResource  # noqa: F401
from .message import MessageResource  # noqa: F401
from .attachment import AttachmentResource  # noqa: F401
from .mailfolder import MailFolderResource  # noqa: F401
from .contactfolder import ContactFolderResource  # noqa: F401
from .calendar import CalendarResource  # noqa: F401
from .event import EventResource  # noqa: F401
from .contact import ContactResource  # noqa: F401
from .profilephoto import ProfilePhotoResource  # noqa: F401
from .subscription import SubscriptionResource  # noqa: F401

kopano.set_bin_encoding('base64')
kopano.set_missing_none()
# TODO set_timezone_aware?


def initialize(options):
    '''Backend initialize function, should be called only once.'''
    from .utils import SessionPurger

    SessionPurger(options).start()
