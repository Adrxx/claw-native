# Original core handlers and bitset lifecycle

`Sources/CoreRegistration.h/.cpp` recovers the original core handler list, its construction/search/register/remove routines, the default and empty-string bitset construction paths, and CRT free-wrapper control flow. The original v1.0 executable is SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private independent recovery artifacts are in `work/core-registration-agent/`.

## Recovered entries

| Original identity | Native behavior |
| --- | --- |
| `0x4dc3a0` | Handler construction: callback `0x4dc420`, modes 2/2, prefix, low status 16 bits cleared; search index and upper status retained. |
| `0x4dc3d0` | Binary lookup, including exact wrapped signed subtraction and retained insertion index at handler+4. |
| `0x4dc560` | Sorted global registration/update/removal, old-handler return, capacity gating, overlapping moves and untouched trailing storage. |
| `0x4db620` | Base construction, default handler selection and lazy diagnostic globals. |
| `0x4db6c0` | Base destruction: restores base vtable then unregisters receiver with argument 2=0. |
| `0x4dc180` | Default bitset construction with handler `0x544b68` and configured original size. |
| `0x4dc7b0` | Exact explicit bitset initialization: inline 32 bits or allocated storage rounded to complete 32-bit words; failure preserves intermediate fields. |
| `0x4dbe10` | Empty-string and null-string constructor paths. Nonempty parsing remains unsupported before object mutation. |
| `0x4db600/610`, `0x4dbb70/80`, `0x4dc160/170`, `0x4dc260/270`, `0x4dc380/390` | Five original handler CRT wrappers/bodies in actual PE order. The final wrapper is a no-op. |
| `0x4a49b0`, `0x4f6428` | Full wrapper selection/order over declared CRT lock, small-block and Windows heap services. Their physical allocator bodies remain explicit. |

`0x4dbcb0` is inside dynamic-array destructor `0x4dbca0`; it is not a bitset constructor. Bitset destruction `0x4dbcd0` remains owned by frozen `ActorDestruction`. The tests compose that recovered destructor with this module's populated unregister and free wrappers.

## What the actual constructor does

The retail image starts with registration count `0x544d18` equal 0. A byte-level scan finds exactly one internal direct call to `0x4dc560`, at `0x4db6cc`, which passes removal argument 0. The absolute function pointer is absent from the mapped original image; no vtable contains a nonzero-registration binding. All writes to the count are inside the recovered method itself. This supports an empty list in ordinary internal game operation; it does not imply hypothetical external code cannot call the method.

Tests execute the actual 84 state-related CRT constructors, then the five core-handler wrappers at PE slots `0x52222c..0x52223c`, followed by 120 original `0x4332f0` enemy constructors. The list remains empty. Each enemy constructor:

1. Calls `0x4dc180` on enemy+`0x2f4`.
2. Calls `0x4dbe10` on a stack-local temporary with `(0x534938,0)`; the original empty string selects default size 32.
3. Copies the temporary bitset and destroys it; that destruction calls `0x4dc560(handler 0x544b68,temporaryToken,0)`.

The temporary removal is a real call. With count 0 it returns before looking up or changing the handler index. The frozen `GenericEnemy` inline representation therefore matches this declared default 32/empty-string/empty-list profile, including complete shared core globals across callbacks. Under a manually populated list, the omitted temporary destructor can change handler+4's lookup index. Frozen `GenericEnemy` does not represent that extra global context; such a composition requires an explicit adapter or later recovery. No change to the frozen module was made.

The constructor proof uses its existing explicit actor-binding, resource and collision services. It executes the state/core CRT subset, not all unrelated CRT initializers or retail WinMain. Full retail startup is not established by this proof.

## API and integration

`ClawCoreRegistrationGlobals.words[130]` is the exact contiguous region `0x544b14..0x544d1b`: diagnostic globals, four six-word handlers, all 32 three-word rows starting at `0x544b98`, and count at words[129]. Unwritten words and high status halves are preserved. Defaults copies only original `0x533470` size 32; it does not reset raw globals or create registrations.

