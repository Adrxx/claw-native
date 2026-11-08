# Original scenery callbacks

SceneryLogicRuntime recovers the largest remaining Level1 scenery family from
the verified original v1.0 registration table. The original compressed WWD has
1,479 records, of which594 belong to these callbacks. This module does not use
the legacy CrazyHook SimpleAnimation implementation or change its files.

| Registered name | Original callback | Level1 records | Default z |
|---|---|---|---|
| BehindAniCandy | `461970` |485 |990 |
| DoNothing | `461730` |58 |none |
| FrontCandy | `461770` |35 |5100 |
| BehindCandy | `4617d0` |15 |990 |
| FrontAniCandy | `4618e0` |1 |5100 |
| DoNothingNormal | `461750` |0 |none |
| GooCoverup | `461830` |0 |8010 |
| GooBubble | `461870` |0 |8000 |

The eight exact entry boundaries were independently decompiled in a private
Ghidra project and checked against original instructions:19,19,85,85,62,111,
138 and138 bytes in the table's underlying address order. Private evidence is
`work/scenery-logic-agent/callbacks.c` and its verified log.

## Native ABI and order

`claw_scenery_logic_entry` takes a function identity, actor token, mutable
ClawSceneryLogicContext and result pointer. The original registered callbacks
are cdecl and receive actor as one stack argument; the native actorToken is
that argument, not an x86 ECX receiver. Successful callbacks return EAX1,
except DoNothingNormal, which returns2. Native support/completion and original
EAX remain separate. Actor+6c supplies the primary93-word logic buffer.

DoNothing and DoNothingNormal always OR actor+8 with1, regardless of primary
state. Other variants initialize only when primary+1c is zero: OR actor flags
with1, set primary state5, select default ANI for animated variants if
actor+190 is null, and then apply default z if actor+64 is zero. Default z
selection also ORs actor flags with20000, scheduling the recovered reorder
path. Existing z values, including negative/wrapping values, are preserved.

Animated variants use exact name token5240d8, `GAME_CYCLE100`, through original
4c79e0(actor,name,eager0). They preserve an already bound ANI. This first
selection does not consume an animation update. On every nonzero primary
state, including states other than5, animated variants call4c82a0(actor+188,
animationDelta). Static variants perform no further writes on nonzero state.
The new bodies compose frozen ActorAnimationRuntime when composeAnimation is
nonzero; otherwise those calls are explicit SceneActorHost services.

Front/Behind Candy variants read raw settings+124 after resource lookup and z
handling. If zero, they OR actor flags with10000. Frozen SceneActorRuntime
interprets10000 as deferred deletion, not merely hidden drawing. Goo variants
do not read this setting. The context.settingsToken represents original
global5371fc. Frozen SinglePlayerSceneRuntime's application constructor sets
manager+124 to1; supplying the source-created manager preserves this default.
This does not prove the entire retail settings/startup graph.

The context carries the frozen animation globals. animationDelta is5430c4,
distinct from stage53720c. The historical field `audioPosition` corresponds
to overall volume532c10, not a position or clock; its stable type is unchanged.
Lookup/audio service mutations occur at their exact callback snapshots. Tests
also change actor z, flags, logic state and settings during lookup, proving
that later decisions reread those fields in the original order.

## Resources, allocation and deletion

The callback bodies allocate no actor/private/animation objects and perform
no direct deletion. Generic actor/primary construction, image binding, named
ANI lookup, scene insertion/reordering and deferred destruction retain their
existing source module ownership. Parent integration should route these
function identities through this module on live actor/logic heap buffers;
then retain the scene's existing scheduling and destruction lifecycle.

SceneActorHost.lookup provides aligned raw-word spans. The new module handles
unaligned four-byte accesses through byte offsets and memcpy. Missing spans
produce native fault1; missing explicit animation services produce fault1;
unsupported delegated animation metadata can produce fault2. Frozen
ActorAnimation's documented fault3 for reentrant audio mutation propagates.
These are native bounded diagnostics, not substituted original return values.
Unknown callback identities return unsupported without executing a stand-in.

