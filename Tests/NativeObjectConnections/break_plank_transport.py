"""Finite BreakPlank owner transport comparisons against hash-verified v1.0."""
import json
from pathlib import Path
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_ESP
BASE, SIZE, ALLOC = 0x10000000, 0x40000, 0x61000000
(ACTOR, STATE, WORLD, REGISTRY, IMAGES, ANIMATIONS, TABLE, STRING, HIT, ATTACK,
 CHILD, MANAGER, NODES, LEVEL, GRID, ROWS, TILES, PLAYER, PLAYERSTATE, CHECKPOINT,
 CONFIG, PARENTMETHODS, CHILDMETHODS) = [BASE + i * 0x1000 for i in range(1, 24)]
OBSERVE = (0x40f7b0, 0x40f870, 0x488e30, 0x488ef0, 0x4f63ec, 0x4c7fa0,
           0x4c8060, 0x4c8160, 0x4c81b0, 0x4c8da0, 0x4c96b0, 0x4dc870,
           0x4c9e30, 0x40fb30, 0x4890f0, 0x4041b0)
BOUNDARIES = (0x40f7e8, 0x40f7ed, 0x40f803, 0x40f808, 0x40f972, 0x40f977,
              0x40fa08, 0x40fa0d, 0x488e65, 0x488e6a, 0x488e80, 0x488e85,
              0x4dc93a, 0x4dc93d, 0x4dc943, 0x4dc946, 0x4dc9fa, 0x4dc9fd)
