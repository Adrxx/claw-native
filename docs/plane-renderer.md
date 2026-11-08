# Original v1.0 plane renderer

`PlaneRenderer.h/.cpp` recover the complete finite tile loop `0x4d0d50` and world plane/actor ordering `0x4cb9b0`. The ordinary container draw `0x4c91d0` and actor draw dispatcher `0x4c9e00` also execute natively. The image draw and physical DirectDraw wrapper bodies remain declared services. This is command and heap parity over the tested original graph, not complete framebuffer or full-game parity.

The executable invariant is SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. No OpenClaw gameplay or pixel implementation is copied. Private Ghidra evidence is in `work/plane-renderer-agent/{tile,renderer,actor-dispatch,graphics-wrappers,outerframe}.c`; original image-load evidence is in frozen `work/geometry-agent/image-loader.c`.

## API and native graph recipe

Call `claw_plane_renderer_draw(plane,target,host,&fault)` for one plane or `claw_plane_renderer_world(world,target,sceneActors,host,&fault)` for the original ordered world draw. Initialize `fault` to zero. Both return native diagnostic 1 for completion, 0 for a fault; the original functions are void, so these are not incidental EAX claims. A null fault pointer is supported. Fault 1 means an absent graph/service, including original null-image fault paths; fault 2 means the native global one-million-visit bound.

Use the frozen `ClawSceneActorHost` token heap. Its `lookup` returns writable sized word spans for objects, interior pointers, arrays and list nodes. The renderer does not allocate, free, or read clocks. The graphics callback must consume/copy its rectangle synchronously; its four words are writable and callback mutation is observable by subsequent original draws. Do not store native stack rectangle pointers beyond the callback.

| Object | Required fields / storage |
| --- | --- |
| Plane | 86 words; flags +8, tiles +20, row offsets +24, columns/rows +28/+2c, tile width/height +38/+3c, inclusive camera rectangle +40..4c, screen offsets +50/+54, full tile rectangle +60..6c, z +80, shifts +8c/+90, image-manager pointer array +a0 |
| Plane fill FX | Live 25-word DDBLTFX at plane +f4, size word 100; fill color +144 |
| World | At least 25 words; flags +8, plane pointer array +38, count +3c, main plane index +60; normal native world storage is 56 words |
| Scene actors | Container with vtable +0, list head +14, nodes of three words: next, previous, actor |
| Actor | Native 128-word span; z +64, current image +174, draw virtual at vtable +2c |
| Target | Original outer surface object, graphics service receiver at +2c; provide at least 12 words |
| Image manager | At least 27 words; pointer table +14, signed inclusive minimum/maximum image IDs +64/+68; table indexed by absolute low-16 image ID |
| Image | Original allocation is 52 bytes; +0 vtable, +10/+14 width/height, +18/+1c floor half dimensions, +20/+24 signed PID offsets, +28 image kind, +2c uncompressed surface wrapper, +30 compressed object |

Construct and load planes with frozen `WorldPlaneRuntime`; project the original integer main-plane center with frozen `SceneCameraRuntime`. This module consumes those exact plane fields instead of recomputing Swift viewport coordinates. The original gameplay viewport is 640 by 480; renderer entry itself uses the supplied inclusive plane rectangle, and tiny-viewport behavior is tested separately. Preserve original plane array and scene list order rather than sorting anew.

## Graphics service contract

`ClawPlaneGraphicsCall` contains original function identity, receiver, four arguments, and a writable four-word rectangle. Stack rectangle identity is deliberately adapted to `rectangleToken = 0`; a live interior tile rectangle keeps `rectangleToken = plane + 0x60`. No fabricated native stack address is claimed.

| Original boundary | Receiver | Arguments | Rectangle |
| --- | --- | --- | --- |
| `4b9d80` | Cached target +2c | destination x, destination y, image +2c source surface, image +28 kind | Source rectangle |
| `4b9ce0` | Cached target +2c | 0 source surface, 0 source rectangle, `01000400` flags, plane +f4 FX token | Destination rectangle |

The graphics callback return is ignored by the original tile loop, including failed HRESULT fixtures. The finite loop preserves subsequent reads after callback side effects. DirectDraw wrapper retry, lost-surface, palette, device, and actual OS blit semantics are not recovered here. Parent can replace these services with its texture/pixel backend while preserving the command contract; that replacement requires separate pixel evidence.

## Tile selection and clipping

Plane flag 2 skips before target/tiles/rows are accessed. `FFFFFFFF` skips a tile; `EEEEEEEE` emits a fill. `FFFFFFFE` is not a skip sentinel in this body. The high 16 bits of a tile choose the plane's image manager; the low 16 bits choose its image ID. They are not flip bits. IDs are range checked using signed manager bounds and then resolved from the absolute-index image table. A rejected ID or null image is dereferenced by the original executable; native reports graph fault 1. The three invalid-image tests are original unmapped-null-page fault witnesses, not successful whole-call comparisons.

