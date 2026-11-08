# Original WWD generic actor construction

This recovers the original v1.0 **generic WWD actor loader 0x4d17e0**, its common actor/logic initialization, and record-to-runtime field stores. It does not recover Rat, Candy, enemy, pickup or other gameplay callbacks merely by binding their names. Registry metadata, image/sound helpers, destruction and spatial insertion are explicit host dependencies. The parent owns actual native level-object integration and callback recovery.

Original profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Algorithms and offsets come from this binary's instructions; no reference gameplay implementation is copied. The CLAW/Level1 CD-rip resource identity with original retail resources remains unknown.

Private Ghidra outputs: `work/world-object-agent/object-load.c`, `constructors.c`, `common-init.c`, `logic-init.c` and `initializer.c`. These are evidence, not replacement source. Requests mistakenly inside an existing function were rejected by the script; only successfully decompiled real entrypoints inform this implementation.

## Stable API

`Sources/WorldObjectRuntime.h/.cpp` exports:

```c
uint32_t claw_world_object_load(
    const uint8_t *record, size_t length,
    ClawWorldObjectRuntime *runtime,
    ClawWorldObjectContext *context,
    ClawWorldObjectDependency dependency, void *user,
    ClawWorldObjectInfo *info);
void claw_world_object_construct(
    ClawWorldObjectRuntime *, const ClawWorldObjectContext *, uint32_t id);
uint32_t claw_world_object_initialize(
    ClawWorldObjectRuntime *, const ClawWorldObjectContext *,
    uint32_t x, uint32_t y, uint32_t z);
```

Runtime contains `actor[128]` and `logic[93]` uint32 words. The original actor allocation is **0x1b4 (436) bytes**, or 109 words; the 128-word host buffer is deliberately compatible with the existing player representation. Extra host words remain untouched. Original logic allocation is **0x174 (372) bytes**, or 93 words. Caller seeds remain unchanged except exact recovered stores: the original allocator does not initialize every field, so zero-filled defaults for untouched fields would be a host choice, not an original constructor fact.

Context carries scene/actor/logic opaque identities, scene field +0x24 (`sceneDefaultType`), signed world width/height, registry/layer identities and lookup-supplied entry identity/callback/flags. Do not cast ARM64 pointers into these 32-bit fields. The source buffer is 71 little-endian words followed by four raw byte-length strings; it must not alias runtime/context buffers. The native safety envelope requires nonzero supplied actor/logic identities, complete header/strings, and each string length <=1023 before mutating anything. The original copies into a 1024-byte temporary buffer without equivalent checks. Native malformed-input rejection does not claim original crash/overflow parity.

Return value is the original consumed record byte count, or zero for initialization failure/native safety rejection. Optional info records consumed bytes and whether the object reached the successful spatial-insertion path. An out-of-world or unknown-logic object can be destroyed while still consuming the whole record. Dependencies must keep allocated identities stable and must not retarget the actor's attached logic to another object; this API represents one actor and one logic allocation.

Public construction/initialization allow the separately recovered player startup to use the exact common baseline. Initialization with a zero supplied callback returns zero after the original pre-binding actor stores. It does not invoke a gameplay callback.

## Original creation flow

1. **0x4d17e0** reads record ID, four string lengths, x/y/z and image ID; allocates the actor; calls **0x4c98c0** with scene pointer, record ID and flags zero.
2. **0x4c98c0** initializes base actor fields and allocates the generic logic object, storing its pointer at actor +0x6c. The loader then initializes animation-related fields and supplies actor vtable token 0x5137f0, logic vtable token 0x513740 and animation member vtable token 0x513870.
3. Four temporary CStrings are created from the raw strings with an appended NUL. The first is the object's name but is unused after construction in this routine. Embedded NUL terminates the CString while byte consumption still uses the complete declared string length.
4. Signed x/y must be within `[0, worldWidth)` and `[0, worldHeight)`. Outside objects are destroyed and consumed without registry lookup.
5. A nonempty logic string is looked up through **0x4f6286** in the scene's registry. Empty or missing names destroy/consume the object.
6. Resolved metadata is passed to original virtual **0x4c9d40**, which calls **0x4c81f0 → 0x4c7df0 → 0x4d5800 → 0x4c8160**. Metadata +0x10 becomes the future logic callback; metadata +8 becomes logic flags. These helpers **bind but do not call the registered gameplay callback**.
7. Failed callback binding destroys the actor and returns zero. Success ORs actor flags 0x40000, performs optional image/sound helpers, then applies WWD fields.
8. **0x4d51a0** selects a spatial registration layer from actor flags and calls **0x4f4630** with actor's member at +0x88. The four CStrings are destroyed in reverse order.

