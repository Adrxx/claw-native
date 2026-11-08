# IFC read composition

`InterfaceReadCompositionRuntime` adds typed native composition of the **already recovered** ordinary load-mode reader in `InterfaceFileRuntime`. It recovers no additional original function body and contains no independent IFC parser. The unchanged original loader still determines node records, CString lengths, children, initialization, selection, failure and cleanup. The facade makes argument shape and ownership explicit for native menu integration.

Original executable: `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. The reader inventory uses existing private original disassembly/decompilation in `work/interface-file-agent/`, read-only. No shared source or original-reader implementation is changed.

## Inventory and ownership

| Elected source routine | Ownership / boundary |
| --- | --- |
|4dcdf0,4dcd10|Frozen whole borrowed-memory/file loader; facade calls those exact entries|
|4ff5f9,4f72c9,4ff645,4ff670,4ff682|Frozen borrowed-file ctor/attach/detach/destruction behavior internal to4dcdf0; no redundant public port|
|4ff79f,4ff822,4ff8a8|Frozen public CMemFile Read, Seek, GetBufferPtr|
|4fda33|Frozen internal CArchive constructor|
|4a16a7,4a16d6,4a1709|Frozen internal archive scalar byte/word/DWORD reads|
|4fd914|Frozen internal variable string-length decode|
|4fd877|Frozen internal load-mode CString serialization|
|4fdba5,4fddbd|Frozen internal Read and FillBuffer|
|4fdb0f,4fdb55,4fdb97, load branch of4fdd43|Frozen internal archive close/destructor/release; store-mode flush remains explicit|
|4df490,4deb50|Frozen original node/component load serialization; no replacement schema|
|4fc139|Still explicit filename/status/CString-output transport; not another read algorithm|
|4fe675(3,0)|Explicit source archive-exception request; stopped unsafe prefix, not successful empty tree|
|4f66f3|Wide CString conversion service for non-retail wide-string variants; no ordinary retail election measured|

The whole4fc139 is47 bytes, RET4. It calls4fc168 with a local280-byte status structure, then4f65f2 constructing the output CString from status+18, and returns the output cell.4fc168 zeroes that structure and calls the `5469cc` path-copy import; valid handles additionally elect `546a58` GetFileTime, `546a60` GetFileSize, `546a64` GetFileAttributes and time conversion4f5003. Existing menu tests stop this graph at4fc139 and supply an **explicit empty filename** transport. They do not prove Win32 file-status/timestamp behavior. That boundary is preserved, not relabeled recovered. No additional ordinary menu-reader body remains to be invented.

## Native transport recipe

1. Construct the source256-byte interface controller with4dcc40(width,height). Actual StateFive owns its later derived vtable/callback elections.
2. Supply caller-owned, disjoint40-byte CMemFile,68-byte CArchive and4-byte CString scratch aliases in the frozen context. These replace original automatic addresses; they are not persistent original allocations. Preserve initial seeds and keep them alive for the synchronous call.
3. Retain the exact borrowed IFC byte span. `ClawInterfaceMemoryLoad` is28 bytes: graphics, bytes, length, imageResolver, three trailing source arguments. Normal StateFive passes three zeros. `claw_interface_read_memory` invokes whole4dcdf0 with seven words/RET28, creating/attaching the borrowed file and detaching it before return.
4. For an existing file, `ClawInterfaceFileLoad` is24 bytes: graphics, file, imageResolver, three trailing arguments; invoke whole4dcd10 with six words/RET24. The caller owns the file object and its physical lifetime; archive close rewinds unread bytes but does not close the file.
5. Preserve raw52e1c8/52e1cc empty-string aliases and original vtables. Resolve physical allocation/free4f63ec/4f6428 using exact requested lengths. No implicit zero initialization or guessed success is added by this facade.
6. Forward rich dependency packets synchronously. Original automatic receiver/pointer arguments become token0 and `localMask` bits; borrowed buffers must be mutated in place.4fc139 in the borrowed-file profile has receiver0/mask257 and buffers40-byte file then4-byte output CString. The output must be a valid constructed CString cell, with source refcount/lifetime behavior; a raw path pointer alone is not enough.
7. Source file virtual+58 GetBufferPtr(3,0,0,0) decides direct versus buffered reading. Ordinary physical-file adapters may report0, implement virtual+3c Read(destination,count) with actual bytes/short reads, and virtual+30 Seek(signedOffset,origin) with actual position. The new tests use explicit addressed adapters rather than inventing a second CFile implementation. Do not falsely report direct buffering unless output pointer aliasing is genuinely supplied.
8. Keep meaningful original EAX separate from covered/completed status and shared fault. Missing spans/services1, EOF/unsafe2 and ABI/operation limit3 remain diagnostics. Truncation reaches source4fe675(3,0); no native exception unwinding or clean rollback is claimed.

The ordinary file-profile oracle does not open or write user files: it reads immutable retail bytes and explicitly transports Read/Seek/filename results. Physical Windows handle/status behavior and actual host disk errors are outside this proof. StateFive image resolution remains an explicit callback in these reader tests; joining the real image-controller/PCX/display graph is a separate existing source task.

## Verification

Run:

```
work/test-env/bin/python Tests/compare_interface_read_composition_runtime.py
work/test-env/bin/python Tests/compare_interface_read_file_rewind.py
zsh work/interface-read-composition-agent/check.sh
```

The new helper compiles all dependencies into its own private directory; it never imports a frozen helper that recompiles into someone else's work. Whole-call comparisons retain every byte of4MiB heap plus520000..54ffff globals, ordered service packets and rich automatic file/archive snapshots, meaningful EAX and RET/SP. Source stack/SEH implementation and physical Windows allocation are not native identity claims. Standalone memory-file comparisons include all40 receiver bytes; only genuinely automatic alias fields are normalized. The4-byte native scratch cell always normalizes its source stack identity.

Retail borrowed inputs are CLAW.IFC14249 bytes/133 nodes/1064 image calls and CLAWWITHLOBBY.IFC14678 bytes/138 nodes/1104 image calls. Tests also execute both complete trees through ordinary non-direct file transport with31/500/4096-byte short-read limits, source allocation/release of the archive4096-byte buffer, read-buffer reuse and close rewind. They cover mandatory-image failures, truncation throw prefixes and retained memory-file reads/seeks/direct spans. Exact-span sanitizer replays allocate the retail input at its **actual** byte length, all nodes176, components108, controller256, CStrings length+13, and automatic aliases40/68/4.

Final differential result: **202 whole unchanged-original compositions /51,904 ordered full snapshots /8 matched EOF prefixes /2,570 instrumented text addresses /2,577 total instrumented addresses**. A separate retained file proof passes **6 calls /7,940 full snapshots** with both real IFCs followed by an84-byte unread trailer, requiring an actual negative Seek at archive close and restoring the parser endpoint before caller-owned file destruction. Counts are separate; this is not additional original-function recovery.

Strict C++17 warning-clean compilation, C11 header assertions and executed Swift ABI checks (memory request28/file request24) pass. **6 exact-span ASAN/UBSAN replays /7,912 callback snapshots** pass: actual133/138-node borrowed loads plus their constructors/destructors. This sanitizer corpus covers the borrowed-memory profile; physical ordinary-file adapters/rewind are differential-tested, not sanitizer-replayed. Alloc/free endpoints remain replay transports; no physical Windows allocator or UAF/liveness poisoning claim is added. Logs are `verify.log`, `rewind.log`, `checks.log` and `swift-abi.log` in the private work directory. This proves composition of the existing original reader, not a new MFC implementation or whole native menu/device acceptance.

The exact-size native replay source is retained as `Tests/exact_sized_interface_read_composition.cpp`; the original-capture comparator emits its private corpus under work/interface-read-composition-agent. Original inputs/captures remain excluded from the source checkpoint.
