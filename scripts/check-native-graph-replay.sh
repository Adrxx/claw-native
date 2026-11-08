#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec python3 Tests/NativeGraphReplay/build.py "$@"
