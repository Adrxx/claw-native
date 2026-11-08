# Original PCX image bodies and native surfaces

`PCXImageRuntime` recovers the fingerprinted original v1.0 loader and reached
RLE/conversion bodies. Original SHA256 is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The earlier exact-file sanitizer failure was an unchecked original read in the
declared direct24-bit tile profile. It was not repaired by clamping RLE runs,
changing image dimensions or replacing the decoder with a standard PCX library.

| Entry | Arguments / source behavior |
| --- | --- |
|4bebc0|surface,(graphics manager,data,file length),RET12: whole loader|
|4babe0 /4bad30|surface,(encoded data),RET4: indexed /BGR surface decode|
|4bef50 /4bf070|(destination,data,width,height),RET16: indexed /RGB linear decode|
|4b9e90|surface,(data,source depth,palette,direction),RET16: conversion election|
|4ba580 /4ba2d0|surface,(data,palette,direction),RET12: quantize /expand|
|4bb040 /4bb050|surface,RET0: live width /height|
|4bb0f0|surface,(row),RET4: wrapping pitch×row|
|4b9e60|surface,RET0: restore callback and source error notification|

The loader reads signed16-bit coordinate differences and planes1/3. It checks
surface dimensions and target-depth admission. It does not validate the PCX
signature, encoding, bits-per-pixel or bytes-per-line. Same-depth indexed widths
and heights are cached before Lock; planar dimensions are reread after Lock.
Each RLE run writes its complete six-bit count, even across a row/plane boundary.
Zero-count runs consume their value byte. No row-end clamping is inserted.

For changed depths, allocation requests remain exactly width×height×1or3.
An indexed source palette is expanded from the final768 file bytes into raw
global541bb0. Three-plane→indexed uses the graphics manager's actual palette
admission flag+878 and palette+478. The source24→8 squared-distance election,
first-index ties, early exact-match exit and row direction are preserved.
Unrecovered16-bit conversion bodies remain addressed source services. Physical
Lock/Unlock/restore, diagnostics and allocator behavior remain native transports.
Frozen GameImage4b9730/4bb0e0 compose when selected; they are not duplicated.

The API uses raw32-bit tokens and an optional exact-byte lookup. Word-only
lookups may expose their final containing word; a host must declare that padding.
Return1 means a recognized source body completed; meaningful original EAX is
separate. Native faults1(missing span/service),2(ABI/domain),3(operation bound)
are diagnostics, not original error returns.

Root independently runs `Tests/compare_pcx_image_runtime.py`:968 whole calls,
1670 full ordered snapshots, two unsafe prefixes,1343 instrumented text
addresses, complete4MiB heap and294912-byte globals. It includes all469 actual
disc PCX files (313 indexed/156 three-plane), generated literals/counts/zero
runs, callback descriptor mutation, source allocation/Lock/restore failures,
streaming aliases, retained changed-depth histories and ignored metadata.
That broad-heap corpus contains Seed721 neighboring bytes; it does not prove
exact-file safety or retail archive allocation identity.

`Tests/capture_pcx_image_spans.py` executes another469 unchanged-original calls
and938 snapshots while measuring actual input reads and surface writes. The
result records58 three-plane tile profiles that read1..38 bytes beyond their
file, and a maximum180-byte destination tail. No state image reaches beyond its
input. Exact-file native faults match the complete original heap/events at the
first forbidden read in all58 cases. Those are source-prefix comparisons, not
successful decoding of an exact file or proof of real archive neighbor bytes.

`Tests/check_pcx_image_spans_asan.py` passes469 source-captured exact declared
input/surface spans, repeated calls and58 tight-file prefixes under ASAN/UBSAN.
The declared input tail is copied from the measured Seed721 fixture; allocator
requests/file lengths are unchanged. Captured bytes stay ignored in
work/root-pcx-spans. The reusable C++ replay and scripts are included in Tests.
Strict C11/C++17 and Swift imports pass (call64/context88 bytes).

Native Display now creates requested memory surfaces through whole source4bc670
and its list ownership. Dynamic descriptors report actual width/height/depth;
mode-only primary descriptors inherit640×480×8. Backing includes one physical
offscreen row. Whole4bebc0 shares the native GameImage globals, actual DD
interfaces and pixel storage. Its file-byte lookup rejects exact EOF even if
the native token heap rounded that allocation to a word. Source deletion removes
the surface from its graphics list. Physical interface storage lasts until the
device transport ends, as in the current display adapter.

Run `CLAW_NATIVE_ASAN=1 scripts/check-native-player.sh --pcx-only` after generating
the capture corpus. The directed native history passes313 actual indexed files,
including299 state images, every cropped original-captured pixel, repeated
decoding and source surface/list cleanup. It also checks an exact130-byte EOF
prefix despite word padding, ordinary frame resumption and graph destruction.
The final outcome and build/full-regression evidence are recorded in STATUS.md.

The whole PCX creation wrapper4be810 is now recovered and composed through
native4bc520→4bf9c0(type2), with header-derived dimensions and source list
ownership. See pcx-creation-runtime.md for596-call original comparison and
313-file native factory evidence. Live image-controller/menu/IFC/Story election
remains pending. Type1 wrapper4bdad0 reads BMP header fields and is not PCX.
Three-plane native palette conversion, actual archive neighbor allocation,
16-bit bodies, full retail boot/presentation and device/pixel acceptance remain
unfinished.
