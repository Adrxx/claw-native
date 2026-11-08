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
addresses = {0x50257f,0x503510,0x4a56e0,0x502301,0x50210b,0x4f5e89,0x4f5133,0x50228f,0x503420,0x502e47,0x502e95,0x502f05,0x50335e,0x503167,0x502fb6,0x502ff8,0x4a4a20,0x502335,0x502369,0x502f84,0x502f26,0x4a48c0,0x501f01,0x501fde}
manifest_bytes = {p:p.read_bytes() for p in gen_project.FAMILIES.glob('*.json')}
exclusions = gen_project.EXCLUDE_FILE.read_bytes()
rows = gen_project.canonical_inventory([json.loads(v) for v in manifest_bytes.values()], json.loads(exclusions))[2]
rows = [r for r in rows if r['address'] in addresses]
assert {r['address'] for r in rows} == addresses, 'manager and byte fill must be admitted'
registry = gen_project.canonical_dispatch_text(rows).encode()
families = {r['family'] for r in rows}
selected = {p:v for p,v in manifest_bytes.items() if json.loads(v).get('id') in families}
cpp_sources = sorted({s for v in selected.values() for s in json.loads(v)['sources']})
swift_sources = ['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeMfcApplicationObject/main.swift']
paths = cpp_sources + swift_sources + ['Tests/NativeMfcApplicationObject/Bridge.h','scripts/check-native-mfc-application-object.sh','tools/claw/gen_project.py','Tests/NativeMfcApplicationObject/reference.py','Tests/NativeSourceEdges/validate_edges.py','work/native-mfc-application-object-check/profile-index.json']
paths += [str(p.relative_to(root)) for p in root.joinpath('Sources').rglob('*') if p.suffix in ('.h','.hpp') and p != gen_project.DISPATCH_HEADER]
inputs = {str(p.relative_to(root)):v for p,v in selected.items()}
inputs[str(gen_project.EXCLUDE_FILE.relative_to(root))] = exclusions
inputs.update({p:Path(p).read_bytes() for p in paths})
# Check the reviewed new finite CALL metadata against the hash-checked original.
# This validates original bytes; it never generates expected native observations.
p = claw()
host = inputs['Sources/ClawNativeCanonicalHost.swift'].decode()
table = host.split('private static let managerEdges: [ManagerEdge] = [',1)[1].split('\n    ]',1)[0]
pattern = r'\.init\(root: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+), delta: (\d+), operation: \.(\w+)\)'
edges = re.findall(pattern, table)
assert len(edges) == 15 and len({(r,c) for r,_,c,_,_,_ in edges}) == 15
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_EBX, X86_REG_ESP
md = Cs(CS_ARCH_X86,CS_MODE_32); md.detail = True
def validate_edges(edges):
    assert len(edges) == 15 and len({(r,c) for r,_,c,_,_,_ in edges}) == 15
    for r,pc,cont,target,delta,op in edges:
        r,pc,cont,target = (int(v,16) for v in (r,pc,cont,target))
        assert r in (0x502fb6,0x502ff8)
        section = next(s for s in p.sections if s.address <= r < s.address+len(s.data))
        instructions = list(md.disasm(section.data[r-section.address:cont-section.address],r))
        instruction = next((i for i in instructions if i.address == pc),None)
        assert instruction and instruction.mnemonic == 'call' and pc+instruction.size == cont, (hex(pc),'CALL/continuation')
        operand = instruction.operands[0]
        if op in ('lock','failedLock'):
            assert target == 0x5469c4 and operand.type == X86_OP_REG and operand.reg == X86_REG_EBX
        elif op in ('fill','missingThrow'):
            assert operand.type == X86_OP_IMM and operand.imm == target
        else:
            assert operand.type == X86_OP_MEM and operand.mem.base == operand.mem.index == 0 and operand.mem.disp == target
validate_edges(edges)
for field,value in [(0,'0x502ff8'),(1,'0x502fd9'),(2,'0x502fdf'),(3,'0x546a91')]:
    modified=[list(e) for e in edges]; modified[0][field]=value
    try: validate_edges(modified)
    except (AssertionError,StopIteration): pass
    else: raise AssertionError('invalid original edge accepted')
tls_table=host.split('private static let tlsEdges: [TLSEdge] = [',1)[1].split('\n    ]',1)[0]
tls_edges=re.findall(r'\.init\(caller: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+|0), delta: (\d+), count: (\d+)\)',tls_table)
assert len(tls_edges)==16
for caller,pc,cont,target,delta,count in tls_edges:
    caller,pc,cont,target=(int(v,16) for v in (caller,pc,cont,target))
    section=next(s for s in p.sections if s.address<=caller<s.address+len(s.data))
    instruction=next(i for i in md.disasm(section.data[caller-section.address:cont-section.address],caller) if i.address==pc)
    assert instruction.mnemonic=='call' and instruction.address+instruction.size==cont
    operand=instruction.operands[0]
    if target==0:
        assert caller==0x50335e and pc==0x5033ba and operand.type==X86_OP_MEM and operand.mem.base==X86_REG_ESP and operand.mem.index==0 and operand.mem.disp==12
    elif target in (0x502fb6,0x502ff8,0x502f84,0x502f26,0x4f50fd,0x4a4a20):
        assert operand.type==X86_OP_IMM and operand.imm==target
    else:
        assert operand.type==X86_OP_MEM and operand.mem.base==operand.mem.index==0 and operand.mem.disp==target
