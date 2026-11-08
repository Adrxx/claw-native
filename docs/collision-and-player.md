# Original v1.0 collision and player recovery

All instruction addresses below select the fingerprinted original-labeled v1.0
CLAW.EXE, SHA-256
350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263.
The native app remains a preview. Full movement/collision response and physics
are now recovered separately; player state transitions and gameplay integration
are still unfinished.

## Level data and native storage

ClawWorld now preserves every 71-word WWD object record and its four strings,
plane flags/parallax/z metadata, and type-1/type-2 tile collision descriptions.
This parser is reference-informed by pinned OpenClaw libwap, not a reconstruction
of the original WWD loader. Original binary tile loaders are used to check the
resulting collision-description fields.

The CD-rip Level 1 asset contains 1,479 Action objects and 938 descriptions:
905 single-attribute tiles and 33 rectangle tiles. All three planes, all 40,320
cells, every object word/string, image-set names and every description field
agree with an independent raw-WWD dump. Asset identity with v1.0 remains unknown.
These objects are parsed but not instantiated or rendered.

Sources/ClawCollision.swift selects the plane whose flags contain bit 1,
preserves unsigned cell bits, builds contiguous row offsets and passes native
storage to recovered point, movement/resolver and ground-placement calls. The
adapter rejects out-of-range IDs and
unsupported plane dimensions. This is a native malformed-input extension.

## Collision instructions recovered

- 0x4cddc0: a single-attribute tile returns its runtime attribute and ignores x/y.
- 0x4cde10: a double-attribute tile checks signed, inclusive rectangle edges,
  returning its inside or outside attribute.
- 0x4cd740: sample an actor's foot at x + supplied offset, y + actor bottom.
  Additions wrap at 32 bits, then signed coordinates clamp to the plane bounds.
  Original row offsets address the cell array. Empty cells 0xffffffff and
  0xeeeeeeee return zero; other cells select description ID from the low 16 bits.
  The tile's virtual method samples local coordinates.
- 0x4d5840 and 0x4d5c30: original single/double tile-description loaders copy
  WWD width, height, attributes and rectangle into their runtime fields.

Native source: Sources/TileCollision.h/.cpp. Type 3 is not present in the Level 1
reference and is rejected by the native loader; it has not been recovered.

Tests/compare_tile_collision.py executes those actual instructions with no
stubbed callees. Measured results:

- 5,000 generated tile samples, including signed limits and inclusive boundaries.
- 5,000 generated world samples, including wrapping, signed clamping, shuffled
  runtime row offsets, cell flag bits and both empty sentinels.
- All 938 original tile loaders and their boundary samples.
- 10,000 original/native samples in the CD-rip Action plane, reaching attributes
  0, 1, 2, 3 and 4.
- 1,024 additional Swift/C adapter queries compared with the original routine.
- Complete actor state remains unchanged by the point query. Complete description
  state remains unchanged by sample calls. 135 original instruction addresses
  were reached.

Reproduce the data and collision checks:

```sh
xcrun clang++ -std=c++17 -c Sources/PIDRaster.cpp -o work/PIDRaster.o
xcrun clang++ -std=c++17 -c Sources/PIDSurfaceRaster.cpp -o work/PIDSurfaceRaster.o
xcrun clang++ -std=c++17 -c Sources/AnimationEngine.cpp -o work/AnimationEngine.o
xcrun clang++ -std=c++17 -c Sources/TileCollision.cpp -o work/TileCollision.o
xcrun clang++ -std=c++17 -c Sources/CollisionResponse.cpp -o work/CollisionResponse.o
xcrun clang++ -std=c++17 -dynamiclib Sources/TileCollision.cpp -o work/libTileCollision.dylib
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h \
  Sources/ClawAssets.swift Sources/ClawWorld.swift Sources/ClawCollision.swift \
  Tests/World/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o work/TileCollision.o work/CollisionResponse.o \
  -lc++ -lz -o work/world-tests
work/world-tests Original/cd-assets work/swift-world.json
work/test-env/bin/python Tests/compare_tile_collision.py Original/claw10/CLAW.EXE \
  work/libTileCollision.dylib --world Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD \
  --swift-world work/swift-world.json
```

## Player registration and direction

The original registration at 0x401007 references "CaptainClaw" at 0x522e80
and registers callback 0x415df0. CaptainClawHit registers 0x41ce80. The player
private allocation contains 78 words (0x138 bytes).

Ghidra's automatic function discovery did not create the callback at 0x415df0.
research/ghidra/RecoverRegisteredCallback.java explicitly defines observed
entries and exports pseudocode. It checks the program's executable hash before
using these version-specific addresses and modifies only its local analysis
database. Successful decompilation is not successful native reconstruction.

Sources/PlayerEngine.cpp recovers complete direction routines 0x418080 (left)
and 0x418120 (right). They change render-flag bit 2, mirror movement/hit/attack
rectangles with unsigned negation, skip rectangles whose left field is
0x80000000, update facing and reset private idle timer to 1500. Original nonzero
facing checks and no-op cases are preserved.

Tests/compare_player_direction.py verifies 20,000 chained calls against those
unmodified original instructions. Entire actor/private buffers agree; 72
instruction addresses were reached. No callees or stubs are involved.

