# Original ambient list, voice and fade backend

`AmbientAudioBackendRuntime.h/.cpp` recovers the raw source boundary needed by frozen `SoundTriggerLogicRuntime`. Original input is the unmodified v1.0 `Original/claw10/CLAW.EXE`, SHA256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Private Ghidra outputs, exact numeric capture, verification report and native smoke live in `work/ambient-audio-backend-agent/`. No gameplay reference-source code or guessed immediate fade was used.

The source module composes the already verified `AudioEvents` initialized volume/pan table. It does **not** delegate ambient play to `claw_audio_play_pool`: original4b3dc0 uses its raw resource's existing DirectSound buffer directly, whereas4b45f0 performs separate4b4430 selection. Frozen `AudioResourceRuntime` creates these same14-word raw resource/voice objects, and frozen `AudioPCMTransfer` remains the separate source PCM upload layer. Physical DirectSound→CoreAudio transport, clock transport, allocation/free and diagnostic reporting remain explicitly supplied services.

## Stable C11 API

`claw_ambient_audio_backend_entry(function,receiver,args,count,context,dependency,user,result)` returns native support/completion; meaningful original EAX is written separately. Receiver is actual thiscall ECX, except cdecl4b3bf0 and stdcall4f5aa8 use receiver0. Unknown entries and invalid counts never fabricate a successful original return.

Context owns a frozen `ClawSceneActorHost`, native-only maximumTraversal and fault. Each rich service provides actual original function identity, receiver, six scalar argument slots, and optional bufferMethod/outputWord. DirectSound COM services use receiver0, retain the interface token as arguments0 and resolve function from its actual vtable. Getter stack output-pointer transport is represented by synchronous `outputWord`; its original pointer is omitted from logical argument count. Do not retain that pointer after the callback returns. Its initial word is the source voice token, matching the original `push ecx` local, including failure-with-output mutation profiles.

Clock service function `0x546df0` identifies the **timeGetTime import slot**, not GetTickCount, stageDelta, animationDelta or frame-count timing. A rich dependency receives that exact slot identity; with no dependency the explicit scene.readClock fallback is used. DirectSound method offsets are GetVolume18, GetStatus24, Play30, SetVolume3c, SetPan40, SetFrequency44 and Stop48. Original report service4b4ed0 receives cdecl `(0x53228c,line,result)`. Volume/pan/play/stop/get failures report boolean1; frequency reports the raw HRESULT. The physical report implementation is not claimed recovered here.

Fault1 indicates missing raw span/service, fault2 unsupported original unchecked table/numeric/ABI domain, fault3 a source nonadvancing/runaway list. Native checks protect the host and do not replace a source trap or infinite loop with original successful behavior. maximumTraversal0 uses65536; ordinary valid ambient profiles are far smaller.

## Raw object graph

- Voice/resource is14 words (`0x38`): +c DirectSound interface token, +10 audio-manager token, +14 playback flags, +18 base frequency, +24 successfully applied current frequency.
- Audio manager must provide at least32 words (`0x80`): +78 is the actual device availability/nonzero identity, +c/+10 intrusive control-list head/tail, +7c last multimedia-clock word. This API does not recover the outer manager constructor or assert arbitrary zero heap is its source initialization.
- A timed volume controller is10 words (`0x28`), vtable513520 with tick4b4d80/finalizer4b4df0. +4/+8 intrusive next/previous node identities, +c kind1, +10 voice, +14 stop-at-completion, +18 target percentage, +1c current percentage, +20 duration, +24 creation time. List links address **controller+4**, not its base.
- Completed/cancelled controllers are unlinked, their vtable becomes513518, then their entire allocation is freed. Slots0/4 of the base513518 table are4a3910; manager update/finalize invokes the live derived table before changing it.
- CPtrList is7 words: +0 preserved vtable, +4 head, +8 tail, +c count, +10 free-node head, +14 Cplex block head, +18 block-size count. SoundTrigger already owns its original4f5133 constructor (vtable51000c/default ambient block-size10); it is not duplicated.
- Each CPtrList node is12 bytes: next, previous, opaque data. Each Cplex allocation is `4 + blockSize*12` with its first word pointing to the previous block. Nodes start block+4; source creates the free chain by walking backward through the block, yielding ascending allocations.