namespace={'__file__':str(root/'Tests/NativeSourceEdges/validate_edges.py'),'__name__':'snapshot_validator'}
exec(compile(inputs['Tests/NativeSourceEdges/validate_edges.py'],'frozen-edge-validator','exec'),namespace)
factory_edges=[r for r in namespace['contracts'](host) if r['root'] in (0x502335,0x502369)]
assert len(factory_edges)==8
namespace['check'](factory_edges,p,{r['address']:r for r in rows})
module_edges=namespace['module_contracts'](host)
namespace['check_module'](module_edges,p,{r['address']:r for r in rows})
application_edges=namespace['check_application'](host,p,{r['address']:r for r in rows})
application_object_edges=namespace['check_application_object'](host,p,{r['address']:r for r in rows})
lock_table=host.split('private static let locksEdges: [LocksEdge] = [',1)[1].split('\n    ]',1)[0]
lock_edges=re.findall(r'\.init\(caller: (0x[0-9a-f]+), callPC: (0x[0-9a-f]+), continuation: (0x[0-9a-f]+), target: (0x[0-9a-f]+), delta: (\d+), count: (\d+)\)',lock_table)
assert len(lock_edges)==7
for caller,pc,cont,target,delta,count in lock_edges:
    caller,pc,cont,target=(int(v,16) for v in (caller,pc,cont,target))
    section=next(s for s in p.sections if s.address<=caller<s.address+len(s.data))
    instruction=next(i for i in md.disasm(section.data[caller-section.address:cont-section.address],caller) if i.address==pc)
    assert instruction.mnemonic=='call' and instruction.address+instruction.size==cont
    operand=instruction.operands[0]
    if target==0x546aac:assert operand.type==X86_OP_REG and operand.reg==X86_REG_EBX
    else:assert operand.type==X86_OP_MEM and operand.mem.base==operand.mem.index==0 and operand.mem.disp==target

compiler_edges=[]
for caller,pc,cont in [(0x502335,0x50233a,0x50233f),(0x502369,0x50236e,0x502373)]:
    section=next(s for s in p.sections if s.address<=caller<s.address+len(s.data))
    instruction=next(i for i in md.disasm(section.data[caller-section.address:cont-section.address],caller) if i.address==pc)
    assert instruction.mnemonic=='call' and instruction.address+instruction.size==cont
    assert instruction.operands[0].type==X86_OP_IMM and instruction.operands[0].imm==0x4a48c0
    compiler_edges.append(dict(caller=caller,call=pc,continuation=cont,target=0x4a48c0))
# The root capability names are continuations of the original getter's CALLs.
root_sites=[]
for name,pc,function in [('managerInitialize',0x50337c,0x502fb6),('managerAllocate',0x50338d,0x502ff8),('tlsGet',0x502299,0x50335e),('tlsSet',0x5033c9,0x503167)]:
    continuation=int(re.search(r'case '+name+r' = (0x[0-9a-f]+)',host).group(1),16)
    actual_function=int(re.search(r'case \.'+name+r': return (0x[0-9a-f]+)',host).group(1),16)
    start=0x50228f if name=='tlsGet' else 0x50335e
    section=next(s for s in p.sections if s.address <= start < s.address+len(s.data))
    instructions=list(md.disasm(section.data[start-section.address:continuation-section.address],start))
    call=next(i for i in instructions if i.address==pc)
    assert call.mnemonic=='call' and call.address+call.size==continuation
    assert call.operands[0].type==X86_OP_IMM and call.operands[0].imm==actual_function==function
    root_sites.append(dict(site=name,call=pc,continuation=continuation,function=function))
