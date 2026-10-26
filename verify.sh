#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
# Use the same managed runtime binaries as install.sh and the Hyprland session.
export PATH="$HOME/.local/bin:$PATH"
exec python3 "$repo/scripts/verify.py" "$@"
