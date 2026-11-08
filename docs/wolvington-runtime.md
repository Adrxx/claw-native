# Original Level6 Wolvington

`WolvingtonRuntime` reconstructs the pinned original v1.0 Wolvington facade,
constructor, specialized states, and specialized WolvingtonBullet. It composes
frozen CBoss/Raux, actor wrapper, image binding, animation, and lifecycle bodies.
Shared WolvingtonLFX belongs to frozen `FlareRuntime`; gem creation belongs to
frozen `EndLevelGemRuntime`. Those source bodies are not duplicated here.

The executable fingerprint is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`;
the disc REZ fingerprint is
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Original instruction boundaries and decompiler logs are in the module's private
`work/wolvington-agent/`. An exploratory request for458580 failed boundary
verification; the actual source state is458570. No failed decompile is used as
a recovered function.

## Identity and allocation

The verified registry has `Wolvington`, literal522c54, ordinal43, callback49fb30,
flags0. The sole retail record occurs in Level6, plane1, row183, offset675444,
id2877 at(34960,4496,0), image name`LEVEL_WOLVINGTON`. All14 worlds contain34,784
records; none of the other13 contains this logic. Source-derived inventory and
all71 record words plus strings are retained in private JSON.

49fb30 allocates478 bytes (286 words), calls49fbf0, selects vtable50ff2c, invokes
slot10, and only then publishes primary+18. Primary+1c changes0→1000 before
allocation. States29/30 elect slots20/1c;1000 skips; other states call original
cdecl4dc870(private). Null allocation dereferences null after this prefix.

`WolvingtonBullet`, literal522da8, ordinal15, callback410340, flags0, allocates158
bytes (86 words); constructor411cf0 selects vtable50b87c. WolvingtonLFX458010
allocates4c bytes in FlareRuntime, not in this module. Generic actor allocations
remain source1b4 bytes; portable frozen services may marshal128 words internally.
The private fixture uses explicitly larger raw backing and compares untouched
padding as well as live fields; this is not a claim that the source allocates
that padding.

## C11 host recipe

Use `ClawWolvingtonContext` with the raw `ClawSceneActorHost`, borrowed identical
`ClawRauxGlobals`, and explicit composition flags. `claw_wolvington_entry` accepts
an original function identity, ECX receiver token and actual stack arguments.
Facade49fb30/410340 is cdecl: receiver0, one actor argument. Constructors49fbf0/
411cf0 take ECX private and actor argument. Dispatch4a0230/411e70 takes one state;
pre4a0740 takes original name token; deleting4a0140 takes mode. Other owned
entries take no stack arguments. Support/diagnostic status is separate from
meaningful EAX. Unknown identities return0; faults1/2/3 denote missing span,
unsafe arithmetic, or bounded/ABI diagnostics respectively. Clear a previous
fault before a new independent call.

The dependency receives exact function/receiver, up to12 raw arguments and an
optional verified source literal name. Preserve pointer identities and aliases;
argument literals remain their original PE tokens. Names are transport metadata,
not replacements for pointer comparisons. `claw_wolvington_function` returns
only the45 callable boss slots and12 bullet slots; trailing vtable data is not
callable. The inherited health-reset slotb0 is original47eeb0, supplied by frozen
Raux. Other inherited Human/Common/Combat entries retain their exact source
addresses and should route to those frozen modules. Boss destruction4a0160
composes frozen47e810 because its actual complete field/leaf sequence is equal;
no independent generic destructor is invented.

Provide global aliases5371fc manager/app,537e88 player,537210 absolute tick,
5430c4 animation delta,534eac level,532c0c sound gate,532c10 master volume,
541334 jump gate,5349dc boss,5262b0/b4/b8 float scaling. Volume is the semantic
meaning of532c10, despite older portable fields named audioPosition. Keep
source53724c magic-disabled separate; manager+124 is the source LFX gate.
Manager+2c points to actual scene owner; its+768 is the palette-table token,
passed by FlareRuntime to compressed image metadata, not opacity.

## Specialized source behavior

Constructor49fbf0 completes CBoss40e0d0 then binds44 actual Wolvington PIDs and17
source ANI getter calls, each independently falling back toGAME_NULL. Four
sound strings and two sound-pointer fields preserve lookup order. Rectangles,
scaled health100/damage30 and range probability are source stores. The source
probability clamp is unsigned`value<100 ?99:value`, including unusual scales.
Only the specialized tail460 is zeroed; other unnamed tail words retain allocator
contents until their elected states write them.

Class53ec68 overrides HOME4a0960,SGATTACK4a0ae0,GATTACK4a0cf0,
SUPPERCUT4a0f40,SWORDATTACK4a1020,RUNUPPERCUT4a10f0,ADVANCE4a1250. Preserve the
source spelling`LS_SUPPERCUT`. IDs come from the verified complete registry boot
capture, rather than fresh CEnemy-only IDs. Class selectors perform the original
double lookup, including cache/error/default path side effects.

SGATTACK retains the source signed random%11 counter; counter10 calls virtual44
before clearing460 and rereading the counter. GATTACK animation marker latches
1a0 before creation, sets child damage15/type40, invokes its cdecl registered
callback, then reacquires its primary/private for vx/vy/gravity and mirroring.
Creation/audio/metadata/collision transports remain explicit. Uppercut and sword
markers install different source rectangles; run-up uses wrapped integer4×speed,
not an inferred floating multiplier.

Inherited idle44f1b0 is220 bytes and recovered here because no other module owns
it: facing/rect mirrors, vx0, LS_IDLE transition, signedrand%100<33 plus
actor+38!=-1 elects cdecl48ce40(actor,private420,0), selects ANI350, writes2000ms
and absolute tick into43c/438. It does not turn speech into a guessed cooldown.

Bullet411cf0 bindsLEVEL_WOLVINGTONMAGIC andGAME_CYCLE50, sets actor flags80000,
and elects LFX only with53724c==0 andmanager+124!=0; sparkle count is2 withLFX,
1 otherwise. Class534ad8 overrides FALLING412150. That body calls frozen4742f0,
then uses two source signed remainders per sparkle over inclusive movement
rectangle extents. Width0 usesrandom&1; RAND_INT_MIN%-1 is a source arithmetic
fault. It emits GlitterBaby creation/initialization explicitly. Negative vx
mirrors LFX private38/40 and visual actor rectangles once, then follows current
physics positions. Ordinary positive/zero velocity preserves the mirror state.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_wolvington_runtime.py`, then
`zsh work/wolvington-agent/run-sanitizers.sh`. The oracle executes unchanged
original instructions and compares the complete512KiB raw fixture plus192KiB
source global image after every call and hashes those full buffers at every
ordered service event. Meaningful facade/constructor/deleting EAX and random/
query consumption order are checked. Final counts are recorded in
`work/wolvington-agent/verification.json` and sanitizer log.

