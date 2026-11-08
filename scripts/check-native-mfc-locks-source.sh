#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
exec work/test-env/bin/python - "$@" <<'PY'
import fcntl, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from tools.claw import gen_project
from Tests.clawparity.program import claw
root = Path.cwd()
def sha(b): return hashlib.sha256(b).hexdigest()
def capture(args): return subprocess.check_output(args, text=True).strip()
assert not os.environ.get('CLAW_NATIVE_CXXFLAGS', '').strip(), 'use fixed ASAN/OPTIMIZE modes'
addresses = {0x502e47,0x502e95,0x502f05}
manifest_bytes = {p:p.read_bytes() for p in gen_project.FAMILIES.glob('*.json')}
exclusions = gen_project.EXCLUDE_FILE.read_bytes()
rows = gen_project.canonical_inventory([json.loads(v) for v in manifest_bytes.values()], json.loads(exclusions))[2]
rows = [r for r in rows if r['address'] in addresses]
assert {r['address'] for r in rows} == addresses, 'lock source family must be admitted'
registry = gen_project.canonical_dispatch_text(rows).encode()
families = {r['family'] for r in rows}
selected = {p:v for p,v in manifest_bytes.items() if json.loads(v).get('id') in families}
cpp_sources = sorted({s for v in selected.values() for s in json.loads(v)['sources']})
swift_sources = ['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcLocks.swift','Tests/NativeMfcLocksSource/main.swift']
paths = cpp_sources + swift_sources + ['Tests/NativeMfcLocksSource/Bridge.h','scripts/check-native-mfc-locks-source.sh','tools/claw/gen_project.py','Tests/NativeMfcLocksSource/reference.py']
paths += [str(p.relative_to(root)) for p in root.joinpath('Sources').rglob('*') if p.suffix in ('.h','.hpp') and p != gen_project.DISPATCH_HEADER]
inputs = {str(p.relative_to(root)):v for p,v in selected.items()}
inputs[str(gen_project.EXCLUDE_FILE.relative_to(root))] = exclusions
inputs.update({p:Path(p).read_bytes() for p in paths})
# Hash-check the original first; validate every declared real CALL/continuation.
p = claw()
host = inputs['Sources/ClawNativeCanonicalHost.swift'].decode()
table = host.split('private static let locksEdges: [LocksEdge] = [',1)[1].split('\n    ]',1)[0]
pattern = r'\.init\(caller: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+), delta: (\d+), count: (\d+)\)'
edges = re.findall(pattern, table)
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_EBX
md = Cs(CS_ARCH_X86,CS_MODE_32); md.detail = True
def instruction_at(start,pc,cont):
    section=next(s for s in p.sections if s.address <= start < s.address+len(s.data))
    instruction=next(i for i in md.disasm(section.data[start-section.address:cont-section.address],start) if i.address==pc)
    assert instruction.mnemonic=='call' and instruction.address+instruction.size==cont
    return instruction
def validate_edges(edges):
    assert len(edges)==7 and len({row[2] for row in edges})==7
    for caller,pc,cont,target,delta,count in edges:
        caller,pc,cont,target=(int(v,16) for v in (caller,pc,cont,target))
        assert caller in addresses
        operand=instruction_at(caller,pc,cont).operands[0]
        if target==0x546aac: assert operand.type==X86_OP_REG and operand.reg==X86_REG_EBX
        else: assert operand.type==X86_OP_MEM and operand.mem.base==operand.mem.index==0 and operand.mem.disp==target
validate_edges(edges)
for field,value in [(0,'0x502f05'),(1,'0x502e5b'),(2,'0x502e61'),(3,'0x546abd')]:
    changed=[list(e) for e in edges]; changed[0][field]=value
    try: validate_edges(changed)
    except (AssertionError,StopIteration): pass
    else: raise AssertionError('invalid original edge accepted')
