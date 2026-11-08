# clawparity: how a canonical family is built and tested

A family has three files.

| File | Who writes it | What it is |
| --- | --- | --- |
| Specification, `Tests/families/<id>.json` | Boundary role | Which original functions the family owns, and which calls are replaced by stand-ins. |
| Module, `Sources/<Name>Runtime.cpp` | Translator | The native implementation of the owned functions. |
| Cases, `Tests/families/<id>.cases.py` | Case author | The inputs both sides are run on. |

A worked example of all three is in `Tests/clawparity/examples/surface_flip/`.

### Original executable profiles

Omitting `program` still selects the pinned **claw-v1.0** executable. To compare
a separate family against v1.3, put `"program": "claw-v1.3"` at the top level
of its manifest, then run the usual `make oracle FAMILY=<id>` or
`make gate FAMILY=<id>`. Do not switch an admitted v1.0 family's identity.

The v1.3 loader verifies the RealNetworks launcher at
`Original/claw-rip/files/App_EXE/CLAW.EXE` (SHA-256
`5130d7d951e4a350fc19fe3134aa447a17c3e220ae49e7834d06ec79724fa0c0`), selects
exactly resource `EXE/101/1033`, and verifies the embedded game (SHA-256
`8f5069541a1c7d3f62896fb935ba591efa6fbfa4450798b96fe6f48f9cf396a0`). Extraction
stays in memory; no launcher instructions or cached extraction are executed.
The original precision initializer is `0x4a9a52` in v1.3 (`0x4a7ef0` in v1.0).
Both run before the test snapshot and must produce x87 CW `0x023f` under mask
`0x0f3f`. This initializes precision only, not WinMain or game globals.

Use the selected executable's actual function addresses, globals, fixture
addresses and object layouts on both sides of its comparison. Nothing is
automatically rebased or field-translated. Imported physical services come from
that executable's IAT; declare fixtures in `callees` as usual:

| Fixture | v1.0 IAT slot | v1.3 IAT slot | Signature |
| --- | --- | --- | --- |
| `is-bad-read-ptr` | `0x546a40` | `0x50c168` | stdcall, 2 arguments |
| `set-rect` | `0x546d5c` | `0x50c4d8` | stdcall, 5 arguments |
| `set-rect-empty` | `0x546cdc` | `0x50c430` | stdcall, 1 argument |

The v1.3 contract rejects mismatched service identities. CRT/native stand-ins
also need their actual v1.3 code addresses; a v1.0 address is never a mapping.
Each v1.3 owned entry currently requires an explicit `interval_end`. The v1.0
corpus and its `body_ranges` extension are not v1.3 ownership evidence.
Ownership overlaps are checked within each program identity. V1.3 admission
fingerprints additionally bind the profile loader and validation code.

`Tests/OracleProfiles/v10.json` and `v13.json` compare the same duration
initialization behavior at `0x49e470` and `0x4a2010`. The proof uses actual
duration offsets `0x148/0x14c` and `0x164/0x168`, respectively; the destination
sum remains at `+0x4c`. These are harness proofs, not new gameplay admissions.
Run the focused check, including three existing v1.0 gates without recording
their admissions, with:

```sh
PYTHONPATH=Tests work/test-env/bin/python -m clawparity.selftest.oracle_profiles --spot-check-gates
```

### Canonical build inputs and retained ownership

`sources` lists everything the family owns, including retained portable APIs.
By default the comparison compiles all owned `.cpp` files in that order.
A canonical manifest may instead declare `canonical_sources`, a nonempty ordered
list of existing, unique, unaliased `.cpp` paths from `sources`. This selects only
the comparison build; native app membership and source ownership still use
`sources`. The first selected file is the primary module for packets, skeletons
and mutation. `--module-source` replaces only that file, preserving all selected
auxiliary translation units. Missing or unowned inputs fail before execution.

Selection, order, selected source contents and owned headers participate in the
build cache. Admission records bind the selection, manifest contract, owned
sources, cases and build harness to `build_inputs_sha256`. Changing them makes
that admission stale in manifest validation and app generation. Opting into
`canonical_sources` requires a new admission; historical default admissions
without this fingerprint retain their existing meaning. This mechanism grants
no admission by itself. Run the independent transport checks with
`PYTHONPATH=Tests work/test-env/bin/python -m clawparity.selftest.build_inputs`.

To link another admitted canonical family's implementation in a comparison,
declare `shared_sources`, for example:

```json
"shared_sources": [{
  "family": "logic_state_registry_core",
  "sources": ["Sources/LogicStateRegistryCoreRuntime.cpp",
              "Sources/LogicStateRegistryCoreRuntime.h"]
}]
```

Keep these paths out of the borrower's `sources` and `canonical_sources`.
Borrowed translation units append after the owned primary, including for mutant
builds; shared headers and the owner's headers participate in cache identity.
References must be unique, local, unaliased paths owned by the named admitted
family; `.cpp` paths must be among its canonical build inputs. Sharing is one
level deep: an owner cannot itself borrow sources. The app links each path once
through its owner and rejects missing or excluded owners. This does not grant
ownership of the owner's original addresses or relax the comparison boundary.

The public package `build_inputs` API adds this opt-in extension around the
unchanged owned-input implementation. Existing manifests use that implementation
and retain their fingerprints. Shared admissions additionally bind the extension,
borrowed files and the owner's full input fingerprint; changed inputs or stale
owner admissions require a new gate. Owner evidence refreshes alone do not change
the contract. Check this extension with
`PYTHONPATH=Tests work/test-env/bin/python -m clawparity.selftest.shared_build_inputs`.

## What the harness does with them

Each case is set up once into an initial memory image. The harness then runs it twice from that image: through the native module, and through the original instructions under emulation. It compares, in this order:

1. Every fixture call and declared x87 original boundary: the function, the receiver, the arguments (including exact x87 operand bits), the bytes its pointer arguments point to, and a digest of all memory at the moment of the call. Other original callees are executed on both sides; their nested fixture calls are compared.
2. The heap after the function returns.
3. The program's global data after the function returns.
4. Which objects are live and which were freed.
5. The return value, unless the specification says the function returns nothing.

Outside calls are of two kinds. A **fixture** is a stand-in both sides call: imports, the allocator, function pointers a case supplies. Any other function inside the program runs as **original code on both sides**. When native code calls one, the harness runs the original callee over the native side's memory. So a family never needs a stand-in for game code it does not own.

An original whole callee that reads its caller's EBP declares `caller_frame`: a list of `{caller, site, ebp: {base, offset}}`, one per owned ordinary caller, where `site` is that caller's direct CALL and EBP is `receiver`, `entry_esp` or `argument:N` of the caller's entry state plus `offset`. The original side checks the rule at every declared site and rejects any other CALL of the callee from that caller; native bridges of the callee receive that EBP only under a declared outer entry and with its exact signature, and are refused otherwise (`make selftest`, `python -m clawparity.selftest.caller_frame`). A callee that reads EBP at a site where the caller's own caller EBP is still live, so no caller-relative rule fits, uses a case-elected entry frame instead: setup calls `env.entry_frame_pointer(value)` (one 32-bit value, ordinary outer entries only). The original enters the owned function with EBP = value and must return it unchanged. Native code never receives the value: a direct zero-operand `run.call` of a declared compiler-context callee whose masks are exactly `0x5c1` executes the unchanged original with that EBP; sites reached after the original changes EBP keep `run.context_call` with an explicit EBP (`python -m clawparity.selftest.entry_frame`). The catalogue also offers `reallocate` (C runtime realloc `0x4a9070`), `is-bad-read-ptr` (IsBadReadPtr), `set-rect` and `set-rect-empty`.

### Long original runs

Original code runs under Unicorn at full speed except where a Python hook is installed. The FLD m32/m64 signaling-NaN correction (`kernel.py`) used to hook every instruction, about one million instructions a second, so an original such as `0x4c6d90` (65536 calls to `0x4c7580`, about 370 million instructions) could not return within the fixed 30 s per call. The correction now hooks an exact superset instead: every address outside program text, and in text each byte offset whose bytes, after the accepted prefixes, decode as `D9 /0` or `DD /0` with a memory operand, plus the 15 bytes that contain its fall-through. The handler still decodes every hooked instruction, so the correction and the comparison are unchanged. A write into program text, by the harness or by emulated code, restores the global hook. No declaration is needed and the 30 s limit is unchanged: one `0x4c7580` call now takes about 0.05 ms instead of about 8 ms, and a whole `0x4c6d90` case returns on both sides in about 1.5 s.

The native side needs care too. Each `run.call` of an original callee is a bridge that copies the heap, the globals and the stack into the emulator and back; tens of thousands of bridges cost seconds per case (measured: 65536 bridged `0x4c7580` calls, about 12 s per `0x4c6d90` case). When an admitted family owns such a callee, borrow its source with `shared_sources` and call its exported canonical entry directly, for example `claw_player_fade_blend_canonical_entry(0x4c7580, 0, arguments, 4, &run.host, &result)`, failing with `run.fail` when it returns 0. The comparison then checks the native caller together with the admitted callee translation against the unchanged original of both, on every call. Keep such cases ordinary comparisons: original-only cases watch the heap with a Python callback per access. Check the hooks with `PYTHONPATH=Tests work/test-env/bin/python -m clawparity.selftest.x87_load_hooks` (also part of `make selftest`).

## Writing the module

Include `ClawRuntime.hpp`. Everything goes through the `Run` object.

