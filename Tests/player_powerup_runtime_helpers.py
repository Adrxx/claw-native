"""Private raw graph oracle; original bodies execute from the hash-pinned EXE."""
import ctypes as C,hashlib,json,random,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EIP,UC_X86_REG_ECX,UC_X86_REG_ESP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-powerup-agent'
sources=['PlayerPowerupRuntime','PlayerInputDispatch','PlayerEngine','PlayerPhysics','GameImageRuntime','SpriteGeometry','PIDRaster','PIDSurfaceRaster','PIDBlitter',
    'PlayerDamage','PlayerInitialization','PlayerLocomotion','PlayerAirStates','CollisionResponse','TileCollision']
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',
    *[str(ROOT/'Sources'/f'{name}.cpp')for name in sources],str(WORK/'image-effect-adapter.cpp'),
    '-o',str(WORK/'libPlayerPowerupRuntime.dylib')],check=True)
class SceneCall(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('arguments',C.c_uint32*4),('argumentCount',C.c_uint32)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32)
Allocate=C.CFUNCTYPE(C.c_uint32,C.c_void_p,C.c_uint32);Free=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32)
Invoke=C.CFUNCTYPE(C.c_uint32,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(C.c_uint32,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Allocate),('free',Free),('call',Invoke),('readClock',Clock)]
class Globals(C.Structure):_fields_=[(n,C.c_uint32)for n in('managerToken','playerToken','powerup','remaining','expired','musicDisabled','cycleRemaining','cycleIndex')]
class Context(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(Globals)),('fault',C.c_uint32)]
class Call(C.Structure):_fields_=[('function',C.c_uint32),('receiver',C.c_uint32),('argumentCount',C.c_uint32),('arguments',C.c_uint32*6),('name',C.c_char_p)]
Dependency=C.CFUNCTYPE(C.c_uint32,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
BASE,SIZE=0x3000000,0x40000
A,L,P,MUSICOWNER,MUSICOWNER2,MUSIC,MUSIC2,LEVEL,POWER,THIRD,VT,IM,ARRAY,IMAGE,COMP,OLDGLITTER,NEWGLITTER,NEWLOGIC,PARENT,ACTORS=[BASE+0x1000+i*0x1000 for i in range(20)]
SUSPEND,RESUME,STOP=0x10ff100,0x10ff110,0x10ff120
GLOBALS=(0x5371fc,0x537e88,0x534eac,0x534ea8,0x534eb8,0x53c9c0,0x534ec8,0x534ecc)
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.executed.clear()
lib=C.CDLL(str(WORK/'libPlayerPowerupRuntime.dylib'))
lib.claw_player_powerup_entry.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint32,C.POINTER(Context),Dependency,C.c_void_p,C.POINTER(C.c_uint32)];lib.claw_player_powerup_entry.restype=C.c_uint32
lib.claw_powerup_test_image_effect.argtypes=[C.POINTER(Context),C.c_uint32,C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32)];lib.claw_powerup_test_image_effect.restype=C.c_uint32
heap=(C.c_uint8*SIZE)();g=Globals();ctx=Context();ctx.globals=C.pointer(g)
rng=random.Random(0x41f990);native_events=[];original_events=[];calls=events=0;mutation=0;created=NEWGLITTER;levelResult=LEVEL;powerResult=POWER;errors=[];effects=(C.c_uint32*4)();serial=0
GLOBAL_START,GLOBAL_SIZE=0x528000,0x1c000
global_seed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE));native_global_updates=None
def put(t,values,native=True):
    data=struct.pack('<'+'I'*len(values),*(v&0xffffffff for v in values))
    if native:C.memmove(C.addressof(heap)+t-BASE,data,len(data))
    else:m.u.mem_write(t,data)
def get(t,n=1,native=True):
    data=C.string_at(C.addressof(heap)+t-BASE,n*4)if native else bytes(m.u.mem_read(t,n*4))
    return list(struct.unpack('<'+'I'*n,data))
