"""Build one family manifest per Codex-era native module, mechanically.

Usage:
    python -m tools.claw.import_legacy            write every manifest
    python -m tools.claw.import_legacy --refresh  update only source_sha256,
                                                  integration and oracle.commands
                                                  of the manifests that exist

A module is a Sources/<Name>.cpp (with its header and optional .inc). Its
tests, documents, scratch directories and coordinator logs are found by name
first and by content second. Everything the rules cannot state truthfully is
left empty or "unknown" rather than guessed.

The final stdout line is one JSON object with the summary numbers.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from . import legacy
from . import manifest as manifest_module
from .paths import DOCS, FAMILIES, ROOT, SOURCES, TESTS, WORK

# Codex left these four unfinished, so their comparisons count only as provisional.
PROVISIONAL_FAMILIES = {
    "startup_logic_registration",
    "application_archive_path",
    "player_profile_confirmation",
    "surface_transform",
}

# Module base names whose snake case is not the plain mechanical one.
ID_EXCEPTIONS = {"CArrayRuntime": "carray", "CStringAssignmentRuntime": "cstring_assignment"}

# Comparison scripts whose names do not line up with any module name. Each was
# assigned by reading what the script exercises; the reason is written into
# the family notes.
COMPARE_BY_CONTENT = {
    "actor_list_renderer": ("plane_renderer", "calls claw_plane_renderer_actor_list"),
    "cstring_image_cache_join": ("cstring_assignment", "joins the cstring helper chain to the image cache"),
    "dynamic_child_residency": ("elemental_projectile", "its document says it composes the frozen elemental cleanup bodies"),
    "indexed_bottom_edge": ("native_indexed_presentation", "compiles and calls claw_native_indexed_composite8"),
    "interface_read_file_rewind": ("interface_read_composition", "uses interface_read_composition_helpers"),
    "native_indexed_composite": ("native_indexed_presentation", "compiles and calls claw_native_indexed_composite8"),
    "physics_retarget": ("player_physics", "calls claw_physics_retarget declared in PlayerPhysics.h"),
    "player_direction": ("player_engine", "calls claw_player_face_left/right declared in PlayerEngine.h"),
    "player_menu_assignment_tail": ("player_menu_management", "compiles PlayerMenuManagementRuntime.cpp"),
    "singleplayer_travel_runtime": ("special_command", "its document says the bodies reside in SpecialCommandRuntime"),
}

# Support files (and logs and directories) whose names do not start with any
# module name, keyed by name prefix after normalisation.
NAME_ALIASES = {
    "palette_schedule": "palette_fade",
    "animation_core": "animation_engine",
    "fast_presentation": "native_indexed_presentation",
    "hud_plane_renderer": "plane_renderer",
    "ambient_audio": "ambient_audio_backend",
    "crt_rng": "crt_random",
    "carry_dispatch": "player_carry_dispatch",
    "stack_lifecycle": "stacked_actor_lifecycle",
    "pid_surface": "pid_surface_raster",
    "light_pid": "light_pid_blitter",
    "effect_pid": "effect_pid_blitter",
    "pid_blit": "pid_blitter",
    "singleplayer_travel": "special_command",
    "indexed_frame": "native_indexed_presentation",
    "animation_seek": "actor_animation",
    "breakable": "breakable_object",
    "cstring_cache_join": "cstring_assignment",
    "elemental": "elemental_projectile",
    "interface_read_rewind": "interface_read_composition",
    "pcx_spans": "pcx_image",
}
FILE_SUFFIXES = (".dylib", ".json", ".log", ".o", ".py", ".c", ".cpp", ".h", ".swift", ".txt", ".asm", ".bin", ".gz", ".zip", ".mov", ".png", ".mp4", ".md")

SUPPORT_PREFIXES = ("check_", "capture_", "build_", "exact_sized_", "verify_", "audit_")
EVIDENCE_NAMES = {
    "verification.json", "verification.log", "verify.log", "report.json", "compare-final.log",
    "comparison.log", "sanitizer.log", "smoke.log", "test-results.txt", "frozen-sha256.txt",
    "source-sha256.json",
}
EVIDENCE_MAX_BYTES = 200_000
ADDRESS = re.compile(r"\b0x4[0-9a-fA-F]{5}\b")
# A definition (not a call) starts with a return type and an optional class scope.
DEFINITION_PREFIX = r"\b(?:bool|uint32_t|uint64_t|int|void|auto)\s+(?:\w+\s*::\s*)?"
CASE_LABEL = re.compile(r"\bcase\s+(0x4[0-9a-fA-F]{5})\s*:")
WHOLE_FUNCTION = re.compile(r"\bWhole\s*(?:0x)?([0-9a-f]{6})\b")
SWIFT_CALL = re.compile(r"\b(claw_[a-z0-9_]+)\s*\(")


# ---------------------------------------------------------------- names

def snake_case(name):
    name = ID_EXCEPTIONS.get(name, name)
    name = re.sub(r"Runtime$", "", name)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", spaced)
    return spaced.lower()


def split_words(name):
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name))


def canonical(text):
    """Normalised comparison key: underscores, no runtime/logic word, singular words."""
    text = text.lower().replace("-", "_").replace(".", "_")
    text = re.sub(r"(?:^|_)(?:runtime|logic)(?=_|$)", "", text).strip("_")
    words = []
    for word in text.split("_"):
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        words.append(word)
    return "_".join(w for w in words if w)


def strip_support_prefix(stem):
    for prefix in SUPPORT_PREFIXES:
        if stem.startswith(prefix):
            return stem[len(prefix):]
    return stem


# ---------------------------------------------------------------- source text

def blank_comments_and_strings(text):
    """Same-length copy of C++ text with comments and literals replaced by spaces."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        two = text[i:i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(c if c == "\n" else " " for c in text[i:j]))
            i = j
        elif text[i] in "\"'":
            quote = text[i]
            j = i + 1
            while j < n and text[j] != quote:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(quote + " " * (j - i - 2) + quote if j - i >= 2 else quote)
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def matching_close(text, start, opener, closer):
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return -1


