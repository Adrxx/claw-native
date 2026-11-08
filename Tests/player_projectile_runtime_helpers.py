"""Owned raw-heap weapon projectile oracle and explicit transport profile."""
import ctypes as C,struct,subprocess,hashlib,random,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-projectile-agent';U=C.c_uint32
sources=list((ROOT/'Sources').glob('*.cpp'))+[WORK/'fire-chain.cpp']
if not (WORK/'libPlayerProjectile.dylib').exists()or any(p.stat().st_mtime>(WORK/'libPlayerProjectile.dylib').stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libPlayerProjectile.dylib')],check=True)
lib=C.CDLL(str(WORK/'libPlayerProjectile.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',U),('nameToken',U),('name',C.c_char_p)]
class Generic(C.Structure):_fields_=[(n,U)for n in('actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken')]+[('playerActor',U*128),('platformActor',U*128)]+[(n,U)for n in('tick','animationDelta','levelWord','forcedRandom','hitMode')]+[('defaults',U*24),('virtualFunctions',U*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(U)),('bitWordCount',C.c_size_t),('emptyStringToken',U),('bitHandlerToken',U)]
class Bullet(C.Structure):_fields_=[('generic',C.POINTER(Generic)),('states',C.POINTER(State)),('stateCount',C.c_size_t),('scene',Host),('imageRegistryToken',U),('imageRootToken',U),('imageRootHeader',U*28),('imageFrames',C.POINTER(U)),('imageFrameOrigin',C.c_int32),('imageFrameCount',C.c_size_t),('imageLeafToken',U),('imageLeafHeader',U*10),('fault',U)]
class Globals(C.Structure):_fields_=[(n,U)for n in('tick','animationDelta','magicDisabled','ownerToken','audioEnabled','masterVolume')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('bullet',C.POINTER(Bullet)),('composeAnimation',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
A,L,E,SC,WORLD,PLANE,CELLS,ROWS,DESC,ROOTIMAGE,LEAF,FRAME,SEQ,SOUND,POOL,OWNER,FX,FXL,FLARE=[BASE+0x1000+i*0x1000 for i in range(19)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();generic=Generic();b=Bullet();c=Context();b.generic=C.pointer(generic);c.globals=C.pointer(g);c.bullet=C.pointer(b)
lib.claw_player_projectile_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)];lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(Generic)]
rng=random.Random(0x410900);animationResult=0;resource=1;allocation=1;collision=0;mode=8;mutation=0;randomWords=[];randomIndex=0;native_events=[];original_events=[];errors=[];calls=eventsCount=0
names=[('LS_IDLE',0x523148),('LS_FALLING',0x5236fc),('LS_EXPLODING',0x524418),('LS_STRIKE',0x52720c),('LS_DEAD',0x5234f4),('LS_JUMP',0x527204),('LS_MOVINGLEFT',0x5271f4),('LS_MOVINGRIGHT',0x5271e4),('LS_BOUNCE',0x5240b4),('LS_LIFTED',0x5271d8),('LS_THROWN',0x5271cc)]
states=(State*len(names))(*[State(2000+i,0,token,text.encode())for i,(text,token)in enumerate(names)]);generic.states=states;generic.stateCount=len(states);fall=(State*len(names))(*[State(2000+i,0x4742f0 if i==1 else 0,token,text.encode())for i,(text,token)in enumerate(names)]);b.states=fall;b.stateCount=len(fall)
TABLES=[0x538428,0x534ab0,0x534910,0x5375d8,0x537698];BACKS=[BASE+0x20000+i*0x1000 for i in range(5)]
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def pointer(t,n=1):
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 raw=pack(*v)
 if native:C.memmove(pointer(t,len(v)),raw,len(raw))
 else:m.u.mem_write(t,raw)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(pointer(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def dbl(t,v,native=True):
 raw=struct.pack('<d',v)
 if native:C.memmove(pointer(t,2),raw,8)
 else:m.u.mem_write(t,raw)
def updates():return {0x537210:g.tick,0x5430c4:g.animationDelta,0x53724c:g.magicDisabled,0x5371fc:g.ownerToken,0x532c0c:g.audioEnabled,0x532c10:g.masterVolume}
def flush_globals():
 for t,v in updates().items():put(t,[v])
def raw(native):
 if native:flush_globals();return bytes(heap)+C.string_at(pointer(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snapshot(native):return hashlib.sha256(raw(native)).digest()
@Lookup
def lookup(_,t,n):
 p=pointer(t,n)if not t%4 else 0
 if not p:errors.append(("lookup",hex(t),n))
 return p
c.scene=Host(None,lookup,Alloc(),Free(),Invoke(),Clock())
def cname(t):
 data=C.string_at(pointer(t),100)if imageStart<=t<=imageEnd else C.string_at(pointer(t),100)
 return data.split(b'\0')[0]
def effect(fn,t,args,name,native):
 global randomIndex
 if fn in(0x4c7fa0,0x4c8060):return 1
 if fn==0x4cbb60:
  put(args[0]+76,args[1:3],native);put(args[0]+204,[7 if get(args[0]+204,native=native)[0]==7 else mode],native);return collision
 if fn==0x4f6286:return (SEQ if t==SC+0x310 else ROOTIMAGE)if resource else 0
 if fn==0x4061b0:return SOUND if resource else 0
 if fn==0x4c8220:
  if mutation:put(t+8,[args[0]],native)
  return 0
 if fn==0x4c82a0:
  if mutation:put(A+420,[1],native);put(A+412,[0],native)
  return animationResult
 if fn==0x4dba00:return dict((n.encode(),2000+i)for i,(n,_)in enumerate(names))[name]
 if fn==0x4c8da0:
  if not allocation:return 0
  child=FLARE if name==b'Flare'else FX
  put(child+76,args[1:3],native);put(child+100,[args[3]],native);put(child+108,[FXL],native);return child
 if fn==0x4a3050:
  value=randomWords[randomIndex%len(randomWords)]if randomWords else 12345+randomIndex*13;randomIndex+=1;return value
 if fn==0x4f63ec:return E if allocation else 0
 if fn==0x4f6428:return 0
 if fn in(0x4b45f0,0x486e70,0x4a36f0,0x4db4d0,0x10ff100):return 0
 if fn==0x4db5f0:return 0x1234
 if fn==0x4db6e0:return 0
 raise AssertionError(('unexpected service',hex(fn),hex(t),args,name))
@Dep
def dependency(_,ev,user):
 try:
  e=ev.contents;a=tuple(e.arguments[:e.count]);native_events.append((e.function,e.receiver,a,e.name,snapshot(True)));return effect(e.function,e.receiver,a,e.name,True)
 except Exception as exc:errors.append(exc);return 0
# Scene free is same explicitly observed original CRT delete boundary.
@Free
def free(_,t):native_events.append((0x4f6428,0,(t,),None,snapshot(True)))
c.scene.free=free
@Invoke
def sceneInvoke(_,e):
 native_events.append((e.function,e.receiver,tuple(e.arguments[:e.count]),None,snapshot(True)));return effect(e.function,e.receiver,tuple(e.arguments[:e.count]),None,True)
c.scene.call=sceneInvoke
abis={0x4f6286:(2,8),0x4c7fa0:(1,4),0x4c8060:(1,4),0x4cbb60:(4,16),0x4c8220:(1,4),0x4c82a0:(1,4),0x4dba00:(1,4),0x4c8da0:(6,24),0x4061b0:(1,4),0x4a3050:(0,0),0x4f63ec:(1,0),0x4f6428:(1,0),0x4b45f0:(4,16),0x4a36f0:(1,0),0x4db5f0:(0,0),0x4db6e0:(2,8),0x4db4d0:(3,12),0x10ff100:(1,0)}
def hook(uc,fn,size,user):
 if fn==0x486e70:return
 if fn not in abis:return
 n,pop=abis[fn];sp=uc.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX);name=None
 if fn in(0x4f6286,0x4c7fa0,0x4c8060,0x4dba00,0x4061b0):name=bytes(uc.mem_read(args[0],100)).split(b'\0')[0];normalized=()
 else:normalized=args
 if fn in(0x4a3050,0x4f63ec,0x4f6428,0x486e70,0x4a36f0,0x4db5f0,0x10ff100):t=0
 if fn==0x4c8da0:name=bytes(uc.mem_read(args[4],100)).split(b'\0')[0]
 original_events.append((fn,t,normalized,name,snapshot(False)));v=effect(fn,t,normalized,name,False)
 if fn==0x4f6286:m.write_words(args[1],[v]);v=1 if v else 0
 uc.reg_write(UC_X86_REG_EAX,v&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
transportHook=m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(kind=0):
 global generic,b,g,animationResult,collision,mode,resource,allocation,mutation,randomWords,imageMap,aniMap
 imageMap={};aniMap={};C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);lib.claw_generic_enemy_context_defaults(C.byref(generic));g.tick=1000;g.animationDelta=17;g.ownerToken=OWNER;g.magicDisabled=0;g.audioEnabled=0;g.masterVolume=83;c.fault=b.fault=0;c.composeAnimation=0
 put(A,[0x5137f0]);put(A+8,[0x40000,SC]);put(A+76,[300,400]);put(A+100,[500,8,L,0]);put(A+120,[0]);put(A+128,[0]);put(A+204,[8]);put(A+320,[5,5]);put(A+0x148,[700,0]);put(A+0x158,[80]);put(A+0x170,[ROOTIMAGE,LEAF]);put(A+0x190,[SEQ]);put(A+0x19c,[1]);put(A+0x1a4,[0]);put(L+12,[SC,0x40ff80,0,E,2001]);put(L+44,[0,0,0,0]);put(E,[0x50b74c if kind==0 else 0x50b784 if kind==1 else 0x50da04]);put(E+8,[A,A,L,0,0,1001,2,0]);put(E+296,[A,A,L,SEQ]);put(E+0x148,[SEQ]);put(E+0x150,[1,FLARE]);put(E+0x158,[0,2,1000,1250,1250]);put(E+0x170,[1,SEQ,SEQ,SOUND,0,0]);put(OWNER+0x124,[1]);put(SOUND+16,[POOL]);put(FXL+16,[0x10ff100]);put(SC+8,[SC+0x100]);put(SC+16,[SC+0x200]);put(SC+36,[WORLD]);put(SC+40,[SC+0x400]);put(SC+44,[SC+0x300]);put(WORLD+76,[DESC+0x100]);put(WORLD+92,[PLANE]);put(PLANE+32,[CELLS,ROWS]);put(PLANE+48,[1024,1024]);put(PLANE+140,[6,6]);put(ROWS,[i*16 for i in range(16)]);put(CELLS,[0]*256);put(DESC+0x100,[DESC]);put(DESC,[0x513980,64,64,0,0]);put(ROOTIMAGE+20,[FRAME]);put(ROOTIMAGE+100,[1,3]);put(FRAME,[LEAF]*8);put(LEAF+24,[7,5,1,0]);put(A+0x118,[0xfffffff9,0xfffffffc,6,4]);put(A+0x128,[0xfffffffa,0xfffffffc,7,4]);put(A+0x138,[0xfffffff9,0xfffffffc,6,4]);generic.tileManagerToken=WORLD;generic.sceneToken=SC
 for off in range(0x28,0x100,8):dbl(E+off,0)
 for off in(0x80,0x88,0x90):dbl(E+off,-1e9)
 for off in(0x98,0xa0,0xa8):dbl(E+off,1e9)
 for off in(0xe8,0xf0,0xf8):dbl(E+off,24)
 dbl(E+0x28,1);dbl(E+0x68,300);dbl(E+0x70,400);dbl(E+0x50,700 if kind<2 else 350);dbl(E+0x58,-400 if kind==2 else 0);dbl(E+0x40,2000 if kind==2 else 0);put(E+0xc8,[0,0]);put(E+0x120,[0,8 if kind==2 else 0]);put(E+0x164,[1250]);put(E+0x168,[1250]);put(E+0x150,[SEQ if kind==2 else 1,SOUND if kind==2 else FLARE]);put(E+0x158,[0,2])
 for table,back in zip(TABLES,BACKS):put(table,[0,0,2000,2010,back,back+0x100,4,0,0]);put(back,[0]*11)
 put(BACKS[0]+4,[0x4742f0]);put(BACKS[1]+4,[0x410d60]);put(BACKS[2]+4,[0x4089d0]);put(BACKS[3]+4,[0x43b320,0x43b290]);nameTokens=[]
 for i,(text,literal)in enumerate(names):
  nt=BASE+0x2b000+i*64+12;encoded=text.encode()+b"\0";put(nt-12,[1,len(encoded)-1,len(encoded)-1]);C.memmove(pointer(nt),encoded,len(encoded));states[i].nameToken=nt;nameTokens.append(nt)
 put(BACKS[4],nameTokens);flush_globals();animationResult=collision=mutation=0;mode=8;resource=allocation=1;randomWords=[]
voids={0x410a80,0x408580,0x43ad20,0x408860,0x43b120,0x43b160,0x43b1a0,0x43b1e0,0x414010,0x408510,0x4c7970,0x456030,0x4c9e30,0x4c96b0,0x4741f0,0x474290,0x4742f0,0x473f40,0x4063b0,0x4dca10}
def compare(fn,t=E,args=(),label=None):
 global calls,eventsCount,randomIndex,captureReplay
 captureReplay=seenReplay.get(fn,0)<3 or bool(label and isinstance(label,tuple)and(str(label[0]).startswith("real-")and(label[0].endswith("start")or label[0]=="real-resource-flight"and label[-1]%20==0)))
 c.fault=b.fault=0;serviceTape.clear();flush_globals();before=bytes(heap);beforeImage=bytes(image);beforeGlobals=bytes(g);randomIndex=0;native_events.clear();errors.clear();out=U();av=(U*len(args))(*args);ok=lib.claw_player_projectile_entry(fn,t,av,len(args),C.byref(c),dependency,None,C.byref(out));assert not errors,errors;assert ok and not c.fault,(label,hex(fn),'native',c.fault,b.fault)
 wanted=raw(True);events=list(native_events);savedTape=list(serviceTape);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),beforeImage,len(image));C.memmove(C.addressof(g),beforeGlobals,C.sizeof(g));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,beforeImage);randomIndex=0;original_events.clear();
 try:ret=m.call(fn,t,pack(*args))
 except UcError as exc:raise AssertionError((label,hex(fn),hex(m.u.reg_read(UC_X86_REG_EIP)),original_events[-3:]))from exc
 got=raw(False)
 if got!=wanted:
  differences=[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],wanted[i])for i in range(len(got))if got[i]!=wanted[i]];raise AssertionError((label,hex(fn),'heap/globals',differences[:24]))
 assert len(events)==len(original_events),(label,'event count',[(hex(e[0]),e[2],e[3])for e in events],[(hex(e[0]),e[2],e[3])for e in original_events])
 for i,(a,bx)in enumerate(zip(events,original_events)):assert a==bx,(label,hex(fn),'event',i,a,bx)
 if fn not in voids:assert ret==out.value,(label,hex(fn),'EAX',hex(ret),hex(out.value))
 C.memmove(C.addressof(heap),wanted[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,wanted[SIZE:],0x30000);calls+=1;eventsCount+=len(events);serviceTape[:]=savedTape;saveReplay(fn,t,args,c.composeAnimation,beforeGlobals,before,beforeImage,wanted,out.value,label);return ret
_rez=None
def rez():
 global _rez
 if _rez is not None:return _rez
 data=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(data).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';_rez={}
 def w(t):return struct.unpack_from('<I',data,t)[0]
 def walk(t,n,path=()):
  end=t+n
  while t<end:
   k,at,size=w(t),w(t+4),w(t+8);start=t+(16 if k else 28);nul=data.index(0,start,end);name=data[start:nul].decode()
   if k:walk(at,size,path+(name,));t=nul+1
   else:
    ext=data[t+20:t+24].split(b'\0')[0][::-1].decode();p='/'.join(path+(name+'.'+ext,));t=nul+2;_rez[p]=data[at:at+size]
 walk(w(131),w(135));return _rez
class Record(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(Record),C.POINTER(U)]
assets=[];aniMap={};realCollision=False
priorEffect=effect
abis.update({0x4c88e0:(4,16),0x4208e0:(4,16)})
def effect(fn,t,args,name,native):
 if fn in(0x4c88e0,0x4208e0):return 0
 if fn==0x4f6286 and t==SC+0x310 and aniMap:return aniMap.get(name,0)
 return priorEffect(fn,t,args,name,native)
priorHook=hook
# Replace transport interception for recovered real animation only.
def hook(uc,fn,size,user):
 if c.composeAnimation and fn in(0x4c8220,0x4c82a0):return
 priorHook(uc,fn,size,user)
m.u.hook_del(transportHook)
# The registered hook looks up global hook? Unicorn retains the function object.
# Remove original transport hook and install this wrapper.

animationTransportHook=m.u.hook_add(UC_HOOK_CODE,hook)
def installANI():
 global aniMap
 paths=['GAME/ANIS/CYCLE50.ANI','GAME/ANIS/DYNAMITELIT.ANI','GAME/ANIS/DYNAMITEHORZ.ANI','GAME/ANIS/DYNAMITEEXPLO.ANI'];aniMap={}
 for j,path in enumerate(paths):
  data=rez()[path];sig,_,flags,count,pathLength=struct.unpack_from('<5I',data);assert sig==32;token=BASE+0x30000+j*0x2000;pointers=token+0x100;records=token+0x400;put(token+12,[pointers,count]);put(pointers,[records+i*48 for i in range(count)]);offset=32+pathLength
  for i in range(count):
   record=Record();length=U();buf=(C.c_uint8*(len(data)-offset)).from_buffer_copy(data[offset:]);used=lib.claw_animation_decode_record(buf,len(buf),0,C.byref(record),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(record)));put(records+i*48,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);offset+=used
  assert offset==len(data);aniMap[path.replace('GAME/ANIS/','GAME_').replace('.ANI','').encode()]=token
  if path not in [x.get('path')for x in assets]:assets.append({'path':path,'records':count,'sha256':hashlib.sha256(data).hexdigest()})
 # Original actor embedded animation ctor fields, distinct from fake ANI marker transport.
 put(A+0x188,[0x513848,A,0,0,0,0,0,0,0,1,0x3f800000])
 return aniMap
