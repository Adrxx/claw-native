"""Frozen original-only getter/setter source execution and physical owner evidence.

No native implementation, native result, or family golden is consumed. All code
children execute unchanged pinned CLAW.EXE; only physical imports are serviced.
"""
import hashlib
import json
import random
import struct
import sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_TOP, STACK_BASE, STACK_SIZE, CONTEXT_FIELDS, CONTEXT_REGISTERS
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.program import claw
from Tests.NativeMfcTlsManagerSource.reference import IMPORTS
from unicorn.x86_const import UC_X86_REG_ESP

GET, SET, INIT, SLOT = 0x50335e, 0x503167, 0x502fb6, 0x502ff8
STATIC, OWNER, PUBLICATION = 0x540af8, 0x53ec9c, 0x540af0
CHILDREN = (GET, SET, INIT, SLOT, 0x502335, 0x502369, 0x502f84,
            0x502f26, 0x4a4a20, 0x4a48c0, 0x501f01, 0x501fde, 0x4f50fd)
class Stop(Exception): pass

class Reference:
    def __init__(self, name):
        self.p=claw();self.m=Machine(self.p,0x62000000,0x100000)
        self.name=name;self.next_data=0x62000000;self.next_handle=0x78000000;self.next_tls=0
        self.managers=[STATIC];self.owners=[OWNER];self.blocks={};self.locals={};self.allocations=[]
        self.sections={};self.tls={};self.events=[];self.entries=[];self.steps=[];self.preparations=[]
        self.failure=None;self.set_false=False;self.current=None;self.pending_entries=[];self.return_observers=set()
        self.imports={s:self.m.import_stub[s] for s in IMPORTS}
        self.reverse={v:k for k,v in self.imports.items()}
        for s,(label,_) in IMPORTS.items():assert self.p.imports[s].split('!')[-1]==label
        self.initial=self.m.read(0x5408e0,0x210).hex()
        assert self.get(PUBLICATION)==0 and self.get(OWNER)==0
        self.m.on_external=self.external
        for address in CHILDREN:self.m.observe(address,self.observe)
    def put(self,a,v):self.m.write(a,struct.pack('<I',v))
    def get(self,a):return self.m.words(a,1)[0]
    def alloc(self,n,kind,zero=False):
        p=self.next_data;self.next_data=(p+n+15)&~15
        self.m.write(p,bytes([0 if zero else 0xcc])*n)
        self.allocations.append(dict(identity=len(self.allocations)+1,address=p,size=n,kind=kind,live=True))
        return p
    def retire(self,p):
        matches=[a for a in self.allocations if a['address']==p and a['live']]
        assert len(matches)==1;matches[0]['live']=False
    def cpu(self):return dict(zip(CONTEXT_FIELDS,[self.m.register(r) for r in CONTEXT_REGISTERS]+[self.m.fs_head]))
    def stack(self):return self.m.read(STACK_BASE,STACK_SIZE).hex()
    def snapshot(self):
        return dict(managerBytes={str(t):self.m.read(t,0x34).hex() for t in self.managers},
          ownerBytes={str(t):self.m.read(t,4).hex() for t in self.owners},ownerValue=self.get(OWNER),
          globals={str(PUBLICATION):self.get(PUBLICATION)},staticManagerBytes=self.m.read(STATIC,0x34).hex(),
          locals={str(t):n for t,n in sorted(self.locals.items())},
          localBytes={str(t):self.m.read(t,n).hex() for t,n in sorted(self.locals.items())},
          blocks=[dict(self.blocks[h]) for h in sorted(self.blocks)],
          blockBytes={str(b['data']):self.m.read(b['data'],b['size']).hex() for b in self.blocks.values()},
          allocations=[dict(a) for a in self.allocations],
          allocationBytes={str(a['address']):self.m.read(a['address'],a['size']).hex() for a in self.allocations},
          borrowedStorage=[dict(address=STATIC,size=0x34,kind='static-manager'),dict(address=OWNER,size=4,kind='slot-owner'),dict(address=PUBLICATION,size=4,kind='publication')],
          sections=[dict(self.sections[t]) for t in sorted(self.sections)],tlsIndices=sorted(self.tls),
          tlsValues={str(t):v for t,v in sorted(self.tls.items())},thread=1)
    def observe(self,m,address):
        sp=m.register(UC_X86_REG_ESP)
        argc={GET:1,SET:2,0x502f84:1,0x502f26:1,0x4a4a20:3,0x501fde:1}.get(address,0)
        entry=dict(function=address,frame=sp,returnPC=self.get(sp),arguments=list(m.words(sp+4,argc)),inputCPU=self.cpu(),stack=self.stack(),stackBefore=self.stack(),state=self.snapshot(),before=self.snapshot(),rootStep=len(self.steps))
        self.entries.append(entry);self.pending_entries.append(entry)
        pc=entry['returnPC']
        if pc not in self.return_observers:
            self.return_observers.add(pc);self.m.observe(pc,self.returned_child)
        if address==0x4f50fd:raise Stop('missing-exception')
    def returned_child(self,m,address):
        matches=[e for e in self.pending_entries if e['returnPC']==address]
        if matches:
            e=matches[-1];e.update(completed=True,outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot());self.pending_entries.remove(e)
    def external(self,m,target):
        s=self.reverse[target];count=IMPORTS[s][1];sp=m.register(UC_X86_REG_ESP);a=list(m.words(sp+4,count));r=0
        event=dict(function=s,target=target if s==0x5469c4 else s,importedTarget=target,frame=sp,stackPointer=sp,returnPC=self.get(sp),arguments=a,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps))
        fail=self.failure
        if s==0x546a90:
            if fail=='tls':r=0xffffffff
            else:r=self.next_tls;self.next_tls+=1;self.tls[r]=0
        elif s==0x546a7c:assert a[0] in self.tls;r=self.tls[a[0]]
        elif s==0x546a84:
            assert a[0] in self.tls
            if not self.set_false:self.tls[a[0]]=a[1];r=1
        elif s==0x546aa4:
            assert a[0]-28 in self.managers and a[0] not in self.sections
            self.sections[a[0]]=dict(section=a[0],owner=0,depth=0,initialized=1,entered=0,left=0)
        elif s in (0x546aac,0x546a9c):
            st=self.sections[a[0]]
            if s==0x546aac:st['depth']+=1;st['entered']+=1
            else:assert st['depth']>0;st['depth']-=1;st['left']+=1
            st['owner']=1 if st['depth'] else 0
        elif s==0x546b1c:
            assert a[0]==0x2002
            if fail!='global':
                r=self.next_handle;self.next_handle+=4;self.blocks[r]=dict(handle=r,data=self.alloc(a[1],'global'),size=a[1],flags=a[0],locks=0)
        elif s==0x5469c4:
            if a[0]:b=self.blocks[a[0]];b['locks']+=1;r=b['data']
        elif s==0x546a8c:
            r=next((h for h,b in self.blocks.items() if b['data']==a[0]),0);assert r or a[0]==0
        elif s==0x5469c8:
            b=self.blocks[a[0]];assert b['locks']>0;b['locks']-=1;r=int(b['locks']>0)
        elif s==0x546a88:
            b=self.blocks[a[0]];assert b['locks']==0 and a[2]==0x2002
            if fail!='global-realloc':
                old=b['data'];data=self.alloc(a[1],'global');m.write(data,m.read(old,min(a[1],b['size'])));self.retire(old);b.update(data=data,size=a[1],flags=a[2]);r=b['handle']
        elif s==0x546aa8:
            assert a[0] in (0,0x40)
            if not (fail=='container' and a[0]==0x40 and a[1]==16) and not (fail=='array' and a[0]==0):
                r=self.alloc(a[1],'local',bool(a[0]&0x40));self.locals[r]=a[1]
        elif s==0x546a80:
            assert a[0] in self.locals and a[2]==2
            if fail!='local-realloc':
                old=a[0];r=self.alloc(a[1],'local');m.write(r,m.read(old,min(self.locals[old],a[1])));self.retire(old);del self.locals[old];self.locals[r]=a[1]
        else:raise AssertionError(hex(s))
        if s in (0x546aa4,0x546aac,0x546a9c):r=0xa1b2c3d4
        m.return_from_external(r,4*count)
        event.update(result=r,completed=True,after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack());self.events.append(event)
    def call(self,f=GET,receiver=OWNER,args=None,label=None):
        args=([0x502335] if f==GET else []) if args is None else args
        i=len(self.steps);frame=STACK_TOP-0x100-i*0x40;seed=0x50335e+i*0x10001
        rng=random.Random(seed);self.m.write(STACK_BASE,rng.randbytes(STACK_SIZE))
        vals=[rng.getrandbits(32) for _ in CONTEXT_FIELDS];vals[2]=receiver;vals[7]=frame;vals[8]=f;vals[9]=rng.getrandbits(32)&0x8d5|2;vals[10]=0xffffffff
        preserve={GET:0x400,SET:0x442,INIT:0x462,SLOT:0x400}[f]
        pc={GET:0x50229e,SET:0x5033ce,INIT:0x503381,SLOT:0x503392}[f]
        c=NativeSourceContext(72,1,0x7ff,0x7ff,*vals,preserve,0,0)
        for j,v in enumerate([pc]+args):self.put(frame+j*4,v)
        step=dict(function=f,receiver=receiver,arguments=args,frame=frame,seed=seed,returnPC=pc,label=label,inputContext={k:getattr(c,k) for k,_ in c._fields_},stackBefore=self.stack(),before=self.snapshot(),failure=self.failure,tlsSetFalse=self.set_false,eventStart=len(self.events),entryStart=len(self.entries))
        try:
            result=self.m.call_source(f,c,pc,convention='thiscall',ecx=receiver,arguments=args)
            assert result.completed and result.stack_pointer==frame+4+len(args)*4
            step.update(completed=True,eax=result.eax,halt=None,outputContext={k:getattr(c,k) for k,_ in c._fields_})
        except Stop as stop:step.update(completed=False,eax=None,halt=str(stop),outputContext=None)
        for entry in self.pending_entries:
            entry.update(completed=step['completed'],halt=step['halt'],outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot())
        self.pending_entries=[]
        step.update(after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),eventCount=len(self.events),entryCount=len(self.entries));self.steps.append(step)
        return step['eax']
    def prepare(self,label,writes):
        for a,v in writes.items():self.put(a,v)
        self.preparations.append(dict(label=label,beforeStep=len(self.steps),writes={str(a):v for a,v in writes.items()},state=self.snapshot()))
    def container(self,manager=STATIC):return self.tls[self.get(manager)]
    def finish(self):
        for e in self.entries:
            assert len(e['stackBefore'])==STACK_SIZE*2 and len(e['stackAfter'])==STACK_SIZE*2
            assert set(e['inputCPU'])==set(CONTEXT_FIELDS) and set(e['outputCPU'])==set(CONTEXT_FIELDS)
            if e['completed']:assert e['outputCPU']['eip']==e['returnPC']
        for e in self.steps:
            assert len(e['stackBefore'])==STACK_SIZE*2 and len(e['stackAfter'])==STACK_SIZE*2
            assert all(e['inputContext'][k]==v for k,v in {'size':72,'version':1,'inputMask':0x7ff,'outputMask':0x7ff}.items())
            if e['completed']:
                assert all(e['outputContext'][k]==e['inputContext'][k] for k in tuple(k for k,_ in NativeSourceContext._fields_ if k not in CONTEXT_FIELDS))
        for e in self.events:
            assert len(e['stackBefore'])==STACK_SIZE*2 and len(e['stackAfter'])==STACK_SIZE*2
            assert set(e['inputCPU'])==set(CONTEXT_FIELDS)
            for field in CONTEXT_FIELDS:
                if field not in ('eax','esp','eip'):assert e['inputCPU'][field]==e['outputCPU'][field],(field,e['function'])
        return dict(name=self.name,sha256=self.p.sha256,initialBytes=self.initial,imports={str(k):v for k,v in self.imports.items()},lockImports={str(s):self.m.import_stub[s] for s in (0x546abc,0x546aa4,0x546aac,0x546a9c)},manager=STATIC,managers=self.managers,owner=OWNER,owners=self.owners,preparations=self.preparations,steps=self.steps,events=self.events,entries=self.entries)