def function_bodies(code, name_pattern):
    """Bodies of every definition (not declaration) whose name matches the pattern."""
    bodies = []
    for found in re.finditer(name_pattern + r"\s*\(", code):
        open_paren = found.end() - 1
        close_paren = matching_close(code, open_paren, "(", ")")
        if close_paren < 0:
            continue
        tail = re.match(r"\s*(?:const\s*)?(?:noexcept\s*)?\{", code[close_paren + 1:])
        if not tail:
            continue
        brace = close_paren + 1 + tail.end() - 1
        end = matching_close(code, brace, "{", "}")
        if end > brace:
            bodies.append(code[brace:end + 1])
    return bodies


def unique_sorted(addresses):
    return sorted({a.lower() for a in addresses})


def declared_addresses(cpp_text):
    """Addresses of the module's own ownership test."""
    code = blank_comments_and_strings(cpp_text)
    owned = set()
    for body in function_bodies(code, DEFINITION_PREFIX + r"(?:owned|owns|own)"):
        owned |= set(ADDRESS.findall(body))
    if owned:
        return unique_sorted(owned), "ownership function"
    cases = set()
    for body in function_bodies(code, DEFINITION_PREFIX + r"(?:entry|claw_[a-z0-9_]*entry[a-z0-9_]*)"):
        cases |= set(CASE_LABEL.findall(body))
    if cases:
        return unique_sorted(cases), "entry dispatcher"
    return [], "none"


def comment_text(text):
    pieces = re.findall(r"//[^\n]*|/\*.*?\*/", text, re.S)
    return "\n".join(pieces)


def inferred_addresses(header_text):
    found = set()
    for digits in WHOLE_FUNCTION.findall(comment_text(header_text)):
        found.add("0x" + digits)
    return unique_sorted(found)


# ---------------------------------------------------------------- repository scan

