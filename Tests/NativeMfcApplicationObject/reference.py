"""Independent whole original CWinApp source reference; no native code/results.

Only hash-pinned original instructions and declared physical services execute.
Output and source-derived evidence stay in ignored work/. Existing references
are reused without modification. This is not a CWinApp exception dispatcher.
"""
import argparse
import gzip
import hashlib
import json
import random
import struct
from pathlib import Path
from Tests.NativeMfcApplicationThreadSource.reference import Reference as ApplicationReference, MEMBERS
from Tests.NativeMfcColdModule.reference import ARGC, REFERENCE_ONLY, MODULE_OWNER, Stop
from Tests.NativeMfcTlsValuesSource.reference import STATIC, OWNER, PUBLICATION
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.kernel import STACK_BASE, STACK_SIZE, STACK_TOP, CONTEXT_FIELDS
from Tests.clawparity import program
from unicorn import UC_HOOK_CODE

ROOT, END, RETURN = 0x50257f, 0x502669, 0x4251ff
ROOT_HASH = '773a9a0d6f2a97ff7aa5c5a391b2439094c9b172ecbcada61b8795de5ccfb682'
STRDUP, MALLOC = 0x4a56e0, 0x4a48e0
STRDUP_HASH = '84b588289c7dd00fdb228fadca0787eef9be41811872221d5df7e7ec1e2be1b7'
RECEIVER, NAME = 0x537008, 0x524eec
# These observation-only member entries execute unchanged, never as callbacks.
# The owning complete application/thread constructors remain source candidates.
OBSERVATION_ONLY = set(REFERENCE_ONLY) | set(MEMBERS) | {0x4f6a9a, 0x50354d}
ADDITIONAL = {0x503510, STRDUP, 0x4f6a9a, 0x50354d}
SERVICES = {0x546cd0:('GetCursorPos',1), 0x5469bc:('GetCurrentThread',0),
            0x5469c0:('GetCurrentThreadId',0), 0x546958:('RaiseException',4),
            0x546b0c:('GetLastError',0), 0x546ab8:('SetLastError',1)}
HEADERS = {0x503510:0x472, STRDUP:0x472, 0x50228f:0x400,
           0x50335e:0x400, 0x502301:0x472, 0x50210b:0x472}

def digest(data):return hashlib.sha256(data).hexdigest()
def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def source_context(cpu,preserve=0):
    c=NativeSourceContext(72,1,0x7ff,0x7ff,*[cpu[k] for k in CONTEXT_FIELDS],preserve,0,0)
    return {k:getattr(c,k) for k,_ in c._fields_}