Vtable tokens are preserved for byte comparison; the native host must never invoke those x86 addresses as function pointers. No private gameplay-state allocation is invented here; unrecovered private/pointer fields retain their caller seed until a recovered callback initializes them.

## Exact common baseline

Construction stores actor ID +4, flags +8 zero, scene +0xc; INT_MIN at +0x20/+0x4c/+0x54/+0xac; -1 at +0x38/+0xc4; zero at +0x3c/+0x40/+0x90/+0x94/+0xa0/+0x68/+0x84/+0x80/+0x70/+0x78. Animation/image fields +0x168/+0x16c become -1, +0x170/+0x174/+0x178/+0x17c/+0x180/+0x184/+0x18c/+0x190/+0x194 become zero. Logic gets ID +4, flags +8 zero, scene +0xc, and zero +0x10/+0x14/+0x18/+0x1c.

The common successful initializer sets:

- Actor x/y/z +0x4c/+0x50/+0x64, and position snapshots +0xe8/+0xec/+0xf0.
- Actor +0x10/+0x14/+0x40/+0x44 zero; +0x48 = 50; +0x3c from scene +0x24.
- Actor **+0xdc/+0xe0 = 10**, not the preview's earlier chosen step 16.
- Zero actor +0xf8/+0xfc/+0x100/+0x104/+0x108/+0x10c/+0x110/+0x114/+0x148/+0x14c/+0xc8/+0x164.
- Animation actor identity +0x18c, zero +0x190, one +0x1a4, float bits 1.0 (+0x1b0); metadata identity +0x180 and zero +0x184.
- Logic callback +0x10 and flags +8 from metadata; zero +0x14/+0x18/+0x20/+0x24/+0x2c/+0x34/+0x30/+0x38/+0x168/+0x16c/+0x28. A zero callback fails before these stores.
- On binding success, zero actor +0x70/+0x78/+0x74/+0x7c/+0xd0/+0xd4/+0xd8; INT_MIN rectangle-left sentinels +0x118/+0x128/+0x138; actor identity +0xa0 and current x/y +0x98/+0x9c.
- Metadata logic flag 1 ORs actor flag **0x800000**; otherwise logic flag 2 ORs **0x1000000**. Flag 1 takes priority if both are present.

Generic constructor flags zero do not establish the preview's chosen actor flag 0x80. Default actor type comes from the supplied scene field; type 2 is not hard-coded by these routines. The API preserves exact pointers as tokens and exact signed/unsigned word bit patterns.

## Original WWD field map

Indices are zero-based fixed words; strings begin at byte 284.

| WWD words | Runtime destination / behavior |
| --- | --- |
| 0 | Actor +4 ID |
| 1...4 | Name, logic, image-set, sound byte lengths |
| 5,6,7 | Common x,y,z initialization above |
| 8 | Image helper selection: -1 → 0x4c7970; else 0x4c7900 with image ID |
| 9 | **Unused by this loader**; do not apply addFlags implicitly |
| 10 | OR into actor +8, after common flags and resource helpers |
| 11 | Actor +0x40 |
| 12 | Logic +0x28 |
| 13...18 | Actor +0xf8...+0x10c |
| 19...22 | Actor +0x118...+0x124, move rectangle |
| 23...26 | Actor +0x128...+0x134, hit rectangle |
| 27...30 | Actor +0x138...+0x144, attack rectangle |
| 31...34 | Actor +0x54...+0x60, clip rectangle |
| 35...42 | Logic +0xf0...+0x10c |
| 43...50 | Logic +0x64...+0x80 |
| 51,52,53,54 | Logic +0x2c,+0x34,+0x30,+0x38 **in this reordered sequence** |
| 55,56 | Actor +0x148,+0x14c |
| 57,58 | Logic +0x44,+0x48 |
| 59,60 | Logic +0xb8,+0xbc |
| 61,62 | Logic +0xc8,+0xcc |
| 63,64 | Actor +0x110,+0x114 |
| 65,66 | Logic +0x20,+0x24 |
| 67,68 | Actor +0xd0,+0xd4 |
| 69,70 | Actor +0xdc,+0xe0 only when record value nonzero; else retain common 10 or a helper's later mutation |