| Call | Meaning |
| --- | --- |
| `run.get(a)`, `run.put(a, v)` | Read or write 32 bits at address `a`. |
| `run.get8`, `put8`, `get16`, `put16` | The same for 8 and 16 bits. |
| `run.gets(a)` | Signed 32-bit read. |
| `run.getf`, `putf`, `getd`, `putd` | `float` and `double`. |
| `run.call(f, receiver, {args})` | Call a function the module does not own. `receiver` is ECX for a thiscall callee and must be 0 for stdcall and cdecl callees. |
| `run.call_x87(f, receiver, st0, {args})` | Pass one binary64-representable operand in ST(0), then execute the unchanged original callee. Declare it as `kind: whole` with `x87_args: 1`, `convention` and `argc`. |
| `run.call_x87_exact(f, receiver, state, {args})` | Transfer a declared full extended stack to unchanged original code; validate pops, result, lower live values and control word. |
| `run.x87_step(op, state, {operands})` | Evaluate one bounded x87 arithmetic primitive with the supplied masked CW (PC 24/53/64, all rounding modes). |
| `run.icall(slot, {args})` | Call through an import-table slot. |
| `run.vcall(object, offset, {args})` | Virtual call: reads the method from the object's vtable. |
| `run.automatic(offset)` | Address of a stack local, given its offset from the function's entry stack pointer. Needed only when a local's address is passed to another function. |
| `claw::s32(v)` | Reinterpret as signed, for signed comparisons and signed division. |

Rules that keep the native code equal to the original:

- Do arithmetic in `uint32_t` and convert with `claw::s32` only where the original instruction is signed (`jl`, `jg`, `idiv`, `sar`, `imul` on signed data). Signed overflow in C++ is undefined and the sanitizer run will stop on it.
- Read a field again wherever the original reads it again. Do not cache a value the original reloads after a call: the callee may have changed it.
- Keep outside calls and stores in the original's order. The comparison checks memory at every outside call.
- An owned function that calls another owned function calls it directly in C++.
- Never keep a host pointer. Addresses are plain numbers.
- `call_x87` transfers a value, not a conversion implementation: the original callee performs its own rounding and conversion. Its exact extended operand bits and memory are compared at entry. This legacy helper supports one binary64-representable input and EAX output. Use the separate exact stack capability below for extended values, additional live slots or an x87 result.
- One statement per line. Name fields in a comment the first time an offset is used. Cite the original address above each function.
- When the decompile and the disassembly disagree, the disassembly is right. Check every indirect call, every tail jump and every argument count against the `.asm` file.

A stub that is not implemented yet calls `run.fail(CLAW_FAULT_UNIMPLEMENTED, address)`.

### Exact x87 runtime boundary

Declare an original callee with `kind: whole`, ordinary `convention`, `argc`
and `x87_exact: {"pop": 1, "push": 0}` for conversion, or
`x87_exact: {"pop": 2, "push": 1}` for power. Stack-argument producers such
as floor/ceil use `argc: 2` and `x87_exact: {"pop": 0, "push": 1}`: the
binary64 input is two ordinary low/high stack words, independent of the x87
stack. `pop` is 0 through 8; `push` is 0 or 1. A balanced call
(`{"pop": 0, "push": 0}`, for example thiscall `0x403b40`) accepts an empty or
nonempty stack, must leave every live value, depth/TOP and CW unchanged, and
publishes only the callee's actual SW and EDX:EAX through the same receipt;
`Tests.clawparity.selftest.x87_balanced --all` checks it. Producers accept an empty stack or up to seven lower live values;
both the C++ helper and host reject result overflow before execution.
This declaration is exclusive with `x87_args`, compiler/source
context, tail and guest capabilities. Fixtures cannot implement this boundary.
The runner and manifest reject malformed or mixed declarations.

`ClawX87State` is a borrowed synchronous value with `size = sizeof(state)` and
`version = CLAW_X87_VERSION`. `slots[0..count)` are logical ST registers;
each has an explicit 64-bit significand and 16-bit sign/exponent in a checked
32-bit field. There is no host `long double`, binary64 conversion or packed
unaligned load. Reserved fields and inactive slots must be zero. The state
contains CW and SW, including physical TOP; the live stack must be contiguous
and contain at most eight values. Tags are derived from the live value encodings.
Empty physical register payloads, last-opcode/IP/data-pointer fields, unmasked
exceptions and sparse tag stacks are outside this contract.

Before `run.call_x87_exact`, set `popCount`/`pushCount` to the declaration and
clear `returned`, `eax` and `edx`. Every live value, including those below the
arguments, is installed as raw register bits. Entry events compare the entire
live stack, CW/SW, ordinary arguments and memory digest. The unchanged original
callee must actually return with the declared ordinary stack cleanup, expected
x87 depth/TOP, unchanged CW and byte-identical lower live values. Only then does
the host publish the new stack, SW, EDX:EAX and `returned = 1`; the helper also
checks the response and immutable request. An unaware host cannot succeed by
returning an integer alone. The helper's return is EAX; `state.edx` is available
for integer conversions and `state.slots[0]` carries an x87 result. Clear the
receipt/integer outputs again before the next outside call.

An owned ordinary entry (cdecl, stdcall or thiscall) that returns its result
in ST(0) declares `"returns": "x87"` and `"x87_result": {"pop": 0, "push": 1}`;
it is exclusive with source, compiler, guest and other x87 capabilities, and
EAX is not compared. The module starts from `auto fp = run.x87_entry(address)`,
the host's exact entry stack, CW and SW (the elected case profile, otherwise an
empty stack, the elected sticky SW or 0 and the startup CW), computes with `x87_step` and `call_x87_exact`, and
ends with `run.x87_return(address, fp)` as its last outside call. The host
accepts only the entry stack plus one pushed value with unchanged CW and
TOP one below entry, once; it rejects a missing, repeated or late publication,
another entry's address and malformed requests. The original side captures
the unchanged callee's actual stack after RET and reports a declaration whose
original does not return exactly one ST(0) with unchanged CW and lower slots.
The comparison then requires CW, SW and every live slot bit-identical (kind
`x87-result`). `work/test-env/bin/python -m Tests.clawparity.selftest.x87_result --all`
checks synthetic loads and an owned body calling a declared original producer,
wrong values, SW, missing/extra/late publications, corrupt hosts, schema and
the runner path against hash-checked unchanged 0x420af0 on its equal-factor
exit (sign-zero factors, signaling NaN with IE). The app dispatch generator
still rejects `returns: x87`: no shipping host serves ENTRY/RESULT yet.

An ordinary `u32` or `void` owner that consumes inherited x87 state instead
uses `"x87_environment": {"pop": 0, "push": 0}` on its owned signature. It is
exclusive with `x87_result`, source/compiler context, guest graphs and other
entry x87 declarations. It does not turn an integer owner into an ST(0) producer:
EAX is still compared for `u32`. The entry queries once with
`auto fp = run.x87_entry(function)` and publishes once with
`run.x87_finish(function, fp)` as its last outside call. Publication must preserve
the entry CW, depth/TOP and every live slot; the full final SW is compared against
the unchanged original. Missing, repeated, undeclared, mixed or malformed requests
fail. ENTRY/RESULT reuse their checked version-1 receipt; an unsupported host
cannot succeed by returning an integer without serving the receipt.

Case setup may call `env.entry_x87_status(sw)` once, before freezing. This bounded
profile accepts integer exception flags in bits 0 through 5 (`0..0x3f`), including
`0`, `0x20` and `0x21`, with all exceptions masked by the program startup CW.
Both original and native runs start with that SW, an empty stack and TOP 0.
It resets between cases; booleans, condition codes, SF/ES/B, TOP changes,
unmasked environments, late setup and context/guest entries are refused.
The election also applies to existing owned x87-result entries.

For a declared owned `x87_environment` or `x87_result` entry, use
`Case(..., entry_x87=profile)` or call `env.entry_x87(profile)` in setup.
The Case field also accepts a function of the setup return value. The exact API is:

```python
profile = {
    'control': 0x023f,
    'status': (5 << 11) | 0x4021,  # physical TOP 5, C3, sticky IE/PE
    'slots': ((0x8000000000000001, 0x3fff), (0, 0x8000)),
}
```

Slots are logical ST(0) onward, each `(uint64_significand, uint16_sign_exponent)`;
the example preserves an extended value not representable as binary64 and negative
zero. Zero through eight contiguous slots are supported, including empty stacks
at any TOP. An x87-result entry needs room for its additional result. No explicit
tag/count/reserved fields or holes are accepted. Normal values, signed zero,
subnormals, infinities and signaling/quiet NaN payloads retain all bits; pseudo
denormals and unnormal/pseudo-special encodings are rejected. Integers must be
actual Python ints, never booleans, floats or values that need truncation.

CW is exactly `0x003f | PC | RC`: PC is `0`, `0x200` or `0x300` (24, 53 or
64-bit precision) and RC is `0`, `0x400`, `0x800` or `0xc00`. All exceptions
are masked; reserved PC, reserved bits and the legacy infinity-control bit are
unsupported. SW accepts sticky exception bits 0..5, C0/C1/C2/C3 and TOP bits
11..13 (`sw & ~0x7f3f == 0`); SF, ES, B and reserved bits are rejected.
`x87_step` supports these same twelve CW settings without resetting to startup
CW. This is comparison-host support, not an election of app-host arithmetic.

