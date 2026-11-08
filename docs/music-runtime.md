# Original XMIDI music manager and resource runtime

`MusicRuntime.h/.cpp` recovers26 bounded original v1.0 manager/resource bodies needed by memory-based level music and the frozen SpecialCommand pause/resume wrappers. Backend synthesis, device output and library-managed sequence timing remain explicit transport. The code does not invent a MIDI parser, melody, duration timer or music fade.

The oracle hashguards `Original/claw10/CLAW.EXE` SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private `work/music-agent/roots.c` and `work/v10-disassembly.txt` establish boundaries and true ABI. The private PE import inventory `work/music-agent/imports.json` proves that `546e68..546e9c` are `mss32.dll` decorated AIL imports, including their stdcall argument byte counts. Ghidra's guessed fastcall and virtual argument lists are not treated as the ABI.

## Separate original object graph and construction recipe

**Music is not the128-byte audio manager.** Audio remains scene+20 with its DirectSound device+14/availability+78 fields. Music is a separate **44-byte (`0x2c`) object at application+50**, with a28-byte MFC map header at+0..18, current resource+1c, target/window token+20, application instance+24 and enabled word+28. These identities and offsets must not be shared.

The original application startup instruction interval is concrete:

- `4261d8`: push allocation size2c; `4261da`: call4f63ec.
- `4261f7`: push block size10; `4261f9`: ECX=allocated object; `4261fb`: call4f6118.
- `426200`: music+1c=0; `426203`: music+20=0; `426206`: global54131c=0.
- `426212..426215`: store the resulting separate object at application+50.
- `426218..42622b`: initialize it through4b52a0(instance,target,disabled), with original disabled argument0 on this startup path.

Map constructor4f6118 is already recovered by frozen `SinglePlayerSceneRuntime`; route that existing entry rather than duplicating it. It writes vtable5105c4, bucket pointer+4=0, bucket count+8=17, count+c=0, free-node+10=0, block-chain+14=0 and block size+18=10. The application interval's additional stores do not initialize music+24/+28;4b52a0 does. Other source allocator bytes remain preserved. This recipe establishes the interval and dependencies, not the whole application startup/WinMain body.

The source global words at54131c/541320/541324 are MIDI driver/resource ordinal/application instance. Their initial PE data values are0. The application interval explicitly resets only the driver word. Ordinal and instance are not reset by shutdown.

Each memory music resource is **96 bytes/24 words**, vtable513528. Its exact table has initialization+14=4b58a0, filename loader+18=4b5720, unload+1c=4b5a40, valid+20=4b56a0, start+24=4b5a80, pause+28=4b5b00, resume+2c=4b5b40, end+30=4b5ad0, restart+34=4b5b90, PE-resource loader+3c=4b59c0 and deleting destructor+4=4b56b0.

Inline factory4b53f0 initializes vtable513528; **only the byte at+4** to0; pause count+44, loop flag+48, target+4c, sequence+58 and cached-byte pointer+5c to0; and volume metadata+54/+50 to100, in original store order. It preserves the rest of the name buffer and other bytes. This is not a blanket memset. The resource name occupies the area starting+4; supported genuine names are short. Original name copy is unchecked; host byte-span validation/string scan bounds are explicit native extensions for unsafe metadata.

## Whole entry inventory

All entries use thiscall receiver except master-volume routines which ignore it and operate on the original globals. The original stack argument counts are preserved.

