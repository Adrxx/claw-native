"""Freshness and regate --dry-run controls; no compiler, emulator or live edits.

    work/test-env/bin/python -m Tests.clawparity.selftest.admission_fingerprint

Evidence below is a synthetic freshness baseline, never a recorded admission.
"""
import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import admission_inputs, build_inputs
from tools.claw import regate_stale
from tools.claw import migrate_admissions

ROOT = build_inputs.ROOT


class AdmissionFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claw-fingerprint-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = set(admission_inputs.COMMON + admission_inputs.GUEST)
        for paths in admission_inputs.PROFILES.values():
            names.update(paths)
        for name in [admission_inputs.HARNESS + n for n in names] + list(admission_inputs.RANGES):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        self.write("Sources/ClawRuntime.h", "// common ABI\n")
        self.write("Sources/ClawGuestTransfer.h", "// guest ABI\n")
        self.write("Sources/ClawGuestTransfer.cpp", "// guest transport\n")
        self.write("Tests/symbols.json", '{"symbols": {}}\n')
        self.write("Tests/helpers/__init__.py", "")
        self.write("Tests/helpers/value.py", "VALUE = 1\n")
        self.write("docs/ADMISSION.md", "documentation\n")
        self.write("tools/claw/regate_stale.py", "# orchestration outside the gate\n")
        self.specs = {}
        for name, profile in (("old_alpha", "claw-v1.0"), ("old_beta", "claw-v1.0"),
                              ("new_gamma", "claw-v1.3"), ("borrow_alpha", "claw-v1.0")):
            self.write(f"Sources/{name}.cpp", f"int {name}() {{ return 1; }}\n")
            self.write(f"Tests/cases/{name}.py", "from clawparity.cases import Case\n")
            self.specs[name] = {
                "id": name, "abi": "canonical", "program": profile,
                "sources": [f"Sources/{name}.cpp"],
                "owned": [{"address": "0x401000", "interval_end": "0x401001"}],
                "callees": {"0x401010": {"kind": "fixture", "fixture": "set-rect"}},
                "oracle": {"cases": f"Tests/cases/{name}.py"},
            }
        self.write("Tests/cases/old_alpha.py", "from Tests.helpers.value import VALUE\n")
        self.specs["borrow_alpha"]["shared_sources"] = [
            {"family": "old_alpha", "sources": ["Sources/old_alpha.cpp"]}]
        self.refresh()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def save(self, spec):
        self.write(f"Tests/families/{spec['id']}.json", json.dumps(spec))

    def refresh(self):
        # Owner must be fresh before the borrowing family can fingerprint.
        for spec in self.specs.values():
            spec["evidence"] = {"level": "admitted", "gate": {
                "build_inputs_sha256": build_inputs.fingerprint(spec, root=self.root)}}
            self.save(spec)

    def dry_run(self):
        output = io.StringIO()
        scan = regate_stale.stale_families
        with patch.object(regate_stale, "stale_families", side_effect=lambda: scan(root=self.root)), \
                patch.object(regate_stale, "regate", side_effect=AssertionError("dry-run ran a gate")), \
                contextlib.redirect_stdout(output):
            self.assertEqual(regate_stale.main(["--dry-run"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["stale_count"], len(result["stale"]))
        return result["stale"]

    def test_control_edits_report_exactly_affected_families(self):
        all_families = sorted(self.specs)
        controls = {
            "Tests/clawparity/program_v13.py": ["new_gamma"],
            "Tests/clawparity/profiles.py": ["new_gamma"],
            "Tests/clawparity/program.py": all_families,
            "Tests/clawparity/runner.py": all_families,
            "Tests/clawparity/env.py": all_families,
            "Tests/clawparity/kernel.py": all_families,
            "Tests/clawparity/hostlib.cpp": all_families,
            "Tests/clawparity/fixtures.py": all_families,
            "Tests/clawparity/build_inputs.py": all_families,
            "Tests/clawparity/shared_build_inputs.py": all_families,
            "Tests/clawparity/admission_inputs.py": all_families,
            "Tests/clawparity/mutation_review.py": all_families,
            "Sources/ClawRuntime.h": all_families,
            "Sources/old_alpha.cpp": ["borrow_alpha", "old_alpha"],
            "Sources/old_beta.cpp": ["old_beta"],
            "Tests/cases/old_alpha.py": ["borrow_alpha", "old_alpha"],
            "Tests/helpers/value.py": ["borrow_alpha", "old_alpha"],
            "Tests/helpers/__init__.py": ["borrow_alpha", "old_alpha"],
            "Tests/clawparity/guest_adapter.py": [],
            "Tests/clawparity/selftest/synthetic.py": [],
            "docs/ADMISSION.md": [],
            "tools/claw/regate_stale.py": [],
        }
        self.assertEqual(self.dry_run(), [])
        for name, expected in controls.items():
            with self.subTest(input=name):
                path = self.root / name
                original = path.read_bytes()
                try:
                    # Valid source edits in the isolated input tree. Runtime
                    # implementations remain the checked-in implementation.
                    path.write_bytes(original + (b"\n// control\n" if path.suffix in (".cpp", ".h")
                                                 else b"\nCONTROL_EDIT = 1\n"))
                    self.assertEqual(self.dry_run(), expected)
                    for family, spec in self.specs.items():
                        self.assertEqual(bool(build_inputs.admission_errors(spec, root=self.root)),
                                         family in expected, family)
                finally:
                    path.write_bytes(original)
        self.assertEqual(self.dry_run(), [])

    def test_profile_spec_fixture_and_missing_hash_controls(self):
        original = self.specs["old_beta"]
        for edit in ("profile", "fixture", "hash", "old-hash"):
            with self.subTest(edit=edit):
                spec = copy.deepcopy(original)
                if edit == "profile":
                    spec["program"] = "claw-v1.3"
                elif edit == "fixture":
                    spec["callees"]["0x401010"]["fixture"] = "set-rect-empty"
                elif edit == "hash":
                    spec["evidence"]["gate"] = {}
                else:
                    spec["evidence"]["gate"]["build_inputs_sha256"] = "0" * 64
                self.save(spec)
                self.assertEqual(self.dry_run(), ["old_beta"])
        self.save(original)
        spec = copy.deepcopy(original)
        spec["program"] = "unreviewed-profile"
        with self.assertRaisesRegex(ValueError, "no reviewed admission inputs"):
            build_inputs.fingerprint(spec, root=self.root)

    def test_optional_guest_inputs_and_cross_profile_owner(self):
        self.specs["old_beta"]["oracle"]["guest_graph"] = {}
        self.specs["borrow_alpha"]["program"] = "claw-v1.3"
        self.refresh()
        for name in ("Tests/clawparity/guest_adapter.py", "Sources/ClawGuestTransfer.h"):
            path = self.root / name
            original = path.read_bytes()
            try:
                path.write_bytes(original + b"\n")
                self.assertEqual(self.dry_run(), ["old_beta"])
            finally:
                path.write_bytes(original)
        path = self.root / "Sources/old_alpha.cpp"
        path.write_text(path.read_text() + "\n")
        self.assertEqual(self.dry_run(), ["borrow_alpha", "old_alpha"])

    def test_corpus_only_affects_consumers_of_changed_ranges(self):
        del self.specs["old_beta"]["owned"][0]["interval_end"]
        corpus = {"functions": [{"entry": "0x401000", "ranges": [[0x401000, 0x401001]]},
                                {"entry": "0x402000", "ranges": [[0x402000, 0x402001]]}]}
        self.write("work/corpus/index.json", json.dumps(corpus))
        self.refresh()
        corpus["functions"][1]["ranges"][0][1] += 1
        self.write("work/corpus/index.json", json.dumps(corpus))
        self.assertEqual(self.dry_run(), [])
        corpus["functions"][0]["ranges"][0][1] += 1
        self.write("work/corpus/index.json", json.dumps(corpus))
        self.assertEqual(self.dry_run(), ["old_beta"])

    def test_missing_input_stales_and_unadmitted_family_is_not_regated(self):
        (self.root / "Tests/helpers/value.py").unlink()
        self.assertEqual(self.dry_run(), ["borrow_alpha", "old_alpha"])
        spec = self.specs["borrow_alpha"]
        spec["evidence"]["level"] = "none"
        self.save(spec)
        self.assertEqual(self.dry_run(), ["old_alpha"])

    def test_count_is_emitted_before_any_gate_starts(self):
        output = io.StringIO()

        def gate(family):
            first = json.loads(output.getvalue().splitlines()[0])
            self.assertEqual(first, {"command": "regate-stale", "stale_count": 1,
                                     "status": "starting"})
            return family, "admitted"

        with patch.object(regate_stale, "stale_families", return_value=["old_alpha"]), \
                patch.object(regate_stale, "FAMILIES", self.root / "Tests/families"), \
                patch.object(regate_stale, "regate", side_effect=gate), \
                contextlib.redirect_stdout(output):
            self.assertEqual(regate_stale.main(["--jobs", "1"]), 0)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["regated"], 1)


    def test_exact_baseline_migrates_and_records_proof(self):
        baseline = self.baseline()
        result = migrate_admissions.migrate(baseline, root=self.root, record=True)
        self.assertEqual(result["migrated"], 3)  # v1.3 has no migration authority.
        self.assertEqual(result["requires_gate"], ["new_gamma"])
        self.assertEqual(self.dry_run(), ["new_gamma"])
        for name in ("old_alpha", "old_beta", "borrow_alpha"):
            row = result["families"][name]
            self.assertTrue(all(r["identical"] for r in row["harness"].values()))
            self.assertTrue(all(r["identical"] for r in row["inputs"].values()))

    def baseline(self):
        for spec in self.specs.values():
            spec["evidence"]["gate"]["build_inputs_sha256"] = "old-record"
            spec["evidence"]["gate"]["status"] = "admitted"
            self.save(spec)
        files = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}

        class Snapshot:
            commit = "synthetic-baseline"
            read = staticmethod(files.get)

        return Snapshot()

    def test_changed_module_cannot_migrate_any_family(self):
        baseline = self.baseline()
        path = self.root / "Tests/clawparity/runner.py"
        path.write_text(path.read_text() + "\n")
        result = migrate_admissions.migrate(baseline, root=self.root, record=True)
        self.assertEqual(result["migrated"], 0)
        self.assertEqual(sorted(result["requires_gate"]), sorted(self.specs))
        self.assertEqual(json.loads((self.root / "Tests/families/old_alpha.json").read_text())
                         ["evidence"]["gate"]["build_inputs_sha256"], "old-record")

    def test_changed_named_input_or_last_record_is_not_migrated(self):
        baseline = self.baseline()
        self.write("Sources/old_alpha.cpp", "int old_alpha() { return 2; }\n")
        spec = self.specs["old_beta"]
        spec["evidence"]["gate"]["seed"] = 99
        self.save(spec)
        result = migrate_admissions.migrate(baseline, root=self.root, record=True)
        self.assertEqual(result["migrated"], 0)
        self.assertFalse(result["families"]["old_beta"]["last_record"]["verified"])


if __name__ == "__main__":
    unittest.main()
