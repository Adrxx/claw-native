#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec work/test-env/bin/python - <<'PY'
import fcntl, hashlib, pathlib, re, subprocess
def run(command):
    result=subprocess.run(command)
    if result.returncode: raise SystemExit(result.returncode)
root=pathlib.Path.cwd()
load=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
if load>=16:
    raise SystemExit('load is 16 or more; retry when the shared host is free')
cache=root/'work/build/cannon-switch-transport'
cache.mkdir(parents=True,exist_ok=True)
lock=(cache/'build.lock').open('w')
fcntl.flock(lock,fcntl.LOCK_EX)
headers=sorted((root/'Sources').glob('*.h'))+sorted((root/'Sources').glob('*.hpp'))
inputs={}
def capture(path):
    data=path.read_bytes();inputs[path]=hashlib.sha256(data).digest();return data
hash_headers=hashlib.sha256(b''.join(capture(p) for p in headers)).digest()
compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip()
swift=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip()
sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
version=subprocess.check_output([compiler,'--version'])+sdk.encode()
objects=[]
# Legacy public APIs coexist with canonical modules in Sources. Select the
# registry owners; the native player-cache wrapper includes its canonical body.
legacy={'AudioManagerLifecycleRuntime.cpp','AmbientAudioBackendRuntime.cpp',
        'BootyStoryRuntime.cpp','BootyProgressionRuntime.cpp','BootyResultsRuntime.cpp',
        'SpecialCommandRuntime.cpp','ResourceTableConstructionRuntime.cpp',
        'MenuGameLaunchRuntime.cpp','PlayerCacheApplicationCanonical.cpp'}
for source in sorted((root/'Sources').glob('*.cpp')):
    if source.name in legacy: continue
    raw=capture(source)
    included=b''.join(capture(source.parent/name.decode()) for name in re.findall(rb'#include\s+"([^"]+\.cpp)"',raw))
    key=hashlib.sha256(raw+included+hash_headers+version+b'O0-fp-contract-off').hexdigest()[:20]
    target=cache/(source.stem+'-'+key+'.o')
    if not target.exists():
        run([compiler,'-isysroot',sdk,'-std=c++17','-O0','-ffp-contract=off','-I',str(root/'Sources'),'-c',str(source),'-o',str(target)])
    objects.append(str(target))
bridge=cache/'bridge.h'
bridge.write_text('#include "ClawCanonicalDispatch.h"\n#include "ClawNativeMenuInterface.h"\n')
swift_sources=[root/'Sources'/name for name in ['ClawTokenHeap.swift','ClawNativeCanonicalHost.swift','ClawNativeMfcMemory.swift','ClawNativeMfcLocks.swift']]
swift_sources.append(root/'Tests/NativeObjectConnections/cannon_switch_transport.swift')
key=hashlib.sha256(b''.join(capture(p) for p in swift_sources)+hash_headers+' '.join(objects).encode()+subprocess.check_output([swift,'--version'],stderr=subprocess.STDOUT)).hexdigest()[:20]
binary=cache/('transport-'+key)
if not binary.exists():
    run([swift,'-sdk',sdk,'-O','-I',str(root/'Sources'),'-import-objc-header',str(bridge),*[str(p) for p in swift_sources],*objects,'-Xlinker','-lc++','-Xlinker','-lz','-o',str(binary)])
if any(hashlib.sha256(p.read_bytes()).digest()!=digest for p,digest in inputs.items()):
    raise SystemExit('build inputs changed; rerun for current shared-checkout bytes')
run([str(root/'work/test-env/bin/python'),'-m','Tests.NativeObjectConnections.cannon_switch_transport','--native',str(binary)])
PY
