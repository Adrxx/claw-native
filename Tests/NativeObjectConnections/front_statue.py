"""FrontStatue scene wiring against the hash-verified original.

Primary callback, crate state machine, binding and animation execute original
instructions. Downstream hit comparison cuts at the existing scene factory and
goodie initialization owners on the ORIGINAL side only; native uses real owners.
We compare crate-selected creation parameters and subsequent source physics writes,
not the already-owned goodie constructor's internals or live Level 5 acceptance.
"""
import json
import struct
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import ROOT, claw
from Tests.NativeObjectConnections.rez import entries, verify_assets
OBSERVE = {0x471530:False,0x4c7fa0:True,0x4f63ec:False,0x4c8160:True,0x4c81b0:True,0x40f680:True,0x4c82a0:True}

def prepare(directory):
    root=directory.resolve()/'resources';root.mkdir(exist_ok=True)
    def link_tree(target,source):
        assert target.parent.resolve().is_relative_to(root)
        if source.is_dir():
            if target.is_symlink():target.unlink()
            target.mkdir(exist_ok=True)
            for child in source.iterdir():link_tree(target/child.name,child)
        elif not target.exists():target.symlink_to(source.resolve())
    for child in (ROOT/'App/GameData').iterdir():link_tree(root/child.name,child)
    found=[]
    for name,payload in entries():
        if name=='LEVEL5/WORLDS/WORLD.WWD':(directory/'WORLD5.WWD').write_bytes(payload)
        if name.startswith('LEVEL5/IMAGES/STATUE/'):
            target=root/'LEVEL1'/name.removeprefix('LEVEL5/');target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.is_symlink();target.write_bytes(payload);found.append(name)
    assert len(found)==10
    (directory/'physical-assets.json').write_text(json.dumps(dict(sha256=verify_assets(),files=found),indent=2)+'\n')

def string(machine,pointer):
    out=bytearray()
    for i in range(256):
        b=machine.read(pointer+i,1)
        if b==b'\0':return out.decode('ascii')
        out+=b
    raise AssertionError('Unterminated name')

def machine_from(profile):
    machine=Machine(claw(),0x10000000,4096)
    mapped={page for start,end,_ in machine.uc.mem_regions() for page in range(start,end+1,4096)}
    def map_span(address,count):
        for page in range(address&~4095,(address+count+4095)&~4095,4096):
            if page not in mapped:
                machine.uc.mem_map(page,4096);mapped.add(page)
    original={a:machine.read(a,n) for a,n in [(0x513740,40),(0x5228dc,9),(0x510020,4)]}
    for segment in profile['segments']:
        data=bytes.fromhex(segment['hex']);map_span(segment['address'],len(data));machine.write(segment['address'],data)
    for address,data in original.items():assert machine.read(address,len(data))==data,f'Original metadata differs at {address:#x}'
    return machine,map_span

def reference(profile):
    machine,map_span=machine_from(profile)
    def write(address,*words):machine.write(address,struct.pack('<'+'I'*len(words),*(v&0xffffffff for v in words)))
    allocations=iter(profile['allocations']);bindings={(b['receiver'],b['name']):b['token'] for b in profile['resourceBindings']}
    calls,services=[],[]
    for function in OBSERVE:machine.observe(function,lambda m,a:calls.append([a,m.register(UC_X86_REG_ECX) if OBSERVE[a] else 0]))
    machine.intercept(0x4a48e0);machine.intercept(0x4f6286)
    def external(m,address):
        sp=m.register(UC_X86_REG_ESP)
        if address==0x4a48e0:
            row=next(allocations);size=m.words(sp+4,1)[0];assert row['count']==size
            map_span(row['token'],size);m.write(row['token'],b'\xcc'*size)
            services.append(['malloc',row['token'],size]);m.return_from_external(row['token'],0)
        elif address==0x4f6286:
            name,out=m.words(sp+4,2);receiver=m.register(UC_X86_REG_ECX);key=string(m,name);token=bindings[(receiver,key)]
            write(out,token);services.append(['registry',receiver,key,token]);m.return_from_external(int(token!=0),8)
        else:raise AssertionError(hex(address))
    machine.on_external=external;outputs=[]
    for step in profile['steps']:
        calls.clear();services.clear()
        for address,value in step['writes']:write(address,value)
        done=machine.call(step['callback'],arguments=[step['actor']]);assert done.completed,done
        outputs.append(dict(label=step['label'],calls=list(calls) if step['callback']==0x471780 else [],services=list(services) if step['callback']==0x471780 else [],spans=[dict(address=s['address'],hex=machine.read(s['address'],s['count']).hex()) for s in step['spans']]))
    assert next(allocations,None) is None
    return dict(steps=outputs)