The complete first/middle/last row and column loops produce nine regions. First/last edges use clipped mutable local rectangles; the interior uses live plane +60..6c. Source rectangles determine fill destination extents. Rectangle mutations persist wherever original storage persists. Initial shifts/counts/edge widths are cached; subsequent tile width/height and later-row screen-x reads remain live. The target graphics receiver is cached once per plane draw.

Columns and rows wrap on reaching their respective counts even when wrap flags 4/8 are clear. The first row and column are not modulo normalized. The loops always emit both first and last edges, even when a viewport fits one tile and middle counts are negative. Tests preserve those duplicate/overlapping commands rather than imposing a new clipping algorithm. Negative/edge camera fixtures first pass through the recovered follow/clamp routine; arbitrary invalid direct row pointers remain outside successful execution.

## Actor ordering and exact dispatch identities

When world flag 1 and a first plane are present, the first plane draws before every actor. For each following plane, actors with signed z strictly less than that plane's z draw first; equal-z actors remain until after that plane. Remaining actors draw after the final plane. List next is saved before each actor callback, preserving traversal despite current-node mutations.

The fallback draws planes through the main index inclusive, invokes container virtual +28, then draws the remaining planes. Default container `513c20` resolves +28 to `4c91d0`; animated actor `5137f0` resolves +2c to `4c9e00`. The latter reads image pointer +174, skips null, and invokes image virtual +38 with arguments `[actor,target]`. Other container/actor/image vtables resolve their actual table entry through heap lookup and dispatch through `scene.call`.

The PID image vtable is **513a70** for both compressed and uncompressed images, and virtual +38 is **4d2890**. This module dispatches that body as an explicit `scene.call` with image receiver and actor/target arguments; frozen SpriteGeometry/PIDBlitter/PIDSurfaceRaster can be composed by the parent. `4ce3d0` allocates 0x34 bytes, initializes vtable 513a70, ID, parent, and null surface/compressed fields. A native 64-byte header is an explicit storage extension, not original allocation parity.

Original uncompressed loader `4d2410` stores a surface wrapper at image +2c and selects image kind +28 as `0x11` if surface +b8 is nonzero, otherwise `0x10`. Compressed route `4d25e0` allocates a separate 0x28-byte object through `4bfbf0`, stores it at image +30, and selects kind `0x11`; the PID image vtable does not change. Image +28 must not hold a presentation/surface token.

Plane vtable 513d40 contains 12 entries; tile draw is not one of them. Its +24 entry is `4d0800`, an alternate initializer, while +28 is the WWD loader `4d0450`. Earlier guesses that +24 drew tiles were discarded after original body/caller inspection.

## Evidence and limits

Run `work/test-env/bin/python Tests/compare_plane_renderer.py`. The optimized warning-clean suite executes actual original bodies under Unicorn and compares complete 1,310,720-byte heaps by SHA-256 at every ordered callback and return, plus exact callback identities, receivers, arguments, mutable rectangles, and heap/interior rectangle tokens. Only adapted stack pointer identity and void-function incidental EAX are excluded. Final evidence in `work/plane-renderer-agent/verification.json`:

- 394 complete original calls, 51,876 ordered full-heap events, 880 original-image addresses.
- 21 actual Level 1 plane draws across all three planes and seven recovered camera positions.
- 64 retained actual Level 1 whole-world draws, with all three plane graphs and changing camera positions.
- Three separate original invalid-image fault witnesses.
- Generated multi-manager/sparse IDs, fill/skip/no-draw flags, all nine clipped regions, wrapping independent of flags, 1/63/64/65/127/128 pixel viewports, alternate polymorphic dispatch, equal-z ordering, saved-next behavior, live rectangle/size/offset/header mutation, and ignored graphics failure returns.

Actual Level 1 fixtures load the real WWD records/tile arrays through frozen native WorldPlaneRuntime, and use the real 113 uncompressed PID metadata headers. Graphics surface identities and kind `0x11` are declared fixture resource services; the suite does not claim original full surface creation, palette or texture allocation. Actual world tile histories clear fixture actor images; separate generated actor graphs verify the actor/image dispatch and ordering.

C11 header compilation with `-Wall -Wextra -Werror` and native Swift C bridge execution pass. The Swift smoke verifies exact nine-region clip commands, high-16 manager selection, live rectangle token, fill FX, ignored error return, and flag-2 skip with absent tile pointers. No Xcode, simulator, device, GUI or whole-game acceptance is claimed.

The observed ordinary frame caller `46ac30` renders via `4cb9b0` before optional main-plane `4d2000` residency. That ordering evidence was handed to the independent GameFrameRuntime worker; this renderer does not insert a guessed once-per-UI-frame residency call.

The public `claw_plane_renderer_actor_list(container,target,host,fault)` now
exposes the existing recovered `actors` helper for story/results drawing. No
actor-list body was duplicated or changed. Actual513c20 dispatch composes whole
4c91d0; other container tables retain the existing virtual-routing boundary.
`Tests/compare_actor_list_renderer.py` checks64 unchanged-original4c91d0 calls,
158 ordered complete1,310,720-byte heap snapshots and31 original addresses across
empty/1..6 actor lists, absent images and alternate draw/image callbacks. Original
incidental EAX is excluded for the void RET4 body; source stack cleanup is checked.
