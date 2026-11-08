"""Finite GroundBlower transport evidence from the hash-verified original."""
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
ACTOR, STATE, WORLD, REGISTRY, TABLE, STRING, HIT, ATTACK, IMAGES, ANIMATIONS, METHODS, NODE, COLLECTION, SEQUENCE, RECORD, FRAMES, PLAYER, SPRITE = [BASE+i*0x1000 for i in range(1,19)]
OBSERVE = (0x448d10,0x4490e0,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4dc870,0x4c9e30,0x448e30,0x4492c0,0x449270,0x4dba00,0x4c7970,0x4c8220,0x4c82a0,0x4041b0,0x484d90,0x456030,0x4f6428,0x406290,0x41e810,0x41c4e0,0x4c79e0,0x4208b0,0x4170b0,0x420dd0)
BOUNDARIES = (0x448d45,0x448d4a,0x448d60,0x448d65,
              0x4c7f4a,0x4c7f4f,0x4c800a,0x4c800f,0x4c7f40,0x4c7f43,0x4c8000,0x4c8003,
              0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd)

class Reference:
    def __init__(self,label,exhausted=0,occupied=0,interleave=False,command=7,recreate=False,tick=False,frame=4,elapsed=100,duration=2,rect="valid",intersects=True,force=450,player_mode="inactive"):
        self.label,self.exhausted,self.occupied,self.interleave,self.command=label,exhausted,occupied,interleave,command
        self.recreate,self.tick,self.frame,self.elapsed=recreate,tick,frame,elapsed
        self.rect,self.intersects,self.force=rect,intersects,force
        self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
        self.cursor=ALLOC;self.allocations=[];self.events=[];self.calls=[];self.requests=[];self.boundaries=[];self.foreign=[];self.ordinary=[];self.frontier=None;self.attempts=0
        self.blocks=[(a,0x400) for a in range(ACTOR,FRAMES,0x1000)]
        self.blocks += [(FRAMES,0x100)]+[(FRAMES+0x100+i*8,8) for i in range(11)]
        self.blocks += [(0x510020,4),(0x50dfac,0x24),(0x513740,0x28),(0x537668,0x60),(0x5377e8,0x30),
                        (0x522d48,0x20),(0x527abc,0x40),(0x523604,0x20),(0x537210,4),(0x5430c4,4),(0x537e88,4),(0x546d58,4),(0x546d4c,4),(0x546ce0,4),(PLAYER,0x400),(SPRITE,0x400)]
        assert [self.get(0x50dfac+i) for i in (0,4,8,12,16,28,32)]==[0x484d90,0x4c9e30,0x448e30,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
        self.w(ACTOR+4,91);self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x6c,STATE)
        self.w(STATE+0xc,WORLD);self.w(STATE+0x10,0x448d10)
        self.w(WORLD+0x10,IMAGES,REGISTRY);self.w(WORLD+0x2c,ANIMATIONS)
        self.w(ACTOR+0x4c,120,240);self.w(STATE+0x2c,10,110,20,120)
        self.w(HIT,11,12,13,14,0x4dc830);self.w(ATTACK,21,22,23,24,0x4dc850)
        self.w(STATE+0xb8,50);self.w(0x537210,1234);self.w(0x5430c4,1)
        self.w(ACTOR+0x18c,ACTOR);self.w(ACTOR+0x16c,frame)
        self.w(ACTOR+0x174,SPRITE);self.w(SPRITE+0x18,10,20,0,0)
        self.w(ACTOR+0x118,*((0,0,0,0) if rect=='zero' else (10,10,5,5) if rect=='empty' else (-10,-20,10,20)))
        self.w(0x537e88,PLAYER);self.w(PLAYER+0x4c,120 if intersects else 1000,240)
        self.w(PLAYER+0x118,-10,-20,10,20);self.w(STATE+0x38,force)
        self.w(PLAYER+0x6c,PLAYER+0x200);self.w(PLAYER+0xd0,0 if player_mode=="inactive" else 2)
        self.w(PLAYER+0x21c,0x1c if player_mode=="excluded" else 7)
        if player_mode=='active':
            self.blocks += [(PLAYER+0x400,0x200),(PLAYER+0x800,0x40),(0x537204,4),(0x534db8,0x100),(0x50ba88,0x58),(0x513e20,8),(0x5246a8,0x20)]
            self.w(PLAYER+0xc,WORLD);self.w(WORLD+0x28,REGISTRY)
            self.w(PLAYER+0x214,PLAYER+0x400);self.w(0x537204,PLAYER+0x800)
            # The physical fixture supplies an orthonormal vector basis.
            self.m.write(0x534db8,bytes(0x100))
            self.m.write(0x534dc8,struct.pack('<ddd',0.0,1.0,0.0))
            self.m.write(0x534df8,struct.pack('<ddd',120.0,240.0,0.0))
        self.w(COLLECTION+0x14,FRAMES);self.w(COLLECTION+0x64,frame,max(frame,9))
        for i in range(11):self.w(FRAMES+i*4,FRAMES+0x100+i*8)
        self.w(SEQUENCE+0xc,SEQUENCE+0x100,1);self.w(SEQUENCE+0x100,RECORD)
        self.w(RECORD+0xc,9);self.w(RECORD+0x18,duration,42)
        self.w(NODE,NODE,NODE,0,0x523604,7)
        self.w(0x5377e8,0,0,0,63,METHODS,0,4,0,0,0,0,0)
        self.w(0x537668,*([0]*12));self.w(0x537680,NODE);self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0)
        text=b'ES_IDLE\0';self.w(STRING,1,len(text)-1,32);self.m.write(STRING+12,text)
        for i in range(64):self.w(TABLE+i*4,STRING+12);self.w(METHODS+i*4,0x4492c0 if tick else 0x449270)
        for address in OBSERVE:
            self.m.observe(address,lambda m,a:self.calls.append([a,0 if a in (0x448d10,0x4f63ec,0x4dc870,0x4f6428,0x41e810,0x41c4e0,0x4170b0) else m.register(UC_X86_REG_ECX)]))
        for address in BOUNDARIES:self.m.observe(address,lambda m,a:self.boundaries.append(a))
        for address in (0x4a48e0,0x4f6286,0x5022b5,0x4f6428):self.m.intercept(address)
        self.m.observe(0x4f6974,self.buffer)
        self.imports={self.get(slot):name for slot,name in [(0x546d58,'copy'),(0x546d4c,'empty'),(0x546ce0,'intersect')]}
        self.forces=[]
        self.physics=player_mode=='active'
        self.m.observe(0x41e810,lambda m,a:self.forces.append(m.words(m.register(UC_X86_REG_ESP)+4,2)))
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
        if a in self.imports:
            name=self.imports[a]
            if name=='copy':
                self.m.write(arg(0),self.m.read(arg(1),16));value=1;arity=2
            elif name=='empty':
                l,t,r,b=self.m.words(arg(0),4);signed=lambda x:x if x<0x80000000 else x-0x100000000
                value=int(signed(l)>=signed(r) or signed(t)>=signed(b));arity=1
            else:
                signed=lambda x:x if x<0x80000000 else x-0x100000000
                a1=list(map(signed,self.m.words(arg(1),4)));a2=list(map(signed,self.m.words(arg(2),4)))
                rect=[max(a1[0],a2[0]),max(a1[1],a2[1]),min(a1[2],a2[2]),min(a1[3],a2[3])]
                value=int(rect[0]<rect[2] and rect[1]<rect[3]);self.w(arg(0),*(rect if value else [0]*4));arity=3
            self.events.append(['rectangle',name,value]);m.return_from_external(value,arity*4)
        elif a==0x4a48e0:
            count=arg(0);assert count in (0x50,0x174)
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
            value=({'LogicHit':HIT,'LogicAttack':ATTACK,'CLAW_JUMP':RECORD}.get(key,0) if receiver==REGISTRY+16 else SEQUENCE if receiver==ANIMATIONS+16 and key=='LEVEL_GROUNDBLOWER' else COLLECTION if receiver==IMAGES+16 and key=='LEVEL_GROUNDBLOWER' else 0)
            self.w(arg(1),value);self.events.append(['registry',receiver,key,value]);m.return_from_external(int(value!=0),8)
        elif a==0x4f6428:
            token=arg(0);assert (token,0x50) in self.allocations and self.get(token)==0x50b014
            self.events.append(['delete',token,self.get(token)]);self.allocations.remove((token,0x50));m.return_from_external(0,0)
        elif a==0x5022b5:self.frontier=a;m.uc.emu_stop()
        else:raise AssertionError(hex(a))
    def run(self):
        results=[];snapshots=[];steps=[]
        commands=[0] if self.exhausted or self.occupied else [0,1000,29,30,self.command]+([-1,0,self.command] if self.recreate else [])
        for command in commands:
            if command==-1:
                helper=self.get(STATE+0x18);done=self.m.call(self.get(self.get(helper)), ecx=helper,arguments=[1]);self.w(STATE+0x18,0)
            else:
                self.w(STATE+0x1c,command);self.w(0x537210,1234+(self.elapsed if command==self.command else 0));done=self.m.call(0x448d10,arguments=[ACTOR])
            steps.append(command)
            if not done.completed:
                if self.frontier is None:raise RuntimeError((self.label,command,done,self.calls[-8:],self.events[-5:]))
                snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(PLAYER,0x400)]+([(PLAYER+0x400,0x200),(PLAYER+0x800,0x40),(0x534db8,0x100)] if self.physics else [])+self.allocations+self.ordinary+[(0x537668,0x60),(0x5377e8,0x30)]))
                break
            results.append(self.m.register(UC_X86_REG_EAX));snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(PLAYER,0x400)]+([(PLAYER+0x400,0x200),(PLAYER+0x800,0x40),(0x534db8,0x100)] if self.physics else [])+self.allocations+self.ordinary+[(0x537668,0x60),(0x5377e8,0x30)]))
        return dict(label=self.label,exhausted=self.exhausted,occupied=self.occupied,interleave=self.interleave,tick=self.tick,frame=self.frame,elapsed=self.elapsed,initial=self.initial,forces=self.forces,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,foreign=self.snapshot(self.foreign),allocations=self.allocations)

