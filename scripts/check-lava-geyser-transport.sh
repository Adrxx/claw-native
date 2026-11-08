#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
export PYTHONPATH=.
wait_for_load() {
 while ! $python -c 'import subprocess,sys; v=subprocess.check_output(["sysctl","-n","vm.loadavg"],text=True); print(v.strip(),file=sys.stderr);sys.exit(float(v.split()[1])>=16)'; do sleep 10; done
}
verify_dir=work/native-object-connections/lava_geyser_transport
wait_for_load
$python Tests/NativeObjectConnections/lava_geyser_transport.py prepare
wait_for_load
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
sources=(${(f)"$($python - <<'PY'
import re
from pathlib import Path
print('\n'.join(dict.fromkeys(re.findall(r'Sources/[A-Za-z0-9]+\.swift', Path('scripts/check-native-player.sh').read_text()))))
PY
)"})
adapters=(${(f)"$($python Tests/NativeObjectConnections/compare.py adapters)"})
sources=(${(u)sources} ${adapters:|sources})
# Capture only compiler inputs in the existing ignored content-addressed cache.
sources+=(Tests/NativeObjectConnections/lava_geyser_transport.swift)
sources=(${(f)"$($python - "${sources[@]}" <<'PYBUILD'
import hashlib,json,subprocess,sys
from pathlib import Path
files=[(name,Path(name).read_bytes()) for name in sys.argv[1:]]
flags=['-import-objc-header','Sources/Claw-Bridging-Header.h','-lc++','-lz']
compiler=subprocess.check_output(['xcrun','swiftc','--version'])
h=hashlib.sha256(compiler+json.dumps(flags).encode())
for name,data in files:h.update(name.encode()+b'\0'+data)
root=Path('work/build/lava-geyser-transport-swift')/h.hexdigest();root.mkdir(parents=True,exist_ok=True)
manifest={}
for name,data in files:
 dest=root/Path(name).name
 if not dest.exists():dest.write_bytes(data)
 manifest[name]=hashlib.sha256(data).hexdigest()
 print(dest)
(root/'inputs.json').write_text(json.dumps(manifest,sort_keys=True))
Path('work/native-object-connections/lava_geyser_transport/swift-inputs.json').write_text(json.dumps({'cache':str(root),'inputs':manifest},sort_keys=True))
PYBUILD
)"})
wait_for_load
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h $sources $objects -lc++ -lz -o "$verify_dir/transport-tests"
wait_for_load
"$verify_dir/transport-tests" "$verify_dir"
$python Tests/NativeObjectConnections/lava_geyser_transport.py compare

$python - <<'PYVERIFY'
import hashlib,json
from pathlib import Path
m=json.loads(Path('work/native-object-connections/lava_geyser_transport/swift-inputs.json').read_text())
for name in ['Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeObjectConnections/lava_geyser_transport.swift']:
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==m['inputs'][name], f'Changed during check: {name}; rerun'
print(json.dumps({'swift_inputs':'current','cache':m['cache']}))
PYVERIFY
