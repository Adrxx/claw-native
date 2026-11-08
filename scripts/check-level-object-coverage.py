#!/usr/bin/env python3
"""Run the muted app loader census; queued work never exempts a missing object."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sign_allowance(entry):
    """Bind the exception to current original execution and exact disc records."""
    from Tests.NativeLevels.object_loading import EVIDENCE, verified_outcomes
    outcome = verified_outcomes(12)['Sign']
    world = ROOT / 'Original/retail-assets/LEVEL12/WORLDS/WORLD.WWD'
    placements = [{**{k: record[k] for k in ('id', 'plane', 'x', 'y', 'z', 'record_offset')},
                   'callback': '0x00000000', 'reason': 'loader-returned-no-actor'}
                  for record in outcome['object_records']]
    assert entry.get('basis') == 'original-ignores'
    assert entry.get('levels') == [12], 'Sign allowance must name only Level 12'
    assert entry.get('wwd_sha256') == hashlib.sha256(world.read_bytes()).hexdigest(), 'Stale Sign WWD'
    assert entry.get('evidence') == EVIDENCE, 'Wrong Sign evidence path'
    assert entry.get('evidence_sha256') == outcome['load_evidence_sha256'], 'Stale Sign evidence hash'
    assert entry.get('placements') == placements, 'Changed Sign allowance records'
    return placements


def assess(report, allow, tasks):
    errors, gaps, untracked, lines = [], [], [], []
    if report.get('schema') != 1 or report.get('complete') is not True or report.get('muted') is not True:
        errors.append('incomplete or invalid report')
    levels = report.get('levels', [])
    if [r.get('level') for r in levels] != list(range(1, 15)):
        errors.append('report must contain levels 1 through 14 exactly once')
    owners = {}
    for task in tasks:
        if task.get('state') not in ('open', 'taken', 'blocked'):
            continue
        names = task.get('coverage_logics', []) + [c['name'] for c in task.get('connection', {}).get('classes', [])]
        for name in names:
            owners.setdefault(name, []).append(task['id'])
    exemptions = {}
    for entry in allow:
        if not entry.get('logic') or not entry.get('reason', '').strip() or entry.get('basis') not in ('original-ignores', 'out-of-scope'):
            errors.append('invalid allow-list entry')
            continue
        if entry['logic'] == 'Sign':
            try:
                sign_allowance(entry)
            except (AssertionError, KeyError, ValueError, OSError) as error:
                errors.append(f'Invalid Sign proof: {error}')
                continue
        exemptions[entry['logic']] = entry
    for row in levels:
        level = row.get('level')
        if row.get('error') or row.get('fault') != 0 or row.get('duplicate_visits') != 0:
            errors.append(f"L{level}: load failure: {row.get('error', row.get('fault'))}")
        skipped = row.get('skipped', [])
        count = sum(g['count'] for g in skipped)
        if (row.get('skipped_count') != count or row.get('placed', -1) != row.get('instantiated', 0) + count
                or row.get('visited') != row.get('placed') or not row.get('wwd_sha256')):
            errors.append(f'L{level}: incomplete placement accounting')
        names, offsets = set(), set()
        for group in skipped:
            name = group['logic']
            if name in names or group['count'] <= 0 or len(group['placements']) != group['count']:
                errors.append(f'L{level}: invalid group {name}')
            names.add(name)
            for placement in group['placements']:
                if (not {'id', 'x', 'y', 'z', 'plane', 'record_offset', 'reason', 'callback'} <= placement.keys()
                        or placement.get('record_offset') in offsets):
                    errors.append(f'L{level}: invalid placement {name}')
                offsets.add(placement.get('record_offset'))
                if placement.get('reason') not in ('unsupported-logic', 'loader-returned-no-actor'):
                    errors.append(f'L{level}: {name}: {placement.get("reason")}')
            exempt = exemptions.get(name)
            if exempt and name == 'Sign':
                fields = ('id', 'plane', 'x', 'y', 'z', 'record_offset', 'callback', 'reason')
                actual = [{k: p.get(k) for k in fields} for p in group['placements']]
                if (level != 12 or row.get('wwd_sha256') != exempt['wwd_sha256']
                        or actual != exempt['placements'] or group['count'] != 3):
                    errors.append(f'L{level}: changed original Sign placements or WWD')
                    exempt = None
            if exempt and level in exempt.get('levels', range(1, 15)):
                group['allow_reason'] = exempt['reason']
            else:
                group['tasks'] = owners.get(name, [])
                gaps.append((level, name, group['count']))
                if not group['tasks']:
                    untracked.append((level, name))
        detail = ', '.join(f"{g['logic']}={g['count']}" for g in skipped) or 'none'
        lines.append(f"L{level}: {row.get('instantiated', 0)}/{row.get('placed', '?')} instantiated; gaps: {detail}")
    errors = list(dict.fromkeys(errors))
    return {'status': 'error' if errors else 'fail' if gaps else 'pass', 'errors': errors,
            'untracked': untracked, 'gaps': gaps, 'summary': lines}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-build', action='store_true', help='Check the existing Release snapshot even if another session changed sources; record its executable hash')
    parser.add_argument('--report-only', action='store_true', help='Validate existing evidence without launching')
    args = parser.parse_args()
    directory = ROOT / 'work/object-coverage'
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / 'levels.json'
    app_failed = False
    if not args.report_only:
        derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT / 'work/MacCatalyst'))
        binary = derived / 'Build/Products/Release-maccatalyst/Claw.app/Contents/MacOS/Claw'
        if not binary.exists():
            parser.error('Release app missing; run this script with --build')
        source_tree_newer = any(p.stat().st_mtime > binary.stat().st_mtime for folder in ('App', 'Sources')
                                for p in (ROOT / folder).rglob('*') if p.is_file())
        if source_tree_newer and not args.reuse_build:
            parser.error('Release app is older than sources; run this script with --build')
        executable_sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
        report_path.unlink(missing_ok=True)
        rows, run_seconds = [], 0.0
        for level in range(1, 15):
            # Waiting for other sessions is excluded from census runtime.
            while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
                print(f'object coverage: L{level} waiting for load below 16', flush=True)
                time.sleep(30)
            row_path = directory / f'level-{level}.json'
            row_path.unlink(missing_ok=True)
            began = time.monotonic()
            with (directory / f'level-{level}.log').open('w') as log:
                try:
                    result = subprocess.run([str(binary), '--mute', '--new-game-clock',
                                             '--object-coverage', str(directory), '--object-coverage-level', str(level)],
                                            stdout=log, stderr=subprocess.STDOUT, timeout=60)
                    app_failed |= result.returncode != 0
                except subprocess.TimeoutExpired:
                    app_failed = True
            run_seconds += time.monotonic() - began
            row = json.loads(row_path.read_text()) if row_path.exists() else {'level': level, 'error': 'No app level report'}
            rows.append(row)
            print(f"L{level}: {row.get('instantiated', 0)}/{row.get('placed', '?')} instantiated", flush=True)
            report = {'schema': 1, 'complete': len(rows) == 14, 'muted': True,
                      'executable_sha256': executable_sha256, 'source_tree_newer_than_build': source_tree_newer,
                      'mode': 'canonical-app-level-load-without-gameplay', 'elapsed_seconds': run_seconds, 'levels': rows}
            report_path.write_text(json.dumps(report, indent=2) + '\n')
    if not report_path.exists():
        print('No object coverage report', file=sys.stderr)
        return 2
    report = json.loads(report_path.read_text())
    allow = json.loads((ROOT / 'scripts/level-object-coverage-allowlist.json').read_text())
    tasks = json.loads((ROOT / 'tools/queue.json').read_text())['tasks']
    result = assess(report, allow, tasks)
    if app_failed:
        result['errors'].append('app process exited unsuccessfully')
        result['status'] = 'error'
    (directory / 'check.json').write_text(json.dumps(result, indent=2) + '\n')
    # Retain ownership next to each gap, without changing the app census itself.
    (directory / 'triage.json').write_text(json.dumps(report, indent=2) + '\n')
    summary = '\n'.join(result['summary']) + '\n'
    (directory / 'summary.txt').write_text(summary)
    print(summary, end='')
    for error in result['errors']:
        print(error, file=sys.stderr)
    print(json.dumps({'status': result['status'], 'errors': len(result['errors']),
                      'untracked': result['untracked'], 'gap_groups': len(result['gaps']),
                      'elapsed_seconds': report.get('elapsed_seconds')}))
    return {'pass': 0, 'fail': 1, 'error': 2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
