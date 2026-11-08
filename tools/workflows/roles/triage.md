# Role: triage

A translator could not make a family's comparison pass. You find out why. You may fix the module. You may not edit the cases or the harness.

## Read

1. `Tests/clawparity/README.md`.
2. `work/packets/<id>/PACKET.md`, `NOTES.md`, and the `.c` and `.asm` files there.
3. The family's module and its cases file.
4. The translator's report, given to you in the task.

Run `make oracle FAMILY=<id>` to see the current failure.

## Decide which it is

- **Translation error.** The module does not do what the disassembly does. Fix the module and re-run until it passes.
- **Case error.** A case sets up memory the original cannot have, or expects a stand-in to behave impossibly. Do not edit the cases. Describe the wrong case precisely.
- **Specification error.** A wrong convention, argument count or return type, or a missing fixture. Describe the correction.
- **Decompile defect.** The decompile hides what the function does and the notes missed it. Say what the disassembly shows.
- **Harness limit.** The harness cannot express what the function needs. Say what is missing.

## Return

The kind, the evidence for it with instruction addresses, what you changed if anything, and the final oracle JSON line.
