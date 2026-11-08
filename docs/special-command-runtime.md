# Original Special warp and map-piece commands

Frozen additive controller recovery from Captain Claw v1.0 `CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The public interface is `Sources/SpecialCommandRuntime.h`; all original addresses and tokens are 32-bit identities. This module does not establish whole-game parity or implement a native map/Booty screen.

## Recovered entries

| Address | Body and calling convention |
| --- | --- |
|426e30|Thiscall application `(unused,command,unused)`, branches805c,800e,8023 only, RET12|
|46c630|SinglePlayer virtual+54, warp, zero arguments|
|46c900|SinglePlayer virtual+40, map-piece/end-level, zero arguments|
|42abf0|Manager clock/frame publication/player cooldown reset|
|48feb0 /48fda0|Fade-out/in admission and packet dispatch `(steps,duration,flag)`, RET12|
|42d420 /42d440|Music pause/resume admission|
|46b7b0 /46bbc0|End-level teardown / layout and rankings option publication|
|415d90|Cdecl player-private capture `(player)`|
|46c7b0|Owner level accounting `(player)`, RET4|
|428c40|Whole controller bounded to state10 `(10,level,retainPrevious,unused)`, RET16|
|40ac20 /40b120|Booty state resource/child initialization `(manager,level,previousMode)` / child enter `(previousMode)`|
|4ecc00 /4ec600|Five-word fade packet constructor / manager fader list removal `(fader)`|

Private analysis opens only `work/special-command-agent/ghidra-project`. The recovered files and logs are in that directory; address boundaries are verified by the hash-checking Ghidra script. Instruction comparisons resolved decompiler omissions: audio4208e0 is thiscall with four stack arguments; fader4ec9c0 receives three; settings4b5e50 receives two; palette4bb990 receives six.

## Warp publication and execution

The frozen PowerupObjectRuntime41ee60 warp branch publishes item+148/+14c into529fa0/a4 and posts805c when both are signed-positive. Source static529fa0/a4 are bothFFFFFFFF. The new command body preserves42a630's repeated current-owner mode probes: mode3 succeeds first, otherwise mode4 succeeds second, otherwise mode6 succeeds third. A rejected ready gate still yields recognized command return1.

46c630 requires signed-positive targets and a live537e88 player. It writes player+4c/+50, consumes both target words toFFFFFFFF, resolves GAME_WARP through the owner's current sound registry unless registry+30 disables lookup, and invokes4208e0(sound,volume,0,0,0). It runs fade-out `(80,1450,0)` and ignores its return; performs42abf0; runs two spatial refresh→visibility→actor virtual+24 `(refresh=1)` passes; then renders and presents using live owner/scene pointers. Fade-in receives `(80,1450,0)` and controls whether the final42abf0 and return1 happen. Failed fade-in preserves the already committed position and all preceding work.

There are no direct camera, physics, input or player-logic writes in the warp body. Camera following occurs through scene services. Native integration must compose those real services instead of forcing camera position or inventing a fixed update step.

42abf0 composes frozen GameTiming4b83d0: one clock read clears clock delta and pacedFrameStart, preserving countdown/reload. If manager+30 is nonzero, a second read sets animation-now and clears animation-delta. Stage-now/delta copy clock-now/delta. A live player's nonnull private pointer receives private+120=20000. Accumulated537210, player reset serial, input state and countdowns are not reset.

## Map-piece / end-level and retained Booty state

800e invokes current owner virtual+40 after the same readiness gate. A zero owner return sends synchronous `SendMessageA(HWND,111,8023,0)` via546d44. Source8023 requests428c40 `(5,1,0,0)` and reports429e10 `(8005,3f7)` on failure. State5 itself is an explicit frozen PlayerDeathCommands transition service, not duplicated here.

46c900 first tears down the level, sets537e88=0, conditionally calls46d620 `(0,0,3)` and file49bbc0 when owner+258==0, and sets owner+25c when level14 completes. Default4254a0 manager+9c=0 requests retained state10 with the live level argument. Nonzero9c follows the distinct source branch: owner+25c selects palette/clears/42b910/42abb0, otherwise source posts8075. No timer duration or option is forced.

The teardown captures78 words from player's private object into534c80..534db7 after copying player score+f8 and health+10c into private+44/+48 and clearing private+4. It records signed-valid levels1..14 once, with unsigned score differences/time totals and option+128 bit publication, then releases the source ordered services. Sound/ANI/world/container/UI teardown remain explicit recovered-body or unrecovered-address services; returning without their effects is not a complete native end-level lifecycle.

State10 transition retains the outgoing owner in the original CArray, preserving source allocation/growth/clear order, then allocates352 bytes (`0x160`,88 words), calls frozen40b5c0 base construction, installs vtable50c0c4 and stores+154=0,+158=0,+15c=10. It resets the clock, calls virtual initializer+4 with `(manager,level,previousMode)`, enters virtual+24, marks application-shell+244, resets431300/input+C and4b3ab0/mouse+20c, and resets the clock again. Allocation/init failures preserve preceding history mutations. Application+A0's separate154-byte base-only shortcut is recovered verbatim from the inlined source stores.

40ac20 accepts previousMode3 only, probes42bfd0, binds frozen48f0d0 base resources and42af50 viewport, publishes the source status-mode and resolves `STATES_BOOTY`, `CLAW`, `SOUNDS`, `BOOTY`, `_`. It unloads actors/sounds, binds Booty audio, repeats ShowCursor(0) until its signed result is negative, resets window input, and allocates the exact option-selected child:344 bytes/vtable50b43c when manager+130==0,388 bytes/vtable50b494 otherwise. Both source inlined constructors are recovered, including the latter CString+180 boundary and nine zero words. Their virtual initializers40b6a0/40d470 and enter callbacks40b720/40dca0 remain UI-family dependencies. Null child allocation reaches an original invalid-memory path after earlier writes, exposed as native diagnostic fault rather than success.

## Live aliases and required integration

Share managerToken5371fc, playerToken537e88, targets529fa0/a4 with PowerupObjectRuntime; audioVolume532c10; fadeBypass537238; inputMapping537204; mouse537200; tick537210; clock541328..338; stage537208/20c; animation5430c8/c4; capture534c80..db7; rankings525518 (source static default1;fadeBypass default0). Root scene/camera/actors/save contexts use the same aliases: publish/import around external callbacks so their changes remain visible. No separate copies may advance the clock independently.

Rich dependency calls use argumentCount up to8. Automatic stack-pointer arguments are normalized token0 with localMask bits. Fade factory4ec050 `(2,localPacket)` has mask2 and a live five-word packet `[3,back,front,outward,steps]`. Its returned fader must be registered in the actual manager CArray; source4ec600 removes the first matching pointer, shifts later pointers, decrements count, and invokes its actual deleting destructor. An absent match is untouched. Source fade factory4ec050/type2 allocation/init and fader4ec9c0 pixel/clock loop are **unrecovered source bodies**, not merely OS calls; packet/order checks do not establish their execution parity. They, timed palette4bb990 `(0,256,0,0,0,500)`, graphics/window/audio/file services and Booty child UI must be honestly identified until separately recovered/adapted. No visual approximation is supplied here.

40b5c0 and48f0d0/42af50 must route frozen SinglePlayerSceneRuntime bodies with valid scene/resource identities.46d620 must route frozen CheckpointLogicRuntime with the source save/config/player aliases;49bbc0 is physical file transport.431300/4b3ab0 are recovered input-reset services where available. Actor frames4c8fc0, grid4d2000/4d1fd0, destruction4c89e0, registry unload4ca300/4cdf40 and renderer4cb9b0 require their real module adapters. The module routes exact addresses and leaves these effects to the host.

## Evidence and limits

`work/test-env/bin/python Tests/compare_special_command_runtime.py` passes743 whole original calls,3848 ordered full snapshots,1550 distinct original instruction addresses. Each snapshot compares all512KiB of mutable fixture heap plus97 global words, not selected output fields; meaningful EAX and stack cleanup also match. Matrices cover signed target extrema, all fade gates/factory-null paths, audio gates, exact clock read counts/order and retained counters, option/level/save gates, both child allocation shapes, cursor-loop behavior, resource/init failures, history resizing/clearing, allocator failure prefixes, live receiver/global mutation and fader-list removal.

All eight actual Level1 GAME_WARP WWD profiles use the frozen WorldObject loader and the frozen PowerupObject selector, with32 original/native publication calls and four retained805c→consumed-command cycles each. The fixture explicitly elects contact by calling41ee60; it does not prove actor interaction election. Actual Level1 spatial and actor-frame bodies are addressed and ordered but remain service adapters in these comparisons. Retail WWD provenance hashes/coordinates and exact totals are saved in `work/special-command-agent/verification.json`.

Transport adapters model resource success/failure, base construction/binding, renderer/audio/window, teardown/save and Booty child services. Thus a passing command test establishes controller state/order under those explicit adapters, not complete native Booty rendering or physical fade/audio/save identity. Independent C11 header/strict C++ compilation and a200-clock-read native ASAN/UBSAN retained warp/fade-failure smoke pass. Parent owns shared host integration and device verification.
