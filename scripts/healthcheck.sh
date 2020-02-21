#!/bin/sh
#
# Copyright 2019 Kopano and its licensors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License, version 3 or
# later, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

set -e

SOCKETS=$(ls ${KOPANO_GRAPI_SOCKET_PATH}/*.sock 2>/dev/null || .)
if [ -z "$SOCKETS" ]; then
	>&2 echo "No sockets found - this is not right"
	exit 1
fi

failed=0
for socket in $SOCKETS; do
	code=$(curl -o /dev/null -s -m 5 -w "%{http_code}" --unix-socket "$socket" http://localhost/health-check)
	if [ "$code" -ne 200 ]; then
		>&2 echo "Socket $socket failed with status $code"
		failed=1
	fi
done

exit $failed
