# Level 1 closure Rat helpers: review notes

2026-10-22. Three coverage exemptions in 0x47cd70, same mechanism as
level_one_closure_projectiles_01.notes.md: realloc failure in 0x4db6e0 faults the original
in 0x4dc680 (reproduced under the harness with realloc failing: null pointer access at 0x4),
so 0x47cdc5-0x47cdf3 and 0x47ce3f-0x47ce72 cannot complete. 0x47ce0e-0x47ce25 is the
re-check of the index straight after the first lookup with no intervening call; the grow
routine leaves the index in range, so it cannot fail.
Fallback entries with a zero first word reach 0x43d490 -> 0x4a36f0 -> IsBadReadPtr; cases
avoid it (not owned bytes).
