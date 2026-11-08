"""Original-backed finite transport reference; derived bytes stay in ignored work/."""
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from Tests.clawparity.kernel import Machine
from Tests.clawparity.program import claw
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP
BASE,SIZE=0x10000000,0x10000
MANAGER,SCENE,REGISTRY,CONTEXT,LOGICS,META,CONTAINER,BOSS,NODE,TRACK,KEY=[BASE+i*0x100 for i in range(1,12)]
SPEC=json.loads((ROOT/"Tests/NativeObjectConnections/boss_stager_transport.json").read_text())
SETRECT=SPEC["fixtures"]["SetRect"]
ALLOC=0x61000000
OBSERVE=(0x42b000,0x42a630,0x40af90,0x46cab0,0x4b54a0,0x4b54f0,0x4c8060,0x4c7fe0,0x4f63ec,0x4c8160,0x4c81b0,0x4c8da0,0x4c8be0,0x4c9780,0x4c9830,0x4c9d40,0x4c7df0,0x491fa0)
class Reference:
    def __init__(self,kind,found=True,context=True,scene=True,flags=0x200000):
        self.kind,self.found,self.flags=kind,found,flags
        self.m=Machine(claw(),BASE,SIZE);self.m.uc.mem_map(ALLOC,0x10000);self.m.uc.mem_map(0x68001000,0x1000)
        self.blocks,self.events,self.entries,self.allocations=[],[],[],[]
        self.next_alloc=ALLOC
        self.blocks.append((BASE,SIZE))
        for a,n in ((0x50c264,0x64),(0x513740,0x50),(0x513790,0xe0),(0x529fbc,8),(0x522280,16),(0x52c8c8,16),(0x5371fc,4),(0x5349dc,4),(0x52c6f0,8),(0x510020,4)):
            self.blocks.append((a,n))
        self.w(MANAGER+0x2c,SCENE if scene else 0);self.w(MANAGER+0x50,REGISTRY);self.w(MANAGER+0x78,8)
        self.w(SCENE,0x50c264,MANAGER);self.w(REGISTRY+0x20,CONTEXT if context else 0)
        self.w(CONTAINER+0xc,CONTEXT);self.w(CONTAINER+0x28,1)
        self.w(CONTEXT+0x10,REGISTRY,LOGICS);self.w(CONTEXT+0x24,3)
        self.w(META+0x10,0x491fa0 if kind=='health' else 0x48e430)
        self.w(0x5371fc,MANAGER);self.w(0x5349dc,BOSS);self.w(BOSS+0x10c,173)
        self.m.write(KEY,b'BossHealthMeter\0' if kind=='health' else b'Claw\0')
        # The physical SetRect import has a distinct fixed transport token.
        self.w(SETRECT["slot"],SETRECT["target"]);self.blocks.append((SETRECT["slot"],4))
        for a in OBSERVE:self.m.observe(a,self.entry)
        for a in (0x4a48e0,0x4f6286,0x4f51c5,0x68001000):self.m.intercept(a)
        self.m.on_external=self.external
        self.initial=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in self.blocks]
    def w(self,a,*v):self.m.write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
    def get(self,a):return self.m.words(a,1)[0]
    def entry(self,m,a):
        # Only semantic receiver-bearing entries are compared; cdecl ECX is scratch.
        self.entries.append([a,m.register(UC_X86_REG_ECX) if a not in (0x4f63ec,0x491fa0) else 0])
        if a==0x491fa0:
            actor=self.get(m.register(UC_X86_REG_ESP)+4)
            self.events.append(['callback',actor,self.get(actor+0x68),self.get(CONTAINER+0x1c),self.get(NODE+8)])
    def external(self,m,a):
        sp=m.register(UC_X86_REG_ESP);arg=lambda i:self.get(sp+4+4*i);receiver=m.register(UC_X86_REG_ECX)
        if a==0x4a48e0:
            n=arg(0);token=self.next_alloc;extent=(n+3)&~3;self.m.write(token,bytes([204])*n)
            self.next_alloc=(token+extent+15)&~15;self.allocations.append([token,n]);self.events.append(['malloc',token,n]);m.return_from_external(token,0)
        elif a==0x4f6286:
            key=m.read(arg(0),32).split(b'\0')[0].decode('ascii')
            if self.kind=='music':value=TRACK if self.found and key=='BOSS' else 0
            elif receiver==LOGICS+0x10:value=META if self.found else 0
            elif receiver==REGISTRY+0x10 and key=='GAME_BOSSBAR':value=0
            else:raise RuntimeError(('registry',hex(receiver),key))
            self.events.append(['registry',receiver,key,value]);self.w(arg(1),value);m.return_from_external(bool(value),8)
        elif a==0x4f51c5:
            if receiver!=CONTAINER+0x10 or self.get(CONTAINER+0x1c):raise RuntimeError('unexpected list')
            actor=arg(0);self.w(NODE,0,0,actor);self.w(CONTAINER+0x14,NODE,NODE,1)
            self.events.append(['append',receiver,actor,NODE]);m.return_from_external(NODE,4)
        elif a==0x68001000:
            values=[arg(i) for i in range(1,5)];self.w(arg(0),*values);self.events.append(['rectangle',*values]);m.return_from_external(1,20)
        else:raise RuntimeError(('service',hex(a)))
    def run(self,label,rebind=False):
        if self.kind=='music':root,receiver,args=0x42b000,MANAGER,()
        elif self.kind=='contact':root,receiver,args=0x4c8060,CONTAINER,(KEY,)
        else:root,receiver,args=0x4c8da0,CONTAINER,(0,0,0,0,KEY,self.flags)
        results=[]
        for _ in range(2 if rebind else 1):
            done=self.m.call(root,ecx=receiver,arguments=args)
            if not done.completed:raise RuntimeError(done)
            results.append(self.m.register(UC_X86_REG_EAX))
        spans=[(BASE,SIZE),(0x52c6f0,8)]+[(a,n) for a,n in self.allocations]
        return dict(label=label,kind=self.kind,found=self.found,root=root,receiver=receiver,args=args,rebind=rebind,initial=self.initial,allocations=self.allocations,results=results if self.kind!='contact' else [],events=self.events,entries=self.entries,final=[dict(address=a,data=self.m.read(a,n).hex()) for a,n in spans])
