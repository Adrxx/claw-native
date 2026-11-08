# Original v1.0 logic registry bindings

`Sources/LogicRegistry.h/.cpp` provides **212 ordered built-in logic bindings observed in original registration routine 0x401000**, including **all 38 logic names used by the 1,479 local Level1 WWD objects**. Each binding includes its exact original name, callback identity and flags. This is metadata recovery; it does not implement or execute those 212 gameplay callbacks.

Original profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The table is generated from hash-pinned original execution, not CrazyHook metadata or reference gameplay source. Local CD-rip resource identity with original retail assets remains unproved.

## Stable native API

```c
uint32_t claw_logic_registry_count(void);
const ClawLogicRegistryEntry *claw_logic_registry_at(uint32_t index);
const ClawLogicRegistryEntry *claw_logic_registry_find(const char *name);
```

`at` takes a zero-based index. Entry fields are `name`, `registrationOrdinal`, `originalNameAddress`, `callback`, `flags`. Ordinal is one-based and gives a stable **native identity**, not an original x86 allocation address. `originalNameAddress` is the actual string address in the fingerprinted binary. Callback is likewise an original address identity: never invoke it as an ARM64 function pointer. `find` compares exact NUL-terminated bytes, including case; unknown names return null. Null input and out-of-range indices return null as deliberate native safety extensions.

To satisfy `WorldObjectRuntime` lookup, use a chosen nonzero native metadata token (the ordinal is suitable), and copy `callback`/`flags` into `entryCallback`/`entryFlags`. The existing generic initializer then binds the future callback and derives actor layer flags through the recovered rules. Registration flags are **logic metadata flags**, not WWD dynamic flags or complete actor flags.

Player bindings are:

| Name | Ordinal | Original name address | Callback | Flags |
| --- | --- | --- | --- | --- |
| CaptainClaw | 1 | 0x00522e80 | 0x00415df0 | 0 |
| CaptainClawHit | 2 | 0x00522e70 | 0x0041ce80 | 0 |
| SimpleAnimation | 181 | 0x005224d8 | 0x00498f40 | 0 |

These ordinals agree with the generated source; addresses and flags come from original instructions. No CrazyHook address is used.

## Original factory and lookup

Original population **0x401000...0x40223a** invokes scene +0x14 registry vtable +0x24. Actual vtable **0x513b60** resolves that slot to factory **0x4d6340**. Each call passes callback, name and flags.

Factory 0x4d6340 allocates a **0x174-byte generic logic object**, rather than a small invented descriptor. It stores original generic logic vtable 0x513740, scene pointer at +0xc and metadata ID at +4. The ID is the current registry map count before insertion, so ordinary unique built-ins have ID `ordinal-1`. Duplicate registration does not increment map count and can reuse that ID; the ID is therefore not a unique allocation identity.

Factory executes original logic initializer **0x4c8160**. A nonzero callback becomes entry +0x10 and flags become +8. It clears the exact logic state/timer/bounds fields described in `docs/world-object-runtime.md`; untouched words retain the allocator's seed. A zero callback fails before binding stores, destroys the allocated object and returns zero without inserting/replacing a map value.

Success uses original **0x4f62a8** (`CString → pointer` map assignment), which calls original hashing/key search **0x4f5d5c** and association constructor **0x4f6226**. Hash accumulates `hash*33 + signedByte` with uint32 wrapping, then takes the bucket modulus. Equality uses original CRT strcmp **0x4a3810**, so lookup is case-sensitive. Strings are copied through a CString storage boundary **0x4f66cc**; the caller's temporary string is not retained as the key.

Original lookup **0x4f6286** calls the same map search. It returns nonzero for a found entry and writes its pointer to the supplied output. **A missing name leaves the caller's output word unchanged.** The WWD loader explicitly initializes that output to zero; there is no automatic DoNothing fallback.

For an exact duplicate key, original assignment replaces the existing map value with the newly created object, retains its stored key, leaves the map count unchanged and does not destroy the replaced object in this factory. Built-in 0x401000 has **212 unique exact names**, so its native immutable table has no duplicate entries. Native reverse traversal retains last-binding semantics if a generated table ever contains duplicate keys; dynamic custom registration itself is not supplied by this API.

## Execution adapters and limits

`Tests/logic_registry_helpers.py` runs the original population entry, original registration factory/binding, actual map-node construction/insertion, signed-byte hash, CRT strcmp and original lookup. Only these boundaries are adapted:

- CRT allocation returns audited **372-byte** caller memory seeded with 0xa5, so full metadata-buffer preservation is checked.
- CString string-storage assignment provides a copied NUL-terminated buffer and audited length/header; the original map's key-management calls execute but the original CString allocator/copy internals do not.
- Empty map buckets and a free-association pool provide backing memory. Original association initialization and linked-bucket insertion execute unchanged.
- Original destruction for the zero-callback probe is an explicit boundary; its receiver/argument are checked.
- **84 calls to 78 per-logic resource/configuration initializer entries** interleaved with registration are adapted. Their ordered call sites/addresses are recorded in private evidence. Their global resource/configuration effects are outside this binding-table recovery; no claim is made that their own complete bodies, all dependent global tables or later dynamic registry additions have been recovered.

