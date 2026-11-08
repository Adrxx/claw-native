"""Hash-pinned raw Gabriel oracle with explicit common-body/transport services."""
import ctypes as C,struct,subprocess,hashlib,random,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/ground-cannon-agent';U=C.c_uint32
sources=list((ROOT/'Sources').glob('*.cpp'))+[WORK/'ground_cannon_bridge.cpp']
if not(WORK/'libGroundCannon.dylib').exists()or any(p.stat().st_mtime>(WORK/'libGroundCannon.dylib').stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libGroundCannon.dylib')],check=True)
lib=C.CDLL(str(WORK/'libGroundCannon.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,U)for n in('manager','player','tick','animationDelta','level','audioEnabled','volume','jumpDisabled','boss')]+[(n,C.c_float)for n in('damage','health','range')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('bullet',C.c_void_p)]+[(n,U)for n in('composeCore','composeProjectiles','composeAnimation','composeImages','maximumSteps','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*12),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(C.c_uint64,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.ground_cannon_test_image.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.ground_cannon_test_flare.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.ground_cannon_test_projectile.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.ground_cannon_test_animation.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),C.POINTER(U)]
lib.ground_cannon_test_common.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.ground_cannon_test_punk.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
lib.ground_cannon_test_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x400000
A,L,E,SC,MANAGER,PLAYER,PL,PP,ROOTIMAGE,LEAF,TABLE,SEQ,SEQTABLE,RECORD,SOUND,POOL,GEM,GL,GP,WORLD,CONTAINER,THREAD,OTHER,S,K=[BASE+0x1000+i*0x1000 for i in range(25)]
RCLASS,BCLASS,CLASSFN,BOSSFN=0x537728,0x5349b8,BASE+0x20000,BASE+0x21000
NAMEOBJECTS,NAMEBYTES=BASE+0x22000,BASE+0x24000
RECTFN=0x4000010;EMPTYFN=0x4000030;POINTFN=0x4000040;RANDOMTHREAD=THREAD
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x4000000,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g)
bootstrap=json.load(open(ROOT/'work/state-registry-agent/native-bootstrap.json'));stateIDs={n:i for i,n in bootstrap['names']};names={i:n.encode()for n,i in stateIDs.items()};registryStates={b'LS_STARTUP':0x4441b0,b'LS_IDLE':0x4442c0,b'LS_MULTIBOMBATTACK':0x4445d0,b'LS_THUGATTACK1':0x444760,b'LS_CANNONATTACK':0x444960,b'LS_CANNONHIT':0x444b70,b'LS_BLOCKED':0x444d00,b'LS_DEADACT1':0x445090,b'LS_DEADACT2':0x4455b0,b'LS_DEADACT3':0x445660,b'LS_DEADACT4':0x445720}
rng=random.Random(0x443290);events=[];originalEvents=[];errors=[];calls=eventCount=0;found=True;randomValues=[0];randomIndex=0;queryValues=[1,0];queryIndex=0;allocated=E;created=GEM;mutation=0;currentFunction=0;unsafeCases=[];composeCommon=False;capture=False;corpusCases=[];replayEvents=[];realRandom=False
GLOBAL=(0x5371fc,0x537e88,0x537210,0x5430c4,0x534eac,0x532c0c,0x532c10,0x541334,0x5349dc)
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 b=pack(*v)
 if native:C.memmove(ptr(t,len(v)),b,len(b))
 else:m.u.mem_write(t,b)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def number(t,v,native=True):
 b=struct.pack('<d',v)
 if native:C.memmove(ptr(t,2),b,8)
 else:m.u.mem_write(t,b)
def sync():
 for t,v in zip(GLOBAL,struct.unpack('<9I',bytes(g)[:36])):put(t,[v])
 C.memmove(ptr(0x5262b0,3),bytes(g)[36:],12)
