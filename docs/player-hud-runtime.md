# Original player HUD frames

`PlayerHUDRuntime` recovers the five previously external children of the original
MultiStats HUD. It composes frozen `CheckpointTimerRuntime` positioning, digit
creation, collection dispatch/draw and teardown; it does not duplicate the
optional CheckpointTimer491b30 or StatusNumberDigit4919f0.

There was an important caller-identity correction: literal5223cc is
**ClawDialogSound48c630**, not a HUD. In source46aeb0, the actual HUD creator is
`4c8f60(container,0,0,0,9999,literal52297c,200000)` for **MultiStats491ed0**,
immediately before the dialog actors. MultiStats creates the five children in
the following source order. Only TimerFrame has immediate-callback flag200000.

| Registration | Callback/size | Literal/ordinal/flags | Child z |
| --- | --- | --- | --- |
| ScoreFrame |4908b0 /841 bytes |5229d8 /95 /0 |9998 |
| WeaponFrame |490f80 /798 bytes |5229cc /96 /0 |9999 |
| HealthFrame |490c50 /814 bytes |5229c0 /97 /0 |9999 |
| LivesFrame |4912a0 /667 bytes |5229b4 /98 /0 |9999 |
| TimerFrame |491540 /869 bytes |5229a8 /99 /0 |9999 |

The executable is original v1.0 SHA256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The independent project, clean boundary logs and source decompilation are
`work/player-hud-agent/ghidra-project`, `frames.log` and `frames.c`. An initial
headless invocation with an incorrect project name failed before execution;
the subsequent verified `ClawOriginal` invocation recovered all five complete
entries without script errors. Registration identities are from frozen
LogicRegistry, not inferred from filenames or a source port.

## Source object recipe and shared identities

Each frame is an ordinary1b4-byte actor with a174-byte primary logic. Its
primary+18 owns a0x60-byte/24-word HUD object, main vtable50b5c4 and embedded
number-group vtable50b5cc at+28. ScoreFrame and TimerFrame temporarily install
50b014, call the frozen490c40 embedded-group constructor, then install50b5c4.
The other three constructors store the two final vtables directly. Untouched
allocator words remain seeded; the source is not a blanket-zero constructor.
WeaponFrame and HealthFrame cache the startup player's private token into
primary+168. HealthFrame additionally owns countdown primary+130.

The source startup profile is the existing frozen manager4254a0, which sets
manager68=2, manager6c=0 and manager9c=0. The module takes those raw manager
fields and the source screen bounds; it does not invent window-derived
anchors. MultiStats actor identity is shared53c9fc, manager5371fc and live
player537e88. The additional four words are initial score534cc4, initial
health534cc8, player-powerup remaining534ea8 and audioEnabled532c0c.
Powerup remaining shares frozen PlayerPowerupRuntime's storage and is distinct
from CheckpointTimer remaining53c9f8. The inherited field named
`audioPosition` represents overall volume532c10.

HUD bind fields are horizontal anchor4/offset8, vertical anchorc/offset10,
cached manager mode14, maximum mode18, draw status1c/20 and live actor24.
Number groups begin at28: cached value2c, count30 and child tokens34 onward.
All five use maximum mode99 and vertical anchor4 (top). The table below gives
exact startup offsets after reading the current leaf image's half-width18 and
x offset20. Coordinates use wrapping32-bit arithmetic.

| Frame | Horizontal/x offset | y offset | Initial digits/value/step | Digit x/y offsets |
| --- | --- | --- | --- | --- |
| Score |left1 /halfWidth-offsetX |15 |8 /initialScore /11 |36 /0 |
| Weapon |right2 /1-offsetX-halfWidth |46 |2 /99 /8 |-42 /0 |
| Health |right2 /3-offsetX-halfWidth |15 |3 /initialHealth /11 |-52 /-1 |
| Lives |right2 /3-offsetX-halfWidth |72 |1 /9 /8 |-32 /1 |
| Powerup timer |left1 /halfWidth-offsetX |48 |3 /0 /11 |36 /1 |

Source digit creation belongs to MultiStats' actual child list at parent+1b4,
not to an invented SwiftUI counter. Each digit gets another0x60-byte HUD and
z=frame.z+1. Frozen HUD/digit/collection destructors preserve list order and
the repeated generic actor/primary/animation/base cleanup. HUD destruction
changes both vtables to50b014 and frees when the deleting flag requires it;
digit actors remain collection-owned until collection teardown. The source
collection teardown does not clear the retained53c9fc alias.

