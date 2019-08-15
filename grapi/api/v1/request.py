# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

from .context import Context


class Request(falcon.request.Request):
    context_type = Context
