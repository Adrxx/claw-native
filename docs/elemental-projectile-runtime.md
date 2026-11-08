# Original elemental projectile controllers

`ElementalProjectileRuntime` recovers the retail FireBullet, LightningBullet, and IceBullet bodies. The original executable is `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Analysis used the worker's separate Ghidra project under `work/elemental-projectile-agent`; all recovery logs were checked for script errors. Original instructions remain unchanged in the differential oracle. Physical adapters intercept named boundary functions only.

| Family | Registered callback | Constructor | Vtable | Dispatcher | Class array | Flight |
| --- | --- | --- | --- | --- | --- | --- |
| FireBullet | 410100 | 410ec0 | 50b7bc | 411030 | 534ba0 | 411310 |
| LightningBullet | 4101c0 | 411370 | 50b80c | 4114e0 | 534a38 | 4117c0 |
| IceBullet | 410280 | 411820 | 50b844 | 411990 | 534b00 | 411c70 |

Each callback is 180 bytes, constructor 261 bytes, dispatcher 272 bytes, and flight body 82 bytes. Shared cleanup411cd0 is 18 bytes. These are verified function boundaries, not decompiled interior fragments.

Every family allocates **344 bytes /86 words**, directly inheriting Bullet4107c0. Magic410900 is a different derived family. The source Flare field is private+150; private+154 remains unwritten throughout these bodies. Preserve its input bytes. The exact vtable extent is **12 words /48 bytes**:

```
484d90 4c9e30 ownDispatch 4063b0 4741f0 4bb030
4bb030 4c96b0 411cd0 4dca10 474290 4bb030
```

The data after these 12 entries includes raw numeric constants, not additional virtual methods. The source class arrays initialized by401000 span IDs2000..2010, with only LS_FALLING bound here. The actual source LS_FALLING ID is **2001**. INIT4741f0→474290 sets that state; the class fallbacks compose frozen473f40/Projectile538428. The 119 shared state names use actual allocated CString identities; callers must not replace them with literal name addresses.

## Native integration

The public context, globals, rich call and dependency types alias the frozen `PlayerProjectileRuntime` types. Their sizes on this Mac are72,24,72 bytes respectively. Supply a live raw SceneActorHost and its Bullet/Generic views, actual actor/primary/private identities, source class/name tables, image roots/leaves, ANI records and static memory spans. The module borrows them; it does not own another scene or RNG.

- Registered cdecl callback: `entry(callback,0,{actor},1,...)`.
- Constructor: `entry(ctor,private,{actor},1,...)`.
- Dispatcher: `entry(dispatch,private,{state},1,...)`.
- Flight/cleanup: `entry(flightOr411cd0,private,nullptr,0,...)`.
- **Original4dc870 is cdecl(private)**: public receiver0 with one private-token argument. This module converts to the frozen internal private-receiver adapter itself.
- Inherited pre4c9e30/post4063b0 take one name-token argument; scalar delete484d90 takes one mode argument. Non-executable vtable data addresses are rejected.

Completion/support is separate from original meaningful EAX. Wrappers return1, constructors return the private token, flights return0, scheduler4dc870 returns1 and scalar delete returns the deleted token. Dispatch, pre/post, startup and cleanup have no claimed meaningful EAX. A missing span/service gives fault1, unchecked null allocation gives fault2, and invalid ABI/recursion gives fault3. Faults report a reached source prefix; they never claim successful gameplay.

A new wrapper first writes primary.state=1000, requests operator-new4f63ec(158), constructs, invokes private.virtual10, then publishes private at primary+18. It does not call the constructor at creation time from the scene factory. State29 invokes cleanup; state30 invokes4c96b0; state1000 skips; all other states use source4dc870. Do not replace this scheduling with a fixed timestep or impose a lifetime.

Constructors bind GAME_BULLETS through the base, then their actual image and ANI names:

| Family | Image literal/name | ANI literal/name |
| --- | --- | --- |
| Fire | 5241e4 GAME_PROJECTILES_FIRESWORD | 5241d4 GAME_FIRESWORD |
| Lightning | 524244 GAME_PROJECTILES_LIGHTNINGSWORD | 524230 GAME_LIGHTNINGSWORD |
| Ice | 5242a4 GAME_PROJECTILES_ICESWORD | 524294 GAME_ICESWORD |

All mark actor.flags80000. If global53724c==0 and actor-owner5371fc+124 is nonzero, they call4c8da0(container,0,x,y,z-1,Flare522e24,40000), store the returned actor at private150, and **do not immediately invoke its callback**. A null optional Flare is legal. The child constructor/tick/removal remain the existing Flare host's responsibility.

After frozen4742f0 updates animation and checks the prior source collision result, flight writes the child position. It uses these live immutable original doubles:

| Address | Raw words | Value |
| --- | --- | --- |
| 50b7f0 | 00000000 00000000 | 0 |
| 50b7f8 | 00000000 c0340000 | -20 |
| 50b800 | 00000000 40340000 | 20 |

For velocityX>0, X=ftol(positionX-(-20)); otherwise X=ftol(positionX-20). Negative/positive zero and unordered NaN use the latter branch. Y=ftol(positionY). Source captures the child token for X and rereads private150 for Y. The source CRT's53-bit precision and truncating integer conversion are retained. Ghidra omitted the arithmetic from its flight decompile, so the implementation and edge fixtures use actual assembly/original instruction evidence.

Cleanup marks the retained Flare actor.flags10000 and leaves private150 unchanged. Shared scalar delete writes private VT50b014 and optionally delegates CRT free. Full scene actor removal and the Flare lifecycle compose their frozen owners.

## Boundaries and measured coverage

The three vtables contain no specialized typed-hit body. Actor attack type/mask/damage/element fields are retained from source41cc60 and the Bullet base; scanner election and target CaptainClawHit/Human-hit callbacks remain the existing source interaction/target modules. The tests below prove source emission and flight/collision/deletion, not a newly substituted target damage implementation.

Explicit services include physical allocation/free; named Flare or projectile creation and list ownership; raw dictionary/name transport; LogicHit/LogicAttack binders; optional audio/effects; and out-of-range4db6e0 array growth/error transport. Successful own bodies compose frozen Bullet/Generic physics, PlayerProjectile scheduler, ActorAnimation and resource binding. No RNG is consumed by the owned elemental bodies. Current globals are clock537210, animationDelta5430c4, optional-child gates53724c/5371fc, and shared audio532c0c/532c10.

The oracle compares a complete1MiB actor/resource/registry arena plus every byte520000..54ffff (**1,245,184 bytes**) at call completion and each ordered service event. It compares meaningful original EAX separately. Resource transports normalize the original dictionary output-local pointer to the returned raw token and decoded name, consistent with the frozen resource API; binding/name events compare that name rather than a synthetic stack identity. All other receiver/argument packets remain ordered and exact. CPU stack/SEH bookkeeping and unrelated executable bytes are not claimed as gameplay state equality.

- Directed constructors, all wrapper branches, dispatcher/flight/cleanup/delete, mutable leaf callbacks, resource failure and optional-child gates.
- Actual source401000-derived registry heap identity profile; all11 initialized class cells and inherited fallback calls.
- Twelve retained retail PID/ANI paths (three families × two directions × two child gates), 65 frames each with unequal stage/animation deltas, followed by cleanup/delete. Actual retail Fire/Ice ANI each has6 records, Lightning4; none contains a sound-name event. Every asset path/hash/header is in `work/elemental-projectile-agent/verification.json`.
- Six whole original41cc60→explicit named-factory transport→deferred elemental startup→flight→cleanup/delete histories. Source25 damage, powered element flags, player weapon serial and signed±700 velocity remain intact. The factory is a declared raw-object transport profile; this test does not duplicate the separate scene creator proof.
- Six retained paths through actual original4cbb60 tile instructions versus frozen CollisionResponse/TileCollision, both directions, ending in source deletion flags. The tile cells/wall placement and empty scene-actor list are deterministic fixtures, not a claim of retail Level1 collision election.
- Directed NaN, out-of-int64 ranges, signed zero and positive/negative velocity for actual child-coordinate arithmetic.
- Three unchecked null-private allocation prefixes and three failed dynamic-growth/returning-diagnostics invalid-default-pointer prefixes. Source default+14 is token1; returning from diagnostic after growth failure reaches an invalid dereference. This is an explicit failing transport profile, not successful fallback or the complete physical error UI.

Reproduce with:

```
work/test-env/bin/python Tests/compare_elemental_projectile_runtime.py
work/test-env/bin/python work/elemental-projectile-agent/compile_replay.py
clang -std=c11 -Wall -Wextra -Werror -I Sources work/elemental-projectile-agent/abi.c -o work/elemental-projectile-agent/abi
swiftc -sanitize=address -import-objc-header Sources/ElementalProjectileRuntime.h -Xcc -I -Xcc Sources work/elemental-projectile-agent/abi.swift -L work/elemental-projectile-agent -lElementalProjectile -Xlinker -rpath -Xlinker "$PWD/work/elemental-projectile-agent" -o work/elemental-projectile-agent/swift-abi
work/elemental-projectile-agent/swift-abi
```

Final differential result: **2,124 complete original/native calls,2,661 paired full snapshots,2,385 executed instruction addresses and6 unsafe prefixes**.

The C++ASAN/UBSAN replay uses an independently allocated **exact86-word** private block, checks every lookup's extent, and replays33 complete source-matched calls/75 complete snapshots. It covers emitted-family constructor/startup, flight, cleanup, free and the actual cdecl scheduler for all three families. SwiftASAN verifies the imported raw ABI, borrowed actor/primary/private/child aliases, deferred callback, retained child cleanup and scalar free; it uses exact86 private words. Strict C11 and strict C++ warnings pass. These bounded checks do not establish whole-game or physical-renderer parity.
