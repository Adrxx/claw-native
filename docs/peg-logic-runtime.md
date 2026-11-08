# Original CrumblingPeg and TogglePeg controllers

`PegLogicRuntime.h/.cpp` recover a finite original v1.0 platform family from
`Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Original registration and direct-call instructions establish true entry bounds;
private Ghidra analysis resides under `work/peg-agent/`. Its logs contain no
SCRIPT ERROR. Shared original, frozen source and project files were unchanged.

## Address map and raw interface

| Entry | Original scope |
| --- | --- |
|49d860|CrumblingPeg146, literal5226ac, metadata flags2|
|49d620|CrumblingPegNoRespawn147, literal522694, metadata flags2|
|49e4e0|TogglePeg148, literal522688, metadata flags2|
|49e7b0|TogglePeg2/149, literal52267c, flags2, wrapper mode2|
|49e7d0|TogglePeg3/150, literal522670, flags2, wrapper mode3|
|49e7f0|TogglePeg4/151, literal522664, flags2, wrapper mode4|
|49e470|Toggle initialization: defaults/period from actor148/14c|
|49e4b0|Wrapped absolute-tick visibility predicate|
|40f680|Signed image-index/range/frame-array selection, composed internally|
|4ca610|Complete bounded name/spatial routing wrapper, composed down to4c88e0|

The six registered callbacks are cdecl(actor). Helpers49e470 and49e4b0 are
cdecl(actor,primary) and cdecl(actor,primary,tick).4ca610 is thiscall with raw
receiver and four stack arguments(name,sourceX,clampDistance,panDistance).
`claw_peg_entry` preserves these shapes through the raw argument-view ABI.
Support is separate from the original meaningful result: callbacks return1,
49e4b0 and4ca610 return0/1, while49e470 is void.

`ClawPegContext` supplies the live token heap, shared `ClawPegGlobals`, an
explicit dependency callback, and `composeAnimation`. Set composeAnimation=1
to run frozen ActorAnimationRuntime/AnimationEngine/AnimationOperations bodies.
Zero delegates the exact ANI service calls for directed boundary tests; it
must not be described as completed animation. Fault1 reports a missing span or
service,2 an original unsigned division trap,3 an argument/ANI profile safety
diagnostic. Clear fault before another request; these diagnostics are not
fabricated original successful returns. The composed ANI module retains its
existing valid-metadata/reentrant-mutation limits documented in its own API.

Shared globals are defaults537960, player537e88, absolute tick537210, ANI
delta5430c4, gate53725c, audio manager532c0c, volume532c10 and wrapper mode53ebf0.
Do not allocate per-actor substitutes for these globals. The toggle wrappers
write mode2/3/4 every call; ordinary TogglePeg leaves it unchanged, including
whatever an Elevator or another wrapper last published.

No body allocates private state, installs a vtable, creates a child, reads the
OS clock or performs tile/player collision election. The generic actor/primary
allocation and raw WWD fields are supplied by frozen WorldObjectRuntime. Source
clock fields, resource identities and ANI state remain actual heap aliases.

## CrumblingPeg

State0 optionally selects image root minimum64 through the signed range check
and frame pointer array14. It sets typeD0=80 and actor flags bit1, binds literal
52dd04/GAME_FORWARD50 with eager0, clears delta158/15c and copies default
profile78 into hit rectangle128. Bottom134 increases32, actor164 gains8000,
and Z0 becomes2000 withReorder20000. Speed/delay148 defaults to25 if zero.
Primary state becomes5 and primary64 receives signed wrapped(minimum+maximum)/2
when an image root exists. A missing image root preserves the prior midpoint.

Respawning49d860 additionally clears actor40 hide bit1 and defaults direction
110 to4 if zero. NoRespawn49d620 does neither. Move rectangles, coordinates and
other property fields are preserved; no falling platform motion is invented.

State5 arms only when gate53725c is0, player flags+8 includes10, and player
support token+80 equals this actor. It writes primary state1002 and primary20
from actor148. Scripted state1111 arms under gate0 without testing player
support. The callback **does not decrement primary20**. The frozen scene actor
scheduler delays callback election according to that source field; a host must
not replace it with a guessed crumble timeout.

State1002 looks up52dd24/LEVEL_PEGCRUMBLE only when the sound registry's30
word is0. Lookup is on actor+C -> scene28 -> registry10. A resolved sound plays
through frozen AudioEvents4208e0-equivalent routing when532c0c is present,
using current532c10 and zero pan/pitch/loop. Then captured primary becomes1005,
even when the sound is unavailable or disabled. Physical4b45f0 remains explicit.
The NoRespawn original inlines the same manager/pool check; both paths match
their complete original bodies and ordered lookup/play snapshots.

State1005 advances actual actor+188 animation using ANI delta5430c4. Equality
between image index16c and midpoint primary64 changes typeD0 to1. Once stopped
1a4 is nonzero and delay19c is0, NoRespawn setsDelete10000. Respawning CrumblingPeg
sets actor40 hide bit1, state23, and primary64 to the player's current private80
reset word.

Precisely, the reset word path is **player+0x6c -> primary+0x14 -> private+0x80**.
In state23,49d860 reinitializes only when signed(primary64) is strictly less
than signed(current reset word). Equal, lower and wrapped-negative values do
not reset it. This differs from Elevator's inequality reset predicate. It does
not automatically respawn after time elapses. Other states, including29, have
no special gameplay/destruction work in these callbacks; generic scene removal
is separate.

## TogglePeg

State0 clears deltas and selects the minimum frame when an image root exists.
It sets type80/flags1 and copies default profile58 into hit rectangle128, adding
32 to bottom. Z0 becomes2000 with flags based on the originally captured actor
flags. Callback identity49e7b0/7d0/7f0 overwrites primaryBC with750/1500/2250;
ordinary TogglePeg preserves the WWD phase offset.

49e470 defaults zero actor148/14c to1500 and stores their wrapped sum in primary
4C. Primary state becomes1006, and primary64 receives the signed image midpoint.
Gate53725c nonzero or actor108==1 overrides startup state to5. Such state5 pegs
remain static in this callback; do not activate them with an inferred timer.
No ANI is selected during ordinary TogglePeg startup.

49e4b0 computes unsigned wrapped `(tick-primaryBC)%primary4C`, interprets the
remainder and actor148 as signed, and returns remainder<=actor148. The threshold
is inclusive. Primary period0 produces an original DIV trap; the native exposes
fault2 with the same preceding buffer stores. There is no fixed host time step.

| State | Source behavior |
| --- | --- |
|1006|Visibility predicate false selects1004; true retains1006.|
|1004|Type1, bind GAME_FORWARD50 eager0, request named slide sound, select1003.|
|1003|Advance ANI. At midpoint set type1. On stop/delay0 keep type1, bind GAME_BACKWARD50 eager0, select1007.|
|1007|Visibility predicate true selects1002; false retains1007.|
|1002|Request named slide sound, select1005. The backward ANI was already selected by1003.|
|1005|Advance ANI. At midpoint set type80. On stop/delay0 keep type80, bind GAME_FORWARD50 eager0, select1006.|
|other|No side effects beyond an enclosing wrapper's mode write.|

The hidden/visible type change occurs at exact frame-index equality and at
animation completion. Do not reduce this graph to periodic show/hide flags or
an independently chosen host crumble/toggle period.

## Audio/resource and native host contracts

GAME_FORWARD50 and GAME_BACKWARD50 use original literals52dd04 and52dd14.
The frozen actor ANI binder resolves through scene2c -> registry10. Its record
selection, time, image/control operations and stop fields are composed. Resource
transport returns raw sequence headers, pointer arrays, records and image roots;
it must retain source identities and original frame numbering.

The complete4ca610 slide wrapper first reads sound registry+C -> scene24
collision manager, requires nonzero manager and manager5C plane, then checks
registry30 disabled. Only then does4f6286 resolve528a3c/LEVEL_PEGSLIDE on
registry+10. A sound calls4c88e0(sound,sourceX,-1,clamp,pan). Toggle callers pass
actorX and zero clamp/pan. Registry/plane absence and disabled/missing resource
return0. Missing required pointer spans diagnose the original failing graph.
Native physical spatial audio and voice playback remain explicit services;
there is no invented voice output or camera coordinate.

Compose the complete level profile from frozen ElevatorLogicRuntime's452b00
initializer. Level1 profile78 yields CrumblingPeg hit[-24,-46,24,64], and
profile58 yields TogglePeg hit[-24,-8,24,64]. Bind actual image roots/ANI records
before startup, publish the player's live flags/support/private reset word, and
let the existing scene scheduler consume primary20. Actor Delete or state29
lifecycle invokes the separately recovered generic destruction/removal path.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_peg_logic_runtime.py`.
Final pass: **12,085 whole original controller/helper calls**, **1,476 ordered
full snapshots**, **952 original instruction addresses** and **625 separate
whole original4d76e0 record decodes**. Every call compares the complete524,288-byte
heap plus8 globals. Strict C++17 and C11 checks pass. No allocation failure can
occur in the peg bodies themselves because they do not allocate.

