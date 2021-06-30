# SPDX-License-Identifier: AGPL-3.0-or-later

from .utils import _header_args

_marker = {}


class Prefer:
    def __init__(self, req):
        self._prefer = _header_args(req, 'Prefer')
        self._parsed = {}
        self._applied = {}

    def get(self, name, default=None, raw=False, apply=True):
        if not raw:
            v = self._parsed.get(name, _marker)
            if v is _marker:
                return default
            if apply:
                self.applied(name)
            return v
        else:
            v = self._prefer.get(name, _marker)
            if v is _marker:
                return default
            return v.strip('"')  # TODO(longsleep): Find out if the strip is needed and why.

    def update(self, name, value):
        self._parsed[name] = value

    def applied(self, name):
        self._applied[name] = True

    def set_headers(self, resp):
        if self._applied:
            resp.set_header('Preference-Applied', ','.join(name for name in self._applied))
