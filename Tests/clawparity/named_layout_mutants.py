"""Opt-in mutations of recovered field uses, constants and registered bodies.

This intentionally supports a small, documented C++ spelling, not arbitrary C++.
Unsupported accessor syntax fails closed. Only the primary scratch translation
unit changes; layout headers and auxiliary/shared sources are never rewritten.
"""
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

from . import build_inputs, mutation_review, mutants as literal

ROOT = Path(__file__).resolve().parents[2]
HEADERS = ("Sources/ClawRecoveredLayout.h", "Sources/ClawRecoveredNames.h")
TOKENS = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
NUMBER = r"(?:0x[\da-fA-F]+|\d+)"


def masked(source):
    return TOKENS.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), source)


def closing(code, start, left="(", right=")"):
    depth = 1
    for pos in range(start + 1, len(code)):
        depth += (code[pos] == left) - (code[pos] == right)
        if not depth:
            return pos
    raise ValueError("unbalanced named-layout source")


def layouts(header):
    code = masked(header)
    offsets = {(m[1], m[2]): int(m[3], 0) for m in re.finditer(
        rf"static_assert\(offsetof\((\w+),\s*(\w+)\)\s*==\s*({NUMBER})\s*,", code)}
    result = {}
    for cls in re.finditer(r"\bclass\s+(\w+)\s*\{", code):
        end = closing(code, cls.end() - 1, "{", "}")
        body = code[cls.end():end]
        fields = {}
        for field in re.finditer(r"CLAW_RECOVERED_FIELD\((\w+),\s*offsetof\((\w+),\s*(\w+)\)\)", body):
            key = field[2], field[3]
            if key not in offsets:
                raise ValueError(f"field {key} needs a compiled offsetof static_assert")
            fields[field[1]] = offsets[key]
        if len(re.findall(r"CLAW_RECOVERED_FIELD\s*\(", body)) != len(fields):
            raise ValueError("recovered fields require unique names and checked offsetof expressions")
        if fields:
            result[cls[1]] = fields
    if not result:
        raise ValueError("no recovered fields declared")
    return result


def registrations(code, spec):
    """Address switch registrations or {address, body} table rows, never aliases."""
    mapping = {}
    pattern = (r"\bcase\s+(0x[\da-fA-F]+)\s*:\s*return\s+(\w+)\s*\(run\s*,"
               r"|\{\s*(0x[\da-fA-F]+)\s*,\s*&?(\w+)\s*\}")
    owned = {int(e["address"], 16) for e in spec["owned"]}
    for match in re.finditer(pattern, code):
        address = int(match[1] or match[3], 16)
        name = match[2] or match[4]
        if address in owned:
            if name in mapping and mapping[name] != address:
                raise ValueError(f"ambiguous registration for {name}")
            mapping[name] = address
    signatures = {}
    for match in re.finditer(r"\buint32_t\s+(\w+)\s*\(\s*Run\s*&\s*run\s*,\s*uint32_t\s+\w+\s*,\s*const\s+uint32_t\s*\*\s*\w+\s*\)\s*\{", code):
        if match[1] in mapping:
            signatures[match[1]] = (match.end(), closing(code, match.end() - 1, "{", "}"))
    if set(mapping.values()) != owned or set(signatures) != set(mapping):
        raise ValueError("named-layout requires one registered canonical body for every owned address")
    if len(mapping) != len(owned):
        raise ValueError("duplicate named-layout entry registrations")
    return mapping, signatures


def constants(headers):
    result = {}
    for header in headers:
        code = masked(header)
        for enum in re.finditer(r"enum\s+class\s+(\w+)\s*(?::\s*\w+)?\s*\{([^{}]*)\}", code):
            values = []
            for entry in filter(str.strip, enum[2].split(",")):
                match = re.fullmatch(rf"\s*(\w+)\s*=\s*({NUMBER})[uUlL]*\s*", entry)
                if not match:
                    raise ValueError("named-layout enum values must be explicit integer literals")
                values.append((match[1], int(match[2], 0)))
            for index, (name, value) in enumerate(values):
                following = values[index + 1:] + values[:index]
                other = next((n for n, v in following if v != value), None)
                if other:
                    result[f"{enum[1]}::{name}"] = f"{enum[1]}::{other}"
        for const in re.finditer(rf"\bconstexpr\s+(?:u?int(?:8|16|32|64)_t|unsigned|int)\s+(\w+)\s*=\s*({NUMBER})[uUlL]*\s*;", code):
            result[const[1]] = f"({const[1]} ^ 1u)"
    return result


