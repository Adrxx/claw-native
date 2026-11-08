#!/bin/zsh
# Original construction plus native scene storage/lifetime boundary checks.
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/object-allocation-lifecycle
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'Object allocation lifecycle: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
$python Tests/NativeObjectConnections/object_allocation_lifecycle.py prepare "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
adapters=(${(f)"$($python Tests/NativeObjectConnections/compare.py adapters)"})
sources=(${(f)"$($python - <<'PY'
import re
from pathlib import Path
print('\n'.join(dict.fromkeys(re.findall(r'Sources/[A-Za-z0-9]+\.swift', Path('scripts/check-native-player.sh').read_text()))))
PY
)"})
sources=(${(u)sources} ${adapters:|sources})
extra=(Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift)
sources+=(${extra:|sources})
xcrun swiftc -j 1 -import-objc-header Sources/Claw-Bridging-Header.h $sources \
  Tests/NativeObjectConnections/object_allocation_lifecycle.swift \
  $objects -lc++ -lz -o "$verify_dir/lifecycle-tests"
"$verify_dir/lifecycle-tests" "$verify_dir"
$python Tests/NativeObjectConnections/object_allocation_lifecycle.py compare "$verify_dir"
