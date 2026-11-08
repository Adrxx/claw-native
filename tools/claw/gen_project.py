"""Generate the Xcode project membership, the bridging header, canonical registry and native gate source list.

Membership rule: every git-tracked Sources/*.cpp and Sources/*.swift plus
App/ClawApp.swift is compiled. Canonical sources instead require an admitted
manifest, regardless of Git tracking. Explicit app Swift/header inventory and
ClawRuntime.h are included too. Every selected Sources/*.h is a file
reference, except entries listed in tools/claw/app_exclude.json.  Each entry is
{"path", "reason"} and may carry "role": "bridging" to leave a header out of the
bridging header only (the default role "compile" leaves the file out of the app).

Only the parts of project.pbxproj that carry membership are rewritten:
PBXBuildFile entries for sources, PBXFileReference entries for sources, the
children of the main and iOS groups, and the PBXSourcesBuildPhase file list.
The app marketing version is also generated. Every other byte is left alone.

Subcommands:
  write   regenerate project membership, bridging header, canonical registry and native gate list
  check   assert, without writing, that all four outputs are in sync with the rule
"""
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from Tests.clawparity.abi import CALL_ARGUMENT_CAPACITY

from pathlib import PurePosixPath

from tools.claw.paths import ROOT
from tools.claw.manifest import compiler_contract_errors

PROJECT = ROOT / "Claw.xcodeproj" / "project.pbxproj"
MARKETING_VERSION = "1.3"
BRIDGING_HEADER = ROOT / "Sources" / "Claw-Bridging-Header.h"
BRIDGING_HEADER_PATH = "Sources/Claw-Bridging-Header.h"
GATE_SOURCES = ROOT / "scripts" / "native-gate-sources.txt"
EXCLUDE_FILE = ROOT / "tools" / "claw" / "app_exclude.json"
APP_SWIFT = "App/ClawApp.swift"
APP_SOURCES = ROOT / "tools" / "claw" / "app_sources.json"
FAMILIES = ROOT / "Tests" / "families"
DISPATCH_PATH = "Sources/ClawCanonicalDispatch.h"
DISPATCH_HEADER = ROOT / DISPATCH_PATH
RUNTIME_PATH = "Sources/ClawRuntime.h"
MAIN_GROUP_ID = "F18983388ABFA29FB272672C"
IOS_GROUP_ID = "2056798116DE3EF1A7D1F106"
SOURCES_PHASE_ID = "CE4C5E6D538A6F4D6AE6075E"
REQUIRED_FLAGS = ('OTHER_CFLAGS = "-ffp-contract=off";', 'OTHER_CPLUSPLUSFLAGS = "-ffp-contract=off";')
FILE_TYPES = {
    ".cpp": "sourcecode.cpp.cpp",
    ".swift": "sourcecode.swift",
    ".h": "sourcecode.c.h",
}
# These admitted translations share an entry name with a retained legacy ABI.
# Compile the existing one-include native wrapper once and register its alias.
# The original source still passes canonical admission before substitution.
APP_CANONICAL_ALIASES = {
    "ambient_audio_backend": ("AmbientAudioBackendCanonical", "ClawMenuAudioListOwner", "audio_list"),
    "audio_manager_lifecycle": ("AudioManagerLifecycleCanonical", "ClawMenuAudioManagerLifecycleOwner", "audio_manager_lifecycle"),
    "booty_progression": ("BootyProgressionCanonical", "ClawMenuBootyProgressionOwner", "booty_progression"),
    "booty_results": ("BootyResultsCanonical", "ClawMenuBootyResultsOwner", "booty_results"),
    "booty_story": ("BootyStoryCanonical", "ClawMenuBootyStoryOwner", "booty_story"),
    "menu_game_launch": ("MenuGameLaunchCanonical", "ClawMenuMenuGameLaunchOwner", "menu_game_launch"),
    "player_cache_application": ("PlayerCacheApplicationCanonical", "ClawMenuPlayerCacheApplicationOwner", "player_cache_application"),
    "resource_table_construction": ("ResourceTableConstructionCanonical", "ClawMenuResourceTableOwner", "resource_table"),
    "special_command": ("SpecialCommandCanonical", "ClawMenuSpecialCommandOwner", "special_command"),
}
MEMBERSHIP_PATH = re.compile(r"path = ((?:Sources/[^;]+|App/ClawApp)\.(?:cpp|swift|h));")
ID_ALONE = re.compile(r"^\s*([0-9A-F]{24})(?: /\*.*\*/)?,\s*$")
ID_LINE = re.compile(r"^\s*([0-9A-F]{24})(?: /\*.*?\*/)? = ")


def hashed_id(role, path):
    digest = hashlib.sha1(f"{role}:{path}".encode()).hexdigest()
    return digest[:24].upper()


def tracked_files():
    output = subprocess.run(
        ["git", "ls-files", "Sources", APP_SWIFT],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in output.splitlines() if (ROOT / line).exists()]


def load_exclusions():
    entries = json.loads(EXCLUDE_FILE.read_text())
    return entries


def compile_excluded_paths(entries):
    return {entry["path"] for entry in entries if entry.get("role", "compile") == "compile"}


def bridging_excluded_paths(entries):
    return {entry["path"] for entry in entries if entry.get("role") == "bridging"}


def extension_of(path):
    return PurePosixPath(path).suffix


def membership(files, entries):
    """Return (compiled paths, header paths) after exclusions, both sorted."""
    excluded = compile_excluded_paths(entries)
    compiled = []
    headers = []
    for path in files:
        if path in excluded or path.startswith("Sources/Lua51/"):
            continue
        extension = extension_of(path)
        if extension in (".cpp", ".swift"):
            compiled.append(path)
        elif extension == ".h":
            headers.append(path)
    return sorted(compiled), sorted(headers)


