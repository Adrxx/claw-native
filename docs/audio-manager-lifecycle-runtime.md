# Original audio manager initialization and lifecycle

`AudioManagerLifecycleRuntime.h/.cpp` recovers the finite manager constructor/startup/stop/shutdown/destructor bodies and the duplicate-voice stop loop. It uses the frozen `AudioEvents` table and explicit callbacks for frozen resource/PCM/ambient bodies and physical DirectSound transport. No all-zero original initialization, unconditional stopAll, repaired source loop or reference gameplay implementation is substituted.

The oracle hashguards `Original/claw10/CLAW.EXE` SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private `work/audio-manager-lifecycle-agent/roots.c` covers verified function boundaries; assembly in `work/v10-disassembly.txt` establishes true argument counts where Ghidra invents fastcall/extra COM parameters.

## Complete owned entries

| Address | Source ABI | Behavior |
|---|---|---|
| `4b4710` | thiscall manager, no stack args | Constructor, original field stores, volume-table initialization; EAX=manager. |
| `4b4770` | thiscall manager, one flag word | Deleting destructor; flag lowbit1 frees manager; EAX=manager. |
| `4b4790` | thiscall manager, no args | Base destructor, vtable store, conditional shutdown. |
| `4b47e0` | thiscall manager `(hwnd,cooperativeLevel)` | Whole DirectSoundCreate/SetCooperativeLevel startup/failure ordering; EAX boolean. |
| `4b4860` | thiscall manager, no args | Whole resource-head destruction loop and device release. |
| `4b4b40` | thiscall manager, no args | Stop each resource and its duplicate voices. |
| `4b4670` | thiscall pool, no args | Whole duplicate-voice stop loop. |
| `4b3c80` | no stack args; ECX ignored | Write all101 original volume-table words. |

The manager is `0x80` bytes/32 words and its vtable is `513514`, whose deleting destructor is `4b4770` at slot0. The original scene initializer `4cea10` allocates `0x80` at instruction `4ced08`, calls the constructor at `4ced22`, and stores the result at scene+20 (`4ced2e`). It later calls `4b47e0(window,1)` at `4cee63`. Failure invokes deleting destructor through vtable slot0 and sets scene+20=0 (`4cee6c..7d`); the scene's existing required-audio flag/error path remains owned by frozen `SinglePlayerSceneRuntime`, not this module.

## Exact initialized fields

The constructor writes, in source order:

1. Resource-list head+4=0 and tail+8=0.
2. Timed-control head+c=0 and tail+10=0.
3. Vtable+0=`513514`.
4. Availability word+78=0.
5. Global volume table at `541178`,101 words for indexes0..100, through original `4b3c80`.

It **preserves +14, +7c and every other heap word**. The original table initializer computes each finite value through `4b3b90`/CRT math; native copies the frozen verified `AudioEvents` values through the recovered finite101-store loop. Full original table/CRT execution and all mutable-global bytes are compared. This does not claim to recover `4b3b90` for arbitrary external arguments. A host zero allocator is an explicit native allocation profile; these exact constructor stores do not establish original zero heap.

Manager+14 is the **actual DirectSound COM device identity**. Manager+78 is an availability word, set exactly1 by successful startup and0 by shutdown; it is not the COM pointer. Manager+7c is the last multimedia-clock word consumed by frozen ambient manager updates. Successful startup sets +7c=0 immediately before +78=1. No lifecycle entry reads timeGetTime or substitutes the game/stage/animation clock. Reserved +18..74 words are preserved by these bodies; no invented capabilities initialization is applied.

## Startup and failure ordering

`4b47e0` passes stdcall DirectSoundCreate wrapper `4f4480` the exact arguments `(0,manager+14,0)`. `4f4480` is the original import trampoline to IAT slot `546864`. The physical operation can update the output word even when returning a nonzero HRESULT. The source normalizes any nonzero HRESULT to failure and returns0 immediately, without reporting, releasing or changing +78/+7c itself.

