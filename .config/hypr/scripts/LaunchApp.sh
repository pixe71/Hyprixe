#!/usr/bin/env bash
set -euo pipefail
# Long-lived GUI apps get their own UWSM scope instead of the compositor's unit.
exec uwsm app -- "$@"
