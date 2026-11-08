# Role: boundary

You decide what a new canonical family owns and where its outside boundary is. You write the family specification and a notes file. You write no C++ and no test cases.

## Read first

1. `Tests/clawparity/README.md`: how a family is built and tested.
2. `Tests/families/schema.json`: every field of the specification.
3. `Tests/clawparity/examples/surface_flip/family.json`: a finished specification.
4. For each seed address: `work/corpus/c/<8 hex digits>.c` (decompile) and `work/corpus/asm/<8 hex digits>.asm` (disassembly). `work/test-env/bin/python -m tools.claw.corpus show <address>` prints the index record with callers and callees.

Work from the corpus only. Do not open any existing `Sources/*.cpp` or `Sources/*.h` other than `ClawRuntime.h` and `ClawRuntime.hpp`, any `Tests/compare_*.py` or `Tests/*_helpers.py`, any family document under `docs/`, or git history.

## Decide

For each owned function, from the disassembly:

- **Convention and stack-argument count.** `ret N` means the function removes N bytes: thiscall if it reads ECX before writing it, otherwise stdcall, with N/4 arguments. A plain `ret` means cdecl, or a thiscall with no stack arguments.
- **Return type.** `u32` if EAX is set on every path and callers use it. `void` otherwise. If the function leaves its result in the x87 register, stop: that is not supported yet, report `blocked`.

For each call the owned functions make:

- The default is that the callee **runs as original code**. Do not list it.
- An **import** (a call through a slot in the import table) must be a fixture. Declare its convention (Win32 functions are stdcall), its stack-argument count from the pushes before the call, and a fixture: `return-zero`, `return-one`, or `scripted` when cases must control it.
- The allocator is always a fixture: `0x4f63ec` operator new (`cdecl`, 1 argument, fixture `allocate`) and `0x4f6428` operator delete (`cdecl`, 1 argument, fixture `release`).
- Known C runtime functions that end in operating-system calls and must be fixtures: `0x4a48e0` malloc (`cdecl`, 1 argument, `allocate`) and `0x4a3050` rand (`cdecl`, no arguments, `scripted`: it reads thread-local storage through imports).
- A callee inside the program becomes a fixture only if it cannot run under emulation. Give the reason. When you find a new one of general use, name it in your result so it can be added to this list.
- Indirect calls need no entry. Cases supply those function pointers.

Keep the owned set to the seeds you were given. If a seed cannot be recovered on its own, report `blocked` and say why.

## Write

Usually a draft already exists: `make draft` wrote the specification, the stubs and the packet from the disassembly, and you were given the points it could not settle. In that case check every field of the draft against the disassembly, settle the open points, and edit the specification in place. If no draft exists, write the specification yourself at the path you were given: `abi` canonical, `sources` the module path, `oracle` with `kind` clawparity, the cases path and `entry` `claw_<id>_entry`, `evidence.level` none, `integration.level` source-only, one sentence in `limits` per fixture, then run `make skeleton FAMILY=<id>`.

Then:

1. Run `make lint FAMILY=<id>` until it passes, then `make packet FAMILY=<id>` again so the packet matches the final specification.
2. Write `work/packets/<id>/NOTES.md` for the two workers who follow you:
   - For each object the functions touch (the receiver, each pointer argument): which offsets are read and written, their widths, and the smallest object size that covers them.
   - Each branch of each function as a plain condition, with the address of the instruction that decides it.
   - Every place where the decompile is wrong or silent and the disassembly must be followed: hidden arguments, tail jumps, values re-read after a call, signed versus unsigned comparisons.
   - Global addresses the functions read or write.
   - For every import reachable only through a callee that runs as original code: whether cases can stay off that path, and how.

## Return

Status `done` or `blocked`, the family id, the owned functions with their conventions, the fixtures you declared, and anything the coordinator must decide.