def raw(native):
 if native:sync();return bytes(heap)+C.string_at(ptr(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
def text(t,native=True):
 if native:return C.string_at(ptr(t&~3)+t%4).split(b'\0')[0]
 return bytes(m.u.mem_read(t,200)).split(b'\0')[0]
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('lookup',hex(t),n))
 return p
@Invoke
def sceneCall(_,e):
 q=Call();q.function=e.function;q.receiver=e.receiver;q.count=e.count;q.arguments[:e.count]=e.arguments[:e.count];return dependency(C.byref(ctx),C.pointer(q),None)&0xffffffff
@Alloc
def allocate(_,n):
 q=Call();q.function=0x4f63ec;q.count=1;q.arguments[0]=n;return dependency(C.byref(ctx),C.pointer(q),None)&0xffffffff
ctx.scene=Host(None,lookup,allocate,Free(),sceneCall,Clock())
@Dep
def dependency(_,e,user):
 try:
  e=e.contents;a=tuple(e.arguments[:e.count]);name=e.name
  if name is None and e.function in(0x4f6286,0x4dba00,0x4c7fa0,0x4c8060):name=text(a[0])
  if composeCommon and e.function in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060): logged=()
  else:logged=a
  # Shared frozen APIs express source literal transport as name; raw Raux ABI is retained above.
  if composeCommon and e.function in(0x4060b0,0x406120,0x406150,0x406180):return effect(e.function,e.receiver,a,name,True)or 0
  if composeCommon:
   out=U();args=(U*len(a))(*a)
   if e.function==0x414b20 and not ctx.bullet and lib.ground_cannon_test_entry(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if ((e.function==0x4dc870 and a and get(a[0])[0]==0x50b87c)or e.function in(0x4107c0,0x4741f0,0x474290,0x473f40,0x4742f0,0x414010,0x4dca10,0x4063b0))and lib.ground_cannon_test_projectile(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if e.function in(0x458010,0x458120,0x4581c0,0x458280,0x458530,0x458570)and lib.ground_cannon_test_flare(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if lib.ground_cannon_test_image(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if lib.ground_cannon_test_animation(e.function,e.receiver,args,len(a),C.byref(ctx),C.byref(out)):return out.value
   if lib.claw_ground_cannon_entry(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if e.function in(0x4c9be0,)and lib.ground_cannon_test_entry(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
   if ctx.fault:raise AssertionError(("owned source diagnostic",hex(e.function),ctx.fault))
   if (e.receiver==E or e.function==0x4dc870 or e.function in(0x4357a0,0x406310)) and lib.ground_cannon_test_common(e.function,e.receiver,args,len(a),C.byref(ctx),dependency,None,C.byref(out)):return out.value
  events.append((e.function,e.receiver,logged,name,snap(True)))
  before=raw(True)if capture else None;value=effect(e.function,e.receiver,a,name,True)or 0
  if capture:
   after=raw(True);old=struct.unpack('<'+'I'*(len(before)//4),before);new=struct.unpack('<'+'I'*(len(after)//4),after);patches=[(i,y)for i,(x,y)in enumerate(zip(old,new))if x!=y];replayEvents.append((e.function,e.receiver,a,name,hashlib.sha256(before).digest(),value,patches))
  return value
 except Exception as exc:errors.append(exc);return 0

def effect(f,t,a,name,native):
 global randomIndex,queryIndex
 if f==0x44c000:
  # Explicit common-service profile. Joined frozen constructor is added below.
  for o in(8,12,0x128,0x12c,0x178,0x17c,0x190,0x194):put(t+o,[a[0]],native)
  for o in(16,0x130,0x180,0x198):put(t+o,[get(a[0]+108,native=native)[0]],native)
  put(t+0x2fc,[32,0x229],native);put(t+0x1a4,[0x52e1c4,0x52e1c4],native);return t
 if f==0x4f63ec:return GP if a[0]==76 else allocated
 if f in(0x4f6428,0x4dbcd0,0x4f6584,0x4f6439):return 0
 if f==0x4f6286:return SEQ if found else 0
 if f==0x4c7970:
  if found:put(t+0x170,[ROOTIMAGE,LEAF],native);put(t+0x16c,[0],native)
  else:put(t+0x170,[0],native)
  return int(found)
 if f==0x4c79e0:return 1
 if f in(0x4c8220,0x4c82a0):
  if f==0x4c8220:put(t+8,[a[0]],native)
  return 1
 if f==0x4cd800:put(a[0]+80,[get(a[0]+80,native=native)[0]+3],native);return 0
 if f==0x4dba00:return stateIDs[name.decode()]
 if f==0x4107c0:
  for off in(8,12,0x128,0x12c):put(t+off,[a[0]],native)
  for off in(16,0x130):put(t+off,[get(a[0]+108,native=native)[0]],native)
  return t
 if f in(0x4742f0,0x473f40):return 0
 if f in(0x4c7fa0,0x4c8060):return 0
 if f==0x4cbb60:put(a[0]+76,[a[1],a[2]],native);return 0
 if f in(0x43eab0,0x4cda10):return 1
 if f==0x42df90:return 0
 if f==0x4a3050 and realRandom:
  value=(get(THREAD+20,native=native)[0]*214013+2531011)&0xffffffff;put(THREAD+20,[value],native);randomIndex+=1;return(value>>16)&0x7fff
 if f==0x4a3050:value=randomValues[randomIndex%len(randomValues)];randomIndex+=1;return value&0xffffffff
 if f==0x4207f0:value=queryValues[queryIndex%len(queryValues)];queryIndex+=1;return value
 if f in(0x441030,0x406020):return NAMEOBJECTS+(a[0]-2000)*4
 if f==0x4a3810:
  x,y=text(a[0],native),text(a[1],native);return (x>y)-(x<y)&0xffffffff
 if f==0x48cf90:return mutation&2
 if f==0x4c8da0:
  if name==b'GlitterBaby':return OTHER if created else 0
  if created:
   put(created+8,[0x40000,SC],native);put(created+76,list(a[1:3]),native);put(created+100,[a[3],0,GL],native);put(GL+16,[0x458010 if name==b'GabrielLFX' else 0x4000020,0,GP],native);put(GP+12,[created],native);put(GP+300,[created],native);put(GP+0x138,[0xffffffff,0xffffffff,1,1],native);put(created+0x40,[0],native)
   for off in(0x118,0x128,0x138):put(created+off,[0xffffffff,0xffffffff,1,1],native)
  return created
 if f in(0x43dfa0,0x405f60,0x483e40,0x4dbd20,0x43d0f0,0x4000020,0x48ceb0,0x4b45f0,0x461a00,0x420370,0x420a10,0x48cf50,0x48ce40):return 0
 if f==0x4060b0:
  for off in(0x118,0x128,0x138):
   left,right=get(t+off,native=native)[0],get(t+off+8,native=native)[0]
   if left!=0x80000000:put(t+off,[0-right],native);put(t+off+8,[0-left],native)
  return 0
 if f in(0x406120,0x406150,0x406180):
  off={0x406120:0x128,0x406150:0x118,0x406180:0x138}[f];
  if get(t+off,native=native)[0]==0x80000000:return 0
  left,right=get(t+off,native=native)[0],get(t+off+8,native=native)[0];put(t+off,[0-right],native);put(t+off+8,[0-left],native);return 0
 if f in(0x44d000,0x44c840,0x44cfd0,0x44e0c0,0x43e9c0,0x44f3c0,0x44f510,0x440e20,0x44edd0,0x44da20,0x43f720,0x44f660,0x44f490,0x43efe0,0x43fa10,0x43f740,0x44d9f0,0x44f1b0,0x44ebb0,0x440c90,0x404dd0,0x43dfa0,0x4357a0,0x406310,0x4c96b0,0x4dc870,0x40e5c0):
  if mutation&1:put(E+0x3c4,[get(E+0x3c4,native=native)[0]^3],native)
  return 0
 if f==0x4db6e0:return CLASSFN
 if f==0x4db5f0:return 0x12345
 if f==0x4db4d0:return 0
 raise AssertionError(('unexpected',hex(f),hex(t),a,name))
ABIS={0x44c000:(1,4),0x4f63ec:(1,0),0x4f6428:(1,0),0x4dbcd0:(0,0),0x4f6584:(0,0),0x4f6439:(0,0),0x4f6286:(2,8),0x4c7970:(1,4),0x4c8220:(1,4),0x4c82a0:(1,4),0x4cd800:(2,8),0x4dba00:(1,4),0x4a3050:(0,0),0x4207f0:(2,8),0x441030:(1,4),0x4a3810:(2,0),0x4c8da0:(6,24),0x43d0f0:(2,8),0x4000020:(1,0),0x48ceb0:(3,0),0x4b45f0:(4,16),0x4db6e0:(2,8),0x4db5f0:(0,0),0x4db4d0:(3,12),0x44d000:(1,4),0x44c840:(1,4),0x44e0c0:(1,4),0x43e9c0:(1,4),0x440e20:(1,4),0x404dd0:(1,4)}
for f in(0x406120,0x406150,0x406180,0x44cfd0,0x44f3c0,0x44f510,0x44edd0,0x44da20,0x43f720,0x44f660,0x44f490,0x43efe0,0x43fa10,0x43f740,0x44d9f0,0x44f1b0,0x44ebb0,0x440c90,0x4357a0,0x406310,0x4c96b0,0x4dc870,0x40e5c0):ABIS[f]=(0,0)
def hook(uc,f,size,user):
 global randomIndex
 if f==0x4cbb60 and realCollision:
  sp=uc.reg_read(UC_X86_REG_ESP);args=tuple(m.read_words(sp+4,4));originalEvents.append((f,uc.reg_read(UC_X86_REG_ECX),args,None,snap(False)));return

 if f==0x4f6974 and currentFunction not in(0x4493c0,0x4dc870):return
 if f in(0x44f1b0,0x4c96b0):return
 if f==0x4a7dc0 and realRandom:
  sp=uc.reg_read(UC_X86_REG_ESP);n,pop,value=0,0,THREAD
 elif f==0x4a3050 and realRandom:
  originalEvents.append((f,0,(),None,snap(False)));randomIndex+=1;return
 elif f==POINTFN:
  sp=uc.reg_read(UC_X86_REG_ESP);t,x,y=m.read_words(sp+4,3);l,top,right,bottom=map(lambda x:C.c_int32(x).value,get(t,4,False));x,y=C.c_int32(x).value,C.c_int32(y).value;n,pop,value=3,12,int(l<=x<right and top<=y<bottom)
 elif f==EMPTYFN:
  sp=uc.reg_read(UC_X86_REG_ESP);t=m.read_words(sp+4,1)[0];put(t,[0]*4,False);n,pop,value=1,4,1
 elif f==RECTFN:
  sp=uc.reg_read(UC_X86_REG_ESP);values=m.read_words(sp+4,5);m.write_words(values[0],values[1:]);n,pop,value=5,20,1
 elif composeCommon and f==0x4dbcd0 and not(BASE<=uc.reg_read(UC_X86_REG_ECX)<BASE+SIZE):
  sp=uc.reg_read(UC_X86_REG_ESP);n,pop,value=0,0,0
 elif composeCommon and f in(0x4dbe10,0x4dbd60,0x4f6439):
  sp=uc.reg_read(UC_X86_REG_ESP);t=uc.reg_read(UC_X86_REG_ECX)
  if f==0x4dbe10:put(t,[0,0,32,0],False);n,pop,value=2,8,t
  elif f==0x4dbd60:source=m.read_words(sp+4,1)[0];put(t+8,get(source+8,2,False),False);n,pop,value=1,4,t
  else:put(t,[get(0x52e1cc,native=False)[0]],False);n,pop,value=0,0,t
 elif f in ABIS:
  if composeCommon and f==0x441030 and not(0x4a0800<=m.read_words(uc.reg_read(UC_X86_REG_ESP),1)[0]<0x4a0960):
   sp=uc.reg_read(UC_X86_REG_ESP);a=tuple(m.read_words(sp+4,1));value=effect(f,uc.reg_read(UC_X86_REG_ECX),a,None,False);uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+8);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);return
  if composeCommon and f==0x4a3810 and not(0x4a0800<=m.read_words(uc.reg_read(UC_X86_REG_ESP),1)[0]<0x4a0960):return
  if composeCommon and f in(0x4107c0,0x4742f0,0x4741f0,0x474290,0x473f40,0x414010,0x4060b0,0x406120,0x406150,0x406180,0x44c000,0x44d000,0x44c840,0x44cfd0,0x44e0c0,0x43e9c0,0x44f3c0,0x44f510,0x440e20,0x44edd0,0x44da20,0x43f720,0x44f660,0x44f490,0x43efe0,0x43fa10,0x43f740,0x44d9f0,0x44f1b0,0x44ebb0,0x440c90,0x404dd0,0x43dfa0,0x4357a0,0x406310,0x4dc870):return
  if f in(0x4c79e0,0x4c8220,0x4c82a0,0x420a10)and ctx.composeAnimation:return
  if f==0x4c7970 and ctx.composeImages:return
  sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=tuple(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX);norm=a;name=None
  if f in(0x4f63ec,0x4f6428,0x4a3050,0x4a3810,0x48ceb0,0x4db5f0,0x4dc870,0x461a00,0x420370,0x48cf50,0x48ce40,0x4000020,0x48cf90,0x4a36f0):t=0
  if f in(0x4f6286,0x4c7970,0x4c79e0,0x4dba00,0x4c7fa0,0x4c8060):name=text(a[0],False)
  if f==0x4f6286:norm=(a[0],)
  if f==0x48ceb0:name=text(a[1],False)
  if f==0x4c8da0:name=text(a[4],False)
  if f==0x44d000:name=text(a[0],False)
  if f==0x4a3810:name=text(a[1],False)
  originalEvents.append((f,t,()if composeCommon and f in(0x4f6286,0x4dba00,0x4c7970,0x4c7fa0,0x4c8060)else norm,name,snap(False)));value=effect(f,t,norm,name,False)or 0
  if f==0x4f6286:m.write_words(a[1],[value]);value=int(bool(value))
 else:return
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
ABIS.update({0x43dfa0:(0,0),0x406020:(1,4),0x405f60:(1,4),0x483e40:(0,0),0x48cf90:(1,0),0x4dbd20:(1,4),0x473f40:(1,4),0x4107c0:(1,4),0x4742f0:(0,0),0x4060b0:(0,0),0x4c79e0:(2,8),0x4dc870:(1,0),0x4c7fa0:(1,4),0x4c8060:(1,4),0x4cbb60:(4,16),0x43eab0:(0,0),0x4cda10:(4,16),0x42df90:(0,0)})
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(state=0):
 global found,randomValues,randomIndex,queryValues,queryIndex,allocated,created,mutation,realRandom
 C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);C.memset(C.addressof(g),0,C.sizeof(g));g.manager=MANAGER;g.player=PLAYER;g.tick=1000;g.animationDelta=17;g.level=2;g.audioEnabled=1;g.volume=100;g.damage=g.health=g.range=1;ctx.fault=ctx.composeAnimation=ctx.composeImages=0;ctx.composeCore=1;ctx.composeProjectiles=0;ctx.maximumSteps=65536;realRandom=False;found=True;randomValues=[0];randomIndex=0;queryValues=[1,0];queryIndex=0;allocated=E;created=GEM;mutation=0
 put(OTHER+108,[OTHER+0x200]);put(OTHER+0x210,[0x4000020]);
 put(A,[0x5137f0]);put(A+8,[0,SC]);put(A+76,[43203,5184]);put(A+100,[100,0,L,S,0,K]);put(A+0x170,[ROOTIMAGE,LEAF]);put(A+0x188,[0x513870,A,0,0,0,0,1,0,0,0,0x3f800000]);put(A+0x40,[0]);put(A+0x148,[0,0]);put(A+0x124,[52]);put(A+0xcc,[1]);put(L+12,[SC,0x443290,0,E,state]);put(E,[0x50de1c]);put(E+8,[A,A,L,0,0,state,2]);put(E+0x128,[A,A,L]);put(E+0x1a4,[0x52e1c4,0x52e1c4]);put(E+0x184,[2,0,3]);put(E+0x2fc,[32,0]);put(E+0x2e4,[100]);put(E+0x3c4,[250]);put(E+0x450,[43203,5184,0,0]);put(E+0x460,[SEQ]*16);put(E+0x498,[SOUND]*17);put(E+0x4dc,[0]*12);put(E+0x514,[0]*9);put(E+0x528,[43200,43050,5234,0]);put(E+0x308,[SEQ]*16);put(E+0x350,[SEQ]);put(E+0x3a4,[SOUND]);put(E+0x458,[SOUND]);put(E+0x220,[0,0,0,0]);put(E+0x210,[0xffffffff,0xffffffff,1,1]);put(SC+8,[CONTAINER]);put(SC+16,[SC+0x100]);put(SC+0x24,[WORLD,SC+0x200,SC+0x300]);put(PLAYER+76,[43100]);put(PLAYER+108,[PL]);put(PLAYER+0x50,[5184]);put(PLAYER+0x124,[52]);put(PLAYER+0x10c,[100]);put(PL+20,[PP]);put(PP,[0]*78);put(ROOTIMAGE+20,[TABLE]);put(ROOTIMAGE+100,[0,10]);put(TABLE,[LEAF+i*64 for i in range(11)]);put(LEAF+24,[15,60,0,0]);put(SOUND+16,[POOL]);put(SEQ+12,[SEQTABLE,1]);put(SEQTABLE,[RECORD]);put(RECORD,[0x513af0,0,1,0,0,0,100,0,0,0,0,0]);put(0x546d5c,[RECTFN]);put(0x53724c,[1]);put(MANAGER+0x124,[0]);put(MANAGER+0x2c,[WORLD]);put(WORLD+0x768,[0]);put(0x546cdc,[EMPTYFN]);put(0x546cd4,[POINTFN]);put(0x533470,[32]);put(0x544d18,[0]);put(0x52e1cc,[0x52e1c4]);put(0x53c9c0,[0]);put(0x5376b4,[0,0]);put(0x544b4c,[0x534938]);put(RCLASS+8,[2000,max(stateIDs.values()),CLASSFN,CLASSFN,4,10,0]);put(BCLASS+8,[2000,max(stateIDs.values()),BOSSFN,BOSSFN,4,10,0]);put(CLASSFN,[0]*(max(stateIDs.values())-1999));put(BOSSFN,[0]*(max(stateIDs.values())-1999));put(BOSSFN+(stateIDs['LS_STARTUP']-2000)*4,[0x40e580]);put(0x537698+8,[2000,max(stateIDs.values()),NAMEOBJECTS,NAMEOBJECTS,4,10,0])
 for base,fnbase in((0x537638,BASE+0x28000),(0x537878,BASE+0x29000),(0x538428,BASE+0x2a000)):
  put(base+8,[2000,max(stateIDs.values()),fnbase,fnbase,4,10,0]);put(fnbase,[0]*(max(stateIDs.values())-1999))
  for row in bootstrap['classes'].values():
   if row['token']==base:
    for state in row['states']:put(fnbase+(state['id']-2000)*4,[state['function']])
 for base,fnbase,functions in((0x534ad8,BASE+0x2b000,{"LS_FALLING":0x412150}),(0x537ac0,BASE+0x2c000,{"LS_IDLE":0x458570})):
  put(base+8,[2000,max(stateIDs.values()),fnbase,fnbase,4,10,0]);put(fnbase,[0]*(max(stateIDs.values())-1999))
  for name,f in functions.items():put(fnbase+(stateIDs[name]-2000)*4,[f])
 for name,f in registryStates.items():put(CLASSFN+(stateIDs[name.decode()]-2000)*4,[f])
 for i,name in names.items():
  token=NAMEBYTES+(i-2000)*64;put(NAMEOBJECTS+(i-2000)*4,[token]);put(token-12,[1,len(name),len(name)]);C.memmove(ptr(token),name+b'\0',len(name)+1)
 for t,val in((0x38,0.0),(0x40,2000.0),(0x48,0.0),(0x50,0.0),(0x58,0.0),(0x60,0.0),(0x68,43203.0),(0x70,5184.0),(0x78,0.0),(0x80,42000.0),(0x98,44000.0)):number(E+t,val)
 sync()
def compare(f,label,arguments=(),receiver=E,meaningful=False):
 global calls,eventCount,randomIndex,queryIndex,currentFunction,poolCursor,capture
 capture=capture and len(corpusCases)<48;savedPool=poolCursor;currentFunction=f;ctx.fault=0;sync();before=bytes(heap);bi=bytes(image);bg=bytes(g);events.clear();replayEvents.clear();errors.clear();randomIndex=queryIndex=0;arg=(U*len(arguments))(*arguments);out=U();ok=lib.ground_cannon_test_entry(f,receiver,arg,len(arguments),C.byref(ctx),dependency,None,C.byref(out))
 if not ok:ok=lib.ground_cannon_test_punk(f,receiver,arg,len(arguments),C.byref(ctx),dependency,None,C.byref(out))
 if not ok:ok=lib.ground_cannon_test_flare(f,receiver,arg,len(arguments),C.byref(ctx),dependency,None,C.byref(out))
 assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors,[(hex(f),hex(t),a,name)for f,t,a,name,_ in events[-8:]]);expected=raw(True);replays=list(replayEvents);ev=list(events);randomUsed,queryUsed=randomIndex,queryIndex;poolAfter=poolCursor;poolCursor=savedPool;C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(g),bg,len(bg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);originalEvents.clear();randomIndex=queryIndex=0;result=m.call(f,receiver,pack(*arguments),max_instructions=2000000 if f==0x4d1620 else 500000);got=raw(False)
 if got!=expected:raise AssertionError((label,'buffers',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),hex(got[i]),hex(expected[i]))for i in range(len(got))if got[i]!=expected[i]][:24]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x,y)for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if meaningful:assert result==out.value,(label,'EAX',result,out.value)
 assert poolCursor==poolAfter,(label,'allocation order');assert(randomIndex,queryIndex)==(randomUsed,queryUsed),(label,'ordered-input-consumption');C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000)
 for (n,_),t in zip(Globals._fields_[:9],GLOBAL):setattr(g,n,get(t)[0])
 if capture:corpusCases.append((f,receiver,arguments,bg,ctx.composeAnimation,ctx.composeImages,int(composeCommon),out.value,int(meaningful),before,bi[0x520000-imageStart:0x550000-imageStart],expected,replays))
 g.damage,g.health,g.range=struct.unpack('<3f',C.string_at(ptr(0x5262b0,3),12));calls+=1;eventCount+=len(ev);return result
# Own, pinned real-resource transport; enumeration semantics are frozen elsewhere.
resourceTokens={};resourceInventory=[]
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
class AniRecord(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U];lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(AniRecord),C.POINTER(U)]
def assets():
 b=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';out={}
 def w(t):return struct.unpack_from('<I',b,t)[0]
 def walk(t,n,path=()):
  end=t+n
  while t<end:
   k,target,size=w(t),w(t+4),w(t+8);start=t+(16 if k else 28);nul=b.index(0,start,end);name=b[start:nul].decode()
   if k:walk(target,size,path+(name,));t=nul+1
   else:
    ext=b[t+20:t+24].split(b'\0')[0][::-1].decode();p='/'.join(path+(name+'.'+ext,));t=nul+2
    if p.startswith(('LEVEL2/','LEVEL8/','GAME/ANIS/','GAME/IMAGES/LIGHTFX/')):out[p]=b[target:target+size]
 walk(w(131),w(135));return out
