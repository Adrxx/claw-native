# Original v1.0 Officer logic

`Sources/OfficerLogic.h/.cpp` recover the Officer-specific layer from the hash-pinned original `CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. No gameplay implementation from a source port or CrazyHook table was copied. This module does not yet make a complete playable Officer: the shared HumanEnemy layer and host scene/resource services must be supplied explicitly. `Sources/HumanEnemy.h`, being recovered by another worker, provides pointer views into the same buffers.

## Native entries and exact boundaries

| Original entry | Native coverage |
|---|---|
| `462350` | Entire actor callback: startup allocation/constructor/init, state29 deletion dispatch, state30 empty callback, state1000 skip, otherwise frozen common FSM |
| `462410` | Every Officer derived constructor store and resource/RNG call, **after explicit shared constructor `44c000`** |
| `462af0` | Resolved in-range Officer table lookup; callback or explicit shared dispatch `44c840` |
| `462ef0` | Explicit shared pre `44d000`, then crouching-player low/high attack rectangle selection and STRIKE1/STRIKE lookup |
| `463020` | HOME update, mirror changes and inclusive-sentinel rectangle preservation, mandatory discarded RNG, cue/virtual or shared patrol branch |
| `463120` | IDLE enter: zero X velocity, signed RNG cue selector, saved old state, named ID, animation select/advance and idle timer |
| `4631e0` | IDLE update: unsigned timers, signed RNG five-way stand selection, region and patrol decisions |
| `463310` | Random release cue selection then explicit shared thrown body `44df10` |
| `462a20`, `462a00` | Destructor field/vtable writes and ordered bitset/CString/free services, including low-byte delete flag |
| `405000`, `4c96b0` | Verified pure attack-rectangle copy/mirror and empty virtual callback |

`claw_officer_entry` returns native support separately from original callback EAX. Unknown entries return unsupported; missing state metadata sets `context.fault=3`. Valid metadata is caller-owned. Shared GenericEnemy/FSM, movement, physics and GenericEnemyStates are composed through their frozen APIs rather than reimplemented.

Officer registry boot is `462c00`, with HOME→`463020` and IDLE→`4631e0`. It first invokes shared Human registration `44c950`, itself invoking common registration `43d5b0`. Human captures are BOUNCE→`44dd30`, THROWN→`44de50`, JUMPATCLAW→`44e510`, JUMPBACK→`44ea10`, ADVANCE→`44ea60`, FASTADVANCE→`44ec80`, STRIKE→`44ef70`, HITLOW→`44f290`, HITHIGH→`44f490`, FLAILING→`44f660`, HOME→`44da20`, IDLE→`44f800`. Numeric IDs depend on original registration order. Test IDs2000–2002 are explicitly installed metadata fixtures, not a claimed full-game boot profile.

## Full private allocation and native integration

Original Officer allocation is `0x470` bytes, 284 words. The frozen `ClawGenericEnemy.enemy` holds words0–263; `ClawOfficerContext.privateTail[20]` holds words264–283. `claw_officer_private_word` and `claw_officer_set_private_word` accept original byte offsets across both spans. Invalid/alignment/out-of-range accesses return0 or perform no write as a native safety extension.

At every host virtual/dependency boundary, concatenate both spans into the actor's original-identity heap block, then split all284 words back after the call. Copy actor128, primary93, secondary93 and contact93 as well. Tail words include Human fields, sound references450/454, and Officer timers458–46c; dropping them loses real behavior. Context contains complete effect actor/logic/private buffers, other actor/primary and platform primary views for shared Human services. `HumanEnemyContext` can point directly to these views without changing frozen generic layout.

Constructor alias profile is the actual constructed object: private+c, embedded wrapper128/12c/190/194 all refer to the same actor, and private10/130/198 to its primary logic. Arbitrary malformed or independently aliased heap identities are not silently simulated. Resource returns are opaque identity tokens, not native pointers.

Defaults install the original 43-entry Officer vtable `50ea0c` and original generic globals, with original scale defaults1.0. The host supplies runtime scales, difficulty537964, tick537210, animation delta5430c4, registry identities and player buffers. Native zero-seeded allocations are a host extension; original heap content is not claimed to be zero.

Important integration observations:

- Shared Human construction is `44c000`→`44bc60`, whose initial time uses **unsigned** tick times50e008 (actual zero-extended fild qword, verified at80000000); substituting generic4332f0 is not equivalent. The Human worker owns those bodies.
- `40abf0` subtracts32 from actorY, invokes grounding `4cd800(tileManager, actor, 0)` with **two arguments/pop8**, then sets actor type/modeCC=1. The decompiler omitted the zero argument; disassembly and original execution establish it.
- Officer health is3 on difficulty1, otherwise7, then healthScale; damage10 timesdamageScale; range50 timesrangeScale with the original unsigned minimum99.
- Original resource text is `LEVEL_OFFICER_OFCSWSTB8-22` with a hyphen. Sound names and missing sequence fallback `GAME_NULL` are preserved.
- IDLE cue selector uses signed modulo2: negative odd RNG selects field44c instead of450/454. Negative signed modulo5 skips stand-animation selection. Timer subtraction/comparison is unsigned, including wrap.
- Original Humanpre compares state-name pointer identities to literals. Matching the text alone cannot reproduce those gates. The Human host must retain verified original identity/profile rather than invent equality.
- State29 forwards actual Human deletion function `44cfd0`; state30 uses empty `4c96b0`. No invented Officer projectile behavior is present; the traced Officer layer uses shared melee strike/hit/death services.

Explicit services and shared body inventory are also saved in `work/officer-agent/dependencies.json`. In particular `44d000`, `44d3c0`, `44edd0`, `44df10`, `44df60`, `44e0c0`, `44d9f0`, typed hits and registry dynamic-growth paths remain shared Human/host boundaries until their separately verified module is integrated. Destructor cleanup calls `4dbcd0`, `4f6584` twice, then optional `4f6428`; it does not call a guessed Human destructor.

## Verification

Run from the repository root:

```sh
work/test-env/bin/python Tests/compare_officer_logic.py
zsh work/officer-agent/check-swift.sh
```

The optimized C++ suite compiles with `-O2 -Wall -Wextra -Werror -ffp-contract=off` and compares actual original x86 instructions with native code. Final evidence: **3,352 complete original Officer calls, 23,799 ordered full-snapshot dependency events, 1,282 distinct original instruction addresses**. Each comparison preserves all actor/logic words, every284-word private allocation, player and extra effect/other/platform buffers, and restored SEH head. Void-function incidental EAX is not treated as behavior.

Coverage includes250 generated cases per native method, wrapper branches, signed RNG boundary values/negative selectors, sentinel rectangles and mirroring, unsigned timer boundaries/wrap, resource present/missing/fallback, scaling/difficulty, low-byte deleting destructor flags, dependency mutations across tail and actor fields, and captured-state mutation during pre. Test-only virtual sentinels exercise Officer caller order without claiming shared Human behavior.

All **26 actual Level1 Officer WWD records** run complete startup and retained idle histories against the original Action-plane tiles and tile descriptions. At the ground service, the original executes the actual `4cd800` body; native executes verified `claw_collision_place_on_ground`. The original shared Human constructor is executed separately **26 times**, covering1,098 distinct original addresses, to generate explicit constructor dependency fixtures. Those fixtures replay changed words into both implementations at44c000; this is reference evidence for Officer composition, **not native Human recovery**. Its resource, collision, CString and bitset allocation services are controlled fixture adapters. Ordinary Officer tests use controlled shared-Human adapters to expose caller-side preservation/order.

Optimized Swift C interop passes a native Officer idle entry and state/timer assertions across the full264+20 split. This is a headless ABI check, not Xcode/device/UI acceptance. Evidence JSON is `work/officer-agent/verification.json`; bounded decompiles and private logs remain in that directory. No shared Ghidra project or device was used.

The missing Human/scene/resource implementation and full original boot profile still limit whole-game equivalence. Bounded buffer/event equality here is not a perfect-decompilation or complete-game claim.
