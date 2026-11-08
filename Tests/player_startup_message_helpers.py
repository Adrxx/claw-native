"""Private CStringList full-byte/order oracle; CString storage transport explicit."""
import player_startup_runtime_helpers as h
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
LIST,MSG,NODEBASE,STRINGBASE=h.BASE+0xa000,h.BASE+0xb000,h.BASE+0x80000,h.BASE+0x90000
nodeCursor=stringCursor=0;live={};allocationFailure=False;faultService=0;fontPolicy=fontCalls=0
originalEffect=h.effect

def bytesAt(t,n):
 if h.native:return h.C.string_at(h.C.addressof(h.raw)+t-h.GS if h.GS<=t<h.GS+h.GN else h.C.addressof(h.heap)+t-h.BASE,n)
 return bytes(h.u.mem_read(t,n))
def write(t,b):
 if h.native:h.C.memmove(h.C.addressof(h.raw)+t-h.GS if h.GS<=t<h.GS+h.GN else h.C.addressof(h.heap)+t-h.BASE,b,len(b))
 else:h.u.mem_write(t,b)
def text(t):return bytesAt(t,1024).split(b'\0')[0]
def state():return(h.snapshot(),nodeCursor,stringCursor,tuple(sorted(live.items())),fontCalls)
def effect(f,t,args,buffers=(),mask=0):
 global nodeCursor,stringCursor,fontCalls
 payload=tuple(h.C.cast(p,h.UP)[0]if h.native else h.m.read_words(p,1)[0]for p in buffers)if f in(0x4f6449,0x4f6584)else tuple(h.C.cast(buffers[0],h.UP)[:14])if f==0x546918 and h.native else tuple(h.m.read_words(buffers[0],14))if f==0x546918 else()
 if f==0x4f6449 and mask==256:payload=(0,) # Uninitialized temporary before copyCtor.
 h.events.append(((f,t,tuple(args),mask,payload),state()))
 if f==0x546918:
  fontCalls+=1;return 0 if fontPolicy==2 or(fontPolicy==1 and fontCalls==1)else 0x76543210
 if f==0x4f6449:
  value=(h.C.cast(buffers[0],h.UP)[0]if h.native else h.m.read_words(buffers[0],1)[0])if mask==1 else h.get(args[0])[0]
  refs=h.get(value-12)[0]
  if refs!=0xffffffff:h.put(value-12,[refs+1])
  if mask==256:
   if h.native:h.C.cast(buffers[0],h.UP)[0]=value
   else:h.m.write_words(buffers[0],[value])
  else:h.put(t,[value])
  return t

 if f==0x4f63ec:
  if allocationFailure:return 0
  q=NODEBASE+nodeCursor;nodeCursor+=(args[0]+15)&~15;live[q]=('node',args[0],True);return q
 if f==0x4f6428:
  q=args[0];kind,n,_=live[q];live[q]=(kind,n,False);return 0
 if f==0x4f66cc:
  data=text(args[0]);q=STRINGBASE+stringCursor;stringCursor+=(len(data)+13+15)&~15;h.put(q,[1,len(data),len(data)]);write(q+12,data+b'\0');h.put(t,[q+12]);live[q]=('CString',len(data)+13,True);return t
 if f==0x4f6584:
  value=(h.C.cast(buffers[0],h.UP)[0]if h.native else h.m.read_words(buffers[0],1)[0])if mask==256 else h.get(t)[0];q=value-12;refs=h.get(q)[0]
  if refs!=0xffffffff:
   h.put(q,[refs-1]);kind,n,_=live[q];live[q]=(kind,n,refs!=1)
  return 0
 raise AssertionError((hex(f),hex(t),args))
@h.Allocate
def allocate(_,n):return effect(0x4f63ec,0,[n])
@h.Free
def free(_,t):effect(0x4f6428,0,[t])
@h.Dependency
def dependency(c,e,_):
 try:
  q=e.contents;value=effect(q.function,q.receiver,list(q.arguments[:q.argumentCount]),list(q.buffers[:q.bufferCount]),q.localMask);
  if q.function==faultService:c.contents.fault=99
  return value
 except BaseException as error:h.errors.append(error);c.contents.fault=1;return 0