def prepare(out):
    profiles=[Reference('default-7').run(),Reference('default-31',command=31).run(),Reference('shared-heap',interleave=True).run(),Reference('destroy-recreate',recreate=True).run()]
    profiles += [Reference('tick-frame-'+str(i),tick=True,frame=i).run() for i in (1,2,9)]
    profiles += [Reference('rectangle-'+r,rect=r).run() for r in ('zero','empty')]
    profiles += [Reference('tick-force-'+str(f),tick=True,frame=1,force=f).run() for f in (0,-1,700)]
    profiles += [Reference('tick-no-intersection',tick=True,frame=1,intersects=False).run()]
    profiles += [Reference('tick-player-'+mode,tick=True,frame=1,player_mode=mode).run() for mode in ('boardless','excluded')]
    profiles += [Reference('tick-active-force-'+str(force),tick=True,frame=1,player_mode='active',force=force).run() for force in (0,450,700)]
    exhaustions=[Reference('exhaustion-'+str(i),exhausted=i,interleave=True).run() for i in (1,2,3)]
    exhaustions += [Reference('occupied-'+str(i),occupied=i,interleave=True).run() for i in (1,2,3)]
    out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(dict(version=1,executable_sha256=claw().sha256,profiles=profiles,exhaustions=exhaustions),indent=2)+'\n')
    print(json.dumps(dict(status='pass',profiles=len(profiles),exhaustions=len(exhaustions))))

