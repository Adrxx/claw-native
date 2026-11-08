# Original PAL resource and physical palette orchestration

`PaletteResourceRuntime` recovers the source PAL expansion, palette creation, source object/list ownership, palette updates, display attachment and bounded timed color changes. It replaces a format-only PAL expansion shim while preserving DirectDraw/GDI/resource/map/diagnostic calls as exact rich services. It composes frozen `AmbientAudioBackendRuntime` for complete source CPtrList operations; frozen image, light-table, scene and render modules are not edited or duplicated.

The oracle is the unchanged v1.0 `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. All 14 actual MAIN.PAL files come from the separately pinned retail archive already used by resource fixtures. Their version identity against the original v1.0 installation is not assumed. No reference gameplay implementation is used.

## Actual source routes and graph

All offsets are hexadecimal bytes. The **palette resource manager** is scene `+18`, a 104-byte / 26-word object with vtable `513b28`, parent scene `+c`, CString map `+10`, backend graphics manager `+1c` and source `+64` field. Its constructor belongs to frozen scene initialization. It is distinct from the six-word light-table manager at application `+58`.

The actual level-start resource route is vtable `513b28+24 → 4d4420(resource,nameOverride,flags)`, RET 12. It locks the REA resource, allocates a **20-byte / five-word** wrapper `{VT513d78,manager+1c,0,parentScene,0}`, then invokes wrapper virtual `+28 = 4d65a0(raw768Bytes,flags)`. That selects `4bcac0 → 4bb240 → 4bb100` with CreatePalette flags `0x44`. Success/failure unlock ordering and wrapper cleanup are preserved. The name defaults to the resource's first word when no override is supplied; success copies it into an original 80-byte local and inserts the wrapper via `4f62a8(manager+10,key)`, writing the returned slot.

The separately requested sized-memory route is `4d6620(data,size,flags) → 4bcbc0 → 4bb5a0 → 4bb100`. `4bb5a0` rejects sizes below 768 and selects the **final 768 bytes**, allowing leading bytes. The ordinary `4bb240` reads exactly 768 bytes without a size argument. Both preserve every three-byte source entry in byte order, expanding bytes 0/1/2 unchanged and setting byte 3 to zero. That fourth byte is palette reserved/flags state, not inferred image alpha.

The backend graphics manager's first word is the physical DirectDraw device token. Its palette CPtrList begins at `+3d4`, seven source words with 12-byte nodes and original pooled block ownership. Source list construction `4f5133` is already owned by frozen SoundTrigger; this module does not invent an all-zero manager. The backend palette object is **56 bytes / 14 words**, initialized by `4bcac0/4bcbc0/4bcb40`. Stores clear words 0..6 and 11..13, leaving words 7..10 as original allocation seed. Important fields are node token `+0`, COM palette token `+4`, copied 1024-byte base entries `+c`, allocated 1024-byte backup `+10`, optional allocation `+18`, and `+34` field.

`4bb100` allocates/copies base entries, then allocates backup entries, then calls device virtual `+14` CreatePalette `(device,flags,entries,backend+4,0)`. A failed HRESULT emits `4bd260(532500,4b,hr)` and returns zero. A failed backup allocation alone does **not** prevent successful creation. Backend object/base-buffer allocation failures can instead reach unsafe unchecked source accesses; those are stopped prefixes, not invented clean failures.

## Stable ABI and integration

Initialize `ClawPaletteResourceContext` to zero then call defaults. Supply a live raw `ClawSceneActorHost`, typed `ClawPaletteResourceGlobals.cooperativeHolder` sharing original `541374`, rich dependencies, and source-owned allocation/free services. With `composeLists=1`, list source bodies execute through frozen AmbientAudioBackend over the same live heap. With zero, exact list calls remain dependencies. No second private heap/list identity is introduced.

`ClawPaletteResourceCall` retains original function, receiver and up to eight raw arguments. COM methods use receiver zero and the interface as argument 0. A `localMask` bit identifies an argument normalized to token zero, with synchronous bytes exposed through the buffer fields. CreatePalette's local expanded entry array uses argument-2 bit `4`, 1024 bytes. MFC local name uses argument-0 bit `1`, exact NUL-terminated bytes. Heap entry/output pointers retain their original tokens, including the CreatePalette output at backend `+4`. Buffer pointers cannot escape the callback.

`systemPaletteScratchToken` owns 1024 caller bytes representing the original `4bbf60` uninitialized local entry-array seed. It is required only by that function and has no original heap identity. Tests initialize the original fixture stack before its unchanged function executes and pass the same seed. Positive GDI services write the complete requested span; short positive writes/unobserved stack seed must not be replaced with invented zero colors.

`claw_palette_resource_capture_owner` composes only the verified **`46afe9..46b000` instruction prefix**, not a duplicated whole `46aeb0`. It traverses owner `+2c → wrapper+10 → backend+4`, then calls physical palette virtual `+10` GetEntries `(palette,0,0,256,owner+360)`. The source caller does not inspect that HRESULT before continuing. Owner `+360` is therefore the complete physical GetEntries result, including reserved bytes; it is not necessarily a direct memcpy of MAIN.PAL under every physical driver.

## Whole bounded function inventory

| Entry | Original stack arguments / behavior |
| --- | --- |
| `4d4420` | resource, optional name override, flags; normal locked-resource factory |
| `4d44f0` | raw triples, name, flags; raw wrapper factory with direct heap name |
| `4d4570` | file name, map name, flags; whole wrapper, **inner file loader `4d6560` explicitly unrecovered** |
| `4d65a0`, `4d65e0` | bytes, flags; triple / existing quad entry load |
| `4d6620` | bytes, size, flags; sized triple load |
| `4bcac0`, `4bcb40` | bytes, flags; 56-byte triple / quad backend factories |
| `4bcbc0` | bytes, size, flags; sized backend factory |
| `4bb240`, `4bb100` | device, bytes, flags; triple expansion / exact quad CreatePalette |
| `4bb5a0` | device, bytes, size, flags; final-768 expansion |
| `4bc9b0`, `4bca10` | palette token; list registration / removal and destruction |
| `4bb2a0` | none; backend cleanup |
| `4d6670`, `4d4810`, `4d47f0` | release / base destructor / deleting wrapper (delete flag) |
| `4bb800` | start, count, quad entries, ignored fourth argument; source copy, cooperative call, SetEntries |
| `4bb870` | none; allocate missing backup then GetEntries into it |
| `4bb910` | start, count, R byte, G byte, B byte, SetEntries flags; fill RGB, preserve reserved bytes |
| `4bb990` | start, count, R byte, G byte, B byte, duration; whole clocked color transition |
| `4bbf60` | none; whole system-palette edge preservation and update |
| `4d6690`, `4b96f0` | display gate / palette token plus ignored second argument; SetPalette |

These boundaries/argument counts are checked against actual instructions and return stack, including misleading Ghidra signatures for `4bb800/4bb990`. The resource manager/type-wide destructor, general file PAL/PCX/BMP loading, CString map internals, exception machinery and physical COM/GDI remain separate boundaries. `4d4570` comparisons adapt its exact original virtual file-loader call; that is not recovery of the inner parser.

## Updates, clocks and ownership quirks

`4bb800` copies complete four-byte entries into base storage. If `541374` is nonzero it traverses holder word 0 to a DD interface and invokes virtual `+58 (dd,1,0)` before palette SetEntries. The source fourth stack argument is ignored and physical SetEntries receives flags zero. The raw SetEntries HRESULT is returned.

`4bb870` allocates backup if missing, returns without physical reads if that allocation fails, otherwise queries all 256 entries and emits diagnostic line `261` on failure. `4bb910` modifies only RGB bytes, preserves reserved bytes and calls SetEntries with the caller's flags, emitting line `29f` on failure.

`4bb990` first physically refreshes base entries, reporting line `2bc` for failed GetEntries but continuing. It allocates/copies an exact 1024-byte snapshot, captures multimedia time, starts elapsed at 10 and previous at 9, and loops while unsigned elapsed is below duration. Changed elapsed values update channels using signed 32-bit wrapping multiply and signed division by duration, truncating toward zero, then SetEntries with flags zero. Each loop polls time again; repeat timestamps skip the color update but still poll. Final source `4bb910` sets the exact target RGB, then the temporary snapshot is freed. Durations <=10 still refresh, allocate/copy, poll once, fill and free. No host sleep, fabricated timing or float opacity is introduced. Nonadvancing time/domain overflow can reach a bounded native fault rather than claimed original success.

Flag bit 1 in wrapper load invokes `4bbf60`: CreateDC `546910`, GetDeviceCaps `546894` indices 104/106, two GetSystemPaletteEntries `546914` calls, DeleteDC `5468b0` only after both succeed, then RGB edge stores and `4bb800`. Failures before both queries complete intentionally leave the DC un-deleted. The copied edge colors preserve base reserved bytes. Source placement uses a 256-entry local tail even when reported device size differs, hence the explicit local-seed profile. Out-of-stack-domain caps are rejected natively, not claimed valid source paths.

`4d6690` reads wrapper parent `+4 → holder+10 → target+18` bit depth. Non-8-bit returns one without attachment. Eight-bit uses target `+2c` surface and `4b96f0`, which invokes DD surface virtual `+7c` SetPalette, emitting diagnostic line `1b8` on failure.

Cleanup removes the source list node, clears backend node/COM pointer/word 2, frees nonzero `+c/+10/+18`, and zeroes `+34`. **It does not call COM Release.** Wrapper cleanup zeros `+10`, sets base fields/vtable as original, and optional deleting wrapper frees its 20 bytes. Other seeded fields and live physical palette identities are preserved. Physical device teardown remains its own source graph.

## Evidence and limits

The main suite passes **1,655 original/native comparisons including four stopped unsafe prefixes**, **7,693 ordered full snapshots**, and **1,129 distinct original instruction addresses**. It compares a complete 1 MiB heap, 320 KiB global image, allocation/free/liveness, physical-service palette state, return values and source callback order/buffers. DLL import resolution and COM/GDI/resource/map/diagnostic methods are explicit transports; source instructions are unchanged. Local scratch has declared fixture identity and is excluded from an original heap-identity claim.

All 14 actual MAIN.PAL files run through normal resource and sized routes, flags 0/1, varied prefixes, physical owner GetEntries and cleanup. Coverage includes short-size failures, failed CreatePalette, source null/allocation/name-overflow prefixes, nonfatal backup allocation failure, 12 retained managers each with 25 resources and mixed deletion order, seeded raw fields, palette entry/fill/display/GetEntries failures, 90 clock trajectories including repeat/wrapped times, system-palette success/failure/caps/local-seed profiles, and the optional file-wrapper boundary.

Strict C11, Swift import/link and 96 exact logical-buffer PAL create→GetEntries→set/fade→display→list cleanup histories pass ASAN/UBSAN. The private arena rejects accesses beyond each original-sized allocation. Logs, `verification.json` and reproduction commands are in `work/palette-resource-agent`. This establishes finite source orchestration and native memory evidence, not actual DirectDraw, Mac/iPad UI acceptance or complete-game equivalence. No shared files, project, devices or Xcode builds are changed by this worker.
