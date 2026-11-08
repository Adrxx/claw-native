# Layered Level 1 asset rendering

This is a native asset-preview component, not recovered original rendering or
playable Claw. No actor, enemy, object, lighting, audio, or gameplay behavior is
invented here. The 1,479 parsed Level 1 objects remain absent from this preview.
The local CD-rip assets have not been proved equivalent to the original-labeled
v1.0 executable's retail assets.

`Sources/ClawLevelScene.swift` loads the three WWD planes and their named tile
sets using `LEVEL1/PALETTES/MAIN.PAL`. The earlier Action-only view is now a
layered scene. The preview keeps the animation tab functional.

| Plane | Tile set | PID files | z | Camera x/y movement | Wrapping |
| --- | --- | ---: | ---: | --- | --- |
| Background | BACK | 64 | -999 | 50% / 50% | x and y |
| Action | ACTION | 41 | 0 | 100% / 100% | none |
| Front | FRONT | 8 | 9000 | 150% / 125% | x |

The WWD values come from the existing parser. Plane flag meanings are referenced
from OpenClaw `libwap/libwap.h` at pinned commit
`5ee5740ca98377c76b13b50c84f610b0066a4717`: main plane 1, no-draw 2, x wrapping 4,
y wrapping 8. No OpenClaw gameplay source is used. Applying percentages to the
camera, wrapping tile indices, and sorting ascending z are renderer inferences
from this metadata; they have not been compared against the original executable.
No claim is made about original camera centering, integer rounding or viewport
resolution. The preview uses its actual Canvas dimensions to center and clamp
the camera to the main plane.

Every plane retains all its named image sets in WWD order. Missing tile IDs and
ambiguous IDs across sets are rejected rather than silently picking a set. Both
empty cell sentinels are skipped. Lower 16 cell bits select the image; actual
Level 1 cells have no additional non-sentinel flag bits. Semantics of additional
draw flags, automatic tile sizing and WWD fill colors are not reconstructed.
All 113 current tile PIDs are 64 × 64 with zero signed offsets; they draw at their
native size. `ClawSpriteImage` keeps the decoded PID with its CGImage, including
signed offsets and existing transparent pixels. The PID decoder's transparency
rules are unchanged and have not acquired additional original-renderer proof.

## Reusable interface

```swift
let scene = try ClawLevelScene(root: gameDataURL) // or .bundled()
let renderer = ClawLevelRenderer(scene: scene)
let camera = renderer.cameraCentered(at: playerPosition, viewport: size)
let sprite = ClawSceneSprite(image: image, position: playerPosition,
    origin: suppliedOrigin, mirrored: facingLeft, z: actorZ)
let commands = renderer.commands(camera: camera, viewport: size, sprites: [sprite])
```

`position` and `camera` use world coordinates; `origin` is the image coordinate
that coincides with the actor position. The caller must supply this origin.
The decoded sprite initializer also accepts `ClawSpriteImage` but still requires
an explicit origin. This avoids guessing whether the original game adds or
subtracts a PID offset from an image center. Mirroring reflects the supplied
origin around the actor position and flips the image pixels. Actor draws use
the main plane's camera movement, independent of background parallax.

Each `ClawSceneDraw` contains image, screen rect, mirror flag, z, optional plane
index, and optional tile ID. Equal-z order is stable: plane tiles precede supplied
sprites, whose supplied order is retained. This is an explicit preview convention,
not evidence for original equal-z object sorting. The parent's character view
can consume these commands without depending on the asset-preview SwiftUI view.
`ClawLevelRenderer.draw(_:in:)` renders into a top-left, y-down CGContext; it
converts CGImage orientation and disables interpolation. Canvas callers should
draw non-mirrored commands directly and reflect mirrored commands around their
screen rectangles. The existing level preview contains only tile commands.

`commands` rejects nonfinite inputs, viewports above 16,384 pixels per dimension
and camera coordinates outside ±1e12. These native bounds avoid integer overflow
and unbounded preview allocation; they do not claim original invalid-input parity.

## Validation

Headless native Swift checks use the actual local Level 1 WWD and all 113 PIDs:

```sh
xcrun clang++ -std=c++17 -c Sources/PIDRaster.cpp -o work/PIDRaster.o
xcrun clang++ -std=c++17 -c Sources/PIDSurfaceRaster.cpp -o work/PIDSurfaceRaster.o
mkdir -p work/render-agent
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h Sources/ClawAssets.swift Sources/ClawWorld.swift Sources/ClawLevelScene.swift Sources/ClawLevelRenderer.swift Tests/Rendering/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o -lc++ -lz -o work/render-agent/render-tests
work/render-agent/render-tests App/GameData work/render-agent/level1-layers.png
```

The checks cover exact plane resources, 1,084 emitted tile draws inverse-projected
to source WWD cells across five cameras, negative wrapping, both background axes,
foreground x-only wrapping, z order, camera edges and large-viewport clamping.
An asymmetric 2 × 2 PID fixture checks signed metadata, explicit actor origins,
mirrored placement and rendered pixel orientation/alpha. Its transparent pixel
must preserve a white background; its red/green/blue pixels must flip correctly.
The generated 960 × 600 PNG at Level 1 spawn was visually inspected and composes
background, Action and foreground layers. This is headless rendering evidence;
native app build and GUI validation belong to the orchestrating parent agent.
No original-renderer instruction comparison, simulator acceptance or physical
iPad acceptance is established by these checks.
