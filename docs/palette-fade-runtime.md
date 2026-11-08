# Original palette fade and clock bodies

`PaletteFadeRuntime` owns original v1.0 whole table fade `4bbd90`, scheduled
update `4bbb70`, finalize/cancel `4bbd20` and backup application `4bb8c0`. It
composes existing PaletteResource final set/fill bodies and preserves the same
56-byte backend, palette entries, clock source, physical palette and list owner.
The native menu/Story host can elect these source bodies through the stable C11
API without replacing their interpolation with a presentation animation.

The unchanged oracle is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Source evidence is `work/palette-fade-agent/roots.c`; actual stack arguments and
loop/callback order are checked against `work/v10-disassembly.txt`,
`4bbb70..4bbf56` and `4bb8c0..4bb90a`. Ghidra incorrectly presents `4bbd90`
with inferred stack variables/fastcall; the complete instructions establish
its real four-argument thiscall ABI and RET16.

## Owner inventory

[PaletteResource](palette-resource-runtime.md) already owns backend/palette
creation, resource wrappers, list insertion/removal, GetEntries backup `4bb870`,
SetEntries `4bb800`, uniform RGB fill `4bb910`, blocking uniform-color fade
`4bb990`, system palette handling and backend destruction `4bb2a0`. Its
backend arrays are owned there, including the persistent scheduled-fade saved
array at `+18` (hexadecimal). [LightPalette](light-palette-runtime.md) owns
player CLT/table loading and effect/table math; it does not own the new palette
clock scheduler/update bodies. Neither owner is duplicated or changed.

The table fade reads physical entries into backend `+c`, whereas existing
`4bb870` reads into backup `+10` and has a different diagnostic line. Those are
separate source operations. PaletteFade therefore retains its direct GetEntries
call. Final table application elects exactly existing `4bb800`; final uniform
RGB application elects exactly existing `4bb910`. Intermediate updates are the
original direct physical SetEntries calls. No extra cooperative wait, backup
copy, array release, list mutation or update call is inserted into the fade.

## API and physical joining

`claw_palette_fade_entry(function, backendToken, arguments, count, context, dependency, user, result)`
uses the raw original backend graph. The context supplies the shared scene host,
an optional borrowed `ClawPaletteResourceContext` and an operation bound. The
borrowed context is copied before composing final set/fill, and caller host and
callback bindings survive completion. Raw cooperative alias `541374` is
recognized as authoritative; the optional owner global view is synchronized
from it on ordinary completion.

A return of 1 means a covered body completed. Meaningful EAX is separate:
`4bbb70` returns 1 while active and before expiry, and 0 when inactive or when
it completes/cancels. The other entries are original void bodies and return
native result zero; their incidental original EAX is not compared. Initialize
`fault` to zero. Native diagnostics 1/2/3 identify missing span/service,
unsupported ABI/arithmetic domain and operation limit; nonzero device HRESULTs
remain ordinary source outcomes.

| Entry | Arguments | Original behavior |
| --- | --- | --- |
| `4bbd90` | start, count, target entries, duration | Blocking table fade, RET16 |
| `4bbb70` | none | Update an already source-configured scheduled fade |
| `4bbd20` | none | Finalize/cancel an active scheduled fade immediately |
| `4bb8c0` | unused argument | Copy 256-entry backup to live array and apply; RET4 |

The rich dependency preserves exact import/vtable tokens and raw pointer
arguments, with synchronous writable buffer views. Physical COM has receiver
zero and interface token in argument zero. Buffer lifetimes end at callback
return. The clock and physical joining recipe is:

| Endpoint | Arguments and span |
| --- | --- |
| source timeGetTime import `546df0` | no arguments; return source UInt32 milliseconds |
| palette interface virtual `+10`, GetEntries | interface, 0, 0, 256, live entry token; 1024-byte output buffer |
| palette interface virtual `+18`, SetEntries | interface, 0, start, count, entry token; count×4 live bytes |
| cooperative DD virtual `+58`, reached by final `4bb800`/backup | interface, 1, 0 |
| source allocation `4f63ec` / free `4f6428` | exact 1024-byte transient table snapshot / its raw token |
| diagnostic `4bd260` | original filename token, line, HRESULT |

The actual physical function is loaded from the current interface vtable.
PaletteFade preserves raw interface/entry aliases and re-reads source fields at
their reached boundaries. A callback can replace a valid backing array,
interface or cooperative alias; a captured earlier pointer is kept only where
the original retains it. Fourth entry bytes are source palette flags: the fade
changes RGB bytes, then final table SetEntries copies all four bytes through
the existing owner. The physical indexed transport must preserve this raw
palette record while deriving presentation colors as needed.

## Blocking menu and Story timelines

Pinned original `4bbd90` is **blocking**, not a fade scheduler. It first asks
GetEntries for all 256 entries into the live array at backend `+c`. Nonzero
HRESULT reports `4bd260(532500,41b,hr)` and continues. It then allocates a
1024-byte transient snapshot and copies all 256 live entries into it, rereading
the live array field in source copy order.

The source samples `timeGetTime`, starts with elapsed 10 and previous elapsed 9,
then loops while unsigned elapsed is below the supplied duration. At a changed
elapsed value, it interpolates the requested RGB channels from the snapshot
and target, and performs one direct SetEntries for that range. Equal elapsed
values skip the RGB update/SetEntries but still resample the source clock.
Elapsed is `currentTime - initialTime` with source UInt32 wrapping.

For each channel, the arithmetic is the source wrapped 32-bit product followed
by signed integer division truncating toward zero:

`old + signed32((target - old) * elapsed) / signed32(duration)`