For a new image, zero the globals, apply defaults and initialize the five handlers. With `LogicStateRegistry`, preserve the shared first15 words explicitly: after state-array initialization, copy registry `errorGlobals` into core words[0..14], run core initialization, then copy those 15 words back before registry bootstrap. This follows the observed CRT order and preserves the default handler fields shared by both APIs.

Use `claw_core_registration_entry(function,receiver,arg0,arg1,globals,host,fault,result)` to route `ActorDestruction`'s `0x4dc560` boundary to the full method. It returns support separately from meaningful original EAX. Base/bitset constructors and search/registration/bit allocation return their recovered values; void-body incidental EAX is not exposed as a gameplay result.

The registration method retains original edge behavior:

- Any nonzero request is rejected when count is32, even if updating an existing row.
- A missing removal performs lookup when nonempty, changing the handler's insertion index.
- When empty, insertion uses the handler's **preserved** index instead of resetting it. Valid indices 0..31 are compared against the original, including resulting writes beyond the active row range.
- New row status clears only its low 16 bits. Removal shifts active rows without clearing stale tail storage.

`ClawSceneActorHost.lookup` supplies exact live object/backing spans; core-global tokens resolve directly inside the supplied globals. Empty parser strings require a readable one-word span. Allocation uses `host.allocate` at the original `0x4a48e0` boundary. Null allocation returns follow the original bitset result/diagnostic path, including partial size/pointer fields.

For nonnull `0x4a49b0` backing release, supply `heapHandle` (original global `0x545fc4`), the resolved `heapFreeFunction` identity for IAT slot `0x546964`, and two writable one-word `freeScratchTokens` for its local out-parameters. `host.call` receives exact ordered boundaries:

1. `0x4a7bc0(9)` CRT lock.
2. `0x4ab400(pointer,scratch0,scratch1)` small-block lookup; nonzero return requires the service to populate its two out cells.
3. If found, `0x4ab460(*scratch0,*scratch1,block)` then `0x4a7c40(9)`.
4. If absent, `0x4a7c40(9)` then supplied HeapFree function `(heapHandle,0,pointer)`.

Null pointers skip all these services. This module does not reproduce CRT mutex internals, small-block heap structures or Windows heap allocation/free. A native physical allocator profile remains an explicit host choice. `errorLocation` supplies the original `0x4dc680` diagnostic location value; diagnostic method `0x4db4d0` receives its actual handler receiver and `(object,messageToken,code)`.

Fault 1 means missing span/service; fault 2 means a represented count/index outside the supported storage. Those checks and support0 for nonempty parser bodies are native scope boundaries, rather than original normal-return claims. Arbitrary invalid objects, count overflow, allocator internals, concurrent free/registration and exception/platform behavior remain outside this proof.

## Evidence

Run `work/test-env/bin/python Tests/compare_core_registration.py`. It compiles strict optimized C++17 source plus frozen destruction read-only into this worker's directory, then runs the separate CRT/enemy caller proof. The helper reads existing registry/enemy test fixtures without editing them and redirects all builds to `work/core-registration-agent/`.

The primary suite passes 17,805 complete operations and 2,415 ordered snapshots across 487 original instruction addresses. Each compares all 130 raw global words and the entire 64KiB arena; each external service compares exact arguments, receiver and complete live buffer snapshot. Meaningful EAX and SEH head restoration are checked. Directed and retained histories cover all counts0..32, capacity update rejection, missing/found removals, stale insertion indices, signed/wrapped pointer lookup, partial allocation failures, null strings, lock/free branches and 168 joined bitset destructor paths.

The caller proof additionally executes84 state CRT constructors and five handler constructors, then120 complete enemy comparisons with 1,080 callback snapshots augmented by all core globals and the original registry arena. It reaches 2,402 original instruction addresses. The normal constructor's temporary removal and the absence of nonzero registration are directly observed. These figures describe separate bounded suites and are not full-game identity evidence.
