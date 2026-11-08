"""Original-only connected CRT registry reference in physical memory domain v1.

No native implementation or family cases are inputs. All original reads use the
pinned program loader. Outputs (including original-derived pages) stay in work/.
This is bounded registration-leaf composition, not whole static initialization.
"""
import argparse
import gzip
import gc
import hashlib
import json
import random
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import UC_HOOK_CODE
from Tests.clawparity.program import claw
from Tests.clawparity.kernel import (Machine, CONTEXT_FIELDS, CONTEXT_REGISTERS,
    STACK_BASE, STACK_SIZE, STACK_TOP, STUB_BASE, STUB_SIZE)
from Tests.clawparity.env import NativeSourceContext

HEAP, HEAP_SIZE, PAGE = 0x62000000, 0x10000, 4096
MALLOC, CAPACITY, REALLOC, FREE = 0x4a48e0, 0x4a6560, 0x4a9070, 0x4a49b0
INIT_LOCKS, INIT, REGISTER = 0x4a7b90, 0x4a3610, 0x4a35f0
BASE, NEXT = 0x545fd4, 0x545fd0
SERVICES = {MALLOC:('malloc',1,False), CAPACITY:('capacity',1,False),
    REALLOC:('realloc',2,False), FREE:('free',1,False),
    0x546aa4:('InitializeCriticalSection',1,True),
    0x546aac:('EnterCriticalSection',1,True), 0x546a9c:('LeaveCriticalSection',1,True),
    0x5469f4:('GetModuleFileNameA',3,True), 0x546a14:('LoadLibraryA',1,True),
    0x546980:('SetUnhandledExceptionFilter',1,True), 0x546998:('ExitProcess',1,True)}
ENTRIES = {INIT_LOCKS:0, INIT:0, REGISTER:1, 0x4a3560:1, 0x4a5860:0,
    0x4a5870:0, 0x4a7bc0:1, 0x4a7c40:1, 0x4a4860:1, 0x4ad130:0,
    0x4ad170:1, 0x4b0e70:3, 0x4a5780:1, 0x4a57a0:3, 0x4a5880:2, 0x4ad7e0:0}
SCHEMA = 'claw-original-crt-exit-registry-pages-v1'


def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(path): return sha(Path(path).read_bytes())


def registration_leaves(p):
    """Read the fixed original table and follow its direct registration tails."""
    def read(a,n):
        s=next(s for s in p.sections if s.address<=a and a+n<=s.address+len(s.data))
        return s.data[a-s.address:a-s.address+n]
    dis=Cs(CS_ARCH_X86,CS_MODE_32)
    def leaf(a,depth=0):
        b=read(a,14)
        if (b[0]==0x68 and b[5]==0xe8 and a+10+struct.unpack_from('<i',b,6)[0]==REGISTER
                and (b[10:14]==bytes.fromhex('83c404c3') or b[10:12]==bytes.fromhex('59c3'))):
            n=14 if b[10]==0x83 else 12
            callback=struct.unpack_from('<I',b,1)[0]
            assert p.in_text(callback)
            return dict(leaf=a,callback=callback,callSite=a+5,returnPC=a+10,
                        bytes=n,sha256=sha(read(a,n)))
        if depth==2:return None
        for i in dis.disasm(read(a,40),a):
            if i.mnemonic=='jmp' and i.op_str.startswith('0x'):return leaf(int(i.op_str,16),depth+1)
            if i.mnemonic in ('ret','int3'):return None
        return None
    roots=struct.unpack('<144I',read(0x522004,576));rows=[]
    for index,root in enumerate(roots):
        r=leaf(root)
        if r:rows.append(dict(tableIndex=index,initializer=root,**r))
    assert len(rows)==126 and len({r['leaf'] for r in rows})==126
    return rows


