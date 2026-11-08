#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/red_tail_wind/transport
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'RedTailWind transport: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
sources=(${(f)"$($python - "$verify_dir" <<'PYCODE'
import re,subprocess,sys
from pathlib import Path
paths=re.findall(r'Sources/[A-Za-z0-9]+\.swift',Path('scripts/check-native-player.sh').read_text())
paths+=subprocess.check_output([sys.executable,'Tests/NativeObjectConnections/compare.py','adapters'],text=True).splitlines()
print('\n'.join(dict.fromkeys(paths)))
PYCODE
)"})
mkdir -p "$verify_dir/includes" "$verify_dir/swift"
# Capture only this invocation's native Swift inputs against concurrent writes.
for source in $sources; do cp "$source" "$verify_dir/swift/${source:t}"; done
captured=()
for source in $sources; do captured+=("$verify_dir/swift/${source:t}"); done
cp Sources/*.h "$verify_dir/includes/"
shasum -a 256 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/red_tail_wind_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs.sha256"
wait_for_load
xcrun swiftc -whole-module-optimization -Onone -Xcc "-I$PWD/$verify_dir/includes" -import-objc-header "$verify_dir/includes/Claw-Bridging-Header.h" $captured \
  Tests/NativeObjectConnections/red_tail_wind_transport.swift $objects -lc++ -lz \
  -o "$verify_dir/transport-tests"
shasum -a 256 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/red_tail_wind_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs-after.sha256"
cmp "$verify_dir/build-inputs.sha256" "$verify_dir/build-inputs-after.sha256"
cmp Sources/ClawNativeCanonicalHost.swift "$verify_dir/swift/ClawNativeCanonicalHost.swift"
cmp Sources/ClawNativeMfcMemory.swift "$verify_dir/swift/ClawNativeMfcMemory.swift"
cmp Sources/ClawTokenHeap.swift "$verify_dir/swift/ClawTokenHeap.swift"
wait_for_load
$python -m Tests.NativeObjectConnections.red_tail_wind_transport prepare
wait_for_load
"$verify_dir/transport-tests" "$verify_dir" > "$verify_dir/native.json"
wait_for_load
$python -m Tests.NativeObjectConnections.red_tail_wind_transport compare