IMAGESET, IMAGETABLE, IMAGE, IDLE, CRUMBLE, FRAMETABLE, FRAME = [BASE+i*0x1000 for i in range(24,31)]
class Reference:
    def __init__(self, label, children=1, exhausted=0, resources=False, interleave=False, occupied=0):
        self.label, self.children, self.exhausted, self.resources = label, children, exhausted, resources
        self.interleave, self.occupied = interleave, occupied
        self.ordinary, self.foreign = [], []
        self.m = Machine(claw(), BASE, SIZE)
        self.m.uc.mem_map(ALLOC, 0x20000)
        self.cursor, self.allocations = ALLOC, []
        self.events, self.requests, self.calls, self.boundaries = [], [], [], []
        self.frontier = None
        self.blocks = [(a, 0x400) for a in range(ACTOR, FRAME + 1, 0x1000)]
        self.blocks += [(a, n) for a, n in ((0x510020,4),(0x50b6ec,0x24),(0x50f664,0x24),(0x513770,0x100),(0x513740,0x28),(0x537668,0x60),(0x534a10,0x30),(0x53c2c8,0x30),(0x537210,4),(0x5430c4,4),(0x537960,4),(0x537e88,4),(0x522bd4,0x20),(0x522d48,0x20),(0x523148,0x20),(0x52bfdc,0x60))]
        for table, dispatcher in ((0x50b6ec, 0x40fb30), (0x50f664, 0x4890f0)):
            assert [self.get(table+i) for i in (4,8,12,16,28,32)] == [0x4c9e30,dispatcher,0x4041b0,0x4c96b0,0x4c96b0,0x4c96b0]
        self.w(ACTOR + 4, 91); self.w(ACTOR + 0xc, WORLD); self.w(ACTOR + 0x4c, 32, 64)
        self.w(ACTOR + 0x64, 3); self.w(ACTOR + 0x6c, STATE)
        self.w(STATE + 0xc, WORLD); self.w(STATE + 0x10, 0x40f7b0); self.w(STATE + 0xb8, 117); self.w(STATE + 0xc8, children)
        self.w(WORLD + 8, MANAGER); self.w(WORLD + 0x10, IMAGES, REGISTRY); self.w(WORLD + 0x24, LEVEL); self.w(WORLD + 0x2c, ANIMATIONS)
        self.w(MANAGER + 0xc, WORLD); self.w(MANAGER + 0x20, NODES); self.w(MANAGER + 0x28, 16)
        for i in range(16): self.w(NODES+i*12, NODES+(i+1)*12 if i<15 else 0, 0, 0)
        self.w(HIT, 11,12,13,14,0x4dc830); self.w(ATTACK,21,22,23,24,0x4dc850)
        self.w(CHILD,31,32,0,34,0x488e30)
        self.w(LEVEL + 0x5c, GRID); self.w(GRID + 0x20, TILES, ROWS); self.w(GRID + 0x8c, 5, 5)
        for i in range(64): self.w(ROWS+i*4,i*8); self.w(TILES+i*4,0x1100+i)
        self.w(PLAYER + 0x6c, PLAYERSTATE); self.w(PLAYERSTATE + 0x14,CHECKPOINT); self.w(CHECKPOINT + 0x80,9)
        self.w(0x537960,CONFIG); self.w(CONFIG + 0xa8,32,0); self.w(0x537e88,PLAYER)
        self.w(IMAGESET+0x14,IMAGETABLE,1); self.w(IMAGESET+0x64,0,0); self.w(IMAGETABLE,IMAGE)
        self.w(IMAGE,0x513a70,0,0,WORLD,32,16,16,8,0,0)
        for animation in (IDLE,CRUMBLE): self.w(animation+12,FRAMETABLE,1)
        self.w(FRAMETABLE,FRAME); self.w(FRAME,0,0,0,0,0,0,100,0,0,0,0,0)
        self.w(0x537210,113); self.w(0x5430c4,17)
        self.w(0x537668,*([0]*12)); self.w(0x537698,0,0,0,63,TABLE,0,4,0,0,0,0,0)
        for r, t in ((0x534a10,PARENTMETHODS),(0x53c2c8,CHILDMETHODS)):
            self.w(r,0,0,0,63,t,0,4,0,0,0,0,0)
        self.w(STRING,1,0,0,0)
        for i in range(64):
            self.w(TABLE+i*4,STRING+12); self.w(PARENTMETHODS+i*4,0x40fde0); self.w(CHILDMETHODS+i*4,0x489530)
        for a in OBSERVE: self.m.observe(a,lambda m,a:self.calls.append([a,m.register(UC_X86_REG_ECX) if a not in (0x40f7b0,0x488e30,0x4f63ec,0x4dc870) else 0]))
        for a in BOUNDARIES: self.m.observe(a,lambda m,a:self.boundaries.append(a))
        for a in (0x4a48e0,0x4f6286,0x5022b5): self.m.intercept(a)
        self.m.observe(0x4f6974,self.buffer)
        self.m.observe(0x4f51c5,lambda m,a:self.events.append(['append',m.register(UC_X86_REG_ECX),self.get(m.register(UC_X86_REG_ESP)+4)]))
        self.m.on_external = self.external
        self.initial = self.snapshot(self.blocks)
    def w(self,a,*v): self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def get(self,a): return self.m.words(a,1)[0]
    def snapshot(self,blocks): return [dict(address=a,data=self.m.read(a,n).hex()) for a,n in blocks]
    def buffer(self,m,a):
        sp=m.register(UC_X86_REG_ESP); receiver=m.register(UC_X86_REG_ECX)
        assert self.get(sp+4)==0 and TABLE<=receiver<TABLE+256
        self.events.append(['buffer',receiver,self.get(receiver)])
    def external(self,m,a):
        sp=m.register(UC_X86_REG_ESP); arg=lambda i:self.get(sp+4+i*4)
        if a==0x4a48e0:
            count=arg(0)
            assert count in (0xa4,0x6c,0x174,0x1b4),hex(count)
            self.requests.append([a,self.get(sp),self.get(sp+20),count,m.register(UC_X86_REG_EBX)])
            if self.interleave and count==0x6c:
                # The physical scene owner shares one cursor with unrelated
                # actor, logic and list storage. These are not game fixtures.
                for size in (0x1b4,0x174,12):
                    token=self.cursor; self.cursor+=512 if size==0x1b4 else (size+15)&~15
                    self.ordinary.append((token,size));m.write(token,bytes([0x5a])*size)
                    self.events.append(['ordinary',token,size])
            if count==self.occupied:
                self.foreign.append((self.cursor,count));m.write(self.cursor,bytes([0x6d])*count)
            value=0 if len(self.allocations)+1==self.exhausted or count==self.occupied else self.cursor
            if value:
                self.cursor+=(512 if count==0x1b4 else (count+15)&~15)
                self.allocations.append((value,count)); m.write(value,bytes([204])*count)
            self.events.append(['malloc',value,count]); m.return_from_external(value,0)
        elif a==0x4f6286:
            receiver=m.register(UC_X86_REG_ECX)
            assert receiver in (REGISTRY+16,IMAGES+16,ANIMATIONS+16),hex(receiver)
            key=m.read(arg(0),64).split(b'\0')[0].decode('ascii')
            value={'LogicHit':HIT,'LogicAttack':ATTACK,'SinglePlank':CHILD}.get(key,0) if receiver==REGISTRY+16 else 0
            if self.resources:
                value = IMAGESET if receiver==IMAGES+16 and key=='LEVEL_BREAKPLANK' else IDLE if receiver==ANIMATIONS+16 and key=='LEVEL_BREAKPLANK_IDLE' else CRUMBLE if receiver==ANIMATIONS+16 and key=='LEVEL_BREAKPLANK_CRUMBLE' else value
            self.w(arg(1),value);self.events.append(['registry',receiver,key,value]);m.return_from_external(int(value!=0),8)
        elif a==0x5022b5:
            self.frontier=a;m.uc.emu_stop()
        else: raise AssertionError(hex(a))
    def run(self):
        results=[];steps=[];snapshots=[]
        for command in ([0] if self.exhausted or self.occupied else [0,1000,29,30,7]):
            self.w(STATE+0x1c,command)
            done=self.m.call(0x40f7b0,arguments=[ACTOR]);steps.append([0x40f7b0,ACTOR,command])
            if not done.completed:
                if self.frontier is None: raise RuntimeError((self.label,command,done,self.calls[-5:],self.events[-5:]))
                break
            results.append(self.m.register(UC_X86_REG_EAX))
            snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(MANAGER,0x2c),(NODES,0xc0)]+self.allocations+self.ordinary))
        if not self.exhausted and not self.occupied:
            child=self.get(self.get(STATE+0x18)+0xa0)
            while child:
                actor=self.get(child+0xc); state=self.get(actor+0x6c)
                self.w(state+0x1c,7); done=self.m.call(0x488e30,arguments=[actor]);steps.append([0x488e30,actor,7])
                assert done.completed,(self.label,done)
                results.append(self.m.register(UC_X86_REG_EAX));child=self.get(child+0x50)
            snapshots.append(self.snapshot([(ACTOR,0x1b4),(STATE,0x174),(MANAGER,0x2c),(NODES,0xc0)]+self.allocations+self.ordinary))
        if self.occupied:
            assert self.frontier==0x5022b5, (self.label, self.frontier)
        return dict(label=self.label,children=self.children,resources=self.resources,exhausted=self.exhausted,interleave=self.interleave,occupied=self.occupied,foreign=self.snapshot(self.foreign),initial=self.initial,steps=steps,results=results,snapshots=snapshots,events=self.events,requests=self.requests,calls=self.calls,boundaries=self.boundaries,frontier=self.frontier,allocations=self.allocations)
