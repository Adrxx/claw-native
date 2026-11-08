# Original stacked-parent lifetime and callback restoration

`Sources/StackedActorLifecycleRuntime.h/.cpp` recovers seven complete bounded entries from the original v1.0 executable, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. It is an additive C11 raw-token interface using the frozen `ClawSceneActorHost`. The recovered stack allocation is **76 bytes /19 words**, not a generic enemy's264-word portable buffer. Existing frozen BreakableObjectRuntime owns the three stack constructors; this module does not duplicate them.

The complete original bodies and disassembly evidence are captured under `work/stacked-actor-lifecycle-agent/`. Source cleanup does not traverse spawned crate siblings, invent child ownership, destroy strings, or invoke the queued callbacks from the destructor. The source routines below preserve every other allocation word.

## Stable API and caller ABI

`claw_stacked_actor_lifecycle_entry(function,receiver,args,count,context,result)` returns native support/completion separately from meaningful original EAX. Every raw pointer is a32-bit token. Context contains `ClawSceneActorHost scene` and `fault`; each entry resets fault. A dependency can signal a missing body through that context before returning; later source writes stop. Fault1 is a native missing-span/service boundary, fault2 a native caller-ABI rejection. Unsupported function returns0 without fault. These native safety extensions are not original successful returns.

| Entry | Actual source stack arguments | Result and body |
| --- | --- | --- |
|484d90 | deleteFlag; thiscall RET4 | Calls456030, tests **low flag byte bit0**, optionally CRT4f6428(receiver), returns receiver |
|456030 | none; RET | Only writes private word0=50b014 |
|4041b0 | unusedMap; RET4 | Deferred cleanup/transition sequence below |
|4041a0 | unusedMap; RET4 | Calls cdecl CRT4a36f0(receiver), discards result |
|4c96b0 | none; RET | True no-op; no receiver read |
|4c9e30 | unusedMap; RET4 | True no-op; no receiver read |
|4bb030 | none; RET | Returns EAX0; no receiver read |

Void entries expose result0; incidental register contents are not treated as gameplay results. Allocation/free and Windows exception transport remain explicit host services. The portable routine requests individual1-word spans in source order; it never requests264 words for the private object. Lookup must support interior tokens and original immutable vtable data when composing surrounding actor/logic destruction.

Original front/back/base vtables50f824/50f84c/50f874 and CUserLogic50b064 share nine actual callable slots: deleting484d90,+4=4c9e30,+8=4041a0,+c=4041b0,+10=4c96b0,+14/+18=4bb030,+1c/+20=4c96b0. The word after+20 belongs to following metadata, not a tenth method.

## Exact deferred callback order

4041b0 reads private+14 (queued transition) first. Zero returns immediately, even if private+18 contains cleanup. With a queued transition:

1. Cache cleanup+18. If nonzero, read primary token+10, that primary's state+1c, then private expected state+1c.
2. Only equal states invoke the cached cleanup identity with **ECX=private token and zero stack arguments**. After it returns, clear private+18. A cleanup callback that replaces+18 has that replacement cleared.
3. Fetch the **current** private+14 after cleanup, invoke that identity with the same receiver and zero stack args, then clear private+14 and set private+1c=1001 after it returns. Replaced queued functions are therefore observed; changes made by the transition to+14/+1c are overwritten.

If the state mismatches, cleanup is retained while the transition still executes. The destructor does not execute this restoration method. There is no post-call virtual movement function here; frozen generic enemy4063b0 has that additional step, whereas4041b0 ends after these writes.

Callbacks may replace primary tokens, alias primary-state storage with private fields, and mutate queued functions. Tests preserve exact observations of those writes. A callback that frees its own object before outer writes is compared only using an explicitly retained arena; this demonstrates the source write order after free, not permission to reuse/dereference physically freed storage. A cleanup that clears the queued pointer produces an original jump to0; the native bridge can stop at that missing-body prefix rather than invent success.

## RTTI correction