messageHost=h.Host(None,h.lookup,allocate,free,h.invoke,h.clock)
COUNTS={0x4f63ec:1,0x4f6428:1,0x4f66cc:1,0x4f6584:0,0x4f6449:1}
FONT=0x10e0500;h.m.write_words(0x546918,[FONT]);seed=bytearray(h.seedGlobals);h.struct.pack_into('<I',seed,0x546918-h.GS,FONT);h.seedGlobals=bytes(seed)
def hook(_,address,size,user):
 if address==FONT:
  packet=h.u.reg_read(UC_X86_REG_ESP)+4;value=effect(0x546918,0,[],[packet]);h.returned(14,value);return
 if address not in COUNTS:return
 n=COUNTS[address];args=h.m.read_words(h.u.reg_read(UC_X86_REG_ESP)+4,n);receiver=0 if address in(0x4f63ec,0x4f6428)else h.u.reg_read(UC_X86_REG_ECX);buffers=[];mask=0
 if address in(0x4f6449,0x4f6584)and 0x2000000<=receiver<0x2010000:buffers=[receiver];receiver=0;mask=256
 elif address==0x4f6449 and 0x2000000<=args[0]<0x2010000:buffers=[args[0]];args[0]=0;mask=1
 value=effect(address,receiver,args,buffers,mask);h.returned(0 if address in(0x4f63ec,0x4f6428)else n,value)
h.u.hook_add(h.UC_HOOK_CODE,hook)
def setup(seed=0,block=10):
 global nodeCursor,stringCursor,live,allocationFailure,faultService,fontCalls,fontPolicy
 h.setup(seed);h.ctx.scene=messageHost;h.put(LIST,[0x510224,0,0,0,0,0,block]+[seed+i for i in range(7)]);h.put(h.APP+0x4c,[LIST]);write(MSG,b'Your game has been saved\0');nodeCursor=stringCursor=0;live={};allocationFailure=False;faultService=0;fontPolicy=fontCalls=0

def compare(f,t,args=()):
 global nodeCursor,stringCursor,live,fontCalls
 h.native=True;before=state();h.events.clear();h.errors.clear();out=h.U();aa=(h.U*len(args))(*args);assert h.lib.claw_player_startup_entry(f,t,aa,len(args),h.C.byref(h.ctx),dependency,None,h.C.byref(out))and not h.ctx.fault,(hex(f),h.ctx.fault,h.errors);a=(state(),list(h.events),0 if f in(0x4f5288,0x4f5359)else out.value)
 h.native=False;h.u.mem_write(h.BASE,before[0][0]);h.u.mem_write(h.GS,before[0][1]);h.callbackCount=before[0][2];nodeCursor,stringCursor=before[1:3];live=dict(before[3]);fontCalls=before[4];h.events.clear();ret=h.m.call(f,t,h.struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)));assert h.u.reg_read(UC_X86_REG_ESP)==h.m.stack+4+len(args)*4;b=(state(),list(h.events),0 if f in(0x4f5288,0x4f5359)else ret)
 if a!=b:
  for z,(x,y)in enumerate(zip(a[0][0][:2],b[0][0][:2])):
   print('diff',z,[(hex((h.BASE if z==0 else h.GS)+i),x[i:i+4].hex(),y[i:i+4].hex())for i in range(0,len(x),4)if x[i:i+4]!=y[i:i+4]][:8])
  print('events',[q[0]for q in a[1]],[q[0]for q in b[1]]);raise AssertionError((hex(f),a[2],b[2]))
 h.native=True;h.C.memmove(h.heap,a[0][0][0],h.SIZE);h.C.memmove(h.raw,a[0][0][1],h.GN);nodeCursor,stringCursor=a[0][1:3];live=dict(a[0][3]);fontCalls=a[0][4];h.calls+=2;h.snapshots+=len(a[1])*2;return a