```sh
xcrun clang++ -std=c++17 -dynamiclib Sources/PlayerEngine.cpp -o work/libPlayerEngine.dylib
work/test-env/bin/python Tests/compare_player_direction.py \
  Original/claw10/CLAW.EXE work/libPlayerEngine.dylib
```

## Physics and integer displacement

Sources/PlayerPhysics.h/.cpp recover original global constructor 0x415ab0,
initialization 0x420a40, velocity limits 0x420ad0, full three-axis integration
0x403b40, and pixel/residual conversion 0x420cd0/0x420d50. Constructor fields
that the original leaves untouched remain untouched. Integration preserves
elapsed updates while stopped, delta/position limits, velocity recomputation
and the original one-sided maximum-velocity check. Pixel conversion preserves
signed truncation, low-32-bit wrapping and the original fractional operation
order. It is not a standard round-to-nearest pixel accumulator.

Tests/compare_player_physics.py compares complete buffers and scratch globals:
1,000 constructor/initialize/limit cases, 5,000 integration cases, 10,000 pixel
conversions and 23,040 chained updates with 46,080 pixel conversions. The tests
execute original CRT precision setup and all original helper callees. No stubs
are involved. This covers finite game-scale and boundary inputs, not all
nonfinite values or x87 extended-exponent behavior.

The target-velocity routine 0x420dd0 is also recovered. 5,000 generated calls
and 1,000 original jump targets compare complete state and floating return.
Gravity 2250 and a target 45 pixels upward choose velocity -450, overriding
earlier constants written by surrounding player code. An initial comparison
caught a rounding-order difference in the decompiler's reassociated sums;
native code now follows instruction order. Zero target distance retains the
original return of 1.0 and clears velocity. No original callees are stubbed.

## Movement and collision response

Sources/CollisionResponse.h/.cpp recover the full movement splitter 0x4cbb60,
resolver 0x4cbcd0 and its ground, falling, ceiling and climbing responses
0x4cbe30/0x4cbff0/0x4cc1b0/0x4cc2b0. Helpers preserve side rejection, floor
and ceiling backtracking, hazards, ladder-top transitions/alignment and ordered
platform acquisition/support. Original manager constructor 0x4cad42 selects
maximum movement steps of 64. Portable actor tokens replace x86 pointers;
platform ordering remains unchanged.

Tests/compare_collision_response.py compares 5,000 generated full-response
calls, 5,000 calls using CD-rip Level 1 and 1,024 Swift/C adapter calls against
the original. Complete original actor/platform buffers agree without callee
stubs. Directed landing, ladder-top and retained/lost platform support exercise
all 18 required original resolver/helper entries. These are routine calls with
supplied actor state, not whole-level input traces or instantiated level objects.

Ground placement 0x4cd800 is also recovered, including its absent-rectangle
sentinel, first-sample ordering and acceptance of attributes 1/2/3. It matches
1,000 generated calls and 1,001 Level 1 calls. The actual starting coordinate
(689,4723) becomes (689,4730); placing the sprite at the WWD start without this
call would change its initial collision state. Another 256 Swift/C ground
placement traces compare against original instructions.

Reproduce physics and full collision checks:

```sh
xcrun clang++ -std=c++17 -ffp-contract=off -dynamiclib Sources/PlayerPhysics.cpp -o work/libPlayerPhysics.dylib
work/test-env/bin/python Tests/compare_player_physics.py Original/claw10/CLAW.EXE work/libPlayerPhysics.dylib
work/test-env/bin/python Tests/compare_physics_retarget.py Original/claw10/CLAW.EXE work/libPlayerPhysics.dylib
xcrun clang++ -std=c++17 -dynamiclib Sources/CollisionResponse.cpp Sources/TileCollision.cpp -o work/libCollisionResponse.dylib
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h \
  Sources/ClawAssets.swift Sources/ClawWorld.swift Sources/ClawCollision.swift \
  Tests/Collision/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o work/TileCollision.o work/CollisionResponse.o \
  -lc++ -lz -o work/collision-tests
work/collision-tests Original/cd-assets work/swift-collision-traces.json
work/test-env/bin/python Tests/compare_collision_response.py Original/claw10/CLAW.EXE \
  work/libCollisionResponse.dylib --world Original/cd-assets/LEVEL1/WORLDS/WORLD.WWD \
  --swift-traces work/swift-collision-traces.json
```

## Next player dependencies

Pseudocode and disassembly are available locally for walking entries
0x417dd0/0x417f20, walking updates 0x4183e0/0x418790, jump entry 0x417590,
jump update 0x41b630 and fall update 0x418b40. These player state transitions
are not yet native implementations. Exact whole-callback input, animation,
weapon and audio dependencies remain to be integrated.

Original CRT initializer 0x4a7ef0 selects 53-bit floating-point precision. The
previous animation harness assumed the x87 reset default of 64 bits, which
produced a one-unit mismatch in a generated case. That assumption has been
corrected and the animation comparisons rerun. See animation-engine.md.
Actual original Windows launch, scheduler, rendering, audio and whole-level
input traces remain outstanding.
