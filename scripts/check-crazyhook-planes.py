"""Focused WWD/native geometry and real-input plane composition acceptance."""
import json
import os
from pathlib import Path
import shutil
import struct
import zlib
import zipfile
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/crazyhook/checks'


def reference_flags():
    import sys
    import capstone
    sys.path.insert(0,str(ROOT))
    from Tests.clawparity.program import claw
    original = claw()  # Verifies the fixed original executable hash.
    decoder = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
    rows = []
    # Flag decisions in original load 4d0450, clamp 4d0a60 and draw 4d0d50.
    for address,operation,value in [(0x4d05bd,'test','0x10'),(0x4d0799,'test','1'),
                                    (0x4d0a77,'and','4'),(0x4d0b06,'and','8'),
                                    (0x4d0d5c,'test','2')]:
        section = next(s for s in original.sections if s.address <= address < s.address+s.size)
        instruction = next(decoder.disasm(section.data[address-section.address:address-section.address+16],address))
        assert instruction.mnemonic == operation and instruction.op_str.endswith(', '+value)
        rows.append(dict(address=hex(address),flag=int(value,0)))
    return dict(sha256=original.sha256,flag_decisions=rows,
                explanation='Load preserves the full word and selects bits 1/16; clamp selects 4/8; draw selects 2. Sampled high bits do not change these original operations.')


