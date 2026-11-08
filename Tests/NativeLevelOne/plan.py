"""Read-only ownership census for an observed Level 1 trace; never admits code."""
import argparse
from Tests.NativeLevels.storage import read_trace, fingerprint
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from Tests.NativeMenuBase.trace import ROOT
from Tests.clawparity import build_inputs


def read(path):
    return read_trace(path) if path.name in ('trace.json', 'trace.json.gz') else json.loads(path.read_text())


def census(trace_path):
    trace = read(trace_path)
    review_path = ROOT/'work/menu-map/final-reviewed-batches.json'
    review = read(review_path)
    menu = read(ROOT/'work/menu-map/trace.json')
    menu_entries = {e['address'] for e in menu['game_functions']}
    claims = defaultdict(list)
    specs = {}
    for path in sorted((ROOT/'Tests/families').glob('*.json')):
        spec = read(path)
        specs[path.stem] = spec
        for entry in spec.get('owned', []):
            if isinstance(entry, dict):
                claims[entry['address']].append(path.stem)
    legacy = {
        '0x46e160': ('light_palette', 'Sources/LightPaletteRuntime.cpp'),
        '0x4c60a0': ('light_palette', 'Sources/LightPaletteRuntime.cpp'),
        '0x4c6fa0': ('light_palette', 'Sources/LightPaletteRuntime.cpp'),
        '0x4c70b0': ('light_palette', 'Sources/LightPaletteRuntime.cpp'),
        '0x4cb5f0': ('world_file', 'Sources/WorldFileRuntime.cpp'),
    }
    codec_entries = {'0x4d5fe0', '0x4d66c0', '0x4d6760', '0x4d6870', '0x4d6890', '0x4d77a0', '0x4d7840', '0x4d78b0', '0x4d85a0', '0x4d86d0', '0x4d86f0', '0x4da080', '0x4da0e0', '0x4da800'}
    # Additional original inflate teardown, Huffman decoding and window flush
    # entries observed after the CRT free boundary. These are zlib internals,
    # covered by the existing native decompressor, not missing game owners.
    codec_entries.update(('0x4d6710','0x4d8560','0x4da5a0','0x4da840',
                          '0x4da880','0x4db030','0x4db050','0x4db190'))
    owners = {}
    rows = []
    for entry in trace['game_functions']:
        if entry['entry_kind'] != 'function':
            continue
        address = entry['address']
        names = claims[address]
        elected = review['addresses'].get(address, {}).get('owner')
        owner = names[0] if len(names) == 1 else elected if elected in names else None
        canonical = [n for n in names if specs[n].get('abi') == 'canonical']
        if owner is None and len(canonical) == 1:
            owner = canonical[0]
        native = review['native_reuse_addresses'].get(address)
        row = dict(address=address, count=entry['count'], phases=entry['phases'],
            new_since_menu=address not in menu_entries, claims=names, owner=owner,
            native_reuse=native)
        if native:
            row.update(classification='native-reuse', reason='Existing menu startup/platform boundary; do not recertify')
        elif address in codec_entries:
            row.update(classification='native-reuse', native_reuse='native zlib adapter',
                reason='Original uncompress and its codec helpers; existing ClawNativeWorld uses native zlib. No library recovery or admission.',
                source_evidence=['Sources/ClawNativeWorld.swift', 'Sources/WorldFileRuntime.h', 'Tests/world_file_codec_oracle.py'])
        elif address in legacy and not canonical:
            legacy_owner, source = legacy[address]
            row.update(classification='owned-but-unadmitted', owner=legacy_owner,
                reason='Existing legacy entry implementation outside current canonical ownership; reuse body and adapt ABI, never count as admitted.',
                source_evidence=[source], source_sha256=fingerprint(ROOT/source))
        elif owner:
            if owner not in owners:
                spec = specs[owner]
                errors = build_inputs.admission_errors(spec)
                gate = spec.get('evidence', {}).get('gate', {})
                owners[owner] = dict(specification=f'Tests/families/{owner}.json',
                    specification_sha256=fingerprint(ROOT/f'Tests/families/{owner}.json'),
                    evidence_level=spec.get('evidence', {}).get('level'),
                    gate_status=gate.get('status'), gate_seed=gate.get('seed'),
                    build_inputs_sha256=gate.get('build_inputs_sha256'), admission_errors=errors,
                    abi=spec.get('abi'), sources=spec.get('sources', []),
                    admitted=spec.get('evidence', {}).get('level')=='admitted' and gate.get('status')=='admitted' and not errors)
            evidence = owners[owner]
            row['classification'] = 'admitted' if evidence['admitted'] else 'owned-but-unadmitted'
            row['reason'] = 'Exact manifest ownership and repository admission-input validation; no new gate run'
        elif 'game-logic-registration' in entry['phases'] and not names:
            row.update(classification='partial',owner='logic_state_registry',
                reason='Existing typed whole-401000 bootstrap and trie/array implementation; no individually owned original-entry ABI. Reuse its bodies and binding data before adding canonical entry coverage.',
                source_evidence=['Sources/LogicStateRegistry.cpp','Sources/LogicStateRegistry.h',
                    'Tests/families/logic_state_registry.json','Tests/logic_state_registry_profile.json'])
        else:
            row.update(classification='partial' if names else 'unowned',
                reason='Conflicting canonical owners require review' if names else 'No canonical owner; review legacy source candidates before recovery')
        rows.append(row)
    return dict(schema=1, trace_sha256=fingerprint(trace_path),
        menu_review_sha256=fingerprint(review_path), status='partial' if trace['stop'] else 'complete',
        stop=trace['stop'], rows=rows, owners=owners,
        counts=dict(Counter(r['classification'] for r in rows)),
        new_functions=sum(r['new_since_menu'] for r in rows),
        legacy_registry_sha256=fingerprint(ROOT/'Sources/LogicStateRegistry.cpp'),
        legacy_registry_profile_sha256=fingerprint(ROOT/'Tests/logic_state_registry_profile.json'),
        limitations=['Only the recorded loading path and input route are covered; unobserved functions and paths are not claimed.',
            'Admission reuse follows the existing manifest validation semantics; historical records without a build fingerprint are not new full-input freshness proof.',
            'Native startup/platform entries are listed separately and are never new recovery work.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, default=ROOT/'work/level-one-map/trace.json')
    parser.add_argument('--output', type=Path, default=ROOT/'work/level-one-map/ownership.json')
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived ownership output must stay under work/')
    result=census(args.trace)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','counts','new_functions','stop')}))


if __name__=='__main__':
    main()
