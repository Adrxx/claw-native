#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir="${CLAW_MFC_FACTORY_CHECK_DIR:-work/native-mfc-factories-check}"
mkdir -p "$task_verify_dir"
# The independent original reference is owned by the coordinator.
[[ -f "$task_verify_dir/reference.json" ]]
objects=(${(f)"$(python3 - "$task_verify_dir" <<'PY'
import hashlib,json,os,shlex,subprocess,sys
from pathlib import Path
from tools.claw import gen_project
out=Path(sys.argv[1])
rows=gen_project.canonical_inventory([json.loads(p.read_text()) for p in gen_project.FAMILIES.glob('*.json')],gen_project.load_exclusions())[2]
# Private generated registry, all and only the real admitted helper/factories.
rows=[r for r in rows if r['address'] in (0x4a48c0,0x502335,0x502369,0x502f84,0x501f01,0x501fde)]
assert {r['address'] for r in rows} == {0x4a48c0,0x502335,0x502369,0x502f84,0x501f01,0x501fde}
(out/'ClawCanonicalDispatch.h').write_text(gen_project.canonical_dispatch_text(rows))
(out/'Bridge.h').write_text(Path('Tests/NativeMfcFactories/Bridge.h').read_text())
flags=['-std=c++17','-ffp-contract=off']+shlex.split(os.environ.get('CLAW_NATIVE_CXXFLAGS',''))
if os.environ.get('CLAW_NATIVE_OPTIMIZE','0')=='1': flags+=['-O2']
if os.environ.get('CLAW_NATIVE_ASAN','1')=='1': flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
for name in ('MfcCompilerScopeRuntime','MfcStateFactoriesRuntime','MfcModuleAccessRuntime','MfcStartupRecordsRuntime'):
    obj=out/(name+'.o')
    subprocess.run(['xcrun','clang++',*flags,'-I','Sources','-c','Sources/'+name+'.cpp','-o',str(obj)],check=True)
    print(obj)
PY
)"})
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then swift_flags+=(-sanitize=address); fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then swift_flags+=(-O); fi
xcrun swiftc $swift_flags -import-objc-header "$task_verify_dir/Bridge.h" -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Tests/NativeMfcFactories/main.swift \
 $objects -lc++ -o "$task_verify_dir/mfc-factories-tests"
"$task_verify_dir/mfc-factories-tests" "$task_verify_dir/reference.json"
