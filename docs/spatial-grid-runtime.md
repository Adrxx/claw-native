# Original spatial grid runtime

`SpatialGridRuntime.h/.cpp` translates the original v1.0 plane/grid stage graph, intrusive cell registration, rectangle activation, scene residency, startup extraction, and dormant destruction traversal. It composes frozen `SceneActorRuntime` insertion and caller-routed destruction/gameplay callbacks. No reference gameplay source or CrazyHook table supplies these routines. The original oracle remains SHA-256 pinned to `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

## Stable C11 API

`claw_spatial_grid_entry(function, receiver, arguments, host, fault, result)` uses the frozen raw `ClawSceneActorHost`. `ClawSpatialGridArguments` contains eight 32-bit words and a count. Set fault to zero before calling. The native return indicates support; `result` carries the original meaningful result. Unknown entries return zero. Void incidental EAX is not claimed. Fault 1 indicates a missing token span/service; fault 2 indicates unsupported metadata/allocation paths or a native loop/allocation safety bound.

| Entry | Native receiver | Arguments | Meaningful result |
| --- | --- | --- | --- |
| `4d1fd0` / `4d2000` | plane | none | activated / residency-change count |
| `4d4b50` / `4d4d10` | grid | centerX, centerY | corresponding count |
| `4d2030` / `4d4c40` | plane / grid | none | startup extraction count |
| `4d50e0` | grid | none | dormant destruction traversal count |
| `4d51a0` | grid | actor token | void |
| `4f4630` | layer | member token (actor+88) | one |
| `4f4680` | layer | member token | void |
| `4f46b0` | layer | left, top, right, bottom, remove | activated count |
| `4f4860` | 17-word iterator | layer, remove | member token or zero |
| `4f48a0` | iterator | layer, left, top, right, bottom, remove | member token or zero |
| `4f49c0` | iterator | none | next member token or zero |
| `4f4490` | layer | left, top, right, bottom, requested cellWidth, cellHeight | success |
| `4d4890` | grid | scene container, rectangle token, six pair tokens | success |
| `4d1620` | plane | WWD record token, signed record count | success |
| `4d2050` | plane | none | void |
| `4d4b00` | grid | none | void |
| `4d4a90` / `4f45f0` | layer | deleteFlag / none | receiver / void |
| `4cb040` / `4cb0e0` | world | viewport width,height / rectangle token | success |

Public conventions follow the original ECX receiver and stack argument words. Internal `4d5120` is an original cdecl layer argument; it is composed inside `4d50e0`, rather than exposing a changed calling convention. The supported dispatcher does not replace the original module's missing resource/record implementations with successful no-ops.

## Object graph and initialization

The camera-only world needs 25 words; **spatial construction needs 56 words** through +dc. The root host's 56-word world and 86-word planes are sufficient for this module. A plane needs at least 45 words: parent token at +c, positive pixel extents at +30/+34, binary32 center at +10/+14, and grid token at +b0. Parent+8 is the scene actor container, and parent+24 is the world.

The grid allocation is **70 hex bytes / 28 words**, with fields:

| Grid offset | Meaning |
| --- | --- |
| +0 | scene actor container |
| +4 / +8 / +c | three layer tokens |
| +10..1c | ordinary residency rectangle based on pair 4 |
| +20..2c | flag1000000 residency rectangle based on pair 6 |
| +30..3c | flag800000 residency rectangle based on pair 5 |
| +40/+44 | ordinary half-size |
| +48/+4c | flag800000 half-size |
| +50/+54 | flag1000000 half-size |
| +58..64 | inclusive complete world rectangle |
| +68/+6c | last activation center; initial sentinel `ffffa932` |

Each layer allocation is **44 hex bytes / 17 words**. Its original vtable identity is `513db0`, whose deleting method is `4d4a90` and activation method is `4d4870`. Fields are vtable+0; initialized+4; dormant member count+8; column/row counts+c/+10; shift counts+14/+18; cell count+1c; coordinate differences+20/+24; unnormalized inclusive bounds+28..34; quantized cell sizes+38/+3c; and cell array token+40.

The cell array allocation is `cellCount*8+4` bytes. Its allocation base stores count; layer+40 points **four bytes after that base**. Each cell has head/tail tokens. Layer destruction frees `arrayToken-4`. Original cell construction `4f4a90` clears both words, and the array destructor uses the original no-op cell destructor; native memory adaptation preserves those writes and ownership.

Cell nodes are embedded in actor+88:

| Member offset | Actor offset | Meaning |
| --- | --- | --- |
| +0 / +4 | +88 / +8c | next / previous cell member |
| +8 | +90 | preserved unrelated member word |
| +c | +94 | owning cell token |
| +10/+14 | +98/+9c | residency coordinate |
| +18 | +a0 | actor identity |

These nodes are separate from the scene's pooled three-word nodes. Actor+68 holds its scene node. The native host must retain the actual scene list layout and preserve raw token interiors.

### Verified original world defaults

The actual world constructor `4cace0` stores the following six pairs. Complete methods `4cb040(width,height)` and `4cb0e0(rectToken)` reproduce the same stores and set world+10..1c to an inclusive viewport. Both methods are native entries, compared over seeded whole heaps; the suite separately executes the complete original constructor as a default witness, without claiming to port that entire constructor.

| World offsets | Requested sizes | Use |
| --- | --- | --- |
| +b0/+b4 | 500,250 | ordinary layer cells |
| +b8/+bc | 1000,1000 | flag800000 layer cells |
| +c0/+c4 | 250,125 | flag1000000 layer cells |
| +c8/+cc | 1600,1200 | ordinary activation/residency extent |
| +d0/+d4 | 2560,1920 | flag800000 extent |
| +d8/+dc | 768,576 | flag1000000 extent |

`4f4490` truncates its original logarithm ratio to shift counts and evaluates powers of two for cell sizes. The native positive-integer form gives original default actual cells **256×128**, **512×512**, and **128×64**, not the requested sizes. Original instruction comparisons cover powers, adjacent values, these defaults, and complete actual Level1-sized construction. The native integer form replaces the original log/pow/ftol sequence for supported positive integer metadata; nonpositive sizes and unsafe allocation domains receive a native fault rather than an invented normal-return claim.

The plane constructor captures its complete-world rectangle, scene-container identity, and all twelve size words **before allocating its grid**. These stack-local values remain authoritative if an allocation adapter mutates parent/world/plane buffers. Directed full-buffer/event comparisons exercise that ordering. The rectangle overload `4cb0e0` preserves original sequential writes even when its source aliases the destination world words; ten nonzero alias fixtures compare the actual body.

The original formula uses coordinate differences **without +1**, then signed division by quantized cell size **plus one** for column/row counts. In a 24576×6144 Level1 action plane, the three cell-array counts are **4608, 576, and 18432**, verified through complete original plane/grid construction. Allocation spans must accommodate those original arrays.

### Native host recipe

1. Retain the original world/parent/plane/list links and initialize the 56-word world viewport/default sizes through `4cb040(world,640,480)` or the appropriate recovered rectangle method. These methods preserve unrelated world words.
2. Use the original loader-derived pixel extents, plane parent, and zero initial +b0. `4d1620(plane,nonzeroRecordToken,count)` allocates grid/layers/cells and invokes the bounded record decoder service once per record. For a separately materialized graph, `4d4890` accepts a caller rectangle and all six world pair tokens; initialize the grid's first four words as the original enclosing allocator does.
3. Route frozen WorldObjectRuntime's `4f4630` dependency directly into this module with its selected layer and actor+88. `4d51a0` offers the original flag-based selection: 800000 has priority over 1000000; otherwise ordinary layer.
4. Execute original startup `4d2030` after the grid/records exist. It inserts always-active actors into the scene and removes their cell memberships before camera-range activation. Do not initialize every WWD actor as a scene resident.
5. Route SceneActorRuntime's `4d1fd0`/`4d2000` events into the dispatcher with the event's plane receiver and no arguments. Return the original `result`, preserving the scene scheduler's existing order. The wrappers read/truncate **binary32 plane center**, not viewport left/top.
6. Route actor callbacks and actual polymorphic actor destructors through the existing native modules. For plane teardown, `4d50e0` destroys dormant actors through their actual vtable+4, then `4d4b00` destroys layer arrays and layer objects. Complete enclosing plane/resource destruction remains WorldPlaneRuntime/host work; do not infer that `4d4b00` alone destroys dormant actors.

Plane constructor evidence starts at `4d03b0`; WWD160 loader at `4d0450`, whose `4d07ca` call reaches `4d1620`. WWD flags/scales/extents and full plane construction are owned by the independent WorldPlaneRuntime worker. Frozen SceneCameraRuntime owns viewport/clamp/follow `4d0c50`/`4d0a60`/`42d5f0`. This module neither duplicates their bodies nor infers source-reference plane conversion.

## Activation, residency, and ordering

`4d4b50` returns zero when both integer center values equal its cached values. Otherwise it stores them, then invokes the three layer rectangle queries in ordinary/800000/1000000 order. Rectangle queries clamp to layer bounds, traverse cells row-major and members head-first, test inclusive coordinate bounds, optionally remove the member and clear its owning cell, decrement dormant count, then invoke layer virtual+14. The default original `4d4870` reads member+18 → actor+c → parent+8 and composes actual scene insertion `4c9320`. Unknown layer vtable identities remain explicit calls with their actual receiver and argument.

`4d2030` calls `4d4c40`, which traverses all three layers using the original iterator helpers. An actor flag2 or primary logic flag4 selects startup scene insertion regardless of camera range; the member is then removed from its cell. This gate does not mean every dormant actor should run an initialization callback immediately. Actual generic scene dispatch governs subsequent callback timing.

`4d4d10` caches its six activation limits and scene-list identity, then traverses the original scene list using each node's saved next token. Actor flag40 plus a center outside complete-world margins **320 X / 220 Y** can issue state29 when flag80000 is set, unlink the scene node, and invoke the actual deleting destructor. The routine then rereads actor flags; complete generic destruction clears them. Earlier bounded adapter tests and later complete destructor chains distinguish these two dependency domains.

For remaining actors, flag2 bypasses residency management and flag40000 enables it. The routine clamps actor x/y into complete grid bounds and stores actor+98/+9c. It selects the same three flag-prioritized layers. Out-of-range actors without flag20 can receive state30 when flag100000 is set; the previous primary state is restored only if the callback leaves it at30. It unlinks the scene node and registers the embedded member back into the selected dormant layer. Actors with flag20 instead optionally receive state29 and are destroyed. Callback bodies may mutate buffers, so callback order and rereads are preserved.

Scene unlink/pool release translates original `4f5212`, `4f56e7`, `4f5172`, and chunk-chain frees. The final scene node removal clears count/free/head/tail, frees every original pool block in order, and clears the block chain. Insertions compose frozen SceneActorRuntime, including actual z sorting and node allocation. No invented duplicate membership filtering or range normalization is introduced.

Dormant traversal `4d50e0`/`4d5120` invokes each represented actor's actual deleting vtable method. It does not independently clear cell arrays or decrement dormant counts; the enclosing teardown must complete layer destruction before reusing that graph. Unknown private/gameplay/resource destructors remain actual host-call boundaries. The suite additionally composes frozen ActorDestruction for complete generic actor→primary logic→heap release paths against the actual original bodies.

### Iterator nontermination boundary

Actual `4f49c0` instructions at `4f4a26..4f4a50` repeatedly reread the **same current member** when that member is outside the filtered rectangle. The next pointer is written but current is not advanced in this branch. A directed original witness exceeds the 500,000-instruction bound inside this loop. The native API reports fault2 after its loop bound; it does not fabricate a successful filtered iterator result. Whole-layer startup/destruction with valid in-world residency coordinates avoids this branch and has complete original-call evidence. Rectangle activation `4f46b0` uses a separate traversal that advances past nonmatching nodes normally and is fully compared for clipped/remove/nonremove queries.

## Verification and limits

Run `work/test-env/bin/python Tests/compare_spatial_grid_runtime.py`. The suite compiles optimized C++17 with `-Wall -Wextra -Werror -ffp-contract=off`. It executes hash-pinned original functions, including original log/pow/ftol bodies, list/cell routines, actor scheduling, clock bodies, and camera follow, with explicit heap/platform/resource adapters. Every complete call and ordered service boundary compares all **384 KiB** of caller raw heap; full frame snapshots additionally compare stage, animation, camera, and input globals. Original SEH restoration is checked on normal returns.

Final verified run: **5,564 complete original calls**, **17,835 ordered full-heap snapshots**, and **3,164 original instruction addresses**. Coverage includes seeded/aliased world defaults, preallocation captures and constructor failure paths, direct original actor/member registration/removal, inclusive/edge queries, iterator state buffers, startup gates, callback state/flag mutations, 48 genuine normal/substep frames, 128 retained frame histories, and 160 complete generic destruction chains. The nonterminating iterator witness is separate and is not counted as a successful original call.

All **38 actual CD Level1 Rat/Officer WWD records** feed frozen WorldObjectRuntime with explicitly adapted resource lookup/gameplay callbacks and verified zero entry flags; all38 profiles activate through actual Level1-sized cells, then execute 192 retained activation/residency calls against original bodies. This proves their spatial profile transitions. It does not claim to execute Rat/Officer private initialization, ANI/resources, attack/death gameplay, or full world startup in this fixture. Those bodies remain their respective recovered modules and root integration responsibilities.

The genuine frame graphs compose frozen SceneActorRuntime, SceneCameraRuntime, GameTiming, SpriteGeometry, and ActorInteractions. Input is a deterministic no-key platform profile; represented actors have no eligible contact/damage masks in these frame fixtures. The grid stages are real bodies, not no-op services. Actual macOS input, complete populated collision/gameplay, graphics/resource lifetime, and full-game equivalence require separate integration evidence.

C11 header compilation passes. A native Swift executable links the C ABI and verifies original world defaults, full grid construction, cell registration, scene activation, dormant reinsertion, and scene-pool cleanup. Its private sources/executable are `work/spatial-grid-agent/bridge-smoke.*`; no Xcode or device/UI driving is used. Numerical/count evidence is retained in `work/spatial-grid-agent/verification.json`; original decompiles and closed private Ghidra project are in that directory. Only this module's new source/test/doc files were edited.
