# Bounded common enemy entry controllers

`CommonEnemyEntries.h/.cpp` supplies twelve original entries required by the verified Soldier/Human vtables. It operates on the frozen Human pointer view, preserves support separately from original EAX, and composes recovered Human/Common bodies or forwards actual virtual identities through the supplied dependency. It does not change frozen headers. The executable SHA256 is `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.

| Entry | Behavior |
|---|---|
| `43ed70` | Select falling ANI, save/resolve state, set actor mode 8 |
| `43efe0` | Set stopped flag, save/resolve STRIKE, select current strike ANI |
| `43fe00` | Zero X velocity, save/resolve STANDING, select saved stand ANI |
| `43f500` | Save/resolve PAUSE, retain supplied duration and unsigned start tick |
| `404e00` | Store supplied scalar at private `1ac` |
| `404e10` | Wrapping actor health subtraction by 4 |
| `44de30` | Set thrown timer 2000/start tick, then invoke recovered throw `440120` |
| `440b20`, `440c90` | Enter high/low block, queue release `440c70`, save state, select ANI/play gated sound, set actor flag 4 and X velocity ±200 |
| `440c70` | Restore private mode 2 and clear actor flag 4 |
| `44dbb0` | Increment Human bounce count, conditional first sound, frozen bounce for counts below 3, PAUSE at 3, then virtual damage/death or movement-rectangle/ANI/HOME restoration with timer 1500 |
| `43fa10` | Signed RNG modulo 41 chooses target near player, verifies bounds and repeated tile probes, then sets velocity ±150, mirrors and enters MOVEAHEAD |

`43fa10` preserves the exact repeated attribute queries: the same point is tested separately against 1, then 2, then 3, followed by the above-floor point against zero. Its Y is captured once; direction and actor/state/resource values remain live at their original read points. Block entry preserves queued callback and saved-state writes before resolving the state name, and audio callbacks precede final actor flag/velocity writes. Bounce restoration captures all four private rectangle fields before changing actor Y. Counters/health/timers retain wrapping arithmetic and the original signed/unsigned comparisons.

These twelve bodies are tested through Soldier composition against whole original instructions, 72 seeded cases each, with complete receiver/player/attacker/effect/platform/private/globals and ordered service snapshots. Directed MOVEAHEAD cases execute actual point geometry over a floor/wall fixture. The independent `compare_common_enemy_entries.py` checks the standalone API for ten bodies and Soldier composition for the two bodies needing its throw/virtual routing. The combined larger suite and actual Level 1 retained Soldier histories are documented in `soldier-logic.md`.

The original full bootstrap does not assign every name used by these optional generic entries; a real lookup returning zero remains zero rather than inventing an ID. Resolved registry metadata must remain caller-owned, including copied CString identities.

Multi-argument strike variants `43ee10` (sequence-name/rectangle) and `43eee0` (sequence-name/rectangle/sound-name) remain explicit dependencies with their actual two/three-argument ABI. No single-argument public entry substitutes their arguments. Resources, ANI advancement, pool playback, virtual subclass overrides and heap services remain host dependencies; the ordinary Soldier uses the recovered zero-argument `43efe0` entry. Production strict compilation and C11 headers pass. Verified evidence is in private `work/soldier-agent/common-entries.c`, `common-extra.c`, `common-release.c` and their clean recovery logs.
