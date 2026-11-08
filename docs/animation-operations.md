# Bounded animation recovery - 2026-10-11

Original v1.0 input: SHA-256 `350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263`.
Downloaded from the Claw Recluse link labeled original v1.0; this does not assert
an independent match to a physical retail CD. See original-reference-manifest.json.

Registration at 0x401fbf references "SimpleAnimation" (0x5224d8) and callback
0x498f40. Direct disassembly shows actor logic pointer +0x6c, actor field +0xc8,
updater context +0x188, global argument 0x5430c4, nested updater 0x4c82a0.
These differ from the CrazyHook-pack callback/layout. Both callback profiles
pass 600 cases each; their updater call is stubbed, so this proves dispatch only.

New recovery uses direct Capstone disassembly of the original v1.0 updater:

- Delay prefix 0x4c82a0 through (excluding) 0x4c8305. Missing sequence (+8)
  returns -1. Pending delay (+0x14) decrements by one when +0x18 is zero;
  otherwise subtracts the unsigned argument or becomes zero when it expires.
  Expiry copies +0x20 into +0x24 and enters subsequent processing. The native
  `ready` result represents this boundary, not a recovered original return value.
- Movement block 0x4c8487 through (excluding) 0x4c84f7 clears actor +0x10/+0x14.
  Record +0x10 selects mode: 1 copies record +0x20/+0x24 into those actor fields;
  2 adds them to actor +0x4c/+0x50, reversing horizontal sign if actor +0x40 bit 1
  is set; 3 assigns actor +0x4c/+0x50 directly. Other modes only clear the fields.
  Position/velocity labels remain interpretations; no collision or player
  movement equivalence is claimed. Arithmetic is modulo 2^32.

Sources/AnimationOperations.cpp implements these blocks using v1.0 field offsets.
Tests/compare_animation_operations.py executes the actual instruction ranges,
checks complete actor/state buffers, boundary/return behavior and unsigned edge
cases. 1,200 movement + 1,200 delay cases pass per profile (4,800 total).
No nested calls occur in these slices; none are stubbed. The pack profile maps
its different offsets into the native v1.0 layout for comparison. Both tests
reject an unknown binary hash before reusing addresses.

Not recovered: full updater event dispatch, frame selection, loops, audio,
player controls, velocity integration, collision or fixed-step scheduling.
The blocks compile into the iPad app but are not integrated with the preview.
