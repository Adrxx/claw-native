"""Pinned game profiles, physical imports and a two-profile native comparison.

PYTHONPATH=Tests work/test-env/bin/python -m clawparity.selftest.oracle_profiles --spot-check-gates
"""
import argparse
import copy
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from .. import build_inputs, program, profiles, runner
from ..env import Env
from ..fixtures import CATALOGUE
from ..kernel import STACK_TOP

ROOT = Path(__file__).resolve().parents[3]
PROOF = ROOT / "Tests/OracleProfiles"


def load_guard():
    load = subprocess.check_output(["sysctl", "-n", "vm.loadavg"], text=True)
    if float(load.split()[1]) >= 16:
        raise RuntimeError(f"wait for load below 16 before rerunning: {load.strip()}")


def checks():
    found = {}

    def rejects(label, action, error=ValueError):
        try:
            action()
        except error:
            found[label] = True
        else:
            found[label] = False

    old, new = program.claw(), program.claw_v13()
    found["default_identity_unchanged"] = (
        runner.load_program({}) == old and program.profile() == old and
        old.sha256 == program.CLAW_SHA256 and old.startup_calls == (0x4a7ef0,))
    found["explicit_v13_identity"] = (
        runner.load_program({"program": "claw-v1.3"}) == new and
        new.sha256 == program.CLAW_V13_SHA256 and new.startup_calls == (0x4a9a52,))
    rejects("unknown_profile_rejected", lambda: program.profile("claw-v1.4"))
    rejects("wrong_game_hash_rejected", lambda: program.Program.from_bytes(
        b"not the game", program.CLAW_V13_SHA256, "claw-v1.3"))
    with patch.object(Path, "read_bytes", return_value=b"not the launcher"):
        rejects("wrong_launcher_hash_rejected", program.claw_v13)
    # Keep the real resource lookup, but corrupt the extracted game's payload.
    import pefile
    wrapper = pefile.PE(str(program.CLAW_V13_WRAPPER))
    with patch("pefile.PE", return_value=wrapper), patch.object(wrapper, "get_data", return_value=b"wrong game"):
        rejects("embedded_game_hash_rejected", program.claw_v13)
    wrapper = pefile.PE(str(program.CLAW_V13_WRAPPER))
    resources = wrapper.DIRECTORY_ENTRY_RESOURCE.entries
    wrapper.DIRECTORY_ENTRY_RESOURCE.entries = [e for e in resources if str(e.name) != "EXE"]
    with patch("pefile.PE", return_value=wrapper):
        rejects("missing_exact_resource_rejected", program.claw_v13)

    spec = json.loads((PROOF / "v13.json").read_text())
    found["v13_contract"] = profiles.validate(spec) == new
    found["v13_lint"] = profiles.lint(spec) == ([], [])
    missing = copy.deepcopy(spec)
    del missing["owned"][0]["interval_end"]
    rejects("no_v10_corpus_fallback", lambda: runner.owned_ranges(missing))
    bad_range = copy.deepcopy(spec)
    bad_range["owned"][0]["interval_end"] = "0x600000"
    rejects("out_of_image_extent_rejected", lambda: profiles.validate(bad_range))
    cut = copy.deepcopy(spec)
    cut["owned"][0]["interval_end"] = "0x4a2013"
    found["cut_instruction_rejected_by_lint"] = bool(profiles.lint(cut)[0])
    signature = copy.deepcopy(spec)
    signature["owned"][0]["convention"] = "stdcall"
    found["wrong_return_pop_rejected"] = bool(profiles.lint(signature)[0])

    # Ownership identity includes the program; equal numeric addresses in two
    # different executables are not duplicate claims.
    from tools.claw.owned_ranges import canonical_overlap_errors
    same_address = copy.deepcopy(spec)
    same_address.update(id="old_profile", program="claw-v1.0")
    found["ownership_separate_by_profile"] = not canonical_overlap_errors([spec, same_address], corpus={})
    duplicate = copy.deepcopy(spec)
    duplicate["id"] = "duplicate_v13"
    found["same_profile_overlap_rejected"] = bool(canonical_overlap_errors([spec, duplicate], corpus={}))
    admitted = copy.deepcopy(spec)
    admitted["evidence"] = {"level": "admitted", "gate": {"build_inputs_sha256": build_inputs.fingerprint(spec)}}
    found["v13_admission_fingerprint"] = not build_inputs.admission_errors(admitted)
    read_bytes = Path.read_bytes
    for filename in ("program.py", "profiles.py", "shared_build_inputs.py"):
        target = ROOT / "Tests/clawparity" / filename
        def changed(path):
            return read_bytes(path) + (b"\n# changed profile input\n" if path == target else b"")
        with patch.object(Path, "read_bytes", changed):
            found[filename + "_change_invalidates_v13_admission"] = bool(build_inputs.admission_errors(admitted))
    admitted["program"] = "claw-v1.0"
    found["profile_change_invalidates_admission"] = bool(build_inputs.admission_errors(admitted))

    fixture_slots = {
        "claw-v1.0": {"set-rect": 0x546d5c, "set-rect-empty": 0x546cdc, "is-bad-read-ptr": 0x546a40},
        "claw-v1.3": {"set-rect": 0x50c4d8, "set-rect-empty": 0x50c430, "is-bad-read-ptr": 0x50c168},
    }
    services = {"set-rect": "USER32.dll!SetRect", "set-rect-empty": "USER32.dll!SetRectEmpty",
                "is-bad-read-ptr": "KERNEL32.dll!IsBadReadPtr"}
    arities = {"set-rect": 5, "set-rect-empty": 1, "is-bad-read-ptr": 2}
    for p in (old, new):
        load_guard()
        env = Env(p)
        found[p.name + "_startup_x87"] = env.machine.initial_control_word == 0x23f
        for effect, service in services.items():
            slot = next(a for a, name in p.imports.items() if name == service)
            found[p.name + "_" + effect + "_slot"] = slot == fixture_slots[p.name][effect]
            env.fixture(slot, "stdcall", arities[effect], CATALOGUE[effect], service)
        for effect, arguments, expected in (
                ("set-rect", (-10, 20, 30, -40), (-10, 20, 30, -40)),
                ("set-rect-empty", (), (0, 0, 0, 0)),
                ("is-bad-read-ptr", (16,), (7, 8, 9, 10))):
            env._begin_case(None)
            rect = env.object(16, "RECT", words=(7, 8, 9, 10))
            env._freeze()
            slot = next(a for a, name in p.imports.items() if name == services[effect])
            result = env.run_original(env.machine.import_stub[slot], 0,
                                      (rect, *(a & 0xffffffff for a in arguments)))
            found[p.name + "_" + effect + "_physical"] = (
                result.completed and not result.errors and len(result.events) == 1 and
                result.eax == (0 if effect == "is-bad-read-ptr" else 1) and
                result.stack_pointer == STACK_TOP + 4 + 4 * arities[effect] and
                env.machine.read(rect, 16) == b"".join((v & 0xffffffff).to_bytes(4, "little") for v in expected))
    bad_fixture = copy.deepcopy(spec)
    bad_fixture["callees"] = {"0x546d5c": {"kind": "fixture", "fixture": "set-rect"}}
    rejects("v10_import_slot_rejected", lambda: profiles.validate(bad_fixture))
    bad_fixture["callees"] = {"0x50c430": {"kind": "fixture", "fixture": "set-rect"}}
    rejects("wrong_v13_service_rejected", lambda: profiles.validate(bad_fixture))
    bad_fixture["callees"] = {"0x50c4d8": {"kind": "fixture", "fixture": "set-rect",
        "convention": "stdcall", "argc": 5}}
    found["valid_v13_fixture_declaration"] = profiles.validate(bad_fixture) == new
    bad_fixture["callees"]["0x50c4d8"]["argc"] = 4
    rejects("wrong_v13_fixture_arity_rejected", lambda: profiles.validate(bad_fixture))

    results = {}
    for version in ("v10", "v13"):
        load_guard()
        result = runner.run(PROOF / f"{version}.json", seed=1729, trace=True)
        results[version] = result
        found[version + "_native_comparison"] = result["status"] == "pass" and result.get("cases") == 69
        found[version + "_full_coverage"] = all(
            c["fraction"] == 1 and c["exempt_bytes"] == 0 for c in result.get("coverage", {}).values())
    return found, results


