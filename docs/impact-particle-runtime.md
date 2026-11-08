# Original impact particle creation and controllers

`ImpactParticleRuntime.h/.cpp` recovers four complete original v1.0 cdecl bodies. It composes the frozen actor creator and animation runtime and keeps registry/image/audio transport explicit. No reference-port gameplay or particle implementation is used.

The original instruction oracle requires `Original/claw10/CLAW.EXE` SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private decompiles are `work/impact-particle-agent/roots.c` and `callbacks.c`; instruction addresses and actual call ABI are checked against `work/v10-disassembly.txt`.

## Owned whole entries

| Original address | Exact ABI | Recovered behavior |
|---|---|---|
| `461a00` | cdecl `(scene,x,y,z,style,sourceActor)` | Reject invalid source, create/bind/init HitBurst immediately, return creation success. |
| `461a90` | cdecl `(actor)` | HitBurst controller: validate source, random animation, relative positioning, animation stop/deletion. |
| `461c40` | cdecl `(scene,x,y,z)` | Create deferred Splash, with explicit null-scene rejection. |
| `461bc0` | cdecl `(actor)` | Splash controller: animation then image binding, animation stop/deletion. |

Original registry entries are HitBurst ordinal169/name literal `522570`/callback `461a90`/flags2 and Splash ordinal170/name literal `522568`/callback `461bc0`/flags2. These controllers have **no subtype-private allocation or subtype vtable**. The complete composed generic creator allocates animated actor `0x1b4` bytes and common logic `0x174` bytes; their original vtables are `5137f0` and `513740`. The API uses 128 actor words as the frozen portable actor span, without claiming those extra words are allocated by the original.

`461a00` checks `sourceActor==0`, then `source+38==-1`, then `source.flags8&10000`. It calls `4c8da0(scene+8,0,x,y,z,522570,40000)`, binds `GAME_ENEMYHIT` (`5294dc`) for style0 or `GAME_CLAWHIT` (`5294ec`) for every other style, stores `sourceActor` at actor+80, and immediately calls actor+6c→logic+10. Its final return is1 even if that immediate controller returns0 and marks the new actor deleted. The `40000` create flag alone does not request generic eager initialization. The draw-status test is the exact -1 sentinel; status0 is accepted.

`461a90` caches source+80 and logic+6c before external calls. Its source rejection order is source0, deleted flag, then draw-status -1. Every rejection ORs actor.flags8 with `10000` and returns0. State0 ORs flags with `21`; signed `4a3050()%3` chooses `GAME_SMLHITBURST` (`5294fc`) for0, `GAME_BIGHITBURST` (`529510`) for2, and `GAME_MEDHITBURST` (`529524`) otherwise. Negative remainders take medium; the genuine RNG normally returns nonnegative values. Named ANI selection is `4c79e0(actor,name,0)`, so the first record is not eagerly advanced. It then writes actor+158/+15c = actor.x/y - cached source.x/y and cached logic+1c=5. These are exact raw offsets, despite their generic motion-field reuse.

In state5, `4c82a0(actor+188,5430c4)` runs before checking actor+1a4 stopped and actor+19c index. A nonzero stopped word with index0 marks `10000` and returns0 before position following. Otherwise x/y become cached source.x/y plus actor+158/+15c with modulo2^32 arithmetic. Other states return1 without animation/follow stores. External services may mutate actor+80, coordinates or logic pointers; the source preserves the cached identities for the current invocation.

`461c40` rejects scene0 before reads, calls `4c8da0(scene+8,0,x,y,z,522568,40000)`, and returns whether the created actor is nonzero. It does not invoke Splash immediately. Splash state0 sets flags21, calls `4c79e0(actor,GAME_SPLASH5266ec,0)` **before** `4c7970(actor,LEVEL_SPLASH529538)`, then writes cached logic state5. State5 has the same animation stopped/index0 deletion test and no source-follow movement. Other states return1.

There are no collision, countdown/TTL, explosion-radius, opacity, particle physics, audio or scene-delete calls in these four owned bodies. ANI records can dispatch their own audio through the composed animation runtime; these four extracted ANI files contain no audio-event records. Actor flag deletion is consumed by the frozen generic scene scheduler; generic teardown is not reimplemented in this module.

## Raw C11 host contract

`claw_impact_particle_entry(function,receiver,args,count,context,dependency,user,result)` separates native support from meaningful source EAX. The four owned roots are cdecl: `receiver` is ignored and exact argument counts are 6,1,4,1 respectively. Unsupported addresses return native0 without changing fault. Invalid count/null args produce fault2; missing span/service produces fault1. Frozen creator/animation faults propagate. Invalid native spans stop safely; failure-prefix comparisons do not claim the original returned normally.

`context.scene` is the existing `ClawSceneActorHost`. It must map raw writable actor/logic/scene/registry/ANI/image-manager/list blocks and original immutable identity words when a frozen composed callee reads them. The host's allocation/free functions preserve the allocation size and ownership boundaries. The context's `animation.animationDelta` is original `5430c4` and `audioPosition` is `532c10`. Neither of these four roots reads a wall clock. Stage timing, animation timing and random TLS state remain separate.

`composeCreation!=0` executes frozen `claw_scene_actor_create_named` rather than requesting a six-argument creation service. It resolves metadata through `scene+14→registry+10`, allocates the actor and common logic, initializes fields and inserts into the original depth-ordered list. This uses the frozen constructor's preserved allocation bytes; a zeroed native allocator is a declared allocator adaptation, not a claim about original heap identity.

