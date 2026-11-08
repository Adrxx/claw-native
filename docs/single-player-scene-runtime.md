# Original single-player construction and startup

`Sources/SinglePlayerSceneRuntime.h/.cpp` recovers original constructor and finite startup control flow, using SHA256-pinned original v1.0 `CLAW.EXE` (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`). Original instruction boundaries, not a reference source port, define the implementation. It does not implement all WinMain, settings, renderer, sound, REZ or operating-system bodies.

## Actual sizes and constructors

| Object/entry | Original footprint and effect |
|---|---|
| Application `4254a0` | Allocation at `423466` is **0x134 bytes /77 words**. Complete constructor composes timer constructor, shared-empty CString cells and history-array initialization, sets vtable `50bee4` and the actual scattered defaults. Untouched words remain seeded. |
| Base timer `4b8240` | Full base fields and vtable `50bf04`, then frozen GameTiming initializes the original five-word manager timing view and five global clock words using two clock reads. `manager+28` minimum-frame duration and clock countdown/reload remain untouched. |
| Single-player owner | Allocation at `428d5d` is **0x778 bytes /478 words**, not474. Original inlined span `428d81..428dce` calls base `40b5c0`, constructs CString+250, sets vtable `50c264`, first-start latch+154=1 and clears+258/+25c/+764/+768/+76c/+770/+774. |
| Base state `40b5c0` | Exact 56-byte original body. Clears its sparse fields and only the low byte at+4c; it does not zero the whole owner. |
| Scene `4ce960` | Allocation at `425da1` is **0x3c bytes /15 words**. Constructor vtable `513ab8`, thirteen zeroed pointer/flag words, animation now/delta0. **Scene+30 is untouched** until initialization. |
| Base scene child `45fde0` | Exact parent/type/flags linkage and base vtable `50e924`; unrelated words preserved. |
| World `4cace0` | Delegates to the disjoint `WorldFileRuntime` implementation:0xe0/56 words, exact three embedded CArray constructors and world defaults. No duplicate constructor body here. |
| Collections `4f5620`, `4f6118`, `4f5cbd` | Exact seven-word constructors. List vtable5107bc, map vtables5105c4/510054, map bucket count17, original cleared links/count/free blocks, and supplied grow-block value. |
| Initialization probes | Original `4bd250` and `4cdf20` literally return1. `4cfa60` zeros the25-word DirectDrawFX structure at543108, then sets word0=100. These execute directly, including actual scene virtual initialization calls. |

Application construction includes the exact five-word history-array constructor `4f54ea` effects (vtable51079c and four zeros), and shared-empty CString constructor `4f6439/4f6433` effects. The shared data token comes from the live/static original cell52e1cc; the source image contains52e1c4. Constructor parity never assumes freshly allocated memory is zero.

## Scene initializer `4cea10`

The complete original body accepts `(HWND,width,height,colorDepth,flags)`, sets scene+30/+34, then allocates and constructs the following objects in this exact order:

| Scene offset | Bytes | Original derived vtable | Role observed in callers |
|---|---:|---|---|
| +4 |28|513c68|Surface/controller |
| +8 |44|513c20|Actor container with actual embedded list |
| +c |44|513be8|Renderer with actual embedded list |
| +10 |44|513b88|Image registry/controller |
| +14 |44|513b60|Logic registry/controller |
| +18 |104|513b28|Palette registry/controller with three maps |
| +24 |224|513938|World |
| +28 |52|513b00|Sound registry/controller |
| +2c |44|513ad8|Animation registry/controller |
| +1c |2180|Explicit `4bc120` constructor service|Additional graphic/resource object |
| +20 |128|Explicit `4b4710` constructor service|Audio manager |

Allocations retain actual `4f63ec(bytes)` service boundaries and their ordering. Object/list/map/world constructors execute here or through frozen modules; no fabricated standalone renderer/scene layout is substituted. The physical constructors `4bc120` and `4b4710` remain explicit.

The initializer calls virtual+18 on actors, renderer, images, logic registry, palettes and animations in that order. The actual default targets are4bd250,4cfa60 and4cdf20, recovered above. It then calls world+34 `(width,height)` through frozen SpatialGridRuntime4cb040, surface+24 `(width,height,depth,flags)`, `4b47e0(audio,HWND,1)` and `4ca280(sound,1)`. Failure records the first error1001..1010 atscene+38 without replacing an existing error. Failed audio is deleted through its actual returned vtable slot0; flags8 requires successful audio, flags4 deletes/disables a successfully initialized audio object. No general rollback/destructor is invented.

Null allocation of required controllers leads the original to unchecked pointer reads later. Native fault1 reports missing spans safely; this is an extension, not proof that the original returns safely. Separate witnesses stop immediately before the observed original null dereference because the Unicorn fixture maps a low page for FS exception-chain instrumentation.

## Single-player entry and level/reinitialization

`48f0d0(owner,manager,level,parameter)` binds actual manager fields+30/+34/+44, clears precisely observed state fields, formats the original banner and LEVEL name, resolves the level resource and elects success. It preserves state+34 if resource lookup fails.

Whole `46a6d0` rejects null manager, checks the saved-path CString length, copies/decodes saved-path level through explicit MFC/file services and rejects nonpositive decoded levels. It performs the base initializer, cursor-hide polling, exact owner/reset-object fields, `42aa50` ten global clears, exact640x480 gate `42af50`, CLAW/GAME root-resource lookups, then complete `46aeb0(level,1)`. Successful initialization sets owner+15c to3600000 or180000 depending manager+9c. Failure preserves every write already performed.

Whole level routine `46aeb0` accepts two stack arguments and pops8; the second is unused even though Ghidra omits it. It resets the original globals/owner fields, requests CRT seed0x1b3cf, handles saved-level mismatch, then performs the complete finite ordered graph:

1. Level lookup, MAIN palette lookup/replacement, palette output into owner+360, surfaces/palette selection, loading display and cursor polling.
2. Existing level cleanup and original progress calls, graphic setup gate, TILES, then LEVEL/CLAW/GAME sound groups, image groups and animation groups with their exact prefix/separator literals and loading-flag writes.
3. World resource/file loading through actual world vtable+3c/+40, post-load4cdcb0, configuration/saved-level gate452b00 and progress75.
4. CaptainClaw creation **`(id1,x320,y350,z100,name522e80,flags40002)`**. It clears first-start latch+154 and calls415ce0/46c790/46d8e0 only on first startup; otherwise word534ca4 becomes0. It then immediately invokes the new player's actual primary callback as a cdecl actor argument.
5. CaptainClawScreenPosition creation, forced camera coordinatesFFFFFFFF, frozen detached-camera cancellation, MultiStats, ClawDialogSound, EnemyDialogSound and optional CheckpointTimer creations; loot-table initialization4719e0.
6. Screen-size-dependent surface operation, frozen input mapping/device reset, cursor polling, owner+158 reset and actual movie/settings gates.
7. Frozen spatial startup4d2030 then residency activation4d1fd0 on the reread main plane. Ordered music variant/resource loading and final loading/progress/sleep service.

There are no guessed player start coordinates in this graph. The creation coordinates precede the immediate player initializer, which applies the actual WWD/checkpoint/ground-placement logic through the frozen player module when the host routes that callback. The world loader should route actual `4cb5a0/4cb470` identities to `WorldFileRuntime`; REZ/file/decompression/resource providers remain necessary.

Source caller evidence at425e7f/425e86 establishes application viewport640x480, and425e9d/425ea0/425ea3 assigns world+64/+68=14 after scene initialization. The field meaning is not guessed here. The original application loader creates a0x38-byte message/config object and calls4222a0 with delays5000/2000, as previously recorded by GameFrameServices. **Application4254a0 construction alone leaves window/scene/REZ/config/audio bindings null**; the enclosing application-loader boundaries must establish them. `startup-evidence.json` distinguishes these source-derived stores from a whole retail boot replay.

The existing frozen PlayerDeathCommands respawn controller46be40 sets logic23 on the current player and immediately invokes its primary callback. This scene startup creates a new player and invokes its initial callback; it does not guess/set logic23 or replace the posted803a/8006 handling. Keep those command/death paths separate from full scene reinitialization.

## ABI, clocks and dependencies

C11 `claw_single_player_scene_entry` exposes the verified entries; `claw_single_player_scene_construct` exposes the observed inlined owner constructor span. Context composition flags default1 and do not initialize any graph/global values. Known constructor/probe paths compose automatically. World constructor uses `WorldFileRuntime` + frozen CArray; world viewport/grid startup use frozen SpatialGridRuntime; mapping/device reset and detached cancellation use frozen SceneCameraRuntime; complete timer construction uses frozen GameTiming.

`ClawSinglePlayerSceneGlobals` maps its21 words in order to:

```
538418 loot initialization;54316c image loading;537210 accumulated tick;
53c9c0 and5349dc observed reset words;537e88 player;534ca4 reset word;
52be14/52be18 forced camera coordinates;537204 input mapping;53ec44 build;
537268,537214,537218,53721c,537220,537228,537224,53722c,537230,537264 reset flags.
```

Do not infer semantic names for unclassified words. `camera` provides the frozen twelve-word camera/global view; scene constructor zeros its animation words, level startup composes actual input reset and detached cancellation. The host must synchronize shared animation/stage/player aliases with its frame/actor/image modules, including callback mutations. `host.lookup(543108,25)` must alias `GameImageRuntime.directDrawFX`; `host.lookup(541328,5)` must alias the frozen clock state. Read-only/static spans must provide52e1cc and actual vtable/CString nil-header metadata. `host.readClock` supplies physical millisecond samples for timer construction; samples are not invented by the module.

Rich calls preserve original receiver/argument count/arguments, up to8. Automatic stack pointers are token0 with mask bit i for argument i or bit8 for temporary receiver; synchronous buffers supply the actual data/output. Raw owner palette/banner destinations retain original tokens and expose their live buffers. COM palette-read explicitly receives its interface object on stack; cdecl actor callbacks use receiver0. Platform calls retain IAT-slot identity. For simpler calls `host.call` is a fallback; temporary buffers/more than4arguments require the rich callback. Safe diagnostic faults:1 missing span,2 missing service,3 invalid native argument shape; these are outside normal original-equivalence claims.

Explicit remaining boundaries include MFC CString copy/clear/destruction and saved-level decoding; formatting; CRT thread-local RNG seed; REZ lookup/group/palette/resource conversion; physical surface/palette/font/window/cursor/audio/music/movie/settings operations; level cleanup/progress/setup helpers46db30/46f040/46e100/46b7b0/46bb80/46e160; player-default/saved-state host composition415ce0/46c790/46d8e0; actor creation wrappers and actual registered gameplay callback. The native host can route already recovered original-address services into their frozen modules. The oracle records every adapted service with exact arguments and complete ordered snapshots; no service is silently ignored.

## Verification

Run `work/test-env/bin/python Tests/compare_single_player_scene.py`.

Final verification passes **1,814 whole original entry calls +245 inlined owner-constructor spans** (2,059 normal comparisons), **40,685 ordered complete snapshots**, and **8 separately classified null-allocation witnesses**, covering2,370 observed original addresses. There are594 directed startup cases,240 retained construct/reinitialization calls,60 joined application/scene calls and24 joined populated-grid graph calls. Every normal comparison covers the **entire1MiB heap plus63 global words** (21 startup,12 camera,25 DirectDrawFX,5 clock), ordered callback snapshots, meaningful returns, stack cleanup and FS-chain restoration. Untouched buffer seeds, saved path/nonpositive level gates, all resource/creation failure positions, first-start latch, extreme grow-block values, exact application/scene constructors, physical initialization failure services and retained reinitialization histories are covered.

Joined constructor→scene initialization→owner→level histories retain actual constructed list/map/world/controller words. Six populated startup profiles create real frozen grid layers over24576x6144, register nine dormant fixture actors and compare original startup activation/reinsertion bodies. Thus the spatial calls are not zero-main-plane fixtures. Actor gameplay bodies, physical graphics/audio/resource bodies and WWD loading in these joined profiles are explicitly declared fixtures; full asset/resource/lifecycle identity is not established by this module.

The constructor span check executes original instructions428d81..428dce and stops at the observed constructor boundary. It is explicitly **not** a whole428c40 transition or an original return/stack parity claim. Eight null-allocation witnesses separately compare complete state/event prefixes to the first unchecked original null read; native safe failure and original OS exception handling are not equated.