def checked_source(path, suffixes=(".cpp", ".h"), *, root=ROOT):
    """Inventory paths are local regular sources, never escapes or aliases."""
    if (not isinstance(path, str) or not re.fullmatch(r"Sources/[A-Za-z0-9_]+\.[A-Za-z]+", path)
            or PurePosixPath(path).suffix not in suffixes):
        raise ValueError(f"invalid source path: {path!r}")
    source = root / path
    if not source.is_file() or source.is_symlink():
        raise ValueError(f"missing or symlink source: {path}")
    return path


def canonical_inventory(manifests, exclusions, *, root=ROOT):
    """Return all canonical-owned paths, admitted paths and unambiguous entries.

    A compile exclusion disables the entire canonical family. Nonadmitted
    canonical sources cannot enter through Git tracking or app inventory.
    Admitted alternate-profile sources compile for explicit native bridges;
    their addresses never enter the v1.0 host's address-only dispatch table.
    """
    all_paths, admitted_paths, registry = set(), set(), []
    source_owners, symbols, addresses, family_ids = {}, set(), set(), set()
    source_manifests = {}
    for manifest in manifests:
        if not isinstance(manifest, dict):
            raise ValueError("malformed family manifest")
        for path in manifest.get("sources", []):
            if not isinstance(path, str):
                raise ValueError("invalid source path")
            if path in source_owners:
                # Named-layout admission binds these common header bytes in
                # every opted-in family; they are not implementation owners.
                if (path in ("Sources/ClawRecoveredLayout.h", "Sources/ClawRecoveredNames.h")
                        and manifest.get("mutation") == "named-layout"
                        and source_manifests[path].get("mutation") == "named-layout"
                        and manifest.get("abi") == source_manifests[path].get("abi") == "canonical"
                        and manifest.get("id") != source_owners[path]):
                    continue
                raise ValueError(f"duplicate source {path}: {source_owners[path]} and {manifest.get('id')}")
            source_owners[path] = manifest.get("id")
            source_manifests[path] = manifest
    excluded = compile_excluded_paths(exclusions)
    for manifest in sorted(manifests, key=lambda m: m.get("id", "")):
        if manifest.get("abi") != "canonical":
            continue
        family = manifest.get("id")
        if not isinstance(family, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", family) or family in family_ids:
            raise ValueError(f"invalid or duplicate canonical family: {family!r}")
        family_ids.add(family)
        sources = manifest.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"{family}: missing sources")
        for path in sources:
            # Nonadmitted drafts are not build inputs, but must not sneak in
            # through the legacy tracked-file rule.
            if not isinstance(path, str):
                raise ValueError(f"{family}: invalid source path")
            all_paths.add(path)
        if manifest.get("evidence", {}).get("level") != "admitted":
            continue
        from Tests.clawparity import build_inputs
        errors = build_inputs.admission_errors(manifest, root=root)
        if errors:
            raise ValueError(f"{family}: " + "; ".join(errors))
        for path in sources:
            checked_source(path, root=root)
        if not any(path.endswith(".cpp") for path in sources):
            raise ValueError(f"{family}: no native source")
        oracle = manifest.get("oracle", {})
        symbol = oracle.get("entry")
        if oracle.get("kind") != "clawparity" or not isinstance(symbol, str) or not re.fullmatch(r"claw_[a-z0-9_]+_entry", symbol):
            raise ValueError(f"{family}: malformed canonical entry")
        if symbol in symbols:
            raise ValueError(f"duplicate entry symbol: {symbol}")
        symbols.add(symbol)
        errors = compiler_contract_errors(manifest)
        if errors:
            raise ValueError("; ".join(errors))
        owned = manifest.get("owned")
        if not isinstance(owned, list) or not owned:
            raise ValueError(f"{family}: no owned functions")
        selected = not excluded.intersection(sources)
        program = manifest.get("program", "claw-v1.0")
        if program not in ("claw-v1.0", "claw-v1.3"):
            raise ValueError(f"{family}: unsupported program: {program!r}")
        if selected:
            borrowed, owners = build_inputs.shared(manifest, root=root)
            for owner in owners.values():
                if excluded.intersection(owner["sources"]):
                    raise ValueError(f"{family}: shared source owner {owner['id']} is excluded")
            for path in borrowed:
                if source_owners.get(path) not in owners:
                    raise ValueError(f"{family}: shared source owner is absent from app inventory: {path}")
        if selected:
            admitted_paths.update(sources)
        for signature in owned:
            if not isinstance(signature, dict):
                raise ValueError(f"{family}: malformed owned signature")
            address_text = signature.get("address")
            if not isinstance(address_text, str) or not re.fullmatch(r"0x[0-9a-fA-F]{6,8}", address_text):
                raise ValueError(f"{family}: invalid owned address")
            address = int(address_text, 16)
            identity = (program, address)
            if not address or identity in addresses:
                raise ValueError(f"duplicate or zero owned address: {address_text}")
            addresses.add(identity)
            convention, argc, returns = (signature.get(k) for k in ("convention", "argc", "returns"))
            # An x87 result is supported for an ordinary entry that leaves the
            # caller's stack and pushes exactly one ST(0) (pop 0, push 1).
            x87_result = (returns == "x87" and signature.get("x87_result") == {"pop": 0, "push": 1}
                          and convention in ("cdecl", "stdcall", "thiscall")
                          and "source_context" not in signature and "compiler_context" not in signature)
            if "x87_environment" in signature and (
                    signature["x87_environment"] != {"pop": 0, "push": 0} or returns not in ("u32", "void")
                    or convention not in ("cdecl", "stdcall", "thiscall")
                    or "source_context" in signature or "compiler_context" in signature):
                raise ValueError(f"{family}: unsupported x87 environment ABI at {address_text}")
            if (convention not in ("cdecl", "stdcall", "thiscall", "compiler-context", "fastcall") or type(argc) is not int or not 0 <= argc <= CALL_ARGUMENT_CAPACITY
                    or (returns not in ("u32", "void", "context") and not x87_result) or signature.get("x87_args", 0) != 0):
                raise ValueError(f"{family}: unsupported owned ABI at {address_text}")
            if "interval_end" in signature:
                end = signature["interval_end"]
                if not isinstance(end, str) or not re.fullmatch(r"0x[0-9a-fA-F]{6,8}", end) or int(end, 16) <= address:
                    raise ValueError(f"{family}: malformed owned interval at {address_text}")
            if selected and program == "claw-v1.0":
                registry.append(dict(address=address, convention=convention, argc=argc,
                                     returns=returns, entry=symbol, family=family,
                                     **({k: signature[k] for k in ("source_context", "compiler_context", "x87_environment") if k in signature})))
    return all_paths, admitted_paths, sorted(registry, key=lambda e: e["address"])


