"""Whole retail path admission with real source CString ctor/destructor bodies.
Directory/OpenFile/formatter/mode are isolated typed transports, not live OS.
"""
import ctypes as C,hashlib,random,struct
from application_archive_path_build import ROOT,WORK,SOURCES,shared
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
if not(WORK/'libArchivePath.dylib').exists()or any((ROOT/p).stat().st_mtime>(WORK/'libArchivePath.dylib').stat().st_mtime for p in SOURCES):shared()
U=C.c_uint32;Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Lifecycle(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('display','graphics','audio','palette','world','image')]+[('maximum',U),('fault',U)]
class Fade(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('descriptorWord','descriptorToken','maximum','fault')]
class Blend(C.Structure):_fields_=[('fade',C.c_void_p)]+[(n,U)for n in('temporary','empty','capture')]
class Strings(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('lifecycle','allocation','arrays','byteContext','bytes')]+[('maximum',U),('fault',U)]
class Context(C.Structure):_fields_=[('scene',Host),('strings',C.c_void_p)]+[(n,U)for n in('automatic','openFile','maximum','fault')]+[('byteContext',C.c_void_p),('bytes',C.c_void_p)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('mask',U),('bufferCount',U),('buffers',C.c_void_p*3),('sizes',U*3),('name',C.c_void_p)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x10000;IS,IN=0x500000,0x48000
APP,AUT,PROBE,EMPTY,PATH,ALLOC=[BASE+x for x in(0x100,0x400,0x800,0xa00,0xb00,0x1000)]
OBJECTS={APP:308,AUT:268,PROBE:136,EMPTY:4,PATH:32}
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x700000,4096);m.executed.clear();seedImage=bytes(m.u.mem_read(IS,IN));heap=(C.c_uint8*SIZE)();image=(C.c_uint8*IN)()
native=True;objects={};live={};created=[];freed=[];cursor=ALLOC;events=[];oevents=[];records=[];errors=[];directory=b'C:\\CLAW';drive=ord('D');directoryReturn=None;fileResults=[];fileIndex=0;modeReturn=1;mutation=None;capture=False;corpus=[];calls=snapshots=0;sourceAliases={};currentRoot=0
def ptr(t,n):
 if IS<=t and t+n<=IS+IN:return C.addressof(image)+t-IS
 for start,size in objects.items():
  if start<=t and t+n<=start+size and(start<ALLOC or start in live):return C.addressof(heap)+t-BASE
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,4*n)if not t%4 else 0
@Lookup
def byteLookup(_,t,n):return ptr(t,n)
host=Host(None,lookup,None,None,None,None);fade=Fade();fade.scene=host;life=Lifecycle();life.scene=host;blend=Blend(C.addressof(fade),0,0x52e1c4,0);strings=Strings();strings.scene=host;strings.lifecycle=C.addressof(life);strings.allocation=C.addressof(blend);strings.bytes=C.cast(byteLookup,C.c_void_p).value;strings.maximum=1000000;context=Context(host,C.addressof(strings),AUT,PROBE,1000000,0,None,C.cast(byteLookup,C.c_void_p).value)
lib=C.CDLL(str(WORK/'libArchivePath.dylib'));lib.claw_application_archive_path_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def sourceAddress(t):
 for token,(actual,n)in sourceAliases.items():
  if token<=t<token+n:return actual+t-token
 return t
def read(t,n):return C.string_at(ptr(t,n),n)if native else bytes(m.u.mem_read(sourceAddress(t),n))
def write(t,b):
 if native:C.memmove(ptr(t,len(b)),b,len(b))
 else:m.u.mem_write(sourceAddress(t),b)
def get(t,n=1):return list(struct.unpack('<'+'I'*n,read(t,4*n)))
def put(t,v):write(t,pack(*v))
def text(t):
 b=bytearray()
 while read(t+len(b),1)!=b'\0':b+=read(t+len(b),1)
 return bytes(b)
def fullRaw():return bytes(heap)+bytes(image)if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IS,IN))
def raw():
 b=bytearray(fullRaw());b[AUT-BASE:AUT-BASE+268]=bytes(268);b[PROBE-BASE:PROBE-BASE+136]=bytes(136);return bytes(b)