_assetCache=None
def realResources():
 global _assetCache
 import re
 if _assetCache is None:_assetCache=assets()
 resourceTokens.clear();resourceInventory.clear();leafAt=BASE+0x40000;table=BASE+0x38000;root=BASE+0x37000;rows=[]
 for path,data in sorted(_assetCache.items()):
  if not path.startswith('LEVEL8/IMAGES/GABRIEL/')or not path.endswith('.PID'):continue
  ident=int(re.search(r'[0-9]+',Path(path).stem)[0]);_,_,w,ht,x,y=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,ht,x,y);put(leafAt+16,list(struct.unpack('<10I',bytes(geo)))[:6]);rows.append({'path':path,'id':ident,'token':leafAt,'width':w,'height':ht,'offsetX':C.c_int32(x).value,'offsetY':C.c_int32(y).value});leafAt+=64
 assert rows;minimum=min(r['id']for r in rows);maximum=max(r['id']for r in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1))
 for row in rows:put(table+row['id']*4,[row['token']])
 resourceTokens[b'LEVEL_GABRIEL']=root;resourceInventory.append({'name':'LEVEL_GABRIEL','images':rows});recordAt=BASE+0x55000;groupAt=BASE+0x32000
 for path,data in sorted(_assetCache.items()):
  if not(path.startswith('LEVEL8/ANIS/GABRIEL/')or path=='GAME/ANIS/NULL.ANI')or not path.endswith('.ANI'):continue
  name=b'GAME_NULL'if path.startswith('GAME/')else('LEVEL_GABRIEL_'+Path(path).stem).encode();sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;root=groupAt;table=root+0x40;groupAt+=0x200;pointers=[];eventsNames=[]
  for i in range(count):
   tail=data[at:];buffer=(C.c_uint8*len(tail)).from_buffer_copy(tail);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(buffer,len(tail),SOUND,C.byref(rec),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(rec)));put(recordAt,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);pointers.append(recordAt);recordAt+=48
   if length.value:eventsNames.append(tail[20:20+length.value].decode())
   at+=used
  assert at==len(data)and len(pointers)*4<0x1c0;put(root+12,[table,count]);put(table,pointers);resourceTokens[name]=root;resourceInventory.append({'name':name.decode(),'path':path,'count':count,'events':eventsNames})
 assert groupAt<BASE+0x37000 and recordAt<BASE+SIZE
 ctx.composeImages=ctx.composeAnimation=1
 return resourceInventory