imageMap={}
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U]
def installImages():
 global imageMap
 imageMap={};groups=['BULLETS','MAGICCLAW','DYNAMITELIT','DYNAMITEEXPLO']
 import re
 for j,group in enumerate(groups):
  paths=[p for p in rez()if p.startswith('GAME/IMAGES/'+group+'/')and p.endswith('.PID')];assert paths,(group,'missing source images');ids={int(re.search(r'[0-9]+',Path(p).stem).group()):p for p in paths};root=BASE+0x14000+j*0x2000;table=root+0x100;first,last=min(ids),max(ids);put(root+20,[table]);put(root+100,[first,last]);put(table,[0]*(last+1))
  for i,path in ids.items():
   data=rez()[path];_,_,w,ht,ox,oy=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,ht,ox,oy);leaf=root+0x400+i*64;put(leaf+16,list(struct.unpack('<10I',bytes(geo)))[:6]);put(table+i*4,[leaf])
  imageMap['GAME_'+group]=root
  if group not in [x.get('group')for x in assets]:assets.append({'group':group,'fileCount':len(ids),'minimum':first,'maximum':last})
 return imageMap
previousResources=effect
def effect(fn,t,args,name,native):
 if fn==0x4f6286 and t==SC+0x210 and imageMap:return imageMap.get(name.decode(),0)
 return previousResources(fn,t,args,name,native)
