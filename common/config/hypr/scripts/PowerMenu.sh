#!/usr/bin/env bash
set -euo pipefail
# Compatibility entrypoint for Waybar and existing callers; one session menu.
exec hyprixe-session "$@"
