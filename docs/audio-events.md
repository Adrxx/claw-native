# Original audio routing and parameter dispatch

`Sources/AudioEvents.h/.cpp` recover original v1.0 direct playback helper
`0x004208e0`, name playback helper `0x00420910`, spatial helper `0x004c88e0`,
speech-name routing `0x0048c8a0`, and speech queue helper `0x0048c820`.
The native voice dispatch also implements `0x004b45f0` after an explicitly
external voice-selection boundary, plus its volume/pan/frequency/loop/play
setters. No native platform playback is implemented by this source.

The executable is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Private analysis logs/decompilation, sound metadata index, dylib, and test output
are under `work/audio-agent/`. The analysis uses the worker's private Ghidra
project; original files and shared project/App resources remain unchanged.

## Routing API

`ClawAudioRouting` represents the original audio manager's nonzero global at
`0x532c0c`, master volume word `0x532c10`, spatial default fields, and speech
queue state. **The master volume word is not a positional coordinate.** Earlier
animation-preview APIs called it `globalAudioPosition`; that label should not
be used to infer behavior.

`claw_audio_play_direct` forwards four request words to the `host.play`
voice-pool boundary when the manager exists. It does not scale master volume.
Callers such as the ANI updater pass the master-volume value themselves.

`claw_audio_play_name` respects the supplied registry's disabled word first.
If enabled it always resolves the name before checking audio-manager presence.
A resolved resource and nonzero audio manager play with master volume and zero
pan/pitch/loop values. `ClawAudioHost.resolve` corresponds to `0x4f6286` and
returns both an opaque resource token and its voice-pool token. `host.play`
corresponds to `0x4b45f0`; its ordinary return is preserved.

`claw_audio_play_spatial` preserves the original signed fallback tests and
wrapping integer arithmetic. Its four original arguments are source x,
reference x, clamp distance, and pan distance. Nonpositive reference x is
replaced by the original default reference field. Nonpositive clamp distance
uses scene width shifted left two bits. Nonpositive pan distance uses signed
scene width divided by three.

The default field paths are retained as explicit injected values:

- Reference: sound resource `+0xc` → scene `+0x24` → collision manager `+0x5c`
  → plane `+0x84`.
- Width: sound resource `+0xc` → scene `+4` → object `+0x10` → width `+0x10`.

The camera/reference interpretation of these fields is not independently
verified here. A preview's camera center must not be labeled the original field
without that integration evidence.

Spatial offset is signed and clamped by the smaller signed distance. The
`INT_MIN` absolute-value wrap quirk is retained. Offset multiplied by `100`
wraps at 32 bits before signed division by pan distance. Master volume `100`
passes through unchanged; other volume values are multiplied by the original
single-precision `0.01` constant and then by `100`, using the recovered CRT's
53-bit arithmetic and integer truncation. This makes spatial master volume
`50` become request volume `49`, whereas direct playback retains `50`.

Original x86 division by zero has no return value. The portable spatial API
returns zero and exposes `arithmeticFault = 1`; its signed-division overflow
guard exposes `2` if reached. These diagnostic results are an explicit host
extension. Directed tests observe the original divide interrupt for scene
widths `0`, `1`, and `2` with default pan distance.

## Speech queue

`0x48c8a0` is **not** immediate audio playback. It resolves the name through the
speech actor's scene audio registry and calls `0x48c820`. The queue helper
requires a resource token, speech actor, and speech logic pointer. With force
zero it also rejects a nonzero global speech gate `0x53c9a0`, or player logic
states `28`, `5004`, and `5005`. Nonzero force bypasses those two gates.

An accepted request writes the resource token to speech actor `+0x184` and
sets its logic state to `1001`. It does not call the playback boundary and is
independent of master audio-manager availability at this stage. Speech-name
routing does not apply the generic registry's disabled-word check.

