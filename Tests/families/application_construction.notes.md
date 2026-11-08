# Original application factory and constructor

Own the complete 90-byte factory `423450..4234aa` and 402-byte constructor
`4254a0..425632`. Both are thiscall0/u32 with source7ff/7ff/preserve0. Compare
all represented CPU, flags, FS and bounded source stack. Both return with
ESP=entryESP+4. No byte or branch exemptions.

The actual parent dispatches outer vtable50bbdc+38 at CALL4b8b58/RPC4b8b5b.
Incoming factory ECX is the outer owner, although this body does not dereference
it. Real new4f63ec receives134; successful allocation becomes constructor ECX
at CALL423485/RPC42348a. Parent publication and subsequent real init425730 are
outside this family.

Factory entryS installs a registration atS-c containing priorFS, handler504b4b
and state-1. Allocation local isS-10; new entersS-18 and constructor entersS-14.
State becomes0 before JE423481 to423499. Both normal arms restoreFS and remove
the frame. Constructor entryT installs registrationT-c, local receiverT-10,
saved EBX/ESI/EDI atT-14/T-18/T-1c. Steady P=T-1c; direct children enterP-4.
State atT-4 progresses0 after base,1 before embedded record,2 before CStringf8,
3 before CStringfc,4 before CString100. Preserve actual frame bytes and original
child return sites.

Constructor calls these admitted children as real source:

- Base4b8240 at4254bf/RPC4254c4, receiverA.
- Empty CString4f6439 at4254d0/RPC4254d5, receiverA+c0;
  4254f4/RPC4254f9, A+f8; 425504/RPC425509, A+fc;
  425514/RPC425519, A+100.
- Embedded record4f54ea at4254e4/RPC4254e9, receiverA+dc.

All are thiscall0/u32. Do not duplicate existing owners or inherit unrelated
allocation-fixture permissions from another family. The only physical constructor
effect is two clock reads through the base. Receiver backing is134 bytes; retain
original holes and shared empty-string pointer52e1c4 from slot52e1cc. Original
constructor installs vtable50bee4. No virtual callback executes inside these roots.

Game allocation remains source, including4f63ec,4a48e0,4a4900,4a4950 and small-heap
helpers. Same-owner setup runs real4ab120 and4a7b90 with physical heap, VM and
critical-section services. Original code writes545fc4, descriptors and lock records.
Physical models supply tracked backing and handles, reserve/commit semantics,
flags, failures and lifetime only. No source/global/receiver fixture writes.

To reach the factory's ordinary null arm, declare a nondefault unit policy and
invoke genuine original setter4f63d8(0), stdcall1/u32 returning the previous handler.
It runs real TLS/module/thread constructors and writes actual thread state itself.
Default constructor50210b installs4f63d0, which throws through4f50fd/4a5690 on
allocation failure. Do not change or claim that default policy. Never fixture a
handler return or directly enter the null arm.

Independent ignored readiness ran source heap/locks, whole factory success,
real setter0 (old handler4f63d0),191 additional real malloc(134) successes, then a
real malloc0 and second whole factory0. All allocations remained live; subsequent
physical commit10000 and fallback HeapAlloc140 requests failed. Existing small-heap
blocks served earlier allocations, so returning HeapAlloc0 alone is insufficient.

Exact script and receipt:

- `work/coordination/application_construction_readiness.py`
- `work/coordination/application-construction-readiness.json`

The probe observed114 instructions/492 bytes, restored FS after every entry, and
performed no native comparison. It uses source API entries, not actual parent,
static144 or WinMain execution. Fresh blind cases must independently reproduce
this authentic setup, full source contexts and meaningful clock/receiver/state
variation. The receipt establishes feasibility, not authored cases or admission.

Physical TLS stores and loads genuine per-thread values; real source constructs
all objects. LocalAlloc flag40 zeroes physical backing; LocalReAlloc preserves
contents and flags. GlobalAlloc2002 supplies movable storage through GlobalLock;
handles and locks must retain correct lifetime. Probe GetVersion4 declares NT4
for real MFC lock policy. Listed bootstrap-failure/reallocation imports remain
declared even when not used by this bounded profile. Allocation failures that
throw stop at the external EH frontier, not successful factory outcomes.

All inlined SEH instructions are ordinary owned bytes. External cleanup/handler
fragments504b40..504b55 and504db0..504dfa, FuncInfo519d30/51a038, throw4a5690 and
handler4a31c0 are separate compiler contexts. No cleanup direct entry, fabricated
unwind or guest-EH claim. Ordinary success and declared normal-null paths cover
all owned bytes; no owned range excludes a branch. Factory cleanup's delete and
constructor cleanup's member destructors remain external EH dependencies.

This draft establishes neither family admission nor native election, application
initialization, menu/gameplay or device acceptance. Exact hashes, fields and
physical contracts are retained in ignored
`work/coordination/application-construction-boundary.json`.
