"""Original-backed Gabriel attacks and spawned pirate scenarios."""
import struct
from clawparity.cases import Case
F=(0x483e40,0x4444d0,0x4445d0,0x4446f0,0x444760,0x444850,0x444960,0x444aa0,0x444b70,0x444c20,0x444d00,0x444d90,0x444f80)
N={0x483e40:'LS_GABRIELATTACK',0x4444d0:'LS_MULTIBOMBATTACK',0x4446f0:'LS_THUGATTACK1',0x444850:'LS_CANNONATTACK',0x444aa0:'LS_CANNONHIT',0x444c20:'LS_BLOCKED',0x444f80:'LS_DEADACT1'}
def build(f,s,**o):
 def setup(e):
  b=e.object(0x560,'boss',fill=0); a=e.object(0x240,'actor',fill=0); d=e.object(0x180,'data',fill=0); h=e.object(0x40,'holder',fill=0); v=e.object(0x60,'vtable',fill=0); log=e.object(0x100,'callbacks',fill=0)
  def transition(e,c):
   n=e.get(log); e.put(log,n+1); e.put(log+4+(n%12)*16,c.receiver,e.get(b+0x510),e.get(a+0x40),e.get(b+0x524)); return s^0x31415926
  e.put(v+0x48,e.stub('transition','thiscall',0,transition)); e.put(b,v); e.put(b+0xc,d,h); e.put(b+0x12c,a)
  e.put(b+0x138,0x123+s,0xABCDEF21,0xfffffe99-s); e.put(b+0x18c,o.get('direction',2)); e.put(b+0x19c,o.get('last_identity',17)); e.put(b+0x404,o.get('speed',s))
  e.put(b+0x4f4,o.get('hit_start',900),o.get('hit_delay',100)); e.put(b+0x504,o.get('start',500),o.get('delay',500),o.get('sound_fired',0),o.get('fired',0),o.get('hits',2),0xabcdef01); e.put(b+0x520,o.get('immune',0),o.get('pirates',0))
  e.put(d+0x10c,o.get('health',73)); e.put(d+0x38,0xffffffff)
  e.put(a+0x40,o.get('orientation',0x124)); e.put(a+0x4c,0x235+s,0x173+s); e.put(a+0x64,0x701+s)
  for i,off in enumerate((0x118,0x128,0x138)): e.put(a+off,0x80000000 if o.get('sentinels',0)&(1<<i) else 0x100+i*0x21+s,0xA1234567,0xffffff00-i*0x31-s)
  e.put(b+0x134,0x31415926);
  if f in N: e.put(a+0x190,e.object(0x18,'prior-animation',fill=0))
  e.put(a+0x16c,o.get('frame',0x190)); e.put(a+0x18c,a); e.put(a+0x19c,o.get('anim_delay',0)); e.put(a+0x1a4,o.get('complete',0))
  seq=0
  if o.get('sequence',False):
   item=e.object(0x34,'animation-item',fill=0); e.put(item+0xc,9); e.put(item+0x1c,0x24680000+s); arr=e.object(4,'animation-array',words=[item]); seq=e.object(0x18,'animation-sequence',fill=0); e.put(seq+0xc,arr,1)
  for off in (0x30c,0x338,0x468,0x478,0x490,0x494): e.put(b+off,seq)
  e.put(0x537210,o.get('now',1000)); e.put(0x5430c4,13); e.put(0x513e10,s,0xabcdef01^s,0x88776655+s,0xfedcba98-s); e.override(0x4a3050,lambda e,c:o.get('rand',s%7))
  name=N.get(f,'LS_MULTIBOMBATTACK'); np=e.object(len(name)+1,'lookup-name',data=name.encode()+b'\0'); leaf=e.object(0x14,'name-leaf',fill=0); e.put(leaf+8,0,np,3); root=e.object(0x14,'name-root',words=[leaf,leaf,0,0,0]); e.put(0x537668+0x18,root)
  name=o.get('state_name','LS_IDLE'); np=e.object(len(name)+1,'current-name',data=name.encode()+b'\0'); table=e.object(16,'state-table',words=[np]*4); e.put(0x537698+8,0,3,table,0,4); e.put(h+0x1c,1)
  inc=e.object(0x160,'incoming',fill=0); e.put(inc+0xd0,o.get('type',0x20)); e.put(inc+0x138,0x80000000); e.put(d+0x74,0 if o.get('no_incoming') else inc)
  player=e.object(0x80,'player',fill=0); pc=e.object(0x20,'player-component',fill=0); ident=e.object(0xf0,'identity',fill=0); e.put(ident+0xe8,o.get('identity',29)); e.put(player+0x6c,pc); e.put(pc+0x14,ident); e.put(0x537e88,player)
  voice=e.object(0x190,'voice',fill=0); vc=e.object(0x24,'voice-component',fill=0); e.put(voice+0x6c,vc); e.put(0x53c9ac,voice); e.put(0x53c9a8,0)
  for off in range(0x480,0x4c8,4):
   if off not in (0x490,0x494): e.put(b+off,0x7000+off+s)
  sm=e.object(0x80,'sound-manager',fill=0); sound=e.object(0x38,'sound',fill=0); e.put(sound+0x10,sm); handle=e.object(0x14,'sound-handle',fill=0); e.put(handle+0x10,sound); e.put(b+0x4c4,handle); e.put(b+0x4c8,handle if o.get('handle',True) else 0,handle if o.get('handle',True) else 0); e.put(0x532c0c,o.get('sound_enabled',1)); e.put(0x532c10,0x13579+s)
  if o.get('active_sound'):
   e.put(sm+0x78,1)
   channel=e.object(0x38,'sound-channel',fill=0); interface=e.object(4,'DirectSoundBuffer',fill=0); methods=e.object(0x48,'DirectSoundBuffer-vtable',fill=0)
   e.put(channel+0xc,interface,sm,0x234,22050); e.put(channel+0x30,1); e.put(sound+0x30,channel+4,channel+4); e.put(interface,methods)
   def com_effect(off):
    def com(e,c):
     n=e.get(log+0x80); e.put(log+0x80,n+1)
     observed=(c.arguments[0],e.get(c.arguments[1])) if off==0x24 else c.arguments
     e.put(log+0x84+(n%3)*16,*observed)
     if off==0x24: e.put(c.arguments[1],0)
     return 0
    return com
   # Record real platform calls, including state at the final Play boundary.
   for off,argc in ((0x24,2),(0x3c,2),(0x40,2),(0x44,2),(0x30,4)):
    e.put(methods+off,e.stub('DirectSoundBuffer-'+hex(off),'stdcall',argc,com_effect(off),arguments=('u32','out:4') if off==0x24 else ('u32',)*argc))
   e.put(0x532c10,7)
  ctx=e.object(0x20,'context',fill=0); world=e.object(0x30,'world',fill=0); mgr=e.object(0x40,'actor-manager',fill=0); wi=e.object(0x30,'world-info',fill=0); reg=e.object(0x24,'class-registry',fill=0); buckets=e.object(4,'class-buckets',fill=0)
  e.put(b+0x130,ctx); e.put(ctx+0xc,world); e.put(world+8,mgr); e.put(mgr+0xc,wi); e.put(wi+0x14,reg); e.put(reg+0x14,buckets,1)
  nodes=[e.object(12,'free-node',fill=0) for _ in range(8)]
  for i,node in enumerate(nodes): e.put(node,nodes[i+1] if i+1<len(nodes) else 0)
  e.put(mgr+0x20,nodes[0])
  def initialize(e,c):
   created=c.arguments[0]; comp=e.get(created+0x6c); st=e.object(0x560,'spawn-state',fill=0); sh=e.object(0x20,'spawn-holder',fill=0); e.put(st+0x10,sh); e.put(st+0x12c,created); e.put(st+0x404,s^0x1234); e.write(st+0x38,struct.pack('<ddd',1.,2.,3.)); e.write(st+0x68,struct.pack('<ddd',10.,20.,30.)); e.put(comp+0x18,st); e.put(log+0xd0,e.get(log+0xd0)+1); e.put(log+0xd4,created,e.get(created+0x4c),e.get(created+0x50),e.get(created+0x64)); return s
  cb=e.stub('registered-initialize','cdecl',1,initialize); prev=0
  for cls in ('GabrielBomb','RedTailPirate'):
   np=e.object(len(cls)+1,'class-name',data=cls.encode()+b'\0'); record=e.object(0x14,'registration',fill=0); e.put(record+0x10,cb); prev=e.object(16,'map-entry',words=[prev,0,np,record])
  e.put(buckets,0 if o.get('missing_class') else prev)
  return {'boss':b}
 return setup

