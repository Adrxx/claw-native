"""Read-only dependency planning; no admission, worker launch, or native readiness claim."""
import argparse
import json
import re
from pathlib import Path
from tools.claw.paths import ROOT, FAMILIES, CORPUS, ORIGINAL_SHA256


def address(value):
    return value if isinstance(value, int) else int(value, 16)


def key(value):
    return hex(address(value))


def full_context(entry):
    context = entry.get('compiler_context') or entry.get('source_context') or {}
    return all(address(context.get(k, 0)) == 0x7ff for k in ('input_mask', 'output_mask'))


def context_signature(entry):
    """Compare declared transport contracts, not just presence of full masks."""
    for kind in ('source_context', 'compiler_context'):
        if kind in entry:
            fields = ('input_mask', 'output_mask', 'preserve_mask') if kind == 'source_context' else ('input_mask', 'output_mask')
            return {'kind': kind, **{name: address(entry[kind].get(name, 0)) for name in fields}}
    return None


def ownership(families):
    candidates = {}
    for family in families:
        for entry in family.get('owned', []):
            if isinstance(entry, str):
                entry = {'address': entry}
            candidates.setdefault(key(entry['address']), []).append((family, entry))
    result = {}
    for addr, choices in candidates.items():
        canonical = [c for c in choices if c[0].get('abi') == 'canonical']
        selected = canonical or choices
        ids = {f['id'] for f, _ in selected}
        if len(ids) > 1 and canonical:
            raise ValueError('multiple canonical owners for %s: %s' % (addr, sorted(ids)))
        result[addr] = sorted(selected, key=lambda c: c[0]['id'])[0]
    return result


def cycle_components(nodes, edges):
    """Tarjan components preserve recursion without inventing a topological order."""
    adjacency = {n: set() for n in nodes}
    for edge in edges:
        if edge['to'] in nodes:
            adjacency[edge['from']].add(edge['to'])
    indices, low, stack, active, components = {}, {}, [], set(), []
    def visit(node):
        indices[node] = low[node] = len(indices)
        stack.append(node)
        active.add(node)
        for child in sorted(adjacency[node]):
            if child not in indices:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in active:
                low[node] = min(low[node], indices[child])
        if low[node] == indices[node]:
            component = []
            while True:
                child = stack.pop()
                active.remove(child)
                component.append(child)
                if child == node:
                    break
            if len(component) > 1 or node in adjacency[node]:
                components.append(sorted(component))
    for node in nodes:
        if node not in indices:
            visit(node)
    return components


