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
