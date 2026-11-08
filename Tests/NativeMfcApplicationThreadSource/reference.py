"""Original-only module/application boundary pair; CWinApp body is not claimed.

The four pinned instructions at the module return produce the second root's
actual CPU/stack. All application factory/constructor code runs unchanged.
"""
import hashlib
import json
import sys
from pathlib import Path
from Tests.NativeMfcColdModule.reference import Reference as ModuleReference, Stop, MODULE_OWNER
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.kernel import CONTEXT_FIELDS, STACK_SIZE
from unicorn.x86_const import UC_X86_REG_ESP

GET, FACTORY, CONSTRUCTOR = 0x50335e, 0x502301, 0x50210b
MEMBERS = (0x4f5e89,0x4f5133)

class Reference(ModuleReference):
    def __init__(self,name):
        self.bridges=[];self.interior_owners=[]
        super().__init__(name)
        for a in (FACTORY,CONSTRUCTOR,*MEMBERS):self.m.observe(a,self.observe)
    def snapshot(self):
        s=super().snapshot();s['interiorOwners']=[dict(a) for a in self.interior_owners];return s
    def observe(self,m,address):
        super().observe(m,address)
        if address in (CONSTRUCTOR,*MEMBERS):
            e=self.entries[-1];e['observation']='original-only-internal'
            if address in MEMBERS:e['arguments']=list(m.words(e['frame']+4,1))
    def external(self,m,target):
        if self.reverse.get(target)!=0x546a80:return super().external(m,target)
        s=0x546a80;sp=m.register(UC_X86_REG_ESP);a=list(m.words(sp+4,3))
        e=dict(function=s,target=s,importedTarget=target,frame=sp,stackPointer=sp,returnPC=self.get(sp),arguments=a,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),completed=False,order=len(self.timeline))
        self.events.append(e);self.mark('physical-enter',len(self.events)-1)
        if self.physical_fail_at==len(self.events):
            e.update(halt='physical-service',outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot());raise Stop('physical-service')
        assert a[0] in self.locals and a[2]==2
        self.allocation_attempts+=1;e['allocationAttempt']=self.allocation_attempts;r=0
        if self.allocation_attempts!=self.allocation_fail_at:
            old=a[0];r=self.alloc(a[1],'local');m.write(r,m.read(old,min(self.locals[old],a[1])));self.retire(old);del self.locals[old];self.locals[r]=a[1]
        m.return_from_external(r,12)
        e.update(result=r,completed=True,after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),returnOrder=len(self.timeline));self.mark('physical-return',len(self.events)-1)
    def application(self,label):
        module=self.get(MODULE_OWNER)
        assert module and self.locals[module]==0x1074 and self.steps[-1]['completed']
        assert self.cpu()['eip']==0x5025bd and self.cpu()['eax']==module
        owner=module+0x1070
        if owner not in self.owners:
            self.owners.append(owner)
            identity=next(a['identity'] for a in self.allocations if a['address']==module and a['live'])
            self.interior_owners.append(dict(address=owner,size=4,allocation=module,allocationSize=0x1074,identity=identity,offset=0x1070))
        bridge=dict(fromPC=0x5025bd,toPC=GET,inputCPU=self.cpu(),stackBefore=self.stack(),before=self.snapshot(),rootStep=len(self.steps),order=len(self.timeline),observation='original-only-caller-fragment')
        # Execute the real caller's move/push/lea/call; there is no recreated frame.
        result=self.m._execute(0x5025bd,GET,30)
        assert result.completed and self.cpu()['ecx']==owner and self.get(self.cpu()['esp'])==0x5025cf and self.get(self.cpu()['esp']+4)==FACTORY
        bridge.update(outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot());self.bridges.append(bridge);self.mark('caller-fragment',len(self.bridges)-1)
        vals=[self.cpu()[k] for k in CONTEXT_FIELDS];c=NativeSourceContext(72,1,0x7ff,0x7ff,*vals,0x400,0,0)
        frame=c.esp;pc=0x5025cf;i=len(self.steps)
        e=dict(function=GET,receiver=owner,arguments=[FACTORY],frame=frame,returnPC=pc,label=label,inputProvenance='original-5025bd-through-5025ca-from-previous-module-root-output',bridgeIndex=len(self.bridges)-1,inputContext={k:getattr(c,k) for k,_ in c._fields_},stackBefore=self.stack(),before=self.snapshot(),eventStart=len(self.events),entryStart=len(self.entries),order=len(self.timeline))
        self.mark('root-enter',i)
        try:
            result=self.m.call_source(GET,c,pc,convention='thiscall',ecx=owner,arguments=[FACTORY])
            assert result.completed and result.stack_pointer==frame+8
            e.update(completed=True,eax=result.eax,halt=None,outcome='returned',outputContext={k:getattr(c,k) for k,_ in c._fields_})
        except Stop as stop:e.update(completed=False,eax=None,halt=str(stop),outcome='physical-host-stop' if str(stop)=='physical-service' else 'missing-native-dependency-prefix',outputContext=None)
        for child in self.pending_entries:
            completed=e['completed'] and self.cpu()['eip']==child['returnPC'];assert not e['completed'] or completed
            child.update(completed=completed,halt=e['halt'],outputCPU=self.cpu(),stackAfter=self.stack(),after=self.snapshot());child['returnOrder' if completed else 'stopOrder']=len(self.timeline);self.mark('return' if completed else 'entry-stop',self.entries.index(child))
        self.pending_entries=[]
        e.update(after=self.snapshot(),outputCPU=self.cpu(),stackAfter=self.stack(),eventCount=len(self.events),entryCount=len(self.entries),returnOrder=len(self.timeline));self.mark('root-return' if e['completed'] else 'root-stop',i);self.steps.append(e)
        return e['eax']
    def finish(self):
        row=super().finish();row.update(schema='claw-original-application-thread-source-v1',root=GET,rootReturn=0x5025cf,moduleRoot=0x50228f,moduleRootReturn=0x5025bd,bridges=self.bridges,referenceOnlyEntries=sorted(set(row['referenceOnlyEntries'])|{CONSTRUCTOR,*MEMBERS}),scope='Real module root then genuine caller fragment then application TLS root; omitted CWinApp body is not executed or claimed.')
        return row