_oldEffect=effect
def effect(f,t,a,name,native):
 if f==0x4f6286 and resourceTokens:return resourceTokens.get(name+b'_ANI' if name and b'LIGHTFX'in name and t==SC+0x310 else name,SOUND)if found else 0
 if f in(0x4c88e0,0x4208e0):return 0
 return _oldEffect(f,t,a,name,native)
ABIS.update({0x4c88e0:(4,16),0x4208e0:(4,16),0x461a00:(6,0),0x420370:(1,0),0x420a10:(2,8),0x48cf50:(1,0),0x48ce40:(3,0)})
class WorldState(C.Structure):_fields_=[('actor',U*128),('logic',U*93)]
class WorldContext(C.Structure):_fields_=[(n,U)for n in('scene','actor','logic','defaultType','width','height','registry')]+[('layers',U*3)]+[(n,U)for n in('entry','callback','flags')]
class WorldCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U),('text',C.c_char_p)]
WorldDep=C.CFUNCTYPE(U,C.POINTER(WorldState),C.POINTER(WorldContext),C.POINTER(WorldCall),C.c_void_p)
lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(WorldState),C.POINTER(WorldContext),WorldDep,C.c_void_p,C.POINTER(U)]
@WorldDep
def worldDep(s,c,e,user):
 e=e.contents
 if e.function==0x4f6286:return 0x302c000
 if e.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=resourceTokens[b'LEVEL_GABRIEL'];return 1
 if e.function==0x4f4630:return 1
 raise AssertionError(('world-profile',hex(e.function)))
