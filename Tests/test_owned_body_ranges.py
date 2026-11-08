"""Synthetic ownership validation; no original bytes or source implementations."""
import hashlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.claw import manifest, owned_ranges, speclint


BASE = 0x401000
# Authored synthetic x86: mov eax, immediate; add eax, 1; ret; nop padding.
CODE = bytes.fromhex('b87856341283c001c3') + b'\x90' * 55


def row(low=BASE, high=BASE + 9, data=CODE):
    return dict(start=hex(low), end=hex(high),
                sha256=hashlib.sha256(data[low - BASE:high - BASE]).hexdigest())


def family(name='example', entries=None):
    return dict(schema=1, id=name, title='Synthetic ownership', abi='canonical', sources=[],
                owned=entries if entries is not None else [dict(address=hex(BASE), body_ranges=[row()])],
                callees={}, oracle=dict(kind='none'), evidence=dict(level='none'),
                integration=dict(level='source-only'))


class BodyRangesTests(unittest.TestCase):
    def setUp(self):
        self.corpus = {BASE: dict(ranges=[[BASE, BASE + 9]])}
        self.reference = SimpleNamespace(
            sha256=owned_ranges.ORIGINAL_SHA256, text=(BASE, BASE + len(CODE)),
            sections=[SimpleNamespace(address=BASE, data=CODE)])
        self.loader = patch.object(owned_ranges.programs, 'claw', return_value=self.reference).start()
        patch.object(owned_ranges.index, 'functions', return_value=self.corpus).start()
        self.addCleanup(patch.stopall)

    def reject(self, spec, text):
        with self.assertRaisesRegex(ValueError, text):
            owned_ranges.resolve_owned_ranges(spec)

    def test_valid_body_and_pinned_loader(self):
        self.assertEqual(owned_ranges.resolve_owned_ranges(family()), {BASE: [(BASE, BASE + 9)]})
        self.loader.assert_called_once_with()

    def test_loader_failure_cannot_be_bypassed_by_matching_range_hash(self):
        self.loader.side_effect = ValueError('full executable SHA-256 mismatch')
        self.reject(family(), 'full executable SHA-256 mismatch')

    def test_alternate_reference_identity_rejected(self):
        self.reference.sha256 = '0' * 64
        self.reject(family(), 'pinned reference')

    def test_content_hash_mismatch(self):
        spec = family()
        spec['owned'][0]['body_ranges'][0]['sha256'] = '0' * 64
        self.reject(spec, 'SHA-256 mismatch')

    def test_strict_range_structure_and_scalar_types(self):
        bad_rows = [None, True, {}, [], [None], [True], [dict(start=hex(BASE), end=hex(BASE + 9))],
                    [{**row(), 'comment': 'ignored?'}], [{**row(), 'start': BASE}],
                    [{**row(), 'start': True}], [{**row(), 'end': '0x100401009'}],
                    [{**row(), 'end': '0x40100A'}], [{**row(), 'sha256': True}],
                    [{**row(), 'sha256': 'A' * 64}], [{**row(), 'end': hex(BASE)}],
                    [{**row(), 'end': hex(BASE - 1)}]]
        for rows in bad_rows:
            with self.subTest(rows=rows):
                spec = family()
                spec['owned'][0]['body_ranges'] = rows
                self.reject(spec, 'body[ _]range|address')

    def test_malformed_owned_container_rejected_without_crashing(self):
        for entries in (None, True, {}, 'owned'):
            with self.subTest(entries=entries):
                spec = {**family(), 'owned': entries}
                self.reject(spec, 'owned must be a list')
                self.assertEqual(owned_ranges.body_range_errors(spec), [])

    def test_missing_root(self):
        spec = family()
        spec['owned'][0]['body_ranges'] = [row(BASE + 5, BASE + 9)]
        self.reject(spec, 'include the public root')

    def test_unknown_root(self):
        spec = family()
        spec['owned'][0]['address'] = hex(BASE + 5)
        self.reject(spec, 'not an original corpus function entry')

    def test_cut_instruction_end_even_with_matching_hash(self):
        spec = family()
        spec['owned'][0]['body_ranges'] = [row(BASE, BASE + 4)]
        self.reject(spec, 'cuts an instruction')

    def test_cut_start_must_not_be_redecoded_as_a_new_instruction(self):
        # The byte at +1 can decode independently. The prior anchor reveals
        # that it is actually inside mov eax,imm32.
        self.corpus[BASE + 8] = dict(ranges=[[BASE + 8, BASE + 9]])
        spec = family(entries=[dict(address=hex(BASE + 8), body_ranges=[row(BASE + 1, BASE + 9)])])
        self.reject(spec, 'cuts an instruction')

    def test_contained_root_must_itself_be_an_instruction_boundary(self):
        self.corpus[BASE + 1] = dict(ranges=[[BASE + 1, BASE + 9]])
        spec = family(entries=[dict(address=hex(BASE + 1), body_ranges=[row()])])
        self.reject(spec, 'cuts an instruction')

    def test_root_can_be_inside_body_on_a_real_instruction_boundary(self):
        self.corpus[BASE + 5] = dict(ranges=[[BASE + 5, BASE + 9]])
        spec = family(entries=[dict(address=hex(BASE + 5), body_ranges=[row()])])
        self.assertEqual(owned_ranges.resolve_owned_ranges(spec), {BASE + 5: [(BASE, BASE + 9)]})

    def test_overlap_duplicate_and_unsorted_ranges(self):
        for rows in ([row(), row()], [row(), row(BASE + 5, BASE + 9)],
                     [row(BASE + 8, BASE + 9), row(BASE, BASE + 5)]):
            spec = family()
            spec['owned'][0]['body_ranges'] = rows
            self.reject(spec, 'sorted and nonoverlapping')

    def test_adjacent_ranges_are_valid_and_cover_existing_root(self):
        spec = family()
        spec['owned'][0]['body_ranges'] = [row(BASE, BASE + 5), row(BASE + 5, BASE + 9)]
        self.assertEqual(owned_ranges.resolve_owned_ranges(spec),
                         {BASE: [(BASE, BASE + 5), (BASE + 5, BASE + 9)]})

    def test_discontiguous_ranges_are_valid_when_no_corpus_bytes_omitted(self):
        self.corpus[BASE]['ranges'] = [[BASE, BASE + 5], [BASE + 8, BASE + 9]]
        spec = family()
        spec['owned'][0]['body_ranges'] = [row(BASE, BASE + 5), row(BASE + 8, BASE + 9)]
        self.assertEqual(len(owned_ranges.resolve_owned_ranges(spec)[BASE]), 2)

    def test_cannot_shrink_known_body_to_reduce_coverage(self):
        spec = family()
        spec['owned'][0]['body_ranges'] = [row(BASE, BASE + 5), row(BASE + 8, BASE + 9)]
        self.reject(spec, 'omit bytes already owned')

    def test_body_and_inline_interval_are_mutually_exclusive(self):
        spec = family()
        spec['owned'][0]['interval_end'] = hex(BASE + 9)
        self.reject(spec, 'mutually exclusive')

    def test_noncanonical_and_alternate_program_rejected(self):
        for change in ({'abi': 'legacy'}, {'program': 'synthetic'}):
            self.reject({**family(), **change}, 'canonical pinned original')

    def test_nonexecutable_or_unbacked_bytes_rejected(self):
        self.reference.text = (BASE, BASE + 8)
        self.reject(family(), 'executable text')
        self.reference.text = (BASE, BASE + 64)
        self.reference.sections[0].data = CODE[:8]
        self.reject(family(), 'not backed')

    def test_owned_entries_cannot_overlap_new_body(self):
        spec = family()
        spec['owned'].append(dict(address=hex(BASE + 5), interval_end=hex(BASE + 8)))
        self.reject(spec, 'owned bodies.*overlap')
        spec['owned'].reverse()
        self.reject(spec, 'owned bodies.*overlap')

    def test_old_intervals_and_corpus_resolution_do_not_read_binary(self):
        old = family(entries=[dict(address=hex(BASE)),
                              dict(address=hex(BASE + 16), interval_end=hex(BASE + 20)),
                              dict(address=hex(BASE + 32))])
        self.assertEqual(owned_ranges.resolve_owned_ranges(old),
                         {BASE: [(BASE, BASE + 9)], BASE + 16: [(BASE + 16, BASE + 20)], BASE + 32: []})
        self.assertEqual(owned_ranges.body_range_errors(old), [])
        self.loader.assert_not_called()

    def test_cross_family_overlap_with_distinct_roots(self):
        second = family('other', [dict(address=hex(BASE + 5), interval_end=hex(BASE + 8))])
        errors = owned_ranges.canonical_overlap_errors([family(), second])
        self.assertEqual(len(errors), 1)
        self.assertIn('canonical bodies overlap', errors[0])
        self.assertIn('[0x401005, 0x401008)', errors[0])

    def test_cross_family_adjacent_ranges_and_legacy_overlap_permitted(self):
        adjacent = family('adjacent', [dict(address=hex(BASE + 9), interval_end=hex(BASE + 12))])
        legacy = {**family('legacy'), 'abi': 'legacy'}
        self.assertEqual(owned_ranges.canonical_overlap_errors([family(), adjacent, legacy]), [])

    def test_numeric_duplicate_roots_rejected_even_without_known_range(self):
        a = family('a', [dict(address='0x401020')])
        b = family('b', [dict(address='0x00401020')])
        self.assertIn('canonical root', owned_ranges.canonical_overlap_errors([a, b])[0])

    def test_manifest_runs_semantic_checks_and_rejects_incomplete_guest_contract(self):
        spec = family()
        spec['owned'][0]['body_ranges'][0]['sha256'] = '0' * 64
        spec['owned'][0]['attached_entries'] = []
        spec['oracle']['guest_graph'] = {}
        errors = manifest.validate(spec)
        self.assertTrue(any('SHA-256 mismatch' in e for e in errors))
        self.assertTrue(any('invalid guest contract' in e for e in errors))
        self.assertTrue(any('missing version' in e for e in errors))

    def test_manifest_accepts_only_valid_ownership_extension(self):
        self.assertEqual(manifest.validate(family()), [])

    def test_manifest_check_all_invokes_canonical_interval_check(self):
        specs = {'a': family('a'), 'b': family('b', [dict(address=hex(BASE + 5), interval_end=hex(BASE + 8))])}
        with patch.object(manifest, 'load_all', return_value=specs), patch.object(manifest, 'validate', return_value=[]):
            result = manifest.check_all()
        self.assertTrue(any('canonical bodies overlap' in e for e in result['errors']))

    def test_only_named_harness_transport_is_exempt_from_family_inventory(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Sources').mkdir()
            (root / 'Sources/ClawGuestTransfer.cpp').touch()
            (root / 'Sources/UnknownSupport.cpp').touch()
            with patch.object(manifest, 'ROOT', root), patch.object(manifest, 'load_all', return_value={}):
                result = manifest.check_all()
        self.assertEqual(result['errors'], ['Sources/UnknownSupport.cpp: belongs to no family'])

    def test_spec_lint_checks_intervals_not_only_addresses(self):
        import json
        import tempfile
        from pathlib import Path
        spec = family()
        spec['owned'][0].update(convention='cdecl', argc=0, returns='u32')
        other = family('other', [dict(address=hex(BASE + 5), interval_end=hex(BASE + 8))])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example.json'
            path.write_text(json.dumps(spec))
            with patch.object(manifest, 'load_all', return_value={'other': other}), \
                 patch.object(speclint.index, 'returned_bytes', return_value={0}), \
                 patch.object(speclint.index, 'call_targets', return_value={}), \
                 patch.object(speclint.index, 'indirect_call_sites', return_value=[]):
                result = speclint.lint(path)
        self.assertTrue(any('canonical bodies overlap' in e for e in result['errors']))


if __name__ == '__main__':
    unittest.main()
