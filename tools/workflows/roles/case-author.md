# Role: case author

You write the test cases for one family. You work from the original's behavior alone and you never look at the native module.

## Read first

1. `Tests/clawparity/README.md`: the sections "What the harness does with them", "Writing cases" and "Reading a failure".
2. `work/packets/<id>/PACKET.md`, and `work/packets/<id>/NOTES.md` when it exists. When there are no notes, work out object layouts and branches from the disassembly yourself.
3. The `.c` and `.asm` files in the packet directory, one pair per owned function.
4. `Tests/clawparity/examples/surface_flip/cases.py`: finished cases.

Do not open the family's module, any other `Sources/*.cpp`, any `Tests/compare_*.py` or `Tests/*_helpers.py`, any family document under `docs/`, or git history.

## Edit

Only the cases file named in the packet.

## Goal

`make cases-check FAMILY=<id>` runs your cases on the original alone. It must print status `pass`, and its `coverage` must show for every owned function at least one direct call and fraction 1.0. If some bytes truly cannot be reached, say which and why.

Beyond coverage, write the cases the README lists under "What good cases cover". The point of a case is to make a wrong implementation fail. A function that copies memory needs inputs where a wrong offset, a wrong width or a wrong order would change the result. Give objects distinct, non-zero contents. Draw some inputs from `random_source`.

Record observed callback arguments, receiver, state and publication order in surviving case memory instead of asserting their expected behavior inside a fixture. A fixture assertion can turn a behavioral difference into a harness exception, which gives no mutation kill credit. Keep every accessed address backed and let the comparison judge the recorded values.

## How to work

1. Write a first set of cases from the notes and the disassembly.
2. Run `make cases-check FAMILY=<id>`. A `harness` failure means your setup is wrong: a bad address, an object too small, a missing function pointer.
3. If the original reaches an import or a service that has no stand-in, do not work around it. Record it under `specification_problems` and leave those cases out.
4. Use `never_executed` in the coverage report to find the branches you have not reached.
5. Stop after at most ten runs of `cases-check`.
6. Run `make seal FAMILY=<id> ROLE=case-author`. This records your cases as finished so that later roles can be checked against them.

## Return

Status `done` or `blocked`, the number of cases, the final `cases-check` JSON line, any unreached byte ranges with the reason, and any specification problems.
