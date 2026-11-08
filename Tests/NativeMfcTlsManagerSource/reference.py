"""Fresh original MFC manager calls; only physical imports return host values.

The unresolved native exception dependency is observed at its real entry and
halts the bounded prefix. No throw/exception return is fabricated. The canonical
family gate separately observes the unchanged throw chain at RaiseException.
"""
import json
import struct
import random
import sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_TOP, STACK_BASE, STACK_SIZE, CONTEXT_FIELDS, CONTEXT_REGISTERS
from Tests.clawparity.env import NativeSourceContext
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_ESP

IMPORTS = {
 0x546a90: ('TlsAlloc',0), 0x546a7c: ('TlsGetValue',1), 0x546a84: ('TlsSetValue',2),
 0x546aa4: ('InitializeCriticalSection',1), 0x546aac: ('EnterCriticalSection',1),
 0x546a9c: ('LeaveCriticalSection',1), 0x546aa0: ('DeleteCriticalSection',1),
 0x546b1c: ('GlobalAlloc',2), 0x546a8c: ('GlobalHandle',1), 0x5469c8: ('GlobalUnlock',1),
 0x546a88: ('GlobalReAlloc',3), 0x5469c4: ('GlobalLock',1), 0x546ac0: ('GlobalFree',1),
 0x546aa8: ('LocalAlloc',2), 0x546a80: ('LocalReAlloc',3), 0x5469d8: ('LocalFree',1),
}
INIT, SLOT = 0x502fb6, 0x502ff8
class Stop(Exception): pass

