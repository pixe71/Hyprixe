#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo/scripts:$repo/common/tools:$repo/common/compat:$repo/profiles/debian/install${PYTHONPATH:+:$PYTHONPATH}"
export HYPRIXE_ENTRYPOINT="$0"
exec bash "$repo/profiles/debian/install/install.sh" "$@"
