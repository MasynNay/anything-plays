#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" == Darwin ]]; then
  exec "$(dirname "$0")/build_macos_dmg.sh"
else
  exec "$(dirname "$0")/build_linux_deb.sh"
fi
