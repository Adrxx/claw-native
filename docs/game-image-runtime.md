# Original v1.0 raw game image runtime

`GameImageRuntime.h/.cpp` adapt original thiscall image and surface objects to the raw token heap used by SceneActorHost. They execute the complete ordinary eight-bit PID load chain and original raw draw-wrapper field/call ownership. Frozen SpriteGeometry supplies the draw geometry; frozen PIDSurfaceRaster supplies uncompressed pixels. The graphics service can compose frozen PIDBlitter, as the joined tests do. Physical DirectDraw COM calls, file/resource loading, container insertion, and polymorphic cleanup remain named services.

The executable is pinned to SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. This is original instruction recovery, not source-port gameplay or pixel copying. Private decompilation evidence is in `work/game-image-agent/{image,surface,pixels,compressed}.c` and frozen `work/geometry-agent/draw-paths.c`. Passing this suite does not establish whole-game equivalence or Apple UI acceptance.

## Stable C11 API

`claw_game_image_entry(function, receiver, arguments, globals, host, &fault, &result)` takes eight raw argument words plus their count. The receiver and every non-stack pointer are original-style 32-bit identities, never truncated native addresses. Host contains the frozen SceneActorHost heap plus a rich service callback. Initialize fault to zero. Return 1 means the supported body completed, including original ordinary failure return 0; result receives the value-returning entry's result. Return 0 means fault 1 (missing heap/service) or 2 (bounded safety/unsupported path). A null fault pointer is supported. Void function incidental EAX is excluded.

| Entry | Receiver | Arguments / native scope |
| --- | --- | --- |
| `4d2890` | PID image | actor, target; full eight-path wrapper through graphics services |
| `4d2410` | PID image | raw data, format, byte length, use key; ordinary eight-bit PID plus compressed metadata |
| `4d25e0` | PID image | raw PID, byte length; full ordinary compressed allocation/metadata/copy path |
| `4bfbf0` | compressed side object | none; exact constructor stores and preserved high bytes |
| `4bfc50` | compressed side object | raw PID, length, low-byte bit depth; 8-bit or 16-bit without embedded palette conversion |
| `4c6130` | compressed side object | effect mode, optional effect value; exact common effect stores/default lookup |
| `4d22f0` | PID image | file name token, use key; file surface service and complete header stores |
| `4ce3d0` | image manager | file name token, image ID, use key; exact factory/header/CArray/min-max order |
| `4bc520` | surface manager | raw data, format, length, creation flags, key; factory and registration |
| `4bf9c0` | surface | manager, raw data, format, length, flags, key; format dispatch; other bitmap codecs are services |
| `4bf310` | surface | manager, raw PID, length, flags, key; full ordinary 8-bit creation/raster/key path |
| `4b9180` | surface | manager, width, height, requested bit depth, flags; original descriptor initialization and virtual creation |
| `4b9380` | surface | manager; original COM creation/description and derived surface metadata |
| `4b9730` | surface | optional rectangle token; original lock/failure/restore/retry ordering |
| `4bb0e0` | surface | none; original unlock call |
| `4b9990` | surface | key; b8 store, exact COM SetColorKey and reporting |
| `4bc490` | surface manager | surface; list-add service and returned-node store |

The interface also dispatches alternate virtual entries as explicit rich services at the same original call boundary. Unknown public entry addresses return fault 2. Argument count is checked before the call. Native checks on lengths, dimensions, source streams, heap spans, allocation failure and iteration/capacity extend original unsafe behavior; malformed, unaligned, negative-ID, null-allocation, or unsupported color-conversion paths are not original successful-return claims.

## Raw object graph

Image vtable is `513a70` for compressed and uncompressed PID images. Original image allocation is **52 bytes**, not 64. A native 64-byte block is a declared storage extension; the implementation preserves its untouched words. Virtual +38 is `4d2890(image,[actor,target])`.

| Image offset | Meaning |
| --- | --- |
| +0, +4, +8, +c | vtable, image ID, flags, parent scene |
| +10/+14 | full width/height |
| +18/+1c | floor half width/height, preserving signed shift behavior |
| +20/+24 | signed PID offsets |
| +28 | image kind `0x10` or `0x11`; not a surface token |
| +2c | uncompressed surface wrapper token |
| +30 | separate compressed object token (40-byte original allocation) |