def state():return hashlib.sha256(raw()).digest(),tuple(created),tuple(freed),tuple(sorted(live.items()))
def allocation(size):
 global cursor
 p=cursor;cursor+=(size+15)&~15;objects[p]=size;live[p]=size;created.append((p,size));return p
def free(t):freed.append(t);live.pop(t,None)
def formatted(destination,content):
 #The whole MFC formatter is a declared service. Its fixture owns valid
 #CString output allocation/refcount state; no formatter body is claimed.
 old=get(destination)[0]
 if old!=get(0x52e1cc)[0]:
  refs=(get(old-12)[0]-1)&0xffffffff;put(old-12,[refs])
  if not refs or refs&0x80000000:free(old-12)
 p=allocation(len(content)+13);put(p,[1,len(content),len(content)]);write(p+12,content+b'\0');put(destination,[p+12])
def effect(f,t,a,buffers):
 global fileIndex
 if f==0x4f63ec:return allocation(a[0])
 if f==0x4f6428:free(a[0]);return 0
 if f==0x5469e4:return len(text(a[0]))
 if f==0x546a28:
  if directoryReturn==0:return 0
  buffers[0][:len(directory)+1]=directory+b'\0';return len(directory)if directoryReturn is None else directoryReturn
 if f==0x42b020:return drive
 if f==0x4f4f58:
  fmt=text(a[1]);name=text(a[3]);cwd=bytes(buffers[0]).split(b'\0',1)[0]if buffers else None
  if fmt==b'%s\\%s':content=cwd+b'\\'+name
  else:
   assert fmt.startswith(b'%c:\\')and fmt.endswith(b'%s'),fmt
   content=bytes([a[2]&255])+fmt[2:-2]+name
  formatted(a[0],content);return 0
 if f==0x546a30:
  which=fileIndex;fileIndex+=1;value=fileResults[which]if which<len(fileResults)else 0;buffers[0][:136]=bytes((which+i)&255 for i in range(136))
  if mutation:mutation(f,t,a)
  return value
 if f==0x42ce90:
  if mutation:mutation(f,t,a)
  return modeReturn
 if f==0x429e10:return 0
 raise AssertionError(('service',hex(f),hex(t),a))
def event(f,t,a,mask,buffers):return(f,t,tuple(a),mask,tuple(bytes(b)for b in buffers),state())
@Dep
def dependency(_,qp,user):
 q=qp.contents;a=list(q.arguments[:q.count]);buffers=[(C.c_uint8*q.sizes[i]).from_address(q.buffers[i])for i in range(q.bufferCount)];events.append(event(q.function,q.receiver,a,q.mask,buffers));before=fullRaw();beforeBuffers=[bytes(b)for b in buffers];oldLive=dict(live)
 try:
  value=effect(q.function,q.receiver,a,buffers)
  if capture:records.append((q.function,q.receiver,a,value,q.mask,beforeBuffers,[bytes(b)for b in buffers],hashlib.sha256(rawBefore(before)).digest(),[(i,y)for i,(x,y)in enumerate(zip(before,fullRaw()))if x!=y],[(p,n)for p,n in live.items()if p not in oldLive],[p for p in oldLive if p not in live]))
  return value
 except Exception as ex:errors.append(ex);context.fault=1;return 0
def rawBefore(b):
 b=bytearray(b);b[AUT-BASE:AUT-BASE+268]=bytes(268);b[PROBE-BASE:PROBE-BASE+136]=bytes(136);return bytes(b)
