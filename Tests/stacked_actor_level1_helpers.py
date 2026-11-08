"""Read-only original WWD inventory fed through frozen generic source loader."""
import stacked_actor_constructor_helpers as h
C=h.C
class State(C.Structure):_fields_=[('actor',C.c_uint32*128),('logic',C.c_uint32*93)]
class Context(C.Structure):_fields_=[(n,C.c_uint32)for n in('sceneToken','actorToken','logicToken','sceneDefaultType')]+[('worldWidth',C.c_int32),('worldHeight',C.c_int32),('registryToken',C.c_uint32),('layers',C.c_uint32*3)]+[(n,C.c_uint32)for n in('entryToken','entryCallback','entryFlags')]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32),('text',C.c_char_p)]
class Info(C.Structure):_fields_=[('consumed',C.c_uint32),('created',C.c_uint32)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(State),C.POINTER(Context),C.POINTER(Call),C.c_void_p)
h.lib.claw_world_object_load.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(State),C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(Info)]
@Dependency
def dependency(s,c,event,_):
 e=event.contents
 if e.function==0x4f6286:return h.BASE+0x3e000
 if e.function in(0x4c7970,0x4c7900):s.contents.actor[0x16c//4]=1;s.contents.actor[0x170//4]=h.IM;s.contents.actor[0x174//4]=h.IMAGE;return 1
 if e.function in(0x4c79e0,0x4c7a40,0x4f4630):return 1
 raise AssertionError(('world profile dependency',hex(e.function)))
CALLBACKS={'PowderKeg':0x46f1e0,'FrontCrate':0x471720,'BehindCrate':0x471750,'BackStackedCrates':0x48d620,'FrontStackedCrates':0x48d560}
def records():
 blob=(h.ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert h.hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';assets={}
 def w(o):return h.struct.unpack_from('<I',blob,o)[0]
 def walk(offset,size,path=()):
  end=offset+size
  while offset<end:
   kind,target,length=w(offset),w(offset+4),w(offset+8);start=offset+(16 if kind else 28);nul=blob.index(0,start,end);text=blob[start:nul].decode('ascii')
   if kind:walk(target,length,path+(text,));offset=nul+1
   else:
    ext=blob[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii');assets['/'.join(path+(text+'.'+ext,))]=blob[target:target+length];offset=nul+2
 walk(w(131),w(135));wwd=assets['LEVEL1/WORLDS/WORLD.WWD'];header=h.struct.unpack_from('<188I',wwd);raw=wwd[:header[0]]+h.zlib.decompress(wwd[header[0]:]);out=[]
 for plane in range(header[183]):
  p=h.struct.unpack_from('<40I',raw,header[184]+plane*160);at=p[35]
  for index in range(p[32]):
   words=h.struct.unpack_from('<71I',raw,at);end=at+284;strings=[]
   for length in words[1:5]:strings.append(raw[end:end+length].split(b'\0')[0].decode('ascii'));end+=length
   if strings[1]in CALLBACKS:out.append({'plane':plane,'index':index,'words':words,'strings':strings,'bytes':raw[at:end],'rawSHA256':h.hashlib.sha256(raw[at:end]).hexdigest()})
   at=end
 assert len(out)==114;return out

def install(row):
 state=State((C.c_uint32*128)(*h.get(h.A,128)),(C.c_uint32*93)(*h.get(h.L,93)));c=Context(h.SC,h.A,h.L,h.BASE+0x3e000,24576,6144,h.BASE+0x3e400,(C.c_uint32*3)(0,0,0),h.BASE+0x3e800,CALLBACKS[row['strings'][1]],2);data=(C.c_uint8*len(row['bytes'])).from_buffer_copy(row['bytes']);info=Info();assert h.lib.claw_world_object_load(data,len(data),C.byref(state),C.byref(c),dependency,None,C.byref(info))==len(data)and info.created
 h.put(h.A,list(state.actor));h.put(h.L,list(state.logic));h.put(h.A+0x74,[h.ATT]);return CALLBACKS[row['strings'][1]]