Root integration can materialize manager/interface/vtable tokens using its existing raw heap and physical-buffer map, pass frozen source resource/voice tokens, and copy actual pointer-list metadata unchanged. Wire the original SoundTrigger dependencies4f51c5/5212/5172 and4b3dc0/3e30/3f40/3fe0/4110/4b4b80/4b4c10 to this module. Populate actual manager/interface fields from the recovered caller or an explicitly labeled physical/native allocation profile. Do not substitute a selected playback voice or a broad stopAll for the raw controller operations.

## Complete recovered entry inventory

| Entries | Actual stack ABI / behavior |
| --- | --- |
|4f51c5|thiscall(data): AddTail and original pooled allocation |
|4f5212|thiscall(node): unlink and FreeNode |
|4f5172|thiscall(): RemoveAll/reset before block destruction |
|4f5692|thiscall(previous,next): NewNode |
|4f56e7|thiscall(node): FreeNode, release blocks when count reaches0 |
|4f5aa8|stdcall(pointerToBlockHead,count,stride), RET12: Cplex allocation/header |
|4f5ac8|thiscall(): ECX is first Cplex block; whole block-chain free |
|4b3dc0|thiscall(volume,pan,pitchPercent,loop): complete play wrapper |
|4b3d80,4b3e30|thiscall(): raw Play/Stop wrappers |
|4b3f40,4b4110,4b41b0|thiscall(value): volume/pan/pitch parameter setters |
|4b3ef0,4b40c0,4b4160|thiscall(rawDSvalue): exact raw volume/pan/frequency setters |
|4b3ec0|thiscall(loop): playback flag bit1 setter |
|4b3f70,4b3e70|thiscall(): GetVolume / GetStatus-playing-bit wrappers |
|4b3bf0|cdecl(rawVolume): source inverse mapping over documented numeric domain |
|4b3fc0|thiscall(): GetVolume then inverse mapping |
|4b3fe0|thiscall(target,duration,stop): whole immediate/timed selection |
|4b4c80|thiscall(voice,kind): source cancellation scan |
|4b4d00|thiscall(target,start,duration,voice,stop): whole timed controller constructor |
|4b4d80|thiscall(now): source controller tick |
|4b4df0|thiscall(): source controller finalizer |
|4b5210,4b5270|thiscall(node): intrusive control insertion/removal |
|4b4b80,4b4c10|thiscall(): manager update/finalize |

The ordinary play wrapper gates manager+78, executes volume→pan→frequency→loop-bit→Play in that order, and only then combines their boolean results. It does not short-circuit later calls when an earlier physical setter failed. Each nested source setter rechecks the current device gate. Pitch multiplication wraps32 bits before signed division100, then the resulting unsigned frequency is clamped101..99999. Only successful SetFrequency writes voice+24. Pan uses the same actual initialized logarithmic table as volume, mirrored by sign. Successful GetStatus returns its output bit0, not a buffer-pointer bit (the Ghidra decompile of this stack local is misleading; actual assembly and full comparisons establish this).

Timed volume first cancels controllers of kind1 for the same voice. Duration0 applies the volume setter and returns1 regardless of its physical success (while native faults remain failures); stop argument does not cause an immediate Stop here. Positive duration allocates0x28, calls GetVolume/inverse, stores the controller fields, samples timeGetTime and inserts at the manager's list head. Allocation0 returns original false after prior cancellation effects. It does not change the current volume immediately.

Inverse conversion first takes the signed magnitude and performs **integer division100**, so a nonzero magnitude below100 takes quotient0. Original CRT pow then evaluates the quotient-based expression and original FTOL returns its low32 word; positive raw values negate the result. The finite valid DirectSound volume domain−10000..0 has quotients0..100. Source integer outputs for all101 quotients are embedded as original numeric data, generated by executing the complete4b3bf0/CRT bodies under original53-bit x87 control. The generator/hashguard and captured JSON are private. Comparisons also cover both signs and remainders within±10099. Larger magnitudes/INT_MIN are a declared native fault2 domain rather than a guessed CRT approximation. Source inverse0 is100; small nonzero negative values also produce100.

