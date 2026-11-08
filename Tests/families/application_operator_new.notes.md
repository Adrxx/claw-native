# Whole original operator new

Own exactly4f63ec..4f6428:60 bytes,27 instructions, cdecl1/u32,
source7ff input/output and preserve0. RET leaves the one argument for its caller.
Every owned byte must execute in ordinary full-source or genuine physical-halt
profiles; there are no exemptions. Legacycarray lists this entry with unknownABI
and provisional evidence. The new family is a separate exact canonical capability;
do not modify/read/reuse that legacy implementation. Admission and native election
remain distinct.

At entryN, the requested size is[N+4]. Source saves EBX,ESI,EDI, loads sentinel
[510020] into ESI, and calls realmalloc4a48e0 at4f63fa/RPC4f63ff. ChildESP=N-0x14;
its sole argument is the original requested size. CallerPOP at4f6401 consumes it.
Nonzero malloc returns directly through the source epilogue. On zero, if cached
ESI equals current sentinel, CALL4f640e/RPC4f6413 invokes actualaccessor5022b5
(childESP=N-0x10) and reads handler from actualapplicationthread+28. A null handler
returns zero. Otherwise CALL4f641b/RPC4f641d invokes that exact sourcehandler,
cdecl1/u32 atN-0x14. POP4f641f consumes the argument and JNE4f6420 retries when
handlerEAX is nonzero. All CPU/flags, source-stack and inheritedFS effects matter.

Pinned initial sentinel510020 isffffffff and CRTnewmode540fe8 is0. Source setters
and constructors establish per-thread policy. Never fixture these words, TLS
records, allocator descriptors or application outputs. Setter inputs that are
opaque data in application_new_policy are not automatically executable here.

All program callees stay original: malloc and every CRT heap helper; admitted
application-thread accessor; default4f63d0 and reserve4fe0e5 handlers;
genericgetter501fad; msize4a6560, free4a49b0 and_expand4a64b0. **Do not use env.stub
or a fixture for fixed original handlers or any allocator/helper**, even if
 generic lint/packet advice says to provide a stub for an indirect call. The real
source callback must execute with its actualcdecl frame and returnPC. Outside
helpers need not be added to this family's ownership merely to execute them.

Authentic setup and policies:

- Run realheapbootstrap4ab120 andlockbootstrap4a7b90 on one owner. PhysicalHeapCreate,
  VirtualAlloc and critical sections supply real handles/backing; source creates
  its own descriptors and lock publications.
- Ordinary success uses realmalloc and a live tracked allocation. For genuine
  normal-null behavior, source-execute4f63d8(0), exhaust real small-heap storage,
  then fail real physical expansion/fallback requests. HeapAlloc0 alone does not
  defeat existing free small blocks.
- Default actualthread constructor installs4f63d0. Its failure path reaches
  original4f50fd/4a5690 and physicalRaiseException. A null reserve under4fe0e5 also
  throws; neither may be forced to return or treated as completed allocation.
- The returning-handler profile below source-establishes a real reserve and
  reaches all post-callback instructions and the retry. No field injection or
  external-handler substitution is necessary.

Genuine reserve/retry recipe:

1. Run original4251f0→50257f, constructing image-backed CWinApp537008. Real source
   publishes it to actualmodule/applicationthread and sets app+b8=0x200(512).
2. Run whole4fb412 to increment actualapplicationthread+0x10. Run whole4fb41b(0)
   to decrement tozero. Argument0 legitimately skips temporary-map cleanup but
   retains reserve maintenance. ActualTLSgetter obtains the genericthread;
   CALL4fb4dc/RPC4fb4e1 allocates512 through realmalloc, and source4fb4e4 publishes
   the pool at genericthread+c. Never write that field from a fixture.
3. Use genuine setter4f63d8(4fe0e5). Retain live source allocations until the
   initial smallheap is actually exhausted. Block further physicalVM commits.