class Rect(C.Structure):_fields_=[(n,U)for n in('left','top','right','bottom')]
class CollisionActor(C.Structure):_fields_=[(n,U)for n in('flags','x','y','mode','type','stepX','stepY','supportToken','token','deltaX','deltaY')]+[('moveRect',Rect),('hitRect',Rect)]
class Description(C.Structure):_fields_=[(n,U)for n in('type','width','height','inside','outside')]+[(n,C.c_int32)for n in('left','top','right','bottom')]
class World(C.Structure):_fields_=[('cells',C.POINTER(U)),('rows',C.POINTER(U)),('width',C.c_int32),('height',C.c_int32),('shiftX',U),('shiftY',U),('descriptions',C.POINTER(Description)),('descriptionCount',U),('actors',C.POINTER(CollisionActor)),('actorCount',U),('stepX',U),('stepY',U)]
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(CollisionActor),U,U,U]
collisionDescription=(Description*2)(Description(1,64,64,0,0,0,0,0,0),Description(1,64,64,1,0,0,0,0,0));collisionWorld=World(C.cast(pointer(CELLS,256),C.POINTER(U)),C.cast(pointer(ROWS,16),C.POINTER(U)),1024,1024,6,6,collisionDescription,2,None,0,64,64)
priorCollision=effect
actorFields={'flags':8,'x':76,'y':80,'mode':204,'type':208,'stepX':220,'stepY':224,'supportToken':128,'deltaX':344,'deltaY':348}
def effect(fn,t,args,name,native):
 if fn==0x4cbb60 and realCollision:
  assert native
  actor=CollisionActor()
  for n,off in actorFields.items():setattr(actor,n,get(args[0]+off)[0])
  actor.token=args[0];actor.moveRect=Rect(*get(args[0]+280,4));actor.hitRect=Rect(*get(args[0]+296,4));value=lib.claw_collision_move(C.byref(collisionWorld),C.byref(actor),*args[1:])
  for n,off in actorFields.items():put(args[0]+off,[getattr(actor,n)])
  return value
 return priorCollision(fn,t,args,name,native)