For each move/hit/attack/clip rectangle, **left and right both zero** cause left alone to become INT_MIN, even if top/bottom are nonzero. The left/right tests and their original order are preserved. No rectangle geometry is filled from sprite size in this loader.

Spatial layer selection tests actor flag 0x800000 first, then 0x1000000, otherwise neither. Context `layerTokens[1]`, `[2]`, `[0]` map to original registration object +8,+0xc,+4 respectively. Layer names/semantics are intentionally not inferred. The original cell-coordinate/list insertion routine 0x4f4630 remains a dependency.

## Dependency contract and test scope

Callbacks receive original address, opaque receiver, portable scalar arguments and optional temporary string. Internal CString/output-pointer arguments of lookup are represented by `text` and context's supplied metadata, not host pointer casts.

| Address | Dependency meaning |
| --- | --- |
| 0x4f6286 | Logic lookup: receiver registry; text logic name; return metadata identity and supply context entryCallback/entryFlags |
| 0x4c7970 | Image-set helper: actor receiver; text image set; automatic/default image choice |
| 0x4c7900 | Image-set helper: actor receiver; text image set; argument image ID |
| 0x4c79e0 | Sound setup: actor receiver; text sound; argument zero |
| 0x4c7a40 | Sound helper: actor receiver; text sound |
| 0x4c9be0 | Actor destruction: actor receiver; argument one |
| 0x4f4630 | Spatial insertion: selected layer receiver; argument actor identity +0x88 |

Tests execute original4d17e0, constructor4c98c0, all common initializer bodies and selector4d51a0 unchanged. Only CRT actor/logic allocation, CString construction/destruction, and the listed dependencies are adapted. Allocation sizes 436/372, four CString contents/lifetime/order and each portable dependency's arguments are audited. Adapters intentionally mutate selected actor/logic fields in both executions to verify helper ordering and subsequent WWD overwrites; those mutations are **test adapter behavior**, not recovered resource/destructor/spatial routines.

`Tests/compare_world_object_runtime.py` passes:

- **1,500 generated records**, including arbitrary signed word bit patterns, optional strings, automatic/explicit image IDs, embedded NUL, rectangle sentinels, zero/nonzero step overrides, both metadata flag choices and random uninitialized-buffer seeds.
- Original rejection/skip branches for negative or edge x/y, empty logic, unknown logic and metadata's zero callback.
- **All 1,479 exact raw Level1 records**, covering **38 distinct logic names**. The test independently decompresses WWD and passes raw object bytes; no Swift string reserialization is used. Metadata is supplied explicitly rather than claimed as the actual original Rat/Candy/etc registry table.
- Full 512-byte actor and 372-byte logic buffers, untouched trailing/seeding words, input immutability, ordered dependency arguments and original consumed-byte return.
- Native malformed/truncated/oversized strings reject without buffer, info or event mutation.
- **2,986 complete original loader calls**, **872 original instruction addresses**, excluding adapter and stop entries.

Run:

```sh
work/test-env/bin/python Tests/compare_world_object_runtime.py
```

Optimized C++ and Swift C-bridge smoke checks also pass for the public common constructor/initializer: x/y/z, steps10, supplied scene type and callback/flag binding. Scratch `work/world-object-agent/main.swift` uses no application source or UI.

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -O2 -c Sources/WorldObjectRuntime.cpp -o work/world-object-agent/WorldObjectRuntime.o
xcrun swiftc -import-objc-header Sources/WorldObjectRuntime.h work/world-object-agent/main.swift work/world-object-agent/WorldObjectRuntime.o -lc++ -o work/world-object-agent/swift-object-tests
work/world-object-agent/swift-object-tests
```

The test builds only the owned C++ source into private scratch. No Xcode, UI/device/simulator or shared project edits are used. Actual per-name registry callback/flags, dependency bodies, private gameplay initialization, object updates, enemy/pickup behavior and native application acceptance remain separate required work.
