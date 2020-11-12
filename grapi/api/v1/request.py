# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

if falcon.__version__.startswith("1."):
    from .context import Context
else:
    from falcon import Context


class Request(falcon.request.Request):
    context_type = Context
