"""Independent original-only cold module graph, with physical services only.

All code, including factories, constructors, locks and publication, executes
from the hash-pinned image. Native sources/results and family cases are unused.
The source context type is an ABI data container; no native execution is loaded.
"""
import hashlib
import json
import random
import sys
from pathlib import Path
from Tests.NativeMfcTlsValuesSource.reference import Reference as TLSReference, Stop, IMPORTS, CHILDREN, STATIC, OWNER, PUBLICATION
from Tests.clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_FIELDS
from Tests.clawparity.env import NativeSourceContext
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ESP

GETTER, SINGLETON, MODULE_OWNER = 0x50228f, 0x503420, 0x53eca0
LOCK_INIT, ACQUIRE, RELEASE = 0x502e47, 0x502e95, 0x502f05
MASTER, NUMBERED = 0x540a90, 0x540a70
FUNCTIONS = set(CHILDREN) | {GETTER, SINGLETON, LOCK_INIT, ACQUIRE, RELEASE}
ARGC = {0x50335e:1,0x503167:2,0x502f84:1,0x502f26:1,0x4a4a20:3,0x501fde:1,SINGLETON:1,ACQUIRE:1,RELEASE:1}
# These are original observations, not a claim that each is a native boundary.
REFERENCE_ONLY = {0x503167,0x501f01,0x501fde,LOCK_INIT}

