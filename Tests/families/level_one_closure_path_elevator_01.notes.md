# Level 1 closure Path elevator helpers: review notes

2026-10-22. One coverage exemption, 0x468780-0x468824 in 0x468540: the branch for a source
object whose +0x6c word is zero reads absolute addresses 0xf0-0x10c. A case reaching it
faulted under the harness (null pointer access at 0xf4 from 0x468780) and the first 64KB is
never mapped on Windows, so the original faults too. The disassembly confirms absolute
operands (mov eax, [0xf4]). 0x4682c0 is declared void: its callers (0x4681c0) ignore EAX.