4041a0 is not an unconditional fatal routine. Its only callee4a36f0 reads receiver's vtable[-1] locator, then locator+c type descriptor, calls Windows `IsBadReadPtr(descriptor,8)`, and returns the descriptor on the normal branch. Its null/invalid-pointer branches construct and throw CRT exceptions. Exception handling and this helper remain explicit services in the public API; no guessed crash is introduced.

A separate unchanged-original probe executes4041a0 and4a36f0 through the normal Windows pointer-test adapter for all four source classes:

| Vtable | Locator | Type descriptor | Original RTTI name |
| --- | --- | --- | --- |
|50f824 |5177b0 |52c5d0 |`.?AVCFrontStackedCrates@@` |
|50f84c |517808 |52c5f8 |`.?AVCBackStackedCrates@@` |
|50f874 |517848 |52c5b0 |`.?AVCStackedCrates@@` |
|50b064 |5145d8 |523120 |`.?AVCUserLogic@@` |

The native callback receives `{function:4a36f0,receiver:0,args:[privateToken],count:1}`. A normal complete service can return the descriptor;4041a0 ignores it. The exception branch is an identified CRT/Windows boundary, not a recovered native exception implementation.

## Native integration recipe

Retain the actual19-word parent allocation created by frozen48d560/48d620/48d6e0, whose primary common logic+18 owns the private token. Route **484d90** for that token into this additive API rather than copy it into a generic enemy264-word snapshot. Frozen ActorDestruction's4c80e0 reads the actual private vtable slot0 and calls it with deleteFlag1; after the nested delete returns, it clears common logic+18 and continues its actual base stores. Frozen actor destruction supplies the actual actor/common-logic virtual order and CRT frees. The test composes those whole source bodies unchanged.

For the19-word parent, source delete only changes VT50b014 and optionally frees that token. It leaves its actor/logic/embedded wrapper/queued function/created-child count fields untouched; it does not recursively delete already-created Crate actors. Those children are separately scene-owned objects with their distinct262-word private graph and frozen crate destructor. Do not apply this parent destructor to arbitrary crate or keg private types.

Route4041b0,4041a0 and actual no-op slots through their exact arity above. Queue callbacks are exact identities and remain explicit services unless an existing verified module owns them. No timer, fade, animation, audio or RNG call is invented by this lifetime layer.

## Verification

Run:

```sh
work/test-env/bin/python Tests/compare_stacked_actor_lifecycle_runtime.py
work/test-env/bin/python work/stacked-actor-lifecycle-agent/probe-rtti.py
work/stacked-actor-lifecycle-agent/check-smoke.sh
```

The main differential suite compares complete1MiB caller heap,192KiB original mutable globals, exact ordered callbacks/free snapshots, lifetime maps and meaningful EAX against unchanged original instructions. Directed/matrix cases cover all deleting low-bit profiles, actual front/back/base vtables, empty/mismatching/equal queued states, callback replacement, primary-pointer replacement, aliased fields, retained callback self/other destruction, whole actor→logic→private deletion, and three failure prefixes. Source no-ops are also run with an invalid receiver to verify no hidden read.

All22 actual Level1 stack WWD records are decoded from the fingerprinted legacy-rip archive and sent through frozen source constructor wrappers, then retained post-restoration and primary-logic deletion. Private constructor-test scaffolding reuses the frozen breakable oracle's explicitly declared child-init/scene/binder service profile; those adapted dependencies are not counted as recovery of crate gameplay. Their complete constructor heap/service observations are compared separately. The original asset-version identity remains unproved.

Final counts: **2,611 complete lifecycle/surrounding original calls /2,920 ordered full snapshots**, plus **22 composed original constructor calls /178 snapshots**, over **550 distinct original-image instruction addresses**. All22 records and **three invalid-span/callback prefixes** pass. Separate RTTI probing makes eight actual original entry calls. Warning-clean C++ builds, C11 exact19-word/mutated-callback smoke under ASAN/UBSAN, and Swift C11-import smoke pass. These bounded results do not establish whole-game equivalence or native device acceptance.
