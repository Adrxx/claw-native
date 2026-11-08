#!/usr/bin/env python3
"""Diagnose the seven startup/dialog context obligations without executing code.

A passing diagnosis validates original CALL sites and current source witnesses.
It does not exempt these calls, prove native-root closure, or admit a provider.
The original really takes these edges; the app replaces its startup and dialogs.
Whether any other app route can reach the retained bodies remains an obligation
for the complete closure checker.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def witness(path, start, stop, required):
    """Retain source locations/hashes, never a copy of translated code."""
    raw = (ROOT / path).read_bytes()
    text = raw.decode()
    first = text.index(start)
    last = text.index(stop, first + len(start))
    selected = text[first:last]
    for token in required:
        if token not in selected:
            raise ValueError(f'Native/source witness changed in {path}: {token}')
    return dict(path=path, source_sha256=sha(raw),
                first_line=text.count('\n', 0, first) + 1,
                last_line=text.count('\n', 0, last) + 1,
                range_sha256=sha(selected.encode()))


def check():
    spec = importlib.util.spec_from_file_location('closure', ROOT / 'scripts/check-call-closure.py')
    closure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(closure)
    program = closure.profile('claw-v1.0')
    graph = closure.Graph(program, set())
    owners = closure.manifests()
    sites = [(0x4251f0, 0x4251fa, 0x50257f)] + [
        (0x49b730, site, 0x546d40 if site == 0x49b7d7 else 0x546d34)
        for site in (0x49b765, 0x49b780, 0x49b7b8, 0x49b7d7, 0x49b7ee, 0x49b807)]
    edges = []
    for caller, site, target in sites:
        instruction = next(graph.decoder.disasm(graph.bytes(site, 15), site, count=1))
        operand = instruction.operands[0]
        actual = (operand.imm if operand.type == closure.X86_OP_IMM else
                  operand.mem.disp if operand.type == closure.X86_OP_MEM and
                  not operand.mem.base and not operand.mem.index else None)
        if instruction.mnemonic != 'call' or actual != target:
            raise ValueError(f'Original CALL changed at {site:#x}')
        manifest, owned = owners[(program.name, caller)]
        reader = closure.SourceShapes(ROOT, manifest, import_slots=program.imports)
        edge = dict(caller=caller, site=site, target=target, kind='call')
        extracted = reader.edge(edge, owned, instruction.size)
        if extracted is None:
            raise ValueError(f'No current caller witness at {site:#x}')
        shape, evidence = extracted
        variants = shape.get('variants', [shape])
        contextual = [v for v in variants if v.get('source') and
                      bool(v.get('callback')) == (caller == 0x49b730)]
        if len(contextual) != 1 or contextual[0]['return_pc'] != site + instruction.size:
            raise ValueError(f'Contextual CALL evidence changed at {site:#x}')
        selected = contextual[0]
        expected_argc, expected_pop = (1, 4) if caller == 0x4251f0 else (2, 8)
        if selected['argc'] != expected_argc or selected['return_pop'] != expected_pop:
            raise ValueError(f'Original caller shape changed at {site:#x}')
        edges.append(dict(original_site=dict(edge, size=instruction.size,
            bytes_sha256=sha(instruction.bytes)), family=manifest['id'],
            import_name=program.imports.get(target), caller_shape=selected,
            source_evidence=evidence, disposition='unresolved-native-root-boundary',
            original_impossible=False, provider_servable='unproved'))

    evidence = {
        'native_application_allocation': witness('Sources/ClawNativeScene.swift',
            'applicationToken = heap.allocate(bytes: UInt32(CLAW_ORIGINAL_APPLICATION_BYTES))',
            'let nativeVT = heap.allocate(bytes: 16)',
            ['baseEntry(0x4254a0, applicationToken, [])', 'app[2] = errorReceiver']),
        'resource_host_initialization': witness('Sources/ClawNativeMenuResources.swift',
            'init(heap:ClawTokenHeap,archiveURL:URL,metadata:',
            'if heap.lookupBytes(0x01ff0000,count:0x20000) == nil',
            ['host.initialize(to:ClawHost())', '.service(q.pointee,request:q)']),
        'callback_branch': witness('Sources/PlayerCacheApplicationCanonical.cpp',
            'uint32_t changePlayerDialogProc(', 'uint32_t populatePlayerList(',
            ['run.host.callbackCPU ? changePlayerDialogWithCPU(run, arguments) : handleChangePlayerDialog(run, arguments)']),
        'disabled_without_native_dialog': witness('Sources/ClawNativeMenuInterface.swift',
            'private func disableUnavailableMenuItems()', 'func enter(previous:',
            ['if showPlayers == nil {unavailable += [13001]}']),
        'native_player_command': witness('Sources/ClawNativeMenuInterface.swift',
            'if command.wParam == 0x8090,command.lParam == 4,let showPlayers',
            'if command.wParam == 0x800e', ['playersActive = true;showPlayers();return']),
        'native_player_sheet': witness('App/ClawApp.swift',
            'menu.showPlayers = ', 'menu.postedCommandsDelivered = ',
            ['PlayersState(choices:menu.playerChoices,selected:menu.selectedPlayer)']),
        'native_player_result': witness('Sources/ClawNativeMenuInterface.swift',
            'func finishPlayerDialog(cancelled:Bool)', '// USERNEW reads buffers',
            ['claw_v13_profile_close_result(cancelled ? 1:0)', 'put(0x52545c,result)',
             'resources.invoke(0x42bf90,base.applicationToken,[record])']),
    }
    resource_text = (ROOT / 'Sources/ClawNativeMenuResources.swift').read_text()
    assignments = [i for i, line in enumerate(resource_text.splitlines(), 1)
                   if re.search(r'host\.pointee\.callbackCPU\s*=(?!=)', line)]
    # An added activation invalidates this diagnosis; it would require checking
    # the issuing host, identity/lifetime, descendants and native OS providers.
    if assignments:
        raise ValueError(f'Resource host now assigns callbackCPU at {assignments}')
    return dict(check='call-closure-context-diagnosis', status='pass',
        contract='Pass means these original/current-source witnesses were found; it is not call-closure success.',
        profile=program.name, original_sha256=program.sha256, edges=edges,
        native_source_witnesses=evidence, resource_callback_assignments=assignments,
        closure_complete=False, unresolved_edges=len(edges), impossible_exemptions=0,
        obligations=[
            'Classify native startup roots separately from admitted static/MFC inventory; prove which original roots the app replaces.',
            'Follow native player-command replacement and callback activation provenance before pruning any DialogProc variant.',
            'Check all remaining direct, virtual and callback entrants; these local witnesses do not prove whole-program unreachability.',
            'If a retained callback is app-reachable, implement authenticated activation plus EndDialog/GetDlgItem providers; do not only relax the transport gate.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/call-closure/context-boundaries.json')
    args = parser.parse_args()
    try:
        result = check()
    except Exception as error:
        result = dict(check='call-closure-context-diagnosis', status='fail',
                      error=f'{type(error).__name__}: {error}', closure_complete=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('edges', 'native_source_witnesses', 'obligations')}))
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
