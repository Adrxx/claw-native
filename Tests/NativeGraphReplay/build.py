"""Bounded replay build cache. Original-derived artifacts stay under work/."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from tools.claw import gen_project


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(command):
    return subprocess.check_output(command, text=True).strip()


def validate_extra_flags(value):
    # This prototype has two built-in modes. Arbitrary compiler arguments can
    # smuggle uncaptured inputs through forwarding/configuration mechanisms,
    # so no nonempty extra flag string belongs to its cache contract.
    if value.strip():
        raise ValueError('CLAW_NATIVE_CXXFLAGS is unsupported; use CLAW_NATIVE_OPTIMIZE/CLAW_NATIVE_ASAN')


def main():
    started = time.monotonic()
    validate_extra_flags(os.environ.get('CLAW_NATIVE_CXXFLAGS', ''))
    addresses = {0x4a48c0, 0x502335, 0x502369, 0x502f84, 0x501f01,
                 0x501fde, 0x4f6a9a, 0x50354d, 0x503510}
    # Capture manifests once: the registry and recorded manifest hashes must
    # describe the same bytes even if the live workspace is changing.
    manifest_bytes = {p: p.read_bytes() for p in sorted(gen_project.FAMILIES.glob('*.json'))}
    manifests = [(p, json.loads(data)) for p, data in manifest_bytes.items()]
    exclusion_bytes = gen_project.EXCLUDE_FILE.read_bytes()
    rows = gen_project.canonical_inventory([m for _, m in manifests], json.loads(exclusion_bytes))[2]
    rows = [r for r in rows if r['address'] in addresses]
    assert {r['address'] for r in rows} == addresses, 'all nine bodies must currently be admitted'
    registry = gen_project.canonical_dispatch_text(rows).encode()
    families = {r['family'] for r in rows}
    selected = [(p, m) for p, m in manifests if m.get('id') in families]
    sources = sorted({s for _, m in selected for s in m['sources']})
    assert all(s.endswith('.cpp') for s in sources)
    swift_sources = ['Sources/ClawTokenHeap.swift', 'Sources/ClawNativeCanonicalHost.swift',
                     'Sources/ClawNativeMfcLocks.swift', 'Sources/ClawNativeMfcMemory.swift',
                     'Tests/NativeGraphReplay/MemoryChecks.swift',
                     'Tests/NativeGraphReplay/main.swift']
    # Capture every local runtime header except the global dispatch registry.
    # The private generated nine-entry registry must be the only visible one.
    inputs = sorted(set(sources + swift_sources +
                        [str(p.relative_to(ROOT)) for p in ROOT.joinpath('Sources').rglob('*') if p.suffix in ('.h', '.hpp') and p != gen_project.DISPATCH_HEADER] +
                        [str(p.relative_to(ROOT)) for p, _ in selected] +
                        ['Tests/NativeGraphReplay/Bridge.h', 'Tests/NativeGraphReplay/build.py',
                         'Tests/NativeSourceEdges/validate_edges.py',
                         'scripts/check-native-graph-replay.sh', 'tools/claw/gen_project.py',
                         str(gen_project.EXCLUDE_FILE.relative_to(ROOT))]))
    captured = {str(p.relative_to(ROOT)): manifest_bytes[p] for p, _ in selected}
    captured[str(gen_project.EXCLUDE_FILE.relative_to(ROOT))] = exclusion_bytes
    for p in inputs:
        if p not in captured:
            captured[p] = Path(p).read_bytes()
    hashes = {p: sha(data) for p, data in captured.items()}
    # Validate the exact edge/manifest bytes that will be compiled. Concurrent
    # edits cause a retryable mismatch, never an unverified cached publication.
    edges = json.loads(capture([str(ROOT/'work/test-env/bin/python'),
                               'Tests/NativeSourceEdges/validate_edges.py']))
    assert edges['status'] == 'pass'
    assert all(hashes.get(p) == digest for p, digest in edges['input_sha256'].items()), 'edge inputs changed during capture; rerun'
    cpp = ['-std=c++17', '-ffp-contract=off']
    swift = []
    optimized = os.environ.get('CLAW_NATIVE_OPTIMIZE', '0') == '1'
    sanitized = os.environ.get('CLAW_NATIVE_ASAN', '1') == '1'
    if optimized:
        cpp += ['-O2']; swift += ['-O']
    if sanitized:
        cpp += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']; swift += ['-sanitize=address']
    mode = 'sanitized' if sanitized else 'optimized' if optimized else 'debug'
    identity = {name: capture(command) for name, command in {
        'clang_path': ['xcrun', '--find', 'clang++'],
        'swift_path': ['xcrun', '--find', 'swiftc'],
        'sdk': ['xcrun', '--show-sdk-path'],
        'sdk_version': ['xcrun', '--show-sdk-version'],
    }.items()}
    # Query and execute these exact paths, not another later xcrun resolution.
    for name in ('clang_path', 'swift_path', 'sdk'):
        assert Path(identity[name]).is_absolute(), 'toolchain paths must be absolute'
    identity['clang'] = capture([identity['clang_path'], '--version'])
    identity['swift'] = capture([identity['swift_path'], '--version'])
    cpp += ['-isysroot', identity['sdk']]
    swift += ['-sdk', identity['sdk']]
    manifest = dict(input_sha256=hashes, registry_sha256=sha(registry), compiler=identity,
                    edge_validation=edges,
                    cpp_flags=cpp, swift_flags=swift, link_flags=['-lc++'], addresses=sorted(addresses),
                    input_policy='immutable-private-snapshot-fixed-flags-v2')
    key = sha(json.dumps(manifest, sort_keys=True).encode())
    cache = ROOT / 'work/native-graph-replay-cache'
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / key
    build_started = time.monotonic()
    # Kernel lock releases on interruption. Build in a private directory then
    # publish atomically; another invocation never sees a partially linked file.
    with (cache / (key + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        hit = destination.is_dir()
        if hit:
            metadata = json.loads((destination / 'build.json').read_text())
            assert metadata['manifest'] == manifest
            assert sha((destination / 'replay').read_bytes()) == metadata['binary_sha256']
        else:
            temporary = Path(tempfile.mkdtemp(prefix=key + '.', dir=cache))
            try:
                snapshot = temporary / 'snapshot'
                for path, data in captured.items():
                    target = snapshot / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    target.chmod(0o444)
                private_header = temporary / 'ClawCanonicalDispatch.h'
                private_header.write_bytes(registry)
                private_header.chmod(0o444)
                bridge = temporary / 'Bridge.h'
                bridge.write_bytes(captured['Tests/NativeGraphReplay/Bridge.h'])
                bridge.chmod(0o444)
                # Quoted includes resolve alongside captured sources, then in
                # captured Sources. Ambient include variables cannot re-add live
                # workspace headers behind the explicit compiler arguments.
                compile_env = dict(os.environ)
                for name in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT'):
                    compile_env.pop(name, None)
                include = str(snapshot/'Sources')
                objects = []
                for source in sources:
                    obj = temporary / (Path(source).stem + '.o')
                    subprocess.run([identity['clang_path'], *cpp, '-I', include, '-c', str(snapshot/source), '-o', str(obj)], check=True, cwd=temporary, env=compile_env)
                    objects.append(str(obj))
                subprocess.run([identity['swift_path'], *swift, '-import-objc-header', str(temporary/'Bridge.h'),
                                '-I', include, *[str(snapshot/p) for p in swift_sources], *objects, '-lc++', '-o', str(temporary/'replay')], check=True, cwd=temporary, env=compile_env)
                assert hashes == {p: sha((snapshot/p).read_bytes()) for p in inputs}, 'private snapshot changed during compilation'
                assert sha(private_header.read_bytes()) == manifest['registry_sha256']
                metadata = dict(manifest=manifest, binary_sha256=sha((temporary/'replay').read_bytes()))
                (temporary/'build.json').write_text(json.dumps(metadata, indent=2)+'\n')
                os.rename(temporary, destination)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
    build_seconds = time.monotonic() - build_started
    reference_paths = ['work/native-mfc-factories-check/reference.json', 'work/native-mfc-thread-records-check/reference.json']
    run_started = time.monotonic()
    # UBSAN must fail the process, rather than emit a diagnostic and pass.
    env = dict(os.environ, UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    output = capture_with_env([str(destination/'replay'), *reference_paths], env)
    run_seconds = time.monotonic() - run_started
    replay = json.loads(output)
    assert replay['status'] == 'pass' and replay['profiles'] == 448 and replay['unique_reference_profiles'] == 288
    report = dict(status='pass', mode=mode, optimized=optimized, sanitized=sanitized,
                  cache_hit=hit, cache_key=key, build_seconds=build_seconds,
                  run_seconds=run_seconds, total_seconds=time.monotonic()-started,
                  clock='time.monotonic', replay=replay, build=metadata,
                  edge_validation=edges,
                  reference_sha256={p: sha(Path(p).read_bytes()) for p in reference_paths})
    report_path = ROOT/'work/coordination/native-graph-replay-prototype-report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with (cache/'report.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        history = json.loads(report_path.read_text()) if report_path.exists() else {'schema': 1, 'runs': []}
        history['runs'].append(report)
        with tempfile.NamedTemporaryFile(mode='w', dir=report_path.parent, delete=False) as f:
            json.dump(history, f, indent=2); f.write('\n'); staging = f.name
        os.replace(staging, report_path)
    print(json.dumps({k: v for k, v in report.items() if k != 'build'}, sort_keys=True))


def capture_with_env(command, env):
    return subprocess.check_output(command, text=True, env=env).strip()


if __name__ == '__main__':
    main()