class PageStore:
    """Full ranges encoded once per page version, with exact verified deltas.

    Each state delta is relative to its immediately previous state. The separate
    reconstruction below uses serialized hex pages, not the source/raw cache.
    """
    def __init__(self,m):
        self.m=m;self.pages=[];self.ids={};self.previous={};self.rebuilt={}
        self.ranges=[('image',m.program.base,m.program.size),('stack',STACK_BASE,STACK_SIZE),
                     ('heap',HEAP,HEAP_SIZE),('thread',0,PAGE),('imports',STUB_BASE,STUB_SIZE)]
        self.verified=0;self.raw_bytes=0
    def capture(self):
        changes=[];checks=[]
        for name,base,size in self.ranges:
            raw=self.m.read(base,size);self.raw_bytes+=size
            for offset in range(0,size,PAGE):
                at=base+offset;page=raw[offset:offset+PAGE]
                if self.previous.get(at)!=page:
                    h=sha(page)
                    if h not in self.ids:
                        self.ids[h]=len(self.pages);self.pages.append(dict(sha256=h,bytes=page.hex()))
                    pid=self.ids[h]
                    assert bytes.fromhex(self.pages[pid]['bytes'])==page
                    changes.append([at,pid]);self.previous[at]=page
            checks.append(dict(name=name,address=base,size=size,sha256=sha(raw)))
        # Reconstruct exclusively from serialized page payloads and emitted delta.
        for at,pid in changes:
            record=self.pages[pid];b=bytes.fromhex(record['bytes']);assert sha(b)==record['sha256']
            self.rebuilt[at]=b
        for r in checks:
            rebuilt=b''.join(self.rebuilt[a] for a in range(r['address'],r['address']+r['size'],PAGE))
            assert sha(rebuilt)==r['sha256']
            assert rebuilt==self.m.read(r['address'],r['size'])
        self.verified+=1
        return dict(parent=self.verified-2 if self.verified>1 else None,pageChanges=changes,ranges=checks)


class Stop(Exception): pass


