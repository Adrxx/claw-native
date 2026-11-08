# Native scene integration

ClawNativeScene runs complete recovered singleplayer46ac30 over pinned token
storage. Its ordinary order composes actor/input/camera phases, plane/image draw,
native presentation, message timers, DD flush transport and final spatial
residency. Stage deltas19–99ms split into18ms passes plus remainder; other deltas
use the ordinary actor phase and its separate animation-clock read. Primary/
secondary/private buffers persist across callbacks, including player death's
750ms primary timer. Source list ordering and deferred reorder remain recovered.

The complete scheduler comparisons cover1,500 creators,1,500 full frames,
4,000 retained chains,1,000 normal/substep stages,500 direct insertions and failure
paths. Root original outer-frame comparisons cover496 calls/25,509 snapshots;
renderer394 calls/51,876 events; native integration verifies0/18/19/37/99/100ms,
source frame order, whole player/camera write-back and retained world state.
These finite tests do not prove complete gameplay identity.

The recovered WWD loader and source spatial layers now load1479 Level1 records:
12 Rats,26 Officers,16 Soldiers,458 pickups,594 scenery,31 platforms,120 pegs,
81 sound/dialog/ambient records,34 single crates,7 ordinary checkpoints plus2 super checkpoints,8 curse records,
58 powder kegs,22 stacked-crate parents and10 SpecialPowerup records. Shared whole-source CRT thread RNG and source
special-powerup startup/scanner awards now compose. Native assertions check warp
coordinates/commands, map audio/wait/command and extra-life award using declared
visitor/live-player flags/progressing-clock fixtures. Their command execution is
still pending. Native
RatBombs use the original scene creator and deferred actor/logic destruction.
Retained throw/flight fixtures use synthetic player placement. The three planes
use original constructors/loaders and owned tile/row buffers. Source input
polling/gates, plain camera creation/follow and source grid activation/reinsertion
are connected. CArray storage composes recovered bodies with native allocation.
The whole compressed-world native wrapper is now connected. Additional actor
hosts are attached. ASAN checks activate all42 humanoids through ordinary
frames and collect a real WWD treasure through the interaction scanner; synthetic
visits/idle-timer seeding are explicit. Shared source48ce40 NPC speech and Claw dialog scheduler now compose; actual
voice-pool durations come from the loaded audio metadata. All scenery/platform/peg
activation, input-only spawn-to-ladder, and source-elected elevator rider checks pass.

Source application4254a0 and singleplayer owner constructors now initialize the
native startup profile. Scene-owned803a commands run outside the player callback.
Original46be40 resets primary23, cleans active/dormant actors, runs two exact
plane/frame(refresh1) passes, renders/presents and publishes timing. Native ASAN
checks retain world/ammo/lives/deaths and walking continuation. Fade requests
are explicit transport adapters; original fade loops and game-over UI remain
pending. Source powerup setter/reset/countdown now compose for supported calls;
normal type3 death notification and the no-op audio reset also compose.
Points/Glitter, ordinary awards and loot compose over the live heap. Broader
particles beyond HitBurst/Splash, music and source fade loops remain separate work.

The pair-scanner synchronizes all represented actors before and after each
callback. Native player damage and Rat callbacks run; absent bodies produce
address diagnostics. Only recovered callbacks may be registered. Heap tokens
are32-bit identities with checked indexed interior spans. Generic/plain actor
allocations reserve explicit128-word snapshot padding beyond source sizes.
Logical freeing removes ownership immediately; physical storage is retained
until the outer native call returns for source cached post-free field reads.

PlaneRenderer and GameImage select draw order and mutate blink/draw fields once
inside source frame execution. SwiftUI redraw presents cached commands, so it
cannot repeat original blink preparation. A byte-checked faster indexed adapter
replaces the costly Swift scan while retaining frozen PIDBlitter output. Physical
DD surfaces/palette/color conversion and SwiftUI transport remain graphics
boundaries. CoreAudio PCM transport, event-loop timing, complete startup/resource
factories, other-level families and incomplete progression still prevent a whole-game identity claim.