class Reference(ApplicationReference):
    def __init__(self,name,index=0):
        self.receiver=RECEIVER;self.name_pointer=NAME;self.input_ranges=[]
        self.cursor_success=True;self.cursor_point=(-31,57);self.thread_handle=0xffffffff
        self.thread_id=1;self.last_error=0;self.visited=set();self.root_bytes=set();self.index=index
        self.malloc_null=False;self.malloc_rescan=None;self.tls_set_false=False
        self.service_null=None
        super().__init__(name)
        assert digest(self.m.read(ROOT,END-ROOT))==ROOT_HASH
        assert digest(self.m.read(STRDUP,80))==STRDUP_HASH
        assert self.m.read(NAME,5)==b'Claw\0' and self.m.read(RECEIVER,0xc0)==bytes(0xc0)
        for a,(label,_) in SERVICES.items():
            assert self.p.imports[a].split('!')[-1]==label
            self.imports[a]=self.m.import_stub[a]
        self.reverse={v:k for k,v in self.imports.items()}
        self.m.intercept(MALLOC)
        for a in ADDITIONAL:self.m.observe(a,self.observe)
        for a in (0x5025cf,0x5025d2,0x5025e7,0x5025ea):self.m.observe(a,self.root_publication)
        self.m.uc.hook_add(UC_HOOK_CODE,self.instruction,begin=self.p.text[0],end=self.p.text[1]-1)
        self.cold=self.snapshot()
        self.initial_image_data=self.m.read(self.p.data_start,self.p.base+self.p.size-self.p.data_start).hex()
    def instruction(self,uc,address,size,user):
        self.visited.add(address)
        if ROOT<=address<END:self.root_bytes.update(range(address,min(address+size,END)))
    def snapshot(self):
        s=super().snapshot()
        s.update(receiver=self.receiver,receiverBytes=self.m.read(self.receiver,0xc0).hex(),
                 inputRanges=[dict(address=a,size=n,bytes=self.m.read(a,n).hex()) for a,n in self.input_ranges],
                 currentThreadHandle=self.thread_handle,currentThreadId=self.thread_id,lastError=self.last_error)
        if self.thread_id!=1:
            for section in s['sections']:
                if section['owner']==1:section['owner']=self.thread_id
        s['thread']=self.thread_id
        s['borrowedStorage'].append(dict(address=self.receiver,size=0xc0,kind='caller-owned-application-object'))
        return s
    def observe(self,m,address):
        sp=self.cpu()['esp'];argc=1 if address in (*MEMBERS,STRDUP) else ARGC.get(address,0)
        # Register module+0x1070 as an interior identity as soon as the genuine
        # caller supplies it, before the genuine getter begins its first write.
        if address==0x50335e and self.get(sp)==0x5025cf:
            module=self.get(MODULE_OWNER);owner=module+0x1070
            assert module and self.cpu()['ecx']==owner and self.get(sp+4)==0x502301
            if owner not in self.owners:
                self.owners.append(owner)
                identity=next(a['identity'] for a in self.allocations if a['address']==module and a['live'])
                self.interior_owners.append(dict(address=owner,size=4,allocation=module,allocationSize=0x1074,identity=identity,offset=0x1070))
        e=dict(function=address,frame=sp,returnPC=self.get(sp),arguments=list(m.words(sp+4,argc)),inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),order=len(self.timeline),observation='original-only-internal' if address in OBSERVATION_ONLY else 'source-boundary-candidate')
        if address in HEADERS:e['inputContext']=source_context(e['inputCPU'],HEADERS[address])
        if address==0x4a48c0:e['inputContext']=source_context(e['inputCPU']);e['observation']='compiler-context-boundary'
        if address==0x4f50fd:e['observation']='original-throw-helper-continues'
        self.entries.append(e);self.pending_entries.append(e);self.mark('entry',len(self.entries)-1)
        pc=e['returnPC']
        if pc not in self.return_observers:self.return_observers.add(pc);self.m.observe(pc,self.returned_child)
    def returned_child(self,m,address):
        matching=[e for e in self.pending_entries if e['returnPC']==address]
        super().returned_child(m,address)
        if matching and 'inputContext' in matching[-1]:
            e=matching[-1];e['outputContext']=dict(e['inputContext'],**e['outputCPU'])
    def root_publication(self,m,address):
        e=dict(function=address,observation='application-publication-'+{0x5025cf:'before',0x5025d2:'after',0x5025e7:'module-before',0x5025ea:'module-after'}[address],cpu=self.cpu(),stack=self.stack(),state=self.snapshot(),rootStep=len(self.steps),order=len(self.timeline))
        self.publications.append(e);self.mark('publication',len(self.publications)-1)
    def special_event(self,s,count,target):
        sp=self.cpu()['esp'];a=list(self.m.words(sp+4,count))
        e=dict(function=s,target=target if s in (0x5469c4,0x546aac) else s,importedTarget=target,frame=sp,stackPointer=sp,returnPC=self.get(sp),arguments=a,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),completed=False,order=len(self.timeline))
        self.events.append(e);self.mark('physical-enter',len(self.events)-1)
        if self.physical_fail_at==len(self.events):self.stop_event(e,'physical-service')
        return e,a
    def stop_event(self,e,reason):
        e.update(halt=reason,outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot(),stopOrder=len(self.timeline))
        self.mark('physical-stop',len(self.events)-1);raise Stop(reason)
    def finish_event(self,e,r,count):
        self.m.return_from_external(r,count*4)
        e.update(result=r,completed=True,after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),returnOrder=len(self.timeline));self.mark('physical-return',len(self.events)-1)
    def external(self,m,target):
        s=MALLOC if target==MALLOC else self.reverse.get(target)
        if s==MALLOC:
            e,a=self.special_event(s,1,target);self.allocation_attempts+=1;e['allocationAttempt']=self.allocation_attempts
            r=0 if self.malloc_null or self.allocation_attempts==self.allocation_fail_at else self.alloc(a[0],'malloc')
            if self.malloc_rescan is not None:m.write(self.name_pointer,self.malloc_rescan)
            self.finish_event(e,r,0);return
        if s in SERVICES:
            e,a=self.special_event(s,SERVICES[s][1],target);r=0
            if s==0x546cd0:
                assert a==[self.receiver+0x5c] and e['returnPC']==0x50356f
                if self.cursor_success:m.write(a[0],struct.pack('<ii',*self.cursor_point))
                r=int(self.cursor_success)
            elif s==0x5469bc:r=self.thread_handle
            elif s==0x5469c0:r=self.thread_id
            elif s==0x546b0c:r=self.last_error
            elif s==0x546ab8:self.last_error=a[0]
            elif s==0x546958:
                assert a[1]==1;self.stop_event(e,'physical-RaiseException-nonreturning')
            self.finish_event(e,r,len(a));return
        if s in (0x546aac,0x546a9c) and self.get(self.cpu()['esp']+4) not in self.sections:
            e,a=self.special_event(s,1,target)
            self.stop_event(e,'physical-uninitialized-critical-section-'+hex(a[0]))
        if s==0x546a7c and self.get(self.cpu()['esp']+4) not in self.tls:
            e,a=self.special_event(s,1,target)
            self.stop_event(e,'physical-unallocated-tls-index-'+hex(a[0]))
        if s==0x546a84 and self.tls_set_false:
            e,a=self.special_event(s,2,target);assert a[0] in self.tls;self.finish_event(e,0,2);return
        if s==self.service_null:
            count=1
            e,a=self.special_event(s,count,target);self.finish_event(e,0,count);return
        return super().external(m,target)
    def call(self,label='whole-original-root',name=NAME,receiver=RECEIVER):
        self.receiver=receiver;self.name_pointer=name;i=len(self.steps);seed=ROOT+self.index*0x10001+i
        rng=random.Random(seed);self.m.write(STACK_BASE,rng.randbytes(STACK_SIZE))
        frame=(STACK_TOP-0x100,STACK_BASE+0x1000,STACK_BASE+STACK_SIZE-0x100)[self.index%3]-i*0x40
        fs=0xffffffff if self.index%3==0 else STACK_BASE+0x10000
        if fs!=0xffffffff:
            self.put(fs,0xffffffff if self.index%3==1 else fs+0x20);self.put(fs+4,0x5086f4);self.put(fs+8,0xffffffff)
            if self.index%3==2:self.put(fs+0x20,0xffffffff);self.put(fs+0x24,0x5086f4);self.put(fs+0x28,0xffffffff)
        vals=[rng.getrandbits(32) for _ in CONTEXT_FIELDS];vals[2]=receiver;vals[7]=frame;vals[8]=ROOT;vals[9]=rng.getrandbits(32)&0x8d5|2;vals[10]=fs
        c=NativeSourceContext(72,1,0x7ff,0x7ff,*vals,0x472,0,0);self.put(frame,RETURN);self.put(frame+4,name)
        e=dict(function=ROOT,receiver=receiver,arguments=[name],frame=frame,seed=seed,returnPC=RETURN,label=label,inputContext={k:getattr(c,k) for k,_ in c._fields_},stackBefore=self.stack(),before=self.snapshot(),eventStart=len(self.events),entryStart=len(self.entries),order=len(self.timeline))
        self.mark('root-enter',i)
        try:
            result=self.m.call_source(ROOT,c,RETURN,convention='thiscall',ecx=receiver,arguments=[name])
            assert result.completed and result.eax==receiver and result.stack_pointer==frame+8
            e.update(completed=True,eax=result.eax,halt=None,outcome='returned',outputContext={k:getattr(c,k) for k,_ in c._fields_})
        except Stop as stop:e.update(completed=False,eax=None,halt=str(stop),outcome='physical-host-stop',outputContext=None)
        assert not e['completed'] or not self.pending_entries
        for child in self.pending_entries:
            child.update(completed=False,halt=e['halt'],outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot(),stopOrder=len(self.timeline));self.mark('entry-stop',self.entries.index(child))
        self.pending_entries=[]
        e.update(after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),eventCount=len(self.events),entryCount=len(self.entries),returnOrder=len(self.timeline));self.mark('root-return' if e['completed'] else 'root-stop',i);self.steps.append(e)
        if e['completed']:
            module=self.get(MODULE_OWNER);app=next(child['outputCPU']['eax'] for child in reversed(self.entries) if child['function']==0x50335e and child['returnPC']==0x5025cf and child['completed'])
            assert self.get(module+4)==receiver and self.get(app+4)==receiver
            assert self.get(receiver+0x28)==self.thread_handle and self.get(receiver+0x2c)==self.thread_id
            assert e['outputContext']['preserveMask']==0x472 and e['outputCPU']['fsHead']==fs
            for event in self.events[e['eventStart']:]:
                if event['function'] in (0x5469bc,0x5469c0):
                    assert bytes.fromhex(event['before']['localBytes'][str(app)])[4:8]==struct.pack('<I',receiver)
        # Verify actual direct-child source frames independently of native code.
        expected={0x502597:(0x503510,frame-36),0x5025af:(STRDUP,frame-40),0x5025bd:(0x50228f,frame-36),0x5025cf:(0x50335e,frame-40)}
        for child in self.entries[e['entryStart']:]:
            if child['returnPC'] in expected:
                function,sp=expected[child['returnPC']];assert child['function']==function and child['frame']==sp
            if child['function']==0x4a48c0 and child['returnPC']==0x502589:assert child['frame']==frame-4 and child['inputCPU']['eax']==0x5086f4
        for event in self.events[e['eventStart']:]:
            if event['function']==MALLOC:assert event['frame']==frame-60 and event['returnPC']==0x4a56fc
            if event['function'] in (0x5469bc,0x5469c0):assert event['frame']==frame-36
        return e['eax']
    def finish(self):
        row=super().finish()
        row.update(schema='claw-original-application-object-v1',root=ROOT,rootEnd=END,rootSha256=ROOT_HASH,rootReturn=RETURN,referenceOnlyEntries=sorted(OBSERVATION_ONLY),initialImageData=self.initial_image_data,imageDataStart=self.p.data_start,coveredRootBytes=sorted(self.root_bytes),instructionPCs=sorted(self.visited),profileIndex=self.index,cursorSuccess=self.cursor_success,cursorPoint=self.cursor_point,threadHandle=self.thread_handle,threadId=self.thread_id,mallocNull=self.malloc_null,mallocRescan=None if self.malloc_rescan is None else self.malloc_rescan.hex(),tlsSetFalse=self.tls_set_false,serviceNull=self.service_null,scope='Whole original 234-byte CWinApp normal return or exact physical stop; no guest catch/unwind or cold CRT startup claim.',setupPolicy='Pinned image state; modeled physical ownership; no preseeded module/TLS/CRT caches. Prepared warm receiver inputs are explicit.')
        row.pop('moduleRoot',None);row.pop('moduleRootReturn',None)
        row['missingNativePrefixes']=[dict(entryIndex=i,function=e['function'],order=e['order'],description='Observation at original throw helper entry; original execution continues to separately recorded physical stop.') for i,e in enumerate(self.entries) if e['function']==0x4f50fd]
        row['physicalPolicy']='One logical thread per profile; inherited lock owner token 1 is serialized as threadId. TLS indices are local to that same logical thread. Cursor FALSE leaves POINT unchanged. Known malloc is a physical allocation boundary. Services preserve CPU except EAX/ESP/EIP, with no preseeded CRT state.'
        row['nativeBoundaryClaims']=False
        assert [x['order'] for x in self.timeline]==list(range(len(self.timeline)))
        return row