class Reference:
    def __init__(self,name,mode='inplace',fail_resize=0,fail_malloc=False,physical_stop=0,index=0):
        self.name=name;self.mode=mode;self.fail_resize=fail_resize;self.fail_malloc=fail_malloc
        self.physical_stop=physical_stop;self.p=claw();self.leaves=registration_leaves(self.p)
        self.m=Machine(self.p,HEAP,HEAP_SIZE);self.reverse={v:k for k,v in self.m.import_stub.items()}
        self.m.on_external=self.external
        for a in (MALLOC,CAPACITY,REALLOC,FREE):self.m.intercept(a)
        for a,(label,_,imported) in SERVICES.items():
            if imported:assert self.p.imports[a].split('!')[-1]==label
        self.sections={};self.allocations=[];self.bump=HEAP;self.identity=0;self.resize_attempts=0
        self.malloc_attempts=0;self.filter=0x70001111;self.thread=1
        self.states=[];self.events=[];self.entries=[];self.pending=[];self.steps=[];self.timeline=[]
        self.instructions=[];self.exited=False;self.halt=None;self.completed_registrations=[]
        self.entry_points=dict(ENTRIES,**{})
        self.entry_points.update({r['leaf']:0 for r in self.leaves})
        self.m.write(STACK_BASE,random.Random(0xc17e0000+index).randbytes(STACK_SIZE))
        self.m.fs_head=0xffffffff
        # CPU and stack persist across roots; the explicit harness invocation only
        # sets original entry/return addresses and normal argument/return words.
        rng=random.Random(index+0x4a35f0)
        self.current={k:rng.getrandbits(32) for k in CONTEXT_FIELDS}
        self.current.update(esp=STACK_TOP-0x100,eip=INIT_LOCKS,eflags=0x202&0x8d7,fsHead=0xffffffff)
        self.current['eflags']=2
        for k,r in zip(CONTEXT_FIELDS,CONTEXT_REGISTERS):self.m.uc.reg_write(r,self.current[k])
        self.store=PageStore(self.m);self.initial=self.snapshot()
        self.m.uc.hook_add(UC_HOOK_CODE,self.instruction,begin=self.p.text[0],end=self.p.text[1]-1)
        # Prove the pinned cold state rather than creating a registry/lock cache.
        assert self.get(BASE)==0 and self.get(NEXT)==0
        assert [self.get(0x52ed18+4*i) for i in (17,13,9,1)]==[0x540e38,0x540e68,0x540e50,0x540e20]
        assert self.get(0x52e9f8)==0x4a5780 and self.get(0x540b88)==0 and self.get(0x52e9fc)==2
    def get(self,a):return self.m.words(a,1)[0]
    def cpu(self):
        out={k:self.m.register(r) for k,r in zip(CONTEXT_FIELDS,CONTEXT_REGISTERS)}
        out['fsHead']=self.m.fs_head;return out
    def snapshot(self):
        memory=self.store.capture()
        row=dict(cpu=self.cpu(),memory=memory,thread=self.thread,filter=self.filter,memoryOwner='crt-memory-owner-v1',
                 allocationNext=self.bump,allocationIdentity=self.identity,
                 allocations=[dict(a) for a in self.allocations],
                 sections=[dict(address=a,**s) for a,s in sorted(self.sections.items())],
                 registryBase=self.get(BASE),registryNext=self.get(NEXT))
        self.states.append(row);return len(self.states)-1
    def mark(self,kind,index):
        self.timeline.append(dict(order=len(self.timeline),kind=kind,index=index,instruction=len(self.instructions)))
    def instruction(self,uc,a,n,user):
        try:
            # Scoped continuation is not an executed instruction.
            if self.m._source_return_boundary(a) or a in (MALLOC,CAPACITY,REALLOC,FREE) or self.m._pending is not None:return
            self.instructions.append([a,n])
            sp=self.cpu()['esp']
            while self.pending and self.pending[-1]['returnPC']==a and sp==self.pending[-1]['frame']+4:
                e=self.pending.pop();e.update(completed=True,after=self.snapshot(),returnOrder=len(self.timeline))
                self.mark('source-return',e['index'])
            if a in self.entry_points:
                e=dict(index=len(self.entries),function=a,frame=sp,returnPC=self.get(sp),
                       arguments=list(self.m.words(sp+4,self.entry_points[a])),before=self.snapshot(),
                       rootStep=len(self.steps),order=len(self.timeline),completed=False)
                self.entries.append(e);self.pending.append(e);self.mark('source-entry',e['index'])
        except BaseException as error:self.m._pending=error;uc.emu_stop()
    def live(self,base):
        matches=[a for a in self.allocations if a['address']==base and a['live']]
        assert len(matches)==1,('not exact live base',hex(base));return matches[0]
    def allocate(self,size):
        assert 0<=size<=0x10000
        capacity=(max(size,1)+15)&~15
        address=self.bump;self.bump=address+capacity+16
        assert self.bump<HEAP+HEAP_SIZE
        self.identity+=1
        a=dict(address=address,requested=size,capacity=capacity,identity=self.identity,live=True)
        self.allocations.append(a)
        self.m.write(address,bytes((i*31+self.identity*19)&255 for i in range(capacity)))
        return address
    def external(self,m,target):
        fn=self.reverse.get(target,target)
        assert fn in SERVICES,('undeclared physical boundary',hex(fn))
        label,argc,stdcall=SERVICES[fn];sp=self.cpu()['esp'];args=list(m.words(sp+4,argc))
        e=dict(function=fn,name=label,target=target,frame=sp,returnPC=self.get(sp),arguments=args,
               before=self.snapshot(),rootStep=len(self.steps),order=len(self.timeline),completed=False)
        self.events.append(e);self.mark('physical-enter',len(self.events)-1)
        if self.physical_stop==len(self.events):
            e.update(halt='physical-prefix-stop',after=self.snapshot());self.mark('physical-stop',len(self.events)-1)
            raise Stop('physical-prefix-stop')
        result=0
        if fn==MALLOC:
            self.malloc_attempts+=1
            if not(self.fail_malloc and self.malloc_attempts==1):result=self.allocate(args[0])
        elif fn==CAPACITY:result=self.live(args[0])['capacity']
        elif fn==REALLOC:
            base,size=args;old=self.live(base);self.resize_attempts+=1;e['resizeAttempt']=self.resize_attempts
            assert size>0 and size<=0x10000
            prefix=m.read(base,old['capacity']);e['prefixSha256']=sha(prefix)
            if self.resize_attempts!=self.fail_resize:
                capacity=(size+15)&~15
                moving=self.mode=='moving' or (self.mode=='mixed' and self.resize_attempts%2==0)
                if moving:
                    result=self.allocate(size);m.write(result,prefix[:min(len(prefix),capacity)])
                    old['live']=False;old['retiredBy']='resize-move'
                else:
                    assert base+capacity<HEAP+HEAP_SIZE
                    assert all(not a['live'] or a is old or base+capacity<=a['address'] or a['address']+a['capacity']<=base for a in self.allocations)
                    if capacity>old['capacity']:m.write(base+old['capacity'],bytes((i*17+old['identity'])&255 for i in range(capacity-old['capacity'])))
                    old.update(requested=size,capacity=capacity);self.bump=max(self.bump,base+capacity+16);result=base
                assert m.read(result,min(len(prefix),capacity))==prefix[:min(len(prefix),capacity)]
            else:assert m.read(base,old['capacity'])==prefix
        elif fn==FREE:
            if args[0]:self.live(args[0])['live']=False
        elif fn==0x546aa4:
            a=args[0];assert a not in self.sections
            self.sections[a]=dict(initialized=True,owner=0,depth=0)
            m.write(a,struct.pack('<6I',0,0xffffffff,0,0,0,0))
        elif fn in (0x546aac,0x546a9c):
            a=args[0];s=self.sections[a]
            if fn==0x546aac:
                assert s['owner'] in (0,self.thread);s.update(owner=self.thread,depth=s['depth']+1)
            else:
                assert s['owner']==self.thread and s['depth']>0
                s['depth']-=1
                if not s['depth']:s['owner']=0
            m.write(a,struct.pack('<6I',0,(s['depth']-1)&0xffffffff,s['depth'],s['owner'],0,0))
        elif fn==0x5469f4:
            assert args[0]==0 and args[2]>0
            path=b'C:\\CLAW\\CLAW.EXE\0';assert len(path)<=args[2]
            m.write(args[1],path);result=len(path)-1
        elif fn==0x546a14:
            raw=m.read(args[0],32).split(b'\0')[0];assert raw.lower()==b'user32.dll'
            result=0
        elif fn==0x546980:result=self.filter;self.filter=args[0]
        elif fn==0x546998:
            assert args==[255] and e['returnPC']==0x4a584e
            self.exited=True;e.update(halt='ExitProcess-nonreturning',exitCode=args[0],after=self.snapshot())
            self.mark('physical-stop',len(self.events)-1);raise Stop('ExitProcess-nonreturning')
        m.return_from_external(result,4*argc if stdcall else 0)
        e.update(result=result,completed=True,after=self.snapshot(),returnOrder=len(self.timeline))
        self.mark('physical-return',len(self.events)-1)
    def call(self,fn,return_pc,args=(),label=None):
        assert not self.halt
        cpu=self.cpu();frame=STACK_TOP-0x100
        cpu.update(esp=frame,eip=fn)
        c=NativeSourceContext(72,1,0x7ff,0x7ff,*[cpu[k] for k in CONTEXT_FIELDS],0x472,0,0)
        self.m.write(frame,struct.pack('<'+'I'*(len(args)+1),return_pc,*args))
        for k,r in zip(CONTEXT_FIELDS,CONTEXT_REGISTERS):self.m.uc.reg_write(r,cpu[k])
        step=dict(function=fn,returnPC=return_pc,frame=frame,arguments=list(args),label=label,
                  before=self.snapshot(),eventStart=len(self.events),entryStart=len(self.entries),
                  instructionStart=len(self.instructions),completed=False)
        self.mark('root-enter',len(self.steps))
        try:
            result=self.m.call_source(fn,c,return_pc,arguments=args)
            assert result.completed and result.stack_pointer==frame+4
            step.update(completed=True,eax=result.eax)
        except Stop as stop:self.halt=str(stop);step['halt']=str(stop)
        # Root continuation is stopped before observer execution, so its entry
        # (and tail entries sharing that physical frame) complete here.
        final=self.snapshot()
        for e in reversed(self.pending):
            if step['completed']:assert e['returnPC']==return_pc and e['frame']==frame
            e.update(completed=step['completed'],after=final,returnOrder=len(self.timeline),halt=self.halt)
            self.mark('source-return' if step['completed'] else 'source-stop',e['index'])
        self.pending=[]
        step.update(after=final,eventEnd=len(self.events),entryEnd=len(self.entries),instructionEnd=len(self.instructions))
        self.mark('root-return' if step['completed'] else 'root-stop',len(self.steps));self.steps.append(step)
        return step
    def initialize(self):
        self.call(INIT_LOCKS,0x4a7d46,label='prepared-unit-invocation-at-real-caller-continuation')
        if self.halt:return
        assert [e['arguments'][0] for e in self.events]==[0x540e38,0x540e68,0x540e50,0x540e20]
        self.call(INIT,0x4a5896,label='prepared-unit-invocation-at-real-caller-continuation')
    def register(self,r):
        old_base,old_next=self.get(BASE),self.get(NEXT)
        old_record=dict(self.live(old_base));old_bytes=self.m.read(old_base,old_record['capacity'])
        e=self.call(r['leaf'],0x4a5896,label='original-registration-leaf-table-index-'+str(r['tableIndex']))
        if not e['completed']:return
        children=[c for c in self.entries[e['entryStart']:] if c['function']==REGISTER]
        assert len(children)==1 and children[0]['returnPC']==r['returnPC'] and children[0]['arguments']==[r['callback']]
        child=children[0];result=self.states[child['after']]['cpu']['eax']
        if result==0:self.completed_registrations.append(r['callback'])
        else:
            assert result==0xffffffff
            assert self.get(BASE)==old_base and self.get(NEXT)==old_next
            assert self.live(old_base)==old_record and self.m.read(old_base,old_record['capacity'])==old_bytes
        base=self.get(BASE);nxt=self.get(NEXT)
        assert nxt-base==len(self.completed_registrations)*4
        assert list(self.m.words(base,len(self.completed_registrations)))==self.completed_registrations
        assert self.sections[0x540e68]['depth']==0
        return result
    def finish(self):
        return dict(schema=SCHEMA,name=self.name,programSha256=self.p.sha256,domain='crt-memory-service-v1',
                    scope='bounded-registry-composition; no full game initializer execution or native admission',
                    mode=self.mode,failResize=self.fail_resize,failMalloc=self.fail_malloc,physicalStop=self.physical_stop,
                    registrationLeaves=self.leaves,initial=self.initial,states=self.states,pages=self.store.pages,
                    events=self.events,entries=self.entries,steps=self.steps,timeline=self.timeline,instructions=self.instructions,
                    final=self.steps[-1]['after'],halt=self.halt,exited=self.exited,
                    resizeAttempts=self.resize_attempts,completedRegistrations=self.completed_registrations,
                    verification=dict(reconstructedFullStates=self.store.verified,rawObservedBytes=self.store.raw_bytes,
                                      byteIdentical=True),
                    physicalPolicy='Single logical thread. Exact live bases; capacity rounded16. Allocation poison deterministic. CRT sections modeled24-byte Windows-shaped records. Services preserve registers except EAX/ESP/EIP; default GUI diagnostic library-unavailable. No callback invocation.',
                    invocationPolicy='Persistent CPU/fullstack/image/heap; root harness prepares entry/return and arguments at fixed bounded frame. Initializer and leaf outer calls are explicit prepared calls at genuine caller continuation; child CALLs execute original instructions.')


