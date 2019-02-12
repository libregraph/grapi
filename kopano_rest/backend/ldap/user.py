# SPDX-License-Identifier: AGPL-3.0-or-later

import codecs
import json
import os

import ldap

from .resource import Resource

HOST = 'ldaps://ldap.kopano.io:636'
USER = os.getenv('GRAPI_USER')
PASSWORD = os.getenv('GRAPI_PASSWORD')
BASE = 'dc=hoags,dc=org'
AUTH = 'uid=%s,ou=users,dc=hoags,dc=org' % USER

class UserResource(Resource):
    fields = {
        'id': lambda user: user.userid,
        'displayName': lambda user: user.fullname,
        'jobTitle': lambda user: user.job_title,
        'givenName': lambda user: user.first_name,
        'mail': lambda user: user.email,
        'mobilePhone': lambda user: user.mobile_phone,
        'officeLocation': lambda user: user.office_location,
        'surname': lambda user: user.last_name,
        'userPrincipalName': lambda user: user.name,
    }

    def on_get(self, req, resp, userid=None, method=None):
        l = ldap.initialize(HOST)
        l.simple_bind_s(AUTH, PASSWORD)

        value = []

        if userid:
            result = l.search(BASE, ldap.SCOPE_SUBTREE, '(uidNumber=%s)' % userid)
        else:
            result = l.search(BASE, ldap.SCOPE_SUBTREE, '(objectClass=kopano-user)')

        count = 0
        while 1:
            t, d = l.result(result, 0)
            if d == []:
                break
            else:
                if b'kopano-user' in d[0][1]['objectClass']:
                    name = codecs.decode(d[0][1]['cn'][0], 'utf-8')
                    mail = codecs.decode(d[0][1]['mail'][0], 'utf-8')
                    uidnum = codecs.decode(d[0][1]['uidNumber'][0], 'utf-8')
                    d = {x: '' for x in self.fields}
                    d.update({
                        'displayName': name,
                        'mail': mail,
                        'id': uidnum,
                    })
                    value.append(d)
                    count += 1
                    if count >= 10:
                        break

        if userid:
            data = value[0]
        else:
            data = {
                '@odata.context': '/api/gc/v1/users',
                '@odata.nextLink': '/api/gc/v1/users?$skip=10',
                'value': value,
            }

        resp.content_type = "application/json"
        resp.body = json.dumps(data, indent=2) # TODO stream