def source_inventory(files, manifests, extras, exclusions):
    canonical, admitted, registry = canonical_inventory(manifests, exclusions)
    explicit = set()
    for item in extras:
        if not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError("app source inventory requires path and reason")
        path = checked_source(item.get("path"), (".swift", ".h", ".cpp"))
        if path in explicit or path in canonical:
            raise ValueError(f"duplicate app inventory path: {path}")
        explicit.add(path)
    checked_source(RUNTIME_PATH, (".h",))
    selected = (set(files) - canonical) | admitted | explicit | {RUNTIME_PATH, DISPATCH_PATH}
    selected, registry = app_canonical_aliases(selected, registry)
    for row in registry:
        row["original_entry"] = row["entry"]
    # Keep oracle exports and v1.0 layouts intact; elect the admitted v1.3
    # gameplay overlay explicitly at the native app boundary.
    if "Sources/V13EnemyDeathSoundRuntime.cpp" in admitted:
        overrides = {0x43f120: "claw_v13_enemy_death_compat_entry",
                     0x4208e0: "claw_v13_native_overlay_entry",
                     0x420910: "claw_v13_native_overlay_entry",
                     0x4ca3b0: "claw_v13_native_overlay_entry"}
        for row in registry:
            if row["address"] in overrides:
                row["entry"] = overrides[row["address"]]
    if {"Sources/V13LivesScoreRuntime.cpp", "Sources/V13BossDamageRuntime.cpp"} <= admitted:
        # Native adapters are composition code, not separately admitted bodies.
        # Include them explicitly even in the dispatcher's uncommitted tree.
        for path in ("Sources/V13LivesBossAdapter.cpp", "Sources/V13PlayerHUD.cpp", "Sources/V13LivesBoss.h"):
            checked_source(path)
            selected.add(path)
        damage_roots = {0x47e210, 0x47e2d0, 0x453d30, 0x453df0, 0x49fb30, 0x49fbf0,
                        0x4041f0, 0x404990, 0x4459d0, 0x445ef0, 0x4a0cf0, 0x480c40}
        for row in registry:
            if row["address"] in damage_roots:
                row["entry"] = "claw_v13_lives_boss_compat_entry"
            elif row["address"] in {0x415ce0, 0x46d8e0}:
                row["entry"] = "claw_v13_player_startup_compat_entry"
            elif row["address"] == 0x4908b0:
                row["entry"] = "claw_v13_score_compat_entry"
    if {"Sources/V13EnemyLifecycleRuntime.cpp", "Sources/V13RawLifecycleRuntime.cpp"} <= admitted:
        path = "Sources/V13EnemyLifecycleAdapter.cpp"
        checked_source(path)
        selected.add(path)
        lifecycle_roots = {0x409860, 0x421200, 0x434190, 0x4379d0, 0x441be0, 0x449c40,
                           0x45ff00, 0x462350, 0x465580, 0x4689b0, 0x474330, 0x47c850}
        for row in registry:
            if row["address"] in lifecycle_roots:
                row["entry"] = "claw_v13_enemy_lifecycle_compat_entry"
    if "Sources/V13ProfilesRuntime.cpp" in admitted:
        selected.update({"Sources/V13ProfilesAdapter.cpp", "Sources/V13Profiles.h"})
    if "Sources/V13ContactBindingsRuntime.cpp" in admitted:
        selected.add("Sources/V13ContactBindingAdapter.cpp")
    if "Sources/V13CheatMovementRuntime.cpp" in admitted:
        selected.add("Sources/V13CheatNativeAdapter.cpp")
        cheat_roots = {0x415df0, 0x4183e0, 0x418790, 0x41de90, 0x49d330, 0x49d620, 0x49d860, 0x49e4e0, 0x49e7b0, 0x49e7d0, 0x49e7f0, 0x43f120}
        for row in registry:
            if row["address"] in cheat_roots:
                row["entry"] = "claw_v13_cheat_native_entry"
        # These two v1.0 identities have no retained app owner. Their complete
        # v1.3 peg bodies use the same explicit native layout adapter.
        template = next(row for row in registry if row["address"] == 0x49e4e0)
        for address in (0x49d330, 0x49d620):
            if not any(row["address"] == address for row in registry):
                row = dict(template)
                row["address"] = address
                row["family"] = "v13_cheat_pegs"
                row.pop("original_entry", None)
                registry.append(row)
        registry.sort(key=lambda row: row["address"])
    compiled, headers = membership(selected, exclusions)
    return compiled, headers, registry


