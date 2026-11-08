"""Whole default-scene source composition; only allocator/COM/OS are adapted."""
import ctypes as C,struct,hashlib,random,subprocess,json,os
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=Path(os.environ.get('CLAW_SCENE_STARTUP_WORK',ROOT/'work/scene-startup-composition-agent'));WORK.mkdir(parents=True,exist_ok=True);U=C.c_uint32
support=Path(os.environ.get('CLAW_SCENE_STARTUP_SUPPORT',ROOT/'work/application-level-progression-agent/libProgressionFrozenSupport.dylib'))
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/SceneStartupCompositionRuntime.cpp'),str(support),'-o',str(WORK/'libComposition.dylib')],check=True)
lib=C.CDLL(str(WORK/'libComposition.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call')]+[('clock',Clock)]
class Base(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('camera',C.c_void_p)]+[(n,U)for n in('base','level','cameraFlag','spatial','fault')]
class Graphics(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('palette',C.c_void_p),('max',U),('fault',U)]
class Display(C.Structure):_fields_=[('scene',Host),('graphics',C.c_void_p),('images',C.c_void_p),('max',U),('fault',U)]
class Palette(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p),('scratch',U),('lists',U),('max',U),('fault',U)]
class Audio(C.Structure):_fields_=[('scene',Host),('max',U),('fault',U)]
class World(C.Structure):_fields_=[('scene',Host),('arrays',C.c_void_p),('spatial',U),('fault',U)]
class Registry(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('arrays','images','imageHost')]+[('fault',U),('nameBytes',U)]
class Life(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('display','graphics','audio','palette','world','image')]+[('max',U),('fault',U)]
class Collections(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('progression','numbers','actors')]+[(n,U)for n in('base','numbersFlag','sceneFlag','animation','images','max','fault')]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('startup','lifecycle','display','graphics','palette','audio','world','registry','images','arrays','collections')]+[('max',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.c_void_p*3),('sizes',U*3),('tokens',U*3),('name',C.c_char_p)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_scene_startup_composition_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x100000;SCENE=BASE+0x1000;DEVICE=BASE+0x2000;VT=BASE+0x3000;DS=BASE+0x4000;DSVT=BASE+0x5000;DD=BASE+0x6000;DDVT=BASE+0x7000;ALLOC=BASE+0x10000;IMAGE_START,IMAGE_SIZE=0x500000,0x48000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.stack=0x200e000;m.u.mem_map(BASE,SIZE);m.u.mem_map(0x700000,0x30000);m.executed.clear();imageSeed=bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE));image=(C.c_uint8*IMAGE_SIZE)();heap=(C.c_uint8*SIZE)();ctx=Context();native=True;events=[];originalEvents=[];errors=[];cursor=ALLOC;allocationIndex=0;allocFailure=0;failure={};created=[];freed=[];calls=snapshots=0;mutations={};capture=False;corpus=[];replays=[]
@Lookup
def lookup(_,t,n):
 if t%4:return 0
 if BASE<=t and t+4*n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IMAGE_START<=t and t+4*n<=IMAGE_START+IMAGE_SIZE:return C.addressof(image)+t-IMAGE_START
 return 0
@Clock
def clock(_):return 1000
host=Host(None,lookup,None,None,None,clock);bg=(U*21)();cg=(U*12)();gg=(U*8)();pg=U();ig=(U*288)();base=Base(host,C.addressof(bg),C.addressof(cg),1,1,1,1,0);graphics=Graphics(host,C.addressof(gg),None,1000000,0);display=Display(host,C.addressof(graphics),C.addressof(ig),1000000,0);palette=Palette(host,C.addressof(pg),BASE+0xa000,1,1000000,0);audio=Audio(host,1000000,0);world=World(host,None,1,0);registry=Registry(host,None,C.addressof(ig),None,0,0);life=Life(host,C.addressof(display),C.addressof(graphics),C.addressof(audio),C.addressof(palette),C.addressof(world),C.addressof(ig),1000000,0);collections=Collections(host,None,None,None,0,1,0,0,0,1000000,0)
ctx.scene=host
for name,value in [('startup',base),('lifecycle',life),('display',display),('graphics',graphics),('palette',palette),('audio',audio),('world',world),('registry',registry),('images',ig),('collections',collections)]:setattr(ctx,name,C.addressof(value))
ctx.max=1000000
TEB,GDT=0x10ed000,0x10ee000
for index,address,access in((8,0,0x9b),(16,0,0x93),(24,TEB,0x93)):m.u.mem_write(GDT+index,struct.pack('<HHBBBB',65535,address&65535,(address>>16)&255,access,0xcf,(address>>24)&255))
m.u.reg_write(UC_X86_REG_GDTR,(0,GDT,256,0));m.u.reg_write(UC_X86_REG_CS,8)
for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,16)
m.u.reg_write(UC_X86_REG_FS,24);m.write_words(TEB,[0xdeadbeef])
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def get(t,n=1):return list(struct.unpack('<'+'I'*n,C.string_at(lookup(None,t,n),4*n)if native else m.u.mem_read(t,4*n)))
def put(t,v):
 b=pack(*v)
 if native:
  p=lookup(None,t,len(v));assert p,('native missing write',hex(t));C.memmove(p,b,len(b))
 else:m.u.mem_write(t,b)
