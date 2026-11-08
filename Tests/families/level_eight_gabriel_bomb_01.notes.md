# Level 8 Gabriel bomb closure: review notes

## 2026-10-24, coverage exemption review

Five exemptions were checked against the original disassembly.

- `0x445a2c`-`0x445a2e`: operator new returning 0 leads to an unconditional load through a zero pointer.
- `0x445b45`-`0x445b73` and `0x445bbf`-`0x445bf2`: reached only after `0x4db6e0` fails; its failure exit calls `0x4dc680` with EBP equal to the zero realloc result, which loads EBP plus 4 and faults.
- `0x445b8e`-`0x445ba5`: the second range check cannot fail, because a grown table's first new entry is zero-filled and an in-range entry keeps the same bounds.
- `0x446255`-`0x4462b2` in `0x446130`: the squared-length scalar includes the stored 2000.0, so scaled by 0.25 it is at least 1e6, never within 0.1. Confirmed with a stack simulation of the sequence and the data constants.
