"""Whole original plain creators under frozen scene harness services.

The camera startup uses this90-word actor, not the animated109-word variant.
128-word padding is explicitly supplied by the native snapshot interface.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Reuse frozen fixture definitions read-only, redirecting all build artifacts.
# Registry, physical allocation and polymorphic delete/gameplay are services.
original=(ROOT/'Tests/scene_actor_original.py').read_text()
original=original.replace('class OriginalScene(', 'class PlainOriginalScene(')
original=original.replace('count==0x1b4', 'count in(0x1b4,0x168)')
original=original.replace('0x4c9be0,0x4a35f0', '0x4c9be0,0x4c9e60,0x4a35f0')
original=original.replace('0x4c9be0:1,', '0x4c9be0:1,0x4c9e60:1,')
original=original.replace('elif address==0x4c9be0:', 'elif address in(0x4c9be0,0x4c9e60):')
exec(compile(original,str(ROOT/'Tests/scene_actor_original.py'),'exec'),globals())
fixture=(ROOT/'Tests/compare_scene_actor_runtime.py').read_text().split('for i in range(1500):')[0]
fixture=fixture.replace("WORK=ROOT/'work/scene-actor-agent'", "WORK=ROOT/'work/plain-actor-runtime-check'")
fixture=fixture.replace("str(ROOT/'Sources/SceneActorRuntime.cpp'),", "str(ROOT/'Sources/PlainActorRuntime.cpp'),str(ROOT/'Sources/SceneActorRuntime.cpp'),")
fixture=fixture.replace('o=OriginalScene(', 'o=PlainOriginalScene(')
fixture=fixture.replace("('id','x','y','z','entryToken','flags')", "('id','z','entryToken','flags')")
fixture=fixture.replace('lib.claw_scene_actor_create_named', 'lib.claw_plain_actor_create_named').replace('lib.claw_scene_actor_create.', 'lib.claw_plain_actor_create.').replace('lib.claw_scene_actor_create(', 'lib.claw_plain_actor_create(')
fixture=fixture.replace('0x4c8be0', '0x4c8a20').replace('0x4c8da0', '0x4c8b90').replace('args[4]', 'args[2]')
fixture=fixture.replace('if call.function==0x4c9be0:', 'if call.function in(0x4c9be0,0x4c9e60):')
# The unrelated nested animated creator callback is outside this suite.
exec(compile(fixture,str(ROOT/'Tests/compare_scene_actor_runtime.py'),'exec'),globals())
o.executed.clear()
for i in range(1500):
 g,s=prepare(rng.randrange(9));entry=rng.choice([0x4c8a20,0x4c8b90]);o.found=True
 if i%11==0:memory[ENTRY][4]=0;o.write_words(ENTRY+16,[0])
 flags=rng.choice([0,0x40002,0x200000,0x240002,0x20000,rng.getrandbits(32)])
 try:compare(entry,g,s,(rng.getrandbits(32),rng.getrandbits(32),ENTRY if entry==0x4c8a20 else 0x522e3c,flags))
 except Exception:print('plain creator case',i,hex(entry),'original EIP',hex(o.u.reg_read(UC_X86_REG_EIP)),flush=True);raise
# Actual camera startup arguments and metadata, no immediate callback.
g,s=prepare();memory[ENTRY][2]=0;memory[ENTRY][4]=0x486240;o.write_words(ENTRY+8,[0]);o.write_words(ENTRY+16,[0x486240])
compare(0x4c8b90,g,s,(0,9999,0x522e3c,0))
created=o.allocations[0][0]
assert readWords(created,128)[0]==0x5137b0
assert readWords(created,128)[19:21]==[0,0]
assert not any(e[:2]==('call',0x486240)for e in events)
print('PASS1501 complete original plain creators:90-word stores/preserved padding, flags, signed-Z list insertion, initialization rejection, immediate callback and actual camera startup;',len(o.executed),'original addresses')
g,s=prepare();o.found=False
try:o.call(0x4c8b90,CONTAINER,packed(0,9999,0x522e3c,0));raise AssertionError('Original unexpectedly returned for missing metadata')
except UcError as error:
 assert error.errno==UC_ERR_READ_UNMAPPED and o.u.reg_read(UC_X86_REG_EIP)==0x4c7e85
fault=C.c_uint32();allocIndex=0
assert lib.claw_plain_actor_create_named(CONTAINER,CreateArgs(0,9999,0,0),0x522e3c,host,C.byref(fault))==0 and fault.value==1
print('PASS missing-name scope: original null dereference4c7e85; native fault1 early safety extension, no normal-return parity claim')
