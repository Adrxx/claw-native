# Original game-frame services

`Sources/GameFrameServices.h/.cpp` recovers finite control flow surrounding the frozen frame/stage/runtime bodies. The oracle is SHA256-pinned original v1.0 `CLAW.EXE` (`350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`). No reference gameplay implementation was used. No new original input, camera, player damage, or death-command calls occur in this graph; those remain composed by the frozen frame/stage modules at their actual boundaries.

| Entry | Recovered body |
|---|---|
| `4774f0` | Saturating pose-send timer, wrapped peer-count interval, exact five-word packet, four-word pose comparison, unchanged-pose timeout, broadcast/target selection |
| `477840` | COM pending-message query, HRESULT election, exact `owner+14c` count, signed pending-count gate, warning timer/message/sound election, receive loop, self filtering and ordered packet-handler calls |
| `478290` | Conditional 500ms refresh timer, raw linked-list enumeration and iterator writes, in-place descending signed-score swaps, tied ranks and score/mode gates |
| `46c2c0` | Debug flag selection, ordered text concatenation, captured argument ordering, state/queue drawing gate, HDC acquisition, text color/background/font method, debug rectangle/text selection and HDC release; message-timer fallback |
| `4224f0` | Editing flag/timer expiry, CString clear boundary, empty-queue reset, unsigned timer arithmetic, signed queue-count selection, remove-head/destruct sequence |
| `46ca50` | Actual single-player virtual message-draw wrapper: timer update then exact viewport-derived rectangle and `4226b0(config,1,HDC,&rect,1)` |
| `40af90`, `4750d0`, `4bb030`, `4750e0` | Actual state/count virtual probes: 3,4,0 and `network+60` respectively |

Known probe and `46ca50` targets selected through raw vtables execute natively. They are not replaced by guessed state IDs. `composeMessages=1` composes the recovered `4224f0` body at both the fallback and single-player drawing wrapper; disabling it emits the actual call as an explicit dependency.

## Host ABI and live state

The C11 entry accepts a raw 32-bit receiver token and an argument (rank force, message delta, or HDC as applicable), a `ClawSceneActorHost`, a pointer to `ClawGameFrameServiceGlobals`, and an optional rich dependency callback. The globals map in declaration order to:

```
53720c stage delta; 537e88 player actor; 537210 accumulated tick;
537264 debug flags; 5370c8..5370d7 viewport rectangle;
53abc0..53abd3 pose packet; 52a7bc..52a7cb last pose;
52a7cc rank timer; 532c0c audio enable; 532c10 overall volume.
```

The volume semantic is deliberate: `532c10` is overall volume, not a positional audio field. The stage delta is distinct from the animation delta used in frozen actor/stage processing. Globals are mutable during callbacks: synchronize shared aliases with the parent host's actual clocks/player globals before/after routing, and expose callback mutations live. Defaults set only the composition flag; owner fields/session pointers are never initialized heuristically.

All heap access uses aligned, bounds-checked one-word/precise-span `lookup`. Network helpers require owner offsets through `c04` (at least 770 words), unlike the generic 474-word single-player frame owner. Network+18 supplies a COM object; its vtable+44/+64 methods receive the object as the first stack argument, with receiver0 in the portable service. Ordinary owner virtual methods retain their actual receiver token. The score list stores peers; peer+14 points to a cell containing the actor token. Refresh writes the original network+84 iterator while enumerating nodes. The original routine does not enforce a 256-peer bound; valid host spans are the API's limit.

`ClawGameFrameServiceCall` carries original function/receiver/arguments (up to eight), plus automatic-storage pointer masks and mutable buffers. An automatic argument pointer becomes token0 and bit `i` of `localMask`; a temporary CString receiver becomes token0 and bit8. Buffers appear in argument order then temporary receiver, followed by optional global payloads. Their physical addresses are not stable original tokens. Font/GDI calls use the original import slot as identity (`546888`, `546880`, `546890`, `546d30`). Text buffers and rectangles are valid only synchronously during the callback. Global pose packet calls retain original token `53abc0` and also expose its five words as a buffer.

Meaningful original EAX is returned for `477840` (processed count) and the four virtual probes; void routines have native diagnostic0. Native fault1 denotes missing mapped span, fault2 local text overflow, fault3 missing dependency service. Safe native fault exits are not original parity claims. Calls with automatic storage, more than four arguments, or formatting require the rich callback; simple raw calls can use `host.call` as fallback.

## Actual services still external

The following bodies are explicit dependencies, with original arguments and ordered snapshots in tests:

