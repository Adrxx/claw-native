"""Stale discovery must honor the same public admission API as the gate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Tests.clawparity import build_inputs
from tools.claw import regate_stale


class StaleDiscoveryTests(unittest.TestCase):
    def test_shared_admission_uses_public_validation(self):
        # The owned-only checker cannot validate a shared-source fingerprint.
        # Model both disagreement directions: a fresh shared admission must not
        # be re-gated, and a stale borrowed input must not be overlooked.
        for public_errors, owned_errors, expected in (
            ([], ["owned-only fingerprint differs"], []),
            (["borrowed input changed"], [], ["borrower"]),
        ):
            with self.subTest(public_errors=public_errors), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                spec = {"id": "borrower", "shared_sources": [{"family": "owner", "sources": ["owner.cpp"]}]}
                (root / "borrower.json").write_text(json.dumps(spec))
                (root / "schema.json").write_text("{}")
                with (patch.object(regate_stale, "FAMILIES", root),
                      patch.object(build_inputs, "admission_errors", return_value=public_errors),
                      patch.object(build_inputs.owned_inputs, "admission_errors", return_value=owned_errors)):
                    self.assertEqual(regate_stale.stale_families(), expected)


if __name__ == "__main__":
    unittest.main()
