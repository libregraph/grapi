# SPDX-License-Identifier: AGPL-3.0-or-later

import falcon


class HealthCheckResource:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
