"""Hash-pinned original lighting pixel bodies; DD Lock/Unlock only adapted."""
import ctypes as C,struct,random,subprocess,hashlib
from pathlib import Path
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/light-pid-blit-agent'
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/LightPIDBlitter.cpp'),str(ROOT/'Sources/PIDBlitter.cpp'),'-o',str(WORK/'libLightPID.dylib')],check=True)
U=C.c_uint32;B=C.c_uint8;Z=C.c_size_t
class Rect(C.Structure):_fields_=[(x,C.c_int32)for x in('left','top','right','bottom')]
class Command(C.Structure):_fields_=[('destination',Rect),('source',Rect),('flipX',U),('flipY',U),('sourceAddress',U)]
class State(C.Structure):_fields_=[(x,U)for x in('renderWord','effectMode','effectValue','formatByte','bothTopSkipSeed')]
class Table(C.Structure):_fields_=[('words',U*3),('data',C.POINTER(B)),('capacity',Z)]
class Info(C.Structure):_fields_=[('consumed',Z),('writes',Z),('locks',U),('unlocks',U)]
lib=C.CDLL(str(WORK/'libLightPID.dylib'));lib.claw_light_pid_blit8.argtypes=[C.POINTER(B),Z,C.POINTER(Command),C.POINTER(State),C.POINTER(Table),C.POINTER(B),C.POINTER(B),Z,Z,C.POINTER(B),C.POINTER(Info)];lib.claw_light_pid_blit8.restype=U
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');u=m.u;m.executed.clear();u.mem_map(0,4096)
IMAGE,ENCODED,SURFACE,DST,SRC,DD,VT,TABLE,TABLEDATA,PIXELS=0x1000000,0x1020000,0x1001000,0x1002000,0x1003000,0x1004000,0x1005000,0x1006000,0x1040000,0x1080000
UNLOCK=0x10ef000;SCRATCH=0x542bb0;GUARD=128
m.write_words(SURFACE+8,[DD]);m.write_words(DD,[VT]);m.write_words(VT+0x80,[UNLOCK])
events=[];offsets=set();stores=[];size=0;calls=totalWrites=snapshots=0;r=random.Random(0x4c1190);expectedSeed=0;lastEvidence=None
def packed(*v):return struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v])
def header(w,h,flags=32):return packed(10,flags,w,h,0,0,0,0)
def ret(pop,v):
 sp=u.reg_read(UC_X86_REG_ESP);ip=m.read_words(sp,1)[0];u.reg_write(UC_X86_REG_EAX,v);u.reg_write(UC_X86_REG_ESP,sp+4+pop);u.reg_write(UC_X86_REG_EIP,ip)
def host(_,f,n,unused):
 if f==0x4c4c20:assert m.read_words(u.reg_read(UC_X86_REG_ESP)-36,1)[0]==expectedSeed
 if f==0x4b9730:
  sp=u.reg_read(UC_X86_REG_ESP);assert u.reg_read(UC_X86_REG_ECX)==SURFACE and m.read_words(sp+4,1)==[0];events.append(('lock',bytes(u.mem_read(PIXELS,size+GUARD*2)),bytes(u.mem_read(SCRATCH,128))));ret(4,PIXELS+GUARD)
 elif f==UNLOCK:
  assert m.read_words(u.reg_read(UC_X86_REG_ESP)+4,2)==[DD,0];events.append(('unlock',bytes(u.mem_read(PIXELS,size+GUARD*2)),bytes(u.mem_read(SCRATCH,128))));ret(8,0)
def write(_,access,t,n,v,unused):
 if PIXELS<=t<PIXELS+size+GUARD*2:
  assert PIXELS+GUARD<=t and t+n<=PIXELS+GUARD+size,('original overflow',hex(t),n)
  offsets.update(range(t-PIXELS-GUARD,t-PIXELS-GUARD+n));stores.append((t-PIXELS-GUARD,n,v))
