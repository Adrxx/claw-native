# Original surface blit and color-key wrappers

`SurfaceBlitRuntime` owns the whole original v1.0 surface Blt wrapper `4b9ce0`,
BltFast wrapper `4b9d80`, and direct color-key wrapper `4b9950`. It composes the
already frozen GameImage color-key convenience `4b9990` and PCX restore
`4b9e60`, preserving their owner APIs. It passes exact source rectangles,
flags, surface tokens and DirectDraw FX data to physical services; indexed pixel
transport remains a caller responsibility.

The unchanged oracle is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Recovered source evidence is `work/surface-blit-agent/roots.c`; exact instruction
ordering is in `work/v10-disassembly.txt`, `4b9ce0..4b9e08`, `4b9950..4b99c9`
and `4b9e60..4b9e81`. Ghidra's retry expressions contain unaffiliated register
names, so the implementation uses the actual saved-register/stack instructions,
validated through the whole original calls below.

## Stable API

`claw_surface_blit_entry(function, receiver, arguments, context, dependency, user, result)`
uses a raw 32-bit surface receiver. The surface's complete source allocation is
188 bytes / 47 words. `ClawSurfaceBlitArguments` carries five raw argument words,
count, and optional synchronous destination/source pointers. Optional pointers
replace source-local rectangle/pair tokens; their corresponding argument words
must be zero. Absent spans with raw word zero represent the original null
rectangle. Nonlocal pointers retain their raw tokens.

| Entry | Raw arguments | Optional spans | Original return |
| --- | --- | --- | --- |
| `4b9ce0` | destination RECT, source surface or 0, source RECT, flags, FX token | destination replaces arg0; source replaces arg2; each 16 bytes | HRESULT; RET20 |
| `4b9d80` | x, y, source surface, source RECT, flags | source replaces arg3; 16 bytes | HRESULT; RET20 |
| `4b9950` | flags, color-key pair | source replaces arg1; 8 bytes | HRESULT; RET8 |
| `4b9990` | key | none | void; RET4; native result zero |
| `4b9e60` | none | none | Boolean restore success |

A return of 1 means the selected covered body completed; meaningful source EAX
is returned separately. Nonzero HRESULTs are ordinary completed source returns,
not native faults. Initialize `context.fault` to zero. Native faults 1/2/3
identify missing span/service, unsupported ABI/domain, and operation limits;
they are distinct from DirectDraw HRESULTs. Unknown entry addresses return
unhandled. The ordinary lost-surface retry path requires a nonnull source
surface, as the original retry unconditionally reads its interface field.

The context borrows the raw scene host, an optional PCX owner context and an
optional GameImage global view. PCX context copies receive the temporary bridge
host, so caller host/context identities survive completion. Default local owner
views support the key and restore bodies when no explicit view is supplied.
Source allocation/free, clock and unknown callback services remain addressed
operations whenever elected. This family does not invent asset reload callbacks.

## Physical joining recipe

Use one raw token heap and actual surface/interface/vtable identities. Read
`surface+8` for its DirectDraw interface token. Physical calls have receiver zero
and interface token in argument zero. `ClawSurfaceBlitCall.function` is the actual
function token read from the interface's current vtable, not a fixed native
operation ID.

| Physical endpoint | Arguments | Source local buffer masks |
| --- | --- | --- |
| destination DD virtual `+14`, Blt | destination DD, destination RECT, source DD or 0, source RECT, flags, FX token | bit1 for destination RECT; bit3 for source RECT |
| destination DD virtual `+1c`, BltFast | destination DD, x, y, source DD, source RECT, flags | bit4 for source RECT |
| DD virtual `+74`, SetColorKey | DD, flags, pair | bit2 for a local pair |

Buffers appear in increasing argument order. Their lifetime is the dependency
callback only. A raw rectangle, pair or FX pointer is looked up through its
unchanged token; local rectangles/pairs are supplied directly with mask-marked
zero tokens. FX remains the live raw source pointer. No rectangles are enlarged,
clamped or translated inside these wrappers. A physical indexed transport may
resolve its buffer/interface tokens and perform the elected operation, but it
must retain the wrapper's HRESULT, source flags, null/full-rectangle behavior,
color-key configuration and physical alias effects.

The ordinary source image drawing caller remains GameImage `4d2890`. Its
unflipped surface branch elects `4b9d80` and passes image kind `10/11` (hex) as
its original flags; its flipped branch elects `4b9ce0` with flags `8800` and the
shared 25-word FX block at `543108`. GameImage owns clipping/rectangle generation
and writes FX flip bits before reaching this family. SurfaceBlit neither changes
image kind nor replaces either branch with a custom pixel copy. The coordinator
can forward the existing `ClawGameImageCall` by copying its five argument words
and destination/source span pointers into `ClawSurfaceBlitArguments`.

## Restore, retry and diagnostics

