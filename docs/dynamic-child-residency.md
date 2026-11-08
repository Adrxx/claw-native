# Dynamic elemental-child deletion and spatial residency

This audit composes frozen source bodies; it adds no gameplay runtime or deletion policy. The oracle executes unchanged v1.0 instructions from `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

## Source result

Elemental cleanup `411cd0` ORs `10000` into the optional Flare actor's flags. It does not clear the elemental private `150` child token or destroy the child. The generic scene update `4c8fc0` inspects this flag only on actors it traverses in the active CList. It gathers actors for deletion, finishes the full traversal, then invokes state29 for each queued actor whose flags contain80000 and performs its deleting virtual/list removal. An elemental parent therefore marks its Flare during the deferred deletion phase, after the child's visit, regardless of their relative z order.

Final `4d2000` calls residency `4d4d10` using the integer truncation of the main plane's binary32 `10/14` center. That body has **no10000 deletion branch**. Ordinary40000 actors outside their layer rectangle move from the active list into the dormant spatial cells. This includes a marked Flare. Subsequent active updates do not traverse it; the flag and private allocation remain live. Activation `4d1fd0 →4d4b50` removes the dormant member and reinserts its actor in the active list. The ensuing `4c8fc0` finally elects deletion, frees the Flare private19/primary93/actor, and clears the actor flags through the real destructor.

The retail elemental constructor's child creation passes flags40000 and child z=parent z−1. Neither the Flare constructor nor initializer invents an always-resident bit or TTL. This audit starts from a source-shaped, already-published private graph and does not repeat constructor/asset recovery from the frozen ElementalProjectile/Flare suites.

## Exact residency distinctions

The source `4cb040` profile has ordinary half-width/height 800/600, layer800000: 1280/960, and layer1000000: 384/288. When both layer bits are present,800000 wins. The out-of-range comparison is strict; exactly 800 pixels from an ordinary center remains active. Actor flag2 bypasses residency. Flag20 selects destruction instead of dormancy when outside the selected rectangle. Flag100000 requests state30 while moving dormant and restores the previous state only if the callback leaves30. Flag80000 requests state29 on destructive paths. Flag40 has a separate destruction gate on the **camera center** leaving the full world's ±320/220 margins. These flags are not substitutes for10000.

Membership uses actor `88` embedded links, cell token `94`, and stored/clamped coordinates `98/9c`. A dormant actor's live `4c/50` position can change without moving that member. Activation tests the member coordinates, not its latest visual pose. Activation also returns immediately when its integer center equals the last cached grid `68/6c` center. A newly dormant marked member inside that cached rectangle can therefore remain dormant until the center changes.

Whole ordinary frame `46ac30` runs activation/update/interactions, bounds and rendering/presentation services, overlay, device servicing, and **then** final residency. For source 19..36ms subdivision, a second active pass can delete the marked child before final residency. At 37..99ms, the intermediate residency can move it dormant before the next pass. The tests retain these source distinctions instead of installing a uniform repeated timestep.

Grid teardown `4d50e0` destroys dormant actors through their real deleting virtuals. That routine itself leaves cell links/counts containing the now-freed actor member. Following `4d4b00` releases the layer/cell storage. Do not query or activate between those teardown phases.

## Parent integration recipe

Keep the existing source deferred marking and retain the child component/token while its spatial member is dormant. Reinsert through source activation and remove the component only when the elected source destruction actually releases it. Do not sweep10000 across all components, force Flare expiry, or free it when the parent component is removed.

For a retained child, log the actual plane binary32 center, the grid cached center, actor flags/layer, embedded cell token, stored member coordinates, active CList membership, and ordered deletion/free calls. Player distance alone does not identify the source window. In the reported x1601 child/x781 stationary player fixture, actual movement and camera approach should elect source activation; the parent reports that the corrected releaseDown/right pressed-edge fixture now observes that release without changing runtime deletion behavior.

Preserve ownership distinctions: elemental private150 is a retained reference; the scene/grid owns the child's membership and deletion. Source destruction clears actor bytes before its allocator free. `4d4d10` has an actual post-destruction flags reread, so the allocator transport in these tests retains cleared actor storage while tracking its logical free. This is explicit original behavior, not permission to dereference other freed objects.

## Measured evidence and limits

`Tests/compare_dynamic_child_residency.py` passes 255 complete original/native calls, 6,714 ordered full snapshots, 253 retained frame observations, and 1,945 original instruction addresses. Every snapshot contains 393,352 bytes: the entire384KiB fixture heap, scene scratch/list globals, stage clocks/player alias, camera aliases, and outer timing state. Meaningful whole46ac30 returns, stack restoration, SEH alias, allocation order, complete actor/primary/private/cell/list bytes and free order are checked. The suite rejects spans beyond the actual 86/19 private words and rejects swallowed composition callback errors.

Histories cover stationary retention, camera re-entry, cached-center behavior, changed live pose with retained stored cell coordinates, both z orders, boundary truncation, all three layers, explicit flags2/20/100000/80000, source frame deltas0/1/17/18/19/20/36/37/54/55/98/99/100/101/FFFFFFFF, full dormant destruction/layer teardown, and 40 seeded out/in histories with unsigned countdown/skip gates. Six source actor/private/logic identities are checked for duplicate frees on every completed frame.

`work/dynamic-child-residency-agent/compile-smoke.sh` passes 100 native ASAN/UBSAN retained mark→dormancy→reactivation→destruction histories. The private allocations are exactly 86 and 19 words and are actually released once. The generic actor API still uses the frozen128-word compatibility view; source animated actor allocation is109 words. Actor storage is deliberately retained for the source post-free reread, so this sanitizer claim does not establish a109-word generic destructor allocation contract. No new C ABI is introduced.

The differential profile parks the Flare primary at source state1000; the exact457f00 wrapper executes, but its idle ANI/controller is not elected. This isolates list ownership and delayed destruction from the separately recovered Flare ANI/asset graph. Clock/timeGetTime, keyboard GetAsyncKeyState,4025c0 bounds,4cb9b0 rendering, renderer presentation,46c2c0 overlay/audio and4b98b0 device operations are explicit transports. Contact pairs are deliberately ineligible; parent collision is represented by its preexisting10000 mark, then **actual**410100 state29/411cd0 executes. The pose-mutation history is an explicit external mutation, not a new claim of elemental flight recovery. Resource loading, constructor failure, physical rendering/audio, player input election and complete original event-loop scheduling remain outside this focused audit.

A Python-loaded sanitizer library failed because the signed interpreter did not install ASAN interceptors. The standalone instrumented C++ ownership smoke above replaces that failed attempt; no Python-sanitizer pass is claimed.