def planes():
    out = OUT/'planes'
    out.mkdir(parents=True, exist_ok=True)
    unpacked = out/'input'
    unpacked.mkdir(exist_ok=True)
    names = ['heart_of_the_woods', 'murky_valley', 'creep_diving', 'assassin', 'arcana_v13', 'the_poisonous_caves', 'midnight_espionage']
    paths = {}
    for name in names:
        folder = unpacked/name
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample'/(name+'.zip')) as archive:
            for item in archive.infolist():
                assert (folder/item.filename).resolve().is_relative_to(folder.resolve())
            archive.extractall(folder)
        worlds = sorted(folder.rglob('*.wwd'))
        assert worlds, name
        for world in worlds:
            paths[name+('_lite' if 'Lite' in world.stem else '')] = world
    # Synthetic malformed copies, never attributed to the downloaded originals.
    raw = paths['arcana_v13'].read_bytes()
    decoded = bytearray(raw[:1524]+zlib.decompress(raw[1524:]))
    struct.pack_into('<I',decoded,8,1)
    at = struct.unpack_from('<I',decoded,740)[0]
    count = struct.unpack_from('<I',decoded,at+8)[0]
    at += 32
    mask = None
    for _ in range(count):
        kind,_,w,h = struct.unpack_from('<4I',decoded,at)
        if kind == 3:
            mask = at
            break
        at += 20 if kind == 1 else 40
    assert mask is not None
    for name,offset,value in [('grid',1524+96,4097),('flags',1524+8,0x100),
                              ('mask_size',mask+8,0x10000000),('mask_stride',mask+8,32),
                              ('object_count',1524+128,100001)]:
        data = bytearray(decoded)
        struct.pack_into('<I',data,offset,value)
        path = unpacked/('invalid_'+name+'.wwd')
        path.write_bytes(data)
        paths['invalid_'+name] = path
    report = dict(group='planes', status='fail', marks={}, ipad='Mac Catalyst only; no iPad build or runtime acceptance')
    def save():
        (OUT/'planes.json').write_text(json.dumps(report,indent=2)+'\n')
    report['marks']['original_plane_flags'] = reference_flags()
    save()
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    probe = out/'probe'
    probe.mkdir(exist_ok=True)
    request = probe/'request.json'
    request.write_text(json.dumps({k:str(v) for k,v in paths.items()}))
    (probe/'geometry.json').unlink(missing_ok=True)
    (probe/'native-fault.json').unlink(missing_ok=True)
    session = Session(probe,helper=helper)
    try:
        session.launch(app,{},['--long-trace','--no-paper-startup','--plane-geometry-check',str(request),
            '--save-dir',str(probe/'saves'),'--settings-dir',str(probe/'settings')],start_seconds=180)
        assert not session.failed(), json.loads((probe/'real-speed.json').read_text()).get('error',session.gate())
        result = json.loads((probe/'geometry.json').read_text())
        assert result['status'] == 'pass', result
        assert all(v.get('rejected') for k,v in result['samples'].items() if k.startswith('invalid_'))
        rows = result['samples']
        assert len(rows['heart_of_the_woods']['planes']) == 10
        assert len(rows['murky_valley']['planes']) == 7
        assert rows['creep_diving']['object_count'] == rows['creep_diving_lite']['object_count'] == 25676
        assert rows['assassin']['object_count'] == 11651
        assert max(p['size'][0]*p['size'][1] for p in rows['midnight_espionage']['planes']) == 1105000
        assert rows['arcana_v13']['mask_pixels'] == 4*64*64
        assert rows['the_poisonous_caves']['mask_pixels'] > 0
        assert any(p['tile_size']==[16,16] for p in rows['arcana_v13']['planes'])
        assert any(p['tile_size']==[1,1] for p in rows['creep_diving']['planes'])
        assert rows['arcana_v13']['ladder']['placed'] == 3
        report['marks']['geometry'] = result
        report['marks']['geometry_scope'] = 'Original native loader on private copies with population disabled; only tile assets registered; object counts and words retained by import parser, not a claim all objects executed'
        report['marks']['remaining_services'] = ['Arcana full animation preload separately faulted at the 4cdff0 registry join before geometry; geometry acceptance registers tiles only. Full Arcana Lua/gameplay/presentation remains for the later integration tasks.']
        report['marks']['high_bits'] = 'Original plane load preserves the full flags word. Main=0x1, NoDraw=0x2, wrap=0x4/0x8, auto tile dimensions=0x10. Sampled high bits 0x20/0x40/0x80 do not select additional behavior in original plane loading, clamp or tile drawing; retained, not stripped. Creep Diving control has 0xec and 0xc0.'
        save()
    finally:
        session.close()
        clean_frames(probe)
    for name,count in [('heart_of_the_woods',10),('murky_valley',7)]:
        play = out/name
        play.mkdir(exist_ok=True)
        custom = play/'Custom'
        custom.mkdir(exist_ok=True)
        world = paths[name]
        shutil.copy2(world,custom/world.name)
        if world.with_suffix('').exists():
            shutil.copytree(world.with_suffix(''),custom/world.stem,dirs_exist_ok=True)
        session = Session(play,helper=helper)
        def live(): return json.loads((play/'live.json').read_text())
        def tap(code):
            session.post('key',code);session.run(15)
            assert not session.failed(), session.gate()
        try:
            (play/'native-fault.json').unlink(missing_ok=True)
            for mark in ('before','moved','jumped'):
                for extension in ('json','png'):
                    (play/(mark+'.'+extension)).unlink(missing_ok=True)
            session.launch(app,{},['--custom-dir',str(custom),'--no-paper-startup','--long-trace',
                '--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings')],start_seconds=180)
            session.run(60)
            if live().get('menu_page')==10000: tap(36)
            for _ in range(10):
                if live().get('menu_selected')==11003: break
                tap(125)
            assert live().get('menu_selected')==11003,live()
            tap(36);tap(36)
            assert not live().get('custom_dialog'),live().get('custom_error')
            assert live().get('state_vtable')=='0x50c264',live()
            session.run(45)
            before = session.mark('before')
            session.post('press',124,'down');session.run(20)
            session.post('press',124,'up')
            moved = session.mark('moved')
            session.post('press',49,'down');session.run(10)
            jumped = session.mark('jumped')
            session.post('press',49,'up');session.run(20)
            assert before['player']['x'] != moved['player']['x'],[before['player'],moved['player']]
            assert jumped['player']['y'] < moved['player']['y'],[moved['player'],jumped['player']]
            hashes = before
            assert len(hashes['display_plane_flags'])==count,hashes.get('display_plane_flags')
            assert live()['custom_level']['tile_frame_plane_count'] == count,live()['custom_level']
            assert live()['custom_level']['unresolved_tile_frames'] == [],live()['custom_level']['unresolved_tile_frames']
            assert not session.failed(),session.gate()
            report['marks'][name] = dict(before=before['player'],moved=moved['player'],jumped=jumped['player'],
                plane_flags=hashes['display_plane_flags'],pixels_sha256=hashes['pixels_sha256'],
                loaded=live()['custom_level'],input_transitions=session.transitions())
            save()
        finally:
            session.close();clean_frames(play)
    report['status']='pass'
    save()
    return report


def clean_frames(folder):
    for pattern in ('hud-*.png','frame-*.png'):
        for path in folder.glob(pattern): path.unlink()
