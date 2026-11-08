# Native original death-command and respawn host

`Sources/ClawNativeRespawn.swift` binds the frozen original application command
handler426e30 and respawn controller46be40. It does not call the Swift level
loader. A dequeued803a/8006 batch transfers ownership to `consume(commands:)`;
unknown commands and commands not attempted after a fault are returned.
`handle(command:)` is deliberately non-reentrant: posted messages are processed
outside the player hit/death callback. Original death election sets private+0x18
(index6), decrements lives unless configuration mode4, optionally restores an
infinite life, increments deaths, and posts precisely one WM_COMMAND.

The source gate803a accepts current state type3/4/6. Missing current state is a
recognized no-op. An accepted state's missing player/palette makes46be40 return0
and sends the original8005/3fb fallback.8006 selects state5 when application+9c
is zero, setting old state+38 first, or state12 with retained state history
otherwise. UI construction, fade/window/music/resource transport and state
lifecycle services are explicit; missing service routing produces fault4 rather
than a success adapter. A fault can follow partial original mutations; do not
replay an already consumed command.

## Integration hooks and aliases

The initializer takes the same pinned `ClawTokenHeap`, application token,
`ClawPlayerDeathCommandGlobals`, a clock-capable `ClawSceneActorHost`, and:

- `playerPrimary(actor)`: import live actor, primary logic and private78 words,
  dispatch the actual415df0 initialization body when primary state23, and export
  all changed buffers and physics. Keep the existing initialization/input
  contexts, checkpoint coordinates and accumulator globals. Do not reconstruct
  the player or copy state0 defaults.
- `actorFrame(container, refresh)`: run actual4c8fc0 scheduling with refresh1 and
  existing scene globals. This is distinct from outer ordinary46ac30 rendering.
- `service(call)`: route exact original addresses, returning nil for unavailable
  dependencies. Route4d2000/4d1fd0 to frozen SpatialGridRuntime,4cb9b0 to the
  frozen/native plane renderer, and the live renderer virtual+34 to presentation.
  Source game-over constructor/helper services can compose SinglePlayerSceneRuntime
  where its actual entry matches. Fade48fae0/48fbe0 and audio4b55a0/4b55b0,
  sound registry4061b0/4208e0 remain declared platform/resource services.
- `captureTiming` / `publishTiming`: import/export global541328 clock5words,
 537208/53720c stage clock and5430c8/5430c4 animation clock. Preserve accumulated
  time and the countdown words. Use the same aliases as GameFrameRuntime.
- `importPlayer`: after controller timing reset, import private+120 (20000) from
  the heap without overwriting it with a stale Swift cache. Source callbacks can
  also mutate player/scene/plane identities; use current heap tokens.
- `observe`: optional pre-call instrumentation; records the same call order as
  `events`. `unresolvedServices` is cumulative, `events` is per command.

The application requires77 words; singleplayer owner478 words.
`installActorContainerMetadata(heap:)` supplies the actual original513c20
18-word vtable required by the controller virtual+24 lookup. It validates any
already installed table rather than replacing unrelated host bytes. The native
scene also needs its ordinary50c264 singleplayer owner metadata. Source convenience
constructors execute4254a0 and the actual inlined428d81..428dce state constructor.
They require the CRT empty CString alias cell52e1cc and clock541328. They preserve
unwritten heap bytes. Caller supplies the actual application+2c current state,
application+30 scene,+7c/+80 viewport dimensions, owner+4 application,+c scene
and+2c palette bindings. Those links are a declared startup profile until the
full REZ/graphics/state initialization graph is integrated; this is not WinMain
or retail startup acceptance. The source constructors alone do not produce a
usable palette or renderer.

## Preserved controller order

46be40 pauses enabled music, optionally projects/clamps the old player position
and requests fade-out1250ms. It sets primary+1c=23 and invokes the live player
callback immediately. State23 restores health100, chooses both checkpoint
coordinates only when neither isFFFFFFFF (otherwise saved start private19/20),
restores source masks and standing state, places the actor on ground, updates
its retained accumulator and powerup/reset dependencies. It preserves ammo,
lives, deaths and other fields not written by the original body.