asan = os.environ.get('CLAW_NATIVE_ASAN','1') == '1'
opt = os.environ.get('CLAW_NATIVE_OPTIMIZE','0') == '1'
identity = {k:capture(v) for k,v in {'clang':['xcrun','--find','clang++'],'swift':['xcrun','--find','swiftc'],'sdk':['xcrun','--show-sdk-path']}.items()}
identity['clang_version'] = capture([identity['clang'],'--version'])
identity['swift_version'] = capture([identity['swift'],'--version'])
cpp = ['-std=c++17','-ffp-contract=off','-isysroot',identity['sdk']]
swift = ['-sdk',identity['sdk']]
if asan: cpp += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']; swift += ['-sanitize=address']
if opt: cpp += ['-O2']; swift += ['-O']
certificate = dict(schema=1,command='native-mfc-application-object',sanitized=asan,optimized=opt,inputs={k:sha(v) for k,v in inputs.items()},registry=sha(registry),toolchain=identity,cpp=cpp,swift=swift,original=p.sha256,edges=edges,tls_edges=tls_edges,factory_edges=factory_edges,compiler_edges=compiler_edges,root_sites=root_sites,module_edges=module_edges,lock_edges=lock_edges,application_edges=application_edges,application_object_edges=application_object_edges)
assert all(Path(name).read_bytes()==data for name,data in inputs.items()), 'inputs changed during capture; rerun'
key = sha(json.dumps(certificate,sort_keys=True).encode())
cache = root/'work/native-mfc-application-object-cache'; cache.mkdir(parents=True,exist_ok=True)
destination = cache/key
with (cache/(key+'.lock')).open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not destination.exists():
        temporary = Path(tempfile.mkdtemp(prefix=key+'.',dir=cache))
        try:
            for name,data in inputs.items():
                path=temporary/'snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o444)
            (temporary/'ClawCanonicalDispatch.h').write_bytes(registry)
            (temporary/'Bridge.h').write_bytes(inputs['Tests/NativeMfcApplicationObject/Bridge.h'])
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
import lzma
base=root/'work/native-mfc-application-object-check'
index_path=base/'profile-index.json'
assert sha(index_path.read_bytes())=='0889633df7b2a2befbe91f22119b1c1b7e1b3dddf4c2cf368ccfadd50b37ae82'
index=json.loads(index_path.read_bytes())
selected=os.environ.get('CLAW_NATIVE_PROFILE')
rows=index['shards'] if selected is None else [index['shards'][int(selected)]]
results=[]
for row in rows:
    compressed=(base/row['path']).read_bytes();assert sha(compressed)==row['sha256']
    logical=lzma.decompress(compressed);assert sha(logical)==row['logicalSha256']
    with tempfile.NamedTemporaryFile(suffix='.json') as f:
        f.write(logical);f.flush();del logical,compressed
        output=subprocess.check_output([str(destination/'check'),f.name,str(row['index'])],text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
    replay=json.loads(output.strip().splitlines()[-1]);assert replay['status']=='pass'
    assert replay['profile_index']==row['index'] and replay['profile_name']==row['name'] and replay['roots']==row['roots']
    assert replay['reference_entries']==row['childEntries'] and replay['reference_physical_events']==row['physicalEvents']
    assert replay['returned_roots']==row['completedRoots'] and replay['returned_roots']+replay['stopped_roots']==replay['roots']
    assert replay['whole_cwinapp_executed']==(replay['returned_roots']>0) and not replay['catch_executed']
    assert replay['assertions']==replay['original_assertions']+replay['native_controls']
    results.append(replay);print('PASS profile',row['index'],row['name'],flush=True)
replay={k:sum(r[k] for r in results) for k in ('profiles','roots','physical_events','observed_entries','reference_only_entries','native_unobserved_entries','assertions','original_assertions','native_controls','missing_native_prefixes','later_original_physical_events','later_original_entries','reference_entries','reference_physical_events','returned_roots','stopped_roots')}
replay.update(status='pass',whole_cwinapp_executed=replay['returned_roots']>0,catch_executed=False,unobserved_sites=[site for r in results for site in r['unobserved_sites']])
replay['missing_native_sites']=[site for r in results for site in r['missing_native_sites']]
assert len(replay['missing_native_sites'])==replay['missing_native_prefixes']
assert all(site['function']==0x4f50fd for site in replay['missing_native_sites'])
assert replay['physical_events']+replay['later_original_physical_events']==replay['reference_physical_events']
assert replay['observed_entries']+replay['reference_only_entries']+replay['native_unobserved_entries']+replay['later_original_entries']==replay['reference_entries']
if selected is None:
    expected=dict(profiles=61,roots=62,returned_roots=21,stopped_roots=41,physical_events=1358,reference_physical_events=1366,observed_entries=1356,reference_only_entries=316,native_unobserved_entries=26,reference_entries=1698,missing_native_prefixes=8,later_original_physical_events=8,later_original_entries=0,original_assertions=571962)
    assert all(replay[k]==v for k,v in expected.items())
    assert replay['native_controls']>=165
    from collections import Counter
    assert Counter(s['function'] for s in replay['unobserved_sites'] if s['original_defined'])=={0x4f6a9a:62,0x50354d:62,0x503167:74,0x502e47:40,0x4f5e89:52,0x4f5133:26}
    assert Counter(s['function'] for s in replay['unobserved_sites'] if not s['original_defined'])=={0x50210b:26}
assert all(Path(name).read_bytes()==data for name,data in inputs.items()),'captured inputs changed during replay'
report=dict(schema=1,command='native-mfc-application-object',status='pass',complete_reference=selected is None,sanitized=asan,optimized=opt,cache_key=key,reference_sha256=sha(index_path.read_bytes()),replay=replay,certificate=str(destination/'certificate.json'),certificate_sha256=sha((destination/'certificate.json').read_bytes()))
report_path=base/('profile-'+selected+'-report.json' if selected is not None else 'sanitized-report.json' if asan else 'optimized-report.json' if opt else 'debug-report.json')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
PY
