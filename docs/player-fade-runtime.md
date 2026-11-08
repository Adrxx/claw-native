# Original bounded player respawn circle fades

`PlayerFadeRuntime.h/.cpp` recover original `48fae0` fade-out and `48fbe0`
fade-in for the standard scene-owned respawn path, including the complete
circle allocation/initialization, timing controller, indexed pixel writes,
array insertion/removal and effect destruction under explicit platform
services. This is a bounded circle-fade source recovery, not a whole-game
identity claim or a general recovery of every fader.

The original executable is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private evidence lives in `work/player-fade-agent/{fade,core,circle}.c` and
corresponding checked Ghidra logs. Tests execute the pinned instructions,
not the decompiled text, as the differential oracle.

## Entry inventory

| Original entry | Recovered scope / actual arguments |
| --- | --- |
| `48fae0`, `48fbe0` | Whole standard wrapper: owner; centerX,centerY,duration,initialWait; RET16; result0/1 |
| `4ebf80` | Manager constructor, preserving default surface and DD-holder words |
| `4ecbc0`, `4ecb30` | Nine-word circle descriptor / base descriptor constructors |
| `4ec050` | Circle factory type1, explicit or null descriptor; allocation0x206c; initialized success path and composed frozen CArray resize |
| `4c61d0`, `4ec8d0`, `4ed5e0` | Embedded/base/derived constructors with preserved allocation seeds |
| `4ecb00`, `4ecb20` | Default surfaces / DD-holder bindings |
| `4ed670` | Full finite circle initializer, including palette metadata/creation boundary and invalid input returns |
| `4ee6b0` | Maximum radius with exact bounded original CRT numeric profile |
| `4ee820`, `4ee860` | Pre/post capture-surface creation/copy/destruction boundaries |
| `4ed800` | Whole no-blend circle pixel step for gradient width<=0; bytesPerPixel1..4, rows<=1024 |
| `4ee170` | Confirmed gradient<=0 RET24 with no writes; positive-gradient helper remains unsupported |
| `4ec9c0` | Whole runner with **three** arguments(duration,initialWait,pumpFlag), RET12 |
| `4ec990` | Source GetTickCount busy-wait with unsigned `<` deadline |
| `4b8960` | Distinct source clock busy-wait used by bypass branch; cdecl |
| `42d420`, `42d440` | Music pause/resume gates; music transport explicit |
| `4ec600` | Find-first removal, in-place shift, retained unused tail and polymorphic delete |
| `4ed600`, `4ed620`, `4ec920` | Circle deleting/derived/base destruction; embedded resource release explicit |

The derived destructor calls `4bc110`, already established by frozen
PlayerPowerupRuntime as a single RET. The source has no hidden stop-all,
opacity, frame scheduler or Sleep added by this module. Public meaningful
returns are separate from incidental EAX in originally void routines.

## Integration graph

The raw host uses original32-bit tokens and mutable aligned word spans;
lookups may identify interiors and read-only original vtable words.

- Owner `+4` points to application; `+c` parent scene; `+10` captured manager.
- Parent `+1c` must be nonzero. Parent `+4` points to surface controller.
- Controller `+10/+14` point to primary/second image; each image `+2c`
  points to its surface wrapper. These are the actual source pointer chains.
- Surface wrapper `+14` height, `+18` width, `+1c` byte pitch, `+ac`
  bytes per pixel; `+8` is the DirectDraw COM interface.
- The surface COM interface word0 is its vtable; slot `+80` unlocks with
  stdcall arguments(interface,0), represented service receiver0.
- Manager needs ten words. Constructor sets `+10=5141c0`, clears
  `+8/+c/+14/+18/+1c/+20`, and preserves `+0/+4/+24`.
  Those preserved words are default primary/second surface and DD-holder.
- Manager `+10` holds five-word CArray metadata(vtable,data,size,capacity,grow).
  Factory append composes frozen CArrayRuntime `4f5915`; tests execute the
  actual original factory's inlined allocation/copy/zeroing loop.
- Effect allocation has2075 words. Circle VT is `514250`, mapping slots
  `0/4/8/c/10` to `4ed600/4ed800/4ee6b0/4ee820/4ee860`.
- Effect row boundaries occupy `+60` and `+1060`,1024 words each.
  `+2060` gradient width, `+2064/+2068` initialized width/height.

`temporaryDescriptorToken` is caller-owned36-byte synchronous scratch,
replacing a native stack identity. It requires no source allocation event.
The descriptor constructor intentionally leaves word3 untouched; caller
`descriptorWord3` represents that original uninitialized stack seed.
Only that scratch storage is normalized out of the original heap comparison;
all manager/effect/surface/pixel/array storage is byte-complete. Standalone
constructor tests check preserved word3 directly.

