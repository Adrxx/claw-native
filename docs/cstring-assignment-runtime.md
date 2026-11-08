# Original ordinary CString assignment

`CStringAssignmentRuntime` recovers three complete original v1.0 procedures and composes the existing release, allocation and byte-copy bodies. It closes the ordinary name assignment service used by the source image-controller dictionary without adding another CString destructor or allocator.

The unchanged executable is `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private analysis is in `work/cstring-assignment-agent/roots.c`, `copy.c` and their logs. `copy.log` rejects interior address4f6514; no implementation uses it. The separately observed copy constructor4f6449 is not required by ordinary assignment and remains outside this module.

## Exact owned entries

| Entry | Whole span | Original stack arguments / result |
| --- | ---: | --- |
| `4f66cc` |39 bytes|LPCSTR data token; RET4; meaningful EAX is receiver |
| `4f6650` |45 bytes|length, data token; RET8; void |
| `4f655b` |41 bytes|length; RET4; void |

`4f66cc` saves its supplied data pointer, calls lstrlenA import slot `5469e4` when it is nonzero, otherwise selects length zero, then invokes `4f6650`. It does not interpret low-word pointers as string-resource IDs. That special constructor behavior remains in frozen4f65f2.

`4f655b` reads the current CString data token and tests signed reference count greater than one, or signed capacity less than requested length. Either condition elects frozen4f64ba release/clear followed by frozen4f6480 allocation. Otherwise the existing data buffer is retained, including locked negative-reference buffers with adequate capacity. No new shared-buffer shortcut, growth policy or empty-string optimization is inserted.

`4f6650` calls the whole prepare method, invokes the frozen overlap-safe4a4a80 with the current destination token, saved source pointer and requested count, re-reads the receiver to store length at data−8, re-reads it again, and stores NUL at data+length. Thus a callback or overlapping copy can change what later stores address. The saved count is not recalculated when a callback changes the source text; it may include an interior NUL after such a mutation.

The CString object is one four-byte data-pointer cell. Its data header contains signed references at data−12, length at data−8 and capacity at data−4. Ordinary nonempty source allocation is **length+13 bytes**, including the twelve-byte header and final NUL. Raw globals52e1c8 and52e1cc remain the original empty header/data identities.

## Existing ownership inventory

| Existing owner | Composed or preserved boundary |
| --- | --- |
| SceneLifecycleRuntime |4f64ba release/clear;4f667d CString-to-CString assignment |
| ActorDestruction |4f6584 destruction, composed inside release |
| PlayerFadeBlendRuntime |4f6480 allocation,4f65f2 constructor,4f6433 empty-cell getter |
| CArrayRuntime |4a4a80 overlap-safe copy and optional4f63ec/4f6428 allocator wrappers |
| LogicStateRegistry |Private bounded assignment used by its own registry; no raw public helper entry |

The new source does not copy those release, clear, constructor or allocation implementations. With optional contexts absent, their exact reached addresses remain dependency calls. Supply the existing contexts to execute the composed source closure. No unsupported service should fabricate allocation or assignment success.

## API and joining recipe

`Sources/CStringAssignmentRuntime.h` exports `claw_cstring_assignment_entry(function, receiver, arguments, argumentCount, context, dependency, user, result)`. Only the three owned entries are public. Unknown entries return zero without changing result/fault. Valid argument counts are one/two/one respectively. Native status one means covered completion; original EAX is separate, with no incidental void-result claim.

The96-byte C11 context borrows the shared scene host, SceneLifecycle context, PlayerFadeBlend allocation view, and CArray context. Every view must address the same raw heap and globals, with cleared fault fields. Host views temporarily substituted for composition are restored on normal and failed returns. They are synchronous borrowed views and cannot be used concurrently during the call. Allocation's empty-string view is refreshed from live52e1cc before its body executes, preserving free-callback alias changes. Physical lstrlenA uses addressed import identity5469e4 through the four-argument dependency ABI. Allocator/new-handler/CRT-thread endpoints remain explicit as defined by frozen CArray.

For source cache names, route ImageControllerLoading's reached4f66cc service into this entry using its exact receiver and LPCSTR token. Supply `lifecycle` so4f64ba executes the existing source release/clear, and `allocation` with its borrowed fade/scene view so4f6480 executes the existing source allocation. Supply CArray with the same allocator mode/global handler profile used by the table/registry. The scene/heap lookup must retain current CString cells, headers and actual allocation liveness. The input argument is a data pointer, not a CString object-cell pointer. Calls to frozen4f667d's locked-copy boundary4f6650 may likewise route into this module.

### Exact byte capacity

The optional byte lookup supplies a writable exact `(token, byteLength)` span or null, without mutating source state during probes. This allows original length+13 allocations and unaligned source pointers while the frozen helpers continue using their existing word-only interface.

For a terminator write at a partial final word, synchronous native scratch holds only the available bytes. It flushes those bytes before the next lookup/service and at body completion. For4a4a80, scratch represents the exact source/destination byte ranges within rounded interface views; overlapping ranges share one scratch view. The frozen CArray body performs its real copy, and only the actual destination count is flushed. No padding is added to the game allocation, no scratch token becomes an original heap identity, and no extra tail bytes are written or read from the caller. This is a native transport adaptation, not recovered scratch allocation behavior.

Without byte lookup, callers use the already declared containing-word capacity of the shared UInt32 host interface. Exact-span gates here enable byte lookup and enforce actual allocation lengths. Copy staging is bounded to1,000,000 bytes; span/overflow/operation guards are native safety extensions.

## Verification and limitations

`Tests/compare_cstring_assignment_runtime.py` executes **411 whole original calls, 1,122 ordered full snapshots and four unsafe prefixes**. Every1MiB raw heap byte,274,432 mapped global bytes, meaningful EAX, allocator/live/free histories and ordered external endpoints are compared. **199 instrumented original text addresses** and **201 total addresses** distinguish `.text`401000..50adb5 from normalized physical import bindings. The release, allocation and copy bodies execute in the original; they are not stubbed in this direct suite.

Profiles include reference counts−3/−1/0/1/2/3/INTMAX, signed capacity tests, empty/null input, explicit lengths, high bytes, unchanged/shared storage, self/substring overlaps, exact new lengths1..255, unaligned input, retained cell sequences and length/malloc/free callback aliases. Stopped prefixes are failed allocation before4f649e, released aliased input before4a4a80, copy overwriting the receiver before4f666f, and an unbounded explicit count before4a4a80. They prove reached state/order and the native rejection; they do not claim original safe returns or successful access to freed buffers.

Physical lstrlenA and CRT allocation/free are addressed transport. Original InterlockedDecrement is represented by a synchronous source-compatible DWORD decrement in the single-thread oracle; native composes the already recovered destructor's corresponding pure state update. No cross-thread atomic scheduling or Windows heap address identity is claimed. Mutable data/header fields remain raw source state, not normalized strings.

`Tests/compare_cstring_image_cache_join.py` separately proves **86 whole source graph calls /12,761 ordered snapshots** across actual disc `STATES_MENU/IMAGES` and `STATES_BOOTY/IMAGES`. The original assignment body now executes inside Archive→Table→Namespace→ImageRegistry→dictionary graphs, yielding20/52 roots and295/452 physical image-init boundary calls, followed by retained duplicate/restore/name removal/REZ cleanup. This replaces the earlier assignment stub without changing frozen modules. Direct key destruction/map clear and physical image/FILE endpoints retain the previous declared boundaries in this joined suite; image pixels, full IFC/Story rendering and physical presentation are outside it.

Private strict gates pass C11, warning-clean C++17, Swift import of the96-byte context, and **31 exact-size ASAN/UBSAN replays**. CString objects are exactly4 bytes and string buffers are exactly length+13 bytes, including odd/non-word capacities, with live/dead lookup enforcement and ordered original snapshots. The new module and frozen release/destruction/allocation/copy sources are compiled under the sanitizers. Other linked frozen graph code is not exercised by those exact-size cases.

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_cstring_assignment_runtime.py
work/test-env/bin/python Tests/compare_cstring_image_cache_join.py
work/test-env/bin/python work/cstring-assignment-agent/checks.py
```

The private scripts link read-only frozen libraries from SceneLifecycle, PlayerFadeBlend and the previously recovered image/resource owners. If missing, use their documented gates to rebuild them; these new scripts do not write frozen work directories. Measured JSON/logs and sanitizer corpus stay under `work/cstring-assignment-agent`. No shared source, native host, PCX work, project, Xcode or device was edited or driven.