4. A declared general-heap live-byte quota0x210(528) holds the512-byte reserve and
   leaves16. Application request0x134(308), rounded bysource to0x140(320), cannot
   fit; realmalloc returnszero after its genuine physical attempts.
5. Original4fe0e5 calls501fad, queries actualpool capacity via realmsize, and
   calls source_expand4a64b0 with0xc8(200). OriginalCRT rounds to0xd0(208) and
   calls physicalHeapReAlloc(heap,0x10,pool,208). In-place shrink preservespointer
   andprefix while releasing304 quota. The sourcehandler returns1; originalnew
   retries, and its realmalloc can now obtain320 bytes from the same physicalheap.

The quota must be a real physical allocation policy based on the live ledger,
not a conditional keyed to sourceEIP or a desired result. Separate Local/Global
and VM ownership remains coherent. HeapSize returns actual capacity. HeapReAlloc
flags0x10 require in-place behavior; a moving realloc stand-in is not equivalent.
The source pool pointer remains unchanged on this shrink. Physical state and
source state must both survive between setup, exhaustion, handler and retry.

Independent original-only producer:
`work/coordination/application_safety_pool_retry_probe.py`.
Receipt: `work/coordination/application-safety-pool-retry-probe.json`, SHA-256
`658202e8f703115ab088b2058ad8013c3c19193962f57cc903db44575c5b99d4`.
It observed all27 instructions/all60 owned bytes and genuine successful retry.
Fresh blind cases must independently reproduce this behavior and meaningful
source-context/input variation; this receipt is feasibility evidence, not cases
or admission. The producer's optional wholeapplicationconstructor calls need the
declared clock; operatornew itself does not construct an application object.

The27 declared physical imports cover heap/VM and bootstrapcleanup, MFC
TLS/Local/Global memory, locks, GetVersion, GetCursorPos, currentthread handle/ID,
clock and noncontinuable RaiseException. Preserve exact argument ordering,
flags, ownership, distinct Global handle/data identities, zeroing rules, failure
preservation and logical-thread identity. PhysicalGetCursorPos writes only the
source-provided POINT. Real source owns every other constructor/cache write.
The16MiB oracleheap supports the actual4MiB VM reserve and other physicaldomains;
it does not license fabricated allocator state.

No sourcehelper/handler coverage exemption or guestEH transport is introduced.
Noncontinuable RaiseException must Halt at genuineRPC4a56cf without return,
dispatch or unwind. External compiler cleanup fragments remain external domains.
All60 owned bytes are reachable without such machinery using the genuine reserve.

The future native CRT memory-service join is a separately declared domain and
comparison. Do not replace malloc in this source family, rewrite the admitted
492B construction reference, or imply native election, WinMain/game initialization,
menu/gameplay or device acceptance from this draft.

Corpus metadata repair (original-only): the hash-checked Ghidra two-address seed
added genuine entries `004f63d0` and `004fe0e5`, with no pointer-seeded additions.
Ghidra independently bounded the complete default-handler fragment at
`[0x4f63d0,0x4f63d8)` (8 bytes, 3 instructions) and the reserve handler at
`[0x4fe0e5,0x4fe137)` (82 bytes, 35 instructions). Both decompiled successfully;
the corpus leaves their convention as `unknown`. The manifest's cdecl1/u32
contract comes from the actual operator-new callback frame and original bodies,
not a decompiler ABI guess. The default handler's trailing XOR/RET bytes exist,
but its real throw path is still nonreturning in the declared profile.

The repair changed none of the 6,680 existing function records or 20,040 existing
C/meta/assembly files. Only these two entries and their six files were added.
The receipt is `work/coordination/operator-handler-corpus-repair/receipt.json`;
its sibling `index.before.json`, `before.json`, `seeds.txt` and `phaseA.json`
preserve the exact prior index, file hashes and narrow seed evidence. This repair
supplies genuine source dependency metadata; it neither owns those handlers in
this family nor changes any source execution, callback or exception policy.
