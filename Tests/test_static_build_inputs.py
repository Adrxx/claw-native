"""V9 dependency perturbations using the retained original capture and real manifests.

These bounded integration tests need the frozen v9 capsule, but never compile or
execute native code. Mutations affect only a temporary copy of selected inputs.
"""
import copy
import gzip
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.claw import milestone as m
from tools.claw import static_build_inputs as s

ROOT = Path(__file__).resolve().parents[1]


class StaticFinalBuildInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A staging launcher may provide the unchanged checkout and proposed files.
        cls.original_root = getattr(cls, 'checkout_root', ROOT)
        cls.overlay = getattr(cls, 'proposed_root', None)
        root = cls.original_root
        provenance = root / m.STATIC_FINAL_REFERENCE
        if not provenance.exists():
            raise unittest.SkipTest('frozen original v9 capsule is required')
        p = json.loads(provenance.read_text())
        cls.clean = json.load(gzip.open(provenance.parent / 'final144-clean.json.gz', 'rt'))
        cls.manifests = {str(f.relative_to(root)): f.read_bytes() for f in (root / 'Tests/families').glob('*.json')}
        cls.exclusions = json.loads((root / 'tools/claw/app_exclude.json').read_text())
        rows = s.gen_project.canonical_inventory([json.loads(data)for data in cls.manifests.values()],cls.exclusions,root=root)[2]
        selected = s.select_final_build(cls.manifests, rows, cls.clean)
        cls.temp = tempfile.TemporaryDirectory(prefix='claw-static-final-inventory-')
        cls.root = Path(cls.temp.name)
        references = m.static_final_archived_producers(p, root)
        references[m.STATIC_FINAL_REFERENCE] = m.STATIC_FINAL_REFERENCE_SHA256
        references['Original/claw10/CLAW.EXE'] = m.ORIGINAL_SHA256
        references.update({str(Path(m.STATIC_FINAL_REFERENCE).parent / row['path']): row['sha256'] for row in p['profiles']})
        names = set(references) | set(cls.manifests) | set(selected['cpp']) | set(selected['swift']) | set(s.RECIPE_INPUTS) | {'Tests/NativeStaticStartup/Bridge.h'}
        names.update(str(f.relative_to(root)) for f in (root / 'Sources').rglob('*') if f.suffix in ('.h', '.hpp') and f != root / 'Sources/ClawCanonicalDispatch.h')
        for name in names:
            source = cls.overlay / name if cls.overlay is not None and (cls.overlay / name).exists() else root / name
            target = cls.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        # Unselected source contents are never read or compiled here, but the
        # all-manifest validator still requires their actual path membership.
        for raw in cls.manifests.values():
            for name in json.loads(raw).get('sources', []):
                target=cls.root/name
                if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'// unselected validation-only fixture\n')
        cls.baseline = s.final_input_inventory(cls.root)
        cls.build = s.load_final_build(cls.root)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    def changed_file(self, name, contents):
        path = self.root / name
        before = path.read_bytes()
        try:
            path.write_bytes(contents)
            return s.final_input_inventory(self.root)
        finally:
            path.write_bytes(before)

    def test_compiled_sources_headers_manifests_and_recipe_imports_invalidate(self):
        selected = self.build['selection']
        paths = [selected['cpp'][0], selected['swift'][0], self.build['membership']['headers'][0],
                 selected['manifests'][0], 'Tests/NativeStaticStartup/Bridge.h', *s.RECIPE_INPUTS]
        for name in dict.fromkeys(paths):
            with self.subTest(path=name):
                self.assertNotEqual(self.changed_file(name, (self.root / name).read_bytes() + b'\n'), self.baseline)

    def test_original_shard_metadata_and_archival_drift_fail_closed(self):
        paths = ['Original/claw10/CLAW.EXE', m.STATIC_FINAL_REFERENCE,
                 'work/native-static-startup-check/frozen-v9/final144-clean.json.gz',
                 'work/native-static-startup-check/frozen-v9/final144-message-return-zero.json.gz',
                 'work/native-static-startup-check/frozen-v9/provenance-metadata-addendum-v1.json']
        p = json.loads((self.root / m.STATIC_FINAL_REFERENCE).read_text())
        paths.append(str(Path(m.STATIC_FINAL_REFERENCE).parent / next(iter(p['frozenInputInventory'].values()))['path']))
        for name in paths:
            with self.subTest(path=name), self.assertRaises(ValueError):
                self.changed_file(name, (self.root / name).read_bytes() + b'\n')

    def test_selected_manifest_source_membership_changes(self):
        name = 'Tests/families/static_final_records.json'
        data = json.loads((self.root / name).read_text())
        extra = self.root / 'Sources/StaticFinalInventoryExtra.cpp'
        extra.write_text('// additional selected source\n')
        try:
            data['sources'].append(str(extra.relative_to(self.root)))
            changed = self.changed_file(name, json.dumps(data).encode())
            self.assertNotEqual(changed['@static-final/selected-build-membership'], self.baseline['@static-final/selected-build-membership'])
            self.assertIn(str(extra.relative_to(self.root)), changed)
        finally:
            extra.unlink()

    def test_header_membership_add_remove_and_namespace_initializer(self):
        for name in ('Sources/StaticFinalInventoryExtra.hpp', 'tools/__init__.py'):
            path = self.root / name
            path.write_text('// membership input\n' if name.endswith('.hpp') else '# namespace initializer\n')
            try:
                changed = s.final_input_inventory(self.root)
                self.assertNotEqual(changed['@static-final/selected-build-membership'], self.baseline['@static-final/selected-build-membership'])
                self.assertIn(name, changed)
            finally:
                path.unlink()
        header = self.root / self.build['membership']['headers'][0]
        contents = header.read_bytes(); header.unlink()
        try:
            self.assertNotEqual(s.final_input_inventory(self.root), self.baseline)
        finally:
            header.write_bytes(contents)

    def test_admission_exclusion_removal_and_collision_reject(self):
        name = 'Tests/families/static_final_records.json'
        for change in ('admission', 'remove', 'exclude', 'collision'):
            manifests = dict(self.manifests); exclusions = copy.deepcopy(self.exclusions)
            data = json.loads(manifests[name])
            if change == 'admission':
                data['evidence']['level'] = 'draft'; manifests[name] = json.dumps(data).encode()
            elif change == 'remove':
                del manifests[name]
            elif change == 'exclude':
                exclusions.append(dict(path=data['sources'][0], reason='test selected exclusion'))
            else:
                duplicate = copy.deepcopy(data); duplicate['id'] = 'static_inventory_collision'
                duplicate['sources'] = ['Sources/StaticInventoryCollision.cpp']
                duplicate['oracle']['entry'] = 'claw_static_inventory_collision_entry'
                manifests['Tests/families/static_inventory_collision.json'] = json.dumps(duplicate).encode()
            collision=self.root/'Sources/StaticInventoryCollision.cpp'
            if change=='collision':collision.write_text('// present so duplicate address is the rejected condition\n')
            try:
                with self.subTest(change=change), self.assertRaises((ValueError, KeyError, AssertionError)) as caught:
                    rows=s.gen_project.canonical_inventory([json.loads(data)for data in manifests.values()],exclusions,root=self.root)[2]
                    s.select_final_build(manifests, rows, self.clean)
                if change=='collision':self.assertIn('duplicate or zero owned address',str(caught.exception))
            finally:
                if collision.exists():collision.unlink()

    def test_unrelated_valid_family_source_and_git_membership_are_stable(self):
        source = self.root / 'Sources/StaticInventoryUnrelated.cpp'
        manifest = self.root / 'Tests/families/inventory_unrelated.json'
        source.write_text('// unrelated compiled elsewhere\n')
        manifest.write_text(json.dumps(dict(id='inventory_unrelated', abi='canonical',
            sources=[str(source.relative_to(self.root))], evidence=dict(level='admitted'),
            oracle=dict(kind='clawparity', entry='claw_inventory_unrelated_entry'),
            owned=[dict(address='0x600010', convention='cdecl', argc=0, returns='u32')])))
        git = self.root / '.git'; git.mkdir(); (git / 'index').write_bytes(b'changed unrelated Git membership')
        try:
            with patch.object(m, 'project_membership', side_effect=AssertionError('v9 does not read Git')):
                self.assertEqual(m.input_inventory(self.root, ['static_startup_final']), self.baseline)
        finally:
            source.unlink(); manifest.unlink(); shutil.rmtree(git)

    def test_new_observed_static_owner_changes_selection(self):
        manifests = dict(self.manifests); reference = copy.deepcopy(self.clean)
        reference['entries'].append(dict(function=0x600020))
        manifests['Tests/families/static_inventory_observed.json'] = json.dumps(dict(
            id='static_inventory_observed', abi='canonical', sources=['Sources/StaticInventoryObserved.cpp'],
            evidence=dict(level='admitted'), oracle=dict(kind='clawparity', entry='claw_static_inventory_observed_entry'),
            owned=[dict(address='0x600020', convention='cdecl', argc=0, returns='u32')])).encode()
        extra=self.root/'Sources/StaticInventoryObserved.cpp';extra.write_text('// observed selected member\n')
        try:
            rows=s.gen_project.canonical_inventory([json.loads(data)for data in manifests.values()],self.exclusions,root=self.root)[2]
            selected = s.select_final_build(manifests, rows, reference)
        finally:extra.unlink()
        self.assertIn('Sources/StaticInventoryObserved.cpp', selected['cpp'])
        self.assertNotEqual(selected['registry'], self.build['selection']['registry'])

    def test_validation_uses_supplied_root_and_rejects_aliases_and_escape(self):
        name='Sources/ClawTokenHeap.swift'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaisesRegex(ValueError,'missing or symlink'):
                s.gen_project.checked_source(name,('.swift',),root=root)
            path=root/name;path.parent.mkdir(parents=True);path.write_text('// only in supplied root\n')
            self.assertEqual(s.gen_project.checked_source(name,('.swift',),root=root),name)
            path.unlink();path.symlink_to(self.original_root/name)
            with self.assertRaisesRegex(ValueError,'missing or symlink'):
                s.gen_project.checked_source(name,('.swift',),root=root)
            with self.assertRaisesRegex(ValueError,'invalid source path'):
                s.gen_project.checked_source('Sources/../ClawTokenHeap.swift',('.swift',),root=root)
        self.assertEqual(s.gen_project.checked_source(name,('.swift',)),name)

    def test_snapshot_reconstructs_same_dependency_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, data in self.build['inputs'].items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            rebuilt = s.load_final_build(root)
            self.assertEqual(rebuilt, self.build)

    def test_default_generator_and_project_inventory_remain_unchanged(self):
        import importlib.util
        # Read the checked-out baseline only when testing an ignored proposal.
        if self.overlay is None:return
        spec=importlib.util.spec_from_file_location('tools.claw.inventory_legacy_baseline',self.original_root/'tools/claw/milestone.py')
        baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
        self.assertEqual(m.input_inventory(self.original_root,['project']),baseline.input_inventory(self.original_root,['project']))
        manifests=[json.loads(data)for data in self.manifests.values()]
        self.assertEqual(s.gen_project.canonical_inventory(manifests,self.exclusions),
                         s.gen_project.canonical_inventory(manifests,self.exclusions,root=self.original_root))

    def test_retained_snapshot_dependencies_and_metadata_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,data in self.build['inputs'].items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            self.assertEqual(s.final_input_inventory(root),self.baseline)
            # Changes in the original checkout cannot supply missing retained bytes.
            for name in (self.build['selection']['cpp'][0],self.build['membership']['headers'][0]):
                path=root/name;data=path.read_bytes();path.write_bytes(data+b'\n')
                self.assertNotEqual(s.final_input_inventory(root),self.baseline);path.write_bytes(data)
            provenance=json.loads((root/m.STATIC_FINAL_REFERENCE).read_text())
            self.assertEqual(len(m.static_final_archived_producers(provenance,root)),105)
            for filename in m.STATIC_FINAL_METADATA:
                path=root/Path(m.STATIC_FINAL_REFERENCE).parent/filename;data=path.read_bytes();path.write_bytes(data+b'\n')
                with self.subTest(metadata=filename),self.assertRaises(ValueError):m.static_final_archived_producers(provenance,root)
                path.write_bytes(data)
            missing=root/self.build['selection']['cpp'][0];missing.unlink()
            with self.assertRaises(ValueError):s.load_final_build(root)

    def test_legacy_and_mixed_selection_never_use_scoped_inventory(self):
        with patch.object(s, 'final_input_inventory', side_effect=AssertionError('v9-only scope entered')):
            for checks in (['static_startup_list'], ['project'], ['startup_prefix'], ['project', 'static_startup_final']):
                # A missing root fails through the old generic required-input path.
                with self.subTest(checks=checks), self.assertRaises((m.PrerequisiteError, FileNotFoundError)):
                    m.input_inventory(self.root / 'missing', checks)


