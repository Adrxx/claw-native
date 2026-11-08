# Original player death command handling

`PlayerDeathCommands.h/.cpp` recover the application command branches for
`0x803a` and `0x8006`, the complete respawn controller `0x46be40`, cleanup
`0x46e2d0/0x46e340`, and the controller body of state transition `0x428c40`
for destination states 5 and 12. Constructors and UI/resource callbacks
remain explicit dependencies. This is controller parity under those adapters,
not a complete game-over screen or a claim of whole-game behavioral identity.

The executable is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private Ghidra outputs/logs are in `work/death-command-agent`; logs were checked
for script errors. The comparisons execute original instructions rather than
using decompiled text as the behavioral oracle.

## Posted messages and dispatch

Verified PlayerDamage posts `PostMessageA(window, WM_COMMAND=0x111,
wParam=0x803a or 0x8006, lParam=0)` and then sets its death latch. Its lives
counter chooses the command. Process these messages after the damage callback
returns; do not process them synchronously at the posting dependency.

The actual callback entry `0x4b8500` takes HWND/message/wParam/lParam. The
window registered in `0x54133c` receives a virtual pre-handler at slot `+4`.
For WM_COMMAND its slot `+0x48` resolves to `0x4b8810` in window vtables
`0x50c37c/0x50c3cc`. That routine splits the notification high word and command
low word, tries two pre-handlers, then calls the application virtual slot
`+0x14`. Application vtable `0x50bee4` maps that slot to `0x426e30`.
The recovered native API accepts the already normalized **low command word**.
It does not implement the surrounding Win32 message pump/pre-handlers.
The original command handler returns 1 for both branches, including rejected
respawns. The Win32 callback returns 0 once the command is handled.

The original two-level switch uses byte table `0x428950`, indexed by
`command-0x8005`, then address table `0x428870`. `0x803a` selects case 25 at
`0x4271b2`; `0x8006` selects case 1 at `0x42735a`. Neither address is treated
as a standalone function.

## Respawn

`0x803a` first executes `0x42a630`: a null current application state rejects
the command; otherwise virtual type queries accept 3, then 4, then 6. Query
count and short-circuit order are preserved. The current state pointer is
re-read between queries. The actual gameplay type getter `0x40af90` returns
3, and is implemented directly. State types 5/12 and the debug/base getters
also have their verified constant leaves implemented directly.

For an accepted state, `0x46be40` returns 0 if global player `0x537e88` is
zero or game-state `+0x2c` is zero. These are the observed gates; no alternate
meaning or substitute state is inferred. A rejected controller invokes
application error-routing helper `0x429e10(0x8005,0x3fb)`.

On success, the exact ordering is:

1. Music pause through `0x42d420`, gated by manager `+0x50` and `+0x14`.
2. If the initial map plane is present, compute a fade center from player
   x plus/minus 30 according to actor `+0x40` bit 2, and y plus 55. Project
   through the plane's original wrapping/view offsets and clamp to the
   manager bounds (upper bound minus 32, lower bound 32). Optionally resolve
   `0x52a00c`, `GAME_CIRCLEFADE`, and play it at global master volume. Call
   `0x48fae0(gameState,x,y,1250,0)`.
3. Write **23** to the live player's primary logic `+0x1c`, then immediately
   invoke its registered primary callback with the actor as one cdecl
   argument. This is observed code at `0x46bf79..0x46bf95`, not a guessed
   respawn state. Integrate the frozen PlayerInitialization state23 body at
   this dependency. The controller itself does not replenish health, clear
   the death latch, decrement lives, or overwrite player inventory.
4. Mark temporary actors for deferred removal, then plane `0x4d2000`, plane
   `0x4d1fd0`, actor-container virtual `+0x24(1)`, plane `0x4d2000`, plane
   `0x4d1fd0`, actor-container virtual `+0x24(1)`. The refresh argument is 1
   on both actor-frame calls. Plane pointers are re-read between these
   calls. **No `0x4c9390` interaction pass is called here.** Use the frozen
   SceneActorRuntime for the two frame dependencies when integrating.
5. Map/render refresh `0x4cb9b0(map,parent+4 surface,parent+8 actors)` and
   renderer virtual `+0x34(surface,parent+4 second value)`.
6. If the initially saved plane was present, reproject the updated player
   x and y minus 32 through that same saved plane. When game-state `+0x44`
   is `0xffffffff`, optionally resolve/play `0x5246b4`, `GAME_FLAGWAVE`.
   Call `0x48fbe0(gameState,x,y,1000,500)`; this second center has no manager
   bounds clamp.
7. Music resume through `0x42d440`, with the same gates, then `0x42abf0`.

Plane wrapping uses signed comparisons with 32-bit wrapping arithmetic,
including one-period adjustment, the asymmetric view-range correction, and
the final `plane+0x50/+0x54` offsets. It is not modulo or floating arithmetic.
The player and scene tokens may change during callbacks; subsequent reads
follow the original re-read order.

Cleanup walks the live actor CPtrList, caching next before checking its actor.
Actor `+0x164` bit `0x2000` sets actor `+8` flag `0x10000`. Null actors are
ignored. A nonzero plane `+0xb0` additionally invokes its tree enumerator
`0x4d51f0(tree,0x46e340)`. The native single-actor callback is exposed for
that service to enumerate the exact tree members. This does not delete
immediately or change primary logic to 29; deferred scene deletion owns that.

