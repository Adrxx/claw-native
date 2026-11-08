"""Mutation testing: does the family's test suite notice when the native code is wrong?

Each mutant is the module with one small deliberate error: a dropped store or
call, a shifted field offset, a flipped comparison, two statements swapped. A
mutant is killed when at least one case fails. A mutant that survives marks
behavior no case checks.
"""
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

from . import mutation_review, build_inputs

ROOT = Path(__file__).resolve().parents[2]
STATEMENT = re.compile(r"^(\s*)run\.(put\w*|call|icall|vcall|fastcall|call_x87|call_x87_exact|x87_step|source_call)\(.*\);\s*(?://.*)?$")
SOURCE_EDGE = re.compile(r"^\s*run\.source_(call|tail)\(\s*(0x[0-9a-fA-F]+),\s*[^,\n]+,\s*(0x[0-9a-fA-F]+),\s*[^;\n]+\);\s*(?://.*)?$")
OFFSET = re.compile(r"\+ 0x([0-9a-fA-F]+)")
CONDITION = re.compile(r"\b(if|for|while)\s*\(")
SKIP = ("CLAW_MODULE_ENTRY", "#include", "run.fail(", "return -1", "case 0x")


def outcome(summary, returncode):
    """Only an observed comparison difference earns mutation-kill credit."""
    if summary.get("status") == "pass" and returncode == 0 and summary.get("cases", 0) > 0:
        return "survived"
    differences = {"event", "event-memory", "event-count", "heap", "globals", "ownership",
                   "return-value", "native-fault", "halt", "compiler-context", "stack",
                   "guest-outcome", "guest-state", "guest-owned-entry", "source-boundary"}
    if summary.get("status") == "fail" and any(
            failure.get("kind") in differences for failure in summary.get("failures", [])):
        return "killed"
    return "invalid"


def _flip(line, old, new):
    return line.replace(old, new, 1) if old in line else None


def literal_returns(lines, returns_u32=None):
    """Conservatively select literal returns in addressed uint32_t bodies.

    The generated function_<address> naming convention keeps arity helpers and
    dispatch wrappers out. Mask comments and quoted strings before locating
    signatures/braces; preserve offsets so replacements touch only live code.
    """
    source = "\n".join(lines)
    # These lexical forms need a richer C++ tokenizer. Fail closed rather
    # than mistaking raw-string contents or a continued comment for code.
    if re.search(r'\b(?:u8|u|U|L)?R"', source) or re.search(r'\\\r?\n', source):
        return {}
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    code = tokens.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), source)
    if re.search(r"(?m)^\s*#\s*(?:if|ifdef|ifndef|elif|else|endif)\b", code):
        return {}
    signature = re.compile(r"\buint32_t\s+function_([0-9a-fA-F]+)\s*\([^;{}]*\)\s*\{")
    result = {}
    for match in signature.finditer(code):
        if returns_u32 is not None and int(match.group(1), 16) not in returns_u32:
            continue
        start, cursor, depth = match.end(), match.end(), 1
        while cursor < len(code) and depth:
            depth += (code[cursor] == "{") - (code[cursor] == "}")
            cursor += 1
        if depth:
            continue
        for literal in re.finditer(r"\breturn\s+([01])([uU]?)\s*;", code[start:cursor - 1]):
            offset = start + literal.start(1)
            prefix = code[start:offset]
            # Only the outer implementation body: nested lambdas/functions
            # can return a different type. Nested branch returns are also
            # conservatively left to the other mutation operators.
            if prefix.count("{") != prefix.count("}"):
                continue
            index = code.count("\n", 0, offset)
            column = offset - (code.rfind("\n", 0, offset) + 1)
            # One standalone return per line: never rewrite an inline branch
            # or multiple statements using a line-based mutation identity.
            if re.fullmatch(r"\s*return\s+[01][uU]?\s*;\s*", code.splitlines()[index]):
                result[index] = column
    return result


