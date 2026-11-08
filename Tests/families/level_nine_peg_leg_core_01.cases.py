"""Original-driven PegLeg state cases."""
import struct
from clawparity.cases import Case


def double(e,a,v): e.write(a,struct.pack('<d',v))


def setup(**p):
 def build(e):
  def obj(*a,**kw):
   kw.setdefault("fill",0)
   return e.object(*a,**kw)
  o=obj(0x4e8,'peg-leg',fill=0x39); a=obj(0x220,'actor'); d=obj(0x200,'logic'); w=obj(0x80,'world'); s=obj(0xa0,'scene'); pl=obj(0x100,'plane'); lv=obj(0xa0,'level'); player=obj(0x220,'player'); log=obj(0x400,'observations'); vt=obj(0x70,'vtable'); fr=obj(0x40,'frame'); arr=obj(4,'frames',words=[fr]); ani=obj(0x20,'animation',words=[0,0,0,arr,1])
  e.put(fr+0x1c,p.get('result',0)); e.put(fr+0xc,9); e.put(fr+0x18,5)
  e.put(a+0xc,w); e.put(a+0x6c,d); e.put(w+8,s); e.put(w+0x24,pl); e.put(s+0xc,w)
  tiles=obj(4,'tiles',words=[0xffffffff]); rows=obj(4,'rows'); e.put(lv+0x20,tiles,rows); e.put(lv+0x30,1,1); e.put(lv+0x8c,16,16); e.put(pl+0x5c,lv)
  e.put(a+0x4c,p.get('x',100),100); e.put(player+0x4c,p.get('px',100),p.get('py',100)); e.put(player+0xcc,p.get('ps',0)); e.put(a+0x38,p.get('astate',0)); e.put(a+0x40,p.get('flags',0))
  e.put(a+0x188,0,a,ani,fr,0,p.get('delay',0),1,p.get('end',1),p.get('result',0),0,struct.unpack('<I',struct.pack('<f',p.get('animation_speed',1.)))[0])
  e.put(d+0x1c,0x12345678); e.put(o,vt); e.put(o+0xc,a,d); e.put(o+0x128,a,a,d,0x11223344); e.put(o+0x18c,p.get('dir',3),s,a); e.put(o+0x184,p.get('state',7))
  for off in range(0x308,0x494,4):
   resource=obj(0x20,'animation-%x'%off,words=[0,0,0,arr,1]) if off not in (0x45c,0x490) else 0
   e.put(o+off,resource)
  e.put(o+0x2fc,0,0)
  for off in range(0x494,0x4e8,4): e.put(o+off,0)
  for off,key,default in ((0x4a0,'rw',0),(0x4a8,'fw',0),(0x4b0,'aw',0),(0x4b8,'duration',1500),(0x4bc,'dest',100),(0x4cc,'fired',1),(0x4d0,'count',0),(0x4d8,'hurt',0),(0x4dc,'alt',0),(0x4e0,'seen',1),(0x4c8,'speed',500)): e.put(o+off,p.get(key,default))
  double(e,o+0x68,p.get('pos',100.25)); double(e,o+0x80,p.get('left',-100.)); double(e,o+0x98,p.get('right',500.))
  e.put(o+0x138,17,29,41); e.put(a+0x118,11,13,19); e.put(a+0x128,23,31,47,59); e.put(a+0x138,61,67,71)
  for g,v in ((0x537210,p.get('clock',1000)),(0x5430c4,1),(0x537964,p.get('level',9)),(0x537e88,player),(0x534eac,p.get('disable',0)),(0x532c0c,0),(0x53c9ac,0),(0x537680,0)): e.put(g,v)
  def callback(e,c):
   n=e.get(log); e.put(log+4+(n%40)*20,c.function,c.receiver,e.get(o+0x4a4),e.get(o+0x4a8),e.get(a+0x128)); e.put(log,n+1); return 0x89abcdef
  for slot in (0x44,0x48,0x58): e.put(vt+slot,e.stub('state-%x'%slot,'thiscall',0,callback))
  vals=p.get('rand',(73,1,37,0))
  def rand(e,c): return vals[(e.calls_so_far(0x4a3050)-1)%len(vals)]&0xffffffff
  e.override(0x4a3050,rand)
  return dict(o=o,a=a,d=d,ani=ani,vt=vt,log=log,w=w,s=s)
 return build


def C(label,f,**p): return Case(label,f,setup(**p),receiver=lambda t:t['o'])


