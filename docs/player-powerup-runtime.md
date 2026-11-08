# Original player powerup setter and reset

`PlayerPowerupRuntime.h/.cpp` recovers the pinned original v1.0 setter,
reset and finite image/effect helpers. No frozen player, initialization,
damage, input, pickup, image, scene, bridge or project files were changed.

The original executable SHA-256 is
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
The private Ghidra project and output are in `work/player-powerup-agent`.
Assembly and whole original-instruction execution determine the behavior;
the decompile is a navigation aid, not the parity oracle.

## Stable C11 API

`claw_player_powerup_entry(function, receiver, arguments, argumentCount,
context, dependency, user, result)` returns one for a supported completed
entry and zero for an unsupported entry or bounded host fault. Meaningful
original results are separate. Void incidental EAX is not claimed.
The raw context is named **ClawPlayerPowerupRuntimeContext**, distinct from
the frozen timer's existing three-word `ClawPlayerPowerupContext`.

| Entry | Original ABI | Result / implementation |
| --- | --- | --- |
| `0x41f990` | cdecl `(actor,primary,private,type,duration)` | Whole setter, result 1 on ordinary completion |
| `0x41fc00` | cdecl `(type,duration)` | Whole global-player wrapper, 0 when player is absent |
| `0x41fc30` | cdecl `(actor,primary,private,delta)` | Composes frozen `claw_player_update_powerup_timer` |
| `0x4ce7b0` | thiscall image manager, `(effect)` | Whole image-range traversal, count of affected compressed images |
| `0x448400` | cdecl `(ownerActor)` | Whole GlitterMother creation wrapper, created actor or 0 |
| `0x420070` | cdecl `(actor,delta)` | Whole timed image-effect/color cycle |
| `0x4bc110` | no stack arguments; usual receiver is manager | The complete pinned body is a single `ret` |

`context.scene` supplies exact sized raw token spans through the existing
`ClawSceneActorHost`. Resource/backend callbacks use the rich dependency
containing function, receiver, up to six arguments and optional literal
text. If no rich dependency is supplied, calls with at most four arguments
can use `scene.call`; the six-argument scene creator requires the rich
dependency. Fault 1 means missing graph/service; fault 2 means malformed
argument count or bounded traversal. Clear a previous fault before a call.
Original pointer identities remain 32-bit tokens, never truncated host
addresses. Lookup must be a pure resolution operation; callbacks may mutate
the live graph and globals.

The caller owns the eight represented globals:

| Context word | Original address |
| --- | --- |
| managerToken | `0x5371fc` |
| playerToken | `0x537e88` |
| powerup | `0x534eac` |
| remaining | `0x534ea8` |
| expired | `0x534eb8` |
| musicDisabled | `0x53c9c0` |
| cycleRemaining | `0x534ec8` |
| cycleIndex | `0x534ecc` |

No unverified startup defaults are supplied. In the native player adapter,
commit actor/private and these globals before calling the raw entry, then
reload them after the call. The timer bridge internally synchronizes full
actor128/private78 snapshots at each dependency boundary while composing
the frozen timer. Primary logic remains raw caller-owned storage; the
setter's second parameter is unused by the original body.

## Setter behavior and ordering

Music handling occurs first if original manager `+0x14` is nonzero and
global `0x53c9c0` is zero. The music manager is manager `+0x50`, with current
resource at music manager `+0x1c`. All later original global-manager reloads
are preserved; an external resource callback may replace that manager.

For nonzero type **and** nonzero duration, a changed type looks up `LEVEL`
(`0x524d80`), queries `0x4b5bd0` and conditionally invokes resource virtual
`+0x28`. It then looks up `POWERUP` (`0x524d78`), stores that resource as
current if present and invokes `0x4b5570(1)`.

When type or duration is zero, the setter saves the current resource before
lookup. If it matches the nonnull POWERUP lookup and that query is nonzero,
resource virtual `+0x30` runs. The LEVEL lookup can replace the current
resource; if its query is zero, resource virtual `+0x2c(0)` runs. Missing
resources skip only their specific operations; selection/reset continues.

After music callbacks, equal current/requested types extend remaining time
with **wrapping UInt32 addition**, then cap the wrapped result at 999000.
This is not a saturating-before-overflow addition. Changed types store the
supplied duration without that cap. In particular, reset `(0,0)` when the
current type is already zero preserves its remaining time, subject to the
same-type cap. It does not unconditionally clear every timer/global.

On a changed type, positive signed type invokes `0x4bc110`; its actual body
has no heap/global effects. The old powerup is then cleaned up:

| Old type | Exact cleanup |
| --- | --- |
| `0x26b7` | If actor `+0x170` image manager exists, traverse `0x4ce7b0(manager,1)` |
| `0x26bc` | Nonnull private `+0x130` actor receives flags `+8 |= 0x10000`; private pointer becomes 0 |
| `0x26bd` | Actor `+0xd4 |= 0x01000044`, then the same image-manager traversal as `0x26b7` |
| Other | No cleanup stores |

The new type and duration are stored after cleanup callbacks. New effects:

