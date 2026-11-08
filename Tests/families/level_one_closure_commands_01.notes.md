# Level 1 closure commands: review notes

2026-10-22. Two coverage exemptions, both checked against the disassembly:
0x46bcb8-0x46bcba (0x46bc90): 0x46bcf0 has one exit, which loads 1 into eax, so the jne after
its call is always taken. 0x43748a-0x437491 (0x4373d0): reached only after the length is at
least 5 and 4 characters were removed, so the length is at least 1 and the less-than-1 branch
cannot run.
Unreached by cases (not exempt): 0x49bbc0 file-writing branch behind 0x46bdb0 (needs
GetFullPathNameA and other file imports); the -2 argument of 0x42b910 into 0x42b140 is not
observable because the reachable path returns before using it.
