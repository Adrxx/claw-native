#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec work/test-env/bin/python - "$@" <<'PYCODE'
import fcntl, gzip, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from tools.claw import gen_project
from Tests.clawparity.program import claw
root=Path.cwd()
check_dir=Path(os.environ.get('CLAW_NATIVE_CRT_CHECK_DIR','work/coordination')).resolve()
check_dir.mkdir(parents=True,exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def capture(args): return subprocess.check_output(args,text=True).strip()
assert not os.environ.get('CLAW_NATIVE_CXXFLAGS','').strip(), 'use fixed ASAN/OPTIMIZE modes'
whole=os.environ.get('CLAW_NATIVE_CRT_WHOLE','0')=='1'
addresses={0x4a3610,0x4a3560,0x4a35f0,0x4a5860,0x4a5870,0x4a7b90,0x4a7bc0,0x4a7c40}
manifest_bytes={p:p.read_bytes() for p in gen_project.FAMILIES.glob('*.json')}
if whole:
    leaves=json.loads(manifest_bytes[root/'Tests/families/static_exit_registrations.json'])
    assert leaves['id']=='static_exit_registrations' and len(leaves['owned'])==126
    addresses.update(int(r['address'],16) for r in leaves['owned'])
exclusions=gen_project.EXCLUDE_FILE.read_bytes()
rows=gen_project.canonical_inventory([json.loads(v) for v in manifest_bytes.values()],json.loads(exclusions))[2]
rows=[r for r in rows if r['address'] in addresses]
assert {r['address'] for r in rows} == addresses,'all eight CRT source roots must be admitted'
registry=gen_project.canonical_dispatch_text(rows).encode()
families={r['family'] for r in rows}
selected={p:v for p,v in manifest_bytes.items() if json.loads(v).get('id') in families}
cpp_sources=sorted({s for v in selected.values() for s in json.loads(v)['sources']})
swift_sources=['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeCrtMemory.swift','Sources/ClawNativeCrtServices.swift','Tests/NativeCrtExitRegistry/main.swift']
paths=cpp_sources+swift_sources+['Tests/NativeCrtExitRegistry/Bridge.h','scripts/check-native-crt-exit-registry.sh','tools/claw/gen_project.py','Tests/NativeCrtExitRegistry/validate_edges.py']
paths += [str(p.relative_to(root)) for p in root.joinpath('Sources').rglob('*') if p.suffix in ('.h','.hpp') and p != gen_project.DISPATCH_HEADER]
inputs={str(p.relative_to(root)):v for p,v in selected.items()}
inputs[str(gen_project.EXCLUDE_FILE.relative_to(root))]=exclusions
inputs.update({p:Path(p).read_bytes() for p in paths})
p=claw()
validation_args=['--leaves'] if whole else []
validation=json.loads(capture(['work/test-env/bin/python','Tests/NativeCrtExitRegistry/validate_edges.py',*validation_args]))
assert validation['status']=='pass' and validation['edges']==23 and validation['prepared_roots']==8
if whole: assert validation['registration_leaves']==126
assert validation['input_sha256']['Sources/ClawNativeCanonicalHost.swift']==sha(inputs['Sources/ClawNativeCanonicalHost.swift']), 'host changed during validation; rerun'
assert all(Path(name).read_bytes()==data for name,data in inputs.items()),'compiled inputs changed during capture; rerun'
edges=validation
root_sites='prepared original leaf roots at4a5896; admitted leaf CALLs execute natively; no constructor wrappers' if whole else 'prepared-direct-unit-roots-at-reviewed-real-callers; no registration-leaf election'
asan = os.environ.get('CLAW_NATIVE_ASAN','1') == '1'
opt = os.environ.get('CLAW_NATIVE_OPTIMIZE','0') == '1'
identity = {k:capture(v) for k,v in {'clang':['xcrun','--find','clang++'],'swift':['xcrun','--find','swiftc'],'sdk':['xcrun','--show-sdk-path']}.items()}
identity['clang_version'] = capture([identity['clang'],'--version'])
identity['swift_version'] = capture([identity['swift'],'--version'])
cpp = ['-std=c++17','-ffp-contract=off','-isysroot',identity['sdk']]
swift = ['-sdk',identity['sdk']]
if asan: cpp += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']; swift += ['-sanitize=address']
if opt: cpp += ['-O2']; swift += ['-O']
certificate = dict(schema=1,command='native-crt-exit-registry',whole_leaves=whole,sanitized=asan,optimized=opt,inputs={k:sha(v) for k,v in inputs.items()},registry=sha(registry),toolchain=identity,cpp=cpp,swift=swift,original=p.sha256,edges=edges,root_sites=root_sites)
key = sha(json.dumps(certificate,sort_keys=True).encode())
cache = root/'work/native-crt-exit-registry-cache'; cache.mkdir(parents=True,exist_ok=True)
destination = cache/key
with (cache/(key+'.lock')).open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not destination.exists():
        temporary = Path(tempfile.mkdtemp(prefix=key+'.',dir=cache))
        try:
            for name,data in inputs.items():
                path=temporary/'snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o444)
            (temporary/'ClawCanonicalDispatch.h').write_bytes(registry)
            (temporary/'Bridge.h').write_bytes(inputs['Tests/NativeCrtExitRegistry/Bridge.h'])
            env=dict(os.environ)
            for name in ('CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','LIBRARY_PATH','SDKROOT'): env.pop(name,None)
            include=str(temporary/'snapshot/Sources')
            objects=[]
            # Exactly one compiler child at a time; no shared writable objects.
            for source in cpp_sources:
                obj=temporary/(Path(source).stem+'.o')
                subprocess.run([identity['clang'],*cpp,'-I',include,'-c',str(temporary/'snapshot'/source),'-o',str(obj)],check=True,env=env)
                objects.append(str(obj))
            subprocess.run([identity['swift'],*swift,'-import-objc-header',str(temporary/'Bridge.h'),'-I',include,*[str(temporary/'snapshot'/s) for s in swift_sources],*objects,'-lc++','-o',str(temporary/'check')],check=True,env=env)
            negative_binaries={}
            if whole:
                original=inputs['Sources/StaticExitRegistrationsRuntime.cpp'].decode()
                mutations={
                    'callback':('item->callback','(item->callback ^ 4u)'),
                    'parentPC':('cpu.eip = function + 0x05;','cpu.eip = function + 0x06;'),
                    'argumentStore':('run.put(cpu.esp, item->callback);','/* missing actual PUSH callback store */'),
                    'returnStore':('run.put(child.esp, returnPC);','/* missing actual CALL return store */'),
                    'frame':('child.esp -= 0x04;','child.esp -= 0x08;'),
                    'bodyEAX':('return cpu.eax;','cpu.eax ^= 1u; return cpu.eax;'),
                    'cleanupECX':('cpu.ecx = run.get(cpu.esp);','cpu.ecx = 0;'),
                    'cleanupFlags':('cpu.eflags = addFlags(cpu.eflags, previousESP, 0x04, cpu.esp);','cpu.eflags = 2;'),
                }
                baseline_objects=[o for o in objects if Path(o).stem!='StaticExitRegistrationsRuntime']
                for kind,(before,after) in mutations.items():
                    assert before in original
                    mutated=original.replace(before,after)
                    candidate=temporary/('negative-'+kind+'.cpp');candidate.write_text(mutated)
                    obj=temporary/('negative-'+kind+'.o')
                    subprocess.run([identity['clang'],*cpp,'-I',include,'-c',str(candidate),'-o',str(obj)],check=True,env=env)
                    executable=temporary/('negative-'+kind)
                    subprocess.run([identity['swift'],*swift,'-import-objc-header',str(temporary/'Bridge.h'),'-I',include,*[str(temporary/'snapshot'/s) for s in swift_sources],*baseline_objects,str(obj),'-lc++','-o',str(executable)],check=True,env=env)
                    negative_binaries[kind]=dict(binary=sha(executable.read_bytes()),source=sha(candidate.read_bytes()))
            (temporary/'certificate.json').write_text(json.dumps(dict(certificate=certificate,binary=sha((temporary/'check').read_bytes()),negative_binaries=negative_binaries),indent=2))
            os.rename(temporary,destination)
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    saved=json.loads((destination/'certificate.json').read_text())
    assert saved['certificate'] == json.loads(json.dumps(certificate)) and saved['binary'] == sha((destination/'check').read_bytes())
    for kind,artifact in saved['negative_binaries'].items():
        assert artifact['binary']==sha((destination/('negative-'+kind)).read_bytes())
        assert artifact['source']==sha((destination/('negative-'+kind+'.cpp')).read_bytes())
reference_dir=root/'work/native-crt-exit-registry-check/frozen-v1'
provenance_path=reference_dir/'provenance.json'
provenance_bytes=provenance_path.read_bytes()
assert sha(provenance_bytes)=='45c1fb281c84cd54a5adbd891177f1c79d551b5dc42be917e3ec80c2ce5a4e84', 'reviewed frozen-v1 provenance changed'
provenance=json.loads(provenance_bytes)
assert provenance['status']=='PASS' and provenance['programSha256']==p.sha256
reports=[]
negative_reports=[]
assert not whole or len(saved['negative_binaries'])==8
scope_name='whole' if whole else 'direct'
snapshot_dir=check_dir/('crt-native-'+scope_name+'-snapshots')/('sanitized' if asan else 'optimized' if opt else 'debug')
for profile in provenance['profiles']:
    path=reference_dir/(profile['name']+'.json.gz')
    assert sha(path.read_bytes())==profile['sha256'],'immutable reference changed'
    with tempfile.NamedTemporaryFile(prefix='crt-reference-',suffix='.json',dir=cache,delete=False) as decoded:
        decoded_path=Path(decoded.name)
        with gzip.open(path,'rb') as reference:
            shutil.copyfileobj(reference,decoded)
    try:
        if whole and not reports:
            for kind in saved['negative_binaries']:
                negative=json.loads(capture([str(destination/('negative-'+kind)),str(decoded_path),'--negative-leaf',kind]))
                assert negative['status']=='pass' and negative['negative_leaf']==kind
                negative_reports.append(negative)
                print(json.dumps(negative),flush=True)
        control_args=(['--controls'] if not reports else [])+(['--whole'] if whole else [])
        output=subprocess.check_output([str(destination/'check'),str(decoded_path),*control_args,'--snapshot-dir',str(snapshot_dir)],text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        replay=json.loads(output.strip().splitlines()[-1]);assert replay['status']=='pass'
        replay['reference_sha256']=profile['sha256']
        native_path=snapshot_dir/(profile['name']+'-native.json')
        native_bytes=native_path.read_bytes();native=json.loads(native_bytes)
        native_pages=[]
        for page in native['pages']:
            raw=bytes.fromhex(page['bytes']);assert len(raw)==4096 and sha(raw)==page['sha256']
            native_pages.append(raw)
        reconstructed={}
        for index,state in enumerate(native['states']):
            memory=state['memory'];assert memory['parent']==(index-1 if index else None)
            for address,pid in memory['pageChanges']:reconstructed[address]=native_pages[pid]
            for region in memory['ranges']:
                full=b''.join(reconstructed[a] for a in range(region['address'],region['address']+region['size'],4096))
                assert len(full)==region['size'] and sha(full)==region['sha256'],'native snapshot disk roundtrip failed'
        assert len(native['states'])==replay['observations']
        replay['native_snapshot_sha256']=sha(native_bytes)
        replay['native_snapshot']=str(native_path)
        reports.append(replay);print(output.strip(),flush=True)
    finally: decoded_path.unlink()
    assert sha(path.read_bytes())==profile['sha256'],'reference changed during replay'
assert provenance_path.read_bytes()==provenance_bytes
assert len(reports)==21
if whole: assert sum(r['native_controls'] for r in reports)==40 and len(negative_reports)==8
if whole: assert tuple(sum(r[k] for r in reports) for k in ('roots','leaf_roots','physical_events','observed_source_entries','observations','compared_reference_states'))==(797,756,2616,3070,11366,11340)
if not whole: assert tuple(sum(r[k] for r in reports) for k in ('roots','physical_events','observed_source_entries','observations','native_controls'))==(41,103,49,298,37)
report=dict(schema=1,command='native-crt-exit-registry',status='pass',whole_leaves=whole,sanitized=asan,optimized=opt,cache_key=key,profiles=reports,negative_leaf_controls=negative_reports,reference_provenance_sha256=sha(provenance_bytes),certificate=str(destination/'certificate.json'),certificate_sha256=sha((destination/'certificate.json').read_bytes()),scope=root_sites)
report_path=check_dir/('crt-native-'+scope_name+'-'+('sanitized' if asan else 'optimized' if opt else 'debug')+'-report.json')
report['report_path']=str(report_path)
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
PYCODE