def compare(out):
    ref,actual=[json.loads((out/name).read_text()) for name in ('reference.json','native.json')];failures=[]
    for group in ('profiles','exhaustions'):
        if len(ref[group])!=len(actual[group]):failures.append(group+' count')
        for r,n in zip(ref[group],actual[group]):
            for key in ('label','results','snapshots','events','requests','frontier','foreign','forces'):
                if r[key]!=n[key]:failures.append(dict(label=r['label'],field=key))
            if not n['physicalIntegrity']:failures.append(dict(label=r['label'],field='physical allocation integrity'))
            selected=set(OBSERVE)-{0x448d10,0x456030}
            def joined_calls(calls):
                # The admitted constructor and tick method inline ventIdle;
                # dynamic dispatcher calls to that same method remain observed.
                constructing=False;tick=False;result=[]
                for c in calls:
                    if c[0]==0x4490e0:constructing=True
                    if c[0]==0x4492c0:tick=True
                    if c[0]==0x449270 and constructing:continue
                    if c[0]==0x4c96b0:constructing=False
                    if c[0]==0x4041b0:tick=False
                    if c[0] in selected:result.append(c)
                return result
            if joined_calls(r['calls'])!=joined_calls(n['calls']):failures.append(dict(label=r['label'],field='ordered canonical calls'))
            if group=='profiles':
                required=[0x448d45,0x448d4a,0x448d60,0x448d65,0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd]
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
