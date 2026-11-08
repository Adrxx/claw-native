#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/aquatis_dynamite/transport
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'AquatisDynamite transport: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
sources=(Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift)
mkdir -p "$verify_dir/includes" "$verify_dir/swift"
# Capture only this invocation's native Swift inputs against concurrent writes.
for source in $sources; do cp "$source" "$verify_dir/swift/${source:t}"; done
captured=()
for source in $sources; do captured+=("$verify_dir/swift/${source:t}"); done
cp Sources/*.h "$verify_dir/includes/"
shasum -a 256 Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/aquatis_dynamite_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs.sha256"
wait_for_load
xcrun swiftc -whole-module-optimization -O -Xcc "-I$PWD/$verify_dir/includes" -import-objc-header "$verify_dir/includes/Claw-Bridging-Header.h" $captured \
  Tests/NativeObjectConnections/aquatis_dynamite_transport.swift $objects -lc++ -lz \
  -o "$verify_dir/transport-tests"
shasum -a 256 Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/aquatis_dynamite_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs-after.sha256"
cmp "$verify_dir/build-inputs.sha256" "$verify_dir/build-inputs-after.sha256"
cmp Sources/ClawNativeCanonicalHost.swift "$verify_dir/swift/ClawNativeCanonicalHost.swift"
cmp Sources/ClawNativeMfcMemory.swift "$verify_dir/swift/ClawNativeMfcMemory.swift"
wait_for_load
$python -m Tests.NativeObjectConnections.aquatis_dynamite_transport --native "$verify_dir/transport-tests"
