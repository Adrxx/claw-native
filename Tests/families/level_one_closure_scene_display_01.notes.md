# Level 1 closure scene display helpers: review notes

2026-10-22. One coverage exemption in 0x4bdad0: 0x4bdbc4-0x4bdbc6 (xor esi, esi) is dead code. It needs depth 8, the converting flag set and [this+0x878] zero, which already returns zero at 0x4bdb3c-0x4bdb45 with no intervening writes.
Cases left out: 0x4b9d31-0x4b9d3b (0x4b9ce0 retry after a lost surface with a successful restore) dereferences a null argument passed by 0x4b97c0, so the original faults. 0x4b9ce0 is not an owned function.
All nine owned functions are thiscall; the draft listed them as cdecl with one argument.
Imports declared as scripted fixtures: resource, file and string services including SetFilePointer.