def profiles():
    q=Reference('actual-static-Claw-cold-and-genuine-warm');q.call();physical=len(q.events);allocations=q.allocation_attempts
    assert q.get(RECEIVER+0x78) and q.m.read(q.get(RECEIVER+0x78),5)==b'Claw\0'
    stable_module=q.get(MODULE_OWNER);stable_app=q.get(q.get(q.container()+12)+8)
    allocation_count=len(q.allocations);warm_receiver=0x620e0003
    q.m.write(warm_receiver,bytes([0xa7])*0xc0);q.input_ranges.append((warm_receiver,0xc0))
    q.call('warm-original-module-and-application-new-receiver',name=0,receiver=warm_receiver)
    assert len(q.allocations)==allocation_count and q.get(MODULE_OWNER)==stable_module and q.get(stable_app+4)==warm_receiver
    yield q.finish()
    for i in range(16):
        q=Reference('bounded-name-cursor-register-frame-'+str(i),i+1)
        receiver=0x620e0000+(i%4);name=0 if i==0 else 0x620e1000+(i%4)
        q.m.write(receiver,bytes((j*53+i*29)&255 for j in range(0xc0)));q.input_ranges.append((receiver,0xc0))
        if name:
            n=0 if i==1 else i-1 if i<12 else (31,64,127,255)[i-12]
            content=bytes((j*53+i*37)%255+1 for j in range(n))+b'\0';q.m.write(name,content);q.input_ranges.append((name,len(content)))
        q.cursor_success=i%2==0;q.cursor_point=((0,0),(-1,1),(2147483647,-2147483648),(-2147483648,2147483647))[i%4]
        q.thread_id=(1,57,0x11223344,0x7ffffffe)[i%4]
        q.call(name=name,receiver=receiver);assert q.steps[-1]['completed'];yield q.finish()
    for n in range(1,allocations+1):
        q=Reference('allocation-null-at-'+str(n));q.allocation_fail_at=n;q.call()
        assert q.steps[-1]['completed'] if n==1 else not q.steps[-1]['completed']
        yield q.finish()
    q=Reference('tls-index-exhausted-original-failure');q.tls_failure=True;q.call();assert not q.steps[-1]['completed'];yield q.finish()
    q=Reference('tls-publication-false-original-flow');q.tls_set_false=True;q.call();assert q.tls[0]==0;yield q.finish()
    for n in range(1,physical+1):
        q=Reference('physical-service-stop-'+str(n));q.physical_fail_at=n;q.call()
        assert q.steps[-1]['halt']=='physical-service' and len(q.events)==n;yield q.finish()
    q=Reference('malloc-rescan-shorter-valid-source');name=0x620e1001;q.m.write(name,b'abcdefgh\0');q.input_ranges=[(name,9)];q.malloc_rescan=b'xyz\0';q.call(name=name)
    assert q.m.read(q.get(RECEIVER+0x78),4)==b'xyz\0';yield q.finish()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path);args=ap.parse_args();out=args.output.resolve()
    assert Path('work/native-mfc-application-object-check').resolve() in out.parents
    out.parent.mkdir(parents=True,exist_ok=True)
    p=program.claw();correct=program.CLAW_SHA256;program.CLAW_SHA256='0'*64
    try:
        try:program.claw()
        except ValueError:wrong_pin_rejected=True
        else:raise AssertionError('wrong pin accepted')
    finally:program.CLAW_SHA256=correct
    assert program.claw().sha256==p.sha256
    files=[Path(__file__),Path('Tests/NativeMfcColdModule/reference.py'),Path('Tests/NativeMfcApplicationThreadSource/reference.py'),Path('Tests/NativeMfcTlsValuesSource/reference.py'),Path('Tests/NativeMfcTlsManagerSource/reference.py'),Path('Tests/NativeMfcThreadRecords/reference.py'),Path('Tests/clawparity/program.py'),Path('Tests/clawparity/kernel.py'),Path('Tests/clawparity/env.py')]
    hashes={str(f):file_hash(f) for f in files};counts=dict(profiles=0,roots=0,physicalEvents=0,childEntries=0,completedRoots=0);coverage=set();stops={}
    with gzip.open(out,'wt',compresslevel=5) if out.suffix=='.gz' else out.open('w') as f:
        f.write('[')
        for row in profiles():
            if counts['profiles']:f.write(',')
            json.dump(row,f,separators=(',',':'));counts['profiles']+=1;counts['roots']+=len(row['steps']);counts['physicalEvents']+=len(row['events']);counts['childEntries']+=len(row['entries']);counts['completedRoots']+=sum(s['completed'] for s in row['steps']);coverage.update(row['coveredRootBytes'])
            for s in row['steps']:
                if s['halt']:stops[s['halt']]=stops.get(s['halt'],0)+1
            print(json.dumps(dict(profile=row['name'],roots=len(row['steps']),completed=row['steps'][-1]['completed'],halt=row['steps'][-1]['halt'])),flush=True)
        f.write(']\n')
    assert coverage==set(range(ROOT,END)),sorted(set(range(ROOT,END))-coverage)
    assert all(file_hash(f)==v for f,v in hashes.items())
    report=dict(status='PASS',schema='claw-original-application-object-v1',**counts,coveredBytes=len(coverage),requiredBytes=END-ROOT,sha256=file_hash(out),bytes=out.stat().st_size,programSha256=p.sha256,rootSha256=ROOT_HASH,strdupSha256=STRDUP_HASH,producerHashes=hashes,wrongPinRejected=wrong_pin_rejected,positivePinAccepted=True,stops=stops,output=str(out))
    out.with_name('reference-provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
