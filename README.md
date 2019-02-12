# GRAPI

GRAPI provides a general REST web service for multiple groupware applications/stanadards. It aims to be largely compatible with Microsoft Graph. See `COMPAT.MD` for compatibility details.

In a production environment, GRAPI is deployed together with Konnect, Kopano-apid and the provided grapi-mfr script.

GRAPI requires python3.

## Running

    python3 grapi-mfr.py

## Parameters

The `--socket-path` parameter specifies where grapi-mfr should create its UNIX sockets (default `/var/run/grapi').

The `--workers` parameter specifies how many worker processes to utilize (default 8).

The `--insecure` parameter disables checking of SSL certificates for subscription webhooks.

The `--enable-auth-basic` parameter enables basic authentication (by default on bearer authentication is enabled).

The `--with-metrics` parameter adds an additional worker process to collect usage metrics (using Prometheus).

The `--metrics-listen` parameter specifies where the metrics worker can be reached.

## Development

GRAPI consists of separate WSGI applications. The grapi-mfr scripts runs both together, in a scalable way.

During development, it is sometimes easier to use the applications directly, and without needing access tokens (so using basic authentication).

    gunicorn3 'grapi:RestAPI()'
    gunicorn3 'grapi:NotifyAPI()'

In fact, gunicorn is not even necessary, but comes with many useful options, such as automatic reloading. The following also works:

    python3 -m grapi [REST_PORT=8000, NOTIFY_PORT=8001]