Directed coverage includes all source states, gate/support combinations,
ANI stops, resource/audio disable paths, wrap and signed visibility arithmetic,
lookup-time property/default mutations, DIV-by-zero and9 missing-pointer
failure prefixes, and complete spatial-name routing gate/call ordering.
The valid composed ANI profile uses actual retail original-disc
GAME/ANIS/FORWARD50.ANI and BACKWARD50.ANI. Image roots/frame numbering and file
transport are explicit adapters; every record is compared with original decode.

All64 CrumblingPeg and56 TogglePeg/2/3/4 raw Level1 WWD records are loaded through
frozen WorldObjectRuntime with actual metadata flags2, source Level1 profiles,
and all12 retail PID frame geometry records for CRUMBLINGPEG/PEG. Each crumbling
profile retains support arm -> source delay field -> sound -> actual ANI ->
midpoint type change -> stop/hide/state23 -> equal/lower/greater reset-word
checks -> source reinitialization. Each toggle profile retains170 clock/ANI
updates: active records visit all six phases and actor108==1 records remain5.
Deletion-state callbacks and a separately selected NoRespawn actual-resource
lifetime throughDelete are also compared. Level1 has no NoRespawn WWD record;
that alternate callback selection is a directed fixture.

Player support/election and the scheduler's clearing/election of primary20 are
explicit fixture inputs. These retained histories verify the complete selected
callbacks/ANI graph; they do not claim another whole4c8fc0 scheduling proof,
complete rider collision physics, original resource enumeration, rendering,
physical sound playback or whole-game parity. Those services/modules have their
own boundaries and comparisons. Summary and record histories are saved in
`work/peg-agent/verification.json`.
