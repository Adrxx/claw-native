# Player menu management

The additive facade closes ordinary retail UserInfo49b160 and Remove49b630 dialog callbacks, their selected-list and statistics helpers, and the actual application426e30 branch for full command8090. It does not claim whole425730 startup, the entire426e30 handler, a native modal pump or a completed state13 graphical popup.

The oracle is local original v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private decompilation and instruction evidence is under `work/player-menu-management-agent/`. Source functions and physical imports retain their actual addresses.

## Stable API and transport recipe

Use `claw_player_menu_management_entry(function,receiver,args,count,context,dependency,user,result)` with one raw `ClawSceneActorHost` token heap. Borrow the frozen PlayerCacheApplication context with its SaveLoad/SaveFile projections and source-owned manager/records. Borrow optional PlayerStartup for source cache selection and CStringAssignment with its existing allocation/fade context. Preserve all existing source ownership. Supply a caller-owned456-byte automatic projection at `automaticToken`: title128 bytes, list text256 bytes, two CString cells4 bytes each, time format64 bytes. Automatic contents have only the original local lifetime; no profile retains them.

Export live5371fc(application),537204(input mapping),53725c(difficulty),53ebe0(selected dialog record),53ebe4/e8(statistics controls),53ebec(change control) into the same raw heap before calls; reimport after callbacks and return. The selected application record atapp+64 borrows a manager-owned9800-byte record. Manager88bytes, application308bytes, input144bytes and actual12-byte list nodes retain the frozen modules' sizes and lifetimes.

Route frozen menu wrappers42bbe0/42bbf0 through PlayerCacheApplication. Its synchronous modal procedure dispatch must reenter this facade for49b160/49b630. Reuse the existing304-byte PlayerCache projection for its nested list operations. Root can deliver native dialog events to this facade using original HWND identities and message/control values. WM_INITDIALOG110 and WM_COMMAND111 compare complete32-bitwParam1/2. List notifications use exact retained control identity and highword1. Preserve each addressed call's source order.

Physical imports remain546d40 GetDlgItem,546d34 EndDialog,546d3c SetDlgItemTextA,546d1c SetDlgItemInt and546d44 SendMessageA. Supply ordinary listbox188/189, insertion180 and selection semantics synchronously. `4a3920` is the actual cdecl formatter with output raw automatic token, literal format and source arguments. Resolve raw pointers using token spans; never truncate host pointers. CString ctor/copy/destructor and assignment may compose frozen source modules; unlocked ordinary string ownership must preserve the constructor, copy, destructor sequence and actual allocator extents.

Remove49b630 only snapshots the selected record into53ebe0 and returns modal1 after OK selection; cancel returns0. It never deletes a record or changesapp+64 itself. The frozen42bbf0 wrapper posts8090/data6 only after positive modal result. New-player42bbb0 posts8090/data5. Deliver posts after normal message dequeue. The recovered actual426e30/8090 branch elects428c40(app,13,1,1,data) and reports429e10(app,8005,6ad) when that transition returns0. State13 is an actual380-byte owner with VT50bf94 and initialization438c40→4399d0(data); the graphical popup/transition subtree remains addressed and needs its own integration. Do not replace the command with an immediate native deletion or manufacture an application state.

UserInfo retains the selected record even ifapp+64 later changes. Initialization populates name/description/email, the Info title and two15-item level lists. Selection changes display score/time from the retained source record. Statistics helper49b470 resets labels and numbers before querying admitted nonzero/nonone levels through49aed0 and frozen49ae60. Both OK and Cancel simply close the informational dialog.

Validation uses fictional profile names and isolated in-memory game-file fixtures. No OS registry/settings, actual user save, shared native/Xcode project or device changes are part of this worker.

## Measured validation and reproduction

The completed ordinary differential corpus passes **87 paired calls/968 ordered snapshots**, visiting2057 mapped original.text addresses/2075 instrumented addresses. This includes82 new menu calls, three complete frozen record-insertion calls, one encrypted writer and one reader. The saved fixture contains actual original-encrypted29420 bytes for the fictional Player/Ada/Lin profiles; the real reader imports those records before retained OK/cancel/informational histories. Complete heap and196608-byte mutable-global state, ordered dependency state hashes, meaningful EAX, actual callee stack pop, list/record/String allocation ownership and retained UI values are compared. Source automatic bytes without defined lifetime are excluded consistently; defined text and physical-service changes are preserved in callback arguments/state.

Independent exact-size ASAN/UBSAN passes **35 source-matched menu replays/399 outer callbacks**. The replay uses308-byte application,88-byte manager,9800-byte records,12-byte list nodes,144-byte input mapping, distinct128/256/4/4/64-byte automatic projections and exact source allocation extents. Dead tokens, including dead initial fixture allocations, are denied. String constructor allocation tails of21/22 bytes use synchronous byte-backed word projections when a frozen word-only body writes the last byte; those projection bytes flush before the next external service. No extra source allocation bytes are granted or retained. New Menu/CStringAssignment and actively composed PlayerCache, SaveLoad, SaveFile, Startup, FadeBlend, DeathServices, ActorDestruction, Checkpoint and AmbientAudioBackend translation units are instrumented; other frozen support retains its separate validation.

