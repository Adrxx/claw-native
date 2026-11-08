# Original enemy and Claw dialog routing

This additive module recovers the fingerprinted original v1.0 speech services
`420370`, `48ce40`, `48ceb0`, `48cc60`, `48cf50`, and `48cf90`. It also supplies a
live token-heap adapter for the frozen player queue functions `48c820/48c8a0`
and the profile-verified `SpeechActor` callback `48c630`.

Original executable: `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The registered `EnemyDialogSound` entry is **48cc60**, metadata ID198, literal
`5223b8`; `ClawDialogSound` is **48c630**, ID197, literal `5223cc`.
An interior address such as48c950 is not a registered callback or recovered
function entry. Existing `SpeechActor.cpp` is correct for the Claw profile and
must not be used as an NPC speech controller.

## Raw API and globals

`claw_enemy_speech_entry(function, receiver, args, count, context, dependency,
user, result)` returns support independently of the original meaningful result.
The recovered functions below are cdecl; the receiver parameter is ignored.
`420370` and `48cf50` are void, so their original incidental EAX is not an API
result. Callback `48cc60/48c630` always returns1 on successful execution.

| Function | Arguments | Behavior |
| --- | --- | --- |
|48ce40|speaker actor, sound resource, force|NPC direct queue, result0/1|
|48ceb0|speaker actor, name token, force|NPC name resolution then queue, result0/1|
|48cc60|dialog actor|Complete NPC dialog controller|
|420370|attacker type|Select and queue one Claw death line for attacker type2/32|
|48cf50|speaker actor|Cancel the matching active NPC speaker|
|48cf90|speaker actor|Identity equality with the global NPC speaker, including0==0|
|48c820|sound resource, force|Frozen player queue over the live actor/primary heap|
|48c8a0|name token, force|Player name lookup followed by its live queue gate|
|48c630|dialog actor|Frozen Claw controller over valid constructed raw buffers|

The host provides a live `ClawSceneActorHost` lookup for actors, primaries,
scene/registry owners, manager/settings, resources and pools. Actor/primary
views follow the existing128/93-word frozen ABI. Dialog actors are actual
0x1b4-byte generic actor allocations with0x174-byte primary allocations; this
family allocates no private gameplay buffer. A host may provide padded views
without changing the original requested allocation sizes.

`ClawEnemySpeechGlobals` is shared among every speaker:

| Field | Original address |
| --- | --- |
|managerToken|5371fc|
|playerToken|537e88|
|audioManagerToken|532c0c|
|clawBusy / clawActorToken|53c9a0 /53c9a4|
|enemyBusy / enemyActorToken|53c9a8 /53c9ac|
|speakerToken|53c9b0|
|stageDelta|53720c|

Use the actual millisecond stage delta, not the ANI delta5430c4. Global values
and all pointer identities remain live through synchronous dependencies.
The context's optional `nameHint` labels the raw48ceb0/48c8a0 name token for a
native resource transport; it must refer to that token's actual string and must
not replace its identity. The module supplies the verified literal labels for
420370, default-image lookup and named dialog actor construction.

`fault=1` diagnoses a missing heap span or required dependency; `fault=2`
diagnoses a bad argument shape or source factory failure. These are host
extensions, not invented original returns. Clear fault before another request.
Supported execution and original failure prefixes are distinguished in tests.
The frozen Claw bridge requires valid constructed player/manager/resource
spans and separate actor/primary objects; its eager field projection does not
claim instruction-prefix identity for arbitrary malformed Claw pointer graphs.

## Queue ordering and ownership

48ce40 rejects zero speaker/resource, missing registered EnemyDialogSound,
busy speech with force0, or a zero primary pointer. It writes actor+184 to the
resource, then the currently registered actor's primary state1001, then global
speaker53c9b0. It does not check the player's death state, speech settings or
physical audio manager and does not set busy or play immediately.

48ceb0 performs those same actor/force/primary checks **before** resource
lookup. Lookup uses manager+30 -> scene+28 -> registry+10 and4f6286(name).
Missing resource returns0 without queue stores. Success rereads the registered
actor and its primary; it does not repeat the busy/force gate. A resource service
that changes the registration or sets busy can therefore still produce a
successful queue. A post-lookup null primary produces the original bad-pointer
prefix after the sound store; native diagnostics expose that failure.

The player queue composes frozen AudioEvents: unforced requests additionally
reject player primary states28,5004,5005. Name lookup occurs before that live
queue gate. Forced requests bypass the busy/death gates. The actor's resource
and primary still must exist. Queue acceptance does not depend on audio output
being enabled or available.

No queue entry stops an existing physical voice. Replacement can happen before
busy is set or under force. Actual overlap/reuse belongs to the shared recovered
voice-pool runtime and native audio service.

## EnemyDialogSound controller

| State | Exact state changes |
| --- | --- |
|0|Set actor40 bit1, flags8 bitsc0003, typeD0=4000000. Bind GAME_EXCLAMATION through4c7970. Set the captured primary state5, then register this actor in53c9ac.|
|5|Clear53c9a8 and53c9b0; set actor40 bit1. Does not itself clear queued sound.|
|1001|If no queued sound or manager+118 is0, set captured primary5 and clear actor184. Otherwise read sound+10 -> pool+28 duration, set primary15 and timer130; reread actor184 and optionally call4b45f0. Does not set busy yet.|
|15|Set53c9a8=1. If the speaker hasDelete10000, clear speaker and timer. Hide the icon when no speaker; otherwise follow its X, Y+top-30 and layer+1, flaggingReorder20000 only on layer change. Saturating unsigned subtraction of stageDelta from timer130; expiry clears queue and sets primary5.|
|29|Clear53c9ac unconditionally. Busy/speaker are unchanged.|
|other|Return1 with no side effects.|

Playback uses the live sound+10 pool token. Volume is manager+12c+10 with32-bit
wrap and signed upper clamp100, pan0, pitch0, looping0. Audio-manager absence
suppresses only4b45f0; it does not suppress state15 or its timer. Settings+118
is the earlier speech enable gate. Zero duration still requests playback.

48cf50 acts only when the argument equals53c9b0, registered53c9ac is nonzero
and its primary state is15: timer130 becomes0 and speaker53c9b0 becomes0. It
composes the identical frozen ActorDestruction entry using explicitly named
aliases. The subsequent controller visits expire and clear busy. Cancellation,
expiry and deregistration contain no physical stop request.

The Claw profile has separate registration/busy globals, follows the player,
uses volume+20, freezes state15 when the player is absent, and expires existing
speech for player states5004/5005. It does not use53c9b0 or the NPC Delete test.
The raw adapter commits and reloads actor/primary shadows around image/play
services so live raw mutations are retained. Only the globals written by the
original state are published after the frozen callback.

## Claw death-line selection

420370 first requires nonzero player537e88 and attacker type2 or32. It calls
4a3050, uses signed remainder10 and accepts only results0..9. Negative
remainders fall through without a name lookup. The original literal routing is:

| Choice | Literal | Resource label |
| --- | --- | --- |
|0|524e04|CLAW_1001|
|1|524df8|CLAW_1004A|
|2|524dec|CLAW_1004B|
|3|524de0|CLAW_1007A|
|4|524dd4|CLAW_1007B|
|5|524dc8|CLAW_1010|
|6|524db8|CLAW_1110033|
|7|524da8|CLAW_1110059|
|8|524d98|CLAW_1110063|
|9|524d88|CLAW_1110058|

Each choice invokes the live48c8a0 player-name queue with force0. The host's
4a3050 service must share the game RNG with other callers. It can compose the
frozen `claw_world_loot_next_random` CRT LCG after its platform thread-local
lookup; this suite also runs the whole original4a3050 with only4a7dc0 adapted.
There is no independent speech seed or inferred sequence selection.

## Source construction and host integration

`claw_enemy_speech_create(containerToken, enemyProfile, ...)` composes frozen
SceneActorRuntime's actual4c8da0 named creation. The source single-player scene
startup profile is id0,x0,y0,z1000,flags40000 and respectively literal5223cc or
5223b8. Original metadata flags0 do not add eager dispatch. The constructor
leaves primary state0; registration occurs only when the scheduled callback
runs. Do not register a fabricated dialog actor or mark busy on construction.

Route registered48cc60/48c630 callbacks through this module and invoke their
state29 callback during the source destruction lifecycle. Expose each actor's
scene pointer, primary pointer, manager/settings and sound/pool metadata through
live heap aliases. GAME_EXCLAMATION is an image lookup, not an ANI controller.
The image binder composes the frozen default-image implementation, preserving
missing-image frame/index retention and original lookup ordering.

Resource/name lookup4f6286 is an explicit transport service. Physical4b45f0 is
an explicit audio service with the exact pool/volume/pan/pitch/loop arguments;
connect it to the shared source AudioEvents/AudioResourceRuntime backend. Scene
allocation/list storage and Win32 thread-local context are host boundaries.
The generic allocator/list failure prefixes are composed, not duplicated.
No Swift host, native voice backend, renderer, scheduler shortcut or audible
output is implemented by this task. Ordinary NPC physics/ANI/loot/FX beyond
these speech callers remain their frozen modules and explicit fixture services.

## Verification

Run `work/test-env/bin/python Tests/compare_enemy_speech_runtime.py`. The private
dylib is compiled with C++17,-O2,-Wall,-Wextra,-Werror,-ffp-contract=off. Its
shared fixtures are consumed read-only. The original harness fingerprint-checks
the executable and executes the complete speech entries, image binder, source
named creation, actual Human/Officer/Soldier constructors and selected callers.

Final pass: **1,256 whole original calls**, **3,057 ordered full snapshots**,
**3,684 original instruction addresses**, with393,216 bytes of retained extra
heap plus complete enemy/actor/primary/contact/private-tail/player/platform/
FX/context/scene/list/bitset buffers, all9 speech globals and player primary.
The source401000 copied CString registry/name pointers are retained and checked;
they are not replaced with literal-name addresses.

Coverage includes the queue gate matrix; both registered controller state
profiles; settings/audio absence; signed volume overflow; zero/unsigned/max
clock deltas; missing sound/image/logic metadata; allocator1/2 failure prefixes;
post-lookup registered actor/busy/primary mutation; post-play actor/global
mutation; cancel/equality including0==0; player death gates; source generic
creation -> registration -> queue -> play -> pending replacement -> busy ->
forced replacement -> expiry -> idle -> deregistration; and48 retained actual
CRT RNG steps from6 seeds with only thread-local lookup adapted.

All26 Officer and16 Soldier Level1 WWD raw records run their full source
constructors and real Level1 tile grounding/queries, then HOME queue -> NPC
play/follow -> busy rejection -> cancellation/expiry -> typed-death420370 ->
Claw name queue/play/expiry. Their placement, last-attacker identity and collision
election are directed fixture inputs. Caller RNG choices are directed adapter
outputs; the separate48-step check verifies real RNG/name selection. Sound
metadata duration100 is a declared fixture pool value, not a substituted game
TTL or an asserted duration of every actual WAV. Physical audio is logged at
4b45f0, so these tests establish control/ownership/parameter behavior, not
whole-game scheduler parity, PCM playback timing or completed voice output.
The Windows SEH/TLS scaffold for original allocation failures lives outside the
game heap snapshot and is a platform adapter. Verification details are saved
in `work/enemy-speech-agent/verification.json`.