| New type | Exact effect |
| --- | --- |
| `0x26b7`, `0x26bd` | Queue `CLAW_1110064` (`0x524d68`) with force 0 |
| `0x26b8` | Queue `CLAW_1110001` (`0x524d58`) with force 0 |
| `0x26b9` | Queue `CLAW_1110022` (`0x524d48`) with force 0 |
| `0x26ba` | Queue `CLAW_1110012` (`0x524d38`) with force 0 |
| `0x26bc` | Run whole `0x448400(actor)` and store its result at private `+0x130` |
| Other | No new effect calls |

The setter does not directly modify jump velocity, walking velocity,
weapon counters or general physics. The frozen locomotion bodies consume
powerup `0x26bc` for later faster movement and jump behavior. This module
does not invent immediate physics changes or new invulnerability gates.
Speech queue calls are not claims of immediate sound playback.

## Finite image and effect helpers

`0x4ce7b0` traverses the signed inclusive image index range manager
`+0x64..+0x68`, reading its array pointer at `+0x14`. It rereads the range
after callbacks. Each nonnull image with compressed object at image `+0x30`
receives `0x4c6130(compressed,effect,0)` and increments the returned count.
Negative indices are preserved when the supplied graph owns the corresponding
wrapped token span. Traversal exceeding one million iterations faults as a
host safety extension, not an original successful return.

`0x448400` returns zero for a null owner. Otherwise it calls the original
named creator on owner `+0xc` parent `+8` actor container with arguments
`(1,100,100,0,"GlitterMother",0)`; the original name token is `0x5225a0`.
A missing actor result returns zero. A successful result writes the owner
actor token to created actor `+0x6c` primary logic `+0x170`. The creator,
callback, allocation and actual GlitterMother gameplay remain services.
Cleanup marks that actor for scene deletion; it does not free it immediately.

`0x420070` does nothing for a null actor. Otherwise it subtracts delta from
cycleRemaining with unsigned saturation at zero. Expiration resets that
counter to 100 and advances cycleIndex `0x34→0x35→0x36→0x37→0x65→0x34`;
any unrecognized value becomes `0x65`. For the current image's nonnull
compressed object, it invokes `0x4c6130(object,4,0)`, rereads image `+0x30`
after that callback and, if still nonnull, stores cycleIndex at object
`+0x18`. No palette/raster algorithm is duplicated here.

The original countdown is composed from frozen `PlayerInputDispatch`.
Its expiration signal is preserved, setter/reset executes as a complete
body, its confirmed `0x4bc110` tail is native, and active `0x26bd` calls the
whole cycle helper before its existing actor flag mask. Image effects route
through the dependency into frozen `GameImageRuntime(0x4c6130)` when desired.

## Exact service boundaries

Music lookup `0x4b54a0`, query `0x4b5bd0`, manager operation `0x4b5570` and
actual resource virtual `+0x28/+0x2c/+0x30` remain dependencies. Their original
order, receiver, arguments, conditional selection and current-resource stores
are recovered; a physical Windows music backend is not implemented here.
The query itself calls resource virtual `+0x20` then an imported platform
query in the original; this module does not fabricate that physical status.
Likewise `0x48c8a0` can compose the existing AudioEvents speech implementation,
`0x4c8da0` can compose the existing scene creator, and `0x4c6130` can compose
the frozen GameImageRuntime through the adapter. Missing implementations
must remain explicit. `0x41ebd0` death notification and `0x4b7aa0` audio
reset were not broadened into this task.

## Original comparisons

Run the owned oracle and imported-ABI smoke:

```sh
work/test-env/bin/python Tests/compare_player_powerup_runtime.py
zsh work/player-powerup-agent/check-smoke.sh
```

Final evidence: **4,297 complete original calls, 5,317 ordered full snapshot
events and 748 executed original instruction addresses**, excluding adapted
service entry points and synthetic backend functions. The oracle compares
the complete 256KiB heap directly after each whole call and hashes complete
heap/global byte images at every callback boundary. The complete 112KiB
global image is also compared directly after each call, including physics,
input, initialization and unrelated preserved globals in joined graphs.
Native actor128, primary93, private78, image managers, compressed objects,
music resources and created effect actors are all represented in that heap.

The directed matrix covers normal and reset selection, same-type extension,
unsigned overflow/cap edges, signed type extremes, zero duration, missing
music lookups, query states, creator failure/success, old effect cleanup,
image holes/negative ranges and callback mutations of managers/globals/ranges.
Retained raw setter/countdown histories exercise rebinding and expiration.
Frozen timer and compressed image-effect bodies execute natively; their
original bodies execute in the oracle rather than being replaced by matching
invented algorithms.

There are **402 genuine joined caller calls**: all 62 original loot metadata
profiles through frozen/original CaptainClawHit, directed state23 respawn
through setter `(0,0)`, and 24 retained Catnip22/23 award→countdown→respawn
histories. Loot22/23 really use mask `0x10000`, values 15000/30000 and route
the hit callback to powerup `0x26bc`. Resource/ground/mode/pickup sound services
use identical declared adapters on both sides. The Special/Curse/EndOfLevel
`0x41ee60` descendants in other metadata rows remain explicit services;
those rows prove hit-engine dispatch identity, not those unported bodies.
No item metadata inventory from CrazyHook or reference gameplay source is used.

Strict C11 compilation, warning-clean C++ and Swift-imported context/empty
player/single-RET smoke pass. Null/malformed ABI and unsupported entry checks
are separately labeled host rejections. No simulator, device or Xcode build
was performed. Parent owns source/project integration and native acceptance.