On creation success, it reads the current device+14 and calls COM vtable+18 with `(device,hwnd,cooperativeLevel)`. Any nonzero HRESULT is converted to boolean1 for diagnostic `4b4ed0(53228c,27d,1)`. It then **rereads manager+14 after reporting**, calls that current device's IUnknown Release+8, and returns0. The source does not clear device+14, availability+78 or clock+7c in this failure path. This fresh reread is preserved when the report callback changes the device pointer.

Success writes +7c=0, then +78=1, and returns1. Startup does not guard against an already initialized manager or release the old device before calling DirectSoundCreate again. Retained success/restart/failure cases preserve these effects: a failed repeated startup can leave the old nonzero availability word intact, and the device output pointer reflects the physical service's writes. This source behavior is recorded, not replaced with a safer invented reset.

## Stop, shutdown and ownership

`4b4b40` checks manager+78 once at entry. For each resource in current head order it calls `4b3e30(pool)`, then owned `4b4670(pool)`, then reads pool+4 to obtain the next resource link. `4b4670` reads pool+10→manager+78 once, visits its voice-list head at pool+30, calls `4b3e30` on each duplicate, and reads voice+4 **after** the callback. `4b3e30` is the frozen ambient raw Stop wrapper and rechecks the current manager availability itself. Stop failure does not abort either loop. No resources/list nodes/voices/timed controls are deleted by these stop loops.

`4b4860` checks availability at entry. If nonzero, it obtains manager+4 and calls `4b4ae0(manager,pool)` where pool=head-4. After each callee it **reloads manager+4**, rather than using a cached next pointer. When no resource remains, it reads current manager+14 and calls IUnknown Release+8 on that device. Only after release does it set +78=0. It preserves device+14, last clock+7c, vtable and other words. With availability0 it bypasses the list and COM release and still writes +78=0.

The resource callee is frozen `AudioPCMTransfer`:

- Cancel every timed-control node associated with this resource, regardless of its type, without invoking finalizers.
- Release/clear the source buffer, unlink the resource, release/unlink/free duplicate voices in current order, then free the pool.
- Preserve unrelated controls. No physical Stop is inserted into destruction.

The outer manager destructor does not call `4b4c10` to finalize arbitrary orphan controls. A manager with no resource list can retain a nonempty timed-control list through shutdown. Resource deletion cancels only matching nodes. The suite verifies mixed controller types0/1/2/FFFF/FFFFFFFF and unmatched orphan lists. A resource appended by the final device Release callback remains because the source has already exited the resource loop; final availability still becomes0.

`4b4790` writes vtable513514 and calls shutdown only when availability is nonzero. It has no hidden all-resource stop or generic-list zeroing. `4b4770` then frees the raw manager only if the supplied flag's low bit is1 and returns its original token. The destructor leaves the manager vtable513514; it does not overwrite a guessed base vtable or null the device word.

## C11 adapter and native-host recipe

`claw_audio_manager_lifecycle_entry(fn,receiver,args,count,context,dependency,user,result)` returns native completion/support separately from source EAX. Only constructor, startup and deleting destructor have meaningful source returns. Other entries are source void functions and write native result0; an accidental machine-register return is not exposed as behavior. Exact stack counts are0 except deleting destructor1 and startup2. Unknown addresses return native0 without fault; invalid ABI yields fault2. Fault1 denotes missing span/service. Fault3 denotes a traversal bound prefix, not source success.

The context contains the existing raw `ClawSceneActorHost`, `maximumTraversal` and `fault`. Zero maximum uses65536; the guard is a portable extension. Host lookup must supply the writable manager32-word block and, for constructor/table initialization, the original writable `541178`101-word global span. Device/interface and vtable tokens must resolve to their true raw fields. The optional original immutable image map can supply raw vtable identities for composed frozen callees. No wall-clock callback is called by the owned lifecycle routines.

