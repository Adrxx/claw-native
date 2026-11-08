# level_one_closure_breakables_powerups_01 notes

Coverage exemptions (checked against the original disassembly by the coordinator):

- 0x4710df-0x4710f1 in 0x470f00 and 0x47150f-0x471521 in 0x471330: branch on `[esi+0xd0] == 1`. The function stores 0x100000 (0x200000 in the second) into that field earlier and the only intervening callee, 0x4719e0, writes only absolute global tables. The compare can never succeed.
