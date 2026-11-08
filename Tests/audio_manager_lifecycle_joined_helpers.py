"""Joined actual WAV factory/upload to frozen PCM then manager shutdown."""
import ctypes as C,hashlib,struct
import audio_manager_lifecycle_runtime_helpers as h
from unicorn.x86_const import UC_X86_REG_ESP
INPUT,FIRST,SECOND=h.BASE+0x20000,h.BASE+0x28000,h.BASE+0x2c000
physicalAddresses={0x10fd00c:0xc,0x10fd018:0x18,0x10fd01c:0x1c,0x10fd020:0x20,0x10fd02c:0x2c,0x10fd04c:0x4c}
for a in physicalAddresses:h.u.mem_write(a,b'\xc3')
nextBuffer=h.B;failureCreate=failureLock=failureUnlock=0;currentBytes=0;profile=None;assets=[]
def emit(f,args,method=0,initial=None):h.events.append((f,0,tuple(args),method,initial,h.snapshot()))
@h.Create
def create(_,device,format,count,out):
 global currentBytes
 currentBytes=count;emit(0x10fd00c,(device,C.string_at(format,18),count,0),0xc);out[0]=nextBuffer;return failureCreate
@h.Get
def get(_,buffer,method,out):
 token=h.BASE+C.cast(out,C.c_void_p).value-C.addressof(h.heap);emit(0x10fd000+method,(buffer,token),method,out[0]);out[0]={0x20:22050,0x1c:0,0x18:0}[method];return 0
@h.BytesLookup
def byteLookup(_,t,n):return h.lookup(None,t,(n+3)//4)
@h.Lock
def lock(_,buffer,offset,count,flags,out):
 emit(0x10fd02c,(buffer,offset,count,flags),0x2c);out[0]=h.Regions(FIRST,count//2,SECOND,count-count//2);return failureLock
@h.Unlock
def unlock(_,buffer,regions):emit(0x10fd04c,(buffer,*[getattr(regions,n)for n,_ in h.Regions._fields_]),0x4c);return failureUnlock
host=h.PCMHost(h.ResourceHost(None,h.objectLookup,h.allocate,create,h.Duplicate(),get,h.Set(),h.report),byteLookup,h.free,h.Seek(),h.Read(),h.Retry(),lock,unlock,h.release)
h.lib.claw_audio_load_pcm.argtypes=[C.POINTER(h.PCM),h.U,h.U,h.PCMHost,h.UP];h.lib.claw_audio_load_pcm.restype=h.U

def original(uc,address,size,user):
 global currentBytes
 if address==0x4b4ae0 and h.selectedEntry==0x4b4a20 and h.compose:return True
 if address not in physicalAddresses:return False
 sp=uc.reg_read(UC_X86_REG_ESP);method=physicalAddresses[address]
 if method==0xc:
  args=h.get(sp+4,4);desc=h.get(args[1],5);assert desc[:2]==[20,0xe0]and desc[3]==0 and args[3]==0;currentBytes=desc[2];emit(address,(args[0],bytes(uc.mem_read(desc[4],18)),currentBytes,0),method);h.put(args[2],[nextBuffer]);h.returned(16,failureCreate)
 elif method in(0x18,0x1c,0x20):
  args=h.get(sp+4,2);emit(address,args,method,h.get(args[1])[0]);h.put(args[1],[{0x20:22050,0x1c:0,0x18:0}[method]]);h.returned(8)
 elif method==0x2c:
  args=h.get(sp+4,8);emit(address,(args[0],args[1],args[2],args[7]),method)
  for token,value in zip(args[3:7],(FIRST,args[2]//2,SECOND,args[2]-args[2]//2)):h.put(token,[value])
  h.returned(32,failureLock)
 else:emit(address,h.get(sp+4,5),method);h.returned(20,failureUnlock)
 return True

def native(f,receiver,args,out):
 words=h.get(receiver,32);h.activePCM=h.PCM(h.Resource(receiver,words[5],words[30],words[1],words[2]),words[3],words[4]);fault=h.U();out.value=h.lib.claw_audio_load_pcm(C.byref(h.activePCM),args[0],len(profile),host,C.byref(fault));assert not fault.value;h.sync();h.activePCM=None;return 1
h.extraPhysical=original;h.extraNative=native

def prepare(file,failure=0):
 global profile,nextBuffer,failureCreate,failureLock,failureUnlock
 h.prepare();profile=file.read_bytes();assert len(profile)<0x4000;C.memmove(C.addressof(h.heap)+INPUT-h.BASE,profile,len(profile));nextBuffer=h.B;failureCreate=0x80004005 if failure==1 else 0;failureLock=0x80004005 if failure==2 else 0;failureUnlock=0x80004005 if failure==3 else 0;h.put(h.DVT+0xc,[0x10fd00c]);h.put(h.BVT+0x18,[0x10fd018]);h.put(h.BVT+0x1c,[0x10fd01c]);h.put(h.BVT+0x20,[0x10fd020]);h.put(h.BVT+0x2c,[0x10fd02c]);h.put(h.BVT+0x4c,[0x10fd04c]);h.put(nextBuffer,[h.BVT]);h.compose=True;assets.append({'path':str(file.relative_to(h.ROOT)),'sha256':hashlib.sha256(profile).hexdigest(),'bytes':len(profile)})