def app_canonical_aliases(selected, registry):
    selected = set(selected)
    registry = [dict(row) for row in registry]
    for family, (source, wrapper, suffix) in APP_CANONICAL_ALIASES.items():
        rows = [row for row in registry if row["family"] == family]
        if not rows:
            continue
        source_path, wrapper_path = f"Sources/{source}.cpp", f"Sources/{wrapper}.cpp"
        if source_path not in selected:
            raise ValueError(f"{family}: alias requires admitted source {source_path}")
        checked_source(wrapper_path)
        symbol = f"claw_native_menu_{suffix}_entry"
        expected = f'#define {rows[0]["entry"]} {symbol}\n#include "{source}.cpp"'
        # A wrapper can rename only the symbol, never change recovered behavior.
        body = re.sub(r"//[^\n]*", "", (ROOT / wrapper_path).read_text()).strip()
        if body != expected:
            raise ValueError(f"{family}: canonical alias wrapper must only rename and include")
        selected.discard(source_path)
        selected.add(wrapper_path)
        for row in rows:
            row["entry"] = symbol
    return selected, registry


def canonical_dispatch_text(registry):
    """C-compatible dispatch. ClawHost carries a host-validated entry ESP.

    Accept the full call envelope at the boundary and reject unsupported live
    fields explicitly; never silently truncate it to the narrower module ABI.
    """
    declarations = "".join(
        f"uint32_t {entry}(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);\n"
        for entry in sorted({entry for row in registry for entry in (row["entry"], row.get("original_entry", row["entry"]))}))
    def render_rows(items):
        return "".join(
        f'    {{0x{r["address"]:08x}u, CLAW_CANONICAL_{r["convention"].upper().replace("-", "_")}, {r["argc"]}u, '
        f'CLAW_CANONICAL_RETURN_{r["returns"].upper()}, {r["entry"]}, "{r["family"]}", '
        f'{(2 if r.get("source_context", {}).get("optional", False) else int("source_context" in r))}u, {r.get("source_context", {}).get("input_mask", 0)}u, '
        f'{r.get("source_context", {}).get("output_mask", 0)}u, {r.get("source_context", {}).get("preserve_mask", 0)}u, '
        f'{int("compiler_context" in r)}u, {r.get("compiler_context", {}).get("input_mask", 0)}u, '
        f'{r.get("compiler_context", {}).get("output_mask", 0)}u, {int("x87_environment" in r)}u}},\n'
        for r in items)
    rows = render_rows(registry)
    originals = [dict(row, entry=row["original_entry"]) for row in registry
                 if row.get("original_entry", row["entry"]) != row["entry"]]
    original_rows = render_rows(originals)
    version_cases = "".join(f"        case 0x{row['address']:08x}u: return &clawCanonicalOriginalEntries[{index}];\n"
                            for index, row in enumerate(originals))
    return """/* Generated by tools.claw.gen_project. Do not edit. */
#ifndef CLAW_CANONICAL_DISPATCH_H
#define CLAW_CANONICAL_DISPATCH_H
#include "ClawRuntime.h"
#include "V13LivesBoss.h"
#include <stddef.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif

enum { CLAW_CANONICAL_CDECL = 0, CLAW_CANONICAL_STDCALL = 1, CLAW_CANONICAL_THISCALL = 2, CLAW_CANONICAL_COMPILER_CONTEXT = 3, CLAW_CANONICAL_FASTCALL = 4 };
enum { CLAW_CANONICAL_RETURN_VOID = 0, CLAW_CANONICAL_RETURN_U32 = 1, CLAW_CANONICAL_RETURN_CONTEXT = 2, CLAW_CANONICAL_RETURN_X87 = 3 };
/* Registry-local fault for an address with no admitted native owner. */
enum { CLAW_CANONICAL_FAULT_UNKNOWN_ADDRESS = 7 };
typedef struct ClawCanonicalEntry {
    uint32_t address;
    uint32_t convention;
    uint32_t argumentCount;
    uint32_t returnKind;
    ClawEntry entry;
    const char *family;
    uint32_t sourceCapability, sourceInputMask, sourceOutputMask, sourcePreserveMask;
    uint32_t compilerCapability, compilerInputMask, compilerOutputMask;
    uint32_t x87Environment;
} ClawCanonicalEntry;

""" + declarations + """
static const ClawCanonicalEntry clawCanonicalEntries[] = {
""" + rows + """    {0, 0, 0, 0, NULL, NULL, 0, 0, 0, 0, 0, 0, 0, 0} /* sentinel; not part of count */
};
static const ClawCanonicalEntry clawCanonicalOriginalEntries[] = {
""" + original_rows + """    {0, 0, 0, 0, NULL, NULL, 0, 0, 0, 0, 0, 0, 0, 0}
};
static inline uint32_t claw_canonical_entry_count(void) {
    return (uint32_t)(sizeof(clawCanonicalEntries) / sizeof(clawCanonicalEntries[0]) - 1);
}
static inline const ClawCanonicalEntry *claw_canonical_lookup(uint32_t address) {
    uint32_t lo = 0, hi = claw_canonical_entry_count();
    if (!claw_native_v13_enabled()) {
        switch (address) {
""" + version_cases + """        default: break;
        }
    }
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (clawCanonicalEntries[mid].address < address) lo = mid + 1;
        else hi = mid;
    }
    return lo < claw_canonical_entry_count() && clawCanonicalEntries[lo].address == address
        ? &clawCanonicalEntries[lo] : NULL;
}
/* Explicit host-owned synchronous graph dispatch. This is a separate surface:
   ordinary dispatch below never enables contexts. The host must own borrowed
   pointers, thread, stack, budget, callsite authorization and graph lifetime. */
enum { CLAW_CANONICAL_SOURCE_GRAPH = 1, CLAW_CANONICAL_COMPILER_GRAPH = 2 };
static inline uint32_t claw_canonical_dispatch_context(const ClawCall *call, ClawHost *host,
                                                       uint32_t capability, uint32_t *result) {
    const ClawCanonicalEntry *entry;
    uint32_t value = 0, valid = 0, ok;
    if (!host || host->fault) return 0;
    if (!call || !result || !(entry = claw_canonical_lookup(call->function))) goto bad;
    if (entry->returnKind == CLAW_CANONICAL_RETURN_X87 || entry->x87Environment || call->x87State || call->x87Operation) goto bad;
    if (call->argumentCount != entry->argumentCount || call->argumentCount > CLAW_CALL_ARGUMENT_CAPACITY ||
        call->sourceTransferVersion || call->sourceTransferKind || call->sourceTransferSite ||
        call->sourceCallerFunction || call->sourceDisposition ||
        call->receiver2 || call->x87ArgumentCount || !host->remainingOperations ||
        call->stackPointer != host->entryStackPointer) goto bad;
    if (capability == CLAW_CANONICAL_COMPILER_GRAPH) {
        valid = entry->compilerCapability && !entry->sourceCapability &&
            entry->convention == CLAW_CANONICAL_COMPILER_CONTEXT && !call->receiver &&
            !call->argumentCount && call->compilerContext &&
            call->compilerContext == host->compilerContext && !call->sourceContext &&
            !host->sourceContext && !call->sourceReturnPC && !host->sourceReturnPC &&
            call->compilerContext->inputMask == entry->compilerInputMask &&
            call->compilerContext->outputMask == entry->compilerOutputMask &&
            call->compilerContext->esp == host->entryStackPointer;
    } else if (capability == CLAW_CANONICAL_SOURCE_GRAPH) {
        valid = entry->sourceCapability && !entry->compilerCapability &&
            entry->convention <= CLAW_CANONICAL_THISCALL &&
            (entry->convention == CLAW_CANONICAL_THISCALL || !call->receiver) &&
            !call->compilerContext && !host->compilerContext && call->sourceContext &&
            call->sourceContext == host->sourceContext && call->sourceReturnPC &&
            call->sourceReturnPC == host->sourceReturnPC &&
            call->sourceContext->inputMask == entry->sourceInputMask &&
            call->sourceContext->outputMask == entry->sourceOutputMask &&
            call->sourceContext->preserveMask == entry->sourcePreserveMask &&
            call->sourceContext->esp == host->entryStackPointer &&
            (entry->convention != CLAW_CANONICAL_THISCALL ||
             !(call->sourceContext->inputMask & CLAW_CONTEXT_ECX) ||
             call->sourceContext->ecx == call->receiver);
    }
    if (!valid) goto bad;
    ok = entry->entry(call->function, call->receiver, call->arguments, call->argumentCount, host, &value);
    if (!ok && !host->fault) goto bad;
    if (!ok || host->fault) return 0;
    *result = value;
    return 1;
bad:
    host->fault = CLAW_FAULT_ABI;
    host->faultAddress = call ? call->function : 0;
    return 0;
}
/* Owned x87 result (pop 0, push 1) or environment (pop 0, push 0). The caller passes
   its exact x87 stack as a CLAW_X87_EXACT request. The entry reads that stack
   through CLAW_X87_ENTRY and publishes the declared stack effect through
   CLAW_X87_RESULT, once, as its last outside call; the dispatcher checks the
   publication and returns it to the caller with full 80-bit slots. Every other
   outbound call, including x87 steps, reaches the caller's host unchanged. */
typedef struct ClawCanonicalX87Frame {
    ClawHost shim;
    ClawHost *outer;
    ClawX87State *caller;
    ClawX87State result;
    uint32_t function, entered, published, push;
} ClawCanonicalX87Frame;
static inline uint32_t claw_canonical_x87_state_ok(const ClawX87State *s) {
    uint32_t i;
    if (!s || s->size != sizeof(*s) || s->version != CLAW_X87_VERSION || s->reserved0 || s->reserved1 ||
        s->control > 0xffff || (s->control & 0x3f) != 0x3f || s->status > 0xffff || s->count > 8) return 0;
    for (i = 0; i < 8; ++i)
        if (s->slots[i].reserved || s->slots[i].signExponent > 0xffff ||
            (i >= s->count && (s->slots[i].significand || s->slots[i].signExponent))) return 0;
    return 1;
}
static inline uint32_t claw_canonical_x87_request_ok(const ClawCall *call) {
    const ClawX87State *s = call->x87State;
    return call->x87ArgumentCount == CLAW_X87_EXACT && !call->x87Operation && claw_canonical_x87_state_ok(s) &&
        s->count < 8 && !s->popCount && s->pushCount == 1 && !s->returned && !s->eax && !s->edx;
}
static inline uint32_t claw_canonical_x87_environment_request_ok(const ClawCall *call) {
    const ClawX87State *s = call->x87State;
    return call->x87ArgumentCount == CLAW_X87_EXACT && !call->x87Operation && claw_canonical_x87_state_ok(s) &&
        !s->popCount && !s->pushCount && !s->returned && !s->eax && !s->edx;
}
static inline uint8_t *claw_canonical_x87_bytes(void *user, uint32_t token, uint32_t count) {
    ClawHost *outer = ((ClawCanonicalX87Frame *)user)->outer;
    return outer->bytes ? outer->bytes(outer->user, token, count) : NULL;
}
static inline uint32_t claw_canonical_x87_call(void *user, const ClawCall *call) {
    ClawCanonicalX87Frame *frame = (ClawCanonicalX87Frame *)user;
    ClawHost *outer = frame->outer;
    const ClawX87State *c = frame->caller;
    ClawX87State *s;
    uint32_t value, i;
    if (!call || frame->published || frame->shim.fault) goto bad;
    if (call->x87ArgumentCount == CLAW_X87_ENTRY || call->x87ArgumentCount == CLAW_X87_RESULT) {
        s = call->x87State;
        if (call->function != frame->function || call->receiver || call->receiver2 || call->argumentCount ||
            call->stackPointer || call->x87Operation || !s) goto bad;
        if (call->x87ArgumentCount == CLAW_X87_ENTRY) {
            /* The entry asks with an empty versioned state and receives the caller's. */
            ClawX87State empty;
            memset(&empty, 0, sizeof(empty));
            empty.size = sizeof(empty); empty.version = CLAW_X87_VERSION;
            if (frame->entered || memcmp(s, &empty, sizeof(empty))) goto bad;
            *s = *c;
            s->popCount = s->pushCount = 0; s->returned = 1; s->eax = s->edx = 0;
            frame->entered = 1;
            return 0;
        }
        if (!frame->entered || !claw_canonical_x87_state_ok(s) || s->popCount || s->pushCount != frame->push || s->returned || s->eax || s->edx ||
            s->control != c->control || s->count != c->count + frame->push ||
            ((s->status >> 11) & 7u) != (((c->status >> 11) + 8u - frame->push) & 7u)) goto bad;
        for (i = 0; i < c->count; ++i)
            if (memcmp(&s->slots[i + frame->push], &c->slots[i], sizeof(ClawX87Value))) goto bad;
        frame->result = *s;
        s->returned = 1;
        frame->published = 1;
        return 0;
    }
    if (!outer->call) goto bad;
    value = outer->call(outer->user, call);
    if (outer->fault && !frame->shim.fault) {
        frame->shim.fault = outer->fault;
        frame->shim.faultAddress = outer->faultAddress;
    }
    return value;
bad:
    if (!frame->shim.fault) {
        frame->shim.fault = CLAW_FAULT_ABI;
        frame->shim.faultAddress = call ? call->function : frame->function;
    }
    return 0;
}
static inline uint32_t claw_canonical_x87_invoke(const ClawCall *call, const ClawCanonicalEntry *entry,
                                                 ClawHost *host, uint32_t *value) {
    ClawCanonicalX87Frame frame;
    ClawX87State *c = call->x87State;
    uint32_t ok;
    memset(&frame, 0, sizeof(frame));
    frame.shim = *host;
    frame.shim.user = &frame;
    frame.shim.call = claw_canonical_x87_call;
    frame.shim.bytes = host->bytes ? claw_canonical_x87_bytes : NULL;
    frame.outer = host; frame.caller = c; frame.function = call->function;
    frame.push = entry->x87Environment ? 0 : 1;
    ok = entry->entry(call->function, call->receiver, call->arguments, call->argumentCount, &frame.shim, value);
    if (frame.shim.fault || host->fault) {
        if (!host->fault) {
            host->fault = frame.shim.fault;
            host->faultAddress = frame.shim.faultAddress;
        }
        return 0;
    }
    if (!ok || !frame.published) return 0;
    *c = frame.result;
    c->popCount = 0; c->pushCount = frame.push; c->returned = 1; c->eax = *value; c->edx = 0;
    return 1;
}
/* Leaves a previous fault and the result untouched on failure. EDX and x87
   arguments remain unsupported; an x87 result needs an EXACT request. A nonzero ESP must agree with the host's prepared
   entry scope; zero means the outermost CLAW_STACK_TOP default. This checks ABI
   agreement, not memory ownership: hosts must own the bounded stack storage,
   authorize nesting and materialize argument words before dispatch. Outbound
   ClawHost.call receives the complete ClawCall unchanged from the module. */
static inline uint32_t claw_canonical_dispatch(const ClawCall *call, ClawHost *host, uint32_t *result) {
    const ClawCanonicalEntry *entry;
    uint32_t ok, value = 0;
    if (!host || host->fault) return 0;
    if (!call || !result) {
        host->fault = CLAW_FAULT_ABI;
        host->faultAddress = call ? call->function : 0;
        return 0;
    }
    entry = claw_canonical_lookup(call->function);
    if (!entry) {
        host->fault = CLAW_CANONICAL_FAULT_UNKNOWN_ADDRESS;
        host->faultAddress = call->function;
        return 0;
    }
    /* This ordinary API has no context capability. Never reinterpret special
       entries or required source entries as ordinary context-free calls. */
    if (call->sourceTransferVersion || call->sourceTransferKind || call->sourceTransferSite ||
        call->sourceCallerFunction || call->sourceDisposition ||
        entry->convention == CLAW_CANONICAL_COMPILER_CONTEXT ||
        call->compilerContext || host->compilerContext || entry->sourceCapability == 1 ||
        call->sourceContext || host->sourceContext || call->sourceReturnPC || host->sourceReturnPC ||
        entry->convention == CLAW_CANONICAL_FASTCALL ||
        call->argumentCount != entry->argumentCount || call->argumentCount > CLAW_CALL_ARGUMENT_CAPACITY || call->receiver2 ||
        (entry->x87Environment ? !claw_canonical_x87_environment_request_ok(call) :
         entry->returnKind == CLAW_CANONICAL_RETURN_X87 ? !claw_canonical_x87_request_ok(call)
            : (call->x87ArgumentCount || call->x87State || call->x87Operation)) ||
        (entry->convention != CLAW_CANONICAL_THISCALL && call->receiver)) {
        host->fault = CLAW_FAULT_ABI;
        host->faultAddress = call->function;
        return 0;
    }
    if ((call->stackPointer &&
         (call->stackPointer != host->entryStackPointer || (call->stackPointer & 3u) ||
          call->stackPointer < CLAW_STACK_BASE ||
          (uint64_t)call->stackPointer + 4u * (1u + call->argumentCount) > CLAW_STACK_END)) ||
        (!call->stackPointer && host->entryStackPointer && host->entryStackPointer != CLAW_STACK_TOP)) {
        host->fault = CLAW_FAULT_ABI;
        host->faultAddress = call->function;
        return 0;
    }
    ok = entry->returnKind == CLAW_CANONICAL_RETURN_X87 || entry->x87Environment
        ? claw_canonical_x87_invoke(call, entry, host, &value)
        : entry->entry(call->function, call->receiver, call->arguments, call->argumentCount, host, &value);
    if (!ok && !host->fault) {
        host->fault = CLAW_FAULT_ABI;
        host->faultAddress = call->function;
    }
    if (!ok || host->fault) return 0;
    *result = value;
    return 1;
}
#ifdef __cplusplus
}
#endif
#endif
"""


