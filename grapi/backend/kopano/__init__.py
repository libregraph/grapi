# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

import kopano
import kopano.log

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

# Python Kopano has some wild logger with default behavior. We do not want it
# to do stuff, so remove all handers.
logger = kopano.log.LOG
for handler in logger.handlers:
    logger.removeHandler(handler)


def initialize(options):
    '''Backend initialize function, should be called only once.'''
    log_level = options.log_level if options else 'INFO'
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logger.setLevel(numeric_level)

    from .utils import SessionPurger

    SessionPurger(options).start()
