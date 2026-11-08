# Native points and glitter host

`Sources/ClawNativeEffects.swift` is an additive native bridge for the frozen source PointsIcon/GlitterMother/GlitterBaby/PowerupGlitter bodies. It uses the existing scene token heap and actual actor image/ANI resources. It has no independent actor state cache, game timer, RNG stream, velocity, fade or TTL. The original-instruction proofs remain in `pickup-points-runtime.md` and `glitter-logic.md`; this document describes the separately verified Swift composition.

## Root hooks

Construct `ClawNativeEffects(scene:resources:managerToken:)` after scene/resources/application initialization. The default manager token comes from the scene owner+4; the public token is the original5371fc alias and must be updated if the application manager changes. Optional `frameClock` supplies animation delta/audio global; otherwise it uses scene.animationDelta and shared audio masterVolume.

The owned `actors` map contains `ClawNativeEffect` components with tick/callback/refresh/flush/snapshot. `onCreated` registers a component with Root; it must not eagerly tick it. Register callbacks473a70/448440/4485a0/470110 in the shared scene dispatcher, forwarding `(actorToken,function)` to `callback`. Generic source scene scheduling controls primary+20/+24 and deferred deletion; do not add an independent15ms Mother scheduler.

- `service(_ call: ClawPlayerPowerupCall) -> UInt32?` handles the exact rich six-argument4c8da0 named effect creation forwarded by the frozen powerup setter. It executes the source named creator directly and does not recursively run448400 again. Nil means unsupported scope; zero is a legitimate missing/failed creation result.
- `itemService(_ call: ClawItemPickupCall) -> UInt32?` handles4737c0 and the ordinary PowerupGlitter named creator. Ordinary pickup award/player write-back remains Root's existing responsibility.
- `points(item:) -> Bool` executes whole frozen4737c0, including live score/frame selection. A normal missing named actor is still a completed wrapper; the Bool is native coverage/diagnostic, not original void EAX.
- `mother(owner:) -> UInt32` executes frozen448400 for a direct caller that has not already entered the wrapper. Its temporary powerup globals are unused by this wrapper; it does not create a separate powerup state.
- `attach(token:)`, `remove(_:)`, and `onRemoved` manage component ownership. They do not insert/unlink scene nodes or deallocate gameplay storage by themselves.
- `receiverLifecycle(_ call: ClawSceneActorCall) -> UInt32?` handles owned generic deleting entry4c9be0 through frozenActorDestruction. Route this before Root's generic fallback when using it; do not execute both. Alternatively let Root's existing generic destructor run and call `effects.remove(token)` when it frees the actor. Root's backing scene host does not run this proxy's free hook automatically.

`actorHost` is the owned creation/ANI/heap proxy, available for finite source scene composition. Root's ordinary scene lifecycle can keep its current host and invoke the hooks above.

## Live creation and resources

The proxy retains named lookup events with original literal identities522874/5225a0/522594/522950. It resolves them through public `scene.entry(named:)`; no Root-private namesByToken dictionary or direct metadata shortcut is used. GAME_POINTS has both image and ANI resources, so its registry receiver selects the correct domain. GAME_GLITTER/GAME_SPARKLE and GAME_CYCLE100/GAME_GLITTER1 use their actual source namespaces and the existing resource path adapter.

Actor1b4 allocations are tracked as pending. The creator initializes the primary, links the scene node, and stores actor+68. On the next proxy lookup, registration occurs only after the node's actor identity matches and the primary callback is supported. Thus the internally composed immediate GlitterBaby callback starts with a registered component at state0. The onCreated snapshot is a view of a suspended source call: registering/render bookkeeping is appropriate; mutating/ticking it would change source behavior.

Controller stores commit directly to raw heap spans. Owner identity remains primary+170; the powerup's actor pointer remains player private+130. Raw player/private export/import stays in RootPlayerServices. Shared RNG routes to scene.nextRandom. Audio routes to existing shared native audio services; missing audio remains absent and the smoke test does not activate playback. Resource directory enumeration/PID palette selection and physical sound/render services remain existing native adapters.

The source generic constructor applies its metadata flag rules in addition to caller flags. In particular, Mother callerflags0 is preserved and no40000 flag is forced; its resulting raw flags can include the recovered800000 metadata bit. Mother has no inferred owner-liveness cleanup. Source powerup expiry/reset marks it Delete and the scene scheduler performs removal.

`allocationAllowed` is an explicit test/host allocation boundary. `fault`/`failure` report native bounded rejection; original null allocations fault after observable prefixes. `resetDiagnostic` clears those diagnostics without rolling back source heap effects or freeing a partially constructed object. Pending failed objects stay unregistered, matching the pre-fault ownership prefix. Unknown services enter `unresolved` and produce a diagnostic unless an explicit externalService supplies them. `events` captures service arguments/order, while allocations/freed record allocator requests (including zero free requests).

## Native verification

Run `CLAW_NATIVE_ASAN=1 zsh work/native-effects-agent/check-native-effects.sh`. This private script compiles the full Swift/C++ graph with AddressSanitizer, including current NativeWorld/Respawn/PlayerServices and powerup/death/world modules, without Xcode or devices. Final smoke passed with **155 ordered service events,60 allocator requests and68 free requests**. These counts exclude physical image/ANI registry allocations made by the shared resources object.

The test uses actual Level1 world/player/resource initialization. Ten score mappings create actual Points actors, bind real GAME_POINTS frame/ANI tables, reach source Delete, and execute original scene node removal plus generic primary/actor destruction. One/two Baby emission checks retain actual owner, depth, shared RNG and creation flags; onCreated sees every Baby at state0 before its immediate source startup sets5. Three Babies complete actual GLITTER1 ANI and source removal. A separate generic scheduler check subtracts14ms from the source15ms countdown, then1ms invokes Mother and resets it to15.

Ordinary PowerupGlitter exercises rich item creation, real GAME_GLITTER images, CYCLE100 ANI, depth/reorder, random delay and30 retained visits without invented self-deletion. Frozen Catnip setter41f990 creates Mother through the rich service, writes the actual private+130 identity, then41fc30 expiry and a later setter reset mark each Mother Delete and clear that private field. Original deferred scene destruction removes them. Actor and primary allocation failures verify native diagnostics and unregistered partial construction under ASAN; their original instruction fault prefixes are covered by the frozen C suites.

For the isolated source-scene sweeps, unrelated player/camera/enemy callbacks and process-exit registration use an explicit return0 test service. A frame-counter fixture defers the unrelated Mother while individual elected Baby destructors are checked; the separate14+1 timer test executes the real generic timer. These are declared isolation inputs, not substituted gameplay claims. Catnip globals are explicit test-owned aliases passed into the frozen setter; Root retains the real production global/write-back integration. No whole ordinary frame, rendering screenshot, sound playback, device acceptance or complete game-equivalence claim follows from this test.