class Reference(TLSReference):
    def __init__(self,name,allocation_fail_at=None,physical_fail_at=None,tls_failure=False):
        self.timeline=[];self.publications=[];self.global_writes={};self.allocation_attempts=0
        self.allocation_fail_at=allocation_fail_at;self.physical_fail_at=physical_fail_at;self.tls_failure=tls_failure
        super().__init__(name)
        self.owners.append(MODULE_OWNER)
        self.imports[0x546abc]=self.m.import_stub[0x546abc]
        self.reverse={v:k for k,v in self.imports.items()}
        assert self.p.imports[0x546abc].split('!')[-1]=='GetVersion'
        for a in FUNCTIONS-set(CHILDREN):self.m.observe(a,self.observe)
        for a in (0x503450,0x503452):self.m.observe(a,self.publication)
        self.m.uc.hook_add(UC_HOOK_MEM_WRITE,self.wrote)
        assert self.get(MODULE_OWNER)==0 and self.get(0x5408e8)==0 and self.get(PUBLICATION)==0
        assert self.get(OWNER)==0 and self.m.read(STATIC,0x34)==bytes(0x34)
        self.cold=self.snapshot()
    def mark(self,kind,index):
        self.timeline.append(dict(order=len(self.timeline),kind=kind,index=index,rootStep=len(self.steps)))
    def wrote(self,uc,access,address,size,value,user):
        if self.p.data_start<=address<self.p.base+self.p.size:
            for a in range(address,address+size):self.global_writes[a]=True
    def snapshot(self):
        s=super().snapshot()
        s.update(imageBytes=self.m.read(0x5408e0,0x210).hex(),moduleOwnerValue=self.get(MODULE_OWNER),
          sourceGlobalBytes={str(a):self.m.read(a,n).hex() for a,n in ((OWNER,8),(0x5408e0,0x244))},
          writtenImageBytes={str(a):self.m.read(a,1).hex() for a in sorted(self.global_writes)},
          staticOwnerIdentities=[dict(address=OWNER,size=4,identity='pinned-thread-slot'),dict(address=MODULE_OWNER,size=4,identity='pinned-module-singleton'),dict(address=PUBLICATION,size=4,identity='pinned-manager-publication')])
        s['borrowedStorage'].append(dict(address=MODULE_OWNER,size=4,kind='static-module-singleton'))
        return s
    def observe(self,m,address):
        sp=m.register(UC_X86_REG_ESP)
        e=dict(function=address,frame=sp,returnPC=self.get(sp),arguments=list(m.words(sp+4,ARGC.get(address,0))),inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),observation='original-only-internal' if address in REFERENCE_ONLY else 'source-boundary-candidate')
        e['order']=len(self.timeline);self.entries.append(e);self.pending_entries.append(e);self.mark('entry',len(self.entries)-1)
        pc=e['returnPC']
        if pc not in self.return_observers:self.return_observers.add(pc);self.m.observe(pc,self.returned_child)
        if address==0x4f50fd:raise Stop('missing-native-exception-0x4f50fd')
    def returned_child(self,m,address):
        matches=[e for e in self.pending_entries if e['returnPC']==address]
        if matches:
            e=matches[-1];e.update(completed=True,outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot(),returnOrder=len(self.timeline));self.pending_entries.remove(e);self.mark('return',self.entries.index(e))
    def publication(self,m,address):
        e=dict(function=address,observation='original-only-publication-'+('before' if address==0x503450 else 'after'),cpu=self.cpu(),stack=self.stack(),state=self.snapshot(),rootStep=len(self.steps),order=len(self.timeline))
        self.publications.append(e);self.mark('publication',len(self.publications)-1)
    def external(self,m,target):
        assert target in self.reverse,('unsupported-import',hex(target))
        s=self.reverse[target];count=0 if s==0x546abc else IMPORTS[s][1]
        sp=m.register(UC_X86_REG_ESP);a=list(m.words(sp+4,count));r=0
        e=dict(function=s,target=target if s in (0x5469c4,0x546aac) else s,importedTarget=target,frame=sp,stackPointer=sp,returnPC=self.get(sp),arguments=a,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),completed=False,order=len(self.timeline))
        self.events.append(e);self.mark('physical-enter',len(self.events)-1)
        if self.physical_fail_at==len(self.events):
            e.update(halt='physical-service',outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot());raise Stop('physical-service')
        allocation=s in (0x546b1c,0x546aa8,0x546a88,0x546a80)
        if allocation:self.allocation_attempts+=1;e['allocationAttempt']=self.allocation_attempts
        fail=allocation and self.allocation_attempts==self.allocation_fail_at
        if s==0x546abc:r=10
        elif s==0x546a90:
            if self.tls_failure:r=0xffffffff
            else:r=self.next_tls;self.next_tls+=1;self.tls[r]=0
        elif s==0x546a7c:assert a[0] in self.tls;r=self.tls[a[0]]
        elif s==0x546a84:assert a[0] in self.tls;self.tls[a[0]]=a[1];r=1
        elif s==0x546aa4:
            assert a[0] in (STATIC+28,MASTER,NUMBERED) and a[0] not in self.sections
            self.sections[a[0]]=dict(section=a[0],owner=0,depth=0,initialized=1,entered=0,left=0)
        elif s in (0x546aac,0x546a9c):
            st=self.sections[a[0]]
            if s==0x546aac:assert st['owner'] in (0,1);st['depth']+=1;st['entered']+=1
            else:assert st['owner']==1 and st['depth']>0;st['depth']-=1;st['left']+=1
            st['owner']=1 if st['depth'] else 0
        elif s==0x546b1c:
            assert a[0]==0x2002
            if not fail:r=self.next_handle;self.next_handle+=4;self.blocks[r]=dict(handle=r,data=self.alloc(a[1],'global'),size=a[1],flags=a[0],locks=0)
        elif s==0x5469c4:
            if a[0]:b=self.blocks[a[0]];b['locks']+=1;r=b['data']
        elif s==0x546a8c:r=next((h for h,b in self.blocks.items() if b['data']==a[0]),0);assert r or a[0]==0
        elif s==0x5469c8:b=self.blocks[a[0]];assert b['locks']>0;b['locks']-=1;r=int(b['locks']>0)
        elif s==0x546aa8:
            assert a[0] in (0,0x40)
            if not fail:r=self.alloc(a[1],'local',bool(a[0]&0x40));self.locals[r]=a[1]
        else:raise AssertionError(('unexpected-cold-import',hex(s)))
        if s in (0x546aa4,0x546aac,0x546a9c):r=0xa1b2c3d4
        m.return_from_external(r,4*count)
        e.update(result=r,completed=True,after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),returnOrder=len(self.timeline));self.mark('physical-return',len(self.events)-1)
    def call(self,label):
        i=len(self.steps);frame=STACK_TOP-0x100-i*0x40;seed=GETTER+i*0x10001
        rng=random.Random(seed);self.m.write(STACK_BASE,rng.randbytes(STACK_SIZE))
        vals=[rng.getrandbits(32) for _ in CONTEXT_FIELDS];vals[7]=frame;vals[8]=GETTER;vals[9]=rng.getrandbits(32)&0x8d5|2;vals[10]=0xffffffff
        c=NativeSourceContext(72,1,0x7ff,0x7ff,*vals,0x400,0,0);pc=0x5025bd;self.put(frame,pc)
        e=dict(function=GETTER,receiver=0,arguments=[],frame=frame,seed=seed,returnPC=pc,label=label,inputContext={k:getattr(c,k) for k,_ in c._fields_},stackBefore=self.stack(),before=self.snapshot(),eventStart=len(self.events),entryStart=len(self.entries),order=len(self.timeline))
        self.mark('root-enter',i)
        try:
            result=self.m.call_source(GETTER,c,pc,convention='cdecl')
            assert result.completed and result.stack_pointer==frame+4
            e.update(completed=True,eax=result.eax,halt=None,outcome='returned',outputContext={k:getattr(c,k) for k,_ in c._fields_})
        except Stop as stop:e.update(completed=False,eax=None,halt=str(stop),outcome='physical-host-stop' if str(stop)=='physical-service' else 'missing-native-dependency-prefix',outputContext=None)
        for child in self.pending_entries:
            completed=e['completed'] and self.cpu()['eip']==child['returnPC']
            assert not e['completed'] or completed
            child.update(completed=completed,halt=e['halt'],outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot())
            child['returnOrder' if completed else 'stopOrder']=len(self.timeline)
            self.mark('return' if completed else 'entry-stop',self.entries.index(child))
        self.pending_entries=[]
        e.update(after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),eventCount=len(self.events),entryCount=len(self.entries),returnOrder=len(self.timeline));self.mark('root-return' if e['completed'] else 'root-stop',i);self.steps.append(e)
        return e['eax']
    def finish(self):
        row=super().finish()
        row.update(schema='claw-original-cold-module-v1',root=GETTER,rootReturn=0x5025bd,moduleOwner=MODULE_OWNER,coldState=self.cold,timeline=self.timeline,publications=self.publications,allocationFailAt=self.allocation_fail_at,physicalFailAt=self.physical_fail_at,tlsFailure=self.tls_failure,allocationAttempts=self.allocation_attempts,referenceOnlyEntries=sorted(REFERENCE_ONLY),nativeExecution=False,setupPolicy='Pinned static bytes, physical services only; fresh stack/CPU ordinary root calls; no cache, lock, callback or CRT exception setup.')
        for e in self.events:
            assert len(e['stackBefore'])==STACK_SIZE*2 and len(e['stackAfter'])==STACK_SIZE*2
        return row


