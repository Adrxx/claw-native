"""Storage regressions; no emulation, family admission, or provenance overrides."""
import gzip
import hashlib
import io
import json
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Tests.NativeLevels import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_trace_round_trip_and_hash(self):
        report = dict(status='pass', physical_events=[{'service': 'a', 'values': [1, 2]},
                      {'service': 'b', 'text': '\u2603"\\\n'}], math_events=[],
                      frames=[{'x': 1}], nullable=None, number=1.25e-8)
        path = self.root/'trace.json'
        original = (json.dumps(report, indent=2)+'\n').encode()
        path.write_bytes(original)
        streamed = storage.read_trace(path)
        self.assertEqual(streamed, report)
        self.assertIsInstance(streamed['physical_events'], storage.TraceArray)
        self.assertEqual(streamed['physical_events'][-1], report['physical_events'][-1])
        self.assertEqual(list(streamed['physical_events']), list(streamed['physical_events']))
        self.assertEqual(streamed['physical_events'][1:], report['physical_events'][1:])
        target = storage.write_trace(path, streamed)
        self.assertFalse(path.exists())
        self.assertEqual(gzip.decompress(target.read_bytes()), original)
        self.assertEqual(storage.fingerprint(path), hashlib.sha256(original).hexdigest())
        self.assertEqual(storage.read_trace(path), report)
        # Rewriting an already compressed trace reads the old file until commit.
        storage.write_trace(path, storage.read_trace(path))
        self.assertEqual(storage.read_trace(path), report)

    def test_legacy_compression_preserves_exact_bytes(self):
        path = self.root/'trace.json'
        raw = b'{ "physical_events" : [], "number": 1e-3 }\n'
        path.write_bytes(raw)
        target = storage.compress_trace(path)
        self.assertEqual(gzip.decompress(target.read_bytes()), raw)
        self.assertEqual(storage.fingerprint(path), hashlib.sha256(raw).hexdigest())

    def test_parser_chunk_boundaries_and_truncation(self):
        class TinyStream(io.StringIO):
            def read(self, count=-1):
                return super().read(min(count, 1) if count >= 0 else 1)
        report = {'physical_events': [{'text': 'a"\\\n\u2603', 'number': 1.23e-45}],
                  'empty': [], 'boolean': True, 'nothing': None}
        with patch.object(storage, 'open_artifact', lambda *a: TinyStream(json.dumps(report))):
            self.assertEqual(list(storage.trace_rows('unused')),
                             [('physical_events', 'array', None),
                              ('physical_events', 'item', report['physical_events'][0]),
                              ('empty', 'array', None), ('boolean', 'value', True),
                              ('nothing', 'value', None)])
        for invalid in ('{"x": [1,', '{"x": "unterminated', '{"x": 1e}', '{} garbage'):
            with patch.object(storage, 'open_artifact', lambda *a: TinyStream(invalid)):
                with self.assertRaises(ValueError):
                    list(storage.trace_rows('unused'))

    def test_failed_writer_preserves_previous_artifact(self):
        path = self.root/'trace.json'
        path.write_text('{"old": true}\n')
        with self.assertRaises(TypeError):
            storage.write_trace(path, {'bad': object()})
        self.assertEqual(json.loads(path.read_text()), {'old': True})
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_chunked_checkpoint_and_legacy_migration(self):
        regions = [(0x1000, bytes(range(256)) * 9000), (0x500000, b'final region')]
        class Machine:
            def mem_regions(self):
                return [(a, a+len(data)-1, 7) for a, data in regions]

            def mem_read(self, address, count):
                self.max_read = max(getattr(self, 'max_read', 0), count)
                for start, data in regions:
                    if start <= address < start+len(data):
                        return data[address-start:address-start+count]
                raise AssertionError(address)

            def mem_write(self, address, data):
                self.assertion(address, data)
        machine = Machine()
        written = []
        machine.assertion = lambda a, d: written.append((a, d))
        header = {'version': 3, 'state': {'set': {1, 2}, 'tuple': (3, 4)}, 'cpu': [12]}
        path = self.root/'start.pkl'
        storage.save_checkpoint(path, header, machine)
        self.assertEqual(storage.load_checkpoint(path), header)
        storage.restore_memory(path, machine)
        self.assertLessEqual(machine.max_read, storage.CHUNK)
        self.assertEqual(b''.join(d for _, d in written), b''.join(d for _, d in regions))

        legacy = self.root/'legacy.pkl'
        with legacy.open('wb') as stream:
            pickle.dump(dict(header, memory=regions), stream)
        target = storage.migrate_checkpoint(legacy)
        self.assertFalse(legacy.exists())
        self.assertEqual(storage.load_checkpoint(target), header)
        written.clear()
        storage.restore_memory(target, machine)
        self.assertEqual(b''.join(d for _, d in written), b''.join(d for _, d in regions))

    def test_event_log_keeps_callback_updates_and_reverse_lookup(self):
        log = storage.EventLog()
        self.addCleanup(log.close)
        ordinary = {'service': 'COM', 'result': None}
        callback = {'service': 'CRT vector constructor iterator', 'completed': 0}
        enumeration = {'service': 'IDirectDraw::EnumDisplayModes', 'callback': 1}
        log.append(ordinary)
        ordinary['result'] = (1, 2)
        log.append(callback)
        log.append(enumeration)
        log.extend({'service': 'unrelated', 'n': i} for i in range(5000))
        callback['completed'] = 70000
        enumeration['returned'] = True
        self.assertEqual(log[0], ordinary)
        self.assertIs(log[1], callback)
        self.assertIs(log[2], enumeration)
        self.assertEqual(len(log), 5003)
        self.assertEqual(next(reversed(log)), {'service': 'unrelated', 'n': 4999})
        self.assertEqual(json.loads(json.dumps(log))[1]['completed'], 70000)
        path = self.root/'events.pkl'
        class Machine:
            def mem_regions(self):
                return []
        payload = {'state': {'physical_events': log, 'count': 5003}}
        storage.save_checkpoint(path, payload, Machine())
        restored = storage.load_checkpoint(path)
        self.addCleanup(restored['state']['physical_events'].close)
        self.assertEqual(restored, payload)
        storage.restore_memory(path, Machine())
        self.assertEqual(len(restored['state']['physical_events'].live), 2)

    def test_large_trace_reads_are_bounded_and_arrays_stay_lazy(self):
        path = self.root/'large.json.gz'
        count = 20000
        with gzip.open(path, 'wt') as stream:
            stream.write('{"physical_events":[')
            for index in range(count):
                if index:
                    stream.write(',')
                json.dump({'index': index, 'data': 'x' * 256}, stream)
            stream.write('],"math_events":[],"status":"pass"}')

        original_open = storage.open_artifact
        reads = []

        class BoundedReader:
            def __enter__(self):
                self.stream = original_open(path, 'rt')
                return self

            def __exit__(self, *args):
                self.stream.close()

            def read(self, count=-1):
                self_test.assertGreater(count, 0, 'Whole-file read')
                self_test.assertLessEqual(count, 65536)
                reads.append(count)
                return self.stream.read(count)

        self_test = self
        with patch.object(storage, 'open_artifact', lambda *args: BoundedReader()):
            trace = storage.read_trace(path)
            rows = trace['physical_events']
            self.assertIsInstance(rows, storage.TraceArray)
            self.assertEqual(len(rows), count)
            # The list subclass must not quietly accumulate decoded rows.
            self.assertEqual(list.__len__(rows), 0)
            self.assertEqual(sum(row['index'] for row in rows), count*(count-1)//2)
            self.assertEqual(sum(row['index'] for row in rows), count*(count-1)//2)
        self.assertGreater(len(reads), 3)

    def test_memory_restore_skips_event_records_without_decoding_them(self):
        log = storage.EventLog({'service': 'COM', 'index': i} for i in range(1000))
        self.addCleanup(log.close)
        path = self.root/'memory.pkl'
        writes = []

        class Machine:
            def mem_regions(self):
                return [(0x1000, 0x1003, 7)]

            def mem_read(self, address, count):
                return b'data'

            def mem_write(self, address, data):
                writes.append((address, data))

        storage.save_checkpoint(path, {'state': {'physical_events': log}}, Machine())
        with patch.object(storage.pickle, 'loads', side_effect=AssertionError('Decoded event')):
            storage.restore_memory(path, Machine())
        self.assertEqual(writes, [(0x1000, b'data')])



if __name__ == '__main__':
    unittest.main()