previousHook=hook
def hook(uc,fn,size,user):
 if fn==0x4cbb60 and realCollision:
  sp=uc.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,4));original_events.append((fn,uc.reg_read(UC_X86_REG_ECX),args,None,snapshot(False)));return
 previousHook(uc,fn,size,user)
# Reinstall without duplicate original boundary hooks.
m.u.hook_del(animationTransportHook)

collisionTransportHook=m.u.hook_add(UC_HOOK_CODE,hook)
PLAYER,PLAYERLOGIC,PLAYERPRIVATE,INPUT=BASE+0x3a000,BASE+0x3b000,BASE+0x3c000,BASE+0x3d000
lib.claw_projectile_test_fire.argtypes=[U,U,U,U,C.POINTER(Context),Dep,C.c_void_p]
previousFire=effect
def effect(fn,t,args,name,native):
 if fn==0x4c8da0 and name in(b'PistolBullet',b'MagicBullet',b'Dynamite'):
  if not allocation:return 0
  put(A+76,args[1:3],native);put(A+100,[args[3]],native);put(A+8,[args[5]],native);put(A+108,[L],native);put(L+28,[0],native);return A
 return previousFire(fn,t,args,name,native)
def fire(weapon,direction,charge,repeat=3,prepareOnly=False):
 global calls,eventsCount,randomIndex,animationResult
 fresh(weapon-1);installImages();installANI();c.composeAnimation=0;put(PLAYER,[0]*128);put(PLAYER+8,[0x40000,SC]);put(PLAYER+76,[300,400]);put(PLAYER+100,[500,0,PLAYERLOGIC]);put(PLAYER+420,[0]);put(PLAYERLOGIC,[0]*93);put(PLAYERPRIVATE,[0]*78);put(PLAYERPRIVATE,[direction]);put(PLAYERPRIVATE+12*4,[weapon]);put(PLAYERPRIVATE+21*4,[20,0xffffffe2]);put(PLAYERPRIVATE+28*4,[10,10,10]);put(PLAYERPRIVATE+58*4,[repeat]);put(PLAYERPRIVATE+64*4,[charge,0,1000]);put(INPUT,[0]*4);put(0x537204,[INPUT]);put(A+0x170,[0]);animationResult=2
 if prepareOnly:return
 return fireStep(weapon,direction,charge)
