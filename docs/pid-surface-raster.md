# Original uncompressed PID surface raster

This is a bounded recovery of the original v1.0 **8-bit uncompressed PID image-load path**, including its surface color-key setup. It is not proof of the full game, palette/RGB conversion, DirectDraw rasterization, lighting, or 16/24/32-bit image loading. The resource set remains the local CD-rip CLAW/Level1 set, whose identity with the retail executable's original assets has not been established.

Executable: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The native algorithm was recovered from this binary's instructions, not copied from a reference decoder. Ghidra outputs in `work/surface-raster-agent/` are private scratch evidence.

## Recovered route

The full observed chain is:

1. Image loader **0x4d2410**, resource type 4, takes the surface path when PID header flags at +4 lack 0x20. It writes PID signed offsets +0x10/+0x14 into image +0x20/+0x24. Its fourth parameter controls whether the current color key is used; zero supplies key -1.
2. Surface factory **0x4bc520** allocates 188 bytes, executes the constructor stores and original string constructor 0x4f54ea, and dispatches surface vtable `0x513690 + 0x24` to **0x4bf9c0**.
3. **0x4bf9c0** adds creation flag 0x40 and calls PID loader **0x4bf310**.
4. **0x4bf310** rejects width not divisible by four, observes the requested manager bit depth at +0x474, and chooses **0x4babe0** when it is eight. PID flag 4 requests system memory by changing creation flags; flag 2 clears the system-memory flag. Header flags 8, 16 and 64 do not change the 8-bit raster decoder at this boundary.
5. Surface setup **0x4b9180** writes dimensions then calls original **0x4b9380**, which makes DirectDraw CreateSurface/GetSurfaceDesc calls and derives surface byte widths and pitch state.
6. **0x4babe0** queries original width/height getters 0x4bb040/0x4bb050, locks through original **0x4b9730**, computes each row offset through **0x4bb0f0**, writes decoded bytes, and unlocks through **0x4bb0e0**.
7. If PID flags & 1, **0x4bf310** calls **0x4b9990**. It sets surface +0xb8 to one for a key other than -1, or zero for -1. It submits the identical low/high key through original **0x4b9950** to surface COM vtable +0x74, flags **8**.
8. Factory registration **0x4bc490 → 0x4f51c5 → 0x4f5692** links the surface into the manager's list. The image loader copies width, height, floor half-width/height and sets image surface-kind +0x28 to 0x11 for an enabled key or 0x10 otherwise.

The original mode setter **0x42c640**, called with mode eight, writes **zero** to global color key `0x543170`. Tests execute that routine to verify the constant; it is not inferred from sprite appearance. The global is mode-dependent for other bit depths, which are outside this API.

## Exact row grammar

Each row begins at `lockedPixels + y * surfacePitch`. The decoder consumes the encoded stream continuously across rows, but starts a fresh width counter and destination row pointer for every row.

- `(token & 0xc0) != 0xc0`: write the token as one palette index, including literal zero, 0x80 and 0xbf.
- `(token & 0xc0) == 0xc0`: consume the following byte as the index and write it `token & 0x3f` times. Values 0xc0 through 0xff all take this route.
- **0xc0 is a two-byte zero-length run.** It consumes the following index and does not advance the destination. It is not literal palette index 192. A nonzero run such as `0xc1,0xc0` represents a literal index 192.
- The original decoder writes zero-index pixels into the surface; it does not skip them. Transparency is the subsequent optional surface key, unlike the separate compressed PID skip grammar.
- Original loops do not bound-check encoded reads or reject a run that overshoots a row. The native API explicitly rejects truncation and row overshoot instead of reproducing unsafe writes. Zero-length runs remain accepted when the bounded stream eventually supplies enough pixels.

Embedded palette flag 0x80 copies the final 768 bytes into original global palette storage. In the observed eight-bit surface path it does not alter the decoded palette-index bytes. Native input validation excludes those bytes from the raster stream; conversion from indices to RGB remains the host's separate responsibility.

## Stable native API

`Sources/PIDSurfaceRaster.h/.cpp` exports:

```c
uint32_t claw_pid_decode_surface_raster8(
    const uint8_t *pid, size_t length, uint32_t useColorKey,
    uint8_t *output, uint8_t *coverage,
    size_t capacity, size_t rowStride,
    ClawPIDSurfaceRasterInfo *info);
```

The whole PID is passed, including its 32-byte header and optional palette trailer. `output` is the decoded byte-index raster, including index zero. `coverage` is the host's alpha mask corresponding to the loaded surface key: it is zero only when PID flags & 1, `useColorKey != 0`, and the decoded index is zero; otherwise it is one. This coverage-to-alpha adaptation represents the observed key setup; native CoreGraphics pixel blitting is not the original DirectDraw implementation.

`ClawPIDSurfaceRasterInfo` has fields `width, height, offsetX, offsetY, consumed, colorKeyEnabled` in that order. `consumed` is the offset immediately after the required raster stream, excluding an optional palette trailer or unused trailing bytes. Signed offsets are preserved.

