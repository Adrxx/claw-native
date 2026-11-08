"""Raw tile oracle; only physical allocation/free are adapted in factories."""
import ctypes as C, hashlib, json, random, struct, subprocess, zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UcError
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/'work/raw-tile-description-agent'; WORK.mkdir(exist_ok=True)
U=C.c_uint32
sources=['RawTileDescriptionRuntime.cpp','TileCollision.cpp','WorldFileRuntime.cpp','WorldPlaneRuntime.cpp','CArrayRuntime.cpp','SpatialGridRuntime.cpp','SceneCameraRuntime.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp']
library=WORK/'libRawTile.dylib'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',*[str(ROOT/'Sources'/s) for s in sources],'-o',str(library)],check=True)
lib=C.CDLL(str(library))
class Args(C.Structure): _fields_=[('words',U*4),('count',U)]
class SceneCall(C.Structure): _fields_=[('function',U),('receiver',U),('arguments',U*4),('argumentCount',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U); Allocate=C.CFUNCTYPE(U,C.c_void_p,U); Free=C.CFUNCTYPE(None,C.c_void_p,U); Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall); Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure): _fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Context(C.Structure): _fields_=[('scene',Host),('arrays',C.c_void_p),('composeSpatial',U),('fault',U)]
lib.claw_raw_tile_entry.argtypes=[U,U,Args,Host,C.POINTER(U),C.POINTER(U)]
lib.claw_raw_tile_virtual.argtypes=[U,U,Args,Host,C.POINTER(U),C.POINTER(U)]
lib.claw_raw_tile_function.argtypes=[U,U]
lib.claw_world_file_entry.argtypes=[U,U,Args,C.POINTER(Context),C.c_void_p,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x10000; DESC=BASE+0x1000; RECORD=BASE+0x2000; MASK=BASE+0x8000; OUT=BASE+0x400
heap=(C.c_uint8*SIZE)(); m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE'); u=m.u; u.mem_map(0,4096); u.mem_map(BASE,SIZE); m.executed.clear()
imageStart,imageEnd,_=next(r for r in u.mem_regions() if r[0]==0x400000)
imageBefore=hashlib.sha256(bytes(u.mem_read(imageStart,imageEnd-imageStart+1))).digest(); imageWrites=[]
def imageWrite(uc,access,address,size,value,user):
 if imageStart<=address<=imageEnd:imageWrites.append((address,size,value))
u.hook_add(UC_HOOK_MEM_WRITE,imageWrite)
rng=random.Random(0x4cdef0); native=True; errors=[]; events=[]; cursor=BASE+0x4000; calls=eventCount=0; faults=0; functions={}; originalSP=set(); restricted=None
replay=(WORK/'sanitizer-replay.bin').open('wb'); replayCases=0
def snapshot(): return hashlib.sha256(bytes(heap) if native else bytes(u.mem_read(BASE,SIZE))).hexdigest()
def write(t,b):
 assert BASE<=t and t+len(b)<=BASE+SIZE
 C.memmove(C.addressof(heap)+t-BASE,b,len(b)) if native else u.mem_write(t,b)
def put(t,words): write(t,struct.pack('<'+'I'*len(words),*(x&0xffffffff for x in words)))
def read(t,n): return bytes(heap[t-BASE:t-BASE+n]) if native else bytes(u.mem_read(t,n))
def words(t,n=1): return list(struct.unpack('<'+'I'*n,read(t,4*n)))
@Lookup
def lookup(_,t,n):
 if t%4 or not(BASE<=t and t+n*4<=BASE+SIZE): return None
 if restricted is not None and not any(a<=t and t+n*4<=b for a,b in restricted): return None
 return C.addressof(heap)+t-BASE
@Allocate
def allocate(_,n):
 global cursor
 events.append((('allocate',n),snapshot())); result=cursor; cursor+=max(16,(n+15)&~15)
 assert cursor<BASE+0x8000
 return result
@Free
def free(_,t): events.append((('free',t),snapshot()))
@Invoke
def invoke(_,c): errors.append(('unexpected service',hex(c.function))); return 0
@Clock
def clock(_): errors.append('unexpected clock'); return 0
host=Host(None,lookup,allocate,free,invoke,clock)
def returned(value):
 sp=u.reg_read(UC_X86_REG_ESP); ret=m.read_words(sp,1)[0]; u.reg_write(UC_X86_REG_EAX,value); u.reg_write(UC_X86_REG_ESP,sp+4); u.reg_write(UC_X86_REG_EIP,ret)
def hook(uc,address,size,user):
 sp=u.reg_read(UC_X86_REG_ESP)
 if address==0x4f63ec: returned(allocate(None,m.read_words(sp+4,1)[0]))
 elif address==0x4f6428: free(None,m.read_words(sp+4,1)[0]); returned(0)
u.hook_add(UC_HOOK_CODE,hook)
def reset(seed=0):
 global native,cursor,events,restricted
 native=True; cursor=BASE+0x4000; events=[]; restricted=None
 pattern=random.Random(seed).randbytes(1024); write(BASE,pattern*(SIZE//1024))
def args(values):
 a=Args(); a.count=len(values); a.words[:len(values)]=[x&0xffffffff for x in values]; return a
def compare(function,token,values,label,virtualSlot=None,frozen=False):
 global native,events,cursor,calls,eventCount,replayCases
 before=bytes(heap); oldCursor=cursor; events=[]; fault=U(); result=U()
 if frozen:
  ctx=Context(host,None,0,0); ok=lib.claw_world_file_entry(function,token,args(values),C.byref(ctx),None,None,C.byref(result)); fault.value=ctx.fault
 elif virtualSlot is None: ok=lib.claw_raw_tile_entry(function,token,args(values),host,C.byref(fault),C.byref(result))
 else: ok=lib.claw_raw_tile_virtual(token,virtualSlot,args(values),host,C.byref(fault),C.byref(result))
 assert not errors,(label,errors); assert ok==1 and fault.value==0,(label,'native fault',ok,fault.value)
 expected=bytes(heap); expectedEvents=events[:]; expectedCursor=cursor
 native=False; u.mem_write(BASE,before); cursor=oldCursor; events=[]
 original=m.call(function,token,struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values)))
 actual=bytes(u.mem_read(BASE,SIZE)); assert actual==expected,(label,'heap',[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(expected,actual)) if a!=b][:12])
 assert result.value==original,(label,'EAX',hex(result.value),hex(original))
 assert events==expectedEvents,(label,'events',events,expectedEvents); assert cursor==expectedCursor
 sp=u.reg_read(UC_X86_REG_ESP)-m.stack; assert sp==4+len(values)*4,(label,'ESP',sp,len(values)); originalSP.add((function,sp))
 if function not in functions or calls%800==0 or label.startswith('alias-') or label.startswith('wrapped-shift/63/') or label.startswith('chain/0/'):
  v=[x&0xffffffff for x in values]+[0]*(4-len(values))
  replay.write(struct.pack('<11I',function,token,*v,len(values),int(frozen),oldCursor,original,expectedCursor)+before+actual);replayCases+=1
 native=True; events=expectedEvents; calls+=1; eventCount+=len(events); functions[function]=functions.get(function,0)+1
 return result.value
