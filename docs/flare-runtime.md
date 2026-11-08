# Original Flare and WolvingtonLFX

This additive module recovers both source light-effect callback facades, their19-word private object, initialization, named-state dispatch/controller, inherited queue/destruction, and the image-manager pointer setter reached by initialization. It preserves the original image effect selection. Rendering its physical indexed-color effect is a separate graphics boundary, not an invented opacity.

Original executable SHA256: `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Retail REZ SHA256: `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`. Evidence is unchanged-executable whole-call execution, bounded assembly, and private Ghidra output. No CrazyHook or reference gameplay implementation is used. `work/flare-agent/inventory.json` inventories all14 retail worlds and exact real asset hashes. Both names are absent among34,784 static WWD records; they are dynamic children. Exact retail-asset identity relative to all assets shipped with v1.0 remains a separate question.

## Stable raw ABI and source scope

`Sources/FlareRuntime.h` is C11. `ClawFlareContext` borrows a raw `ClawSceneActorHost`, `ClawActorAnimationGlobals` and `ClawGameImageGlobals`; it owns only composition flags, a bounded traversal limit and fault. The entry accepts original function/receiver/argument identities. Support return1 is separate from completion: fault must be0. Meaningful EAX is returned separately; incidental void EAX is normalized. Unknown identities return0. Checked fault1 missing graph/service and fault2 argument/bounded rejection are native safety extensions, not claimed original behavior on unsafe graphs.

| Original entry | ABI | Scope |
| --- | --- | --- |
|457f00|cdecl(actor)|Whole registered Flare wrapper; ordinal6/literal522e24/flags0|
|458010|cdecl(actor)|Whole WolvingtonLFX companion; ordinal7/literal522e14/flags0|
|458120|ECX private, actor arg RET4|Whole147-byte inlined base/derived constructor|
|4581c0|ECX private, no args|Whole95-byte virtual initializer|
|458280|ECX private, state arg RET4|Whole273-byte class-function dispatch/error/fallback body|
|458530|ECX private, no args|Whole64-byte LS_IDLE entry/reset; EAX0|
|458570|ECX private, no args|Whole23-byte ANI update controller; EAX0|
|4dc870|cdecl(private)|Frozen GenericEnemy FSM composition with exact raw name-array bookkeeping|
|4041b0|ECX private, unusedName arg RET4|Frozen whole queued callback restoration/transition body|
|484d90/456030|ECX private, deleteFlag RET4/no args|Frozen actual inherited deleting/base lifecycle|
|4c9e30/4c96b0/4bb030|ECX private, unusedName RET4/no args/no args|Verified source no-ops|
|4ce850|ECX image manager, pointer arg RET4|Whole73-byte compressed-image pointer setter and count return|

The allocation is0x4c/19 words. Base458120 stores50b064, private+8/+c actor, +10 cached primary, clears+4 and invokes LogicHit4c7fa0/LogicAttack4c8060 in source order. It clears queued fields14/18, sets1c=1001 and20=2; sets wrapper28/2c=actor and30=actor's fresh primary; then50e74c. Other words retain allocator seed.

Flare wrapper changes the vtable to50e6fc and binds/looks up `GAME_LIGHTFX_FLARE` literal5286e8. Companion458010 uses50e724 and `GAME_LIGHTFX_WOLVINGTONLFX`528720. Both store the resolved ANI at private48, invoke virtual+10 before storing the private token at cached primary+18, and return1. Allocation-null is unchecked after primary becomes1000; the suite stops before the bad dereference. State29 invokes virtual+20, state30 virtual+1c, state1000 skips, other states run the common FSM.

Each vtable contains exactly nine callable slots:
`484d90,4c9e30,458280,4041b0,4581c0,4bb030,4bb030,4c96b0,4c96b0`.
The following word at+24 is data516b90/516bd0 (and base50e74c has42c80000), not a movement callback. Do not use the264-word generic enemy destructor or4063b0 motion post. There is no recovered Flare physics, fuse, collision radius, TTL or self-deletion added by this module.

## Source ordering and live graph

Initialization caches the image manager from private2c→actor170, sets actorD0=1, applies manager effect2 through frozen PlayerPowerupRuntime4ce7b0 and frozen GameImageRuntime4c6130. It then copies the live owner768 pointer through4ce850. Zero pointer returns0 and leaves existing compressed-side1c unchanged. Nonzero pointer iterates signed manager64..68 image IDs, rechecks live bounds, dereferences manager14 image table, and writes compressed-image sideobject1c if both image and image30 are nonnull; count increments for each actual write. The manager is cached across4ce7b0, while app/owner/pointer are read afterward.

Initializer saves the current actor ANI into private34, selects private48 into actor188, then calls458530. That entry preserves primary state into private24, looks up LS_IDLE through537668, writes its returned ID into the primary, saves actor190 into private34 again, and selects private48 again. Consequently the final saved ANI is normally the newly selected sequence, not the pre-initialization ANI. This double selection and its order are verified rather than optimized away.

LS_IDLE is registered at original class table537ac0→458570 by the already frozen LogicStateRegistry bootstrap. IDs remain caller-owned original runtime identities. The suite's bootstrap profile resolves LS_IDLE to2000; the API does not hardcode an ID. Supply the live raw nine-word class table537ac0, ID-name CString array537698 and name trie537668. Growth/error/pending-CString/get-buffer ordering remains exact services4db6e0/4db5f0/4db4d0/4f6439/4f6974.

The controller reads animation delta5430c4 and advances actor188. The whole FSM composes the frozen scheduler, marshaling only19 private/109 actor/93 primary words. The unused generic portable tail is local and never committed. The frozen ANI helper uses128-word internal shadows; this module supplies a local padded shadow and commits only actual109 actor words, including at audio boundaries. It does not require a fake512-byte original actor allocation. No physical graphics or movement calls are hidden in the FSM.

The constructor does not create, position or delete the actor. Frozen PlayerProjectileRuntime source410900 creates Flare only if original magicDisabled53724c==0 and application+124!=0. Parent Falling updates its coordinates and parent state29 marks it for deletion. Wolvington's owned411cf0 creates its companion and412150 supplies position/mirror wrapper writes. Those projectile bodies stay owned by the separate modules; do not replace their source gate with a native setting or attach a guessed lifetime.

## Owner768 is a source palette-table token

Application+2c is the actual478-word single-player scene owner, not a separate alpha/config object. Frozen source construction428db6 and initializer46a783 initially zero owner768. The original level startup46aeb0 reaches46e160 at46b0e5. That routine checks owner4→app78==8, obtains app58 palette manager, clears owner768/76c/770, and tries `PALETTES_LIGHT`52a09c with type434c54 (`CLT`) through4b7dc0(owner1c,...). If locked4b61c0 data exists,4c7360(paletteManager,bytes,resource14 length) produces the token stored at46e1c8. If absent,4c68e0(paletteManager,owner360 palette,256,400,1,16) generates the token stored at46e1f7. Cleanup46b7b0 passes the nonzero token to4c7510 and zeros it at46b7ea.

Therefore zero is a verified constructor store but does not prove completed8-bit level palette setup. Flare's source4ce850 installs this pointer into compressed1c, overriding the default effect table selected by4c6130 if nonzero. The source table load/generation/destruction graph is not recovered by this module; native physical image/palette transport must retain that explicit boundary. Do not call the token opacity or infer a blend formula from the callback name.

## Composition and explicit boundaries

Composition flags default1. Animation1 uses frozen ActorAnimationRuntime;0 exposes exact4c8220/4c82a0 calls. FSM1 composes frozen GenericEnemy tick plus real raw name-table bookkeeping;0 exports4dc870. Effects1 composes frozen whole4ce7b0 and4c6130;0 exposes those exact services. Whole4ce850 remains native in both profiles.

Resources4c7970/4f6286, secondary/contact binding4c7fa0/4c8060, registry name lookup4dba00/growth/error/CString, allocation/free and physical ANI audio remain explicit exact-address services. The normalized resource lookup returns the token and adapts the original writable stack-local out pointer; it does not implement a new resource format. No physical PID raster/render equivalence is claimed from controller tests or metadata fixture loading. Existing frozen GameImage/renderer/PID modules and physical effect lookup must supply it.

Tests use the actual real GAME Flare and WolvingtonLFX ANI/PID bytes as input adapters. The ANI records are also decoded by the unchanged original4d76e0 and compared to frozen native decode. PID header fields and the actual one-frame image identity are metadata fixtures; this is not a claim that Python executed the original full resource loader. Source asset hashes and decoded input boundaries are retained in inventory.json.

## Verification

`work/test-env/bin/python Tests/compare_flare_runtime.py` compares complete1MiB seeded heap and320KiB original image/global view, ordered callback snapshots, meaningful EAX and real cdecl/RET argument behavior against the unchanged original bodies. Coverage includes both facades, constructor/init/double selection, common class/name lookup, retained real resource frames, empty/missing sequence, pointer-zero/missing-frame/range branches, queued callbacks, aliases, inherited no-ops/deletion and stopped allocation-null prefixes. Registry/table transport profiles and source exception prefixes are labeled; arbitrary mutated vtables/unsafe graphs are not whole-game parity claims.

Final evidence is4,774 paired whole-call comparisons,9,399 paired ordered full snapshots,715 original instruction addresses,2,880 retained real resource frames,18 source-decoded ANI records and two stopped allocation-null prefixes. `work/flare-agent/verification.json` and `verify.log` retain these measured counts. `work/flare-agent/smoke.py` checks strictC11 and standalone Swift import/link, then ASAN/UBSAN with200 source-shaped constructor→180-frame→deletion histories. Actor109/private19/image/manager/compressed allocations are distinct and exactly sized, so shadow tail access cannot silently spill into adjacent fields. Native scene routing, builds and Mac/iPad acceptance remain coordinator-owned.
