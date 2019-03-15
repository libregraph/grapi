# Kopano GRAPI

Kopano GRAPI provides a general REST web service for multiple groupware
applications/standards. It aims to be largely compatible with Microsoft Graph.
See `COMPAT.MD` for compatibility details.

GRAPI is meant to be used directly by for Kopano API and requires Python 3.

## Running GRAPI MFR

MFR stands for Master Fleet Runner and starts the WSGI services provided by
GRAPI in a way that they can be consumed using unix sockets. To achieve best
scalability, MFR starts multiple instances of its services so they can be
utilized in parallel.

```
./mfr.py
```

MFR behaviour can be controlled using commandline parameters. Use
`./mfr.py --help` to get the details.

## Development

GRAPI consists of separate WSGI applications. Mfr runs them together, in a
scalable way to be picked up by Kopano API. Recommended way to develop is to
run GRAPI together with Kopano API.

During development, it is sometimes easier to use the applications directly,
and without needing access tokens (so using basic authentication). To do that
use the `--enable-auth-basic` and start the WSGI applications directly for
example using gunicorn:

```
gunicorn3 'grapi.api.v1:RestAPI()'
gunicorn3 'grapi:api.v1:NotifyAPI()'
```

## Backends

The Kopano backend is currently the most tested and supported backend for mail,
calendar and directory information. Other backends are LDAP, CalDAV and
IMAP should be treated as experimental and can be run simultaneous where
for example mail is provided by the IMAP backend and calendar by the CalDAV
backend.

### LDAP backend

The ldap backend requires two environment variables to be set:

* LDAP_URI - the ldap uri
* LDAP_BASEDN - the base dn

If the LDAP server needs authentication for listing users the following
environment variables should be set:

* LDAP_BINDDN
* LDAP_BINDPW

#### Dependencies

* python-ldap

### Caldav backend

The caldav backend requires three environment variables to be set:

* CALDAV_SERVER - the caldav server url
* GRAPI_USER - the caldav user
* GRAPI_PASSWORD - the caldav password

#### Dependencies

* python-vobject
* python-caldav

### IMAP Backend

The IMAP backend only supports IMAP over SSL/TLS and requires three environment
variables to be set:

* IMAP_SERVER - the IMAP server url
* GRAPI_USER - the IMAP user
* GRAPI_PASSWORD - the IMAP password

## License

See `LICENSE.txt` for licensing information of this project.