def raw():return(bytes(heap)+bytes(image))if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IMAGE_START,IMAGE_SIZE))
def snap():return hashlib.sha256(raw()).digest()
def differences(a,b):
 result=[]
 def walk(start,end):
  if a[start:end]==b[start:end]:return
  if end-start<=32:result.extend((i,b[i])for i in range(start,end)if a[i]!=b[i]);return
  middle=(start+end)//2;walk(start,middle);walk(middle,end)
 walk(0,len(a));return result
def effect(f,t,a,buffers):
 global cursor,allocationIndex
 if f==0x4f63ec:
  allocationIndex+=1
  if allocationIndex==allocFailure:return 0
  result=cursor;cursor+=(max(a[0],1)+15)&~15;created.append((result,a[0]));assert cursor<BASE+SIZE;return result
 if f==0x4f6428:freed.append(a[0]);return 0
 if f==0x546850:put(a[1],[DEVICE]);return failure.get('ddCreate',0)
 if f==0x700050:return failure.get('ddCoop',0)
 if f==0x70002c:put(a[1]+4,[0x08000000]);return failure.get('ddCaps',0)
 if f==0x700020:return failure.get('ddEnum',0) #Declared empty physical mode inventory.
 if f==0x700054:return failure.get('ddMode',0)
 if f==0x700030:
  values=[0]*27;values[0]=108;values[21]=8;values[22:25]=[0xff0000,0xff00,0xff]
  if native:C.memmove(buffers[0],pack(*values),108)
  else:m.u.mem_write(buffers[0],pack(*values))
  return failure.get('ddFormat',0)
 if f==0x700018:put(a[2],[DD]);return failure.get('surfaceCreate',0)
 if f==0x710058:
  desc=[0]*27;desc[0]=108;desc[1]=7;desc[2]=480;desc[3]=640;desc[4]=640;desc[21]=8;put(a[1],desc);return failure.get('surfaceDescribe',0)
 if f==0x710030:
  if native:C.memmove(buffers[1],pack(DD),4)
  else:m.u.mem_write(buffers[1],pack(DD))
  return failure.get('attached',0)
 if f==0x4f4480:put(a[1],[DS]);return failure.get('dsCreate',0)
 if f==0x720018:return failure.get('dsCoop',0)
 if f in(0x70004c,0x700008,0x710008,0x720008,0x4bd260,0x4b4ed0):return 0
 raise AssertionError(('physical service',hex(f),hex(t),a))
@Dep
def dep(_,qp,u):
 try:
  q=qp.contents;a=list(q.arguments[:q.count]);buffers=list(q.buffers[:q.bufferCount]);before=raw();inputBuffers=tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount));events.append((q.function,q.receiver,tuple(a),q.mask,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)),snap()));value=effect(q.function,q.receiver,a,buffers)
  for token,values in mutations.get(q.function,[]):put(token,values)
  if capture:replays.append((q.function,q.receiver,tuple(a),q.mask,value,inputBuffers,tuple(C.string_at(q.buffers[i],q.sizes[i])for i in range(q.bufferCount)),hashlib.sha256(before).digest(),differences(before,raw())))
  return value
 except Exception as ex:errors.append(ex);ctx.fault=1;return 0
