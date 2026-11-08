#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/path_elevator/transport
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'PathElevator transport: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
$python Tests/NativeObjectConnections/path_elevator_transport.py prepare "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
wait_for_load
swift_flags=()
binary=transport-tests
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
  swift_flags=(-O)
  binary=transport-tests-release
fi
xcrun swiftc $swift_flags -import-objc-header Sources/Claw-Bridging-Header.h \
 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
 Tests/NativeObjectConnections/path_elevator_transport.swift \
 $objects -lc++ -lz -o "$verify_dir/$binary"
"$verify_dir/$binary" "$verify_dir"
$python Tests/NativeObjectConnections/path_elevator_transport.py compare "$verify_dir"
wait_for_load
$python Tests/NativeObjectConnections/path_elevator.py --audit-scene-destruction "${verify_dir:h}"
