#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-or-later

# Simple helper to start GRAPI mfr. This is script is to run GRAPI mfr directly
# from the source tree. It is doing exactly the same as if it would be used
# by the packaging console_scripts entry point.

import sys

from grapi.mfr import main

sys.exit(main())
