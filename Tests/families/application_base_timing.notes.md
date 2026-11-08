# Application base record and timing boundary

This family owns exactly four whole functions,199 bytes. Use ordinary source context input7ff/output7ff/preserve0 for every root; no exemptions. The manifest pins each exclusive range and SHA256 from the hash-checked v1.0 executable. No native implementation or case body informed this boundary.

| Root | Exclusive end | ABI | Exact EAX result |
|---|---|---|---|
|4b8240|4b8275|thiscall0/u32|receiver|
|4b8280|4b82d4|thiscall2/u32|0 for invalid window;1 after source binding|
|4b83a0|4b83c6|thiscall1/u32|reset argument bit pattern|
|4b83d0|4b83e8|thiscall0/u32|0|

The decompiler's void result for4b83a0 loses a real EAX output. Its cdecl guess for4b83d0 ignores actual callers that transport the receiver inECX. That helper does not readECX, but its declared source interface here is thiscall0. Full source comparison retains actual outputs, including volatile state left by the physical call; preserve_mask0 makes no invented preservation promise.

## Actual source consumers and joins

Application factory423450 allocates0x134 bytes and invokes constructor4254a0. Its CALL4254bf→4b8240 returns4254c4. Whole application initializer425730 receives(windowQ,command) and its CALL425761→4b8280 returns425766. These larger functions stay outside this family's ownership and are not success fixtures.

All internal edges are owned source calls with genuine return words:

| CALL | Target | Return | Receiver / arguments |
|---|---|---|---|
|4b8265|4b83a0|4b826a|current base receiver; reset1|
|4b826c|4b83d0|4b8271|same receiver; no arguments|
|4b82b0|4b83a0|4b82b5|current base receiver; reset1|
|4b82b7|4b83d0|4b82bc|same receiver; no arguments|

Do not replace these helpers with fixtures or flatten the calls in a way that loses source stack/return/CPU effects. Existing original methods, constructor fields, pinned vtable and clock globals remain source-owned.

## Receiver and effects

A base receiver must have at least0x28 live writable bytes. Constructor4b8240 installs original vtable50bf04; sets+4,+8,+c,+1c to0 and+10,+14 to1; then invokes the two owned clock helpers. Receiver holes and physical scratch bytes must not be blanket-zeroed. The caller's larger0x134-byte application record is constructed by its actual source, not a snapshot or handwritten success object.

Window bind4b8280 takes two stack arguments. The first is nullableQ. NullQ returns0 without writes or clock calls; nonnullQ requires readable+4 and a zero HWND there also returns0. On success it storesQ atreceiver+4 andQ+8 atreceiver+8, clearsreceiver+1c, invokes both owned timing helpers, writes541338=100 and541334=100, then returns1. The second argument is unused but remains in the ABI/stack and is removed byRET8. Standalone helper cases may use declared structural inputs. A joined WinMain/application profile must use the actual source-createdQ, live physicalHWND andQ+8=outerowner; such a helper case is not proof of real application creation.

Reset helper4b83a0 first clearsreceiver+20, calls timeGetTime, stores that tick atreceiver+24, then loads its original reset argument intoEAX. Zero preservesreceiver+18; nonzero setsreceiver+18=ffffffff. It returns the complete reset argument, not a normalizedBOOL and not the tick. RET4 removes one argument.

Global reset4b83d0 calls timeGetTime and writes541328=tick,54132c=0,541330=0. EAX becomes0. ReceiverECX is transported but unused. Do not seed those globals to mimic an already-completed call.

## Physical clock contract and source stack

Only IAT546df0, WINMM timeGetTime, is outside: stdcall0/u32, scripted. Actual calls are4b83aa/RPC4b83b0 and4b83d0/RPC4b83d6. Supply a deterministic per-environment physical32-bit millisecond timeline, allowing equal ticks and genuine wraparound. Fixture state must not advance globally across original/native sides. The effect returns physical time; original instructions publish record/global outputs. No fixture writes to timing globals, source owner fields, game/menu decisions or helper results are authorized. An honest before-effect Halt may observe a prefix but cannot stand for full199-byte coverage.

For root entryESP S: constructor4b8240 exitsS+4; bind4b8280 exitsS+12; reset4b83a0 exitsS+8; global reset4b83d0 exitsS+4. Standalone reset's physical clock entryESP isS-8; standalone global reset's isS-4. Constructor/bind nested first clock seesS-14(hex), second clockS-c. Preserve genuine savedESI, argument and CALL return bytes as well asFS and all represented registers/flags. None of these four functions changesFS or owns an exception prologue.

## Coverage and scope

Ordinary whole-body profiles are constructor; bindnullQ,zeroHWND,validQ; resetflag0/nonzero; and both clock outputs with varied coherent timelines. These branches can statically reach every owned byte, without exception-only fragments or exemptions. Blind dynamic coverage and admission still must establish that. There are no allocator, guest-EH, source callback or x87 dependencies in these199 bytes.

This source boundary does not claim whole425730 startup completion, runtime/native election, window lifecycle, menu, Level1 or device success. The new unadmitted family is outside the selected frozen144 inputs. No existing exact owned root or declared body-range overlap was found during boundary review; preserve canonical ownership and existing admitted empty-string/static-record families.