| Address | Arguments | Recovered body |
|---|---|---|
|4b52a0|instance,target,disabled|Manager initialization and AIL startup/open admission. |
|4b5300|none|Whole manager shutdown, two clears, global driver reset and AIL shutdown. |
|4b5340|none|Stop current, iterate/delete resources and clear map. |
|4b53f0|bytes,size,name|Allocate/inline-construct96-byte resource, initialize, register. |
|4b5470|resource|Insert map value; select first current resource only when current0. |
|4b54a0|name|Target-gated named lookup with original boolean/output semantics. |
|4b54f0|name,loop|Enabled-gated lookup, stop/clear old current, start new resource. |
|4b5550|none|End and clear current resource pointer. |
|4b5570|loop|End current, reread pointer and replay; forwards start result. |
|4b55a0|none|Current resource pause virtual wrapper. |
|4b55b0|force|Current resource resume virtual wrapper. |
|4b55d0|none|Current resource end virtual wrapper, preserving current pointer. |
|4b55e0|percent|Global master volume0..100→MSS0..127. |
|4b5650|none|Global MSS master volume→0..100. |
|4b56a0|none|Resource validity: sequence+58!=0. |
|4b56b0|deleteFlag|Deleting resource destructor. |
|4b56d0|none|Resource base destructor and vtable transition. |
|4b58a0|bytes,size,name|Whole memory-XMI loader/cached copy/AIL handle initialization. |
|4b59c0|PE-resource-name,name|Finite Find/Load/Lock/SizeofResource wrapper into initialization. |
|4b5a40|none|End, release sequence handle, free cached bytes. |
|4b5a80|target,loop|Start sequence and exact loop request. |
|4b5ad0|none|End sequence and clear pause count. |
|4b5b00|none|Status-gated nested pause. |
|4b5b40|force|Status/count-gated resume. |
|4b5b90|none|Conditional restart using saved target/loop. |
|4b5bd0|none|Valid handle and exact status==4 or==16 test. |

The public function returns native support/completion separately from its `result`. Meaningful source EAX is compared for scalar/pointer-return routines, including resource load/start/control/delete and master volume. Source void routines report native0 rather than elevating accidental register leftovers into behavior. Unsupported direct entry4b5720 returns native0 without claiming filename/CFile recovery. Dynamic unsupported virtual methods are explicitly forwarded through dependency.

## Exact startup, load and ownership behavior

Manager initialization stores+24 instance,+20 target,+1c=0,+28=1 and global instance541324. With disabled0 it calls AIL_startup and then AIL_midiOutOpen(&54131c,0,-1). Startup's return is ignored. A nonzero open return or zero driver clears enabled+28. Disabled!=0 also clears enabled without making either AIL call. **Every normal initialization returns1**, even when disabled/open fails. It does not invent a failure return or clear an old driver on the disabled path.

Resource load4b58a0 rejects bytes0, unsigned size<4 or global driver0 before ordinal/metadata effects. Otherwise it increments unsigned ordinal541320, sets loop+48=0 and volume+54/+50=100, and copies the provided name including NUL. Name0 formats original `MIDI%i` (`53244c`) using the signed decimal interpretation of the wrapping ordinal.

Only when cached pointer+5c=0 does the loader allocate exactly size bytes, store+5c, and copy every input byte. Allocation0 returns0 after the prior name/ordinal/metadata stores. An existing nonzero cache causes it to **skip allocation and copy**, even if a different input pointer/size was supplied. It then calls AIL_allocate_sequence_handle(global driver), stores+58 and calls AIL_init_sequence(handle,cached bytes,0). It calls init even if the allocated handle is0. Any nonzero init return is source success; a zero return calls AIL_release_sequence_handle on the current+58, clears+58 and returns0. Cached bytes remain for later unload. Reload overwrites an existing sequence handle without a preceding release; this source ownership quirk is preserved.

Factory4b53f0 allocates96 bytes, runs the exact inline constructor, dispatches initialization through virtual+14, deletes on normal initialization failure, and registers successful resources through4b5470. Resource-object allocation0 reaches an original null dereference, not a graceful false branch; native reports the tested failure prefix safely. Registration writes the returned4f62a8 map-value slot and sets current+1c only if it was0. Same-name registration replaces the map value while retaining the first current pointer. The suite verifies this and the resulting old-resource ownership behavior rather than inventing cleanup.

Manager select4b54f0 checks enabled+28, then performs target-gated lookup4b54a0. A missing name leaves the current pointer intact. A found resource causes4b5550 to end and clear the old current before starting the selected resource with the freshly read target+20. Success sets current to the selected pointer; failed start leaves current0. Replay4b5570 ends the current resource, **rereads** current+1c, then invokes its start with the freshly read target and supplied loop flag. Pause/resume/end wrappers require only a current pointer and retain source dynamic-vtable dispatch; end wrapper4b55d0 does not clear current.