def new(name,**kwargs):
    return Reference(name,**kwargs)

def profiles():
    q=new('genuine-cold-module-and-repeat-warm');v=q.call('cold')
    assert q.locals[v]==0x1074 and q.get(v)==0x51020c and q.get(MODULE_OWNER)==v
    assert q.get(v+0x1070)==0
    assert [e['function'] for e in q.publications]==[0x503450,0x503452]
    assert q.publications[0]['state']['moduleOwnerValue']==0 and q.publications[1]['state']['moduleOwnerValue']==v
    assert any(e['function']==0x502335 and e['completed'] for e in q.entries)
    assert any(e['function']==LOCK_INIT and e['completed'] for e in q.entries)
    assert all(s['depth']==0 and s['entered']==s['left'] for s in q.sections.values())
    physical_count=len(q.events);allocation_count=q.allocation_attempts;ledger=[dict(a) for a in q.allocations];event_start=len(q.events)
    assert q.call('warm-same-physical-owners')==v
    assert q.events[event_start:][0]['function']==0x546a7c and len(q.events)==event_start+1
    assert q.allocations==ledger and q.allocation_attempts==allocation_count and len(q.publications)==2
    yield q.finish()
    for n in range(1,allocation_count+1):
        q=new('cold-allocation-failure-'+str(n),allocation_fail_at=n);q.call('cold-failure')
        assert q.steps[-1]['halt']=='missing-native-exception-0x4f50fd' and q.cpu()['eip']==0x4f50fd
        assert q.get(MODULE_OWNER)==0 and not q.publications and q.allocation_attempts==n
        yield q.finish()
    q=new('cold-tls-allocation-failure',tls_failure=True);q.call('cold-failure');assert q.steps[-1]['halt']=='missing-native-exception-0x4f50fd' and q.get(MODULE_OWNER)==0;yield q.finish()
    for n in range(1,physical_count+1):
        q=new('cold-physical-service-stop-'+str(n),physical_fail_at=n);q.call('cold-prefix')
        assert q.steps[-1]['halt']=='physical-service' and len(q.events)==n and not q.events[-1]['completed']
        yield q.finish()

if __name__=='__main__':
    output=Path(sys.argv[1]).resolve();assert Path('work').resolve() in output.parents
    output.parent.mkdir(parents=True,exist_ok=True)
    counts=dict(profiles=0,roots=0,physicalEvents=0,childEntries=0,completedRoots=0)
    with output.open('w') as f:
        f.write('[')
        for row in profiles():
            if counts['profiles']:f.write(',')
            json.dump(row,f,separators=(',',':'))
            counts['profiles']+=1;counts['roots']+=len(row['steps']);counts['physicalEvents']+=len(row['events']);counts['childEntries']+=len(row['entries']);counts['completedRoots']+=sum(s['completed'] for s in row['steps'])
        f.write(']\n')
    h=hashlib.sha256()
    with output.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    print(json.dumps(dict(status='PASS',**counts,sha256=h.hexdigest(),bytes=output.stat().st_size)))
