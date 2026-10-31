#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo/scripts:$repo/common/tools:$repo/common/compat:$repo/profiles/debian/install${PYTHONPATH:+:$PYTHONPATH}"
exec bash "$repo/profiles/debian/install/uninstall.sh" "$@"
