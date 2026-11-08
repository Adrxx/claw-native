# Glossary

| Term | Meaning |
| --- | --- |
| Original | The v1.0 `CLAW.EXE` whose SHA-256 is recorded in `AGENTS.md`. Every tool checks the hash before reading it. |
| Family | A group of original functions recovered together as one native module. One manifest in `Tests/families/` per family. |
| Owned function | An original function a family implements natively. |
| Module | The C++ source of a family. |
| Canonical family | A family built on `Sources/ClawRuntime.h` and tested with the shared library `Tests/clawparity/`. |
| Legacy family | A Codex-era family with its own context structures and its own test scripts. |
| Token | An address in the original's 32-bit address space. Native modules use tokens, never host pointers. |
| Specification | The JSON manifest of a canonical family: owned functions, fixtures, where the cases are. |
| Case | One input the comparison runs on both sides. |
| Comparison, oracle | Running a case through the native module and through the original instructions, and requiring the same outside calls, memory and return value. |
| Outside call | A call from an owned function to anything the family does not own. |
| Fixture | A stand-in both sides call in place of a function that cannot run under emulation: an import, the allocator, a callback a case supplies. Codex's documents also say "transport". |
| Runs as original | An unowned callee inside the program that is executed as original instructions on both sides. No stand-in is involved. |
| Halt | A fixture that stops both sides at a service the test must not pass. The sides are compared up to that call. Codex's documents say "unsafe prefix". |
| Corpus | The local dump of every original function as decompiled C and disassembly, under ignored `work/corpus/`. |
| Packet | The bounded set of files a worker needs for one family, under ignored `work/packets/<id>/`. |
| Gate | The admission script. See `docs/ADMISSION.md`. |
| Mutant | The module with one small deliberate error, used to check that the cases would notice. |
| Evidence level | `none`, `provisional`, `legacy-frozen` or `admitted`. |
| Integration level | `source-only`, `compiled`, `elected` or `live`. |
| Frozen | Codex's word for a module whose test passed and was re-run by the coordinator. Recorded as `legacy-frozen`. |
| Elected | The module is called from a Swift host in the app. |
| Live | The module is reached through the original call graph in a recorded run of the app. Nothing is live yet. |
| Host | The Swift code that owns memory and dispatches calls for the modules inside the app. |
| Device lane | The owner's rule that one agent at a time may drive a given phone or simulator. |
