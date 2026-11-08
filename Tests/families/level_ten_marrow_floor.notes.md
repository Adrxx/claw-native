# level_ten_marrow_floor notes

Coverage exemptions 0x45a455-0x45a483 and 0x45a4cf-0x45a502 (dispatch branch taken when table growth 0x4db6e0 returns zero): checked against the original disassembly in work/packets/level_ten_marrow_floor/callees/004db6e0.asm. A failed realloc result is moved into EBP (0x4db70b, 0x4db77f) and the failure exit at 0x4db788 calls 0x4dc680, which reads [EBP+4] and faults at address 4, so growth never returns zero. Same finding and evidence as break_single_plank, level_eight_gabriel_bomb_01 and level_one_closure_dynamite_01.
