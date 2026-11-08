# Original pickup points actor

`PickupPointsRuntime` recovers the whole retail v1.0 `4737c0` points wrapper and registered `PointsIcon` callback `473a70`. It composes the frozen scene creator, actor image binder and actor animation runtime. The fingerprinted executable is `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra output and entry-boundary evidence are in `work/pickup-points-agent`; the headless log has no script error.

## Original behavior

Registry entry120 is literal `522874`, `PointsIcon`, callback `473a70`, metadata flags2. There is no Points-specific private allocation, constructor, physics, timer, state table or destructor. Its actor/primary are the ordinary animated scene actor allocations `1b4`/`174` bytes. The wrapper's named creator receives `(0, item.x, item.y, 22c4, PointsIcon, 40000)`, with the container read through `item.parent+8`. The source flags are therefore passed by this caller, not forced by generic creation. A missing named entry or null adapted creator is a normal void return.

After creation, the wrapper binds the default `GAME_POINTS` image (`52a6c0`) and then reads the live item value at `fc`. Values map as follows:

| Value | Frame |
| --- | --- |
|100|1|
|500|2|
|1500|3|
|2500|4|
|5000|5|
|7500|6|
|10000|7|
|15000|8|
|25000|9|

All other values invoke the indexed image setter with frame0, including its second registry lookup. For mapped values, a missing image root returns without another frame write. A present root uses signed minimum/maximum bounds; an unavailable mapped frame writes the requested frame number and a zero image pointer. Frames8/9 invoke `40f680`; the other cases inline the same absolute image-table indexing. Missing image lookup clears root170 and preserves the old frame/leaf fields. Default and indexed setters are supported only for the original `GAME_POINTS` literal, not generalized to arbitrary resource names.

Callback state0 captures the original primary pointer, sets actor flags `|21`, selects `GAME_POINTS` ANI with eager0, and sets that captured primary state to5. Thus rebinding actor.primary during the service does not redirect its final state store. State5 passes the current animation delta (`5430c4`) into the original animation update; after the update it reads live stopped1a4 and delay19c. It sets Delete10000 only when stopped is nonzero and delay is zero. Other states return1 without changes. Missing ANI lookup still advances the startup state to5, matching the source. There is no invented TTL, rising velocity, fade or independently timed completion: the retail ANI supplies movement and stop control.

The generic actor destructor frees its primary and actor through the frozen `ActorDestruction` implementation. Scene scheduling remains the frozen `SceneActorRuntime` responsibility; this module sets the original deletion flag and does not remove the scene node itself.

## Native host ABI

The header is C11-compatible. Call `claw_pickup_points_entry` with one cdecl actor argument for `4737c0`/`473a70`; use a root receiver plus one index for `40f680`, or actor receiver with name and optional index for the image setters. Return value denotes supported scope. Meaningful original EAX is separately returned for `473a70` and `40f680`; incidental wrapper/setter EAX is deliberately not represented as gameplay output.

`ClawPickupPointsContext.scene` owns stable token-addressed spans, heap allocation/free, metadata lookup and ordered external services. Set animationDelta/audioPosition from the current source frame/audio globals and clear fault before entry. `composeCreation=1` executes the frozen scene creator. With pointsEntryToken0 it preserves the named lookup; host.call `4f6286` can resolve the token through public `scene.entry(named:"PointsIcon")`. A nonzero pointsEntryToken is an explicitly pre-resolved metadata shortcut and omits that lookup event. It is not the exact original named-wrapper event graph.

`composeAnimation=1` executes frozen actor ANI selection/advance with live actor records and actual image tables. `4f6286` returns the resolved resource token, while the original bool/out-pointer transport is adapted. Audio `4c88e0`/`4208e0` remains an explicit ordered leaf call; its four arguments are preserved. External callbacks can mutate context globals. As in the frozen animator, mutation of actor/sequence/image/record buffers during an audio callback is an explicit unsupported boundary, diagnosed rather than silently committed.

With composition disabled, dependency callbacks receive the original creation or animation entry and arguments. This supports host routing without pretending those services were executed here. Fault1 denotes missing spans/services; fault2 propagates creator/animation diagnostics. These are native safety diagnostics, not original normal failure returns. Original allocation failures actually fault after an already-observable prefix; tests compare that prefix.

## Verification

Run `work/test-env/bin/python Tests/compare_pickup_points_runtime.py`. Strict C++17 compilation uses `-Wall -Wextra -Werror -ffp-contract=off`; the header also passed a C11 include-only compile.

Final evidence: **1,082 whole original calls, 1,144 ordered full 524,288-byte heap snapshots, 1,055 original instruction addresses**. Each call compares the complete heap, animation/audio globals, actor identities, allocation cursor and ordered boundary state, with meaningful returns checked separately. Directed cases cover every mapped value and nearby/unmapped/signed values, absent images/metadata/ANI, signed image bounds and table guards, null creator, and live service mutations. Forty histories retain actual named creation → original startup → actual retail eight-record `POINTS.ANI` completion → generic actor/primary destruction; deltas16/75/300/ffffffff exercise timing and unsigned large-delta paths. All 344 actual ANI record decodes used by fixtures are independently compared against whole original `4d76e0`.

Three failures inject null allocation for actor, primary and list block. Full prefix buffers/services agree through original faults at `4c8d02`, `4c7e8b` and `4f5ac1`, respectively; the x86 null page is unmapped and FS uses an explicit Windows TEB adapter. One actual ANI record additionally receives a synthetic sound token to verify ordered audio transport and audio-global mutation; this is not evidence of retail Points audio playback.

Resource lookup results, allocator address choices and image leaf tokens are explicit fixture services. Retail ANI bytes are decoded, but image loading/rendering and audio playback remain native resource/platform boundaries. The suite proves the bounded points family and its composed tested paths; it does not prove complete game behavior, collision election, UI presentation or every scene scheduler history.
