#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
profile=native
export PATH="$HOME/.local/bin:$PATH"
packages=true
dry_run=false
dolphin_only=false
waybar_only=false
restore_interface=false
interface_backup=
usage() {
    printf 'Usage: %s [native|vmware] [--no-packages] [--dry-run] [--waybar-only | --dolphin-only [--restore-dolphin-interface] [--interface-backup=ID]]\n' "$0"
}
for arg in "$@"; do
    case "$arg" in
        native|vmware) profile=$arg ;;
        --no-packages) packages=false ;;
        --dry-run) dry_run=true ;;
        --dolphin-only) dolphin_only=true ;;
        --waybar-only) waybar_only=true ;;
        --restore-dolphin-interface) restore_interface=true ;;
        --interface-backup=*) interface_backup=${arg#*=} ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
if $waybar_only && { $dolphin_only || $restore_interface || [[ -n $interface_backup ]]; }; then
    echo 'ERROR: --waybar-only cannot change or restore Dolphin.' >&2
    exit 2
fi
if { $restore_interface && ! $dolphin_only; } || { [[ -n $interface_backup ]] && ! $restore_interface; }; then
    echo 'ERROR: interface restoration requires --dolphin-only --restore-dolphin-interface.' >&2
    exit 2
fi
[[ $(uname -s) == Linux && -r /etc/os-release ]] || { echo 'ERROR: Debian 13 Linux required.' >&2; exit 1; }
# shellcheck source=/dev/null
source /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID:-} == 13 ]] || { echo 'ERROR: This installer targets Debian 13 only.' >&2; exit 1; }
[[ $EUID -ne 0 ]] || { echo 'ERROR: Run as your desktop user, without sudo. APT and SDDM system files use sudo separately.' >&2; exit 1; }
trap 'printf "ERROR: installation failed (line %s). No session was started.\n" "$LINENO" >&2' ERR
runtime=$(mktemp -d -t hyprixe-runtime.XXXXXXXX)
trap 'rm -rf -- "$runtime"' EXIT
if ! $waybar_only && ! $dry_run && command -v pgrep >/dev/null && pgrep -u "$UID" -x dolphin >/dev/null; then
    echo 'ERROR: Close all Dolphin windows/processes before updating its theme or restoring its interface.' >&2
    exit 1
fi
if $waybar_only; then
    command -v python3 >/dev/null || { echo 'ERROR: python3 is required.' >&2; exit 1; }
    args=(install --profile "$profile" --waybar-only)
    if $dry_run; then
        args+=(--dry-run)
    else
        python3 "$repo/scripts/waybar_compat.py" || {
            echo 'ERROR: Compatible Waybar with Lua IPC, taskbar and click drawer required; run the full ./install.sh native to prepare it.' >&2
            exit 1
        }
        command -v fc-cache >/dev/null || { echo 'ERROR: fontconfig (fc-cache) is required.' >&2; exit 1; }
    fi
    python3 "$repo/scripts/deploy.py" "${args[@]}"
    if ! $dry_run; then
        fc-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/fonts/hyprixe"
        echo 'Waybar files installed; restart waybar.service from the active UWSM session.'
    fi
    exit 0