## Latest source integrations - 2026-10-12

All66 actual nonambient trigger/dialog records and34 single crates activate
through ordinary source frames from synthetic placements. Crates bind their
actual CrateHit secondary controller. All34 additionally pass actual scanner
election from synthetic projectile inputs, damage/cooldown/break ANI/loot and
ordinary scheduler destruction. Player sword input acceptance is separate.
All8 curse records execute original470a20 mode3 rejection and ordinary
actor/common-logic destruction without multiplayer effects. All7 ordinary checkpoints elect contact through the actual interaction scanner,
publish owner+44/+48, add25000 to the source timer alias, and animate RISE/WAVE.
A lethal hit after checkpoint contact posts803a and the original ground query
respawns at9118/4109 with health100 over the retained world.

All15 actual ambient records elect source initialization. Their objects and
CPtrList nodes use the retained scene/audio heaps, whole original4025c0 updates
center coordinates, and original voice wrappers use existing buffers directly.
Focused ASAN checks cover refresh, timed fades, stop and402270 destruction;
source fader/list cleanup preserves original ownership. CoreAudio mixing,
physical clock and COM transports remain explicit. The whole original audio-manager constructor/startup/Stop/shutdown now compose.
The allocator, cooperative-level/device factory and CoreAudio output remain
native transports. Source shutdown destroys all170 loaded WAV pools, reloads
the raw manager head after every callee, then releases the actual device.
Focused ASAN verifies that order and repeated shutdown gate behavior.

Whole461a00/461c40/461a90/461bc0 now compose into the effects host. PlayerDamage
publishes its borrowed actor, restores the original fixed scene/style/source
arguments, and creates the real GAME_CLAWHIT burst. Focused ASAN checks cover
source following, actual ANI termination, ordinary scheduler teardown, distinct
GAME_ENEMYHIT images and invalid-source deletion. Level1 LEVEL_SPLASH images
remain missing; no replacement assets are supplied.

The source breakable host imports actual260/262-word keg/crate allocations into
portable264-word snapshots without copying padding back into source spans. It
composes whole generic constructor/FSM/state bodies, actual vtable words and
resource getter/bounds wrappers. All22 stack parents create45 crates through the
real creator and link their private400/404 neighbors, then source flags elect
scheduler deletion of their19-word parent allocation. Child private graphs remain
owned by the source scene. The native ASAN focused checks cover all58 kegs, all
22 stack parents/45 children and a controlled source-elected lift/carry/charge/
throw history. Synthetic camera/player placement and defender mask0 are fixture
inputs. Original raw clocks/deadlines drive the recovered camera shake.

## Native saves and source status messages

All1479 Level1 records are instantiated. Both super checkpoints elect their actual
4231a0 attack callback through the ordinary scanner, update the full44-word source
cache with calendar data, write the original encrypted save and reset source clocks.
Native FileHandle transports perform actual disk reads/writes; all45 checkpoint slots
round-trip and unchanged original x86 reads the native9828-byte file byte-identically.
Save boot precedes the later level RNG seed. Missing/existing saves produce the same
checked post-load random stream; full retail pregame ordering remains unproven.

The source422370 queue,4226b0 text assembler and original frame timer/dequeue now
compose. Both saves display the original message and remove it after the source
5000ms timer. Native GDI/font/Canvas adapters present cached text commands; Arial
raster/layout is not pixel-parity evidence. Synthetic visits/live flags/contact
profiles are declared. Optional timed mode is not forced. Full selected-save player
restoration and broader startup remain pending. The original MultiStats HUD now
composes five frames and17 digits, including source life thresholds and timer
visibility. Source private writes survive scanner transport. See native-hud-host.md. See native-save-host.md.

## Native ranged launch

Standing Pistol/Magic/Dynamite now compose source launch, named creation, exact raw
controllers/ANI, collision/effects and whole scheduler cleanup. Magic owns an actual
19-word source Flare, with parent placement before post-update motion. Focused native
ASAN histories use actual spawn/input and a16ms clock fixture. Duck/elemental helpers,
source light palette and physical raster remain pending. See native-player-projectile-host.md.