def glob(index,native=True):return getattr(g,Globals._fields_[index][0])if native else m.read_words(GLOBALS[index],1)[0]
def setglob(index,value,native):
    if native:setattr(g,Globals._fields_[index][0],value)
    else:m.write_words(GLOBALS[index],[value])
def raw(native):return bytes(heap)if native else bytes(m.u.mem_read(BASE,SIZE))
def global_raw(native):
    if not native:return bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
    data=bytearray(global_seed)
    for i,address in enumerate(GLOBALS):struct.pack_into('<I',data,address-GLOBAL_START,glob(i))
    if native_global_updates:
        for address,value in native_global_updates().items():data[address-GLOBAL_START:address-GLOBAL_START+len(value)]=value
    return bytes(data)
def snapshot(native):return tuple(glob(i,native)for i in range(8)),hashlib.sha256(raw(native)).digest(),hashlib.sha256(global_raw(native)).digest()
@Lookup
def lookup(user,token,count):
    if BASE<=token and token+count*4<=BASE+SIZE:return C.addressof(heap)+token-BASE
    return None
ctx.scene=Host(None,lookup,Allocate(),Free(),Invoke(),Clock())
def effect(fn,receiver,args,native):
    global serial
    if mutation and fn==0x4b54a0 and args==[0x524d80]:
        # Real setter reloads global manager after this service. Preserve
        # the original incoming receiver while moving future operations.
        setglob(0,MUSICOWNER2,native)
    if mutation==2 and fn==0x4b5bd0:
        setglob(2,0x26bd if receiver==POWER else 0x26bc,native)
        put(A+0xd4,[0x11111111],native)
    if fn==0x4b54a0:return levelResult if args[0]==0x524d80 else powerResult
    if fn==0x4b5bd0:return get(receiver+0x10,native=native)[0]
    if fn==0x4b5570:put(receiver+0x20,[get(receiver+0x20,native=native)[0]+1],native);return 0
    if fn in(SUSPEND,RESUME,STOP):
        put(receiver+0x18,[get(receiver+0x18,native=native)[0]+1],native)
        return 0
    if fn==0x48c8a0:
        put(PARENT+0x100,[args[0],args[1]],native)
        if mutation==2:setglob(4,0x24681357,native)
        return 1
    if fn==0x4c8da0:
        assert receiver==ACTORS and args==[1,100,100,0,0x5225a0,0]
        if created:
            put(created+0xc,[PARENT],native);put(created+0x6c,[NEWLOGIC],native)
            put(created+0x4c,[100,100],native)
        return created
    if fn==0x4c6130:
        if mutation==2:
            put(IM+0x68,[1],native)
            put(IMAGE+0x30,[0],native)
        if native:
            return lib.claw_powerup_test_image_effect(C.byref(ctx),receiver,*args,effects)
        return None # Execute the entire original compressed-effect body.
    raise AssertionError(('unexpected dependency',hex(fn),hex(receiver),args))
@Dependency
def dependency(context,call,user):
    c=call.contents;args=list(c.arguments[:c.argumentCount])
    event=(c.function,c.receiver,tuple(args),snapshot(True));native_events.append(event)
    try:return effect(c.function,c.receiver,args,True)or 0
    except Exception as e:errors.append(e);return 0
COUNTS={0x4b54a0:1,0x4b5bd0:0,0x4b5570:1,SUSPEND:0,RESUME:1,STOP:0,0x48c8a0:2,0x4c8da0:6,0x4c6130:2}
CDECL={0x48c8a0}
def hook(u,address,size,user):
    if address not in COUNTS:return
    sp=u.reg_read(UC_X86_REG_ESP);args=m.read_words(sp+4,COUNTS[address])
    receiver=0 if address in CDECL else u.reg_read(UC_X86_REG_ECX)
    original_events.append((address,receiver,tuple(args),snapshot(False)))
    value=effect(address,receiver,args,False)
    if value is None:return
    u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0]);u.reg_write(UC_X86_REG_ESP,sp+4+(0 if address in CDECL else COUNTS[address]*4))
