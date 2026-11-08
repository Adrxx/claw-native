# Original v1.0 sprite geometry

Binary profile: original-labeled Claw Recluse v1.0 `CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Addresses here do not apply to CrazyHook. This recovers geometry and exposes
original blit arguments; it does not recover the pixel blitters or prove native
CoreGraphics output identical to DirectDraw.

## Confirmed image origin

The original PID header has width at +8, height at +0x0c, signed offsetX at +0x10
and signed offsetY at +0x14. Runtime image fields are:

| Image field | Meaning |
| --- | --- |
| +0x10 / +0x14 | full width / height |
| +0x18 / +0x1c | arithmetic right shift of width / height by one |
| +0x20 / +0x24 | signed PID offsetX / offsetY |
| +0x28 | surface kind passed to plain surface blitter |
| +0x2c | surface pointer |
| +0x30 | compressed-image pointer, zero for surface route |

`0x4d2410` copies the offsets directly for resource types 3/4; type 4 selects PID.
Its compressed PID route is `0x4d25e0`, which constructs the compressed-image
object at `0x4bfbf0` and invokes `0x4bfc50`. The latter reads width and height
directly from the PID header and copies encoded data after the 32-byte header.
At 8 bpp this path does not run the embedded-palette 16-bit conversion branch.
The final stores at `0x4d2676..0x4d269f` set runtime size, floor halves for valid
positive sizes, and unchanged signed offsets. Native
`claw_sprite_set_geometry` covers these six field stores only; surface allocation,
resource loading, compressed data copying, lighting and palette conversion are
outside that helper.

For actor x/y at +0x4c/+0x50 and extra draw displacements dx/dy at +0x10/+0x14,
the original draw location before plane projection is:

| Render mask | x left | y top |
| --- | --- | --- |
| 0 | x + dx + offsetX − halfWidth | y + dy + offsetY − halfHeight |
| 2, horizontal mirror | x − dx − offsetX − halfWidth | y + dy + offsetY − halfHeight |
| 4, vertical invert | x + dx + offsetX − halfWidth | y − dy − offsetY − halfHeight |
| 6, both | x − dx − offsetX − halfWidth | y − dy − offsetY − halfHeight |

These are instruction-derived, not assumptions from the format reference. Image
right/bottom are left + full width − 1 and top + full height − 1. Odd dimensions
matter: the original always subtracts the floor half, including when mirrored.
A generic reflection of `width − origin` differs by one pixel for odd widths.
Native callers can use the recovered command directly instead of inventing an
image anchor.

## Recovered native interfaces

`Sources/SpriteGeometry.h/.cpp` provides:

- `claw_sprite_relative_bounds`: complete `0x4061e0`; returns 0 with no output
  mutation when the actor has no image, otherwise writes
  `[offsetX − halfWidth, offsetY − halfHeight, offsetX + halfWidth − 1,
  offsetY + halfHeight − 1]` and returns 1. Its bounds omit the final pixel of an
  odd-sized image; this original behavior is preserved.
- `claw_sprite_project`: complete `0x4c96d0`, including signed comparisons,
  32-bit wrapping arithmetic and the original one-period wrap adjustment. This
  is not arbitrary modulo wrapping. It then subtracts camera and adds screen
  offsets. The supplied runtime projection fields are not inferred from WWD
  percentage metadata by this routine.
- `claw_sprite_prepare_draw`: `0x4d2890` dispatcher and geometry of all seven
  selected paths: surface both/horizontal/vertical at `0x4d2bb0`, `0x4d2e10`,
  `0x4d3080`; compressed plain/both/horizontal/vertical at `0x4d32e0`,
  `0x4d3550`, `0x4d3790`, `0x4d3a00`. Hide flag 1, blink flag 8, blink countdown
  and visibility toggle `0x10000000` are preserved. Plane projection applies
  when actor flags contain `0x40000`. Clip selection follows original world clip,
  explicit actor clip, or destination dimensions when clip-left is INT32_MIN.

All arithmetic uses unsigned storage and signed comparisons to preserve x86
low-32-bit wrap semantics. Structures adapt original field layouts explicitly;
they are not memory-compatible x86 objects. Fields not represented are untouched
by these original routines under the tested host-adapter contract.

`ClawSpriteDrawCommand.kind` is 0 for no blit, 1 for plain surface, 2 for flipped
surface, 3 for compressed PID. Plain surface calls pass x/y separately; the
command normalizes these into an exclusive destination rectangle. Surface
source/destination rectangles use exclusive right/bottom; compressed calls use
inclusive right/bottom. Actor `drawn` is always inclusive, with original draw
x/y, width/height and status updated independently. No-draw changes only status
to `0xffffffff` after any original blink updates.

`directDrawFlip` adapts original global `0x54310c`. A visible flipped surface
call sets it to mask 2/4/6; other calls leave it unchanged. Compressed horizontal
only and both-flip paths use different source-cropping conventions, preserved
exactly in command arguments. A native pixel adapter must respect these
differences rather than assume source coordinates are interchangeable.

## Verification

```sh
mkdir -p work/geometry-agent
clang++ -std=c++17 -dynamiclib Sources/SpriteGeometry.cpp -o work/geometry-agent/libSpriteGeometry.dylib
work/test-env/bin/python Tests/compare_sprite_geometry.py Original/claw10/CLAW.EXE work/geometry-agent/libSpriteGeometry.dylib --assets App/GameData
```

Passing checks:

- 5,000 complete original relative-bounds calls, including null image and arbitrary
  32-bit field values. No original callees are adapted.
- 5,000 complete original plane-projection calls with arbitrary 32-bit fields.
  No original callees are adapted.
- 10,000 complete original draw-dispatcher calls covering all eight compressed
  and surface paths, hide/blink, signed offsets/displacements, clipping and plane
  projection. Complete actor, image, destination and projection buffers agree,
  along with original flip global and exact blit receiver/arguments.
- Directed 3 × 5 image examples establish odd-size floor-half origins in every
  flip combination for both compressed/surface routes.
- All 482 actual CD-rip PID headers supply 1,928 additional full draw calls.
- All 261 compressed PID files run complete original `0x4d25e0` and its original
  constructor/header/raw-data-copy helper at 8 bpp. Entire image setup buffers
  agree with the field mapping; original copied encoded bytes match the file.
  No PID decoder is stubbed in this check.

For draw calls only these host operations are adapted and their arguments are
logged: surface pixel blits `0x4b9d80`/`0x4b9ce0`, compressed pixel blit
`0x4bffa0`, and Windows `CopyRect`. `CopyRect` copies exactly the original
supplied world rectangle. Blit adapters return success and leave supplied actor,
image, destination and projection objects untouched; pixel surfaces themselves
are synthetic tokens. A separate compressed-loading check adapts CRT allocation
`0x4f63ec`, auditing its 40-byte object allocation and exact encoded-body length.
Tests verify every original function returns and all ten required geometry
entries execute. With asset/loading checks, 1,632 original instruction addresses
are reached. Headless decompilation uses a private APFS-cloned Ghidra project in
`work/geometry-agent`; shared analysis files and devices are untouched.

No original Windows runtime, DirectDraw surface allocation, pixel conversion,
compressed pixel blending, palettes, lighting, scrolling scheduler, equal-z
sorting or final-framebuffer comparison is established. Existing tile-layer
camera percentages/continuous modulo wrapping remain preview inferences;
recovering actor projection does not prove the entire native layered renderer.

The proposed actor-vtable leads were clarified: `0x4c9890` checks validity,
`0x4c9a70` destroys attached logic/resources, and `0x4c9e00` dispatches drawing
through image virtual method +0x38 when image pointer +0x174 is nonzero. It is
not simply an image getter.
