# Original application startup composition

`ApplicationStartupRuntime` recovers the **whole controlling body** `425730`, VT`50bee4` slot`+4`, from the pinned original v1.0 executable. The body is 4465 bytes, ending at`4268a1`; actual `RET8` is at`42689e`. The API is `claw_application_startup_entry(425730,app,[windowOwner,commandLine],2,context,dependency,user,result)`. Completion and the original EAX 0/1 are separate. This is not the old selected-cache instruction interval represented as a new function.

The executable fingerprint is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Recovery output is private `work/application-startup-agent/startup.c`; Ghidra's decompilation is checked against the actual instructions. It incorrectly omits some arguments and receivers: `4b8280` has two arguments, `401000` is cdecl with one scene argument, `42b140` takes level 0, and the old ambient CPtrList receiver is manager`+8`. The underlying window admission requires `windowOwner+4` HWND and publishes `windowOwner+8` as the application's instance-owner token; the instance owner's`+12` is HINSTANCE. The command-line string is copied unconditionally later in the entry, so an ordinary empty command line is a valid nonnull empty-string token.

## Composition and remaining boundaries

The caller creates the application using the existing frozen application constructor (`4254a0`, composed by `SceneStartupCompositionRuntime`) before invoking startup. Startup itself does not repeat that constructor or pretend to be WinMain.

| Source dependency | Frozen owner elected by the borrowed context |
|---|---|
| `4b8280(windowOwner,ignoredCommand)` | New thin 84-byte admission wrapper, calling existing `GameTiming` reset-rate/reset-clock bodies; two clock reads, reported rate FFFFFFFF, pacing 0, countdown/reload 100 |
| `4a3040(seed)` | `CRTRandomRuntime`, real TLS/thread seed ownership; initial clock plus GetTickCount wrapping addition/logical shift |
| `4ce960`, scene virtual admission/close, `4cf010`, collection constructors/lifecycle | `SceneStartupCompositionRuntime`, existing scene/display/graphics/audio/palette/world owners |
| `4b7210`, `4b7250`, `4b72e0` | `ResourceArchiveLoadingRuntime`, with the same live `ResourceTableConstructionRuntime` graph |
| `4b7f20`, `4b67f0`, reached table methods | Existing `ResourceNamespaceRuntime` and table owners, never synthetic resource matches |
| `4b61c0` | Existing `ResourceDataRuntime`/AudioPCM shared resource acquisition over the same archive heap |
| `4f5249`, `4222a0` | `PlayerStartupRuntime` message configuration/list/font owner |
| `4ebf80` | `PlayerFadeRuntime` constructor; it does not elect a visual fade or replace the still-addressed `4ec010` admission |
| `4c61d0`, `4c6260` | `LightPaletteRuntime` manager constructor/admission |
| `4f5133`, `402240`, `402270`, `402520`, `402570` | `SoundTriggerLogicRuntime` ambient owner |
| `4b52a0`, `4b55e0` | `MusicRuntime`, source MIDI driver/instance/resource globals `54131c/320/324` |
| **instructions426546..4266e0** | Existing `claw_player_cache_application_startup_span`, actual88-byte manager constructor and player selection/migration; no duplicated body |

Null borrowed optional owners elect the exact addressed dependency. The selected-player owner is required when its interval is reached, because the facade always composes that frozen interval. Unknown meaningful dependencies are never implicitly successful. The facade does not use an opaque prebuilt library: validation links 65 current source files.

The following remain meaningful **source-method boundaries**, not claimed physical implementations: registry configuration `4b5c50/4b5f30/4b5e90/4b5f80`; cached media/device probe `42b020`; game-mode probe `42a680` outside the archive's real retry profile; logging `5028ec`; `401000` logic registration; `42cab0`, CString path selector`4268b0`, `42ce90`, `42c640`; command binding `493c20`; fade admission `4ec010`; helper manager `422890`; sound-font `48bbb0/48c030/48bf70`; audio options`42cdc0/42ce20`; input `4b3410/4b3240/430590`; logo/movie `42b900/42b140`; and initial-state transition `428c40`. Hosts must elect their recovered bodies when available or preserve these exact boundaries. Returning1 from a fixture is evidence only for the caller's behavior under that fixture.

## Source bootstrap and retained failures