The projected actor graph is **actor +3c → world +5c → main plane**. Original actor initializer `4d5800` sets actor +3c from actor +c → scene +24. Frozen WorldObjectRuntime's historical `sceneDefaultType` field therefore carries this world token. It does not mean a numeric object type or scene +20.

The image's **+c → parent +24 → world +10..1c** supplies the inclusive projected clip rectangle. Plane flags +8, extents +30/+34, camera edges +40..4c, and offsets +50/+54 supply frozen SpriteGeometry projection. Target +10/+14 supplies ordinary viewport width/height; target +2c supplies its surface wrapper. Actor +54..60 supplies a custom ordinary clip when +54 is not INT_MIN.

Compressed load bit depth comes from **image +c → parent +4 → holder +10 → target +18 low byte**. Provide that graph explicitly; it is distinct from the world/clip graph. Ordinary compressed eight-bit allocation retains constructor fields: +14=1 effect mode, +18=0x80, +24 low byte=1, and null data/palette tokens. `4bfc50` copies `length-32` raw bytes exactly, including unused trailing embedded palette bytes in the eight-bit path. Width/height come from PID +8/+c. PID flag 0x40 selects effect 2 through `4c6130`; its later lighting pixel bodies are not recovered here.

Surface manager needs its physical DirectDraw object at +0, current bit depth +474, optional translation palette +478 and availability +878, and list metadata at +3b8. A surface is 47 words/188 bytes with vtable `513690`, COM surface pointer +8, DDSURFACEDESC +c (27 words), creation flags +74, derived bit depth +a4, byte width +a8, pixel byte size +ac, pitch in pixels +b0, and key-enabled flag +b8.

Heap lookup takes aligned word spans. Raw resources and compressed data require readable final word padding when their byte length is not divisible by four; only the exact byte payload is copied/decoded. Host allocation may preserve arbitrary seed bytes. Constructors do not zero whole objects; the full-heap oracle checks the untouched storage, including three high bytes of compressed +24.

## Draw ownership and service order

Original `4d2890` first handles actor +40 hide/blink flags, mutating +44/+40 with animation delta `5430c4`. It then selects the compressed or surface path. Projected draws invoke Windows CopyRect after projection and before clipping/blitting. These pre-blit stores and events happen before actor draw-result fields +18..38 are updated.

Frozen SpriteGeometry computes into a temporary actor/context. The native wrapper publishes pre-blit blink and flip-global stores, invokes the original graphics boundary, then applies the original draw-result stores. It preserves callback changes to unrelated raw actor fields. A failed graphics return is ignored by the original wrapper and still yields draw status zero. Hidden/outside draws set +38 to FFFFFFFF and preserve earlier draw-result fields.

Both flipped surface and compressed services receive writable destination/source stack spans. Destination callback mutations affect final coordinates and drawn edges, while width/height remain the pre-call values. Unflipped surface destination x/y are passed by value; mutable source coordinates do not alter actor result coordinates. This differs materially from applying all draw fields before the graphics callback.

`ClawGameImageCall` passes up to eight original arguments. Adapted stack pointer arguments are zero, with writable `destination`/`source` spans provided separately; non-stack pointers remain exact raw tokens. Consume stack spans synchronously. CopyRect uses function identity `546d58`, the original import slot, rather than inventing an Apple function address.

| Service | Receiver / arguments / spans |
| --- | --- |
| `546d58` CopyRect | receiver 0; args 0,0; four-word destination and source |
| `4b9d80` | target +2c; destination x,y, image +2c, 0 stack-source, image +28; source rectangle |
| `4b9ce0` | target +2c; 0 stack-destination, image +2c, 0 stack-source, `8800`, `543108`; both rectangles |
| `4bffa0` | image +30; 0 stack-destination, target +2c, 0 stack-source, flipX, flipY; both inclusive rectangles |

