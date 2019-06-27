# CHANGELOG

## Unreleased



## v9.1.0 (2019-06-27)

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
- Add changelog
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


## v0.0.1 (2019-02-21)

- Add ARGS variable to dev make targets
- fix imports after recent refactoring, so tests run again
- Add license files
- Add basic Makefile for linting and dev helpers
- Remove obsolete shebangs
- Move dev helpers to scripts folder
- Move mfr to its own module and make it an entry point
- Reorganize project to use Python namespaces
- grapi: rename everything to grapi
- Merge pull request [#1](https://stash.kopano.io/projects/KC/repos/grapi/issues/1/) in KC/grapi from kc_sync to master
- rest: fill in caldav basics
- rest: start filling in ldap, imap backends
- rest: skip missing backend types
- rest: move final kopano imports into backend/kopano
- rest: move kopano-specific notification to kopano backend
- rest: add missing on_put hook in backend middleware
- pyko: replace all ext calls to Server() with server()
- Merge pull request [#2404](https://stash.kopano.io/projects/KC/repos/grapi/issues/2404/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_backend_plugins to master
- Merge branch 'kc-8.7.x'
- rest: use utf-8 encoding in json data
- Merge branch 'kc-8.7.x'
- rest: fix missing shbang line
- rest: basic pluggable backends
- Merge branch 'kc-8.7.x'
- pyko: improve user queries
- pyko: improve user queries
- pyko: ECtools: fix lazy-logging and deprecated warning
- ECtools: remove unused imports from kopano_rest
- build: Unbreak `make dist`
- pyko: merge Company.users with Server.users
- Merge pull request [#2231](https://stash.kopano.io/projects/KC/repos/grapi/issues/2231/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_round_31_plus to master
- rest: html-escape http error messages
- rest: only build rest when building with Python 3
- rest: improved query parameter checking
- rest: improved worker-process management
- rest: pagination improvements
- rest: use specified socket path instead of default
- rest: fix broken $select functionality
- rest: fix contact ICS deletion
- rest: various coverage improvements
- pyko: minor coverage improvements
- pyko: add folder.items(query=..)
- rest: expansion of message attachments
- rest: fix embedded attachment expansion
- rest: fix EmbeddedMessageResource import
- rest: variosu coverage improvements
- rest: error handling improvements
- Merge pull request [#2183](https://stash.kopano.io/projects/KC/repos/grapi/issues/2183/) in KC/kopanocore from ~JVANDERWAA/kopanocore:rest_mfr_unused_imports to master
- kopano-mfr: clean up unused imports
- Merge pull request [#2174](https://stash.kopano.io/projects/KC/repos/grapi/issues/2174/) in KC/kopanocore from ~JVANDERWAA/kopanocore:jsonschema to master
- rest: Introduce post request validation
- treewide: add missing SPDX license identifiers
- Merge pull request [#2141](https://stash.kopano.io/projects/KC/repos/grapi/issues/2141/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_round_29 to master
- rest: add --pid-file, --process-name options to mfr
- rest: add content-length=0 on 204
- rest: Handle invalid subscription gracefully
- pyko: minor ics cleanups
- rest: add attachment contentId, contentLocation
- pyko: add item.{codepage, encoding, html_utf8}
- rest: ignore html-decoding errors for now
- rest: use pidfile
- rest: replace README.txt with README.md
- python: add initial requirements.txt files
- rest: support $top for calendarView
- rest: support outlook.timezone preference header
- rest: avoid re-raising from NameError
- rest: try to reconnect session on server restart
- rest: (mfr) re-raise non-falcon errors on logging
- rest: move to API v1, and drop v0
- rest: add user reminderView
- rest: calendar event subscriptions
- rest: fix HTTP status code for deletion
- rest: fix recurrence range type
- pyko: clean up Recurrence.{_start, _end, ..}
- pyko: generate MAPI tz struct from Olson name
- python: add no-cover directives to py2-only paths
- rest: notification improvements.
- rest: some fixes for contacts
- rest: improvements for events and attachments
- rest: minor fixes for message createReply
- rest: add message send
- rest: fix mailfolder childFolders
- rest: sendMail: check SaveToSentItems
- rest: message copy/move should be post, not get
- rest: Support setting an all day event
- rest: Return 204 when deleting an event
- rest: streamline subscription resource matching
- rest: listing subscriptions
- rest: support folder and contacts subscriptions
- rest: switch to new-style pyko notifications
- rest: fixes for token session cache.
- rest: fix notifications.
- rest: re-enable $search for /users
- rest: add token session caching
- rest: remove pids from subscription metrics
- pyko: add basic query language
- rest: add kopano_mfr_ to metrics names
- rest: enable basic searching for users
- rest: fix group/members and event/attachments/id
- rest: improve subscription validation
- rest: fix missing import
- rest: automate metrics
- pyko: add hidden, active filters to Server.users
- rest: add photo scaling via photos/..X..
- pyko: add/improve Picture attributes
- rest: basic accept/decline appointments
- rest: flesh out __main__ further
- rest: send meeting requests on appointment creation
- rest: update README
- rest: basic subscription validation
- rest: do not hard depend on prometheus bindings
- rest: fix html body setting
- rest: add more useful metrics
- rest: enhance appointment creation
- rest: check for startDateTime, endDateTime args
- rest: use new kopano.ArgumentError
- rest: add prometheus metrics worker
- rest: fix bearer auth
- rest: add bunch of 400 (bad request) errors
- pyko: smarter recurrence offset updating
- kopano-mfr: add logging
- Merge pull request [#1831](https://stash.kopano.io/projects/KC/repos/grapi/issues/1831/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_round_19 to master
- rest: fix notifications
- Merge pull request [#1829](https://stash.kopano.io/projects/KC/repos/grapi/issues/1829/) in KC/kopanocore from ~JVANDERWAA/kopanocore:readd_rest_user to master
- rest: add some basic 404's.
- rest: contactFolders hierarchy syncing
- rest: Re-add removed UserResource fields
- rest: Fixup kopano_rest dist files
- rest: Add missing __init__.py files for submodules
- rest: make contactFolders include main contacts
- rest: avoid SYSTEM session for subscriptions
- rest: use setproctitle if available
- rest: more versioning
- rest: use wsgiref instead of gunicorn
- rest: basic authentication error handling
- rest: add API versioning
- rest: factor out config.py.
- rest: add kopano_rest/__main__.py
- rest: restore ability to change contact photos
- rest: fix profilePhoto routing
- rest: move api classes to api/ dir
- rest: avoid awkward import
- rest: fix contacts/delta
- rest: add basic README.txt
- rest: rename base.py to resource.py
- rest: move RestAPI to its own file
- rest: factor out resources
- pyko: add Picture class
- rest: GET user/photo, user/photo/$value
- Merge pull request [#1796](https://stash.kopano.io/projects/KC/repos/grapi/issues/1796/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_round_17 to master
- Merge pull request [#1795](https://stash.kopano.io/projects/KC/repos/grapi/issues/1795/) in KC/kopanocore from ~JVANDERWAA/kopanocore:pyko_rest_gab_users to master
- rest: add basic Group resource
- pyko: rest: Add missing user fields
- rest: we can just pass token and userid now
- rest: add sync window for messages
- pyko: add direct (bulk) body preview
- rest: factor out authentication
- rest: make authentication methods configurable
- rest: basic support for mailFolders/delta
- pyko: hide most internal Recurrence attributes
- rest: update compatibility description
- rest: fixes for pyko's localtime usage
- Merge pull request [#1756](https://stash.kopano.io/projects/KC/repos/grapi/issues/1756/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_round_16 to master
- python: Use staging directory to resolve build issues
- Merge pull request [#1748](https://stash.kopano.io/projects/KC/repos/grapi/issues/1748/) in KC/kopanocore from ~SEISENMANN/kopanocore:longsleep-python-add-version-py-where-missing to master
- pyko: fix recurrences with no end date
- rest: update compatibility description
- rest: add basic Bearer authentication
- rest: update compatibility description.
- rest: check if 'indent' arg is supported
- rest: use ujson if installed
- python: Distribute setup.cfg
- python: Remove hardcoded egg-info version prefix
- rest: add mailFolder resource to compat.md
- rest: support basic creation of monthly recurrence
- rest: add WSGI profiler script
- rest: support basic creation of weekly recurrence
- pyko: basic folder.occurrences preloading
- rest: make pyko datetimes naive UTC (for now)
- rest: Build with setuptools
- rest: update compatibility description
- rest: add contact searching
- rest: add basic Preference-Applied header
- rest: start of informal compatibility description.
- rest: Add /me/calendarView shortcut
- rest: fix event 'type'
- rest: support basic creation of daily recurrence
- rest: fix for kopano-mfr.
- rest: finally, implement users delta tracking
- rest: translate MAPI message notifications to REST
- Merge pull request [#1706](https://stash.kopano.io/projects/KC/repos/grapi/issues/1706/) in KC/kopanocore from ~MDUFOUR/kopanocore:rest_simon_fixes to master
- rest: use classes, improving configuration
- rest: disable content_type header by default
- Merge pull request [#1695](https://stash.kopano.io/projects/KC/repos/grapi/issues/1695/) in KC/kopanocore from ~JVANDERWAA/kopanocore:rest_sendMail_returncode to master
- rest: allow insecure connections
- rest: support patching occurrence start/end fields.
- rest: factor out emailAddress generation
- rest: Event organizer/isOrganizer
- pyko: python3 fix for Item.categories
- rest: finally, enable occurrence deletion.
- rest: support event/instances.
- rest: some notification fixes
- rest: add event iCalUId, responseRequested fields
- rest: rename sockets from mfr* to rest*.
- rest: add createReply, createReplyAll hooks
- rest: add event type, seriesMasterId.
- rest: add notify process to mfr.
- rest: move kopano-mfr to ECtools/rest.
- rest: basic post to notification url
- rest: GET subscription
- rest: fix http status code for sendMail
- Merge pull request [#1663](https://stash.kopano.io/projects/KC/repos/grapi/issues/1663/) in KC/kopanocore from ~JVANDERWAA/kopanocore:kopano-rest-isRead to master
- rest: do as little as possible on import
- rest: fix notifications after rebase.
- rest: fix sendMail
- rest: remove MAPI stuff from notify app.
- rest: notifications for given folder
- rest: add utils.py, factor out _folder()
- rest: basic inbox (un)subscription.
- rest: separate notification app.
- rest: move over to ECtools/rest

