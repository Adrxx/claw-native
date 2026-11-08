# Original player death services

`PlayerDeathServices.h/.cpp` recovers original `0x41ebd0` death notification
and `0x4b7aa0`, plus the finite name-copy and notification packet helpers.
The previously assumed audio stop/reset behavior is corrected by the
original instructions: **`0x4b7aa0` is exactly `ret 4`** (`c2 04 00`). It does
not read the receiver, inspect a pool, stop a voice, change resources or
clear audio state. Its incidental EAX is not a gameplay result.

The original executable remains SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The cloned private Ghidra project, decompiles, phrase capture, tests and
coverage are in `work/player-death-services-agent`. No frozen/shared source,
project, bridge, device or simulator was changed or driven.

## API and finite scope

`claw_player_death_service_entry(function,receiver,args,count,context,
dependency,user,result)` uses the existing raw `ClawSceneActorHost` graph.
Context globals are original manager token `0x5371fc` and the shared empty
CString data identity (normally original `0x52e1c4`). Return one means the
entry is covered/completed, zero means unsupported or a bounded host fault.
Meaningful original return values are separate. Clear fault before a call;
fault 1 is missing graph/service and fault 2 is argument/text domain rejection.

| Entry | Original ABI | Native scope |
| --- | --- | --- |
| `41ebd0` | cdecl, no arguments | Complete notification branch/control/text selection |
| `4b7aa0` | receiver ignored, one stack argument | Complete literal RET4; no effects |
| `41ee40` | thiscall name object, `(destinationCString)` | Complete name wrapper |
| `4f6449` | thiscall destination CString, `(sourceCString)` | Complete shared-copy branch; locked assignment is explicit service |
| `479f10` | thiscall owner, `(text,kind,prependName,display)` | Complete finite text/packet/send control |
| `47a220` | thiscall owner, no arguments | Complete client binding/buffer allocation gate |

The rich dependency preserves actual entry identities and argument order,
with two synchronous buffer views for adapted original stack pointers.
Native stack arguments use token zero; raw heap arguments retain their
actual token. `4a3920` receives output buffer 0 (256 bytes), source phrase
or input buffer 1, original format token in argument 1 and raw CString data
token in argument 2. Argument 3 remains the raw input token for a public
sender; a native stack phrase uses zero. `422370` receives its complete
display string in buffer 0 and argument 0 is zero. These buffers must not be
retained after the callback. Buffer callbacks require the rich dependency;
ordinary raw calls can fall back to `scene.call`.

`context.temporaryStringToken` is a caller-owned four-byte scratch object
representing the local CString's stack identity, required only when a
name-copy branch is reached. This is an explicit host temporary, not an
original heap allocation. In public `479f10` the source later reuses that
dead CString slot as its packet text pointer, and that alias store is
preserved when scratch storage is supplied. The nested sender in `41ebd0`
has its own local slot and does not overwrite the outer notification scratch.
The parent can omit scratch entirely for normal mode-3 death calls.

## Normal single-player death

`41ebd0` reads global manager `+2c`, invokes that state object's actual
virtual `+10`, and performs further notification work only if the result is
4. Original single-player owner vtable `50c264` has `+10 = 40af90`; that exact
getter is `mov eax,3; ret`, already recovered in frozen `GameFrameServices`.
The death notice therefore has no RNG, name, UI, network or audio operations
for the real mode-3 single-player profile. It still calls the actual getter
and preserves any declared callback effects. It does not replace the getter
with an assumed hardcoded mode inside this module.

Frozen fall and spike death constructors invoke the recovered services in
their original order. The death service does not clear voices. The separate
frozen `PlayerPowerupRuntime` reset still owns its conditional music/resource
transition; its behavior is not conflated with the RET4 helper.

## Mode-4 notification body

After the mode query returns 4, `41ebd0` invokes `4a3050`, computes signed
remainder by 26, and selects one of the original 26 byte-exact phrases.
Negative remainder uses the default last phrase. The ordinary original RNG
returns nonnegative 15-bit values; negative directed service outputs are
tested separately to cover the actual selector's default branch.

The phrase is copied to the original bounded 256-byte local counterpart.
The body then reloads global manager and state `+2c`. If that state's name
object `+784` is null, it returns after selection without formatting/sending.
Otherwise it obtains the name through whole `41ee40`, invokes the explicit
original `sprintf`-style formatter `4a3920` with format `524acc` (`%s %s`),
releases the local CString through frozen `ActorDestruction(4f6584)`, and
executes whole `479f10(state,message,1,0,1)`.

