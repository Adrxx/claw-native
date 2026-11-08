# Original actor image, secondary and contact logic binding

`Sources/ActorResourceBindings.h/.cpp` recovers original v1.0 image helpers **0x4c7900 / 0x4c7970**, secondary generic logic binder **0x4c7f20 / 0x4c7fa0**, reset **0x4c81b0**, and the shared generic logic constructor/initializer stores. It establishes actor/secondary buffer writes and dependency ordering, not resource loading, image decoding, actual heap allocation/destruction or gameplay callback execution.

Profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Field stores and branches are recovered from original instructions. No CrazyHook or reference gameplay implementation is copied. The active native resource files now match the separately obtained original disc byte-for-byte; see original-disc-provenance.json.

Starting evidence was read without editing `work/player-init-agent/initialization-helpers.c` and `work/v10-disassembly.txt`. Additional bounded Ghidra output is private `work/actor-bindings-agent/binders.c`, in a separately cloned project.

## Stable API

Runtime is `ClawActorResourceBindings { actor[128], secondary[93] }`. All words are uint32, with original pointer fields treated as opaque identities. The second buffer represents **actor +0x70 secondary logic** for secondary APIs, or **actor +0x78 contact logic** for contact APIs. It never represents primary logic +0x6c or a sound handle. Allocation seeds remain caller-owned; every word without an original store is preserved.

Context contains image/logic registry identities, resolved image table, metadata identity/callback/flags and an associated-resource virtual destructor identity. API functions are:

```c
uint32_t claw_actor_bind_indexed_image(state, context, name, imageID, dependency, user);
uint32_t claw_actor_bind_default_image(state, context, name, dependency, user);
uint32_t claw_actor_bind_secondary_logic(state, context, dependency, user);
uint32_t claw_actor_bind_secondary_logic_name(state, context, name, dependency, user);
uint32_t claw_actor_bind_contact_logic(state, context, dependency, user);
uint32_t claw_actor_bind_contact_logic_name(state, context, name, dependency, user);
void claw_actor_reset_secondary_logic(state, context, dependency, user);
```

For image helpers, return one means the recovered field update completed; original entries are void and no claim is made that their incidental EAX value equals this native safety status. Return zero denotes native invalid input/table safety rejection. Secondary bind functions return the original zero/one binder result. Failure after secondary allocation/reset **does not roll back stores**, matching the original.

Image context has `token, minimum, maximum, firstImageIndex, images, imageCount`. `images` is a bounded array whose first element represents the signed logical `firstImageIndex`, allowing the original absolute-ID indexing even for negative IDs. The native range check uses the original signed resource minimum/maximum. Null or out-of-view table access is rejected before image-field writes. A lookup dependency can still have side effects before such rejection; no whole-callback transaction is claimed.

Existing actor +0x70 must identify this secondary buffer, with the original generic logic vtable behavior. Dependencies must keep represented object identities stable. Arbitrary polymorphic secondary subclasses or retargeting pointers to another object are outside the API. Input/context/output arrays must not alias. Null state/context/name checks are native safety additions; original invalid-pointer behavior is not reproduced.

## Exact image behavior

Both image helpers initialize a local lookup result to zero and call actual scene image manager +0x10 registry via **0x4f6286**. They store the result into actor **+0x170 image-set root**.

- Indexed **0x4c7900**: for a found root, actor **+0x16c image ID** becomes the requested signed index. If root minimum +0x64 <= ID <= maximum +0x68, actor **+0x174 image** becomes root +0x14 table indexed by that absolute ID. Otherwise image becomes zero.
- Default **0x4c7970**: for a found root, image ID becomes root's minimum +0x64. It still checks that minimum against maximum; an inverted resource range therefore stores minimum as ID and image zero.
- **Missing root sets +0x170 to zero but leaves existing +0x16c and +0x174 unchanged.** Clearing all image fields on missing lookup would change original behavior.
- A present zero image token is preserved as zero. Neither helper fills gaps, clamps an out-of-range ID, selects a neighboring image, changes sprite geometry, or changes actor animation/logic state.

Original table-pointer adjustment for negative absolute IDs is represented by a bounded first-index view, not a new image-selection rule. Pixel decoding and resolving the actual named resource/image inventory remain host responsibilities.

## Exact secondary logic behavior

The contact entries4c7fe0/4c8060 follow the same allocation, reset, lookup and
initializer behavior below, addressing actor78 and preserving unrelated actor70.
The coordinator extended and independently reran the comparison suite:
16,371 complete calls, including2,000 retained named/resolved contact histories,
and357 original binding instruction addresses. Contact metadata flags are also
ignored in favor of the original zero initializer argument.

Named **0x4c7fa0** initializes lookup output to zero, resolves a metadata object through scene logic manager +0x14 registry, then calls **0x4c7f20**. Unknown metadata causes zero return without changing or resetting an existing secondary object.

Resolved binder **0x4c7f20**:

