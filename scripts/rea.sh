#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
: "${GHIDRA_INSTALL_DIR:?Set GHIDRA_INSTALL_DIR; see docs/RESEARCH.md}"
: "${JAVA_HOME:?Set JAVA_HOME; see docs/RESEARCH.md}"
export GHIDRA_INSTALL_DIR JAVA_HOME
export REA_GHIDRA_STARTUP_TIMEOUT_MS=180000
exec node "$project_dir/research/node_modules/rea-agents/scripts/rea.mjs" "$@"
