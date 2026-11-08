# Original actor pair interactions

`Sources/ActorInteractions.h/.cpp` recovers the complete original v1.0 fixed-list pair scan **0x4c9390**, direct damage/hit selector **0x4c9ae0**, and rectangle helper **0x4c95b0**. It establishes generic callback selection and ordering. Gameplay callback bodies, mutable scene-list operations, and scheduler timing remain separate dependencies.

Profile: `Original/claw10/CLAW.EXE`, SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`. Branches, stores, and call order come from original instructions; no CrazyHook or reference gameplay implementation is copied. Private bounded Ghidra output is `work/actor-interactions-agent/scene.c` and `helpers.c` in a separately cloned project.

## Entry identity and native boundary

Original `0x4c9390` is actor-container vtable **0x513c20 slot +0x40**, stored at **0x513c60**. Creation at **0x4ceab5** installs that vtable and **0x4ceac5** stores the container in its parent +8. Original container +0x14 is the list head; nodes use next +0 and actor +8. This work executes the actual entry and its helpers. The higher-level scheduler invocation of that virtual slot is not yet independently traced, so the API does not prescribe its position within a game tick.

`ClawInteractionActor` contains an opaque actor identity and complete actor128 / primary93 / secondary93 / contact93 word buffers. Actor +0x6c / +0x70 / +0x78 identify those corresponding logic buffers. All pointer words remain 32-bit identities; no native pointer is cast into an original token. Untouched words and caller allocation seeds are preserved.

```c
uint32_t claw_actor_interactions(actors, count, dependency, user);
uint32_t claw_actor_interaction_hurt(actors, count, defenderIndex, attackerIndex, dependency, user);
uint32_t claw_actor_interaction_overlap(defender, attacker);
```

The scan uses the caller's fixed ordered list. Dependencies may mutate any represented actor or logic buffer, but must preserve represented identities, list order and membership. The caller supplies valid original logic buffers, including primary logic when generic damage can reach zero. Arbitrary polymorphic objects, null callback crashes, list deletion/insertion during callbacks, and aliasing represented objects are outside this bounded API. Native return one denotes completion, zero denotes invalid list/index input; original scan/damage entries are void. Null plus count zero is accepted. Native null/index/count rejection is a safety extension, not original invalid-pointer equivalence.

## Pair gates and ordering

For each actor A followed by each later actor B:

1. Test A flag1 once before entering its inner loop. Test each B flag1 when the pair is reached. Reject pairs where `(A.flags ^ B.flags) & 0x40000` is nonzero.
2. For A as defender / B as attacker, skip the direction if A flag4 or B flag0x80 is set. Cache `hitMask=A.d4 & B.d0` and `contactMask=A.d0 & B.d8`.
3. If either mask is nonzero and A hit rectangle overlaps B attack rectangle, contact runs first: when B +0x78 is present, set **B +0x7c=A identity**, then invoke its logic +0x10 callback with B as the sole cdecl argument. If the cached hit mask is nonzero, apply damage/hit dispatch to A using its current flag8 after contact effects.
4. The reverse direction rereads current B flag4 / A flag0x80 and masks after forward callbacks. Its masks are `A.d0 & B.d4` and `A.d8 & B.d0`; geometry is B hit / A attack. Contact sets A +0x7c=B and invokes A contact logic; the cached reverse hit mask then selects damage to B.

Flag1 and space-bit tests are not repeated before the reverse direction or after each callback. Forward masks remain cached across contact effects; reverse masks are fresh. These details matter when a callback changes eligibility or geometry mid-pair.

## Damage, secondary callback and geometry

Original **0x4c9ae0** performs no mask or rectangle checks of its own:

- Defender flag8: subtract attacker **+0x104** from defender **+0x10c**, using 32-bit wrapping arithmetic. A signed result <=0 sets defender primary logic **+0x1c=28**.
- Otherwise, if defender **+0x70** exists: set defender **+0x74=attacker identity** and invoke secondary logic **+0x10** with defender as the sole cdecl argument.

Neither path adds an explicit CaptainClaw invulnerability timer or powerup test. Such policy can affect flags/masks elsewhere; this engine must not invent additional immunity checks. CaptainClawHit41ce80 is selected through the actually bound secondary callback identity, not hardcoded by actor name.

Rectangle helper **0x4c95b0** translates defender hit +0x128..0x134 and attacker attack +0x138..0x144 by their +0x4c/+0x50 positions. Any left field equal to INT_MIN disables that rectangle. Coordinate addition wraps to 32 bits; comparisons are signed and edge touching counts as overlap. There is no rectangle normalization, sprite-size inference or implicit mirroring. The same rule appears inline in the forward scan and in complete rectangle-only helper0x4ca230.

`ClawActorInteractionCall` records callback function identity, receiver actor identity, peer identity, logic identity and portable kind (zero secondary hit, one contact). Function identities are original x86 tokens. Host adapters supply callback behavior and can see updated +0x74/+0x7c before invocation. Callback returns are ignored as in the original.

## Original-instruction evidence

`Tests/compare_actor_interactions.py` runs the hash-pinned original scan, direct damage selector and overlap helper through Unicorn. Only the gameplay callback bodies at registered **0x41ce80 / 0x498f40** are adapted to log and perform the same controlled mutations in both engines. No collision, mask, damage, or list-loop branch is adapted. All original list nodes are checked unchanged.

The suite passes **7,255 complete original scan/damage calls**, plus **2,000 independent original overlap comparisons**, **2,939 ordered adapted gameplay callbacks**, and records **308 interaction instruction addresses** after clearing the separate original CRT initialization trace. Each case compares every actor128 and all three logic93 buffers, plus ordered event arguments and node preservation. Coverage includes 5,000 generated lists of zero through six actors; 252 directed mask/flag/edge cases; three callback mutation policies; 2,000 direct damage cases; INT_MIN rectangle sentinels; wrapped coordinates, negative damage, signed overflow results, and equality at edges. Invalid native indices are also checked for no writes/events.

```sh
work/test-env/bin/python Tests/compare_actor_interactions.py
```

Optimized C++ and Swift import checks pass pair-mask selection, wrapping damage with primary state28, and inclusive translated edge overlap:

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -O2 -c Sources/ActorInteractions.cpp -o work/actor-interactions-agent/ActorInteractions.o
xcrun swiftc -import-objc-header Sources/ActorInteractions.h work/actor-interactions-agent/main.swift work/actor-interactions-agent/ActorInteractions.o -lc++ -o work/actor-interactions-agent/swift-interaction-tests
work/actor-interactions-agent/swift-interaction-tests
```

This is bounded original engine parity with explicit callbacks and a fixed list, not complete combat or scene scheduling parity. Root owns native integration and acceptance. No shared source/project/analysis edits, devices, simulators or extra agents are used.
