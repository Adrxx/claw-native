"""Offline native audio and muted real-input package acceptance."""
import json
import hashlib
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time
import wave
import zipfile
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/crazyhook/checks'


def clean(folder):
    for pattern in ('hud-*.png','frame-*.png'):
        for path in folder.glob(pattern): path.unlink()


def clear_run_logs(folder):
    for name in ('real-speed.json','native-fault.json','trace.txt','sound-lifecycle-fault.json'):
        (folder/name).unlink(missing_ok=True)


def note_frames(data, frames=176400):
    # Independent check of the source event clock against the native synth log.
    at = data.index(b'EVNT')
    stream = data[at+8:at+8+int.from_bytes(data[at+4:at+8],'big')]
    at = tick = end = 0
    notes = []
    def byte():
        nonlocal at
        value = stream[at];at += 1
        return value
    def variable():
        value = 0
        for _ in range(4):
            part = byte();value = value*128+(part&127)
            if part < 128: return value
        raise AssertionError('Invalid XMI variable')
    while at < len(stream):
        status = byte()
        if status < 128: tick += status;continue
        if status == 255:
            kind = byte();length = variable();at += length
            if kind == 47: break
        elif status in (240,247):
            length = variable();at += length
        else:
            a = byte();b = byte() if status>>4 not in (12,13) else 0
            if status>>4 == 9:
                duration = variable();end = max(end,tick+duration)
                if b: notes.append((tick,status&15,a))
    ticks = max(tick,end)
    assert ticks > 0
    result = []
    for loop in range(int(frames/(ticks*44100/120))+1):
        for tick,channel,key in notes:
            frame = int(tick*44100/120+0.5)+loop*int(ticks*44100/120+0.5)
            if frame < frames: result.append([frame,channel,key])
    return result


def audio():
    # The offline synth and app checks share the build's heavy-job lane.
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check_audio()


