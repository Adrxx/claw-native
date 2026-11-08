"""Raw hash lookup oracle. REZ directory transport is an explicit fixture."""
import ctypes as C,hashlib,random,struct,subprocess,json
from pathlib import Path
from unicorn import UC_HOOK_CODE,UcError
from unicorn.x86_const import *
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/resource-namespace-agent';U=C.c_uint32
assert hashlib.sha256((ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest()=='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/ResourceNamespaceRuntime.cpp'),'-o',str(WORK/'libNamespace.dylib')],check=True)
lib=C.CDLL(str(WORK/'libNamespace.dylib'))
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup)]+[(n,C.c_void_p)for n in('allocate','free','call','clock')]
class Context(C.Structure):_fields_=[('scene',Host),('maximum',U),('fault',U)]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*4),('mask',U),('bufferCount',U),('buffers',C.c_void_p*2),('sizes',U*2)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_resource_namespace_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x400000;CONTROL=BASE+0x100;PATH=BASE+0x200;ALLOC=BASE+0x1000
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.executed.clear();heap=(C.c_uint8*SIZE)()
iBase,iEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(iEnd-iBase+1)).from_buffer_copy(m.u.mem_read(iBase,iEnd-iBase+1));seedImage=bytes(image)
ctx=Context();cursor=ALLOC;events=[];oevents=[];errors=[];calls=snapshots=0;objects={};capture=False;replays=[];replayEvents=[];mutationToken=mutationValue=0
def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if iBase<=t and t+n*4<=iEnd+1:return C.addressof(image)+t-iBase
 return 0
@Lookup
def lookup(_,t,n):return ptr(t,n)
ctx.scene=Host(None,lookup,None,None,None,None);ctx.maximum=100000

def put(t,v):C.memmove(ptr(t,len(v)),pack(*v),len(v)*4)
def text(t,b):C.memmove(ptr(t&~3)+(t&3),b+b'\0',len(b)+1)
def get(t):return U.from_address(ptr(t)).value
def allocation(n):
 global cursor
 t=cursor;cursor+=(n+3)&~3;assert cursor<BASE+SIZE;objects[t]=n;return t
def name(s):t=allocation(len(s)+1);text(t,s);return t

def table(t,count,values,hashfn,embedded):
 buckets=allocation(count*16);put(t,[count,buckets]);groups={}
 for v in values:groups.setdefault(hashfn(v),[]).append(v)
 for i in range(count):
  nodes=[allocation(24)for _ in groups.get(i,[])];put(buckets+16*i+8,[nodes[0]+4 if nodes else 0])
  for j,(node,v)in enumerate(zip(nodes,groups.get(i,[]))):
   nxt=nodes[j+1]+4 if j+1<len(nodes)else 0;put(node,[0,nxt,0,t,i,v]);put(v+embedded,[0,nxt,0,t,i,v])
 return buckets
folders={};leaves={};types={};folderPaths={};leafPaths={}
def buildTree(tree,path=()):
 # Folder76 bytes, type44, resource96; only fields needed by original lookup.
 t=allocation(76);n,kids,files=tree;nt=name(n);put(t,[nt]);folderPaths[path]=t;children=[buildTree(child,path+(child[0],))for child in kids];folders[t]=children
 table(t+60,5,children,lambda v:len(readName(get(v)))%5,36)
 ty=[]
 for tag in dict.fromkeys(f[1]for f in files):
  tt=allocation(44);put(tt,[tag]);vals=[]
  for leaf,ltag,rid in files:
   if ltag!=tag:continue
   r=allocation(96);put(r,[name(leaf),rid,tt]);leaves[r]=(leaf,tag,rid);leafPaths[path+(leaf,tag)]=r;vals.append(r)
  types[tt]=vals;table(tt+36,19,vals,lambda v:len(readName(get(v)))%19,72);table(tt+28,19,vals,lambda v:get(v+4)%19,72);ty.append(tt)
 table(t+68,9,ty,lambda v:get(v)%9,4);return t