COUNTS={0x4f63ec:(1,0),0x4f6428:(1,0),0x4bd260:(3,0),0x4b4ed0:(3,0),0x546850:(3,12),0x700050:(3,12),0x70002c:(3,12),0x700020:(5,20),0x700054:(4,16),0x700030:(2,8),0x700018:(4,16),0x70004c:(1,4),0x700008:(1,4),0x710058:(2,8),0x710030:(3,12),0x710008:(1,4),0x4f4480:(3,12),0x720018:(3,12),0x720008:(1,4)}
def hook(u,f,size,user):
 if f not in COUNTS:return
 n,pop=COUNTS[f];sp=u.reg_read(UC_X86_REG_ESP);a=list(m.read_words(sp+4,n));mask=0;buffers=[];sizes=[]
 if f==0x700030:mask=2;buffers=[a[1]];sizes=[108];a[1]=0
 if f==0x710030:mask=6;buffers=a[1:3];sizes=[4,4];a[1:3]=[0,0]
 originalEvents.append((f,0,tuple(a),mask,tuple(bytes(u.mem_read(p,n))for p,n in zip(buffers,sizes)),snap()));v=effect(f,0,a,buffers)
 for token,values in mutations.get(f,[]):put(token,values)
 u.reg_write(UC_X86_REG_EAX,v&0xffffffff);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0):
 global native,cursor,allocationIndex,allocFailure,failure,mutations
 native=True;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,imageSeed,IMAGE_SIZE);cursor=ALLOC;allocationIndex=allocFailure=0;failure={};mutations={};ctx.fault=0;created.clear();freed.clear();put(0x546850,[0x546850]);put(0x541398,[0]);put(0x541374,[0]);put(0x541378,[0x51079c,0,0,0,0]);put(DEVICE,[VT]);put(VT+8,[0x700008]);put(VT+0x18,[0x700018]);put(VT+0x20,[0x700020]);put(VT+0x2c,[0x70002c,0x700030]);put(VT+0x4c,[0x70004c,0x700050,0x700054]);put(DD,[DDVT]);put(DDVT+8,[0x710008]);put(DDVT+0x30,[0x710030]);put(DDVT+0x58,[0x710058]);put(DS,[DSVT]);put(DSVT+8,[0x720008]);put(DSVT+0x18,[0x720018]);return seed

def compare(f,t,args,label,void=False,unsafe=False):
 global native,cursor,allocationIndex,calls,snapshots
 native=True;ctx.fault=0;events.clear();originalEvents.clear();errors.clear();replays.clear();before=bytes(heap);bi=bytes(image);old=(cursor,allocationIndex,len(created),len(freed));out=U();a=(U*len(args))(*args);ok=lib.claw_scene_startup_composition_entry(f,t,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert (not ok and ctx.fault in(1,2))if unsafe else(ok and not ctx.fault and not errors),(label,'native',ctx.fault,errors);expected=raw();ev=list(events);new=(cursor,allocationIndex,len(created),len(freed));createdExpected=list(created);freedExpected=list(freed);native=False;m.u.mem_write(BASE,before);m.u.mem_write(IMAGE_START,bi);cursor,allocationIndex=old[:2];del created[old[2]:];del freed[old[3]:]
 try:value=m.call(f,t,pack(*args),max_instructions=10000000)
 except UcError:assert unsafe,(label,'original fault',hex(m.u.reg_read(UC_X86_REG_EIP)));value=0
 else:assert not unsafe,(label,'original did not fault');assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+4*len(args),(label,'SP')
 if raw()!=expected:raise AssertionError((label,'raw',[(hex(BASE+i if i<SIZE else IMAGE_START+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:20]))
 if ev!=originalEvents:raise AssertionError((label,'events',len(ev),len(originalEvents),next(((i,x[:5],y[:5],x[5]==y[5])for i,(x,y)in enumerate(zip(ev,originalEvents))if x!=y),None)))
 if not void and not unsafe:assert value==out.value,(label,'EAX',hex(value),hex(out.value))
 assert new==(cursor,allocationIndex,len(created),len(freed))and createdExpected==created and freedExpected==freed,(label,'ownership');native=True;calls+=1;snapshots+=len(ev)+1
 if capture and not unsafe:corpus.append((f,t,args,label,out.value,not void,before,bi,expected,createdExpected,list(replays)))
 return out.value
