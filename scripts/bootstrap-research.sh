#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
npm ci --prefix research --ignore-scripts
python3 -m venv work/test-env
work/test-env/bin/python -m pip install -r research/requirements.txt
node scripts/patch-rea.mjs
print 'Python and REA installed. Set GHIDRA_INSTALL_DIR and JAVA_HOME to the pinned tools documented in docs/RESEARCH.md.'
