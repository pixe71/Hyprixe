#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
profile=native
export PATH="$HOME/.local/bin:$PATH"
packages=true
dry_run=false
usage() {
    printf 'Usage: %s [native|vmware] [--no-packages] [--dry-run]\n' "$0"
}
for arg in "$@"; do
    case "$arg" in
        native|vmware) profile=$arg ;;
        --no-packages) packages=false ;;
        --dry-run) dry_run=true ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
[[ $(uname -s) == Linux && -r /etc/os-release ]] || { echo 'ERROR: Debian 13 Linux required.' >&2; exit 1; }
# shellcheck source=/dev/null
source /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID:-} == 13 ]] || { echo 'ERROR: This installer targets Debian 13 only.' >&2; exit 1; }
[[ $EUID -ne 0 ]] || { echo 'ERROR: Run as your desktop user, without sudo. APT and SDDM system files use sudo separately.' >&2; exit 1; }
trap 'printf "ERROR: installation failed (line %s). No session was started.\n" "$LINENO" >&2' ERR
runtime=$(mktemp -d -t hyprixe-runtime.XXXXXXXX)
trap 'rm -rf -- "$runtime"' EXIT
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
