"""Private HumanEnemy harness derived from the project snapshot fixture shapes."""
import ctypes as C,random,struct,subprocess,argparse
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];scratch=ROOT/'work/human-enemy-agent'
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');opts=p.parse_args()
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/n)for n in ['HumanEnemy.cpp','OfficerLogic.cpp','GenericEnemyStates.cpp','GenericEnemy.cpp','PlayerPhysics.cpp','WorldObjectRuntime.cpp','CollisionResponse.cpp','TileCollision.cpp']],'-o',str(scratch/'libHumanEnemy.dylib')],check=True)
class Enemy(C.Structure):_fields_=[(n,C.c_uint32*k)for n,k in [('actor',128),('primary',93),('secondary',93),('contact',93),('enemy',264)]]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('name',C.c_char_p)]
class GenericContext(C.Structure):_fields_=[(x,C.c_uint32)for x in ['actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken']]+[(x,C.c_uint32*128)for x in ['playerActor','platformActor']]+[(x,C.c_uint32)for x in ['tick','animationDelta','levelWord','forcedRandom','hitMode']]+[('defaults',C.c_uint32*24),('virtualFunctions',C.c_uint32*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(C.c_uint32)),('bitWordCount',C.c_size_t),('emptyStringToken',C.c_uint32),('bitHandlerToken',C.c_uint32)]
class Resource(C.Structure):_fields_=[('token',C.c_uint32),('controllerToken',C.c_uint32)]
class Extra(C.Structure):_fields_=[('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128),('playerPrivate',C.c_uint32*78),('strikeCounter',C.c_uint32),('audioEnabled',C.c_uint32),('audioPosition',C.c_uint32),('resources',C.POINTER(Resource)),('resourceCount',C.c_size_t)]
class Context(C.Structure):_fields_=[('generic',GenericContext),('sharedStates',Extra),('privateTail',C.c_uint32*20)]+[(x,C.c_float)for x in ['damageScale','healthScale','rangeScale']]+[(x,C.c_uint32)for x in ['difficulty','sequenceRegistryToken','audioManagerToken','audioManagerAvailable','masterVolume']]+[('patrolStates',C.POINTER(State)),('patrolStateCount',C.c_size_t),('officerStates',C.POINTER(State)),('officerStateCount',C.c_size_t)]+[('effectToken',C.c_uint32),('effectActor',C.c_uint32*128),('effectPrimary',C.c_uint32*93),('effectPrivate',C.c_uint32*92),('otherActorToken',C.c_uint32),('otherActor',C.c_uint32*128),('otherPrimary',C.c_uint32*93),('platformPrimary',C.c_uint32*93),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*12),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint64,C.POINTER(Enemy),C.POINTER(GenericContext),C.POINTER(Call),C.c_void_p)
lib=C.CDLL(str(scratch/'libHumanEnemy.dylib'))
lib.claw_officer_context_defaults.argtypes=[C.POINTER(Context)]
lib.claw_officer_entry.argtypes=[C.POINTER(Enemy),C.POINTER(Context),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_officer_entry.restype=C.c_uint32
m=OriginalV10(opts.exe);u=m.u;u.mem_map(0,4096);m.executed.clear()
A,L,S,K,E,P,PL,SC,T,R=[0x1001000+i*0x1000 for i in range(10)]
SEQ,EF,EFL,EFE,OTHER,OTHERL,PLATFORM_L=[0x1020000+i*0x1000 for i in range(7)]
STRINGS,EMPTY,STRING_OBJECTS,FUNCTIONS,REGISTRY=0x1011000,0x1014000,0x1015000,0x1016000,0x1018000
VBASE=0x10fd000
names=[b'LS_HOME',b'LS_IDLE',b'LS_TEST'];functions=[0x463020,0x4631e0,0]
states=(State*4)(*[State(2000+i,f,STRINGS+64*i,n)for i,(n,f)in enumerate(zip(names,functions))],State(1000,0,EMPTY,b''))
officerStates=(State*4)(*[State(2000+i,f,STRINGS+64*i,n)for i,(n,f)in enumerate(zip(names,functions))],State(1000,0,EMPTY,b''))
virtuals=m.read_words(0x50ea0c,43)+[0]*21
sizes={'actor':128,'primary':93,'secondary':93,'contact':93,'enemy':264};addresses={'actor':A,'primary':L,'secondary':S,'contact':K,'enemy':E}
extraBuffers=[('effectActor',EF,128),('effectPrimary',EFL,93),('effectPrivate',EFE,92),('otherActor',OTHER,128),('otherPrimary',OTHERL,93),('platformPrimary',PLATFORM_L,93)]
rng=random.Random(462350);current=None;native=False;events=[];policy=0;random_results=[0];random_index=0;resource_mode=1;ground=False;world=None;humanBase=None;humanReference=True;humanReferenceCalls=0;humanExecuted=set();calls=event_count=0
humans={}
def snapshot():
 s=Enemy()
 for name in sizes:getattr(s,name)[:]=m.read_words(addresses[name],sizes[name])
 current.privateTail[:]=m.read_words(E+0x420,20);current.generic.playerActor[:]=m.read_words(P,128)
 for f,a,n in extraBuffers:getattr(current,f)[:]=m.read_words(a,n)
 return s
def write(s):
 for name in sizes:m.write_words(addresses[name],getattr(s,name))
 m.write_words(E+0x420,current.privateTail);m.write_words(P,current.generic.playerActor)
 for f,a,n in extraBuffers:m.write_words(a,getattr(current,f))
def serialized(s):return bytes(s)+bytes(current.privateTail)+bytes(current.generic.playerActor)+b''.join(bytes(getattr(current,f))for f,a,n in extraBuffers)
def text(a):return bytes(u.mem_read(a,128)).split(b'\0')[0]
def effects(s,event):
 global random_index
 f,receiver,args,name=event;result=0
 if f==0x44c000:
  if humanBase:
   updates,tailUpdates=humanBase
   words=(C.c_uint32*(C.sizeof(s)//4)).from_buffer(s)
   for index,value in updates:words[index]=value
   for index,value in tailUpdates:current.privateTail[index]=value
  else:
   s.enemy[3]=s.enemy[2]=s.enemy[0x128//4]=s.enemy[0x12c//4]=A;s.enemy[4]=s.enemy[0x130//4]=L
  result=E
 elif f==0x4a3050:result=random_results[random_index%len(random_results)]&0xffffffff;random_index+=1
 elif f==0x4dba00:result=2000+names.index(name)
 elif f==0x4f6286:
  if resource_mode==1 or(resource_mode==2 and name==b'GAME_NULL'):
   result=0x10a0000+(sum((i+1)*b for i,b in enumerate(name))%0x500)*4
 elif f==0x4c7970:s.actor[0x170//4]=0x10b0000 if resource_mode else 0
 elif f==0x4f63ec:result=E
 elif f==0x4c82a0:result=0x314
 elif f==0x4cbb60:
  s.actor[0x4c//4]=args[1];s.actor[0x50//4]=args[2];result=0
 elif f==0x4cda10:result=clear_path
 elif f==0x43eab0:result=ledge
 elif f==0x4cd800:
  if ground:
   v=Actor();fields={'flags':8,'x':0x4c,'y':0x50,'mode':0xcc,'type':0xd0,'stepX':0xdc,'stepY':0xe0,'supportToken':0x80,'deltaX':0x158,'deltaY':0x15c}
   for name,offset in fields.items():setattr(v,name,s.actor[offset//4])
   v.token=1;v.moveRect=Rect(*s.actor[0x118//4:0x128//4]);v.hitRect=Rect(*s.actor[0x128//4:0x138//4]);result=lib.claw_collision_place_on_ground(C.byref(world),C.byref(v))
   for name,offset in fields.items():s.actor[offset//4]=getattr(v,name)
  else:s.actor[0x50//4]=(s.actor[0x50//4]+3)&0xffffffff
 if policy:
  s.enemy[0x404//4]^=f;current.privateTail[3]^=f
  if f==0x44d000:
   current.generic.playerActor[0xcc//4]=5 if current.generic.playerActor[0xcc//4]!=5 else 1
   s.enemy[0x230//4]^=0x123;s.enemy[0x240//4]^=0xabc
  elif f==0x4c82a0:s.actor[0x190//4]^=0x12345678
  if policy==2 and f==0x44d000:s.primary[7]=2002
  elif f==0x4a3050:s.actor[0x38//4]^=0x10
 return result
@Dependency
def dependency(s,c,e,user):
 e=e.contents;event=(e.function,e.receiver,tuple(e.arguments[:e.argumentCount]),e.name);events.append((event,serialized(s.contents)));return effects(s.contents,event)
def returned(pop,result=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,result&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def host(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address in(0x10fb000,0x10fb010):
  n=1 if address==0x10fb000 else 5;vals=m.read_words(sp+4,n);m.write_words(vals[0],[0]*4 if n==1 else vals[1:]);returned(n*4,1);return
 if address==0x10fb020:
  rect,x,y=m.read_words(sp+4,3);left,top,right,bottom=[C.c_int32(v).value for v in m.read_words(rect,4)];x=C.c_int32(x).value;y=C.c_int32(y).value;returned(12,int(left<=x<right and top<=y<bottom));return
 if address in(0x4c7970,0x4c7fa0,0x4c8060):
  
  name=text(m.read_words(sp+4,1)[0]);event=(address,receiver,(),name);s=snapshot();events.append((event,serialized(s)));r=effects(s,event);write(s);returned(4,r);return
 if address in(0x4f6286,0x4dba00):
  n=2 if address==0x4f6286 else 1;args=m.read_words(sp+4,n);name=text(args[0]);event=(address,receiver,(),name);s=snapshot();events.append((event,serialized(s)));r=effects(s,event);write(s)
  if n==2:m.write_words(args[1],[r])
  returned(n*4,int(bool(r))if n==2 else r);return
 if humanReference and address==0x44c000:return
 config={**humans,0x4a3050:(0,0),0x4c8220:(1,4),0x4c82a0:(1,4),0x4cd800:(2,8),0x48ce40:(3,0),0x48ceb0:(3,0),0x4f63ec:(1,0),0x4f6428:(1,0),0x4f6584:(0,0)}
 config.update({0x4b45f0:(4,16),0x4208e0:(4,16),0x420370:(1,0),0x420a10:(2,8),0x42df90:(0,0),0x43eab0:(0,0),0x4cda10:(4,16),0x440420:(0,0),0x48cf50:(1,0),0x4a36f0:(1,0)})
 if VBASE<=address<VBASE+0x100:
  slot=(address-VBASE)*4;has=slot in(4,8,12,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x5c,0x90);config[address]=(int(has),4*int(has))
 if humanReference:
  config.update({0x4cbb60:(4,16),0x4dbe10:(2,8),0x4dbd60:(1,4),0x4f6439:(0,0)})
  if address==0x4f6439:m.write_words(receiver,[EMPTY]);returned(0,receiver);return
  if address==0x4dbe10:
   m.write_words(receiver,[0,0,32,0]);returned(8,receiver);return
  if address==0x4dbd60:
   source=m.read_words(sp+4,1)[0];m.write_words(receiver+8,m.read_words(source+8,2));returned(4,receiver);return
 if address not in config:return
 n,pop=config[address];args=tuple(m.read_words(sp+4,n));receiver=0 if address in(0x4a3050,0x48ce40,0x48ceb0,0x4f63ec,0x4f6428,0x420370,0x48cf50,0x4a36f0)else receiver
 name=b'LEVEL_OFFICER_00340024'if address==0x48ceb0 else None;event=(address,receiver,args,name);s=snapshot();events.append((event,serialized(s)))
 if address==0x4cd800 and ground:return
 r=effects(s,event);write(s);returned(pop,r)
u.hook_add(UC_HOOK_CODE,host)
def fresh():
 s=Enemy();c=Context();lib.claw_officer_context_defaults(C.byref(c));g=c.generic
 for name,k in sizes.items():getattr(s,name)[:]=[rng.getrandbits(32)for _ in range(k)]
 for f,a,n in extraBuffers:getattr(c,f)[:]=[rng.getrandbits(32)for _ in range(n)]
 c.privateTail[:]=[rng.getrandbits(32)for _ in range(20)];g.playerActor[:]=[rng.getrandbits(32)for _ in range(128)]
 g.actorToken,g.primaryToken,g.secondaryToken,g.contactToken,g.enemyToken=A,L,S,K,E;g.sceneToken,g.tileManagerToken,g.soundRegistryToken,g.playerToken=SC,T,R,P;g.tick=rng.randrange(0,10000);g.animationDelta=rng.randrange(40);g.emptyStringToken=EMPTY;g.states=states;g.stateCount=len(states)
 c.officerStates=officerStates;c.officerStateCount=len(officerStates);c.sequenceRegistryToken=SEQ;c.effectToken=EF;c.otherActorToken=OTHER
 s.actor[0xc//4]=SC;s.actor[0x6c//4]=L;s.actor[0x70//4]=S;s.actor[0x78//4]=K;s.actor[0x80//4]=PL;s.actor[0x38//4]=rng.choice([0,0xffffffff]);s.actor[0x40//4]=rng.choice([0,2,8,10]);s.actor[0x50//4]=rng.randrange(-500,500)&0xffffffff
 for off in(0x118,0x128,0x138):
  if rng.randrange(3)==0:s.actor[off//4]=0x80000000
 s.enemy[0x2fc//4]=32;s.enemy[0x300//4]=0;s.enemy[0x1a4//4]=s.enemy[0x1a8//4]=EMPTY;s.enemy[0]=0x50e12c;s.enemy[2]=s.enemy[3]=s.enemy[0x128//4]=s.enemy[0x12c//4]=A;s.enemy[4]=s.enemy[0x130//4]=L;s.primary[0x18//4]=E;s.primary[7]=2000+rng.randrange(3);s.enemy[0x184//4]=rng.randrange(-1,9)&0xffffffff;s.enemy[0x18c//4]=rng.choice([0,2,3]);g.playerActor[0xcc//4]=rng.choice([1,5]);s.enemy[7]=2000
 for off in(0x458,0x468):c.privateTail[(off-0x420)//4]=rng.choice([0,g.tick,max(0,g.tick-4000),0xfffffffe])
 for off in(0x45c,0x46c):c.privateTail[(off-0x420)//4]=rng.choice([0,999,1000,4000,0xffffffff])
 # Virtual sentinels test real Officer caller timing without pretending Human bodies recovered.
 for slot in(0x44,0x58,0x20):g.virtualFunctions[slot//4]=VBASE+slot//4
 return s,c
def install(s,c):
 global current
 current=c;write(s);m.write_words(0,[0x12345678]);m.write_words(0x546cdc,[0x10fb000]);m.write_words(0x546d5c,[0x10fb010]);m.write_words(0x537e88,[P]);m.write_words(0x537210,[c.generic.tick]);m.write_words(0x5430c4,[c.generic.animationDelta]);m.write_words(0x537964,[c.difficulty]);u.mem_write(0x5262b0,struct.pack('<3f',c.damageScale,c.healthScale,c.rangeScale));m.write_words(SC+0x28,[R-0x10]);m.write_words(SC+0x2c,[SEQ-0x10]);m.write_words(SC+0x14,[R-0x10]);m.write_words(SC+0x24,[T]);m.write_words(0x50e12c,c.generic.virtualFunctions[:43]);m.write_words(0x50ea0c,c.generic.virtualFunctions[:43]);m.write_words(0x513e10,c.generic.defaults);m.write_words(0x52e1cc,[EMPTY]);m.write_words(EMPTY-12,[1,0,0]);u.mem_write(EMPTY,b'\0');m.write_words(0x533470,[32]);u.mem_write(0x534938,b'\0')
 m.write_words(0x537ba0+8,[1000,2002,REGISTRY,0,4,0,0,0]);m.write_words(REGISTRY,[0]*1000+functions)
 m.write_words(0x537638+8,[1000,2002,FUNCTIONS,0,4,0,0,0]);m.write_words(FUNCTIONS,[0]*1000+[0]*3)
 m.write_words(0x537698+8,[1000,2002,STRING_OBJECTS,0,4,0,0,0]);m.write_words(STRING_OBJECTS,[EMPTY]*1000)
 for i,name in enumerate(names):
  token=STRINGS+64*i;m.write_words(STRING_OBJECTS+4*(1000+i),[token]);m.write_words(token-12,[1,len(name),len(name)]);u.mem_write(token,name+b'\0')
def officer_reference_compare_unused(s,c,entry,label,arg=0):
 global current,native,random_index,calls,event_count
 before=bytes(s);before_c=bytes(c);current=c;native=True;events.clear();random_index=0;result=C.c_uint32()
 rr=lib.claw_officer_entry(C.byref(s),C.byref(c),entry,arg,dependency,None,C.byref(result));assert rr and not c.fault,(label,'native scope',c.fault)
 expected=serialized(s);expected_events=list(events)
 old=Enemy.from_buffer_copy(before);old_c=Context.from_buffer_copy(before_c);install(old,old_c);native=False;events.clear();random_index=0
 args=struct.pack('<I',A)if entry in(0x462410,0x462350)else struct.pack('<I',arg)if entry in(0x462af0,0x462ef0,0x462a00)else b''
 try:ret=m.call(entry,E,args)
 except Exception:print('original fault',label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for i,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',i,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 assert m.read_words(0,1)==[0x12345678],(label,'SEH')
 if entry not in(0x405000,0x462ef0,0x462af0,0x462a20):assert ret==result.value,(label,'EAX',ret,result.value)
 if events!=expected_events:
  print(label,'original',[(e,len(b))for e,b in events]);print('native',[(e,len(b))for e,b in expected_events]);
  for j,(x,y)in enumerate(zip(events,expected_events)):
   if x!=y:print('event mismatch',j,x[0],y[0],'snapshot equal',x[1]==y[1]);break
  raise AssertionError((label,'full ordered events'))
 calls+=1;event_count+=len(events);current=c;return s,c

# Reuse frozen world/WWD test fixture shapes, not reference gameplay implementations.
class Rect(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('left','top','right','bottom')]
class Actor(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('flags','x','y','mode','type','stepX','stepY','supportToken','token','deltaX','deltaY')]+[('moveRect',Rect),('hitRect',Rect)]
class Description(C.Structure):
    _fields_=[(n,C.c_uint32)for n in ('type','width','height','insideAttribute','outsideAttribute')]+[(n,C.c_int32)for n in ('left','top','right','bottom')]
class World(C.Structure):
    _fields_=[('cells',C.POINTER(C.c_uint32)),('rowOffsets',C.POINTER(C.c_uint32)),('width',C.c_int32),('height',C.c_int32),('shiftX',C.c_uint32),('shiftY',C.c_uint32),('descriptions',C.POINTER(Description)),('descriptionCount',C.c_uint32),('actors',C.POINTER(Actor)),('actorCount',C.c_uint32),('maximumStepX',C.c_uint32),('maximumStepY',C.c_uint32)]
def install_world(levelOne=False):
    import zlib
    columns,rows=16,12
    cells=[0]*(columns*rows)
    for x in range(columns):cells[8*columns+x]=1
    for x in (8,9):cells[8*columns+x]=0
    for y in range(3,8):cells[y*columns+4]=3
    cells[8*columns+2]=4
    descriptions=[Description(1,64,64,i,0,0,0,0,0)for i in range(5)]
    if levelOne:
        raw=(ROOT/'Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD').read_bytes()
        offset=struct.unpack_from('<I',raw,736)[0]
        if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
        for i in range(struct.unpack_from('<I',raw,732)[0]):
            ph=struct.unpack_from('<40I',raw,offset+160*i)
            if ph[2]&1:
                columns,rows=ph[24:26];assert ph[22:24]==(64,64)
                cells=list(struct.unpack_from('<'+'I'*(columns*rows),raw,ph[33]));break
        descOffset=struct.unpack_from('<I',raw,740)[0];count=struct.unpack_from('<I',raw,descOffset+8)[0];pos=descOffset+32
        descriptions=[]
        for _ in range(count):
            kind,unknown,width,height=struct.unpack_from('<4I',raw,pos)
            if kind==1:
                descriptions.append(Description(kind,width,height,struct.unpack_from('<I',raw,pos+16)[0],0,0,0,0,0));pos+=20
            else:
                assert kind==2
                outside,inside=struct.unpack_from('<2I',raw,pos+16)
                descriptions.append(Description(kind,width,height,inside,outside,*struct.unpack_from('<4i',raw,pos+24)));pos+=40
    offsets=[x*columns for x in range(rows)]
    owner,actorList,plane,descPtrs,descData,cellData,rowData=0x1090000,0x1092000,0x1091000,0x1081000,0x1070000,0x1040000,0x1080000
    m.write_words(T+0xc,[owner]);m.write_words(owner+8,[actorList]);m.write_words(actorList+0x14,[0])
    m.write_words(T+0x4c,[descPtrs]);m.write_words(T+0x5c,[plane]);m.write_words(T+0x64,[64,64])
    m.write_words(plane+0x20,[cellData,rowData]);m.write_words(plane+0x30,[columns*64,rows*64]);m.write_words(plane+0x8c,[6,6])
    m.write_words(cellData,cells);m.write_words(rowData,offsets)
    for i,d in enumerate(descriptions):m.write_words(descData+i*0x40,[0x513980 if d.type==1 else 0x5139c8,d.width,d.height,d.insideAttribute if d.type==1 else d.outsideAttribute,d.insideAttribute,d.left,d.top,d.right,d.bottom])
    m.write_words(descPtrs,[descData+i*0x40 for i in range(len(descriptions))])
    cs,rs,ds=(C.c_uint32*len(cells))(*cells),(C.c_uint32*len(offsets))(*offsets),(Description*len(descriptions))(*descriptions)
    world=World(cs,rs,columns*64,rows*64,6,6,ds,len(descriptions),None,0,64,64);world.storage=(cs,rs,ds)
    return world
class ObjectRuntime(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class ObjectContext(C.Structure):_fields_=[(n,C.c_uint32)for n in ('sceneToken','actorToken','logicToken','sceneDefaultType')]+[(n,C.c_int32)for n in ('worldWidth','worldHeight')]+[('registryToken',C.c_uint32),('layerTokens',C.c_uint32*3)]+[(n,C.c_uint32)for n in ('entryToken','entryCallback','entryFlags')]
class ObjectCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('text',C.c_char_p)]
class ObjectInfo(C.Structure):_fields_=[('consumed',C.c_uint32),('created',C.c_uint32)]
def initialize_record(s,data):
 runtime=ObjectRuntime();runtime.actor[:]=s.actor;runtime.logic[:]=s.primary
 c=ObjectContext();c.sceneToken=SC;c.actorToken=A;c.logicToken=L;c.sceneDefaultType=2;c.worldWidth=world.width;c.worldHeight=world.height;c.registryToken=R
 info=ObjectInfo();buf=(C.c_uint8*len(data)).from_buffer_copy(data)
 assert lib.claw_world_object_load(buf,len(data),C.byref(runtime),C.byref(c),object_dependency,None,C.byref(info))==len(data) and info.created==1 and info.consumed==len(data)
 s.actor[:]=runtime.actor;s.primary[:]=runtime.logic

lib.claw_collision_place_on_ground.argtypes=[C.POINTER(World),C.POINTER(Actor)];lib.claw_collision_place_on_ground.restype=C.c_uint32
ObjectDependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(ObjectRuntime),C.POINTER(ObjectContext),C.POINTER(ObjectCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(ObjectRuntime),C.POINTER(ObjectContext),ObjectDependency,C.c_void_p,C.POINTER(ObjectInfo)];lib.claw_world_object_load.restype=C.c_uint32
@ObjectDependency
def object_dependency(s,c,e,user):
 if e.contents.function==0x4f6286:
  c.contents.entryToken=0x10ff100;c.contents.entryCallback=0x462350;c.contents.entryFlags=0;return 0x10ff100
 return 0

# Human-owned ABI view and exact registration family; IDs are test adapters,
# while function/name literal identities are original executable metadata.
humanRegistrations=[(b'LS_BOUNCE',0x44dd30,0x5240e8),(b'LS_THROWN',0x44de50,0x5271cc),(b'LS_JUMPATCLAW',0x44e510,0x527dac),(b'LS_JUMPBACK',0x44ea10,0x527da0),(b'LS_ADVANCE',0x44ea60,0x527d94),(b'LS_FASTADVANCE',0x44ec80,0x527d84),(b'LS_PACING',0x44ef70,0x527d78),(b'LS_IDLE',0x44f290,0x523148),(b'LS_HITLOW',0x44f490,0x523204),(b'LS_HITHIGH',0x44f660,0x523210),(b'LS_HOME',0x44da20,0x5234ec),(b'LS_JUMPOFFSPRINGBOARD',0x44f800,0x527d60)]
names=[x[0]for x in humanRegistrations]+[b'LS_DEAD',b'LS_PAUSE',b'LS_TEST']
functions=[x[1]for x in humanRegistrations]+[0,0,0]
states=(State*len(names))(*[State(2000+n,f,STRINGS+64*n,name)for n,(name,f)in enumerate(zip(names,functions))])
humanStates=(State*len(names))(*[State(2000+n,f,STRINGS+64*n,name)for n,(name,f)in enumerate(zip(names,functions))])
resourceViews=(Resource*16)(*[Resource(0x10a4000+n*0x80,0x10a6000+n*0x80)for n in range(16)])
class HumanContext(C.Structure):
 _fields_=[('generic',C.POINTER(GenericContext)),('sharedStates',C.POINTER(Extra)),('privateTail',C.POINTER(C.c_uint32))]+[(x,C.c_float)for x in('damageScale','healthScale','rangeScale')]+[(x,C.c_uint32)for x in('sequenceRegistryToken','clockCountdown')]+[('humanStates',C.POINTER(State)),('humanStateCount',C.c_size_t),('effectToken',C.c_uint32)]+[(x,C.POINTER(C.c_uint32))for x in('effectActor','effectPrimary','effectPrivate')]+[('otherActorToken',C.c_uint32)]+[(x,C.POINTER(C.c_uint32))for x in('otherActor','otherPrimary','platformPrimary')]+[('fault',C.c_uint32)]
lib.claw_human_enemy_entry.argtypes=[C.POINTER(Enemy),C.POINTER(HumanContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
clear_path=ledge=0
originalFresh=fresh;originalInstall=install
def human_view(c):
 x=HumanContext();x.generic=C.pointer(c.generic);x.sharedStates=C.pointer(c.sharedStates);x.privateTail=c.privateTail
 x.damageScale=c.damageScale;x.healthScale=c.healthScale;x.rangeScale=c.rangeScale;x.sequenceRegistryToken=c.sequenceRegistryToken;x.clockCountdown=c.generic.forcedRandom;x.humanStates=humanStates;x.humanStateCount=len(humanStates);x.effectToken=c.effectToken
 for f in('effectActor','effectPrimary','effectPrivate','otherActor','otherPrimary','platformPrimary'):setattr(x,f,getattr(c,f))
 x.otherActorToken=c.otherActorToken;return x
def fresh():
 s,c=originalFresh();g=c.generic
 for slot in range(64):g.virtualFunctions[slot]=VBASE+slot
 s.enemy[0]=0x50e12c;g.states=states;g.stateCount=len(states);s.primary[7]=2000+rng.randrange(len(names));s.enemy[9]=2000+rng.randrange(len(names));s.enemy[0x184//4]=rng.randrange(-1,9)&0xffffffff
 for off in range(0x28,0x118,8):s.enemy[off//4:off//4+2]=struct.unpack('<2I',struct.pack('<d',rng.choice([-150.0,-25.0,0.0,25.0,150.0])))
 for off in(0x80,0x88,0x90):s.enemy[off//4:off//4+2]=g.defaults[:2]
 for off in(0x98,0xa0,0xa8,0x100,0x108,0x110):s.enemy[off//4:off//4+2]=g.defaults[2:4]
 s.enemy[0x2fc//4]=32;s.enemy[0x300//4]=rng.getrandbits(10)|2;s.enemy[0x3cc//4]=1000;s.enemy[0x3c8//4]=g.tick
 s.enemy[0x194//4]=OTHER;s.enemy[0x190//4]=A;s.enemy[0x198//4]=L;s.enemy[0x3d4//4]=0;s.enemy[0x19c//4]=0;s.enemy[5]=s.enemy[6]=0
 s.actor[0x10c//4]=20;s.actor[0x74//4]=OTHER;s.actor[0xcc//4]=rng.choice([1,7,8]);s.actor[2]=rng.randrange(256);s.actor[0x40//4]=rng.choice([0,2,8,10]);s.actor[0x4c//4]=rng.randrange(512);s.actor[0x50//4]=rng.randrange(512)
 g.playerActor[0x4c//4]=rng.randrange(512);g.playerActor[0x50//4]=rng.randrange(512);g.playerActor[0x6c//4]=0x1038000
 for o in(0x148,0x14c):s.actor[o//4]=rng.randrange(-100,101)&0xffffffff
 for o in(0x2c,0x30,0x34,0x38):s.primary[o//4]=rng.choice([0,-400,400])&0xffffffff
 c.otherActor[0x6c//4]=OTHERL;c.otherActor[0xd0//4]=0;c.sharedStates.attackerToken=OTHER;c.sharedStates.attackerActor[:]=c.otherActor;c.sharedStates.audioEnabled=0;c.sharedStates.audioPosition=50;c.sharedStates.resources=resourceViews;c.sharedStates.resourceCount=len(resourceViews)
 c.generic.platformActor[0x6c//4]=PLATFORM_L;c.platformPrimary[7]=rng.choice([5,1111,0]);c.effectActor[0x1a4//4]=rng.choice([0,1]);c.effectActor[0x19c//4]=rng.choice([0,1]);c.privateTail[(0x44c-0x420)//4]=rng.choice([0,EF]);g.forcedRandom=rng.choice([0,1])
 return s,c
def install(s,c):
 originalInstall(s,c);m.write_words(0x546cd4,[0x10fb020]);m.write_words(0x50e12c,c.generic.virtualFunctions[:43]);m.write_words(0x50b16c,c.generic.virtualFunctions[:43]);m.write_words(PL,c.generic.platformActor)
 m.write_words(0x541334,[c.generic.forcedRandom]);m.write_words(0x534eac,[c.generic.levelWord]);m.write_words(0x532c0c,[c.sharedStates.audioEnabled]);m.write_words(0x532c10,[c.sharedStates.audioPosition]);m.write_words(0x1038000+0x14,[0x1039000]);m.write_words(0x1039000,c.sharedStates.playerPrivate)
 m.write_words(0x537878+8,[1000,2000+len(names)-1,0x10b1000,0,4,0,0,0]);m.write_words(0x10b1000,[0]*1000+functions)
 m.write_words(0x537698+8,[1000,2000+len(names)-1,STRING_OBJECTS,0,4,0,0,0]);m.write_words(STRING_OBJECTS,[EMPTY]*1000)
 for n,name in enumerate(names):
  token=STRINGS+n*64;m.write_words(STRING_OBJECTS+4*(1000+n),[token]);m.write_words(token-12,[1,len(name),len(name)]);u.mem_write(token,name+b'\0')
 m.write_words(0x537638+8,[1000,2000+len(names)-1,FUNCTIONS,0,4,0,0,0]);m.write_words(FUNCTIONS,[0]*(1000+len(names)))
 for resource in resourceViews:m.write_words(resource.token+0x10,[resource.controllerToken])
def compare(s,c,entry,label,arg=0):
 global current,native,random_index,calls,event_count
 before=bytes(s);before_c=bytes(c);current=c;native=True;events.clear();random_index=0;result=C.c_uint32();view=human_view(c)
 support=lib.claw_human_enemy_entry(C.byref(s),C.byref(view),entry,arg,dependency,None,C.byref(result));assert support and not view.fault,(label,'native scope',view.fault)
 expected=serialized(s);expectedEvents=list(events)
 old=Enemy.from_buffer_copy(before);old_c=Context.from_buffer_copy(before_c);install(old,old_c);native=False;events.clear();random_index=0
 args=struct.pack('<I',A)if entry in(0x44c000,0x44bc60)else struct.pack('<I',arg)if entry in(0x44c840,0x44d000,0x44e0c0,0x44d760)else b''
 try:ret=m.call(entry,E,args)
 except Exception:print('original fault',label,hex(u.reg_read(UC_X86_REG_EIP)),m.read_words(u.reg_read(UC_X86_REG_ESP),8));raise
 actual=serialized(snapshot())
 if actual!=expected:
  for n,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',n,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 if entry not in(0x44c840,0x44d000,0x44d3c0,0x44cfd0,0x44d760):assert ret==result.value,(label,'EAX',ret,result.value)
 if events!=expectedEvents:
  print(label,'original',[(e,len(b))for e,b in events]);print('native',[(e,len(b))for e,b in expectedEvents]);
  for n,(a,b)in enumerate(zip(events,expectedEvents)):
   if a!=b:print('first mismatch',n,a[0],b[0],'same snapshot',a[1]==b[1]);break
  raise AssertionError((label,'full ordered events'))
 calls+=1;event_count+=len(events);current=c;return s,c
