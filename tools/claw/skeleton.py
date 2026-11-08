"""Generates the starting files of a canonical family from its specification.

Writes the module with one unimplemented stub per owned function and an empty
cases file. Existing files are never overwritten. Prints one JSON line.
"""
import json
import sys
from pathlib import Path

from .paths import ROOT
from .manifest import compiler_contract_errors
from Tests.clawparity import build_inputs

MODULE = '''// {title}
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {{

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {{
    switch (function) {{
{owned_cases}    default:
        return -1;
    }}
}}

{stubs}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {{
    switch (function) {{
{body_cases}    default:
        run.fail(CLAW_FAULT_ABI, function);
    }}
}}

}} // namespace

CLAW_MODULE_ENTRY({entry}, owned, body)
'''

STUB = '''// {address}{name}. {convention}, {argc} stack argument(s), returns {returns}.
uint32_t function_{digits}(Run &run, uint32_t receiver, const uint32_t *arguments) {{
    (void)receiver;
    (void)arguments;
    run.fail(CLAW_FAULT_UNIMPLEMENTED, {address});
}}

'''

CASES = '''"""Cases for {id}: {title}."""
from clawparity.cases import Case
from clawparity.fixtures import allocate, halt, release, returns, sequence, store_words  # noqa: F401


def cases(random_source):
    """Yield Case objects. See Tests/clawparity/examples/surface_flip/cases.py for a worked example."""
    return
    yield
'''


def generate(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    errors = compiler_contract_errors(spec)
    if errors:
        raise ValueError("; ".join(errors))
    special = bool(spec["owned"]) and spec["owned"][0].get("convention") == "compiler-context"
    module = ROOT / build_inputs.sources(spec, require_exists=False)[0]
    cases = ROOT / spec["oracle"]["cases"]
    entry = spec["oracle"].get("entry", f"claw_{spec['id']}_entry")
    owned_cases, stubs, body_cases = "", "", ""
    for function in spec["owned"]:
        address = function["address"]
        digits = address[2:]
        owned_cases += f"    case {address}:\n        return {function.get('argc') or 0};\n"
        body_cases += f"    case {address}:\n        return function_{digits}(run, receiver, arguments);\n"
        label = f" {function['name']}" if function.get("name") else ""
        stubs += STUB.format(address=address, name=label, convention=function.get("convention", "unknown"),
                             argc=function.get("argc") or 0, returns=function.get("returns", "u32"), digits=digits)
    written = []
    if not module.exists():
        module.parent.mkdir(parents=True, exist_ok=True)
        text = MODULE.format(title=spec["title"], owned_cases=owned_cases, stubs=stubs,
                             body_cases=body_cases, entry=entry)
        if special:
            text = text.replace("int owned(uint32_t function)", "bool owned(uint32_t function)")
            text = text.replace("return 0;", "return true;").replace("return -1;", "return false;")
            text = text.replace("uint32_t function_", "void function_").replace("uint32_t body(", "void body(")
            text = text.replace("uint32_t receiver, const uint32_t *arguments", "ClawCompilerContext &context")
            text = text.replace("    (void)receiver;\n    (void)arguments;", "    (void)context;")
            text = text.replace("(run, receiver, arguments)", "(run, context)")
            text = text.replace("CLAW_MODULE_ENTRY(", "CLAW_COMPILER_MODULE_ENTRY(")
        if any('source_context' in entry for entry in spec['owned']):
            contracts = []
            for entry in spec['owned']:
                if 'source_context' not in entry:
                    contracts.append(f"    case {entry['address']}: return {{}};")
                    continue
                c = entry['source_context']
                pops = 4 * entry['argc'] if entry['convention'] in ('stdcall', 'thiscall', 'fastcall') else 0
                contracts.append(f"    case {entry['address']}: return {{{c['input_mask']}u, {c['output_mask']}u, {c['preserve_mask']}u, {pops}u}};")
            helper = "static ClawSourceContract source_contract(uint32_t function) {\n    switch (function) {\n" + "\n".join(contracts) + "\n    default: return {};\n    }\n}\n"
            if any(entry.get('source_context', {}).get('optional', False) for entry in spec['owned']):
                choices = []
                for entry in spec['owned']:
                    optional = 'source_context' not in entry or entry['source_context'].get('optional', False)
                    choices.append(f"    case {entry['address']}: return {'true' if optional else 'false'};")
                selector = 'static bool source_optional(uint32_t function) {\n    switch (function) {\n' + '\n'.join(choices) + '\n    default: return false;\n    }\n}\n'
                text = text.replace('CLAW_MODULE_ENTRY(', helper + selector + 'CLAW_OPTIONAL_SOURCE_MODULE_ENTRY(')
                text = text.replace(', owned, body)', ', owned, source_contract, source_optional, body, body)')
            else:
                text = text.replace('CLAW_MODULE_ENTRY(', helper + 'CLAW_SOURCE_MODULE_ENTRY(')
                text = text.replace(", owned, body)", ", owned, source_contract, body)")
        module.write_text(text)
        written.append(str(module.relative_to(ROOT)))
    if not cases.exists():
        cases.parent.mkdir(parents=True, exist_ok=True)
        cases.write_text(CASES.format(id=spec["id"], title=spec["title"]))
        written.append(str(cases.relative_to(ROOT)))
    return {"command": "skeleton", "family": spec["id"], "written": written, "functions": len(spec["owned"]),
            "status": "pass"}


def main(argv):
    print(json.dumps(generate(argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
