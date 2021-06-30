# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging

import ldap
from ldap.controls import SimplePagedResultsControl

from grapi.api.v1.resource import HTTPBadRequest
from grapi.backend.ldap import Resource

from .utils import _get_from_env, _get_ldap_attr_value

PAGESIZE = 1000
ldap.set_option(ldap.OPT_REFERRALS, 0)
ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

USERID_SEARCH_FILTER_TEMPLATE = "({loginAttribute}=%(userid)s)"
SEARCH_SEARCH_FILTER_TEMPLATE = "(|({emailAttribute}=*%(search)s*)({givenNameAttribute}=*%(search)s*)({familyNameAttribute}=*%(search)s*))"


class UserResource(Resource):
    ldap_obj = None

    uri = "ldap://127.0.0.1:389"
    baseDN = ""
    bindDN = None
    bindPW = None

    searchScope = ldap.SCOPE_SUBTREE
    searchFilter = "(objectClass=inetOrgPerson)"

    attributeMapping = None
    searchFields = []
    useridSearchFilterTemplate = None
    searchSearchFilterTemplate = None

    retryMax = 3
    retryDelay = 1.0

    def __init__(self, options):
        Resource.__init__(self, options)

        self.uri = _get_from_env("LDAP_URI", None)
        self.baseDN = _get_from_env("LDAP_BASEDN", None)
        self.bindDN = _get_from_env("LDAP_BINDDN", None)
        self.bindPW = _get_from_env("LDAP_BINDPW", "")

        self.attributeMapping = {
            'loginAttribute': 'uid',
            'emailAttribute': 'mail',
            'nameAttribute': 'cn',
            'familyNameAttribute': 'sn',
            'givenNameAttribute': 'givenName',
            'jobTitleAttribute': 'title',
            'officeLocationAttribute': 'l',
            'businessPhoneAttribute': 'telephoneNumber',
            'mobilePhoneAttribute': 'mobile',
        }
        self.attributeMapping['loginAttribute'] = _get_from_env("LDAP_LOGIN_ATTRIBUTE", self.attributeMapping['loginAttribute'])
        self.attributeMapping['emailAttribute'] = _get_from_env("LDAP_EMAIL_ATTRIBUTE", self.attributeMapping['emailAttribute'])
        self.attributeMapping['nameAttribute'] = _get_from_env("LDAP_NAME_ATTRIBUTE", self.attributeMapping['nameAttribute'])
        self.attributeMapping['familyNameAttribute'] = _get_from_env("LDAP_FAMILY_NAME_ATTRIBUTE", self.attributeMapping['familyNameAttribute'])
        self.attributeMapping['givenNameAttribute'] = _get_from_env("LDAP_GIVEN_NAME_ATTRIBUTE", self.attributeMapping['givenNameAttribute'])
        self.attributeMapping['jobTitleAttribute'] = _get_from_env("LDAP_JOB_TITLE_ATTRIBUTE", self.attributeMapping['jobTitleAttribute'])
        self.attributeMapping['officeLocationAttribute'] = _get_from_env("LDAP_OFFICE_LOCATION_ATTRIBUTE", self.attributeMapping['officeLocationAttribute'])
        self.attributeMapping['businessPhoneAttribute'] = _get_from_env("LDAP_BUSINESS_PHONE_ATTRIBUTE", self.attributeMapping['businessPhoneAttribute'])
        self.attributeMapping['mobilePhoneAttribute'] = _get_from_env("LDAP_MOBILE_PHONE_ATTRIBUTE", self.attributeMapping['mobilePhoneAttribute'])

        self.searchFields = [
            'objectClass',
        ].extend(self.attributeMapping.values())

        searchScope = _get_from_env("LDAP_SCOPE", "sub")
        if searchScope == "sub":
            self.searchScope = ldap.SCOPE_SUBTREE
        elif searchScope == "base":
            self.searchSCope = ldap.SCOPE_BASE
        elif searchScope == "onelevel":
            self.searchScope = ldap.SCOPE_ONELEVEL
        else:
            raise RuntimeError("unknown LDAP_SCOPE in environment")

        self.searchFilter = _get_from_env("LDAP_FILTER", self.searchFilter)
        self.useridSearchFilterTemplate = _get_from_env("LDAP_LOGIN_ATTRIBUTE_FILTER_TEMPLATE", USERID_SEARCH_FILTER_TEMPLATE).format(**self.attributeMapping)
        self.searchSearchFilterTemplate = _get_from_env("LDAP_SEARCH_FILTER_TEMPLATE", SEARCH_SEARCH_FILTER_TEMPLATE).format(**self.attributeMapping)

        if not self.searchFilter or not self.useridSearchFilterTemplate or not self.searchSearchFilterTemplate:
            raise RuntimeError("filters must not be empty - check environment")

        if not self.uri or not self.baseDN:
            raise RuntimeError("missing LDAP_URI or LDAP_BASEDN in environment")

        try:
            self.ldap_obj = ldap.ldapobject.ReconnectLDAPObject(self.uri, retry_max=self.retryMax, retry_delay=self.retryDelay)
        except ldap.LDAPError:
            logging.error("unable to connect to LDAP server", exc_info=True)

        if self.bindDN is not None:
            try:
                self.ldap_obj.simple_bind_s(self.bindDN, self.bindPW)
            except ldap.LDAPError as excinfo:
                logging.error("unable to authenticate with LDAP server: %s" % excinfo)

    def on_get(self, req, resp, userid=None, method=None):
        if method:
            raise HTTPBadRequest("Unsupported user segment '%s'" % method)

        if not userid and req.path.split('/')[-1] != 'users':
            userid = req.get_header('X-Kopano-Username', None)
            if not userid:
                raise HTTPBadRequest('No user')

        ldap_obj = self.ldap_obj

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
            msgid = ldap_obj.search_ext(
                self.baseDN,
                self.searchScope,
                searchFilter,
                self.searchFields,
                serverctrls=[lc]
            )

            rtype, rdata, rmsgid, serverctrls = ldap_obj.result3(msgid, all=1)

            for _, attrs in rdata:
                count += 1
                if skip and count <= skip:
                    continue

                try:
                    uid = _get_ldap_attr_value(attrs, self.attributeMapping['loginAttribute'])
                except KeyError:
                    # Ignore entries which have no login attribute.
                    continue
                cn = _get_ldap_attr_value(attrs, self.attributeMapping['nameAttribute'], '')
                mail = _get_ldap_attr_value(attrs, self.attributeMapping['emailAttribute'], '')
                givenName = _get_ldap_attr_value(attrs, self.attributeMapping['givenNameAttribute'], '')
                sn = _get_ldap_attr_value(attrs, self.attributeMapping['familyNameAttribute'], '')
                jobTitle = _get_ldap_attr_value(attrs, self.attributeMapping['jobTitleAttribute'], '')
                officeLocation = _get_ldap_attr_value(attrs, self.attributeMapping['officeLocationAttribute'], '')
                businessPhone = _get_ldap_attr_value(attrs, self.attributeMapping['businessPhoneAttribute'], '')
                mobilePhone = _get_ldap_attr_value(attrs, self.attributeMapping['mobilePhoneAttribute'], '')
                d = {
                    'displayName': cn,
                    'mail': mail,
                    'id': uid,
                    'userPrincipalName': uid,
                    'surname': sn,
                    'givenName': givenName,
                    'jobTitle': jobTitle,
                    'officeLocation': officeLocation,
                    'businessPhone': businessPhone,
                    'mobilePhone': mobilePhone,
                }
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

        if userid and value:
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
