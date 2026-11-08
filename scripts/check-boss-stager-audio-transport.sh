#!/bin/zsh
# Enabled finite audio transport, separate from BossStager object attachment.
set -euo pipefail
cd "${0:A:h:h}"
python=work/test-env/bin/python
verify_dir=work/native-object-connections/boss_stager
mkdir -p "$verify_dir"
wait_for_load() {
  while (( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') >= 16 )); do
    print -u2 'BossStager audio: waiting for load below 16'
    sleep 20
  done
}
wait_for_load
$python Tests/NativeObjectConnections/boss_stager_audio.py prepare
objects=(${(f)"$($python -m tools.claw.native_objects --dir work/native-player-check --jobs 1)"})
# Snapshot only this build's Swift inputs, not the checkout. Each basename is
# unique and the witness retains hashes for the compiled shared-host bytes.
sources=(${(f)"$($python - "$verify_dir" <<'PY'
import hashlib,json,re,sys,subprocess
from pathlib import Path
# Keep source membership identical to the shared player check.
paths=re.findall(r'Sources/[A-Za-z0-9]+\.swift',Path('scripts/check-native-player.sh').read_text())
paths+=subprocess.check_output([sys.executable,'Tests/NativeObjectConnections/compare.py','adapters'],text=True).splitlines()
paths+=['Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeObjectConnections/boss_stager_audio.swift']
paths=list(dict.fromkeys(paths))
captured={p:Path(p).read_bytes() for p in paths}
digest=hashlib.sha256(b''.join(p.encode()+b'\0'+v for p,v in captured.items())).hexdigest()
destination=Path(sys.argv[1])/'audio-swift-inputs'/digest
destination.mkdir(parents=True,exist_ok=True)
for p,data in captured.items():
    target=destination/Path(p).name
    if not target.exists():target.write_bytes(data)
    print(target)
(Path(sys.argv[1])/'audio-transport-build-inputs.json').write_text(json.dumps({p:hashlib.sha256(v).hexdigest() for p,v in captured.items()},indent=2)+'\n')
PY
)"})
wait_for_load
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h $sources $objects -lc++ -lz -o "$verify_dir/audio-transport-tests"
$python - "$verify_dir/audio-transport-build-inputs.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
changed=[p for p,h in json.loads(Path(sys.argv[1]).read_text()).items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
if changed:raise SystemExit('Swift inputs changed during build; rerun: '+', '.join(changed))
PY
"$verify_dir/audio-transport-tests" "$verify_dir"
wait_for_load
$python Tests/NativeObjectConnections/boss_stager_audio.py compare "$verify_dir"