Setup copies the profile once before freezing; it cannot be combined with
`entry_x87_status`, repeated, changed after setup or used on context/guest or
undeclared ordinary entries. Both execution sides reinstall the identical input;
ENTRY queries expose it and final comparison checks every live bit, CW and actual
SW/TOP. New cases reset the election. Internal temporary-stack capacity remains
the case author's responsibility. `work/test-env/bin/python -m
Tests.clawparity.selftest.x87_environment --all` checks this API, runner comparisons,
nested balanced transport, rounding and corrupted publications, including an
independent hash-verified unchanged-original CALL/callee control.

Carry the environment through each relevant original balanced callee explicitly:

```cpp
auto fp = run.x87_entry(function);
fp.popCount = fp.pushCount = 0;
const auto value = run.call_x87_exact(callee, receiver, fp, {argument});
// fp.status is the actual post-callee SW; x87_step carries it onward.
// Before another exact call, clear returned/eax/edx and select its stack effect.
run.x87_finish(function, fp);
return value;
```

Declare that callee as `kind: whole` with `x87_exact: {"pop": 0, "push": 0}`.
For an owned factory calling an owned constructor, query at the outer entry and
pass the same state through the native helper; publish using the outer entry's
address. Do not query a second outer entry, seed a fitted SW, or bridge an
x87-changing dependency through ordinary `run.call` and assume its SW was returned.
`work/test-env/bin/python -m Tests.clawparity.selftest.x87_environment --all`
checks deterministic direct/factory flags, post-balanced-callee state, strict final
comparison and negative controls under O0, O2 and sanitizers. Its original-backed
probe executes the hash-checked unchanged CALL at `0x4dca5c` to `0x403b40`.
It is a harness control, not a family admission.

Owned logarithm/division intermediates use an explicit instruction sequence,
not a host logarithm or a delegated game body. `run.x87_step` accepts only
`CLAW_X87_LN2`, `I32`, `F64`, `YL2X`, `DIV_ST1`, `POP`, `CHS`, `SUBR_F64`,
`MUL_F64`, `ROUND_F64`, `DIV_F64`, `ADD_ST1` and `ADD_F64` (all with the `CLAW_X87_` prefix),
plus the register, compare, store and trigonometric primitives described next.
I32 takes one raw signed word. F64 and the four binary64 memory arithmetic
operations take low/high words; the others take no ordinary operands.
CHS flips ST(0)'s sign. SUBR_F64 computes operand minus ST(0); MUL_F64 and
DIV_F64 multiply or divide ST(0) by the operand. ROUND_F64 stores and pops
ST(0) to isolated binary64 scratch memory, then reloads that rounded value.
These five operations replace only ST(0), preserve lower live values and
physical TOP, and return the actual instruction SW. DIV_ST1 remains available;
DIV_F64 avoids introducing an extra live divisor into a memory-divide sequence.
ADD_ST1 (operation 12, `D8 C1`) computes ST(0) + ST(1), requires at least two
live slots and takes no ordinary operands. ADD_F64 (operation 13, `DC /0 m64`)
computes ST(0) + the binary64 low/high operand words and requires one live slot.
Both replace only ST(0): their transport effect is pop 1/push 1, with no
architectural pop, unchanged depth/TOP, byte-identical lower slots and CW, and
the instruction's resulting SW. Extended significands and exponent range never
pass through host floating arithmetic. Their arity, depth, CW, request fields
and completion receipt have the same checked rejection contract as other steps.
Register, compare and store primitives (operations 14 to 21 and `0x100` to `0x1bf`)
cover pure register-stack code. `COMPP` (`DE D9`), `SQRT` (`D9 FA`) and `ABS`
(`D9 E1`) take no operands; `COM_F64`, `COMP_F64` and `SUB_F64` (`DC /2`, `/3`,
`/4`) take low/high words; `ST_F64` and `STP_F64` (`DD /2`, `/3`) take none and
`run.x87_step` returns the stored binary64 bits (EDX:EAX, also left in
`state.eax`/`state.edx`); the translated code writes them to guest memory itself.
Every other step returns 0. Register forms are `CLAW_X87_ST(form, i)` for
ST(i), i from 0 to 7, with the exact encoding beside each form in
`Sources/ClawRuntime.h`: `LD_ST`, `XCH_ST`, `ST_ST`, `STP_ST`, `COM_ST`, `COMP_ST`,
the `D8` forms `ADD/MUL/SUB/SUBR/DIV/DIVR_TO0` (result in ST(0)), the `DC` forms
`*_TOI` (result in ST(i)) and the `DE` popping forms `ADDP`, `MULP`, `SUBRP`,
`SUBP`, `DIVRP`, `DIVP`. Map by encoding, not by a disassembler's mnemonic:
`DC E8+i` is `SUB_TOI` (ST(i) = ST(i) - ST(0)) and `DE E8+i` is `SUBP`.
Their transport effect covers the touched slots, with k = i + 1: loads pop 0/push 1,
compares pop 0 or 1 (2 for `COMPP`)/push 0, `D8` forms pop 1/push 1, `XCH`, `ST_ST`
and `DC` forms pop k/push k, `STP_ST` and `DE` forms pop k/push k - 1; minimum
depth is k, and a step that would leave more than eight live values fails.
Compare steps leave the instruction's actual SW in `state.status`, the value
the original's `FNSTSW AX` reads; translate the branch from its C0/C2/C3 bits.
The reference interpreter raises no IE/PE flags for these instructions (hardware
would for an ordered compare with a quiet NaN or an inexact square root); both
comparison sides use it. `Tests.clawparity.selftest.x87_register --all` checks every
operation, depth and TOP against independently assembled instructions,
hand values naming each operand order, FNSTSW agreement, malformed requests
and corrupt hosts. The helper resets the receipt and selects
the primitive's fixed stack effect. The comparison host executes one independently
written instruction (a store/load pair for ROUND_F64) in an isolated interpreter, with no game addresses, guest
memory or fixtures. The sequence and operand selection remain in translated code.
Each step consumes the Run operation budget; stack underflow/overflow fails.

`CLAW_X87_SIN` (22, `D9 FE`, FSIN) and `CLAW_X87_COS` (23, `D9 FF`, FCOS)
take no ordinary operands and require one live slot. Both replace only ST(0):
transport pop 1/push 1, unchanged depth/TOP/CW and byte-identical lower slots,
with the actual resulting SW and zero EDX:EAX. They use the same isolated
instruction engine and checked receipt; no game address, fixture, host floating
conversion or host-libm substitution is introduced. Preserve the live angle in
the state across the first exact `__ftol` call when computing both coordinates.

The focused command for the deferred three-entry Omar recovery is:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.x87_trigonometry --all
```

It runs O0, O2 and ASan/UBSan controls: all eight depths and TOP positions,
extended-only inputs, signed zero, range edges, special encodings, malformed
operations/receipts, corrupt hosts, and unchanged instructions at `0x464051`,
`0x46406d`, `0x4641e8`, `0x46420a`. Both original ring sequences retain their
angle scaling, multiplication, subtraction and two actual `0x4a30e0` calls;
every intermediate, exact conversion operand, lower live angle, SW and EDX:EAX
is compared. Nearby angles straddle integer results, and a separate extended
operand detects binary64 rounding before conversion. These controls also run
in `make selftest`; they admit no game family and provide no shipping host math.

Range behavior is explicitly reference-interpreter behavior: it computes at
exactly positive and negative 2^63 and clears C2, whereas the next binary64
magnitude above 2^63 leaves ST(0) unchanged and sets C2. The extended value just
above 2^63 follows the former behavior. The original-site controls pin this
quirk; do not infer architectural or hardware transcendental accuracy from
exact transport parity.

The primitive profile is deliberately limited to Claw's hash-verified startup
CW `0x023f` (masked exceptions, 53-bit precision, nearest rounding). Other
control words fail before execution. In the current reference interpreter,
FLDLN2 retains significand `0xb17217f7d1cf79ac`, whereas the grid's subsequent
FYL2X of 2 produces `0xb17217f7d1cf7800`. Both are preserved at their actual
steps; do not assume every intermediate is binary64 or replace the sequence
with `std::log2`. Probes also found that this interpreter's FLDLN2 does not
change its constant for directed rounding, so those primitive profiles are not
claimed. The broader exact-call transport still preserves masked CW settings;
this task establishes parity with the existing reference interpreter, not
new hardware transcendental accuracy guarantees.

