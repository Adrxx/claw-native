# Original Elevator controllers and level rectangle profile

This additive module recovers the original v1.0 Level1 moving-platform family
from `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Original registrations and observed direct calls establish every entry boundary;
private Ghidra logs contain no SCRIPT ERROR. Shared original/resources/analysis
projects and frozen source modules were not edited.

## Entry map and ABI

| Entry | Original convention / scope |
| --- | --- |
|49e2a0|cdecl(actor), registered Elevator135/522778/flags1|
|49daf0|cdecl(actor), registered StartElevator131/5227ac/flags1|
|49db10|cdecl(actor), registered TriggerElevator138/52273c/flags1|
|49db30|cdecl(actor), registered OneWayStartElevator136/522764/flags1|
|49db50|cdecl(actor), registered OneWayTriggerElevator137/52274c/flags1|
|49db70|cdecl(actor), registered StopElevator132/52279c/flags1|
|49cdd0|cdecl(actor), complete shared start/trigger/stop controller|
|49e060|cdecl(actor,primary), complete absolute-controller phase initialization|
|49e1c0|cdecl(actor,primary,tick), complete absolute-controller update|
|4061b0|thiscall(registryOwner,name), composed internal lookup to4f6286|
|4a4630|cdecl(numerator,denominator), whole original quotient/remainder executes in oracle; native uses equivalent remainder in its controller's guaranteed nonnegative domain|
|452b00|cdecl(level), complete48-word level profile initializer and14 finite leaf setters|

`claw_elevator_entry` exposes the first9 entries through the raw argument-view
ABI and `ClawSceneActorHost`. Receiver is ignored because these are cdecl.
Its return reports support, separately from the original meaningful result.
Controllers/wrappers return1;49e060/49e1c0 are void and their incidental EAX is
excluded from comparison. `fault1` is a missing heap/service, `fault2` is an
original arithmetic trap and `fault3` is an argument-shape diagnostic. Clear it
before another request. Diagnostic returns do not claim an original successful
return after a fault.

These callback bodies allocate **no private object**, install no vtable, advance
no ANI, create no scene child and invoke no tile movement/collision routine.
They work directly in the generic actor/primary established by the frozen
WorldObjectRuntime loader. Do not add a guessed private physics controller,
oscillation speed, animation update or platform TTL.

`ClawElevatorGlobals` holds six live source aliases:
manager5371fc, defaults pointer537960, player537e88, absolute tick537210,
animation delta5430c4 and wrapper mode53ebf0. Heap lookup must supply actual
actor/primary/image-frame/scene/manager/config/player/private spans. The player
support gate reads player flags+8 bit10 and support actor token+80. Reset tests
read player+6c -> primary+14 -> private+80; this is a raw observed reset word,
not an inferred checkpoint event or substituted host counter.

## Ordinary Elevator

State0 invokes49e060, then establishes platform type80, actor flags bit1 and
movement rectangle from the current image-frame fields18/1c/20/24. A null
frame leaves the old movement rectangle untouched. The support/hit rectangle
comes from the live level profile+68. In level10 (manager+2c -> config+14 ==10),
matching resolved LEVEL_TRAPELEVATOR overrides it with profile+98. A primary
callback identity49e810 selects profile+88. A matching LEVEL_STEPPINGSTONE
image also selects profile+88. Matching compares resource identities, including
zero==zero, and the actor's image root is captured before each lookup. Finally
hit-rectangle bottom increases32. Z0 becomes2000 and setsReorder20000; nonzero
Z is preserved. Captured primary state becomes1.

49e060 uses positive primaryC8/CC distances to replace bounds with actor
coordinate +/- integer half-distance. Otherwise supplied bounds remain literal.
Extent is signed `(upper-lower+1)` with32-bit wrapping; extents below2 become0.
The doubled extent supplies the period. Zero actor speeds148/14c become125.
Actor delta158/15c is cleared. Initial coordinate phase is clamped to0..extent;
direction1/4/7 adds one X extent and7/8/9 adds one Y extent. Each phase is
multiplied by1000 with32-bit wrapping and divided signed by its actor speed.
The original INT_MIN/-1 fault is exposed, with the exact preceding stores.

State1 invokes49e1c0 with the absolute537210 tick. Each axis advances only when
both signed speed and signed doubled extent are positive. The product
`(phaseMilliseconds+tick)*speed` wraps to32 bits, is divided unsigned by1000,
then reduced modulo the doubled extent. Remainder at most extent gives
`lower+remainder`; greater remainder gives `upper-remainder+extent`. Preserve
these original inclusive-bound arithmetic and seam effects. The actor delta is
new coordinate minus old coordinate. A disabled axis preserves its old delta.
There is no per-frame16-pixel cap in this controller. Other states do nothing.

## Start/Trigger/Stop shared controller

The five registered wrappers write mode53ebf0=20,21,22,23,24 respectively on
**every call**, then invoke the complete49cdd0 body. This global side effect
also occurs on idle/deletion/failed calls; it is not a local actor state.

State0 sets the same type/flags/image-derived movement rectangle and ordinary
profile support rectangle, with the level10 trap lookup override. It recognizes
original primary callback identities:

| Primary callback | Added actor164 bits / setup |
| --- | --- |
|Start49daf0|2|
|Trigger49db10|1002|
|OneWayStart49db30|102|
|OneWayTrigger49db50|1102|
|Stop49db70|1|
|49e810|profile88, direction2|
|49eb30|bit2, profile88, direction2|
|49ee20|bits102, profile88, direction2|

The latter three identity branches are part of the recovered shared body;
their distinct registered callback bodies are **not** provided by this module.
Hit-rectangle bottom increases32. Zero bounds are replaced with the current
actor coordinate, unlike ordinary Elevator's phase initializer. Zero speeds
become125, then direction4/6 disablesY and2/8 disablesX. Direction2/3/6 selects
state1001; all others select1000. Primary64 captures the player's private80
word. Startup preserves actor deltas; it does not allocate or advance time.

For nonzero state:

- Actor164 bit2 first clears both deltas. If the player is not supported by this
  actor, equal private80/primary64 returns immediately; changed reset word
  restores actorE8/EC intoX/Y, changes primary state0, and records the new word.
  A supported actor with bit1000 clears bit2, making Trigger movement persist
  after dismount. Start without bit1000 continues requiring support.
- Without bit2, bit1 clears deltas and pauses while the player is supported.
- Bit1000 also checks the reset word after those gates and restores/reinitializes
  on change. This later reset path does not independently clear prior deltas.
- State5 clears deltas and returns. States other than1000/1001 retain fields
  after the above gates. There is no special state29 deregistration work here.
- State1000 approaches lower bounds, state1001 approaches upper bounds. Per-axis
  magnitude is the wrapped low32-bit speed*animationDelta divided unsigned by
  1000, negated for1000 and capped signed to-16/+16. Coordinates add the deltas.
  Bounds do not clamp position: overshoot is retained. Reversal occurs only
  once **both** axes have reached/passed the bound. Bit100 makes that endpoint
  transition state5 instead of reversing.

Resource lookup4f6286 is the only transport service in the controller graph.
It receives the exact registry receiver, raw literal token and optional verified
label. The shared controller's4061b0 wrapper is composed down to that lookup.
Lookup mutations of actor properties and the live defaults pointer are retained.
No player collision election, native rendering, rider displacement or scheduler
implementation is introduced; the host consumes the returned source fields
through its separately recovered collision/support/scene pipeline.

## Complete source level profile

`claw_elevator_initialize_profile(level, ClawElevatorLevelProfile*, optionalSetRect,
user)` recovers452b00 and the14 setters452c50,452cc0,452d50,452db0,452ea0,
452f80,453070,453150,453240,453310,453410,453500,453600,4536f0. The input must be a
valid profile object. Nonpositive signed levels return0 without writes. Positive
levels clear48 words at source5378a0, publish537960=5378a0, store the level in
word0 and537964, then dispatch1..14. Positive levels above14 return0 after
those writes and preserve scale globals. Thus rejection is not universally
atomic. The name `levelWord` describes the observed537964 write; other existing
contexts calling it `difficulty` do not change these source semantics.

The profile contains source literal string byte copies, flag/offset words and
59 ordered SetRect calls across all14 levels. Setters finally store IEEE1.0
words3f800000 into globals5262b0/b4/b8. The optional platform callback receives
the profile destination offset and four raw rectangle words; its return is
ignored. With no callback, equivalent four-word stores implement SetRect. The
source-derived operation tables preserve stores before and after each callback,
including callbacks that mutate profile fields or the selected pointer.

For Level1, full source452c50 supplies:

- Profile58 rectangle[-24,-8,24,32].
- Profile78 rectangle[-24,-46,24,32].
- Platform profile68 rectangle[-32,-8,36,32].
- Word44=0, all other cleared words retained, scaleWords all1.0.

Platforms add32 to the profile68 bottom, yielding[-32,-8,36,64]. Level1's
alternate88/trap98 rectangles remain allzero until changed by another source
profile/service. They must not be filled with guessed common geometry.

The host can map/alias the complete48-word profile at source selectedToken5378a0
and use that token in `ClawElevatorGlobals.defaultsToken`, or publish its contents
under an explicitly rebased heap token. Preserve the complete profile and the
observed537964/scale writes when connecting other modules. The API does not
infer later menu/options/configuration updates or unrelated global aliases.
Literal source operation capture is under `work/elevator-agent/defaults-profile.json`;
whole original comparison output for all14 rows is `verified-level-profiles.json`.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_elevator_logic_runtime.py`.
Final pass: **5,129 whole original calls**, **487 ordered full snapshots**,
**1,835 original instruction addresses**. Every controller call compares the
full524,288-byte actor/primary/player/private/image/scene/manager/config/defaults
heap and all six globals; profile initialization compares every profile word,
selected pointer,537964 and three scales at every SetRect boundary and return.
Strict C++17 and C11 header checks pass.

