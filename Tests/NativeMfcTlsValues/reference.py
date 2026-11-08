"""Composed original TLS storage; source routines unchanged, physical APIs only.

Dynamic manager/publication and getter owner are explicit unit inputs. These
profiles do not claim real CWinApp/factory startup or source exception dispatch.
"""
import json, struct, sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_TOP
from Tests.clawparity.program import claw
from Tests.NativeMfcTlsManager.reference import IMPORTS
from unicorn.x86_const import UC_X86_REG_ESP

class Stop(Exception): pass

def reference(name, grow=False, failure=None, cold=False):
    p=claw(); m=Machine(p,0x62000000,0x100000)
    imports={s:m.import_stub[s] for s in IMPORTS}; reverse={v:k for k,v in imports.items()}
    lock_imports={s:m.import_stub[s] for s in (0x546abc,0x546aa4,0x546aac,0x546a9c)}
    initial=m.read(0x5408e0,0x210).hex()
    manager=0x62000000; owner=0x60000000; m.uc.mem_map(owner,0x1000)
    next_data=manager+0x40; next_handle=0x78000000; next_tls=0
    m.write(manager,b'\xcc'*0x34);m.write(owner,b'\0'*4)
    blocks={}; locals_={}; tls={}; sections={};events=[];steps=[]
    def put(t,v):m.write(t,struct.pack('<I',v))
    def allocate(n,zero=False):
        nonlocal next_data
        t=next_data;next_data=(t+n+15)&~15;m.write(t,bytes([0 if zero else 0xcc])*n);return t
    def snapshot():
        return dict(managerBytes=m.read(manager,0x34).hex(),ownerValue=m.words(owner,1)[0],
          locals={str(t):m.read(t,n).hex() for t,n in locals_.items()},
          blocks=[dict(blocks[h]) for h in sorted(blocks)],
          blockBytes={str(b['data']):m.read(b['data'],b['size']).hex() for b in blocks.values()},
          sections=[dict(sections[t]) for t in sorted(sections)])
    def external(machine,target):
        nonlocal next_handle,next_tls
        s=reverse[target];count=IMPORTS[s][1];sp=m.register(UC_X86_REG_ESP);a=list(m.words(sp+4,count));r=0
        if s==0x546a90:r=next_tls;next_tls+=1;tls[r]=0
        elif s==0x546a7c:r=tls[a[0]]
        elif s==0x546a84:tls[a[0]]=a[1];r=1
        elif s==0x546aa4:sections[a[0]]=dict(section=a[0],owner=0,depth=0,initialized=1,entered=0,left=0)
        elif s in (0x546aac,0x546a9c):
            st=sections[a[0]];st['depth']+=1 if s==0x546aac else -1;st['entered' if s==0x546aac else 'left']+=1;st['owner']=1 if st['depth'] else 0
        elif s==0x546b1c:
            r=next_handle;next_handle+=4;blocks[r]=dict(handle=r,data=allocate(a[1]),size=a[1],flags=a[0],locks=0)
        elif s==0x5469c4:
            if a[0]:b=blocks[a[0]];b['locks']+=1;r=b['data']
        elif s==0x546a8c:r=next(h for h,b in blocks.items() if b['data']==a[0])
        elif s==0x5469c8:b=blocks[a[0]];b['locks']-=1;r=int(b['locks']>0)
        elif s==0x546a88:
            b=blocks[a[0]];t=allocate(a[1]);m.write(t,m.read(b['data'],min(a[1],b['size'])));b.update(data=t,size=a[1],flags=a[2]);r=b['handle']
        elif s==0x546aa8:
            if failure!='container' or a[1]!=16:r=allocate(a[1],bool(a[0]&0x40));locals_[r]=a[1]
        elif s==0x546a80:
            if failure!='reallocate':
                r=allocate(a[1],bool(a[2]&0x40));m.write(r,m.read(a[0],min(locals_[a[0]],a[1])));del locals_[a[0]];locals_[r]=a[1]
        else:raise AssertionError(hex(s))
        if s in (0x546aa4,0x546aac,0x546a9c):r=0xa1b2c3d4
        events.append(dict(function=s,target=target if s==0x5469c4 else s,frame=sp,arguments=a,result=r,**snapshot()))
        m.return_from_external(r,4*count)
    m.on_external=external
    def stop(machine,address):raise Stop(address)
    m.observe(0x4f50fd,stop);m.observe(0x502335,stop)
    operations=[(0x502fb6,manager,[])]
    if not cold:
        operations += [(0x502ff8,manager,[]),(0x503167,manager,[1,0x789abcde]),(0x50335e,owner,[0x502335])]
        if grow:operations += [(0x502ff8,manager,[])]*34+[(0x503167,manager,[35,0x10203040]),(0x50335e,owner,[0x502335])]
    else:operations += [(0x50335e,owner,[0x502335])]
    for i,(f,receiver,args) in enumerate(operations):
        writes={}
        if f==0x50335e:
            writes={0x540af0:manager,owner:1 if i<5 else 35}
            for t,v in writes.items():put(t,v)
        frame=STACK_TOP-0x100-i*0x40
        try:
            result=m.call(f,ecx=receiver,arguments=args,stack_pointer=frame)
            assert result.completed
            completed=True;eax=0 if f==0x503167 else result.eax;halt=None
        except Stop as e:completed=False;eax=None;halt=e.args[0]
        steps.append(dict(function=f,receiver=receiver,arguments=args,frame=frame,writes={str(t):v for t,v in writes.items()},completed=completed,eax=eax,halt=halt,eventCount=len(events),**snapshot()))
        if not completed:break
    return dict(name=name,sha256=p.sha256,initialBytes=initial,imports={str(k):v for k,v in imports.items()},lockImports={str(k):v for k,v in lock_imports.items()},manager=manager,owner=owner,failure=failure,events=events,steps=steps)

if __name__=='__main__':
    out=Path(sys.argv[1]).resolve();assert Path('work').resolve() in out.parents
    profiles=[reference('source-produced-container-and-hit'),reference('source-produced-moving-growth',grow=True),reference('checked-container-allocation-failure',failure='container'),reference('source-produced-value-reallocation-failure',grow=True,failure='reallocate'),reference('genuine-cold-factory-stop',cold=True)]
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(profiles,indent=2)+'\n');print(f'PASS {len(profiles)} fresh original TLS value join profiles')