The focused command is:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.x87_exact --all
work/test-env/bin/python -m Tests.clawparity.selftest.x87
```

`work/test-env/bin/python -m Tests.clawparity.selftest.x87_load_store` checks
the bounded reference correction for masked `FLD m64` signaling NaNs. Unicorn
leaves these signaling and omits IE; Intel SDM volume 1 section 4.8.3.5 and the
FLD instruction require setting the quiet bit and IE, preserving sign/payload.
The correction runs after a successful load, before the next observer/store,
without changing guest memory or replacing address, fault, tag or stack handling.
Other load formats, unmasked invalid exceptions and stack overflow retain the
interpreter's behavior. This is not a general x87 exception or NaN implementation.
Independent controls cover all TOP positions and available stack depths, ordinary
values, signed NaNs, addressing forms, stops, memory faults and the hash-checked
actor entry at `0x4082d0`. The authoritative finding and independent Bochs 3.1
instruction probe are retained under `work/x87-signaling-nan/`.

The first runs O0, O2 and ASan/UBSan. Synthetic controls exercise extended-only
inputs/results, signed zero, subnormal/NaN/infinity encodings, one through eight
live slots, precision/rounding state, malformed capabilities and bad host returns.
Hash-verified original probes run 0x4f4490 through conversions at 0x4f4504 and
0x4f451a and powers at 0x4f4532 and 0x4f454b, including the actual 0x4f1b52
math body and the two subsequent conversions. An independent native instruction
sequence matches captured operands, results and live state across ten dimension
pairs around powers of two. Ambient volume controls also compare ten arithmetic
states, stored binary64 bits and both unchanged CRT boundary inputs against
0x4b3bf0 over eighteen input/constant combinations. They include the finite
extended-exponent multiplication that overflows with premature binary64 math.
Independent register-indirect synthetic controls exercise cancellation, rounding
ties, signed zero, special encodings, every depth/TOP and malformed new requests.
These are transport tests, not family fixtures.

Addition controls also execute the unchanged dialog spans at `0x4e281a` and
`0x4e2832`, including their original `__ftol` calls. Native steps match the full
pre-conversion stack/CW/SW and the conversion's state and EDX:EAX for every TOP,
minimum/full depth, extended cancellation, ties, extended exponent range, signed
zero, subnormal and NaN inputs. Independent synthetic memory-indirect additions
check known result bits, every live depth, malformed requests and corrupt host
responses. Family geometry then preserves all four original conversion boundaries
and actual binary64 scale/x store points; these checks do not establish app
Controls acceptance or elect an app arithmetic backend.

Zero-input producer controls cover initial depths zero through seven, full-stack
rejection, exact extended result bits, lower live values, all TOP positions,
CW/SW, two-word argument order, cdecl/stdcall/thiscall cleanup, and malformed
requests and host receipts. Hash-verified state-five probes execute the unchanged
calls at `0x45f1ef`, `0x45f1fc` and `0x45f26c`, including original floor/ceil
at `0x4a4350`/`0x4a4250`, caller cleanup and conversion at `0x4a30e0`.
They supply finite signed binary64 inputs, signed zeros, integers and adjacent
rounding boundaries with empty and nonempty x87 stacks; native transport of
each result into the original conversion matches the captured state and integer.
These focused callsite spans do not establish whole state-five caller parity.

All 23 spatial_grid owners remain intact. No CRT recovery, family admission or
app integration follows from this prerequisite. The app has no elected extended
arithmetic backend; before app integration the owner must choose faithful native
x87 numerical emulation or explicitly authorize a replacement math policy with
an agreed equivalence contract. The current comparison support does not make
that policy decision or silently select platform `double` math.

### Scoped native entry frames

`ClawHost.entryStackPointer` initializes `Run.frame`; zero preserves `CLAW_STACK_TOP`.
Outgoing `Run.stackPointer` remains zero until the translation explicitly tracks
the **callee-entry ESP**, including the return word already pushed by CALL.
The native app accepts descending canonical nesting only with that explicit
value. Never infer it from argument count or a guessed local-frame size.
`automatic(4)` addresses the physical first incoming argument slot, as well as
negative offsets addressing locals. Owned C++ calls must still model and restore
their own frame when needed; the entry channel does not discover internal calls.

The app owns one pinned stack backing for a synchronous outer call graph at
`[0x01ff0000, 0x02010000)`. Parent aliases survive descendant calls; all stack
resolution ends at outer return/fault. This is not per-local lifetime checking.
The return word is a transport sentinel, not an original return PC; functions
that inspect their return-site identity need a separate contract. Canonical
EDX/x87 entry operands and untracked nested calls remain unsupported.

A non-NULL `ClawHost.remainingOperations` shares a pinned UInt64 operation
counter across the graph; zero is exhausted. NULL preserves the comparison
harness's independent per-Run budgets. Hosts must restore scoped frame/budget
pointers on unwind without clearing the first fault or refunding consumed work.
Changing ClawHost requires recompiling consumers and updating ctypes together;
the harness verifies native sizeof/offsetof for ClawHost, ClawCall and
ClawCompilerContext before executing any entry.

### Explicit compiler contexts

`ClawCall.compilerContext` and `ClawHost.compilerContext` are borrowed synchronous
pointers. NULL preserves the ordinary ABI. Compiler entries must use the separate
`CLAW_COMPILER_MODULE_ENTRY` macro; ordinary `CLAW_MODULE_ENTRY` rejects an active
compiler context. Canonical families may declare this convention explicitly as described below.
The shipping app rejects compiler-context dispatch until its host supports it.

`ClawCompilerContext` has size 72 and version 1. Set `size`, `version`, both masks,
all selected register fields, `continuation`, and zero both reserved words. Masks
use `CLAW_CONTEXT_*` bits. Input and output require EAX, EBP, ESP, EIP and FS_HEAD;
EBX, ECX, EDX, ESI, EDI and arithmetic EFLAGS are optional. Unselected machine input
registers start at zero (EFLAGS at 2); unselected output fields remain unchanged.
EFLAGS accepts only arithmetic flags and fixed bit 1, with bit 1 set. Unknown or
missing mask bits, mixed ordinary operands, malformed frames, invalid FS heads,
unsupported code addresses and altered output contracts fail closed.

The caller supplies the complete guest stack and genuine return word itself.
Input EIP equals the callee; output EIP equals `continuation`, an executable
original PC distinct from `CLAW_STACK_RETURN_SENTINEL`. A compiler transfer may
return with ESP below entry and may jump directly to its continuation. The stack
and registration head stay inside the bounded guest stack; FS may also hold the
terminal head `0xffffffff`. EBP is opaque uint32 register data; dereferencing it must use checked guest memory,
and nonterminal FS must identify an aligned twelve-byte registration record.

`run.context_call(function, context)` invokes this explicit channel and validates
its result. The host must validate code identities and context lifetime, provide
bounded stack backing, and never reinterpret a compiler call as cdecl0. On the
comparison side, `Machine.call_context`, `Env.run_original_context`, and
`Env.run_native(..., compiler_context=context)` provide explicit low-level entry.
The latter two consume stack bytes prepared through `env.put` during setup.
Canonical cases use the explicit contract below; admission thresholds are unchanged.

Bridges transfer the active FS head and stack bytes in both directions. Ordinary
bridges preserve the existing thread head; only ordinary outer calls initialize
it. Unicorn register snapshots keep bridge execution from destroying an enclosing
machine context. Exact continuation hooks and code-cache invalidation make repeat
runs independent of previously translated stop addresses. Thread state beyond
FS:[0] is not transported by this ABI.

No guest exception is encoded in `CLAW_FAULT_*`, and `claw::Failure` remains a
native safety failure. The ordinary/source comparison ABI does not yet transport
guest exceptions or dispatch native catch funclets.

`GuestExceptionRunner` in `guest_exception.py` is a separate, opt-in original-only
driver. It intercepts physical RaiseException/RtlUnwind while executing the
original registered handlers, type search, cleanup and rethrow code. A caller
must supply allowed handler identities; stack bounds, live registration and
record lifetimes, instruction/depth limits and supported dispositions are checked.
It returns an explicit `returned` or `unhandled` result; unsupported behavior
raises a harness fault. Neither noncontinuable throws nor unwinds become ordinary
successful source returns. The driver is single-use and removes its hooks on exit.

`make selftest` includes the driver's synthetic controls. This layer provides
original execution evidence only: native owned-funclet dispatch, exception
transport through ctypes and family exception outcomes remain unfinished. Do not
use it to claim native exception parity or convert an admission halt into return.

`make selftest` exercises independently authored synthetic x86 and native callers
at O0/O2 and under ASan/UBSan, including real return identity, selected outputs,
preserved registers, nested FS, malformed contracts and stack boundaries. It also
runs six hash-checked unchanged original helper readiness probes. Those probes
establish transport readiness only; they are not native helper parity/admission.

## Writing cases

The cases file defines `cases(random_source)` and yields `Case` objects.

```python
Case(label, function, setup=None, receiver=0, arguments=(), compare_eax=None, expect="return",
     covers=(), compiler_context=None, source_context=None, source_return_pc=0, receiver2=0,
     initial_stack=())
```

`setup(env)` builds the initial memory and returns anything, usually a dictionary of addresses. `receiver` and each argument are either numbers or functions of what `setup` returned.

Ordinary cases may opt into nonzero local stack backing with `initial_stack`,
a sequence of at most 256 `(offset, bytes)` regions, or a function of the setup
tokens returning that sequence. Offsets are negative integers relative to entry
ESP. Every payload must be nonempty immutable `bytes`, lie entirely below entry
ESP within the bounded stack, and not overlap another region. For example,
`initial_stack=((-16, b"\x78\x56\x34\x12"),)` supplies one local word.
Draw payloads from the case random source to vary them on unseen seeds.

The runner validates and freezes this input after setup. Each ordinary side
first clears its stack, then copies the frozen regions, then materializes the
return sentinel and incoming arguments in disjoint slots at and above entry
ESP. Repeated runs and original bridges preserve this input through the normal
memory transport. Empty input retains the existing zero-stack behavior; raw
`env.put`/`env.write` stack setup remains exclusive to explicit context entries.
This input cannot be mixed with compiler/source contexts or guest exception
graphs. Low-level controls use `env.initial_stack(regions)` before `_freeze()`;
relocated entry frames are checked again against the lower stack bound.
There is no native app ABI change and no new final-stack comparison rule.

Independent transport controls, including omitted-initializer sensitivity,
malformed regions and one-sided seed corruption, run with:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.initial_stack --all
```

Inside `setup`, and inside fixture effects, `env` offers:

| Call | Meaning |
| --- | --- |
| `env.object(size, name, words=[...], data=b"...", fill=0)` | A new live heap object. Returns its address. Memory outside live objects is random bytes, and native code that touches it faults. |
| `env.put(a, w0, w1, ...)`, `env.get(a)`, `env.write(a, bytes)`, `env.read(a, n)`, `env.cstr(a)` | Memory access. Works for the heap and for the program's global data. |
| `env.stub(name, convention, argc, effect)` | A fresh fake function address, for vtable slots and callbacks. Returns the address. |
| `env.override(address, effect)` | Replace a declared fixture's behavior for this case. |
| `env.release(a)` | Mark an object freed. |
| `env.calls_so_far(function)` | How many times this side has called a fixture, counting the current call. |

An effect is `effect(env, call)` and returns EAX. `call.arguments` are the stack arguments and `call.receiver` is ECX. Ready-made effects are in `fixtures.py`: `returns(v)`, `sequence(v1, v2, ...)`, `allocate(fail=False)`, `release()`, `store_words(argument, [words], result)`, `halt()`.

