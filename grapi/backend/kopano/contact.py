# SPDX-License-Identifier: AGPL-3.0-or-later

from .item import ItemResource, get_email2
from .resource import _date
from .utils import HTTPBadRequest, _folder, _item, _server_store, experimental


def set_email_addresses(item, arg):  # TODO multiple via pyko
    item.address1 = '%s <%s>' % (arg[0]['name'], arg[0]['address'])


def _phys_address(addr):
    data = {
        'street': addr.street,
        'city': addr.city,
        'postalCode': addr.postal_code,
        'state': addr.state,
        'countryOrRegion': addr.country
    }
    return {a: b for (a, b) in data.items() if b}


class DeletedContactResource(ItemResource):
    fields = {
        '@odata.type': lambda item: '#microsoft.graph.contact',  # TODO
        'id': lambda item: item.entryid,
        '@removed': lambda item: {'reason': 'deleted'}  # TODO soft deletes
    }


@experimental
class ContactResource(ItemResource):
    fields = ItemResource.fields.copy()
    fields.update({
        'displayName': lambda item: item.name,
        'emailAddresses': lambda item: [get_email2(a) for a in item.addresses()],
        'parentFolderId': lambda item: item.folder.entryid,
        'givenName': lambda item: item.first_name or None,
        'middleName': lambda item: item.middle_name or None,
        'surname': lambda item: item.last_name or None,
        'nickName': lambda item: item.nickname or None,
        'title': lambda item: item.title or None,
        'companyName': lambda item: item.company_name or None,
        'mobilePhone': lambda item: item.mobile_phone or None,
        'personalNotes': lambda item: item.text,
        'generation': lambda item: item.generation or None,
        'children': lambda item: item.children,
        'spouseName': lambda item: item.spouse or None,
        'birthday': lambda item: item.birthday and _date(item.birthday) or None,
        'initials': lambda item: item.initials or None,
        'yomiGivenName': lambda item: item.yomi_first_name or None,
        'yomiSurname': lambda item: item.yomi_last_name or None,
        'yomiCompanyName': lambda item: item.yomi_company_name or None,
        'fileAs': lambda item: item.file_as,
        'jobTitle': lambda item: item.job_title or None,
        'department': lambda item: item.department or None,
        'officeLocation': lambda item: item.office_location or None,
        'profession': lambda item: item.profession or None,
        'manager': lambda item: item.manager or None,
        'assistantName': lambda item: item.assistant or None,
        'businessHomePage': lambda item: item.business_homepage or None,
        'homePhones': lambda item: item.home_phones,
        'businessPhones': lambda item: item.business_phones,
        'imAddresses': lambda item: item.im_addresses,
        'homeAddress': lambda item: _phys_address(item.home_address),
        'businessAddress': lambda item: _phys_address(item.business_address),
        'otherAddress': lambda item: _phys_address(item.other_address),
    })

    set_fields = {
        'displayName': lambda item, arg: setattr(item, 'name', arg),
        'emailAddresses': set_email_addresses,
    }

    deleted_resource = DeletedContactResource

    def handle_get(self, req, resp, store, server, folderid, itemid):
        folder = _folder(store, folderid or 'contacts')  # TODO all folders?

        if itemid:
            if itemid == 'delta':
                self._handle_get_delta(req, resp, folder=folder)
            else:
                self._handle_get_with_itemid(req, resp, folder=folder, itemid=itemid)
        else:
            raise HTTPBadRequest("Missing contact itemid")

    def _handle_get_delta(self, req, resp, folder):
        req.context.deltaid = '{itemid}'
        self.delta(req, resp, folder)

    def _handle_get_with_itemid(self, req, resp, folder, itemid):
        data = _item(folder, itemid)
        self.respond(req, resp, data)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_get
        else:
            raise HTTPBadRequest("Unsupported contact segment '%s'" % method)

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, server=server, folderid=folderid, itemid=itemid)

    def handle_delete(self, req, resp, store, server, folderid, itemid):
        item = _item(store, itemid)

        store.delete(item)

        self.respond_204(resp)

    def on_delete(self, req, resp, userid=None, folderid=None, itemid=None):
        handler = self.handle_delete

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, server=server, folderid=folderid, itemid=itemid)