def retailRecord():
 row=next(r for r in json.load(open(WORK/'records.json'))if r['strings'][1]=='Gabriel');w=row['words'];data=pack(*w)+b''.join(x.encode().ljust(n,b'\0')for x,n in zip(row['strings'],w[1:5]));assert len(data)==284+sum(w[1:5]);buf=(C.c_uint8*len(data)).from_buffer_copy(data);s=WorldState();s.actor[:]=get(A,128);s.logic[:]=get(L,93);c=WorldContext(SC,A,L,2,100000,20000,SC+0x120,(U*3)(SC+0x500,SC+0x600,SC+0x700),0,0x443290,1);info=(U*2)();assert lib.claw_world_object_load(buf,len(data),C.byref(s),C.byref(c),worldDep,None,info)==len(data)and info[1]==1;put(A,s.actor);put(L,s.logic);put(A+112,[S]);put(A+120,[K]);return row
def nullPageOff():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def desc(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,desc(0,0x9b));m.u.mem_write(gdt+16,desc(0,0x93));m.u.mem_write(gdt+24,desc(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved

def unsafeCompare(f,label,arguments=(),receiver=E):
 from unicorn import UcError
 global eventCount,randomIndex,queryIndex
 sync();before=bytes(heap);bi=bytes(image);bg=bytes(g);events.clear();errors.clear();randomIndex=queryIndex=0;ctx.fault=0;out=U();arg=(U*len(arguments))(*arguments);ok=lib.ground_cannon_test_entry(f,receiver,arg,len(arguments),C.byref(ctx),dependency,None,C.byref(out));assert not ok and ctx.fault,(label,'native diagnostic');fault=ctx.fault;expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(g),bg,len(bg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);originalEvents.clear();randomIndex=queryIndex=0;saved=nullPageOff()
 try:
  try:m.call(f,receiver,pack(*arguments));raise AssertionError((label,'expected original null fault'))
  except UcError:pass
  eip=m.u.reg_read(UC_X86_REG_EIP);got=raw(False)
  # TEB/GDT are emulation setup, outside gameplay comparison ownership.

  assert got==expected,(label,'unsafe prefix buffers');assert ev==originalEvents,(label,'unsafe prefix events');unsafeCases.append({'label':label,'function':hex(f),'nativeFault':fault,'originalEIP':hex(eip),'events':len(ev)});eventCount+=len(ev)
 finally:m.u.mem_map(0,4096);m.u.context_restore(saved)
def dumpCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as file:
  file.write(b'GABR'+pack(imageStart,len(imageSeed),SIZE,len(corpusCases))+imageSeed)
  for f,t,a,bg,ani,img,common,out,meaning,before,globalBefore,after,replays in corpusCases:
   file.write(pack(f,t,len(a),*list(a)+[0]*(4-len(a)))+bg+pack(ani,img,common,out,meaning,len(replays))+before+globalBefore)
   for ef,et,ea,name,digest,value,patches in replays:
    nb=name or b'';file.write(pack(ef,et,len(ea),*list(ea)+[0]*(12-len(ea)),value,value>>32,len(nb),len(patches))+digest+nb)
    for i,v in patches:file.write(pack(i,v))
   file.write(after)
 return len(corpusCases)
# Weapon family host profiles retain original class/state identities.
_weaponFresh=fresh
def weaponFresh(kind='cannon',state=0):
 _weaponFresh(state);g.level=8;ctx.composeProjectiles=1;ctx.composeCore=1;ctx.composeAnimation=ctx.composeImages=0
 callback,vt={'cannon':(0x4493c0,0x50dfd4),'bomb':(0x4459d0,0x50ded4),'ball':(0x414b20,0x50ba04)}[kind]
 put(L+16,[callback,0,E,state]);put(L+44,[0]*4);put(E,[vt]);put(E+20,[0,0,1001,2]);put(E+40,[A,A,L]);put(E+48,[L]);put(E+72,[SEQ]*3);put(E+124,[SEQ]*2+[SOUND]*2+[0,0,0]);put(E+88,[0]);put(E+92,[50,54,-26,-10]);put(E+0x148,[SEQ]);put(E+0x150,[SEQ,0,0,0,0,0,1250]);put(E+0x170,[SEQ]+[SOUND]*6+[0,0]);put(E+200,[0]);put(A+8,[0x40000,SC]);put(A+0x164,[0]);put(A+0xcc,[8]);put(A+0x104,[0]);put(A+0x148,[0,0]);put(0x53774c,[OTHER]);put(OTHER+0x518,[0,0,0]);put(OTHER+0x530,[5234,0]);put(OTHER+0x534,[0]);put(E+0x94,[0]);
 for o in(0x118,0x128,0x138):put(A+o,[-3,-5,3,5])
 for base,fnbase in((0x537818,BASE+0x35000),(0x534bf8,BASE+0x2d000),(0x537788,BASE+0x2e000),(0x537758,BASE+0x2f000),(0x534910,BASE+0x30000)):
  put(base+8,[2000,max(stateIDs.values()),fnbase,fnbase,4,10,0]);put(fnbase,[0]*(max(stateIDs.values())-1999))
  for token,ident,fn,name in json.load(open(ROOT/'work/state-registry-agent/bootstrap-probe.json'))['bindings']:
   if token==base:put(fnbase+(ident-2000)*4,[fn])
 plane,cells,rows,descs,desc=[BASE+x for x in(0x76000,0x77000,0x77500,0x77600,0x77700)]
 put(WORLD+76,[descs]);put(WORLD+92,[plane]);put(WORLD+100,[64,64]);put(plane+32,[cells,rows]);put(plane+48,[512,512]);put(plane+140,[6,6]);put(rows,[i*8 for i in range(8)]);put(cells,[0]*64);put(descs,[desc]);put(desc,[0x513980,64,64,0,0]);put(A+220,[10,10]);put(WORLD+12,[SC]);put(SC+0x100+20,[0]);put(E+0x124,[0]);put(E+0x148,[SEQ]);put(A+0x158,[0,0]);return callback

# Real retail REZ content; resource lookup remains explicit dictionary transport.
def weaponResources():
 global _assetCache
 import re
 if _assetCache is None:_assetCache=assets()
 resourceTokens.clear();resourceInventory.clear();leafAt=BASE+0x40000;table=BASE+0x3a000;root=BASE+0x31000
 for group in ('CANNON','CANNONBALL'):
  rows=[]
  for path,data in sorted(_assetCache.items()):
   if not path.startswith(f'LEVEL{g.level}/IMAGES/'+group+'/')or not path.endswith('.PID'):continue
   ident=int(re.search(r'[0-9]+',Path(path).stem)[0]);_,_,w,ht,x,y=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,ht,x,y);put(leafAt+16,list(struct.unpack('<10I',bytes(geo)))[:6]);rows.append({'path':path,'id':ident,'token':leafAt,'width':w,'height':ht});leafAt+=64
  minimum=min(r['id']for r in rows);maximum=max(r['id']for r in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1))
  for row in rows:put(table+row['id']*4,[row['token']])
  resourceTokens[('LEVEL_'+group).encode()]=root;resourceInventory.append({'name':'LEVEL_'+group,'images':rows});root+=0x100;table+=0x400
 recordAt=BASE+0x55000;groupAt=BASE+0x32000
 for path,data in sorted(_assetCache.items()):
  if not (any(path.startswith(f'LEVEL{g.level}/ANIS/'+group+'/')for group in('CANNON','CANNONBALL'))or path=='GAME/ANIS/NULL.ANI')or not path.endswith('.ANI'):continue
  name=b'GAME_NULL'if path.startswith('GAME/')else('LEVEL_'+path.split('/')[2]+'_'+Path(path).stem).encode();sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;root=groupAt;table=root+0x40;groupAt+=0x200;pointers=[]
  for i in range(count):
   tail=data[at:];buffer=(C.c_uint8*len(tail)).from_buffer_copy(tail);rec=AniRecord();length=U();used=lib.claw_animation_decode_record(buffer,len(tail),SOUND,C.byref(rec),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(rec)));put(recordAt,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);pointers.append(recordAt);recordAt+=48;at+=used
  assert at==len(data)and len(pointers)*4<0x1c0;put(root+12,[table,count]);put(table,pointers);resourceTokens[name]=root;resourceInventory.append({'name':name.decode(),'path':path,'count':count})
 assert groupAt<BASE+0x3a000 and recordAt<BASE+0x76000
 ctx.composeImages=ctx.composeAnimation=1;return resourceInventory

