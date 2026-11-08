# Original scene and default-controller lifecycle

`SceneLifecycleRuntime` recovers the finite original v1.0 scene cleanup and its elected default controller/map/string orchestration. It is original executable recovery; it does not replace physical DirectDraw operations with a claimed source implementation. Constructor `4ce960` and initializer `4cea10` remain in the frozen `SinglePlayerSceneRuntime`.

The executable is `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Instruction/decompilation evidence is in the worker-private `work/scene-lifecycle-agent/{roots,leaves,remaining,final,lists}.c` and `work/v10-disassembly.txt`. Function boundaries were checked against instructions. In particular, the list destructor starts at `4f565f`; `4f5650` is an interior address.

## Entry API and source footprint

The C11 API is `claw_scene_lifecycle_entry(function, receiver, arguments, count, context, dependency, user, result)`. A return of one means the selected finite body completed. Meaningful original EAX is supplied separately. Native faults identify missing heap/service spans (1), invalid ABI/domain (2), or traversal limits (3); these are adapter diagnostics, not original error codes.

The scene is exactly 60 bytes / 15 words, vtable `513ab8`. Supported scene bodies:

| Entry | Original arguments | Behavior |
|---|---|---|
| `4ceef0` | none | Ordered owned-component cleanup |
| `4ce9c0` | none | Install scene vtable, cleanup, install base vtable `50becc` |
| `4ce9a0` | flags | Destructor; flags & 1 elects free; returns receiver; RET4 |
| `4cefc0` | none | Boolean readiness, not a type getter |

`4ceef0` uses the following exact field and virtual-call order. All offsets here are hexadecimal.

| Scene field | Owned component | Operation |
|---|---|---|
| `+28` | Sound resource controller | Virtual `+4(1)` |
| `+20` | Audio manager | Virtual `+0(1)` |
| `+4` | Surface holder | Virtual `+4(1)` |
| `+8` | Actor container | Virtual `+4(1)` |
| `+c` | Queued-effects renderer | Virtual `+4(1)` |
| `+10` | Image controller | Virtual `+4(1)` |
| `+14` | Logic controller | Virtual `+4(1)` |
| `+18` | Palette controller | Virtual `+4(1)` |
| `+2c` | Animation controller | Virtual `+4(1)` |
| `+24` | World | Virtual `+4(1)` |
| `+1c` | Graphics manager | Whole `4bc1b0`, then `4f6428` free |

Each nonzero field is cleared only after its call returns. The next field is read from the live scene after that callback, so callback replacement and recursive cleanup affect later operations exactly as in the original. It is not an initial snapshot of all owners. No extra stop-all or cleanup pass is inserted. HWND `+30`, initialization flags `+34`, and sticky error `+38` are preserved.

`4cefc0` first requires nonzero `+4/+8/+c/+10/+14`, invokes holder virtual `+14`, then checks the reread world field `+24`. It does not require audio, graphics, palette, animation, or sound fields.

## Default-controller entries

| Controller | Vtable | Bytes | Deleting / base destructor | Clear bodies |
|---|---|---:|---|---|
| Palette | `513b28` | 104 | `4cf0a0 / 4cf0c0` | `4d4370` |
| Image | `513b88` | 44 | `4cf160 / 4cf180` | `4cfa80 / 4d0240` |
| Logic | `513b60` | 44 | `4cf940 / 4cf960` | `4d6290` |
| Animation | `513ad8` | 44 | `4cf9d0 / 4cf9f0` | `4cdf30 / 4cdf40` |
| Sound | `513b00` | 52 | `4cf800 / 4cf820` | `4ca2e0 / 4ca300` |
| Actor container | `513c20` | 44 | `4cf8a0 / 4cf8c0` | Frozen Results-owned `4c89e0` |
| Effects renderer | `513be8` | 44 | `4cf280 / 4cf2a0` | Frozen Results-owned `4c89f0` |

Deleting wrappers call the base destructor, test flags & 1, and return the original receiver with RET4. Base destructors install the derived vtable before cleanup, destroy their embedded collections, then set base fields `+4=ffffffff`, `+8=0`, `+c=0`, vtable `50becc`.

Image clear invokes the current virtual `+58` (the default table selects `4d0240`) before setting raw globals `54316c/543170` to zero. If a `ClawGameImageGlobals` view is supplied, its corresponding surface-load flags/color-key aliases are synchronized to those stores. Logic/image maps use destructor `4f61f3`; animation/sound maps use `4f5d00`. Palette cleanup destroys maps in order `+48`, `+2c`, `+10`; only its primary map payloads receive virtual deletion in this routine, and active palette `+64` is zeroed after primary clear. Sound `4ca2e0` clears its `+2c` field after map cleanup.

The image and logic type getters `4cf150` and `4cf930` return 18 and 19 respectively. Palette getter `4cde00` remains frozen WorldFile-owned. Actor/renderer embedded list destructor `4f565f` installs `5107bc`, composes the frozen whole `4f5172`, then installs `50becc`; collection payload cleanup stays in the existing Results module.

## Map and CString lifecycle

The raw map is seven words: vtable, bucket-table token, bucket count, association count, free-list head, CPlex head, allocation block size. Associations are exactly 16 bytes: next pointer, stored bucket index, CString data cell, payload pointer. Fixture insertion is a raw valid graph adapter; this module does not claim to recover map insertion/constructor bodies.

Recovered map entries are `4f5e1e` GetNextAssoc (three pointer arguments, RET12), `4f61a1` RemoveAll, `4f61f3` and `4f5d00` destructors. An initial position of `ffffffff` scans buckets in unsigned ascending order. GetNextAssoc writes the next position before key assignment, then rereads the current association payload after assignment. RemoveAll destroys each key, rereads its next pointer after that destructor, frees the bucket table, zeroes count/free head, composes actual CPlex release `4f5ac8`, and finally zeroes the CPlex head. Hash size/block size are preserved.

Controller clearing uses a source-constructed temporary CString data cell from raw global `52e1cc`. It walks nonnull payloads through their actual virtual `+4(1)`, then removes the map, and destroys the temporary key afterward. A map count inconsistent with its bucket graph is not converted to a successful empty map: the original reaches a null dereference and the native adapter stops with a missing-span diagnostic.

CString `4f667d` assignment and `4f64ba` release/reset are recovered. Equal data pointers cause no operation. Ordinary shared assignment releases the destination, rereads the source cell after release callbacks, assigns its data, then increments its reference count. Release compares the header against `[52e1c8]`, composes the frozen real `4f6584`, and rereads `52e1cc` afterward. The header pointer and empty data pointer are distinct original globals. The locked-copy branch calls original `4f6650(dest, length, sourceData)` as an explicit source service; this module does not claim recovery of that copy body.

The single-thread atomic reference stores follow the already verified ActorDestruction convention. Oracle Interlocked operations execute exact x86 increment/decrement stubs with original returned values. This is not a concurrent allocator claim.

## Integration and synchronous transport

Use the original scene field graph and actual controller vtables. Do not substitute a generic enemy destructor for resource/controller objects. Attach optional frozen contexts for Display, GraphicsLifecycle, AudioLifecycle, PaletteResource, WorldFile and GameImage globals; otherwise their exact addresses are emitted as dependency services. Default actor/renderer clear bodies `4c89e0/4c89f0` should route to frozen `BootyResultsRuntime`, with the live actor/number contexts needed by its elected children.

The rich call contains eight argument words plus up to three synchronous buffers. Stack pointers are normalized to zero, with argument bits in `localMask`; bit eight marks a temporary CString receiver. Ordinary heap tokens are preserved. Temporary CString cells are borrowed for the callback duration only. The host must supply shared raw global aliases `52e1c8/cc`, `54316c/170`, graphics global storage and the same resource tokens to all composed contexts.

Composed contexts temporarily receive a bridge host so their allocation, free and nested services are routed through this entry. Their caller-owned host fields are restored on completion and on native faults; no stack-local bridge is retained. Dependency transport should use its explicit user/context bindings rather than casting the temporarily adapted `scene.context` to a platform heap type.

This module composes only reached WorldFile cleanup/getter and audio deleting/shutdown entries. Its adapters do not generalize WorldFile file-loader local buffers or AudioLifecycle startup COM output metadata. Those whole startup calls should use their original modules directly. Physical COM release/restore, unknown resource/private virtual destructors, diagnostic transport, and locked CString copy remain named service boundaries. Cleanup completion with a transport fixture is not evidence of a live physical device operation.

## Verification

Run `work/test-env/bin/python Tests/compare_scene_lifecycle_runtime.py`. The original oracle executes the fingerprinted unchanged executable and compares the complete 262,144-byte worker heap, complete 294,912-byte globals range, allocated/freed token histories, and full snapshots at every ordered external callback. Meaningful EAX and original stack pops are checked separately. Only undefined incidental EAX on void bodies is excluded.

The corpus covers all supported controller/wrapper bodies, reference-sharing/map iteration, partial ownership masks, repeated teardown, callback replacement and guarded recursive cleanup; retained actual holder/display startup, all 14 retail `MAIN.PAL` loads and controller/scene destruction; and cleanup of the graph produced by actual original `4cea10` when `4cb040` reports a world setup failure. That last initializer is fixture generation, not a new initializer implementation or an additional whole-call parity claim. Two malformed profiles stop immediately before the original null dereference/virtual call and compare the preceding heap/events only.

Final verification passes 1,098 complete calls, 5,186 ordered full snapshots and two unsafe prefixes. It records 3,244 instrumented text addresses and 3,265 total instrumented addresses. `work/scene-lifecycle-agent/report.json` records these counts and fingerprint. Text instrumentation is filtered using the PE's actual executable section `[401000,50adb5)`; total instrumentation includes transported service entries and stubs. Neither count is a number of independently recovered functions.

`work/test-env/bin/python work/scene-lifecycle-agent/checks.py` checks strict C11/C++17 declarations and warnings, the Swift 96-byte rich-call ABI, and 64 ASAN/UBSAN retained chains with exact 60/28/44/52/104/188/2180-byte scene/controller/display/graphics objects, exact CString blocks, bucket arrays and CPlex nodes. Those sanitizer chains exercise empty actor/audio/world slots; their populated original graphs are covered by the differential corpus, not claimed as additional sanitizer coverage.

This recovery closes finite source scene teardown and default-controller collection ownership. It does not establish complete application shutdown, device fidelity, all private polymorphic destructors, or full-game behavioral equivalence.

Root reruns both the whole original comparison and64 sanitizer chains independently. The portable root command is `work/test-env/bin/python Tests/check_scene_lifecycle_asan.py`; its exact-span C++ fixture is included in Tests rather than depending on a private work/smoke.cpp file. This fixture proves bounded source ownership behavior, not physical COM or retail native boot.
