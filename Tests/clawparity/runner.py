"""Runs one canonical family's cases and prints one line of JSON.

    python -m clawparity.runner Tests/families/<id>.json [--seed N] [--flavor O2|O0|sanitize] [--trace]
"""
import argparse
from .abi import CALL_ARGUMENT_CAPACITY

import ctypes as C
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

from . import build, build_inputs
from . import program as programs
from .cases import resolve, compiler_contract_errors, caller_frame_base
from .env import CALLEE_POPS, U32, Env, HarnessError, NativeHost, NativeCompilerContext, NativeSourceContext
from .fixtures import CATALOGUE
from .kernel import STACK_TOP, STACK_BASE, STACK_SIZE, CONTEXT_FIELDS, validate_context

ROOT = Path(__file__).resolve().parents[2]


def number(text):
    return int(text, 16)


def load_symbols():
    path = ROOT / "Tests" / "symbols.json"
    if not path.exists():
        return {}
    return {number(address): entry["name"] for address, entry in json.loads(path.read_text())["symbols"].items()}


def load_program(spec):
    name = spec.get("program", "claw-v1.0")
    if name in ("claw-v1.0", "claw-v1.3"):
        return programs.profile(name)
    if name == "ordinary-source-synthetic":
        from .selftest.source_context import program
        return program()
    if name == "compiler-family-synthetic":
        from .selftest.compiler_family import program
        return program()
    if name == "synthetic":
        from .selftest import synthetic
        return synthetic.program()
    raise HarnessError(f"unknown program {name!r}")