The stored byte wraps to eight bits. There is no float interpolation, color-space
conversion, minimum frame increment or forced channel default. A duration of
0..10 takes the source immediate-final branch after GetEntries/snapshot/initial
clock sampling. Menu duration 1000 and Story duration 750 remain literal caller
inputs. The physical clock must progress synchronously to let these calls finish;
repeating an unchanging clock forever reaches the native operation bound rather
than inventing a source completion.

After duration expiry, the source elects `4bb800(start,count,target,0)`, which
copies/applies the final entries with the existing cooperative wait behavior,
and frees the transient snapshot. Intermediate SetEntries HRESULTs are ignored
by this original body. Final `4bb800` HRESULT does not prevent snapshot release
or turn the source void routine into a new Boolean failure API.

For nonzero `start`, source interpolation indexes `target[start+i]`, while final
`4bb800` copies `target[i]` into the live range beginning at `start`. This
asymmetry is retained and compared for ordinary partial ranges; the menu/Story
full-range calls use start zero. A synchronous palette endpoint may apply each
source intermediate palette to physical indexed presentation. This module does
not invent additional rendering frames during the blocking call.

## Scheduled tick, cancellation and backup

`4bbb70` consumes an already configured source backend. It does not fabricate a
setup function or convert `4bbd90` into that setup. The source fields are:

| Hex offset | Meaning |
| --- | --- |
| `+c` | live 256-entry data |
| `+10` | backup 256-entry data |
| `+14` | table target, or zero for packed RGB mode |
| `+18` | persistent saved starting entries |
| `+1c` | packed RGB target |
| `+20` | duration |
| `+24` | start clock |
| `+28` | previously applied elapsed |
| `+2c/+30` | start/count |
| `+34` | active flag |

An inactive tick returns 0 without a clock call. An active tick samples source
clock, subtracts `+24`, and finalizes through `4bbd20` when unsigned elapsed is
at least duration. Otherwise a repeated elapsed suppresses intermediate writes;
a changed elapsed interpolates RGB from saved `+18` to table `+14` or packed
RGB `+1c`, preserving the fourth bytes and issuing direct SetEntries. It stores
the captured elapsed at `+28` after the physical callback and returns 1.
Intermediate SetEntries failures are ignored, matching the source.

`4bbd20` first clears active `+34`. A nonzero table target elects whole `4bb800`
and clears `+14` after that callback returns. Packed RGB elects whole `4bb910`
with the low three bytes and flags zero. This immediate finalization also
occurs when explicitly cancelled before duration. It does not free persistent
saved entries or unlink a palette. Uniform final fill reports its original
SetEntries error through `4bd260(532500,29f,hr)`; table final SetEntries follows
existing `4bb800` behavior without an added diagnostic.

`4bb8c0` is a separate backup application. With a nonzero backup `+10`, it
copies all 256 backup words into the current live array, rereading the live
field during copying. It then elects the raw cooperative wait if present and
SetEntries using the retained backup pointer. With no backup it performs no
physical call. It ignores the argument and physical return as the original.

These operations preserve the backend's original palette-list node/ownership.
Transient fade snapshots are allocated/freed in the blocking body; source
backend destruction remains the existing owner responsible for its persistent
`+c/+10/+18` arrays. No light tables or extra native palettes are allocated here.

## Validation and limits

The ordinary comparison suite passes **471 whole original calls / 2,517 ordered
full snapshots**. It checks every byte of a 65,536-byte worker heap and
294,912-byte original global range, those same ranges before every physical,
clock, allocator/free or diagnostic callback, ownership token history, meaningful
EAX and exact original stack pops. It includes both real menu/Story durations,
repeated source timestamps, ordinary immediate durations, full/partial/empty
ranges, retained scheduled table/RGB histories, early/repeated cancellation,
normal UInt32 clock wrap, backup application and synchronous valid alias changes.
Device-error profiles include failing GetEntries, SetEntries and cooperative
wait returns, preserving each routine's actual diagnose/continue behavior.

Scheduled fixtures explicitly supply a valid source field graph; these checks
do not claim recovery of an absent scheduling setup entry. Physical callbacks
provide declared palette data/HRESULTs and controlled timestamps. Full source
body parity over those finite inputs is separate from real-time presentation,
physical palette acceptance or a live main-menu/Story walkthrough.

Exact-sized captured replay passes **76 calls / 260 callback snapshots** under
ASAN/UBSAN. Backends are separate exact 56-byte allocations, interfaces/holder
four bytes, palette vtables 28 bytes and cooperative vtable 92 bytes. Live,
backup, target, saved and callback-replacement tables are separate exact
1024-byte allocations; every source transient allocation is separately sized.
Replay checks raw digests, callback arguments/buffers/outputs, final bytes,
meaningful EAX and caller host/owner binding preservation. All four dependency
sources are sanitizer-instrumented. LeakSanitizer is unavailable on this macOS,
so leak detection is disabled; the ordinary oracle verifies source allocator/
free identities, and replay storage uses RAII.

Reproduce from the repository root:

```sh
work/test-env/bin/python Tests/compare_palette_fade_runtime.py
work/test-env/bin/python Tests/build_palette_fade_validation.py
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
work/palette-fade-agent/exact-sized-replay \
work/palette-fade-agent/sanitizer-replay.bin.gz
```

The build also checks strict C11 header declarations, C++17 with
`-Wall -Wextra -Werror` and Swift public import. Logs, `report.json` and compiled
source/header hashes are in `work/palette-fade-agent`. No native Swift host,
Xcode project, simulator or physical device was changed by this handoff.
