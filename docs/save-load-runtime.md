# Original save-reader, startup and player-record ownership

`Sources/SaveLoadRuntime.h/.cpp` recovers nineteen complete bounded original functions from fingerprinted v1.0 `CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. It composes frozen SaveFileRuntime for CFile constructor/open/close/destructor and source checksum/XOR, frozen AmbientAudioBackendRuntime for CPtrList add/remove/clear, and frozen CheckpointLogicRuntime for49a720 cache reset. It does not duplicate those bodies or replace the save format.

Physical file/directory/path/CString/CRT locale/exception operations remain explicit services. Native tests compose the frozen CRTRandomRuntime on the same original29-word thread object as other consumers. The original oracle executes complete actual4a3040/4a3050/4a7dc0 and their OS/TLS ordering. Pregame startup/seed order, native disk persistence and exception unwinding remain separate acceptance boundaries.

## Stable C11 interface and original entries

`claw_save_load_entry(function,receiver,args,count,context,dependency,user,result)` returns native support/completion separately from meaningful original EAX. Void results normalize0. Every pointer is a32-bit token; the byte/word views come from embedded frozen `ClawSaveFileContext save`. Context adds directoryScratchToken (260 caller-owned bytes), a traversal bound and fault. All four frozen save scratch views are still required. These views represent original automatic stack locals, not extra source heap allocations.

Fault1 is a missing span/service,2 an invalid ABI/domain,4 a native traversal guard; dependency faults are preserved. The API resets the two context faults at entry. Unsupported function returns0 without fault. Do not treat a faulted call as a completed load or assume native bounded failures were normal original returns.

| Original entry | Actual arguments | Result/scope |
| --- | --- | --- |
|49b840 | filename; thiscall RET4 | Whole path/read/default-Player startup;1/0 |
|49b9a0 | none, thiscall | Whole reader; processed count/0 |
|49b950 | none, thiscall | Whole record-list cleanup then pathname clear; void |
|49b970 | none, thiscall | Whole record-list cleanup; void |
|49bdb0 | name,description,email,flags; thiscall RET16 | Create initialized player and insert; token/0 |
|49be50 | rawPayload; thiscall RET4 | Create imported player and insert; token/0 |
|49bee0 | name; thiscall RET4 | First matching player token/0 |
|49bf30 | record; thiscall RET4 | Remove matching node then actual virtual delete; void |
|49a5a0 | name,description,email,flags; thiscall RET16 | Initialize actual player record;1/0 |
|49a6d0 | rawPayload; thiscall RET4 | Import/validate actual player record;1/0 |
|49a8f0 | none, thiscall | Actual score validation/reset election;1/0 |
|49a990 | scoreRecord17; cdecl,receiver0 | Actual weighted-score comparison;1/0 |
|49ad50 /49adc0 | none, thiscall | Actual bit/key binding defaults; void |
|4d5330 | deleteFlag; thiscall RET4 | Whole deleting wrapper→423f00; receiver |
|423f00 | none, thiscall | Actual base-vtable50becc store; void |
|4f7570 | data,bytes; thiscall RET8 | Whole ReadFile wrapper; output-count |
|4f75f5 | signedDistance,origin; thiscall RET8 | Whole seek/error wrapper; new position |
|4f774d | none, thiscall | Whole three virtual-seek size query; byte size |

Raw scene/object services use the rich eight-argument call descriptor inherited from SaveFileRuntime. Source Windows imports identify their real IAT slots. Queue/list/player cleanup does not assume every associated virtual delete has the same identity; unknown identities remain explicit.

## Startup graph and source path behavior

The caller supplies the frozen verified **88-byte /22-word application+60 manager** initialized by SaveFileRuntime's exact inline constructor stores. The manager is a CPtrList (VT5107bc, block size10) with CString+1c, header+20..3f, current version/value+40 and shared cipher seed+44. Constructor+48..54 remain heap seed until permutation initialization. The actual application caller stores this object at4265aa and passes literal525618=`CLAW.USR` into49b840. This module recovers that whole called startup body, not the surrounding full application initializer.

49b840:

1. Empty the current manager pathname. Store directory-local byte0=0, then call GetCurrentDirectoryA(254,directoryBuffer).
2. A nonzero return formats manager CString+1c using actual literal525f78=`%s\\%s`, the directory and caller filename. The formatted result is a declared CString formatter service, not guessed path concatenation inside the recovered routine.
3. Store **directory byte3=0** before GetDriveTypeA(directoryBuffer). Drive type5 empties the formatted pathname. The source asks about the first three directory bytes, not its full path.
4. If the pathname is still empty, call GetWindowsDirectoryA(buffer,254), formatting the same literal if its return is nonzero. If still empty, return0 without reader/default work.
5. Zero exactly eight header words+20..3c; call whole49b9a0.
6. Only a **signed-positive** reader return triggers lookup of literal5255e8=`Player`. A found player returns1.
7. Otherwise call whole49bdb0 with `(Player,534938,534938,0)`, where both534938 pointers are the original empty ANSI literal. Return1 only for a nonzero created record.

No source call creates a replacement filename, writes the file after default creation, clears existing players before reading, or rolls back imported records. Native directory/file transports must declare their mapping of source Windows path identities onto the platform's storage. The source formatter uses backslashes; a native file backend can adapt physical path transport without pretending that adaptation is an original path routine.

## Whole reader and source validation quirks

49b9a0 constructs its stack CFile and opens manager+1c with flags0/errorObject0. The composed source open requests read access/open-existing. Failure destructs the CFile and returns0.

4f774d queries the current position through **current vtable+30**, then end position through a fresh vtable+30, then restores the old position through a fresh vtable+30. Actual CFile VT510844 maps that slot to4f75f5. Each seek transports SetFilePointer(handle,distance,0,origin), with origin1/current,2/end,0/begin. An FFFFFFFF result elects GetLastError→4fc242(error,0). The three calls and live field/virtual reads are preserved rather than replaced with an atomic host size query.

A measured size≤32 returns0 without header read/decryption. Otherwise read32 bytes into manager+20. **Any nonzero output count proceeds**, including a positive short read. The source decrypts all32 bytes, including prior contents of unread header bytes. It allocates measuredSize−32 bytes and reads that requested payload length. Again, any positive count proceeds, then decrypts/checksums the full allocated/measured length, including allocator seed in unread tail. The source does not insert equality checks, zeros or a guessed short-read rejection.

Success requires checksum equal to header+24 and payload length divisible by2644. The nominal payload-record count is unsigned measured payload length/2644. If header+2c is smaller, it replaces that count; an overstated/max header count is merely clipped. A declared zero count can reach the successful cleanup/version-update path while returning0 and importing nothing. The import loop uses a signed-positive count gate.

For each selected record, call whole49be50 with its payload address. A zero result returns0 after freeing the payload and destructing CFile. **Earlier records remain admitted**; no rollback occurs. A duplicate case-folded name makes49be50 fail before allocation. A later invalid name can allocate/initialize/delete its own attempted record while preserving the previously inserted player. Startup may then fail its default creation because that earlier `Player` already exists.

After successful processing, free payload; if header+28 differs from live manager+40, replace header+28 with manager+40; destruct CFile and return the processed count. **Version mismatch is not a rejection.** Failed checksum/length/import paths retain the decoded header fields without this successful correction. No magic-word/trailing-header-word check is added.

4f7570 initializes its output-count slot with the requested count, skips platform reads for size0, calls real ReadFile import for nonzero size and returns the count slot. A false transport elects GetLastError→4fc242(error,0). Actual exception helpers remain explicit and tests stop at their reached prefixes; source exception unwinding is not synthesized.

## Player records, validation and ownership

Actual records allocate **0x2648 bytes /2450 words**, VT50feac. Both create wrappers set that vtable and zero all2449 payload words before invoking their corresponding initializer. The payload is0x2644 bytes and starts after the vtable. Record deleting slot+4 maps to4d5330: call423f00 (only VT50becc store), test low delete-flag bit0, optionally CRT-free, return receiver. Other record fields are preserved by the destructor.

49a5a0 requires a nonnull name with byte length<32; **empty name is accepted** by this initializer. Optional description/email checks repeat the name's length rather than checking those respective inputs. The original may therefore copy longer secondary strings over following fields; the native routine preserves valid in-allocation writes and bounds unsafe spans rather than adding an invented80-byte validation.

It zeros payload again, applies the exact original binding defaults, copies NUL-terminated name to record+14, description to+36, email to+88. Copies use original forward DWORD chunks followed by remaining bytes, including the terminator and original alias behavior. Flags argument bit4 sets record+4 bit4; other incoming flag bits are not copied. Record+8 becomes1. Source bindings are:

-49adc0 writes17 words at+25c0: `[0,25,27,26,28,20,11,12,10,0,5a,31,32,33,34,0,0]` (hex values).
-49ad50 writes17 words at+2604: `[0,0,0,0,0,1,2,4,8,0,10,20,40,80,0,0,0]` (hex).

49a6d0 requires nonnull raw payload with **name at payload+10 length1..31**, copies2449 words forward to record+4, calls49a8f0, **ignores its return**, then returns1. It does not reject copied records merely because validation returned0.

49a8f0 returns0 immediately without reset if record+8 is not1. Otherwise, for each15 level indices, it validates the17-word best score at+21c4+i*44 and two17-word subrecords at+1780+i*b0 and+17c4+i*b0. Those latter subrecords belong to the third checkpoint-kind region; the source does not validate every first/second-kind packet here. A failing score calls frozen whole49a720 cache reset and returns0. All passed returns1. The importer still admits a record whose caches were reset.

49a990 compares score word+4 against wrapping32-bit sum of ten DWORDs starting+1c times actual immutable source weights52d698: `[100,500,1500,2500,5000,7500,10000,15000,25000,0]`. Null score pointer returns0. No floating-point score or invented final weight is used.

49bee0 traverses manager head+4, caches node-next before comparison and calls actual CRT4a3cf0(record+14,inputName). Its normal original locale branch is case-insensitive for ASCII. CRT locale conversion remains an explicit service; the oracle executes the actual original comparator. No Unicode/locale equivalence is claimed from native fixture adapters. Whole49bdb0/49be50 reject an existing matching name before allocation. Successful initialization inserts through frozen original CPtrList4f51c5. Its pooled nodes are12bytes; with block size10 the first block allocation is124 bytes.

49bf30 finds the exact record token, invokes frozen RemoveAt4f5212, then fetches and invokes the record's actual deleting slot+4(1). Null record parameters do not read even an invalid manager. 49b970 caches each node-next before invoking its nonnull record's deleting slot+4, then calls frozen RemoveAll4f5172. That clears list count/free/head/tail, frees actual pooled block chains and clears block ownership. 49b950 composes that whole cleanup, then source CString empty helper on pathname+1c. No whole save-manager destructor is invented here.

## Source services and native integration recipe

Supply:

- Actual88-byte manager and full0x2648 records; shared empty-CString data identity with original header semantics.
- Frozen SaveFile's four scratch views, plus this startup's260-byte directory view. Scratch bytes are not source heap ownership or persisted save data.
- Immutable original CFile VT510844+30=4f75f5 and record VT50feac+4=4d5330 in token lookup. Fresh virtual identities are observed; other identities need explicit adapters.
- Scene allocation/free that preserve exact sizes and distinct live identities, including payload, records and CPtrList blocks. Null record allocation reaches an unchecked null receiver; it is a stopped safety prefix, not a normal no-op failure.
- Rich directory/path/CString/file/exception/comparator transport, with callbacks allowed to set context fault. Source imports added here:546a28 GetCurrentDirectoryA(254,out),546a10 GetWindowsDirectoryA(out,254),546a2c GetDriveTypeA(directory),546afc ReadFile(handle,data,count,outCount,0),546af4 SetFilePointer(handle,distance,0,origin).
- Shared CRTRandomRuntime globals/TLS index and actual29-word thread token. Route4a3040/4a3050 source services to that frozen API with original OS/TLS transport; do not create a private save RNG seed. Cipher contexts merely borrow that same thread's seed+14. Their header/payload transformations still use frozen SaveFileRuntime.

CString formatting4f4f58 is cdecl(field,format,directory,filename); path resolver4f777f is stdcall(out,name). Assignment4f66cc, clearing4f64ba, destructor4f6584, locale comparator4a3cf0 and MFC exception services remain explicit. Parent may compose its verified CString destructor and platform-specific storage adapters. Actual read/write/file-close exceptions must propagate a fault into the enclosing context rather than pretend that a file save/load completed. Disk IO and recovery from exceptions require independent acceptance.

## Evidence

Run:

```sh
work/test-env/bin/python Tests/compare_save_load_runtime.py
work/save-load-agent/check-smoke.sh
```

Final differential suite: **866 complete original calls /1,485 ordered complete snapshots /1,666 distinct source-image instruction addresses**. It compares full1MiB caller heap,192KiB original mutable globals, in-memory physical-file bytes, handle positions, allocation sizes/lifetimes, CPtrList blocks and the actual shared CRT thread/RNG service ordering. Nineteen newly recovered roots and their reached frozen bodies execute against unchanged original instructions.

Three retained source-writer→clear→reader histories cover all45 populated checkpoint slots, all15 best-score entries, byte-identical loaded payloads and version correction. Tests cover first/optional string lengths and original validation quirk, case-folded duplicates, directory/CD-ROM/Windows fallback, missing/empty/corrupt/nonmultiple files, positive short reads, failed opens, payload allocation failure, declared-count0/overstatement/max, retained full cleanup and partial-load/no-rollback/default failure. Four additional stopped prefixes cover ReadFile throw, seek throw, imported-record allocation0 and default-record allocation0. They are not included as normal successful calls. Native null-guard/no-read, argument and traversal checks are also exercised.

Defined directory input is compared at drive-type polling, and security/count slots at their physical calls. Scratch CFile16bytes are compared through their live source lifetime; expired stack locals and uninitialized path/directory padding are not treated as persistent source heap. Actual original RNG/TLS getter and CString destructor execute; physical file/directory/path/assignment transports remain explicit. Native RNG services compose frozen CRTRandomRuntime rather than duplicate its implementation.

Strict C11, Swift import, warning-clean C++, ASAN and UBSAN smoke pass, including a full2450-word record, actual binding arrays, score-failure reset, deleting lifetime and invalid-receiver null guards. No shared Swift/project/build scripts, native devices, Xcode or physical save files were modified. This bounded evidence does not establish entire application startup, whole-game equivalence, native disk-save acceptance or exception recovery.
