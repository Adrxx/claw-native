"""Independent shared-owner linking, freshness and rejection controls."""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import build, build_inputs, mutants, runner
from .build_inputs import BuildInputTests

ROOT = build_inputs.ROOT
# Family case modules use this import root, also when make selftest invokes us
# from the repository root through the Tests package.
sys.path.insert(0, str(ROOT / "Tests"))


class SharedBuildInputTests(unittest.TestCase):
    relative = staticmethod(BuildInputTests.relative)
    write_spec = BuildInputTests.write_spec

    @classmethod
    def setUpClass(cls):
        BuildInputTests.setUpClass.__func__(cls)
        with tempfile.NamedTemporaryFile(prefix="shared_input_test_", suffix=".json",
                                         dir=ROOT / "Tests/families", delete=False) as file:
            cls.owner_path = Path(file.name)
        cls.owner = copy.deepcopy(cls.spec)
        cls.owner.update(id=cls.owner_path.stem,
                         sources=[cls.relative(cls.auxiliary), cls.relative(cls.header)],
                         canonical_sources=[cls.relative(cls.auxiliary)])
        cls.owner["owned"][0].update(address="0x401100", interval_end="0x401109")
        cls.owner["oracle"]["entry"] = "claw_shared_owner_selftest_entry"
        cls.owner["evidence"] = dict(level="admitted", gate={})
        cls.owner["evidence"]["gate"]["build_inputs_sha256"] = build_inputs.fingerprint(cls.owner)
        cls.owner_path.write_text(json.dumps(cls.owner))
        cls.borrower = copy.deepcopy(cls.spec)
        cls.borrower["sources"] = [cls.relative(cls.retained), cls.relative(cls.primary)]
        cls.borrower["canonical_sources"] = [cls.relative(cls.primary)]
        cls.borrower["shared_sources"] = [dict(family=cls.owner_path.stem, sources=cls.owner["sources"])]

    @classmethod
    def tearDownClass(cls):
        cls.owner_path.unlink()
        BuildInputTests.tearDownClass.__func__(cls)

    def test_link_and_mutant_keep_borrowed_translation_unit(self):
        self.assertEqual(build_inputs.sources(self.borrower),
                         [self.relative(self.primary), self.relative(self.auxiliary)])
        result = runner.run(self.write_spec(self.borrower))
        self.assertEqual((result["status"], result.get("cases")), ("pass", 3), result)
        variant = self.directory / "SharedMutant.cpp"
        variant.write_text(self.primary.read_text().replace("return value;", "return value + 1;"))
        result = runner.run(self.write_spec(self.borrower), module_source=variant)
        self.assertEqual(result["status"], "fail", result)
        self.assertEqual(result["failures"][0]["kind"], "return-value", result)
        with patch.dict(os.environ, CLAW_BUILD_DIR=str(self.directory / "cache")):
            result = mutants.run(self.write_spec(self.borrower), limit=1, jobs=1)
        self.assertEqual((result["tried"], result["killed"], result["invalid"]), (1, 1, 0), result)
        shutil.rmtree(ROOT / "work/build/mutants" / self.borrower["id"])
        default = copy.deepcopy(self.borrower)
        del default["canonical_sources"]
        default["sources"] = [self.relative(self.primary)]
        result = runner.run(self.write_spec(default))
        self.assertEqual(result["status"], "pass", result)

    def test_cache_and_admission_bind_shared_source_header_and_owner(self):
        spec = copy.deepcopy(self.borrower)
        baseline = build_inputs.fingerprint(spec)
        library = build_inputs.library(spec)
        spec["evidence"] = dict(level="admitted", gate=dict(build_inputs_sha256=baseline))
        self.assertEqual(build_inputs.admission_errors(spec), [])
        for path in (self.auxiliary, self.header):
            original = path.read_text()
            try:
                path.write_text(original + "\n// changed shared input\n")
                self.assertTrue(build_inputs.admission_errors(spec))
                with self.assertRaisesRegex(ValueError, "stale"):
                    build_inputs.library(spec)
                refreshed = copy.deepcopy(self.owner)
                refreshed["evidence"]["gate"]["build_inputs_sha256"] = build_inputs.fingerprint(refreshed)
                self.owner_path.write_text(json.dumps(refreshed))
                self.assertNotEqual(library, build_inputs.library(spec))
                self.assertNotEqual(baseline, build_inputs.fingerprint(spec))
            finally:
                path.write_text(original)
                self.owner_path.write_text(json.dumps(self.owner))
        changed = copy.deepcopy(self.owner)
        changed["evidence"]["gate"]["seed"] = 456
        self.owner_path.write_text(json.dumps(changed))
        self.assertEqual(baseline, build_inputs.fingerprint(spec))
        self.owner_path.write_text(json.dumps(self.owner))
        # An opt-in extension must not invalidate unchanged default admissions.
        self.assertEqual(build_inputs.fingerprint(self.spec),
                         build_inputs.owned_inputs.fingerprint(self.spec))

    def test_invalid_references_fail_before_original_or_native_execution(self):
        from tools.claw import manifest
        reference = self.borrower["shared_sources"][0]
        variants = [None, [], "bad", [1], [reference, reference],
                    [dict(family=self.borrower["id"], sources=reference["sources"])],
                    [dict(family="../escape", sources=reference["sources"])],
                    [dict(family="missing_shared_owner", sources=reference["sources"])],
                    [dict(family=self.owner_path.stem, sources=[])],
                    [dict(family=self.owner_path.stem, sources=[self.relative(self.primary)])],
                    [dict(family=self.owner_path.stem, sources=[self.relative(self.auxiliary)] * 2)]]
        for references in variants:
            with self.subTest(references=references):
                spec = copy.deepcopy(self.borrower)
                spec["shared_sources"] = references
                self.assertTrue(manifest.validate(spec))
                result = runner.run(self.write_spec(spec), original_only=True)
                self.assertEqual(result["status"], "error", result)
        for modification in (dict(evidence=dict(level="none")),
                             dict(shared_sources=self.borrower["shared_sources"])):
            try:
                self.owner_path.write_text(json.dumps(dict(self.owner, **modification)))
                with self.assertRaises(ValueError):
                    build_inputs.sources(self.borrower)
            finally:
                self.owner_path.write_text(json.dumps(self.owner))

    def test_app_membership_keeps_single_owner_and_rejects_missing_owner(self):
        from tools.claw import gen_project
        spec = copy.deepcopy(self.borrower)
        spec["evidence"] = dict(level="admitted", gate=dict(build_inputs_sha256=build_inputs.fingerprint(spec)))
        with patch.object(gen_project, "checked_source", side_effect=lambda p, **kw: p):
            _, admitted, _ = gen_project.canonical_inventory([self.owner, spec], [], root=ROOT)
            self.assertEqual(admitted, set(self.owner["sources"] + spec["sources"]))
            with self.assertRaisesRegex(ValueError, "absent from app inventory"):
                gen_project.canonical_inventory([spec], [], root=ROOT)
            with self.assertRaisesRegex(ValueError, "is excluded"):
                gen_project.canonical_inventory([self.owner, spec],
                    [dict(path=self.relative(self.auxiliary))], root=ROOT)


if __name__ == "__main__":
    unittest.main()
