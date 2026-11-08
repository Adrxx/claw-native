#!/bin/zsh
# Finite shared-owner ABI proof; does not attach or promote a scene adapter.
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/jump_switch/transport
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'JumpSwitch transport: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
$python Tests/NativeObjectConnections/jump_switch_transport.py prepare "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h \
  Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift \
  Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/jump_switch_transport.swift \
  $objects -lc++ -lz -o "$verify_dir/transport-tests"
"$verify_dir/transport-tests" "$verify_dir"
$python Tests/NativeObjectConnections/jump_switch_transport.py compare "$verify_dir"
