"""Independent synthetic build selection, mutation transport and freshness checks."""
import copy
import ctypes
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import build, build_inputs, gate, mutants, runner

ROOT = build_inputs.ROOT


class BuildInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "work/pilot").mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="build-inputs-", dir=ROOT / "work/pilot")
        cls.directory = Path(cls.temporary.name)
        cls.cache = patch.object(build, "CACHE", cls.directory / "cache")
        cls.cache.start()
        cls.primary = cls.directory / "Primary.cpp"
        cls.auxiliary = cls.directory / "Auxiliary.cpp"
        cls.header = cls.directory / "Value.h"
        cls.retained = cls.directory / "Portable.cpp"
        cls.primary.write_text('''#include "ClawRuntime.hpp"
extern "C" uint32_t auxiliary(uint32_t, uint32_t);
int owned(uint32_t f) { return f == 0x401000 ? 0 : -1; }
uint32_t body(claw::Run &run, uint32_t, uint32_t receiver, const uint32_t *) {
    uint32_t value = auxiliary(run.get(receiver), run.get(receiver + 4));
    run.put(receiver + 8, value);
    return value;
}
CLAW_MODULE_ENTRY(claw_build_inputs_selftest_entry, owned, body)
''')
        cls.header.write_text("#define EXTRA 0u\n")
        cls.auxiliary.write_text('''#include <stdint.h>
#include "Value.h"
extern "C" uint32_t auxiliary(uint32_t a, uint32_t b) { return a + b + EXTRA; }
''')
        cls.retained.write_text('#error Retained portable source must not enter this comparison\n')
        cls.cases = cls.directory / "cases.py"
        cls.cases.write_text('''from clawparity.cases import Case
def cases(random_source):
    for a, b in ((3, 8), (0xffffffff, 2), (0, 0)):
        def setup(env, a=a, b=b):
            receiver = env.object(12, 'receiver')
            env.put(receiver, a)
            env.put(receiver + 4, b)
            return receiver
        yield Case(str((a, b)), 0x401000, setup, receiver=lambda t: t)
''')
        cls.spec = dict(schema=1, id="build_inputs_selftest", title="Synthetic build input transport",
            abi="canonical", program="synthetic",
            sources=[cls.relative(p) for p in (cls.retained, cls.auxiliary, cls.primary, cls.header)],
            canonical_sources=[cls.relative(p) for p in (cls.primary, cls.auxiliary)],
            owned=[dict(address="0x401000", interval_end="0x401009", convention="thiscall", argc=0, returns="u32")],
            callees={}, oracle=dict(kind="clawparity", cases=cls.relative(cls.cases), entry="claw_build_inputs_selftest_entry"),
            evidence=dict(level="none"), integration=dict(level="source-only"))
        cls.path = cls.directory / "family.json"

    @classmethod
    def tearDownClass(cls):
        cls.cache.stop()
        cls.temporary.cleanup()

    @staticmethod
    def relative(path):
        return str(path.relative_to(ROOT))

    def write_spec(self, spec):
        self.path.write_text(json.dumps(spec))
        return self.path

    def test_default_and_explicit_native_comparisons(self):
        explicit = runner.run(self.write_spec(self.spec))
        self.assertEqual((explicit["status"], explicit.get("cases")), ("pass", 3), explicit)
        default = copy.deepcopy(self.spec)
        del default["canonical_sources"]
        default["sources"] = [self.relative(p) for p in (self.primary, self.auxiliary, self.header)]
        self.assertEqual(build_inputs.sources(default), default["sources"][:2])
        result = runner.run(self.write_spec(default))
        self.assertEqual(result["status"], "pass", result)
        # No field means all owned translation units, including this deliberate
        # compile error. Selection must never silently discard portable inputs.
        default["sources"].append(self.relative(self.retained))
        result = runner.run(self.write_spec(default))
        self.assertEqual(result["status"], "error")
        self.assertIn("Retained portable source", result["detail"])

    def test_mutant_keeps_auxiliary_and_replaces_selected_primary(self):
        variant = self.directory / "Mutant.cpp"
        variant.write_text(self.primary.read_text().replace("return value;", "return value + 1;"))
        for explicit in (True, False):
            spec = copy.deepcopy(self.spec)
            if not explicit:
                del spec["canonical_sources"]
                spec["sources"] = [self.relative(p) for p in (self.primary, self.auxiliary, self.header)]
            result = runner.run(self.write_spec(spec), module_source=variant)
            self.assertEqual(result["status"], "fail", result)
            self.assertEqual(result["failures"][0]["kind"], "return-value", result)
        # Actual mutation subprocess exercises CLI --module-source and proves
        # the retained first owned file is not selected as the mutation target.
        with patch.dict(os.environ, CLAW_BUILD_DIR=str(self.directory / "cache")):
            result = mutants.run(self.write_spec(self.spec), limit=1, jobs=1)
        self.assertEqual((result["tried"], result["killed"], result["invalid"]), (1, 1, 0), result)
        shutil.rmtree(ROOT / "work/build/mutants" / self.spec["id"])

    def test_invalid_inputs_fail_validation_and_runner(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from tools.claw import manifest
        primary = self.relative(self.primary)
        missing = self.relative(self.directory / "Missing.cpp")
        alias = self.directory / "Alias.cpp"
        alias.symlink_to(self.primary)
        invalid = [None, [], "bad", [1], [primary, primary], [self.relative(self.header)],
                   [missing], ["Sources/NotOwned.cpp"], [str(self.primary)],
                   [primary.replace("/Primary", "/../Primary")], [self.relative(alias)]]
        for value in invalid:
            with self.subTest(value=value):
                spec = copy.deepcopy(self.spec)
                spec["canonical_sources"] = value
                spec["sources"] += [missing, str(self.primary), primary.replace("/Primary", "/../Primary"), self.relative(alias)]
                self.assertTrue(manifest.validate(spec))
                result = runner.run(self.write_spec(spec), original_only=True)
                self.assertEqual(result["status"], "error", result)
        legacy = copy.deepcopy(self.spec)
        legacy["abi"] = "legacy"
        self.assertTrue(manifest.validate(legacy))
        self.assertEqual(manifest.validate(self.spec), [])

    def test_cache_identity_and_auxiliary_output(self):
        baseline = build_inputs.library(self.spec)
        self.assertEqual(baseline, build_inputs.library(self.spec))
        for path in (self.primary, self.auxiliary, self.header):
            original = path.read_text()
            try:
                path.write_text(original + "\n// changed input\n")
                self.assertNotEqual(baseline, build_inputs.library(self.spec))
            finally:
                path.write_text(original)
        reverse = copy.deepcopy(self.spec)
        reverse["canonical_sources"].reverse()
        self.assertNotEqual(baseline, build_inputs.library(reverse))
        default = copy.deepcopy(self.spec)
        del default["canonical_sources"]
        default["sources"] = [self.relative(p) for p in (self.primary, self.auxiliary, self.header)]
        self.assertNotEqual(baseline, build_inputs.library(default))
        try:
            self.header.write_text("#define EXTRA 17u\n")
            library = ctypes.CDLL(str(build_inputs.library(self.spec)))
            self.assertEqual(library.auxiliary(3, 8), 28)
        finally:
            self.header.write_text("#define EXTRA 0u\n")

    def test_admission_freshness_and_packet_primary(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from tools.claw import gen_project, manifest, packet, skeleton
        original = copy.deepcopy(self.spec)
        original["evidence"] = dict(level="admitted", gate={})
        self.assertTrue(build_inputs.admission_errors(original))
        original["evidence"]["gate"]["build_inputs_sha256"] = build_inputs.fingerprint(original)
        self.assertEqual(build_inputs.admission_errors(original), [])
        self.assertEqual(manifest.validate(original), [])
        self.assertEqual(packet._files(original, self.path)["module"], self.relative(self.primary))
        # App input ownership remains the full retained set, not canonical_sources.
        with patch.object(gen_project, "checked_source", side_effect=lambda p, **kw: p):
            self.assertEqual(gen_project.canonical_inventory([original], [], root=ROOT)[1], set(original["sources"]))
        variants = []
        changed = copy.deepcopy(original); changed["canonical_sources"].reverse(); variants.append(changed)
        changed = copy.deepcopy(original); del changed["canonical_sources"]; variants.append(changed)
        changed = copy.deepcopy(original); changed["canonical_sources"].pop(); variants.append(changed)
        for changed in variants:
            self.assertTrue(build_inputs.admission_errors(changed))
            self.assertTrue(manifest.validate(changed))
            with self.assertRaisesRegex(ValueError, "stale"):
                gen_project.canonical_inventory([changed], [], root=ROOT)
        for path in (self.primary, self.auxiliary, self.header, self.retained, self.cases):
            text = path.read_text()
            try:
                path.write_text(text + "\n")
                self.assertTrue(build_inputs.admission_errors(original))
            finally:
                path.write_text(text)
        # A draft primary is intentionally absent when generating its skeleton.
        draft = copy.deepcopy(self.spec)
        stub = self.directory / "Stub.cpp"
        draft["sources"].append(self.relative(stub))
        draft["canonical_sources"][0] = self.relative(stub)
        skeleton.generate(self.write_spec(draft))
        self.assertIn("CLAW_MODULE_ENTRY", stub.read_text())
        self.assertIn("#error", self.retained.read_text())

    def test_gate_records_and_checks_input_fingerprint(self):
        # Exercise the real gate orchestration without unrelated compiler,
        # coverage or mutation tests; these have independent real runs above.
        good = dict(status="pass", cases=3, failed=0, coverage={"0x401000":
                    dict(fraction=1, direct_calls=3, bytes=9, executed=9, owned_bytes=9, exempt_bytes=0)})
        mutation = dict(candidates=1, tried=1, killed=1, invalid=0, score=1, survived=[],
                        equivalent=[], source_sha256="unused", review_errors=[], status="pass")
        self.write_spec(self.spec)
        with patch.object(gate.runner, "run", return_value=good), \
                patch.object(gate, "_sanitized", return_value=dict(status="pass")), \
                patch.object(gate.mutants, "run", return_value=mutation):
            result = gate.run(self.path, seed=1, mutant_jobs=1)
        self.assertEqual(result["checks"]["build_inputs_sha256"], build_inputs.fingerprint(self.spec))
        self.assertEqual(result["status"], "admitted", result)
        def change_inputs(*args, **kwargs):
            altered = copy.deepcopy(self.spec)
            altered["canonical_sources"].reverse()
            self.write_spec(altered)
            return good
        with patch.object(gate.runner, "run", side_effect=change_inputs), \
                patch.object(gate, "_sanitized", return_value=dict(status="pass")), \
                patch.object(gate.mutants, "run", return_value=mutation):
            result = gate.run(self.path, seed=1, mutant_jobs=1)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("canonical build inputs changed during the gate", result["reasons"])


if __name__ == "__main__":
    unittest.main()