def query(slot,values,label,token=DESC):
 fn=lib.claw_raw_tile_function(words(token)[0],slot); assert fn
 assert fn==m.read_words(words(token)[0]+slot,1)[0],(label,'vtable map',hex(fn))
 return compare(fn,token,values,label,virtualSlot=slot)
def construct(record,label):
 write(RECORD+1,record)
 return compare(0x4cb700,DESC,[RECORD+1],label,frozen=True)
def rawDescription(kind,width=8,height=8,attr=3,outside=9,bounds=(2,2,5,5),mask=None):
 if kind==1: return struct.pack('<5I',1,0,width,height,attr)
 if kind==2: return struct.pack('<10I',2,0,width,height,outside,attr,*[v&0xffffffff for v in bounds])
 if mask is None: mask=bytes((x+y*3)&255 for y in range(height) for x in range(width))
 return struct.pack('<4I',3,0,width,height)+mask
def actualRecords():
 # Enumerate the fingerprinted original REZ, rather than trusting old decoded files.
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes()
 assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
 worlds=[]
 def word(o): return struct.unpack_from('<I',blob,o)[0]
 def walk(offset,size,parent=()):
  end=offset+size
  while offset<end:
   kind,target,length=word(offset),word(offset+4),word(offset+8); start=offset+(16 if kind else 28); nul=blob.index(0,start,end); name=blob[start:nul].decode('ascii')
   if kind: walk(target,length,parent+(name,)); offset=nul+1
   else:
    extension=blob[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii'); offset=nul+2
    if len(parent)==2 and parent[0].startswith('LEVEL') and parent[1]=='WORLDS' and name=='WORLD' and extension=='WWD': worlds.append((int(parent[0][5:]),blob[target:target+length]))
 walk(word(131),word(135)); assert len(worlds)==14
 for level,b in sorted(worlds):
  h=struct.unpack_from('<188I',b); raw=b[:h[0]]+zlib.decompress(b[h[0]:]) if h[2]&2 else b
  at=h[185]; count=struct.unpack_from('<I',raw,at+8)[0]; at+=32; records=[]
  for i in range(count):
   k,_,w,t=struct.unpack_from('<4I',raw,at); length=20 if k==1 else 40 if k==2 else 16+w*t; assert k in(1,2,3)
   records.append(raw[at:at+length]); at+=length
  yield level,records
def failure(function,token,values,label,expectedFault=1):
 global native,faults
 before=bytes(heap); fault=U();result=U(); ok=lib.claw_raw_tile_entry(function,token,args(values),host,C.byref(fault),C.byref(result))
 assert ok==0 and fault.value==expectedFault,(label,ok,fault.value)
 expected=bytes(heap); native=False; u.mem_write(BASE,before)
 try: m.call(function,token,struct.pack('<'+'I'*len(values),*(x&0xffffffff for x in values)))
 except UcError: pass
 else: raise AssertionError((label,'original unexpectedly returned'))
 assert bytes(u.mem_read(BASE,SIZE))==expected,(label,'fault partial heap')
 native=True; faults+=1