def profiles():
    q=Reference('cold-module-application-and-repeat-warm-pair');module=q.call('cold-module');start=len(q.events);app=q.application('cold-application')
    assert q.locals[app]==0x84 and q.get(app)==0x510204 and q.get(app+0xc)==0x54 and q.get(app+0x28)==0x4f63d0
    assert q.get(module+0x1070)==2 and q.get(0x53ec9c)==1
    container=q.container();array=q.get(container+12)
    assert q.get(array+8)==app and q.get(container+8)==3
    assert q.get(app+4)==0 and q.get(app+0x10)==0
    assert any(e['function']==CONSTRUCTOR and e['completed'] for e in q.entries)
    assert sum(e['function'] in MEMBERS for e in q.entries)==3
    physical_count=len(q.events)-start;allocation_count=q.allocation_attempts-5
    ledger=[dict(a) for a in q.allocations];assert q.call('warm-module')==module;n=len(q.events);assert q.application('warm-application')==app
    assert len(q.events)==n+1 and q.events[-1]['function']==0x546a7c and q.allocations==ledger
    yield q.finish()
    for n in range(1,allocation_count+1):
        q=Reference('application-allocation-failure-'+str(n));module=q.call('cold-module');q.allocation_fail_at=q.allocation_attempts+n;q.application('application-failure')
        assert q.steps[-1]['halt']=='missing-native-exception-0x4f50fd' and q.cpu()['eip']==0x4f50fd
        assert q.get(MODULE_OWNER)==module and q.get(module+0x1070)==2
        yield q.finish()
    for n in range(1,physical_count+1):
        q=Reference('application-physical-service-stop-'+str(n));q.call('cold-module');q.physical_fail_at=len(q.events)+n;q.application('application-prefix')
        assert q.steps[-1]['halt']=='physical-service' and not q.events[-1]['completed']
        yield q.finish()

if __name__=='__main__':
    output=Path(sys.argv[1]).resolve();assert Path('work').resolve() in output.parents;output.parent.mkdir(parents=True,exist_ok=True)
    counts=dict(profiles=0,roots=0,physicalEvents=0,childEntries=0,completedRoots=0)
    with output.open('w') as f:
        f.write('[')
        for row in profiles():
            if counts['profiles']:f.write(',')
            json.dump(row,f,separators=(',',':'));counts['profiles']+=1;counts['roots']+=len(row['steps']);counts['physicalEvents']+=len(row['events']);counts['childEntries']+=len(row['entries']);counts['completedRoots']+=sum(s['completed'] for s in row['steps'])
        f.write(']\n')
    h=hashlib.sha256()
    with output.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    print(json.dumps(dict(status='PASS',**counts,sha256=h.hexdigest(),bytes=output.stat().st_size)))
