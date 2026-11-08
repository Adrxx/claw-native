"""Builds the progress page: what is recovered, what is wired into the app, and what is missing. One JSON line.

    python -m tools.claw.progress_page [output.html]

Everything on the page is computed from the manifests, the function index, the level inventory and the sources.
"""
import datetime
import glob
import json
import re
import sys
from pathlib import Path

from . import index, manifest, sync
from .paths import ROOT, SOURCES, WORK

GAME_RANGES = ((0x401000, 0x4A1300), (0x4B3400, 0x4F0000))  # the rest of the code is C runtime and MFC (approximate)
REGISTRIES = {"LogicRegistry.cpp", "LogicStateRegistry.cpp", "CoreRegistration.cpp", "StartupLogicRegistrationRuntime.cpp"}
CASE = re.compile(r"case 0x([0-9a-fA-F]{6,8})\b")
LITERAL = re.compile(r"0x(4[0-9a-fA-F]{5})\b")
CLASS_OWNER = re.compile(r"^\s*// claw-progress-class-owner: ([a-z0-9_]+)((?: 0x[0-9a-fA-F]+)+)\s*$", re.MULTILINE)
FLOW = [
    ("Program startup", ["application_startup", "application_state_factory", "startup_state_two", "application_bootstrap_managers", "application_archive_path", "startup_logic_registration", "core_registration"]),
    ("Resource archive", ["resource_archive_loading", "resource_namespace", "resource_data", "resource_table_construction"]),
    ("Graphics and palette", ["graphics_manager_construction", "graphics_manager_lifecycle", "palette_resource", "palette_fade", "scene_display", "surface_blit", "surface_flip"]),
    ("Main menu", ["state_five", "interface_file", "interface_read_composition", "player_menu_management", "player_profile_confirmation", "player_cache_application"]),
    ("Starting a game", ["menu_game_launch", "scene_startup_composition", "player_startup", "image_controller_loading", "image_resource_lifecycle", "image_registry"]),
    ("Loading a level", ["world_file", "world_object", "world_plane", "raw_tile_description", "spatial_grid", "logic_registry", "logic_state_registry"]),
    ("The frame loop", ["single_player_scene", "game_frame", "game_frame_services", "scene_actor", "scene_camera", "plane_renderer", "game_image"]),
    ("Captain Claw himself", ["player_locomotion", "player_standing", "player_air_states", "player_pose_states", "player_attack_input", "player_input_dispatch", "player_damage", "player_death_commands", "player_death_services", "player_powerup", "player_projectile", "player_hud"]),
    ("End of level", ["end_level_gem", "booty_progression", "booty_story", "booty_results", "application_level_progression"]),
    ("Saving", ["save_file", "save_load", "checkpoint_logic", "checkpoint_timer"]),
    ("Sound and music", ["audio_events", "audio_resource", "audio_pcm_transfer", "audio_manager_lifecycle", "ambient_audio_backend", "music", "sound_trigger_logic"]),
]
OUTSIDE = [
    ("Intro and story movies", "Visible playback is approved. All twelve original Smacker streams passed exact-length extraction and complete offline decoding; a HEVC/AAC sample decoded with AVFoundation on the Mac. Full conversion, source scene mapping, presentation/timing checks and game integration remain."),
    ("Music synthesis", "Native synthesis is approved. Apple's sampler loaded original Claw SoundFont instruments on the Mac. Original XMI event playback, looping, transitions and integrated audio acceptance remain."),
    ("Windows dialogs", "Native sheets are approved for profiles and options, preserving values and confirm/cancel behavior. Implementation and game-state integration remain."),
    ("Touch and controller input", "The original input manager is not recovered. The lab uses keyboard and on-screen buttons wired by hand."),
    ("iPad presentation and device acceptance", "The 640 by 480 frame has to be scaled for the 13-inch screen, then accepted on the simulator and on the device."),
]


def in_game(address):
    return any(low <= address < high for low, high in GAME_RANGES)


def ownership(manifests, include_drafts=False):
    """Comparison-backed ownership, including legacy case-label estimates.

    Draft declarations can be shown separately, but never establish recovery.
    """
    if not include_drafts:
        manifests = {n: m for n, m in manifests.items() if m["evidence"]["level"] != "none"}
    functions = index.functions()
    owner = {}
    for name, spec in manifests.items():
        for entry in spec["owned"]:
            owner.setdefault(int(entry["address"], 16), name)
    for name, spec in manifests.items():
        if spec["owned"] or spec["evidence"]["level"] == "none":
            continue
        for source in spec["sources"]:
            path = ROOT / source
            if path.suffix == ".cpp" and path.name not in REGISTRIES and path.exists():
                for match in CASE.findall(path.read_text(errors="replace")):
                    address = int(match, 16)
                    if address in functions:
                        owner.setdefault(address, name)
    return owner