## Complete frame behavior

All frames use state0 startup and state5 update; other states are inert EAX1,
except LivesFrame's source mode4 startup hides actor40 bit1 and enters11.
Weapon/Health startup returns EAX0 if the live player or its private pointer is
missing. There is no new ability duration, actor subclass or private allocator.

* **ScoreFrame** binds TREASURECHEST/CHEST, advances ANI before loading its HUD,
  refreshes anchors, and displays current player actor+f8 when it changes.
  Startup threshold actor+fc is `(signed(initialScore)/1000000+1)*1000000`,
  wrapping32-bit stores. When cached score reaches that signed threshold, the
  source increments captured player private+7c once if signed lives<10, then
  advances the threshold by1000000 even when the life cap prevents an award.
  Only one threshold is processed per callback. Its sound lookup/play is gated
  by sound registry+30, resolved GAME_EXTRALIFE, and audioEnabled; life addition
  proceeds independently of audio success. This is gameplay behavior.
* **WeaponFrame** uses cached private+168. A changed private+30 selector1/2/3
  binds PISTOL/MAGIC/DYNAMITE image and ANI; displayed ammo comes from private
  +70/+74/+78. For other selectors, the original fallback displayed value is
  the actor token itself; no replacement weapon semantics are invented.
  Anchor refresh and digit changes occur before its final ANI update.
* **HealthFrame** displays current live actor+10c, then saturating-subtracts
  animation delta5430c4 from unsigned primary+130. At zero it stores
  `300-2*health` with32-bit wrapping and advances the heart image ID. A null or
  out-of-range next image resets to the source minimum frame. It does not use
  a hand-chosen heartbeat rate or an ANI for this heart cycle. If the player
  disappears exactly when the heartbeat resets, the original dereferences the
  null player; this is a measured unsafe prefix, not a normal null-player mode.
* **LivesFrame** advances ANI first, then displays signed-clamped
  `max(0,wrapping(lives-1))` from the current player's private+7c. The subtraction
  wraps before the signed clamp, including the INT_MIN boundary. It rereads the
  current player/private identity, unlike WeaponFrame's cached private token.
* **TimerFrame** binds STOPWATCH/CYCLE100, initially hides actor40 bit1 and its
  three digits. Nonzero player-powerup remaining clears their hide flags,
  advances ANI and displays unsigned remaining/1000 (floor). Zero remaining
  hides them on the transition; the conditional4bc110 body is composed from
  frozen PlayerPowerupRuntime and is exactly a single RET. No music-reset
  effect is invented for that call. This frame does not decrement the timer.

Position refresh checks manager68/6c and signed maximum mode. Left/right/top/
bottom anchors use the live source bounds; center differences wrap then divide
toward zero. Mode0 executes source scene+c renderer virtual+28 with x,y,image.
It then ORs the **live** HUD actor's40 with1 and sets draw status20=0/1c=1.
The WeaponFrame contains that draw sequence inline; the other frames invoke
frozen490c00. Service mutation of the HUD's live actor pointer is measured.

All numeric output uses source `%010i` (literal52c6f8), selecting the rightmost
digit characters. Score/Health invoke frozen actor setter4209d0; Weapon/Lives
perform their actual inline root64/68 range/table14 reads; Timer uses frozen
getter40f680. Each touched digit primary+68 becomesffffffff. Signed negative
values, overflow boundaries, sparse/null frames and unchanged cached values
retain the original behavior.

## Resource inventory

The hash-pinned original disc REZ is
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
The retained fixtures use84 actual PID files in these10 image groups and all
six elected ANI files. IDs use frozen ImageRegistry's first numeric substring
rule; the inventory's resource transport, REZ enumeration and geometry setup
are explicit fixtures rather than newly claimed whole resource loading.

| Exact image registry name | Source ID interval /PID count |
| --- | --- |
|GAME_INTERFACE_TREASURECHEST |1..12 /12 |
|GAME_INTERFACE_SCORENUMBERS |0..9 /10 |
|GAME_INTERFACE_WEAPONS_PISTOL |1..6 /6 |
|GAME_INTERFACE_WEAPONS_MAGIC |1..4 /4 |
|GAME_INTERFACE_WEAPONS_DYNAMITE |1..4 /4 |
|GAME_INTERFACE_SMALLNUMBERS |0..10 /11 |
|GAME_INTERFACE_HEALTHHEART |1..3 /3 |
|GAME_INTERFACE_HEALTHNUMBERS |0..9 /10 |
|GAME_INTERFACE_LIVESHEAD |1..8 /8 |
|GAME_INTERFACE_STOPWATCH |1..16 /16 |

