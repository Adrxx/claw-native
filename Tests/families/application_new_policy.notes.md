# Application-thread allocation policy boundary

Own two complete functions: accessor5022b5..5022cc (23 bytes) and
setter4f63d8..4f63ec (20 bytes). Source context is7ff input/output, preserve0.
No partial prefixes or coverage exemptions. Exact pinned hashes are in the manifest.

The accessor is cdecl0/u32. At entryF it calls realmodulegetter50228f at
CALL5022b5/RPC5022ba with childESP=F-4. It then passes actualsourcefactory502301
to realTLSgetter50335e at CALL5022c6/RPC5022cb, ECX=module+0x1070 and childESP=F-8.
That child consumes its one argument with RET4; accessor's own RET endsESP=F+4.
The getter may source-create the manager, generic thread, module singleton,
application-thread slot and record. None may be supplied by a cache fixture.

The setter is stdcall1/u32. It calls the owned accessor at
CALL4f63d8/RPC4f63dd, childESP=entryESP-4. Once the accessor returns, it loads
its original input word from entryESP+4, reads previoushandler at returnedthread+28,
stores the new word there, and returns the old word. RET4 endsESP=entryESP+8.
The actual constructor50210b initializes that field to4f63d0.

The setter input is an opaque32-bit data word within these owned bodies. It is
neither invoked nor dereferenced here. Zero, an original handler pointer and
other opaque values can test exact storage/old-value behavior without declaring
any callback fixture or permitting later execution of those values. Actual
operatornew4f63ec invocation, callback authority and retry remain separate work.

Keep all outside program functions as real source. Canonical admitted children
already cover module getter, TLS manager/values, actual502301 application-thread
factory and its constructor, generic thread/module factories and records, locks,
compiler scope, byte fill and the physical-throw chain. Do not duplicate these
owners or import a legacy allocation shortcut. No malloc/new fixture is part
of this43-byte closure.

Use one actual source image and physical owner across sequences. A cold getter
must obtain its records through real source calls. A warm getter returns the
same source-created application-thread record without duplicate construction.
Sequential setter calls must return the actual prior word, retain the getter's
record identity and leave unrelated fields unchanged. The previously executed
original construction probe demonstrates genuine cold setup and setter0; it is
not a replacement for fresh blind cases.

Physical TLS is keyed by the declared current logical thread and a live allocated
index. Different modeled threads must have distinct containers and application
records while retaining the actual process manager/module ownership selected by
source. Switching a declared physical logical-thread input between completed
calls must not rewrite source records or impersonate a native thread capability.
Cold/warm, repeated setter, return-old-word and thread-isolation cases should
exercise real publication and lookup. Model only supported logical-thread
profiles; this does not establish native scheduling or concurrent execution.

The15 physical imports are TLS allocation/get/set, LocalAlloc/LocalReAlloc,
GlobalAlloc/GlobalHandle/GlobalLock/GlobalUnlock/GlobalReAlloc, critical-section
initialize/enter/leave, GetVersion and RaiseException. Preserve exact flags,
separate movable handle/data identities, sizes, byte initialization, movement,
failure preservation, ownership, recursion and lifetime. LocalAlloc40 zeroes its
physical backing; flag0 and GlobalAlloc2002 do not promise zeros. Real source
byte fill initializes the slot arrays. GetVersion is an explicit process input;
the known original probe used NT4 DWORD4 and let source derive lock policy.

All allocation-failure and noncontinuable exception observations are genuine
prefixes through original4f50fd/4a5690 to physicalRaiseException546958,
RPC4a56cf. Do not return from that fixture, dispatch guest exceptions, fabricate
unwind or claim a completed setter after the halt. Real child compiler frames
and source FS state remain intact. The owned43 bytes have no localSEH frame.

Provide mapped source stack/FS and enough headroom for the authentic deep child
calls. Compare all represented CPU, flags, FS and bounded stack effects. Source
slots, managers, thread fields and game outputs must never be written by fixtures.
No captured records or synthetic success cache may replace actual initialization.

The broader application's allocation request is0x134(308) with declared rounded
capacity0x140(320); that allocator-domain connection is outside this family.
This draft establishes no admission, newcaller native election, operatornew retry,
WinMain/game initialization, menu/gameplay, guestEH or device acceptance.