root_sites=[]
for name,start,pc,function in [('locksInitialize',0x502e95,0x502ea3,0x502e47),('locksAcquire',0x503426,0x50343f,0x502e95),('locksRelease',0x503426,0x503473,0x502f05),('locksCatchRelease',0x503454,0x503456,0x502f05)]:
    cont=int(re.search(r'case '+name+r' = (0x[0-9a-f]+)',host).group(1),16)
    operand=instruction_at(start,pc,cont).operands[0]
    assert operand.type==X86_OP_IMM and operand.imm==function
    root_sites.append(dict(site=name,call=pc,continuation=cont,function=function,executed=name!='locksCatchRelease'))
asan = os.environ.get('CLAW_NATIVE_ASAN','1') == '1'
opt = os.environ.get('CLAW_NATIVE_OPTIMIZE','0') == '1'
identity = {k:capture(v) for k,v in {'clang':['xcrun','--find','clang++'],'swift':['xcrun','--find','swiftc'],'sdk':['xcrun','--show-sdk-path']}.items()}
identity['clang_version'] = capture([identity['clang'],'--version'])
identity['swift_version'] = capture([identity['swift'],'--version'])
cpp = ['-std=c++17','-ffp-contract=off','-isysroot',identity['sdk']]
swift = ['-sdk',identity['sdk']]
if asan: cpp += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']; swift += ['-sanitize=address']
if opt: cpp += ['-O2']; swift += ['-O']
certificate = dict(schema=1,command='native-mfc-locks-source',sanitized=asan,optimized=opt,inputs={k:sha(v) for k,v in inputs.items()},registry=sha(registry),toolchain=identity,cpp=cpp,swift=swift,original=p.sha256,edges=edges,root_sites=root_sites)
key = sha(json.dumps(certificate,sort_keys=True).encode())
cache = root/'work/native-mfc-locks-source-cache'; cache.mkdir(parents=True,exist_ok=True)
destination = cache/key
with (cache/(key+'.lock')).open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not destination.exists():
        temporary = Path(tempfile.mkdtemp(prefix=key+'.',dir=cache))
        try:
            for name,data in inputs.items():
                path=temporary/'snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o444)
            (temporary/'ClawCanonicalDispatch.h').write_bytes(registry)
            (temporary/'Bridge.h').write_bytes(inputs['Tests/NativeMfcLocksSource/Bridge.h'])
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
            (temporary/'certificate.json').write_text(json.dumps(dict(certificate=certificate,binary=sha((temporary/'check').read_bytes())),indent=2))
            os.rename(temporary,destination)
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    saved=json.loads((destination/'certificate.json').read_text())
    assert saved['certificate'] == json.loads(json.dumps(certificate)) and saved['binary'] == sha((destination/'check').read_bytes())
reference=root/'work/native-mfc-locks-source-check/reference.json'
assert reference.exists(), 'run the independent original-only reference first'
reference_hash=sha(reference.read_bytes())
assert reference_hash == '27414dcf82c0bfe805514d7e278e773f7a790ef3816e43966f462270039a1aed', 'independently frozen reference bytes changed'
output=subprocess.check_output([str(destination/'check'),str(reference)],text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
assert sha(reference.read_bytes()) == reference_hash, 'reference changed during replay'
replay=json.loads(output.strip().splitlines()[-1])
assert replay['status'] == 'pass' and (replay['profiles'],replay['roots'],replay['physical_events'],replay['reference_entries']) == (22,76,195,96)
assert replay['assertions'] >= 2500 and replay['native_controls'] == 23
assert (replay['observed_entries'],replay['reference_only_entries']) == (76,20)
assert len(replay['unobserved_sites']) == replay['reference_only_entries']
assert all(s['function']==0x502e47 and s['return_pc']==0x502ea8 for s in replay['unobserved_sites'])
assert len({(s['profile'],s['root_step'],s['frame']) for s in replay['unobserved_sites']})==20
report=dict(schema=1,command='native-mfc-locks-source',status='pass',sanitized=asan,optimized=opt,cache_key=key,reference_sha256=reference_hash,replay=replay,certificate=str(destination/'certificate.json'),certificate_sha256=sha((destination/'certificate.json').read_bytes()))
report_path=root/'work/native-mfc-locks-source-check'/('sanitized-report.json' if asan else 'optimized-report.json' if opt else 'debug-report.json')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(output.strip())
print(json.dumps(report))
PY