def reference(name, operations, manager_count=1, fail=None, fail_at=None):
    p = claw()
    m = Machine(p,0x62000000,0x100000)
    for slot,(label,_) in IMPORTS.items(): assert p.imports[slot].split('!')[-1] == label
    imports = {slot:m.import_stub[slot] for slot in IMPORTS}
    lock_imports = {slot:m.import_stub[slot] for slot in (0x546abc,0x546aa4,0x546aac,0x546a9c)}
    initial = m.read(0x5408e0,0x210).hex()
    reverse = {value:key for key,value in imports.items()}
    next_data, next_handle, next_tls = 0x62000000,0x78000000,0
    managers, blocks, sections, indices, events, steps, entries = [],{},{},[],[],[],[]
    def allocate(count):
        nonlocal next_data
        ptr=next_data;next_data=(ptr+count+15)&~15
        m.write(ptr,b'\xcc'*count)
        return ptr
    for _ in range(manager_count): managers.append(allocate(0x34))
    def put(ptr,value):m.write(ptr,struct.pack('<I',value))
    def snapshot():
        return dict(blocks=[dict(blocks[h]) for h in sorted(blocks)],
                    sections=[dict(sections[s]) for s in sorted(sections)],
                    managerBytes={str(t):m.read(t,0x34).hex() for t in managers},
                    blockBytes={str(b['data']):m.read(b['data'],b['size']).hex() for b in blocks.values()},
                    tlsIndices=indices[:])
    def cpu():
        return dict(zip(CONTEXT_FIELDS, [m.register(r) for r in CONTEXT_REGISTERS] + [m.fs_head]))
    def context_dict(context):
        return {field: getattr(context, field) for field, _ in context._fields_}
    current=None
    def external(machine,target):
        nonlocal next_handle,next_tls
        slot=reverse[target];count=IMPORTS[slot][1]
        sp=m.register(UC_X86_REG_ESP);args=list(m.words(sp+4,count));result=0
        offset=(8 if slot==0x546a90 else 12) if current['function']==INIT else (36 if slot==0x546b1c else 40 if slot==0x546a88 else 32)
        assert sp == current['frame']-offset, (name,hex(slot),sp,current)
        event=dict(function=slot,target=target if slot==0x5469c4 else slot,importedTarget=target,
                   stackPointer=sp,returnPC=m.words(sp,1)[0],arguments=args,result=None,completed=False,
                   inputCPU=cpu(),stackBefore=m.read(STACK_BASE,STACK_SIZE).hex(),before=snapshot())
        if fail_at==len(events)+1:
            event.update(snapshot(),after=snapshot(),outputCPU=cpu(),stackAfter=m.read(STACK_BASE,STACK_SIZE).hex());events.append(event);raise Stop(hex(slot))
        if slot==0x546a90:
            if fail=='tls':result=0xffffffff
            else:result=next_tls;next_tls+=1;indices.append(result)
        elif slot==0x546aa4:
            assert args[0]-28 in managers and args[0] not in sections
            sections[args[0]]=dict(section=args[0],owner=0,depth=0,initialized=1,entered=0,left=0)
        elif slot==0x546aac:
            state=sections[args[0]];state['depth']+=1;state['entered']+=1;state['owner']=1
        elif slot==0x546a9c:
            state=sections[args[0]];assert state['depth']>0
            state['depth']-=1;state['left']+=1;state['owner']=1 if state['depth'] else 0
        elif slot==0x546b1c:
            assert args[0]==0x2002
            if fail!='allocate':
                result=next_handle;next_handle+=4
                blocks[result]=dict(handle=result,data=allocate(args[1]),size=args[1],flags=args[0],locks=0)
        elif slot==0x546a8c:
            result=next((h for h,b in blocks.items() if b['data']==args[0]),0)
            assert result or args[0]==0
        elif slot==0x5469c8:
            b=blocks[args[0]];assert b['locks']>0;b['locks']-=1;result=int(b['locks']>0)
        elif slot==0x546a88:
            b=blocks[args[0]];assert b['locks']==0 and args[2]==0x2002
            if fail!='reallocate':
                data=allocate(args[1]);m.write(data,m.read(b['data'],min(args[1],b['size'])))
                b.update(data=data,size=args[1],flags=args[2]);result=b['handle']
        elif slot==0x5469c4:
            if args[0]:b=blocks[args[0]];b['locks']+=1;result=b['data']
        else:raise AssertionError(hex(slot))
        if slot in (0x546aa4,0x546aac,0x546a9c):result=0xa1b2c3d4
        event.update(result=result,completed=True,**snapshot());events.append(event)
        m.return_from_external(result,4*count)
        event.update(after=snapshot(),outputCPU=cpu(),stackAfter=m.read(STACK_BASE,STACK_SIZE).hex())
    m.on_external=external
    def observe(machine,address):
        sp=m.register(UC_X86_REG_ESP)
        entry=dict(function=address,frame=sp,returnPC=m.words(sp,1)[0],inputCPU=cpu(),stack=m.read(STACK_BASE,STACK_SIZE).hex(),state=snapshot(),arguments=list(m.words(sp+4,3)) if address==0x4a4a20 else [])
        entries.append(entry)
        assert sp==current['frame']-(40 if address==0x4a4a20 else 8 if current['function']==INIT else 28)
        if address==0x4f50fd:raise Stop('missing-exception')
    m.observe(0x4a4a20,observe);m.observe(0x4f50fd,observe)
    for index,operation in enumerate(operations):
        function,manager_index,patch=operation
        manager=managers[manager_index]
        writes={}
        # Explicit source-state inputs for occupied scan and highwater branches.
        if patch:
            data=m.words(manager+16,1)[0]
            for offset,value in patch.get('manager',{}).items():writes[manager+int(offset)]=value
            for offset,value in patch.get('table',{}).items():writes[data+int(offset)]=value
            for address,value in writes.items():put(address,value)
        current=dict(function=function,receiver=manager,frame=STACK_TOP-0x100-index*0x40,writes={str(k):v for k,v in writes.items()})
        seed=0x502fb6 + index * 0x10001
        rng=random.Random(seed)
        m.write(STACK_BASE,rng.randbytes(STACK_SIZE))
        return_pc=0x503381 if function==INIT else 0x503392
        values=[rng.getrandbits(32) for _ in CONTEXT_FIELDS]
        values[2]=manager; values[7]=current['frame']; values[8]=function
        values[9]=rng.getrandbits(32)&0x8d5|2; values[10]=0xffffffff
        context=NativeSourceContext(72,1,0x7ff,0x7ff,*values,0x462 if function==INIT else 0x400,0,0)
        put(current['frame'],return_pc)
        current.update(seed=seed,returnPC=return_pc,inputContext=context_dict(context),
                       stackBefore=m.read(STACK_BASE,STACK_SIZE).hex(),before=snapshot())
        try:
            result=m.call_source(function,context,return_pc,convention='thiscall',ecx=manager)
            assert result.completed and result.stack_pointer==current['frame']+4
            current.update(completed=True,eax=result.eax,halt=None)
        except Stop as stop:current.update(completed=False,eax=None,halt=str(stop))
        current.update(snapshot(),after=snapshot(),outputContext=context_dict(context) if current['completed'] else None,outputCPU=cpu(),stackAfter=m.read(STACK_BASE,STACK_SIZE).hex(),eventCount=len(events),entryCount=len(entries));steps.append(current)
        if not current['completed']:break
    return dict(name=name,sha256=p.sha256,initialBytes=initial,imports={str(k):v for k,v in imports.items()},
                lockImports={str(k):v for k,v in lock_imports.items()},managerCount=manager_count,
                managers=managers,fail=fail,failAt=fail_at,steps=steps,events=events,entries=entries)

if __name__=='__main__':
    output=Path(sys.argv[1]).resolve();assert Path('work').resolve() in output.parents
    init=(INIT,0,None);slot=(SLOT,0,None)
    profiles=[reference('cold-65-slots-moving-growth',[init]+[slot]*65),
      reference('two-independent-managers',[init,(INIT,1,None),slot,(SLOT,1,None),slot,(SLOT,1,None)],manager_count=2),
      reference('tls-exhaustion',[init],fail='tls'),
      reference('initialize-physical-stop',[init],fail_at=2),
      reference('allocation-failure-prefix',[init,slot],fail='allocate'),
      reference('moving-realloc-failure-prefix',[init]+[slot]*32,fail='reallocate'),
      reference('occupied-next-scan-and-highwater',[init,slot,(SLOT,0,dict(manager={'8':2,'12':9},table={'16':0x8201,'8':0x8200,'12':0x12345678})),slot]),
      reference('out-of-range-scan',[init,slot,(SLOT,0,dict(manager={'8':100},table={'16':0x8201,'24':0x8200,'28':0xaabbccdd}))]),
      reference('full-occupied-growth',[init,slot,(SLOT,0,dict(manager={'8':2},table={str(i*8):0x8201 for i in range(32)}))])]
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(profiles,indent=2)+'\n')
    print(f'PASS {len(profiles)} fresh original source MFC TLS manager profiles; unchanged original manager/memset instructions and bounded genuine missing exception entry')
