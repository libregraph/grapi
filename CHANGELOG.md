# CHANGELOG

## Unreleased



## v10.4.0 (2020-06-03)

- Update German translation
- Disable per request verbose debug i18n logging
- Add translations_path to binscript and config
- Always add English translations
- Use consistent commandline arguments and logging
- Implement setting the language based on HTTP Accept Language
- Move HTTP Accept Language parsing to a seperate module
- Move mfr main() to a seperate file
- Compile po to mo files in memory when starting mfr
- Add documentation about adding a new translation
- Refactor out globals RUNNING and ABNORMAL_SHUTDOWN
- Restructure the mfr initialization with a Server class
- Add i18n via gettext


## v10.3.0 (2020-05-15)

- Make the Kopano calendar endpoints not experimental
- Validate subscription object when posting
- Add validate_json to grapi.v1.Resource for reuse
- Move load_json to grapi.v1.resource for reusability
- Move respond_204 to the common Resource class
- Inherit SubscriptionResource from grapi's Resource
- Handle invalid JSON on a subscription PATCH request
- Do not throw a 500 when subscriptionid is missing
- correct showAs not starting lowercase
- Update TODO's in kopano's event resource
- Support POST to /me/calendars/$id/events
- Correct field name for CalendarResource
- Add useful information to the TODO for calendar post endpoint
- Make /me/calendars endpoint non-experimental
- Add basic jsonschema validation for event creation
- sensitivity should be all lowercase according to grapi docs
- Add script to print the user information of a userid
- Add missing SPDX identifier to create-test-appointments.py
- Skip logging a backtrace when no store is found
- Add missing space to devrunner.py in scripts
- Set default log_level if not set in kopano backend
- Resolve user in subscriptions endpoints with userid
- Add support for isCancelled to events in kopano backend
- Strip trailing slash from URLs before routing
- grapi: mfr: logging.warn is deprecated
- Allow to configure log level via configuration file
- Restart GRAPI service automatically on failures


## v10.2.0 (2020-02-27)

- Always set extra PYTHONPATH on startup
- Update test environment to kopano_core 10.0.1.182.3b0e459
- Add nuke option to test script (default false)
- Fix typos in log message
- Use generator for event instances endpoint
- Move parsing of prefer header to middleware
- Unify JSON encode/decode and query functions
- kopano: correct response to None
- kopano: use item.replytime for the responsestatus
- Fix typos and clarify imports
- Add support for falcon 2.0.0
- Improve direct control on listener sockets
- Refactor and optimize store loading with per request profiler
- Implement store cache for Kopano backend
- Improve URL routing hot path and add heartbeat handler
- Log warning when ujson is not available
- Route warnings to logging
- Set name of master thread for logging purposes
- Improve clean and abnormal shutdown behavior
- Initialize log level for pyko
- Pass empty config when opening kopano server, to avoid potential implicit config
- Add validations and limits to webhook callback subscriptions
- Implement sane logging
- Improve operational logging
- Only log socket unlink errors when they are relevant
- scripts: add test script to generate events
- Define container versions and runtime parameters explicitly
- Run CI integration tests as Jenkins user
- Ensure that tests have python wheel support installed
- Ensure to run chown in Jenkins
- Implement profiling with yappi
- Refactor CI invocation to be more rebust and less duplicates
- Define compose project name in Makefile
- Remove kopano-utils from test environment
- Move CI clean target to always chain
- Remove fixed names in CI environment
- Use dedicated thread to expire cached logon sessions
- Add debounce and duplicate filter to subscription webhook trigger
- Start multiple notify API processes, similar to rest
- Add support for flexible LDAP attribute mapping
- Use default LDAP settings even when env variable is empty
- Allow customization of LDAP filters
- grapi: validate if socket-path is an actual directory


## v10.1.0 (2019-10-31)

- Add v10.1.0 to chagnelog
- kopano: Add proper format for event location get and set
- Log when mfr runs with experimental endpoints enabled
- Keep mfr args in process list
- Add persistency path via environment variable
- Ensure kc subscriptions are properly destroyed when no longer needed
- grapi: add profiling option to mfr
- Improve COMPAT notes
- Add list of used technologies
- grapi: meeting request accept/tentative/decline fixes
- test: kopano: extend event and calendar tests
- test: kopano: event: test multiple endpoint with fixtures
- test: kopano: add mailfolder tests
- test: kopano: do not try to remove folders in the inbox
- grapi: kopano: return new folder on copy/move
- test: add calendar event tests
- Add Docker integration tests
- grapi: test if options are not None
- test: Add integration for Kopano backend
- move arg assignment to the top as well
- move label definition to the top
- Add version information through labels
- Fix error handler detection


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