def prepare(out):
    profiles=[Reference('one-child',1).run(),Reference('three-children',3).run(),Reference('nonzero-resources',1,resources=True).run()]
    profiles += [Reference('interleaved-child-helpers',3,interleave=True).run()]
    exhaustions=[Reference('exhaustion-'+str(i),1,i).run() for i in (1,4,5,6)]
    exhaustions += [Reference('occupied-helper-'+hex(size),occupied=size).run() for size in (0xa4,0x6c)]
    out.mkdir(parents=True,exist_ok=True)
    (out/'reference.json').write_text(json.dumps(dict(version=1,executable_sha256=claw().sha256,profiles=profiles,exhaustions=exhaustions),indent=2)+'\n')
    print(json.dumps(dict(status='pass',profiles=len(profiles))))
def compare(out):
    ref,actual=[json.loads((out/name).read_text()) for name in ('reference.json','native.json')]
    failures=[]
    for group in ('profiles','exhaustions'):
        if len(ref[group])!=len(actual[group]):failures.append(group+' count')
        for r,n in zip(ref[group],actual[group]):
            for key in ('label','results','snapshots','events','requests','frontier','foreign'):
                if r[key]!=n[key]:failures.append(dict(label=r['label'],field=key))
            if not n['physicalIntegrity']:failures.append(dict(label=r['label'],field='physical allocation integrity'))
            if r['occupied'] and (n['frontier']!=0x5022b5 or n['completed']!=[False]):
                failures.append(dict(label=r['label'],field='occupied candidate must reach original exhaustion'))
    for r,n in zip(ref['profiles'],actual['profiles']):
        # Inlined child bodies are byte-observed without synthetic host calls.
        selected=set(OBSERVE)-{0x40f7b0,0x488e30,0x488ef0}
        # Scene actor's primary logic binding is likewise performed internally
        # by its canonical owner; secondary Hit/Attack bindings stay observable.
        primary={r['allocations'][i+1][0] for i,(_,size) in enumerate(r['allocations']) if size==0x1b4}
        visible=lambda c:c[0] in selected and not (c[0]==0x4c8160 and c[1] in primary)
        if [c for c in r['calls'] if visible(c)] != [c for c in n['calls'] if visible(c)]:
            failures.append(dict(label=r['label'],field='ordered canonical calls'))
        expected=[0x40f7e8,0x40f7ed,0x40f803]
        for i in range(r['children']):
            expected += [0x40f972 if i==0 else 0x40fa08,0x40f977 if i==0 else 0x40fa0d,0x488e65,0x488e6a,0x488e80,0x488e85]
        expected += [0x40f808] + [0x4dc93a,0x4dc93d,0x4dc943,0x4dc946,0x4dc9fa,0x4dc9fd]*(1+r['children'])
        if r['boundaries'] != expected:failures.append(dict(label=r['label'],field='original CALL continuations'))
        if n['completed'] != [True]*len(r['steps']):failures.append(dict(label=r['label'],field='completion'))
    for control in actual['controls']:
        if not control['passed']:failures.append(dict(control=control['name']))
    result=dict(status='fail' if failures else 'pass',profiles=len(ref['profiles']),controls=len(actual['controls']),failures=failures)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return bool(failures)
def main():
    out=Path(sys.argv[2]).resolve()
    if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence belongs under ignored work/')
    if sys.argv[1]=='prepare':prepare(out)
    elif sys.argv[1]=='compare':return compare(out)
    else:raise ValueError(sys.argv[1])
if __name__=='__main__':raise SystemExit(main())