def parses_as_c(path):
    result = subprocess.run(
        ["xcrun", "clang", "-fsyntax-only", "-x", "c", "-I", "Sources", path],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0


def bridgeable_headers(headers, entries):
    """Headers that parse as C and are not left out of the bridging header."""
    left_out = bridging_excluded_paths(entries)
    candidates = [h for h in headers if h != BRIDGING_HEADER_PATH and h not in left_out]
    with ThreadPoolExecutor(max_workers=8) as pool:
        verdicts = list(pool.map(parses_as_c, candidates))
    return [h for h, ok in zip(candidates, verdicts) if ok]


def header_includes(text):
    return re.findall(r'^#include "([^"]+)"', text, flags=re.M)


def bridging_header_text(wanted_headers, current_text):
    """Existing include order first, new headers appended alphabetically."""
    wanted_names = {h.split("/", 1)[1] for h in wanted_headers}
    kept = []
    for name in header_includes(current_text):
        if name in wanted_names and name not in kept:
            kept.append(name)
    new_names = sorted(wanted_names - set(kept))
    return "".join(f'#include "{name}"\n' for name in kept + new_names)


def gate_sources_text(compiled):
    names = sorted(p.split("/")[-1][:-4] for p in compiled if p.endswith(".cpp"))
    return "".join(f"{name}\n" for name in names)


# ---- project.pbxproj ---------------------------------------------------

def section_bounds(lines, name):
    begin = lines.index(f"/* Begin {name} section */\n")
    end = lines.index(f"/* End {name} section */\n")
    return begin + 1, end


def object_bounds(lines, object_id, start=0):
    """Line range [first, last] of the multi-line object with this id."""
    first = None
    for index in range(start, len(lines)):
        if first is None and re.match(rf"^\t\t{object_id}\b.* = \{{$", lines[index]):
            first = index
        elif first is not None and lines[index] == "\t\t};\n":
            return first, index
    raise ValueError(f"object {object_id} not found")


def children_range(lines, object_id):
    first, last = object_bounds(lines, object_id)
    opening = next(i for i in range(first, last) if lines[i].strip() == "children = (")
    closing = next(i for i in range(opening, last) if lines[i].strip() == ");")
    return opening + 1, closing


def membership_ref_ids(lines):
    begin, end = section_bounds(lines, "PBXFileReference")
    ids = set()
    for line in lines[begin:end]:
        if MEMBERSHIP_PATH.search(line):
            ids.add(ID_LINE.match(line).group(1))
    return ids


def file_reference_line(path):
    name = path.split("/")[-1]
    ref = hashed_id("fileref", path)
    file_type = FILE_TYPES[extension_of(path)]
    return f'\t\t{ref} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {file_type}; name = {name}; path = {path}; sourceTree = "<group>"; }};\n'


def build_file_line(path):
    name = path.split("/")[-1]
    build = hashed_id("buildfile", path)
    ref = hashed_id("fileref", path)
    return f"\t\t{build} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {ref} /* {name} */; }};\n"


def drop_ids_from_children(lines, group_id, old_ids):
    first, last = children_range(lines, group_id)
    kept = []
    for line in lines[first:last]:
        match = ID_ALONE.match(line)
        if match and match.group(1) in old_ids:
            continue
        kept.append(line)
    return kept, first, last


def build_line_uses_refs(line, ref_ids):
    match = re.search(r"fileRef = ([0-9A-F]{24})", line)
    return bool(match) and match.group(1) in ref_ids


def rewrite_project(text, compiled, headers):
    lines = text.splitlines(keepends=True)
    old_refs = membership_ref_ids(lines)
    all_paths = compiled + headers

    # Groups first (later lines first so earlier indexes stay valid).
    main_kept, main_first, main_last = drop_ids_from_children(lines, MAIN_GROUP_ID, old_refs)
    ref_children = [f"\t\t\t\t{hashed_id('fileref', p)} /* {p.split('/')[-1]} */,\n" for p in sorted(all_paths)]
    ios_kept, ios_first, ios_last = drop_ids_from_children(lines, IOS_GROUP_ID, old_refs)

    phase_files_first, phase_files_last = phase_files_range(lines)
    old_build_ids = {ID_LINE.match(line).group(1) for line in lines
                     if ID_LINE.match(line) and build_line_uses_refs(line, old_refs)}
    phase_kept = [line for line in lines[phase_files_first:phase_files_last]
                  if not ID_ALONE.match(line) or ID_ALONE.match(line).group(1) not in old_build_ids]
    phase_children = phase_kept + [f"\t\t\t\t{hashed_id('buildfile', p)} /* {p.split('/')[-1]} in Sources */,\n" for p in compiled]

    ref_begin, ref_end = section_bounds(lines, "PBXFileReference")
    ref_kept = [l for l in lines[ref_begin:ref_end] if not MEMBERSHIP_PATH.search(l)]
    ref_lines = ref_kept + [file_reference_line(p) for p in all_paths]

    build_begin, build_end = section_bounds(lines, "PBXBuildFile")
    build_kept = [l for l in lines[build_begin:build_end] if not build_line_uses_refs(l, old_refs)]
    build_lines = [build_file_line(p) for p in compiled] + build_kept

    replacements = [
        (build_begin, build_end, build_lines),
        (ref_begin, ref_end, ref_lines),
        (ios_first, ios_last, ios_kept),
        (main_first, main_last, main_kept + ref_children),
        (phase_files_first, phase_files_last, phase_children),
    ]
    for first, last, new_lines in sorted(replacements, key=lambda r: r[0], reverse=True):
        lines[first:last] = new_lines
    return "".join(lines)


def phase_files_range(lines):
    first, last = object_bounds(lines, SOURCES_PHASE_ID)
    opening = next(i for i in range(first, last) if lines[i].strip() == "files = (")
    closing = next(i for i in range(opening, last) if lines[i].strip() == ");")
    return opening + 1, closing


def compiled_paths_in_project(text):
    """Set of source paths in the Sources build phase of a project file."""
    lines = text.splitlines(keepends=True)
    file_paths = {}
    for line in lines:
        match = MEMBERSHIP_PATH.search(line)
        if match:
            file_paths[ID_LINE.match(line).group(1)] = match.group(1)
    build_to_ref = {}
    for line in lines:
        match = re.match(r"^\s*([0-9A-F]{24})(?: /\*.*?\*/)? = \{isa = PBXBuildFile; fileRef = ([0-9A-F]{24})", line)
        if match:
            build_to_ref[match.group(1)] = match.group(2)
    first, last = phase_files_range(lines)
    paths = set()
    for line in lines[first:last]:
        match = ID_ALONE.match(line)
        ref = build_to_ref.get(match.group(1)) if match else None
        if ref in file_paths:
            paths.add(file_paths[ref])
    return paths


def referenced_paths_in_project(text):
    return {m.group(1) for m in MEMBERSHIP_PATH.finditer(text)}


# ---- commands ----------------------------------------------------------

def expected_outputs():
    entries = load_exclusions()
    files = tracked_files()
    manifests = [json.loads(path.read_text()) for path in sorted(FAMILIES.glob("*.json"))
                 if path.name != "schema.json" and not path.name.startswith("_")]
    extras = json.loads(APP_SOURCES.read_text()) if APP_SOURCES.exists() else []
    compiled, headers, registry = source_inventory(files, manifests, extras, entries)
    dispatch = canonical_dispatch_text(registry)
    wanted_bridge = bridgeable_headers([h for h in headers if h != DISPATCH_PATH], entries)
    if DISPATCH_PATH in headers and DISPATCH_PATH not in bridging_excluded_paths(entries):
        wanted_bridge.append(DISPATCH_PATH)
    project_text = PROJECT.read_text()
    new_project = rewrite_project(project_text, compiled, headers)
    new_project, version_count = re.subn(r"MARKETING_VERSION = [^;]+;",
                                       f"MARKETING_VERSION = {MARKETING_VERSION};", new_project)
    if version_count != 2:
        raise ValueError("Expected app marketing version in Debug and Release")
    new_bridge = bridging_header_text(wanted_bridge, BRIDGING_HEADER.read_text())
    new_gate = gate_sources_text(compiled)
    return entries, compiled, wanted_bridge, new_project, new_bridge, new_gate, dispatch


def command_write():
    entries, compiled, bridge, project, header, gate, dispatch = expected_outputs()
    PROJECT.write_text(project)
    BRIDGING_HEADER.write_text(header)
    GATE_SOURCES.write_text(gate)
    DISPATCH_HEADER.write_text(dispatch)
    return summary("project-write", entries, compiled, bridge, True)


def command_check():
    entries, compiled, bridge, project, header, gate, dispatch = expected_outputs()
    flags_present = all(PROJECT.read_text().count(flag) >= 2 for flag in REQUIRED_FLAGS)
    in_sync = (
        PROJECT.read_text() == project
        and BRIDGING_HEADER.read_text() == header
        and GATE_SOURCES.exists()
        and GATE_SOURCES.read_text() == gate
        and DISPATCH_HEADER.exists()
        and DISPATCH_HEADER.read_text() == dispatch
        and flags_present
    )
    return summary("project-check", entries, compiled, bridge, in_sync)


def summary(command, entries, compiled, bridge, in_sync):
    return {
        "command": command,
        "compiled_cpp": sum(1 for p in compiled if p.endswith(".cpp")),
        "compiled_swift": sum(1 for p in compiled if p.endswith(".swift")),
        "bridged_headers": len(bridge),
        "excluded": [entry["path"] for entry in entries],
        "in_sync": in_sync,
        "status": "pass" if in_sync else "fail",
    }


def main(argv):
    if len(argv) != 1 or argv[0] not in ("write", "check"):
        print(json.dumps({"command": "project", "status": "fail", "error": "usage: gen_project (write|check)"}))
        return 2
    try:
        result = command_write() if argv[0] == "write" else command_check()
    except (ValueError, KeyError, TypeError) as error:
        result = {"command": "project-" + argv[0], "status": "fail", "error": str(error)}
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
