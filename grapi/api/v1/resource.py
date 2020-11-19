# SPDX-License-Identifier: AGPL-3.0-or-later

import html
from urllib.parse import parse_qs, quote, urlencode

import falcon
from jsonschema import ValidationError

try:
    import ujson as json
    UJSON = True
except ImportError:  # pragma: no cover
    UJSON = False
    import json

INDENT = True
try:
    json.dumps({}, indent=True)  # ujson 1.33 doesn't support 'indent'
except TypeError:  # pragma: no cover
    INDENT = False


def _parse_qs(req):
    args = parse_qs(req.query_string)
    for arg, values in args.items():
        if len(values) > 1:
            raise HTTPBadRequest("Query option '%s' was specified more than once, but it must be specified at most once." % arg)

    for key in ('$top', '$skip'):
        if key in args:
            value = args[key][0]
            if not value.isdigit():
                raise HTTPBadRequest("Invalid value '%s' for %s query option found. The %s query option requires a non-negative integer value." % (value, key, key))

    return args


def _encode_qs(query):
    return urlencode(query, doseq=True, encoding='utf-8', safe='$', quote_via=quote)


def _loadb_json(b, *args, **kwargs):
    return json.loads(b.decode('utf-8'), *args, **kwargs)


def _dumpb_json(obj, *args, **kwargs):
    if INDENT:
        kwargs.setdefault('indent', 2)
    else:
        kwargs.pop('indent', None)
    if UJSON:
        kwargs.setdefault('escape_forward_slashes', False)
    kwargs.setdefault('ensure_ascii', False)

    return json.dumps(obj, *args, **kwargs).encode('utf-8')


class HTTPBadRequest(falcon.HTTPBadRequest):
    def __init__(self, msg):
        msg = html.escape(msg)
        super().__init__(title=None, description=msg)


class HTTPConflict(falcon.HTTPConflict):

    def __init__(self, msg):
        msg = html.escape(msg)
        super().__init__(title=None, description=msg)



class Resource:
    def __init__(self, options):
        self.options = options

    def parse_qs(self, req):
        return _parse_qs(req)

    def respond_204(self, resp):  # TODO integrate with respond, status_code=..?
        resp.set_header('Content-Length', '0')  # https://github.com/jonashaag/bjoern/issues/139
        resp.status = falcon.HTTP_204

    def load_json(self, req):
        try:
            return _loadb_json(req.stream.read())
        except ValueError:
            raise HTTPBadRequest("Invalid JSON")

    def validate_json(self, schema, fields):
        try:
            schema.validate(fields)
        except ValidationError as e:
            raise HTTPBadRequest("JSON schema violation: %s " % e.message)

    def respond_json(self, resp, data):
        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(data, indent=2)