1. Admit the window; reset timing; seed CRT randomness; set reload33; hide cursor until its signed count is negative; allocate/publish 540-byte registry configuration and open the source Monolith/Claw registry path.
2. Query source options in original order, including retained tuning defaults; query User into the 32-byte automatic name with count 30. Cache audio/detail/front-layer options and volumes, increment runs, and force fades/emulation when direct video access is disabled.
3. Parse the real ordered command substrings `PLAY`, `RACING`, `MENU`, `NOSHELL`, `IPX`, `8BIT`, `16BIT`, `USER:`. `NOSHELL` has no stored effect here. Later matches override earlier choices. User text is uppercased first, then underscores/pluses are replaced with spaces. The source mode probe can override the elected state 4 and clear the network flag.
4. Publish the instance, log the original command line, clear app CString`+c0`, create the scene. Source flags are 1 or 5, optionally OR 16. A failed8-bit scene admission **continues**. A failed16-bit admission closes, retries once at 8 bits, and reports`3ea` only if that retry fails. A successful fallback clears the HiColor global.
5. Set 640×480, install428bc0, set tile manager`+64/+68` to 14, bind logic, run`42cab0`. Only after success destroy/free the prior archive and publish a new 72-byte controller. Select the source path, open readonly, and destroy the temporary CString before testing the open result. Open failure uses`800b/3eb`, or the source mode 8 fallback and`8010/3eb` when app`+104` admits it.
6. Acquire source STATES INGAME/GAMEOVER or their NANI alternatives, then construct/admit the command, fade, helper, message, music, ambient, input, light and control owners in order. Existing old ambient storage is destroyed through its embedded list before free. Input and control admission failures free their published objects but leave the source global token unchanged; no guessed rollback or nulling is added.
7. Compose the frozen player-cache interval. Publish`5371fc`, read/publish the clock and clear`53720c`; restore cached options; elect source logo/movie work; create the initial state with`428c40(state,1,0,0)`. State4 failure retries state2 once. Errors are`8005/3f3` for failed fallback and`8005/3f4` otherwise.
8. On success read/publish the clock again, clear stage delta, and compute NANI factors from **unsigned integer division by 100**, then Float32 conversion. Fractional percentages are not introduced. The final NANI gate rereads the live`5371fc` alias after the clock callback.

Ordinary failure returns retain reached publications and allocations exactly; there is no global cleanup transaction. The source SEH scaffolding and exceptional unwinding are not a native exception transport. Native missing-span/owner/service, ABI-domain and operation-budget faults are separate extensions, never source EAX 0 failures.

## Host recipe and physical isolation

Supply a raw word host for all original object/global tokens and synchronous optional exact byte spans for strings/odd allocations. The optional byte callback is needed for exact 9-byte `CLAW.REZ` allocation ownership; it never invents padded source allocations. Borrowed module contexts are copied before installing the stack-local host. Module host bindings are not left pointing to the facade's stack. CRT TLS, music and the scene composition's documented globals synchronize with raw source aliases at their dependency boundaries.

Allocate a separate caller-owned 1200-byte automatic projection: name32 at0, command300 at32, user-command300 at332, original log-command256 at632, temporary CString4 at888, registry count4 at892, and existing selected-cache304 at896. It is not a source heap allocation, is not freed, and must not be retained by callbacks. The archive still requires its own 168-byte header automatic token in its borrowed context.

The rich callback is the existing `ClawPlayerCacheApplicationCall`: source address, receiver, arguments, optional name, localMask and three synchronous buffers. Receiver-local bit256 precedes arguments; argument-local bits are emitted in ascending order. Local `4f21e0` mutates the actual300-byte command buffer. For local `4a3990` strstr, return offset + 1 into that buffer, or0 when absent; this adapts a32-bit original local pointer without returning a host pointer. `4268b0` writes a4-byte local CString cell; its returned local address is incidental because startup immediately dereferences that same cell. `4f6584` receives the same local cell as receiver bit256. Player-cache registry fields retain their existing raw scratch-token ABI.

Physical startup services are `546df0` timeGetTime, `546a24` GetTickCount, `546d54` ShowCursor, actual window/log imports, registry imports behind the source configuration owner, archive `4f1d90/4a7840/4a7260/4a7ae0`, source TLS/allocator services, and audio/input/font/media transports reached through elected owners. Tests never call a Windows registry, access real OS settings or user-save files, or drive a native app/device. Original executable/disc inputs remain local ignored evidence.

## Verification

Run from the repository root:

```sh
work/test-env/bin/python Tests/application_startup_build.py
work/test-env/bin/python Tests/compare_application_startup_runtime.py
work/test-env/bin/python -c 'import sys; sys.path.insert(0,"Tests"); import application_startup_build as b; b.sanitizer(); b.gates()'
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 work/application-startup-agent/exact-sized-replay work/application-startup-agent/sanitizer-corpus.bin.gz
```

The report, full source fingerprints, original comparison log and sanitizer log are private `work/application-startup-agent`. Whole-entry tests compare original RET8/EAX, ordered complete global/heap snapshots at every declared dependency, synchronous local buffers, allocator/free order, old-object cleanup, clock trajectories and borrowed context bindings. Exact-sized replay uses separate allocations, rejects accesses outside each source allocation, handles the9-byte archive pathname without padding, and removes freed storage. All 65 dependency files are instrumented with ASAN/UBSAN; C11/C++17-Werror/Swift import gates check the public ABI. LeakSanitizer is disabled only because this macOS runtime does not support it.

The final boundary comparison passes 151 whole calls and 15,898 ordered full snapshots; 55 cases retain exact-sized sanitizer replay evidence. The measured whole entry includes the original window/timing admission and frozen selected-cache interval. Three joined original archive-controller/open/fopen-error profiles and six joined music profiles are also checked inside whole425730. Music uses actual MSS identities546e70(startup),546e74(open MIDI),546e6c(master volume), with the output driver54131c live. Failed physical MIDI admission still produces successful bootstrap; audio-disabled startup additionally clears manager`+28` after admission. Other dependency bodies are addressed deterministic fixtures in these comparisons. Existing frozen resource-owner retail REZ evidence remains separate; the complete retail REZ recursive bootstrap, every input/registry/media method, native initial-state rendering, whole WinMain and device acceptance are **not** proved by this facade or these tests.
