"""Finite GooVent transport evidence from the hash-verified original."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESP
BASE, SIZE, ALLOC = 0x10000000, 0x30000, 0x61000000
ACTOR, STATE, WORLD, REGISTRY, TABLE, STRING, HIT, ATTACK, IMAGES, ANIMATIONS, METHODS, NODE, COLLECTION, SEQUENCE, RECORD, FRAMES = [BASE+i*0x1000 for i in range(1,17)]
OBSERVE = (0x448620,0x4486e0,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4dc870,0x4c9e30,0x448850,0x448b50,0x448b00,0x4dba00,0x4c7970,0x4c8220,0x4c82a0,0x4041b0,0x484d90,0x456030,0x4f6428)
BOUNDARIES = (0x448655,0x44865a,0x448670,0x448675,
              0x4c7f4a,0x4c7f4f,0x4c800a,0x4c800f,0x4c7f40,0x4c7f43,0x4c8000,0x4c8003,
              0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd)

class Reference:
    def __init__(self,label,exhausted=0,occupied=0,interleave=False,command=7,recreate=False,tick=False,frame=4,elapsed=100,duration=2):
        self.label,self.exhausted,self.occupied,self.interleave,self.command=label,exhausted,occupied,interleave,command
        self.recreate,self.tick,self.frame,self.elapsed=recreate,tick,frame,elapsed
        self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
        self.cursor=ALLOC;self.allocations=[];self.events=[];self.calls=[];self.requests=[];self.boundaries=[];self.foreign=[];self.ordinary=[];self.frontier=None;self.attempts=0
        self.blocks=[(a,0x400) for a in range(ACTOR,FRAMES,0x1000)]
        self.blocks += [(FRAMES,0x100)]+[(FRAMES+0x100+i*8,8) for i in range(11)]
        self.blocks += [(0x510020,4),(0x50df84,0x24),(0x513740,0x28),(0x537668,0x60),(0x5377b8,0x30),
                        (0x522d48,0x20),(0x527a78,0x40),(0x523148,0x20),(0x537210,4),(0x5430c4,4)]
        assert [self.get(0x50df84+i) for i in (0,4,8,12,16,28,32)]==[0x484d90,0x4c9e30,0x448850,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
        self.w(ACTOR+4,91);self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x6c,STATE)
        self.w(STATE+0xc,WORLD);self.w(STATE+0x10,0x448620)
        self.w(WORLD+0x10,IMAGES,REGISTRY);self.w(WORLD+0x2c,ANIMATIONS)
        self.w(ACTOR+0x4c,120,240);self.w(STATE+0x2c,10,110,20,120)
        self.w(HIT,11,12,13,14,0x4dc830);self.w(ATTACK,21,22,23,24,0x4dc850)
        self.w(STATE+0xb8,50);self.w(0x537210,1234);self.w(0x5430c4,1)
        self.w(ACTOR+0x18c,ACTOR)
        self.w(COLLECTION+0x14,FRAMES);self.w(COLLECTION+0x64,frame,max(frame,9))
        for i in range(11):self.w(FRAMES+i*4,FRAMES+0x100+i*8)
        self.w(SEQUENCE+0xc,SEQUENCE+0x100,1);self.w(SEQUENCE+0x100,RECORD)
        self.w(RECORD+0xc,9);self.w(RECORD+0x18,duration,42)
        self.w(NODE,NODE,NODE,0,0x523148,7)
        self.w(0x5377b8,0,0,0,63,METHODS,0,4,0,0,0,0,0)
        self.w(0x537668,*([0]*12));self.w(0x537680,NODE);self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0)
        text=b'AS_IDLE\0';self.w(STRING,1,len(text)-1,32);self.m.write(STRING+12,text)
        for i in range(64):self.w(TABLE+i*4,STRING+12);self.w(METHODS+i*4,0x448b50 if tick else 0x448b00)
        for address in OBSERVE:
            self.m.observe(address,lambda m,a:self.calls.append([a,0 if a in (0x448620,0x4f63ec,0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)]))
        for address in BOUNDARIES:self.m.observe(address,lambda m,a:self.boundaries.append(a))
        for address in (0x4a48e0,0x4f6286,0x5022b5,0x4f6428):self.m.intercept(address)
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
            count=arg(0);assert count in (0x58,0x174)
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
        elif a==0x4f6286:
            receiver=m.register(UC_X86_REG_ECX);assert receiver in (REGISTRY+16,IMAGES+16,ANIMATIONS+16)
            key=m.read(arg(0),64).split(b'\0')[0].decode('ascii')
            value=({'LogicHit':HIT,'LogicAttack':ATTACK}.get(key,0) if receiver==REGISTRY+16 else SEQUENCE if receiver==ANIMATIONS+16 and key=='LEVEL_GOOVENT_GOOVENT' else COLLECTION if receiver==IMAGES+16 and key=='LEVEL_GOOVENT' else 0)
            self.w(arg(1),value);self.events.append(['registry',receiver,key,value]);m.return_from_external(int(value!=0),8)
        elif a==0x4f6428:
            token=arg(0);assert (token,0x58) in self.allocations and self.get(token)==0x50b014
            self.events.append(['delete',token,self.get(token)]);self.allocations.remove((token,0x58));m.return_from_external(0,0)
        elif a==0x5022b5:self.frontier=a;m.uc.emu_stop()
        else:raise AssertionError(hex(a))
    def run(self):
        results=[];snapshots=[];steps=[]
        commands=[0] if self.exhausted or self.occupied else [0,1000,29,30,self.command]+([-1,0,self.command] if self.recreate else [])
        for command in commands:
            if command==-1:
                helper=self.get(STATE+0x18);done=self.m.call(self.get(self.get(helper)), ecx=helper,arguments=[1]);self.w(STATE+0x18,0)
            else:
                self.w(STATE+0x1c,command);self.w(0x537210,1234+(self.elapsed if command==self.command else 0));done=self.m.call(0x448620,arguments=[ACTOR])
            steps.append(command)
            if not done.completed:
                if self.frontier is None:raise RuntimeError((self.label,command,done,self.calls[-8:],self.events[-5:]))
                snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x5377b8,0x30)]))
                break
            results.append(self.m.register(UC_X86_REG_EAX));snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x5377b8,0x30)]))
        return dict(label=self.label,exhausted=self.exhausted,occupied=self.occupied,interleave=self.interleave,tick=self.tick,frame=self.frame,elapsed=self.elapsed,initial=self.initial,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,foreign=self.snapshot(self.foreign),allocations=self.allocations)

def prepare(out):
    profiles=[Reference('default-7').run(),Reference('default-31',command=31).run(),Reference('shared-heap',interleave=True).run(),Reference('destroy-recreate',recreate=True).run()]
    profiles += [Reference('tick-frame-'+str(i),tick=True,frame=i).run() for i in range(1,11)]
    profiles += [Reference('tick-before-timer',tick=True,elapsed=49).run(),Reference('tick-animation-completion',tick=True,duration=0).run()]
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
            selected=set(OBSERVE)-{0x448620,0x456030}
            def joined_calls(calls):
                # The admitted constructor and tick method inline ventIdle;
                # dynamic dispatcher calls to that same method remain observed.
                constructing=False;tick=False;result=[]
                for c in calls:
                    if c[0]==0x4486e0:constructing=True
                    if c[0]==0x448b50:tick=True
                    if c[0]==0x448b00 and (constructing or tick):continue
                    if c[0]==0x4c96b0:constructing=False
                    if c[0]==0x4041b0:tick=False
                    if c[0] in selected:result.append(c)
                return result
            if joined_calls(r['calls'])!=joined_calls(n['calls']):failures.append(dict(label=r['label'],field='ordered canonical calls'))
            if group=='profiles':
                required=[0x448655,0x44865a,0x448670,0x448675,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd]
                if any(r['boundaries'].count(a)!=(2 if r['label']=='destroy-recreate' else 1) for a in required):
                    failures.append(dict(label=r['label'],field='original CALL continuations',actual=r['boundaries']))
                if n['completed']!=[True]*len(r['steps']):failures.append(dict(label=r['label'],field='completion'))
            elif n['completed']!=[False]:failures.append(dict(label=r['label'],field='exhaustion completion'))
    for control in actual['controls']:
        if not control['passed']:failures.append(dict(control=control['name']))
    result=dict(status='fail' if failures else 'pass',profiles=len(ref['profiles']),exhaustions=len(ref['exhaustions']),controls=len(actual['controls']),failures=failures)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)

def main():
    out=Path(sys.argv[2]).resolve()
    if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence belongs under ignored work/')
    if sys.argv[1]=='prepare':prepare(out)
    elif sys.argv[1]=='compare':return compare(out)
    else:raise ValueError(sys.argv[1])
if __name__=='__main__':raise SystemExit(main())
