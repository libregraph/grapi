# SPDX-License-Identifier: AGPL-3.0-or-later
from .version import __version__

import falcon

from .api_v1.rest import RestAPI
from .api_v1.notify import NotifyAPI
