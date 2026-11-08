"""Focused checks for original-format local test scene generation (no emulator)."""
import struct
import unittest

from tools.claw.test_level import (
    collision_descriptions, entries, family_logics, generate, solid_at, unpack_world,
)


class TestLevelGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packed = next(payload for name, payload in entries()
                          if name == 'LEVEL13/WORLDS/WORLD.WWD')

    def test_ten_original_records_keep_tiles_resources_and_spawn(self):
        generated, manifest = generate(self.packed, 13, [], spacing=28)
        original, planes = unpack_world(self.packed)
        changed, new_planes = unpack_world(generated)
        self.assertEqual(manifest['object_types'], 10)
        selected = [obj for plane in new_planes for obj in plane['objects']]
        self.assertEqual(len(selected), 10)
        self.assertEqual(len({o['logic'] for o in selected}), 10)
        self.assertIn('Checkpoint', {o['logic'] for o in selected})
        self.assertNotIn('CursePowerup', {o['logic'] for o in selected})
        self.assertEqual(struct.unpack_from('<2I', original, 720),
                         struct.unpack_from('<2I', changed, 720))
        # Preserve original length, object offsets, and every byte outside the
        # reused action-record prefix and plane object counts.
        self.assertEqual(len(changed), len(original))
        self.assertEqual(changed[744:748], original[744:748])
        expected = bytearray(original)
        for plane in planes:
            at = plane['header']
            expected[at+128:at+132] = changed[at+128:at+132]
            self.assertEqual(changed[at+140:at+144], original[at+140:at+144])
        start = manifest['record_offset']
        end = start + manifest['record_bytes']
        expected[start:end] = changed[start:end]
        self.assertEqual(changed, expected)
        action = next(p for p in planes if p['flags'] & 1)
        descriptions = collision_descriptions(original)
        for obj, metadata in zip(selected, manifest['objects']):
            source = action['objects'][metadata['source_index']]
            self.assertEqual(source['logic'], obj['logic'])
            self.assertEqual(source['id'], obj['id'])
            copied = bytearray(source['record'])
            for index in metadata['translated_words']:
                copied[index*4:index*4+4] = obj['record'][index*4:index*4+4]
            self.assertEqual(copied, obj['record'])
            self.assertTrue(solid_at(original, action, descriptions, obj['x'], metadata['ground_y']))
            self.assertFalse(solid_at(original, action, descriptions, obj['x'], metadata['ground_y']-1))
            self.assertGreaterEqual(obj['x'], manifest['spawn']['x'])
            self.assertLessEqual(obj['x']-manifest['spawn']['x'], 300)

    def test_family_uses_registered_original_callback(self):
        self.assertEqual(family_logics(['laser']), ['Laser'])

    def test_uncompressed_uses_same_original_payload_and_only_clears_compression_flag(self):
        compressed, first = generate(self.packed, 13, [], spacing=20)
        uncompressed, second = generate(self.packed, 13, [], spacing=20, uncompressed=True)
        decoded, _ = unpack_world(compressed)
        plain, _ = unpack_world(uncompressed)
        flags = struct.unpack_from('<I', decoded, 8)[0]
        self.assertTrue(flags & 2)
        struct.pack_into('<I', decoded, 8, flags & ~2)
        self.assertEqual(decoded, plain)
        self.assertEqual(uncompressed, plain)
        self.assertEqual(first['objects'], second['objects'])
        self.assertTrue(first['compressed'])
        self.assertFalse(second['compressed'])

    def test_missing_placement_is_explicit(self):
        with self.assertRaisesRegex(ValueError, 'Not placed'):
            generate(self.packed, 13, ['Aquatis'])

    def test_duplicate_selection_is_one_copied_object(self):
        generated, report = generate(self.packed, 13, ['PowderKeg', 'PowderKeg'])
        self.assertEqual(report['object_types'], 1)
        _, planes = unpack_world(generated)
        self.assertEqual(sum(len(p['objects']) for p in planes), 1)

    def test_invalid_family_cannot_escape_spec_directory(self):
        with self.assertRaisesRegex(ValueError, 'Family must'):
            family_logics(['../laser'])


if __name__ == '__main__':
    unittest.main()
