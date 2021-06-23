#!/bin/sh
export PYTHONPATH=.:/app/core-${PYTHON_VERSION}/swig/python:/app/core-${PYTHON_VERSION}/swig/python/kopano:/app/core-${PYTHON_VERSION}/swig/python/.libs
export MAPI_CONFIG_PATH=/app/core-${PYTHON_VERSION}/provider/client
export LD_LIBRARY_PATH=/app/core-${PYTHON_VERSION}/.libs
export KOPANO_SOCKET=http://localhost:11236
export PYTHON=~/.pyenv/versions/${PYTHON_VERSION}/bin/python

make ARGS="\
        --socket-path=/srv/shared \
        --backends=kopano \
        --enable-experimental-endpoints \
        --log-level=debug \
        --translations-path=./i18n \
        -w 4 $@" start-mfr