COUNTS={0x4f63ec:1,0x4f6428:1,0x5469e4:1,0x5469e8:1,0x546a28:2,0x546a30:3,0x42b020:0,0x4f4f58:4,0x42ce90:1,0x429e10:2}
CDECL={0x4f63ec,0x4f6428,0x4f4f58}
def hook(uc,f,size,user):
 if f not in COUNTS:return
 sp=uc.reg_read(UC_X86_REG_ESP);a=m.read_words(sp+4,COUNTS[f]);t=0 if f in CDECL or 0x546000<=f<0x547000 else uc.reg_read(UC_X86_REG_ECX);mask=0;locations=[]
 if f==0x5469e8:
  put(a[0],[(get(a[0])[0]-1)&0xffffffff]);value=get(a[0])[0]
 else:
  if f==0x546a28:mask=2;locations=[(a[1],256)];a[1]=0
  if f==0x546a30:mask=2;locations=[(a[1],136)];a[1]=0
  if f==0x4f4f58 and a[1]==0x525f78:mask=4;locations=[(a[2],256)];a[2]=0
  buffers=[bytearray(uc.mem_read(p,n))for p,n in locations];oevents.append(event(f,t,a,mask,buffers));value=effect(f,t,a,buffers)
  for(p,n),b in zip(locations,buffers):uc.mem_write(p,bytes(b))
 pop=0 if f in CDECL else 4*COUNTS[f];uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0):
 global native,objects,live,cursor,directory,drive,directoryReturn,fileIndex,fileResults,modeReturn,mutation
 native=True;objects=dict(OBJECTS);live={};created.clear();freed.clear();cursor=ALLOC;directory=b'C:\\CLAW';drive=ord('D');directoryReturn=None;fileIndex=0;fileResults=[];modeReturn=1;mutation=None;context.fault=strings.fault=fade.fault=life.fault=0;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,seedImage,IN);put(APP,[0]*77);put(APP+0xf8,[0x52e1c4]*3);put(EMPTY,[0x52e1c4]);write(PATH,b'C:\\CLAW\\CLAW.REZ\0');put(0x52e1c8,[0x52e1b8]);put(0x52e1cc,[0x52e1c4]);put(0x52e1b8,[0xffffffff,0,0]);write(0x52e1c4,b'\0');put(0x53724c,[0]);put(0x537250,[0]);
 for p in(0x5469e4,0x5469e8,0x546a28,0x546a30):put(p,[p])
 sourceAliases.clear();sourceAliases.update({AUT:(m.stack-0x10c,256),AUT+256:(m.stack-0x120,12),PROBE:(m.stack-0x1c0,136)})
def compare(f=0x42cab0,a=(),label=''):
 global native,cursor,fileIndex,objects,live,calls,snapshots,currentRoot
 native=True;currentRoot=f;context.fault=0;events.clear();oevents.clear();records.clear();errors.clear();fileIndex=0;before=fullRaw();initial=(cursor,dict(objects),dict(live),list(created),list(freed));bindings=[bytes(x)for x in(strings,blend,fade,life)];out=U();args=(U*len(a))(*a)
 assert lib.claw_application_archive_path_entry(f,APP,args,len(a),C.byref(context),dependency,None,C.byref(out))and not context.fault and not errors,(label,'native',context.fault,errors)
 expected=raw();expectedEvents=list(events);owned=(cursor,dict(objects),dict(live),list(created),list(freed),fileIndex);native=False;cursor,objects,live,cr,fr=initial;created[:]=cr;freed[:]=fr;fileIndex=0;m.u.mem_write(BASE,before[:SIZE]);m.u.mem_write(IS,before[SIZE:]);m.u.mem_write(0,pack(0x98765432));
 if f==0x48c190:sourceAliases[PROBE]=(m.stack-136,136)
 for token,(actual,n)in sourceAliases.items():m.u.mem_write(actual,before[token-BASE:token-BASE+n])
 result=m.call(f,APP,pack(*a),max_instructions=10000000)
 assert result==out.value and m.u.reg_read(UC_X86_REG_ESP)==m.stack+4,(label,'EAX/cdecl',result,out.value)
 assert raw()==expected,(label,'raw',[(hex(BASE+i if i<SIZE else IS+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:12])
 assert expectedEvents==oevents,(label,'events',[(i,x[:5],y[:5],x[5:]==y[5:])for i,(x,y)in enumerate(zip(expectedEvents,oevents))if x!=y][:2],len(expectedEvents),len(oevents))
 assert owned==(cursor,objects,live,list(created),list(freed),fileIndex),(label,'ownership');assert bindings==[bytes(x)for x in(strings,blend,fade,life)],(label,'borrowed bindings');native=True;calls+=1;snapshots+=len(events)+1
 if capture:corpus.append((f,list(a),out.value,before,expected,initial[2],list(records)))
 return out.value
