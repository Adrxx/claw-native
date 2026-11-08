# Original positive circle fades, palette conversion and diagnostics

`PlayerFadeBlendRuntime.h/.cpp` add the positive-gradient portions of original
circle step`4ed800`, complete helper`4ee170`, the full circle factory's
CString diagnostic paths, and their pure palette creation/destruction bodies.
The frozen PlayerFadeRuntime is unchanged. Its nonpositive pixel steps,
constructor, initializer, radius numeric profile, clocks and pre/post routines
are composed rather than replaced.

The executable remains `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private decompiles and checked logs live in `work/player-fade-blend-agent`.
An initial request for`4f64a7` was rejected because it is inside`4f6480`;
the corrected final decompile request uses the actual`4f6480` boundary.
Original instructions, not decompiler text or gameplay reference source,
provide the differential oracle.

## Raw API and entry inventory

`ClawPlayerFadeBlendContext` points directly to the existing frozen
`ClawPlayerFadeContext`. It adds a four-byte temporary CString object token,
the caller's shared empty CString data identity, and an explicit seed for an
unwritten capture pixel pointer. All callbacks use the frozen six-argument
`ClawPlayerFadeDependency` ABI and the same raw SceneActorHost spans/fault.

| Entry | Original arguments and recovered body |
| --- | --- |
| `4ed800` | this=2075-word effect; step; RET4; complete positive pixel branches, frozen nonpositive branches |
| `4ee170` | effect; row,radiusSquared,radius,paletteBytes,destPixels,sourcePixels; RET24; complete palette band traversal |
| `4ec050` | manager; type,descriptor; RET8; whole type1 circle factory, including descriptor/default/initializer diagnostics |
| `4f65f2` | CString object; ANSI text token; RET4; shared-empty initialization, resource-ID dispatch, length/allocation/copy |
| `4f6480` | CString object; length; RET4; allocation/header/terminator stores |
| `4f6433` | noargs; original shared-empty cell identity`52e1cc` |
| `4ec6b0` | by-value CString DATA argument; RET4; actual shared-string destruction |
| `4c6bd0` | palette owner; 256four-byte colors,gradientWidth,packedTargetColor; **RET12**, complete lookup-table builder |
| `4c7580` | cdecl(colors,channel0,channel1,channel2); complete nearest-color search |
| `4c76d0`,`4c76f0` | twelve-byte palette object ctor / backing allocation(bytes) |
| `4dee30` | pointer CArray; size,grow; RET8; zero-free gate plus frozen common positive resize |
| `4c78d0`,`4c76e0` | palette backing reset / object destructor |
| `4c7510` | palette owner; objectToken; find-first removal and heap lifecycle |
| `4c6270`,`4c61f0` | clear all palettes / embedded owner destructor with flag-dependent cleanup |

Meaningful ctor/factory/search returns are separate from incidental EAX of
void routines. Unknown public entry returns0 unchanged. Fault1 indicates a
missing span/service, fault2 a bounded unsafe/unbounded domain, and fault3
an unsupported factory kind. None is an invented safe original exit.

## Pixel progression and quirks

Positive fade-out uses the shrinking circle radius already written by the
frozen exact numeric profile. After the original border zeroing, its band
reads captured original pixels through the palette byte table. Fade-in first
copies newly exposed interior bands, then calls`4ee170` on the wider radius
`step+gradientWidth-1`.

For each palette-band pixel, the actual table index is
`sourceByte*gradientWidth + truncatedDistance-radius+gradientWidth`.
This is a supplied indexed lookup, not a host alpha/opacity calculation.
Four mirrored pixel writes run in the original order: left original row,
left mirror row, right original row, right mirror row. Duplicate center
coordinates deliberately write and read again. Aliased and shifted buffers
can therefore produce a different result from an RGBA blend or a snapshot
of source pixels; tests verify the actual source results.

The canonical row half depends on centerY relative to signed height/2.
Its opposite row is reached only when the original range check accepts
`2*centerY-row`. Horizontal clips preserve the source's asymmetric left
and right conditions, including skipped negative left coordinates. Every
lookup/write resolves byte spans, retaining padding and neighboring storage.

Palette blending writes **one byte per pixel coordinate**, regardless of
surface bytesPerPixel1/2/3/4; border clears/copies still use bytesPerPixel.
Fade-out indexes its capture pixel pointer with the **other surface's pitch**,
not capture surface pitch. Both unusual behaviors are instruction-backed.
The source's capture local is unwritten if effect`+40` is absent; the new
context exposes its seed instead of silently substituting another image.
Ordinary positive fade-out calls frozen pre`4ee820` first and owns a capture.

No new clock, pump, present, Sleep, RGBA conversion or opacity is added.
Complete positive sequences reuse original runner`4ec9c0`, including the
float32 timestamp/duration conversion, final-step catch-up/FPS and optional
DD virtual`+58`. Physical DirectDraw locks/unlocks/capture/copy remain explicit
platform services.

## Source palette conversion and lifetime

`4c6bd0` allocates a twelve-byte object, initializes its three words to0,
allocates `gradientWidth<<8` backing bytes via`4c76f0`, and appends the object
to its embedded palette owner pointer array. Each input color uses its first
three bytes; the fourth byte does not participate. The packed target color
supplies channel0/1/2 from its low/middle/high bytes.

For each shade, original x87 PC53 arithmetic computes a ratio using the
**float32 gradient width** and blends channel values in double, then applies
original FTOL truncation. Nearest-color`4c7580` masks each requested channel
to8bits, sums three squared channel differences over256 colors, and replaces
its best index only for a strictly smaller distance. Ties retain the first
index. All per-color source instructions execute in palette-builder oracle
cases; nearest-color is not replaced by a Python or native adapter there.

Object allocation failure returns0. Backing allocation failure also returns0
and leaves the already allocated object as the source does. The module does
not invent cleanup for that leak. Existing backing storage is freed before
replacement; failed replacement preserves the source's flag/size stores.

Palette reset obeys its original word0 flag. A zero flag may leave nonzero
backing/length words untouched. Remove and clear re-read array slots after
reset callbacks; object and array frees preserve callback order and untouched
unused tail words. Owner destructor sets its array vtable to`5136e8` then
`50becc`, with its original conditional clear behavior. No blanket free or
reset of preserved fields is substituted.

The palette builder bounds positive gradient widths above4096 with fault2;
this is a native finite-domain extension, not a successful original return.
Pixel traversal bounds row storage to1024 and runaway band loops to1million.
Outside caller-owned byte spans faults are explicit. Positive magnitudes
1..511, zero and negative signs are exercised in pixel comparisons; true
per-color builder comparisons include widths0..17 and shifted-size failures.

## Diagnostic strings and ownership

Wrong circle descriptor type emits literal`53404c`; invalid/default circle
initialization emits`5340a0`. The source has no formatter, log display or
message pump in this path. `4f65f2` initializes the local CString to the
shared empty data, calls the ANSI length import`5469e4`, then allocates
length+13 bytes and writes refcount1, length, capacity, and a final zero byte.
The actual literal bytes copy through frozen CArrayRuntime`4a4a80`.
Integer-resource text tokens dispatch exact`4fb253` as a resource service.

`4ec6b0` owns the by-value stack object and composes frozen
ActorDestruction`4f6584` for empty/refcount/free behavior. Invalid initializer
then runs actual circle deleting destructor and returns0. The manager can
accept a later valid circle. Four-byte `temporaryStringToken` replaces only
that original stack object's identity. No original heap allocation is claimed
for it. Standalone CString tests explicitly compare its field value.

## Integration without editing the frozen module here

Two small root-owned hooks are required inside the frozen executor:

1. Before locks in`4ed800`, delegate a positive gradient to dependency
   identity`4ed800`, preserving this/step. Route that dependency to the new API.
2. Before allocating in`4ec050`, delegate type1 factory this/type/descriptor
   to the new API. It composes the frozen ctor/binds/initializer itself.

Also route already explicit `4c6bd0`, `4c7510` and `4c61f0` services to the
new API. Those need no further frozen-body edits. Other factory kinds remain
explicit unsupported scope. Routing nonpositive pixel steps back to frozen
PlayerFadeRuntime terminates because its new positive hook does not apply.

The test harness demonstrates exactly those two hooks in
`work/player-fade-blend-agent/composed-fade.cpp`, a private copied source.
The production frozen source is read-only throughout this worker task.
Link new source with frozen PlayerFadeRuntime, CArrayRuntime and
ActorDestruction. Headers remain strict C11 and import into Swift.

## Differential evidence

Run `work/test-env/bin/python Tests/compare_player_fade_blend_runtime.py`.
**Final verification: 2,365 complete original calls, 6,129 ordered full-buffer
snapshot events, 6 exact unsafe prefixes, and 2,790 distinct original-image
instruction addresses.** C11, warning-clean C++, Swift import, native ASAN and
UBSAN checks pass.
`work/player-fade-blend-agent/verification.json` records final counts.
Every complete call checks the entire0x120000-byte seeded heap(excluding only
explicit stack scratch identities), all112KiB original mutable globals,
allocation/free history and ordered complete-buffer snapshot hashes at each
platform callback. All substantive new pixel/color/string/lifetime bodies
run their real original instructions.

Coverage includes all four pixel sizes, arbitrary odd shapes, every viewport
edge, signed gradients, retained monotonic steps, direct helper calls,
primary/other/capture aliases and shifted pointers, unequal strides,
nearest-color ties/high-bit masks, actual extracted Level1 palette bytes,
allocation failures, CString literals/resource/empty/header/terminator cases,
manager diagnostics followed by valid reuse, and complete
constructor→palette creation→clock controller→post→deleting destructor chains.
Unsafe allocator-zero writes, missing palette reads and a null owned palette
node are compared as exact reached prefixes and
excluded from completed-call totals. Native ASAN/UBSAN smoke composes positive
sequences in both directions and all four pixel sizes. No device/UI build or
visible fade acceptance is claimed by these headless checks.
