"""Finite CrabNest transport evidence from the hash-verified original."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESP
BASE, SIZE, ALLOC = 0x10000000, 0x20000, 0x61000000
ACTOR, STATE, WORLD, REGISTRY, TABLE, STRING, HIT, ATTACK, SOUNDS, ANIMATIONS, METHODS, PLAYER, HATCH, SOUND = [BASE+i*0x1000 for i in range(1,15)]
OBSERVE = (0x432570,0x432a60,0x4f63ec,0x4c7fa0,0x4c8060,0x4c8160,0x4c81b0,0x4c96b0,0x4dc870,0x4c9e30,0x432690,0x432c50,0x4dba00,0x4041b0,0x484d90,0x456030,0x4f6428)
BOUNDARIES = (0x4325a5,0x4325aa,0x4325c0,0x4325c5,0x432aa8,0x432aad,0x432ab5,0x432aba,
              0x4c7f4a,0x4c7f4f,0x4c800a,0x4c800f,0x4c7f40,0x4c7f43,0x4c8000,0x4c8003,
              0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x432757,0x432759,0x4dc9fa,0x4dc9fd)

class Reference:
    def __init__(self,label,exhausted=0,occupied=0,interleave=False,command=7,recreate=False):
        self.label,self.exhausted,self.occupied,self.interleave,self.command=label,exhausted,occupied,interleave,command
        self.recreate=recreate
        self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000)
        self.cursor=ALLOC;self.allocations=[];self.events=[];self.calls=[];self.requests=[];self.boundaries=[];self.foreign=[];self.ordinary=[];self.frontier=None;self.attempts=0
        self.blocks=[(a,0x400) for a in range(ACTOR,SOUND+1,0x1000)]
        self.blocks += [(0x510020,4),(0x50c754,0x24),(0x513740,0x28),(0x537668,0x60),(0x5372d8,0x30),(0x537e88,4),
                        (0x522d48,0x20),(0x52665c,0x50),(0x523604,0x20)]
        assert [self.get(0x50c754+i) for i in (0,4,8,12,16,28,32)]==[0x484d90,0x4c9e30,0x432690,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
        self.w(ACTOR+4,91);self.w(ACTOR+0xc,WORLD);self.w(ACTOR+0x6c,STATE)
        self.w(STATE+0xc,WORLD);self.w(STATE+0x10,0x432570)
        self.w(WORLD+0x14,REGISTRY);self.w(WORLD+0x28,SOUNDS,ANIMATIONS)
        self.w(ACTOR+0x4c,120,240);self.w(STATE+0x2c,10,110,20,120)
        self.w(HIT,11,12,13,14,0x4dc830);self.w(ATTACK,21,22,23,24,0x4dc850)
        self.w(0x537e88,PLAYER);self.w(PLAYER+0xcc,0)
        self.w(0x5372d8,0,0,0,63,METHODS,0,4,0,0,0,0,0)
        self.w(0x537668,*([0]*12));self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0)
        text=b'ES_IDLE\0';self.w(STRING,1,len(text)-1,32);self.m.write(STRING+12,text)
        for i in range(64):self.w(TABLE+i*4,STRING+12);self.w(METHODS+i*4,0x432c50)
        for address in OBSERVE:
            self.m.observe(address,lambda m,a:self.calls.append([a,0 if a in (0x432570,0x4f63ec,0x4dc870,0x4f6428) else m.register(UC_X86_REG_ECX)]))
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
            receiver=m.register(UC_X86_REG_ECX);assert receiver in (REGISTRY+16,SOUNDS+16,ANIMATIONS+16)
            key=m.read(arg(0),64).split(b'\0')[0].decode('ascii')
            value=({'LogicHit':HIT,'LogicAttack':ATTACK}.get(key,0) if receiver==REGISTRY+16 else HATCH if receiver==ANIMATIONS+16 and key=='LEVEL_HATCHNEST' else SOUND if receiver==SOUNDS+16 and key=='GAME_BOINK' else 0)
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
                self.w(STATE+0x1c,command);done=self.m.call(0x432570,arguments=[ACTOR])
            steps.append(command)
            if not done.completed:
                if self.frontier is None:raise RuntimeError((self.label,command,done,self.calls[-8:],self.events[-5:]))
                snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x5372d8,0x30)]))
                break
            results.append(self.m.register(UC_X86_REG_EAX));snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174)]+self.allocations+self.ordinary+[(0x537668,0x60),(0x5372d8,0x30)]))
        return dict(label=self.label,exhausted=self.exhausted,occupied=self.occupied,interleave=self.interleave,initial=self.initial,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,foreign=self.snapshot(self.foreign),allocations=self.allocations)

def prepare(out):
    profiles=[Reference('default-7').run(),Reference('default-31',command=31).run(),Reference('shared-heap',interleave=True).run(),Reference('destroy-recreate',recreate=True).run()]
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
            selected=set(OBSERVE)-{0x432570,0x456030}
            if [c for c in r['calls'] if c[0] in selected]!=[c for c in n['calls'] if c[0] in selected]:failures.append(dict(label=r['label'],field='ordered canonical calls'))
            if group=='profiles':
                expected=[0x4325a5,0x4325aa,0x4325c0,0x432aa8,0x4c7f4a,0x4c7f4f,0x432aad,
                          0x432ab5,0x4c800a,0x4c800f,0x432aba,0x4325c5,
                          0x4dc93a,0x4dc93d,0x4dc943,0x432757,0x432759,0x4dc946,0x4dc9fa,0x4dc9fd]
                if r['label']=='destroy-recreate':
                    expected += [0x4325a5,0x4325aa,0x4325c0,0x432aa8,0x4c7f40,0x4c7f43,0x432aad,
                                 0x432ab5,0x4c8000,0x4c8003,0x432aba,0x4325c5,
                                 0x4dc93a,0x4dc93d,0x4dc943,0x432757,0x432759,0x4dc946,0x4dc9fa,0x4dc9fd]
                if r['boundaries']!=expected:failures.append(dict(label=r['label'],field='original CALL continuations',actual=r['boundaries']))
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
