# Original surface Flip presentation wrapper

`SurfaceFlipRuntime` owns the whole original v1.0 presentation wrapper `4b98b0`.
It composes the frozen SurfaceBlit/PCX restore owner and exposes the actual
DirectDraw Flip operation as a physical service. Existing Blt, BltFast and
color-key bodies remain in their current owners; no additional presentation
helper is required by the measured Flip path.

The unchanged oracle is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Recovered source evidence is `work/surface-flip-agent/roots.c`; instructions
`4b98b0..4b9940` in `work/v10-disassembly.txt` establish receiver/arguments,
retained registers, retry alias reads and error diagnostics.

## Stable API

`claw_surface_flip_entry(function, surfaceToken, arguments, count, context, dependency, user, result)`
recognizes only `4b98b0`, with one argument `optionalSourceSurfaceToken` and
original RET4. The source is optional: zero remains an actual original null
source override. A return of 1 means the covered source body completed, with
its meaningful HRESULT in `result`. Nonzero HRESULTs are ordinary completed
source outcomes. Initialize `context.fault` to zero; faults 1/2/3 denote missing
span/service, unsupported ABI and operation budget respectively.

The context carries the shared scene host, an optional borrowed
`ClawSurfaceBlitContext` and an operation limit. The source surface allocation is
188 bytes / 47 words; its `+8` field identifies the DD interface. SurfaceFlip
copies the borrowed restore context before adapting its host. Existing
SurfaceBlit then copies its optional PCX context. Caller host, context and
callback identities survive completion; no temporary bridge is retained.
`ClawSurfaceFlipCall` aliases the existing rich `ClawSurfaceBlitCall` layout.

## Physical presentation recipe

The actual physical function is read from the destination interface's current
vtable at offset `+2c` (hexadecimal). The dependency call is:

- `function`: that actual virtual function token;
- `receiver`: zero;
- `arguments`: destination DD interface, captured source DD interface or zero, 1;
- `argumentCount`: 3;
- `localMask` and `bufferCount`: zero.

All identities remain raw original tokens. The source first captures
`optionalSourceSurface+8` if the optional source is nonzero, then reads the
destination surface `+8` and its DD vtable. It does not modify rectangles,
colors, image kind or source-owned surface lists. A physical indexed transport
resolves these interfaces and elects the corresponding presentation operation.
When the source override is zero, it remains zero; the physical transport
retains its actual attached front/back relationship. The native adapter is
responsible for presenting/swapping its physical storage and reporting the
HRESULT. The source wrapper does not fabricate physical success or exchange
source heap fields on its own.

The frozen State5 `present` path already calls this original entry for the
primary surface with source zero, followed by its source BltFast copy of the
working back surface into the retained front. SurfaceFlip closes that addressed
Flip service; source display construction and back/attached surface ownership
remain existing owners. This handoff does not claim a complete live State5
presentation walkthrough.

## Error, restore and alias order

The first physical success returns HRESULT zero immediately. A first nonzero
result other than `887601c2` invokes
`4bd260(5324dc,29a,initialHRESULT)` and returns that same HRESULT. Diagnostic
service return values cannot replace the saved Flip result.

Only lost-surface `887601c2` elects the destination surface's current virtual
`+1c`. Default original surface vtables select `4b9e60`. SurfaceFlip composes
frozen [SurfaceBlit](surface-blit-runtime.md), which in turn composes frozen
[PCX](pcx-image-runtime.md) restore: read destination `+b4`, call a nonzero
registered cdecl callback with receiver zero and the destination surface token
as argument, return 1 on nonzero callback result, otherwise call `4bd0a0` and
return 0. Registered asset reload callbacks and fallback remain exact services.
An unknown virtual restore identity remains an addressed thiscall service with
the surface receiver and no arguments.

Failed restore returns the saved lost-surface result, without the Flip wrapper's
HRESULT diagnostic. Successful restore permits one physical retry. The source
**rereads destination `+8` and its DD vtable**, but **retains the source DD value
captured before the first physical call**. This includes a captured zero source
and a source interface sharing the initial destination identity. A restore or
physical callback may replace either source/destination raw field; only the
source-specified live destination read affects the retry.

Retry success returns zero. Any nonzero retry result, including another lost
result, invokes `4bd260(5324dc,294,retryHRESULT)` and returns that retry HRESULT.
There is no second restore or retry loop. The initial and retry diagnostic
line constants differ and are preserved.

## Verification and physical boundary

`Tests/compare_surface_flip_runtime.py` passes **828 whole original calls /
2,853 ordered full snapshots**. The suite compares every byte of a 65,536-byte
worker heap and 294,912-byte source global range, those same ranges before every
physical/restore/diagnostic callback, exact physical tokens/arguments, meaningful
EAX and original RET4. Profiles cover all three default source surface vtables,
null/nonzero/shared source identities, ordinary success and nonzero HRESULTs,
restore success/failure/missing callback, a failed retry, live destination and
retained source aliases, an addressed private restore identity and repeated
presentation over the retained object graph. Diagnostics deliberately return a
separate value, and fallback deliberately returns nonzero, demonstrating that
those transport return values do not replace the source's saved HRESULT or
frozen restore result.

Exact-sized captured replay passes **40 calls / 106 callback snapshots** under
ASAN/UBSAN. Source/destination surfaces are separate exact 188-byte allocations,
interfaces four bytes, Flip vtables 48 bytes, an addressed private restore vtable
32 bytes and the declared presentation output four bytes. Replay compares full
raw digests and exact callback order/arguments/writes, whole-call bytes, meaningful
EAX and borrowed SurfaceBlit/PCX/host identities. Every one of the six dependency
sources is sanitizer-instrumented. LeakSanitizer is unavailable on this macOS,
so it is disabled; no source allocation is elected by these Flip paths, and
replay storage is RAII-owned.

Physical test endpoints provide declared presentation byte writes, HRESULTs
and registered restore effects. They do not execute an actual DirectDraw Flip
or establish native pixel/display/device acceptance. Physical indexed transport
and its source attachment identities must be joined by the coordinator. No
shared native Swift host, Xcode project, simulator or physical device was edited
or driven by this source handoff.

Reproduce from the repository root:

```sh
work/test-env/bin/python Tests/compare_surface_flip_runtime.py
work/test-env/bin/python Tests/build_surface_flip_validation.py
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
work/surface-flip-agent/exact-sized-replay \
work/surface-flip-agent/sanitizer-replay.bin.gz
```

The build also checks strict C11 declarations, C++17 with
`-Wall -Wextra -Werror`, and Swift import including the rich-call type alias.
Logs, `report.json` and compiled source/header hashes remain under
`work/surface-flip-agent`.