Output planes and input must not alias. Row stride must cover width and capacity must cover `rowStride * height`; padding remains untouched. Both planes and info remain unchanged on failure because the stream is fully validated before writing. Positive dimensions at most 4096, and a complete embedded palette are native safety constraints; the original loader does not enforce all of these bounds. Width divisibility by four is an actual original rejection. Flag 0x20 is rejected so compressed decoding continues through `PIDRaster`.

## Original-instruction comparison

`Tests/compare_pid_surface_raster.py` executes **the complete original 0x4d2410 image-load entry**, not just a reimplementation of its inner loop. The only replaced instructions are entrypoints for these host boundaries:

- CRT allocator **0x4f63ec**, audited size 188 bytes, supplies caller-owned surface memory.
- DirectDraw CreateSurface COM +0x18 returns the adapted surface object after validating original requested width/height/flags.
- DirectDraw GetSurfaceDesc COM +0x58 supplies an eight-bit descriptor and caller-selected pitch.
- DirectDraw Lock COM +0x64 validates the original arguments and supplies the same descriptor and output memory.
- DirectDraw SetColorKey COM +0x74 validates flags 8 and identical low/high key values, recording zero or -1.
- DirectDraw Unlock COM +0x80 validates the exact object/null arguments.

No pixel decoder, image loader, geometry setter, surface initialization/lock wrapper or list-registration routine is stubbed. A preexisting free-list node avoids unrelated MFC block allocation, but all original node/link routines still execute. An adapted COM surface is not evidence that the DirectDraw driver itself has run.

Verified:

- **All 221 actual uncompressed CLAW/Level1 PIDs**, including **all 113 Level1 tiles**, with flag distribution 1:64, 2:70, 3:87.
- **912,340 actual source pixels**, including **312,632 zero indices**. Actual inputs have no 0xc0 runs or row overshoots. All flag-2 opaque assets have no zero indices, so the earlier unconditional zero-alpha behavior happened to agree on this asset set while differing on synthetic opaque zeros.
- **1,000 generated rasters** plus explicit literal-zero, literal 0x80/0xbf, index >=192, 0xc0 zero-run, repeat, row-boundary, header flag and embedded palette probes.
- Color-key parameter enabled and disabled, every full surface write, pitch padding and guard bytes, input immutability, image width/height/halves/offset/kind, surface keyed state, allocation size, exact COM arguments and original registration links.
- Native unsupported/malformed/truncated cases reject without output mutation. An independent original PID method call verifies non-four-aligned width rejection before surface creation.
- **2,466 complete original image-loader calls**, **1,477,152 source pixels**, **688 original instruction addresses**, excluding adapter and stop-entry addresses. Synthetic and actual totals count a raster once although both key modes execute.

Commands:

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -dynamiclib Sources/PIDSurfaceRaster.cpp -o work/surface-raster-agent/libPIDSurfaceRaster.dylib
work/test-env/bin/python Tests/compare_pid_surface_raster.py Original/claw10/CLAW.EXE work/surface-raster-agent/libPIDSurfaceRaster.dylib --assets App/GameData
clang++ -std=c++17 -Wall -Wextra -Werror -c Sources/PIDSurfaceRaster.cpp -o work/surface-raster-agent/PIDSurfaceRaster.o
xcrun swiftc -import-objc-header work/surface-raster-agent/Bridge.h Sources/ClawAssets.swift Tests/PIDSurfaceRaster/main.swift work/AnimationEngine.o work/raster-agent/PIDRaster.o work/surface-raster-agent/PIDSurfaceRaster.o -lc++ -o work/surface-raster-agent/swift-surface-raster-tests
work/surface-raster-agent/swift-surface-raster-tests App/GameData
```

The Swift interoperability check also passes all 221 actual sprites / 912,340 pixels against `ClawSprite` RGBA with the current palette. It checks zero-run and optional-key semantics through the new C API. Transparent RGB bytes are immaterial to the key/alpha convention and are not required to match. This check does not establish binary-original palette conversion. The parent agent owns integration into the actual application, the bridge header and project file, plus device/native UI validation.

## Remaining boundaries

16-bit palette conversion, 24/32-bit surface paths, resource loading/failure cleanup beyond these successful eight-bit inputs, actual DirectDraw surface allocation/driver rendering, clipping/mirroring surface blits, palette selection/gamma/lighting, and whole-scene projection remain separate work. The previously observed **compressed horizontal blitter's one-column-right quirk** remains documented in `docs/pid-raster.md`; this surface decoder neither resolves nor erases that separate behavior.

2026-10-12 correction: the first PID header word is opaque. Original disc Flare/LFX use99999; whole original loader and normal draw comparisons confirm acceptance. Native geometry, flag, stream and capacity checks remain. See native-player-projectile-host.md.
