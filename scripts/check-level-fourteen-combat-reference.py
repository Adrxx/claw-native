"""Validate the original Omar combat prefix; never grants app/ending acceptance."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('omar_check', ROOT/'scripts/check-level-fourteen-boss.py')
check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.reference: check.REFERENCE = args.reference.resolve()
    if args.evidence: check.WORK = args.evidence.resolve()
    check.WORK.mkdir(parents=True, exist_ok=True)
    errors = []
    ref = check.original(False)
    checkpoint = ref['observer_checkpoint']
    if checkpoint['sha256'] != check.fingerprint(ROOT/checkpoint['path']):
        errors.append('Checkpoint changed')
    for name, digest in {**checkpoint['inputs_sha256'], **ref['adapter_inputs'],
                        'Tests/NativeLevels/level_fourteen_boss_trace.py': ref['tracer_sha256']}.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            errors.append('Input changed: '+name)
    if ref['plan'] != json.loads((ROOT/'Tests/NativeLevels/level_fourteen_boss_plan.json').read_text()):
        errors.append('Acceptance plan changed')
    check.combat_phases(ref['boss_route_functions'], 'Original', errors, ref['boss_frames'])
    coverage = check.boss.coverage(ref['boss_frames'])
    for key in ('boss_active', 'boss_takes_damage', 'boss_defeated', 'boss_attacks', 'player_damage'):
        if not coverage[key]: errors.append('Missing '+key)
    frames = ref['boss_frames']
    receivers = {f['boss'].get('private') for f in frames}
    callbacks = ref['boss_death_callbacks']
    if not callbacks or any(c['address'] != '0x40e5c0' or c['receiver'] not in receivers
                            or check.boss.signed(c['health']) > 0 for c in callbacks):
        errors.append('Missing completed Omar death callback')
    if frames[-1]['elapsed_ms'] != ref['plan'][-1]['end_ms'] or frames[-1]['boss']['health'] != 0:
        errors.append('Combat did not reach the retained endpoint')
    if any(f['player']['health'] == 0 for f in frames): errors.append('Player died')
    if ref['stop'] and ref['stop'].get('phase') != 'command-8021':
        errors.append('Stop is inside the combat prefix')
    report = dict(check='level-fourteen-original-combat', status='fail' if errors else 'pass',
                  accepted=False, scope='Original combat only; app and ending acceptance are reported separately',
                  frames=len(frames), coverage=coverage, death_callbacks=callbacks,
                  ending_stop=ref['stop'], errors=errors)
    (check.WORK/'combat-result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == '__main__': raise SystemExit(main())
