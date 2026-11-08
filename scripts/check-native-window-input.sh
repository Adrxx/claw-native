#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
work/test-env/bin/python -m Tests.NativeWindowInput.compare
mkdir -p work/native-player-check
export CLAW_NATIVE_INPUT_LITERALS=work/native-player-check/window-input-literals.json
work/test-env/bin/python - <<'PY'
import json, os
from Tests.clawparity.program import claw
program = claw()
literals = {}
for address in (0x5334f0, 0x52a004, 0x52c69c, 0x528b08, 0x52372c, 0x523ce0):
    section = next(s for s in program.sections if s.address <= address < s.address + s.size)
    literals[f'{address:x}'] = list(section.data[address-section.address:].split(b'\0', 1)[0] + b'\0')
with open(os.environ['CLAW_NATIVE_INPUT_LITERALS'], 'w') as stream:
    json.dump(literals, stream)
PY
trap 'rm -f "$CLAW_NATIVE_INPUT_LITERALS"' EXIT
scripts/check-native-player.sh --window-input-only
