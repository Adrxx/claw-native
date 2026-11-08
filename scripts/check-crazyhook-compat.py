"""Focused native CrazyHook checks. Each group owns its own evidence."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time
import zlib
import zipfile
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/crazyhook/checks'


def clean_frames(folder):
    # Keep the six named input marks; discard routine HUD/frame dumps after
    # their measurements have been retained in JSON.
    for pattern in ('hud-*.png','frame-*.png'):
        for path in folder.glob(pattern): path.unlink()


def png_evidence():
    census = json.loads((ROOT/'work/crazyhook/features.json').read_text())
    results = {}
    for name, files in census['features']['png-files']['evidence'].items():
        sample = next(s for s in census['samples'] if s['name'] == name)
        with zipfile.ZipFile(ROOT/sample['archive']) as archive:
            paths = {p.upper():p for p in archive.namelist()}
            scripts = '\n'.join(archive.read(p).decode('latin1') for p in archive.namelist() if p.lower().endswith('.lua')).upper()
            image_sets, tile_uses = set(), set()
            for path in archive.namelist():
                if not path.lower().endswith('.wwd'): continue
                source = archive.read(path)
                data = source[:1524]+zlib.decompress(source[1524:])
                for i in range(struct.unpack_from('<I',source,732)[0]):
                    h = 1524+160*i
                    count, objects, to, io, oo = struct.unpack_from('<IIIII',data,h+124)
                    sets = data[io:].split(b'\0',count)[:count]
                    width,height = struct.unpack_from('<II',data,h+96)
                    for tile in struct.unpack_from('<'+'i'*(width*height),data,to):
                        for tileset in sets: tile_uses.add((tileset.decode('latin1').upper(),tile))
                    at = oo
                    for _ in range(objects):
                        words = struct.unpack_from('<71I',data,at);at += 284
                        values = []
                        for length in words[1:5]:
                            values.append(data[at:at+length].rstrip(b'\0').decode('latin1').upper());at += length
                        image_sets.add(values[2])
            rows = []
            for path in files:
                stem = path.rsplit('.',1)[0]
                parts = stem.upper().split('/')[1:]
                group = '_'.join((['CUSTOM'] if parts[0]=='IMAGES' else ['LEVEL'] if parts[0]=='LEVEL' else [])+parts[1:-1])
                variants = [paths[stem.upper()+'.'+ext] for ext in ('PID','BMP') if stem.upper()+'.'+ext in paths]
                row = dict(png=path, accepted_siblings=variants, explicit_png_reference=path.rsplit('/',1)[-1].upper() in scripts,
                           object_group_reference=group in image_sets, script_group_reference=group in scripts)
                if parts[0]=='TILES':
                    import re
                    numeric = re.search(r'\d+',parts[-1])
                    row['tile_referenced'] = bool(numeric and (parts[-2],int(numeric[0])) in tile_uses)
                rows.append(row)
            results[name] = rows
    return dict(registry='Published/retail image registry recognizes PID, RID, BMP, PCX; PNG is preserved but not registered',
                limit='Static references do not prove that every script branch or asset executes',samples=results)


def assets():
    out = OUT/'assets'
    out.mkdir(parents=True, exist_ok=True)
    samples = ROOT/'work/custom-levels/crazyhook-sample'
    unpacked = out/'input'
    unpacked.mkdir(exist_ok=True)
    names = ['cannonballin', 'flying_carpet_ride', 'heart_of_the_woods', 'just_keep_calm', 'murky_valley']
    worlds = {}
    for name in names:
        folder = unpacked/name
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(samples/(name+'.zip')) as archive:
            for item in archive.infolist():
                target = (folder/item.filename).resolve()
                assert target.is_relative_to(folder.resolve()), item.filename
            archive.extractall(folder)
        worlds[name] = next(folder.rglob('*.wwd'))
    # Clearly synthetic namespace fixture, never attributed to a downloaded map.
    fixture = unpacked/'synthetic'
    fixture.mkdir(exist_ok=True)
    synthetic = fixture/'Synthetic Assets.wwd'
    shutil.copy2(worlds['cannonballin'],synthetic)
    source = worlds['cannonballin'].with_suffix('')/'IMAGES/SEATREAT/FRAME001.PID'
    for path in ['IMAGES/ONE/FRAME002.PID','IMAGES/ONE/FRAME010.PID','IMAGES/TWO/FRAME002.PID','LEVEL/SPLASH/FRAME001.PID']:
        to = synthetic.with_suffix('')/path
        to.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,to)
    worlds['synthetic'] = synthetic
    report = dict(group='assets', status='fail', marks={}, errors=[], ipad='Shared import code exercised on Mac Catalyst; physical iPad not tested')
    report['marks']['png_investigation'] = png_evidence()
    (OUT/'assets.json').write_text(json.dumps(report,indent=2)+'\n')
    while subprocess.run(['pgrep','-f','^/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -project Claw.xcodeproj'],capture_output=True).returncode == 0:
        time.sleep(10)
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    probe = out/'probe'
    probe.mkdir(exist_ok=True)
    request = probe/'request.json'
    request.write_text(json.dumps({k:str(v) for k,v in worlds.items()}))
    (probe/'packages.json').unlink(missing_ok=True)
    session = Session(probe,helper=helper)
    try:
        session.launch(app,{},['--long-trace','--no-paper-startup','--asset-package-check',str(request),'--save-dir',str(probe/'saves'),'--settings-dir',str(probe/'settings')],start_seconds=180)
        assert not session.failed(), json.loads((probe/'real-speed.json').read_text()).get('error')
        result = json.loads((probe/'packages.json').read_text())
        assert result['status'] == 'pass', result
        report['marks']['packages'] = result
        fixture = result['samples']['synthetic']['mapped']
        assert sorted(i['frame'] for i in fixture if i['name']=='CUSTOM_ONE') == [2,10], fixture
        assert [i['frame'] for i in fixture if i['name']=='CUSTOM_TWO'] == [2], fixture
        report['marks']['duplicate_filenames_and_numeric_ids'] = True
    finally:
        session.close()
        clean_frames(probe)
    # Import in the app uses the same security-scoped entry point as Files and
    # the picker. Both maps are played in ONE session, crossing menu teardown.
    play = out/'play'
    play.mkdir(exist_ok=True)
    custom = play/'Custom'
    custom.mkdir(exist_ok=True)
    for name in ('cannonballin','flying_carpet_ride'):
        source = worlds[name]
        shutil.copy2(source,custom/source.name)
        if source.with_suffix('').exists():
            shutil.copytree(source.with_suffix(''), custom/source.stem,dirs_exist_ok=True)
    session = Session(play,helper=helper)
    def live():
        return json.loads((play/'live.json').read_text())
    def tap(code):
        session.post('key',code)
        session.run(15)
        assert not session.failed(), session.gate()
    def picker():
        if live().get('menu_page') == 10000:
            tap(36)
        for _ in range(10):
            if live().get('menu_selected') == 11003: break
            tap(125)
        assert live().get('menu_selected') == 11003, live()
        tap(36)
        assert live().get('custom_dialog'), live()
    try:
        session.launch(app,{},['--custom-dir',str(custom),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace'])
        session.run(60)
        for index,name in enumerate(('cannonballin','flying_carpet_ride')):
            picker()
            if index: tap(125)
            tap(36)
            assert not live().get('custom_dialog'), live().get('custom_error')
            assert live().get('custom_flag') == 1 and live().get('state_vtable') == '0x50c264', live()
            session.run(45)
            before = session.mark(name+'-before')
            session.post('press',124,'down');session.run(20)
            session.post('press',124,'up')
            moved = session.mark(name+'-moved')
            session.post('press',49,'down');session.run(10)
            jumped = session.mark(name+'-jumped')
            session.post('press',49,'up');session.run(20)
            assert before['player']['x'] != moved['player']['x'], [before['player'],moved['player']]
            assert jumped['player']['y'] < moved['player']['y'], [moved['player'],jumped['player']]
            assert not session.failed(), session.gate()
            evidence = live()['custom_level']
            assert evidence['reads'] >= 3, evidence
            if index == 0:
                assert any(i['name']=='CUSTOM_SEATREAT' for i in evidence['package_images']), evidence
            else:
                assert evidence['package_files'] == 0 and evidence['package_images'] == [], evidence
            report['marks'][name] = dict(before=before['player'],moved=moved['player'],jumped=jumped['player'],loaded=evidence)
            for code in [46,35,1,8,32,37,37,16]:
                tap(code)  # Owner-approved MPSCULLY, never finish by play.
            assert session.wait(lambda: live().get('state_vtable') == '0x50c0c4',10), live()
            for _ in range(10):
                if session.wait(lambda: live().get('state_vtable') != '0x50c0c4',12): break
                tap(36)
            assert session.wait(lambda: live().get('menu_page') in (10000,10001),20), live()
            assert live()['custom_level'].get('unloaded'), live()['custom_level']
            report['marks'][name]['completion'] = 'MPSCULLY, results, menu; package unmounted'
        report['marks']['input_transitions'] = session.transitions()
        assert session.transitions().get('39:down',0) >= 2 and session.transitions().get('32:down',0) >= 2
        report['status'] = 'pass'
    finally:
        session.close()
        clean_frames(play)
        (OUT/'assets.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group',required=True,choices=['diagnostics','persistence','presentation','assets','planes','audio','lua','checkpoints','gameplay','palettes','bindings'])
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        if args.group == 'diagnostics':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_diagnostics',ROOT/'scripts/check-crazyhook-diagnostics.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.diagnostics()
        elif args.group == 'persistence':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_persistence',ROOT/'scripts/check-crazyhook-persistence.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.persistence()
        elif args.group == 'presentation':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_presentation',ROOT/'scripts/check-crazyhook-presentation.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.presentation()
        elif args.group == 'bindings':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_bindings',ROOT/'scripts/check-crazyhook-bindings.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.bindings()
        elif args.group == 'palettes':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_palettes',ROOT/'scripts/check-crazyhook-palettes.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.palettes()
        elif args.group == 'gameplay':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_gameplay',ROOT/'scripts/check-crazyhook-gameplay.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.gameplay()
        elif args.group == 'checkpoints':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_checkpoints',ROOT/'scripts/check-crazyhook-checkpoints.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.checkpoints()
        elif args.group == 'lua':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_lua',ROOT/'scripts/check-crazyhook-lua.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.lua()
        elif args.group == 'audio':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_audio',ROOT/'scripts/check-crazyhook-audio.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.audio()
        elif args.group == 'planes':
            import importlib.util
            spec = importlib.util.spec_from_file_location('crazyhook_planes',ROOT/'scripts/check-crazyhook-planes.py')
            module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            report = module.planes()
        else:
            report = assets()
    except Exception as error:
        path = OUT/(args.group+'.json')
        report = json.loads(path.read_text()) if path.exists() else dict(group=args.group,marks={})
        report.update(status='fail',error=str(error))
        path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],report=str(OUT/(args.group+'.json')))))
    return report['status'] != 'pass'

if __name__ == '__main__':
    raise SystemExit(main())
