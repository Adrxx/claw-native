# Original ClawDialogSound servicing

`Sources/SpeechActor.h/.cpp` recover the complete original registered callback
`0x48c630`, including its image-selection callee `0x4c7970`. The registration at
`0x402103` pairs this callback with the string `ClawDialogSound` at `0x5223cc`.
These are verified entry points in the fingerprint-pinned original v1.0
`Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

The module services requests previously queued by the recovered AudioEvents
`0x48c820/0x48c8a0` helpers. It returns 1 on every path, as the original does.
All state changes use retained original actor/logic offsets and 32-bit wrapping
arithmetic. Actor and logic buffers are distinct, valid objects; pointer fields
are opaque host tokens.

## State changes and event ordering

| Logic state | Original behavior |
| --- | --- |
| 0 | OR actor `+0x40` with 1; OR `+8` with `0xc0003`; write `+0xd0=0x4000000`; select the image `GAME_EXCLAMATION`; write state 5; register this actor in global `0x53c9a4`. |
| 5 | Write global busy `0x53c9a0=0`; OR actor `+0x40` with 1. It does not clear the queued resource by itself. |
| 1001 | If the queued resource is zero or settings `+0x118` is zero, write state 5 and clear the queued resource. Otherwise write state 15, copy the queued sound pool's `+0x28` duration into logic `+0x130`, then request playback if audio manager global `0x532c0c` is nonzero. |
| 15 | If the player exists, mark busy, clear actor `+0x40` bit 0, follow the player's position/layer, update the duration, and transition to state 5 with the queue cleared when it expires. With no player, the callback leaves this state and all associated fields unchanged. |
| 29 | Clear global `0x53c9a4`. It does not clear busy, stop playback, or compare registration against this actor. |
| All others | Return 1 with no side effects. |

The 1001 callback does not mark busy or show the exclamation image. Those writes
occur on the following state-15 callback. Even a zero-duration sound receives a
play request first. Its next state-15 callback shows the image, marks busy, and
transitions to state 5; the following state-5 callback hides the image and clears
busy. Expiry itself does not stop the voice through an audio API.

The same delay affects queue acceptance: a second unforced request can replace
the queue after state 1001 has played a sound and before the first state-15 tick
sets busy. Forced requests can replace active speech at any point allowed by
the queue helper. Voice overlap/reuse is determined by the external voice-pool
selector, not this callback.

## Image initialization

The original name token is `0x52c580`, containing `GAME_EXCLAMATION`. This is an
image registry lookup, not an ANI selection. `0x4c7970` calls `0x4f6286` on
actor `+0xc -> scene +0x10 -> registry +0x10`. The portable context provides the
final registry token and `resolveImage` returns resource metadata:

- Actor `+0x170` receives the resolved image token, including zero on failure.
- If resolved, actor `+0x16c` receives image `+0x64`, the first index.
- If signed first index is at most signed last index at image `+0x68`, actor
  `+0x174` receives `image +0x14 -> frame array[first index]`.
- If resolved but the signed range is empty, `+0x174` is zero.
- On lookup failure, previous `+0x16c` and `+0x174` values remain intact.

The resolver receives the flags already written by state 0. Image fields,
state 5, and global registration are written after resolution returns. Tests
compare complete buffers at the resolver boundary as well as after return.

## Playback parameters and duration

For a queued resource, original sound `+0x10` is the voice-pool token and pool
`+0x28` supplies the duration. The context exposes these two immutable metadata
values. Refresh both whenever the actor's queued resource changes. Duration
comes from original resource metadata; an arbitrary host timeout is not an
equivalent substitute. The calculation used to initialize pool `+0x28` is not
recovered here.

Playback calls original `0x4b45f0` with:

```
pool = queuedSound +0x10
volume = settings +0x12c + 20   // wrap to uint32, interpret as signed
if signed(volume) >= 100: volume = 100
pan = 0
pitchPercent = 0
looping = 0
```

The callback does not read master-volume global `0x532c10`, query voice status,
or react to the playback return value. Audio manager absence suppresses only
the play request; state 15 and its duration are still written. Settings
`+0x118=0` rejects the request entirely. `speechEnabled` and `speechVolume` are
portable API names for those observed settings fields; their broader settings
UI/serialization semantics remain outside this recovery.

Unsigned duration is updated by stage milliseconds at global `0x53720c`:
subtract delta when delta is less than remaining duration, otherwise write
zero. Animation delta `0x5430c4` is not used. Zero delta preserves positive
duration; equal delta expires it. No fixed frame rate is introduced.

## Player following and death gates

State 15 copies player `+0x4c` into actor X and computes actor Y as player
`+0x50 + +0x11c - 30`, with unsigned wrapping. Actor layer `+0x64` follows
player layer plus one; only a changed layer sets actor `+8` bit `0x20000`.

Player logic state 5004 or 5005 forces duration to zero before the regular
duration update. State 28 does not expire existing speech. This differs from
the queue helper's gate, which rejects unforced requests in all three states
28, 5004, and 5005. The queue helper also rejects unforced requests when busy is
nonzero. Forced requests bypass these two gates but still require a sound,
registered speech actor, and its valid logic object. Queue acceptance is
independent of audio-manager availability.

## Native integration contract

`claw_speech_actor_update` takes raw `ClawSpeechActor` buffers, a
`ClawSpeechContext`, and two host callbacks. The context carries the current
actor token, registration/busy globals, settings fields, player snapshot,
stage delta, and current queued resource metadata. `resolveImage` adapts the
external registry service; `play` adapts the recovered AudioEvents voice-pool
boundary. No native UI, audio backend, or asset extraction is implemented by
this module.

When connecting to AudioEvents, synchronize its queue result into actor
`+0x184` and logic `+0x1c`, and synchronize registration/busy from this module
before the next queue request. Do not set busy eagerly on queue acceptance or
clear it eagerly on expiry. Use the callback's state machine and actual game
dispatch order. Top-level actor scheduling, object construction/destruction,
rendering of the image, resource registry loading, original sound-duration
calculation, voice selection/reuse, mixer behavior, and PCM identity are not
proven by this module's routine comparisons.

## Verification

Run `work/test-env/bin/python Tests/compare_speech_actor.py`. It compiles only
its private `work/speech-agent/libSpeechActor.dylib`, linking the frozen
AudioEvents source read-only. The original executable is fingerprint verified
and executes the whole callback, image helper, queue helper, and, in chained
tests, recovered voice playback/setters through the DirectSound COM boundary.
The original 101-entry volume-table initializer and CRT math execute in full.

Checks include 8,000 generated complete actor/logic comparisons, complete
unchanged player/settings/scene/resource/pool/image buffers, callback-time
buffer snapshots, and exact ordered image/audio arguments. There are also
1,600 initialization/queue/play/follow/expiry/delete chains, including queue
replacement before busy is set, forced replacement during playback, complete
voice buffers, and DirectSound failure/error ordering. Directed cases cover
death-state distinctions, absent-player freezing, signed volume overflow,
disabled settings/manager, and missing-image retention.

Only registry resolution, voice selection, DirectSound COM methods, and error
reporting are adapted in the playback chains. Generated arbitrary volume-word
tests adapt the public play boundary because the original lower audio routine
indexes a volume table without bounds checking; the native lower wrapper's
valid-domain contract is documented separately in `audio-events.md`.
