"""Whole425730 oracle; isolated declared bootstrap/OS transports only."""
import ctypes as C,hashlib,random,struct
from application_startup_build import ROOT,WORK,shared,SOURCES
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
if not (WORK/'libStartup.dylib').exists()or any((ROOT/p).stat().st_mtime>(WORK/'libStartup.dylib').stat().st_mtime for p in SOURCES):shared()
U=C.c_uint32;Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Save(C.Structure):_fields_=[('scene',Host),('bytes',C.c_void_p)]+[(n,U)for n in('empty','file','path','security','count','maxTraversal','maxSteps','fault')]
class Load(C.Structure):_fields_=[('save',Save)]+[(n,U)for n in('directory','maximum','fault')]
class Players(C.Structure):_fields_=[('scene',Host),('saveLoad',C.c_void_p)]+[(n,U)for n in('automatic','compose','maximum','fault')]
class Context(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('graphics','archive','players','messages','fades','light','ambient','music','random')]+[(n,U)for n in('automatic','maximum','fault')]+[('byteContext',C.c_void_p),('bytes',C.c_void_p)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*40),('name',C.c_void_p),('mask',U),('bufferCount',U),('buffers',C.c_void_p*3),('sizes',U*3)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x20000;IS,IN=0x500000,0x48000
APP,WIN,INSTANCE,CMD,AUT,VT,TILES,AUDIO,RECORD,PATH,OLDREZ,OLDAMBIENT=[BASE+x for x in(0x100,0x400,0x440,0x500,0x800,0x1000,0x1100,0x1200,0x2000,0x4800,0x4a00,0x4b00)]
ALLOC=BASE+0x6000
OBJECTS=[(APP,308),(WIN,12),(INSTANCE,16),(CMD,256),(AUT,1200),(VT,32),(TILES,108),(AUDIO,4),(RECORD,0x2648),(PATH,16),(OLDREZ,72),(OLDAMBIENT,48),(BASE+0x4c00,168),(BASE+0x4d00,308)]
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x700000,4096);m.executed.clear();seedImage=bytes(m.u.mem_read(IS,IN));heap=(C.c_uint8*SIZE)();image=(C.c_uint8*IN)()
native=True;events=[];originalEvents=[];records=[];errors=[];cursor=ALLOC;created=[];freed=[];options={};failure={};timeIndex=cursorIndex=stateIndex=0;sourceAliases={};capture=False;corpus=[];calls=snapshots=0;mutation=None;registry={};recordNames={b'player'}
@Lookup
def lookup(_,t,n):
 if t%4:return 0
 if BASE<=t and t+4*n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IS<=t and t+4*n<=IS+IN:return C.addressof(image)+t-IS
 return 0
@Lookup
def byteLookup(_,t,n):
 if BASE<=t and t+n<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if IS<=t and t+n<=IS+IN:return C.addressof(image)+t-IS
 return 0
class MusicGlobals(C.Structure):_fields_=[('driver',U),('ordinal',U),('instance',U)]
class Music(C.Structure):_fields_=[('scene',Host),('bytes',C.c_void_p),('globals',C.c_void_p),('maximum',U),('fault',U)]
class Table(C.Structure):_fields_=[('scene',Host),('allocator',C.c_void_p),('maximum',U),('fault',U),('byteContext',C.c_void_p),('bytes',C.c_void_p)]
class Archive(C.Structure):_fields_=[('table',C.c_void_p),('header',U),('maximum',U)]
host=Host(None,lookup,None,None,None,None);table=Table(host,None,1000000,0,None,None);archive=Archive(C.addressof(table),BASE+0x4c00,1000000);load=Load();players=Players(host,C.addressof(load),0,0,1000000,0);context=Context();context.scene=host;context.players=C.addressof(players);context.automatic=AUT;context.maximum=1000000;context.bytes=C.cast(byteLookup,C.c_void_p).value;musicGlobals=MusicGlobals();music=Music(host,C.cast(byteLookup,C.c_void_p).value,C.addressof(musicGlobals),1000000,0)
lib=C.CDLL(str(WORK/'libStartup.dylib'));lib.claw_application_startup_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
pack=lambda *v:struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def sourceAddress(t):
 for token,(actual,n)in sourceAliases.items():
  if token<=t<token+n:return actual+t-token
 return t
