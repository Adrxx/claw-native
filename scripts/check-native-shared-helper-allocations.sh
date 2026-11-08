#!/bin/zsh
# Direct heap controls; source transport scripts check owner authority.
set -euo pipefail
cd "${0:A:h:h}"
verify_dir=work/native-object-connections/shared_helper_allocations
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'Shared helper allocations: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
xcrun swiftc Sources/ClawTokenHeap.swift \
  Tests/NativeObjectConnections/shared_helper_allocations.swift \
  -o "$verify_dir/allocation-tests"
"$verify_dir/allocation-tests" | tee "$verify_dir/result.json"

# Reuse the original initial bytes produced by the required JumpSwitch check.
# This mode adds configured-minimum ownership checks without changing its ABI.
jump_dir=work/native-object-connections/jump_switch/transport
if [[ ! -f "$jump_dir/reference.json" ]]; then
  scripts/check-jump-switch-transport.sh
fi
wait_for_load
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
wait_for_load
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h \
  Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift \
  Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/goo_vent_transport.swift \
  $objects -lc++ -lz -o "$verify_dir/owner-tests"
"$verify_dir/owner-tests" "$jump_dir" jump-switch-owner | tee "$verify_dir/owner-result.json"
