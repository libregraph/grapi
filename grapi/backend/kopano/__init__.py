# SPDX-License-Identifier: AGPL-3.0-or-later

import kopano

from .user import UserResource
from .group import GroupResource
from .message import MessageResource
from .attachment import AttachmentResource
from .mailfolder import MailFolderResource
from .contactfolder import ContactFolderResource
from .calendar import CalendarResource
from .event import EventResource
from .contact import ContactResource
from .profilephoto import ProfilePhotoResource
from .subscription import SubscriptionResource

kopano.set_bin_encoding('base64')
kopano.set_missing_none()
# TODO set_timezone_aware?
