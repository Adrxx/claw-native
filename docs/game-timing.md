# Original v1.0 clock and pacing recovery

`Sources/GameTiming.h/.cpp` recover the complete clock helper at `0x004b82f0`,
its rate-reset helper `0x004b83a0`, clock-reset helper `0x004b83d0`, and busy-wait
helper `0x004b83f0`. They also expose the clock-only portions of manager
construction `0x004b8240`, stage publication `0x00428b60`, actor animation clock
refresh `0x004c8fc0`, and replay assignment `0x0042ae40`.

The binary is `Original/claw10/CLAW.EXE`, SHA-256
`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Recovery uses verified instruction entry boundaries and a private Ghidra project
under `work/timing-agent/ghidra-project`; no input executable is modified.

## Clock behavior

All time words use wrapping 32-bit milliseconds. The original imports
`timeGetTime` at `0x00546df0`. There are two independent sampling paths:

| Representation | Original words | Meaning |
| --- | --- | --- |
| `ClawClockState` | `0x541328..0x541338` | Current sample, elapsed milliseconds, prior paced-frame sample, countdown, countdown reload |
| `ClawTimingManager` | manager `+0x18..+0x28` | Reported frame rate, pacing configuration, frame counter, count-window start, minimum frame duration |
| Stage `ClawFrameClock` | `0x537208`, `0x53720c` | Main clock sample and elapsed milliseconds |
| Accumulated stage time | `0x537210` | Wrapping sum of main elapsed milliseconds |
| Animation `ClawFrameClock` | `0x5430c8`, `0x5430c4` | Separately sampled actor-dispatch clock and elapsed milliseconds |

The main helper samples the clock, computes elapsed time, and updates the
countdown before optional pacing. When the countdown starts at zero it reloads;
otherwise it decreases by elapsed time or becomes zero. Its use by gameplay
callbacks remains a separate recovery task. Startup writes reload `33` at
`0x004257a5`; this value alone does not establish a fixed frame rate.

Pacing is enabled only when the configuration word is positive as a signed
32-bit integer. A negative word disables pacing. A nonzero prior paced-frame
sample causes a second read; if elapsed time is less than the unsigned minimum
duration, the helper calls the original wait algorithm. It then takes another
sample to record the paced-frame start. Frame elapsed time remains the value
sampled **before** pacing. It is not recomputed after waiting.

Every frame increments the wrapping counter. Once unsigned elapsed time since
the count-window start is at least 2,000 ms, the reported rate becomes
`frameCount >> 1`, the counter is cleared, and the window start gets a fresh
clock read. This does not divide by actual elapsed seconds when frames stall.

The wait routine performs busy polling, without any `Sleep` call. It takes an
initial sample, forms a wrapping deadline, then reads while the sample is
**less than or equal** to that deadline. A zero-duration wait still polls past
the initial sample. If the deadline wraps below the initial sample it returns
immediately. A deadline of `0xffffffff` cannot be exceeded by a 32-bit sample,
so that original edge case cannot terminate normally. The recovered routine
preserves these semantics rather than substituting host sleeps.

The stage clock is published and accumulated before the `0x00428b60` pause
check. A pause suppresses the later game callback but does not suppress clock
sampling/publication. The separate animation clock refresh occurs only when
the actor dispatcher receives a nonzero refresh argument; a zero argument
preserves both words. Replay assignment supplies both clocks directly without
reading host time.

## Integration contract

Inject a `ClawTimingHost` with a nonnull `read` callback returning a wrapping
monotonic millisecond value. `observeWait` is optional passive instrumentation;
it records each requested wait duration and must not advance clocks or perform
host sleeps. The original external dependency adapted in comparisons is only
`timeGetTime`. No original clock helper or busy-wait instruction is stubbed.

`claw_timing_initialize` executes constructor timing semantics: disable pacing,
clear the rate counter, sample its window start, set reported rate to
`0xffffffff`, sample the main clock, and clear delta/prior paced-frame start.
It leaves minimum frame duration and countdown words untouched, as the original
constructor does. Initialize those words deliberately when constructing a host
instance; portable structs contain no x86 vtable or host-object pointers.

For a prototype using UI callbacks, keep `pacingEnabled = 0`; sample and publish
elapsed time on each callback. This uses the recovered clock arithmetic while
leaving the UI callback schedule externally determined. It is not proof of the
original main-loop schedule. Original-compatible pacing should run on a
dedicated game execution path once its event/message-loop integration is
recovered.

`claw_timing_update_animation` does not run actor logic. Its original dispatcher
walks an ordered actor list, consults `0x004c9860`, handles deferred callbacks,
then applies deletion and reorder queues. The portable clock API deliberately
does not claim those actor lifecycle operations. Input polling, Windows message
processing, render ordering, application-focus pause/resume behavior, the
nonpaused stage callback, and host/device real-time scheduling remain outside
this recovery and validation scope. No original pacing setter is claimed;
manager words are explicit injected configuration.

## Validation

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_game_timing.py
```

The test compiles the portable implementation into its own native dylib under
`work/timing-agent/`, executes original x86 instructions with the existing
hash-pinned Unicorn harness, and supplies identical scripted clock samples to
the original import and native callback. It compares state, clock sample
sequence, sample count, and wait requests. Generated helper tests also compare
manager/global state at every external clock read, checking observable write
ordering.

Passing cases:

- 6,000 generated complete clock updates, including unsigned time wrap, signed
  pacing words, large unsigned minimum durations, countdown boundaries, and
  frame-counter overflow.
- 1,500 rate resets and 1,500 clock resets.
- 500 complete original constructors versus portable timing initialization.
- 12,000 chained paced frames using repeated clock samples, multiple minimum
  durations, pacing enable/disable transitions, and uptime wrap.
- Eight directed waits covering inclusive deadlines, zero duration, immediate
  wrap return, and repeated equal clock samples.
- 1,500 animation clock updates through the complete original dispatcher with
  initialized empty actor/deletion/reorder lists. Collection helpers execute;
  initialization of populated actor lists and actor callbacks are not tested.
- 1,500 stage publications through the paused original frame entry.
- 1,500 replay clock assignments.

The comparison reaches 330 distinct original instruction addresses. This is
routine-level clock evidence, not whole-game or real-device behavior parity.