Controller tick computes unsigned `(now-start)` and caps it to unsigned duration, setting the completion flag at `elapsed>=duration`. It then obtains current playback status. For a playing voice, the interpolation numerator is **wrapped32 `(target-startVolume)*elapsed`**, followed by signed IDIV duration and addition of startVolume. The mapped setter executes even at the terminal elapsed value. Nonplaying or completed controls optionally Stop if stop flag is nonzero. A physical SetVolume failure does not retain a completed controller. A nonplaying controller ends without a volume write, but can still Stop. Division-by-zero/INT_MIN÷−1 traps and out-of-range table indices remain explicit native fault2 prefixes.

Manager update returns0 without reading a clock if its list is empty. Otherwise it samples timeGetTime once and updates only when **unsigned now>manager+7c**, including the original stalled behavior across clock wrap until that comparison becomes true again. It caches each next control before calling its tick; completed controls are removed and freed in source order. Its return remains1 even when that pass empties the list. The finalizer entry4b4c10 calls each live controller's virtual+4 first, then unlinks/changes base vtable/frees; finalizer4b4df0 restores target volume for playing stop0 controls, and Stops playing stop!=0 controls. It is not an unconditional physical stop of every resource.

Cancellation4b4c80 does **not** invoke controller finalizers before free. Voice mismatch advances, and kindFFFF acts as a wildcard. The original instruction at4b4cb7 skips the4b4ce7 advance on a kind mismatch, returning to4b4c9b with the same object. This real nonadvancing branch is preserved as fault3 at that source-state prefix, not repaired into a different scan. Valid ambient controllers have kind1, so ordinary same-class lists remain finite.

## Evidence and verification scope

Run `work/test-env/bin/python Tests/compare_ambient_audio_backend_runtime.py` from the repo. It builds a private dynamic library, checks the EXE hash, executes original instructions and compares whole192KiB token heaps,192KiB original image/global spans, every ordered physical/clock/heap snapshot, allocation/free identities, clock cursor, meaningful EAX and retained state. Physical COM calls, allocation/free, multimedia clock, report transport, and pure CopyRect/SetRect are the only adapters. All listed source list/voice/fade bodies execute as original instructions. Owned source helpers are not stubbed.

Standalone coverage includes pooled block sizes1/2/3/10/11/32, arbitrary data, retained head/middle/tail removal, node reuse and block release, every inverse quotient plus sign/remainder cases, all seven COM failure channels (including HRESULT80004005/FFFFFFFF), caller mutations/read ordering, zero/positive/large unsigned durations, same-voice cancellation, multiple voices/controllers, terminal stops, repeated/backward/wrapped clock samples and allocation failure after cancellation.

Frozen `SoundTriggerLogicRuntime` is genuinely composed into the new native backend/list, and its entire corresponding original caller graph runs without replacing those dependencies. All15 actual Level1 WWD ambient records (2 AmbientSound,4 GlobalAmbientSound,9 SpotAmbientSound) pass startup, center trajectories, manager/frame updates and cleanup; spot30 removes its real pooled-list node. Actual record words and hashes come from the independently verified source inventory; rebuilding their raw records checks each SHA256 before feeding frozen WorldObjectRuntime. Resource identity/DirectSound transport remains a declared fixture, so this does not claim audible device acceptance or a full original resource loader.

The joined oracle compares caller globals, stageDelta and original random-call ordering as well as backend clock ordering. Nonambient speech/gameplay bodies remain disjoint frozen services; no broad playback/voice selection replacement is introduced.

Final exact counts are in private `verification.json` and `verification.log`. Failure-prefix results are separate from successful whole-call counts: null Cplex allocation, zero block size, direct/rebinding kind-mismatch loops, zero fade duration and signed division overflow stop before original invalid dereference/trap or at a repeated nonadvancing instruction. They are not labeled source normal returns.

Private native smoke validates pooled allocation/release and timed→manager update→physical Stop under ASAN+UBSAN. The header is warning-clean C11 and imports through Swift. This worker performed no Xcode/UI/device test.