fi
if $dolphin_only; then
    command -v python3 >/dev/null || { echo 'ERROR: python3 is required.' >&2; exit 1; }
    args=(install --profile "$profile" --dolphin-only)
    if $dry_run; then
        args+=(--dry-run)
    else
        if ! python3 "$repo/scripts/dolphin_checks.py" --dependencies >"$runtime/dolphin-deps.log" 2>&1; then
            if ! $packages; then cat "$runtime/dolphin-deps.log" >&2; exit 1; fi
            command -v sudo >/dev/null || { echo 'ERROR: sudo is required to install missing Dolphin dependencies.' >&2; exit 1; }
            echo 'Installing Dolphin Qt 6, preview and device dependencies from Debian stable.'
            mapfile -t dolphin_packages < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$repo/packages-dolphin.txt")
            sudo apt-get update
            sudo apt-get install --no-remove --no-install-recommends -y "${dolphin_packages[@]}"
            python3 "$repo/scripts/dolphin_checks.py" --dependencies
        else
            cat "$runtime/dolphin-deps.log"
        fi
    fi
    if $restore_interface; then
        restore_args=(restore-dolphin-interface)
        $dry_run && restore_args+=(--dry-run)
        [[ -n $interface_backup ]] && restore_args+=(--backup "$interface_backup")
        python3 "$repo/scripts/deploy.py" "${restore_args[@]}"
    fi
    python3 "$repo/scripts/deploy.py" "${args[@]}"
    if $dry_run; then
        echo 'Dolphin-only preview complete; no configuration changed.'
    else
        echo 'Dolphin Kvantum paint installed. Interface, other Qt themes and desktop/session configuration were preserved.'
    fi
    exit 0
fi
if $dry_run; then
    command -v python3 >/dev/null || { echo 'Install python3 to preview the deployment.' >&2; exit 1; }
    python3 "$repo/scripts/deploy.py" install --profile "$profile" --dry-run --sddm
    exit 0
fi
command -v sddm >/dev/null && command -v sddm-greeter-qt6 >/dev/null || {
    echo 'ERROR: Debian SDDM with its Qt 6 greeter must already be installed; see INSTALL.md.' >&2
    exit 1
}
command -v sudo >/dev/null || { echo 'ERROR: sudo is required for SDDM system files (and APT); see INSTALL.md.' >&2; exit 1; }
if $packages; then
    echo 'Installing Debian packages; sudo may request your password.'
    # A separate source file is created only if no backports suite is configured.
    if ! grep -RqsE '(^deb .*|^Suites:.*)trixie-backports' /etc/apt/sources.list /etc/apt/sources.list.d; then
        source_file=/etc/apt/sources.list.d/hyprixe-backports.sources
        if sudo test -e "$source_file"; then
            echo "ERROR: $source_file exists but backports is not configured; inspect it first." >&2
            exit 1
        fi
        printf '%s\n' 'Types: deb' 'URIs: https://deb.debian.org/debian' 'Suites: trixie-backports' 'Components: main' 'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' |
            sudo tee "$source_file" >/dev/null
        echo "Added official Debian backports: $source_file"
    fi
    sudo apt-get update
    read_packages() { sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$1"; }
    mapfile -t stable < <(read_packages "$repo/packages.txt")
    sudo apt-get install -y "${stable[@]}"
    mapfile -t sddm_packages < <(read_packages "$repo/packages-sddm.txt")
    sudo apt-get install --no-remove -y "${sddm_packages[@]}"
    mapfile -t backports < <(read_packages "$repo/packages-backports.txt")
    sudo apt-get install -y -t trixie-backports "${backports[@]}"
    if [[ $profile == vmware ]]; then
        mapfile -t guest < <(read_packages "$repo/profiles/vmware/packages.txt")
        sudo apt-get install -y "${guest[@]}"
    fi
    if ! command -v awww >/dev/null || ! command -v awww-daemon >/dev/null; then
        if apt-cache show awww >/dev/null 2>&1; then
            sudo apt-get install -y awww
        fi
    fi
    "$repo/scripts/build-runtime.sh" "$runtime"
fi
command -v python3 >/dev/null || { echo 'ERROR: python3 is required.' >&2; exit 1; }
PATH="$runtime:$PATH" python3 "$repo/scripts/check-deps.py"
python3 "$repo/scripts/deploy.py" install --profile "$profile" --runtime "$runtime" --sddm
echo 'SDDM Frosted Glass installed with a separate system backup. SDDM was not restarted.'
echo 'SDDM virtual keyboard disabled through [General] InputMethod=; the physical keyboard stays enabled.'
echo 'Installed. Reboot to load the SDDM theme, then select "Hyprland (uwsm-managed)" and log in.'
echo 'The plain Hyprland entry does not provide the required UWSM session lifecycle. See INSTALL.md.'
