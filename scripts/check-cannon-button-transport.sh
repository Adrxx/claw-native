#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec work/test-env/bin/python Tests/NativeObjectConnections/cannon_button_transport.py "$@"
