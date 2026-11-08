#!/bin/zsh
# Usage: check-native-object-connection.sh FAMILY_ID
# Exit 2: family not in the bridge's election table. Exit 3: elected but its
# adapter or comparison files are missing (JSON names them). Otherwise runs
# the shared bridge controls and only the selected family's comparison.
set -euo pipefail
cd "${0:A:h:h}"
family="${1:?Usage: check-native-object-connection.sh FAMILY_ID}"
python=work/test-env/bin/python
code=0
selected=(${(f)"$($python Tests/NativeObjectConnections/compare.py resolve "$family")"}) || code=$?
if (( code != 0 )); then
  (( code == 2 )) && print -u2 'Unelected object connection'
  print -r -- "${selected[-1]:-}"
  exit $code
fi
verify_dir="work/native-object-connections/$family"
mkdir -p "$verify_dir"
$python Tests/NativeObjectConnections/compare.py prepare "$family"
# Share the existing compiler object cache and the required scene source list.
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 2)"})
adapters=(${(f)"$($python Tests/NativeObjectConnections/compare.py adapters)"})
sources=(${(f)"$($python - <<'PY'
import re
from pathlib import Path
print('\n'.join(dict.fromkeys(re.findall(r'Sources/[A-Za-z0-9]+\.swift', Path('scripts/check-native-player.sh').read_text()))))
PY
)"})
sources=(${(u)sources} ${adapters:|sources})
# Other dispatcher lanes own scene and adapter inputs. Retain exact compiler bytes
# so their later edits cannot invalidate a comparison midway through swiftc.
snapshot_dir="$verify_dir/swift-inputs"
mkdir -p "$snapshot_dir"
$python - "$snapshot_dir" $sources <<'PY'
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
hashes = {}
for name in sys.argv[2:]:
    source = Path(name)
    data = source.read_bytes()
    if source.read_bytes() != data:
        raise SystemExit(f'{source} changed during capture; retry the check')
    (out / source.name).write_bytes(data)
    hashes[str(source)] = hashlib.sha256(data).hexdigest()
(out / 'sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
PY
for ((source_index=1; source_index<=${#sources}; source_index++)); do
  sources[source_index]="$snapshot_dir/${sources[source_index]:t}"
done
# Project regeneration in another dispatcher lane can touch the live bridging
# header while Swift imports it. Compile against the same captured header set
# throughout this comparison, as the transport runner already does.
include_dir="$verify_dir/includes"
mkdir -p "$include_dir"
cp Sources/*.h "$include_dir/"
xcrun swiftc -Xcc "-I$PWD/$include_dir" -import-objc-header "$include_dir/Claw-Bridging-Header.h" $sources \
  Tests/NativeObjectConnections/bridge.swift ${selected[2]} Tests/NativeObjectConnections/main.swift \
  $objects -lc++ -lz -o "$verify_dir/connection-tests"
"$verify_dir/connection-tests" "$verify_dir" "$family"
$python Tests/NativeObjectConnections/compare.py compare "$family"
