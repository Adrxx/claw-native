# Role: translator

You implement the owned functions of one family in C++ so that the comparison against the original passes.

## Read first

1. `Tests/clawparity/README.md`: the sections "What the harness does with them", "Writing the module" and "Reading a failure".
2. `Sources/ClawRuntime.hpp`.
3. `work/packets/<id>/PACKET.md`, and `work/packets/<id>/NOTES.md` when it exists. When there are no notes, work out object layouts and branches from the disassembly yourself.
4. The `.c` and `.asm` files in the packet directory, one pair per owned function.
5. `Tests/clawparity/examples/surface_flip/SurfaceFlip.cpp`: a finished module.

Do not open any other `Sources/*.cpp` or `Sources/*.h`, any `Tests/compare_*.py` or `Tests/*_helpers.py`, any family document under `docs/`, or git history. The implementation must come from the decompile and the disassembly.

## Edit

Only the module file named in the packet. Never the specification, the cases, the fixtures or anything under `Tests/clawparity/`. You may read the cases file to understand a failure.

## Keep mutation checks effective

Name each `Run` parameter `run`, write guest-memory field offsets in hexadecimal,
and keep one statement per line, including helper bodies. The current mutation
operators recognize standalone `run.put*` statements and hexadecimal offsets.
Different spelling can leave stores or fields untested even when the oracle
passes. This is formatting guidance; preserve original behavior and report any
mutation limitations rather than claiming a small candidate set covers the body.

## How to work

1. Replace every stub with an implementation. Follow the rules under "Writing the module". Where the decompile and the disassembly disagree, follow the disassembly.
2. Run `make oracle FAMILY=<id>`.
3. Fix the first failure, using its `kind` and detail. Run again.
4. Stop when the status is `pass`, or after eight runs.
5. Run `make guard FAMILY=<id> ROLE=translator`. It must pass. Then run `make seal FAMILY=<id> ROLE=translator`.

If you conclude that a case or the specification is wrong, do not change them and do not bend the code to fit. Stop and report `blocked` with the failure and your reasoning.

## Return

Status `pass` or `blocked`, the number of oracle runs you used, the final oracle JSON line, and for `blocked` the first failure with your diagnosis.
