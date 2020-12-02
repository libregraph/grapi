# SPDX-License-Identifier: AGPL-3.0-or-later

from grapi.api.v1.resource import Resource

from .message import MessageResource  # noqa: F401
from .user import UserResource  # noqa: F401

GroupResource = Resource
ContactFolderResource = Resource
ContactResource = Resource
ProfilePhotoResource = Resource