def hit_reference(profile):
    machine,map_span=machine_from(profile)
    def write(address,*words):machine.write(address,struct.pack('<'+'I'*len(words),*(x&0xffffffff for x in words)))
    def word(address):return machine.words(address,1)[0]
    seed=profile['seed'];created=iter(profile['created']);rows=[];calls=[]
    bindings={(b['receiver'],b['name']):b['token'] for b in profile['resourceBindings']}
    for address in (0x4c8da0,0x40e690,0x4a3050,0x4f6286):machine.intercept(address)
    def external(m,address):
        nonlocal seed
        sp=m.register(UC_X86_REG_ESP)
        if address==0x4a3050:
            seed=(seed*214013+2531011)&0xffffffff;m.return_from_external((seed>>16)&0x7fff,0)
        elif address==0x4f6286:
            name,out=m.words(sp+4,2);key=string(m,name);receiver=m.register(UC_X86_REG_ECX);token=bindings.get((receiver,key),0)
            write(out,token);m.return_from_external(int(token!=0),8)
        elif address==0x4c8da0:
            a=list(m.words(sp+4,6));row=next(created);rows.append(row);assert a[0]==1 and a[4:]==[0x522cc0,0x40000]
            calls.append([m.register(UC_X86_REG_ECX),*a])
            for token,size in ((row['actor'],0x1b4),(row['state'],0x174),(row['private'],0x1a0)):
                map_span(token,size);m.write(token,bytes(size))
            write(row['actor']+0x4c,*a[1:3]);write(row['actor']+0x64,a[3]);write(row['actor']+0x6c,row['state'])
            write(row['state']+0x10,0x40e690);m.return_from_external(row['actor'],24)
        elif address==0x40e690:
            actor=m.words(sp+4,1)[0];row=next(r for r in rows if r['actor']==actor);write(row['state']+0x18,row['private']);m.return_from_external(1,0)
        else:raise AssertionError(hex(address))
    machine.on_external=external
    done=machine.call(0x4717e0,arguments=[profile['actor']]);assert done.completed,done
    assert next(created,None) is None
    effects=[]
    for row in rows:
        actor,private=row['actor'],row['private']
        effects.append(dict(actor=actor,position=[word(actor+o) for o in (0x4c,0x50,0x64)],physics=(machine.read(private+0x40,8)+machine.read(private+0x50,24)).hex(),item=word(private+0x184),image=word(actor+0x170),frame=word(actor+0x174)))
    return dict(calls=calls,effects=effects,seed=seed,spans=[dict(address=s['address'],hex=machine.read(s['address'],s['count']).hex()) for s in profile['spans']])

def compare(directory):
    source=json.loads((directory/'front-native-input.json').read_text());native=json.loads((directory/'front-native-output.json').read_text())
    original=dict(profiles=[reference(p) for p in source['profiles']],hits=[hit_reference(p) for p in source['hits']],sha256=claw().sha256)
    (directory/'front-original-output.json').write_text(json.dumps(original,indent=2)+'\n');comparisons=0
    for expected,actual in zip(original['profiles'],native['profiles'],strict=True):
        for ref,got in zip(expected['steps'],actual['steps'],strict=True):
            for key in ('label','calls','services','spans'):assert ref[key]==got[key],(got['label'],key,ref[key] if key!='spans' else 'see original output',got[key] if key!='spans' else 'see native output')
            comparisons+=1
    for ref,got in zip(original['hits'],native['hits'],strict=True):
        for key in ('calls','effects','seed','spans'):assert ref[key]==got[key],('downstream pickup',key,ref[key],got[key])
        assert got['effects'];comparisons+=1
    assert len(native['hits'])==2
    trace=native['trace'];positions=[trace.index(e) for e in ['loadGridObject','scene.gameplay','ClawNativeFrontStatue','0x471780']];assert positions==sorted(positions)
    assert all(native['controls'].values()),native['controls'];assert native['faults']==0 and not native['unresolvedDependencies']
    return dict(original_callback='0x471780',native_owner='ClawNativeFrontStatue',comparisons=comparisons,exercised_service_edges=['loadGridObject -> scene gameplay -> ClawNativeFrontStatue -> 0x471780 -> canonical 0x471530','0x471530 -> 0x4c7fa0 -> scene CrateHit registry -> 0x4f63ec -> shared ClawNativeMfcMemory -> 0x4c8160','0x471780 -> descriptor +0x54/+0x64 -> scene 0x4717e0 -> shared crate/loot/goodie owners','following FrontCrate 0x471720 -> shared 0x52a194 and 0x4717e0 pickup effects'],controls=native['controls'],faults=native['faults'],unresolved_dependencies=native['unresolvedDependencies'],scope='Host wiring only; original factory/goodie initialization boundary for downstream physics; no live Level 5 promotion')
