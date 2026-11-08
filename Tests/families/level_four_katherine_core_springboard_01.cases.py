"""Original-driven Katherine core and springboard cases."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import returns, sequence, reallocate

def obj(env,*args,**kw):
 kw.setdefault('fill',0);return env.object(*args,**kw)

def putd(env,a,v): env.write(a,struct.pack('<d',v))
def putf(env,a,v): env.write(a,struct.pack('<f',v))
def cmap(env, entries=()):
    m=obj(env,0x40,'asset map'); b=obj(env,4,'bucket');env.put(m+0x14,b,1)
    head=0
    for text,value in entries:
        s=obj(env,len(text)+1,'key',data=text.encode()+b'\0'); n=obj(env,16,'node',words=[head,0,s,value]);head=n
    env.put(b,head);return m

def callback(env,name,log,argc=0):
    def effect(env,call):
        n=env.get(log);env.put(log,n+1);env.put(log+4+n*24,call.receiver,*(list(call.arguments)+[0]*4)[:4]);return 0
    return env.stub(name,'thiscall',argc,effect)

def world_setup(env):
    w=obj(env,0x100,'world'); empty=cmap(env)
    for off in (0x10,0x14,0x28,0x2c):env.put(w+off,empty)
    scene=obj(env,0x100,'scene');env.put(w+0x24,scene);env.put(scene+0x64,1024,1024)
    env.put(0x544d18,0);env.put(0x537210,123456)
    env.put(0x537668+0x18,0)
    return w

def spring(mode=2,command=0,board=True,face=0,flag=0,level=0x26bc,height=200,accel=1000.0,x=123,y=456):
 def setup(env):
    a=obj(env,0x300,'actor',fill=0x35);b=obj(env,0x180,'behavior');s=obj(env,0x180,'springboard');w=world_setup(env)
    env.put(a+0xc,w);env.put(a+0x6c,b);env.put(a+0x4c,x,y);env.put(a+0xd0,mode)
    env.put(b+0x14,s if board else 0);env.put(b+0x1c,command);env.put(s,face,0);env.put(s+0x5c,0x71a2b3c4);env.put(s+0x60,0x35261708);env.put(s+0x114,flag)
    env.put(0x537204,obj(env,0x40,'input'));env.put(0x534eac,level)
    for off,value in ((0x10,0.0),(0x18,accel),(0x20,0.0),(0x50,0.0)):putd(env,0x534db8+off,value)
    return {'a':a}
 return setup

def destructor(bits=0,refs=0):
 def setup(env):
    a=obj(env,0x480,'receiver',fill=0x67);env.put(0x544d18,0)
    env.put(a+0x2f8,0);env.put(a+0x2fc,bits)
    if bits>32:env.put(a+0x300,obj(env,(bits+7)//8,'bit-storage',fill=0x5a))
    for off in (0x1a4,0x1a8):
      if refs:
        h=obj(env,16,'string-header',words=[refs,0,0,0]);env.put(a+off,h+12)
      else:env.put(a+off,env.get(0x52e1c8)+12)
    def decrement(env,call):
      p=call.arguments[0];v=env.get(p)-1;env.put(p,v);return v
    env.override(0x5469e8,decrement)
    return {'a':a}
 return setup

def dispatch(index=0,lower=-2,upper=2,own=True,grow=False):
 def setup(env):
    a=obj(env,0x480,'receiver',fill=0x45);log=obj(env,0x400,'callback log')
    fn=callback(env,'dispatch',log)
    for base,present in ((0x537980,own),(0x5349b8,True)):
      lo,hi=(lower,upper) if base==0x537980 else (-5,5)
      arr=obj(env,(hi-lo+1)*4,'dispatch array');env.put(base+4,0,lo,hi,arr,0,4,0,0x1234)
      for i in range(hi-lo+1):env.put(arr+i*4,fn if present else 0)
    env.put(0x544d18,0)
    return {'a':a}
 return setup

def basic_actor(env):
    a=obj(env,0x300,'actor');b=obj(env,0x180,'behavior');w=world_setup(env)
    env.put(a+0xc,w);env.put(a+0x6c,b);env.put(a+0x4c,100,200);env.put(a+0x118,0x80000000)
    env.put(0x534938+4,0,0,0)
    return a,b,w

def constructor(found=False,factor=1.):
 def setup(env):
    a,b,w=basic_actor(env);r=obj(env,0x480,'receiver',fill=0x91)
    anim=obj(env,0x30,'animation');frame=obj(env,0x40,'animation frame');frames=obj(env,4,'frame list',words=[frame]);env.put(anim+0xc,frames,1);env.put(frame+0x1c,79)
    names=['WALK','STRIKE1','FALL','HITLOW','HITHIGH','HOME','IDLE','LIFTED1','LIFTED2','FLIP1','FLIP2','FLIP3','THROWN','BLOCKHIGH','BLOCKLOW']
    entries=[('LEVEL_KATHERINE_'+n,anim) for n in names] if found else [('GAME_NULL',anim)]
    env.put(w+0x2c,cmap(env,entries))
    for p in (0x5262b0,0x5262b4,0x5262b8):putf(env,p,factor)
    return {'a':r,'actor':a}
 return setup

def factory(command):
 def setup(env):
    a,b,w=basic_actor(env);r=obj(env,0x480,'boss');vt=obj(env,0xc0,'boss vtable');log=obj(env,0x400,'callback log')
    env.put(r,vt);env.put(b+0x18,r,command)
    for off in (0x10,0x1c,0x20):env.put(vt+off,callback(env,str(off),log))
    return {'actor':a}
 return setup

def transition(timer=50,sound=0,stance=3,facing=1,eligible=1,state=0x525250,count=2,relative=1):
 def setup(env):
    actor,b,w=basic_actor(env);r=obj(env,0x480,'boss');p=obj(env,0x200,'player');pb=obj(env,0x40,'player behavior');ps=obj(env,0x40,'player state')
    env.put(0x537e88,p);env.put(p+0x6c,pb);env.put(pb+0x14,ps);env.put(ps,facing,eligible)
    env.put(p+0x4c,100+relative,200);env.put(r+0xc,actor,b);env.put(r+0x128,actor,actor);env.put(r+0x190,actor,actor)
    env.put(actor+8,0x10);env.put(r+0x2fc,32,0);env.put(r+0x184,stance);env.put(r+0x20,count);putd(env,r+0x68,100.0)
    sound1=obj(env,0x20,'block one',fill=0x43);sound2=obj(env,0x20,'block two',fill=0x87)
    env.put(w+0x28,cmap(env,[('LEVEL_KATHERINE_BLOCK1',sound1),('LEVEL_KATHERINE_BLOCK2',sound2)]))
    env.put(0x534eac,0x26b7);env.put(0x541334,0)
    env.override(0x4a3050,sequence(timer,sound))
    return {'a':r}
 return setup

def hit(text='OTHER',distance=0,high=0,grow=0):
 def setup(env):
    actor,b,w=basic_actor(env);r=obj(env,0x480,'boss');arg=obj(env,0x180,'attacker');p=obj(env,0x200,'player');pb=obj(env,0x40,'player behavior');ps=obj(env,0x40,'player state')
    log=obj(env,0x400,'virtual log');vt=obj(env,0xb0,'vtable')
    env.put(r,vt);env.put(r+0xc,actor,b);env.put(r+0x12c,actor);env.put(r+0x3c4,distance);env.put(r+0x18c,3)
    env.put(actor+0x38,0xffffffff);env.put(arg+0x138,0x80000000)
    env.put(0x537e88,p);env.put(p+0x6c,pb);env.put(pb+0x14,ps);env.put(ps+0x14,high)
    for off,n in ((0x9c,0),(0x28,1),(0x44,0)):env.put(vt+off,callback(env,str(off),log,n))
    header=obj(env,len(text)+13,'state name',words=[1,len(text),len(text)]);string=header+12;env.write(string,text.encode()+b'\0');arr=obj(env,4,'state strings',words=[string])
    env.put(0x537698+4,0,0,0,arr,0,4,0,0)
    env.put(b+0x1c,grow)
    env.put(0x532c0c,0);env.override(0x4a3050,returns(2))
    return {'a':r,'arg':arg}
 return setup

def factory_full(command=0):
 def setup(env):
    t=constructor(False,1.)(env);actor=t['actor'];b=env.get(actor+0x6c)
    if command==0:
      env.put(b+0x1c,0)
    else:
      t=hit()(env);r=t['a'];actor=env.get(r+0xc);b=env.get(r+0x10)
      env.put(b+0x18,r,command);vt=env.get(r);log=obj(env,0x400,'dispatch trace')
      for off in (4,8,12):env.put(vt+off,callback(env,str(off),log,1))
    return {'actor':actor}
 return setup

def cases(random_source):
    for m in (0,1,3):yield Case(f'spring mode {m}',0x41e810,spring(mode=m),arguments=(lambda t:t['a'],100))
    for cmd in (0x1c,0x138d,0x138c):yield Case(f'spring blocked {cmd}',0x41e810,spring(command=cmd),arguments=(lambda t:t['a'],100))
    yield Case('spring null board',0x41e810,spring(board=False),arguments=(lambda t:t['a'],100))
    for face,flag,level,h,acc in [(0,0,0x26bc,200,1000.),(1,1,0x26b7,200,1000.),(0,0,0x26b7,0,0.),(1,0,0x26b7,120,0.),(0,0,0x26bc,200,1e-15)]:
      yield Case(f'spring active {face} {flag} {level} {h} {acc}',0x41e810,spring(face=face,flag=flag,level=level,height=h,accel=acc),arguments=(lambda t:t['a'],h))
    for i in range(6):
      h=random_source.randrange(1,500);yield Case(f'spring random {i}',0x41e810,spring(x=random_source.randrange(-2000,2000),y=random_source.randrange(-2000,2000)),arguments=(lambda t:t['a'],h))
    for bits in (0,32,33,65):
      for refs in (0,1,2):
       yield Case(f'destructor {bits} {refs}',0x454310,destructor(bits,refs),receiver=lambda t:t['a'])
       for f in (0,1,0x100,0x102,0xff):yield Case(f'deleting destructor {bits} {refs} {f}',0x4542f0,destructor(bits,refs),receiver=lambda t:t['a'],arguments=(f,))
    for idx in (-3,-2,0,2,3):
      for own in (False,True):yield Case(f'dispatch {idx} {own}',0x4543e0,dispatch(idx,own=own),receiver=lambda t:t['a'],arguments=(idx,))
    for found in (False,True):
      for factor in (0.5,1.,4.):yield Case(f'constructor {found} {factor}',0x453df0,constructor(found,factor),receiver=lambda t:t['a'],arguments=(lambda t:t['actor'],))
    for command in (0x1d,0x1e,1000):yield Case(f'factory command {command}',0x453d30,factory(command),arguments=(lambda t:t['actor'],))

    for timer,sound,stance,facing,eligible,state,count,rel in [
      (50,0,3,1,1,0x525250,2,-1),(50,1,4,0,1,0x525250,2,1),
      (50,-1,3,1,0,0x525250,2,-1),(50,0,3,0,1,0x525250,2,-1),
      (50,0,3,1,1,0x525250,2,1),(50,0,2,1,1,0x525250,2,-1),
      (50,0,2,1,1,0x525250,2,1),(50,0,1,1,1,0x525250,2,-1),
      (50,0,3,1,1,0x527204,2,-1),(50,0,3,1,1,0x528454,2,-1),
      (50,0,3,1,1,0x52720c,2,-1),(-1,0,3,1,1,0x525250,2,-1),
      (200,0,3,1,1,0x525250,2,-1),(199,1,3,1,1,0x525250,1,-1),
      (0,0,3,1,1,0x525250,2,-1)]:
      yield Case(f'transition {timer} {sound} {stance} {facing} {eligible} {state} {count} {rel}',0x4547c0,transition(timer,sound,stance,facing,eligible,state,count,rel),receiver=lambda t:t['a'],arguments=(state,))
    for text in ('LS_HITLOW','LS_HITHIGH','OTHER'):
      for distance in (-1,0,499,500,599,600):
       for high in (0,1):yield Case(f'hit {text} {distance} {high}',0x4548c0,hit(text,distance,high),receiver=lambda t:t['a'],arguments=(lambda t:t['arg'],))
    for grow in (-2,2):yield Case(f'hit grow {grow}',0x4548c0,hit(grow=grow),receiver=lambda t:t['a'],arguments=(lambda t:t['arg'],))

    for cmd in (0,1,31,0xffffffff):yield Case(f'factory full {cmd}',0x453d30,factory_full(cmd),arguments=(lambda t:t['actor'],))
    def hit_twice(env):
      t=hit(grow=2)(env);b=env.get(t['a']+0x10)
      def move(env,call):
        new=reallocate()(env,call)
        if env.calls_so_far(call.function)==1:env.put(b+0x1c,4)
        return new
      env.override(0x4a9070,move)
      return t
    yield Case('hit reloaded index after growth',0x4548c0,hit_twice,receiver=lambda t:t['a'],arguments=(lambda t:t['arg'],))