def cases(random_source):
 for r in (0,1,1000,1001,0x7fffffff,0xffffffff): yield C('init-%x'%r,0x469510,rand=(r,))
 for level in (8,9,10):
  for direction in (1,2,3):
   for pos in (-101.5,100.,100.25,501.5):
    for dest in (0,100,600): yield C('roll-%s-%s-%s-%s'%(level,direction,pos,dest),0x469e20,level=level,dir=direction,pos=pos,dest=dest)
 for direction in (2,3,4):
  for pos in (-100.,100.,500.):
   for clock in (0,1499,1500,0xffffffff): yield C('roll-limit-%s-%s-%s'%(direction,pos,clock),0x469e20,dir=direction,pos=pos,clock=clock,dest=10000 if direction==2 else -10000,left=pos,right=pos)
 for level in (8,9):
  for direction in (2,3,4):
   for px in (-100,100,500): yield C('start-roll-%s-%s-%s'%(level,direction,px),0x469c40,level=level,dir=direction,px=px)
 yield C('start-roll-wait',0x469c40,rw=1001)
 for flags in (0,2):
  for alt in (0,1):
   for level in (8,10):
    for clock in (0,1000): yield C('start-fire-%s-%s-%s-%s'%(flags,alt,level,clock),0x469840,flags=flags,alt=alt,level=level,clock=clock,aw=500)
 yield C('start-fire-wait',0x469840,fw=1001)
 yield C('start-fire-player',0x469840,level=8,ps=5)
 for level in (8,10):
  for count in (0,1,0xffffffff):
   for aw in (0,1001):
    for end in (0,1):
     for delay in (0,5): yield C('fire-%s-%s-%s-%s-%s'%(level,count,aw,end,delay),0x469a40,level=level,count=count,aw=aw,end=end,delay=delay)
 for state in range(8):
  for hurt,seen in ((0,0),(0,1),(1,0)):
   for r in (0,49,50,69,70,100): yield C('home-%s-%s-%s-%s'%(state,hurt,seen,r),0x469570,state=state,hurt=hurt,seen=seen,rand=(r,1),rw=2000)
 for py in (49,50,100,150,151): yield C('home-height-%s'%py,0x469570,py=py,seen=0,rand=(0,1))
 for n in range(10): yield C('random-%s'%n,0x469e20,pos=random_source.uniform(-200,800),dir=random_source.choice((2,3)),dest=random_source.randint(-200,800))


def constructor(found,scale):
 def build(e):
  t=setup()(e); o=t['o']; a=t['a']; d=t['d']; w=t['w']
  for off in (0x10,0x14,0x28,0x2c):
   table=e.object(0x30,'resource-manager-%x'%off,fill=0)
   e.put(table+0x18,1)
   e.put(w+off,table)
   if off==0x2c and found:
    names=(b'GAME_NULL', b'LEVEL_PEGLEG', b'LEVEL_PEGLEG_00410001', b'LEVEL_PEGLEG_00410002', b'LEVEL_PEGLEG_00410003', b'LEVEL_PEGLEG_00410004', b'LEVEL_PEGLEG_00410005', b'LEVEL_PEGLEG_00410006', b'LEVEL_PEGLEG_00410007', b'LEVEL_PEGLEG_00410008', b'LEVEL_PEGLEG_00410009', b'LEVEL_PEGLEG_00410010', b'LEVEL_PEGLEG_00410011', b'LEVEL_PEGLEG_00410015', b'LEVEL_PEGLEG_00410016', b'LEVEL_PEGLEG_00410017', b'LEVEL_PEGLEG_ADVANCE', b'LEVEL_PEGLEG_BACKWARDROLL', b'LEVEL_PEGLEG_FASTADVANCE', b'LEVEL_PEGLEG_FORWARDROLL', b'LEVEL_PEGLEG_HITHIGH', b'LEVEL_PEGLEG_HITLOW', b'LEVEL_PEGLEG_HOME', b'LEVEL_PEGLEG_IDLE', b'LEVEL_PEGLEG_JUMP', b'LEVEL_PEGLEG_KILLFALL', b'LEVEL_PEGLEG_LIFTED1', b'LEVEL_PEGLEG_LIFTED2', b'LEVEL_PEGLEG_ROLL1', b'LEVEL_PEGLEG_SOLGUNFR8_22', b'LEVEL_PEGLEG_STRIKE1', b'LEVEL_PEGLEG_STRIKE2', b'LEVEL_PEGLEG_THROWN')
    head=0
    for name in names:
     key=e.object(len(name)+1,'resource-name',data=name+b'\0',fill=0)
     node=e.object(16,'resource-node',words=[head,0,key,t['ani']],fill=0); head=node
    buckets=e.object(4,'buckets',words=[head],fill=0); e.put(table+0x14,buckets)
  e.put(d+0x64,0)
  e.put(0x534938,0)
  e.write(0x5262b8,struct.pack('<f',scale))
  e.write(0x5262b4,struct.pack('<f',1.25)); e.write(0x5262b0,struct.pack('<f',0.75))
  return t
 return build


