# Original compressed eight-bit pixel blitters

Profile: original v1.0 `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. This recovers palette-index destination writes from the original instruction bodies. It does not establish palettes/RGB conversion, the DirectDraw driver, other color depths, lighting, the whole renderer or game behavior. Assets are the local CLAW/Level1 CD-rip set, whose identity with original retail resources remains unproved.

The implementation uses binary-derived run loops. No reference pixel/gameplay implementation is copied. Existing decompilations `work/raster-agent/pixel-bodies.c` and `blitter.c` were read without editing the shared or private Ghidra projects. Additional original disassembly verifies the pointer-dependent branch described below.

## Boundaries and dispatch

Original **0x4bffa0** tests only these source-rectangle conditions: `left >= 0`, `right <= width-1`, `top >= 0`, `top <= height-1`. It does not check bottom, ordering, right's lower bound, left's upper bound or destination dimensions. If original image mode +0x14 equals one, it dispatches:

| Flip X | Flip Y | Original body |
| --- | --- | --- |
| zero | zero | 0x4c00b0 |
| nonzero | zero | 0x4c0450 |
| zero | nonzero | 0x4c0920 |
| nonzero | nonzero | 0x4c0cc0 |

All four bodies read surface pitch at +0x1c before locking. They call original lock helper **0x4b9730** with flags zero, then virtual surface unlock +0x80 with the surface object and null rectangle. They do not change the compressed image receiver or supplied rectangles. The dispatcher returns one after the chosen body, including accepted rectangles that result in zero writes; failed dispatcher predicates return zero without locking.

The compressed receiver has width +4, height +8, encoded-data pointer +0xc and bytes-per-pixel byte +0x24. This native implementation covers byte +0x24 equal to one and mode +0x14 equal to one. Other dispatcher pixel-conversion paths remain unsupported.

## Why crop-and-reflect is insufficient

Literal token `1...127` copies that many following palette-index bytes, including zero. Transparent token `129...255` advances by `token-128` without writing. The whole encoded image uses width-completing rows. Literal and transparent runs retain their original boundaries through clipping; converting to a decoded rectangular image and applying an ordinary crop cannot preserve these quirks.

Destination left supplies the byte X origin. Forward Y begins at `destination.top * pitch`; flipped Y begins at `destination.bottom * pitch` and decrements pitch per completed logical row. **Destination right is never used** by these bodies. They do not impose an additional destination rectangle clip.

All horizontal paths start the decreasing X counter at **width**, not width-1. Full-width literal source pixel zero consequently writes at `destination.left + width`, leaving the column at destination.left untouched. Native code retains the extra column even when it lies in usable pitch padding.

| Source branch | Forward X, either Y | Flipped X, forward Y | Flipped X, flipped Y |
| --- | --- | --- | --- |
| left = 0, right = width-1 | Include source.bottom | Include source.bottom | Include source.bottom |
| left = 0, shortened right | Include bottom; right is exclusive | Exclude bottom | Include bottom |
| left nonzero | Exclude bottom; ignore right | Include bottom; ignore right | Include bottom; ignore right |

Forward nonzero-left paths consume whole runs up to the left edge, copy the tail of a literal crossing that edge, then copy subsequent literal runs through the full image width. The requested right edge has no effect. Mirrored nonzero-left paths limit copied count using the decreasing width counter minus source.left, and likewise ignore right.

Mirrored zero-left/shortened-right paths skip runs until the decreasing counter reaches the requested right edge, possibly copy the tail of the crossing literal, then continue consuming/copying runs. The shortened right coordinate is interpreted against that decreasing counter. Logical row completion happens in a separate branch, which explains the bottom-row differences.

### Both-flip top-skip pointer bug

Original **0x4c0cc0**, when source.top is positive, initializes the first row-skip X counter from the **source rectangle pointer** rather than zero. This is confirmed directly by disassembly:

- 0x4c0cf8 loads ESI from the stack's source rectangle pointer.
- 0x4c0d0e / 0x4c0d1f adds transparent/literal run width to ESI.
- 0x4c0d28 compares that value to image width.
- 0x4c0d2d / 0x4c0d2e increments skipped rows and resets ESI to zero.

For an ordinary positive pointer larger than image width, the first token alone counts as a complete skipped row, even if it covers only part of the encoded first row. Remaining skipped rows then consume width-counted runs starting from that mid-row stream position. Rendering can consequently begin mid-row, and subsequent logical rows can cross encoded row boundaries.

`originalSourceRectAddress` in the command preserves this dependency. Use the observed original 32-bit pointer for an exact trace, or a normal positive token greater than image width, such as **0x01003000**, for the usual address case. **Do not leave it zero merely because the host uses a different pointer type.** Low positive pointer tokens also reproduce their different counters; native tests execute original bodies at pointers 4, 37 and 0x7fffffe0. Pathological negative/sign-wrapped pointer counters can force original reads beyond the valid stream; bounded native validation rejects those unsafe cases rather than claiming malformed-input parity.

## Stable buffer API

`Sources/PIDBlitter.h/.cpp` exports:

```c
uint32_t claw_pid_blit8(
    const uint8_t *pid, size_t length,
    const ClawPIDBlitCommand *command,
    uint8_t *output, uint8_t *coverage,
    size_t capacity, size_t rowStride,
    ClawPIDBlitInfo *info);
