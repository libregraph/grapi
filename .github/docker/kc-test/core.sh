#!/bin/sh
export PYTHONPATH=.:/app/core/swig/python:/app/core/swig/python/kopano:/app/core/swig/python/.libs
export MAPI_CONFIG_PATH=/app/core/provider/client
export LD_LIBRARY_PATH=/app/core/.libs
export KOPANO_SOCKET=file:///srv/shared/server.sock

exec /app/core/.libs/kopano-server -F -c /app/cfg/server.cfg --force-database-upgrade