class Repository:
    """Everything read once from the checkout."""

    def __init__(self):
        self.cpp_stems = sorted(p.stem for p in SOURCES.glob("*.cpp"))
        self.compare_scripts = sorted(TESTS.glob("compare_*.py"))
        self.doc_lines = legacy._doc_lines(ROOT)
        self.target_files = self.read_target_files()
        self.bridged_headers = self.read_bridged_headers()
        self.swift_files = self.find_swift_files()
        self.swift_text = {f: blank_comments_and_strings(f.read_text(errors="replace")) for f in self.swift_files}
        self.doc_files = sorted(DOCS.glob("*.md"))
        self.support_files = self.find_support_files()
        self.work_children = sorted(p for p in WORK.iterdir()) if WORK.exists() else []

    def read_target_files(self):
        text = (ROOT / "Claw.xcodeproj/project.pbxproj").read_text(errors="replace")
        references = {}
        for found in re.finditer(r"\b([0-9A-F]{24})\b(?: /\*[^*]*\*/)? = \{isa = PBXFileReference;[^}]*?path = \"?([^\";]+)\"?;", text):
            references[found.group(1)] = found.group(2)
        build_files = {}
        for found in re.finditer(r"\b([0-9A-F]{24})\b(?: /\*[^*]*\*/)? = \{isa = PBXBuildFile; fileRef = ([0-9A-F]{24})", text):
            build_files[found.group(1)] = found.group(2)
        phase = re.search(r"Begin PBXSourcesBuildPhase section(.*?)End PBXSourcesBuildPhase section", text, re.S)
        names = set()
        if phase:
            for identifier in re.findall(r"\b([0-9A-F]{24})\b", phase.group(1)):
                reference = build_files.get(identifier)
                path = references.get(reference)
                if path:
                    names.add(Path(path).name)
        return names

    def read_bridged_headers(self):
        text = (SOURCES / "Claw-Bridging-Header.h").read_text(errors="replace")
        return set(re.findall(r"#\s*(?:include|import)\s+\"([^\"]+)\"", text))

    def find_swift_files(self):
        files = []
        for folder in ("Sources", "App", "Tests"):
            base = ROOT / folder
            if base.exists():
                files.extend(sorted(base.rglob("*.swift")))
        return files

    def find_support_files(self):
        """Top-level Tests files that are not compare scripts, plus Tests/<Dir>/main.swift."""
        found = []
        for path in sorted(TESTS.iterdir()):
            if path.is_file() and not path.name.startswith("compare_") and path.suffix in {".py", ".cpp", ".c", ".swift", ".json", ".h", ".inc"}:
                found.append(path)
            if path.is_dir() and path.name not in {"families", "__pycache__"}:
                found.extend(sorted(p for p in path.glob("*.swift")))
        return [p for p in found if p.name != "original_v10.py"]


class Family:
    def __init__(self, module_name):
        self.module = module_name
        self.id = ID_EXCEPTIONS.get(module_name, snake_case(module_name))
        self.cpp = f"Sources/{module_name}.cpp"
        self.header = f"Sources/{module_name}.h" if (SOURCES / f"{module_name}.h").exists() else None
        self.include = [f"Sources/{p.name}" for p in sorted(SOURCES.glob(re.sub(r"Runtime$", "", module_name) + "*.inc"))]
        self.compares = []
        self.compare_reasons = {}
        self.aliases = set()
        self.docs = []
        self.helpers = []
        self.extra = []
        self.root_logs = []
        self.work_dirs = []
        self.own_dirs = []

    @property
    def sources(self):
        names = [self.cpp]
        if self.header:
            names.append(self.header)
        return names + self.include

    def compute_aliases(self):
        base = canonical(self.id)
        aliases = {base}
        if base.startswith("player_"):
            aliases.add(base[len("player_"):])
        for script in self.compares:
            aliases.add(canonical(script.stem[len("compare_"):]))
        self.aliases = {a for a in aliases if a}


def build_families(repo):
    families = {}
    for stem in repo.cpp_stems:
        family = Family(stem)
        families[family.id] = family
    return families


def best_family(key, families):
    """Family for a normalised name key.

    The explicit name table wins; otherwise the family alias that equals the
    key or is a word-boundary prefix of it, the longest alias first.
    """
    for prefix, family_id in NAME_ALIASES.items():
        wanted = canonical(prefix)
        if key == wanted or key.startswith(wanted + "_"):
            return family_id
    best = None
    best_length = -1
    for family_id in sorted(families):
        for alias in families[family_id].aliases:
            if key == alias or key.startswith(alias + "_"):
                length = len(alias) + (0.5 if key == alias else 0)
                if length > best_length:
                    best, best_length = family_id, length
    return best


# ---------------------------------------------------------------- assignment