`claw_audio_queue_speech` and `claw_audio_queue_speech_name` reproduce this
state transition. The later speech-actor state machine, queue service timing,
completion detection, and speech animation remain unrecovered. Native playback
on request arrival would be a preview shortcut, not proven original timing.

## Voice dispatch and platform boundary

`claw_audio_play_pool` implements the complete post-selection dispatch at
`0x4b45f0`. `ClawAudioBackend.selectVoice` still adapts `0x4b4430`, including
voice reuse, allocation, list reorder, and default-parameter restoration. Those
operations are not inferred by the native API. Device availability is stable
for a tested dispatch; concurrent device-state changes inside a host callback
remain outside the comparison contract.

After selection, the original calls all parameter operations in this order,
including after an earlier failure:

1. SetVolume, DirectSound vtable offset `0x3c`.
2. SetPan, offset `0x40`.
3. SetFrequency, offset `0x44`.
4. Set/clear playback flag bit `1` according to looping.
5. Play, offset `0x30`, with reserved arguments `0,0` and stored playback flags.

The volume table contains all 101 entries produced by the complete original
initializer `0x4b3c80` and its CRT math helpers. Native constants avoid host
libm differences and every entry is compared to original execution. Values
include `0 → -10000`, `1 → -6643`, `25 → -2000`, `50 → -1000`, `100 → 0`, in
DirectSound hundredths of a decibel. Pan uses the reversed table at index
`100 - abs(pan)` and negates it for nonnegative pan.

Pitch percent multiplies the voice's base frequency with 32-bit wrapping,
divides the signed result by `100`, adds base frequency with wrapping, and
clamps the unsigned result to `101..99999`. A successful frequency call updates
the voice's current-frequency word at `+0x24`; failure leaves it untouched.

`ClawAudioBackend.directSound` adapts only platform COM method calls and returns
an HRESULT word. Success is zero. `report` adapts original error reporter
`0x4b4ed0`; volume/pan/play failures report normalized result `1`, with codes
`0xaf`, `0xf6`, and `0x5f`. Frequency reports its actual HRESULT with code
`0x12a`. Final success requires all four operations to succeed.

The original performs unchecked table reads. Portable pool dispatch accepts
volume `0..100` and signed pan `-100..100`; invalid indices explicitly return
zero after selection. This extension is not claimed to match out-of-domain
original memory reads. Upper routing comparisons still test arbitrary request
words against a recorded playback boundary.

DirectSound mixing, attenuation, stereo law, sample-rate conversion, voice
selection/polyphony, buffer position, and real-time playback are not verified
by the platform adapters. An AVFoundation backend needs separate validation;
audible output alone cannot prove identical PCM or playback timing.

## Asset observations

The fingerprinted CD-rip REZ index contains no WAV/MP3/OGG entries found by the
read-only index inspection. The installer instead carries compressed sounds
under `Original/claw-rip/files/App_Data/Sounds/`. Observed examples are
`CLAW/SOUNDS/LAND.mp3`, `CLAW/SOUNDS/1054.mp3`, and
`CLAW/SOUNDS/1110035.mp3`. These are available preview assets, but their lossy
encoding and CD-rip provenance do not establish original PCM identity.
The exact registry loader's name-to-file mapping is not recovered here.

## Verification

Run:

```sh
work/test-env/bin/python Tests/compare_audio_events.py
```

Passing coverage includes 6,000 generated direct/name/spatial/speech-queue
calls, full speech actor/logic buffers, ordered resource/play arguments, all
101 volume table values, directed spatial rounding and queue/disable gates,
three original divide-by-zero boundaries, and 5,000 voice dispatches with
success/failure HRESULTs and exact COM/error ordering. Full voice words and
frequency/loop mutations are compared. Registry resolution, voice selection,
DirectSound methods, and error reporting are explicit adapters. All recovered
routing and parameter-setting instructions execute in the original harness.

This is audio-event/control-flow evidence. It does not establish completed
sound playback or whole-game audio parity.