Set `globals.bypass` from original `537238`. A nonzero bypass still creates
and inserts the circle object, pauses music, busy-waits for duration, then
clears the reloaded primary surface(`4b97c0(primary,0)`) or copies the
captured second surface(`4b9c50(reloadedPrimary,capturedSecond)`). It resumes
music and deletes the effect. Callback mutation tests verify those reloads.

## Pixel and timing details

Fade-out shrinks a circle, zeroing newly exposed bands. Its left interior
edge has `+1`; fade-in expands a circle, copying bands from the second
surface, with `-1` on its left edge. Copy loops are forward byte loops.
Full outside-circle fade-out rows clear **width bytes**, even for multi-byte
surfaces; this original quirk and untouched pitch padding are preserved.
Both surfaces lock through `4b9730(surface,0)` and unlock in original order.
Previous-step and computed pixel tokens remain in the effect after a step.
The ordinary path has no palette blend(gradient width0).

Radius computation re-reads width/height from the surface, not cached effect
fields. The CRT power helper uses x87 FYL2X/F2XM1, which is not equivalent to
multiplication when later truncated: at640x480 center320,240 the original
radius is **399**, while exact squares would give400. Embedded double bit
patterns cover actual original `4f1b30(integer,2)` results for0..1024,
captured by `work/player-fade-agent/capture-squares.py`. This is a bounded
numeric adaptation of original results, not a general CRT pow port.
Subsequent square roots and FTOL use the original double/truncation domain.
Coordinates x,y,width-x,height-y outside0..1024 report native fault2.

Runner order is max-radius, pre, step0, initial busy-wait, start timestamp,
clock-driven positive changed intermediate steps, final maximum step, final
FPS word `+34`, post. It converts start/duration/max steps to **float32**,
then performs the clock arithmetic in double. It does not wrap timestamp
subtraction there; its final elapsed FPS subtraction does wrap UInt32.
`5141ec` is float bits`3a83126f`. Repeated computed steps produce no draw.

Import slot`546a24` is GetTickCount; bypass clock slot`546df0` remains a
separate service identity. Both wait bodies read at least twice and use an
unsigned wrapped absolute deadline with `<`, differing from the frozen
GameTiming wait's `<=`. The runner optionally invokes DD virtual`+58` with
(interface,1,0) before intermediate steps when pumpFlag!=0; both respawn
wrappers pass0. There is no Win32 event pump or renderer call in this body.
Any actual physical surface visibility/presentation remains the graphics
adapter's responsibility; no host animation opacity is inferred.

## Evidence and boundaries

Run `work/test-env/bin/python Tests/compare_player_fade_runtime.py`.
Final result: **1,866 complete original calls, 8,008 ordered full snapshot
events, 16 exact failure/domain prefixes, 1,025 independently executed
original CRT square profiles, and 1,513 distinct original-image instruction
addresses**. C11 header, warning-clean C++ and Swift import checks pass.
Native ASAN/UBSAN smoke executes both640x480 wrapper directions with padded
rows and retained manager lifetime.
The final verification report is in `work/player-fade-agent/verification.json`.
The oracle compares the entire0x120000-byte seeded heap, all original112KiB
mutable globals, allocation/free history, and ordered full-buffer snapshot
hashes at every declared callback. Rect containment uses the actual Win32
contract adapter; all original finite controller/pixel bodies execute.

Coverage includes randomized odd dimensions, arbitrary centers, pitch
padding,1..4-byte surfaces, retained monotonic circle steps, all manager
array growth shapes, first-match removal/duplicates/nulls, palette ownership,
complete640x480 fade wrappers including corners, mutation of parent surface
and bypass flag, float32 high-bit clocks, wrapped deadlines, and retained
fade-out/fade-in pairs using source803a durations1250/1000 and wait500.

Physical allocation/free, DirectDraw lock/unlock/capture/clear/copy,
embedded graphics-resource deletion, palette creation, clock transport and
music pause/resume are explicit source-identity services. Physical failure
return values are not promoted to invented wrapper gates.

Positive-gradient pixel blending and other factory types0/2/3 are not
recovered. Invalid circle-factory descriptors/failed initialization stop
before original diagnostic CString construction; no safe normal return is
claimed. Null allocation/dereference or unsupported row/geometry/buffer
sizes report native fault1/2. A stalled clock or duration0 can prevent the
original from returning; `maximumClockReads` bounds native work, with exact
prefix comparisons, rather than pretending the original safely finishes.
Factory diagnostics and positive-gradient source prefixes are tested
separately and are excluded from complete-call totals.