def assign_compares(repo, families):
    unassigned = []
    for family in families.values():
        family.aliases = {canonical(family.id)}
        if family.id.startswith("player_"):
            family.aliases.add(canonical(family.id)[len("player_"):])
    for script in repo.compare_scripts:
        stem = script.stem[len("compare_"):]
        if stem in COMPARE_BY_CONTENT:
            family_id, reason = COMPARE_BY_CONTENT[stem]
            families[family_id].compares.append(script)
            families[family_id].compare_reasons[script.name] = reason
            continue
        family_id = best_family(canonical(stem), families)
        if family_id is None:
            unassigned.append(script.name)
        else:
            families[family_id].compares.append(script)
    for family in families.values():
        family.compute_aliases()
    return unassigned


def imported_helper_names(script):
    text = script.read_text(errors="replace")
    names = {f"{n}.py" for n in legacy.HELPER_IMPORT.findall(text)} | set(legacy.HELPER_FILE.findall(text))
    return {n for n in names if (TESTS / n).exists()}


def assign_support_files(repo, families):
    importers = {}
    for family in families.values():
        for script in family.compares:
            for name in imported_helper_names(script):
                importers.setdefault(name, set()).add(family.id)
    unplaced = []
    for path in repo.support_files:
        key_source = path.stem if path.name != "main.swift" else path.parent.name
        key = canonical(strip_support_prefix(key_source))
        family_id = best_family(key, families)
        if family_id is None and len(importers.get(path.name, ())) == 1:
            family_id = next(iter(importers[path.name]))
        if family_id is None and path.name == "main.swift":
            family_id = families_by_module(families).get(path.parent.name)
        if family_id is None:
            unplaced.append(path.name)
            continue
        relative = str(path.relative_to(ROOT))
        family = families[family_id]
        if path.name.endswith("_helpers.py"):
            family.helpers.append(relative)
        else:
            family.extra.append(relative)
    return unplaced


def families_by_module(families):
    return {f.module: f.id for f in families.values()}


def assign_docs(repo, families):
    for family in families.values():
        own_key = family.id.replace("_", "-")
        keys = {own_key}
        for stem in family.compares:
            keys.add(stem.stem[len("compare_"):].replace("_", "-"))
        wanted = []
        for key in [own_key] + sorted(keys - {own_key}):
            for variant in (key, key + "-runtime", re.sub(r"-runtime$", "", key), key + "-logic", re.sub(r"-logic$", "", key)):
                path = DOCS / f"{variant}.md"
                if path.exists() and f"docs/{path.name}" not in wanted:
                    wanted.append(f"docs/{path.name}")
        if family.id == "palette_fade" and (DOCS / "palette-schedule-admission-audit.md").exists():
            wanted.append("docs/palette-schedule-admission-audit.md")
        family.docs = wanted


def scratch_directory(path):
    """True for an existing work/ directory (not a file, not a fragment of a longer path)."""
    name = path.split("/", 1)[1]
    if name.endswith(FILE_SUFFIXES) or name == "test-env":
        return False
    return (ROOT / path).is_dir()


def recipe_directories(commands):
    found = set()
    for command in commands:
        for text in command.get("arguments", []) + command.get("prerequisites", []):
            found |= set(re.findall(r"work/[A-Za-z0-9_.-]+", text))
    return found


def assign_work_dirs(repo, families):
    usage = {}
    for family in families.values():
        dirs = set()
        for script in family.compares:
            dirs |= legacy.work_dirs(script)
        dirs |= recipe_directories(oracle_commands([s.name for s in family.compares], repo.doc_lines))
        dirs = {d for d in dirs if scratch_directory(d)}
        family.derived_dirs = dirs
        for directory in dirs:
            usage.setdefault(directory, set()).add(family.id)
    named = {}
    for child in repo.work_children:
        if not child.is_dir() or child.name in {"test-env", "__pycache__"}:
            continue
        key = canonical(re.sub(r"-agent$", "", child.name))
        owner = best_family(key, families)
        if owner:
            named.setdefault(owner, []).append(f"work/{child.name}")
    name_owner = {d: f for f, dirs in named.items() for d in dirs}
    for family in families.values():
        chosen = set(named.get(family.id, []))
        for directory in family.derived_dirs:
            owner = name_owner.get(directory)
            if owner is None or owner == family.id:
                chosen.add(directory)
        family.work_dirs = sorted(chosen)
        family.own_dirs = sorted(d for d in chosen if name_owner.get(d) == family.id or (name_owner.get(d) is None and len(usage.get(d, ())) == 1))


