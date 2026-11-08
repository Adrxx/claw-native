# Original save-file serialization and CFile writer

`Sources/SaveFileRuntime.h/.cpp` recovers twelve complete bounded original functions from v1.0 `CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. It composes frozen checkpoint cache methods in tests, preserving their ownership. No guessed format, save-success message, archive rewrite or alternative checkpoint logic is added. Tests compare the original instructions to the native raw-token routines using the same declared physical file, CString, path, RNG and exception transports.

## Stable C11 contract

`claw_save_file_entry(function,receiver,args,count,context,dependency,user,result)` returns support/completion separately from original meaningful EAX. Source void results normalize0. Context owns frozen `ClawSceneActorHost`, a byte-span lookup, original empty-CString identity, four scratch tokens and traversal/step limits. All pointers are32-bit tokens; no host pointers are truncated. Argument counts are checked before mutation. Each call resets fault; unsupported function returns0 without fault. Fault1 is a missing span/service,2 invalid ABI/domain,4 bounded traversal/permutation iteration. Exception adapters may set fault3 before returning to stop later source writes. These faults are host safety extensions, not original successful returns.

The four **caller-owned automatic-local views** are CFile16bytes, path260bytes, SECURITY_ATTRIBUTES12bytes, and WriteFile count4bytes. They replace original transient stack addresses and must support interior token lookup. They are not original heap allocations and must not appear as extra source allocator events. Original heap allocations/free still use `scene.allocate/free`, including the payload's exact byte count. Direct CFile entries receive a live raw16-byte receiver and use the other three scratch views.

| Original entry | Arguments | Behavior/result |
| --- | --- | --- |
|49bbc0 | none, thiscall | Whole file writer; returns sampled record count or0 |
|49bf70 | data,byteCount; receiver unused | Table-XOR checksum; returns UInt32 |
|49bfb0 | permutationLimit, thiscall | Initializes raw48/4c/50/54; consumes one rand; returns division quotient |
|49c000 | none, thiscall | Whole rejection/permutation next; returns accepted state−1 |
|49c030 | data,byteCount, thiscall | Whole byte XOR; source void |
|49c070 | data,byteCount, thiscall | Whole wrapper invoking49c030; source void |
|4f72c9 | none, thiscall | CFile constructor; returns receiver |
|4f7369 | none, thiscall | CFile destructor; source void |
|4f7448 | name,flags,errorObject, thiscall | Whole CFile open; returns1/0 |
|4f75aa | data,byteCount, thiscall | Whole write and error/short-write election; source void |
|4f766e | none, thiscall | Whole close and clear/error order; source void |
|4f650f | none, thiscall | CString empty helper with exact length/refcount branch; source void |

The source immutable32-word polynomial table52d780 and256-word checksum table52d800 are embedded exactly from the pinned executable; private `source-tables.inc` records their extraction. Source checksum is **not normal rolling CRC**: for nonnull data it initializesFFFFFFFF and XORs `table[byte]` for every byte, without shifting the accumulator. A null pointer returns0 regardless of requested size. Empty nonnull input returnsFFFFFFFF.

## Exact manager/application construction recipe

Application+60 owns a **0x58-byte /22-word save manager**, separate from audio and music objects. Original426546 allocates58, then the inline constructor interval426565..42658d:

1. Calls CPtrList constructor4f5620 with block size10. Vtable5107bc; words+4/+8/+c/+10/+14=0,+18=10.
2. Constructs CString at+1c with shared empty data token52e1c4 (original52e1c8 points at its12-byte header).
3. Clears eight header words+20..3c, stores+40=0,+44=4d505255. **+48..54 retain heap seed** until permutation initialization.

At4265aa the object is stored into application+60. The caller then calls49b840 with literal525618=`CLAW.USR`. That separate path/load/default-player boot is outside this module. Its observed graph formats `%s\\%s` using current-directory or Windows-directory services, handles a CD-ROM drive path, tries the reader49b9a0, and resolves/creates default `Player`; neither that reader nor its record-creation body is silently substituted here.

`claw_save_file_initialize_manager` implements only the exact constructor stores above over an already allocated88-byte object. It is named as a portable helper, not claimed to be an entire original startup function. One unchanged-original instruction-interval comparison executes the actual CPtrList/CString constructors and stops before unrelated path initialization. Initializing this manager leaves its pathname empty, so49bbc0 returns0 until its CString+1c and linked player-record list are populated by the caller's supported startup profile.

The save manager is a CPtrList: +4 head,+8 tail,+c signed count,+10 free nodes,+14 allocation blocks,+18 block size. Each live list node is `{next,previous,dataToken}`; data is an actual **0x2648-byte /2450-word player record**, with word0 vtable50feac. Serialization excludes that vtable and copies the following **0x2644bytes /2449words**. Frozen CheckpointLogicRuntime owns each player's45 checkpoint slots and15 best-score slots. Do not place a checkpoint packet directly into this manager's list in place of the full player record.

## Writer ordering and source-format bytes

49bbc0 reads manager+1c CString's length at data−8. Empty returns0 before any file work. It then requires **signed count+0c>0**. With both gates open:

1. Construct stack CFile (VT510844, handleFFFFFFFF, ownership0, empty filename).
2. Open manager's current pathname with flags1000 and no error object: access80000000 (read), share0, create disposition2 (truncate/create), attributes80, no template. Close it.
3. Read manager's pathname again and open with flags1: access40000000 (write), share0, disposition3 (open existing). Failure destructs the CFile and returns0. Thus reopen or allocation failure may already have truncated the old file.
4. Sample current list count into a local and compute **wrapping UInt32 count×2644**. Allocate exactly that size. Null allocation destructs CFile and returns0.
5. Walk head+4. Cache each node's next before copying its data+4 forward for991 words. List traversal does not use count as its loop bound. Fewer nodes leave allocator seed in the payload tail; extra nodes would overflow the original allocation and are a bounded native span failure rather than fabricated success. The native copy preserves the original forward-copy alias semantics.
6. Compute the payload checksum, store manager+24. Store **live** count+0c into header+2c and live manager+40 into header+28; the returned count and allocation length remain the earlier sample. Other header words are preserved.
7. Encrypt32bytes at manager+20; encrypt the full payload separately. Write the encrypted header first, then encrypted payload.
8. Decrypt **only the header**, free the still-encrypted payload buffer, destroy CFile, return the earlier sampled count.

The32-byte header is therefore the source manager's raw+20..3f block, containing preserved word0, checksum at+4, manager40 value at+8, live count at+c and four preserved trailing words. Its byte values are recovered by source stores and encryption, not guessed structure names. Endianness is the original little-endian raw layout used by the native host.

Each49c030 call seeds the **shared CRT thread RNG** from current manager+44 using4a3040, then49bfb0 consumes exactly one4a3050. The remaining byte loop calls49c000 without further rand draws, XORing each byte with the low byte of accepted state−1. Initial limit is1000000, marker2000000, polynomial2000008. Cipher and inverse are the same routine and reset to that seed independently for header and payload. Even zero-byte input resets/consumes RNG. There is no private RNG state in the public context: parent can route the two services into frozen CRTRandomRuntime with the same actual29-word thread token and seed+14 used elsewhere. This module does not recover their pregame invocation/seeding order.

Reentrant physical callbacks can mutate manager words. Tests confirm a count change during allocation affects the live header count while the sampled count/size/result are retained. A source key+44 change during WriteFile affects the later header-decrypt call; no captured old key is invented.

## CFile and explicit physical services

CFile open clears ownership/handle, empties its filename, calls path normalization4f777f(out260,inputName), then CString assignment4f66cc(file+c,resolvedPath). The path resolver is **stdcall RET8**, not cdecl. CreateFile uses the original input pathname, not the resolved CString; the latter supplies error diagnostics. SECURITY_ATTRIBUTES is `{12,0,((~(flags&ffff7fff))>>7)&1}`. Known mode/share/create branches and unusual default branches are compared; invalid share masks50/70 retain the original pathname token as the share argument rather than a guessed standard share mode. A supplied open-error object gets lastError at+c, mapped4fc384 result at+8, then CString filename assignment at+10.

WriteFile's output-count slot starts with the requested count. Zero-length write performs no platform call. Nonzero write invokes the actual WriteFile import; false reads current CFile filename **before** GetLastError and calls4fc242(error,name). A differing output count then elects4fc303(13,FFFFFFFF,currentName). An exception adapter sets fault to stop at the reached boundary. No return-count success or invented stop/cleanup is used.

Close invokes CloseHandle only for a nonFFFFFFFF handle. It then sets handleFFFFFFFF, ownership0, empties the filename, and only afterward elects GetLastError→4fc242(error,0) on a false CloseHandle result. CFile destructor resets VT510844, closes only if both handle valid and ownership nonzero, releases CString+0c, then writes VT50becc. CString4f650f uses length and **signed refcount**: length0 does nothing; nonnegative references call4f64ba; negative references call4f66cc with actual empty literal53ec90.

Services identify Windows imports by their real IAT slots:546b00 CreateFileA (7args),546b0c GetLastError (0),546a04 CloseHandle (1),546af8 WriteFile (5). Required CString/path/CRT exception helpers4f777f/4f66cc/4f64ba/4f6584/4fc384/4fc242/4fc303 remain named services; a callback can compose frozen CString destruction and RNG APIs. The MFC exception allocation/throw/unwinding graph is **not recovered**. Verified failure fixtures stop at its actual reached helper, preserving the encrypted header, live payload and file handle where present. Physical disk persistence, operating-system error meanings, recovery after exception, and source49b840 load boot remain separate acceptance boundaries.

Checkpoint success-message ordering remains owned by CheckpointLogicRuntime: it invokes49bbc0 but does **not gate its “saved” UI message on that return**. This module does not turn that message into evidence that a file reached disk.

## Verification

```sh
work/test-env/bin/python Tests/compare_save_file_runtime.py
work/save-file-agent/check-smoke.sh
```

Final differential evidence: **645 complete original calls /1,117 ordered full heap/global/file snapshots /784 distinct original-image instruction addresses**, including **183 frozen checkpoint-cache calls** across all15 level indices and45 slots in three retained profiles. Source-format header/payload bytes round-trip against unchanged original encryption with complete full-player records. Tests cover nullable/zero/odd data, all permutation bit ranges, actual CFile arities/flag branches, supplied error objects, empty/negative count gates, failure at both opens, allocation failure after truncation, count/list mismatch, six retained writer histories, source key/state/header aliases and reentrant source-count/key changes. Four additional prefixes cover short write, false WriteFile, false CloseHandle and invalid cipher input; they are not counted as complete successes. One actual manager-constructor instruction interval is compared separately.

Each call compares the full1MiB caller heap and192KiB original mutable globals, physical in-memory file bytes and ordered handle/free lifetimes. Scratch file16bytes are normalized from original stack identity; defined security/count values are checked at their platform call. Expired scratch locals and unspecified path padding are not treated as persistent source heap. The complete source RNG and CString destructor execute in the original oracle; only their physical TLS/Interlocked and declared path/assignment transports are adapted. Native RNG service uses the already frozen exact shared-seed update.

C++ is warning-clean; strict C11, Swift-import, ASAN and UBSAN smoke pass, including exact seven-byte input and one shared RNG draw per transform. No shared Swift/project/check scripts, physical files, devices, simulator or Xcode were modified by this worker. These bounded source comparisons do not establish whole-game parity or disk-save acceptance.