def destruction(refs):
 def build(e):
  t=setup()(e); o=t['o']; e.put(o+0x2fc,32); e.put(o+0x300,0x35)
  for off in (0x1a4,0x1a8):
   block=e.object(20,'CString-header',words=[refs,3,3,0],fill=0)
   e.put(o+off,block+12)
  def dec(e,c):
   v=(e.get(c.arguments[0])-1)&0xffffffff; e.put(c.arguments[0],v); return v
  e.override(0x5469e8,dec)
  return t
 return build


_state_cases=cases

def cases(random_source):
 yield from _state_cases(random_source)
 for found in (False,True):
  for scale in (0.,1000.): yield Case('construct-%s-%s'%(found,scale),0x468eb0,constructor(found,scale),receiver=lambda t:t['o'],arguments=(lambda t:t['a'],))
 for refs in (1,2):
  yield Case('destruct-%s'%refs,0x4694a0,destruction(refs),receiver=lambda t:t['o'])
  for flags in (0,1,2,3): yield Case('scalar-delete-%s-%s'%(refs,flags),0x469480,destruction(refs),receiver=lambda t:t['o'],arguments=(flags,))
 for direction in (2,3): yield C('fire-facing-%s'%direction,0x469840,dir=direction,rand=(0,1))
 for state,hurt in ((0,0),(0,1)):
  for disable in (0x26b7,0): yield C('home-hidden-%s-%s-%s'%(state,hurt,disable),0x469570,state=state,hurt=hurt,disable=disable,astate=-1)


def dispatch(index,grow=False,empty=False):
 def build(e):
  t=setup()(e); log=t['log']
  def cb(e,c): e.put(log,c.receiver,index&0xffffffff,e.get(0x537c80)); return 7
  fn=e.stub('dispatch-state','thiscall',0,cb)
  tab=e.object(12,'dispatch-table',words=[0 if empty else fn,0 if empty else fn,0 if empty else fn],fill=0)
  fallback=e.object(4,'fallback-state',words=[fn],fill=0)
  e.put(0x537c68,10,12,tab,fallback,4)
  base_table=e.object(20,'base-dispatch-table',words=[fn,fn,fn,fn,fn],fill=0)
  e.put(0x537880,9,13,base_table,base_table,4)
  return t
 return build


def with_sound(**p):
 def build(e):
  t=setup(**p)(e); manager=e.object(0x80,'sound-manager',fill=0); sound=e.object(0x18,'sound-record',fill=0); channel=e.object(0x18,'sound-channel',fill=0); e.put(channel+0x10,manager); e.put(sound+0x10,channel); e.put(t['o']+0x490,sound); e.put(0x532c0c,p.get('enabled',1)); return t
 return build


def projectile(speed,flipped,sound):
 def build(e):
  t=setup(result=1,fired=0,speed=speed)(e); w=t['w']; o=t['o']; e.put(o+0x130,t['s'])
  # Supply the original factory's dynamic logic descriptor and initialization callback.
  manager=e.object(0x30,'logic-manager',fill=0); buckets=e.object(4,'logic-buckets',fill=0); desc=e.object(0x18,'bullet-descriptor',fill=0)
  def init(e,c):
   bullet=c.arguments[0]; data=e.get(bullet+0x6c); runtime=e.object(0x150,'bullet-runtime',fill=0)
   e.put(runtime+0x12c,bullet); e.put(runtime+0x138,17,19,23); e.put(bullet+0x40,flipped); e.put(data+0x18,runtime)
   e.put(t['log'],bullet,c.arguments[0],e.get(o+0x4cc),e.get(o+0x4c8)); return 0
  e.put(desc+0x10,e.stub('bullet-initialize','cdecl',1,init)); key=e.object(7,'bullet-key',data=b'Bullet\0',fill=0); node=e.object(16,'bullet-node',words=[0,0,key,desc],fill=0)
  e.put(buckets,node); e.put(manager+0x14,buckets,1); e.put(w+0x14,manager)
  sprites=e.object(0x30,'sprite-manager',fill=0); e.put(sprites+0x18,1); e.put(w+0x10,sprites)
  e.put(t['s']+0x28,0x10)
  if sound:
   sm=e.object(0x80,'sound-manager',fill=0); sr=e.object(0x18,'sound-record',fill=0); ch=e.object(0x18,'sound-channel',fill=0); e.put(ch+0x10,sm); e.put(sr+0x10,ch); e.put(o+0x45c,sr); e.put(0x532c0c,1)
  return t
 return build


