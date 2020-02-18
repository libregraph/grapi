#!/bin/sh

set -eu

export PYTHONDONTWRITEBYTECODE=yes

PYTHON=${PYTHON:-python3}
PYTEST=${PYTEST:-py.test-3}

if [ "$CI" -eq "1" ]; then
	# Install dependencies, when in CI mode.
	grep -Ev "kopano|MAPI" requirements.txt > jenkins_requirements.txt
	$PYTHON -m pip install -r jenkins_requirements.txt
	rm -f jenkins_requirements.txt
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
	KOPANO_SOCKET=file:///var/run/kopano/server.sock \
	KOPANO_SSLKEY_FILE=/kopano/ssl/kopano_dagent.pem
