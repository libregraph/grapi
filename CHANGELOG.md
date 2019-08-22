# CHANGELOG

## Unreleased



## v10.0.0 (2019-08-22)

- Allow to enable experimental endpoints in config
- Fix typos in README
- Include individual mapi version
- Add additional parameters to resource error handler
- Only trigger send for new calendar events when there are attendees
- Add backend error handling hook
- Raise 404 when there is no store
- Cache connections by token
- Use correct pytest executable
- Improve session purging timeouts
- Add log when subscription creates new server connections
- Improve logging and not found handling
- Remove session store/restore in favour of memory cache of connections
- Catch more errors when trying to resume sessions
- Improve kopano session caching and add logging and metrics
- Ignore experimental backends in linting for now
- Fixup more linter errors
- Switch to flake8 for linting
- Fixup more linter errors
- Increase allowed line length
- Use pylint3 by default
- Fixup linter errors
- Disable experimental API endpoints by default
- Avoid returning bogus birthday for contacts without set birthday date
- Fix JSON encoding of nextLink when streaming
- Add missing handlers to avoid empty returns or other unexpected errors
- Fixup JSON marshal error/exception logging
- Make optional event setter fields actually optional
- Add windows timezone name support
- Ensure we have working photo support
- Use Ubuntu 18.04 in Jenkins for testing
- Fixup local time conversion


## v9.2.1 (2019-08-06)

- Add tox ini for pep8 settings
- Update code style for pep8
- Avoid global user connection in kopano subscriptions
- re-order imports stdlib first then third party
- remove unused import traceback
- Remove try/except for Python 2 support
- Add prometheus memory statistics per process
- Add Docker swarm instructions/example
- Add metrics support to Dockerfile
- Add Dockerfile build args
- Add Docker instructions to README
- Install optional dependencies too
- Add simple health check using curl
- Add Docker container to run grapi in production
- Fixup Jenkins
- Ensure to clean workspace


## v9.2.0 (2019-07-25)

- kopano: add onlineMeetingUrl field support
- Improve error handling
- Properly count active subscriptions and expirations
- Improve exception handling and logging in threads
- Add automatic cleanup of expired subscriptions


## v9.1.0 (2019-06-27)

- v9.1.0
- Ignore vim swp files
- Handle MAPIErrorNoSupport on subscribe
- Only include seriesMasterId when event is recurring
- Export newly created subscription without private fields
- Improve subscription logging and reconnect logic
- Log subscription exteptions and reconnects
- Add missing reconnect parameter
- Remove more invalid implicit and explicit localtime conversions
- Add support to update subscriptions
- Add note about tzinfo in non-recurring events
- Use events tzinfo when available for event start/end datetime
- Pass datetime as localtime to/from pyko
- Use timezone data from incoming data
- Remove wrong conversion from local time
- Freeze falcon to 1.4.1 until we support 2.0
- test: Add integration for Kopano backend
- Add PYTEST_OPTIONS for setting pytest options
- Create structure for integration tests
- kopano: catch exception in json_multi
- grapi: kopano: handle 500 on event creation
- Use HTTPBadRequest from grapi.api.v1.resource
- Add unhandled exceptions as prometheus counter
- Handle exception when no auth headers are send
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


## v9.0.0a1 (2019-03-14)

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

