#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)
command -v python3 >/dev/null || { echo 'ERROR: python3 is required.' >&2; exit 1; }
if [[ ${1:-} == --sddm-only ]]; then
    shift
    exec sudo python3 "$repo/profiles/debian/install/sddm_theme.py" restore "$@"
fi
exec python3 "$repo/profiles/debian/install/deploy.py" restore "$@"
