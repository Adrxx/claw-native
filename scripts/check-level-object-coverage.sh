#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Build once with --build; subsequent reports use the current Release binary.
if [[ "${1:-}" == --build ]]; then
  CLAW_AGENT=1 CLAW_CONFIG=Release scripts/run-mac.sh
  shift
fi
exec work/test-env/bin/python scripts/check-level-object-coverage.py "$@"
