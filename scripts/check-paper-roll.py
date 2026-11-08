"""Startup paper pixels, timer sequence and wall time on every check clock.

--run launches muted Release instances, including a run under one batch gate.
A positional directory retains the offline primary-write comparison.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from responsiveness import check_heartbeats
from real_input import Session

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/paper-roll'


def collapse(xs):
    out = []
    for x in xs:
        if not out or out[-1] != x:
            out.append(x)
    return out


def compare(app_dir, ref):
    app = json.loads((app_dir / 'app-menu.json').read_text())
    original = collapse([u['pixels_sha256'] for u in ref['primary_unlocks'] if u['phase'] != 'main-menu-first-presentation'])
    ticks = [m for m in app.get('multi_flip_frames', []) if m['frame'] == 1]
    native = collapse([w['pixels_sha256'] for m in ticks for w in m.get('primary_writes', [])])
    frame = next((f for f in app.get('frames', []) if f['frame'] == 1), {})
    present = [p.get('pixels_sha256') for p in ref['presentations']][:1]
    errors = check_heartbeats(app.get('responsiveness', []), required=('0x4ec9c0',))
    if ref['status'] != 'pass' or app.get('status') != 'pass':
        errors.append('reference or app failed')
    if len(original) <= 1 or native != original or present != [frame.get('pixels')]:
        errors.append('primary writes or first menu frame differ from the original')
    for tick in ticks:
        for write in tick.get('primary_writes', []):
            if not (app_dir / write['png']).is_file():
                errors.append(f"missing primary image {write['png']}")
    return dict(original_screens=len(original), app_screens=len(native),
                first_frame_equal=present == [frame.get('pixels')], errors=errors)


def wait_for_load():
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        time.sleep(10)


def measure(mode, label, app):
    out = WORK / 'speed' / label
    out.mkdir(parents=True, exist_ok=True)
    for name in ('paper-timing.json', 'app-menu.json'):
        (out / name).unlink(missing_ok=True)
    wait_for_load()
    args = ['--paper-timing-check', str(out), '--responsiveness-check']
    if mode in ('fast_clock', 'display_clock_check'):
        subprocess.run([str(ROOT / 'work/new-game/launch.sh'), str(out), '120',
                        '--menu-check', str(out), '--new-game-clock', '--menu-frames', '61', *args],
                       cwd=ROOT, env={**os.environ, 'PAPER': '1', 'FAST': '1' if mode == 'fast_clock' else '0',
                                      'CLAW_CONFIG': app.parent.name.removesuffix('-maccatalyst')},
                       check=True, timeout=150)
    else:
        session = Session(out, fast=mode == 'fast_input_gate')
        try:
            session.launch(app, {}, args, start_seconds=60)
            end = time.monotonic() + 60
            while not (out / 'paper-timing.json').exists() and time.monotonic() < end:
                time.sleep(.02)
        finally:
            session.close()
    return json.loads((out / 'paper-timing.json').read_text())


def run(args, ref):
    modes = ('real_time', 'display_clock_check', 'fast_clock', 'fast_input_gate')
    app = ROOT / f'{os.environ.get("CLAW_DERIVED_DATA", "work/MacCatalyst")}/Build/Products/{args.config}-maccatalyst/Claw.app'
    records = {}
    errors = []
    # Establish unloaded measurements before starting the single requested load job.
    for mode in modes:
        records[mode] = measure(mode, mode, app)
    command = None
    if not args.startup_only:
        wait_for_load()
        command = ['make', 'gate', f'FAMILY={args.load_family}', 'ARGS=--jobs 1']
        with (WORK / 'speed/load-gate.log').open('w') as log:
            gate = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                time.sleep(2)
                for mode in modes:
                    if gate.poll() is not None:
                        raise RuntimeError('batch gate ended before the loaded timing measurement')
                    records[mode + '_loaded'] = measure(mode, mode + '_loaded', app)
                    if gate.poll() is not None:
                        raise RuntimeError('batch gate ended during the loaded timing measurement')
            finally:
                # This non-recording gate supplies load only; stop only our process group.
                if gate.poll() is None:
                    os.killpg(gate.pid, signal.SIGTERM)
                    try:
                        gate.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(gate.pid, signal.SIGKILL)
                        gate.wait()
    original_writes = [u['pixels_sha256'] for u in ref['primary_unlocks'] if u['phase'] != 'main-menu-first-presentation']
    original = collapse(original_writes)
    timers = records['fast_clock']['timer_values']
    for mode, row in records.items():
        errors += [f'{mode}: {e}' for e in check_heartbeats(row['responsiveness'], required=('0x4ec9c0',))]
        # The wall clock skips intermediate positions as rendering consumes
        # time. Deterministic clocks must retain every reference screen.
        deterministic = not mode.startswith('real_time')
        if deterministic and row['primary_writes'] != original_writes:
            errors.append(f'{mode}: paper frames differ from original')
        if not row['primary_writes'] or row['primary_writes'][-1] != original[-1]:
            errors.append(f'{mode}: finished paper differs from original')
        if deterministic and row['timer_values'] != timers:
            errors.append(f'{mode}: deterministic timer values changed')
        if 'fast' in mode and row['seconds'] > records['real_time']['seconds']:
            errors.append(f'{mode}: slower than real time')
        if mode.startswith(('fast_clock', 'display_clock_check')):
            errors += [f'{mode}: {e}' for e in compare(WORK / 'speed' / mode, ref)['errors']]
    report = dict(check='paper-startup-unroll', status='fail' if errors else 'pass',
                  milliseconds={m: round(r['seconds'] * 1000, 1) for m, r in records.items()},
                  original_milliseconds=ref['primary_unlocks'][-1]['ms'] - ref['primary_unlocks'][0]['ms'],
                  original_screens=len(original), timer_queries=len(timers),
                  timer_sequence_equal=all(r['timer_values'] == timers for m, r in records.items() if not m.startswith('real_time')),
                  load_command=command, errors=errors)
    (WORK / 'speed/result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=WORK / 'speed/fast_clock')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--startup-only', action='store_true',
                        help='Check all startup clocks without the separate loaded gate measurement')
    parser.add_argument('--config', default=os.environ.get('CLAW_CONFIG', 'Release'))
    parser.add_argument('--load-family', default='level_nine_crazy_hook_01')
    args = parser.parse_args()
    ref = json.loads((WORK / 'reference.json').read_text())
    try:
        if args.run:
            report = run(args, ref)
        else:
            report = compare(args.directory, ref)
            report.update(check='paper-startup-unroll', status='fail' if report['errors'] else 'pass')
    except Exception as error:
        report = dict(check='paper-startup-unroll', status='fail', errors=[str(error)])
    print(json.dumps(report))
    return report['status'] != 'pass'


if __name__ == '__main__':
    sys.exit(main())
