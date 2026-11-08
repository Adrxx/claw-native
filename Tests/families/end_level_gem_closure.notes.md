# Level 2 end gem closure: review notes

2026-10-22. Three coverage exemptions, all where the original itself faults.
0x43cabc-0x43cabe (0x43ca60): original operator new returning null sets EDI to zero and the
next instruction reads [EDI], so the null path faults. Probe original-null-new-probe faulted
at address 0 (work/packets/end_level_gem_closure/cases-check-7.log).
0x43ce15-0x43ce43 and 0x43ce8f-0x43cec2 (0x43cdc0): both null-return fallbacks follow the same
callee 0x4db6e0. When its realloc fails it zeroes EBP and 0x4dc680 reads [EBP+4], so a failed
growth faults instead of returning null, for either call site. Probe original-growth-failure-probe
faulted at address 4 (cases-check-4.log). A separate probe aimed at the second site faulted in its
own setup (objects too small), so the second exemption rests on the shared callee, not on that probe.
Successful second growth (0x43ce5e-0x43ce75) is covered by cases.