`composeAnimation!=0` executes frozen `claw_actor_animation_entry` for `4c79e0` and `4c82a0`. Exact registry and audio callbacks then pass through `context.scene.call`. The frozen animation runtime's existing malformed-record and callback-mutation restrictions still apply. The actual supported ANI profiles do not reach those restrictions.

`ClawImpactParticleCall` carries function identity, receiver, six raw arguments, argument count and optional descriptive name. The optional names are annotations; original tokens and ordering are authoritative. With composition disabled, creator `4c8da0` and ANI calls retain their exact function/receiver/arity through this richer adapter. Source RNG `4a3050` always has receiver0 and zero arguments. Image binder `4c7970` always has actor receiver and one original name token; root can route this to frozen `ActorResourceBindings`. An immediate creator callback with an identity other than the two owned controllers is forwarded with receiver0 and one actor argument.

### Minimal graph recipe

- Scene+8: actor-container token. The container has scene at+c and its CPtrList at+10, including original block-size/free-node ownership.
- Scene+10: image registry; Scene+14: logic registry; Scene+2c: ANI registry. Image/default ANI services normalize `4f6286(registry+10,name,outPtr)` to a returned resolved token without hiding event order.
- Scene+24: original world/default holder used by frozen generic actor initialization; supply the real existing graph instead of inventing a numeric type.
- Metadata words include flags at+8 and callback at+10. Use the actual registry identities above.
- Image manager uses its image-pointer table at+14 and signed ID bounds at+64/+68. Hit image inventories contain FRAME001 through FRAME005. Distinct enemy-hit and Claw-hit managers/tables are retained in the test graph; image pointer gaps/out-of-range selections preserve source token0 behavior.
- ANI raw sequence has record table+0c/count+10. Raw 12-word records come from the frozen decoder; code/preservation fields remain intact. No private particle object or hidden lifetime buffer is needed.
- HitBurst actor+80 must remain the source actor identity. If the scene destroys that actor before the particle controller next reads it, the host must preserve the source game lifecycle/ordering; this module does not turn stale tokens into an invented deletion result.
- Dispatch HitBurst/Splash through the ordinary frozen scene scheduler after their source-defined initialization order. Generic scheduler deletion/list removal and `ActorDestruction` free ownership remain frozen services. The verification executes the genuine generic deleting destructor after retained terminal profiles.

## Asset and differential evidence

`Tests/compare_impact_particle_runtime.py` runs native and full original roots on the same heap graph, logs ordered service callbacks with whole-heap and mutable-global snapshots, and compares EAX, complete heap bytes, globals, allocations/frees and callback ordering. The span covers384KiB of private heap plus192KiB of original mutable globals. Source RNG can execute actual `4a3050→4a7dc0` while native uses frozen `WorldLoot`'s verified TLS seed update; synthetic signed RNG returns are explicitly labeled adapter cases.

Actual extracted files are GAME ANIS SMLHITBURST/MEDHITBURST/BIGHITBURST (12 records each) and SPLASH (7 records), plus the ten GAME CLAWHIT/ENEMYHIT PID files. Every ANI record is checked against full original decoder `4d76e0` and installed with its original write/preservation behavior; the otherwise unused +28 low16 record field is loaded from file bytes, not falsely treated as preserved. PID bytes serve as opaque preservation payloads: this module does not claim to decode images or recreate source image-factory headers.

The hit ANIs' authored image path is `GAME_IMAGES_PLAYERHITBURST`, while the actual helper independently binds GAME_ENEMYHIT or GAME_CLAWHIT. Splash's authored image path is `LEVEL2_IMAGES_TARSPLASH`. Extracted Level1 has no LEVEL_SPLASH PID inventory. Its seven-image resolved manager is an explicitly synthetic success profile; the missing-manager profile also executes whole original retained animation and teardown. The archive's identity versus original v1.0 assets remains unknown.

The suite covers:

- State0/5, ordinary/negative/unknown states, all source rejection gates, stopped/current combinations, both style image sets, signed remainder selection, wraparound x/y and deletion flags.
- 800 seeded whole roots plus directed services that mutate cached source identities/positions and stop state.
- Complete allocator→metadata→sorted insertion→default image→named ANI initialization, missing metadata/images/ANI and first-frame paths.
- 32 retained actual ANI trajectories at delta1/17/18/60, idle delta0 calls, ordinary/both style selection and original generic teardown.
- Missing image/ANI and image-manager gap/restricted-range retained histories; eight multi-particle histories with12 actors each, equal/signed depth order, persistent RNG, moving source and source invalidation before natural completion.
- Four exact invalid-span failure prefixes and separate ABI/unsupported-address rejection.

Run `work/test-env/bin/python Tests/compare_impact_particle_runtime.py`. Final verification: **6,042 complete original calls, 2,913 ordered full-snapshot service events, 1,101 original instruction addresses, 2,150 original record-decode calls over 43 distinct actual ANI records, and four invalid-span prefixes**. Final counts and per-file hashes are `work/impact-particle-agent/verification.json`, with console log alongside. Run `work/impact-particle-agent/check-smoke.sh` for strict C11 header use, ASAN/UBSAN native controller/init/delete/no-op smoke and Swift import/null-source/null-scene paths. These are headless checks, not a simulator/device or full-game acceptance claim.

## Remaining boundaries

Original image/ANI/registry resolution and physical rendering/DirectDraw/audio transport remain declared services or frozen composed modules. This module owns no graphics or collision algorithms. Generic scene scheduling/list deletion and actual source-actor lifetime are composed by the native scene host. Unrelated impact/FX helpers beyond the four listed roots are not covered by this handoff. A complete-game identical-behavior claim still requires the parent project's remaining gameplay and platform boundaries.