class StaticFinalMeasuredMetadataTests(unittest.TestCase):
    """Counter/schema tests only; synthetic mode flags are never build evidence."""
    @classmethod
    def setUpClass(cls):
        report=ROOT/'work/coordination/static-final-full-optimized-report.json'
        if not report.exists():raise unittest.SkipTest('measured v9 optimized report is required')
        cls.report=json.loads(report.read_text())

    def metadata_fixture(self):
        # Exercise the envelope validator; static_evidence still requires genuine
        # independently compiled sanitized/optimized artifacts and byte snapshots.
        sanitized=copy.deepcopy(self.report);sanitized.update(sanitized=True,optimized=False)
        return dict(status='pass',command='static-startup-final',modes=[sanitized,copy.deepcopy(self.report)])

    def test_measured_counts_and_scope_envelope(self):
        m.validate_static_certificate(self.metadata_fixture(),9)

    def test_scope_counter_and_version_drift_rejected(self):
        for kind in ('physical','scope','version','profile-order'):
            payload=self.metadata_fixture();report=payload['modes'][0]
            if kind=='physical':report['profiles'][0]['physical_events']-=1
            elif kind=='scope':report['profiles'][0]['reference_only_physical_event_indices']=[0]
            elif kind=='version':report['reference_version']=8
            else:report['profiles'][0],report['profiles'][1]=report['profiles'][1],report['profiles'][0]
            with self.subTest(kind=kind),self.assertRaises(ValueError):m.validate_static_certificate(payload,9)


if __name__ == '__main__':
    unittest.main()
