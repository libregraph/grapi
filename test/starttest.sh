#!/bin/sh

# This script is the main test runner. It is run inside the corresponding
# Docker container. Do not run directly, instad run `make test-backend-kopano-ci-run`.

set -eu

export PYTHONDONTWRITEBYTECODE=yes

PYTHON=${PYTHON:-python3}
PYTEST=${PYTEST:-py.test-3}
KOPANO_SOCKET=${KOPANO_SOCKET:-file:///run/kopano/server.sock}
KOPANO_SSLKEY_FILE=${KOPANO_SSLKEY_FILE:-/kopano/ssl/kopano_dagent.pem}

if [ "$CI" -eq "1" ]; then
	# Install dependencies, when in CI mode.
	grep -Ev "kopano|MAPI" requirements.txt > /tmp/jenkins_requirements.txt
	$PYTHON -m pip install -r /tmp/jenkins_requirements.txt

	if [ -x "$(command -v dockerize)" ]; then
		dockerize -wait $KOPANO_SOCKET -timeout 60s
	fi
fi

count=0
while true; do
	if kopano-admin --sync; then
		break
	fi

	if [ "$count" -eq 10 ]; then
		exit 1
	fi

	count=$((count +1))
	sleep 1
done

kopano-admin -l

exec make test-backend-kopano-ci \
	PYTHON=$PYTHON \
	PYTEST=$PYTEST \
	KOPANO_SOCKET=$KOPANO_SOCKET \
	KOPANO_SSLKEY_FILE=$KOPANO_SSLKEY_FILE
