"""Captured fader inputs keep their stored-byte identity with streamed reads."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Tests.NativeLevelTwo.check_fader_power import captured_reference
from Tests.NativeLevels.storage import TraceArray


class CapturedStorageTests(unittest.TestCase):
    def test_plain_and_compressed_capture_preserve_hash_and_context(self):
        report = dict(stopped_context={'last_transfer': {'target': '0x4f1b30'}},
                      level_two_played_ms=17,
                      physical_events=[{'service': 'captured', 'index': i} for i in range(1000)])
        raw = json.dumps(report).encode()
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory)/'trace.json'
            for compressed in (False, True):
                path = Path(str(plain)+'.gz') if compressed else plain
                stored = gzip.compress(raw) if compressed else raw
                path.write_bytes(stored)
                with patch.object(Path, 'read_bytes', side_effect=AssertionError('Whole-file read')):
                    captured, checksum = captured_reference(plain)
                self.assertEqual(checksum, hashlib.sha256(stored).hexdigest())
                self.assertEqual(captured, report)
                self.assertIsInstance(captured['physical_events'], TraceArray)
                self.assertEqual(list.__len__(captured['physical_events']), 0)
                path.unlink()


if __name__ == '__main__':
    unittest.main()