def prepare(out):
    profiles=[]
    for label,opts in [('music-selected',{}),('music-missing',{'found':False}),('music-no-context',{'context':False}),('music-no-scene',{'scene':False})]:profiles.append(Reference('music',**opts).run(label))
    for label,found,rebind in [('contact-create',True,False),('contact-rebind',True,True),('contact-missing',False,False)]:profiles.append(Reference('contact',found=found).run(label,rebind))
    for label,found,flags in [('health-create-callback',True,0x200000),('health-create-deferred',True,0),('health-missing',False,0x200000)]:profiles.append(Reference('health',found=found,flags=flags).run(label))
    result=dict(version=1,executable_sha256=claw().sha256,profiles=profiles)
    out.mkdir(parents=True,exist_ok=True);(out/'reference.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='pass',profiles=len(profiles),output=str(out/'reference.json'))))
def compare(out):
    reference=json.loads((out/'reference.json').read_text())
    native=json.loads((out/'native.json').read_text())
    failures=[]
    if len(native['profiles'])!=len(reference['profiles']):failures.append('profile count')
    for expected,actual in zip(reference['profiles'],native['profiles']):
        label=expected['label']
        for field in ('label','results','events','final'):
            if expected[field]!=actual[field]:failures.append(dict(label=label,field=field))
        if not all(c['completed'] for c in actual['completions']):failures.append(dict(label=label,field='completion',actual=actual['completions']))
        if label=='music-selected':
            calls=actual['calls']
            # The native owner may call its own 46cab0 body directly. The
            # original-only trace proves that body, while the host observes its
            # real music dependency and exact receiver/output effects.
            required=[[0x42a630,MANAGER],[0x40af90,SCENE],[0x4b54a0,REGISTRY]]
            if [0x46cab0,SCENE] not in expected['entries']:
                failures.append(dict(label=label,field='original music virtual witness'))
            cursor=0
            for row in calls:
                if cursor<len(required) and row==required[cursor]:cursor+=1
            if cursor!=len(required):failures.append(dict(label=label,field='actual scene virtual witness',calls=calls))
    for control in native['controls']:
        if not control['passed']:failures.append(dict(control=control['name']))
    result=dict(status='fail' if failures else 'pass',profiles=len(reference['profiles']),controls=len(native['controls']),failures=failures)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return bool(failures)
def main():
    command=sys.argv[1];out=Path(sys.argv[2]).resolve()
    if (ROOT/'work').resolve() not in out.parents:raise ValueError('evidence must stay under work/')
    if command=='prepare':prepare(out)
    elif command=='compare':return compare(out)
    else:raise ValueError(command)
if __name__=='__main__':raise SystemExit(main())