def check_audio():
    out = OUT/'audio'
    out.mkdir(parents=True,exist_ok=True)
    report = dict(group='audio',status='fail',marks={},ipad='Mac Catalyst only; physical iPad not tested')
    report_path = OUT/'audio.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    worlds = {}
    for name in ('las_almenas','christmas_eve_adventure','the_poisonous_caves','flying_carpet_ride'):
        folder = out/'input'/name
        folder.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample'/(name+'.zip')) as archive:
            for item in archive.infolist():
                assert (folder/item.filename).resolve().is_relative_to(folder.resolve())
            archive.extractall(folder)
        worlds[name] = next(p for p in folder.rglob('*') if p.suffix.lower()=='.wwd')
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    probe = out/'probe'
    probe.mkdir(exist_ok=True)
    request = probe/'request.json'
    request.write_text(json.dumps({k:str(v) for k,v in worlds.items()}))
    (probe/'audio-packages.json').unlink(missing_ok=True)
    clear_run_logs(probe)
    while subprocess.run(['pgrep','-f','^/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -project Claw.xcodeproj'],capture_output=True).returncode == 0:
        time.sleep(1)
    session = Session(probe,helper=helper)
    try:
        session.launch(app,{'CLAW_AUDIO_EVIDENCE':'1'},['--long-trace','--no-paper-startup','--audio-package-check',str(request),
            '--save-dir',str(probe/'saves'),'--settings-dir',str(probe/'settings')],start_seconds=180)
        assert not session.failed(),session.gate()
        result = json.loads((probe/'audio-packages.json').read_text())
        assert result['status']=='pass',result
        rows = result['samples']
        for name in worlds: assert rows[name]['restored'],rows[name]
        assert {t['name'] for t in rows['christmas_eve_adventure']['tracks']} == {'LEVEL','PLAY','BOSS','POWERUP'}
        assert {t['name'] for t in rows['the_poisonous_caves']['tracks']} == {'CUSTOM','CUSTOM2'}
        assert rows['las_almenas']['sounds']
        for name in worlds:
            source_sounds = {}
            for path in worlds[name].with_suffix('').rglob('*'):
                relative = path.relative_to(worlds[name].with_suffix('')).as_posix().upper()
                if path.suffix.upper()!='.WAV' or not relative.startswith(('SOUNDS/','LEVEL/')): continue
                folder,leaf = relative.split('/',1)
                key = ('CUSTOM_' if folder=='SOUNDS' else 'LEVEL_')+leaf[:-4].replace('/','_')
                source_sounds[key] = path
            for sound in rows[name]['sounds']:
                with wave.open(str(source_sounds[sound['name']]),'rb') as source: pcm = source.readframes(source.getnframes())
                assert hashlib.sha256(pcm).hexdigest()==sound['pcm_sha256'],sound
            for track in rows[name]['tracks']:
                rendered = json.loads((probe/track['render']).read_text())
                assert rendered['status']=='done' and rendered['nonzero_samples']>0,rendered
                path = worlds[name].with_suffix('')/'MUSIC'/((track['name'] if track['name']!='PLAY' else 'LEVEL')+'.XMI')
                path = next(p for p in path.parent.iterdir() if p.name.upper()==path.name.upper())
                assert rendered['note_on_frames'] == note_frames(path.read_bytes()), track
        assert rows['flying_carpet_ride']['sounds']==[] and rows['flying_carpet_ride']['tracks']==[]
        assert rows['las_almenas-ani']['events']==[{'milliseconds':0,'sound':'LEVEL_SPRINGBOX'}]
        report['marks']['offline_packages'] = result
    finally:
        session.close();clean(probe)
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    play = out/'play'
    play.mkdir(exist_ok=True)
    custom = play/'Custom'
    custom.mkdir(exist_ok=True)
    for name in ('las_almenas','flying_carpet_ride'):
        source = worlds[name]
        shutil.copy2(source,custom/source.name)
        if source.with_suffix('').exists(): shutil.copytree(source.with_suffix(''),custom/source.stem,dirs_exist_ok=True)
    session = Session(play,helper=helper)
    clear_run_logs(play)
    def live(): return json.loads((play/'live.json').read_text())
    def tap(key):
        session.post('key',key);session.run(15)
        assert not session.failed(),session.gate()
    try:
        session.launch(app,{'CLAW_AUDIO_EVIDENCE':'1'},['--custom-dir',str(custom),'--no-paper-startup','--long-trace',
            '--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings')],start_seconds=180)
        session.run(60)
        for name in ('las_almenas','flying_carpet_ride'):
            if live().get('menu_page')==10000: tap(36)
            for _ in range(10):
                if live().get('menu_selected')==11003: break
                tap(125)
            tap(36)
            wanted = worlds[name].name
            for _ in range(10):
                state = live()
                if state['custom_files'][state['custom_selected']] == wanted: break
                tap(125)
            tap(36)
            assert not live().get('custom_dialog'),live().get('custom_error')
            assert live().get('state_vtable')=='0x50c264',live()
            session.run(45)
            before = session.mark(name+'-before')
            session.post('press',124,'down');session.run(20);session.post('press',124,'up')
            moved = session.mark(name+'-moved')
            assert before['player']['x'] != moved['player']['x'],[before,moved]
            evidence = live()['custom_level']
            music_events = moved['music_events']['tail']
            initialized = [e for e in music_events if e.get('service')=='initialize']
            assert moved['audio_output']['muted'],moved['audio_output']
            assert moved['music_manager'][7] and initialized,music_events
            if name=='las_almenas':
                assert evidence['package_sounds'] and 'PLAY' in evidence['package_music'],evidence
                assert any(p['type']=='ANI' for p in evidence['package_images']),evidence
                las_track = next(p for p in worlds[name].with_suffix('').rglob('*') if p.as_posix().upper().endswith('/MUSIC/LEVEL.XMI'))
                las_sha = hashlib.sha256(las_track.read_bytes()).hexdigest()
                assert initialized[-1]['sha256']==las_sha,initialized
            else: assert evidence.get('package_sounds',[])==[] and evidence.get('package_music',[])==[],evidence
            if name=='flying_carpet_ride': assert initialized[-1]['sha256']!=las_sha,initialized
            report['marks'][name] = dict(loaded=evidence,before=before['player'],moved=moved['player'],
                audio=dict(manager=moved['music_manager'],events=music_events,output=moved['audio_output']))
            for key in [46,35,1,8,32,37,37,16]: tap(key)
            assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',10),live()
            for _ in range(10):
                if session.wait(lambda:live().get('state_vtable')!='0x50c0c4',12): break
                tap(36)
            assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
            assert live()['custom_level'].get('unloaded'),live()
        report['marks']['input_transitions'] = session.transitions()
        assert session.transitions().get('39:down',0)>=2
        report['status']='pass'
    finally:
        session.close();clean(play)
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report