`41ee40` copies the CString at name object `+8` into the destination object
and returns that destination token. `4f6449` shares a source with nonnegative
reference count: it stores its data token and increments its header at
data `-12` with UInt32 wrapping. A locked/negative source initializes the
destination with the shared empty token and invokes explicit assignment
`4f66cc(destination,sourceData)`. That assignment/allocation implementation
is not re-created here. Destruction composes the frozen exact release body,
including header decrement, empty-identity handling and `scene.free` when
required. Original Interlocked increment/decrement services are adapted as
serial native word operations in these single-threaded comparisons; no
cross-thread atomic-equivalence claim is made.

The phrase capture JSON is extracted directly from the pinned original
literal addresses, not from a reference game port or CrazyHook table.

## Sender, gate and packet ordering

`479f10` returns zero immediately for a null or empty input. It scans the
original input before truncation and writes NUL at byte 128 if longer. It
then removes at most two trailing bytes whose **signed 8-bit value** is
less than space. The high-byte quirk is retained; this is not Unicode
normalization. Those input writes precede the client gate and still occur
when that gate fails.

Whole `47a220` invokes `4e0c60(owner+780,owner+788)` and stores its returned
client at owner `+784`. If the client is nonnull and its `+18` buffer is
zero, it allocates 1024 bytes, reloads owner `+784`, writes that client's
`+18` allocation result and `+1c = 1024`. **A null allocation does not make
the gate return false:** the result is simply whether owner `+784` remains
nonnull. Allocation and player lookup are exact external services.

On a successful gate the sender either copies the already-trimmed input,
or obtains a name and calls formatter `4a3920` with original `52ac0c`
(`%s: %s`) before releasing its local CString. That second formatted result
is not cropped to 128 again. If display is nonzero, it invokes
`422370(owner+4 manager+4c,message,0)` before constructing the network packet.
Callbacks can rebind the live graph; all source reloads are preserved.

It obtains packet pointer owner `+bc8`, writes packet `+4 = kind` then
packet `+0 = 0x3f0`, copies message including NUL to the freshly reread
owner `+bc8 +8`, and invokes
`4e0d70(owner+780,owner+784,kind,savedPacket,messageLength+9)`. The length
includes the eight-byte header and final NUL. It returns one after that
call even when the external send result is zero. UI, format and network
implementations remain explicit; no actual message is transmitted by this
headless recovery task.

## Bounds and integration limits

The raw sender's initial string scan is bounded to 4096 bytes, and original
local message buffers are represented as 256 bytes. Unterminated/oversized
inputs or formatter results without a NUL in that capacity fault as native
safety extensions. Original stack overflow/invalid-pointer behavior is not
claimed as a successful portable result. Formatter implementations must
honor the exposed buffer capacity in the admitted domain.

Mode-4 graph fields extend through owner `+bc8`; the name object needs its
CString at `+8`, client buffer fields at `+18/+1c`, and packet capacity for
the header plus message/NUL. Normal mode-3 does not read those derived
fields, so it works with the real smaller single-player owner. The module
does not invent networking, UI, CRT formatting, locked string assignment,
pool reset or platform sound behavior. Existing audio modules need no
special stop operation for `4b7aa0`.

## Evidence

```sh
work/test-env/bin/python Tests/compare_player_death_services.py
zsh work/player-death-services-agent/check-smoke.sh
```

Final suite: **2,517 whole original calls, 6,231 ordered complete snapshot
events and 549 executed original instruction addresses**, excluding adapted
platform/service entry points. Each whole call compares complete 256KiB
heap and 112KiB global images directly; every external boundary hashes their
complete contents. The adapted local CString word is checked separately
against the actual original stack cell, including the sender's later alias
store. Seeded active voice/pool bytes are checked unchanged throughout.

Coverage includes all 26 phrases, mode/manager rebinding, absent clients,
shared/locked names, reference-count wrapping, allocator null/present
results, CString frees, input truncation, signed trailing-control cases,
display/prepend flags, UI-driven client replacement, packet ordering and
retained notice/RET4 histories. The actual mode-3 and mode-4 probes execute
in the original and compose frozen GameFrameServices natively.

There are **192 true original fall/spike death constructor chains** with
notification enabled/disabled and actual mode probes, composed with frozen
PlayerDamage and PlayerPowerupRuntime. Animation/resource selection is an
explicit adapter; the death services, shared CString lifecycle, finite
packet controller and powerup reset bodies execute directly. Existing frozen
oracle ABI types are read without running or changing its work directory.

Strict C11 and warning-clean C++ compilation, plus Swift-imported context
and literal-RET4 smoke pass. This is original control/metadata evidence and
native ABI validation; root owns actual app integration and acceptance.