def spot_check_gates():
    from .. import gate
    results = {}
    for family in ("application_startup_zero_hook", "menu_window_record", "surface_flip"):
        path = ROOT / "Tests/families" / f"{family}.json"
        before = path.read_bytes()
        spec = json.loads(before)
        prior = spec["evidence"]["gate"]
        load_guard()
        result = gate.run(path, seed=prior["seed"], mutant_jobs=1)
        checks = result["checks"]
        results[family] = {
            "status": result["status"], "reasons": result["reasons"],
            "cases": checks["gate_seed"].get("cases"),
            "mutation_score": checks["mutants"].get("score"),
            "unchanged_admission_record": path.read_bytes() == before,
            "matches_recorded_result": (result["status"] == prior["status"] == "admitted" and
                checks["gate_seed"].get("cases") == prior["cases"] and
                checks["mutants"].get("score") == prior["mutation_score"]),
        }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spot-check-gates", action="store_true")
    args = parser.parse_args()
    found, comparisons = checks()
    gates = spot_check_gates() if args.spot_check_gates else {}
    for name, result in gates.items():
        found[name + "_gate_unchanged"] = result["unchanged_admission_record"] and result["matches_recorded_result"]
    failed = [name for name, passed in found.items() if not passed]
    print(json.dumps({"command": "oracle-profiles-selftest", "status": "fail" if failed else "pass",
                      "checked": len(found), "failed": failed, "comparisons": comparisons, "gates": gates}))
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