_previous_cases=cases

def cases(random_source):
 yield from _previous_cases(random_source)
 for index in (9,10,11,12,13):
  for empty in (False,True): yield Case('dispatch-%s-%s'%(index,empty),0x468ad0,dispatch(index,empty=empty),receiver=lambda t:t['o'],arguments=(index,))
 for direction in (2,3):
  for enabled in (0,1): yield Case('roll-sound-%s-%s'%(direction,enabled),0x469c40,with_sound(dir=direction,level=8,enabled=enabled),receiver=lambda t:t['o'])
 for speed in (-500,500):
  for flipped in (0,2):
   for sound in (False,True): yield Case('projectile-%s-%s-%s'%(speed,flipped,sound),0x469a40,projectile(speed,flipped,sound),receiver=lambda t:t['o'])
 for state in range(7): yield C('home-no-visibility-%s'%state,0x469570,state=state,disable=0x26b7)


_final_cases=cases

def cases(random_source):
 yield from _final_cases(random_source)
 for speed in (0.5,1.5):
  for root in (0x469570,0x469a40,0x469e20):
   yield C('animation-rate-%x-%s'%(root,speed),root,animation_speed=speed,state=0,rw=2000,rand=(100,1))


def constructor_dirty(found):
 def build(e):
  t=constructor(found,1000.)(e)
  for off in range(0x494,0x4e8,4): e.put(t['o']+off,0x35190000+off)
  return t
 return build


def destruction_heap_container(refs):
 def build(e):
  t=destruction(refs)(e)
  storage=e.object(64,'owned-string-container',fill=0x57)
  e.put(t['o']+0x2fc,64,storage)
  return t
 return build


def fire_voice_boundary(value):
 def build(e):
  t=setup(rand=(value,1),level=8)(e)
  speaker=e.object(0x188,'active-speaker',fill=0)
  data=e.object(0x20,'speaker-logic',fill=0)
  e.put(speaker+0x6c,data)
  e.put(0x53c9ac,speaker)
  e.put(0x53c9a8,0)
  return t
 return build


_mutation_cases=cases

def cases(random_source):
 yield from _mutation_cases(random_source)
 for found in (False,True):
  yield Case('construct-dirty-%s'%found,0x468eb0,constructor_dirty(found),receiver=lambda t:t['o'],arguments=(lambda t:t['a'],))
 for refs in (1,2):
  yield Case('destroy-owned-container-%s'%refs,0x4694a0,destruction_heap_container(refs),receiver=lambda t:t['o'])
 for root in (0x469570,0x469e20):
  for delay in (2,5):
   yield C('animation-delay-%x-%s'%(root,delay),root,delay=delay,state=7,dir=4,clock=0)
 for value in (24,25,26):
  yield Case('voice-threshold-%s'%value,0x469840,fire_voice_boundary(value),receiver=lambda t:t['o'])


def moving_animation(elapsed, delay, rate, dx, dy, **options):
 """A real pending frame has observable controller and actor side effects."""
 def build(e):
  t=setup(end=0,delay=delay,animation_speed=rate,**options)(e)
  a=t['a']; frame=e.get(a+0x194)
  e.put(frame+0x10,2)
  e.put(frame+0x20,dx,dy)
  e.put(a+0x1a8,0x13579bdf)
  e.put(a+0x1ac,0x2468ace0)
  e.put(0x5430c4,elapsed)
  return t
 return build


def constructor_distinct(found, scale, marker):
 def build(e):
  t=constructor(found,scale)(e)
  # Each named animation has its own identity, even where its frame is shared.
  manager=e.get(t['w']+0x2c)
  if found:
   node=e.get(e.get(manager+0x14))
   while node:
    resource=e.object(0x20,'distinct-named-animation',data=e.read(t['ani'],0x20),fill=0)
    e.put(node+12,resource)
    node=e.get(node)
  for off in range(0x494,0x4e8,4): e.put(t['o']+off,(marker+off)&0xffffffff)
  return t
 return build


