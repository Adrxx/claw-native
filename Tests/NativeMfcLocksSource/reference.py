"""Original-only full-source lock observations; physical imports alone are modeled.

Pinned image loading precedes every original read. Root unit frames use genuine
ordinary continuations; no dispatcher/catch activation is fabricated here.
"""
import hashlib
import json
import random
import struct
import sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_FIELDS, CONTEXT_REGISTERS
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.program import claw
from Tests.NativeMfcLocks.reference import BASE, COUNT, MASTER, SLOTS, INIT, ACQUIRE, RELEASE, PhysicalHalt
from unicorn.x86_const import UC_X86_REG_ESP

class Reference:
    def __init__(self, name, version=10, fail_at=None, recheck=None, seed=None, service_eax=0xa1b2c3d4):
        self.p=claw(); self.m=Machine(self.p,0x3000000,0x10000)
        self.name=name; self.version=version; self.fail_at=fail_at; self.recheck=recheck; self.service_eax=service_eax
        self.events=[]; self.entries=[]; self.steps=[]; self.states={}; self.pending=[]; self.return_observers=set(); self.current=None
        self.initial=self.m.read(BASE,COUNT).hex()
        self.imports={s:self.m.import_stub[s] for s in SLOTS}; self.reverse={v:k for k,v in self.imports.items()}
        for s,n in SLOTS.items(): assert self.p.imports[s].split('!')[-1]==n
        self.seed=seed or {}
        for a,v in self.seed.items(): self.put(a,v)
        self.m.on_external=self.external
        for f in (INIT,ACQUIRE,RELEASE): self.m.observe(f,self.observe)
    def put(self,a,v): self.m.write(a,struct.pack('<I',v))
    def get(self,a): return self.m.words(a,1)[0]
    def cpu(self): return dict(zip(CONTEXT_FIELDS,[self.m.register(r) for r in CONTEXT_REGISTERS]+[self.m.fs_head]))
    def stack(self): return self.m.read(STACK_BASE,STACK_SIZE).hex()
    def snapshot(self): return dict(imageBytes=self.m.read(BASE,COUNT).hex(),states=[dict(self.states[k]) for k in sorted(self.states)],thread=1)
    def adopt(self,s):
        assert s not in self.states
        self.states[s]=dict(section=s,owner=0,depth=0,initialized=1,entered=0,left=0)
    def observe(self,m,f):
        sp=m.register(UC_X86_REG_ESP); pc=self.get(sp)
        e=dict(function=f,frame=sp,returnPC=pc,arguments=list(m.words(sp+4,int(f!=INIT))),inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),kind='root' if sp==self.current['frame'] else 'nested-owned-initializer')
        if e['kind']!='root': assert f==INIT and pc==0x502ea8 and sp==self.current['frame']-20
        self.entries.append(e); self.pending.append(e)
        if pc not in self.return_observers:
            self.return_observers.add(pc); self.m.observe(pc,self.returned)
    def returned(self,m,pc):
        candidates=[e for e in self.pending if e['returnPC']==pc]
        if candidates:
            e=candidates[-1]; e.update(completed=True,outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot()); self.pending.remove(e)
    def external(self,m,target):
        s=self.reverse[target]; sp=m.register(UC_X86_REG_ESP); a=list(m.words(sp+4,int(s!=0x546abc)))
        f=self.current['function']; frame=self.current['frame']
        if f==INIT: expected=frame-(8 if s==0x546abc else 12)
        elif f==RELEASE: expected=frame-8
        elif s==0x546abc: expected=frame-28
        elif s==0x546aa4 and a==[MASTER]: expected=frame-32
        else: expected=frame-24
        assert sp==expected
        pc=self.get(sp)
        allowed={0x546abc:{0x502e60},0x546aa4:{0x502e8e,0x502ee8},0x546aac:{0x502ed2,0x502efe},0x546a9c:{0x502ef1,0x502f23}}
        assert pc in allowed[s]
        e=dict(function=s,target=target if s==0x546aac else s,importedTarget=target,frame=sp,stackPointer=sp,returnPC=pc,arguments=a,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),completed=False)
        self.events.append(e)
        if self.fail_at==len(self.events):
            e.update(outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot(),halt='physical-service'); raise PhysicalHalt('physical-service')
        if self.recheck is not None and s==0x546aac and a==[MASTER]:
            section=0x5408f0+24*self.recheck
            if section not in self.states: self.adopt(section); self.put(0x540aa8+4*self.recheck,1)
        if s!=0x546abc:
            section=a[0]
            if s==0x546aa4: self.adopt(section)
            else:
                st=self.states[section]
                if s==0x546aac:
                    assert st['owner'] in (0,1); st['owner']=1; st['depth']+=1; st['entered']+=1
                else:
                    assert st['owner']==1 and st['depth']>0; st['depth']-=1; st['left']+=1
                    if st['depth']==0: st['owner']=0
        r=self.version if s==0x546abc else self.service_eax
        m.return_from_external(r,4*len(a))
        e.update(result=r,completed=True,outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot())
    def call(self,f,args=None,label=None,ebp=None,fs_chain=False):
        args=([] if f==INIT else [16]) if args is None else args
        i=len(self.steps); frame=STACK_TOP-0x100-i*0x40; seed=0x502e47+i*0x10001
        rng=random.Random(seed); self.m.write(STACK_BASE,rng.randbytes(STACK_SIZE))
        vals=[rng.getrandbits(32) for _ in CONTEXT_FIELDS]; vals[7]=frame; vals[8]=f; vals[9]=rng.getrandbits(32)&0x8d5|2; vals[10]=0xffffffff
        if ebp is not None: vals[6]=ebp
        if fs_chain:
            vals[10]=STACK_BASE+0x100; self.put(vals[10],0xffffffff); self.put(vals[10]+4,0x4a8f10); self.put(vals[10]+8,0)
        pc=0x502ea8 if f==INIT else (0x503444 if f==ACQUIRE else 0x503478)
        c=NativeSourceContext(72,1,0x7ff,0x7ff,*vals,0,0,0)
        for j,v in enumerate([pc]+args): self.put(frame+4*j,v)
        self.current=dict(function=f,frame=frame)
        e=dict(function=f,receiver=0,arguments=args,frame=frame,seed=seed,returnPC=pc,label=label,frameKind='ordinary-unit-frame',inputContext={k:getattr(c,k) for k,_ in c._fields_},stackBefore=self.stack(),before=self.snapshot(),eventStart=len(self.events),entryStart=len(self.entries))
        try:
            result=self.m.call_source(f,c,pc,convention='cdecl' if f==INIT else 'stdcall',arguments=args)
            assert result.completed and result.stack_pointer==frame+4+len(args)*4
            e.update(completed=True,eax=result.eax,halt=None,outputContext={k:getattr(c,k) for k,_ in c._fields_})
        except PhysicalHalt as stop: e.update(completed=False,eax=None,halt=str(stop),outputContext=None)
        for child in self.pending:
            completed=e['completed'] and self.cpu()['eip']==child['returnPC']
            assert not e['completed'] or completed
            child.update(completed=completed,halt=e['halt'],outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot())
        self.pending=[]
        e.update(outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot(),eventCount=len(self.events),entryCount=len(self.entries)); self.steps.append(e)
    def finish(self):
        for e in self.steps+self.entries+self.events:
            assert len(e['stackBefore'])==STACK_SIZE*2 and len(e['stackAfter'])==STACK_SIZE*2
            assert set(e['outputCPU'])==set(CONTEXT_FIELDS)
        for e in self.entries:
            assert set(e['inputCPU'])==set(CONTEXT_FIELDS)
            if e['completed']: assert e['outputCPU']['eip']==e['returnPC']
        for e in self.steps:
            assert all(e['inputContext'][k]==v for k,v in dict(size=72,version=1,inputMask=0x7ff,outputMask=0x7ff,preserveMask=0,reserved0=0,reserved1=0).items())
            if e['completed']:
                assert e['outputCPU']['eip']==e['returnPC']
                assert all(e['outputContext'][k]==e['inputContext'][k] for k in ('size','version','inputMask','outputMask','preserveMask','reserved0','reserved1'))
        if self.fail_at is None:
            assert all(s['depth']==0 and s['owner']==0 and s['entered']==s['left'] for s in self.states.values())
        else: assert not self.steps[-1]['completed'] and len(self.events)==self.fail_at and not self.events[-1]['completed']
        return dict(name=self.name,sha256=self.p.sha256,initialBytes=self.initial,imports={str(k):v for k,v in self.imports.items()},version=self.version,failAt=self.fail_at,recheck=self.recheck,serviceEAX=self.service_eax,seed={str(k):v for k,v in self.seed.items()},steps=self.steps,events=self.events,entries=self.entries)