```

- Input is the whole compressed PID including its 32-byte header and optional palette trailer. Output is a caller-seeded palette-index destination surface.
- `ClawPIDBlitCommand` contains signed `destination` and `source` rectangles followed by uint32 `flipX`, `flipY`, `originalSourceRectAddress`. Rect fields are `left, top, right, bottom`. Supply the recovered compressed draw command's coordinates directly, including its inclusive edges; the blitter applies its branch-specific interpretation.
- Coverage is optional. Literal writes set corresponding bytes to one; transparent skips leave existing coverage untouched. Literal index zero therefore remains a write. Seed coverage with zero for a transparent per-actor canvas, or existing coverage for a shared surface. Input, index output and coverage must not alias.
- Capacity describes the entire usable byte buffer, including padding. Original spill into padding or across nominal rectangle edges is retained if the touched byte addresses remain inside this capacity. A negative destination X can be safe if its physical byte address remains within the buffer. No hidden viewport clipping is added.
- Optional `ClawPIDBlitInfo` returns native diagnostic `consumed` (encoded cursor offset including the header) and `writes` (total literal byte stores, including repeated writes to the same location). These are host metadata, not newly recovered image-object fields.
- Return one means an accepted original dispatch whose bounded writes succeeded. Zero means original dispatcher rejection or native safety rejection. Outputs and info remain unchanged on any rejection.

Native safety extends the original with flag checks, positive dimensions <=4096, a complete bounded stream, rejected zero-length compressed tokens and row-crossing malformed runs, a complete palette trailer when requested, representable pitch/capacity and a dry run that validates every destination touch before writing. The four original source-bound predicates remain separate from these safety checks. Unsafe original out-of-buffer reads/writes, failure-driver behavior, aliasing and overflowing original 32-bit addresses are not compatibility claims.

For an RGBA host, preserve this index/coverage placement before palette conversion. Creating a tightly cropped actor canvas requires room for the mirrored +1 column and any original branch spill. Root owns renderer integration and choosing the actual framebuffer/camera surface origin; this worker does not infer another clipping rectangle or apply a generic reflection.

## Original-instruction checks

`Tests/compare_pid_blitter.py` calls the actual **0x4bffa0 dispatcher and all four bodies**, reading actual encoded bytes. Only these host boundaries are adapted:

1. Original lock helper 0x4b9730 validates ECX is the exact target surface, stack argument zero, then returns caller memory. Pitch remains the supplied original surface field.
2. Virtual surface unlock validates the exact original object/null arguments and returns success.

There are no pixel stubs. An original memory-write hook records every destination address and byte count; native output and coverage are compared against actual original writes. The entire caller buffer, padding and guards are checked, plus source bytes, compressed receiver words and source/destination rectangles.

The suite covers the complete source-rectangle matrix on a 7×4 mixed literal/transparent image, all four flips, explicit pointer-dependent top skipping, 700 generated clipped draws with arbitrary/negative destination offsets, five full/clipped rectangles for every actual compressed CLAW/Level1 PID, dispatcher rejections and accepted inverted/no-op rectangles. All 32 combinations of flip pair, zero/nonzero source left, full/shortened source right and zero/nonzero source top must execute. Separate malformed input and insufficient-capacity fixtures require atomic rejection.

Run:

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -dynamiclib Sources/PIDBlitter.cpp -o work/blit-agent/libPIDBlitter.dylib
work/test-env/bin/python Tests/compare_pid_blitter.py Original/claw10/CLAW.EXE work/blit-agent/libPIDBlitter.dylib --assets App/GameData
```

Passing results: **9,172 complete original dispatcher calls**, **13,989,886 original literal byte stores**, **all 261 actual compressed PIDs**, **four original dispatcher rejection cases**, and **1,600 original instruction addresses**, excluding lock-adapter/unlock-adapter/stop entries. All required branch combinations and unchanged buffer/receiver contracts passed. Memory-write hooks verify actual coverage, so a literal equal to the seeded background cannot hide a missing write.

An additional AddressSanitizer/UndefinedBehaviorSanitizer harness in `work/blit-agent/safety.cpp` passes 10,000 commands containing extreme signed rectangle coordinates and pointer tokens, checking atomic failure and reporting no sanitizer errors. The optimized C++ object also compiles through Swift's C bridge: `work/blit-agent/main.swift` verifies mirrored +1 placement, opaque literal zero and untouched coverage.

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all Sources/PIDBlitter.cpp work/blit-agent/safety.cpp -o work/blit-agent/safety-tests
work/blit-agent/safety-tests
clang++ -std=c++17 -Wall -Wextra -Werror -O2 -c Sources/PIDBlitter.cpp -o work/blit-agent/PIDBlitter.o
xcrun swiftc -import-objc-header Sources/PIDBlitter.h work/blit-agent/main.swift work/blit-agent/PIDBlitter.o -lc++ -o work/blit-agent/swift-blitter-tests
work/blit-agent/swift-blitter-tests
```

This work does not use Xcode, a simulator, GUI or a device. Root owns application integration and independent native/UI validation.

2026-10-12 correction: the first PID header word is opaque. Original disc Flare/LFX use99999; whole original loader and normal draw comparisons confirm acceptance. Native geometry, flag, stream and capacity checks remain. See native-player-projectile-host.md.