def cases(random_source):
 s=random_source.randrange(1,128); n=0
 def case(f,**o):
  nonlocal n
  n+=1
  return Case(f'{f:x} scenario {n}: {o}',f,build(f,s,**o),receiver=lambda t:t['boss'])
 for f in F: yield case(f)
 for f in (0x483e40,0x4444d0,0x4446f0,0x444850,0x444aa0,0x444c20,0x444f80):
  for seq in (False,True):
   for ori in (0x124,0x126):
    for mask in (0,7): yield case(f,sequence=seq,orientation=ori,sentinels=mask)
 for f in (0x4445d0,0x444960,0x444b70):
  for now in (999,1000,1001,0,0xffffffff): yield case(f,now=now)
 for f in (0x4445d0,0x444760,0x444960,0x444b70,0x444d00):
  for done,delay,fired in ((0,0,0),(1,1,0),(1,0,1),(1,0,0)): yield case(f,complete=done,anim_delay=delay,fired=fired,frame=0x190)
 for f in (0x4445d0,0x444960):
  for fired in (0,1):
   for frame in (0x190,0x191,0x192): yield case(f,frame=frame,fired=fired)
 for r in (0,1,2,3,4,-1,-2,-3,-4,0x80000000,0x7fffffff):
  for f in (0x4444d0,0x444760,0x444850,0x444aa0,0x444d00): yield case(f,rand=r)
 for r in (0,1,2,3,-1): yield case(0x4445d0,rand=r,frame=0x191)
 for f in (0x444c20,0x444f80):
  for direction in (0,1,2,3,0xffffffff):
   for ori in (0x124,0x126): yield case(f,direction=direction,orientation=ori)
 for n in (0,1,2,0xffffffff,0x7fffffff): yield case(0x4446f0,pirates=n)
 for f in (0x444760,0x444d00):
  for sound in (0,1): yield case(f,sound_fired=sound,complete=1)
 yield case(0x444760,complete=1,missing_class=True)
 yield case(0x444760,complete=1)
 for mask in range(8): yield case(0x444960,complete=1,frame=0x191,orientation=0x126,sentinels=mask)
 for n in (0,3,4,5,0x7fffffff,0xffffffff):
  yield case(0x444aa0,hits=n)
  yield case(0x444b70,hits=n,complete=1)
 for handle,sound in ((False,1),(True,0),(True,1)): yield case(0x444aa0,handle=handle,sound_enabled=sound)
 for name in ('LS_BLOCKED','LS_CANNONHIT','LS_DEADACT1','LS_DEADACT2','LS_DEADACT3','LS_DEADACT4','LS_IDLE'): yield case(0x444d90,state_name=name)
 for ty in (0x20,0x2000000,0x40,0x10): yield case(0x444d90,type=ty)
 yield case(0x444d90,immune=1)
 yield case(0x444d90,no_incoming=True)
 yield case(0x444d90,last_identity=29)
 for now in (999,1000,1001,0xffffffff): yield case(0x444d90,now=now)
 for speed in (0,1,0xffffffff,0x40000000,0x7fffffff,0x80000000): yield case(0x483e40,speed=speed)

 for f in N:
  for flag in (1,0xffffffff,0x80000000): yield case(f,fired=flag,sound_fired=flag,delay=7,sequence=True)
 for r in (0,1,-1): yield case(0x444aa0,active_sound=True,rand=r,delay=7,sound_fired=0x97531,fired=0x2468)
