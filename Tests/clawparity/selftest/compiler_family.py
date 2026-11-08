"""Canonical special-entry pipeline tests with owned, independently authored x86.

The generated ignored pilot is a harness fixture, never a game admission.
"""
import copy
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

from .. import build, gate, mutants, runner
from ..cases import compiler_contract_errors
from ..kernel import CONTEXT_ALL
from ..program import Program, Section

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
CODE = bytes.fromhex('894424fc 8b0424 895c2404 8d6c24fc 64892d00000000 8d6424fc ffe0')


def program():
    # Store incoming values into guest stack, publish a frame, transfer to the
    # real return PC through EAX. The continuation bytes must not execute.
    code = CODE + bytes([0xcc]) * (0x100 - len(CODE))
    return Program('compiler-family-synthetic', '', 0x400000, 0x3000,
        [Section('.text', 0x401000, len(code), code),
         Section('.data', 0x402000, 0x1000, bytes(0x1000))],
        (0x401000, 0x401100), {})


def prepare():
    directory = ROOT / 'work/pilot/compiler_family_selftest'
    directory.mkdir(parents=True, exist_ok=True)
    for source, target in (('compiler_family_module.cpp', 'Module.cpp'), ('compiler_family_cases.py', 'cases.py')):
        (directory / target).write_text((HERE / source).read_text())
    relative = str(directory.relative_to(ROOT))
    spec = {'schema': 1, 'id': 'compiler_family_selftest', 'title': 'Synthetic special-entry pipeline',
        'abi': 'canonical', 'program': 'compiler-family-synthetic', 'sources': [relative + '/Module.cpp'],
        'owned': [{'address': '0x401000', 'convention': 'compiler-context', 'argc': 0, 'returns': 'context',
            'compiler_context': {'input_mask': CONTEXT_ALL, 'output_mask': CONTEXT_ALL},
            'interval_end': hex(0x401000 + len(CODE))}],
        'callees': {}, 'oracle': {'kind': 'clawparity', 'cases': relative + '/cases.py',
                                 'entry': 'claw_compiler_family_entry'},
        'evidence': {'level': 'none'}, 'integration': {'level': 'source-only'}}
    path = directory / 'family.json'
    path.write_text(json.dumps(spec, indent=2) + chr(10))
    return path, spec


