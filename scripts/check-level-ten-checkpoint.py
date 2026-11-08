"""Verify a bounded Marrow reference and exact continuation after combat restore.

This checks original discovery evidence; it does not admit native game code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import trace_rows


def summarize(path):
    values, digests, lengths = {}, {}, {}
    # Stream the large event arrays once, retaining only the small combat rows.
    for key, kind, value in trace_rows(path):
        if kind == 'array':
            digests[key] = hashlib.sha256()
            lengths[key] = 0
            if key in ('boss_frames', 'boss_cheat_keys', 'parrot_wait_entries', 'boss_placements', 'plan'):
                values[key] = []
        elif kind == 'item':
            digests[key].update(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
            digests[key].update(b'\n')
            lengths[key] += 1
            if key in values:
                values[key].append(value)
        else:
            values[key] = value
    return values, {k: dict(rows=lengths[k], sha256=v.hexdigest()) for k, v in digests.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninterrupted', type=Path, required=True)
    parser.add_argument('--resumed', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    errors = []
    full, full_arrays = summarize(args.uninterrupted)
    resumed, resumed_arrays = summarize(args.resumed)
    prefix, _ = summarize(args.prefix)
    for name, trace in [('uninterrupted', full), ('resumed', resumed), ('prefix', prefix)]:
        if trace.get('status') != 'pass' or trace.get('stop') is not None:
            errors.append(name+' did not pass')
        if not trace.get('fight_only'):
            errors.append(name+' is not bounded combat evidence')
    for key, digest in full_arrays.items():
        if digest != resumed_arrays.get(key):
            errors.append('Restored array differs: '+key)
    # Counters, timing and function evidence are scalar report fields, too.
    for key, value in full.items():
        if not isinstance(value, list) and value != resumed.get(key):
            errors.append('Restored field differs: '+key)
    rows = full['boss_frames']
    if rows[:len(prefix['boss_frames'])] != prefix['boss_frames']:
        errors.append('Combat prefix was not retained')
    keys = full.get('boss_cheat_keys', [])
    if [k['letter'] for k in keys] != list('MPKFA'):
        errors.append('Expected exactly one physical MPKFA sequence')
    assistance = [a['start_ms'] for a in full['plan'] if a.get('cheat')]
    health = [f['player']['health'] for f in rows
              if assistance and f['elapsed_ms'] < assistance[0]]
    if len(assistance) != 1 or not health or min(health) >= health[0]:
        errors.append('Missing measured unassisted damage before assistance')
    players = [f['player'] for f in rows]
    # The loaded row is the ordinary Level 10 spawn (750, 7757), before
    # the first coordinate placement enters the arena. Check every arena frame.
    if (any(p['health'] <= 0 or p['level'] != 10 for p in players) or
            any(p['y'] > 7300 for p in players[1:])):
        errors.append('Player death, fall or level departure')
    markers = {f['boss']['player_reset_marker'] for f in rows
               if 'player_reset_marker' in f['boss']}
    if len(markers) != 1:
        errors.append('Original player-reset marker changed')
    initial_actor = players[0]['actor']
    if any(p['actor'] != initial_actor for p in players):
        errors.append('Player actor changed during combat')
    bosses = [f['boss'] for f in rows if f['boss'].get('live')]
    if any(b['health'] > a['health'] for a, b in zip(bosses, bosses[1:])):
        errors.append('Marrow health reset')
    entries = full.get('parrot_wait_entries', [])
    if full['boss_route_functions'].get('0x459830', 0) <= 0 or not entries:
        errors.append('Missing original Parrot wait')
    if any(e['health'] > e['cycle_health']-25 or e['phase'] < 2 for e in entries):
        errors.append('Observed wait contradicts original entry condition')
    physical = dict(full_arrays.get('key_deliveries', {}))
    report = dict(check='level-ten-combat-checkpoint', status='fail' if errors else 'pass',
                  errors=errors, prefix_frames=len(prefix['boss_frames']), frames=len(rows),
                  elapsed_ms=rows[-1]['elapsed_ms'], unassisted_health=sorted(set(health), reverse=True),
                  assistance_letters=''.join(k['letter'] for k in keys),
                  parrot_wait_entries=entries,
                  parrot_wait_calls=full['boss_route_functions'].get('0x459830', 0),
                  identical_arrays=sorted(k for k in full_arrays if full_arrays[k] == resumed_arrays.get(k)),
                  physical_keys=physical)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