Effects run once on each side, so they must not keep state of their own. Use `env.calls_so_far`.

Draw at least some inputs from `random_source`. The admission gate runs the cases with a seed the author never saw.

What good cases cover:

- Every owned function called directly at least once.
- Every branch of every owned function. `make cases-check` lists the byte ranges never executed.
- Each failure path a fixture can produce: allocation returns 0, a callback returns an error.
- The value a callee may change behind the function's back: have a fixture effect change a field the function reads again afterwards.
- Boundary values: zero, one, negative counts, the largest size.

### Canonical compiler-context families

Declare every owned entry in the module with this explicit shape:

~~~json
{
  "address": "0x401000",
  "convention": "compiler-context",
  "argc": 0,
  "returns": "context",
  "compiler_context": {"input_mask": 2047, "output_mask": 2047}
}
~~~

The masks are the exact permitted case masks, using the version-1 transport bits
above (0x7ff selects all fields; 0x5c1 is the required minimum).
argc: 0 prohibits ordinary operands; it does not make the entry cdecl.
A module cannot mix ordinary and compiler-context entries. Ordinary signatures
cannot carry compiler_context contracts; they may separately opt into source_context.
Compiler entries and dependencies cannot be fixtures.

In setup(env), create a NativeCompilerContext (from clawparity.env) and write
the complete initial stack with env.put or env.write, including its genuine
continuation word when the source code uses one. Return the context as a setup
token, then yield Case(..., compiler_context=lambda tokens: tokens["context"]).
Resolution happens before the memory snapshot is frozen; each side receives its
own context copy. Receiver and arguments must be zero/empty. compare_eax
overrides and expect="halt" are rejected: the special entry must complete at
the genuine continuation.

Native modules use CLAW_COMPILER_MODULE_ENTRY(entry, owned, body) with a boolean
ownership predicate and void body(Run &, uint32_t function, ClawCompilerContext &).
Read selected input fields, use bounded run.get/put operations for stack
effects, and update selected outputs only. The macro verifies the immutable
contract and preserved unselected fields. The runner additionally compares the
complete context header, every selected output, preserved unselected fields,
and **all 128 KiB of guest stack backing**, with no excluded stack ranges.
Existing events, heap, globals and lifetime comparisons still apply.

Cases-check validates original heap accesses and records actual original
instruction coverage through the context entry. O0/O2, unseen seeds, sanitizer
and mutation gates use the same path. Context and stack differences count as
observed mutation kills. No threshold changes or source exception simulation
are part of this feature. make selftest generates an ignored synthetic family
under work/pilot/compiler_family_selftest; its gate result admits no game code.

Drafting requires explicit masks:

~~~sh
work/test-env/bin/python -m tools.claw draft --id example_context --title "Compiler helper" \\
  --seeds 0x401000 --compiler-context --context-input-mask 0x7ff --context-output-mask 0x7ff
~~~

Review the exact original ownership and context boundary before giving the packet
to independent case-author and translator roles. Generated app registries expose
CLAW_CANONICAL_COMPILER_CONTEXT and CLAW_CANONICAL_RETURN_CONTEXT metadata;
dispatch fails closed for special entries and any nonnull context until the
shipping host explicitly supports the capability. A family gate is not app
election, startup completion, or device acceptance.

### Bounded guest exception families

The currently supported guest contract is the complete MFC singleton root and
its attached typed catch. `oracle.guest_graph` selects this strict contract;
partial or unknown guest metadata is rejected. `owned[].body_ranges` retains
all owned bytes, including any justified unreachable coverage exemptions.

Cases supply full `NativeSourceContext`, a genuine original caller continuation,
and one of the declared original factory pointers. Use `expect="return"` for
normal completion or `expect="unhandled"` for genuine exception dispatch and
cleanup. `expect="halt"` remains a physical service stop. Never override the
driver-owned RaiseException/RtlUnwind services, seed an attached catch directly,
or substitute internal callbacks with `env.stub`.

The original baseline executes independently of native exports. The native side
guards the complete owned body against original execution and enters the native
catch only through the original dispatcher. Both sides compare full terminal
CPU/FS/stack, physical transfer snapshots, memory and allocation ownership.
Unhandled outcomes have no fabricated normal root epilogue.

Admission requires observed original execution of every declared factory on
both returned and unhandled paths. Warm-owner cases alone cannot provide factory
execution credit. Every unhandled case must exercise the original catch and
exactly one native catch invocation. These are family comparison requirements,
not proof of a shipping native CRT or connected app startup.

### Ordinary ambient source contexts

An ordinary function that needs physical source frames or inherited CPU state
opts in per entry with `source_context`. It retains `cdecl`, `stdcall`,
`thiscall`, or `fastcall`, its ordinary `argc`, and `u32`/`void` return type:

~~~json
"source_context": {"input_mask": 2047, "output_mask": 1523, "preserve_mask": 1138}
~~~

These example masks are `0x7ff/0x5f3/0x472`; their suitability must be proven for
the particular entry. Input requires EBP/ESP/EIP/FS (`0x5c0`), output requires
EAX/ESP/EIP/FS (`0x581`). Preservation may select only EBX/ESI/EDI/EBP/FS
(`0x472`), and every preserved field must be selected as both input and output.
No register value, including EBP=0 or FFFFFFFF, grants memory access.

`ClawSourceContext` is a distinct 72-byte structure: size/version/inputMask/
outputMask; eax/ebx/ecx/edx/esi/edi/ebp/esp/eip/eflags/fsHead; preserveMask/
reserved0/reserved1. Version is 1; reserved words are zero. `ClawCall` and
`ClawHost` append `sourceContext` and `sourceReturnPC` after `compilerContext`.
A call never selects both channels. A source-capable entry cannot be entered
with fabricated zero CPU state by a legacy context-free caller.

Use `CLAW_SOURCE_MODULE_ENTRY(symbol, owned, contract, body)`. The ordinary
`owned(function)` returns argc or -1. `contract(function)` returns
`ClawSourceContract{inputMask, outputMask, preserveMask, returnPopBytes}`;
returnPopBytes is zero for cdecl or four times argc for callee-pop conventions.
An all-zero contract explicitly selects a context-free ordinary entry in a
mixed ordinary module; it rejects a supplied source capability.
The body retains `(Run &, function, receiver, arguments)` and accesses CPU data
through `run.source()`. Model original stack/prologue/epilogue writes explicitly,
leaving ESP at the original entry slot before returning. The wrapper checks the
physical return/argument words, normalizes undeclared inputs to zero (EFLAGS=2),
performs the conventional RET, preserves undeclared output fields from the input
envelope, and checks declared preserved witnesses. Cdecl/stdcall receiver=0
in the call envelope does **not** erase selected source ECX/EDX.

`run.source_call(function, receiver, realReturnPC, childContext, arguments={},
receiver2=0, returnPopBytes=0)` transports an ordinary child at childContext.esp.
The child context is a separate borrowed value; translated source instructions
explicitly update the parent's working state from child outputs. Translated
PUSH instructions must already materialize the exact return word and argument
slots; the comparison host validates them without repair. Special children continue to use
`run.context_call`; a source parent declares each special dependency as
`kind: whole`, `convention: compiler-context`, `argc: 0`, `returns: context`,
with exact `compiler_context` masks. They execute unchanged original instructions
on the comparison side and cannot become fixtures. Whole ordinary dependencies
using source transport declare ordinary signatures plus their `source_context`.
Physical fixtures retain ordinary signatures; their `Call.source_context` and
`Call.source_return_pc` expose the observed CPU inputs and actual return word.

For a direct original JMP, case setup elects
`env.source_tail_edge(callerEntry, originalJumpPC, targetEntry)`. This verifies
the original direct-JMP instruction and requires a declared whole original
target; physical fixtures cannot replace that target. The initial tail domain
is cdecl0/thiscall0 with full `0x7ff` integer input/output masks and RET0.
Original descendants run normally; only tails performed by the native owned
caller need an elected comparison edge.

Translated code sets the parent's EIP to the original JMP site, copies its live
CPU into a separate child context with the target's declared header and EIP,
then invokes `run.source_tail(target, receiver, originalJumpPC, childContext)`.
It inherits the existing physical frame and return word. It never pushes a
return or returns to translated instructions. The host publishes a versioned
returned disposition tied to that exact borrowed request only after the target
returns; the entry wrapper consumes it once, preserves its own immutable header
and exports the returned CPU without another RET. Faults and nonreturning
physical stops retain the deepest CPU/stack prefix and publish no returned
disposition. Guest transfers, stack arguments, RETn and unelected shipping
edges remain unsupported. Synthetic transport checks establish this harness
boundary; they do not admit a game wrapper or prove static startup.

Create `NativeSourceContext` in setup, then yield
`Case(..., source_context=lambda tokens: tokens["source"],
source_return_pc=realPC)`. Ordinary receiver/arguments remain conventional;
`receiver2` is available only for explicit source fastcall. Each side receives
its own context copy. Returning cases compare declared state, the immutable
header, restoration witnesses and **every byte of the bounded stack**, including
all real PCs. `Machine.call_source` stops at the genuine continuation and checks
actual conventional return pop. Legacy `Machine.call` retains its old behavior.

`expect="halt"` is also supported for an honest physical-service prefix. Both
sides must reach a real declared fixture that raises `Halt`. The runner compares
all stack bytes, events, heap/globals/lifetimes, the immutable root header and a
complete CPU snapshot at that same physical stop (function, real return PC,
registers and FS). A direct native physical halt requires inputMask=0x7ff so no
unknown register is silently treated as observed. Original descendants capture
the live Machine state before restoring a suspended bridge. Root epilogue and
return-preservation assertions do not apply before return; suspended parent
registers are not confused with the deeper physical stop. ABI/memory/budget
faults, a fabricated CLAW_FAULT_HALT without a physical stop, and missing stop
state fail. This is prefix evidence, never typed EH, unwind, or successful return.

