# Original scene actor creation and scheduling

`Sources/SceneActorRuntime.h/.cpp` recover generic creation `0x4c8be0`, named
creation `0x4c8da0`, sorted insertion `0x4c9320`, complete scene actor update
`0x4c8fc0`, and the actor phases in normal/subdivided stage routines
`0x46ace0/0x46ad70`. Original executable v1.0 is fingerprint pinned to SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

Common construction/initialization is composed from frozen WorldObjectRuntime.
Animation and replay clock changes use frozen GameTiming. The interaction
service delegates to frozen ActorInteractions through the host; its body is
not duplicated. Generic actor destruction, registry resolution, gameplay
callbacks, heap services, and stage/map services remain explicit dependencies.

## Creator flags and actual player caller

Generic creation takes six words: ID, X, Y, Z, entry token, and constructor
flags. The original requests `0x1b4` actor bytes and `0x174` logic bytes, binds
the supplied entry through the common initializer, and inserts the actor into
the sorted scene list. Constructor flags are passed unchanged to `0x4c9780`.
Registry entry flags may additionally set the common `0x800000/0x1000000`
classification bits during initialization.

**This creator does not force flag `0x40000`.** The WWD object-record loader
separately ORs that flag; that observed behavior does not authorize applying
it to every generic constructor. The native API therefore keeps flags explicit.

The actual CaptainClaw caller is inside entry `0x46aeb0`, at instructions
`0x46b41f..0x46b439`:

```
id = edi                  // 1 on the observed initialization paths
x = 320
y = 350
z = 100
name = 0x522e80           // CaptainClaw
flags = 0x40002
container = scene +8
call 0x4c8da0
```

It stores the returned actor in global `0x537e88`. At `0x46b47c..0x46b480` it
explicitly invokes the actor's primary callback afterward. That callback's
initialization later places Claw at the world's spawn coordinates and Z4000.
The startup caller does not use the creator's immediate-callback flag.
These caller arguments are established by original instruction inspection;
tests execute the complete creator with those arguments and original
CaptainClaw binding metadata. The full resource-heavy `0x46aeb0` startup body
is outside this routine comparison.

The named wrapper calls registry `0x4f6286` at
`container +0xc -> parent +0x14 -> registry +0x10`. Resolution failure returns
zero without allocation. The host returns the entry token, which is a portable
normalization of the original registry's output pointer and separate boolean.
The entry supplies callback at `+0x10` and flags at `+8`.

After successful initialization, insertion writes actor `+0x68` with its node
token. If the **original constructor argument** has bit `0x200000`, the
current primary callback is invoked with actor as one cdecl argument. This
occurs after insertion and node assignment. Its return value is ignored.
Initialization rejection invokes the actor's virtual deleting destructor
(slot `+4`, generic target `0x4c9be0`) and returns zero.

## Raw scene list and ordering

The factory at entry `0x4cea10` installs actor-container vtable `0x513c20`
at `0x4ceab5` and stores this container in parent `+8` at `0x4ceac5`. Initial
container words are:

```
513c20, 0, 0, parentToken, 5107bc, 0, 0, 0, 0, 0, 10
```

The embedded CPtrList starts at container `+0x10`. Container `+0x14/+0x18`
hold head/tail, `+0x1c` count, `+0x20` free nodes, `+0x24` heap-block chain,
and `+0x28` block size. A node has next, previous, and actor token at offsets
0, 4, and 8. Unlike the audio intrusive nodes, these are separately allocated
list nodes and their tokens are not actor-token-plus-four.

Insertion scans head to tail and inserts before the first actor whose signed
Z at `+0x64` is greater than the new signed Z **and** whose `0x20000` flag is
clear. Otherwise it appends. Equal Z retains existing order. Actors pending
reorder are ignored as insertion barriers. Standalone `0x4c9320` and creator
insertion use the same rules.

Node pooling includes the complete relevant original CPtrList behavior:
allocate `blockSize*12+4`, link its four-byte header into the block chain,
populate the free list, consume one node, and increment count. Removed nodes
are returned to the free list. Removing the final node clears count/head/tail/
free-list state and frees the complete block chain. These bodies execute in
the original tests; list operations are not host stubs.

## Actor frame dispatch

Container vtable slot `+0x24` (`0x513c44`) points to `0x4c8fc0`. It initializes
two global temporary arrays once, with their actual atexit registrations, then
resets them each frame. Reset frees their backing buffers, including free(0).
Array growth preserves original capacity/count and initialized versus untouched
words, rather than substituting an unobserved vector-allocation policy.

When `refreshClock` is nonzero, animation clock refresh reads timeGetTime once
and computes wrapped elapsed milliseconds. Zero leaves both animation words
unchanged. Stage and animation clocks remain distinct inputs.

For each node, **the next node is cached before invoking gameplay**. Primary
logic `+0x20` is an unsigned animation-delta countdown. A positive remaining
timer suppresses both callback and skip-counter changes. Equal/larger delta
expires it and proceeds. When the timer is zero, nonzero logic `+0x24` is
decremented; otherwise logic callback `+0x10` runs with the actor argument.
Actor disabled flag 1 does not independently suppress this primary dispatch.

