#!/usr/bin/env bash
# GitHub-hosted Ubuntu 24.04 has intermittently shipped an inaccessible
# Azure archive mirror. Select official Canonical mirrors while retaining
# the existing signed apt Sources configuration. This does not disable
# GPG, HTTPS verification or apt's normal package integrity checks.
set -euo pipefail
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