The comparison host owns one synchronous source graph, shared native/original
bridge operation budget, bounded bridge depth, CPU snapshots and stack backing.
It retires host pointers/PCs on exit and rejects reentrant outer-graph reuse.
Code identity is checked against the comparison program/import metadata. Shipping
requires its own admitted-entry/callsite authorization, logical-thread/TLS lifetime
and native owner; generated dispatch rejects source capability, source pointers
and sourceReturnPC until that host exists. No raw source CPU state executes native
game code or supplies an emulator in the shipping app.

Draft an ordinary source entry with `--source-context --context-input-mask ...
--context-output-mask ... --source-preserve-mask ...`; review its inferred ordinary
signature and exact callsites before sealing independent cases/translation.
The source transport and synthetic family selftests cover real frames, mask modes,
opaque EBP domains, callbacks, original special/ordinary children, halt prefixes,
safety failures and generated fail-closed dispatch at O0/O2 and under sanitizers.

## Reading a failure

`make oracle FAMILY=<id>` prints one JSON line. Each entry in `failures` has a `kind`.

| Kind | What it means | Usual cause |
| --- | --- | --- |
| `event` | Outside call number `index` differs. | Wrong callee, argument or order. |
| `event-memory` | Same outside call, but memory already differs when it is made. | A store before that call is wrong or missing. |
| `event-count` | One side made more outside calls. | A missing or extra call, or a wrong branch. |
| `heap` | Heap differs after return. Lists the first differing words. | A wrong store. |
| `globals` | The program's global data differs after return. | A wrong store to a global. |
| `ownership` | Different objects live or freed. | A missing or extra free. |
| `return-value` | EAX differs. | |
| compiler-context | Special-entry contract or register output differs. | Wrong selected output, changed header, or unselected field corruption. |
| stack | Special-entry guest stack bytes differ. | Missing, extra or misplaced compiler frame stores. |
| `native-fault` | Native code stopped: `memory` is an access outside a live object, `unimplemented` a stub, `budget` a runaway loop, `abi` a wrong argument count. | |
| `halt` | Only one side stopped at a `halt()` fixture. | |
| `specification` | The original's stack pointer after return contradicts the declared convention or argument count. | Report it. Do not work around it. |
| `harness` | The case or the specification is wrong: an import with no stand-in, a bad address in `setup`, an emulation fault. | Fix the case, or report a specification problem. |

## Commands

| Command | Purpose |
| --- | --- |
| `make lint FAMILY=<id>` | Check the specification against the disassembly. |
| `make skeleton FAMILY=<id>` | Generate the module and cases stubs. |
| `make packet FAMILY=<id>` | Build the task packet under `work/packets/<id>/`. |
| `make feedback FAMILY=<id>` | Write blind case-author feedback under `work/gate/<id>/case-author-feedback.json`. Never give a case author `gate.json`: it contains native source snippets. |
| `make cases-check FAMILY=<id>` | Run the cases on the original alone. Reports case errors and coverage. |
| `make oracle FAMILY=<id>` | Run the comparison. Add `ARGS="--seed 7"` for another seed. |
| `make mutants FAMILY=<id>` | Break the module in small ways and check the cases notice. |
| `make gate FAMILY=<id>` | The admission gate. |

Mutation jobs default to four. Use `ARGS="--record --jobs 1"` on `make gate`
when other jobs are already using the Mac. Refresh a packet before starting a
worker so its protected specification hash includes the latest recorded gate.

Literal return mutations flip zero/one in generated `function_<address>`
implementation bodies only when the manifest declares a consumed `u32` result.
Normalized void results and arity/dispatch helpers are excluded. This conservative
selector masks comments/strings and rejects raw strings, line continuations,
conditional preprocessing and nested return bodies rather than guessing which
text executes. It complements the existing store/call/branch mutations; the
mutation-score threshold is unchanged.

Standalone `run.source_call` statements also participate in drop/swap mutations.
Literal source CALL/JMP targets and continuation/JMP sites receive separate
one-byte shifts. Tail operations remain terminal and are never dropped or
swapped. New edge selectors mask comments/quoted strings and conservatively
skip raw strings and line splices; they do not parse conditional preprocessing
or multiline calls. The gate samples candidates at its existing limit, so a
passing result does not mean every candidate was tried.

Equivalent-mutant reviews belong to the coordinator, never to a translator or
case author. `make mutants` reports the current `source_sha256` and each
survivor's `mutant_sha256`. After proving that the specific change cannot affect
any permitted input, record `line`, `operator`, both hashes and `reason` in
`oracle.equivalent_mutants`. Any source change invalidates the review. The gate
reports reviewed equivalents separately and keeps the 0.9 threshold unchanged.

### Opt-in named-layout mutations

Set top-level `"mutation": "named-layout"` and include both
`Sources/ClawRecoveredLayout.h` and `Sources/ClawRecoveredNames.h` in `sources`
so the build cache binds their contents. The admission inputs select
`named_layout_mutants.py` and these headers only for the opt-in mode. Existing
families continue through the literal mutation implementation. Installing the
two common one-line dispatch/registration changes requires coordinator review
and an exact pin in the owner-approved admission migration before refreshing
unrelated admissions; do not re-gate the corpus just to install this opt-in.

The recovered layout header provides transport-bound `ActorFields`,
`LogicHolderFields`, and `ActorContextFields` views. For example:

```cpp
ActorFields actorFields{run, actor};
LogicHolderFields holderFields{run, actorFields.holder()};
uint32_t state = holderFields.state();
holderFields.state(uint32_t(BounceLogicState::Initialized));
```

Each `CLAW_RECOVERED_FIELD(name, offsetof(Layout, member))` must have a compiled
`static_assert` for that offset in the same header. Getters and setters use the
original guest token and `Run` transport. Mutation changes a **single call** to
`holderFields.state<4>()` or `state<4>(value)`, shifting that access by four
bytes. It never edits the shared header, another use, or an auxiliary source.
Keep production calls at the default delta. New layouts can add fields with
the same macro and checked-offset contract.

Use direct, uniquely typed view variables declared with `{run, token}` or
`(run, token)`, and keep each accessor call on one line. Split nested accessor
calls into separate statements. Aliased/pointer views, ambiguous shadowing,
explicit deltas, conditional preprocessing, raw strings and line continuations
are outside this selector and fail closed. This is a constrained source
selector, not a general C++ parser.

Behavior-named bodies retain either `case 0xADDRESS: return name(run, ...);`
registrations or `{0xADDRESS, name}` table rows. Every owned entry must register
one canonical `uint32_t name(Run &, uint32_t, const uint32_t *)` definition.
Consumed literal returns still mutate; normalized void returns do not. Calls
inside those bodies can redirect to another registered body with the same
calling convention, argument count and return contract. Explicit integral
`enum class` values swap to a different value in that enum; literal integral
`constexpr` uses receive a one-bit change. Comments, strings, registrations and
constant declarations are not mutation sites.

The old drop/store/swap/offset/branch/return sample is retained after expanding
the named uses for selection only. Additional named constants, call targets,
and otherwise missed field uses are tested **in addition** to that sample;
`--limit` limits the legacy pool, and zero selects all. Compilation errors and
timeouts remain invalid, not kills. Equivalence reviews and thresholds are
unchanged. Run the focused selector checks with:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.named_layout_mutants
```

The local-only player-actions demonstration uses the existing, unchanged 295
cases against the hash-checked original. A translator supplies an accessor-form
copy under `work/`, with its own opted-in spec; the proof compares the literal
mutation baseline, checks three named/literal negative-control pairs, and
verifies shared headers and retained family inputs stayed byte-identical:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.named_layout_mutants \
  --demo-spec work/readability/level_one_player_actions_01/named-layout-demo/spec.json \
  --baseline work/readability/level_one_player_actions_01/named-layout-demo/literal-mutations.json
```

### Optional ordinary source capability

An ordinary owned entry may declare `source_context.optional: true` together
with exact input/output/preserve masks. This explicitly keeps two independently
compared modes: cases without a context use the original ordinary ABI; cases
with a context compare the declared CPU, real return PC and full stack. Required
source capability remains the default. A source return PC or second receiver
without a context always fails. Optional mode is limited to cdecl, stdcall and
thiscall because the ordinary entry ABI does not transport EDX.

`CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(symbol, owned, contract, optional,
ordinary_body, source_body)` selects separate bodies. `optional(function)` is
an explicit per-entry boolean; false preserves strict source selection, even
in a mixed module. Neither body invents missing ambient CPU values. Both modes
must have independent original cases before an existing entry is re-admitted.
The skeleton generates unimplemented stubs and per-entry selectors; it does
not establish that the two bodies are equivalent. Generated capability values
are 0 (absent), 1 (required) and 2 (optional). The existing ordinary dispatcher
continues refusing every live context pointer or source return PC; the native
source graph owns contextual dispatch separately.

## Synchronous original dialog callbacks

The comparison harness can explicitly opt a source graph into one synchronous
physical DialogBoxParamA callback boundary. During setup, register a frozen
`DialogCallbackContract(program_sha256, service, call_pc, return_pc, target,
body_end, body_sha256)` through `env.dialog_callback(contract)`. The declaration
requires the unchanged original `CALL [IAT]` bytes, stdcall5 physical signature,
matching program identity and callback-body digest. Captain Claw v1.0 is pinned
to IAT 0x546d2c and these exact callsite/body pairs:

- CALL 0x453989, RPC 0x45398f: [0x453a10,0x453b0f).
- CALL 0x42bb7b, RPC 0x42bb81: [0x49b730,0x49b83d),
  [0x49b160,0x49b393), or [0x49b630,0x49b72b).

