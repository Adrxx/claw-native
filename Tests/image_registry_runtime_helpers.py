"""Original registry graph oracle; directory/map/image transport is explicit."""
import ctypes as C,gzip,hashlib,io,json,random,struct,subprocess,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/image-registry-agent';U=C.c_uint32
ADAPTED_ENTRIES={0x4f63ec,0x4f6428,0x4f6286,0x4b68e0,0x4b6900,0x4b6920,0x4b6940,0x4b6960,0x4b6980,0x4b61b0,0x4b61c0,0x4b6230,0x4b7540,0x4b68c0,0x4f62a8,0x4f5db6,0x4d2410,0x4d2540,0x4ce8e0,0x4d27a0,0x4ce3d0,0x4d0096,0x4ce37e}
sources=['ImageRegistryRuntime.cpp','AnimationEngine.cpp','CArrayRuntime.cpp','GameImageRuntime.cpp','SpriteGeometry.cpp','PIDSurfaceRaster.cpp','PIDBlitter.cpp']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/f)for f in sources],'-o',str(WORK/'libImageRegistry.dylib')],check=True)
lib=C.CDLL(str(WORK/'libImageRegistry.dylib'))
class Args(C.Structure):_fields_=[('words',U*5),('count',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Allocate=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,Call);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class ArrayContext(C.Structure):_fields_=[('scene',Host)]+[(x,U)for x in ('composeAllocator','globalNewHandler','fault','crtNewMode','smallBlockThreshold','heapHandle','heapAllocFunction')]
class Context(C.Structure):_fields_=[('scene',Host),('arrays',C.POINTER(ArrayContext)),('images',C.c_void_p),('imageHost',C.c_void_p),('fault',U),('eventNameBytes',U)]
lib.claw_image_registry_entry.argtypes=[U,U,Args,C.POINTER(Context),C.POINTER(U)];lib.claw_carray_defaults.argtypes=[C.POINTER(ArrayContext)]
BASE,SIZE=0x3000000,0x200000;CONTROLLER=BASE+0x1000;SCENE=BASE+0x1200;PREFIX=BASE+0x1400;SEPARATOR=BASE+0x1800;RAW=BASE+0x80000;ALLOC=BASE+0x100000
heap=(C.c_uint8*SIZE)();m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;u.mem_map(0,4096);u.mem_map(BASE,SIZE);m.executed.clear()
replay=io.BytesIO();replayWriter=gzip.GzipFile(fileobj=replay,mode='wb',mtime=0);replayCases=0
imageBase,imageEnd,_=next(v for v in u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageBase+1)).from_buffer_copy(bytes(u.mem_read(imageBase,imageEnd-imageBase+1)))
native=True;ctx=Context();array=ArrayContext();events=[];errors=[];cursor=ALLOC;treeCursor=BASE+0x2000;slotCursor=BASE+0x70000;maps={};directories={};types={};files={};payloads={};freed=[];allocationFailures=[];imageFailures=set();missingPayloads=set();calls=eventCount=0;loadedImages=[];resourceResults=[];contextFaults=0;unsafeStop=0
def read(t,n):return bytes(heap[t-BASE:t-BASE+n])if native and BASE<=t and t+n<=BASE+SIZE else bytes(u.mem_read(t,n))
def write(t,b):
 assert BASE<=t and t+len(b)<=BASE+SIZE,(hex(t),len(b))
 C.memmove(C.addressof(heap)+t-BASE,b,len(b))if native else u.mem_write(t,b)
