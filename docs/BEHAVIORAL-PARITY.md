# Behavioral parity target

User requirement (2026-10-11): source need not resemble the original source,
but the behavior of the game should be identical. The active goal remains a
playable native reconstruction, not an asset viewer or an approximate remake.

Identical behavior is possible in principle for a defined game version, asset
set, input history and timing model. Decompiler output alone is not evidence
that behavior is preserved. Full parity is not currently established.

## Acceptance evidence still needed

1. Fix the reference version and establish matching asset provenance. Current
   v1.0 addresses are hash-pinned. The separately retrieved disc executable
   matches exactly, and all active native resources/all14worlds match its REZ.
   See original-disc-provenance.json for the completed provenance checks.
2. Recover original scheduling, numeric rules, random state and serialization.
   Native presentation/input adapters must preserve game-state updates across
   host frame-rate differences. Matching quirks may be required for parity.
3. Execute identical input/delta traces in the original and native implementations,
   comparing player/world state, collision outcomes, animation/logic events,
   enemies, pickups, damage, checkpoints, saves and level transitions.
4. Exercise every single-player level and relevant special cases, including death,
   restart, combat/powerups, moving platforms, hazards and bosses. A successful
   ordinary playthrough alone does not prove every edge case.
5. Compare rendered scenes and audio separately. State agreement does not prove
   pixel placement, palette, sprite origins, layering, sample timing or mixing.
6. Demonstrate the playable native build on Mac or iPad simulator. A physical
   iPad installation/acceptance remains separate from simulator evidence.

Existing original-instruction comparisons are routine-level evidence for tested
inputs under documented stubs. They do not establish whole-game identity.
docs/animation-engine.md and docs/collision-and-player.md record the current
animation, physics and collision comparisons and their respective limits.

Any claim of "identical" must name its version, coverage and remaining unknowns.
Do not silently substitute a similar-feeling game or mark the active goal
complete because the preview compiles and launches.