## Game over and retained state history

`0x8006` does not query current state type. When application `+0x9c` is
nonzero it requests `0x428c40(newState=12,parameter=1,retainPrevious=1,
extra=0)`. Otherwise it first writes current state `+0x38=1`, then requests
`newState=5,parameter=1,retainPrevious=0,extra=0`. The raw application field
is exposed through token memory; no guessed mode label is assigned to it.

Transition first saves old state type, calls its virtual `+0x28(newState)`,
then either appends the current state to application `+0xdc` CArray or calls
its deleting virtual destructor. The non-retained route then destroys every
earlier retained state in array order (including repeated tokens) and frees
the array, including a free of token zero. Array size is re-read after each
destructor. Allocation growth, count/capacity, initialized new elements,
untouched unused capacity, and the retained allocation history are recovered.

The state-5 and state-12 constructors both allocate `0x2c8` bytes. Their
controller-owned field writes and subobject calls are reproduced, preserving
allocator seed words left untouched by the original. Vtables become
`0x50c1e4` and `0x50bfec`. Application `+0xa0 != 0` instead allocates the
original `0x154`-byte base/debug state `0x50b4ec`, writes its observed fields
(including a **one-byte** clear at `+0x4c`), and returns success without
running initialization or resetting clocks. Allocation failure on this
special path also returns success with a null current state, as the original.

Ordinary allocation failure clears window `+0x244` and returns 0. Otherwise
reset clocks, call new-state virtual `+4(application,parameter,oldType)`, and
on failure delete that state and clear application current-state `+0x2c`.
On success call its virtual `+0x24(oldType)`, set window `+0x244=1`, call
keyboard reset `0x431300` and set keyboard `+0xc=0xffffffff`, call mouse reset
`0x4b3ab0` and set mouse `+0x20c=0xffffffff`, then reset clocks again. The
state-12 prior state remains retained even if new-state initialization fails.

Failed state12/state5 transitions invoke `0x429e10(0x8005,0x6ad/0x3fc)`.
That small original wrapper forwards to application `+8` virtual `+0x1c`
when the window exists. Its UI/error machinery remains a host dependency.

Clock reset composes the frozen `claw_timing_reset_clock`: read once, clear
clock delta and paced start, preserve countdown/reload. When application
`+0x30` is nonzero, read a second time for animation and clear animation delta.
Publish stage now/delta and, if the live player has private data, set private
`+0x120=20000`. No accumulator write, fixed timestep, or sleep is introduced.

## Dependencies and limits

Host lookup provides mutable sized spans for original 32-bit tokens and
read-only vtable metadata. Allocation/free, clock reads, and leaf calls are
explicit. Tokens may identify interiors; list/array storage must remain valid
across callbacks as it did for the original. This module does not run native
audio, GUI screens, transitions' resource loaders, music transport, camera
fade effects, plane transforms/render internals, or Win32 input services.

Constructor dependencies are `0x40b5c0`, `0x4dcc40`, `0x4f5cbd`, `0x429980`,
`0x4296f0` and Win32 `SetRect` import `0x546d5c`. SetRect is normalized into
host call **receiver=rectangle token**, four coordinate arguments, because the
shared call record has four argument slots; its original five stdcall
arguments are tested in the oracle. State virtual initialization/open/close/
destruction remain UI/resource dependencies. Tests adapt these, sometimes
mutating retained buffers or rejecting initialization, without claiming their
full original implementations are recovered.

Respawn primary and actor-frame calls are also adapted in this suite. The
frozen PlayerInitialization and SceneActorRuntime suites separately compare
their real original bodies. Native integration must compose them; controller
tests alone do not demonstrate real complete gameplay or screen acceptance.
Plane-tree membership is adapted; the single-actor cleanup callback and live
list cleanup are independently original-instruction compared.

Diagnostic fault 1 means a missing sized token span, 2 an allocation/null
history-storage fault, and 3 an unsupported transition destination. These are
native diagnostics, not valid original returns. Only state5/state12
transitions are supported. Other commands return zero without work; the rest
of the original application switch is outside this unit.

## Verification

Run `work/test-env/bin/python Tests/compare_player_death_commands.py`.

The suite compares complete actor/logic/private, application/game-state,
scene/list/plane, render/input, allocation and retained-history buffers plus
clock/global words. It checks ordered call arguments and full snapshots at
every adapted call/allocation/free/clock read. There are 6,000 generated
controller cases, 900 cleanup/history cases, 672 consecutive retained
transition-chain passes, 192 actual Win32 WM_COMMAND routing cases (including
nonzero notification high words), and 64 actual gameplay-vtable respawn cases.
Both state-allocation and initialization failure paths are included; history
chains exercise growth, unused tails, subsequent clear and repeated tokens.
The original Win32 routine and command controller execute in the routing
cases; pre-handlers explicitly return zero. Routine comparisons are scoped
to their tested adapters and do not establish whole-game scheduling parity.
Directed null-current cases and three actual original fault prefixes (null
current state on the state5 route, retained-history allocation failure, and
an invalid list successor) match the native diagnostics and all mutations
before the fault. The final suite visited 1,151 original-image instruction
addresses, excluding synthetic service handlers and the stop sentinel.
