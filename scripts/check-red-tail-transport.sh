#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/red_tail/transport
mkdir -p "$verify_dir"
wait_for_load() {
 while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
  print -u2 'RedTail transport: waiting for load below 16'
  sleep 20
 done
}
wait_for_load
$python Tests/NativeObjectConnections/red_tail_transport.py resource-inputs "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
wait_for_load
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h \
 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
 Sources/ClawAssets.swift Sources/ClawAnimationPlayback.swift Sources/ClawLevelScene.swift Sources/ClawWorld.swift Sources/ClawActorResources.swift \
 Tests/NativeObjectConnections/red_tail_transport.swift \
 $objects -lc++ -lz -o "$verify_dir/transport-tests"
wait_for_load
"$verify_dir/transport-tests" --resources "$verify_dir"
wait_for_load
$python Tests/NativeObjectConnections/red_tail_transport.py prepare "$verify_dir"
wait_for_load
"$verify_dir/transport-tests" "$verify_dir"
$python Tests/NativeObjectConnections/red_tail_transport.py compare "$verify_dir"