def generator_checks(spec):
    # CLI tooling is rooted above Tests; this test keeps ordinary harness
    # imports independent of the tooling package.
    sys.path.insert(0, str(ROOT))
    try:
        from tools.claw import gen_project, manifest, skeleton
    finally:
        sys.path.pop(0)
    found = {'schema_accepts_context': not manifest.validate(spec)}
    with tempfile.TemporaryDirectory(dir=ROOT / 'work/pilot', prefix='compiler-generators-') as scratch:
        scratch = Path(scratch)
        generated = copy.deepcopy(spec)
        generated['sources'] = [str((scratch / 'Stub.cpp').relative_to(ROOT))]
        generated['oracle']['cases'] = str((scratch / 'stub_cases.py').relative_to(ROOT))
        generated_path = scratch / 'family.json'
        generated_path.write_text(json.dumps(generated))
        skeleton.generate(generated_path)
        source = scratch / 'Stub.cpp'
        found['compiler_skeleton_macro'] = 'CLAW_COMPILER_MODULE_ENTRY(' in source.read_text()
        build.library('compiler-family-skeleton', [source])
        found['compiler_skeleton_compiles'] = True
        admitted = copy.deepcopy(spec)
        admitted['sources'] = ['Sources/SyntheticCompilerFamily.cpp']
        admitted['evidence']['level'] = 'admitted'
        with patch.object(gen_project, 'checked_source', side_effect=lambda path, *, root=None: path):
            registry = gen_project.canonical_inventory([admitted], [])[2]
        found['registry_special_metadata'] = registry[0]['convention'] == 'compiler-context' and registry[0]['returns'] == 'context'
        ordinary = dict(registry[0], address=0x401100, convention='cdecl', returns='u32',
                        entry='claw_ordinary_fixture_entry')
        header = gen_project.canonical_dispatch_text(registry + [ordinary])
        (scratch / 'dispatch.h').write_text(header)
        c = scratch / 'dispatch.c'
        c.write_text(r"""
#include "dispatch.h"
#include <assert.h>
static unsigned calls;
uint32_t claw_compiler_family_entry(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    calls++; *out=123; return 1;
}
uint32_t claw_ordinary_fixture_entry(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    calls++; *out=123; return 1;
}
int main(void) {
    ClawCall call = {0}; ClawHost host = {0}; ClawCompilerContext ctx = {0};
    uint32_t result = 77;
    assert(claw_canonical_lookup(0x401000)->convention == CLAW_CANONICAL_COMPILER_CONTEXT);
    assert(claw_canonical_lookup(0x401000)->returnKind == CLAW_CANONICAL_RETURN_CONTEXT);
    call.function = 0x401000;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    assert(host.fault == CLAW_FAULT_ABI && result == 77 && calls == 0);
    host.fault = 0; call.compilerContext = &ctx; host.compilerContext = &ctx;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    assert(result == 77 && calls == 0);
    host.fault = 0; call.function = 0x401100;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    host.fault = 0; host.compilerContext = 0;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    host.fault = 0; host.compilerContext = &ctx; call.compilerContext = 0;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    host.fault = 0; host.compilerContext = 0;
    assert(claw_canonical_dispatch(&call, &host, &result));
    assert(result == 123 && calls == 1);
    host.fault = CLAW_FAULT_MEMORY; host.faultAddress = 83; result = 77;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    assert(host.fault == CLAW_FAULT_MEMORY && host.faultAddress == 83 && result == 77 && calls == 1);
    return 0;
}
""")
        executable = scratch / 'dispatch'
        subprocess.run(build.compiler() + ['-x', 'c', '-std=c11', '-I', str(ROOT / 'Sources'),
                       str(c), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
        found['dispatch_fails_closed'] = True
    return found

def checks():
    path, spec = prepare()
    found = generator_checks(spec)
    original = runner.run(path, seed=73, original_only=True, trace=True)
    found['original_cases_coverage'] = (original['status'] == 'pass' and
        original.get('coverage', {}).get('0x401000', {}).get('executed') == len(CODE))
    for flavor in ('O0', 'O2'):
        result = runner.run(path, seed=73, flavor=flavor, trace=True)
        found[flavor] = result['status'] == 'pass'
    source = (path.parent / 'Module.cpp').read_text()
    variants = {
        'context': ('context.eax = run.get(frame);', 'context.eax = 17;', 'compiler-context'),
        'stack': ('run.put(frame - 4, context.eax);', ';', 'stack'),
        'unselected': ('context.eip = context.continuation;', 'context.ebx ^= 1; context.eip = context.continuation;', 'compiler-context'),
        'header': ('context.eip = context.continuation;', 'context.reserved0 = 1; context.eip = context.continuation;', 'native-fault')}
    for label, (old, new, kind) in variants.items():
        bad = path.parent / (label + '.cpp')
        bad.write_text(source.replace(old, new))
        result = runner.run(path, module_source=bad)
        found['reject_' + label] = (result['status'] == 'fail' and
            kind in {failure['kind'] for failure in result['failures']} and mutants.outcome(result, 1) == 'killed')
    raw = path.parent / 'raw_header.cpp'
    raw.write_text(source.replace('CLAW_COMPILER_MODULE_ENTRY(claw_compiler_family_entry, owned, body)', """
extern "C" uint32_t claw_compiler_family_entry(uint32_t function, uint32_t, const uint32_t *,
    uint32_t, ClawHost *host, uint32_t *result) {
    if (!owned(function)) return 0;
    claw::Run run(*host);
    auto &context = *host->compilerContext;
    body(run, function, context);
    context.outputMask = CLAW_CONTEXT_REQUIRED;
    *result = context.eax;
    return 1;
}
"""))
    raw_result = runner.run(path, module_source=raw)
    found['runner_header_comparison'] = any(f['kind'] == 'compiler-context' and 'outputMask' in f['detail']
                                            for f in raw_result.get('failures', []))
    # Minimal selected outputs still preserve unselected caller fields. A module
    # corrupting such a field must be rejected by the runtime, not normalized.
    partial = copy.deepcopy(spec)
    partial['owned'][0]['compiler_context']['output_mask'] = 0x5c1
    partial_path = path.parent / 'partial.json'
    partial_cases = path.parent / 'partial_cases.py'
    partial_cases.write_text((path.parent / 'cases.py').read_text().replace(
        '72, 1, CONTEXT_ALL, CONTEXT_ALL,', '72, 1, CONTEXT_ALL, 0x5c1,'))
    partial['oracle']['cases'] = str(partial_cases.relative_to(ROOT))
    partial_path.write_text(json.dumps(partial))
    found['partial_outputs'] = runner.run(partial_path)['status'] == 'pass'
    rejected = runner.run(partial_path, module_source=path.parent / 'unselected.cpp')
    found['unselected_preservation'] = any(f['kind'] == 'native-fault' for f in rejected.get('failures', []))
    invalid_cases = {
        'missing': ('compiler_context=lambda value: value', 'compiler_context=None'),
        'receiver': ('setup=setup,', 'setup=setup, receiver=1,'),
        'arguments': ('setup=setup,', 'setup=setup, arguments=(1,),'),
        'override': ('setup=setup,', 'setup=setup, compare_eax=False,'),
        'halt': ('setup=setup,', 'setup=setup, expect="halt",'),
        'mask': ('72, 1, CONTEXT_ALL, CONTEXT_ALL,', '72, 1, CONTEXT_ALL, 0x5c1,'),
        'size': ('72, 1, CONTEXT_ALL', '68, 1, CONTEXT_ALL'),
        'version': ('72, 1, CONTEXT_ALL', '72, 2, CONTEXT_ALL'),
        'stack': ('STACK_TOP + 0x100, frame,', 'STACK_TOP + 0x100, STACK_BASE - 4,'),
        'eip': ('frame, 0x401000,', 'frame, 0x401001,'),
        'continuation': ('head, continuation, 0, 0)', 'head, 0x402000, 0, 0)'),
        'reserved': ('head, continuation, 0, 0)', 'head, continuation, 1, 0)')}
    for label, (old, new) in invalid_cases.items():
        case_path = path.parent / ('invalid_' + label + '.py')
        case_path.write_text((path.parent / 'cases.py').read_text().replace(old, new))
        invalid = copy.deepcopy(spec)
        invalid['oracle']['cases'] = str(case_path.relative_to(ROOT))
        invalid_path = path.parent / ('invalid_' + label + '.json')
        invalid_path.write_text(json.dumps(invalid))
        result = runner.run(invalid_path, original_only=True)
        found['case_reject_' + label] = result['status'] == 'fail' and all(f['kind'] == 'harness' for f in result['failures'])
    early_cases = path.parent / 'early_continuation.py'
    early_cases.write_text((path.parent / 'cases.py').read_text().replace(
        '(0x401080, 0x401090)', '(0x401004,)'))
    early = copy.deepcopy(spec)
    early['oracle']['cases'] = str(early_cases.relative_to(ROOT))
    early_path = path.parent / 'early_continuation.json'
    early_path.write_text(json.dumps(early))
    early_result = runner.run(early_path, original_only=True, trace=True)
    found['continuation_does_not_cover_unexecuted_block_tail'] = (
        early_result['status'] == 'pass' and early_result['coverage']['0x401000']['executed'] == 4)
    ordinary = copy.deepcopy(spec)
    ordinary['owned'][0].update(convention='cdecl', returns='u32')
    del ordinary['owned'][0]['compiler_context']
    ordinary_path = path.parent / 'ordinary_mismatch.json'
    ordinary_path.write_text(json.dumps(ordinary))
    found['ordinary_rejects_context'] = runner.run(ordinary_path, original_only=True)['status'] == 'fail'
    for label, change in (
        ('ordinary_context', {'convention': 'cdecl', 'returns': 'u32'}),
        ('context_argc', {'argc': 1}), ('context_return', {'returns': 'u32'}),
        ('context_missing', {'compiler_context': None}),
        ('context_mask', {'compiler_context': {'input_mask': 0x7ff, 'output_mask': 0xffff}})):
        invalid = copy.deepcopy(spec)
        invalid['owned'][0].update(change)
        found['contract_' + label] = bool(compiler_contract_errors(invalid))
    admitted = gate.run(path, mutant_jobs=1)
    (path.parent / 'gate.json').write_text(json.dumps(admitted, indent=2) + chr(10))
    found['unchanged_gate'] = admitted['status'] == 'admitted'
    found['gate_real_mutations'] = (admitted['checks'].get('mutants', {}).get('killed', 0) >= 3 and
                                  admitted['checks']['mutants']['score'] == 1.0)
    for label, kind in (('context', 'compiler-context'), ('stack', 'stack')):
        invalid = copy.deepcopy(spec)
        invalid['sources'] = [str((path.parent / (label + '.cpp')).relative_to(ROOT))]
        invalid_path = path.parent / ('bad_' + label + '.json')
        invalid_path.write_text(json.dumps(invalid))
        rejected = gate.run(invalid_path, mutant_jobs=1)
        (path.parent / ('bad_' + label + '.gate.json')).write_text(json.dumps(rejected, indent=2))
        found['gate_rejects_bad_' + label] = (rejected['status'] == 'rejected' and
            any(f['kind'] == kind for f in rejected['checks']['first_failures']))
    found['ordinary_mutation_classification'] = (mutants.outcome({'status': 'fail', 'failures': [{'kind': 'heap'}]}, 1) == 'killed'
        and mutants.outcome({'status': 'fail', 'failures': [{'kind': 'harness'}]}, 1) == 'invalid')
    return found


if __name__ == '__main__':
    found = checks()
    print(json.dumps({'checked': len(found), 'failed': [name for name, ok in found.items() if not ok]}))
    raise SystemExit(not all(found.values()))