Controller cleanup marks active and dormant actors carrying actor+164 bit2000
for deferred deletion. Then it rereads the main plane before each call and runs
plane4d2000 -> plane4d1fd0 -> actor4c8fc0(refresh1), twice. It renders4cb9b0,
presents through renderer+34, requests fade-in1000/500ms using the original
captured first-plane identity, resumes enabled music, then resets stage and
animation clock aliases and private+120. Timing reset performs two real clock
reads when application+30 is nonzero. The750ms primary+20 delay is enforced by
the original actor scheduler before fall-death callbacks, not by a host sleep.

## Dormant cleanup scanner

The owned Swift scanner composes complete4d51f0/4d5240 control flow with frozen
SpatialGridRuntime iterators4f4860/4f49c0. It visits layers grid+4,+8,+c, calls the
cdecl callback with member+18 actor, and returns a wrapping32-bit count. Null
callback returns0 without looking up the grid. The required46e340 callback uses
the frozen cleanup actor body. Its17-word iterator models original stack bytes;
borrowed tokens descend from7fff0000 by0x100 per nested scanner call and are
reserved only during that call, does not allocate in
the physical heap and faults if that token collides with host storage. Generic
callbacks remain exact-address services. Grid membership is preserved by the
original remove=0 iterator.

## Checks

Private smoke: `work/native-respawn-agent/check-native-respawn.sh`.
Private original fixture: `work/native-respawn-agent/capture-grid.py`, using the
hash-pinned original v1.0 and Tests/original_v10.py.64 complete scanner calls
include a null callback, null actor member, and756 ordered whole32KiB heap snapshots; original
registration and iterator bodies execute without replacing their internals.
Native heap buffers and every callback-entry snapshot are compared byte-for-byte.
The fixture covers12 populated actors distributed over three layers and includes
seeded unrelated actor/layer bytes. Additional smoke coverage checks source
constructors, command gates,24 lives/configuration/infinite-life election cases,
and state5 deletion versus state12 retained-history under explicit original
application+a0 placeholder mode. Physical UI state lifecycle is labeled an adapter.

The actual native Level1 lethal hit and source scheduler750ms delay run against
real decoded Level1 data and reach exactly one803a with lives3→2/deaths1. The
existing player explicitly reports41ebd0 (death notice),4b7aa0 (audio stop) and
41f990(0,0) (powerup reset) as unavailable boundaries; these are asserted as an
exact visible set, not silently treated as recovered. The full native
queued803a controller/state23 trace now passes: health100 and original grounded
start689/4730; both exact plane/frame(refresh1) passes; one render/presentation;
private72=20000; lives2/deaths1/ammo/world preserved; then WALK continuation.
A tagged actual dormant Rat is marked for deferred removal. Clock delta and
paced-frame start clear while seeded countdown123/reload321 and accumulated
game time remain intact. Source application/owner constructors initialize the
controller fixture; explicit bindings supply an opaque palette-presence token,
a fade-request transport with no simulated sleep, the existing native surface
renderer/presenter and no music controller. Source sound lookups use the real
audio/resource resolver. The fixture publishes the logical clock alias into
both scene.currentClockSnapshot and raw541328 storage; stage/animation aliases
use the exact live scene globals. No full-game behavior or
retail startup equivalence is claimed by these bounded checks.

The same complete private smoke passed AddressSanitizer (Swift and all linked
native C++ modules): `CLAW_NATIVE_ASAN=1 work/native-respawn-agent/check-native-respawn.sh`.
Build products stay in separate private build/build-asan directories. The smoke
regenerates its hash-pinned original fixture before compilation. If the scene
retains this component, use weak captures in its hooks to avoid a Swift ownership
cycle. Production8006 ordinary GUI constructors/init and physical fades remain
explicit source-address/platform dependencies; the placeholder-profile fixture
does not establish GUI/game-over-screen equivalence.
