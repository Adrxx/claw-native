#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_CANONICAL_CHECK_DIR:-work/native-canonical-check}"
mkdir -p "$task_verify_dir"
# The generated registry references every admitted canonical entry. Link those
# real modules and the three recovered animation dependencies, never family
# stubs. Validate the narrowed set against generated app/gate membership.
python3 -m tools.claw.gen_project check
# Extend a private generated registry with synthetic frame probes. The shipped
# registry and admitted manifests retain exactly their generated membership.
python3 - "$task_verify_dir" <<'PY'
import json
from pathlib import Path
import sys
from tools.claw import gen_project
out = Path(sys.argv[1])
manifests = [json.loads(p.read_text()) for p in gen_project.FAMILIES.glob('*.json')]
registry = gen_project.canonical_inventory(manifests, json.loads(gen_project.EXCLUDE_FILE.read_text()))[2]
synthetic = [dict(address=address, convention='cdecl', argc=4, returns='u32',
                  entry='claw_frame_test_entry', family='synthetic_frame_test')
             for address in (0x7f001000, 0x7f001010, 0x7f001020)]
assert not {r['address'] for r in registry}.intersection(r['address'] for r in synthetic)
(out / 'ClawCanonicalDispatch.h').write_text(gen_project.canonical_dispatch_text(
    sorted(registry + synthetic, key=lambda r: r['address'])))
(out / 'Bridge.h').write_text('#include "ClawCanonicalDispatch.h"\n#include "ActorAnimationRuntime.h"\n'
    'uint32_t claw_frame_test_scope_state(void);\nuint32_t claw_frame_test_restored_after_fault(void);\n')
PY
objects=(${(f)"$(python3 - "$task_verify_dir" <<'PY'
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

root = Path.cwd()
out = Path(sys.argv[1])
jobs = int(os.environ.get('CLAW_NATIVE_JOBS', '1'))
if jobs < 1:
    raise SystemExit('CLAW_NATIVE_JOBS must be positive')
registry = (root / 'Sources/ClawCanonicalDispatch.h').read_text()
entries = set(re.findall(r'^uint32_t (claw_[a-z0-9_]+_entry)\(', registry, re.M))
sources, covered = set(), set()
for path in sorted((root / 'Tests/families').glob('*.json')):
    manifest = json.loads(path.read_text())
    entry = manifest.get('oracle', {}).get('entry')
    if entry in entries:
        if manifest.get('abi') != 'canonical' or manifest.get('evidence', {}).get('level') != 'admitted':
            raise SystemExit(f'Unadmitted registry entry: {entry}')
        covered.add(entry)
        sources.update(Path(p).stem for p in manifest['sources'] if p.endswith('.cpp'))
if covered != entries:
    raise SystemExit(f'Registry entries without manifests: {sorted(entries-covered)}')
sources.update(['ActorAnimationRuntime', 'AnimationEngine', 'AnimationOperations'])
gate = set((root / 'scripts/native-gate-sources.txt').read_text().splitlines())
if not sources <= gate:
    raise SystemExit(f'Missing generated gate sources: {sorted(sources-gate)}')
flags = ['-std=c++17', '-ffp-contract=off'] + shlex.split(os.environ.get('CLAW_NATIVE_CXXFLAGS', ''))
if os.environ.get('CLAW_NATIVE_ASAN', '1') == '1':
    flags += ['-fsanitize=address', '-fno-omit-frame-pointer']
headers = hashlib.sha256()
for path in sorted((root / 'Sources').glob('*.h')) + sorted((root / 'Sources').glob('*.hpp')):
    headers.update(path.read_bytes())
def build(source):
    name = source.stem
    key = hashlib.sha256(source.read_bytes() + headers.digest() + repr(flags).encode()).hexdigest()[:16]
    obj = out / f'{name}-{key}.o'
    if not obj.exists():
        result = subprocess.run(['xcrun', 'clang++', *flags, '-I', str(root / 'Sources'), '-c', str(source), '-o', str(obj)],
                                capture_output=True, text=True)
        if result.returncode:
            obj.unlink(missing_ok=True)
            raise RuntimeError(f'{name}: {result.stderr}')
    return str(obj)
with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
    inputs = [root / 'Sources' / (name + '.cpp') for name in sorted(sources)]
    inputs.append(root / 'Tests/NativeCanonical/FrameModule.cpp')
    objects = list(pool.map(build, inputs))
print('\n'.join(objects))
PY
)"})
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then
  swift_flags+=(-sanitize=address)
fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
  swift_flags+=(-O)
fi
xcrun swiftc $swift_flags -import-objc-header "$task_verify_dir/Bridge.h" -I Sources \
  Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Tests/NativeCanonical/main.swift \
  $objects -lc++ -o "$task_verify_dir/canonical-host-tests"
"$task_verify_dir/canonical-host-tests"
