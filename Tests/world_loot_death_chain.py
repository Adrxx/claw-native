"""Retained original Human hit/dead callbacks composed with the loot runtime."""
import ctypes as C,struct,subprocess,json
import world_loot_helpers as t
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-dynamiclib',str(t.ROOT/'Tests/world_loot_chain_helpers.cpp'),*[str(t.ROOT/'Sources'/x)for x in('WorldLootRuntime.cpp','HumanEnemy.cpp','GenericEnemy.cpp','GenericEnemyStates.cpp','PlayerPhysics.cpp','SceneActorRuntime.cpp','WorldObjectRuntime.cpp','GameTiming.cpp')],'-o',str(t.WORK/'libWorldLootDeathChain.dylib')],check=True)
class Enemy(C.Structure):_fields_=[(n,C.c_uint32*k)for n,k in [('actor',128),('primary',93),('secondary',93),('contact',93),('enemy',264)]]
class State(C.Structure):_fields_=[('state',C.c_int32),('function',C.c_uint32),('nameToken',C.c_uint32),('name',C.c_char_p)]
class Generic(C.Structure):_fields_=[(x,C.c_uint32)for x in('actorToken','primaryToken','secondaryToken','contactToken','enemyToken','sceneToken','tileManagerToken','soundRegistryToken','playerToken')]+[(x,C.c_uint32*128)for x in('playerActor','platformActor')]+[(x,C.c_uint32)for x in('tick','animationDelta','levelWord','forcedRandom','hitMode')]+[('defaults',C.c_uint32*24),('virtualFunctions',C.c_uint32*64),('states',C.POINTER(State)),('stateCount',C.c_size_t),('bitWords',C.POINTER(C.c_uint32)),('bitWordCount',C.c_size_t),('emptyStringToken',C.c_uint32),('bitHandlerToken',C.c_uint32)]
class Extra(C.Structure):_fields_=[('attackerToken',C.c_uint32),('attackerActor',C.c_uint32*128),('playerPrivate',C.c_uint32*78)]+[(x,C.c_uint32)for x in('strikeCounter','audioEnabled','audioPosition')]+[('resources',C.c_void_p),('resourceCount',C.c_size_t)]
lib=C.CDLL(str(t.WORK/'libWorldLootDeathChain.dylib'));lib.claw_generic_enemy_context_defaults.argtypes=[C.POINTER(Generic)]
lib.world_loot_test_enemy_chain.argtypes=[C.POINTER(Enemy),C.POINTER(Generic),C.POINTER(Extra),C.c_uint32,C.c_uint32,C.POINTER(t.Globals),C.POINTER(t.Context),t.Dependency,C.c_void_p];lib.world_loot_test_enemy_chain.restype=C.c_uint32
E=t.INV-0x128;PRIMARY=t.BASE+0xc000
original_effects=t.effects
def effects(event,native):
 if event[0]==0x4dba00:return 2004
 if event[0]==0x4c82a0:return 0
 return original_effects(event,native)
t.effects=effects
# Preserve the real shared hurt/dead bodies; only named registry/animation
# services are additional declared adapters. Their complete snapshots are logged.
def hook(uc,address,size,user):
 sp=t.u.reg_read(UC_X86_REG_ESP)
 if address==0x4dba00:
  name=t.m.read_words(sp+4,1)[0];t.original_events.append(((address,t.u.reg_read(UC_X86_REG_ECX),(),t.text(name)),t.snapshot(False)));t.returned(4,2004)
 if address==0x4c82a0:
  t.original_events.append(((address,t.u.reg_read(UC_X86_REG_ECX),tuple(t.m.read_words(sp+4,1)),None),t.snapshot(False)));t.returned(4,0)
t.u.hook_add(UC_HOOK_CODE,hook)
def snapshot_state():
 s=Enemy();s.actor[:]=t.get(t.SOURCE,128);s.primary[:]=t.get(PRIMARY,93);s.enemy[:]=t.get(E,264);return s