4f6286 resource resolution and physical4c88e0/4208e0 audio remain explicit
services. Image namespace, filename-to-ID enumeration, aliases, PID physical
surface allocation and raster presentation are not reimplemented here.
The tests use caller-owned image tables and original ANI/PID bytes from the
fingerprinted REZ; they do not claim equivalence of that entire resource loader.

Specific source-data boundaries found during actual Level1 enumeration:

- Twelve Candy records use `LEVEL_SKULL`; its single file is `SKULL.PID`,
  without a numeric suffix. Tests declare fixture ID0 and label retail ID
  enumeration unproved. The current shared native image adapter's suffix-only
  policy needs separate source recovery before claiming that resource mapping.
- Two records request `LEVEL_CANDELABRASINGLE`; the original REZ contains no
  CANDE entries. Tests exercise a missing lookup, clearing the actor image root
  and preserving previous image ID/token. Actual GAME_CYCLE100 control0 can
  still update with no image root; no placeholder pixels are supplied.
- Nineteen `LEVEL_MANICALS_MANICAL` and one `LEVEL_HAND_HAND1` requests are
  tested with explicit registry profiles resolving original MANICLES/MANICAL
  and HAND/HAND1 ANI bytes. Their namespace/alias registration is a service
  profile, not recovered retail alias evidence. The two `LEVEL_MANICALS_M`
  requests have no matching M ANI and use the explicit missing/fallback profile.

## Verification scope

Executable SHA256:
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Original REZ SHA256:
`b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.
Run `work/test-env/bin/python Tests/compare_scenery_logic_runtime.py`.

Every complete callback/composed image-binding/ANI/destruction call compares
the full64KiB persistent raw heap, explicit animation globals, ordered external
service arguments and full-heap snapshots. Registered callback EAX and exact
cdecl stack pop are checked. The synthetic suite covers all eight functions,
arbitrary nonzero states, settings values, existing/null ANI, explicit/default
z, resource lookup failures, delay/rate/control fields and lookup mutations.
Composition-disabled tests preserve actual callee identities and arguments
rather than pretending their body executed.

All594 actual Level1 profiles retain source-initialized actors through source
image binding, named/default ANI,12 scenery ticks and recovered4c9be0 deletion.
The suite decodes the actual ANI records through both native and original
4d76e0 and records hashes of the selected actual PID byte resources. Image IDs
and namespace aliases are explicitly profiled above; pixels are opaque to the
callback/animation control flow. It does not claim a whole WWD loader replay,
raw PID raster comparison or physical presentation proof in this module.

Constructor proof executes complete original4c98c0 with its three arguments,
then actual inline derived stores4d18a7…4d1905 from4d17e0, and complete
initializer4c9d40, comparing full persistent heap against frozen WorldObject
bodies. This is a bounded constructor caller profile, not a claim that the base
ctor contains derived fields or that this test executed the entire4d17e0.
4f63ec's0x174 primary allocation is a declared physical allocation outcome,
including null profiles; callback bodies themselves request no allocation.
Deletion composes frozen ActorDestruction; physical4f6428 free is adapted and
freed bytes stay readable for comparison. Temporary original stack identities
and physical allocator implementation are outside persistent heap equivalence.

Exact measured totals are stored in private `verification.json`. A standalone
ASAN/UBSAN runner replays complete original-verified before/after heaps and
globals for every callback and representative retained/alias/service cases:
`bash work/scenery-logic-agent/check-sanitizer.sh` after the oracle. The C11
header also passes independent syntax compilation. This bounded recovery does
not establish full-game or retail application equivalence.

Final verified totals:12,975 complete callback/composed calls;1,242 bounded
constructor/caller/initializer profiles;2,583 ordered persistent-heap service
snapshots;1,167 original instruction addresses;716 original record decodes;
7,128 retained actual-record ticks. ASAN/UBSAN passed326 complete-heap/global
replays. C11 header syntax compilation and `git diff --check` passed.