The program hash, complete body hashes and pairings are pinned in `Env`.
Register all needed targets separately; the active request's argument 3 elects
one of them. Other Claw targets/sites are rejected. This is a trusted declaration,
not permission for a case to substitute executable code.

Inside that active physical effect only,
`env.invoke_dialog_callback(call, (hwnd, message, wparam, lparam))` executes the
actual argument-3 DIALOGPROC as stdcall4/u32. Original-backed callbacks execute
unchanged original code on both sides. Declare `native_owned=True` for the owned
0x49b730 callback: on the native side it dispatches through the outer run's
selected module, including mutants, and cannot fall back to original code.
External 0x49b160/0x49b630 and the older callback remain original-backed.
It accepts no target, CPU context, stack pointer or return-PC override. Request
identity, complete source inputs, physical argument words, immutable contract,
registered service, VM and run lifetime are checked before execution. A copied,
retired, cross-VM or modified request fails. Callback registration grants no
ordinary source-callee authority and does not extend SourceFixtureCapability.

The callback graph uses a deferred physical-service pump. A code hook stops
Unicorn at the import; the effect runs after `emu_start` returns. Its callbacks
and their physical descendants resume the same live Machine with at most one
active `emu_start`. Existing graphs keep their prior execution mode. Callback
graphs share an instruction budget, bounded nesting and one monotonic deadline;
they never start nested Unicorn timers or reload a frozen initial snapshot.
Guest EH and the native guest adapter are excluded from this first capability.

The OS dispatcher model reserves 64 bytes below the physical entry ESP and then
places a 20-byte stdcall4 callback frame. Its return token at 0x720000 is explicitly
synthetic OS transport, not a game continuation; it is authenticated by the
active frame, exact resulting ESP and actual RET16 instruction. Callback code
that depends on the original OS dispatcher's frame/return-site identity is not
supported. Callback input CPU inherits the known physical-entry state, with
EIP/ESP selecting that frame. Normal return checks EBX/ESI/EDI/EBP, FS:[0], the
parent registration record and suspended physical argument/return words, then
restores the complete suspended CPU. Stack residue and guest memory writes stay
visible. Dispatcher overlap with a live parent FS record fails before entry.

Original-backed effects use live Machine memory directly. Native-backed effects
copy their current buffers into that Machine once and copy heap, globals and all
stack bytes back on every outcome. `env.callback_executions` records typed target,
arguments, actual entry observation, normal-return disposition and EAX. Original
callback descendants remain in the same ordered physical event history.

A deep physical Halt preserves its authenticated innermost CPU/FS/stack prefix
through enclosing services and bridges. Failed callbacks do not restore parent
CPU or run a root epilogue. Catching a callback fault/Halt inside a fixture cannot
turn it into a successful return; changing a captured stop also fails. Request
scopes and execution hooks retire on every exit.

The physical dialog fixture supplies messages and control storage. For Claw,
`end_service` defaults to IAT 0x546d34; synthetic modal tests can declare their
own EndDialog import. The transport binds modal state to the active request and
HWND. The first message must be WM_INITDIALOG with the unchanged initialization
parameter; repeated initialization, changed HWNDs, reentry and dispatch after
EndDialog are rejected. EndDialog must originate during the active callback and
succeed before its result can become the DialogBox result. A callback-free
creation failure may return -1; fabricated positive or cancel results fail.
EndDialog returns normally to the DIALOGPROC; the fixture stops dispatching after
the callback returns. Fixtures
must not write the game's dialog-result globals or fake callback effects. Native
sheets may eventually supply these messages through a separately reviewed app
adapter. Persistent window procedures require a different registration/handle
lifetime; this synchronous capability does not cover CreateWindowExA callbacks.

Owned native callbacks use the ordinary canonical entry ABI on the same borrowed
memory, with the parent's source channel suspended. The OS dispatcher owns the
native frame pop; it does not claim that native code executed a guest RET16.
The host supplies a separate `ClawCallbackCPU` lease through `host.callbackCPU`:
size/version, elected target, entry ESP, unique activation and complete live CPU.
`run.callback_cpu()` exposes that CPU; translated instructions update it and
materialize their real descendant return/argument words. Then
`run.callback_call(target, receiver, realReturnPC, arguments, popBytes)` sends a
separate child source context, the exact borrowed lease pointer and activation.
The child CPU must match the live callback CPU. Whole dependencies still require
explicit ordinary source signatures and execute unchanged original code;
physical services observe complete CPU inputs, including authentic Halt state.
The synthetic callback return never becomes an ordinary source continuation.

The lease is bound to this VM, program, contract, physical request and invocation.
Copied, stale, malformed or changed leases and mutation during a descendant's
borrow fail. Entry operands/frame, immutable headers, final nonvolatiles and FS
are checked. On return the dispatcher restores the suspended parent CPU; on Halt
or original fault it retains the deepest CPU and all stack/memory effects.
Legacy context-free owned callbacks remain supported, but cannot manufacture a
complete source Halt or borrow parent registers through this lease.
Original dependencies run below the live callback frame and share its budget and
deadline. Source-capable caller/root requirements are unchanged. A canonical
family must provide that caller transport before using this boundary; registering
a callback does not make an ordinary DialogBox call source-capable.

`physical_callbacks` selftests use independent synthetic x86 and a native caller
at O0/O2 and under ASan/UBSan. They exercise original, native physical and
native-to-original bridge routes; full stack and CPU parity; repeated callbacks;
FS/local alias preservation; deep Halt; malformed return/authority/lifetime;
shared budgets and hook exceptions; and controls that omit real callback effects.
These transport checks do not admit a game family or establish app acceptance.
Run `work/test-env/bin/python -m Tests.clawparity.selftest.physical_callbacks`
(also `--O0`), and call this module's `sanitized_checks()` for ASan/UBSan. The
focused checks include hash-verified original player-cache callsite probes,
positive removal through original lookup/selection/EndDialog, the older callsite,
native-backed memory parity, selected-owner mutation controls and modal failures.

## Ordinary DirectDraw enumeration callbacks

During case setup, register the physical COM service with `env.stub` as
`stdcall5`, then elect an `EnumerationCallbackContract` with
`env.enumeration_callback(contract)`. The contract contains `program_sha256`,
`service`, `target`, `body_end` and `body_sha256`. Claw's target/body are pinned
to `[0x4bcda0, 0x4bcdd5)`. The service's five operands are the interface, flags,
descriptor filter, context and actual callback target.

Inside that service effect, call
`env.invoke_enumeration_callback(call, (descriptor, call.arguments[3]))` for each
physical mode, respecting the callback's returned enumeration disposition.
Each descriptor needs a live 0x6c-byte allocation. The helper validates the
active request identity, service registration, passed target, uint32 operands,
unchanged context and executable identity. It accepts only ordinary roots;
source/compiler contexts, guest EH and window/dialog capabilities cannot mix
with this election. Copied, cross-run, retired and unsupported requests fail.

On the original side, the actual callback executes in the suspended VM and
must perform `RET 8`, preserve nonvolatile registers/FS and leave its suspended
physical request frame intact. On the native side, the callback enters the
**same selected module entry** passed to `run_native`, including a selected
mutant. A missing owner or failed native entry faults; the owned original body
cannot serve as a native fallback. Fixtures supply modes, never the game's
allocation/copy/append logic or its global enumeration array.

Heap, globals, allocation state, stack aliases and nested fixture events remain
live across callback/bridge transitions, including failure prefixes. Canonical
incoming arguments are materialized as a return word and two stack words.
Dispatcher frames descend in 0x1000-byte steps below the root/bridge frame;
callback original dependencies use a lower bridge frame. These are bounded
ordinary transport frames with a synthetic return token, not original OS frame
identities. Code requiring exact dispatcher ESP/return-PC values, hidden CPU
inputs or more stack than the reserved separation is outside this profile.
No native app ABI or display integration is added.

The graph shares its operation counter, a deadline of at most 30 seconds and
a callback depth limit of 16 (stack bounds may reject earlier). Failure poisons
the synchronous graph even if an effect catches it; public mutations cannot
continue afterward. Unwind restores borrowed host frames, backend and suspended
CPU without rolling back guest writes or refunding the budget. Top-level runners
cannot reset a live enumeration graph.

Run the focused transport check serially with other heavy jobs:

```sh
work/test-env/bin/python -m Tests.clawparity.selftest.enumeration_callback --all
```

It checks synthetic ordinary/native/bridge ordering and stack aliases, selected
native mutants, invalid targets/operands/lifetimes, failures, limits and malformed
stdcall returns at O0, O2 and ASan/UBSan. O2 also runs the existing stdcall4
physical callback regression controls. Its hash-verified real profile executes
`0x4bcc50 -> 0x4bcda0` with three unsorted descriptors, comparing all fixture
events, live heap/global state and allocations and checking the final sort.
This is callback transport evidence only; graphics case expansion and family
admission remain separate work.

## Limits of this version

Canonical calls support at most 32 stack words (`CLAW_CALL_ARGUMENT_CAPACITY`),
including words in by-value aggregates. The Python binding and native hosts
use this same bound; the harness verifies capacity, size and field offsets
before execution. Over-capacity counts fail before reading any argument.
Run `work/test-env/bin/python -m Tests.clawparity.selftest.wide_calls --all`
for independent old/new-limit, final-word and stack-cleanup checks at O0/O2
and under ASan/UBSan. Changing the capacity requires rebuilding all consumers.


