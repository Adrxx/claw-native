# Scheduled palette admission audit

No new scheduled-palette setup entry or argument ABI was established by this
bounded original v1.0 audit. A `PaletteFadeSetupRuntime` API has therefore not
been introduced. Existing [PaletteFade](palette-fade-runtime.md) supports the
recovered tick/cancel bodies and blocking table fade; its scheduled tests
explicitly supply a valid source field graph. They do not establish a setup
body or prove that a retail transition activates that graph.

The unchanged executable is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
This investigation follows that pinned version. Other executable versions,
plugins and custom schedules are outside the audit.

## Verified construction and admission

Whole actual `4bcac0(graphicsManager, raw768Palette, flags)` construction was
executed through frozen PaletteResource and the original, including
`4bb240/4bb100`, physical CreatePalette, list registration and ordinary failure
cleanup. The source-created 56-byte backend has zero table target `+14`, zero
saved-fade array `+18` and zero active flag `+34` (hexadecimal offsets).
The four words `+1c..+28` remain allocation seed, exactly as the source stores
require. They are not converted into invented RGB/duration/start/previous time.

Calling whole original/frozen `4bbb70` on that created backend returns zero,
changes no heap/global bytes and makes no clock or physical update call. The
active gate prevents reading the seeded timing words. The initialized palette
list node and source arrays remain owned by PaletteResource.

A safe ordinary third allocation failure omits backup `+10`, but construction
and registration still succeed. Existing `4bb870` later allocates that backup
and executes the source GetEntries path. That getter does not assign target,
saved-fade or active fields. Failing CreatePalette HRESULTs follow original
array/backend cleanup and leave no registered palette. List removal and
persistent array release run through whole existing `4bca10/4bb2a0`; no extra
cancel or scheduler allocation is inserted.

These checks use a valid declared source CPtrList manager graph with growBy10,
raw RGB input and explicit physical palette/allocator services. They do not
claim to execute the whole graphics manager bootstrap or an actual device.

## Real callers and established owners

The private Ghidra reference audit and instruction checks find four direct tick
call sites. Each reads a palette backend from `owner+2c -> wrapper+10`, checks
`backend+34`, and calls `4bbb70` only when it is nonzero:

| Tick call | Caller entry / measured source context |
| --- | --- |
| `435bd8` | `435b80`, application/state frame |
| `449ab2` | `449a60`, application/state frame |
| `45b74e` | `45b650`, original State5 frame (boundary verified by source/instructions; initial Ghidra manifest lacked its function) |
| `48d3e4` | `48d390`, application/state frame |

The direct cancel calls are tick expiry at `4bbb98` and transition `48f482`
inside `48f470(duration)`. The latter is already frozen
[BootyResults](booty-results-runtime.md) ownership. It admits a nonzero palette
wrapper, cancels its existing scheduled state, then either applies the backup
for duration zero or blackens and executes blocking
`4bbd90(0,256,backup,duration)`. It publishes the actual palette wrapper through
scene palette controller `+64` and invokes its real display slot. This routine
does not configure scheduled target/saved/duration/start/active fields.

The State5 path `45e1b0` likewise directly elects blocking table fade with
literal duration1000. Story/shared screen setup reaches `48f470` and existing
blocking table/color bodies through its frozen Results/Story owners. Original
`48f500(duration)` is already frozen [PaperRoll](paper-roll-runtime.md), with a
type0 fader and descriptor; it is not palette scheduler setup. These established
owners were inspected and their original transition bodies decompiled privately.
They have not been duplicated in a new family.

Additional direct `4bbd90` callers are `42a060`, `48f370`, `48ffa0`, `48f470`
and `45e1b0`. The direct clock/tick/cancel relationships and transition decompiles
are retained in `work/palette-fade-setup-agent/callers-and-functions.txt` and
`transitions.c`. Clock and physical joining remain the existing PaletteFade
contract: `546df0` source milliseconds, exact physical GetEntries/SetEntries,
cooperative alias541374 and source allocator/free identities. A real setup ABI
would require a separately identified entry/caller before adding initialization.

## Bounded write audit and its limits

A Capstone audit inspected **4,072 Ghidra-discovered function spans** for explicit
non-ESP destination writes to field offset `34` and related scheduler offsets.
It recorded **116** four-byte writes at offset34 and **31** broad multi-field
cluster candidates. Offset matches alone are not class identities. Inspected
candidates include already identified resource archives, scene/player/actor
fields, spatial grids/iterators and IFC hierarchy objects. For example,
`4dd180`'s nonzero `+34=400` belongs to the IFC controller with vtable513e88,
not the nonpolymorphic palette backend's active flag.

There are **17** direct `timeGetTime` import calls in the saved instruction
listing, with **zero** overlap with those broad setup-field candidates. Within
`4bb000..4bbfff`, explicit relevant nonstack writes are persistent-array release,
tick's previous-elapsed store and cancel's zero stores. Palette factories
`4bca20/4bcac0/4bcb40/4bcbc0` clear their target/saved/active fields. No eligible
setup entry was established in the traced palette/state caller graph.

This is a bounded static/caller finding, not proof that no possible indirect,
computed, aliased or undiscovered write exists anywhere in the executable.
Ghidra's initial manifest lacks some real function boundaries, so absence of a
candidate cannot be promoted to a whole-binary theorem. The current handoff
records the unsupported assumption precisely: there is no justified new setup
API yet. It also prevents treating source-configured scheduled fixtures as
retail scheduling evidence.

## Ordinary and exact-size validation

`Tests/verify_palette_schedule_admission.py` passes **88 whole original calls /
488 ordered full snapshots** across eight valid allocation seeds, ordinary
CreatePalette HRESULTs and safe missing-backup allocation histories. It compares
all 65,536 worker heap bytes and 294,912 global bytes, ordered rich callback
arguments/buffers/digests, allocated/freed token histories, meaningful EAX and
source admission behavior.

Exact-sized ASAN/UBSAN captured replay passes **11 calls / 50 callback
snapshots**. It rebuilds the four frozen dependency sources with sanitizers and
executes actual construction, inactive tick, backup getter and list/backend
cleanup. Manager storage is exactly2180 bytes, each created backend56, palette
arrays1024 and each recorded CPtrList pool block its exact source allocation
size. Interface/vtable spans are separately sized; raw RGB input is exactly768 bytes. No
source setup or malformed input profile is introduced. LeakSanitizer is
unavailable on this macOS runtime, so leak detection is disabled; original
allocator/free histories are compared separately and replay uses RAII storage.

Strict C11, C++17 with `-Wall -Wextra -Werror` and Swift import gates pass for the
existing PaletteFade/PaletteResource ABI. No new runtime ABI is claimed. Source
hashes were checked after validation. No shared native/project/device file or
existing frozen runtime was edited.

Reproduce the source admission evidence from the repository root:

```sh
work/test-env/bin/python Tests/verify_palette_schedule_admission.py
work/test-env/bin/python Tests/build_palette_schedule_admission_validation.py
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
work/palette-fade-setup-agent/exact-sized-replay \
work/palette-fade-setup-agent/admission-sanitizer-replay.bin.gz
work/test-env/bin/python Tests/audit_palette_schedule_candidates.py
```

The static audit uses the private Ghidra function/reference manifest saved by
`work/palette-fade-setup-agent/scripts/AuditPaletteCallers.java`; its script and
headless invocation are recorded in that scratch directory/audit log. Full
results, compiled source hashes and scope are in `admission-report.json`,
`field-write-audit.json`, and `{admission,field-audit,build,sanitizer}.log` there.
