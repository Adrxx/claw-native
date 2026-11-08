#!/bin/zsh
# Finite shared-owner ABI proof; does not attach or promote a scene adapter.
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/conveyor_belt/transport
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'ConveyorBelt transport: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
$python Tests/NativeObjectConnections/conveyor_belt_transport.py prepare "$verify_dir"
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
sources=(${(f)"$($python - "$verify_dir" <<'PYCODE'
import hashlib,json,re,sys
from pathlib import Path
paths=['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeObjectConnections/conveyor_belt_transport.swift']
swift_paths=paths[:]
pending=[Path('Sources/Claw-Bridging-Header.h')];headers=set()
while pending:
 path=pending.pop()
 if path in headers:continue
 headers.add(path)
 for name in re.findall(r'#include\s+"([^"]+)"',path.read_text()):
  child=path.parent/name
  if child.is_file():pending.append(child)
paths += [str(p) for p in sorted(headers)] + ['Tests/NativeObjectConnections/conveyor_belt_transport.py','scripts/check-conveyor-belt-transport.sh']
captured={p:Path(p).read_bytes() for p in paths}
digest=hashlib.sha256(b''.join(p.encode()+b'\0'+v for p,v in captured.items())).hexdigest()
destination=Path(sys.argv[1])/'swift-inputs'/digest;destination.mkdir(parents=True,exist_ok=True)
for p,data in captured.items():
 target=destination/Path(p).name
 if not target.exists():target.write_bytes(data)
 if p in swift_paths:print(target)
(Path(sys.argv[1])/'build-inputs.json').write_text(json.dumps({p:hashlib.sha256(v).hexdigest() for p,v in captured.items()},indent=2)+'\n')
PYCODE
)"})
wait_for_load
xcrun swiftc -O -import-objc-header "${sources[1]:h}/Claw-Bridging-Header.h" $sources \
  $objects -lc++ -lz -o "$verify_dir/transport-tests"
$python - "$verify_dir/build-inputs.json" <<'PYCODE'
import hashlib,json,re,sys
from pathlib import Path
changed=[p for p,h in json.loads(Path(sys.argv[1]).read_text()).items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
if changed:raise SystemExit('Inputs changed during build; rerun: '+', '.join(changed))
PYCODE
wait_for_load
"$verify_dir/transport-tests" "$verify_dir"
$python Tests/NativeObjectConnections/conveyor_belt_transport.py compare "$verify_dir"