The comparison stack is bounded to `[0x01ff0000, 0x02010000)` (128 KiB).
Its lower backing includes room for large original compiler stack probes;
the outer entry remains `CLAW_STACK_TOP = 0x02008000`, the default original
bridge entry remains `0x02004000`, and the stop address remains `0x0200f000`.
An explicit `run.stackPointer` still selects the original callee's frame.
Growing the backing does not relocate escaped locals, allocate a fresh frame
for recursive native dispatch, or change the separate-frame responsibility
of callers. Both bounds remain enforced; the live-object heap policy is
unchanged. `make selftest` checks large executable probes, nested local aliases,
full bridge copies, exact bounds, and native arena access under ASan/UBSan.
It also runs the hash-checked original CRT stack probe without fixtures.

- An outer owned function returning in x87 uses the comparison-only `x87_result` channel above; the app host does not serve it yet.
- A fixture cannot return a floating-point value.
- Legacy context-free ordinary stack memory is not compared. Source-capable ordinary and explicit compiler-context entries compare the full bounded stack, including physical halt prefixes for source entries.

## Opt-in original window creation callbacks

`WindowCallbackContract(program_sha256, target, body_end, body_sha256,
register_site, create_site)` is a separate setup declaration. Each site is an
immutable `(IAT, CALL, returnPC)` tuple. Claw v1.0 pins original WNDPROC
[0x4b8500,0x4b87e1), RegisterClassA (0x546bd4,0x4b8af8,0x4b8afe), and
CreateWindowExA (0x546bf8,0x4b849c,0x4b84a2). The ABI is stdcall4/u32 RET16.
This does not change DialogCallbackContract or SourceFixtureCapability.

Inside the real RegisterClass effect, `env.register_window_class(call, atom)`
snapshots the actual pointed 40-byte WNDCLASS, module and bounded class-name
string. Return its result from the effect. Registration commits only when the
physical effect returns that same canonical nonzero 16-bit ATOM. A zero physical
result before registration creates no authority. Duplicate class/module or ATOM
registration is rejected. Later changes to descriptor storage do not retarget
the immutable registration; a later CreateWindow class/module must still match.
This first profile supports exact class-name strings, not MAKEINTATOM input.

Inside the matching CreateWindow effect, use
`with env.window_operation(call, hwnd) as lease:`. The nonzero physical HWND is
bound to a fresh incarnation and the committed registration. Parent/menu/lpParam
must be zero in this first profile. The lease exposes three physical transient
objects: `create_struct` (48 bytes derived from all actual API arguments),
`minmax_info` (40 bytes), and `window_rect` (16 bytes). Fill the latter two with
coherent physical display/geometry inputs, then call
`env.invoke_window_callback(call, lease, message, 0, pointer)`.

The bounded creation profile is GETMINMAXINFO (0x24/minmax_info), NCCREATE
(0x81/create_struct), NCCALCSIZE (0x83/window_rect), CREATE (1/create_struct),
in that order. NCCALCSIZE currently supports only FALSE/RECT. Each invocation
executes the actual registered original callback; there is no target/CPU/frame
selector. GETMINMAXINFO/NCCALCSIZE return zero; NCCREATE zero rejects creation;
CREATE returns zero or UINT32_MAX, the latter rejecting creation. A rejected
session cannot invoke another callback or return a successful handle. A normal
success must return the reserved HWND after all four callbacks; the enclosing
physical-service hook checks this before marking it live. A physical zero before
any messages is also allowed. Transient objects retire on ordinary completion.
A failed incarnation may be reused numerically by a later genuine CreateWindow
request, with a fresh lease. A live incarnation cannot be reused in this increment.

Registration lasts across physical calls within one comparison run; the lease
lasts only inside its exact active creation effect. Copied, stale, cross-VM or
cross-request authority fails. Both active backing and Machine code bytes for
both sites and the original body are checked. Native-owned callback roots are
excluded only during the native graph lifetime. The existing deferred pump,
synthetic OS dispatcher, shared operation/depth/deadline bounds and normal-return
CPU/FS validation are reused without kernel changes. Deep Halt/fault preserves
the innermost CPU, memory, stack and event prefix; catching it cannot commit a
window, release its transient storage or mutate public guest state afterward.
All authority retires when the outer graph ends; `window_history` retains the
physical registration/message/disposition trace for comparison diagnostics.

This is a bounded comparison profile, not an exhaustive Windows message schedule.
The first original readiness executes real CRT heap/lock initialization, owner
construction and 4b89d0 until the unsupported ShowWindow boundary. Its borderless
640x480 physical profile sends all four messages through the original WNDPROC,
prefilter and fixed CREATE handler, preserving the full client RECT. It does not
implement ShowWindow, DestroyWindow, queued dispatch, activation, or failure
cleanup callbacks. Those require separately reviewed physical message contracts.
The game reads singleton 0x54133c; callbacks never gain a fabricated userdata
binding. Source code alone writes that singleton, Q+4 and other owner state.
Factory/app initializer 0x425730 and whole WinMain success remain separate work.

## Opt-in first ShowWindow and derived default callbacks

`WindowShowContract(window_contract, show_site, default_sites)` is an additional
setup election made with `env.window_show_callback(contract)`. It requires the
same elected `WindowCallbackContract` object and committed registration/handle
incarnation. Claw pins ShowWindow `(0x546b54,0x4b84b0,0x4b84b6)` and both actual
DefWindowProcA sites `(0x546bf4,0x4b8521,0x4b8527)` and
`(0x546bf4,0x4b87d5,0x4b87db)`. The callback body and every elected CALL are checked
in both active native backing and Machine memory before every invocation.
The Show ABI is stdcall2; the default ABI and original callback are stdcall4.
There is no caller-selected callback target, CPU, stack frame, or continuation.

In the actual ShowWindow effect use
`with env.window_show(call, WindowShowProfile((x,y,width,height), flags)) as lease:`
and execute each tuple from `env.window_messages(call, lease)` with
`env.invoke_window_message(call, lease, *message)`. Return zero after the scope:
this profile starts hidden, so zero reports previous visibility, not failure.
Only command1, an unshown committed popup handle, and the explicit first-show
profile are accepted. Repeat show, missing messages, unsupported flags, mutated
payloads, wrong result, or another handle incarnation fail closed. The profile
has no launcher STARTUPINFO override, no prior active/focused window, no nonclient
frame and no app-present callback handling. It fixes style0x80080000/ex-style0x40008 and accepts
only SHOWWINDOW, NOSIZE, NOMOVE, NOZORDER and FRAMECHANGED position flags. Position
and dimensions use bounded signed16/positive15-bit ranges, respectively.

The declared schedule is WINDOWPOSCHANGING46, NCCALCSIZE83 when size is not
suppressed or FRAMECHANGED is set, WINDOWPOSCHANGED47, ACTIVATEAPP1c,
NCACTIVATE86, ACTIVATE6. It is a deterministic comparison input, not a recovered
universal historical Windows ordering. The original readiness uses unchanged
640x480 geometry with flags0x43; a separate frame-change profile uses0x63.
Synthetic geometry-change profiles independently exercise child transport; they
do not prove the original first-show geometry changed. NOSIZE/NOMOVE flags must
agree with the actual CreateWindow dimensions/position. Each show owns a
WINDOWPOS28 and NCCALCSIZE_PARAMS52 (three RECTs plus the WINDOWPOS pointer).
The pointer and old rectangles are immutable; this first popup profile permits
only the full-window client rectangle and result0. Creation still uses the
separate FALSE/RECT16 schema. [WINDOWPOS](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-windowpos),
[NCCALCSIZE](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-nccalcsize).

Inside a real default effect reached by a show callback, use
`with env.window_default(call) as child_lease:` and execute its `window_messages`
plan through the same invocation API. Authority is derived from the currently
suspended original callback and its exact HWND/message/wParam/lParam. The
current DefWindowProc CPU/frame owns its children; the outer Show CPU cannot be
substituted. Default47 derives SIZE5 and MOVE3 according to NOSIZE/NOMOVE and the
validated geometry. Default ACTIVATE6 derives SETFOCUS7 for the selected active,
non-minimized, no-previous-focus profile. Other supported defaults are leaves.
If original source consumes47 without calling the physical default, no children
are fabricated. Once a default request exists, omitting its required children
is an error. Default86 returns1; the remaining defaults return0.
[WINDOWPOSCHANGED](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-windowposchanged),
[ACTIVATE](https://raw.githubusercontent.com/MicrosoftDocs/win32/docs/desktop-src/inputdev/wm-activate.md).

Show1 excludes WM_SHOWWINDOW by the documented SW_SHOWNORMAL exception.
[ShowWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow),
[WM_SHOWWINDOW](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-showwindow).
Painting is explicitly deferred in this profile: the popup has no nonclient
frame to repaint; successful show marks client painting pending. No UpdateWindow,
RedrawWindow or queue dispatch is performed. Those calls and frame/background
paint obligations would require a separate reviewed capability. This does not
claim a visible rendered frame or exact Windows-version paint timing.
[WM_NCPAINT](https://learn.microsoft.com/en-us/windows/win32/gdi/wm-ncpaint),
[WM_PAINT](https://learn.microsoft.com/en-us/windows/win32/gdi/wm-paint),
[UpdateWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-updatewindow).

All leases are immutable identity tokens with graph-generation and handle
incarnation checks; default authority additionally has one active callback
lineage. Leases and transient storage retire only on validated normal completion;
Halt/fault preserves the deepest authenticated prefix. Catching a failure cannot
resume callbacks, commit visibility, release transient storage or write guest
state. The existing deferred pump, real RET16/nonvolatile/FS/frame checks and
shared instruction/depth/deadline bounds are reused unchanged. SourceFixtureCapability
and the kernel have no changes. DestroyWindow, IsWindow lifecycle transitions,
queued dispatch, arbitrary sent messages, app-present callback flows, and full
WinMain/app-init success remain outside this increment.
