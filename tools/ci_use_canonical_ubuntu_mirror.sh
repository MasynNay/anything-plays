#!/usr/bin/env bash
# Signed-package recovery for an ephemeral GitHub Ubuntu 24.04 runner:
# apt-get update can succeed against non-Ubuntu sources alone while the
# Ubuntu archive indexes disappear. Never disable GPG verification.
set -euo pipefail

emit_signed_noble_sources() {
  cat <<'SOURCES'
Types: deb
URIs: https://archive.ubuntu.com/ubuntu/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://security.ubuntu.com/ubuntu/
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
SOURCES
}

if [[ "${1:-}" == "--print-recovery-sources" ]]; then
  emit_signed_noble_sources
  exit 0
fi

if [[ "${1:-}" == "--repair-missing-packages" ]]; then
  if [[ "${GITHUB_ACTIONS:-}" != "true" || "${RUNNER_OS:-}" != "Linux" ||
        "$(id -u)" != "0" ]]; then
    echo "Ubuntu apt recovery is restricted to root on a GitHub Linux runner" >&2
    exit 2
  fi
  available() {
    apt-cache show python3-tk >/dev/null 2>&1 &&
      apt-cache show libegl1 >/dev/null 2>&1 &&
      apt-cache show libportaudio2 >/dev/null 2>&1
  }
  if available; then
    echo "Ubuntu Tk/EGL/PortAudio packages already available; no repair needed"
    exit 0
  fi
  # Refuse to repair any unexpected runner OS or signing-key environment.
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_CODENAME:-}" != "noble" ||
        ! -r /usr/share/keyrings/ubuntu-archive-keyring.gpg ]]; then
    echo "Expected signed Ubuntu 24.04 package source is unavailable" >&2
    exit 2
  fi
  echo "Ubuntu indexes missing; using signed Canonical sources on this disposable runner"
  emit_signed_noble_sources > /etc/apt/sources.list.d/anything-plays-ci-recovery.sources
  apt-get -o Acquire::Retries=2 update
  if ! available; then
    echo "Required signed Ubuntu packages still unavailable after recovery" >&2
    exit 1
  fi
  exit 0
fi

if [[ "${1:-}" != "" ]]; then
  echo "Unsupported Ubuntu mirror helper command" >&2
  exit 2
fi

# Preserve historical Azure-only mirror recovery for existing CI jobs.
MIRRORS=/etc/apt/apt-mirrors.txt
if [[ -f "$MIRRORS" ]] && grep -q 'azure.archive.ubuntu.com' "$MIRRORS"; then
  echo "Using official Ubuntu archive/security mirrors instead of unavailable Azure mirror"
  cp "$MIRRORS" /tmp/anything-plays-original-apt-mirrors.txt
  printf '%s\n' 'https://archive.ubuntu.com/ubuntu/' 'https://security.ubuntu.com/ubuntu/' > "$MIRRORS"
fi
if [[ -f "$MIRRORS" ]]; then
  echo "Ubuntu repository mirror candidates:"
  cat "$MIRRORS"
fi