def profiles(selected=None):
    names=['inplace126','moving126','mixed126','resize-fail-retry','moving-late-fail-retry','null-callback','first-allocation-failure']
    names += ['physical-prefix-'+str(n) for n in (1,4,5,6,8,71,105,106,107)]
    names += ['fatal-physical-prefix-'+str(n) for n in (6,7,8,9,10)]
    for index,name in enumerate(names):
        if selected and name not in selected:continue
        mode='moving' if name in ('moving126','moving-late-fail-retry') else 'mixed' if name=='mixed126' else 'inplace'
        q=Reference(name,mode,fail_resize=1 if name=='resize-fail-retry' else 24 if name=='moving-late-fail-retry' else 0,
                    fail_malloc=name=='first-allocation-failure' or name.startswith('fatal-physical-prefix-'),
                    physical_stop=int(name.rsplit('-',1)[1]) if 'physical-prefix-' in name else 0,index=index)
        q.initialize()
        if not q.halt:
            if name=='null-callback':
                q.call(REGISTER,0x42520a,args=(0,),label='explicit-unit-null-callback')
                assert q.steps[-1]['eax']==0xffffffff and q.get(NEXT)-q.get(BASE)==4 and q.get(q.get(BASE))==0
            else:
                for r in q.leaves:
                    status=q.register(r)
                    if q.halt:break
                    if status==0xffffffff:
                        assert name in ('resize-fail-retry','moving-late-fail-retry') and q.register(r)==0
                if not q.halt:
                    assert len(q.completed_registrations)==126
                    assert q.live(q.get(BASE))['capacity']==512
                    assert q.resize_attempts==(25 if q.fail_resize else 24)
                    assert q.malloc_attempts==1
                    assert sum(e['function']==CAPACITY for e in q.events)==150+(2 if q.fail_resize else 0)
                    actual=[e['arguments'][1] for e in q.events if e['function']==REALLOC and e.get('result')]
                    assert actual==list(range(144,513,16))
        if name=='first-allocation-failure':
            assert q.exited and q.halt=='ExitProcess-nonreturning'
            assert q.get(BASE)==0 and q.get(NEXT)==0 and q.sections[0x540e68]['depth']==1
            assert any(e['function']==0x4a4860 for e in q.entries)
        if 'physical-prefix-' in name:assert q.halt=='physical-prefix-stop'
        yield q.finish()
        del q
        gc.collect()