def population(source, spec, *, root=ROOT):
    if re.search(r'\b(?:u8|u|U|L)?R"|\\\r?\n', source):
        raise ValueError("named-layout does not support raw strings or line continuations")
    code = masked(source)
    if re.search(r"(?m)^\s*#\s*(?:if|ifdef|ifndef|elif|else|endif|define)\b", code):
        raise ValueError("named-layout requires unconditional primary source")
    headers = [(root / name).read_text() for name in HEADERS]
    fields = layouts(headers[0])
    mapping, bodies = registrations(code, spec)
    # A variable name must identify one view type/transport throughout this TU.
    # Ambiguous shadowing is rejected instead of guessing its C++ lookup scope.
    variables = {}
    for cls in fields:
        for match in re.finditer(rf"\b{cls}\s+(\w+)\s*[{{(]\s*(\w+)\s*,", code):
            value = cls, match[2]
            if match[1] in variables and variables[match[1]] != value:
                raise ValueError(f"ambiguous view variable {match[1]}")
            variables[match[1]] = value
    method_names = "|".join(sorted({name for view in fields.values() for name in view}))
    for match in re.finditer(rf"\b(\w+)\s*(\.|->)\s*(?:template\s+)?({method_names})\s*(?:<[^>]*>\s*)?\(", code):
        if match[1] not in variables or match[2] != "." or "template" in match[0]:
            raise ValueError("recovered field calls require a directly declared value view")
    lines = source.splitlines()
    code_lines = code.splitlines()
    lowered = list(code_lines)
    shifts = {}
    uses = []
    for index, line in enumerate(code_lines):
        replacements = []
        for call in re.finditer(r"\b(\w+)\.(\w+)\s*(?:<[^>]*>\s*)?\(", line):
            if call[1] not in variables:
                continue
            cls, memory = variables[call[1]]
            if call[2] not in fields[cls]:
                raise ValueError(f"unknown field accessor {cls}.{call[2]}")
            if "<" in call[0]:
                raise ValueError("production accessor uses must not specify a mutation delta")
            end = closing(line, call.end() - 1) + 1
            args = line[call.end():end - 1]
            offset = fields[cls][call[2]]
            expansion = (f"{memory}.put({call[1]} + {offset:#x}, {args})" if args.strip()
                         else f"{memory}.get({call[1]} + {offset:#x})")
            replacements.append((call.start(), end, expansion, call.end() - 1))
            uses.append((index, call.end() - 1))
        cursor, chunks, positions, length = 0, [], [], 0
        for start, end, expansion, paren in replacements:
            if start < cursor:
                raise ValueError("nested recovered field uses require separate statements")
            prefix = line[cursor:start]
            chunks.extend((prefix, expansion))
            length += len(prefix)
            positions.append((length, length + len(expansion), paren))
            length += len(expansion)
            cursor = end
        chunks.append(line[cursor:])
        lowered[index] = "".join(chunks)
        first = literal.OFFSET.search(lowered[index])
        if first:
            for start, end, paren in positions:
                if start <= first.start() < end:
                    shifts[index] = paren
    # Catch line-wrapped, pointer, aliased or otherwise unrecognized accessor
    # calls rather than silently lowering only the supported subset.
    recognized = sum(len(re.findall(rf"\b{re.escape(v)}\.\w+\s*\(", code)) for v in variables)
    if recognized != len(uses):
        raise ValueError("unsupported multiline recovered field use")
    for cls in fields:
        declarations = len(re.findall(rf"\b{cls}\s+\w+\s*[{{(]", code))
        bindings = len(re.findall(rf"\b{cls}\s+\w+\s*[{{(]\s*\w+\s*,", code))
        if declarations != bindings:
            raise ValueError("unsupported recovered view declaration")
    # Virtual names expose consumed returns to the unchanged literal selector.
    for index, line in enumerate(lowered):
        for name, address in mapping.items():
            line = re.sub(rf"\b{re.escape(name)}\b", f"function_{address:x}", line)
        lowered[index] = line
    returns = {int(e["address"], 16) for e in spec["owned"] if e.get("returns") == "u32"}
    legacy, added = [], []
    flips = {"lt-to-le": (" < ", " <= "), "le-to-lt": (" <= ", " < "),
             "eq-to-ne": (" == ", " != "), "ne-to-eq": (" != ", " == "),
             "negate": ("if (!", "if ("), "minus-one": (" - 1", " - 2"), "halve": (" / 2", " / 3")}
    for number, operator, unused in literal.mutations(lowered, returns):
        index, changed = number - 1, list(lines)
        line = lines[index]
        if operator == "swap-statements":
            changed[index:index + 2] = lines[index:index + 2][::-1]
        elif operator == "drop-statement":
            changed[index] = re.match(r"\s*", line)[0] + ";"
        elif operator == "shift-offset":
            if index in shifts:
                pos = shifts[index]
                changed[index] = line[:pos] + "<4>" + line[pos:]
            else:
                match = literal.OFFSET.search(code_lines[index])
                if not match:
                    raise ValueError("cannot map literal offset back to source")
                changed[index] = line[:match.start()] + f"+ {int(match[1], 16) + 4:#x}" + line[match.end():]
        elif operator in flips:
            old, new = flips[operator]
            pos = code_lines[index].find(old)
            if pos < 0:
                raise ValueError(f"cannot map {operator} back to source")
            changed[index] = line[:pos] + new + line[pos + len(old):]
        elif operator == "flip-return-literal":
            match = re.search(r"\breturn\s+([01])", code_lines[index])
            pos = match.start(1)
            changed[index] = line[:pos] + str(1 - int(line[pos])) + line[pos + 1:]
        elif operator in ("source-edge-target", "source-edge-site"):
            edge = literal.SOURCE_EDGE.match(code_lines[index])
            group = 2 if operator == "source-edge-target" else 3
            start, end = edge.span(group)
            changed[index] = line[:start] + f"{int(edge[group], 16) + 1:#x}" + line[end:]
        else:
            raise ValueError(f"unmapped literal operator {operator}")
        legacy.append((number, operator, changed))
    # Every accessor use gets its own offset control, including the second use
    # on a line and zero/decimal offsets the literal selector cannot see.
    for index, paren in uses:
        changed = list(lines)
        changed[index] = lines[index][:paren] + "<4>" + lines[index][paren:]
        if not any(row[2] == changed for row in legacy):
            added.append((index + 1, "shift-named-offset", changed))
    for name, replacement in constants(headers + [source]).items():
        for match in re.finditer(rf"(?<![\w:])(?:\w+::)*{re.escape(name)}\b", code):
            if not any(start <= match.start() < end for start, end in bodies.values()):
                continue
            # Keep a namespace qualifier on a scoped enumerator. A named
            # integer expression instead encloses the entire qualified name.
            value = (match[0][:-len(name)] + replacement if "::" in name
                     else f"({match[0]} ^ 1u)")
            prefix = code[code.rfind(";", 0, match.start()) + 1:match.start()]
            if "constexpr" in prefix and "=" not in prefix:
                continue  # declaration, not a constant use
            changed_source = source[:match.start()] + value + source[match.end():]
            added.append((code.count("\n", 0, match.start()) + 1, "swap-named-constant", changed_source.splitlines()))
    entries = {int(e["address"], 16): e for e in spec["owned"]}
    for name, address in mapping.items():
        # Only ABI-compatible alternatives: bad arity alone is not a useful kill.
        own = entries[address]
        alternatives = [n for n, a in mapping.items() if n != name and
                        all(entries[a].get(k) == own.get(k) for k in ("argc", "returns", "convention"))]
        if not alternatives:
            continue
        for match in re.finditer(rf"\b{re.escape(name)}\s*\(\s*run\s*,", code):
            if not any(start <= match.start() < end for start, end in bodies.values()):
                continue
            changed_source = source[:match.start()] + alternatives[0] + source[match.start() + len(name):]
            added.append((code.count("\n", 0, match.start()) + 1, "redirect-named-call", changed_source.splitlines()))
    return legacy, added


