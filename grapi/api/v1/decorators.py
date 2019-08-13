# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon
import logging

def experimental(f, *args, **kwargs):
    def _experimental(req, resp, resource, params):
        if not resource.options.with_experimental:
            logging.debug('incoming request to disabled experimental endpoint: %s', req.path)
            raise falcon.HTTPNotFound()

    return falcon.before(_experimental, *args, **kwargs)(f)
