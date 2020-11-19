# SPDX-License-Identifier: AGPL-3.0-or-later
import calendar
import codecs
import datetime

import dateutil

from .resource import DEFAULT_TOP, Resource, _date
from .utils import db_get, db_put, experimental


def get_body(req, item):
    prefer_body_content_type = req.context.prefer.get('outlook.body-content-type')

    if prefer_body_content_type == 'text':
        return {'contentType': 'text', 'content': item.text}
    else:
        return {'contentType': 'html', 'content': codecs.decode(item.html_utf8, 'utf-8')}  # TODO can we use bytes to avoid recoding?


def set_body(item, arg):
    if arg['contentType'] == 'text':
        item.text = arg['content']
    elif arg['contentType'] == 'html':
        item.html = arg['content'].encode('utf8')


def get_email(addr):
    return {'emailAddress': {'name': addr.name, 'address': addr.email}}


class DeletedItem(object):
    pass


class ItemImporter:
    def __init__(self):
        self.updates = []
        self.deletes = []

    def update(self, item, flags):
        self.updates.append(item)
        db_put(item.sourcekey, item.entryid)

    def delete(self, item, flags):
        d = DeletedItem()
        d.entryid = db_get(item.sourcekey)
        self.deletes.append(d)


class ItemResource(Resource):
    fields = {
        '@odata.etag': lambda item: 'W/"'+item.changekey+'"',
        'id': lambda item: item.entryid,
        'changeKey': lambda item: item.changekey,
        'createdDateTime': lambda item: _date(item.created),
        'lastModifiedDateTime': lambda item: _date(item.last_modified),
        'categories': lambda item: item.categories,
    }

    @experimental
    def delta(self, req, resp, folder):
        args = self.parse_qs(req)
        token = args['$deltatoken'][0] if '$deltatoken' in args else None
        filter_ = args['$filter'][0] if '$filter' in args else None
        begin = None
        if filter_ and filter_.startswith('receivedDateTime ge '):
            begin = dateutil.parser.parse(filter_[20:])
            seconds = calendar.timegm(begin.timetuple())
            begin = datetime.datetime.utcfromtimestamp(seconds)
        importer = ItemImporter()
        newstate = folder.sync(importer, token, begin=begin)
        changes = [(o, self) for o in importer.updates] + \
            [(o, self.deleted_resource) for o in importer.deletes]
        data = (changes, DEFAULT_TOP, 0, len(changes))
        # TODO include filter in token?
        deltalink = b"%s?$deltatoken=%s" % (req.path.encode('utf-8'), codecs.encode(newstate, 'ascii'))
        self.respond(req, resp, data, self.fields, deltalink=deltalink)