# All source creation branches use independent fresh actor/logic/private tokens.
_previousWeaponEffect=effect
fireCreation=False
_childAllocation=0
projectileQuery=1

def effect(f,t,a,name,native):
 global _childAllocation
 if f==0x4f63ec and _childAllocation:return _childAllocation
 if f==0x4c8da0 and fireCreation:
  child=created
  if child:
   put(child,[0x5137f0],native);put(child+112,[0,0,0],native);put(GL,[0]*93,native);put(GL,[0x513740],native);put(child+8,[0x40000,SC],native);put(child+76,list(a[1:3]),native);put(child+100,[a[3],0,GL,0,0,0],native);put(child+0x164,[0],native);put(child+0x170,[0,0],native);put(child+0x148,[0,0],native);put(child+0x104,[0],native);put(child+0x188,[0x513848,child,0,0,0,0,1,0,0,0,0x3f800000],native);put(GL+12,[SC,0x414b20 if name==b'CannonBall'else 0x4459d0,0,0,0],native);put(GL+44,[0]*4,native);put(child+220,[10,10],native)
   for off in(0x118,0x128,0x138):put(child+off,[-3,-5,3,5],native)
   _childAllocation=GP
  return child
 if f==0x4cda10:return projectileQuery
 if f==0x4a36f0:return 0
 return _previousWeaponEffect(f,t,a,name,native)