def readName(t,native=True):
 if not native:
  b=bytearray()
  while True:
   c=m.u.mem_read(t,1)[0];t+=1
   if not c:return bytes(b)
   b.append(c)
 b=bytearray()
 while True:
  c=C.c_uint8.from_address(ptr(t&~3)+(t&3)).value;t+=1
  if not c:return bytes(b)
  b.append(c)
def raw(native):return (bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE)))+(C.string_at(ptr(0x540000),0x10000)if native else bytes(m.u.mem_read(0x540000,0x10000)))
def snap(native):return hashlib.sha256(raw(native)).digest()
def lower(b):return bytes(c+32 if 65<=c<=90 else c for c in b)
@Dep
def dep(c,qp,u):
 q=qp.contents
 try:
  assert q.function==0x4a3cf0 and q.count==2
  vals=[];j=0
  for i in range(2):
   if q.mask&(1<<i):vals.append(C.string_at(q.buffers[j],q.sizes[j]-1));j+=1
   else:vals.append(readName(q.arguments[i]))
  events.append((q.function,tuple(q.arguments[:2]),q.mask,tuple(vals),snap(True)))
  if mutationToken:put(mutationToken,[mutationValue])
  a,b=map(lower,vals);return 0 if a==b else 0xffffffff if a<b else 1
 except Exception as e:errors.append(e);return 0
currentFunction=0

def hook(uc,f,size,user):
 if f!=0x4a3cf0 or get(0x540e88)==0:return
 sp=uc.reg_read(UC_X86_REG_ESP);a=list(m.read_words(sp+4,2));vals=[readName(t,False)for t in a];mask=0
 for i,t in enumerate(a):
  if 0x2000000<=t<0x2010000:mask|=1<<i;a[i]=0
 oevents.append((f,tuple(a),mask,tuple(vals),snap(False)))
 if mutationToken:m.u.mem_write(mutationToken,pack(mutationValue))
 x,y=map(lower,vals);value=0 if x==y else 0xffffffff if x<y else 1
 uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)

def reset(seed=0):
 global cursor,objects,folders,leaves,types,folderPaths,leafPaths
 C.memmove(C.addressof(heap),random.Random(seed).randbytes(SIZE),SIZE);C.memmove(C.addressof(image),seedImage,len(image));put(0x540e88,[0]);cursor=ALLOC;objects={};folders={};leaves={};types={};folderPaths={};leafPaths={};ctx.fault=0

def compare(f,t,args,label):
 global calls,snapshots,currentFunction
 currentFunction=f;ctx.fault=0;events.clear();oevents.clear();errors.clear();before=bytes(heap);bi=bytes(image);a=(U*len(args))(*args);out=U();ok=lib.claw_resource_namespace_entry(f,t,a,len(args),C.byref(ctx),dep,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events)
 m.u.mem_write(BASE,before);m.u.mem_write(iBase,bi);actual=m.call(f,t,pack(*args));assert m.u.reg_read(UC_X86_REG_ESP)==m.stack+4+4*len(args)if f not in(0x4b8140,0x4b7f50,0x4b80d0,0x4b8060)else m.u.reg_read(UC_X86_REG_ESP)==m.stack+4,(label,'SP')
 assert raw(False)==expected,(label,'heap');assert ev==oevents,(label,'events',ev[:2],oevents[:2]);assert actual==out.value,(label,'EAX',hex(actual),hex(out.value));calls+=1;snapshots+=len(ev)+1
 if capture:replays.append((f,t,list(args),before,bytes(heap),bi,actual,dict(objects)))
 return actual

def rezTree():
 b=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(b).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';entries=[]
 def w(o):return struct.unpack_from('<I',b,o)[0]
 def walk(at,size,n):
  end=at+size;kids=[];files=[]
  while at<end:
   kind,target,length=w(at),w(at+4),w(at+8);start=at+(16 if kind else 28);nul=b.index(0,start,end);name=b[start:nul]
   if kind:kids.append(walk(target,length,name));at=nul+1
   else:tag=int.from_bytes(b[at+20:at+24],'little');files.append((name,tag,w(at+16)));entries.append((n,name,tag,w(at+16)));at=nul+2
  return n,kids,files
 return walk(w(131),w(135),b''),entries