The scope is the complete 212 direct registration calls in the verified built-in population entry with those explicit dependencies. It is not a complete original application-startup run. Captured entry addresses such as 0x01080000 are **harness allocator addresses only**, never claimed as original live heap addresses or embedded as native identities.

Private evidence `work/registry-agent/verified.json` records all ordered entries, callback/name/flags, full-trace allocated identities, original metadata IDs, side-helper call sites and Level1 name counts. `work/registry-agent/registry.c` and `map.c` contain bounded private Ghidra outputs.

## Verification

`Tests/compare_logic_registry.py` passes:

- All **212 ordered bindings** against generated native source, including exact name pointers, callbacks, flags and ordinals.
- Complete **372-byte metadata buffers** for every original factory allocation, including original ID, bound/cleared fields and every untouched seed word.
- **1,278 built-in lookup probes**, covering original spelling, lowercase/uppercase, whitespace, prefix truncation, missing defaults, embedded NUL and high-byte unknown names.
- Original duplicate replacement, retained copied key, empty-name acceptance, arbitrary flag words and zero-callback failure.
- All **38 raw Level1 logic names / 1,479 object records**, independently decompressed from WWD, against actual registered metadata.
- **1,736 original instruction addresses**, excluding all adapters and the harness stop address.
- Optimized native object plus Swift C-bridge smoke checks for count, CaptainClaw/Hit flags/callbacks and case sensitivity.

```sh
work/test-env/bin/python Tests/compare_logic_registry.py
clang++ -std=c++17 -Wall -Wextra -Werror -O2 -c Sources/LogicRegistry.cpp -o work/registry-agent/LogicRegistry.o
xcrun swiftc -import-objc-header Sources/LogicRegistry.h work/registry-agent/main.swift work/registry-agent/LogicRegistry.o -lc++ -o work/registry-agent/swift-registry-tests
work/registry-agent/swift-registry-tests
```

No UI, Xcode project, simulator/device or shared source/analysis files are changed. Root owns integration. Callback behavior, secondary hit/collision dispatch, interleaved resource/configuration initializer bodies and actual gameplay acceptance remain separate work.

## Level1 registered metadata

The following table is generated from verified original bindings and exact raw WWD name counts.

| Logic | Objects | Callback | Flags |
| --- | --- | --- | --- |
| Officer | 26 | 0x00462350 | 0 |
| Soldier | 16 | 0x0048a980 | 0 |
| Rat | 12 | 0x0047c850 | 0 |
| PowderKeg | 58 | 0x0046f1e0 | 2 |
| FrontStackedCrates | 4 | 0x0048d560 | 2 |
| BackStackedCrates | 18 | 0x0048d620 | 2 |
| HealthPowerup | 20 | 0x00470d00 | 2 |
| SpecialPowerup | 10 | 0x00470430 | 2 |
| FrontCrate | 25 | 0x00471720 | 2 |
| BehindCrate | 9 | 0x00471750 | 2 |
| TreasurePowerup | 138 | 0x0046fd10 | 2 |
| AmmoPowerup | 1 | 0x00471100 | 2 |
| GlitterlessPowerup | 299 | 0x00470100 | 2 |
| CursePowerup | 8 | 0x00470a20 | 2 |
| Checkpoint | 7 | 0x00422ef0 | 2 |
| FirstSuperCheckpoint | 1 | 0x004232c0 | 2 |
| SecondSuperCheckpoint | 1 | 0x004232e0 | 2 |
| StartElevator | 1 | 0x0049daf0 | 1 |
| Elevator | 26 | 0x0049e2a0 | 1 |
| TriggerElevator | 4 | 0x0049db10 | 1 |
| CrumblingPeg | 64 | 0x0049d860 | 2 |
| TogglePeg | 23 | 0x0049e4e0 | 2 |
| TogglePeg2 | 16 | 0x0049e7b0 | 2 |
| TogglePeg3 | 11 | 0x0049e7d0 | 2 |
| TogglePeg4 | 6 | 0x0049e7f0 | 2 |
| DoNothing | 58 | 0x00461730 | 2 |
| BehindCandy | 15 | 0x004617d0 | 2 |
| FrontCandy | 35 | 0x00461770 | 2 |
| BehindAniCandy | 485 | 0x00461970 | 2 |
| FrontAniCandy | 1 | 0x004618e0 | 2 |
| SoundTrigger | 25 | 0x0048c1e0 | 2 |
| BigSoundTrigger | 21 | 0x0048c410 | 2 |
| SmallSoundTrigger | 7 | 0x0048c430 | 2 |
| ClawDialogBigSoundTrigger | 1 | 0x0048ca40 | 2 |
| ClawDialogSmallSoundTrigger | 12 | 0x0048ca60 | 2 |
| GlobalAmbientSound | 4 | 0x00402ca0 | 4 |
| AmbientSound | 2 | 0x00402cc0 | 1 |
| SpotAmbientSound | 9 | 0x00402e20 | 0 |