def mutations(lines, returns_u32=None):
    """Yield (line_number, operator, mutated_lines) for every applicable single change."""
    returns = literal_returns(lines, returns_u32)
    source = "\n".join(lines)
    tokens = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    code = tokens.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), source).splitlines()
    # Conservatively disable the new source-edge operators for lexical forms
    # that this small tokenizer does not understand.
    source_edges_safe = not re.search(r'\b(?:u8|u|U|L)?R"|\\\r?\n', source)

    def statement_at(index):
        if index >= len(lines):
            return None
        match = STATEMENT.match(lines[index])
        if match and match.group(2) == "source_call" and (
                not source_edges_safe or not STATEMENT.match(code[index])):
            return None
        return match

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or any(token in line for token in SKIP):
            continue
        changed = []
        edge = SOURCE_EDGE.match(code[index]) if source_edges_safe else None
        if edge:
            # Keep a tail terminal: deleting a noreturn statement can only
            # produce a compiler error, which is not a comparison kill.
            for group, operator in ((2, "source-edge-target"), (3, "source-edge-site")):
                start, end = edge.span(group)
                changed.append((operator, [line[:start] + f"{int(edge.group(group), 16) + 1:#x}" + line[end:]]))
        if index in returns:
            column = returns[index]
            changed.append(("flip-return-literal", [line[:column] + ("1" if line[column] == "0" else "0") + line[column + 1:]]))
        statement = statement_at(index)
        if statement:
            changed.append(("drop-statement", [statement.group(1) + ";"]))
            following = statement_at(index + 1)
            # Two plain stores to different places can be swapped without any visible effect, so a swap is only a
            # real error when at least one of the two statements is an outside call.
            if following and {statement.group(2), following.group(2)} & {
                    "call", "icall", "vcall", "fastcall", "call_x87", "call_x87_exact", "x87_step", "source_call"}:
                yield index + 1, "swap-statements", lines[:index] + [lines[index + 1], line] + lines[index + 2:]
        offset = OFFSET.search(line)
        if offset:
            shifted = f"+ {int(offset.group(1), 16) + 4:#x}"
            changed.append(("shift-offset", [line[:offset.start()] + shifted + line[offset.end():]]))
        if CONDITION.search(line):
            for operator, old, new in (("lt-to-le", " < ", " <= "), ("le-to-lt", " <= ", " < "),
                                       ("eq-to-ne", " == ", " != "), ("ne-to-eq", " != ", " == "),
                                       ("negate", "if (!", "if (")):
                flipped = _flip(line, old, new)
                if flipped:
                    changed.append((operator, [flipped]))
        for operator, old, new in (("minus-one", " - 1", " - 2"), ("halve", " / 2", " / 3")):
            flipped = _flip(line, old, new)
            if flipped:
                changed.append((operator, [flipped]))
        for operator, replacement in changed:
            yield index + 1, operator, lines[:index] + replacement + lines[index + 1:]


def run(spec_path, seed=0, limit=48, jobs=4):
    spec = json.loads(Path(spec_path).read_text())
    if spec.get("mutation") == "named-layout": from . import named_layout_mutants; return named_layout_mutants.run(spec_path, seed, limit, jobs)
    module = ROOT / build_inputs.sources(spec)[0]
    source_text = module.read_bytes().decode("utf-8")
    lines = source_text.splitlines()
    # A uint32_t wrapper also transports normalized void entries. Their
    # return literal is not part of original behavior and must not mutate.
    returns_u32 = {int(f["address"], 16) for f in spec["owned"] if f.get("returns") == "u32"}
    every = list(mutations(lines, returns_u32))
    reviewed, review_errors = mutation_review.validate(
        source_text, every, spec.get("oracle", {}).get("equivalent_mutants", []))
    step = max(1, len(every) // limit) if limit else 1
    chosen = every[::step][:limit] if limit else every
    scratch = ROOT / "work" / "build" / "mutants" / spec["id"]
    scratch.mkdir(parents=True, exist_ok=True)

    def attempt(item):
        number, (line, operator, mutated) = item
        source = scratch / f"mutant-{number}.cpp"
        changed_source = "\n".join(mutated) + "\n"
        source.write_text(changed_source)
        identity = {"line": line, "operator": operator,
                    "mutant_sha256": mutation_review.digest(changed_source)}
        command = [sys.executable, "-m", "clawparity.runner", str(spec_path), "--seed", str(seed),
                   "--module-source", str(source)]
        try:
            done = subprocess.run(command, cwd=ROOT / "Tests", capture_output=True, text=True, timeout=300)
            summary = json.loads(done.stdout.strip().splitlines()[-1])
        except subprocess.TimeoutExpired:
            return {**identity, "result": "invalid", "detail": "mutation subprocess timed out"}
        except (IndexError, ValueError):
            return {**identity, "result": "invalid"}
        result = outcome(summary, done.returncode)
        return {**identity, "result": result, "text": lines[line - 1].strip()[:140]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(attempt, enumerate(chosen)))
    summary, classification_errors = mutation_review.classify(results, reviewed)
    review_errors.extend(classification_errors)
    return {"command": "mutants", "family": spec["id"], "candidates": len(every), "tried": len(results),
            **summary, "source_sha256": mutation_review.digest(source_text),
            "review_errors": review_errors, "status": "fail" if review_errors else "pass"}


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(prog="clawparity.mutants")
    parser.add_argument("spec")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--limit", type=int, default=48)
    parser.add_argument("--jobs", type=int, default=4)
    options = parser.parse_args(argv)
    if options.jobs < 1:
        parser.error("--jobs must be positive")
    result = run(options.spec, options.seed, options.limit, options.jobs)
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
