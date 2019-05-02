#!/bin/bash

export PYTHONDONTWRITEBYTECODE=yes

count=0

while true; do
	if kopano-admin --sync; then
		break
	fi

	if [[ "$count" -eq 10 ]]; then
		exit 1
	fi

	count=$((count +1))
	sleep 1
done

kopano-admin -l

make test-backend-kopano-ci PYTEST=pytest KOPANO_SOCKET=file:///var/run/kopano/server.sock KOPANO_SSLKEY_FILE=/kopano/ssl/kopano_dagent.pem

chown -R jenkins test/coverage || true