calls=events=tls=0
for history in range(48):
 t.prepare(history);t.context.composeCreation=history%2;t.put(t.SOURCE+8,[0x40000]);t.put(t.SOURCE+0xc,[t.SC]);t.put(t.SOURCE+0x6c,[PRIMARY]);t.put(t.INV+8,[t.SOURCE]);t.put(t.INV+0x6c,[t.SOURCE]);t.put(t.INV+0x24,[9,3]);t.put(t.INV+0x2c,[33,0,25,0,41,0,0,0,0])
 t.put(E+8,[t.SOURCE,t.SOURCE,PRIMARY]);t.put(E+0x128,[t.SOURCE,t.SOURCE,PRIMARY]);t.put(E+0x190,[t.SOURCE,t.SOURCE,PRIMARY]);t.put(PRIMARY+0xc,[t.SC]);t.put(E+0x2fc,[32,0 if history%3 else 16]);t.put(E+0x3b0,[0]);t.put(E+0x3a8,[0]);t.put(PRIMARY+0x1c,[2018])
 context=Generic();lib.claw_generic_enemy_context_defaults(C.byref(context));context.actorToken=t.SOURCE;context.primaryToken=PRIMARY;context.enemyToken=E;context.animationDelta=16;context.tick=100;extra=Extra()
 for function,tick in[(0x44e0c0,100),(0x44e0c0,101),(0x43f450,1100),(0x43f450,1101)]:
  context.tick=tick;t.m.write_words(0x537210,[tick]);t.m.write_words(0x5430c4,[context.animationDelta]);t.m.write_words(0x513e10,context.defaults)
  state=snapshot_state();before=bytes(t.heap);before_globals=t.Globals.from_buffer_copy(bytes(t.g));old_cursor=t.cursor;old_actors=list(t.actors);old_created=t.created_count
  t.native_events.clear();t.native_tls.clear();t.callback_errors.clear();t.context.fault=0
  assert lib.world_loot_test_enemy_chain(C.byref(state),C.byref(context),C.byref(extra),function,1,C.byref(t.g),C.byref(t.context),t.dependency,None)==1 and not t.context.fault
  expected=t.snapshot(True);expected_events=list(t.native_events);expected_tls=list(t.native_tls);next_cursor=t.cursor;next_actors=list(t.actors);next_created=t.created_count
  t.u.mem_write(t.BASE,before);t.m.write_words(t.GLOBALS_BASE,before_globals.words);t.m.write_words(0x52a190,[before_globals.itemCount]);t.m.write_words(0x532c10,[before_globals.audioVolume]);t.m.write_words(0x53721c,[before_globals.highLaunch]);t.m.write_words(0x537960,[t.CFG]);t.put(t.CFG,[before_globals.configurationWord],False);t.m.write_words(0,[0x12345678]);t.cursor=old_cursor;t.actors=old_actors;t.created_count=old_created;t.original_events.clear();t.original_tls.clear()
  try:t.m.call(function,E,struct.pack('<I',1)if function==0x44e0c0 else b'')
  except BaseException:
   from unicorn.x86_const import UC_X86_REG_EIP
   print('FAIL',history,hex(function),hex(t.u.reg_read(UC_X86_REG_EIP)));raise
  assert t.snapshot(False)==expected,(history,function,'retained complete death/loot buffers')
  assert t.original_events==expected_events,(history,function,'retained complete callback ordering')
  assert t.original_tls==expected_tls and t.m.read_words(0,1)==[0x12345678]
  t.cursor=next_cursor;t.actors=next_actors;t.created_count=next_created;calls+=1;events+=len(expected_events);tls+=len(expected_tls)
 assert len(t.actors)==(0 if history%3==0 else 3),'original bit4 suppression/repeat guard changed'
 assert t.get(t.SOURCE+8)[0]&0x10000,'original dead-state deletion request missing'
report={'retainedHitLootDeadCalls':calls,'orderedCompleteSnapshots':events,'TLSLookupSnapshots':tls,'histories':48,'originalAddresses':len(t.m.executed),'scope':'Original44e0c0->42df90->43f120 and43f450; creator optionally composed, pickup/image/audio/registry/animation bodies explicit.'}
(t.WORK/'death-loot-chain-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