ABIS.update({0x4a36f0:(1,0)})
realCollision=False
class Rect(C.Structure):_fields_=[(n,U)for n in('left','top','right','bottom')]
class CollisionActor(C.Structure):_fields_=[(n,U)for n in('flags','x','y','mode','type','stepX','stepY','supportToken','token','deltaX','deltaY')]+[('moveRect',Rect),('hitRect',Rect)]
class Description(C.Structure):_fields_=[(n,U)for n in('type','width','height','inside','outside')]+[(n,C.c_int32)for n in('left','top','right','bottom')]
class World(C.Structure):_fields_=[('cells',C.POINTER(U)),('rows',C.POINTER(U)),('width',C.c_int32),('height',C.c_int32),('shiftX',U),('shiftY',U),('descriptions',C.POINTER(Description)),('descriptionCount',U),('actors',C.POINTER(CollisionActor)),('actorCount',U),('stepX',U),('stepY',U)]
lib.claw_collision_move.argtypes=[C.POINTER(World),C.POINTER(CollisionActor),U,U,U]
collisionDescriptions=(Description*2)(Description(1,64,64,0,0,0,0,0,0),Description(1,64,64,1,0,0,0,0,0))
collisionWorld=World(C.cast(ptr(BASE+0x77000,64),C.POINTER(U)),C.cast(ptr(BASE+0x77500,8),C.POINTER(U)),512,512,6,6,collisionDescriptions,2,None,0,64,64)
previousWeaponCollision=effect
actorFields={'flags':8,'x':76,'y':80,'mode':204,'type':208,'stepX':220,'stepY':224,'supportToken':128,'deltaX':344,'deltaY':348}
def effect(f,t,a,name,native):
 if f==0x4cbb60 and realCollision:
  assert native
  actor=CollisionActor()
  for n,off in actorFields.items():setattr(actor,n,get(a[0]+off)[0])
  actor.token=a[0];actor.moveRect=Rect(*get(a[0]+280,4));actor.hitRect=Rect(*get(a[0]+296,4));value=lib.claw_collision_move(C.byref(collisionWorld),C.byref(actor),*a[1:])
  for n,off in actorFields.items():put(a[0]+off,[getattr(actor,n)])
  return value
 return previousWeaponCollision(f,t,a,name,native)