def load_cases(spec):
    path = ROOT / spec["oracle"]["cases"]
    module_spec = importlib.util.spec_from_file_location(f"cases_{spec['id']}", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def owned_ranges(spec):
    """Byte ranges of each owned function: from the specification when given, else from the local corpus index."""
    if spec.get("program") == "claw-v1.3":
        # The existing corpus belongs to v1.0. Numeric address coincidences are
        # not ownership evidence for a different executable.
        from .profiles import owned_ranges as profile_ranges
        return profile_ranges(spec)
    if any('body_ranges' in entry for entry in spec['owned']):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools.claw.owned_ranges import resolve_owned_ranges
        return resolve_owned_ranges(spec)
    ranges = {}
    index_path = ROOT / "work" / "corpus" / "index.json"
    index = None
    for entry in spec["owned"]:
        start = number(entry["address"])
        if "interval_end" in entry:
            ranges[start] = [(start, number(entry["interval_end"]))]
            continue
        if index is None and index_path.exists():
            index = {number(f["entry"]) if isinstance(f["entry"], str) else f["entry"]: f
                     for f in json.loads(index_path.read_text())["functions"]}
        function = (index or {}).get(start)
        if function:
            ranges[start] = [(number(a) if isinstance(a, str) else a, number(b) if isinstance(b, str) else b)
                             for a, b in function["ranges"]]
    return ranges


def coverage_report(spec, blocks, direct_calls):
    """Which bytes of each owned function the original side executed, and what was never reached."""
    executed = sorted(blocks)
    exempt = [(number(e["start"]), number(e["end"])) for e in spec["oracle"].get("coverage_exempt", [])]
    report = {}
    for start, ranges in owned_ranges(spec).items():
        total, covered, owned_bytes, exempt_bytes, missing = 0, 0, 0, 0, []
        for low, high in ranges:
            marks = bytearray(high - low)
            for address, size in executed:
                first, last = max(address, low), min(address + size, high)
                if first < last:
                    marks[first - low:last - low] = b"\1" * (last - first)
            for first, last in exempt:
                first, last = max(first, low), min(last, high)
                if first < last:
                    marks[first - low:last - low] = b"\2" * (last - first)
            total += sum(1 for m in marks if m != 2)
            owned_bytes += len(marks)
            exempt_bytes += marks.count(2)
            covered += sum(1 for m in marks if m == 1)
            gap = None
            for offset, mark in enumerate(marks):
                if mark == 0 and gap is None:
                    gap = low + offset
                if mark != 0 and gap is not None:
                    missing.append([f"{gap:#x}", f"{low + offset:#x}"])
                    gap = None
            if gap is not None:
                missing.append([f"{gap:#x}", f"{high:#x}"])
        report[f"{start:#x}"] = {"bytes": total, "executed": covered, "fraction": round(covered / total, 4) if total else 1.0,
                                 "owned_bytes": owned_bytes, "exempt_bytes": exempt_bytes, "required_bytes": total,
                                 "direct_calls": direct_calls.get(start, 0), "never_executed": missing[:20]}
    for entry in spec["owned"]:
        report.setdefault(entry["address"], {"bytes": None, "direct_calls": direct_calls.get(number(entry["address"]), 0),
                                              "never_executed": None})
    return report


def run(spec_path, seed=0, flavor="O2", trace=False, defines=(), limit_failures=10, module_source=None,
        original_only=False):
    started = time.monotonic()
    spec = json.loads(Path(spec_path).read_text())
    summary = {"command": "oracle", "family": spec["id"], "seed": seed, "flavor": flavor}
    if flavor == "sanitize" and not build.sanitizer_preloaded():
        # Loading a sanitized library into a process that started without the
        # sanitizer runtime aborts the whole interpreter. Refuse instead.
        summary.update(status="error", detail="sanitize needs the sanitizer runtime preloaded; run it through the gate")
        return summary
    if original_only:
        summary["command"] = "cases-check"
    try:
        build_inputs.sources(spec)
        if spec.get("program") == "claw-v1.3":
            from .profiles import validate
            selected_program = validate(spec)
            summary.update(program=selected_program.name, program_sha256=selected_program.sha256)
        plan = None
        if ('guest_graph' in spec.get('oracle', {}) or
                any('attached_entries' in e for e in spec.get('owned', [])) or
                any(c.get('kind') == 'guest-service' for c in spec.get('callees', {}).values())):
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from .guest_contract import normalize_guest_contract
            plan = normalize_guest_contract(spec)
        contract_errors = compiler_contract_errors(spec)
        if any('body_ranges' in e for e in spec.get('owned', [])):
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from tools.claw.owned_ranges import body_range_errors
            contract_errors.extend(body_range_errors(spec))
        if contract_errors:
            raise HarnessError("; ".join(contract_errors))
        for address, callee in spec.get('callees', {}).items():
            if 'x87_exact' not in callee:
                continue
            effect = callee['x87_exact']
            if (callee.get('kind') != 'whole' or
                    callee.get('convention') not in ('cdecl', 'stdcall', 'thiscall') or
                    type(callee.get('argc')) is not int or not 0 <= callee['argc'] <= CALL_ARGUMENT_CAPACITY or
                    any(k in callee for k in ('x87_args', 'source_context', 'compiler_context')) or
                    not isinstance(effect, dict) or set(effect) != {'pop', 'push'} or
                    type(effect['pop']) is not int or not 0 <= effect['pop'] <= 8 or
                    type(effect['push']) is not int or not 0 <= effect['push'] <= 1):
                raise HarnessError(f'{address}: malformed or mixed exact x87 declaration')
        entry = None
        if not original_only:
            library = C.CDLL(str(build_inputs.library(spec, flavor, defines, module_source=module_source,
                                                     guest_transfer=plan is not None)))
            entry = getattr(library, spec["oracle"].get("entry", f"claw_{spec['id']}_entry"))
            entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
            entry.restype = U32
        env = Env(load_program(spec), heap_bytes=spec["oracle"].get("heap_bytes", 0x40000), symbols=load_symbols())
        for address, callee in spec.get("callees", {}).items():
            if callee.get('convention') == 'compiler-context':
                env.compiler_callees[number(address)] = callee['compiler_context']
            elif callee.get('kind') == 'whole' and 'source_context' in callee:
                env.source_callees[number(address)] = callee
            if "x87_exact" in callee:
                if (callee['kind'] != 'whole' or any(k in callee for k in
                        ('x87_args', 'source_context', 'compiler_context'))):
                    raise HarnessError(f"{address}: mixed exact x87 capability")
                env.whole_x87(number(address), callee.get('convention'), callee.get('argc'),
                              callee.get('name', ''), callee.get('arguments', ()), exact=callee['x87_exact'])
            if "x87_args" in callee:
                if type(callee["x87_args"]) is not int or callee["x87_args"] != 1 or callee["kind"] != "whole":
                    raise HarnessError(f"{address}: x87_args must be 1 on an original whole callee")
                env.whole_x87(number(address), callee.get("convention"), callee.get("argc"),
                              callee.get("name", ""), callee.get("arguments", ()))
            if "caller_frame" in callee:
                ranges = owned_ranges(spec)
                env.caller_frame(number(address), callee["convention"], callee["argc"], [
                    (number(d["caller"]), number(d["site"]),
                     *caller_frame_base(d["ebp"]["base"], next(o.get("argc", 0) for o in spec["owned"]
                                                               if o["address"] == d["caller"])),
                     d["ebp"]["offset"]) for d in callee["caller_frame"]],
                    {start: [tuple(r) for r in found] for start, found in ranges.items()})
            if callee["kind"] == "fixture":
                env.fixture(number(address), callee["convention"], callee["argc"], CATALOGUE[callee.get("fixture", "scripted")],
                            callee.get("name", ""), callee.get("arguments", ()))
        owned = {number(entry_["address"]): entry_ for entry_ in spec["owned"]}
        for address, entry_ in owned.items():
            if "x87_result" in entry_:
                env.owned_x87_result(address, entry_["x87_result"])
            if "x87_environment" in entry_:
                env.owned_x87_environment(address, entry_["x87_environment"])
        cases = load_cases(spec).cases(random.Random(seed))
    except Exception as error:  # the family cannot even start: report it as data
        summary.update(status="error", detail=f"{type(error).__name__}: {error}"[:3000])
        return summary
    fill = random.Random(seed ^ 0x5EED)
    passed, failures, events, direct, bridged, labels = 0, [], 0, {}, {}, 0
    guest_evidence = {'outcomes': {}, 'factory_outcomes': {}, 'original_catch_cases': 0, 'native_attached_invocations': 0,
        'policy_verified': True, 'ownership_guard': 'stop-before-execution',
        'owned_ranges_guarded': [list(r) for r in plan.owned_ranges]} if plan else None
    for case in cases:
        labels += 1
        difference = None
        try:
            if case.function not in owned:
                raise HarnessError(f"{case.function:#x} is not owned by this family")
            declared = owned[case.function]
            env._begin_case(fill)
            tokens = case.setup(env) if case.setup else None
            context = resolve(case.compiler_context, tokens)
            source = resolve(case.source_context, tokens)
            source_pc = resolve(case.source_return_pc, tokens)
            receiver2 = resolve(case.receiver2, tokens)
            stack_input = resolve(case.initial_stack, tokens)
            x87_profile = resolve(case.entry_x87, tokens)
            if x87_profile is not None:
                env.entry_x87(x87_profile)
            if env._entry_x87_profile is not None:
                if context is not None or source is not None or plan is not None:
                    raise HarnessError('entry x87 profile cannot be mixed with context or guest entries')
                env._check_entry_x87_profile(case.function)
            if stack_input and (context is not None or source is not None or plan is not None):
                raise HarnessError("ordinary initial stack input cannot be mixed with context or guest entries")
            env.initial_stack(stack_input)
            env._freeze()
            receiver = resolve(case.receiver, tokens)
            arguments = tuple(resolve(a, tokens) & 0xFFFFFFFF for a in case.arguments)
            if len(arguments) != declared.get("argc", 0):
                raise HarnessError(f"case passes {len(arguments)} arguments; the specification says {declared.get('argc')}")
            special = declared.get("convention") == "compiler-context"
            if special and (source is not None or source_pc or receiver2):
                raise HarnessError('compiler entry cannot receive ordinary source operands')
            if not special and 'source_context' not in declared and (source is not None or source_pc or receiver2):
                raise HarnessError('ordinary entry has no source capability')
            if not special and source is None and (source_pc or receiver2):
                raise HarnessError('ordinary source operands require an explicit source context')
            if plan is not None:
                from .guest_family import run_case
                native, original, difference, evidence = run_case(env, entry, None if original_only else library,
                    plan, case, receiver, receiver2, arguments, source, source_pc,
                    flavor=flavor, original_only=original_only)
                if difference is None:
                    outcome = evidence['outcome']
                    guest_evidence['outcomes'][outcome] = guest_evidence['outcomes'].get(outcome, 0) + 1
                    guest_evidence['original_catch_cases'] += evidence['original_catch']
                    guest_evidence['native_attached_invocations'] += evidence['native_invocations']
                    for factory in evidence['executed_factories']:
                        counts = guest_evidence['factory_outcomes'].setdefault(f'{factory:#x}', {})
                        counts[outcome] = counts.get(outcome, 0) + 1
            elif special:
                if (type(context) is not NativeCompilerContext or receiver or arguments or
                        case.compare_eax is not None or case.expect != "return"):
                    raise HarnessError("compiler-context requires explicit context, no ordinary operands or comparison overrides, and return expectation")
                validate_context(context, case.function, env.program)
                contract = declared["compiler_context"]
                if (context.inputMask != contract["input_mask"] or context.outputMask != contract["output_mask"]):
                    raise HarnessError("case context masks disagree with owned contract")
                before = NativeCompilerContext.from_buffer_copy(context)
                native_context = NativeCompilerContext.from_buffer_copy(before)
                original_context = NativeCompilerContext.from_buffer_copy(before)
                if not original_only:
                    native = env.run_native(entry, case.function, 0, (), compiler_context=native_context)
                    native_stack = bytes(env._stack)
                original = env.run_original_context(case.function, original_context, trace, check_objects=original_only)
                original_stack = env.machine.read(STACK_BASE, STACK_SIZE)
                if original_only:
                    native, native_context, native_stack = original, original_context, original_stack
                difference = env.compare(native, original, False, original.stack_pointer)
                if difference is None and (not native.completed or not original.completed or original.halted):
                    difference = {"kind": "compiler-context", "detail": "special entry did not complete at its genuine continuation"}
                if difference is None:
                    for field, _ in NativeCompilerContext._fields_:
                        ours, theirs = getattr(native_context, field), getattr(original_context, field)
                        immutable = field not in CONTEXT_FIELDS or not before.outputMask & (1 << CONTEXT_FIELDS.index(field))
                        if ours != theirs or (immutable and ours != getattr(before, field)):
                            difference = {"kind": "compiler-context", "detail": f"{field}: native {ours:#x}, original {theirs:#x}, input {getattr(before, field):#x}"}
                            break
                if difference is None and native_stack != original_stack:
                    difference = {"kind": "stack", "detail": env._word_differences(STACK_BASE, native_stack, original_stack)}
            else:
                if context is not None:
                    raise HarnessError("ordinary entry cannot receive compiler_context")
                pops = 4 * len(arguments) if declared.get("convention") in CALLEE_POPS else 0
                if ('source_context' in declared and
                        (source is not None or not declared['source_context'].get('optional', False))):
                    if type(source) is not NativeSourceContext or case.compare_eax is not None or case.expect not in ('return', 'halt'):
                        raise HarnessError('source entry requires explicit context, a return or physical halt expectation and declared comparisons')
                    env._check_source_masks(source, declared['source_context'])
                    before = NativeSourceContext.from_buffer_copy(source)
                    native_source = NativeSourceContext.from_buffer_copy(source)
                    original_source = NativeSourceContext.from_buffer_copy(source)
                    options = dict(source_return_pc=source_pc, source_convention=declared['convention'], receiver2=receiver2)
                    if not original_only:
                        native = env.run_native(entry, case.function, receiver, arguments, source_context=native_source, **options)
                        native_stack = bytes(env._stack)
                    original = env.run_original_context(case.function, original_source, trace, check_objects=original_only,
                                                        receiver=receiver, arguments=arguments, **options)
                    original_stack = env.machine.read(STACK_BASE, STACK_SIZE)
                    if original_only:
                        native, native_source, native_stack = original, original_source, original_stack
                    difference = env.compare(native, original, True, before.esp + 4 + pops)
                    if case.expect == 'halt':
                        if difference is None and (not native.halted or not original.halted or native.completed or original.completed or
                                native.source_stop is None or native.source_stop != original.source_stop):
                            difference = {'kind': 'compiler-context', 'detail': 'source physical halt state differs or is unavailable'}
                        header = ('size', 'version', 'inputMask', 'outputMask', 'preserveMask', 'reserved0', 'reserved1')
                        if difference is None and any(getattr(c, n) != getattr(before, n)
                                                      for c in (native_source, original_source) for n in header):
                            difference = {'kind': 'compiler-context', 'detail': 'source halted prefix changed immutable input header'}
                    else:
                        if difference is None and (not native.completed or not original.completed):
                            difference = {'kind': 'compiler-context', 'detail': 'source entry failed to return at real PC'}
                        if difference is None and bytes(native_source) != bytes(original_source):
                            difference = {'kind': 'compiler-context', 'detail': 'ordinary source state differs'}
                    if difference is None and native_stack != original_stack:
                        difference = {'kind': 'stack', 'detail': env._word_differences(STACK_BASE, native_stack, original_stack)}
                else:
                    if original_only:
                        original = env.run_original(case.function, receiver, arguments, trace, check_objects=True)
                        native = original
                    else:
                        native = env.run_native(entry, case.function, receiver, arguments)
                        original = env.run_original(case.function, receiver, arguments, trace)
                    compare_eax = case.compare_eax if case.compare_eax is not None else declared.get("returns", "u32") == "u32"
                    difference = env.compare(native, original, compare_eax, STACK_TOP + 4 + pops)
            if difference is None and (case.expect == "halt") != original.halted:
                difference = {"kind": "expectation", "detail": f"case expected {case.expect}; halted={original.halted}"}
            events += len(original.events)
            direct[case.function] = direct.get(case.function, 0) + 1
            for callee in native.bridged:
                bridged[callee] = bridged.get(callee, 0) + 1
        except Exception as error:
            difference = {"kind": "harness", "detail": f"{type(error).__name__}: {error}"}
        if difference is None:
            passed += 1
        elif len(failures) < limit_failures:
            failures.append({"case": case.label, "function": f"{case.function:#x}", **difference})
    failed = labels - passed
    summary.update(status="pass" if labels and not failed else "fail", cases=labels, passed=passed, failed=failed,
                   outside_calls_compared=events,
                   original_callees_run_for_native={env.describe(a): n for a, n in sorted(bridged.items())},
                   failures=failures, seconds=round(time.monotonic() - started, 2))
    if trace:
        summary["coverage"] = coverage_report(spec, env.coverage, direct)
    if plan is not None:
        summary['guest_graph'] = guest_evidence
    return summary


def main(argv):
    parser = argparse.ArgumentParser(prog="clawparity.runner")
    parser.add_argument("spec")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--flavor", default="O2", choices=sorted(build.FLAVORS))
    parser.add_argument("--trace", action="store_true", help="record which original instructions ran")
    parser.add_argument("--define", action="append", default=[])
    parser.add_argument("--module-source", help="replace the primary canonical module, retaining auxiliary inputs (mutation testing)")
    parser.add_argument("--original-only", action="store_true",
                        help="run the cases on the original alone: checks the cases themselves and reports coverage")
    options = parser.parse_args(argv)
    summary = run(options.spec, options.seed, options.flavor, options.trace or options.original_only,
                  tuple(options.define), module_source=options.module_source, original_only=options.original_only)
    print(json.dumps(summary))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