ANI names and record counts are GAME_INTERFACE_CHEST15,
GAME_INTERFACE_PISTOL7, GAME_INTERFACE_MAGIC6, GAME_INTERFACE_DYNAMITE3,
GAME_INTERFACE_LIVES26 and GAME_CYCLE1001. Their exact files are under
GAME/ANIS/INTERFACE, except GAME/ANIS/CYCLE100.ANI. These actual files contain
no record sound-event names. Full PID paths/IDs/geometries and ANI names/counts
are saved in `work/player-hud-agent/verification.json`.

## C11 API and host boundaries

`claw_player_hud_entry(function,receiver,args,count,context,dependency,user,out)`
accepts the five complete cdecl callbacks with `(actorToken)`. Completion and
meaningful original EAX are separate. The context borrows a frozen
CheckpointTimerContext and an additional four-word global view. It preserves
shared configuration flags around composed calls. `composeControllers=1`
routes the actual frozen HUD/number/collection helpers; `composeImages=1` and
`composeAnimation=1` route source lookup/field effects through frozen
ActorResourceBindings, PickupPoints, ActorWrapper and ActorAnimation. Formatting
can execute the fixed signed C format or expose an exact callback-scoped output
buffer, local pointer mask1, format token and value.

The frozen CheckpointTimer implementation's internal image labels cover its
TIME/SCORENUMBERS family. This wrapper intentionally routes its image/ANI
service calls back through the broader recovered HUD names rather than editing
that frozen module or passing unknown labels to its image binder. Existing
collection callbacks can route these five addresses into this API, then retain
their original source call order, child lists, generic drawing and destruction.

Physical renderer/blit/pixels/presentation, audio pool/play, dictionary name→
resource identity and allocator implementation are exact explicit services.
Raw tokens remain authoritative. Dictionary4f6286 uses the established frozen
resolved-output-token ABI; its callback-scoped stack output pointer is
normalized, and the original dictionary bool is not substituted for the token.
The dependency receives function, receiver, all up to8 arguments, optional
literal name and optional local format buffer. At each boundary the host must
publish changes to borrowed globals before returning; raw heap aliases remain
live. No full WinMain/OS message loop, DirectDraw raster or physical sound
device equivalence is claimed.

Invalid raw spans or missing services diagnose fault1. Propagated unsafe
allocator/profile diagnostics use the shared module's fault categories;
unsupported arguments or native formatting/count safeguards use fault3.
These guards are native safety extensions. The source itself faults on HUD
allocation null at49077a, and on a lost heartbeat-reset player at490e10. Both
prefixes are measured with a valid original FS/TIB/GDT profile and an unmapped
null page, avoiding an artificial SEH-prologue fault.

## Verification and freeze

Run `work/test-env/bin/python Tests/compare_player_hud_runtime.py`.
Final result: **1,952 complete original calls**, **4,765 normal ordered full
snapshots**, **3,138 executed original addresses** and **1,500 original formatter
executions**. Six separate unsafe original prefixes add13 measured events.
Every comparison covers524,288 raw heap bytes plus196,608 global bytes,
preserving actor/primary/HUD/digit/resource/list/allocator seeds, aliases and
ordered calls. Snapshots compare whole-buffer SHA256 plus exact scalar call
arguments and original EAX for meaningful-return functions; source void EAX is
not claimed.

Coverage includes25 retained real-resource frame histories (five source status
modes per frame); five whole4c8f60→MultiStats→all five frame bodies→digit
dispatch/draw→wholecollection destruction histories; score thresholds/life caps,
signed wrapping, health heartbeats, all weapon selectors/ammo, mode/viewport
anchors, renderer live-pointer mutation, missing resource/private/HUD gates,
null allocation prefixes, and live-player versus cached-private alias changes.

Strict C11 header, C++17 `-Wall -Wextra -Werror`, Python compilation and a private
Swift C-import typecheck pass. `zsh work/player-hud-agent/run-sanitizers.sh`
passes ASAN/UBSAN on **206 original-matched complete corpus replays** and
**988 ordered full-buffer service snapshots**, including a complete collection
creator/update/draw/destructor history. The private compressed replay corpus
contains original executable/image bytes and is not a distributable source
artifact. No shared Root files, project, device or UI tests were modified or
driven by this task.
