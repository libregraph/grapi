# CHANGELOG

## Unreleased

- Add changelog
- Document prometheus metrics
- Fix argparse for metrics_listen
- Add responseStatus to EventResource
- mock: remove debug print
- event: handle item not found in a generic way
- Catch invalid values when looking up users by id/name
- Log unhandled exception with specific message
- Add unit test framework for grapi
- mfr: use argparse instead of deprecated optparse
- kopano: handle not found and invalid entryid exceptions
- Relax python setup.py install dependencies
- Fixup typos and clarify some details


## v9.0.2 (2019-03-20)

- avoid except-all an general _server_store function
- grapi: add mock backend for testing
- grapi: create a general Resource object
- Document how to run grapi using the devrunner
- scripts: make backends configurable for devrunner
- ldap remove try/except for Python 2 and 3 compatibility
- Document backends and how to configure them
- imap: make the imap server url configurable
- caldav: make caldav server configurable via env var
- ldap: remove unused import codecs
- ldap: Add error handling to LDAP binding
- kopano: Fix json schema validation for body
- Revert "pyko: replace all ext calls to Server() with server()"
- Relax jsonschema schema version requirement
- Add Jenkinsfile integration


## v9.0.1 (2019-03-14)

- Strip newline version


## v9.0.0 (2019-03-14)

- kopano: Set end date in API for recurrences
- kopano: make dayOfMonth optional
- Add bin script, config and systemd service
- Add requirements and install_requires with versions where useful
- Add license section
- Reformat markdown
- Get version number from git or .version file
- Update README
- Add helper script to start mfr
- support /users/userprincipalname next to userid
- fix doc links


## v0.1.0 (2019-02-25)

- Fix typo
- Use robust LDAP attribute lookup
- Add search for users endpoint in LDAP backend
- Auto reconnect LDAP when connection was lost/broken
- Hack in top and skip parametrs to users LDAP
- Return LDAP backend get data as UTF-8 encoded JSON
- Add LDAP backend settings and pagination

