#!/usr/bin/env python3
"""Negative controls for the original-only Level 12 Sign allowance."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coverage_check', ROOT/'scripts/check-level-object-coverage.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
from Tests.NativeLevels import object_loading


def main():
    report = json.loads((ROOT/'work/object-coverage/levels.json').read_text())
    allow = json.loads((ROOT/'scripts/level-object-coverage-allowlist.json').read_text())
    assert checker.assess(deepcopy(report), deepcopy(allow), [])['status'] == 'pass'
    rejected = []

    def reject(name, changed_report, changed_allow):
        assert checker.assess(changed_report, changed_allow, [])['status'] != 'pass', name
        rejected.append(name)

    changed = deepcopy(report)
    changed['levels'][11]['skipped'][0]['placements'][0]['x'] += 1
    reject('changed placement', changed, deepcopy(allow))
    changed = deepcopy(report)
    row = changed['levels'][11]
    placement = deepcopy(row['skipped'][0]['placements'][-1])
    placement.update(id=9999, record_offset=9999999)
    row['skipped'][0]['placements'].append(placement)
    row['skipped'][0]['count'] += 1
    for key in ('skipped_count', 'placed', 'visited'):
        row[key] += 1
    reject('new placement', changed, deepcopy(allow))
    changed = deepcopy(report)
    source, target = changed['levels'][11], changed['levels'][10]
    target['skipped'] = source['skipped']
    source['skipped'] = []
    source['skipped_count'] = 0
    source['instantiated'] += 3
    target['skipped_count'] = 3
    target['instantiated'] -= 3
    reject('different level', changed, deepcopy(allow))
    changed = deepcopy(report)
    changed['levels'][11]['wwd_sha256'] = '0'*64
    reject('different WWD', changed, deepcopy(allow))
    changed_allow = deepcopy(allow)
    changed_allow[0]['evidence_sha256'] = '0'*64
    reject('stale proof digest', deepcopy(report), changed_allow)
    # Rehashing a stale report must not bypass its provider provenance check.
    proof = json.loads((ROOT/object_loading.EVIDENCE).read_text())
    proof['inputs_sha256']['Tests/NativeMenuBase/trace.py'] = '0'*64
    with tempfile.TemporaryDirectory(prefix='sign-negative-', dir=ROOT/'work') as directory:
        path = Path(directory)/'object-loading.json'
        path.write_text(json.dumps(proof))
        changed_allow = deepcopy(allow)
        changed_allow[0].update(evidence=str(path.relative_to(ROOT)),
                                evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with patch.object(object_loading, 'EVIDENCE', str(path.relative_to(ROOT))):
            reject('stale provider provenance with fresh digest', deepcopy(report), changed_allow)
    changed_allow = deepcopy(allow)
    changed_allow[0]['placements'][0]['x'] += 1
    reject('changed allowance record', deepcopy(report), changed_allow)
    print(json.dumps(dict(status='pass', negative_controls=rejected)))


if __name__ == '__main__':
    main()
