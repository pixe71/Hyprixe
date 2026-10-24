#!/usr/bin/env bash
set -euo pipefail
if pgrep -u "$(id -u)" -f '[p]olkit-kde-authentication-agent-1|[h]yprpolkitagent' >/dev/null; then exit 0; fi
for agent in /usr/lib/*-linux-gnu/libexec/polkit-kde-authentication-agent-1 \
    /usr/libexec/polkit-kde-authentication-agent-1 \
    /usr/lib/polkit-kde-authentication-agent-1; do
    [[ -x "$agent" ]] && exec "$agent"
done
echo 'ERROR: Install polkit-kde-agent-1.' >&2
exit 1