The rich dependency call preserves function identity, receiver, up to six original arguments, `deviceMethod` and optional outputWord. DirectSoundCreate retains all three original arguments including raw manager+14 output token; `outputWord` points at that exact host word. COM calls have receiver0 and explicit interface-token args0, with function identity read from the current vtable. `deviceMethod` identifies +18 SetCooperativeLevel or +8 Release. Diagnostic calls retain cdecl function4b4ed0 and all three args. Allocation/free remains host transport; deleting destructor uses scene.free with the original manager identity.

Route `4b4ae0` through frozen `claw_audio_destroy_resource`, constructing its context from manager+4/+8, +c/+10, +14 and +78. Its resource-context shadow fields must be synchronized into the raw manager at observable service boundaries and after completion. The frozen PCM module's stable-manager/valid-source-pool restrictions continue to apply; arbitrary mutation of that manager inside a physical Release callback is outside that callee's proven contract. The outer root's fresh-pointer/list behavior is separately tested through explicitly labeled mutating callee adapters. An unchanged head after a resource service causes the original outer loop to repeat indefinitely; native reports fault3 at the exact tested prefix rather than silently clearing or skipping it.

Route `4b3e30` through frozen `claw_ambient_audio_backend_entry`. The owned pooled stop loop is exposed as4b4670, and whole4b4b40 composes it directly. The rich call shape intentionally aligns with the frozen ambient API's function/receiver/args/method/output fields, but use a correctly typed adapter rather than assuming the C context types are interchangeable.

Physical DirectSound device creation, HWND/cooperative-level mapping, COM Release/Stop, audio buffer allocation/Lock/Unlock and diagnostics remain transport. The API does not claim the physical Mac output has the original DirectSound driver behavior. Windows exception/SEH unwinding and unbounded corrupted-list behavior are outside normal completed-call parity.

## Differential checks

Run:

```
work/test-env/bin/python Tests/compare_audio_manager_lifecycle_runtime.py
work/audio-manager-lifecycle-agent/check-smoke.sh
```

Final oracle result: **1,840 complete original calls / 8,917 ordered full-snapshot events / 982 original instruction addresses / five failure prefixes**. Full snapshots cover192KiB heap plus192KiB mutable original globals, allocation/free history and physical/service ordering. Table initialization executes original CRT math; native table bytes and every untouched manager/global word are compared. Complete composed resource, voice, controller and PCM payload buffers are compared byte-for-byte.

Coverage includes64 seeded constructors;16 direct whole table initializers; startup HRESULT/old-availability/mutating-service matrices; shutdown/delete flags and resource-list variations; resource/voice Stop ordering and post-callback next reads; zero and nonzero gates; mixed timed-control types/orphans;40 retained constructor/startup/restart/create-failure/cooperative-failure/recovery/stop/repeated shutdown/delete histories;32 retained multiple-pool/four-voice/five-control graphs.

The joined fixture reads six actual extracted Level1 WAV files: OFCSWSTB8-22, PEGSLIDE, SOLDIER/00320005, STONEDRIP, PEGCRUMBLE and OFFICER/00340024. It composes frozen RIFF parser, source PCM resource allocator/constructor/list insertion, original split Lock/copy/Unlock, stop and shutdown. Every file is tested for successful upload plus physical CreateSoundBuffer/Lock/Unlock failures. Eight retained histories load all six pools into one initialized manager before stop/shutdown/deletion. File hashes/sizes are recorded in `work/audio-manager-lifecycle-agent/verification.json`. Physical getter values/buffer identities remain explicit fixtures; extracted archive identity versus original v1.0 assets is not asserted.

Failure-prefix tests cover unmapped constructor receiver, invalid device-vtable read, nonadvancing shutdown, cyclic resource stop and cyclic duplicate stop. Whole original heap/events are compared up to the same native traversal limit, stopping source execution before the next callback. These tests do not count as completed original calls. ABI rejection and unsupported-address behavior are checked separately.

Strict C11 smoke exercises constructor preservation, DirectSoundCreate failure, cooperative-level failure/report/release, success, repeated shutdown and deleting free under ASAN/UBSAN. Swift imports the raw token/COM context and verifies explicit ABI rejection. The worker performed no Xcode build, simulator/device or audible acceptance test.
