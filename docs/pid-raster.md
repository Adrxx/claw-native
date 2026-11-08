# Original compressed PID palette-index raster

Profile: original-labeled v1.0 `CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
This adds bounded native decoding backed by execution of the original pixel
bodies, rather than copying a source-reference implementation. It establishes
palette-index writes and transparent skips for compressed 8-bit PID images;
it does not establish complete original screen pixels, palettes or DirectDraw.

## Original instruction observations

`0x4bffa0` is the compressed pixel-blit dispatcher. For the original compressed
image mode at +0x14 equal to 1 it selects these pixel bodies:

| Horizontal flip | Vertical flip | Original routine |
| --- | --- | --- |
| 0 | 0 | 0x4c00b0 |
| 1 | 0 | 0x4c0450 |
| 0 | 1 | 0x4c0920 |
| 1 | 1 | 0x4c0cc0 |

Image +4/+8 contain width/height, +0x0c points to encoded data, and byte +0x24
is the number of bytes per pixel. Tests set it to 1 and execute the real 8-bit
pixel loops. Run tokens have these meanings:

- High bit set: skip `token − 128` pixels without changing the destination.
- High bit clear: copy `token` literal palette indices directly, including
  literal index zero. The row completes when its width has been consumed.

Skipped pixels and literal zero are different. The earlier source-reference Swift
decoder treated every index zero as transparent; root has now replaced its
compressed path with the recovered coverage-aware decoder. All 261 actual
compressed PID files have no literal index zero, so their current decoded RGBA
matches the recovered indices/coverage conversion. A synthetic literal-zero
fixture demonstrates the difference explicitly, and now verifies native
integration keeps literal zero opaque while transparent skips preserve coverage. This does not claim that an
RGBA alpha channel exists in the original 8-bit surface; coverage records
whether the original overwrites a destination index.

The full-width original horizontally mirrored pixel bodies begin at x = width,
then decrement. As a result, they place pixels one column to the right of an
ordinary `width − 1 − x` reflection: the first column is left untouched and a
literal at source x = 0 writes at destination x = width. This is reproduced
through unchanged original instructions across generated and actual files.
Pitch padding in the test accommodates that extra column, and guards establish
the exact write region. The native orientation-neutral decoder does not apply
this blitter quirk; generic CoreGraphics mirroring is not equivalent to the
original compressed pixel placement merely because sprite geometry agrees.

Original clipped paths have additional branch-specific boundary behavior.
For example, `0x4c00b0` with source-left zero and a shortened right edge copies
up to an exclusive right boundary, despite a full-width source using inclusive
right. With source-left nonzero it uses a different bottom-row loop condition.
These are observations from instructions/decompilation, not a recovered native
clipped blitter. No native clipping or arbitrary clipped-pixel parity is claimed.

## Stable native API

`Sources/PIDRaster.h/.cpp` exports:

```c
uint32_t claw_pid_decode_raster8(
    const uint8_t *pid, size_t length,
    uint8_t *output, uint8_t *coverage,
    size_t capacity, size_t rowStride,
    ClawPIDRasterInfo *info);
```

The inputs are a whole compressed PID file, separate output-index and
coverage byte buffers, their shared byte capacity, and row stride. Buffers must
be distinct and not alias the input. `rowStride >= width`; capacity must cover
`rowStride × height`. Successful decoding writes one byte per image pixel in
each buffer, preserving padding. A skipped pixel becomes index 0, coverage 0;
a literal pixel preserves its index, coverage 1. `info` preserves width, height,
signed PID offsets and the byte count consumed through the raster. Trailing
data can remain; an embedded palette's final 768 bytes are excluded from the
run stream. This function does not interpret palette colors.

Return 1 means successful decoding. Return 0 means unsupported, malformed,
truncated input or insufficient buffer. The decoder validates the complete
row grammar before any output mutation. Bounds of 4,096 per dimension, rejected
zero-length tokens/row-crossing runs and failure-without-mutation are native
safety extensions, not reproductions of original unsafe malformed-input behavior.
Uncompressed PIDs (flag 0x20 absent) are unsupported by this API. Mirroring,
clipping, RGB palette conversion, 16-bit surfaces and lighting remain separate.

## Validation

```sh
mkdir -p work/raster-agent
clang++ -std=c++17 -dynamiclib Sources/PIDRaster.cpp -o work/raster-agent/libPIDRaster.dylib
work/test-env/bin/python Tests/compare_pid_raster.py Original/claw10/CLAW.EXE work/raster-agent/libPIDRaster.dylib --assets App/GameData
```

Passing comparisons include:

- 2,000 generated valid compressed images and a directed literal-zero/skip
  fixture, with all four original full-image flip modes.
- All 261 actual compressed PIDs from extracted CLAW and Level 1 resources.
- Two different seeded destination backgrounds for every original call, so a
  literal value matching one background cannot hide a missing write.
- Entire destination buffers, pitch padding and surrounding guard bytes.
- Original image object preservation and exact host lock/unlock contracts.
- Native malformed-input rejection with metadata/output preservation.

There are 18,096 complete original pixel calls across 2,714,090 source pixels;
620 original instruction addresses execute, including every required pixel-body
entry. **No pixel decoder or pixel blitter is stubbed.** Only the DirectDraw
lock helper `0x4b9730` and its virtual unlock boundary are adapted: lock is
checked for the exact destination receiver and zero flags, returns a mapped
byte buffer, and uses the supplied cached row pitch; unlock checks the exact
surface receiver and null rectangle. These adapters provide memory, not pixel
results. The original loop reads the actual encoded bytes and writes the full
destination memory itself.

The original renderer's horizontal one-column shift is included in the expected
original writes for mirrored calls. Native decode remains an unflipped raster;
the test verifies how its indices/coverage map to the actual original writes,
rather than claiming it implements a mirrored/clipped blitter.

An additional headless Swift check runs the actual current `ClawSprite` parser
and recovered native decoder on all 261 actual compressed files, comparing
2,209,844 pixels plus sizes/signed offsets. All RGBA values agree for these
assets under the supplied palette; the literal-zero fixture separately records
the source-reference decoder mismatch.

```sh
printf '#include "../../Sources/Claw-Bridging-Header.h"\n#include "../../Sources/PIDRaster.h"\n' > work/raster-agent/Bridge.h
clang++ -std=c++17 -c Sources/PIDRaster.cpp -o work/raster-agent/PIDRaster.o
xcrun swiftc -import-objc-header work/raster-agent/Bridge.h Sources/ClawAssets.swift Tests/PIDRaster/main.swift work/AnimationEngine.o work/raster-agent/PIDRaster.o -lc++ -o work/raster-agent/swift-raster-tests
work/raster-agent/swift-raster-tests App/GameData
```

The Swift fixture now expects the integrated coverage-aware rule: literal zero
is opaque and a skipped pixel is transparent. Source/reference palette agreement is not
an original Windows final-framebuffer comparison. No Xcode build, GUI/device
driving, uncompressed PID parity, clipped blitter recovery, 16-bit conversion,
lighting or whole-game compatibility is established by these checks.
