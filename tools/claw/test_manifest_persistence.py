"""The admission recorder must retain the named-layout opt-in when saving."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import manifest


class MutationModePersistence(unittest.TestCase):
    def test_admission_record_round_trip(self):
        original = manifest.load("level_one_player_actions_01")
        for mode in (None, "named-layout"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                spec = json.loads(json.dumps(original))
                spec.pop("mutation", None)
                if mode is not None:
                    spec["mutation"] = mode
                # Exercise the same save/load path used by gate --record.
                spec["evidence"]["gate"] = {"status": "admitted"}
                errors = []
                manifest._check(spec, manifest.SCHEMA, spec["id"], errors)
                self.assertEqual(errors, [])
                with patch.object(manifest, "FAMILIES", Path(directory)):
                    manifest.save(spec)
                    self.assertEqual(manifest.load(spec["id"]), spec)

    def test_unknown_mutation_mode_is_rejected(self):
        spec = manifest.load("level_one_player_actions_01")
        spec["mutation"] = "misspelled-mode"
        errors = []
        manifest._check(spec, manifest.SCHEMA, spec["id"], errors)
        self.assertTrue(any(".mutation:" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