u.hook_add(UC_HOOK_CODE,host);u.hook_add(UC_HOOK_MEM_WRITE,write)
def check(data,src,dst,fx,fy,label,render=0,seed=0,palette=None,tablePresent=True,mode=2,fmt=1,initial=None,pitchOverride=None):
 global size,calls,totalWrites,snapshots,expectedSeed,lastEvidence
 _,flags,w,h,*_=struct.unpack('<8I',data[:32]);pitch=w+29 if pitchOverride is None else pitchOverride;size=pitch*(h+14)+w;assert size+GUARD*2<UNLOCK-PIXELS
 palette=palette if palette is not None else r.randbytes(65536);assert len(palette)==65536
 raw=r.randbytes(size)if initial is None else initial;assert len(raw)==size;scratch=r.randbytes(128);pid=(B*len(data)).from_buffer_copy(data);out=(B*size).from_buffer_copy(raw);cov=(B*size)(*([0x41]*size));scratchN=(B*128).from_buffer_copy(scratch);lut=(B*65536).from_buffer_copy(palette)
 table=Table((U*3)(r.getrandbits(32),r.getrandbits(32),TABLEDATA),lut,65536);state=State(render,mode,r.getrandbits(32),fmt,seed);cmd=Command(Rect(*dst),Rect(*src),fx,fy,SRC);info=Info(999,888,77,66)
 result=lib.claw_light_pid_blit8(pid,len(data),C.byref(cmd),C.byref(state),C.byref(table)if tablePresent else None,out,cov,size,pitch,scratchN,C.byref(info))
 expect=int(src[0]>=0 and src[2]<=w-1 and src[1]>=0 and src[1]<=h-1 and(mode==1 or fmt&255==1));assert result==expect,(label,src,dst,fx,fy,render,'native rejects',result)
 m.write_words(IMAGE,[render,w,h,ENCODED,len(data)-32,mode,state.effectValue,TABLE if tablePresent else 0,0,fmt]);m.write_words(TABLE,list(table.words));u.mem_write(TABLEDATA,palette);u.mem_write(ENCODED,data[32:]);m.write_words(SURFACE+28,[pitch]);m.write_words(DST,dst);m.write_words(SRC,src);expectedSeed=seed;m.write_words(m.stack-56,[seed])
 before=b'\x9a'*GUARD+raw+b'\x9a'*GUARD;u.mem_write(PIXELS,before);u.mem_write(SCRATCH,scratch);heapBefore=bytes(u.mem_read(0x1000000,0x100000));globalsBefore=bytes(u.mem_read(0x500000,0x50000));events.clear();offsets.clear();stores.clear()
 original=m.call(0x4bffa0,IMAGE,packed(DST,SURFACE,SRC,fx,fy),max_instructions=10000000);assert original==result,(label,'dispatch')
 expected=b'\x9a'*GUARD+bytes(out)+b'\x9a'*GUARD;actual=bytes(u.mem_read(PIXELS,size+GUARD*2));assert actual==expected,(label,src,dst,fx,fy,render,'pixel mismatch',[(i-GUARD,a,b)for i,(a,b)in enumerate(zip(actual,expected))if a!=b][:12])
 assert bytes(u.mem_read(SCRATCH,128))==bytes(scratchN),(label,src,dst,fx,fy,render,'scratch mismatch')
 mask=bytearray(b'\x41'*size)
 for at in offsets:mask[at]=1
 assert bytes(cov)==mask,(label,'coverage')
 expectedEvents=['lock','unlock']if expect and(mode==1 or tablePresent)else[];assert [e[0]for e in events]==expectedEvents
 if expectedEvents:assert events[0][1:]==(before,scratch) and events[1][1:]==(expected,bytes(scratchN));assert(info.locks,info.unlocks)==(1,1);assert info.writes==sum(n for _,n,_ in stores)
 elif expect:assert(info.locks,info.unlocks,info.writes)==(0,0,0)
 #No other source-visible heap or global stores; preserve complete object/table.
 heapAfter=bytearray(u.mem_read(0x1000000,0x100000));heapAfter[PIXELS-0x1000000:PIXELS-0x1000000+len(before)]=before;assert bytes(heapAfter)==heapBefore,(label,'heap writes')
 globalAfter=bytearray(u.mem_read(0x500000,0x50000));globalAfter[SCRATCH-0x500000:SCRATCH-0x500000+128]=scratch;assert bytes(globalAfter)==globalsBefore,(label,'global writes')
 calls+=1;totalWrites+=sum(n for _,n,_ in stores);snapshots+=len(events);lastEvidence=(data,bytes(cmd),bytes(state),list(table.words),palette,raw,scratch,bytes(out),bytes(cov),bytes(scratchN),size,pitch,result,info.writes);return bytes(out)