Coverage includes all11 direction values; level10/ordinary/missing-image-root
lookup branches; the complete startup and supported/unsupported/reset/one-way/
stopped/deletion-state matrix; generated unsigned wrapped steps and signed
bounds/speeds; absolute tick wrapping and disabled axes; live resource/defaults
mutations; signed division overflow and14 missing-identity failure prefixes;
and77 retained profile initializations over all14 rows, invalid levels and
mutating/failing SetRect adapters. There is no allocator failure path in these
bodies because they do not allocate.

All26 Elevator,4 TriggerElevator and1 StartElevator raw Level1 WWD records are
loaded through the frozen source WorldObjectRuntime into real actor/primary
profiles. Retail LEVEL1/IMAGES/ELEVATORS/1.PID dimensions/hotspots are projected
through frozen SpriteGeometry; resource file transport and binding are explicit
adapters. Each starts from the source Level1 profile and retains96 supported
updates, dismount, reset-word change, reinitialization and deletion-state visit.
The suite makes2,976 supported update comparisons. It does not claim another
full loader/decoder proof: those source modules have independent original
comparisons. Player placement/support election are synthetic fixture inputs,
not an asserted complete rider physics history or pixel-rendered gameplay.

The recovered finite family covers these31 Level1 records. StandardElevator,
SlidingElevator, PathElevator and the distinct49e810/49eb30/49ee20 bodies remain
outside this dispatcher's scope. Whole-game scheduling, collision election,
player rider application, physical rendering and other levels' actor population
are not established by these routine comparisons. Summary and retained record
results are in `work/elevator-agent/verification.json`.