def is_coordinator_log(name):
    if not name.startswith("root-") or not name.endswith(".log"):
        return False
    if "native" in name or name.endswith("-build.log") or "-build." in name:
        return False
    return "independent" in name or "asan" in name


def assign_root_logs(repo, families):
    logs = sorted(p for p in WORK.glob("root-*.log") if is_coordinator_log(p.name))
    unplaced = []
    for log in logs:
        stem = log.name[len("root-"):-len(".log")]
        family_id = best_family(canonical(stem), families)
        if family_id is None:
            mentions = [f.id for f in families.values() if any(log.name in (ROOT / d).read_text(errors="replace") for d in f.docs)]
            if len(mentions) == 1:
                family_id = mentions[0]
        if family_id is None:
            unplaced.append(log.name)
        else:
            families[family_id].root_logs.append(f"work/{log.name}")
    return unplaced


# ---------------------------------------------------------------- fields

def title_of(family):
    for doc in family.docs:
        for line in (ROOT / doc).read_text(errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return " ".join(split_words(re.sub(r"Runtime$", "", family.module)).split())


def sha256_of(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def source_hashes(sources):
    return {path: sha256_of(path) for path in sources if (ROOT / path).exists()}


def oracle_commands(scripts, doc_lines):
    commands = []
    for script in sorted(scripts):
        command = {"script": f"Tests/{Path(script).name}"}
        path = TESTS / Path(script).name
        if legacy.takes_arguments(path):
            arguments, prerequisites = legacy.recipe(path, doc_lines)
            if arguments:
                command["arguments"] = arguments
            if prerequisites:
                command["prerequisites"] = prerequisites
        commands.append(command)
    return commands


def owned_entries(family, header_text, cpp_text):
    declared, _ = declared_addresses(cpp_text)
    entries = []
    for address in declared:
        entries.append({"address": address, "convention": "unknown", "argc": None, "returns": "unknown", "confidence": "declared"})
    for address in inferred_addresses(header_text):
        if address not in declared:
            entries.append({"address": address, "convention": "unknown", "argc": None, "returns": "unknown", "confidence": "inferred"})
    return sorted(entries, key=lambda e: e["address"])


def declared_function_names(header_text):
    return set(SWIFT_CALL.findall(blank_comments_and_strings(header_text)))


def integration_for(sources, repo):
    cpp_names = [Path(s).name for s in sources if s.endswith(".cpp")]
    header_names = [Path(s).name for s in sources if s.endswith(".h")]
    in_target = any(name in repo.target_files for name in cpp_names)
    in_bridge = any(name in repo.bridged_headers for name in header_names)
    names = set()
    for source in sources:
        if source.endswith(".h"):
            names |= declared_function_names((ROOT / source).read_text(errors="replace"))
    references = []
    for swift, text in repo.swift_text.items():
        if any(re.search(r"\b" + re.escape(name) + r"\s*\(", text) for name in names):
            references.append(str(swift.relative_to(ROOT)))
    in_app = any(r.startswith(("Sources/", "App/")) for r in references)
    if in_target and in_app:
        level = "elected"
    elif in_target:
        level = "compiled"
    else:
        level = "source-only"
    return {
        "level": level,
        "in_app_target": in_target,
        "in_bridging_header": in_bridge,
        "swift_references": sorted(references),
    }


def worker_evidence(family):
    found = []
    for directory in family.own_dirs:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for item in sorted(base.iterdir()):
            if item.is_file() and item.name in EVIDENCE_NAMES and item.stat().st_size <= EVIDENCE_MAX_BYTES:
                found.append(f"{directory}/{item.name}")
    return found


def evidence_level(family):
    if family.id in PROVISIONAL_FAMILIES:
        return "provisional"
    if family.root_logs:
        return "legacy-frozen"
    return "provisional" if family.compares else "none"


def notes_for(family):
    notes = []
    if not family.header:
        notes.append("no header of its own")
    if family.include:
        notes.append("also owns " + ", ".join(Path(i).name for i in family.include))
    for name, reason in sorted(family.compare_reasons.items()):
        notes.append(f"{name} assigned by content: {reason}")
    return "; ".join(notes)


def build_manifest(family, repo):
    header_text = (ROOT / family.header).read_text(errors="replace") if family.header else ""
    cpp_text = (ROOT / family.cpp).read_text(errors="replace")
    level = evidence_level(family)
    oracle = {"kind": "legacy" if family.compares else "none"}
    if family.compares:
        oracle["commands"] = oracle_commands([s.name for s in family.compares], repo.doc_lines)
    if family.helpers:
        oracle["helpers"] = sorted(family.helpers)
    if family.extra:
        oracle["extra"] = sorted(family.extra)
    if family.work_dirs:
        oracle["work_dirs"] = family.work_dirs
    result = {
        "schema": 1,
        "id": family.id,
        "title": title_of(family),
        "abi": "legacy",
        "sources": family.sources,
        "source_sha256": source_hashes(family.sources),
        "docs": family.docs,
        "owned": owned_entries(family, header_text, cpp_text),
        "oracle": oracle,
        "evidence": {
            "level": level,
            "codex": {"root_logs": sorted(family.root_logs), "worker_evidence": worker_evidence(family)},
            "baseline": None,
            "gate": None,
        },
        "integration": integration_for(family.sources, repo),
        "limits": [],
    }
    notes = notes_for(family)
    if notes:
        result["notes"] = notes
    return result


# ---------------------------------------------------------------- modes

def write_all(repo):
    families = build_families(repo)
    unassigned = assign_compares(repo, families)
    unplaced_files = assign_support_files(repo, families)
    assign_docs(repo, families)
    assign_work_dirs(repo, families)
    unplaced_logs = assign_root_logs(repo, families)
    FAMILIES.mkdir(exist_ok=True)
    for family in families.values():
        manifest_module.save(build_manifest(family, repo))
    print(json.dumps({"unplaced_support_files": unplaced_files, "unplaced_root_logs": unplaced_logs}), file=sys.stderr)
    return unassigned


def refresh_all(repo):
    for path in manifest_module.paths():
        existing = json.loads(path.read_text())
        sources = existing.get("sources", [])
        existing["source_sha256"] = source_hashes(sources)
        existing["integration"] = integration_for(sources, repo)
        oracle = existing.setdefault("oracle", {"kind": "none"})
        scripts = [c["script"] for c in oracle.get("commands", [])]
        if scripts:
            oracle["commands"] = oracle_commands(scripts, repo.doc_lines)
        manifest_module.save(existing)


def summarize(unassigned):
    manifests = manifest_module.load_all()
    owned_declared = 0
    owned_inferred = 0
    evidence_levels = {}
    integration_levels = {}
    with_oracle = 0
    listed = set()
    for manifest in manifests.values():
        for entry in manifest.get("owned", []):
            if entry.get("confidence") == "declared":
                owned_declared += 1
            else:
                owned_inferred += 1
        level = manifest["evidence"]["level"]
        evidence_levels[level] = evidence_levels.get(level, 0) + 1
        level = manifest["integration"]["level"]
        integration_levels[level] = integration_levels.get(level, 0) + 1
        commands = manifest.get("oracle", {}).get("commands", [])
        if commands:
            with_oracle += 1
        listed |= {Path(c["script"]).name for c in commands}
    if unassigned is None:
        unassigned = sorted(p.name for p in TESTS.glob("compare_*.py") if p.name not in listed)
    return {
        "command": "import-legacy",
        "families": len(manifests),
        "with_oracle": with_oracle,
        "without_oracle": len(manifests) - with_oracle,
        "owned_declared": owned_declared,
        "owned_inferred": owned_inferred,
        "by_evidence_level": dict(sorted(evidence_levels.items())),
        "by_integration_level": dict(sorted(integration_levels.items())),
        "unassigned_compare_scripts": unassigned,
        "validator_status": manifest_module.check_all()["status"],
    }


def main(argv):
    refresh = "--refresh" in argv
    repo = Repository()
    unassigned = None
    if refresh:
        refresh_all(repo)
    else:
        unassigned = write_all(repo)
    print(json.dumps(summarize(unassigned)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