After that actor's callback/gating, actor flag `0x10000` adds it to the deletion
array. Otherwise `0x20000` adds it to the reorder array. Deletion has priority
when both are set. After the full primary pass:

1. Process deletion array in order. For an actor with `0x80000`, write primary
   state 29 and invoke its callback first. Remove its current scene node, then
   invoke virtual deleting destruction. The callback's return is ignored.
2. Process reorder array in order. Clear `0x20000`, remove the current node,
   scan the current list, insert with the same signed-Z rules, and replace
   actor `+0x68` with the new node token.

Gameplay callbacks can create actors during primary dispatch. When the current
actor had no successor before its callback, a newly appended actor is not
visited that frame. With an existing successor, appending can be reached later
when that successor caches its now-updated next node. Tests perform actual
nested original creator calls to verify this distinction. Valid cached nodes
and objects must remain alive; arbitrary removal/free of an already cached
successor is not a supported safe host mutation. Reentrant updates sharing the
original global scratch arrays are not claimed safe.

## Interaction position and stage subdivision

The same container's vtable slot `+0x40` (`0x513c60`) points to interaction
entry `0x4c9390`. In normal stage entry `0x46ace0`, the original order is:

1. Stage service `0x46c860` on the owner.
2. Optional collision-plane service `0x4d1fd0` through parent `+0x24`, map `+0x5c`.
3. Actor update `0x4c8fc0` with refresh 1.
4. Interaction `0x4c9390` on that container.

The actual branch in caller `0x46ac30` (`0x46ac35..0x46ac4c`) and the separate
caller `0x475dc0` (`0x475dd9..0x475df3`) chooses the subdivided stage entry only
when **unsigned 18 < stage delta < 100**. Other deltas take the normal path.
This is the observed original choice, not a proposed fixed frame rate.

Subdivided entry `0x46ad70` uses 18ms parts and a final nonzero remainder,
temporarily publishing stage and animation clocks through `0x42ae40` for each
part. Each part runs the same service/update/interaction order, with actor clock
refresh 0. Intermediate parts after the first and before the last first call
optional map service `0x4d2000`. Stage now/delta/accumulated values are restored
after the loop, and that replay restore also restores the animation clock to
the original stage values. A direct zero-delta subdivided call runs no actor
pass but still performs the replay restore. The public automatic API applies
the observed threshold; the explicit API allows direct comparison of both
original entries.

Both entries finally inspect owner `+0x764`. When nonzero and the global
player has an image, they select frame index 100, using the image frame array
only when its signed first/last range contains 100, otherwise frame token zero.
This override occurs after all actor/interaction passes and clock restoration.

The complete higher-level camera/render/input work surrounding these two caller
branches remains outside the API. `0x46c860`, `0x4d1fd0`, and `0x4d2000` bodies
are external services here. ActorInteractions itself is already recovered;
its host projection must honor its documented fixed-membership contract during
an interaction call. This module establishes the point at which it is invoked.

## Host contract and faults

The host owns 32-bit token identities, exact memory spans, allocation/free,
registry and gameplay callbacks, destruction, and millisecond reads. Generic
actors use the frozen 128-word actor and 93-word logic representation, including
preserved guard words beyond the original actor's allocation size. Constructor
phases project frozen constructor outputs into the actor before nested logic
allocation, preserving allocator-boundary observations without duplicating
the common constructor body.

Original actor allocation failure faults at `0x4c8d02`; logic allocation failure
faults at virtual dispatch `0x4c7e8b`, even when the supplied callback is zero;
node-block allocation failure faults at `0x4f5ac1`. Native fault 2 reports these
null/allocation paths while preserving their compared pre-fault state. Fault
1 denotes an unresolved host span. These diagnostic returns do not claim the
original returned normally. Generic destruction resolves `0x4c9be0` directly;
other actor vtables require the host's slot-4 metadata, and the resolved target
is dispatched as an explicit service.

## Checks

Run `work/test-env/bin/python Tests/compare_scene_actor_runtime.py`. It compiles
its private dylib from this source plus the frozen common constructor, clocks,
and interactions. The pinned executable executes original creation, common
initialization, CPtrList/CArray bodies, frame dispatch, stage entries, and
interaction entries. Synthetic gameplay services are clearly outside original
code; the nested-creation service calls the real original creator.

Checks include 1,500 creators, 1,500 frame updates, 4,000 chained frames, 1,000
normal/substep stage calls, 500 direct insertions, actual player creation
arguments, mutable callback spawning, image100 cases, destructor resolution,
and real allocation fault boundaries. Every scene/node/block/array/actor/logic
word, clock/global word, ordered service call, and callback/allocator-time
snapshot is compared. Scheduling cases execute original and frozen interaction
bodies with zero masks; combat/contact semantics are independently covered by
the existing ActorInteractions suite and are not newly proven here.

The final run visits 1,293 instruction addresses in the original image. Heap
and callback adapters, synthetic shim code, and unexecuted gameplay/destructor
bodies remain explicit limitations. This is scene-scheduling evidence, not
whole-game completion.