def class_status(address, spec, referenced):
    """A literal is a source hint; only the manifest records app-trace evidence."""
    if address is None:
        return "unknown"
    if spec and spec["evidence"]["level"] == "none":
        return "draft"
    integration = spec["integration"]["level"] if spec else None
    if integration == "live":
        return "live"
    if integration == "elected":
        return "wired"
    if referenced:
        return "referenced"
    return "recovered" if spec else "missing"


def reviewed_class_owners(manifests, paths=None):
    """Reviewed legacy callback routing, for the class display only.

    Older adapters do not all use C++ case labels or explicit owned entries.
    Their annotations identify the family behind a placed object's callback;
    they neither establish function ownership nor constitute an app trace.
    Keep the annotation beside its implementation and fail closed on conflicts,
    missing code references, or loss of the family's evidence/host election.
    """
    candidates = {}
    if paths is None:
        paths = SOURCES.glob("*.swift")
    for path in paths:
        source = path.read_text(errors="replace")
        references = {int(m, 16) for m in LITERAL.findall(swift_code(source))}
        for family, addresses in CLASS_OWNER.findall(source):
            spec = manifests.get(family)
            eligible = (spec is not None and spec["evidence"]["level"] != "none"
                        and spec["integration"]["level"] in ("elected", "live"))
            for literal in addresses.split():
                address = int(literal, 16)
                candidates.setdefault(address, set()).add(
                    family if eligible and address in references else None)
    return {address: next(iter(families)) for address, families in candidates.items()
            if len(families) == 1 and None not in families}


def swift_code(source):
    """Mask Swift comments and string literals before collecting code hints."""
    token = re.compile(r'//[^\n]*|/\*|(?P<hashes>\#*)(?P<quote>"""|")')
    parts, position = [], 0
    while match := token.search(source, position):
        parts.append(source[position:match.start()])
        position = match.end()
        if match.group() == "/*":
            depth = 1
            while depth:
                delimiter = re.search(r"/\*|\*/", source[position:])
                if delimiter is None:
                    position = len(source)
                    break
                depth += 1 if delimiter.group() == "/*" else -1
                position += delimiter.end()
        elif match.group("quote"):
            closing = match.group("quote") + match.group("hashes")
            escape = "\\" + match.group("hashes")
            while position < len(source):
                if source.startswith(escape, position):
                    position += len(escape) + 1
                elif source.startswith(closing, position):
                    position += len(closing)
                    break
                else:
                    position += 1
        parts.append(" ")
    parts.append(source[position:])
    return "".join(parts)


def class_family(address, owner, declared_owner, reviewed_owner):
    return owner.get(address) or declared_owner.get(address) or reviewed_owner.get(address)


def swift_addresses():
    found = set()
    for path in list(SOURCES.glob("*.swift")) + [ROOT / "App" / "ClawApp.swift"]:
        found |= {int(m, 16) for m in LITERAL.findall(path.read_text(errors="replace"))}
    return found


def level_classes():
    """Per level, how many placed objects use each logic class."""
    path = WORK / "coordinator" / "all-levels" / "native.json"
    if not path.exists():
        return []
    levels = []
    for level in json.loads(path.read_text()):
        counts = {}
        for plane in level.get("planes", []):
            for item in plane.get("logic", []):
                if isinstance(item, str):
                    label, count = item, 1
                elif isinstance(item, dict):
                    label, count = item.get("name") or item.get("logic") or "?", item.get("count", 1)
                else:
                    label, count = item[0], item[1] if len(item) > 1 else 1
                counts[label] = counts.get(label, 0) + count
        levels.append({"level": level.get("level"), "counts": counts})
    return levels


def class_addresses():
    data = json.loads((ROOT / "Tests" / "symbols.json").read_text())
    names = {entry["name"]: int(address, 16) for address, entry in data["symbols"].items() if entry["kind"] == "logic-callback"}
    for conflict in data.get("conflicts", []):
        dropped = conflict.get("dropped", {})
        if dropped.get("kind") == "logic-callback":
            names.setdefault(dropped["name"], int(conflict["address"], 16))
    return names