The fixtures retain real WWD record startup and six120-frame boss histories,
actual44 boss images/16 boss ANI groups plusGAME_NULL, and actual magic/LFX image and
ANI records. Joined bullet startup, Flare initialization, flight, collision-flag
and29/30 lifecycle calls compose frozen bodies. Physical creation is a declared
deferred actor transport; GlitterBaby's body remains an explicit callback service.
The separate boss emitter fixture verifies all creator arguments, child stores,
callback order and alias reacquisition with a declared child callback; it does
not claim a whole native arena boss-to-player damage acceptance test.

The original grounded/collision/visibility services use a declared finite
fixture profile. Metadata binders use an explicit empty secondary/core-registration
profile; dictionary/resource lookup uses explicit borrowed raw tables and pinned
assets. Some directed constructor tests deliberately expose the inherited Human
constructor as a logged service; joined tests execute the frozen whole body.
Physical audio, speech, resource traversal, heap allocation, scene insertion,
renderer, and OS transports are not recovered by this module. Full WinMain,
retail Level6 arena completion, physical-device acceptance and full-game behavior
identity remain separate work. Invalid source prefixes are compared to actual
faulting instructions; native bounded diagnostics do not promise source recovery
from those faults. Count>4096 is an explicit native guard, not a source mechanic.

Final module suite:2,053 normal original calls,9,960 ordered complete-buffer
service events (including unsafe-prefix events),5,042 original instruction
addresses and four original unsafe prefixes. The249 original-matched corpus
replays pass ASAN/UBSAN with1,259 ordered full-buffer snapshots. C11 compile,
C++17 `-Wall -Wextra -Werror`, Python syntax and an executed Swift C ABI smoke
pass. Stable source-derived host metadata is `work/wolvington-agent/integration.json`.
The Wolvington IDs are HOME2018,SGATTACK2047,GATTACK2048,SUPPERCUT2049,
SWORDATTACK2050,RUNUPPERCUT2051,ADVANCE2021; projectileFALLING2001.

## PID word0 integration proof

`work/wolvington-agent/verify-pid-firstword.py` makes60 whole original calls and
180 complete1MiB raw-heap/global service snapshots, reaching1,340 original
addresses. It uses the fingerprinted actualGAME_LIGHTFX_FLARE/FRAME001.PID
(word0=99999/0x1869f,flags24,width100,height100) andWOLVINGTONLFX/FRAME001.PID
(word0=99999,flags64,width80,height46). Mutating only word0 to0,10,99999,
FFFFFFFF or12345678 produces equal complete loader outputs when the unchanged
input span's first word is normalized. Original4d2410→4d25e0→4bfc50 executes:
flags/geometry are read after word0, and only bytes atPID+32 onward are copied
into the compressed side object. Word0 has no signature election in this graph.

The joined wrapper/pixel proof executes4d2890→4bffa0 and all four original normal
pixel bodies4c00b0/4c0450/4c0920/4c0cc0. It explicitly calls actual4c6130(mode1)
after the full unchanged loader to isolate normal compressed pixel transport.
WolvingtonLFX flags64 actually elect mode2 during loading; mode2 lighting pixels
remain a separate renderer scope. The compressed raw pixel object does not retain
word0, so rejecting these assets because word0 differs from10 has no source basis
in the measured graph. Geometry, run decoding, capacity and token-span safety
checks are separate. The test uses an owned private copy of the frozen image
oracle with private output paths; it edits no frozen image/blitter source.
