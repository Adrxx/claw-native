# Original scene-startup composition

`SceneStartupCompositionRuntime` joins the frozen original single-player scene,
display, graphics, audio, palette, world, image registry and collection modules.
It owns the synchronous composition bridge and three thin source leaves. The
ordinary startup handoff is source-only; the app has not elected this complete
facade, and this evidence does not establish retail asset boot or device acceptance.

The oracle is the unchanged original v1.0 `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The existing `OriginalV10` harness verifies that fingerprint before comparisons.
Saved startup evidence is under `work/scene-startup-composition-agent`; the
independent ordinary QA artifacts are under `work/scene-startup-validation`.

## API and ownership

The C11 function is
`claw_scene_startup_composition_entry(function, receiver, arguments, count, context, dependency, user, result)`.
All game identities remain raw 32-bit tokens. A return of 1 means the selected
covered body completed, with meaningful original EAX in `result`. An original
startup return of 0 is an ordinary source failure, distinct from a composition
fault. The caller sets `fault` to zero before a new call. Diagnostics are 1 for
missing span/context/service, 2 for unsupported ABI/domain and 3 for operation
budget exhaustion. These values are host diagnostics, separate from the scene's
sticky error at `scene+38` (hexadecimal offset).

`context.scene.lookup` supplies the shared original heap and raw global aliases.
The bridge routes source allocation/free through the exact services `4f63ec`
and `4f6428`; `readClock` remains caller-owned. Contexts in the facade are borrowed.
The bridge copies each supplied module context, places its temporary host only
in those copies, and does not leave the caller's host, callback, subcontext or
user binding pointing at a completed call's stack. Borrowed global views remain
live: their contents may change according to the source body's writes.

Global synchronization preserves the original shared aliases. Entering a
composed body imports its current raw aliases. Before a dependency callback,
active views publish source writes; after the callback, raw aliases are reread.
Ordinary completion imports the final raw aliases into the supplied views. These
include scene/camera globals, graphics `541398/541374` and channel words,
image `5430c4/54316c/543170`, the 25-word DirectDraw FX block `543108`, four effect
words `5430b0` and the 256-word palette block `5427b0`.

The rich dependency call carries eight argument words and up to three borrowed
synchronous buffers. Bit 8 of `localMask` identifies a local receiver; argument
bits identify local pointer arguments. Receiver buffers precede argument buffers.
Local tokens are normalized to zero; raw pointer arguments retain their tokens.
A live raw output may also be exposed as a buffer with mask zero, while its raw
argument token remains authoritative. `bufferTokens` is reserved and currently
zero. COM calls use receiver zero and the interface token as argument zero.
Dependency callbacks must use their explicit `user`/caller bindings and complete
all buffer reads/writes before returning.

## Finite composition

The facade preserves module APIs and dispatches their existing supported bodies.
The ordinary whole-scene roots measured in this handoff are:

| Entry | Arguments | Source ownership |
| --- | --- | --- |
| `4ce960` | none | Frozen 60-byte scene constructor and camera animation reset |
| `4cea10` | HWND, width, height, depth, flags | Frozen eleven-component scene initialization and elected display/audio graph |
| `4cefc0` | none | Frozen scene readiness |
| `4ceef0` | none | Frozen ordered component cleanup |
| `4ce9c0` | none | Frozen scene destructor after retained restart histories |

Startup creates eleven component allocations, in source order: 28, 44, 44, 44,
44, 104, 224, 52, 44, 2180 and 128 bytes. Display then creates the actual
48/52/52-byte wrappers and elected 188-byte surfaces/list nodes. The first
constructor does not invent allocation initialization, and the facade does not
add cleanup between source operations. Retained tests explicitly elect the
source cleanup entry between startup calls.

The only new thin source leaves are:

| Entry | Arguments | Behavior |
| --- | --- | --- |
| `4ca280` | force | Sound-controller parent/audio election, controller `+2c/+30` stores and master volume `532c10=100`; rejected branches preserve existing fields |
| `4cf7e0` | none | Boolean sound-controller readiness from `+2c/+30` |
| `4f701d` | none | CObject metadata token `5105d8` |

Their pre-existing source evidence is `work/scene-startup-composition-agent/leaves.c`.
All further meaningful routines remain in their frozen owners or are exact
addressed dependency services. See
[single-player scene](single-player-scene-runtime.md),
[scene display](scene-display-runtime.md),
[scene lifecycle](scene-lifecycle-runtime.md),
[graphics lifecycle](graphics-manager-lifecycle-runtime.md),
[audio lifecycle](audio-manager-lifecycle-runtime.md),
[palette resources](palette-resource-runtime.md),
[world file](world-file-runtime.md),
[image registry](image-registry-runtime.md) and
[results](booty-results-runtime.md) for the broader module inventories.
The facade is not a new independent parity claim for every routed address.

Missing supplied module contexts do not grant successful initialization. In
particular, the whole startup fixture supplies scene/camera globals, display,
graphics, palette, world, images/registry, lifecycle and collection contexts.
Audio and array bridge contexts also have internal defaults where the existing
module API supports them. A caller must still supply all raw spans and reached
physical services. A missing meaningful implementation remains visible as an
exact service or composition fault.

## Ordinary error returns and transport scope

The ordinary suite covers nonzero HRESULTs at DirectDraw create, cooperative
level, capabilities, mode enumeration, display mode, pixel format, surface create,
surface description, attached surface, DirectSound create and cooperative level.
The source decides whether an error returns failure, diagnoses and continues, or
is optional under the supplied flags. These callbacks provide declared writable
output descriptors/interface tokens. The physical mode inventory is explicitly
empty; no real DirectDraw/DirectSound device is created.

Two source-handled allocation histories are measured separately. With scene
flag 1, failure of allocation 14 omits the unused third display wrapper:
initialization returns 1, scene readiness returns 0, and cleanup follows the
actual retained graph. Failure of allocation 11 omits the audio manager while
DirectSoundCreate returns `80004005` without writing its output: optional-audio
flag 1 returns 1, required-audio flag 8 returns 0 with scene error 1009. Both
histories preserve the source ownership/free order and complete cleanup. They
do not imply that every allocation failure in the original has an ordinary exit.

Reached external transports are the allocator/free routines, original import
slots and COM virtual functions, plus diagnostic services `4bd260` and `4b4ed0`.
Test COM identities `700xxx/710xxx/720xxx` are declared oracle fixtures. Resource
I/O, populated logic/actor/image loading, CRT/application bootstrap, asset boot,
window/presentation and actual audio devices remain caller/integration work.
This validation uses empty source-created controller collections and a declared
physical descriptor profile; it does not establish populated full-game startup.

## Independent validation

The ordinary-only comparison suite checks whole native and unchanged-original
calls, meaningful EAX, original stack pops, allocated/freed token histories,
the entire 1,048,576-byte worker heap and 294,912-byte global range, and those same
full ranges at every ordered dependency boundary. It covers nine source flags,
24 allocator seeds, normal device returns, retained cleanup/restart/destruction,
source sound binding, callback writes to live global aliases, borrowed context
identity, and the two ordinary allocation histories above.

Exact-sized ASAN/UBSAN replay allocates every captured source-created object in a
separate allocation of its recorded size. This includes the exact 60-byte scene,
4-byte device interfaces, vtable spans, component objects, wrappers, surfaces,
embedded world-array fields and list-node pool blocks. The global image span and unrelated worker storage
remain shared transport spans. Callback order, complete heap/global digests,
borrowed buffer bytes/outputs, whole-call final bytes and meaningful EAX are
checked against the captured oracle histories. Every one of the 37 dependency
source files is rebuilt with sanitizer instrumentation; replay does not rely on
the historical frozen support library. LeakSanitizer is unavailable on this
macOS runtime, so `detect_leaks=0`; allocation/free identity is checked by the
ordinary oracle, and replay allocations are RAII-owned.

Reproduce from the repository root:

```sh
work/test-env/bin/python Tests/build_scene_startup_composition_validation.py
CLAW_SCENE_STARTUP_WORK=work/scene-startup-validation \
CLAW_SCENE_STARTUP_SUPPORT=work/scene-startup-validation/libOrdinarySupport.dylib \
work/test-env/bin/python Tests/compare_scene_startup_composition_ordinary.py
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
work/scene-startup-validation/exact-sized-replay \
work/scene-startup-validation/ordinary-sanitizer-replay.bin.gz
```

The build checks strict C11 header compilation, C++17 source with
`-Wall -Wextra -Werror`, and Swift import/typecheck. `source-sha256.json` records
the exact compiled source/header hashes. Final ordinary-only QA passes **2,015 whole calls / 33,268 ordered snapshots**.
The representative exact-sized corpus has **77 calls / 1,274 callback snapshots**.
Detailed counts are recorded in
`work/scene-startup-validation/ordinary-compare.log` and
`ordinary-sanitizer.log`. No device, simulator, Xcode project or shared native
host was changed by this QA handoff.
