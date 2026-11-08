"""Independent synthetic controls for bounded milestone evidence (no game assets)."""
import copy
import json
import os
import signal
import time
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.claw import milestone as m


def project_certificate():
    return dict(status='pass', command='project-check', in_sync=True,
                compiled_cpp=1, compiled_swift=2, bridged_headers=1)


def startup_certificate():
    profiles = [dict(name=name, completed=False, callbacks=2, registry_callbacks=1,
                     stop=dict(diagnostic='missingDependency', address='0x1234', code=5))
                for name in ('empty', 'options', 'user', 'empty-user', 'bytes', 'boundaries')]
    return dict(schema=1, status='pass', command='native-application-pregraphics',
                scope='startup-prefix', profiles=profiles, source_callbacks=12,
                registry_callbacks=6, reference_sha256='a' * 64, limits=['finite prefix only'])


def manager_certificate():
    return dict(schema=1, status='pass', command='native-mfc-tls-manager-source',
                sanitized=True, optimized=False, reference_sha256='a' * 64,
                cache_key='b' * 64, replay=dict(status='pass', profiles=9, roots=119,
                physical_events=271, child_entries=13, native_controls=65, assertions=6182))


def values_certificate():
    return dict(schema=1, status='pass', command='native-mfc-tls-values-source',
                sanitized=True, optimized=False, reference_sha256='a' * 64,
                cache_key='b' * 64, replay=dict(status='pass', profiles=11, roots=55,
                physical_events=399, observed_entries=366, reference_entries=410,
                reference_only_entries=44, native_controls=144, assertions=29371,
                unobserved_sites=[dict(function=0x503167, return_pc=0x5033ce,
                    profile='synthetic', root_step=i, frame=0x02007fec) for i in range(44)]))


def module_certificate():
    sites = [dict(function=0x503167 if i < 18 else 0x502e47,
                  return_pc=0x5033ce if i < 18 else 0x502ea8,
                  profile='synthetic', root_step=i, frame=0x02007fec) for i in range(28)]
    return dict(schema=1, status='pass', command='native-mfc-cold-module',
                sanitized=True, optimized=False, reference_sha256=m.MODULE_REFERENCE_SHA256,
                cache_key='b' * 64, replay=dict(status='pass', profiles=29, roots=30,
                physical_events=336, observed_entries=311, reference_entries=339,
                reference_only_entries=28, native_controls=83, original_assertions=71668,
                assertions=71751, catch_executed=False, application_getter_executed=False,
                unobserved_sites=sites))


def application_thread_certificate():
    pairs = [(0x503167, 0x5033ce)] * 15 + [(0x502e47, 0x502ea8)] * 10 + [(0x50210b, 0x502329)] * 5 + [(0x4f5e89, 0x502137)] * 5 + [(0x4f5e89, 0x502145)] * 5 + [(0x4f5133, 0x502153)] * 5
    sites = [dict(function=f, return_pc=pc, profile='synthetic', root_step=i,
                  frame=0x02007fec) for i, (f, pc) in enumerate(pairs)]
    return dict(schema=1, status='pass', command='native-mfc-application-thread-source',
                sanitized=True, optimized=False, reference_sha256=m.APPLICATION_THREAD_REFERENCE_SHA256,
                cache_key='b' * 64, replay=dict(status='pass', profiles=10, roots=22,
                physical_events=267, observed_entries=255, reference_entries=300,
                reference_only_entries=45, native_controls=166, original_assertions=68954,
                assertions=69120, bridges=11, catch_executed=False, application_getter_executed=True,
                whole_cwinapp_executed=False, unobserved_sites=sites))


def application_object_certificate():
    triples = [(0x4f6a9a, 0x503526, True)] * 62 + [(0x50354d, 0x50353e, True)] * 62
    triples += [(0x503167, 0x5033ce, True)] * 74 + [(0x502e47, 0x502ea8, True)] * 40
    triples += [(0x4f5e89, 0x502137, True)] * 26 + [(0x4f5e89, 0x502145, True)] * 26
    triples += [(0x4f5133, 0x502153, True)] * 26 + [(0x50210b, 0x502329, False)] * 26
    sites = [dict(function=f, return_pc=pc, original_defined=original, profile=f'site-{i}',
                  root_step=0, frame=0x2007fd0, reason='owned body internal to factory')
             for i, (f, pc, original) in enumerate(triples)]
    missing = [(f'allocation-null-at-{i}', pc, frame) for i, pc, frame in (
        (2, 0x5030af, 0x2007eac), (3, 0x502f9c, 0x2007ea4), (4, 0x502f9c, 0x2007ea8),
        (5, 0x503205, 0x2007eb4), (6, 0x502f9c, 0x2007e80), (7, 0x502f9c, 0x2007ea8),
        (8, 0x503205, 0x2007eb8))]
    missing += [('tls-index-exhausted-original-failure', 0x502fea, 0x2007ec0)]
    return dict(schema=1, status='pass', command='native-mfc-application-object',
                sanitized=True, optimized=False, complete_reference=True,
                reference_sha256=m.APPLICATION_OBJECT_REFERENCE_SHA256, cache_key='c' * 64,
                replay=dict(status='pass', profiles=61, roots=62, returned_roots=21, stopped_roots=41,
                            physical_events=1358, reference_physical_events=1366, observed_entries=1356,
                            reference_only_entries=316, native_unobserved_entries=26, reference_entries=1698,
                            missing_native_prefixes=8, later_original_physical_events=8, later_original_entries=0,
                            original_assertions=571962, native_controls=165, assertions=572127,
                            whole_cwinapp_executed=True, catch_executed=False, unobserved_sites=sites,
                            missing_native_sites=[dict(profile=n, function=0x4f50fd, return_pc=pc,
                                                       frame=frame, root_step=0) for n, pc, frame in missing]))


class MilestoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Makefile').write_text('synthetic fixture\n')
        (self.root / 'Sources').mkdir()
        (self.root / 'Sources/input.swift').write_text('// input\n')
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.toolchain = {'compiler': 'synthetic-v1'}

    def command(self, code):
        return patch.object(m, 'command_for', return_value=[sys.executable, '-c', code])

    def run_project(self, **kwargs):
        with self.command('print(' + repr(json.dumps(project_certificate())) + ')'):
            return m.run_checks(['project'], root=self.root, toolchain=self.toolchain, **kwargs)

    def fresh_status(self, record):
        with patch.object(m, 'toolchain_identity', return_value=self.toolchain):
            return m.status(record['record_path'], root=self.root)

    def test_malformed_own_record_shape_raises_value_error(self):
        record = self.run_project()
        path = Path(record['record_path'])
        path.write_text('[]')
        with self.assertRaises(ValueError):
            self.fresh_status(record)
        with self.assertRaises(ValueError):
            self.run_project(resume=path)

    def test_failed_parent_cleans_its_still_running_child(self):
        marker = self.root / 'child-survived'
        child_code = ('import time; from pathlib import Path; time.sleep(0.7); '
                      'Path(' + repr(str(marker)) + ').write_text("survived")')
        parent_code = ('import subprocess, sys; subprocess.Popen([sys.executable, "-c", ' +
                       repr(child_code) + ']); sys.exit(7)')
        launched = []
        real_popen = subprocess.Popen
        def capture(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            launched.append(process)
            return process
        try:
            with self.command(parent_code), patch.object(m.subprocess, 'Popen', side_effect=capture):
                result = m.execute_check('project', self.root, 5, root=self.root)
            self.assertEqual(result['exit_code'], 7)
            self.assertEqual(result['status'], 'failed')
            time.sleep(1)
            self.assertFalse(marker.exists(), 'failed checks must terminate their remaining child processes')
        finally:
            for process in launched:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)

    def test_selection_is_canonical_and_rejects_unknown(self):
        self.assertEqual(m.select_checks(['startup_prefix', 'project', 'project']), ['project', 'startup_prefix'])
        with self.assertRaises(ValueError):
            m.select_checks(['gameplay'])

    def test_environment_strips_all_caller_claw_controls(self):
        original = {'PATH': '/synthetic', 'CLAW_NATIVE_ASAN': '0', 'CLAW_EVIL_FLAGS': '-unsafe',
                    'CLAW_APPLICATION_PREGRAPHICS_CHECK_DIR': '/elsewhere',
                    'CLAW_APPLICATION_OBJECT_DIR': '/shared-stale', 'ASAN_OPTIONS': 'bad'}
        env = m.controlled_environment(original, self.root)
        self.assertEqual(original['CLAW_NATIVE_ASAN'], '0')
        self.assertNotIn('CLAW_EVIL_FLAGS', env)
        self.assertEqual(env['PATH'], '/synthetic')
        self.assertEqual(env['CLAW_NATIVE_ASAN'], '1')
        self.assertEqual(env['CLAW_NATIVE_JOBS'], '1')
        self.assertEqual(env['CLAW_NATIVE_OPTIMIZE'], '0')
        self.assertEqual(env['CLAW_APPLICATION_PREGRAPHICS_CHECK_DIR'], str(self.root.resolve()))
        self.assertIn('halt_on_error=1', env['UBSAN_OPTIONS'])
        object_dir = Path(env['CLAW_APPLICATION_OBJECT_DIR'])
        self.assertTrue(object_dir.is_absolute())
        self.assertEqual(object_dir.parent, self.root.resolve())
        second_env = m.controlled_environment(original, self.root / 'another-attempt')
        self.assertNotEqual(env['CLAW_APPLICATION_OBJECT_DIR'], second_env['CLAW_APPLICATION_OBJECT_DIR'])

    def test_inventory_content_and_toolchain_change_identity(self):
        first = m.input_inventory(self.root, ['project'])
        key = m.fingerprint(['project'], first, self.toolchain)
        (self.root / 'Sources/input.swift').write_text('// changed\n')
        second = m.input_inventory(self.root, ['project'])
        self.assertNotEqual(first, second)
        self.assertNotEqual(key, m.fingerprint(['project'], second, self.toolchain))
        self.assertNotEqual(key, m.fingerprint(['project'], first, {'compiler': 'synthetic-v2'}))
        with self.assertRaises(m.PrerequisiteError):
            m.input_inventory(self.root, ['source_graph'])

    def test_inventory_covers_native_gate_list_and_include_bytes(self):
        (self.root / 'scripts').mkdir()
        gate = self.root / 'scripts/native-gate-sources.txt'
        include = self.root / 'Sources/synthetic.inc'
        gate.write_text('Sources/input.swift\n')
        include.write_text('synthetic include bytes\n')
        first = m.input_inventory(self.root, ['project'])
        gate.write_text('Sources/other.swift\n')
        second = m.input_inventory(self.root, ['project'])
        self.assertNotEqual(first, second, 'gate source selection changes must invalidate evidence')
        include.write_text('new include bytes\n')
        third = m.input_inventory(self.root, ['project'])
        self.assertNotEqual(second, third, 'included source bytes must invalidate evidence')

    def test_inventory_covers_git_membership_without_byte_changes(self):
        def git(*args):
            subprocess.run(['git', *args], cwd=self.root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        git('init', '--quiet')
        git('add', 'Makefile', 'Sources/input.swift')
        first = m.input_inventory(self.root, ['project'])
        git('rm', '--cached', 'Sources/input.swift')
        self.assertEqual((self.root / 'Sources/input.swift').read_text(), '// input\n')
        second = m.input_inventory(self.root, ['project'])
        self.assertNotEqual(first, second, 'project file membership is an input independently of bytes')
        git('add', 'Sources/input.swift')
        self.assertEqual(first, m.input_inventory(self.root, ['project']))

    def test_malformed_stdout_and_lying_exit_are_not_verified(self):
        cases = ['print("not json")', 'print("{}")', 'pass',
                 'print(' + repr(json.dumps(project_certificate())) + '); print("trailing garbage")',
                 'print(' + repr(json.dumps(project_certificate())) + '); raise SystemExit(7)']
        for index, code in enumerate(cases):
            with self.subTest(code=code):
                run = self.root / str(index)
                run.mkdir()
                with self.command(code):
                    result = m.execute_check('project', run, 5, root=self.root)
                self.assertEqual(result['status'], 'failed')
                self.assertFalse(m.artifacts_valid(result, run))

    def test_timeout_is_unknown_and_has_retained_logs(self):
        with self.command('import time; print("started", flush=True); time.sleep(10)'):
            result = m.execute_check('project', self.root, 0.1, root=self.root)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['reason'], 'timeout')
        self.assertIsNone(result['certificate'])
        self.assertLess(result['wall_seconds'], 4)
        self.assertTrue((self.root / 'project/stderr.log').is_file())

    def test_missing_executable_fails_without_certificate(self):
        with patch.object(m, 'command_for', return_value=[str(self.root / 'nonexistent')]):
            result = m.execute_check('project', self.root, 1, root=self.root)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'FileNotFoundError')
        self.assertIsNone(result['certificate'])

    def test_valid_evidence_reuses_without_promoting_acceptance(self):
        first = self.run_project()
        self.assertEqual(first['checks_status'], 'verified')
        with patch.object(m, 'execute_check', side_effect=AssertionError('fresh evidence should reuse')):
            second = m.run_checks(['project'], resume=first['record_path'], root=self.root, toolchain=self.toolchain)
        self.assertEqual(second['checks'][0]['reused_from'], first['run_id'])
        for record in (first, second, self.fresh_status(second)):
            self.assertEqual(record['milestone_status'], 'unimplemented')
            self.assertEqual(record['device_acceptance']['status'], 'unknown')
            self.assertTrue(all(x['status'] == 'unimplemented' for x in record['milestones']))
        self.assertEqual(self.fresh_status(second)['checks_status'], 'verified')

    def test_tampered_artifacts_force_execution_and_stale_status(self):
        for artifact in ('stdout.log', 'stderr.log', 'result.json'):
            with self.subTest(artifact=artifact):
                first = self.run_project()
                directory = Path(first['record_path']).parent
                (directory / 'project' / artifact).write_text('tampered')
                self.assertFalse(m.artifacts_valid(first['checks'][0], directory))
                self.assertEqual(self.fresh_status(first)['checks_status'], 'unknown')
                second = self.run_project(resume=first['record_path'])
                self.assertNotIn('reused_from', second['checks'][0])
                self.assertEqual(second['checks_status'], 'verified')

    def test_changed_inputs_prevent_reuse(self):
        first = self.run_project()
        (self.root / 'Sources/input.swift').write_text('// new version\n')
        self.assertEqual(self.fresh_status(first)['checks_status'], 'unknown')
        second = self.run_project(resume=first['record_path'])
        self.assertNotIn('reused_from', second['checks'][0])
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])

    def test_input_changes_during_execution_downgrade_result(self):
        code = ('from pathlib import Path; Path("Sources/input.swift").write_text("changed"); print(' +
                repr(json.dumps(project_certificate())) + ')')
        with self.command(code):
            record = m.run_checks(['project'], root=self.root, toolchain=self.toolchain)
        self.assertEqual(record['freshness']['status'], 'stale')
        self.assertEqual(record['checks'][0]['status'], 'unknown')
        self.assertNotEqual(record['checks_status'], 'verified')

    def test_record_tampering_is_rejected_before_reuse(self):
        first = self.run_project()
        path = Path(first['record_path'])
        payload = json.loads(path.read_text())
        payload['checks_status'] = 'invented'
        path.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            self.run_project(resume=path)

    def test_certificate_rejects_unbounded_or_inconsistent_prefix(self):
        m.validate_certificate('startup_prefix', startup_certificate())
        for mutate in (lambda p: p['profiles'][0].update(completed=True),
                       lambda p: p.update(source_callbacks=999),
                       lambda p: p['profiles'][0]['stop'].update(diagnostic='success'),
                       lambda p: p['profiles'][0]['stop'].update(address=0),
                       lambda p: p['profiles'][0].update(name='invented')):
            payload = copy.deepcopy(startup_certificate())
            mutate(payload)
            with self.assertRaises(ValueError):
                m.validate_certificate('startup_prefix', payload)

    def test_verified_prefix_records_frontier_without_gameplay_acceptance(self):
        reference = b'synthetic reference'
        import hashlib
        certificate = startup_certificate()
        certificate['reference_sha256'] = hashlib.sha256(reference).hexdigest()
        code = ('import os; from pathlib import Path; '
                'Path(os.environ["CLAW_APPLICATION_PREGRAPHICS_CHECK_DIR"], "reference.json").write_bytes(' +
                repr(reference) + '); print(' + repr(json.dumps(certificate)) + ')')
        with patch.object(m, 'input_inventory', return_value={'synthetic': 'a' * 64}), self.command(code):
            record = m.run_checks(['startup_prefix'], root=self.root, toolchain=self.toolchain)
            self.assertEqual(record['checks_status'], 'verified')
            self.assertEqual(len(record['frontiers']), 6)
            self.assertEqual(record['milestone_status'], 'unimplemented')
            self.assertEqual(record['device_acceptance']['status'], 'unknown')
            self.assertTrue(all(x['status'] == 'unimplemented' for x in record['milestones']))
        directory = Path(record['record_path']).parent
        (directory / 'startup_prefix/reference.json').write_bytes(b'tampered')
        self.assertFalse(m.artifacts_valid(record['checks'][0], directory))

    def test_symlink_artifact_is_never_reused(self):
        record = self.run_project()
        directory = Path(record['record_path']).parent
        artifact = directory / 'project/stdout.log'
        external = self.root / 'external.log'
        external.write_bytes(artifact.read_bytes())
        artifact.unlink()
        artifact.symlink_to(external)
        self.assertFalse(m.artifacts_valid(record['checks'][0], directory))
        rerun = self.run_project(resume=record['record_path'])
        self.assertNotIn('reused_from', rerun['checks'][0])

    def test_source_graph_certificate_requires_exact_profile_scope(self):
        payload = dict(status='pass', mode='sanitized', sanitized=True, optimized=False,
                       replay=dict(status='pass', profiles=448, unique_reference_profiles=288),
                       edge_validation=dict(status='pass', edges=9),
                       reference_sha256={name: 'a' * 64 for name in m.GOLDENS}, cache_key='b' * 64)
        m.validate_certificate('source_graph', payload)
        for key, value in (('profiles', 449), ('unique_reference_profiles', 448)):
            bad = copy.deepcopy(payload)
            bad['replay'][key] = value
            with self.assertRaises(ValueError):
                m.validate_certificate('source_graph', bad)
        bad = dict(payload, sanitized=False)
        with self.assertRaises(ValueError):
            m.validate_certificate('source_graph', bad)

    def test_manager_certificate_requires_frozen_scope_and_sanitizers(self):
        m.validate_certificate('tls_manager_source', manager_certificate())
        mutations = [lambda p: p.update(schema=True),
                     lambda p: p.update(sanitized=False),
                     lambda p: p.update(optimized=True),
                     lambda p: p.update(reference_sha256='invalid'),
                     lambda p: p.update(cache_key='z' * 64),
                     lambda p: p.update(replay=None)]
        for key in ('profiles', 'roots', 'physical_events', 'child_entries', 'native_controls', 'assertions'):
            mutations.append(lambda p, key=key: p['replay'].update({key: 0}))
            mutations.append(lambda p, key=key: p['replay'].update({key: True}))
        for mutate in mutations:
            certificate = manager_certificate()
            mutate(certificate)
            with self.assertRaises(ValueError):
                m.validate_certificate('tls_manager_source', certificate)

    def test_manager_reference_mismatch_cannot_verify_or_promote_gameplay(self):
        for digest, expected in (('a' * 64, 'verified'), ('c' * 64, 'unknown')):
            with self.subTest(digest=digest), patch.object(m, 'input_inventory',
                    return_value={m.MANAGER_REFERENCE: digest}), self.command(
                    'print(' + repr(json.dumps(manager_certificate())) + ')'):
                record = m.run_checks(['tls_manager_source'], root=self.root,
                                      toolchain=self.toolchain)
                self.assertEqual(record['checks'][0]['status'], expected)
                self.assertEqual(record['milestone_status'], 'unimplemented')
                self.assertEqual(record['device_acceptance']['status'], 'unknown')
                self.assertEqual(record['frontiers'], [])

    def test_values_certificate_keeps_unobserved_entries_explicit(self):
        m.validate_certificate('tls_values_source', values_certificate())
        mutations = [lambda p: p['replay'].update(observed_entries=410),
                     lambda p: p['replay'].update(reference_only_entries=0),
                     lambda p: p['replay'].update(native_controls=0),
                     lambda p: p['replay'].update(native_controls=143),
                     lambda p: p['replay'].update(assertions=29370),
                     lambda p: p['replay'].update(unobserved_sites=[]),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=0x1234),
                     lambda p: p['replay']['unobserved_sites'][0].update(frame=0),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=True),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=1)]
        for mutate in mutations:
            payload = values_certificate()
            mutate(payload)
            with self.assertRaises(ValueError):
                m.validate_certificate('tls_values_source', payload)

    def test_values_reference_mismatch_cannot_verify_or_promote_gameplay(self):
        for digest, expected in (('a' * 64, 'verified'), ('c' * 64, 'unknown')):
            with self.subTest(digest=digest), patch.object(m, 'input_inventory',
                    return_value={m.VALUES_REFERENCE: digest}), self.command(
                    'print(' + repr(json.dumps(values_certificate())) + ')'):
                record = m.run_checks(['tls_values_source'], root=self.root,
                                      toolchain=self.toolchain)
                self.assertEqual(record['checks'][0]['status'], expected)
                self.assertEqual(record['milestone_status'], 'unimplemented')
                self.assertEqual(record['device_acceptance']['status'], 'unknown')


    def test_module_certificate_rejects_incomplete_or_overclaimed_evidence(self):
        m.validate_certificate('cold_module_source', module_certificate())
        mutations = [lambda p: p.update(schema=True),
                     lambda p: p.update(sanitized=False),
                     lambda p: p.update(optimized=True),
                     lambda p: p.update(reference_sha256='a' * 64),
                     lambda p: p.update(cache_key='z' * 64),
                     lambda p: p['replay'].update(native_controls=82, assertions=71750),
                     lambda p: p['replay'].update(original_assertions=71667, assertions=71750),
                     lambda p: p['replay'].update(catch_executed=True),
                     lambda p: p['replay'].update(application_getter_executed=True),
                     lambda p: p['replay'].update(unobserved_sites=[]),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=0x501f01),
                     lambda p: p['replay']['unobserved_sites'][0].update(frame=0),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=True),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=1),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=0x502e47, return_pc=0x502ea8)]
        for key in ('profiles', 'roots', 'physical_events', 'observed_entries',
                    'reference_entries', 'reference_only_entries', 'native_controls',
                    'original_assertions', 'assertions'):
            mutations.extend([lambda p, key=key: p['replay'].update({key: 0}),
                              lambda p, key=key: p['replay'].update({key: True})])
        for mutate in mutations:
            payload = module_certificate()
            mutate(payload)
            with self.assertRaises(ValueError):
                m.validate_certificate('cold_module_source', payload)

    def test_module_reference_mismatch_cannot_promote_gameplay(self):
        for digest, expected in ((m.MODULE_REFERENCE_SHA256, 'verified'), ('c' * 64, 'unknown')):
            with self.subTest(digest=digest), patch.object(m, 'input_inventory',
                    return_value={m.MODULE_REFERENCE: digest}), self.command(
                    'print(' + repr(json.dumps(module_certificate())) + ')'):
                record = m.run_checks(['cold_module_source'], root=self.root, toolchain=self.toolchain)
                self.assertEqual(record['checks'][0]['status'], expected)
                self.assertEqual(record['milestone_status'], 'unimplemented')
                self.assertEqual(record['device_acceptance']['status'], 'unknown')
                self.assertEqual(record['frontiers'], [])

    def test_application_thread_certificate_rejects_incomplete_or_overclaimed_evidence(self):
        m.validate_certificate('application_thread_source', application_thread_certificate())
        mutations = [lambda p: p.update(schema=True),
                     lambda p: p.update(sanitized=False),
                     lambda p: p.update(optimized=True),
                     lambda p: p.update(reference_sha256='a' * 64),
                     lambda p: p.update(cache_key='z' * 64),
                     lambda p: p['replay'].update(native_controls=165, assertions=69119),
                     lambda p: p['replay'].update(original_assertions=68953, assertions=69119),
                     lambda p: p['replay'].update(catch_executed=True),
                     lambda p: p['replay'].update(whole_cwinapp_executed=True),
                     lambda p: p['replay'].update(bridges=10),
                     lambda p: p['replay'].update(application_getter_executed=False),
                     lambda p: p['replay'].update(unobserved_sites=[]),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=0x501f01),
                     lambda p: p['replay']['unobserved_sites'][0].update(frame=0),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=True),
                     lambda p: p['replay']['unobserved_sites'][0].update(root_step=1),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=0x502e47, return_pc=0x502ea8)]
        for key in ('profiles', 'roots', 'physical_events', 'observed_entries',
                    'reference_entries', 'reference_only_entries', 'native_controls',
                    'original_assertions', 'assertions'):
            mutations.extend([lambda p, key=key: p['replay'].update({key: 0}),
                              lambda p, key=key: p['replay'].update({key: True})])
        for mutate in mutations:
            payload = application_thread_certificate()
            mutate(payload)
            with self.assertRaises(ValueError):
                m.validate_certificate('application_thread_source', payload)

    def test_application_thread_distinguishes_reused_frame_at_different_call_sites(self):
        payload = application_thread_certificate()
        sites = payload['replay']['unobserved_sites']
        first = next(s for s in sites if s['return_pc'] == 0x502137)
        second = next(s for s in sites if s['return_pc'] == 0x502145)
        second.update(profile=first['profile'], root_step=first['root_step'], frame=first['frame'])
        m.validate_certificate('application_thread_source', payload)
        second['return_pc'] = first['return_pc']
        with self.assertRaisesRegex(ValueError, 'duplicate reference-only site'):
            m.validate_certificate('application_thread_source', payload)

    def test_application_thread_reference_mismatch_cannot_promote_gameplay(self):
        for digest, expected in ((m.APPLICATION_THREAD_REFERENCE_SHA256, 'verified'), ('c' * 64, 'unknown')):
            with self.subTest(digest=digest), patch.object(m, 'input_inventory',
                    return_value={m.APPLICATION_THREAD_REFERENCE: digest}), self.command(
                    'print(' + repr(json.dumps(application_thread_certificate())) + ')'):
                record = m.run_checks(['application_thread_source'], root=self.root, toolchain=self.toolchain)
                self.assertEqual(record['checks'][0]['status'], expected)
                self.assertEqual(record['milestone_status'], 'unimplemented')
                self.assertEqual(record['device_acceptance']['status'], 'unknown')
                self.assertEqual(record['frontiers'], [])

    def test_application_object_rejects_partial_or_overclaimed_evidence(self):
        m.validate_certificate('application_object_source', application_object_certificate())
        mutations = [lambda p: p.update(schema=True), lambda p: p.update(complete_reference=False),
                     lambda p: p.update(sanitized=False), lambda p: p.update(optimized=True),
                     lambda p: p.update(reference_sha256='d' * 64), lambda p: p.update(cache_key='z' * 64),
                     lambda p: p['replay'].update(native_controls=164, assertions=572126),
                     lambda p: p['replay'].update(original_assertions=571961, assertions=572126),
                     lambda p: p['replay'].update(catch_executed=True),
                     lambda p: p['replay'].update(whole_cwinapp_executed=False),
                     lambda p: p['replay'].update(unobserved_sites=[]),
                     lambda p: p['replay']['unobserved_sites'][0].update(original_defined=1),
                     lambda p: p['replay']['unobserved_sites'][0].update(frame=0),
                     lambda p: p['replay']['unobserved_sites'][0].update(function=[]),
                     lambda p: p['replay']['unobserved_sites'][-1].update(reason=''),
                     lambda p: p['replay']['unobserved_sites'][-1].update(original_defined=True),
                     lambda p: p['replay']['unobserved_sites'][1].update(profile='site-0'),
                     lambda p: p['replay'].update(missing_native_sites=[]),
                     lambda p: p['replay']['missing_native_sites'][0].update(profile=[]),
                     lambda p: p['replay']['missing_native_sites'][0].update(root_step=True),
                     lambda p: p['replay']['missing_native_sites'][0].update(frame=0x2007eb0),
                     lambda p: p['replay']['missing_native_sites'][0].update(function=0x546aa8),
                     lambda p: p['replay']['missing_native_sites'][0].update(profile='allocation-null-at-3',
                                                                          return_pc=0x502f9c, frame=0x2007ea4)]
        for field in ('function', 'return_pc', 'frame'):
            mutations.append(lambda p, field=field: p['replay']['missing_native_sites'][0].update(
                {field: float(p['replay']['missing_native_sites'][0][field])}))
        for key in ('profiles', 'roots', 'returned_roots', 'stopped_roots', 'physical_events',
                    'reference_physical_events', 'observed_entries', 'reference_only_entries',
                    'native_unobserved_entries', 'reference_entries', 'missing_native_prefixes',
                    'later_original_physical_events', 'later_original_entries', 'native_controls',
                    'original_assertions', 'assertions'):
            mutations.append(lambda p, key=key: p['replay'].update({key: True}))
            mutations.append(lambda p, key=key: p['replay'].update({key: 999}))
        for change in mutations:
            payload = application_object_certificate()
            change(payload)
            with self.assertRaises(ValueError):
                m.validate_certificate('application_object_source', payload)

    def test_application_object_index_mismatch_cannot_promote_gameplay(self):
        for fingerprint, expected in ((m.APPLICATION_OBJECT_REFERENCE_SHA256, 'verified'), ('d' * 64, 'unknown')):
            with self.subTest(fingerprint=fingerprint), patch.object(m, 'input_inventory',
                    return_value={m.APPLICATION_OBJECT_REFERENCE: fingerprint}), self.command(
                    'print(' + repr(json.dumps(application_object_certificate())) + ')'):
                record = m.run_checks(['application_object_source'], root=self.root, toolchain=self.toolchain)
                self.assertEqual(record['checks'][0]['status'], expected)
                self.assertEqual(record['milestone_status'], 'unimplemented')
                self.assertEqual(record['device_acceptance']['status'], 'unknown')
                self.assertEqual(record['frontiers'], [])

    def test_application_object_inventory_pins_every_compressed_shard(self):
        index = self.root / m.APPLICATION_OBJECT_REFERENCE
        index.parent.mkdir(parents=True)
        executable = self.root / m.EXE
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b'original-test-input')
        exe_hash = m.digest(executable)
        shards = []
        for i in range(61):
            relative = f'profiles/profile-{i:03d}.json.xz'
            path = index.parent / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(f'compressed-fixture-{i}'.encode())
            shards.append(dict(index=i, path=relative, sha256=m.digest(path)))
        index.write_text(json.dumps(dict(schema='claw-original-application-object-shards-v1',
                                        originalSha256=exe_hash, profiles=61, roots=62, shards=shards)))
        index_hash = m.digest(index)
        with patch.object(m, 'APPLICATION_OBJECT_REFERENCE_SHA256', index_hash), patch.object(m, 'ORIGINAL_SHA256', exe_hash):
            inventory = m.input_inventory(self.root, ['application_object_source'])
            self.assertEqual(inventory[m.APPLICATION_OBJECT_REFERENCE], index_hash)
            self.assertEqual(len([x for x in inventory if x.endswith('.xz')]), 61)
            path = index.parent / shards[17]['path']
            path.write_bytes(b'changed-shard')
            with self.assertRaisesRegex(m.PrerequisiteError, 'shard fingerprint mismatch'):
                m.input_inventory(self.root, ['application_object_source'])
            path.unlink()
            with self.assertRaisesRegex(m.PrerequisiteError, 'missing input'):
                m.input_inventory(self.root, ['application_object_source'])
        index.write_text('corrupted index')
        with self.assertRaises(m.PrerequisiteError):
            m.input_inventory(self.root, ['application_object_source'])

    def test_application_object_long_default_keeps_explicit_timeout_override(self):
        for requested, expected in ((None, 7200), (12, 12)):
            with patch.object(m, 'input_inventory', return_value={
                    m.APPLICATION_OBJECT_REFERENCE: m.APPLICATION_OBJECT_REFERENCE_SHA256}), patch.object(
                    m, 'execute_check', return_value=dict(id='application_object_source', status='verified',
                                                         certificate=application_object_certificate())) as execute:
                m.run_checks(['application_object_source'], root=self.root, toolchain=self.toolchain,
                             timeout=requested)
                self.assertEqual(execute.call_args.args[2], expected)
        with patch.object(m, 'execute_check', return_value=dict(id='project', status='verified',
                                                              certificate=project_certificate())) as execute:
            m.run_checks(['project'], root=self.root, toolchain=self.toolchain)
            self.assertEqual(execute.call_args.args[2], 900)

    def test_crt_whole_environment_only_for_new_check(self):
        base = dict(CLAW_NATIVE_CRT_WHOLE='0', CLAW_NATIVE_ASAN='0', CLAW_OTHER='unsafe')
        for check in m.CHECKS:
            env = m.controlled_environment(base, self.root, check)
            self.assertEqual(env['CLAW_NATIVE_ASAN'], '1')
            self.assertEqual(env['CLAW_NATIVE_OPTIMIZE'], '0')
            self.assertNotIn('CLAW_OTHER', env)
            self.assertEqual(env.get('CLAW_NATIVE_CRT_WHOLE'), '1' if check == 'crt_registry_source' else None)
        self.assertIn('crt_registry_source', m.select_checks())
        self.assertEqual(m.command_for('crt_registry_source'), ['scripts/check-native-crt-exit-registry.sh'])

    def crt_inventory_fixture(self):
        index = self.root / m.CRT_REFERENCE
        index.parent.mkdir(parents=True)
        exe = self.root / m.EXE
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b'original fixture')
        profiles = []
        for i in range(21):
            name = f'profile-{i}'
            shard = index.parent / (name + '.json.gz')
            shard.write_bytes(f'shard {i}'.encode())
            profiles.append(dict(name=name, path=str(m.ROOT / Path(m.CRT_REFERENCE).parent / shard.name),
                sha256=m.digest(shard), bytes=1, states=1, pages=1, steps=1, physicalEvents=1,
                sourceEntries=1, instructions=1, registrations=1, resizeAttempts=1, halt=None))
        data = dict(schema='claw-original-crt-exit-registry-pages-v1', status='PASS',
                    programSha256=m.digest(exe), profiles=profiles)
        index.write_text(json.dumps(data))
        return index, exe, data

    def test_crt_inventory_pins_every_shard_and_rejects_mutation(self):
        index, exe, data = self.crt_inventory_fixture()
        with patch.object(m, 'CRT_REFERENCE_SHA256', m.digest(index)), patch.object(m, 'ORIGINAL_SHA256', m.digest(exe)):
            inventory = m.input_inventory(self.root, ['crt_registry_source'])
            self.assertEqual(sum(name.endswith('.json.gz') for name in inventory), 21)
            shard = index.parent / 'profile-7.json.gz'
            shard.write_bytes(b'mutated')
            with self.assertRaisesRegex(m.PrerequisiteError, 'CRT shard fingerprint mismatch'):
                m.input_inventory(self.root, ['crt_registry_source'])
            shard.unlink()
            with self.assertRaisesRegex(m.PrerequisiteError, 'missing input'):
                m.input_inventory(self.root, ['crt_registry_source'])

    def test_crt_inventory_rejects_unsafe_paths_types_and_missing_profiles(self):
        index, exe, original = self.crt_inventory_fixture()
        changes = [lambda d: d['profiles'].pop(),
            lambda d: d['profiles'][0].update(name='../escape'),
            lambda d: d['profiles'][0].update(path='/tmp/profile-0.json.gz'),
            lambda d: d['profiles'][0].update(path=str(m.ROOT / Path(m.CRT_REFERENCE).parent / '../profile-0.json.gz')),
            lambda d: d['profiles'][0].update(steps=True),
            lambda d: d['profiles'][0].update(sha256=3),
            lambda d: d['profiles'][1].update(name='profile-0')]
        for change in changes:
            data = copy.deepcopy(original)
            change(data)
            index.write_text(json.dumps(data))
            with self.subTest(data=data), patch.object(m, 'CRT_REFERENCE_SHA256', m.digest(index)), patch.object(m, 'ORIGINAL_SHA256', m.digest(exe)):
                with self.assertRaises(m.PrerequisiteError):
                    m.input_inventory(self.root, ['crt_registry_source'])
        index.write_text(json.dumps(original))
        shard = index.parent / 'profile-0.json.gz'
        shard.unlink(); shard.symlink_to(exe)
        with patch.object(m, 'CRT_REFERENCE_SHA256', m.digest(index)), patch.object(m, 'ORIGINAL_SHA256', m.digest(exe)):
            with self.assertRaisesRegex(m.PrerequisiteError, 'CRT shard path'):
                m.input_inventory(self.root, ['crt_registry_source'])

    def crt_artifact_fixture(self):
        directory = self.root.resolve() / 'attempt'
        directory.mkdir()
        build = dict(schema=1, command='native-crt-exit-registry', root_sites='prepared original leaf roots at4a5896; admitted leaf CALLs execute natively; no constructor wrappers',
                     cpp=['-fsanitize=address,undefined'], swift=['-sanitize=address'],
                     edges=dict(status='pass', edges=23, source_entries=8, prepared_roots=8, physical_services=7, missing_source_stops=1, registration_leaves=126, rejected_metadata_mutations=49, original_registration_order_sha256='4d24cb562a78c6ed56e166257c3141f68d262e6d8798b9607344413ff2e5ed63'),
                     whole_leaves=True, sanitized=True, optimized=False,
                     original=m.ORIGINAL_SHA256, inputs={'Sources/input.swift': m.digest(self.root / 'Sources/input.swift')})
        key = m.hashlib.sha256(json.dumps(build, sort_keys=True).encode()).hexdigest()
        cache = self.root / 'work/native-crt-exit-registry-cache' / key
        cache.mkdir(parents=True)
        binary = cache / 'check'; binary.write_bytes(b'executed binary fixture')
        negatives = {}
        for kind in ('callback', 'parentPC', 'argumentStore', 'returnStore', 'frame', 'bodyEAX', 'cleanupECX', 'cleanupFlags'):
            target = cache / ('negative-' + kind); target.write_bytes(kind.encode())
            source = target.with_suffix('.cpp'); source.write_bytes((kind + ' source').encode())
            negatives[kind] = dict(binary=m.digest(target), source=m.digest(source))
        certificate = cache / 'certificate.json'
        certificate.write_text(json.dumps(dict(certificate=build, binary=m.digest(binary), negative_binaries=negatives)))
        snapshot = directory / 'crt-native-whole-snapshots/sanitized/profile-native.json'
        snapshot.parent.mkdir(parents=True); snapshot.write_text('{}')
        report = directory / 'crt-native-whole-sanitized-report.json'
        payload = dict(scope=build['root_sites'], cache_key=key, certificate=str(certificate), certificate_sha256=m.digest(certificate),
                       profiles=[dict(profile='profile', native_snapshot=str(snapshot), native_snapshot_sha256=m.digest(snapshot))],
                       report_path=str(report))
        report.write_text(json.dumps(payload))
        return directory, cache, payload

    def test_crt_captures_actual_invocation_artifacts_and_detects_corruption(self):
        directory, cache, payload = self.crt_artifact_fixture()
        evidence = m.crt_evidence(payload, directory, self.root, capture=True)
        self.assertEqual(len(evidence), 20)
        self.assertEqual(m.crt_evidence(payload, directory, self.root), evidence)
        for filename in ('build-certificate.json', 'native-check', 'negative-callback',
                         'crt-native-whole-snapshots/sanitized/profile-native.json'):
            target = directory / filename
            original = target.read_bytes()
            target.write_bytes(b'corrupt')
            with self.subTest(filename=filename), self.assertRaises((ValueError, json.JSONDecodeError)):
                m.crt_evidence(payload, directory, self.root)
            target.write_bytes(original)
        (cache / 'check').write_bytes(b'changed actual binary')
        with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
            m.crt_evidence(payload, directory, self.root, capture=True)

    def test_crt_rejects_shared_reports_snapshot_escape_and_changed_certificate(self):
        directory, cache, original = self.crt_artifact_fixture()
        payload = copy.deepcopy(original)
        payload['profiles'][0]['native_snapshot'] = str(self.root / 'external/profile-native.json')
        with self.assertRaisesRegex(ValueError, 'snapshot path'):
            m.crt_evidence(payload, directory, self.root, capture=True)
        payload = copy.deepcopy(original)
        payload['report_path'] = str(self.root / 'shared-report.json')
        with self.assertRaisesRegex(ValueError, 'report path'):
            m.crt_evidence(payload, directory, self.root, capture=True)
        (cache / 'certificate.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'certificate identity'):
            m.crt_evidence(original, directory, self.root, capture=True)

    def crt_certificate_fixture(self):
        profiles = []
        expected = copy.deepcopy(m.CRT_PROFILES)
        for name, (reference, counts, assertions, fingerprint) in expected.items():
            profile = dict(zip(m.CRT_COUNT_FIELDS, counts))
            outcomes = []
            for i in range(profile['roots']):
                completed = not (i == profile['roots'] - 1 and ('prefix' in name or name == 'first-allocation-failure'))
                row = dict(step=i, leaf=i < profile['leaf_roots'], completed=completed, eax=0 if completed else None,
                           function=0x4a3610, returnPC=0x4a5896, frame=0x2007f00, referenceState=i, arguments=[],
                           outputCPU=dict.fromkeys(('eax', 'ebp', 'ebx', 'ecx', 'edi', 'edx', 'eflags', 'eip', 'esi', 'esp', 'fsHead'), 0))
                if not completed:
                    row['stop'] = dict(address=0x4a4860, code=2, diagnostic='missingDependency')
                outcomes.append(row)
            controls = 40 if name == 'inplace126' else 0
            profile.update(command='native-crt-exit-registry', status='pass', profile=name, scope='prepared-original-leaf-roots',
                reference_sha256=reference, native_controls=controls, assertions=assertions + controls, root_outcomes=outcomes,
                native_snapshot_sha256=m.hashlib.sha256(b'{}').hexdigest(), native_snapshot='/tmp/' + name + '-native.json')
            profiles.append(profile)
            expected[name] = reference, counts, assertions, m.stable_hash(outcomes)
        certificate = dict(schema=1, status='pass', command='native-crt-exit-registry', whole_leaves=True,
            sanitized=True, optimized=False, cache_key='c' * 64, certificate_sha256='d' * 64,
            certificate='/tmp/certificate.json', report_path='/tmp/report.json',
            reference_provenance_sha256=m.CRT_REFERENCE_SHA256, profiles=profiles,
            scope='prepared original leaf roots at4a5896; admitted leaf CALLs execute natively; no constructor wrappers',
            negative_leaf_controls=[dict(status='pass', negative_leaf=k, assertions=2110) for k in
                ('callback', 'parentPC', 'argumentStore', 'returnStore', 'frame', 'bodyEAX', 'cleanupECX', 'cleanupFlags')])
        return certificate, expected

    def test_crt_whole_rejects_subsets_wrong_mode_and_overclaimed_outcomes(self):
        original, expected = self.crt_certificate_fixture()
        changes = [lambda p: p.update(schema=True), lambda p: p.update(whole_leaves=False),
            lambda p: p.update(sanitized=False), lambda p: p.update(optimized=True),
            lambda p: p.update(whole_leaves=1), lambda p: p.update(sanitized=1), lambda p: p.update(optimized=0),
            lambda p: p.update(reference_provenance_sha256='f' * 64),
            lambda p: p['profiles'].pop(), lambda p: p['profiles'][0].update(roots=8, leaf_roots=0),
            lambda p: p['profiles'][0].update(native_controls=39),
            lambda p: p['profiles'][0].update(assertions=100),
            lambda p: p['profiles'][0].update(reference_sha256='f' * 64),
            lambda p: p['profiles'][0].update(profile='unrecognized'),
            lambda p: p['profiles'][0].update(native_snapshot='/tmp/../escape-native.json'),
            lambda p: p['profiles'][0].update(root_outcomes=[]),
            lambda p: p['profiles'][0]['root_outcomes'][0].update(leaf=False),
            lambda p: p['profiles'][0]['root_outcomes'][0].update(frame=True),
            lambda p: p['profiles'][0]['root_outcomes'][0]['outputCPU'].update(eax=True),
            lambda p: p['profiles'][6]['root_outcomes'][-1].pop('stop'),
            lambda p: p['profiles'][6]['root_outcomes'][-1]['stop'].update(address=0x1234),
            lambda p: p['negative_leaf_controls'].pop(),
            lambda p: p['negative_leaf_controls'][0].update(assertions=2109),
            lambda p: p['negative_leaf_controls'][0].update(assertions=True)]
        for field in (*m.CRT_COUNT_FIELDS, 'native_controls', 'assertions'):
            changes.append(lambda p, field=field: p['profiles'][0].update({field: True}))
        with patch.object(m, 'CRT_PROFILES', expected):
            m.validate_certificate('crt_registry_source', original)
            for change in changes:
                payload = copy.deepcopy(original); change(payload)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    m.validate_certificate('crt_registry_source', payload)
        self.assertEqual(sum(v[1][0] for v in m.CRT_PROFILES.values()), 797)
        self.assertEqual(sum(v[1][1] for v in m.CRT_PROFILES.values()), 756)

    def test_crt_fresh_run_resume_and_corrupt_snapshot_never_promote_playability(self):
        directory, cache, artifacts = self.crt_artifact_fixture()
        payload, expected = self.crt_certificate_fixture()
        payload.update({k: artifacts[k] for k in ('cache_key', 'certificate', 'certificate_sha256')})
        code = ('import json,os; from pathlib import Path; p=' + repr(payload) + '; '
                'd=Path(os.environ["CLAW_NATIVE_CRT_CHECK_DIR"]); '
                's=d/"crt-native-whole-snapshots/sanitized"; s.mkdir(parents=True); '
                '[(r.update(native_snapshot=str(s/(r["profile"]+"-native.json"))), (s/(r["profile"]+"-native.json")).write_text("{}")) for r in p["profiles"]]; '
                'report=d/"crt-native-whole-sanitized-report.json"; p["report_path"]=str(report); '
                'report.write_text(json.dumps(p)); print(json.dumps(p))')
        inputs = {m.CRT_REFERENCE: m.CRT_REFERENCE_SHA256, 'Sources/input.swift': m.digest(self.root / 'Sources/input.swift')}
        with patch.object(m, 'CRT_PROFILES', expected), patch.object(m, 'input_inventory', return_value=inputs), self.command(code):
            record = m.run_checks(['crt_registry_source'], root=self.root, toolchain=self.toolchain)
            self.assertEqual(record['checks_status'], 'verified', record)
            self.assertEqual(record['milestone_status'], 'unimplemented')
            self.assertEqual(record['frontiers'], [])
            resumed = m.run_checks(['crt_registry_source'], root=self.root, toolchain=self.toolchain, resume=record['record_path'])
            self.assertEqual(resumed['checks'][0]['reused_from'], record['run_id'])
            self.assertEqual(self.fresh_status(resumed)['checks_status'], 'verified')
            snapshot = Path(resumed['record_path']).parent / 'crt_registry_source/crt-native-whole-snapshots/sanitized/inplace126-native.json'
            snapshot.write_text('changed')
            self.assertEqual(self.fresh_status(resumed)['freshness'], 'stale_or_invalid')
            replayed = m.run_checks(['crt_registry_source'], root=self.root, toolchain=self.toolchain, resume=resumed['record_path'])
            self.assertNotIn('reused_from', replayed['checks'][0])
            self.assertEqual(replayed['checks_status'], 'verified')
            self.assertEqual(replayed['milestone_status'], 'unimplemented')

    def test_crt_build_certificate_rejects_false_sanitizer_claim(self):
        directory, cache, payload = self.crt_artifact_fixture()
        saved = json.loads((cache / 'certificate.json').read_text())
        saved['certificate']['cpp'] = ['-O2']
        key = m.hashlib.sha256(json.dumps(saved['certificate'], sort_keys=True).encode()).hexdigest()
        changed_cache = cache.with_name(key); cache.rename(changed_cache)
        certificate = changed_cache / 'certificate.json'; certificate.write_text(json.dumps(saved))
        payload.update(cache_key=key, certificate=str(certificate), certificate_sha256=m.digest(certificate))
        Path(payload['report_path']).write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, 'compiler sanitizer mode'):
            m.crt_evidence(payload, directory, self.root, capture=True)


if __name__ == '__main__':
    unittest.main()