def selected(legacy, added, limit):
    # Extra named operators must not crowd out the pre-existing sample. Always
    # exercise every newly hidden use; the limit applies to the legacy pool.
    step = max(1, len(legacy) // limit) if limit else 1
    return (legacy[::step][:limit] if limit else legacy) + added


def attempt(spec_path, source, item, number, scratch, seed):
    line, operator, changed = item
    text = "\n".join(changed) + "\n"
    path = scratch / f"mutant-{number}.cpp"
    path.write_text(text)
    identity = {"line": line, "operator": operator, "mutant_sha256": mutation_review.digest(text)}
    command = [sys.executable, "-m", "clawparity.runner", str(Path(spec_path).resolve()),
               "--seed", str(seed), "--module-source", str(path)]
    try:
        done = subprocess.run(command, cwd=ROOT / "Tests", capture_output=True, text=True, timeout=300)
        summary = json.loads(done.stdout.strip().splitlines()[-1])
        result = literal.outcome(summary, done.returncode)
        detail = {"failures": summary.get("failures", [])[:1]} if result == "killed" else {}
        if result == "invalid":
            detail = {"detail": done.stderr[-2000:] or str(summary)[:2000]}
    except subprocess.TimeoutExpired:
        result, detail = "invalid", {"detail": "mutation subprocess timed out"}
    except (IndexError, ValueError):
        result, detail = "invalid", {"detail": done.stderr[-2000:]}
    return {**identity, "result": result, "text": source.splitlines()[line - 1].strip()[:140], **detail}


def run(spec_path, seed=0, limit=48, jobs=4):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    if not set(HEADERS).issubset(spec.get("sources", [])):
        raise ValueError("named-layout requires both recovered headers in sources for build-cache identity")
    source = (ROOT / build_inputs.sources(spec)[0]).read_text()
    legacy, added = population(source, spec)
    every = legacy + added
    reviewed, errors = mutation_review.validate(source, every, spec.get("oracle", {}).get("equivalent_mutants", []))
    chosen = selected(legacy, added, limit)
    scratch = ROOT / "work/build/named-layout-mutants" / spec["id"]
    scratch.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda pair: attempt(spec_path, source, pair[1], pair[0], scratch, seed), enumerate(chosen)))
    summary, classification_errors = mutation_review.classify(results, reviewed)
    errors.extend(classification_errors)
    return {"command": "mutants", "family": spec["id"], "mutation": "named-layout",
            "candidates": len(every), "legacy_candidates": len(legacy), "named_candidates": len(added),
            "tried": len(results), **summary, "results": results,
            "source_sha256": mutation_review.digest(source), "review_errors": errors,
            "status": "fail" if errors else "pass"}
