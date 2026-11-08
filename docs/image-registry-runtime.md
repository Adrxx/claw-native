# Original image and ANI registry transport

`Sources/ImageRegistryRuntime.h/.cpp` ports 33 bounded original v1.0 methods around image-controller enumeration, root creation, sparse indexed images, ANI sequence allocation/decoding and deletion. It does not implement a new resource naming convention or repair missing resource names. The original executable fingerprint is SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`; disc REZ fingerprint is `b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596`.

## Source naming and actual inventory

Image-controller vtable `513b88`, slot `48`, is **4cff40**. Image-root vtable `513cf8`, slot `28`, is **4ce5e0**. Original4ce5e0 scans the exact resource leaf name until the **first ASCII decimal digit**, then passes that substring to original CRT4a3ce0. The native body reproduces this observed single-byte locale profile, with unsigned32-bit decimal accumulation. A leaf without digits passes the terminating NUL to the original parser and selects **ID0**. Resource metadata's stored numeric word does not select the image ID. `A12B34` selects12, `A-9` selects9, and decimal4294967296 wraps0. No suffix, sequential ordinal, neighboring-frame or default-ID1 rule is introduced.

Recursive namespace construction uses original format literal532c14, `%s%s%s`: a nonempty prefix, caller separator, and exact child/leaf name. An empty prefix omits the separator. Image directories become named roots; ANI leaves become named sequences. The source does not normalize case, fix spelling or register aliases in these methods. Root display metadata copies63 bytes and terminates byte63, while the dictionary key retains the complete formatted name.

Actual caller instructions corroborate the tested namespaces: **46b200..46b213** selects IMAGES (literal523ce0) and invokes controller+48 with LEVEL (524d80) and `_` (523728); **46b23d..46b24e** selects ANIS (523cd8) and invokes4ce0d0 with the same prefix/separator. CLAW image/ANI calls at46b27a/46b2b7 use literal523734. This is caller-argument evidence, not a complete46b0xx resource-manager or WinMain execution claim.

Whole original enumeration of the fingerprinted real trees produces:

| Transport tree | Input leaves | Registered groups/sequences | Accepted image files |
| --- | ---: | ---: | ---: |
| LEVEL1/IMAGES with LEVEL prefix |222|29 roots|212|
| LEVEL1/ANIS with LEVEL prefix |61|61 sequences|—|
| CLAW/IMAGES with CLAW prefix |157|2 roots|157|
| CLAW/ANIS with CLAW prefix |54|54 sequences|—|

The ten remaining Level1 image-tree leaves are DIR/JBF/TXT and fail the original image-type wrapper. `LEVEL1/IMAGES/SKULL/SKULL.PID` is observed at **LEVEL_SKULL, ID0**. The Level1 image root is **LEVEL_MANICAL1**, and the ANI key is **LEVEL_MANICLES_MANICAL**. Neither LEVEL_MANICALS_MANICAL nor LEVEL_MANICALS_M is registered. The pinned REZ has no path containing CANDE. A caller asking for these missing names must retain the original missing-lookup behavior; replacing them with a similarly named resource would require separate evidence.

`work/image-registry-agent/original-resource-mappings.json` records exact successful roots, sparse IDs, actual filename→observed image ID, payload SHA-256, and opaque raw transport word16, plus all ANI keys. The filename mapping comes from complete original calls under the declared traversal profile, not a standalone reference parser. `initial-rez-profile.json` is exploratory raw metadata; word12 is labeled opaque, and is not an image ID.

## Stable C11 API and host contract

```c
uint32_t claw_image_registry_entry(uint32_t function, uint32_t receiver,
    ClawImageRegistryArguments arguments, ClawImageRegistryContext *context,
    uint32_t *originalResult);
