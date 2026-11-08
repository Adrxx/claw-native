# Original default Booty story sequence

`BootyStoryRuntime.h/.cpp` recovers the default story child and its three registered actors from the pinned original v1.0 executable (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`). The tests also pin the original disc REZ (`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`) and use canonical `Original/retail-assets/STATES/BOOTY` assets. This is bounded source/controller/actor evidence, separate from native menu presentation, physical audio, full application boot, or game completion.

## Entries and actual identities

The story child is **364 bytes**, vtable **50b544**. The source constructor/election is already owned by frozen BootyProgression: its first807c transition creates this child, constructs the two CString members, and invokes initializer40b860. The initializer's third argument and enter40bca0's argument are the **previous mode**, not a retired child pointer.

| Owned original entry | ABI / role |
| --- | --- |
|40b860|thiscall(application, level, previousMode), RET12; whole story initialization and deferred actor creation|
|40bca0|thiscall(previousMode), RET4; background setup and map/amulet music election|
|40bd60|no args; whole timer/audio/input → scene frame → renderer → actor draw list → presentation order|
|40bfd0|no args; wait/voice/latch/countdown gates|
|40bf80,40be60,40bed0|no args; setup, restore, reentry/fade control|
|40bf30|thiscall(key,unused), RET8; escape/space/enter one-shot807c request|
|40bd50|thiscall(nextMode), RET4; returns1|
|40bc80,40b620|no args; cleanup/destructor with source CString/vtable order|
|40b600|thiscall(deleteBits), RET4; deleting destructor, meaningful EAX=receiver|
|40c150|cdecl(actor); registered **MapPieceLogic**, name5224b8, flags0|
|40d1a0|cdecl(actor); registered **AmuletGemLogic**, name5224a8, flags0|
|40c4f0|cdecl(actor); registered **MapProgressLogic**, name522494, flags0|
|4ca9e0,4caa90,4caa20|source surface copy/reset/conditional initialize helpers|
|4ca900|thiscall(file,which), RET8; select holder+18 only for which2, otherwise+14, then virtual+30(file)|
|4d4190|thiscall(file), RET4; image type/acquire/format-dispatch/release wrapper|
|4b95b0|thiscall(graphics,data,kind,size,variant), RET20; whole bounded bitmap format election|

The three story actors have **no specialized private allocation, constructor, class vtable, or named enemy state table**. They use original **436-byte generic actor + 372-byte primary logic** and manually selected numeric states. Their callbacks are deferred because the creator receives flags0. The named registration is verified in original401000; registry storage/lookup remains an explicit transport.

Fourcc election in4d4190 is integer comparison: BMP424d50→1, PCX504358→2, PID504944→4, RID524944→3. These are not string pointer identities.4b95b0 supports only kinds1/2/4; RID3 returns0 after the wrapper acquired the bytes, then the wrapper still releases the resource. BMP4bdda0 has **three** arguments, PCX4bebc0 three, PID4bf680 four; Ghidra omitted BMP's byte-length argument. Bitmap size0 returns0 before invoking a codec. These wrapper bodies execute unchanged in the oracle; physical codec bodies remain named services.

## Raw host and composition

`claw_booty_story_entry(function,receiver,args,count,context,dependency,user,result)` separates support/completion from meaningful original EAX. Unknown entries return0. Require fault0; faults1/2/3 represent missing span/service, a matched unchecked-prefix/safety rejection, and ABI/traversal failure. Incidental EAX of void methods is not a gameplay result. Actor callbacks require receiver0 and one cdecl actor argument.

The host supplies raw32-bit tokens through frozen SceneActorHost. Calls preserve function, receiver, argument count, up to40 words, optional name, and synchronous local buffers. `localMask` bits0.. mark normalized local arguments; bit8 marks a normalized local receiver. Local buffers remain valid only during the dependency call. MFC CString storage/copy/reference ownership is a declared transport, not a recovered portable CString implementation.

Optional composition:

- `composeProgression` requires the borrowed progression context; frozen base48f0d0 also composes when progression.base is supplied.
- `composeCreation` executes frozen4c8da0/generic construction/list insertion. Source name-map adapter returns resolved tokens for the frozen one-argument ABI; the oracle normalizes this to original BOOL+out-pointer lookup.
- `composeImages` executes frozen indexed ActorResourceBindings and PickupPoints getter; no image-ID fallback is invented.
- `composeAnimation` executes frozen ActorAnimationRuntime/AnimationEngine over actual sequence/record tokens.
- `composeFrame` executes frozen SceneActorRuntime4c8fc0 and the root-owned frozen PlaneRenderer actor-list export4c91d0.
- Borrowed `display` composes frozen SceneDisplayRuntime; borrowed `results` composes shared48ffa0/48f470/40df60 and4c89e0/4c89f0. Shared bodies remain owned by those modules. The rich adapter routes elected Story-owned surface/file wrappers back into this module.

Raw clocks and aliases: application/controller5371fc, stage delta53720c, animation now5430c8/delta5430c4, array guard5430d0/deletion5430f0/reorder5430d8, audio enable532c0c/overall volume532c10, map election5349a0, path index5349a4, loop CString53499c, countdown523b50, mouse537200. Frame composition imports/publishes the complete frozen array/clock view at synchronous callbacks; stage and animation clocks remain distinct. The application profile has application+30 scene, +34 resources; story+4 application,+8 resources,+c scene,+14 level,+18 previousMode. Scene+4 holder,+8 actors,+c renderer,+10 images,+14 logic registry,+18 palettes,+1c graphics,+28 sound,+2c ANI.

The 128-word compatibility shadow used by older frozen modules commits **only109 real actor words**. Its interior range stops at436 bytes so an adjacent372-byte logic allocation never aliases the shadow. Animation interiors are resolved before obtaining an updater pointer. New actor/logic allocations require no invented trailing storage. Frame exceptions clear the borrowed local frame pointer before unwinding. Constructor seeds and untouched words stay observable.

## Source state and resource recipe

| Completed level | Source family / retained actor count |
| --- | --- |
|1|map piece /1|
|2,4,6,8,10,12|amulet /1 each|
|3,5,7,9,11|map piece + actual path actors /10,13,8,31,5|
|13|blue GEMB13 → dynamically created red GEMR13 /2|
|14|GEM14 animation, logic level17 and AMMAKE sound election /1|

Initializer loads STATES_BOOTY and CLAW, obtains IMAGES/ANIS, and passes BOOTY/underscore prefixes to original resource services. Odd levels≤11 elect map; all other valid levels elect amulet. Initial delay is5000ms, later odd-map piece delay2000 with its trigger disabled until the path releases it. Level13 red child delay2000. Actual9 GEM ANI files,362 MAPPIECE PID files, and **Level14 FRAME038.PCX** form the image/ANI transport fixture. The PCX is included at source-derived ID38, with declared physical surface geometry416×466/zero offsets; physical PCX decoding is not claimed. The source naming rule comes from frozen ImageRegistry, using the first decimal substring, not arbitrary default IDs. The fixture stores payload hashes and all14 selected background PCX paths.

Map piece states0→5→2330→2331→232f use the exact source start/destination positions, floating slope,53-bit intermediate rounding, signed FTOL, wrapping coordinates, and independent stage timer. Map progress uses all150 source coordinate pairs and sentinelFFFFFFFF values. Its actual delays400/300ms, path index updates, child creation, and linked primary+64 release are preserved. The Level11 path has three coordinate pairs before the sentinel; no path length is inferred from level number.

Amulet state0 hides and positions; state5 waits its timer, advances the actual ANI, elects GEM/AMMAKE sound, and requires source stop/code and sound-busy gates before completing. Level13's second actor is actually constructed, bound to red resources, deferred, animated, and observed completing.

40bfd0 waits for GEM/AMMAKE/IMPACT3, elects the per-level source voice once, then honors the amulet-loop busy gate.40bd60 or escape/space/enter sets story+158 before queuing PostMessage(window,111,807c,0), suppressing repeated requests. No level increment is substituted. The later807c handler belongs to frozen BootyProgression; final application8021/8036/8075 transitions are separate source recovery.

## Evidence and boundaries

The final paired suite compares complete512KiB raw heap plus192KiB writable image aliases, every dependency receiver/argument/name and full snapshot hash, meaningful EAX, exact source SP, generated actor/controller cases, resource failures, repeated input, distinct clocks, all14 joined histories, and five actual allocator-failure prefixes. The final normal suite passes **13,641 whole original calls /102,613 ordered full snapshots /3,025 total instrumented addresses in the root combined rerun (the earlier worker matrix recorded3,018 before the two additional dynamic-allocation prefixes)**, plus five unsafe prefixes. Full counts/address inventory are in `work/booty-story-agent/verification.json`; sanitizer corpus/check commands are in the private check script. The sanitizer passes **140 exact-size replays /2,385 full snapshots**; C11, normalized Swift import/typecheck, strict C++ and Python checks also pass. The exact-size sanitizer replay keeps physical free storage available as an explicitly inert CRT transport, matching the oracle; it does not establish native allocator reuse behavior.

The normal joined profile uses real frozen generic creation, source scene dispatch/list bodies, actual image/ANI records, source timers, one807c request per level, and original cleanup through real generic actor/logic destruction and RemoveAll. Audio busy results are a declared controlled service, not rendered WAV acceptance. Separate controller matrices exercise held busy and expiry gates. Stage100/ANI33 histories verify clock independence.

Explicit remaining services include resource traversal/registry dictionaries4b7f20/4b7cd0/4b7dc0/4cff40/4ce0d0/4d0120, CString operations, CRT physical allocation/free, audio playback/busy queries, palette factory/fade/display, physical bitmap decoding4bdda0/4bebc0/4bf680, GameImage4d2890 physical drawing, buffer copy/presentation, mouse sampling, cursor and Windows PostMessage. The shared-setup fixture executes real48ffa0/48f470 plus source holder/file/format wrappers while palette construction and buffer storage are declared transports. The ordinary frame fixture composes real SceneDisplay queue drain. Their profile boundaries are measured separately; neither is described as a complete retail boot or rendered story acceptance.

Root reproduction: `work/test-env/bin/python Tests/compare_booty_story_runtime.py` passes13,641 calls/102,613 snapshots and allfive failure prefixes. `work/test-env/bin/python Tests/check_booty_runtime_asan.py story` regenerates the140 source-matched replay corpus and checks exact object spans under ASAN/UBSAN. Use `--reuse-corpus` only after generating a matching corpus in this checkout. The replay source and generator are included in Tests; corpus/original executable/assets stay ignored. Native Mac and generic simulator compilation includes this controller; live story progression/render acceptance remains pending.