def verify_file(path):
    """Independent disk roundtrip decoder: no live machine/cache is consulted."""
    with gzip.open(path,'rt') as f:row=json.load(f)
    pages=[]
    for record in row['pages']:
        b=bytes.fromhex(record['bytes']);assert len(b)==PAGE and sha(b)==record['sha256'];pages.append(b)
    memory={}
    for index,state in enumerate(row['states']):
        m=state['memory'];assert m['parent']==(index-1 if index else None)
        for a,pid in m['pageChanges']:memory[a]=pages[pid]
        for r in m['ranges']:
            b=b''.join(memory[a] for a in range(r['address'],r['address']+r['size'],PAGE))
            assert len(b)==r['size'] and sha(b)==r['sha256']
    return dict(states=len(row['states']),pages=len(pages),steps=len(row['steps']),
                physicalEvents=len(row['events']),sourceEntries=len(row['entries']),instructions=len(row['instructions']),
                registrations=len(row['completedRegistrations']),resizeAttempts=row['resizeAttempts'],halt=row['halt'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path);ap.add_argument('--profile',action='append');args=ap.parse_args()
    out=args.output.resolve();allowed=Path('work/native-crt-exit-registry-check').resolve()
    assert out==allowed or allowed in out.parents
    out.mkdir(parents=True,exist_ok=True)
    sources=[Path(__file__),Path('Tests/clawparity/program.py'),Path('Tests/clawparity/kernel.py'),Path('Tests/clawparity/env.py')]
    hashes={str(p):file_sha(p) for p in sources};reports=[]
    for row in profiles(args.profile):
        path=out/(row['name']+'.json.gz');assert not path.exists(),'Frozen references are immutable; choose a fresh output directory.'
        with gzip.open(path,'wt',compresslevel=5) as f:json.dump(row,f,separators=(',',':'))
        name=row['name'];del row
        report=dict(name=name,path=str(path),sha256=file_sha(path),bytes=path.stat().st_size,**verify_file(path))
        reports.append(report);print(json.dumps(report),flush=True)
    assert all(file_sha(p)==v for p,v in hashes.items()),'Producer input changed during generation'
    provenance=dict(schema=SCHEMA,status='PASS',programSha256=claw().sha256,producerHashes=hashes,profiles=reports,
                    authorExposure=['work/coordination/crt-lock-records-gate.log: accidental family gate result summary',
                                    'work/coordination/crt-exit-registry-gate.log: accidental family gate result summary'],
                    independence='Numerical states derived only from pinned original execution and explicit physical policy. Author saw gate metadata; fresh uncontaminated review required. No native implementation/cases/output bytes used.',
                    verification='Every live full range decoded byte-identically at capture; independent disk roundtrip checks all full-range SHA256s and pages.')
    target=out/'provenance.json';assert not target.exists();target.write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',profiles=len(reports),provenance=str(target))),flush=True)

if __name__=='__main__':main()
