"""Runs the harness against the synthetic program and checks that each kind of error is reported. One JSON line."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import mutants, mutation_review, runner
from . import initial_stack, caller_frame, entry_frame, x87_trigonometry
from . import wide_calls, window_lifecycle, window_callbacks, physical_callbacks, source_fixtures, source_tail, source_imports, cached_imports, compiler_context, compiler_family, source_context, source_family, optional_source, native_source_dispatch, frames, stack, x87, x87_exact, x87_balanced, x87_result, x87_environment, x87_register, x87_load_hooks

SPEC = Path(__file__).with_name("family.json")
# compile-time switch -> the kind of difference the harness must report
EXPECTED = {
    "SELFTEST_WRONG_STORE": "heap",
    "SELFTEST_SKIP_GLOBAL": "globals",
    "SELFTEST_WRONG_RETURN": "return-value",
    "SELFTEST_EXTRA_CALL": "event-count",
    "SELFTEST_OUT_OF_BOUNDS": "native-fault",
}


def statement_mutation_checks():
    checks = {}
    for method in ("call", "icall", "vcall", "fastcall", "call_x87", "call_x87_exact", "x87_step", "source_call"):
        # Exercise comments on either or both adjacent statements, including
        # comments immediately after the semicolon and existing bare statements.
        for suffixes in (("", ""), (" // store", ""), ("", "// call"), (" // store", "// call")):
            for call_first in (False, True):
                lines = ["    run.put(address, value);" + suffixes[0],
                         f"    run.{method}(address, value);" + suffixes[1]]
                if call_first:
                    lines.reverse()
                expected = [(1, "swap-statements", list(reversed(lines))),
                            (1, "drop-statement", ["    ;", lines[1]]),
                            (2, "drop-statement", [lines[0], "    ;"])]
                label = f"{method}:{suffixes!r}:call_first={call_first}"
                checks[label] = list(mutants.mutations(lines)) == expected
    # A commented-out call must neither mutate itself nor enable a swap with
    # the live statement before it. Include text matching the other operators.
    comments = ["// run.call(address, value);", "    // run.vcall(address, value);",
                " // run.put(address + 0x10, value - 1);",
                " // if (value < limit) run.put(address, value / 2);"]
    checks["comment_only"] = list(mutants.mutations(comments)) == []
    for comment in comments:
        lines = ["    run.put(address, value); // live store", comment]
        checks[f"comment_neighbor:{comment}"] = list(mutants.mutations(lines)) == [
            (1, "drop-statement", ["    ;", comment])]
    # Store-only swaps remain excluded, even when comments are present.
    lines = ["    run.put(address, value); // store", "    run.put8(other, value);// store"]
    checks["store_only"] = list(mutants.mutations(lines)) == [
        (1, "drop-statement", ["    ;", lines[1]]),
        (2, "drop-statement", [lines[0], "    ;"])]
    for value in ("0", "1", "0u", "1U"):
        lines = ["uint32_t function_401000(Run &run) {", f"    return {value}; // source result", "}"]
        expected = lines.copy()
        expected[1] = expected[1].replace(value, ("1" if value[0] == "0" else "0") + value[1:], 1)
        checks[f"literal_return:{value}"] = list(mutants.mutations(lines)) == [(2, "flip-return-literal", expected)]
    for declaration in ("int owned(uint32_t function)", "uint32_t argc()", "uint32_t arity()",
                        "uint32_t body(Run &run)", "void function_401000()"):
        lines = [declaration + " {", "    return 0;", "}"]
        checks[f"literal_excluded:{declaration}"] = list(mutants.mutations(lines)) == []
    lines = ["/* uint32_t function_401000() {", "return 0;", "} */",
             'const char *text = "uint32_t function_401000() { return 0; }";',
             "uint32_t function_401001(Run &run) {", "    // } return 1;",
             "    /* } */ return 0;", "}"]
    expected = lines.copy()
    expected[6] = "    /* } */ return 1;"
    checks["literal_comments_strings_braces"] = list(mutants.mutations(lines)) == [(7, "flip-return-literal", expected)]
    checks["literal_incomplete_body"] = list(mutants.mutations(["uint32_t function_401000() {", "return 0;"])) == []
    checks["literal_raw_string_fail_closed"] = list(mutants.mutations([
        'const char *s = R"tag("', "uint32_t function_cafe() {", " return 0;", "}", '")tag";'])) == []
    checks["literal_line_splice_fail_closed"] = list(mutants.mutations([
        "// continued " + chr(92), "uint32_t function_cafe() {", "return 0;", "}"])) == []
    checks["literal_nested_lambda_excluded"] = list(mutants.mutations([
        "uint32_t function_cafe() {", "auto predicate = []() -> bool {", "return 0;", "};", "}" ])) == []
    checks["literal_disabled_preprocessor_excluded"] = list(mutants.mutations([
        "#if 0", "uint32_t function_cafe() {", "return 0;", "}", "#endif"])) == []
    lines = ["uint32_t function_cafe() {", "return 0;", "}"]
    checks["literal_semantic_void_excluded"] = list(mutants.mutations(lines, returns_u32=set())) == []
    checks["literal_semantic_u32_selected"] = len(list(mutants.mutations(lines, returns_u32={0xcafe}))) == 1
    for method in ("source_call", "source_tail"):
        for suffix in ("", " // transfer"):
            line = f"    run.{method}(0x401010, receiver, 0x401005, child);" + suffix
            expected = [
                (1, "source-edge-target", [line.replace("0x401010", "0x401011")]),
                (1, "source-edge-site", [line.replace("0x401005", "0x401006")]),
            ]
            if method == "source_call":
                expected.append((1, "drop-statement", ["    ;"]))
            checks[f"source_edge:{method}:{suffix}"] = list(mutants.mutations([line])) == expected
            checks[f"source_edge_comment:{method}:{suffix}"] = list(mutants.mutations(["// " + line])) == []
        # Dynamic expressions are not mistaken for hexadecimal edge literals.
        line = f"    run.{method}(target, receiver, site, child);"
        expected = [(1, "drop-statement", ["    ;"])] if method == "source_call" else []
        checks[f"source_edge_dynamic:{method}"] = list(mutants.mutations([line])) == expected
        line = f"    run.{method}(0x401010, receiver, 0x401005, child);"
        for container in (("/*", line, "*/"),
                          ('const char *s = R"tag(', line, ')tag";')):
            checks[f"source_edge_inert:{method}:{container[0]}"] = list(mutants.mutations(list(container))) == []
    return checks


def main():
    checks, problems = {}, []
    for flavor in ('O0', 'O2'):
        values = initial_stack.checks(flavor)
        checks['initial_stack_' + flavor] = {'checked': len(values), 'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()):
            problems.append('initial stack ' + flavor + ' controls failed')
    checks['initial_stack_sanitize'] = initial_stack.sanitized_checks()
    if not checks['initial_stack_sanitize'].get('passed'):
        problems.append('initial stack sanitizer controls failed or unavailable')
    for flavor in ("O0", "O2"):
        values = wide_calls.checks(flavor)
        checks["wide_calls_" + flavor] = {"checked": len(values), "failed": [k for k, v in values.items() if not v]}
        if not all(values.values()):
            problems.append("wide call " + flavor + " controls failed")
    checks["wide_calls_sanitize"] = wide_calls.sanitized_checks()
    if not checks["wide_calls_sanitize"].get("passed"):
        problems.append("wide call sanitizer controls failed")
    for flavor in ('O0','O2'):
        callback_checks = physical_callbacks.checks(flavor)
        checks['physical_callbacks_'+flavor] = {'checked':len(callback_checks),
            'failed':[name for name,passed in callback_checks.items() if not passed]}
        if checks['physical_callbacks_'+flavor]['failed']:
            problems.append('physical callback '+flavor+' controls failed')
    checks['physical_callbacks_sanitize'] = physical_callbacks.sanitized_checks()
    if not checks['physical_callbacks_sanitize'].get('passed'):
        problems.append('physical callback sanitizer controls failed or unavailable')
    for flavor in ('O0','O2'):
        values=window_callbacks.checks(flavor)
        checks['window_callbacks_'+flavor]={'checked':len(values),'failed':[k for k,v in values.items() if not v]}
        if not all(values.values()):problems.append('window callback '+flavor+' controls failed')
    checks['window_callbacks_sanitize']=window_callbacks.sanitized_checks()
    if not checks['window_callbacks_sanitize'].get('passed'):
        problems.append('window callback sanitizer controls failed or unavailable')
    for flavor in ('O0','O2'):
        values=window_lifecycle.checks(flavor)
        checks['window_lifecycle_'+flavor]={'checked':len(values),'failed':[k for k,v in values.items() if not v]}
        if not all(values.values()):problems.append('window lifecycle '+flavor+' controls failed')
    checks['window_lifecycle_sanitize']=window_lifecycle.sanitized_checks()
    if not checks['window_lifecycle_sanitize'].get('passed'):
        problems.append('window lifecycle sanitizer controls failed or unavailable')
    # Test synthetic dispatch and genuine original-factory capture separately.
    # Repository-root imports retain one ctypes/package identity.
    for key, module, minimum in (
            ('shared_build_inputs', 'Tests.clawparity.selftest.shared_build_inputs', 10),
            ('guest_exceptions', 'Tests.test_guest_exception', 28),
            ('native_guest_adapter', 'Tests.test_native_guest_adapter', 8),
            ('native_guest_graph', 'Tests.test_native_guest_graph', 12),
            ('guest_reference', 'Tests.test_guest_reference', 10),
            ('source_continuation', 'Tests.test_source_continuation', 8),
            ('source_boundary', 'Tests.test_source_boundary', 6),
            ('guest_comparison', 'Tests.test_guest_compare', 7),
            ('guest_contract', 'Tests.test_guest_contract', 4),
            ('guest_policy', 'Tests.test_guest_policy', 4),
            ('guest_family', 'Tests.test_guest_family', 2),
            ('guest_admission', 'Tests.test_guest_admission', 7),
            ('owned_body_ranges', 'Tests.test_owned_body_ranges', 26),
            ('owned_coverage', 'Tests.test_owned_coverage', 3)):
        guest = subprocess.run([sys.executable, '-c',
            'import json, unittest; '
            'suite=unittest.defaultTestLoader.loadTestsFromName(' + repr(module) + '); '
            'result=unittest.TestResult(); suite.run(result); '
            'print(json.dumps(dict(checked=result.testsRun, '
            'failed=[str(test) for test, trace in result.failures+result.errors], '
            'skipped=len(result.skipped), passed=result.wasSuccessful())))'],
            cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, timeout=60)
        try:
            guest_checks = json.loads(guest.stdout)
            passed = (guest.returncode == 0 and guest_checks.get('passed') is True
                      and type(guest_checks.get('checked')) is int and guest_checks['checked'] >= minimum
                      and guest_checks.get('skipped') == 0 and guest_checks.get('failed') == [])
        except (ValueError, AttributeError):
            guest_checks, passed = {'passed': False, 'detail': guest.stderr[-2000:]}, False
        checks[key] = guest_checks
        if not passed:
            problems.append(key + ' controls failed or did not run')
    for flavor in ('O0', 'O2'):
        fixture_checks = source_fixtures.checks(flavor)
        checks['source_fixtures_' + flavor] = {'checked': len(fixture_checks),
            'failed': [name for name, passed in fixture_checks.items() if not passed]}
        if checks['source_fixtures_' + flavor]['failed']:
            problems.append('source fixture ' + flavor + ' controls failed')
    checks['source_fixtures_sanitize'] = source_fixtures.sanitized_checks()
    if not checks['source_fixtures_sanitize'].get('passed'):
        problems.append('source fixture sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        import_checks = source_imports.checks(flavor)
        checks['source_imports_' + flavor] = {'checked': len(import_checks),
            'failed': [name for name, passed in import_checks.items() if not passed]}
        if checks['source_imports_' + flavor]['failed']:
            problems.append(f"source import {flavor} regressions: {checks['source_imports_' + flavor]['failed']}")
    checks['source_imports_sanitize'] = source_imports.sanitized_checks()
    if not checks['source_imports_sanitize'].get('passed'):
        problems.append('source import sanitizer checks failed or unavailable')
    for flavor in ('O0','O2'):
        tail_checks = source_tail.checks(flavor)
        checks['source_tail_' + flavor] = {'checked': len(tail_checks),
            'failed': [name for name, passed in tail_checks.items() if not passed]}
        if checks['source_tail_' + flavor]['failed']:
            problems.append('source tail ' + flavor + ' controls failed')
    checks['source_tail_sanitize'] = source_tail.sanitized_checks()
    if not checks['source_tail_sanitize'].get('passed'):
        problems.append('source tail sanitizer controls failed or unavailable')
    family_checks = compiler_family.checks()
    checks['compiler_family'] = {'checked': len(family_checks),
        'failed': [name for name, passed in family_checks.items() if not passed]}
    if checks['compiler_family']['failed']:
        problems.append(f"compiler family regressions: {checks['compiler_family']['failed']}")
    source_family_checks = source_family.checks()
    checks['source_family'] = {'checked': len(source_family_checks),
        'failed': [name for name, passed in source_family_checks.items() if not passed]}
    if checks['source_family']['failed']:
        problems.append(f"source family regressions: {checks['source_family']['failed']}")
    for flavor in ('O0', 'O2'):
        optional_checks = optional_source.checks(flavor)
        checks['optional_source_' + flavor] = {'checked': len(optional_checks),
            'failed': [name for name, passed in optional_checks.items() if not passed]}
        if checks['optional_source_' + flavor]['failed']:
            problems.append(f"optional source {flavor} regressions: {checks['optional_source_' + flavor]['failed']}")
    checks['optional_source_sanitize'] = optional_source.sanitized_checks()
    if not checks['optional_source_sanitize'].get('sanitizer_ok'):
        problems.append('optional source sanitizer checks failed or unavailable')
    dispatch_checks = native_source_dispatch.checks()
    checks['native_source_dispatch'] = {'checked': len(dispatch_checks),
        'failed': [name for name, passed in dispatch_checks.items() if not passed]}
    if checks['native_source_dispatch']['failed']:
        problems.append(f"native source dispatch regressions: {checks['native_source_dispatch']['failed']}")
    checks['source_context_sanitize'] = source_context.sanitized_checks()
    if not checks['source_context_sanitize'].get('passed'):
        problems.append('source context sanitizer checks failed or unavailable')
    original_context = compiler_context.original_readiness()
    checks['compiler_context_original_readiness'] = {'checked': len(original_context),
        'failed': [name for name, passed in original_context.items() if not passed]}
    if checks['compiler_context_original_readiness']['failed']:
        problems.append('unchanged original compiler helper readiness failed')
    checks['compiler_context_sanitize'] = compiler_context.sanitized_checks()
    if not checks['compiler_context_sanitize'].get('passed'):
        problems.append('compiler context sanitizer checks failed or unavailable')
    for flavor in ('O0', 'O2'):
        source_checks = source_context.checks(flavor)
        checks['source_context_' + flavor] = {'checked': len(source_checks),
            'failed': [name for name, passed in source_checks.items() if not passed]}
        if checks['source_context_' + flavor]['failed']:
            problems.append(f"source context {flavor} regressions: {checks['source_context_' + flavor]['failed']}")
        context_checks = compiler_context.checks(flavor)
        checks['compiler_context_' + flavor] = {'checked': len(context_checks),
            'failed': [name for name, passed in context_checks.items() if not passed]}
        if checks['compiler_context_' + flavor]['failed']:
            problems.append(f"compiler context {flavor} regressions: {checks['compiler_context_' + flavor]['failed']}")
        frame_checks = frames.checks(flavor)
        checks['frames_' + flavor] = {'checked': len(frame_checks),
                                      'failed': [name for name, passed in frame_checks.items() if not passed]}
        if checks['frames_' + flavor]['failed']:
            problems.append(f"frame {flavor} regressions: {checks['frames_' + flavor]['failed']}")
        import_checks = cached_imports.checks(flavor)
        checks['cached_imports_' + flavor] = {'checked': len(import_checks),
            'failed': [name for name, passed in import_checks.items() if not passed]}
        if checks['cached_imports_' + flavor]['failed']:
            problems.append(f"cached import {flavor} regressions: {checks['cached_imports_' + flavor]['failed']}")
        frame_checks = caller_frame.checks(flavor)
        checks['caller_frame_' + flavor] = {'checked': len(frame_checks),
            'failed': [name for name, passed in frame_checks.items() if not passed]}
        if checks['caller_frame_' + flavor]['failed']:
            problems.append(f"caller frame {flavor} regressions: {checks['caller_frame_' + flavor]['failed']}")
        entry_checks = entry_frame.checks(flavor)
        checks['entry_frame_' + flavor] = {'checked': len(entry_checks),
            'failed': [name for name, passed in entry_checks.items() if not passed]}
        if checks['entry_frame_' + flavor]['failed']:
            problems.append(f"entry frame {flavor} regressions: {checks['entry_frame_' + flavor]['failed']}")
    checks['caller_frame_sanitizers'] = caller_frame.sanitized_checks()
    if checks['caller_frame_sanitizers'].get('available', True) and not checks['caller_frame_sanitizers'].get('passed'):
        problems.append(f"caller frame sanitizer regressions: {checks['caller_frame_sanitizers']}")
    checks['entry_frame_sanitizers'] = entry_frame.sanitized_checks()
    if checks['entry_frame_sanitizers'].get('available', True) and not checks['entry_frame_sanitizers'].get('passed'):
        problems.append(f"entry frame sanitizer regressions: {checks['entry_frame_sanitizers']}")
    checks['cached_import_sanitizers'] = cached_imports.sanitized_checks()
    if not checks['cached_import_sanitizers'].get('passed'):
        problems.append(f"cached import sanitizer regressions: {checks['cached_import_sanitizers']}")
    checks['frame_sanitizers'] = frames.sanitized_checks()
    if not checks['frame_sanitizers'].get('passed'):
        problems.append(f"frame sanitizer regressions: {checks['frame_sanitizers']}")
    stack_checks = stack.checks()
    checks["stack_backing"] = {"checked": len(stack_checks),
                               "failed": [name for name, passed in stack_checks.items() if not passed]}
    if checks["stack_backing"]["failed"]:
        problems.append(f"stack backing regressions: {checks['stack_backing']['failed']}")
    checks["stack_sanitizers"] = stack.sanitized_checks()
    if not checks["stack_sanitizers"].get("passed"):
        problems.append(f"stack sanitizer regressions: {checks['stack_sanitizers']}")
    for flavor in ('O0', 'O2'):
        values = x87_exact.checks(flavor)
        checks['x87_exact_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('exact x87 ' + flavor + ' controls failed')
    checks['x87_exact_sanitize'] = x87_exact.sanitized_checks()
    if not checks['x87_exact_sanitize'].get('passed'):
        problems.append('exact x87 sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        values = x87_balanced.checks(flavor)
        checks['x87_balanced_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('balanced x87 ' + flavor + ' controls failed')
    checks['x87_balanced_sanitize'] = x87_balanced.sanitized_checks()
    if not checks['x87_balanced_sanitize'].get('passed'):
        problems.append('balanced x87 sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        values = x87_result.checks(flavor)
        checks['x87_result_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('owned x87 result ' + flavor + ' controls failed')
    checks['x87_result_sanitize'] = x87_result.sanitized_checks()
    if not checks['x87_result_sanitize'].get('passed'):
        problems.append('owned x87 result sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        values = x87_environment.checks(flavor)
        checks['x87_environment_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('owned x87 environment ' + flavor + ' controls failed')
    checks['x87_environment_sanitize'] = x87_environment.sanitized_checks()
    if not checks['x87_environment_sanitize'].get('passed'):
        problems.append('owned x87 environment sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        values = x87_register.checks(flavor)
        checks['x87_register_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('x87 register primitive ' + flavor + ' controls failed')
    checks['x87_register_sanitize'] = x87_register.sanitized_checks()
    if not checks['x87_register_sanitize'].get('passed'):
        problems.append('x87 register primitive sanitizer controls failed or unavailable')
    for flavor in ('O0', 'O2'):
        values = x87_trigonometry.checks(flavor)
        checks['x87_trigonometry_' + flavor] = {'checked': len(values),
            'failed': [k for k, v in values.items() if not v]}
        if not all(values.values()): problems.append('x87 trigonometry ' + flavor + ' controls failed')
    checks['x87_trigonometry_sanitize'] = x87_trigonometry.sanitized_checks()
    if not checks['x87_trigonometry_sanitize'].get('passed'):
        problems.append('x87 trigonometry sanitizer controls failed or unavailable')
    values = x87_load_hooks.checks()
    checks['x87_load_hooks'] = {'checked': len(values), 'failed': [k for k, v in values.items() if not v]}
    if not all(values.values()): problems.append('narrowed x87 load hook controls failed')
    x87_checks = x87.checks()
    checks["x87_boundary"] = {"checked": len(x87_checks),
                               "failed": [name for name, passed in x87_checks.items() if not passed]}
    if checks["x87_boundary"]["failed"]:
        problems.append(f"x87 boundary regressions: {checks['x87_boundary']['failed']}")
    statement_checks = statement_mutation_checks()
    checks["statement_mutations"] = {"checked": len(statement_checks),
                                     "failed": [name for name, passed in statement_checks.items() if not passed]}
    if checks["statement_mutations"]["failed"]:
        problems.append(f"statement mutation regressions: {checks['statement_mutations']['failed']}")
    correct = runner.run(SPEC, seed=1, trace=True)
    checks["correct_module"] = {k: correct.get(k) for k in ("status", "cases", "failed", "detail")}
    if correct["status"] != "pass":
        problems.append(f"the correct module does not pass: {correct.get('failures') or correct.get('detail')}")
    coverage = correct.get("coverage", {})
    checks["coverage"] = {a: c.get("fraction") for a, c in coverage.items()}
    if any(c.get("fraction") != 1.0 for c in coverage.values()) or len(coverage) != 3:
        problems.append("coverage of the three owned functions is not complete")
    if not any("0x401060" in name for name in correct.get("original_callees_run_for_native", {})):
        problems.append("the unowned callee was not run as original code for the native side")
    for switch, kind in EXPECTED.items():
        wrong = runner.run(SPEC, seed=1, defines=(switch,))
        kinds = sorted({failure["kind"] for failure in wrong.get("failures", [])})
        checks[switch] = kinds
        if wrong["status"] != "fail" or kind not in kinds:
            problems.append(f"{switch}: expected a {kind} difference, harness reported {kinds or wrong['status']}")
    mutation = mutants.run(SPEC, seed=1, limit=0)
    checks["mutants"] = {k: mutation[k] for k in ("tried", "killed", "invalid", "score")}
    # Lines inside a SELFTEST_* switch are not compiled into the correct module, so changing them changes nothing.
    lines = Path(__file__).with_name("Module.cpp").read_text().splitlines()
    switched_off, inside = set(), False
    for number, line in enumerate(lines, 1):
        if line.startswith("#ifdef SELFTEST_"):
            inside = True
        elif line.startswith(("#else", "#endif")):
            inside = False
        elif inside:
            switched_off.add(number)
    real = [m for m in mutation["survived"] if m["line"] not in switched_off]
    checks["mutants"]["survived_in_live_code"] = [f"{m['operator']}@{m['line']}" for m in real]
    if real or mutation["killed"] < 5:
        problems.append(f"mutants survived in live code: {checks['mutants']['survived_in_live_code']}")
    # These mutations lie inside disabled synthetic preprocessor branches:
    # they cannot affect any input. Review exact bytes, never just a line number.
    source = Path(__file__).with_name("Module.cpp").read_text()
    reviews = [{"line": m["line"], "operator": m["operator"],
                "source_sha256": mutation_review.digest(source), "mutant_sha256": m["mutant_sha256"],
                "reason": "Inside a disabled synthetic SELFTEST branch; not compiled for any input."}
               for m in mutation["survived"] if m["line"] in switched_off]
    with tempfile.TemporaryDirectory(dir=mutants.ROOT / "work", prefix="selftest-review-") as directory:
        spec = json.loads(SPEC.read_text())
        spec["oracle"]["equivalent_mutants"] = reviews
        reviewed_spec = Path(directory) / "family.json"
        reviewed_spec.write_text(json.dumps(spec))
        reviewed_result = mutants.run(reviewed_spec, seed=1, limit=0)
        spec["oracle"]["equivalent_mutants"][0]["reason"] = ""
        reviewed_spec.write_text(json.dumps(spec))
        invalid_cli = subprocess.run([sys.executable, "-m", "clawparity.mutants", str(reviewed_spec),
                                      "--limit", "0", "--jobs", "1"], capture_output=True, text=True)
        checks["invalid_review_cli_rejected"] = (
            invalid_cli.returncode != 0 and json.loads(invalid_cli.stdout)["status"] == "fail")
        if not checks["invalid_review_cli_rejected"]:
            problems.append("mutation CLI did not reject invalid equivalent reviews")
    checks["equivalent_review"] = {k: reviewed_result[k] for k in ("status", "score", "review_errors")}
    if not reviews or reviewed_result["status"] != "pass" or reviewed_result["score"] != 1.0:
        problems.append("reviewed disabled-code mutants did not produce the expected score")
    candidates = list(mutants.mutations(source.splitlines()))
    for invalid_reviews in ({}, "", None, 1):
        _, errors = mutation_review.validate(source, candidates, invalid_reviews)
        if not errors:
            problems.append(f"malformed review container accepted: {invalid_reviews!r}")
    checks["malformed_review_containers_rejected"] = all(
        mutation_review.validate(source, candidates, invalid)[1] for invalid in ({}, "", None, 1))
    for label, changed_source, changed_reviews in (
            ("stale_source", source + "\n", reviews),
            ("wrong_mutant", source, [{**reviews[0], "mutant_sha256": "0" * 64}]),
            ("empty_reason", source, [{**reviews[0], "reason": " "}]),
            ("duplicate", source, [reviews[0], reviews[0]])):
        _, errors = mutation_review.validate(changed_source, candidates, changed_reviews)
        checks[label] = bool(errors)
        if not errors:
            problems.append(f"{label}: invalid equivalent review accepted")
    identity = (reviews[0]["line"], reviews[0]["operator"], reviews[0]["mutant_sha256"])
    _, errors = mutation_review.classify(
        [{"line": identity[0], "operator": identity[1], "mutant_sha256": identity[2], "result": "killed"}],
        {identity: reviews[0]["reason"]})
    checks["killed_equivalent_rejected"] = bool(errors)
    if not errors:
        problems.append("a killed mutant was accepted as equivalent")
    _, errors = mutation_review.classify(
        [{"line": identity[0], "operator": identity[1], "mutant_sha256": identity[2], "result": "invalid"}],
        {identity: "reviewed equivalent"})
    checks["invalid_equivalent_rejected"] = bool(errors)
    if not errors:
        problems.append("an invalid mutant was accepted as equivalent")
    only_equivalent, errors = mutation_review.classify(
        [{"line": identity[0], "operator": identity[1], "mutant_sha256": identity[2], "result": "survived"}],
        {identity: "reviewed equivalent"})
    checks["all_equivalent_score_undefined"] = only_equivalent["score"] is None and not errors
    if not checks["all_equivalent_score_undefined"]:
        problems.append("all-equivalent score should be undefined")
    outcomes = [
        ({"status": "pass", "cases": 1}, 0, "survived"),
        ({"status": "pass", "cases": 0}, 0, "invalid"),
        ({"status": "fail", "failures": [{"kind": "heap"}]}, 1, "killed"),
        ({"status": "fail", "failures": [{"kind": "source-boundary"}]}, 1, "killed"),
        ({"status": "fail", "failures": [{"kind": "harness"}]}, 1, "invalid"),
        ({"status": "fail", "failures": []}, 1, "invalid"),
        ({"status": "unknown"}, 1, "invalid"),
        ({"status": "error"}, 1, "invalid"),
    ]
    checks["mutation_outcomes"] = all(mutants.outcome(s, code) == expected for s, code, expected in outcomes)
    if not checks["mutation_outcomes"]:
        problems.append("mutation infrastructure failures incorrectly earned kill credit")
    print(json.dumps({"command": "selftest", "status": "pass" if not problems else "fail", "problems": problems,
                      "checks": checks}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