def build():
    manifests = {n: m for n, m in manifest.load_all().items()}
    owner = ownership(manifests)
    declared_owner = ownership(manifests, include_drafts=True)
    reviewed_owner = reviewed_class_owners(manifests)
    wired_addresses = swift_addresses()
    functions = index.functions()
    date, baseline = sync.latest_baseline()
    regate = {}
    for path in sorted(glob.glob(str(WORK / "gate" / "regate-*.jsonl"))):
        for line in Path(path).read_text().splitlines():
            record = json.loads(line)
            regate[record["family"]] = record
    order = sorted(manifests)
    position = {name: i for i, name in enumerate(order)}
    families = []
    for name in order:
        spec = manifests[name]
        scripts = [c["script"] for c in spec["oracle"].get("commands", [])]
        runs = [baseline[s]["status"] for s in scripts if s in baseline]
        rerun = "" if not runs else ("pass" if len(runs) == len(scripts) and all(r == "pass" for r in runs) else "fail")
        measured = regate.get(name, {})
        families.append({
            "id": name, "title": spec["title"][:90], "evidence": spec["evidence"]["level"],
            "integration": spec["integration"]["level"], "rerun": rerun,
            "unseen": measured.get("salted", ""), "coverage": measured.get("coverage"),
            "owned": sum(1 for a, f in owner.items() if f == name)})
    # [entry, size, status, family index]: 0 missing, 1 compared, 2 elected,
    # 3 library, 4 recorded app trace, 5 draft. Drafts cannot expand totals.
    program, totals = [], {"game_bytes": 0, "recovered_bytes": 0, "wired_bytes": 0, "live_bytes": 0,
                          "game_functions": 0, "recovered_functions": 0}
    for address in sorted(functions):
        function = functions[address]
        family = owner.get(address)
        if family is not None:
            status = {"elected": 2, "live": 4}.get(manifests[family]["integration"]["level"], 1)
        else:
            status = 5 if address in declared_owner else (0 if in_game(address) else 3)
        display_family = family or declared_owner.get(address)
        program.append([address, function["size"], status, position.get(display_family, -1)])
        if in_game(address) or family is not None:
            totals["game_bytes"] += function["size"]
            totals["game_functions"] += 1
            if family is not None:
                totals["recovered_bytes"] += function["size"]
                totals["recovered_functions"] += 1
                if status in (2, 4):
                    totals["wired_bytes"] += function["size"]
                if status == 4:
                    totals["live_bytes"] += function["size"]
    # Object classes placed in the levels
    addresses = class_addresses()
    levels = level_classes()
    classes = {}
    for level in levels:
        for label, count in level["counts"].items():
            entry = classes.setdefault(label, {"name": label, "counts": [0] * len(levels), "total": 0})
            entry["counts"][levels.index(level)] += count
            entry["total"] += count
    for entry in classes.values():
        address = addresses.get(entry["name"])
        family = class_family(address, owner, declared_owner, reviewed_owner) if address is not None else None
        entry["address"] = f"{address:#x}" if address is not None else ""
        entry["family"] = family or ""
        entry["recovered"] = address in owner or (family == reviewed_owner.get(address) and family is not None)
        entry["status"] = class_status(address, manifests.get(family), address in wired_addresses)
    flow = []
    for label, members in FLOW:
        present = [m for m in members if m in manifests]
        flow.append({"step": label, "families": [{"id": m, "integration": manifests[m]["integration"]["level"],
                                                  "evidence": manifests[m]["evidence"]["level"]} for m in present]})
    pilot = []
    for path in sorted(glob.glob(str(WORK / "gate" / "pilot_*" / "gate.json"))):
        gate = json.loads(Path(path).read_text())
        mutants = gate["checks"].get("mutants", {})
        pilot.append({"family": gate["family"], "status": gate["status"], "killed": mutants.get("killed"), "tried": mutants.get("tried")})
    return {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "families": families, "program": program,
        "totals": totals, "levels": [level["level"] for level in levels],
        "classes": sorted(classes.values(), key=lambda c: -c["total"]), "flow": flow, "outside": OUTSIDE, "pilot": pilot,
        "baseline_date": date, "regate_measured": len(regate),
        "text": [0x401000, 0x50ADB5], "library": [[0x4A1300, 0x4B3400], [0x4F0000, 0x50ADB5]],
    }


def main(argv):
    data = build()
    template = (Path(__file__).with_name("progress_page.html")).read_text()
    output = Path(argv[0]) if argv else WORK / "progress" / "claw-progress.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("/*DATA*/null", json.dumps(data, separators=(",", ":"))))
    live = sum(1 for c in data["classes"] if c["status"] == "live")
    level_classes = []
    for offset, level in enumerate(data["levels"]):
        placed = [c for c in data["classes"] if c["counts"][offset]]
        level_classes.append({"level": level, "classes": len(placed),
                              "host_wired": sum(c["status"] == "wired" for c in placed),
                              "live": sum(c["status"] == "live" for c in placed),
                              "pending": [c["name"] for c in placed if c["status"] not in ("wired", "live")]})
    print(json.dumps({"command": "progress-page", "output": str(output), "bytes": output.stat().st_size,
                      "families": len(data["families"]), "functions": len(data["program"]), "classes": len(data["classes"]),
                      "classes_live": live, "classes_missing": sum(1 for c in data["classes"] if c["status"] == "missing"),
                      "classes_host_wired": sum(1 for c in data["classes"] if c["status"] == "wired"),
                      "classes_source_referenced": sum(1 for c in data["classes"] if c["status"] == "referenced"),
                      "classes_draft": sum(1 for c in data["classes"] if c["status"] == "draft"),
                      "level_class_status": level_classes,
                      "levels": len(data["levels"]), "totals": data["totals"], "pilot": len(data["pilot"]), "status": "pass"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
