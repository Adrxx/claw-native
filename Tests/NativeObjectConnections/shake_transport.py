"""Finite Shake transport evidence from the hash-verified original."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESP
BASE, SIZE, ALLOC = 0x10000000, 0x10000, 0x61000000
ACTOR, STATE, WORLD, REGISTRY, TABLE, STRING, HIT, ATTACK, METHODS, NODE, SOUND = [BASE+i*0x1000 for i in range(1,12)]
OBSERVE = (0x4887b0,0x488870,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4dc870,0x4c9e30,0x4889e0,0x488c90,0x488cd0,0x488cf0,0x4dba00,0x486e70,0x4a3050,0x4041b0,0x484d90,0x456030,0x4f6428)
BOUNDARIES = (0x4887e5,0x4887ea,0x488800,0x488805,0x4888b6,0x4888bb,0x4888c3,0x4888c8,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd)
class Reference:
    def __init__(self,label,exhausted=0,occupied=0,interleave=False,command=7,recreate=False,handler=0x488c90,elapsed=100,random=0):
        self.label,self.exhausted,self.occupied,self.interleave,self.command=label,exhausted,occupied,interleave,command
        self.recreate,self.handler,self.elapsed,self.random=recreate,handler,elapsed,random
        self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
        self.cursor=ALLOC;self.allocations=[];self.events=[];self.calls=[];self.requests=[];self.boundaries=[];self.foreign=[];self.ordinary=[];self.frontier=None;self.attempts=0
        self.blocks=[(a,0x400) for a in range(ACTOR,SOUND+1,0x1000)]
        self.blocks += [(0x510020,4),(0x50f63c,0x24),(0x513740,0x28),(0x537668,0x60),(0x53c2a0,0x30),(0x522d48,0x20),(0x529a48,0x20),(0x523524,0x68),(0x537210,4),(0x532c0c,8),(0x541328,4),(0x53c260,4)]
        assert [self.get(0x50f63c+i) for i in (0,4,8,12,16,28,32)]==[0x484d90,0x4c9e30,0x4889e0,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
        self.w(ACTOR+4,91);self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x6c,STATE)
        self.w(STATE+0xc,WORLD);self.w(STATE+0x10,0x4887b0)
        self.w(WORLD+0x14,REGISTRY);self.w(WORLD+0x28,REGISTRY,REGISTRY)
        self.w(ACTOR+0x4c,120,240);self.w(ACTOR+0x138,100,200,180,300)
        self.w(0x541328,100);self.w(0x53c260,0);self.w(0x537210,1234);self.w(0x532c0c,0,91)
        self.w(HIT,11,12,13,14,0x4dc830);self.w(ATTACK,21,22,23,24,0x4dc850)
        self.w(0x537668,*([0]*12));self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0)
        self.w(0x53c2a0,0,0,0,63,METHODS,0,4,0,0,0,0,0)
        self.w(NODE,NODE,NODE,0,0x529a48,7);self.w(0x537680,NODE)
        text=b'LS_WAIT\0';self.w(STRING,1,len(text)-1,32);self.m.write(STRING+12,text)
        for i in range(64):self.w(TABLE+i*4,STRING+12);self.w(METHODS+i*4,handler)
        for address in OBSERVE:
            self.m.observe(address,lambda m,a:self.calls.append([a,0 if a in (0x4887b0,0x4f63ec,0x4dc870,0x4a3050,0x486e70,0x4f6428) else m.register(UC_X86_REG_ECX)]))
        for address in BOUNDARIES:self.m.observe(address,lambda m,a:self.boundaries.append(a))
        for address in (0x4a48e0,0x4f6286,0x5022b5,0x4f6428,0x4a3050):self.m.intercept(address)
        self.m.observe(0x4f6974,self.buffer)
        self.m.on_external=self.external
        self.initial=self.snapshot(self.blocks)
    def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def get(self,a):return self.m.words(a,1)[0]
    def snapshot(self,blocks):return [dict(address=a,data=self.m.read(a,n).hex()) for a,n in blocks]
    def buffer(self,m,a):
        receiver=m.register(UC_X86_REG_ECX);assert self.get(m.register(UC_X86_REG_ESP)+4)==0
        assert TABLE<=receiver<TABLE+256
        self.events.append(['buffer',receiver,self.get(receiver)])
    def external(self,m,a):
        sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+i*4)
        if a==0x4a48e0:
            count=arg(0);assert count in (0x54,0x174)
            self.attempts+=1;self.requests.append([a,self.get(sp),self.get(sp+20),count,m.register(UC_X86_REG_EBX)])
            if self.interleave and self.attempts==2:
                for size in (0x1b4,0x174,12):
                    token=self.cursor;self.cursor+=512 if size==0x1b4 else (size+15)&~15
                    self.ordinary.append((token,size));m.write(token,bytes([0x5a])*size);self.events.append(['ordinary',token,size])
            if self.occupied==self.attempts:
                self.foreign.append((self.cursor,count));m.write(self.cursor,bytes([0x6d])*count)
            value=0 if self.attempts in (self.exhausted,self.occupied) else self.cursor
            if value:
                self.cursor+=(count+15)&~15;self.allocations.append((value,count));m.write(value,bytes([204])*count)
            self.events.append(['malloc',value,count]);m.return_from_external(value,0)
        elif a==0x4a3050:
            self.events.append(['random',self.random]);m.return_from_external(self.random,0)
        elif a==0x4f6286:
            receiver=m.register(UC_X86_REG_ECX);assert receiver==REGISTRY+16
            key=m.read(arg(0),64).split(b'\0')[0].decode('ascii');value={'LogicHit':HIT,'LogicAttack':ATTACK}.get(key,SOUND if key.startswith('LEVEL_EARTHQUAKE') else 0)
            self.w(arg(1),value);self.events.append(['registry',receiver,key,value]);m.return_from_external(int(value!=0),8)
        elif a==0x4f6428:
            token=arg(0);assert (token,0x54) in self.allocations and self.get(token)==0x50b014
            self.events.append(['delete',token,self.get(token)]);self.allocations.remove((token,0x54));m.return_from_external(0,0)
        elif a==0x5022b5:self.frontier=a;m.uc.emu_stop()
        else:raise AssertionError(hex(a))
    def run(self):
        results=[];snapshots=[];steps=[]
        commands=[0] if self.exhausted or self.occupied else [0,1000,29,30,self.command]+([-1,0,self.command] if self.recreate else [])
        for command in commands:
            if command==-1:
                helper=self.get(STATE+0x18);done=self.m.call(self.get(self.get(helper)), ecx=helper,arguments=[1]);self.w(STATE+0x18,0)
            else:
                if command==self.command and self.handler==0x488cd0:self.w(self.get(STATE+0x18)+0x4c,1234,100);self.w(ACTOR+8,self.get(ACTOR+8)|1)
                self.w(STATE+0x1c,command);self.w(0x537210,1234+self.elapsed);done=self.m.call(0x4887b0,arguments=[ACTOR])
            steps.append(command)
            if not done.completed:
                if self.frontier is None:raise RuntimeError((self.label,command,done,self.calls[-8:],self.events[-5:]))
                snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x53c2a0,0x30),(0x537210,4),(0x541328,4),(0x53c260,4)]))
                break
            results.append(self.m.register(UC_X86_REG_EAX));snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x53c2a0,0x30),(0x537210,4),(0x541328,4),(0x53c260,4)]))
        return dict(label=self.label,exhausted=self.exhausted,occupied=self.occupied,interleave=self.interleave,initial=self.initial,handler=self.handler,elapsed=self.elapsed,random=self.random,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,foreign=self.snapshot(self.foreign),allocations=self.allocations)
def prepare(out):
    profiles=[Reference('wait-entry').run(),Reference('wait-expired',handler=0x488cd0).run(),Reference('wait-before-expiry',handler=0x488cd0,elapsed=99).run(),Reference('shared-heap',interleave=True).run(),Reference('destroy-recreate',recreate=True).run()]
    profiles += [Reference('activate-random-'+str(i),handler=0x488cf0,random=i).run() for i in range(6)]
    exhaustions=[Reference('exhaustion-'+str(i),exhausted=i,interleave=True).run() for i in (1,2,3)]
    exhaustions += [Reference('occupied-'+str(i),occupied=i,interleave=True).run() for i in (1,2,3)]
    out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(version=1,executable_sha256=claw().sha256,profiles=profiles,exhaustions=exhaustions),indent=2)+'\n')
    print(json.dumps(dict(status='pass',profiles=len(profiles),exhaustions=len(exhaustions))))
def compare(out):
    ref,actual=[json.loads((out/name).read_text()) for name in ('reference.json','native.json')];failures=[]
    for group in ('profiles','exhaustions'):
        if len(ref[group])!=len(actual[group]):failures.append(group+' count')
        for r,n in zip(ref[group],actual[group]):
            for key in ('label','results','snapshots','events','requests','frontier','foreign'):
                if r[key]!=n[key]:failures.append(dict(label=r['label'],field=key))
            if not n['physicalIntegrity']:failures.append(dict(label=r['label'],field='physical allocation integrity'))
            selected=set(OBSERVE)-{0x4887b0,0x456030}
            def joined(calls):
                active=False;result=[]
                for c in calls:
                    if c[0]==0x488cf0:active=True
                    if c[0]==0x488c90 and active:continue
                    if c[0]==0x4041b0:active=False
                    if c[0] in selected:result.append(c)
                return result
            if joined(r['calls'])!=joined(n['calls']):failures.append(dict(label=r['label'],field='ordered canonical calls'))
            if group=='profiles':
                required=[0x4887e5,0x4887ea,0x488800,0x488805,0x4888b6,0x4888bb,0x4888c3,0x4888c8,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd]
                if any(r['boundaries'].count(a)!=(2 if r['label']=='destroy-recreate' else 1) for a in required):failures.append(dict(label=r['label'],field='original CALL continuations'))
                if n['completed']!=[True]*len(r['steps']):failures.append(dict(label=r['label'],field='completion'))
            elif n['completed']!=[False]:failures.append(dict(label=r['label'],field='exhaustion completion'))
    for control in actual['controls']:
        if not control['passed']:failures.append(dict(control=control['name']))
    result=dict(exercised_edges=[hex(a) for a in OBSERVE],status='fail' if failures else 'pass',profiles=len(ref['profiles']),exhaustions=len(ref['exhaustions']),controls=len(actual['controls']),failures=failures)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
def main():
    out=Path(sys.argv[2]).resolve()
    if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence belongs under ignored work/')
    if sys.argv[1]=='prepare':prepare(out)
    elif sys.argv[1]=='compare':return compare(out)
    else:raise ValueError(sys.argv[1])
if __name__=='__main__':raise SystemExit(main())
