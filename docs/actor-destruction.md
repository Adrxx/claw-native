# Original actor and logic destruction

`Sources/ActorDestruction.h/.cpp` recover bounded complete lifecycle entries from original v1.0 `CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Recovery uses original instruction bodies and disassembly, not a source-port gameplay implementation. The raw-token C11 interface accepts the existing `ClawSceneActorHost`, so scene integration can preserve actual heap object and interior identities without another portable actor layout.

## Stable API and ownership

`claw_actor_destruction_entry(function, receiver, argument, globals, host, fault, result)` invokes a known original body. Support/completion is separate from meaningful original EAX. Deleting destructors return the receiver identity even after freeing it. Void incidental EAX is not a gameplay output. `claw_actor_destroy` selects the actual actor vtable+4 rather than assuming a generic scene actor. Missing spans/services set native fault1; this bounded safety extension does not claim original malformed-heap behavior.

Globals supply holder actor53c9ac, held token53c9b0, and original shared empty CString data identity. `host.lookup` must return stable mutable spans, including interiors. `host.free` replaces CRT4f6428; the real allocator's physical free-list behavior is an explicit host boundary. Unknown private/actor destructor slots invoke `host.call` with the actual function, receiver and delete flag. RatBomb `484d90` is delegated to its frozen `RatBombLogic` API, with its original92-word private allocation; its body is not duplicated here.

| Original entry | Native body |
|---|---|
| `4c9be0`, `4c9c00` | Generic actor deleting destructor and complete derived/base teardown |
| `4c9e60`, `4c9e80` | Plain actor deleting destructor and complete derived/base teardown |
| `4c99a0`, `4c99c0` | Base actor deleting destructor and complete base teardown |
| `4c9a70` | Logic-pointer cleanup/reset used independently of destruction |
| `4c80c0`, `4c80e0` | Generic93-word logic deleting destructor and complete cleanup |
| `4c9b30`, `4c9b50`, `4c8210` | Animation deleting destructor/cleanup and three-word animation reset |
| `47cc80`, `47cca0` | Rat deleting destructor and complete bitset/CString/base teardown |
| `4dbcd0` | Bitset destructor stores/backing release and handler unregister call |
| `4f6584` | CString reference release, shared-empty bypass and conditional free |
| `48cf50` | Conditional player-held-object reference cleanup |

All deleting methods test bit0 of the low argument byte. Other bits do not imply additional freeing. This module does not invent resource deletion: actor image/runtime references170/174 are cleared, with no image-owner destructor in the original body.

## Actual callback order and preserved fields

Generic actor4c9c00 first installs5137f0, sets168/16c to−1, and clears170/174. It then deletes primary+6c, secondary+70, contact+78 in that order through **logic vtable+4**, passing1. Each actor pointer is zeroed **after** its callback. Actor geometry/sentinel fields reset, then the embedded animation188 enters513870, clears only animation+4/+8/+c, and becomes50becc. The inlined base phase installs513770 and repeats the three logic pointer checks. A later callback can rebind an earlier actor pointer, making this second pass observable. Final base sentinel stores clear actor+8/+c, set ID+4 to−1 and install50becc; unrelated words remain unchanged.

Plain actor4c9e80 installs5137b0, cleans primary/secondary/contact logic in order, resets its geometry and enters the same base phase with the observable repeated logic checks. It preserves animated-only image and animation fields beyond its actual0x168 allocation; the native128-word snapshot padding remains unchanged. The complete plain deleting/body entries add360 whole original calls to the comparison suite.

Logic4c80e0 installs513740 and clears callback+10. Nonzero raw private+14 is freed through CRT; the field is zeroed after that service. Nonzero polymorphic private+18 instead calls **private vtable+0** with1, then clears the field. It finally clears+8/+c, sets ID+4 to−1 and becomes50becc. Raw private and polymorphic private are distinct ownership routes; no deduplication or alias guard was added.

Rat47cca0 installs50b16c, destroys bitset+2f4, then CString+1a8, then CString+1a4, and finally becomes50b014. The bitset destructor installs513e34; sizes>32 release backing+0xc via `4a49b0`; then it installs513e28 and calls `4dc560(handlerAt+4, bitsetToken, 0)`. The handler/core registration list remains an explicit service. Its global544d18=0/remove-mode0 path returns0 without dereferencing the handler; a populated registration list must not be replaced with that empty-profile behavior.

CString4f6584 compares data−12 against the original shared empty header identity. Other strings decrement the32-bit reference word and free the header through CRT when the **signed** result≤0. It leaves the CString cell pointing at its previous data; no invented clearing store is added. The native single-thread game-thread decrement adapts the original OS InterlockedDecrement operation. Registry string assignment remains owned by `LogicStateRegistry`; no registry source was edited.

`48cf50` is **not** a scene-delete request. If holder53c9ac exists, the supplied token equals held53c9b0, the holder has primary logic, and primary state+1c=15, it clears primary+130 and global53c9b0. Other cases preserve both. Actor deletion flags, list removal and deferred scheduler ordering remain in frozen `SceneActorRuntime`. There are no direct clock reads or wait operations in the recovered destructor bodies.

## Verification

Run:

```sh
work/test-env/bin/python Tests/compare_actor_destruction.py
clang -std=c11 -Wall -Wextra -Werror -I Sources -fsyntax-only work/actor-destruction-agent/header-check.c
```

The optimized C++ suite (`-O2 -Wall -Wextra -Werror -ffp-contract=off`) passes **3,610 complete original calls, 11,742 ordered raw-heap events, 729 distinct original instruction addresses**. Every call and event compares the full65,536-byte heap, including complete actor128/logic93/Rat264/Bomb92 regions, unrelated seeded words and surrounding guards; holder globals; allocation/free ownership records; and the restored original SEH head. No state-buffer normalization hides preserved words. Fixture allocator services record ownership and retain released bytes for observation; their physical allocation policy is not claimed to match CRT.

Coverage includes null/all-present logic pointers, both raw and polymorphic private paths, Rat and frozen native RatBomb private destruction, exact callback/free order, original empty/nonempty CString identities, positive/shared/negative references, inline/larger bitsets, zero/nonzero deleting flags and upper-byte flags, dynamic callback mutations, rebinds that require the second base actor cleanup pass, and missing held-object predicates. Unknown polymorphic callbacks are controlled explicit service adapters with complete before-call heap snapshots.

150 retained raw-buffer chains keep the actor allocation alive during initial cleanup, compare the subsequent empty-buffer teardown, then restore the generic actor vtable fixture and delete the actor. These are instruction-state chains; no complete respawn lifecycle is inferred from them. **100 joined deferred scene deletions** execute actual original4c8fc0 and native frozen SceneActorRuntime with this module, comparing deletion-array changes, node/pool release, final actor/logic/private frees, preserved timing words and whole heap. Their gameplay callback is a controlled adapter; they establish actual scene→destructor composition, not Rat/Bomb gameplay callback equivalence. Native RatBomb destructor is composed through its frozen entry API in these graphs.

The public header passes C11 syntax and fixed shared ABI shape checks. No Xcode/device/UI run was performed. Evidence is `work/actor-destruction-agent/verification.json`. Unknown private/resource destructors, populated core handler registration lists, CRT allocation internals and whole-game respawn scheduling remain explicit host boundaries rather than fabricated bodies.
