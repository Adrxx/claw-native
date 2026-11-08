"""Progress must not promote draft declarations or source hints into proof."""
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from tools.claw import progress_page, status


def family(evidence='admitted', integration='compiled', address=0x401000):
    return {'title': 'Synthetic family', 'abi': 'canonical', 'sources': [],
            'owned': [{'address': hex(address)}], 'oracle': {'commands': []},
            'evidence': {'level': evidence}, 'integration': {'level': integration}}


class ProgressEvidenceTests(unittest.TestCase):
    def build(self, manifests, referenced=(), reviewed=None):
        with ExitStack() as stack:
            stack.enter_context(patch.object(progress_page.manifest, 'load_all', return_value=manifests))
            stack.enter_context(patch.object(progress_page.index, 'functions', return_value={
                0x401000: {'size': 100}, 0x401100: {'size': 200}, 0x501000: {'size': 300}}))
            stack.enter_context(patch.object(progress_page, 'swift_addresses', return_value=set(referenced)))
            stack.enter_context(patch.object(progress_page, 'reviewed_class_owners', return_value=reviewed or {}))
            stack.enter_context(patch.object(progress_page.sync, 'latest_baseline', return_value=('2026-01-01', {})))
            stack.enter_context(patch.object(progress_page.glob, 'glob', return_value=[]))
            stack.enter_context(patch.object(progress_page, 'class_addresses', return_value={'Synthetic': 0x401000}))
            stack.enter_context(patch.object(progress_page, 'level_classes', return_value=[{'level': 1, 'counts': {'Synthetic': 2}}]))
            return progress_page.build()

    def reviewed(self, manifests, sources):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, text in sources.items():
                path = Path(directory) / name
                path.write_text(text)
                paths.append(path)
            return progress_page.reviewed_class_owners(manifests, paths=paths)

    def test_reviewed_class_owner_requires_address_in_same_source(self):
        manifests = {'wired': family(integration='elected')}
        owners = self.reviewed(manifests, {
            'Annotated.swift': '// claw-progress-class-owner: wired 0x401100 0x401200\nlet callback = 0x401100\n',
            'Other.swift': 'let callback = 0x401200\n',
        })
        self.assertEqual(owners, {0x401100: 'wired'})

    def test_marker_comment_alone_cannot_establish_class_owner(self):
        owners = self.reviewed({'wired': family(integration='elected')}, {
            'Annotated.swift': '// claw-progress-class-owner: wired 0x401100\n'
                               '// claw-progress-class-owner: wired 0x401100\n',
        })
        self.assertEqual(owners, {})

    def test_comments_and_strings_cannot_back_reviewed_class_metadata(self):
        snippets = {
            'line_comment': '// callback 0x401100\n',
            'block_comment': '/* callback 0x401100 */\n',
            'nested_block_comment': '/* outer /* inner */ callback 0x401100 */\n',
            'quoted_string': 'let label = "callback 0x401100"\n',
            'escaped_quote': 'let label = "callback \\" 0x401100"\n',
            'raw_string': 'let label = ##"callback " 0x401100"##\n',
            'multiline_string': 'let label = """\ncallback 0x401100\n"""\n',
            'raw_multiline_string': 'let label = #"""\ncallback " 0x401100\n"""#\n',
        }
        for name, snippet in snippets.items():
            with self.subTest(name=name):
                owners = self.reviewed({'wired': family(integration='elected')}, {
                    'Annotated.swift': '// claw-progress-class-owner: wired 0x401100\n' + snippet,
                })
                self.assertEqual(owners, {})

    def test_quotes_in_comments_do_not_swallow_later_code_backing(self):
        for comment in ('// an unmatched "\n', '/* an unmatched " */\n',
                        '/* outer " /* nested """ */ still comment */\n'):
            with self.subTest(comment=comment):
                owners = self.reviewed({'wired': family(integration='elected')}, {
                    'Annotated.swift': '// claw-progress-class-owner: wired 0x401100\n'
                                       + comment + 'let callback = 0x401100\n',
                })
                self.assertEqual(owners, {0x401100: 'wired'})

    def test_reviewed_class_owner_requires_evidence_and_host_integration(self):
        for evidence, integration, accepted in [
            ('admitted', 'elected', True),
            ('legacy-frozen', 'live', True),
            ('provisional', 'elected', True),
            ('none', 'live', False),
            ('none', 'elected', False),
            ('admitted', 'compiled', False),
        ]:
            with self.subTest(evidence=evidence, integration=integration):
                owners = self.reviewed({'candidate': family(evidence, integration)}, {
                    'Annotated.swift': '// claw-progress-class-owner: candidate 0x401100\nlet callback = 0x401100\n',
                })
                self.assertEqual(owners, {0x401100: 'candidate'} if accepted else {})
        self.assertEqual(self.reviewed({}, {
            'Annotated.swift': '// claw-progress-class-owner: absent 0x401100\nlet callback = 0x401100\n',
        }), {})

    def test_conflicting_reviewed_class_owners_reject_only_conflicting_address(self):
        manifests = {'first': family(integration='elected'), 'second': family(integration='live')}
        sources = {
            'First.swift': '// claw-progress-class-owner: first 0x401100 0x401200\n'
                           'let callbacks = [0x401100, 0x401200]\n',
            'Second.swift': '// claw-progress-class-owner: second 0x401100\nlet callback = 0x401100\n',
        }
        self.assertEqual(self.reviewed(manifests, sources), {0x401200: 'first'})
        self.assertEqual(self.reviewed(manifests, dict(reversed(list(sources.items())))), {0x401200: 'first'})

    def test_duplicate_same_family_annotations_are_allowed(self):
        owners = self.reviewed({'wired': family(integration='elected')}, {
            name: '// claw-progress-class-owner: wired 0x401100\nlet callback = 0x401100\n'
            for name in ('First.swift', 'Second.swift')
        })
        self.assertEqual(owners, {0x401100: 'wired'})

    def test_class_family_preserves_manifest_ownership_precedence(self):
        address = 0x401100
        reviewed = {address: 'reviewed'}
        self.assertEqual(progress_page.class_family(address, {address: 'owner'}, {address: 'draft'}, reviewed), 'owner')
        self.assertEqual(progress_page.class_family(address, {}, {address: 'draft'}, reviewed), 'draft')
        self.assertEqual(progress_page.class_family(address, {}, {}, reviewed), 'reviewed')
        self.assertIsNone(progress_page.class_family(0x401200, {}, {}, reviewed))
        self.assertIsNone(progress_page.class_family(None, {}, {}, reviewed))

    def test_reviewed_metadata_promotes_classes_without_function_or_byte_ownership(self):
        manifests = {'wired': family(integration='elected', address=0x401100)}
        before = self.build(manifests, referenced=[0x401000])
        after = self.build(manifests, referenced=[0x401000], reviewed={0x401000: 'wired'})
        self.assertEqual(after['classes'][0]['family'], 'wired')
        self.assertEqual(after['classes'][0]['status'], 'wired')
        self.assertTrue(after['classes'][0]['recovered'])
        for key in ('totals', 'program', 'families'):
            self.assertEqual(before[key], after[key])
        with patch.object(progress_page.index, 'functions', return_value={0x401000: {'size': 100}, 0x401100: {'size': 200}}):
            self.assertEqual(progress_page.ownership(manifests), {0x401100: 'wired'})

    def test_reviewed_metadata_does_not_promote_declared_draft_class(self):
        manifests = {'draft': family('none', 'compiled'),
                     'wired': family(integration='live', address=0x401100)}
        data = self.build(manifests, reviewed={0x401000: 'wired'})
        self.assertEqual(data['classes'][0]['family'], 'draft')
        self.assertEqual(data['classes'][0]['status'], 'draft')
        self.assertFalse(data['classes'][0]['recovered'])

    def test_draft_cannot_advance_counts_or_denominator(self):
        manifests = {'implemented': family()}
        before = self.build(manifests)
        manifests['draft'] = family('none', 'elected', 0x401100)
        manifests['library_draft'] = family('none', 'compiled', 0x501000)
        after = self.build(manifests)
        self.assertEqual(before['totals'], after['totals'])
        self.assertEqual(after['totals']['recovered_bytes'], 100)
        draft_function = next(f for f in after['program'] if f[0] == 0x401100)
        self.assertEqual(draft_function[2], 5)
        self.assertEqual(after['families'][draft_function[3]]['id'], 'draft')

    def test_none_cannot_use_case_label_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Synthetic.cpp').write_text('case 0x401000: break;')
            spec = family('none')
            spec.update(owned=[], sources=['Synthetic.cpp'])
            with patch.object(progress_page, 'ROOT', root), patch.object(progress_page.index, 'functions', return_value={0x401000: {'size': 100}}):
                self.assertEqual(progress_page.ownership({'draft': spec}), {})
                self.assertEqual(progress_page.ownership({'draft': spec}, include_drafts=True), {})
                spec['evidence']['level'] = 'legacy-frozen'
                self.assertEqual(progress_page.ownership({'legacy': spec}), {0x401000: 'legacy'})

    def test_literal_reference_does_not_prove_live(self):
        data = self.build({'implemented': family()}, referenced=[0x401000])
        self.assertEqual(data['classes'][0]['status'], 'referenced')
        self.assertEqual(data['totals']['live_bytes'], 0)
        self.assertEqual(progress_page.class_status(0x401000, None, True), 'referenced')

    def test_elected_live_and_draft_remain_distinct(self):
        for integration, expected, program_state, live_bytes in [('elected', 'wired', 2, 0), ('live', 'live', 4, 100)]:
            data = self.build({'implemented': family(integration=integration)})
            self.assertEqual(data['classes'][0]['status'], expected)
            self.assertEqual(data['program'][0][2], program_state)
            self.assertEqual(data['totals']['live_bytes'], live_bytes)
        data = self.build({'draft': family('none', 'live')}, referenced=[0x401000])
        self.assertEqual(data['classes'][0]['status'], 'draft')
        self.assertFalse(data['classes'][0]['recovered'])
        self.assertEqual(data['totals']['recovered_bytes'], 0)

    def test_status_share_excludes_draft_and_preserves_legacy_measurement(self):
        legacy = family('legacy-frozen')
        legacy['evidence'].update(baseline={'status': 'pass', 'date': '2026-01-01'}, gate={
            'kind': 'legacy-measurement', 'salted': 'pass', 'owned': 1, 'directly_called': 1,
            'bytes_owned': 100, 'bytes_executed': 90, 'coverage': .9})
        manifests = {'legacy': legacy, 'provisional': family('provisional', address=0x401100)}
        functions = {0x401000: {'size': 100}, 0x401100: {'size': 200}, 0x401200: {'size': 400}}
        with patch.object(status.index, 'functions', return_value=functions), patch.object(status.manifest, 'load_all', return_value=manifests):
            before, _ = status.render()
            manifests['draft'] = family('none', address=0x401200)
            after, _ = status.render()
        def section(text, name):
            return text.split('## ' + name + '\n', 1)[1].split('\n## ', 1)[0]
        for name in ('Share of the original recovered', 'Latest plain re-run of the legacy comparisons', 'Measurement of the legacy families'):
            self.assertEqual(section(before, name), section(after, name))
        self.assertIn('2 original functions', section(after, 'Share of the original recovered'))
        self.assertIn('300 bytes', section(after, 'Share of the original recovered'))


if __name__ == '__main__':
    unittest.main()
