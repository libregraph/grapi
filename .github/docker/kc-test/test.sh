#!/bin/bash
export PYTHONPATH=.:/app/core/swig/python:/app/core/swig/python/kopano:/app/core/swig/python/.libs
export MAPI_CONFIG_PATH=/app/core/provider/client
export LD_LIBRARY_PATH=/app/core/.libs
export KOPANO_SOCKET=http://localhost:11236
export PYTEST=pytest

if [ "$#" -ne 1 ]; then
    echo "Argument 'unit' or 'integration' is needed."
    exit 64
fi

if [ "$1" == "unit" ]; then
    $PYTEST test/unit/ -sv
elif [ "$1" == "integration" ]; then
    $PYTEST test/integration/backend.kopano/ -sv
else
    echo "Invalid argument: $1"
    exit 64
fi
