# Original v1.0 logic-state registry

`Sources/LogicStateRegistry.h/.cpp` recovers the state-related C++ initialization sequence, the complete state-binding order inside `0x401000`, the mutable name Patricia trie, class callback arrays, and ID-to-CString storage from original Captain Claw v1.0. The executable is pinned to SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. No reference game implementation was used.

The portable source embeds the captured constructor and binding tables. `Tests/logic_state_registry_profile.json` contains small source-derived evidence: constructor identities, all 119 introduced names and literal tokens, and six useful class maps. Private recovery logs and the extraction program are in `work/state-registry-agent/`.

## Startup and identities

The PE entry `0x4a46b0` calls CRT initialization `0x4a5730`; `_initterm` at `0x4a5880` iterates the C++ constructor table at `0x522000..0x522244`. The native initialization reproduces the 84 state-related constructor wrappers in their actual table order, including Wolvington constructor `0x4a01d0`. It initializes the name trie at `0x537668`, name array at `0x537698`, and 82 class callback arrays. The image counter `0x52712c` starts at 2000; table construction preserves that counter.

Complete original `0x401000` execution introduces 119 global names and leaves the counter 2119. Its 212 metadata registrations are interleaved with 1,139 class binding writes. Repeated registration reuses each name's existing ID and updates its class binding; it preserves the original name CString and counter. The 19 CEnemy-only registration profile used earlier differs from this complete sequence.

A second original caller is statically confirmed inside application initialization `0x425730`, at call site `0x425eaa`. Its function boundary and decompilation are in the clean private recovery log; it has not been executed end to end.

The verified runtime caller `0x42ce90` invokes the entire registration routine at `0x42cfbe`, after successful renderer initialization when changing to mode 8 or 16. Missing scene, unchanged mode, invalid mode, and renderer initialization failure skip registration. Before registration it writes tile manager offsets `0x64/0x68` to 14. Tests execute this caller and its six directed guard/success branches; renderer close/open, callback installation, error reporting, and the subsequent resource loader are explicit services. Resource loader `0x42cab0` returns 0 in this bounded fixture to stop after registration. This is original runtime caller evidence under declared services. Complete retail WinMain, every unrelated CRT initializer, platform/resource initialization, and full game startup are not proved by this module.

| Class | Original table token | Bindings |
| --- | --- | --- |
| CEnemy | `0x537638` | 19 |
| Human | `0x537878` | 12 |
| Officer | `0x537ba0` | 2 |
| Rat | `0x53c0e8` | 4 |
| RatBomb | `0x53c118` | 2 |
| Projectile | `0x538428` | 1 |

Useful complete-bootstrap IDs are IDLE 2000, FALLING 2001, EXPLODING 2002, STRIKE 2003, DEAD 2004, JUMP 2005, MOVINGLEFT 2006, MOVINGRIGHT 2007, BOUNCE 2008, LIFTED 2009, THROWN 2010, PAUSE 2011, DROPPED 2012, MOVEBACK 2013, MOVEAHEAD 2014, BLOCKHIGH 2015, BLOCKLOW 2016, FLAILING 2017, HOME 2018, JUMPATCLAW 2019, JUMPBACK 2020 and THROWING 2030. Full names and callback identities are in the pinned JSON and executable native tables. Lookup is case sensitive.

Nonempty name cells contain allocated CString data pointers. They do **not** retain original literal pointers. `ClawLogicStateView.nameToken` is that actual allocated identity; `literalToken` is separately retained native metadata recording the first name-registration literal. Enemy pointer equality must use the identity supplied by its original caller. Substituting a literal token changes behavior. Empty names use original shared data token `0x52e1c4` (header references=-1, length=capacity=0).

ID 1000 is an actual empty name entry created by the original downward array growth. Unknown ID lookup can reallocate arrays, move previous contents, clear new cells, and construct shared-empty CStrings. Class lookup also grows its array and returns the stored function word, including 0. This module does not apply inheritance or choose a fallback callback.

## Native API and service contract

Zero the registry and context for a fresh image. Supply writable `heap`, `heapBase`, `heapCapacity`, clear `fault`, call `claw_logic_state_context_defaults`, then `claw_logic_state_initialize` and `claw_logic_state_bootstrap`. Defaults set only counter 2000 and empty-string identity; they preserve supplied raw words, storage and services. Bootstrap may be repeated to model original alias registration. Re-running initialization on a live registry is outside the startup fixture.

`find_id`, `register` and `resolve` expose mutable original semantics. Resolve returns the ID, class function, allocated name identity, first literal identity, and a pointer into supplied arena storage. Storage and returned text must remain alive. Class token 0 requests only the name. `table_count/table_at` expose all 84 raw original object views.

The trie owns 11 words and indexed objects own 9 words. Twelve-word views preserve otherwise untouched trailing words, including actual overlap with adjacent known global objects. Pending ranges, lookup flags, and signed array limits are retained. `errorGlobals[15]` represents `0x544b14..0x544b4f`, including lazy diagnostic literals.

The dependency callback receives exact function/receiver/arguments and the live registry/context at the call boundary:

- `0x4f63ec` operator new and `0x4a48e0` allocation: `(byteCount)`.
- `0x4a9070` reallocation: `(oldToken,byteCount)`; the allocator preserves existing bytes.
- `0x4f6428` free: `(allocationToken)`.
- `0x4a35f0` atexit: `(originalDestructorFunction)`.
- Scene metadata method: supplied function and receiver, `(logicFunction,originalNameLiteral,flags)`, with decoded text in `name`.
- `0x4db4d0` diagnostic handler: handler receiver, `(objectToken,originalMessageToken,errorCode)`, with text in `name`. Null lookup is compared against the original handler boundary. `errorLocation` supplies the original error-location value.

Allocation tokens must address the provided arena. The callback owns allocator policy and metadata registration. With a null callback, a bounded 16-byte-aligned native arena is used; reallocation copies the active original array. This allocation/lifetime policy is a host extension, and metadata registration/atexit/free bodies are omitted services in that mode. Its resulting normal registry/heap behavior is compared against the same explicit allocator profile.

Native fault 1 reports allocation/capacity failure,2 invalid storage identity,3 missing tables/literal metadata capacity. The native metadata limits 96 tables and 256 names and these fault returns are host extensions. Original out-of-memory diagnostics, exception unwinding, arbitrary counter overflow/invalid structures, concurrent CString access, and platform allocator behavior are outside proved scope. CString assignment reproduces retained capacity, copying, reference decrement and free order in the serial fixture; original InterlockedDecrement is adapted as an exact memory update. Tests separately record and compare its 156 argument/complete-buffer snapshots; concurrent behavior is outside scope. Public CString destruction remains a separate actor-destruction module.

## Verification

Run `work/test-env/bin/python Tests/compare_logic_state_registry.py`. It compiles the owned source through a private test wrapper using strict optimized C++17 flags, executes the hash-pinned original i386 bodies, and compares all 84 twelve-word views, counter, diagnostic globals and the entire 1 MiB arena after each operation. Every external callback compares its ordered arguments and the complete raw-object/arena snapshot. SEH head restoration is asserted.

The final suite has 1,899 complete operations and 4,834 ordered callback snapshots across 12,506 original instruction addresses. It includes three coherent preserved-word/random-arena profiles, 252 actual CRT constructor calls, complete and repeated bootstrap histories, every introduced name/literal identity, missing and negative IDs, empty/prefix/high-byte names,150 new-name/alias histories, and 252 retained/copy-on-write CString assignment cases. The no-callback arena is also checked against the original-service allocator profile. These checks establish this registry scope; they do not establish full-game behavior identity.