def profiles():
    result=[]
    q=Reference('true-cold-static-thread-factory-and-warm');value=q.call();n=len(q.events);q.call(label='warm-same-owner');assert len(q.events)==n+1 and q.steps[-1]['eax']==value and q.events[-1]['function']==0x546a7c;result.append(q.finish())
    q=Reference('shared-slots-table-and-value-moving-growth');first=q.call()
    for i in range(34):
        owner=q.alloc(4,'slot-owner',True);q.owners.append(owner);q.call(receiver=owner,label=f'shared-owner-{i+2}')
    c=q.container();assert q.get(q.get(c+12)+4)==first;assert any(e['function']==0x546a88 for e in q.events);assert any(e['function']==0x546a80 for e in q.events);result.append(q.finish())
    q=Reference('alternate-real-module-factory-contract');v=q.call(args=[0x502369]);assert q.locals[v]==0x1074 and q.get(v)==0x51020c;result.append(q.finish())
    q=Reference('direct-setter-replacement-zero-and-wider-live-backing');q.call();c=q.container();q.call(SET,STATIC,[1,0xaabbccdd],'replace-in-range');q.call(SET,STATIC,[1,0],'zero-in-range')
    old=q.get(c+12);wider=q.alloc(16,'local',True);q.locals[wider]=16;q.m.write(wider,q.m.read(old,q.locals[old]));q.prepare('explicit wider owned backing with unchanged logical count',{c+12:wider,wider+12:0xdeadbeef});q.call(SET,STATIC,[3,0],'outside-logical-zero-with-live-backing');assert q.get(wider+12)==0;result.append(q.finish())
    q=Reference('missing-container-independent-manager-and-tls-key');q.call();other=q.alloc(0x34,'manager');q.managers.append(other);q.call(INIT,other);q.call(SLOT,other);q.call(SET,other,[1,0x11223344]);assert q.get(other)!=q.get(STATIC) and q.container(other)!=q.container();result.append(q.finish())
    q=Reference('tls-set-false-preserves-binding-and-final-store');q.set_false=True;q.call();q.call();assert q.tls[0]==0;containers=[a for a in q.allocations if a['kind']=='local' and a['size']==16];assert len(containers)==2;result.append(q.finish())
    q=Reference('local-container-failure-genuine-missing-throw');q.failure='container';q.call();assert q.steps[-1]['halt']=='missing-exception';result.append(q.finish())
    q=Reference('moving-reallocation-failure-prefix');q.call();q.call(SLOT,STATIC);c=q.container();q.failure='local-realloc';q.call(SET,STATIC,[2,5]);assert q.steps[-1]['halt']=='missing-exception' and q.get(c+12)==0;result.append(q.finish())
    q=Reference('new-array-failure-genuine-missing-throw');q.failure='array';q.call();assert q.steps[-1]['halt']=='missing-exception';result.append(q.finish())
    for failure in ('tls','global'):
        q=Reference('cold-static-manager-'+failure+'-failure-prefix');q.failure=failure;q.call();assert q.steps[-1]['halt']=='missing-exception';result.append(q.finish())
    return result

if __name__=='__main__':
    output=Path(sys.argv[1]).resolve();assert Path('work').resolve() in output.parents
    rows=profiles();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w') as f:json.dump(rows,f,separators=(',',':'));f.write('\n')
    counts=dict(profiles=len(rows),roots=sum(len(r['steps']) for r in rows),physicalEvents=sum(len(r['events']) for r in rows),childEntries=sum(len(r['entries']) for r in rows))
    print(json.dumps(dict(status='PASS',**counts,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),bytes=output.stat().st_size)))