def fireStep(weapon,direction,charge):
 global calls,eventsCount,randomIndex
 flush_globals();before=bytes(heap);beforeImage=bytes(image);native_events.clear();errors.clear();randomIndex=0;out=lib.claw_projectile_test_fire(PLAYER,PLAYERLOGIC,PLAYERPRIVATE,INPUT,C.byref(c),dependency,None);assert out and not c.fault and not errors,(weapon,errors,c.fault);wanted=raw(True);events=list(native_events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),beforeImage,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,beforeImage);randomIndex=0;original_events.clear();m.call(0x41c5a0,0,pack(PLAYER,PLAYERLOGIC,PLAYERPRIVATE));got=raw(False)
 assert got==wanted,('whole original41c5a0 fire',weapon,direction,charge,[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],wanted[i])for i in range(len(got))if got[i]!=wanted[i]][:15])
 assert original_events==events,('fire events',weapon,original_events,events);C.memmove(C.addressof(heap),wanted[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,wanted[SIZE:],0x30000);calls+=1;eventsCount+=len(events);return wanted
unsafeStop=0
previousFailureHook=hook
def hook(uc,fn,size,user):
 if unsafeStop and fn==unsafeStop:uc.emu_stop();return
 previousFailureHook(uc,fn,size,user)
# Replace the latest registered wrapper, leaving OriginalV10's instruction logger.

m.u.hook_del(collisionTransportHook);m.u.hook_add(UC_HOOK_CODE,hook)
def failure(fn,stop,wrapper=False,division=False):
 global allocation,unsafeStop,randomIndex,randomWords
 fresh(0 if fn==0x40ff80 else 1 if fn in(0x410040,0x410d60)else 2);allocation=0
 if division:put(A+0x118,[1]);put(A+0x120,[0xffffffff]);randomWords=[0x80000000]
 put(L+28,[0]if wrapper else[2001]);t=0 if wrapper else E;args=(A,)if wrapper else();av=(U*len(args))(*args);flush_globals();before=bytes(heap);bi=bytes(image);native_events.clear();errors.clear();randomIndex=0;out=U();ret=lib.claw_player_projectile_entry(fn,t,av,len(args),C.byref(c),dependency,None,C.byref(out));assert not ret and c.fault==2,(fn,c.fault);wanted=raw(True);ev=list(native_events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);original_events.clear();randomIndex=0;unsafeStop=stop
 m.u.mem_write(m.stack,pack(m.stop,*args));m.u.reg_write(UC_X86_REG_ESP,m.stack);m.u.reg_write(UC_X86_REG_ECX,t);m.u.emu_start(fn,m.stop,count=500000);unsafeStop=0;assert m.u.reg_read(UC_X86_REG_EIP)==stop;assert raw(False)==wanted,(hex(fn),'unsafe prefix heap');assert ev==original_events,(hex(fn),'unsafe prefix events');return len(ev)
countMutationOffset=None;registryGrowth=False
previousReloadEffect=effect
def effect(fn,t,args,name,native):
 if fn==0x4db6e0 and registryGrowth:
  back=BASE+0x2e000;put(t+8,[args[0],args[0],back],native);put(back,[0x4bb030],native);return 0x12345678
 value=previousReloadEffect(fn,t,args,name,native)
 if fn==0x10ff100 and countMutationOffset is not None:put(E+countMutationOffset,[1],native)
 return value
# Bounded sanitizer corpus records complete inputs/results and the exact measured
# transport effects; no emulator or guessed callback is used in the C++ replay.
import gzip
replay=gzip.open(WORK/'sanitizer-replay.bin.gz','wb');replay.write(b'PPR1'+pack(len(imageSeed))+imageSeed);replayCases=0;seenReplay={};serviceTape=[];captureReplay=False
previousTapeEffect=effect
def effect(fn,t,args,name,native):
 before=raw(True)if native and captureReplay else None;value=previousTapeEffect(fn,t,args,name,native)
 if native and captureReplay:
  after=raw(True);patches=[];i=0 if before!=after else len(before)
  while i<len(before):
   if before[i]==after[i]:i+=1;continue
   start=i
   while i<len(before)and before[i]!=after[i]:i+=1
   patches.append((BASE+start if start<SIZE else 0x520000+start-SIZE,after[start:i]))
  serviceTape.append((fn,t,args,name,value,patches))
 return value
@Free
def free(_,t):native_events.append((0x4f6428,0,(t,),None,snapshot(True)));serviceTape.append((0x4f6428,0,(t,),None,0,[]))
c.scene.free=free
def saveReplay(fn,t,args,compose,globalsBytes,before,beforeImage,wanted,out,label):
 global replayCases
 seenReplay[fn]=seenReplay.get(fn,0)+1
 special=label and isinstance(label,tuple)and(str(label[0]).startswith('real-')and(label[0].endswith('start')or label[0]=='real-resource-flight'and label[-1]%20==0))
 if seenReplay[fn]>3 and not special:return
 record=bytearray(pack(fn,t,len(args),compose)+pack(*(list(args)+[0]*(12-len(args))))+globalsBytes+before+beforeImage[0x520000-imageStart:0x550000-imageStart]+wanted+pack(out,len(serviceTape)))
 for f,r,a,n,v,patches in serviceTape:
  nameBytes=n or b'';record+=pack(f,r,len(a),len(nameBytes))+pack(*a)+nameBytes+struct.pack('<Q',v&0xffffffffffffffff)+pack(len(patches))
  for token,data in patches:record+=pack(token,len(data))+data
 replay.write(pack(len(record))+record);replayCases+=1
def playerANI(path):
 data=rez()[path];sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;token=BASE+0x3e000;pointers=token+0x100;records=token+0x400;put(token+12,[pointers,count]);put(pointers,[records+i*48 for i in range(count)]);off=32+pl
 for i in range(count):
  rec=Record();length=U();buf=(C.c_uint8*(len(data)-off)).from_buffer_copy(data[off:]);used=lib.claw_animation_decode_record(buf,len(buf),0,C.byref(rec),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(rec)));put(records+i*48,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);off+=used
 assert off==len(data);put(PLAYER+0x188,[0x513848,PLAYER,0,0,0,0,0,0,0,1,0x3f800000]);out=U();lib.claw_actor_animation_entry.argtypes=[U,U,U,U,C.c_void_p,Host,C.POINTER(U),C.POINTER(U)]
 ag=(U*2)(g.animationDelta,g.masterVolume);fault=U();assert lib.claw_actor_animation_entry(0x4c8220,PLAYER+0x188,token,0,ag,c.scene,C.byref(fault),C.byref(out))and not fault.value
 assets.append({'path':path,'records':count,'sha256':hashlib.sha256(data).hexdigest()});return count
