#!/bin/zsh
# Finite constructor transport only; the scene consumer remains separate.
set -euo pipefail
cd "${0:A:h:h}"
# This comparison uses the hash-verified v1.0 callback and its 0x480-byte
# allocation. The app's default v1.3 callback has a different layout.
export CLAW_LIVES_BOSS_PROFILE=claw-v1.0
python=work/test-env/bin/python
verify_dir=work/native-object-connections/cut_throat/transport
swift_flags=()
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
 swift_flags=(-O)
 verify_dir="${verify_dir}-optimized"
fi
mkdir -p "$verify_dir"
wait_for_load() {
 while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
  print -u2 'CutThroat transport: waiting for load below 16'
  sleep 20
 done
}
wait_for_load
$python Tests/NativeObjectConnections/cut_throat_transport.py prepare "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
# Capture only the two shared Swift inputs; concurrent peer edits must not
# change compiler inputs halfway through a run. These exact bytes are retained.
cp Sources/ClawNativeCanonicalHost.swift "$verify_dir/ClawNativeCanonicalHost.swift"
cp Sources/ClawNativeMfcMemory.swift "$verify_dir/ClawNativeMfcMemory.swift"
$python - "$verify_dir" <<'PYHASH'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1])
(p/'swift-inputs.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'ClawNativeCanonicalHost.swift',p/'ClawNativeMfcMemory.swift')},indent=2)+'\n')
PYHASH
wait_for_load
xcrun swiftc $swift_flags -import-objc-header Sources/Claw-Bridging-Header.h \
 Sources/ClawTokenHeap.swift "$verify_dir/ClawNativeCanonicalHost.swift" \
 Sources/ClawNativeMfcLocks.swift "$verify_dir/ClawNativeMfcMemory.swift" \
 Tests/NativeObjectConnections/cut_throat_transport.swift \
 $objects -lc++ -lz -o "$verify_dir/transport-tests"
wait_for_load
"$verify_dir/transport-tests" "$verify_dir"
$python Tests/NativeObjectConnections/cut_throat_transport.py compare "$verify_dir"
env -u CLAW_LIVES_BOSS_PROFILE "$verify_dir/transport-tests" "$verify_dir" --default-profile
