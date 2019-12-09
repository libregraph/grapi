# SPDX-License-Identifier: AGPL-3.0-or-later

import json

import ldap
from ldap.controls import SimplePagedResultsControl

from grapi.backend.ldap import Resource
from .utils import _get_from_env, _get_ldap_attr_value

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
    searchFilter = None

    useridSearchFilterTemplate = None
    searchSearchFilterTemplate = None

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

        self.uri = _get_from_env("LDAP_URI", None)
        self.baseDN = _get_from_env("LDAP_BASEDN", None)
        self.bindDN = _get_from_env("LDAP_BINDDN", None)
        self.bindPW = _get_from_env("LDAP_BINDPW", "")
        self.searchFilter = _get_from_env("LDAP_FILTER", "(objectClass=inetOrgPerson)")
        self.useridSearchFilterTemplate = _get_from_env("LDAP_LOGIN_ATTRIBUTE_FILTER_TEMPLATE", "(uid=%(userid)s)")
        self.searchSearchFilterTemplate = _get_from_env("LDAP_SEARCH_FILTER_TEMPLATE", "(|(mail=*%(search)s*)(givenName=*%(search)s*)(sn=*%(search)s*))")

        if not self.searchFilter or not self.useridSearchFilterTemplate or not self.searchSearchFilterTemplate:
            raise RuntimeError("filters must not be empty - check environment")

        if not self.uri or not self.baseDN:
            raise RuntimeError("missing LDAP_URI or LDAP_BASEDN in environment")

        try:
            self.l = ldap.ldapobject.ReconnectLDAPObject(self.uri, retry_max=self.retryMax, retry_delay=self.retryDelay)
        except ldap.LDAPError as e:
            print("unable to connect to LDAP server", e)

        if self.bindDN is not None:
            try:
                self.l.simple_bind_s(self.bindDN, self.bindPW)
            except ldap.INVALID_CREDENTIALS as e:
                print("invalid LDAP credentials", e)

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

                try:
                    uid = _get_ldap_attr_value(attrs, 'uid')
                except KeyError:
                    # Ignore entries which have no uid.
                    continue
                cn = _get_ldap_attr_value(attrs, 'cn', '')
                mail = _get_ldap_attr_value(attrs, 'mail', '')
                givenName = _get_ldap_attr_value(attrs, 'givenName', '')
                sn = _get_ldap_attr_value(attrs, 'sn', '')
                title = _get_ldap_attr_value(attrs, 'title', '')
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
        resp.body = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')  # TODO stream