- Packet transmission `4e0d70(network,localPeer,0,53abc0,20)` and targeted `477790(owner,targetPeer,53abc0,0)`.
- DirectPlay-style pending/receive virtual methods, packet interpretation `477a10(owner,fromPeer,buffer,length)`, error reporting `4e10d0(52a9bc,302,error,0)`. Query result0 elects the pending count; nonzero HRESULT elects0. Receive buffer mutations and output sender/recipient/length are live.
- Message insertion `422370(config,52a9d4,2)`, named sound lookup `4f6286(soundRegistry+10,52a824,&resource)` and playback `4b45f0(resource+10,overallVolume,0,0,0)`.
- MFC CString/list primitives `4f650f`, `4f53eb`, `4f6584`, `4f6920`. Remove-head and refcount/block lifetime are not implemented by the timer body. The oracle's declared list service mutates count and returns a deterministic borrowed CString; this is an adapter profile, not a recovered queue allocator.
- CRT `4a3920` formatting and `49c860` time-to-CString formatting. Oracle formatting uses the actual literal strings/argument lists with a declared formatting adapter. Time/CString service outputs are deterministic declared fixtures. Outer debug selection/concatenation is recovered; formatter/refcount internals are not claimed.
- Owner's other virtual font/HUD implementation, `4226b0` message text layout, HDC backend and Windows text/background/color APIs. The original physical renderer/UI/font/settings/movie bodies remain services.

The exact literals include `Fps = %i `, ` Objs = %i `, ` Pos = %i,%i `, ` Timing = On ` and ` Racers = %i Msgs = %i Objs = %i `. Complete tests verify the drawn text and rectangle payloads, including signed integer conversion and both TextOut/DrawText branches.

## Startup evidence and integration

`work/game-frame-services-agent/startup-evidence.json` records source-derived metadata and image defaults, without binary bytes. The actual single-player table `50c264` selects `46ac30`, initializer `46a6d0`, state probe3 and peer-count0; its drawing slot+64 is `46ca50`. Racing table `50ef94` selects `475dc0`, initializer `4751c0`, state probe4 and peer-count `network+60`; its drawing slot+64 is `47a280`. `4751c0` actually allocates/joins a network controller and establishes a local peer before racing frame processing. These three networking helpers must not be called for an invented zero-filled single-player session.

Source image defaults are debug flags0, four last-pose values INT_MIN and rank timer500; viewport/pose packet begin zero. This is source-image evidence, not a replay of all application startup. Instructions `42616f/426174/426185` call message initializer `4222a0(config,5000,2000)` after constructing a 0x38-byte CString-list/config object. That initializer stores delays at+24/+28, clears+20/+2c/+30 and creates a font at+34. Its complete font initializer/CRT startup has not been ported here.

In single-player, flags0/state3/empty queue uses the message-timer fallback. A nonempty queue takes the HDC path and actual `46ca50` still updates the timers. Racing state4 always selects HDC; arbitrary other state tables can select the fallback. Thus the generic control flow can call message timers from multiple places, but the measured retail state tables determine the usual branch. The outer frame continues its existing presentation/audio/final-residency order after this service.

## Verification

Run:

```
work/test-env/bin/python Tests/compare_game_frame_services.py
```

Final checks compare 3,789 complete original calls and 11,499 ordered complete heap/global snapshots:

- 3,709 helper calls over entire 64KiB seeded heap plus every mapped service-global word, including all256 debug flag combinations, signed/extreme scores, wrapping/threshold deltas, no-peer/error/sound gates, live callback mutations and actual virtual method targets.
- 395 explicitly directed helper cases and 2,880 retained helper calls. Retained histories interleave pose, receive, rank, overlay and message timers rather than resetting each actor/context.
- 80 joined whole original `46ac30`/`428b60` calls with native services composed into frozen frame, timing, stage, camera, list and real populated spatial grid. Their 3,226 snapshots cover the full384KiB heap and timing/stage/actor/camera globals. Nine synthetic gameplay actors use declared fixture callbacks; original camera and actor-interaction/grid instructions remain real. The renderer fixture moves a real actor outside the resident region so final reinsertion/culling is observable. This does not claim all gameplay/renderer bodies recovered.
- Stack cleanup, meaningful returns and FS exception-chain restoration. Private Ghidra project logs verify actual entry boundaries and clean decompilation.

The comparison is bounded original control-flow equivalence under the declared external service profiles, not proof of full native retail gameplay, network protocol implementation, original text/font rasterization, queue allocator identity, or full application startup.
