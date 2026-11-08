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
addresses = {0x502fb6, 0x502ff8, 0x4a4a20}
manifest_bytes = {p:p.read_bytes() for p in gen_project.FAMILIES.glob('*.json')}
exclusions = gen_project.EXCLUDE_FILE.read_bytes()
rows = gen_project.canonical_inventory([json.loads(v) for v in manifest_bytes.values()], json.loads(exclusions))[2]
rows = [r for r in rows if r['address'] in addresses]
assert {r['address'] for r in rows} == addresses, 'manager and byte fill must be admitted'
registry = gen_project.canonical_dispatch_text(rows).encode()
families = {r['family'] for r in rows}
selected = {p:v for p,v in manifest_bytes.items() if json.loads(v).get('id') in families}
cpp_sources = sorted({s for v in selected.values() for s in json.loads(v)['sources']})
swift_sources = ['Sources/ClawTokenHeap.swift','Sources/ClawNativeCanonicalHost.swift','Sources/ClawNativeMfcLocks.swift','Sources/ClawNativeMfcMemory.swift','Tests/NativeMfcTlsManagerSource/main.swift']
paths = cpp_sources + swift_sources + ['Tests/NativeMfcTlsManagerSource/Bridge.h','scripts/check-native-mfc-tls-manager-source.sh','tools/claw/gen_project.py','Tests/NativeMfcTlsManagerSource/reference.py']
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
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_EBX
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
for row in rows:
    context=row['source_context']
    assert context.get('optional') and (context['input_mask'],context['output_mask'],context['preserve_mask']) == (0x7ff,0x7ff,{0x502fb6:0x462,0x502ff8:0x400,0x4a4a20:0x452}[row['address']])
# The root capability names are continuations of the original getter's CALLs.
root_sites=[]
for name,pc,function in [('managerInitialize',0x50337c,0x502fb6),('managerAllocate',0x50338d,0x502ff8)]:
    continuation=int(re.search(r'case '+name+r' = (0x[0-9a-f]+)',host).group(1),16)
    actual_function=int(re.search(r'case \.'+name+r': return (0x[0-9a-f]+)',host).group(1),16)
    section=next(s for s in p.sections if s.address <= 0x50335e < s.address+len(s.data))
    instructions=list(md.disasm(section.data[0x50335e-section.address:continuation-section.address],0x50335e))
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
certificate = dict(schema=1,command='native-mfc-tls-manager-source',sanitized=asan,optimized=opt,inputs={k:sha(v) for k,v in inputs.items()},registry=sha(registry),toolchain=identity,cpp=cpp,swift=swift,original=p.sha256,edges=edges,root_sites=root_sites)
key = sha(json.dumps(certificate,sort_keys=True).encode())
cache = root/'work/native-mfc-tls-manager-source-cache'; cache.mkdir(parents=True,exist_ok=True)
destination = cache/key
with (cache/(key+'.lock')).open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not destination.exists():
        temporary = Path(tempfile.mkdtemp(prefix=key+'.',dir=cache))
        try:
            for name,data in inputs.items():
                path=temporary/'snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o444)
            (temporary/'ClawCanonicalDispatch.h').write_bytes(registry)
            (temporary/'Bridge.h').write_bytes(inputs['Tests/NativeMfcTlsManagerSource/Bridge.h'])
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
reference=root/'work/native-mfc-tls-manager-source-check/reference.json'
assert reference.exists(), 'run the independent original-only reference first'
reference_hash=sha(reference.read_bytes())
assert reference_hash == 'f751b7a54babf84af3495f6511301e2bc465a2afc00c8437d69a22eebf0ef239', 'independently frozen reference bytes changed'
output=subprocess.check_output([str(destination/'check'),str(reference)],text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
assert sha(reference.read_bytes()) == reference_hash, 'reference changed during replay'
replay=json.loads(output.strip().splitlines()[-1])
assert replay['status'] == 'pass' and (replay['profiles'],replay['roots'],replay['physical_events'],replay['child_entries']) == (9,119,271,13)
assert replay['assertions'] >= 6117 and replay['native_controls'] > 0
report=dict(schema=1,command='native-mfc-tls-manager-source',status='pass',sanitized=asan,optimized=opt,cache_key=key,reference_sha256=reference_hash,replay=replay,certificate=str(destination/'certificate.json'),certificate_sha256=sha((destination/'certificate.json').read_bytes()))
report_path=root/'work/native-mfc-tls-manager-source-check'/('sanitized-report.json' if asan else 'optimized-report.json' if opt else 'debug-report.json')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(output.strip())
print(json.dumps(report))
PY