def words(t,n=1):return list(struct.unpack('<'+'I'*n,read(t,4*n)))
def put(t,v):write(t,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
def text(t):return read(t,512).split(b'\0',1)[0]
def snap():return hashlib.sha256((bytes(heap)if native else bytes(u.mem_read(BASE,SIZE)))+struct.pack('<I',ctx.eventNameBytes if native else m.read_words(0x543174,1)[0])).digest()
def log(e):events.append((e,snap()))
@Lookup
def lookup(_,t,n):
 if t%4:return None
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageBase<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageBase
 return None
@Allocate
def allocate(_,n):
 global cursor
 log(('allocate',n))
 if allocationFailures and allocationFailures[0]==n:allocationFailures.pop(0);return 0
 result=cursor;cursor+=max(16,(n+15)&~15);assert cursor<BASE+SIZE,(hex(cursor),n);return result
@Free
def free(_,t):log(('free',t));freed.append(t)
@Clock
def clock(_):errors.append('unexpected clock');return 0
def effect(fn,t,a):
 global slotCursor
 log(('call',fn,t,a,text(a[0])if fn in(0x4f6286,0x4f62a8,0x4f5db6)else None))
 if fn==0x4b68e0:return directories.get(t,([],[]))[0][0]if directories.get(t,([],[]))[0]else 0
 if fn==0x4b6900:
  values=directories[t][0];i=values.index(a[0])+1;return values[i]if i<len(values)else 0
 if fn==0x4b6920:return directories[t][1][0]if directories[t][1]else 0
 if fn==0x4b6940:
  values=directories[t][1];i=values.index(a[0])+1;return values[i]if i<len(values)else 0
 if fn==0x4b6960:return types[a[0]][0]if types[a[0]]else 0
 if fn==0x4b6980:
  values=types[files[a[0]][0]];i=values.index(a[0])+1;return values[i]if i<len(values)else 0
 if fn==0x4b61b0:return files[t][1]
 if fn==0x4b61c0:
  if t in missingPayloads:return 0
  write(RAW,payloads[t]);resourceResults.append((t,len(payloads[t]),hashlib.sha256(payloads[t]).hexdigest()));return RAW
 if fn==0x4b6230:return 0
 if fn==0x4b7540:return t
 if fn==0x4b68c0:
  requested=text(a[0]);return next((node for node in directories[t][0]if text(words(node)[0])==requested),0)
 if fn==0x4f6286:
  slot=maps.get(t,{}).get(text(a[0]));return words(slot)[0]if slot else 0
 if fn==0x4f62a8:
  entries=maps.setdefault(t,{});key=text(a[0]);slot=entries.get(key)
  if slot is None:slot=slotCursor;slotCursor+=4;entries[key]=slot;put(slot,[0]);put(t+12,[words(t+12)[0]+1])
  return slot
 if fn==0x4f5db6:
  entries=maps.setdefault(t,{});key=text(a[0]);slot=entries.pop(key,None)
  if slot is not None:put(t+12,[words(t+12)[0]-1])
  return 1 if slot else 0
 if fn in(0x4d2410,0x4d2540):
  # Image initializer is an explicit finite service. The frozen GameImage
  # decoder/physical surface graph is independently proved, not substituted
  # by invented pixels. Full raw payload/args/boundary snapshots are retained.
  loadedImages.append((words(t+4)[0],a,hashlib.sha256(read(a[0],a[2])).hexdigest()))
  return 0 if words(t+4)[0]in imageFailures else 1
 if fn==0x4ce8e0:
  # Explicit image-resource deletion boundary, including source-class marker.
  put(t,[0x50becc]);free(None,t);return t
 if fn==0x4d27a0:return 0 if words(t+4)[0]in imageFailures else 1
 if fn==0x4ce3d0:return 0x12345678 # Explicit frozen file-image creation boundary.
 raise AssertionError(('unrepresented',hex(fn),hex(t),a))
@Invoke
def invoke(_,c):
 try:return effect(c.function,c.receiver,tuple(c.arguments[:c.argumentCount]))
 except BaseException as e:errors.append(e);ctx.fault=1;return 0
host=Host(None,lookup,allocate,free,invoke,clock);ctx.scene=host;array.scene=host;ctx.arrays=C.pointer(array)
def returned(pop,value=0):
 sp=u.reg_read(UC_X86_REG_ESP);ret=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 if unsafeStop and address==unsafeStop:u.emu_stop();return
 sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
 if address==0x4f63ec:returned(0,allocate(None,m.read_words(sp+4,1)[0]));return
 if address==0x4f6428:free(None,m.read_words(sp+4,1)[0]);returned(0);return
 if address==0x4f6286:
  name,out=m.read_words(sp+4,2);value=effect(address,receiver,(name,));m.write_words(out,[value]);returned(8,1 if value else 0);return
 counts={0x4b68e0:0,0x4b6900:1,0x4b6920:0,0x4b6940:1,0x4b6960:1,0x4b6980:1,0x4b61b0:0,0x4b61c0:0,0x4b6230:0,0x4b7540:0,0x4b68c0:1,0x4f62a8:1,0x4f5db6:1,0x4d2410:4,0x4d2540:3,0x4ce8e0:1,0x4d27a0:2,0x4ce3d0:3}
 if address in counts:
  n=counts[address];returned(n*4,effect(address,receiver,tuple(m.read_words(sp+4,n))))
u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0,ani=False):
 global native,cursor,treeCursor,slotCursor,maps,directories,types,files,payloads,freed,allocationFailures,imageFailures,missingPayloads,loadedImages,resourceResults,events,errors
 native=True;pattern=random.Random(seed).randbytes(4096);write(BASE,pattern*(SIZE//4096));cursor=ALLOC;treeCursor=BASE+0x2000;slotCursor=BASE+0x70000;maps={};directories={};types={};files={};payloads={};freed=[];allocationFailures=[];imageFailures=set();missingPayloads=set();loadedImages=[];resourceResults=[];events=[];errors=[];ctx.fault=ctx.eventNameBytes=0;array.fault=0;lib.claw_carray_defaults(C.byref(array));put(CONTROLLER,[0x513ad8 if ani else 0x513b88,0,0,SCENE]);put(CONTROLLER+28,[0]);put(SCENE+0x28,[BASE+0x1900]);write(PREFIX,b'LEVEL\0');write(SEPARATOR,b'_\0')
def treeAlloc(n):
 global treeCursor
 t=treeCursor;treeCursor+=max(16,(n+15)&~15);assert treeCursor<BASE+0x70000;return t
def nameToken(value):
 t=treeAlloc(len(value)+1);write(t,value.encode()+b'\0');return t
def makeTree(name,children=(),leaves=()):
 group=treeAlloc(64);put(group,[nameToken(name)]);kids=[makeTree(n,c,f)for n,c,f in children];typeNodes=[]
 for typeValue in sorted({typeValue for _,typeValue,_,_ in leaves}):
  typeToken=treeAlloc(32);put(typeToken,[typeValue]);typeNodes.append(typeToken);values=[]
  for leaf,ty,data,storedID in leaves:
   if ty!=typeValue:continue
   resource=treeAlloc(96);put(resource,[nameToken(leaf),storedID,typeToken,0,0,len(data)]);files[resource]=(typeToken,ty);payloads[resource]=data;values.append(resource)
  types[typeToken]=values
 directories[group]=(kids,typeNodes);return group
def compare(fn,t,a,label,void=False):
 global native,events,cursor,maps,slotCursor,freed,allocationFailures,loadedImages,resourceResults,calls,eventCount,replayCases
 before=bytes(heap);old=(cursor,{k:dict(v)for k,v in maps.items()},slotCursor,freed[:],allocationFailures[:],loadedImages[:],resourceResults[:]);oldEvent=ctx.eventNameBytes;events=[];ctx.fault=array.fault=0;args=Args();args.count=len(a);args.words[:len(a)]=a;result=U()
 ok=lib.claw_image_registry_entry(fn,t,args,C.byref(ctx),C.byref(result));assert not errors,(label,errors);assert ok and not ctx.fault,(label,'native',ok,ctx.fault)
 expected=bytes(heap);expectedEvent=ctx.eventNameBytes;expectedEvents=events[:];owned=(cursor,{k:dict(v)for k,v in maps.items()},slotCursor,freed[:],allocationFailures[:],loadedImages[:],resourceResults[:]);native=False;u.mem_write(BASE,before);m.write_words(0x543174,[oldEvent]);cursor,maps,slotCursor,freed,allocationFailures,loadedImages,resourceResults=old;events=[]
 original=m.call(fn,t,struct.pack('<'+'I'*len(a),*a));actual=bytes(u.mem_read(BASE,SIZE))
 assert actual==expected,(label,'heap',[(hex(BASE+i),hex(x),hex(y))for i,(x,y)in enumerate(zip(expected,actual))if x!=y][:20])
 assert events==expectedEvents,(label,'event order/snapshots',[(e,es==s)for (e,es),(v,s)in zip(events,expectedEvents)if e!=v or es!=s][:4],len(events),len(expectedEvents))
 assert owned==(cursor,maps,slotCursor,freed,allocationFailures,loadedImages,resourceResults),(label,'service state')
 assert expectedEvent==m.read_words(0x543174,1)[0],(label,'ANI event length')
 if not void:assert original==result.value,(label,'EAX',hex(original),hex(result.value))
 if not expectedEvents:
  packed=[0]*5;packed[:len(a)]=a;replayWriter.write(struct.pack('<12I',fn,t,*packed,len(a),oldEvent,expectedEvent,original,int(void))+before+actual);replayCases+=1
 native=True;ctx.eventNameBytes=expectedEvent;calls+=1;eventCount+=len(events);return result.value
def readREZ():
 b=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';out={};order=[]
 def w(o):return struct.unpack_from('<I',b,o)[0]
 def walk(at,size,path=()):
  end=at+size
  while at<end:
   kind,target,length=w(at),w(at+4),w(at+8);start=at+(16 if kind else 28);nul=b.index(0,start,end);name=b[start:nul].decode('ascii')
   if kind:walk(target,length,path+(name,));at=nul+1
   else:
    ext=b[at+20:at+24].split(b'\0')[0][::-1].decode('ascii');key='/'.join(path+(name+'.'+ext,));out[key]=(b[target:target+length],w(at+16));order.append(key);at=nul+2
 walk(w(131),w(135));return out,order
def rezTree(assets,order,prefix,name=''):
 leaves=[];groups={}
 for path in order:
  if not path.startswith(prefix):continue
  rest=path[len(prefix):]
  if '/'in rest:groups.setdefault(rest.split('/')[0],None)
  else:
   leaf,ext=rest.rsplit('.',1);data,idValue=assets[path];typeValue=int.from_bytes(ext.encode()[::-1]+b'\0','little');leaves.append((leaf,typeValue,data,idValue))
 return (name,[rezTree(assets,order,prefix+n+'/',n)for n in groups],leaves)
def rootProfile(name='PROFILE'):
 root=treeAlloc(112);put(root,[0x513cf8,0,0,SCENE]);put(root+16,[0x5108fc,0,0,0,0]);put(root+100,[99999,0]);write(PREFIX,name.encode()+b'\0');compare(0x4d0380,root,[PREFIX],'root-name');return root
def failure(fn,t,a,label):
 global native,events,cursor,maps,slotCursor,freed,allocationFailures,loadedImages,resourceResults,contextFaults,unsafeStop
 before=bytes(heap);old=(cursor,{k:dict(v)for k,v in maps.items()},slotCursor,freed[:],allocationFailures[:],loadedImages[:],resourceResults[:]);oldEvent=ctx.eventNameBytes;events=[];ctx.fault=array.fault=0;args=Args();args.count=len(a);args.words[:len(a)]=a;result=U();assert lib.claw_image_registry_entry(fn,t,args,C.byref(ctx),C.byref(result))==0 and ctx.fault
 expected=bytes(heap);expectedEvents=events[:];native=False;u.mem_write(BASE,before);m.write_words(0x543174,[oldEvent]);cursor,maps,slotCursor,freed,allocationFailures,loadedImages,resourceResults=old;events=[]
 unsafeStop=0x4d0096 if fn==0x4cff40 else 0x4ce37e
 try:m.call(fn,t,struct.pack('<'+'I'*len(a),*a))
 except (UcError,AssertionError):assert u.reg_read(UC_X86_REG_EIP)==unsafeStop,(label,'unexpected original failure point')
 else:raise AssertionError((label,'original unexpectedly returned'))
 finally:unsafeStop=0;m.write_words(0,[0])
 assert bytes(u.mem_read(BASE,SIZE))==expected and expectedEvents==events,(label,'fault heap/events')
 native=True;ctx.fault=array.fault=0;contextFaults+=1