def build_plan(families, roots, require_source=False, direct=None, unresolved=None, max_nodes=400):
    owners = ownership(families)
    direct, unresolved = direct or {}, unresolved or {}
    pending = [key(r) for r in roots]
    nodes, edges, gaps, fixtures, callbacks = {}, [], [], [], []
    selected = {}
    while pending and len(nodes) < max_nodes:
        addr = pending.pop(0)
        if addr in nodes:
            continue
        match = owners.get(addr)
        if match:
            family, entry = match
            fid = family['id']
            admitted = family.get('evidence', {}).get('level') == 'admitted'
            nodes[addr] = {'family': fid, 'admitted': admitted, 'full_context_declared': full_context(entry), 'context_kind': 'compiler' if 'compiler_context' in entry else 'source' if 'source_context' in entry else 'ordinary'}
            selected[fid] = family
            if not admitted:
                gaps.append({'address': addr, 'family': fid, 'kind': 'unadmitted_dependency'})
            if require_source and not full_context(entry):
                gaps.append({'address': addr, 'family': fid, 'kind': 'owned_full_context_capability'})
            # Whole-family declarations deliberately overapproximate individual entry edges.
            for target, declaration in family.get('callees', {}).items():
                target = key(target)
                if declaration.get('kind') == 'fixture':
                    item = {'family': fid, 'address': target, 'name': declaration.get('name'), 'provider_needed': True, 'physical_device_required': 'unknown', 'fixture_declared': declaration.get('fixture')}
                    if item not in fixtures:
                        fixtures.append(item)
                    continue
                if declaration.get('kind') != 'whole':
                    callbacks.append({'family': fid, 'address': target, 'reason': 'non-whole declaration requires boundary review'})
                    continue
                edges.append({'from': addr, 'to': target, 'kind': 'family_whole_declaration'})
                pending.append(target)
                if require_source and not full_context(declaration):
                    gaps.append({'family': fid, 'address': target, 'kind': 'callee_full_context_declaration'})
                target_owner = owners.get(target)
                if require_source and target_owner and target_owner[0].get('abi') == 'canonical':
                    supplied, required = context_signature(declaration), context_signature(target_owner[1])
                    if supplied is not None and required is not None and supplied != required:
                        gaps.append({'family': fid, 'address': target, 'kind': 'callee_context_contract_mismatch',
                                     'target_family': target_owner[0]['id'], 'supplied': supplied,
                                     'required': required, 'needs_boundary_review': True})
            # Add all owned entries to avoid hiding capability work within a family.
            pending.extend(key(e['address'] if isinstance(e, dict) else e) for e in family.get('owned', []))
        else:
            nodes[addr] = {'family': None, 'admitted': False}
            gaps.append({'address': addr, 'kind': 'missing_owner_boundary'})
        for raw_target in direct.get(addr, []):
            provenance = raw_target.get('provenance', 'supplied_direct_edge') if isinstance(raw_target, dict) else 'supplied_direct_edge'
            target = key(raw_target['target'] if isinstance(raw_target, dict) else raw_target)
            edges.append({'from': addr, 'to': target, 'kind': 'corpus_direct_call', 'provenance': provenance, 'needs_boundary_review': True})
            pending.append(target)
            target_owner = owners.get(target)
            if require_source and match and target_owner:
                caller_family = match[0]
                target_family = target_owner[0]
                declarations = {key(a): d for a, d in caller_family.get('callees', {}).items()}
                declaration = declarations.get(target)
                if (target_family.get('abi') == 'canonical' and
                        target_family['id'] != caller_family['id'] and
                        (not declaration or declaration.get('kind') != 'fixture') and
                        (not declaration or declaration.get('kind') != 'whole' or not full_context(declaration))):
                    gaps.append({'family': caller_family['id'], 'address': target,
                                 'kind': 'required_callee_context_declaration',
                                 'declaration_state': 'missing' if not declaration else 'incomplete',
                                 'provenance': provenance, 'needs_boundary_review': True})
        for reason in sorted(set(unresolved.get(addr, []))):
            callbacks.append({'address': addr, 'reason': reason})
    # Deduplicate planning requests without discarding distinct edge provenance.
    unique_edges = {}
    for edge in edges:
        provenance = edge.pop('provenance', None)
        identity = json.dumps(edge, sort_keys=True)
        saved = unique_edges.setdefault(identity, edge)
        if provenance and provenance not in saved.setdefault('provenance', []):
            saved['provenance'].append(provenance)
    edges = list(unique_edges.values())
    unique_gaps = {}
    for gap in gaps:
        provenance = gap.pop('provenance', None)
        identity = json.dumps(gap, sort_keys=True)
        saved = unique_gaps.setdefault(identity, gap)
        if provenance and provenance not in saved.setdefault('provenance', []):
            saved['provenance'].append(provenance)
    gaps = list(unique_gaps.values())
    callbacks = list({json.dumps(c, sort_keys=True): c for c in callbacks}.values())
    # Per-family recovery jobs are independent: originals supply non-owned callees.
    jobs = []
    for fid, family in sorted(selected.items()):
        relevant = [g for g in gaps if g.get('family') == fid]
        if relevant:
            jobs.append({'family': fid, 'gaps': relevant, 'steps': ['boundary_contract', 'blind_cases', 'seal_and_case_guard', 'translation', 'translator_guard', 'gate'], 'native_callee_admission_blocks_recovery': False})
    return {'schema': 1, 'mode': 'read_only_dry_plan', 'roots': [key(r) for r in roots], 'require_source': require_source, 'nodes': nodes, 'edges': edges, 'cyclic_components': cycle_components(nodes, edges), 'gaps': gaps, 'fixtures': fixtures, 'unresolved_callbacks': callbacks, 'closure': {'complete': not pending, 'scope': 'finite_declared_and_cached_direct_edges_only', 'static_call_graph_verified': False, 'node_limit': max_nodes, 'remaining_frontier': sorted(set(pending) - nodes.keys())}, 'recovery_layers': [jobs] if jobs else [], 'composition': {'status': 'unverified', 'dependency_admissions_required_separately': True, 'unknown_boundaries': any(n['family'] is None for n in nodes.values()), 'playable': False}, 'resources': {'cpu_budget': 4, 'project_writers': 1, 'host_editors': 1, 'gate_publishers': 1}, 'limits': ['Declared ABI and masks are not verified behavior.', 'Family declarations overapproximate entry-specific dependencies.', 'Indirect calls remain unresolved; this is not a proven static DAG.', 'Independent recovery jobs may compare against original callees before native composition.']}


def corpus_edges():
    index_path = CORPUS / 'index.json'
    if not index_path.exists():
        return {}, {}, {'status': 'missing'}
    index = json.loads(index_path.read_text())
    if index.get('sha256') != ORIGINAL_SHA256:
        raise ValueError('corpus fingerprint does not match pinned original')
    direct, unresolved = {}, {}
    for function in index['functions']:
        addr = key(function['entry'])
        direct[addr] = [{'target': key(c), 'provenance': 'cached_index_callee'} for c in function.get('callees', [])]
        asm = CORPUS / 'asm' / ('%08x.asm' % address(addr))
        if asm.exists():
            for line in asm.read_text().splitlines():
                call = re.search(r'\bcall\s+(.+)$', line)
                if call:
                    operand = call.group(1).strip()
                    if re.fullmatch(r'0x[0-9a-fA-F]+', operand):
                        direct[addr].append({'target': key(operand), 'provenance': 'cached_body_direct_call'})
                    else:
                        unresolved.setdefault(addr, []).append('indirect call; target and ABI unresolved')
        else:
            unresolved.setdefault(addr, []).append('cached body listing absent; indirect calls unknown')
    return direct, unresolved, {'status': 'cached_corpus', 'fingerprint_matches': True, 'executable_read': False, 'cache_contents_independently_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roots', nargs='+', required=True)
    parser.add_argument('--require-source', action='store_true')
    parser.add_argument('--max-nodes', type=int, default=400)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.max_nodes < 1:
        parser.error('--max-nodes must be positive')
    if args.out:
        import subprocess
        output = args.out.resolve()
        if ROOT not in output.parents or subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=ROOT).returncode:
            parser.error('--out must be a git-ignored path inside the repository')
    try:
        families = [json.loads(p.read_text()) for p in sorted(FAMILIES.glob('*.json'))]
        direct, unresolved, metadata = corpus_edges()
        plan = build_plan(families, args.roots, args.require_source, direct, unresolved, args.max_nodes)
        plan['corpus'] = metadata
    except (ValueError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps({'mode': plan['mode'], 'nodes': len(plan['nodes']), 'gaps': len(plan['gaps']), 'families': len(plan['recovery_layers'][0]) if plan['recovery_layers'] else 0, 'closure': plan['closure'], 'out': str(args.out) if args.out else None}) if args.out else json.dumps(plan))


if __name__ == '__main__':
    main()
