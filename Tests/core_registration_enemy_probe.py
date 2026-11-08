"""Compose frozen registry/GenericEnemy fixtures without writing their work dirs."""
import ctypes as C,hashlib,json,struct,types
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP
import core_registration_helpers as core
ROOT=core.ROOT
# Reuse the proven harness bodies read-only; redirect their build artifacts into
# this worker's directory. Their main suites do not run during fixture loading.
def fixture(name,file,replacements):
 module=types.ModuleType(name);module.__file__=str(ROOT/'Tests'/file);source=(ROOT/'Tests'/file).read_text()
 for a,b in replacements:source=source.replace(a,b)
 exec(compile(source,module.__file__,'exec'),module.__dict__);return module
registry=fixture('core_registry_fixture','compare_logic_state_registry.py',[("WORK=ROOT/'work/state-registry-agent'","WORK=ROOT/'work/core-registration-agent'"),("u.hook_add(UC_HOOK_CODE,hook)","registry_hook=u.hook_add(UC_HOOK_CODE,hook)")])
registry.reset_profile(0);registry.check('initialize','84 original state-related CRT constructors before handler CRT')
assert registry.m.read_words(0x544d18,1)==[0]
# Constructors through52222c..52223c have actual later positions in PE order.
original=registry.m;u=original.u;u.hook_del(registry.registry_hook)
for slot,fn in[(0x52222c,0x4db600),(0x522230,0x4dbb70),(0x522234,0x4dc160),(0x522238,0x4dc260),(0x52223c,0x4dc380)]:assert original.read_words(slot,1)==[fn]
globals=core.Globals();globals.words[:]=original.read_words(core.GBASE,130);core.lib.claw_core_registration_defaults(C.byref(globals));fault=C.c_uint32()
assert core.lib.claw_core_registration_initialize(C.byref(globals),core.host,C.byref(fault))and not fault.value
for fn in(0x4db600,0x4dbb70,0x4dc160,0x4dc260,0x4dc380):original.call(fn,0)
assert list(globals.words)==original.read_words(core.GBASE,130)and globals.words[129]==0
# Exact shared globals need an explicit adapter synchronization between modules.
registry.state.errorGlobals[:]=globals.words[:15]
enemy=fixture('core_generic_fixture','compare_generic_enemy.py',[("scratch=ROOT/'work/generic-enemy-agent'","scratch=ROOT/'work/core-registration-agent'")]);enemy.m=original;enemy.u=u;u.hook_add(UC_HOOK_CODE,enemy.host)
from collections import deque
trace=deque(maxlen=40)
observations=[];native_global_events=[];original_global_events=[];last_event_count=0
original_dependency=enemy.dependency
@enemy.Dependency
def dependency(s,c,e,user):
 native_global_events.append((tuple(globals.words),hashlib.sha256(bytes(registry.heap)).digest()))
 return original_dependency(s,c,e,user)
enemy.dependency=dependency

def observe(uc,address,size,user):
 global last_event_count
 trace.append(address)
 if address in(0x4dc560,0x4dc180,0x4dbe10):
  n=2 if address in(0x4dc560,0x4dbe10)else 0;sp=u.reg_read(UC_X86_REG_ESP);observations.append((address,u.reg_read(UC_X86_REG_ECX),tuple(original.read_words(sp+4,n))))
 if len(enemy.original_events)>last_event_count:
  original_global_events.append((tuple(original.read_words(core.GBASE,130)),hashlib.sha256(bytes(u.mem_read(registry.HEAP,registry.SIZE))).digest()));last_event_count=len(enemy.original_events)
u.hook_add(UC_HOOK_CODE,observe)
for case in range(120):
 s,c=enemy.fresh();enemy.policy=case%2;enemy.collision=case%2;enemy.tile_values=[0];native_global_events.clear();original_global_events.clear();last_event_count=0;observations.clear()
 try:enemy.compare(s,c,0x4332f0,('actual CRT -> original enemy ctor',case))
 except BaseException:
  print('TRACE',*[hex(x)for x in trace]);raise
 assert native_global_events==original_global_events,'complete shared registration globals/arena differ across enemy callbacks'
 assert original.read_words(core.GBASE,130)==list(globals.words)and original.read_words(0x544d18,1)==[0]
 assert [x[0]for x in observations]==[0x4dc180,0x4dbe10,0x4dc560],('unexpected bitset/registration calls',observations)
 assert observations[0][1]==enemy.E+0x2f4 and observations[1][1:]==(original.stack-28,(0x534938,0))
 assert observations[2][1:]==(0x544b68,(original.stack-28,0))
# Raw direct-call and function-pointer evidence supplements the executed profile.
image=bytes(u.mem_read(0x401000,0x149000));direct=[]
for i in range(len(image)-4):
 if image[i]==0xe8 and 0x401000+i+5+int.from_bytes(image[i+1:i+5],'little',signed=True)==0x4dc560:direct.append(0x401000+i)
assert direct==[0x4db6cc]and struct.pack('<I',0x4dc560)not in image
report={'originalStateCRTConstructors':84,'originalHandlerCRTConstructors':5,'genericConstructorComparisons':enemy.total,'genericCallbackSnapshotsWithFullCoreGlobals':enemy.event_total,'registrationCountAfterRealEnemyConstructor':0,'constructorObserver':'4dc180 embedded;4dbe10 temporary(534938,0);4dc560 temporary removal withargument2=0','directRegistrationCallSites':[hex(x)for x in direct],'originalAddresses':len(original.executed),'scope':'Actual state/core CRT subset, original4332f0 with frozen explicit actor-binding/resource/collision services; full retail WinMain/all other CRT initializers not executed.'}
(core.WORK/'enemy-registration-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