Both copy wrappers make the first physical call with the current destination
interface and source interface (when present). Only HRESULT `887601c2` elects
destination surface virtual `+1c`; the real default surface vtables select
frozen PCX restore `4b9e60`. Other virtual restore identities remain exact
addressed services.

Frozen `4b9e60` reads the destination's callback pointer at `+b4`. If nonzero,
it calls that registered cdecl callback with receiver zero and argument
`surfaceToken`. A nonzero callback result returns 1. Otherwise it invokes the
existing diagnostic/recovery service `4bd0a0` and returns 0. This is not an
implicit physical DD Restore call and does not automatically reload both
surfaces. Callers retain the established asset/PCX restore callback owner and
its reached physical services.

Failed restore returns the original lost-surface HRESULT immediately, without
the copy wrapper's HRESULT diagnostic. Successful restore permits exactly one
retry. That retry rereads destination `+8`, its vtable and the source surface
`+8`; it uses the original rectangles, flags and FX argument. Borrowed rectangle
contents remain live if the callback writes them. A second lost-surface result
is diagnosed and returned; there is no retry loop or second restore.

A nonzero initial non-lost result or a nonzero retry result invokes
`4bd260(5324dc,48e,hr)` for Blt, or `4bd260(5324dc,4b8,hr)` for BltFast, then
returns that HRESULT. This family does not substitute successful EAX after a
physical device error.

Direct `4b9950` invokes physical SetColorKey with its raw flags/pair, diagnoses
any nonzero result as `4bd260(5324dc,331,hr)`, and returns the HRESULT. Frozen
GameImage `4b9990` creates the two-word `[key,key]` local pair and stores
`surface+b8 = (key != FFFFFFFF)` before electing SetColorKey with flags 8. That
store remains even if the endpoint fails. It is a source void function; no
incidental original EAX equality is claimed. Literal indexed zero and disabled
key `FFFFFFFF` remain distinct caller inputs.

## Validation and scope

`Tests/compare_surface_blit_runtime.py` passes **912 whole original calls /
2,225 ordered full snapshots**. It checks meaningful EAX, exact original stack
pops, every byte of a 65,536-byte worker heap and 294,912-byte source global range,
and those same full ranges at every physical/service callback. The corpus covers
20 valid allocation seeds, raw/local/null/full rectangles, ordinary source flags,
indexed key values including zero/255/disabled, nonzero device returns,
successful/failed/missing callback restore, one retry, and restore callbacks
replacing valid source/destination interfaces and live rectangles.

`Tests/compare_surface_blit_image_chain.py` additionally passes **24 complete
original GameImage -> SurfaceBlit chains / 48 ordered full snapshots**. It
executes both image kinds, all four flip combinations and ordinary center/edge
placements with source clipping. The native bridge publishes the same sparse
FX alias before physical dispatch; these checks compare the whole source
caller and both complete copy wrappers, not just a synthetic wrapper call.

`Tests/exact_sized_surface_blit.cpp` passes **38 exact-sized captured replays /
73 callback snapshots** under ASAN/UBSAN. Scene surfaces are separate exact
188-byte allocations, interfaces four bytes, vtables 120 bytes, rectangles
16 bytes, key pairs eight bytes, FX 100 bytes, and declared source/destination
pixel transport spans 48/192 bytes. Every dependency source is rebuilt with
sanitizers. Replay checks full raw digests at callbacks, physical argument and
buffer bytes, declared callback outputs/writes, meaningful EAX, whole-call bytes
and borrowed host/PCX context preservation. LeakSanitizer is unavailable on this
macOS runtime; leak detection is disabled. This family performs no source
allocation in the measured wrapper paths.

The physical test endpoints declare deterministic destination byte writes and
HRESULTs. They do not execute real DirectDraw rasterization, and the tests do
not establish actual menu pixels, native presentation, physical audio or device
acceptance. The GameImage chain is an ordinary indexed fixture with the frozen
source geometry caller, separate from a live IFC/main-menu walkthrough.
Registered resource reload callbacks, physical DD operations and diagnostic
transport remain explicit services. No native Swift host, Xcode project or
device was changed by this source handoff.

Reproduce from the repository root:

```sh
work/test-env/bin/python Tests/compare_surface_blit_runtime.py
work/test-env/bin/python Tests/compare_surface_blit_image_chain.py
work/test-env/bin/python Tests/build_surface_blit_validation.py
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
work/surface-blit-agent/exact-sized-replay \
work/surface-blit-agent/sanitizer-replay.bin.gz
```

The build gate also checks strict C11 declarations, C++17 with
`-Wall -Wextra -Werror`, and Swift public import. Evidence is retained in
`work/surface-blit-agent/{compare,image-chain,build,sanitizer}.log`, `report.json`
and the compiled `source-sha256.json` manifest. Existing module owners are
[GameImage](game-image-runtime.md) and [PCX](pcx-image-runtime.md).
