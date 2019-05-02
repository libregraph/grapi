# Kopano GRAPI

Kopano GRAPI provides a general REST web service for multiple groupware
applications/standards. It aims to be largely compatible with Microsoft Graph.
See `COMPAT.MD` for compatibility details.

GRAPI is meant to be used directly by Kopano API (kapi) and requires Python 3.

## Running GRAPI

GRAPI uses a master runner to start its services in a way that they can be
accessed in parallel using unix sockets. So to start GRAPI, one uses the MFR
script (Master Fleet Runner).

```
./mfr.py
```

MFR behaviour can be controlled using commandline parameters. Use
`./mfr.py --help` to get the details.

## Run with Docker

Kopano GRAPI supports Docker to easily be run inside a container. Aside from
the obvious container reason, running with Docker also supports to run newer
GRAPI versions independent of the global Kopano installation.

### Run GRAPI with Docker Swarm

Setup the Docker container in swarm mode like this:

```
docker service create \
    --read-only \
    --mount type=tmpfs,destination=/tmp \
    --mount type=tmpfs,destination=/run \
	--env KOPANO_GRAPI_USER=$(id -u kapi) \
	--env KOPANO_GRAPI_GROUP=$(id -g kopano) \
    --mount type=bind,source=/etc/ssl/certs,target=/etc/ssl/certs,readonly \
    --mount type=bind,source=/run/kopano-grapi-docker,target=/run/kopano-grapi \
    --env KOPANO_GRAPI_KOPANO_SERVER_URI=https://email.kopano.com:237/kopano \
    --name=grapi \
    kopano/grapi \
    serve
```

### Run GRAPI from Docker image

```
docker run --rm=true --name=grapi \
	--read-only \
	--tmpfs /tmp \
	--tmpfs /run \
	--env KOPANO_GRAPI_USER=$(id -u kapi) \
	--env KOPANO_GRAPI_GROUP=$(id -g kopano) \
	--volume /run/kopano-grapi-docker:/run/kopano-grapi \
	--volume /run/kopano:/run/kopano \
	kopano/grapi \
	serve
```

Running GRAPI with Docker exposes the normal command line parameters of GRAPI.

To ensure access, the KOPANO_GRAPI_USER and KOPANO_GRAPI_GROUP environment vars
can be set to properly access Kopano Storage Server socket and create GRAPI
sockets so that they can be accessed by Kapid (provided as volumes).

## Development

GRAPI consists of separate WSGI applications which are run together by MFR in a
scalable way to be picked up by Kopano API. Recommended way to develop is to
run GRAPI together with Kopano API.

### Custom (direct) development startup

During development, it is sometimes easier to use the individual Grapi services
directly. Start the WSGI applications directly for example using gunicorn:

```
gunicorn3 'grapi.api.v1:RestAPI()'
gunicorn3 'grapi:api.v1:NotifyAPI()'
```

Another option is to start the devrunner by invoking make. This will run it
using the Kopano backend and listening by default on port 8000, with the notify
port on 8001.

```
make start-devrunner
```

Arguments, such as running a specific backend, can be passed as following:

```
make start-devrunner ARGS='--backends ldap'
```

## Run unit tests

The unit tests can be run like this:

```
make test
```

Integration tests for various backends are described in the backends section.

## Backends

### Kopano Groupware Storage server backend

The Kopano backend is currently the most tested and supported backend for mail,
calendar and directory information. Other available backends are for example
LDAP, CalDAV and IMAP, these should be treated as experimental at this moment.
Multiple backend can be run simultaneous where for example mail is provided by
the IMAP backend and calendar by the CalDAV backend.

#### Dependencies

* kopano Python module
* MAPI Python module

#### Tests

The kopano backend has integration tests, which require a running kopano-server
without users with the DB backend to be used for testing. Tests can be run as
following and incluenced by KOPANO_SOCKET, KOPANO_SSLKEY_FILE and
KOPANO_SSLKEY_PASS environment variables.

```
make test-backend-kopano
```

Coverage can be generated and viewed as following:
```
make open-integration-cov
```

### LDAP backend

The ldap backend requires two environment variables to be set:

* LDAP_URI - the ldap uri
* LDAP_BASEDN - the base dn

If the LDAP server needs authentication for listing users the following
environment variables should be set:

* LDAP_BINDDN
* LDAP_BINDPW

#### Dependencies

* python-ldap Python module

### Caldav backend

The caldav backend requires three environment variables to be set:

* CALDAV_SERVER - the caldav server url
* GRAPI_USER - the caldav user
* GRAPI_PASSWORD - the caldav password

#### Dependencies

* vobject Python module
* caldav Python module

### IMAP Backend

The IMAP backend only supports IMAP over SSL/TLS and requires three environment
variables to be set:

* IMAP_SERVER - the IMAP server url
* GRAPI_USER - the IMAP user
* GRAPI_PASSWORD - the IMAP password

## Metrics

Grapi can expose prometheus metrics if `prometheus_client` is installed and
metrics are enabled using the appropriate flag `--with-metrics` is set. The env
variable `prometheus_multiproc_dir` must be set to a directory that the client
library can use for metrics.

## License

See `LICENSE.txt` for licensing information of this project.