StrictC11/C++17 and executable Swift imported-signature/layout smoke tests pass. The context is88 bytes onarm64 and the rich callback232 bytes. Evidence is saved in `work/player-menu-management-agent/verification.json`, `sanitizer-verification.json`, `comparison.log`, `capture.log` and `sanitizer.log`.

```sh
work/test-env/bin/python Tests/compare_player_menu_management.py
work/test-env/bin/python Tests/capture_player_menu_management.py
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -ffp-contract=off -I Sources Sources/PlayerMenuManagementRuntime.cpp Sources/CStringAssignmentRuntime.cpp Sources/PlayerCacheApplicationRuntime.cpp Sources/SaveLoadRuntime.cpp Sources/SaveFileRuntime.cpp Sources/PlayerStartupRuntime.cpp Sources/PlayerFadeBlendRuntime.cpp Sources/PlayerDeathServices.cpp Sources/ActorDestruction.cpp Sources/CheckpointLogicRuntime.cpp Sources/AmbientAudioBackendRuntime.cpp Tests/player_menu_management_exact_replay.cpp work/application-level-progression-agent/libProgressionFrozenSupport.dylib -lz -o work/player-menu-management-agent/exact-sized-replay
work/player-menu-management-agent/exact-sized-replay work/player-menu-management-agent/sanitizer-replay.bin.gz
clang -std=c11 -Wall -Wextra -Werror -I Sources Tests/player_menu_management_abi.c work/player-menu-management-agent/libSaveFileRuntime.dylib -o work/player-menu-management-agent/c11-smoke
work/player-menu-management-agent/c11-smoke
clang++ -std=c++17 -Wall -Wextra -Werror -ffp-contract=off -I Sources -c Sources/PlayerMenuManagementRuntime.cpp -o work/player-menu-management-agent/source.o
swiftc -I work/player-menu-management-agent/swift-module Tests/player_menu_management_abi.swift work/player-menu-management-agent/libSaveFileRuntime.dylib -o work/player-menu-management-agent/swift-smoke
work/player-menu-management-agent/swift-smoke
```

Ordinary time-string fixtures execute frozen constructor, shared copy and destructor bodies. Optional Assignment routing retains its independent evidence; this menu corpus does not elect a locked copy or overwrite path. Standalone49c860 constructs a fresh output CString; the caller owns its subsequent destruction. Physical UI/formatting/file services are deterministic fixtures. The complete438c40→4399d0 state13 graphical popup, its confirmation action and428c40 controller integration remain future source work. This evidence does not prove full native startup, game progression or physical device acceptance.

The optional Assignment facade has a separate **six unchanged-original assignment calls/18 ordered snapshots** and **six exact-size ASAN/UBSAN replays/18 callbacks**. Ordinary popup titles and fictional names cover20/21/22/24/30-byte CString allocations. A test-only internal facade probe reaches4f66cc without expanding the public menu ABI. CStringAssignment receives strict nullable word and byte lookups so its own exact-byte tail adapter can run; an outer constructor shadow cannot later overwrite the copied final character. The byte fallback passes the borrowed save host's opaque `save.scene.context`; a distinct, non-null outer/save context profile verifies that routing in both differential and sanitizer tests. Source files, header shape and ordinary87/968 +35/399 gates retain their measured scope.

```sh
work/test-env/bin/python Tests/compare_player_menu_assignment_tail.py
work/test-env/bin/python Tests/capture_player_menu_assignment_tail.py
clang++ -std=c++17 -O1 -g -DCLAW_TEST_MENU_ASSIGNMENT_PROBE -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -ffp-contract=off -I Sources Tests/player_menu_management_assignment_probe.cpp Sources/CStringAssignmentRuntime.cpp Sources/PlayerCacheApplicationRuntime.cpp Sources/SaveLoadRuntime.cpp Sources/SaveFileRuntime.cpp Sources/PlayerStartupRuntime.cpp Sources/PlayerFadeBlendRuntime.cpp Sources/PlayerDeathServices.cpp Sources/ActorDestruction.cpp Sources/CheckpointLogicRuntime.cpp Sources/AmbientAudioBackendRuntime.cpp Tests/player_menu_management_exact_replay.cpp work/application-level-progression-agent/libProgressionFrozenSupport.dylib -lz -o work/player-menu-management-agent/assignment-tail-exact-replay
work/player-menu-management-agent/assignment-tail-exact-replay work/player-menu-management-agent/assignment-tail-replay.bin.gz
```