def destruction_observed(refs):
 def build(e):
  t=destruction_heap_container(refs)(e); o=t['o']; log=t['log']
  def observe(e,c):
   n=e.get(log)
   e.put(log+4+n*24,c.function,c.arguments[0],e.get(o),e.get(o+0x2f4),e.get(o+0x1a4),e.get(o+0x1a8))
   e.put(log,n+1)
  def free(e,c):
   observe(e,c); e.release(c.arguments[0]); return 0
  def dec(e,c):
   observe(e,c)
   value=(e.get(c.arguments[0])-1)&0xffffffff
   e.put(c.arguments[0],value)
   return value
  e.override(0x4a49b0,free)
  e.override(0x5469e8,dec)
  return t
 return build


def projectile_callback(speed, facing, changed_speed):
 def build(e):
  t=projectile(speed,facing,False)(e); o=t['o']
  manager=e.get(t['w']+0x14)
  desc=e.get(e.get(e.get(manager+0x14))+12)
  def initialize(e,c):
   bullet=c.arguments[0]
   old=e.get(bullet+0x6c)
   runtime=e.object(0x150,'dirty-projectile-runtime',fill=0x63)
   replacement=e.object(0x20,'replacement-projectile-logic',fill=0)
   e.put(runtime+0x12c,bullet)
   e.put(runtime+0x138,17,29,43,59)
   e.put(bullet+0x40,facing)
   e.put(replacement+0x18,runtime)
   e.put(bullet+0x6c,replacement)
   e.put(o+0x4c8,changed_speed)
   e.put(t['log'],c.receiver,bullet,old,replacement,runtime,e.get(o+0x4cc),e.get(bullet+0x104),e.get(bullet+0xd0))
   return 0x87654321
  e.put(desc+0x10,e.stub('mutating-projectile-initialize','cdecl',1,initialize))
  return t
 return build


_strengthened_cases=cases

def cases(random_source):
 yield from _strengthened_cases(random_source)
 for root in (0x469570,0x469a40,0x469e20):
  for elapsed,delay in ((0,7),(1,7),(7,7),(8,7),(3,0)):
   for rate in (1.,1.5):
    yield Case('active-frame-%x-%s-%s-%s'%(root,elapsed,delay,rate),root,
               moving_animation(elapsed,delay,rate,13,-17,state=7,dir=4,clock=0),receiver=lambda t:t['o'])
 for found in (False,True):
  for scale in (-1.,0.5,1000.):
   marker=random_source.randrange(0x10000000,0x70000000)
   yield Case('distinct-construct-%s-%s'%(found,scale),0x468eb0,
              constructor_distinct(found,scale,marker),receiver=lambda t:t['o'],arguments=(lambda t:t['a'],))
 for refs in (1,2,0xffffffff):
  yield Case('destruction-publication-%s'%refs,0x4694a0,destruction_observed(refs),receiver=lambda t:t['o'])
 for value in (0xfffffffe,0xffffffff,125,126,127,227):
  yield Case('voice-signed-remainder-%s'%value,0x469840,fire_voice_boundary(value),receiver=lambda t:t['o'])
 for speed in (-701,809):
  for facing in (0,2):
   for changed in (-337,0,463):
    yield Case('projectile-reread-%s-%s-%s'%(speed,facing,changed),0x469a40,
               projectile_callback(speed,facing,changed),receiver=lambda t:t['o'])


def constructor_inherited_status(found, status, scale, attack_factor, speed_factor):
 """Elect only entry flags; unchanged constructors determine every later SW."""
 def build(e):
  t=constructor_distinct(found,scale,0x43170000)(e)
  e.write(0x5262b4,struct.pack('<f',attack_factor))
  e.write(0x5262b0,struct.pack('<f',speed_factor))
  e.entry_x87_status(status)
  return t
 return build


_inherited_status_cases=cases

def cases(random_source):
 yield from _inherited_status_cases(random_source)
 # 0x44c000 converts 10*attack_factor; the owned constructor later converts
 # 7*attack_factor. A factor of .5 keeps the base conversion exact while
 # making the owned conversion fractional. 1.25 makes both fractional.
 profiles=(('exact-zero',0.,1.,1.),
           ('owned-fraction',0.,0.5,1.),
           ('base-fraction',0.,1.25,1.),
           ('health-fraction',0.1,1.,1.),
           ('negative-health',-1.,1.,1.),
           ('large-health',1000.,1.,1.))
 for found in (False,True):
  for name,scale,attack_factor,speed_factor in profiles:
   for status in (0,0x20,0x21):
    yield Case('construct-inherited-sw-%02x-%s-%s'%(status,found,name),0x468eb0,
               constructor_inherited_status(found,status,scale,attack_factor,speed_factor),
               receiver=lambda t:t['o'],arguments=(lambda t:t['a'],))
