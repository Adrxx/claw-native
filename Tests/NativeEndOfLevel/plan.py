"""Read-only ownership census for the observed end-of-level trace; never admits code.

Reuses the Level 1 census rules and adds which entries are new since the
retained Level 1 census (work/level-one-map/ownership.json).
"""
import argparse
import json
from pathlib import Path
from Tests.NativeLevelOne.plan import ROOT, census, read, fingerprint

TRACE = ROOT/'work/end-of-level-map/trace.json'
OWNERSHIP = ROOT/'work/end-of-level-map/ownership.json'
LEVEL_ONE_OWNERSHIP = ROOT/'work/level-one-map/ownership.json'


def end_census(trace_path=TRACE):
    result = census(trace_path)
    level_one = read(LEVEL_ONE_OWNERSHIP)
    seen = {r['address'] for r in level_one['rows']}
    for row in result['rows']:
        row['new_since_level_one'] = row['address'] not in seen
        row['end_of_level_phases'] = [p for p in row['phases']
            if p.startswith(('cheat-', 'results-', 'level-two-'))]
    result.update(level_one_ownership_sha256=fingerprint(LEVEL_ONE_OWNERSHIP),
        new_since_level_one=sum(r['new_since_level_one'] for r in result['rows']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, default=TRACE)
    parser.add_argument('--output', type=Path, default=OWNERSHIP)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived ownership output must stay under work/')
    result = end_census(args.trace)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'counts', 'new_functions', 'new_since_level_one', 'stop')}))


if __name__ == '__main__':
    main()