def profiles():
    rows=[]
    q=Reference('cold-recursive-warm-initializer')
    for f in (ACQUIRE,ACQUIRE,RELEASE,RELEASE,INIT): q.call(f,ebp=0 if len(q.steps)%2 else 0xffffffff,fs_chain=True)
    assert any(e['kind']=='nested-owned-initializer' and e['completed'] for e in q.entries); rows.append(q.finish())
    q=Reference('direct-initializer-cold-and-warm')
    for f in (INIT,INIT,ACQUIRE,RELEASE): q.call(f,args=[] if f==INIT else [0])
    rows.append(q.finish())
    q=Reference('all-seventeen-original-slots')
    for i in range(17): q.call(ACQUIRE,[i]); q.call(RELEASE,[i])
    rows.append(q.finish())
    q=Reference('same-owner-recheck-publication',recheck=16); q.call(ACQUIRE); q.call(RELEASE)
    assert sum(e['function']==0x546aa4 for e in q.events)==1; rows.append(q.finish())
    q=Reference('warm-nonboolean-disabled',seed={0x5408e8:0x753190ab,0x540a88:7})
    q.call(INIT); q.call(ACQUIRE,[0xffffffff],ebp=0); q.call(RELEASE,[0xffffffff],ebp=0xffffffff)
    assert not q.events; rows.append(q.finish())
    for v in (3,4,0x80000003,0x80000004,0x80000000,0x7fffff00,0xffffffff):
        q=Reference('version-'+hex(v),version=v); q.call(ACQUIRE); q.call(RELEASE); rows.append(q.finish())
    for eax in (0,0xffffffff,0x13579bdf):
        q=Reference('opaque-service-eax-'+hex(eax),service_eax=eax); q.call(ACQUIRE); q.call(RELEASE)
        assert q.steps[-1]['outputCPU']['eax']==eax; rows.append(q.finish())
    for n in range(1,8):
        q=Reference('physical-halt-'+str(n),fail_at=n); q.call(ACQUIRE)
        if q.steps[-1]['completed']: q.call(RELEASE)
        rows.append(q.finish())
    return rows

if __name__=='__main__':
    output=Path(sys.argv[1]).resolve(); assert Path('work').resolve() in output.parents
    rows=profiles(); output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w') as f: json.dump(rows,f,separators=(',',':')); f.write('\n')
    counts=dict(profiles=len(rows),roots=sum(len(r['steps']) for r in rows),physicalEvents=sum(len(r['events']) for r in rows),childEntries=sum(len(r['entries']) for r in rows),nestedInitializers=sum(e['kind']=='nested-owned-initializer' for r in rows for e in r['entries']),completedRoots=sum(s['completed'] for r in rows for s in r['steps']),completedEntries=sum(e['completed'] for r in rows for e in r['entries']),completedPhysicalEvents=sum(e['completed'] for r in rows for e in r['events']))
    print(json.dumps(dict(status='PASS',**counts,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),bytes=output.stat().st_size)))