m.u.hook_add(UC_HOOK_CODE,hook)
def prepare(old=0,remaining=0):
    global serial
    serial=0;ctx.fault=0;C.memset(C.addressof(heap),0xa5,SIZE)
    for token,count in((A,128),(L,93),(P,78),(MUSICOWNER,40),(MUSICOWNER2,40),(MUSIC,40),(MUSIC2,40),(LEVEL,24),(POWER,24),(VT,16),(IM,32),(IMAGE,16),(COMP,10),(NEWGLITTER,128),(NEWLOGIC,93)):
        put(token,[rng.getrandbits(32)for _ in range(count)])
    put(A+0xc,[PARENT]);put(PARENT+8,[ACTORS]);put(A+0x6c,[L]);put(L+0x14,[P])
    put(A+0x170,[IM]);put(A+0x174,[IMAGE]);put(P+0x130,[OLDGLITTER])
    put(MUSICOWNER+0x14,[rng.choice([0,1])]);put(MUSICOWNER+0x50,[MUSIC]);put(MUSICOWNER2+0x14,[1]);put(MUSICOWNER2+0x50,[MUSIC2])
    put(MUSIC+0x1c,[rng.choice([0,LEVEL,POWER,THIRD])]);put(MUSIC2+0x1c,[rng.choice([0,LEVEL,POWER,THIRD])])
    put(LEVEL,[VT]);put(POWER,[VT]);put(LEVEL+0x10,[rng.choice([0,1])]);put(POWER+0x10,[rng.choice([0,1])]);put(VT+0x28,[SUSPEND,RESUME,STOP])
    put(IM+0x14,[ARRAY]);put(IM+0x64,[0,3]);put(ARRAY,[IMAGE,0,IMAGE+0x100,IMAGE+0x200])
    put(IMAGE+0x30,[COMP]);put(IMAGE+0x100+0x30,[0]);put(IMAGE+0x200+0x30,[COMP+0x100])
    g.managerToken=MUSICOWNER;g.playerToken=A;g.powerup=old;g.remaining=remaining
    g.expired=rng.getrandbits(32);g.musicDisabled=rng.choice([0,1]);g.cycleRemaining=rng.choice([0,1,99,100,0xffffffff]);g.cycleIndex=rng.choice([0x34,0x35,0x36,0x37,0x65,0,0xffffffff])
    for i in range(4):effects[i]=rng.getrandbits(32)
    sync()
def sync():
    global global_seed
    m.u.mem_write(BASE,bytes(heap))
    for i,address in enumerate(GLOBALS):m.write_words(address,[glob(i)])
    m.write_words(0x5430b0,list(effects))
    global_seed=bytes(m.u.mem_read(GLOBAL_START,GLOBAL_SIZE))
def compare(fn,args,label,receiver=0):
    global calls,events
    sync();native_events.clear();original_events.clear();errors.clear();ctx.fault=0
    values=(C.c_uint32*len(args))(*(x&0xffffffff for x in args));result=C.c_uint32()
    done=lib.claw_player_powerup_entry(fn,receiver,values,len(args),C.byref(ctx),dependency,None,C.byref(result))
    assert not errors,errors
    assert done==1 and ctx.fault==0,(label,'native fault',ctx.fault)
    original=m.call(fn,receiver,struct.pack('<'+'I'*len(args),*(x&0xffffffff for x in args)))
    if fn in(0x41f990,0x41fc00,0x4ce7b0,0x448400):assert original==result.value,(label,'return',original,result.value)
    assert native_events==original_events,(label,'events',[(i,a,b)for i,(a,b)in enumerate(zip(native_events,original_events))if a!=b][:3],len(native_events),len(original_events))
    assert snapshot(True)==snapshot(False),(label,'whole snapshot',snapshot(True)[0],snapshot(False)[0])
    assert raw(True)==raw(False),(label,'raw heap bytes')
    assert global_raw(True)==global_raw(False),(label,'whole global image bytes')
    calls+=1;events+=len(native_events)