uint32_t claw_image_registry_function(uint32_t vtableToken, uint32_t slot);
```

Arguments contain five32-bit original words and their count. Pointers are heap tokens, never native pointers cast to32-bit. Return1 means a recognized entry completed; return0 means unsupported or a native fault. Meaningful original EAX is separate. Void methods' incidental EAX is not claimed. Unknown entries preserve the result/fault. Argument count must match the selected original entry.

Context supplies frozen `ClawSceneActorHost`, optional `ClawCArrayContext`, optional paired `ClawGameImageGlobals`/`ClawGameImageHost`, native fault, and **eventNameBytes** corresponding to original global543174. Initialize fault and eventNameBytes appropriately and retain the latter across calls. The ANI decoder writes that global before optional name-map lookup. Byte operations request an aligned containing-word span and apply the byte offset; the shared host never has to return an unaligned UInt32 pointer. Heap lookup must make requested word spans addressable through the call; name, payload, slot, root and array allocations remain caller-owned.

With arrays nonnull, original CArray ctor/SetAtGrow/SetSize compose the frozen CArray bodies. With arrays null they are explicit service calls. With both image globals/host nonnull, known original4ce3d0/4d2410/4d22f0 dispatch through frozen GameImageRuntime. Its rich physical surface, compression and image-drawing services remain distinct from this module's four-word SceneActor service ABI. Unknown image operations remain explicit calls. The registry oracle uses the latter explicit image initialization profile; it does not claim joined physical pixel decoding.

### Recovered entry inventory

| Entries | Arguments and role |
| --- | --- |
|4cff40 /4d0120 /4ce0d0|directory, prefixName, separatorName; recursive image load/image restore/ANI load|
|4cf080|none; parent/id validity predicate|
|4cf1f0|transportController, directoryName; root traversal then recursive default-prefix image load|
|4d0380|name; root name metadata|
|4ce5e0 /4ce670|directory; leaf enumeration/retained restore|
|4ce770|resource, imageID, key; signed min/max and indexed image restore|
|4cfaa0 /4cfba0|resource, rootName, imageID, key; get/create named root and typed/file factory|
|4cfca0 /4cfdb0|input, format, rootName, length, key; get/create named root then factory|
|4cfee0 /4cfec0|resource, rootToken, imageID, key; existing-root typed/file factory|
|4cff00 /4cff20|input, format, rootToken, length, key; existing-root factory|
|4ce320|resource, imageID, key; typed52-byte image factory|
|4ce480 /4ce530|input, format, imageID, length; raw/virtual52-byte image factory|
|4d2380|resource, key; image type/transport/load/release wrapper|
|4cdff0|sequenceName, resource;32-byte sequence ctor/load/register|
|4d61b0|soundRegistry, resource, flags; ANI type/acquire/decode/release wrapper|
|4d6070|soundRegistry, rawData, flags; whole ANI header/path/records decoder|
|4d76e0|soundRegistry, rawRecord;48-byte signed-field/event decoder|
|4d6260|deleteBits; record deleting destructor|
|4d6210 /4ce2d0|none; sequence/root clear|
|4ce270 /4d0310|none; sequence/root destructor|
|4ce250 /4d02f0|deleteBits; sequence/root deleting destructor|
|4cf230|rootName; named-root remove/delete|

Returned vtable identities include source bodies outside the supported inventory. Those entries are explicit dependencies, not automatically ported by `claw_image_registry_function`.

### Raw buffers and ordering

Image roots allocate108 bytes, bind id from controller+1c, flags0 and controller+c parent, and construct an embedded CArray at+10. Minimum+64 starts99999, maximum+68 starts0; metadata name begins+24. Image entries allocate52 bytes and preserve fields not written by original construction. Existing nonnull sparse slots reject duplicate images before allocation. Signed range checks and CArray absolute-ID indexing are preserved; no gap filling or clamping is introduced.

Image recursion loads child directories first. A nonempty prefix obtains/creates its root, then enumerates this directory. An empty result deletes the root by name; successful roots increment the returned count. Restore obtains existing roots and propagates signed failureFFFFFFFF. Recursive count/ownership ordering remains observable through callback snapshots. Certain initialization failure paths retain the original temporary-buffer leak.

ANI sequences allocate32 bytes, construct CArray+8, and bind parent+c→sound registry+28. Type414e49 is required before transport. The whole decoder ignores a header signature, ORs flags at raw+8, reads signed record count raw+c, and copies the raw+20 sound path of length raw+10 into length+2 allocated bytes. It NUL-terminates at length and preserves the extra allocation byte. Every record allocates48 bytes, stores vtable513df8/+cFFFF, decodes signed short fields, preserves unspecified words/high halves, appends to CArray, and advances20 plus the event-name byte count.

Original eventNameBytes includes the event NUL when record flag2 is set; frozen AnimationEngine's nameLength excludes that NUL, so this wrapper adds one. An empty event still counts one byte and still performs lookup when a sound registry is supplied. The global is written before lookup, and the event token at record+2c is cleared before the optional result. The real61+54 ANI datasets execute these complete bodies; no synthetic animation playback replaces them.

ANI registration creates a new sequence before map-slot access; a duplicate name can overwrite/orphan an earlier sequence. That source behavior is retained rather than silently deduplicated. Clear loops re-read current array length after callbacks; destructors preserve original free/vtable/field ordering. Physical free adapters do not scrub memory in the oracle.

## Explicit services and limitations

Resource traversal remains a finite transport boundary:4b68e0/4b6900 (directories),4b6920/4b6940 (types),4b6960/4b6980 (leaves),4b7540/4b68c0 (root/group),4b61b0 (type),4b61c0 (resident raw bytes),4b6230 (release). Raw resource+0 is its name and+14 its length in this declared transport view. The native host must supply the same graph and callback order.

The real tests supply stored REZ directory/leaf ordering as an explicit traversal profile. Underlying original BTree iteration/storage4d54c0/4d5350 is not recovered here. Thus malformed duplicate-ID selection depends on the supplied traversal order; real-tree naming/count proof is not a full REZ loader or retail transport-order proof.

Map4f6286 uses receiver controller+10, name argument and returns the resolved value (the original output-pointer ABI is adapted). Map4f62a8 returns a writable raw32-bit value-slot token; new slots must update controller+1c when the real map does. Map4f5db6 removes the name. The original generic dictionary body is not reimplemented by these adapters. Physical allocation/free use SceneActorHost.allocate/free. In the oracle,4d2410/4d2540 image initialization,4ce8e0 image deletion,4d27a0 restore and4ce3d0 file factory are explicit measured services, including raw payload hashes and complete boundary snapshots.

Missing span/service produces native fault1, unsafe metadata/argument profiles fault2, bounded iteration/name limits fault3. The original code can dereference null allocations and overrun formatted buffers. Native code stops at those unsupported unsafe accesses: the two null108/null52 allocator cases compare complete original prefixes only, stopping immediately before the first null dereference. They are not whole successful original calls or original diagnostic returns. Native256-byte restore-buffer null handling, maximum formatted length255, name scan limits and iteration cap1,000,000 are safety extensions. Mutable CRT locale/DBCS decimal parsing, OS allocator internals, SEH exceptions and physical renderer/resource transport are not claimed.

## Verification

`Tests/compare_image_registry_runtime.py` executes the pinned original bodies with explicit services and compares every2MiB persistent heap byte, meaningful EAX,543174, raw payload identity, map/allocator service state, and ordered events hashed over the complete heap/global at each boundary. CArray and original ANI decoder execute without body stubs; native composes frozen CArray and AnimationEngine. Field seeds are preserved and retained histories cover duplicate registration, sparse roots, restore failures, removal/deletion and all real Level1/CLAW image/ANI groups. Directed cases include first-digit overflow, no digits, exact case/separators,63-byte metadata truncation, typed image4-format selection, wrong types, missing payloads, safe allocation failures and raw ANI flags/path/empty events.

Final suite: **795 complete original calls**, **15,724 ordered complete snapshots**, **2 unsafe original prefixes** and **374 callback-free original whole-heap sanitizer replays**. Exact instruction coverage excluding adapter and unsafe-stop entry points is recorded in `work/image-registry-agent/verification.json`. C11 header compilation and optimized C++ warnings-as-errors pass. ASAN/UBSAN replay checks complete original buffers and globals, with every unexpected allocator/service callback rejected; it validates the replayed name/record/predicate leaves, not physical image services.

```sh
work/test-env/bin/python Tests/compare_image_registry_runtime.py
work/image-registry-agent/check-sanitizer.sh
clang -std=c11 -Wall -Wextra -Werror -I Sources -fsyntax-only work/image-registry-agent/header_check.c
```

Private Ghidra outputs are registry.c, children-verified.c, loaders.c, ani.c, lifecycle.c and final-bounds.c, each with checked logs. Earlier children.log/extra.log contain explicit SCRIPT ERROR for interior addresses and are diagnostic failures, not evidence. No shared analysis project was modified. This bounded recovery does not establish complete application startup, image/ANI transport, actor rendering, native UI acceptance or whole-game identity.
