"""Owner 0x408580 regression: original Level 7 Seagull and HermitCrab near spawn."""
import ctypes as C
import importlib.util
import time
import hashlib
import struct
import sys
import zlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/seagull-crab'
WORLD = ROOT/'work/test-levels/seagull-crab/objects.WWD'


def tables():
    # The four original fallback callers, +8 vtable overrides and CALL sites.
    sys.path.insert(0, str(ROOT))
    from Tests.clawparity.program import claw
    original = claw()
    reviewed = {0x431df0: (0x50c6e4, 0x431ef5), 0x43ad20: (0x50da04, 0x43ae25),
                0x445af0: (0x50ded4, 0x445bf5), 0x456c20: (0x50e504, 0x456d25)}
    def original_bytes(address, length):
        section = next(s for s in original.sections if s.address <= address and address+length <= s.address+len(s.data))
        return section.data[address-section.address:address-section.address+length]
    text = next(s for s in original.sections if s.name == '.text')
    sites = {text.address+i for i, b in enumerate(text.data[:-4]) if b == 0xe8
             and text.address+i+5+struct.unpack_from('<i', text.data, i+1)[0] == 0x408580}
    assert sites == {site for _, site in reviewed.values()}, 'Original fallback call census changed'
    for caller, (vtable, site) in reviewed.items():
        assert struct.unpack('<I', original_bytes(vtable+8, 4))[0] == caller
        assert original_bytes(site, 1) == b'\xe8'
    while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        time.sleep(10)
    spec = importlib.util.spec_from_file_location('level_transport', ROOT/'scripts/check-level-one-transports.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    lib = shared.build()
    base = lib.claw_level_state_base_call_ok
    base.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32]
    base.restype = shared.U32
    direct = lib.claw_level_tail_direct_ok
    direct.argtypes = [C.POINTER(shared.Call), shared.U32, shared.U32]
    direct.restype = shared.U32
    levels = []
    for level in range(1, 15):
        folder = 'one' if level == 1 else 'two' if level == 2 else str(level)
        election = json.loads((ROOT/f'work/native-level-{folder}-join/owners.json').read_text())
        available = set(election['owners']) | set(election['tail_only'])
        assert not election['unresolved'] and '0x408580' in available
        callers = []
        for caller in reviewed:
            if hex(caller) in available:
                q = shared.Call(function=0x408580, receiver=0x61000000, count=1)
                assert base(C.byref(q), caller, caller) == 1, (level, hex(caller))
                assert direct(C.byref(q), caller, 0) == 0, 'Base fallback lost its regression control'
                for field in ('function', 'receiver', 'receiver2', 'count', 'source', 'compiler',
                              'callback_cpu', 'callback_activation', 'x87_count', 'x87_argument', 'x87_state',
                              'x87_operation', 'return_pc', 'transfer_version', 'transfer_kind',
                              'transfer_site', 'caller', 'disposition'):
                    bad = shared.Call.from_buffer_copy(q)
                    setattr(bad, field, 0 if field in ('receiver', 'count') else 1)
                    assert base(C.byref(bad), caller, caller) == 0, (field, level, hex(caller))
                assert base(C.byref(q), caller, caller+1) == 0, 'Foreign receiver override accepted'
                assert base(C.byref(q), 0x497960, caller) == 0, 'Foreign caller accepted'
                callers.append(hex(caller))
        levels.append(dict(level=level, callers=callers))
    return dict(original_sha256=original.sha256, levels=levels,
                original_calls={hex(k): hex(v[1]) for k, v in reviewed.items()})