1. Null metadata identity returns zero with no actor/secondary writes.
2. If actor +0x70 already exists, call its original generic reset **0x4c81b0**. Otherwise request **0x174 (372) bytes** and set actor +0x70 to the allocation result.
3. A successful allocation receives generic logic vtable 0x513740, actor ID +4, flags zero, actor scene +0xc, and zero callback +0x10 / private +0x14 / associated-resource +0x18 / +0x1c. Other secondary words retain the allocator seed. ID and scene are read after the allocation boundary, retaining the original ordering.
4. Allocation failure sets actor +0x70 zero and returns zero; it leaves the supplied secondary seed untouched except explicit adapter effects.
5. Call actual original generic initializer **0x4c8160** with metadata callback +0x10 and **flags argument zero**. Metadata's own flags are deliberately ignored here.
6. A zero callback returns zero before initializer stores. On success, secondary callback +0x10 becomes the callback, flags +8 become zero, and +0x14/+0x18/+0x20/+0x24/+0x2c/+0x34/+0x30/+0x38/+0x168/+0x16c/+0x28 become zero. Return one.

Reset **0x4c81b0** first clears callback +0x10. Nonzero secondary **+0x14 is freed as a private allocation pointer**, then cleared. Nonzero **+0x18 is destroyed through its object's virtual slot zero with argument one**, then cleared. Other fields remain unchanged. After a failed rebind with zero callback, an existing secondary's previous flags/bounds can therefore remain even though callback/private/associated pointers have been cleared. These fields must not be treated as an invented numerical state machine during reset.

The secondary handler is bound for later invocation; these functions do not invoke CaptainClawHit or another gameplay handler. Primary logic, actor flags and input/physics state are preserved except host dependency mutations. Original hit filtering/dispatch remains separate required work.

## Dependency payloads

`ClawActorBindingCall` contains original function identity, opaque receiver, one portable scalar argument and optional temporary name.

| Function | Payload |
| --- | --- |
| 0x4f6286 | Registry receiver and name. Return resolved resource/metadata token; image lookup fills context image view, logic lookup supplies metadata callback/flags |
| 0x4f63ec | C allocation: receiver zero, argument 372; return represented secondary identity or zero |
| 0x4f6428 | C free: receiver zero, argument private allocation token |
| context.associatedDestructor | Associated object receiver, argument one; identity is supplied from the observed object's original virtual destructor slot |

No ARM64 pointer is cast into an original token. The native host supplies its own allocation/resource identities and maps these dependency events to supported behavior. Root owns application integration and lifecycle policy.

## Original-instruction comparisons

`Tests/actor_resource_binding_helpers.py` extends the existing registry harness without editing it. Original **0x4f6286 / 0x4f5d5c / 0x4a3810** lookup/hash/strcmp execute against real original map associations. The named metadata map includes all 212 actual registered callbacks and a test metadata entry; an explicit image resource/table map provides test resource values.

Actual original image/binder/reset/generic initializer bodies run unchanged. Binding-phase adapters are allocation, free and associated-resource virtual destruction. Adapters deliberately mutate selected actor/secondary words to verify ordering; those mutations are test behavior, not inferred heap/resource semantics. Allocation size, free identity, destructor receiver/argument, ordered lookup names/receivers and every state word are checked. Map population uses the separately documented allocation/CString/interleaved configuration adapters from `docs/logic-registry.md`; those setup addresses are excluded from binding-phase instruction coverage.

Tests cover:

- 2,000 chained image histories: explicit/default/missing lookup, rebinding, signed and extreme IDs, edge/inverted ranges and zero image tokens.
- 2,000 chained secondary histories: allocation failure, existing-object reset, optional private/associated cleanup, metadata missing/zero callback, arbitrary metadata flags and rebinding.
- All 212 actual original callback identities as secondary metadata, proving flags zero independently of registry flags.
- Current extracted CLAW PID IDs, default and out-of-range selection. Tokens refer to caller-owned image representations; this is index/field-placement proof, not original resource-file loading or pixel acceptance.
- Full 512-byte actor and 372-byte secondary snapshots, random preserved words, dependency effects, original binder results and native table-safety rejection.

Completed suite: **12,371 complete original binder/reset calls**, **153 current CLAW PID IDs**, **284 original binding-phase instruction addresses**, excluding setup and all adapter/stop entries. All complete-buffer/event comparisons pass. The 212 registered metadata entries are covered independently of their flags. Extra PID images extracted by the coordinator are included in the current inventory; fixed historical counts are not assumed.

```sh
work/test-env/bin/python Tests/compare_actor_resource_bindings.py
```

Optimized native C++ and Swift C-bridge checks also pass signed indexed/default image selection and secondary callback binding with flags zero. Private scratch `work/actor-bindings-agent/main.swift` uses no application source/UI.

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -O2 -c Sources/ActorResourceBindings.cpp -o work/actor-bindings-agent/ActorResourceBindings.o
xcrun swiftc -import-objc-header Sources/ActorResourceBindings.h work/actor-bindings-agent/main.swift work/actor-bindings-agent/ActorResourceBindings.o -lc++ -o work/actor-bindings-agent/swift-binding-tests
work/actor-bindings-agent/swift-binding-tests
```

No shared source/project/analysis edits, device/simulator driving or extra agents are used. Root owns native integration, original hit dispatch recovery and application acceptance.
