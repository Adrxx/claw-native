"""Independent original raw-object lifecycle cases."""
from clawparity.cases import Case
RAW,GENERIC,NOOP=0x4c7930,0x4d6590,0x4ce9b0

def setup_for(seed,op,null_file=False,null_logic=False,peer=False,lookup='zero',change='keep',provider=1,size=0,io_result=1,fail_name=0):
 def setup(e):
  alloc=lambda n,name:e.object(n,name,fill=0)
  raw=alloc(0x200,'raw');logic=alloc(0x180,'logic');new=alloc(0x180,'replacement');other=alloc(0x200,'peer')
  scene=alloc(0x40,'scene');collection=alloc(0x90,'collection');registry=alloc(0x50,'registry');table=alloc(68,'hash buckets');node=alloc(12,'association')
  file=alloc(4,'native stream');vt=alloc(0x40,'stream methods');delegate=alloc(4,'native serializer');dvt=alloc(8,'serializer methods');trace=alloc(0x10000,'observations')
  string=alloc(16,'CString empty backing');e.put(string,1,0,0);e.put(raw+0xdc,string+12)
  wanted=(seed&0xfffffff0)|7
  e.put(scene+8,collection);e.put(scene+0x14,registry);e.put(registry+0x18,17);e.put(collection+0x4c,table);e.put(collection+0x50,17)
  if lookup in ('hit','chain-miss'):
   e.put(table+((wanted>>4)%17)*4,node);e.put(node,0,wanted if lookup=='hit' else wanted+1,other)
  e.put(other+0x188,seed^0x57a1)
  for owner in (logic,new):
   for off in range(0x20,0xcc,4):e.put(owner+off,seed^off^0x81a2)
   e.put(owner+0xc,scene);e.put(owner+0x1c,seed);e.put(owner+0x170,other if peer else 0);e.put(owner+0x174,wanted if lookup!='zero' else 0);e.put(owner+0x178,size)
   if size:e.put(owner+0x14,e.object(size,'private state',fill=seed&255))
   e.put(owner+0x18,delegate if provider else 0)
  for off in range(0x20,0xcc,4):e.put(raw+off,seed^off)
  e.put(raw+0xc,scene);e.put(raw+0x7c,0 if null_logic else logic);e.put(raw+0x80,0);e.put(raw+0x88,0);e.put(raw+0x90,0);e.put(raw+0x98,other if peer else 0);e.put(raw+0x184,wanted if lookup!='zero' else 0)
  def record(env,tag,c):
   n=env.get(trace);at=trace+0x10+n*0x28;env.put(at,tag,c.receiver,*c.arguments[:4]);active=env.get(raw+0x7c)
   env.put(at+0x18,active,env.get(active+0x1c) if active else 0,env.get(raw+0x184),env.get(raw+0x98));env.put(trace,n+1)
  def io(env,c,reading):
   ptr,n=c.arguments;record(env,0x100+reading,c)
   if reading:
    if n==128:
     seq=env.get(trace+4)+1;env.put(trace+4,seq);payload=b'absent\0' if fail_name and seq==fail_name+1 else b'\0';env.write(ptr,payload+b'\0'*(n-len(payload)))
    elif ptr in (logic+0x178,new+0x178):env.put(ptr,size)
    elif ptr in (logic+0x174,new+0x174):env.put(ptr,0)
    else:env.write(ptr,bytes(((seed+i)&255 for i in range(n))))
   return io_result
  def callback(env,c):
   record(env,0x50,c);active=env.get(raw+0x7c);event=env.get(active+0x1c)
   if change=='event':env.put(active+0x1c,seed^0xbfab)
   elif change.startswith('replace'):
    env.put(new+0x1c,event if change=='replace-same' else seed^0xcefa);env.put(raw+0x7c,new)
   return seed^0x7733
  def delegated(env,c):record(env,0x200,c);return 0 if provider==2 else provider
  e.put(file,vt);e.put(vt+0x2c,e.stub('native stream read','thiscall',2,lambda env,c:io(env,c,1)));e.put(vt+0x30,e.stub('native stream write','thiscall',2,lambda env,c:io(env,c,0)))
  e.put(delegate,dvt);e.put(dvt+4,e.stub('native delegated serializer','thiscall',4,delegated));fn=e.stub('registered lifecycle callback','cdecl',1,callback);e.put(logic+0x10,fn);e.put(new+0x10,fn)
  e.override(0x50c318,lambda env,c:len(env.cstr(c.arguments[0])))
  return dict(raw=raw,logic=logic,file=0 if null_file else file)
 return setup

def case(label,entry,seed,op,**opts):
 return Case(label,entry,setup_for(seed,op,**opts),receiver=lambda t:t['raw' if entry==RAW else 'logic'],arguments=(lambda t:t['file'],op,seed^0x1122,seed^0x3344))

def cases(random_source):
 # Choose scalar contents independently from structural coverage dimensions.
 # The high bits keep saved/changed events distinct from all lifecycle ids.
 seed=lambda:random_source.getrandbits(32)|0x80010000
 for entry in (RAW,GENERIC):
  for op in (0,3,4,5,6,7,8,9,0xffffffff):
   yield case(f'{entry:x} operation{op:x}',entry,seed(),op)
 for op in (0,3,4,7,8):
  for provider in (0,2):
   yield case(f'generic operation{op} provider{provider}',GENERIC,seed(),op,provider=provider)
 yield case('raw normalizes failed delegation',RAW,seed(),0,provider=2)
 for op in (3,4,7,8):
  for change in ('keep','event','replace-same','replace-new'):
   yield case(f'raw callback operation{op} {change}',RAW,seed(),op,change=change,peer=True)
 for entry in (RAW,GENERIC):
  for lookup in ('zero','miss','chain-miss','hit'):
   yield case(f'lookup {entry:x} {lookup}',entry,seed(),8,lookup=lookup,peer=True)
 yield case('generic snapshots present peer id',GENERIC,seed(),3,peer=True)
 for entry in (RAW,GENERIC):
  yield case(f'clear stale peer id with absent peer {entry:x}',entry,seed(),3,lookup='miss')
 for entry in (RAW,GENERIC):
  for op in (3,4,7,8):
   yield case(f'null file {entry:x} {op}',entry,seed(),op,null_file=True)
 for op in (3,4,7,8):
  yield case(f'null logic operation{op}',RAW,seed(),op,null_logic=True)
 for name in (1,2,3):
  yield case(f'input missing binding {name}',RAW,seed(),7,fail_name=name)
 for entry in (RAW,GENERIC):
  for op in (4,7):
   for size,result in ((0,0),(4,0),(13,0xffffffff)):
    yield case(f'ignored IO result {entry:x} {op} {size} {result:x}',entry,seed(),op,size=size,io_result=result)
 yield Case('installed lifecycle no-op',NOOP,lambda e:dict(logic=e.object(32,'receiver',fill=0x8b)),receiver=lambda t:t['logic'])