def solidWorld():
 desc=BASE+0x77700
 put(BASE+0x77600,[desc,desc+0x40]);put(desc+0x40,[0x513980,64,64,1]);put(BASE+0x77000,[1 if(i//8>=6 or i%8 in(1,6))else 0 for i in range(64)])
retailKind='cannon'
_weaponWorldDep=worldDep
@WorldDep
def worldDep(s,c,e,user):
 e=e.contents
 if e.function==0x4f6286:return 0x302c000
 if e.function in(0x4c7970,0x4c7900):s.contents.actor[0x170//4]=resourceTokens[b'LEVEL_GABRIELCANNON'];return 1
 if e.function==0x4f4630:return 1
 raise AssertionError(('world-profile',hex(e.function)))
def retailCannonRecord():
 row=next(r for r in json.load(open(WORK/'records.json'))if r['strings'][1]=='GabrielCannon');w=row['words'];data=pack(*w)+b''.join(x.encode().ljust(n,b'\0')for x,n in zip(row['strings'],w[1:5]));buf=(C.c_uint8*len(data)).from_buffer_copy(data);s=WorldState();s.actor[:]=get(A,128);s.logic[:]=get(L,93);c=WorldContext(SC,A,L,2,100000,20000,SC+0x120,(U*3)(SC+0x500,SC+0x600,SC+0x700),0,0x446550,0);info=(U*2)();assert lib.claw_world_object_load(buf,len(data),C.byref(s),C.byref(c),worldDep,None,info)==len(data)and info[1]==1;put(A,s.actor);put(L,s.logic);put(A+112,[S]);put(A+120,[K]);return row

# Exact bounded CString-data and no-op boundaries for the generic ground FSM.
previousGroundEffect=effect
def effect(f,t,a,name,native):
 if f==0x4f6974:return get(t,native=native)[0]
 return previousGroundEffect(f,t,a,name,native)
ABIS[0x4f6974]=(1,4)

PUNK_ACTOR,PUNK_PRIMARY,PUNK_PRIVATE=[BASE+x for x in(0x1a000,0x1b000,0x1c000)]
previousCreateGround=effect
def effect(f,t,a,name,native):
 if f==0x4c8da0 and name==b'GroundCannon':
  if not created:return 0
  put(A,[0x5137f0],native);put(A+8,[a[5],SC],native);put(A+76,a[1:3],native);put(A+100,[a[3],0,L,S,0,K],native);put(A+64,[0],native);put(A+0x148,[0,0],native);put(A+0x170,[0,0],native);put(L+16,[0x4493c0,0,0,0],native);put(A+0x188,[0x513870,A,0,0,0,0,1,0,0,0,0x3f800000],native)
  return A
 return previousCreateGround(f,t,a,name,native)
def parentProfile(row):
 w=row['words'];raw=pack(*w)+b''.join(v.encode().ljust(n,b'\0')for v,n in zip(row['strings'],w[1:5]));buf=(C.c_uint8*len(raw)).from_buffer_copy(raw);s=WorldState();s.actor[:]=get(PUNK_ACTOR,128);s.logic[:]=get(PUNK_PRIMARY,93);c=WorldContext(SC,PUNK_ACTOR,PUNK_PRIMARY,2,row['worldWidth'],row['worldHeight'],SC+0x120,(U*3)(SC+0x500,SC+0x600,SC+0x700),0,0x474330,0);info=(U*2)()
 @WorldDep
 def profile(s,c,e,u):
  e=e.contents
  if e.function==0x4f6286:return BASE+0x16000
  if e.function in(0x4c7970,0x4c7900,0x4c79e0,0x4c7a40,0x4f4630):return 1
  raise AssertionError(hex(e.function))
 assert lib.claw_world_object_load(buf,len(raw),C.byref(s),C.byref(c),profile,None,info)==len(raw)and info[1]
 put(PUNK_ACTOR,s.actor);put(PUNK_PRIMARY,s.logic);put(PUNK_PRIVATE,[0]*260);put(PUNK_PRIVATE+8,[PUNK_ACTOR,PUNK_ACTOR,PUNK_PRIMARY]);put(PUNK_PRIVATE+300,[PUNK_ACTOR,PUNK_PRIMARY]);put(PUNK_PRIMARY+24,[PUNK_PRIVATE]);put(PUNK_PRIVATE+0x408,[0]);return row

def retailWorld(level):
 import zlib
 global collisionWorld
 path=ROOT/f'work/original-disc-assets/LEVEL{level}/WORLDS/WORLD.WWD';raw=path.read_bytes();offset=struct.unpack_from('<I',raw,736)[0]
 if struct.unpack_from('<I',raw,8)[0]&2:raw=raw[:offset]+zlib.decompress(raw[offset:])
 for i in range(struct.unpack_from('<I',raw,732)[0]):
  ph=struct.unpack_from('<40I',raw,offset+160*i)
  if ph[2]&1:
   columns,rows=ph[24:26];assert ph[22:24]==(64,64);cells=list(struct.unpack_from('<'+'I'*(columns*rows),raw,ph[33]));break
 at=struct.unpack_from('<I',raw,740)[0];count=struct.unpack_from('<I',raw,at+8)[0];at+=32;ds=[]
 for _ in range(count):
  kind,_,w,height=struct.unpack_from('<4I',raw,at)
  if kind==1:ds.append(Description(kind,w,height,struct.unpack_from('<I',raw,at+16)[0],0,0,0,0,0));at+=20
  else:
   assert kind==2;outside,inside=struct.unpack_from('<2I',raw,at+16);ds.append(Description(kind,w,height,inside,outside,*struct.unpack_from('<4i',raw,at+24)));at+=40
 offsets=[columns*i for i in range(rows)];cs=(U*len(cells))(*cells);rs=(U*len(offsets))(*offsets);descriptions=(Description*len(ds))(*ds);collisionWorld=World(cs,rs,columns*64,rows*64,6,6,descriptions,len(ds),None,0,64,64);collisionWorld.storage=cs,rs,descriptions
 plane,cellMemory,rowMemory,descPointers,descMemory,actorList=BASE+0xd0000,BASE+0x100000,BASE+0x1b0000,BASE+0x1b2000,BASE+0x1c0000,CONTAINER
 put(WORLD+12,[SC]);put(SC+8,[actorList]);put(actorList+20,[0]);put(WORLD+76,[descPointers]);put(WORLD+92,[plane]);put(WORLD+100,[64,64]);put(plane+32,[cellMemory,rowMemory]);put(plane+48,[columns*64,rows*64]);put(plane+140,[6,6]);put(cellMemory,cells);put(rowMemory,offsets)
 for i,d in enumerate(ds):put(descMemory+i*64,[0x513980 if d.type==1 else 0x5139c8,d.width,d.height,d.inside if d.type==1 else d.outside,d.inside,d.left,d.top,d.right,d.bottom])
 put(descPointers,[descMemory+i*64 for i in range(len(ds))]);return {'columns':columns,'rows':rows,'descriptions':count}

# Live source scene globals are normalized into a separate fixture alias; all
# physical static global spans are still compared in the final/raw snapshots.
SCENE_GLOBALS=BASE+0xe0000;GRID_PLANE=BASE+0xd2000
sceneMode=False;poolCursor=BASE+0x200000
sourceSceneAddresses=[0x5430d0,*range(0x5430f0,0x543104,4),*range(0x5430d8,0x5430ec,4),0x5430c8,0x5430c4]
previousRaw=raw
def raw(native):
 if sceneMode:
  if native:
   for address,value in zip(sourceSceneAddresses,get(SCENE_GLOBALS,13)):put(address,[value])
  else:put(SCENE_GLOBALS,[get(address,native=False)[0]for address in sourceSceneAddresses],False)
 return previousRaw(native)
@Free
def sceneFree(_,token):
 q=Call();q.function=0x4f6428;q.count=1;q.arguments[0]=token;dependency(C.byref(ctx),C.pointer(q),None)
ctx.scene.free=sceneFree
previousSceneEffect=effect
def effect(f,t,a,name,native):
 global poolCursor
 if sceneMode and f==0x4f63ec:
  value=poolCursor;poolCursor+=(a[0]+15)&~15;assert poolCursor<BASE+SIZE;return value
 if sceneMode and f==0x4a35f0:return 0
 if sceneMode and f==0x4f6428:return 0
 return previousSceneEffect(f,t,a,name,native)
ABIS[0x4a35f0]=(1,0)
def setupSpatial(width,height):
 global sceneMode,poolCursor
 sceneMode=True;poolCursor=BASE+0x200000
 put(CONTAINER,[0x513c20,0,0,SC,0x5107bc,0,0,0,0,0,10]);put(SC+8,[CONTAINER]);put(GRID_PLANE,[0]*45);put(GRID_PLANE+12,[SC]);put(GRID_PLANE+48,[width,height]);put(SCENE_GLOBALS,[3,0x5108fc,0,0,0,0,0x5108fc,0,0,0,0,g.tick,g.animationDelta])
 for address,value in zip(sourceSceneAddresses,get(SCENE_GLOBALS,13)):put(address,[value])
 compare(0x4cb040,'whole source grid dimensions',(640,480),receiver=WORLD,meaningful=True)
 compare(0x4d1620,'whole source plane grid construction',(BASE+0xd1000,0),receiver=GRID_PLANE,meaningful=True)
 return get(GRID_PLANE+176)[0]