def play():
    subprocess.run([str(ROOT/'work/test-env/bin/python'), '-m', 'tools.claw.test_level',
                    '--source-level', '7', '--logic', 'Seagull', '--logic', 'HermitCrab', '--logic', 'CrabNest',
                    '--output', str(WORLD)], cwd=ROOT, check=True, capture_output=True)
    # Keep authenticated records and the original geometry; only raise the
    # two placements so their attack/hit boxes meet Claw on this platform.
    sys.path.insert(0, str(ROOT))
    from tools.claw.test_level import unpack_world, word
    raw, planes = unpack_world(WORLD.read_bytes())
    manifest = json.loads(WORLD.with_suffix('.json').read_text())
    action = next(p for p in planes if p['flags'] & 1)
    at = word(raw, action['header']+140)
    for obj, row in zip(action['objects'], manifest['objects']):
        dy = -120 if obj['logic'] == 'Seagull' else -40 if obj['logic'] == 'HermitCrab' else 0
        struct.pack_into('<i', raw, at+24, obj['y']+dy)
        row['y'] += dy
        if obj['logic'] in ('HermitCrab', 'CrabNest'):
            # These logics store absolute patrol/activation bounds in userRect1.
            dx = obj['x']-row['source_x']
            total_dy = row['y']-row['source_y']
            for index, delta in ((51, dx), (52, total_dy), (53, dx), (54, total_dy)):
                value = struct.unpack_from('<i', raw, at+index*4)[0]
                if value:
                    struct.pack_into('<i', raw, at+index*4, value+delta)
                    row['translated_words'].append(index)
        row['combat_height_offset'] = dy
        row['record_sha256'] = hashlib.sha256(raw[at:at+len(obj['record'])]).hexdigest()
        at += len(obj['record'])
    offset = word(raw, 736)
    packed = bytes(raw[:offset])+zlib.compress(raw[offset:])
    WORLD.write_bytes(packed)
    manifest['output_sha256'] = hashlib.sha256(packed).hexdigest()
    WORLD.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
    out = OUT/'run'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    session = Session(out, helper=build_helper(ROOT/'work/cheat-codes/post-window-input'))
    def read(name):
        try:
            return json.loads((out/name).read_text())
        except (OSError, ValueError):
            return {}
    marks = []
    report = dict(check='seagull-crab', status='fail')
    try:
        report['tables'] = tables()
        derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT/'work/MacCatalyst'))
        session.launch(derived/'Build/Products/Release-maccatalyst/Claw.app',
                       dict(CLAW_LOCAL_TEST_LEVELS='1', CLAW_TRACE_DEPTH='128'),
                       ['--test-level', str(WORLD), '--menu-live-check', str(out),
                        '-ClawCheckDirectory', str(out), '--no-paper-startup', '--save-dir', str(out/'saves')])
        session.run(1)
        marks.append(session.mark('spawn'))
        # Confirm real input delivery, then let both enemies attack in range.
        session.post('press', 124, 'down')
        session.run(45)
        session.post('press', 124, 'up')
        for index in range(40):
            session.run(30)
            if session.failed():
                raise RuntimeError(read('real-speed.json').get('error', 'frame fault'))
            marks.append(session.mark(f'combat-{index}'))
        players = [m['player'] for m in marks if m]
        assert len(players) == 41 and all(p['level'] == 7 for p in players), 'Level 7 marks missing'
        assert any(0 < p['health'] < 100 for p in players), 'Enemy damage not exercised'
        assert session.transitions().get('39:down', 0) and session.transitions().get('39:up', 0), 'Real input missing'
        counts = read('live-state.json').get('transports', {})
        assert counts.get('state-base-direct-431df0', 0) > 0, 'Crab inherited 408580 call not exercised'
        assert marks[-1]['invoke_counts'].get('408580', 0) > 0, 'Shared base handler never ran'
        assert marks[-1]['invoke_counts'].get('487f20', 0) > 0, 'Seagull never entered its dive'
        report['status'] = 'pass'
    except Exception as error:
        report['error'] = str(error)
    finally:
        report.update(marks=marks, live=read('live.json'), state=read('live-state.json'),
                      execution=read('real-speed.json'), input=session.input_state())
        session.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in ('check', 'status', 'error')}))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(play())