def read(t,n):return C.string_at(lookup(None,t&~3,(n+(t&3)+3)//4)+(t&3),n)if native else bytes(m.u.mem_read(sourceAddress(t),n))
def write(t,b):
 if native:C.memmove(lookup(None,t&~3,(len(b)+(t&3)+3)//4)+(t&3),b,len(b))
 else:m.u.mem_write(sourceAddress(t),b)
def get(t,n=1):return list(struct.unpack('<'+'I'*n,read(t,4*n)))
def put(t,v):write(t,pack(*v))
def text(t):
 b=bytearray()
 while read(t+len(b),1)!=b'\0':b+=read(t+len(b),1)
 return bytes(b)
def raw():
 h=bytearray(bytes(heap)if native else m.u.mem_read(BASE,SIZE));h[AUT-BASE:AUT-BASE+1200]=bytes(1200)
 return bytes(h)+(bytes(image)if native else bytes(m.u.mem_read(IS,IN)))
def fullRaw():return(bytes(heap)+bytes(image))if native else bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(IS,IN))
def state():return hashlib.sha256(raw()).digest(),tuple(created),tuple(freed)
def effect(f,t,a,buffers):
 global cursor,timeIndex,cursorIndex,stateIndex
 if f==0x4f63ec:token=cursor;cursor+=(a[0]+15)&~15;created.append((token,a[0]));return token
 if f==0x4f6428:freed.append(a[0]);return 0
 if f in(0x546df0,0x546a24):
  timeIndex+=1
  if mutation:mutation(f,t,a)
  return(0xffffffe0+timeIndex*17)&0xffffffff
 if f==0x546d54:cursorIndex+=1;return(1-cursorIndex)&0xffffffff
 if f==0x4b5f30:return options.get(a[0],a[1])
 if f==0x4b5e90:
  if buffers:
   data=registry.get(a[0],b'Player'if a[0]==0x525714 else b'')+b'\0';buffers[0][:len(data)]=data;buffers[1][:4]=pack(len(data));return 1
  data=registry.get(a[0],b'')+b'\0';write(a[1],data);put(a[2],[len(data)]);return 1 if len(data)>1 else 0
 if f==0x4f21e0:
  data=bytes(buffers[0]);length=data.index(0);buffers[0][:length]=data[:length].upper();return 0
 if f==0x4a3990:
  at=bytes(buffers[0]).split(b'\0',1)[0].find(text(a[1]));return 0 if at<0 else at+1
 if f==0x4268b0:buffers[0][:4]=pack(PATH);return 0
 if f==0x4f6584:return 0
 if f==0x4f650f:put(t,[get(0x52e1cc)[0]]);return 0
 if f==0x4f6439:put(t,[get(0x52e1cc)[0]]);return t
 if f==0x4ce960:put(t,[VT]);put(t+36,[TILES]);put(t+40,[AUDIO]);return t
 if f in(0x4f5620,0x4f6118,0x4f5cbd):
  put(t,[0x5107bc if f==0x4f5620 else 0x5105c4 if f==0x4f6118 else 0x510054,0,0 if f==0x4f5620 else 17,0,0,0,a[0]]);return t
 if f==0x4f5133:put(t,[0x510224,0,0,0,0,0,a[0]]);return t
 if f==0x4ebf80:put(t+16,[0x5141c0,0,0,0,0]);put(t+8,[0,0]);return t
 if f==0x4b7210:
  put(t,[0x513578,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0]);return t
 if f==0x4c61d0:put(t,[0,0x5136e8,0,0,0,0]);return t
 if f==0x4c6260:put(t,[1]);return 1
 if f==0x402240:
  if not a[0]:return 0
  put(t,[a[0],a[1]]);put(t+36,[1,0,0]);return failure.get(f,1)
 if f==0x49bee0:return RECORD if text(a[0]).lower()in recordNames else 0
 if f==0x428c40:stateIndex+=1;return failure.get((f,stateIndex),failure.get(f,1))
 if f==0x546e70:return 0
 if f==0x546e74:
  hr=failure.get(f,0)
  if not hr:put(a[0],[0x60000000])
  return hr
 if f==0x546e6c:return 0
 if f==0x4f1d90:return 0
 if f==0x42a680:return failure.get(f,0)
 if f==0x4b67f0:return 0
 if f==0x42b140:return failure.get(f,0)
 if mutation:mutation(f,t,a)
 return failure.get(f,1)
def snapshot(f,t,a,mask,buffers):return(f,t,tuple(a),mask,tuple(bytes(b)for b in buffers),state())
@Dep
def dependency(_,qp,user):
 q=qp.contents;a=list(q.arguments[:q.count]);buffers=[(C.c_uint8*q.sizes[i]).from_address(q.buffers[i])for i in range(q.bufferCount)];events.append(snapshot(q.function,q.receiver,a,q.mask,buffers));before=raw();beforeFull=fullRaw();beforeBuffers=[bytes(b)for b in buffers]
 try:
  result=effect(q.function,q.receiver,a,buffers)
  if capture:records.append((q.function,q.receiver,a,result,q.mask,beforeBuffers,[bytes(b)for b in buffers],hashlib.sha256(before).digest(),[(i,y)for i,(x,y)in enumerate(zip(beforeFull,fullRaw()))if x!=y]))
  return result
 except Exception as ex:errors.append(ex);context.fault=1;return 0
COUNTS={0x4b8280:2,0x429e10:2,0x546df0:0,0x546a24:0,0x4a3040:1,0x546d54:1,0x4f63ec:1,0x4f6428:1,0x4b5c50:6,0x4b5f30:2,0x4b5e90:4,0x42b020:0,0x4f21e0:1,0x4a3990:2,0x42a680:0,0x5028ec:4,0x4f650f:0,0x4ce960:0,0x700018:5,0x70001c:0,0x4cf010:1,0x401000:1,0x42cab0:0,0x4b7250:0,0x4b7210:0,0x4268b0:1,0x4b72e0:3,0x4f6584:0,0x42ce90:1,0x42c0b0:1,0x42c640:1,0x4b7f20:1,0x4b67f0:2,0x4b61c0:0,0x493c20:0,0x4ebf80:0,0x4ec010:3,0x4f5cbd:1,0x422890:1,0x4f5249:1,0x4f6439:0,0x4222a0:2,0x48bbb0:0,0x48c030:1,0x48bf70:0,0x4f6118:1,0x4b52a0:3,0x4b55e0:1,0x402270:0,0x4f5192:0,0x4f5133:1,0x402240:2,0x402520:0,0x402570:0,0x42cdc0:1,0x4b3410:0,0x4b3240:2,0x4c61d0:0,0x4c6260:0,0x430590:2,0x4f5d00:0,0x49b840:1,0x49bee0:1,0x4b5f80:1,0x42ce20:1,0x42b900:0,0x42b140:1,0x428c40:4}
COUNTS.update({0x4f1d90:2,0x546e70:0,0x546e74:3,0x546e6c:2})
CDECL={0x4f1d90,0x4a3040,0x4f63ec,0x4f6428,0x4f21e0,0x4a3990,0x401000,0x48bbb0,0x48c030,0x48bf70}
def mapped(t):
 for token,(actual,n)in sourceAliases.items():
  if actual<=t<actual+n:return token+t-actual
 return t
def hook(uc,f,size,user):
 if f==0x4b8280:return
 if context.music and f in(0x4b52a0,0x4b55e0):return
 if context.archive and f in(0x4b7210,0x4b7250,0x4b72e0,0x4b7f20,0x4b67f0,0x4b61c0):return
 if f not in COUNTS:return
 sp=uc.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0]
 #The selected-cache interval is executed as original instructions, not stubs.
 if f==0x4f6439 and 0x426546<=ret<0x4266e0:return
 args=m.read_words(sp+4,COUNTS[f]);t=0 if f in CDECL or f==0x5028ec or 0x546000<=f<0x547000 else uc.reg_read(UC_X86_REG_ECX);a=[mapped(x)for x in args];mask=0;buffers=[];locations=[]
 if f in(0x4f21e0,0x4a3990):mask=1;locations=[(args[0],300)];a[0]=0
 if f==0x4b5e90 and a[0]==0x525714:mask=6;locations=[(args[1],32),(args[2],4)];a[1]=a[2]=0
 if f==0x4b5e90 and a[0]!=0x525714:a[2]=AUT+1196
 if f==0x5028ec:mask=4;locations=[(args[2],256)];a[2]=0
 if f==0x4268b0:mask=1;locations=[(args[0],4)];a[0]=0
 if f==0x4f6584 and 0x425f00<=ret<0x425f80:mask=256;locations=[(t,4)];t=0
 buffers=[bytearray(uc.mem_read(p,n))for p,n in locations];originalEvents.append(snapshot(f,t,a,mask,buffers));value=effect(f,t,a,buffers)
 for(p,n),b in zip(locations,buffers):uc.mem_write(p,bytes(b))
 if f==0x4a3990:value=0 if not value else args[0]+value-1
 if f==0x4268b0:value=args[0]
 pop=0 if f in CDECL else COUNTS[f]*4
 uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_EIP,ret);uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(seed=0,command=b'',old=False):
 global native,cursor,timeIndex,cursorIndex,stateIndex,mutation
 native=True;C.memmove(heap,random.Random(seed).randbytes(SIZE),SIZE);C.memmove(image,seedImage,IN);cursor=ALLOC;timeIndex=cursorIndex=stateIndex=0;mutation=None;created.clear();freed.clear();options.clear();failure.clear();registry.clear();recordNames.clear();recordNames.add(b'player');context.fault=0;players.fault=0
 put(APP,[0]*77);put(APP+4,[WIN,INSTANCE]);put(WIN,[0,0x12345678,INSTANCE]);put(INSTANCE+12,[0x11223344]);write(CMD,command+b'\0');write(PATH,b'CLAW.REZ\0');put(APP+16,[1,1]);put(APP+0x118,[1,1,0,1,1]);put(VT+24,[0x700018,0x70001c]);put(RECORD+4,[0]);put(0x546df0,[0x546df0]);put(0x546a24,[0x546a24]);put(0x546d54,[0x546d54]);put(0x546e70,[0x546e70]);put(0x546e74,[0x546e74]);put(0x546e6c,[0x546e6c]);put(0x527130,[155,299,399]);put(0x537204,[0]);put(0x53725c,[0]);put(0x52e1cc,[0x52e1c4]);put(0x52e1bc,[1,0,0,0]);
 if old:put(APP+0x34,[OLDREZ]);put(APP+0x5c,[OLDAMBIENT])
 sourceAliases.clear()
 for offset,stackOffset,n in [(0,-0x4b0,32),(32,-0x42c,300),(332,-0x138,300),(632,-0x238,256),(888,-0x4e4,4),(892,-0x4c4,4),(896,-0x490,100),(996,-0x300,100),(1096,-0x29c,100),(1196,-0x4e4,4)]:sourceAliases[AUT+offset]=(m.stack+stackOffset,n)
def compare(label=''):
 global native,cursor,timeIndex,cursorIndex,stateIndex,calls,snapshots
 native=True;events.clear();originalEvents.clear();records.clear();errors.clear();context.fault=0;before=bytes(heap)+bytes(image);beforeRaw=raw();start=(cursor,list(created),list(freed));timeIndex=cursorIndex=stateIndex=0;bindings=(bytes(players),bytes(load),bytes(context.scene));out=U();args=(U*2)(WIN,CMD)
 assert lib.claw_application_startup_entry(0x425730,APP,args,2,C.byref(context),dependency,None,C.byref(out))and not context.fault and not errors,(label,'native',context.fault,errors)
 expected=raw();expectedEvents=list(events);end=(cursor,list(created),list(freed),timeIndex,cursorIndex,stateIndex);native=False;cursor=start[0];created[:]=start[1];freed[:]=start[2];timeIndex=cursorIndex=stateIndex=0;m.u.mem_write(BASE,before[:SIZE]);m.u.mem_write(IS,before[SIZE:]);m.u.mem_write(0,pack(0x98765432))
 for token,(actual,n)in sourceAliases.items():m.u.mem_write(actual,before[token-BASE:token-BASE+n])
 value=m.call(0x425730,APP,pack(WIN,CMD),max_instructions=10000000)
 assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+12,(label,'RET8')
 assert value==out.value,(label,'EAX',value,out.value)
 assert raw()==expected,(label,'raw',[(hex(BASE+i if i<SIZE else IS+i-SIZE),x,y)for i,(x,y)in enumerate(zip(raw(),expected))if x!=y][:16])
 assert originalEvents==expectedEvents,(label,'events',[(i,x[:5],y[:5],x[5:]==y[5:])for i,(x,y)in enumerate(zip(expectedEvents,originalEvents))if x!=y][:3],len(events),len(originalEvents))
 assert end==(cursor,list(created),list(freed),timeIndex,cursorIndex,stateIndex),(label,'ownership/clock');assert bindings==(bytes(players),bytes(load),bytes(context.scene)),(label,'borrowed contexts');native=True;calls+=1;snapshots+=len(events)+1
 if capture:corpus.append((label,out.value,before,expected,start[1],list(records),int(bool(context.archive))|2*int(bool(context.music))))
 return out.value
