#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/marrow_floor/transport
mkdir -p "$verify_dir"
# Same cached object set and native scene build inputs as the named connection runner.
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
adapters=(${(f)"$($python Tests/NativeObjectConnections/compare.py adapters)"})
sources=(${(f)"$($python - <<'PY'
import re
from pathlib import Path
print('\n'.join(dict.fromkeys(re.findall(r'Sources/[A-Za-z0-9]+\.swift', Path('scripts/check-native-player.sh').read_text()))))
PY
)"})
sources=(${(u)sources} ${adapters:|sources})
mkdir -p "$verify_dir/includes" "$verify_dir/swift"
# Capture only this invocation's native Swift inputs against concurrent writes.
for source in $sources; do cp "$source" "$verify_dir/swift/${source:t}"; done
captured=()
for source in $sources; do captured+=("$verify_dir/swift/${source:t}"); done
cp Sources/*.h "$verify_dir/includes/"
shasum -a 256 Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/marrow_floor_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs.sha256"
xcrun swiftc -Xcc "-I$PWD/$verify_dir/includes" -import-objc-header "$verify_dir/includes/Claw-Bridging-Header.h" $captured \
  Tests/NativeObjectConnections/marrow_floor_transport.swift $objects -lc++ -lz \
  -o "$verify_dir/transport-tests"
shasum -a 256 Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift \
  Tests/NativeObjectConnections/marrow_floor_transport.swift "$verify_dir"/includes/*.h "$verify_dir"/swift/*.swift > "$verify_dir/build-inputs-after.sha256"
cmp "$verify_dir/build-inputs.sha256" "$verify_dir/build-inputs-after.sha256"
cmp Sources/ClawNativeCanonicalHost.swift "$verify_dir/swift/ClawNativeCanonicalHost.swift"
cmp Sources/ClawNativeMfcMemory.swift "$verify_dir/swift/ClawNativeMfcMemory.swift"
$python -m Tests.NativeObjectConnections.marrow_floor_transport --native "$verify_dir/transport-tests"