Globals expose all 25 words at `543108`; flipped surface draws set only its second word at `54310c` to 2/4/6 before the call. Initial DDBLTFX/device setup is caller-owned, not fabricated from PE BSS. Surface creation flags `54316c`, color key `543170`, compressed effect values `5430b0..bc`, and embedded palette `5427b0` remain separate. Eight-bit mode's original key value is zero, as established by the frozen surface-raster mode-setter test.

## Color key and image kind

Successful original `4b9380` explicitly sets **surface +b8=0** after COM GetSurfaceDesc, then derives byte sizes/pitch and rectangle storage from the returned descriptor. The PID path `4bf310` adjusts surface flags according to PID flags 4/2, converts an embedded 768-byte RGB palette into 256 packed four-byte words when flag 0x80 is present, creates and locks the surface, decodes every pixel through frozen PIDSurfaceRaster, unlocks it, then calls `4b9990` only when PID flag 1 is set.

`4b9990` sets +b8 to **key != FFFFFFFF** before SetColorKey with flag 8 and a repeated two-word key pair. Even when SetColorKey reports failure, that b8 store remains. The image loader then assigns **image +28 = 11 if b8 != 0, otherwise 10**. Disabling image key use passes FFFFFFFF rather than silently assuming transparent zero. Raster decoding writes literal zero pixels in either mode; coverage/color-key visibility is a separate decision.

COM creation/description/lock/unlock/key calls use resolved original vtable entries, receiver 0, and the explicit COM object as argument 0. Describe/create/lock pointers refer to the live heap DDSURFACEDESC or surface pointer field. The key's two-word stack pair is exposed through `source`, with its raw stack argument normalized to zero. Report helper `4bd260` remains an explicit service. Lock recognizes original lost-surface HRESULT `887601c2`, calls surface virtual +1c as a service, and retries with a null rectangle if restoration succeeds.

File surface factory `4bc740`, bitmap codecs `4bdad0`/`4be810`, CArray SetAtGrow `4f582f`, CPtrList AddTail `4f51c5`, and image/surface deleting destructors remain explicit services. Their callbacks may use the parent's frozen implementations where available. Generic constructors, metadata stores, invocation order and returned node/resource identities execute in this module; those service bodies are not counted as newly recovered native code.

## Evidence and remaining scope

Run `work/test-env/bin/python Tests/compare_game_image_runtime.py`. The test compiles warning-clean optimized C++ and executes hash-pinned original bodies under Unicorn. It compares a complete one-MiB heap plus every represented render/load global at return and each ordered callback, including raw actor/image/surface/manager/list fields, encoded resources, allocations/frees, mutable rectangle/pair spans and framebuffer padding. Only native/original stack address identity and void incidental EAX are normalized.

Final counts are recorded in `work/game-image-agent/verification.json`. The suite covers 482 actual Claw and Level 1 PID assets, each through real original loading and all four raw-wrapper flips; 144 retained blink/camera draw calls; file-factory success/duplicate/failure; embedded palette; arbitrary zero/positive/disabled key; creation failure; format/length rejection; all eight draw paths; and mutating CopyRect/blit callbacks.

The 288 joined actual compressed draw calls retain loader-created side objects and use native GameImage's rich `4bffa0` service to compose frozen PIDBlitter, while the original executes real `4bffa0` and all four pixel bodies. COM lock/unlock are adapted identically. Full heaps include actual destination bytes and pitch/guard storage. This verifies the horizontal +1 mirror placement and clipped row/column quirks through the raw wrapper graph, not just isolated pixel calls. The source-stack pointer is normalized within the verified positive-address class greater than image width; its absolute x86 address is not an Apple stack identity claim.

C11 compilation and a native Swift C bridge smoke pass. Swift runs the real portable raw PID surface factory/raster/key/header path, verifies source pixels and kind 11, and confirms that actor draw results are still stale during the blit callback and updated afterward despite a failed return. No Xcode/device/GUI work is part of this module.

Explicit remaining pixel paths: compressed lighting/effects (mode +14 != 1), 16-bit embedded palette conversion `4bfd80`, non-eight-bit uncompressed translation/conversion, and physical DirectDraw surface/blit/lost-surface resource implementations. Uncompressed surface draw commands have exact wrapper parity, but their physical texture blits remain services. This module does not promise complete framebuffer parity for those services, full image/resource destruction, or whole-game behavior.