Unload4b5a40 calls virtual end+30 first, rereads/release-clears sequence+58 if nonzero, then rereads/free-clears cached bytes+5c if nonzero. Reentrant release-service changes to these fields are preserved in original read/store order. Base destructor4b56d0 writes vtable513528, unloads, then writes50becc. Deleting destructor4b56b0 frees the entire resource only when flag lowbit1 and returns its token.

Clear4b5340 ends current, derives initial map positionFFFFFFFF from nonzero count+c, iterates GetNextAssoc, deletes each nonzero returned object through virtual+4(1), destroys the temporary CString, calls4f61a1 map clear, then sets current0. Shutdown4b5300 calls clear, checks/stops any current pointer, clears a second time, sets target+20/current+1c/global driver to0, and always calls AIL_shutdown. It preserves instance/ordinal/enabled and other words. Orphan resources absent from the map are not invented into its cleanup loop.

## Source sequence control and volume

Resource start requires virtual validity+20, stores target+4c and raw loop flag+48, calls AIL_start_sequence(handle), and when loop flag!=0 calls AIL_set_sequence_loop_count(handle,0). **Loop0 makes no explicit loop-count call.** It clears pause count+44 only after these calls and returns1. It does not set a guessed finite repeat count or clock deadline. End requires validity, calls AIL_end_sequence, clears pause count and returns1.

Status helper4b5bd0 invokes validity and returns1 only for imported AIL_sequence_status result exactly4 or exactly16. Bitmask combinations such as20 return0. These numeric tests are recovered; names/semantics of other vendor status codes are not inferred.

Pause first checks validity, then the status helper (which checks validity again). Only a true status proceeds. Pause count0 triggers AIL_stop_sequence; every proceeding call increments+44 modulo2^32. Nonzero counts skip the physical stop but still increment. A false status returns0 without changing the count.

Resume requires validity and returns1 for every valid-resource normal path. Only a false status and **signed pause count>0** proceed: decrement count, clear it if force!=0, and call AIL_resume_sequence if signed resulting count<=0. A true status or nonpositive starting count makes no resume/count mutation. Restart requires validity and false status, captures saved loop/target, clears pause count before virtual start, and returns1 regardless of that start result. No source timer is read in these controllers.

Master-volume setter uses global driver regardless of manager enabled/current. Driver0 returns0. Signed percent<=0 maps0, >=100 maps127, and1..99 maps integer floor(percent*127/100); the physical setter result is ignored and source returns1. Getter with driver0 returns100. Otherwise signed physical value<=0 maps0, >=127 maps100 and1..126 maps floor(value*100/127). This is not logarithmic DirectSound volume, float scaling or a fade.

## Raw C11 integration contract

`ClawMusicContext` contains existing raw `ClawSceneActorHost`, exact byte lookup, caller-shared `ClawMusicGlobals` and native traversal/fault fields. Globals correspond exactly to54131c/541320/541324 and must be shared across initialization, controllers, volume and shutdown. `lookupBytes` avoids rounding odd allocation sizes into extra source reads; the headless checks verify actual5-byte and all asset buffers. Without it, the declared fallback requires padded word-addressable spans.

Music manager requires11 words, each XMI resource24; original immutable vtable513528 must resolve through host lookup. Allocation/free and raw map metadata must remain coherent across callbacks. Source copied XMI pointers and sequence handles are distinct; the latter are opaque MSS handles, not image/actor/device identities.

`ClawMusicCall` retains function, receiver, six raw args, transport kind, outputs pointer/count. Ordinary AIL/PE/formatter calls use transport0 and receiver0. AIL_midiOutOpen retains args `(54131c,0,FFFFFFFF)` and a one-word output view directly into shared driver state. Resource methods and MFC map methods retain thiscall receiver identities.

MFC automatic stack pointers have an explicit normalized transport:

- Kind1,4f6286: one name argument, output[0] initialized0, return actual boolean. Resource lookup returns boolean-mask AND resolved output, including failure semantics; do not confuse this with other frozen APIs whose lookup service returns a resolved token directly.
- Kind2,4f5e1e: current position argument; three live output words initialized `{position,52e1c4,0}` become `{nextPosition,keyCStringData,resource}`. The temporary stack-address transport is normalized, not an extra original heap object.
- Kind3,4f6584: receiver0 and one CString data-value argument. Host can compose the frozen `ActorDestruction` CString destructor using an explicitly native temporary one-word receiver view. The oracle executes the actual original4f6584 body, adapting only InterlockedDecrement transport; whole shared-header refcounts/frees are compared.
-4f62a8 returns the writable map-value-slot token, which source then overwrites.4f61a1 is explicit map cleanup. These map/formatter operations remain adapter boundaries, not a recovered MFC hash/allocator implementation.

Normal transport4a3920 formats the original generated name into resource+4 with literal format53244c and signed ordinal. The PE wrapper uses exact FindResourceA/LoadResource/LockResource/SizeofResource slot identities546ac8/546acc/546ac4/546a54 and original type-name token532454. It does not implement a PE parser or CFile path behind those services.

Map traversal guard defaults65536 when maximum0. Fault1 denotes missing span/service,2 ABI/bounded metadata violation,3 nonadvancing traversal. These are native safety extensions and do not produce a claimed successful original return. No Source UI/cursor/keyboard, DirectSound audio-manager identity or game-clock fields belong in this music graph.

## Measured differential evidence

Commands:

```
work/test-env/bin/python Tests/compare_music_runtime.py
work/music-agent/check-smoke.sh
```

Final suite: **5,853 complete original calls / 7,227 ordered full-snapshot events / 767 original instruction addresses / all50 extracted XMI assets / five failure prefixes**. Comparisons cover1MiB heap,192KiB mutable original globals, exact copied bytes, allocation/free histories, map-service state, opaque DLL handle state and ordered calls. The DLL/map/formatter/PE transport policies are explicit fixtures. They are not execution of mss32.dll or a claim about physical MIDI output.

Coverage includes source valid/invalid/status/counter/mutating-controller matrices; nested signed/wrapping counts; volume domains and exact roundtrip scaling; startup disabled/error/output driver profiles; enable/current/target/name gates; odd/short/cached memory loads; normal data-allocation/init failures; resource unload/base/delete ordering and reentrant field reads; PE transport failure prefixes; repeated reload and same-name replacement ownership;16 retained five-resource clears.

All50 files under `work/original-disc-assets` are copied through complete original memory-load/factory bodies and retained select/start/loop/pause/resume/end/restart/shutdown trajectories. Per-file SHA/lengths are in `work/music-agent/verification.json`. PLAY/PLAY0, BOSS/BOSS0 and game music are tested as opaque original file bytes. Archive identity versus original v1.0 assets remains unknown.

Frozen `SpecialCommandRuntime` is genuinely composed through MusicRuntime for216 complete original42d420/42d440 calls covering application+50 music pointer and application+14 admission, current resource, status and nested counts. The application audio-admission word is separate from the music manager enabled word; source wrappers preserve that distinction.

Failure tests compare original prefixes for invalid input span, resource-object allocation0, invalid resource receiver, current pointer nulled during replay's end callback and nonadvancing map transport. They are not counted as completed original calls. Unsupported filename path and ABI rejection are checked separately. Strict C11 smoke exercises exact odd bytes, startup, start/loop, nested pause/resume, volume and deletion under ASAN/UBSAN; Swift imports the raw global/transport ABI and verifies disabled-driver semantics. No Xcode, simulator/device or audible acceptance test was performed.

## Remaining scope

MSS sequence parsing/synthesis/device/timing is physical/library transport; no approximate melody or guessed duration is shipped here. Filename loader4b5720/CFile and alternative MCI music implementations4b5c10 onward are explicitly unported. PE and MFC helper bodies remain declared services; the source wrappers around them are recovered. Full level-start resource variant selection remains the frozen parent-owned scene body and must route its memory bytes into4b53f0. This handoff does not establish full-game or audible equivalence.
