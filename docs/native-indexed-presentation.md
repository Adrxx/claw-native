# Native indexed presentation

`NativeIndexedPresentation` and `ClawFastIndexedDrawing` replace the Swift
viewport coverage scan and palette/RGBA packing used by `ClawIndexedDrawing`.
This is a native presentation adaptation, **not recovered original code**.
The complete pixel store behavior remains the frozen `claw_pid_blit8` body.
Neither the original blitter nor the previous Swift renderer was edited.

## Stable API and integration

Include `NativeIndexedPresentation.h` in the application's bridging header,
compile `NativeIndexedPresentation.cpp` beside the existing `PIDBlitter.cpp`,
and include `ClawFastIndexedDrawing.swift` in the Swift target. Replace calls
to `ClawIndexedDrawing.draw` with `ClawFastIndexedDrawing.draw`. The Swift
signature and `ClawSceneDraw` output are unchanged. The parent owns those
integration edits; this worker has not changed the bridge or project.

The C11 entry `claw_native_indexed_present8` accepts the encoded PID, an
existing `ClawPIDBlitCommand`, exactly 768 RGB palette bytes and integer
viewport dimensions. It returns a `ClawNativeIndexedImage` containing crop
coordinates, dimensions, byte count and malloc-owned RGBA data. Call with a
fresh result structure, or dispose its previous successful result first.
On rejection or no visible covered pixels the result is all zero. After a
successful call either invoke `claw_native_indexed_image_dispose` or transfer
the allocation's ownership once. The Swift adapter adopts it using
`Data(bytesNoCopy:count:deallocator:.free)`; the CGDataProvider retains that
data for the CGImage's lifetime. Never dispose after that transfer.

## Preserved behavior

The helper creates zero-filled index and coverage buffers with the same
four-byte-aligned row stride and full viewport capacity as the old Swift
implementation, then calls the unchanged bounded blitter. The Swift wrapper
uses the same positive original source-rectangle address `0x01003000`, which
preserves the previously verified both-flip pointer-dependent bug profile.
This is not evidence for different original x86 pointer branches.

The bounds pass scans **every visible covered pixel** in the viewport. It
does not restrict scanning to the command's destination rectangle. Original
clipping stores that spill into neighboring visible rows remain visible;
stores in stride padding remain excluded. Eight-byte zero-group skips are
only a scan optimization; they do not change or omit any visible coverage.
Memcpy loads avoid unaligned access and aliasing assumptions and never read
beyond the visible row width.

The output rectangle encloses the complete visible coverage. Covered index
zero is opaque, just like any other literal index. Uncovered holes inside
the cropped rectangle remain transparent black. RGBA uses the caller's RGB
palette, straight alpha with value 255 for covered pixels, device RGB,
`CGImageAlphaInfo.last`, tightly packed rows and disabled interpolation.
The draw's z value is preserved, mirrored is false, and plane/tile metadata
remain nil, matching the previous implementation.

Valid finite Swift viewport dimensions retain truncation toward zero and
the original integer range 1 through 8192. The fast wrapper additionally
rejects nonfinite dimensions safely; the old implementation would trap when
converting those to Int. Allocation failure also produces nil. These are
bounded host safety extensions, not original-game behavior claims.

## Validation

Standalone private driver:

```sh
zsh work/indexed-presentation-agent/check.sh debug
zsh work/indexed-presentation-agent/check.sh release
zsh work/indexed-presentation-agent/check.sh asan
```

It compiles the actual existing Swift asset, world, scene, renderer and old
indexed drawing sources alongside the new helper. No mock draw or sprite
types substitute for the application types. It compares nil results, draw
rectangles/metadata, CGImage metadata and complete provider RGBA bytes.

Coverage includes all 261 supported compressed CLAW/Level 1 PIDs, five source
clip rectangles each and the complete source in a 640x480 viewport, all four
flip modes. Two GAME LIGHTFX files have signature 99999 rather than the
supported PID signature 10 and are explicitly excluded from this blitter
scope. The driver also exercises an exhaustive source-rectangle matrix on
an odd-sized mixed literal/transparent fixture, 150 generated mixed streams,
negative and edge offsets, odd viewport widths and padding, visible row
spills, rejected and inverted rectangles, all-transparent images, literal
zero, fractional/invalid viewport dimensions and retained provider lifetimes.
Directed instrumentation asserts that spill and padding stores really occur.

The C11 smoke checks ownership/disposal, opaque literal zero, allocation
output metadata and bounded rejection. Debug and release benchmarks compile
both old and new Swift paths with identical Swift flags, and the new C++
helper with the same C++ flags as the frozen blitter. Debug uses no
optimization; release uses Swift `-O` and C++ `-O2`. No device, simulator or
Xcode build is involved. These timings measure standalone presentation, not
whole-game frame rate or device acceptance.

On Apple M4 Max / arm64 macOS, Apple Swift 6.4 and Apple clang 21.0.0:

| Build | Old Swift path, 120 draws | Fast path, 120 draws | Speedup |
| --- | ---: | ---: | ---: |
| Debug: Swift unoptimized, C++ unoptimized | 3.012524 s | 0.009946 s | 302.88x |
| Release: Swift `-O`, C++ `-O2` | 0.042015 s | 0.004976 s | 8.44x |

The benchmark uses the same first 24 actual asset frames, four flip modes,
640x480 viewport and draw locations for both implementations. Each benchmark
performs 120 draws and constructs CGImages. It does not retain all output
images or include asset parsing, Canvas composition, scene execution or
platform frame scheduling.

Debug and release each passed 8,613 byte-complete old/new comparisons, with
552 matching nil results and 39 retained images. The edge/padding fixture
matrix exercises 3,540 visible spill writes and 1,153 padding writes, counted
directly from frozen blitter coverage. Strict C11 and warning-clean C++
compilation and the C ownership smoke also pass. Raw output logs are kept in
the private work directory.

AddressSanitizer additionally passed the same 8,613 comparisons and retained
provider tests with no sanitizer diagnostics. Its benchmark was 6.547095 s
old / 0.054200 s fast (120.79x); this instrumented timing is separate from
ordinary Debug/Release performance.
