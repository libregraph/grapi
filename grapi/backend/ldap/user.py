# SPDX-License-Identifier: AGPL-3.0-or-later

import codecs
import json
import os

import ldap
from ldap.controls import SimplePagedResultsControl

from .resource import Resource

PAGESIZE = 1000
ldap.set_option(ldap.OPT_REFERRALS, 0)
ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

class UserResource(Resource):
    l = None

    uri = "ldap://127.0.0.1:389"
    baseDN = ""
    bindDN = None
    bindPW = None

    searchScope = ldap.SCOPE_SUBTREE
    searchFilter = "(objectClass=inetOrgPerson)"

    useridSearchFilterTemplate = "(uid=%(userid)s)"
    searchSearchFilterTemplate = "(|(mail=*%(search)s*)(givenName=*%(search)s*)(sn=*%(search)s*))"

    retryMax = 3
    retryDelay = 1.0

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

    def __init__(self, options):
        Resource.__init__(self, options)

        self.uri = os.getenv("LDAP_URI")
        self.baseDN = os.getenv("LDAP_BASEDN")
        self.bindDN = os.getenv("LDAP_BINDDN")
        self.bindPW = os.getenv("LDAP_BINDPW")

        if not self.uri or  not self.baseDN:
            raise RuntimeError("missing LDAP_URI or LDAP_BASEDN in environment")

        self.l = ldap.ldapobject.ReconnectLDAPObject(self.uri, retry_max=self.retryMax, retry_delay=self.retryDelay)
        if self.bindDN is not None and self.bindPW is not None:
            self.l.simple_bind_s(self.bindDN, self.bindPW)

    def on_get(self, req, resp, userid=None, method=None):
        l = self.l

        value = []

        searchFilter = self.searchFilter
        size = PAGESIZE
        top = 10
        end = top
        count = 0
        skip = 0
        if userid:
            searchFilter = "(&" + searchFilter + (self.useridSearchFilterTemplate % {"userid": userid}) + ")"
        else:
            args = self.parse_qs(req)
            top = int(args.get('$top', [top])[0])
            skip = int(args.get('$skip', [skip])[0])
            search = args.get('$search', [None])[0]
            if search:
                searchFilter = "(&" + searchFilter + (self.searchSearchFilterTemplate % {"search": search}) + ")"
            end = top + skip
            if end < size:
                size = end

        lc = SimplePagedResultsControl(True, size=size, cookie='')
        while True:
            msgid = l.search_ext(
                self.baseDN,
                self.searchScope,
                searchFilter,
                ['objectClass', 'cn', 'mail', 'uid', 'givenName', 'sn', 'title'],
                serverctrls=[lc]
            )

            rtype, rdata, rmsgid, serverctrls = l.result3(msgid, all=1)

            for dn, attrs in rdata:
                count += 1
                if skip and count <= skip:
                    continue
                if b'inetOrgPerson' in attrs['objectClass']:
                    cn = codecs.decode(attrs['cn'][0], 'utf-8')
                    mail = codecs.decode(attrs['mail'][0], 'utf-8')
                    uid = codecs.decode(attrs['uid'][0], 'utf-8')
                    givenName = codecs.decode(attrs['givenName'][0], 'utf-8')
                    sn = codecs.decode(attrs['sn'][0], 'utf-8')
                    title = codecs.decode(attrs['title'][0], 'utf-8')
                    d = {x: '' for x in self.fields}
                    d.update({
                        'displayName': cn,
                        'mail': mail,
                        'id': uid,
                        'userPrincipalName': uid,
                        'surname': sn,
                        'givenName': givenName,
                        'title': title,
                    })
                    value.append(d)
                if end and count >= end:
                    break

            if end and count >= end:
                break

            pctrls = [c for c in serverctrls if c.controlType == SimplePagedResultsControl.controlType]
            if not pctrls:
                break

            cookie = pctrls[0].cookie
            if not cookie:
                break
            lc.cookie = cookie

        if userid:
            data = value[0]
        else:
            data = {
                '@odata.context': '/api/gc/v1/users',
                'value': value,
            }
            if len(value) >= top:
                data['@odata.nextLink'] = '/api/gc/v1/users?$skip=%d' % (top + skip)

        resp.content_type = "application/json"
        resp.body = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8') # TODO stream
