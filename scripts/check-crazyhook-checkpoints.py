"""Per-map CrazyHook super-checkpoint lifecycle with confirmed real window input."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'work/crazyhook/checks'


def checkpoints():
    if os.environ.get('CLAW_BUILD_LOCK_HELD') == '1': return _checkpoints()
    with open(ROOT/'work/.claw-app-build.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _checkpoints()


def _checkpoints():
    out = OUT/'checkpoints'
    out.mkdir(parents=True,exist_ok=True)
    report = dict(group='checkpoints',status='fail',marks={},ipad='Not tested on a physical iPad')
    target = OUT/'checkpoints.json'
    def record(): target.write_text(json.dumps(report,indent=2)+'\n')
    record()
    worlds = {}
    hashes = {}
    for name in ['just_keep_calm','las_almenas','arcana_v1_3','city_in_the_depth']:
        archive = ROOT/'work/custom-levels/crazyhook-sample'/({'arcana_v1_3':'arcana_v13','city_in_the_depth':'citd'}.get(name,name)+'.zip')
        hashes[str(archive)] = hashlib.sha256(archive.read_bytes()).hexdigest()
        folder = out/'input'/name
        folder.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist(): assert (folder/n).resolve().is_relative_to(folder.resolve())
            z.extractall(folder)
        worlds[name] = next(p for p in folder.rglob('*') if p.suffix.lower()=='.wwd')
    helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    saves = out/'saves'
    # Reproducible disposable check stores only, never the owner's profiles.
    if saves.exists(): shutil.rmtree(saves)
    session = None
    def launch(name,extra=()):
        nonlocal session
        if session: session.close()
        folder = out/name;folder.mkdir(exist_ok=True)
        session = Session(folder,helper=helper)
        session.launch(app,{},['--no-paper-startup','--stationary-cursor','--long-trace',
            '--save-dir',str(saves),'--settings-dir',str(out/'settings'),
            '--custom-dir',str(worlds[current].parent),'--crazyhook-checkpoint-check','--custom-checkpoint-check','-ClawCheckDirectory',str(folder),*extra],start_seconds=180)
        run(120)
    def live(): return json.loads((session.out/'live.json').read_text())
    def run(frames):
        result = session.run(frames)
        assert result.get('status') != 'fail',result
    def tap(code): session.post('key',code);run(4)
    def picker():
        if live().get('menu_page') == 10000: tap(36)
        for _ in range(12):
            if live().get('menu_selected') == 11003: break
            tap(125)
        assert live().get('menu_selected') == 11003,live()
        tap(36)
        assert live().get('custom_dialog'),live()
    def profile():
        p=saves/'CLAW.USR'
        return p.read_bytes() if p.exists() else None
    try:
        current = 'just_keep_calm'
        probe = out/'probe';probe.mkdir(exist_ok=True)
        request=probe/'request.json';request.write_text(json.dumps({k:str(v) for k,v in worlds.items()}))
        launch('probe',['--checkpoint-store-check',str(probe/'store.json'),'--checkpoint-package-check',str(request)])
        report['marks']['storage_contract'] = json.loads((probe/'store.json').read_text())
        ownership = json.loads((probe/'ownership.json').read_text())
        assert ownership['arcana_v1_3']['script_owned'] and ownership['city_in_the_depth']['script_owned'],ownership
        assert not ownership['just_keep_calm']['script_owned'] and not ownership['las_almenas']['script_owned'],ownership
        assert not list((saves/'CustomSaves').glob('*'))
        report['marks']['script_owned_preflight_no_automatic_store'] = ownership
        original_profile = profile()
        assert original_profile, "retail fixture profile was not written"
        record()
        for current,slot in [('just_keep_calm',1),('las_almenas',2)]:
            launch(current+'-save')
            picker();tap(36)
            assert live().get('custom_flag') == 1,live()
            run(180)
            before=live()
            session.post('press',124,'down');run(12);session.post('press',124,'up');run(1)
            moved=live()
            assert before['x'] != moved['x'],[before,moved]
            session._command(f'checkpoint-place {slot}');session._gate_wait()
            run(2)
            session.post('press',124,'down');run(24);session.post('press',124,'up');run(1)
            assert session.wait(lambda: 'checkpoint_saved' in live()['custom_level'],12),live()
            saved = live()['custom_level']['checkpoint_saved']
            assert saved['slot'] == slot,saved
            assert len(saved['values'])==18 and saved['values'][17] > 0,saved
            assert profile() == original_profile,'automatic checkpoint changed retail profile'
            report['marks'][current] = dict(saved=saved,loaded=before['custom_level'],movement=[before['x'],moved['x']],input=session.transitions())
            record()
            disk_before = {p.name:p.read_bytes() for p in (saves/'CustomSaves').glob('*.plist')}
            launch(current+'-restart')
            picker();tap(124)
            assert live()['custom_restart_slot'] == slot,live()
            tap(36)
            restored=live()['custom_level'].get('checkpoint_restored')
            assert restored == saved['values'],[restored,saved]
            p=live()
            assert p['health']==restored[1] and p['ammo']==restored[4:7] and p['score']==restored[0],p
            assert p['treasure_counts'][:9] == restored[8:17] and p['lives'] == restored[7],p
            assert abs(p['x']-restored[2]) <= 4 and abs(p['y']-restored[3])<=16,p
            assert restored[17] <= p['game_ms'] <= restored[17]+500,p
            assert profile() == original_profile,'restart changed retail profile'
            assert disk_before == {p.name:p.read_bytes() for p in (saves/'CustomSaves').glob('*.plist')},'resume re-saved the loaded checkpoint'
            # Real slot loads retain the original retirement behavior. Bring
            # the loaded flag into range so its lazy first tick runs.
            session._command(f'checkpoint-place {slot}');session._gate_wait();run(2)
            rows = live()['placements']
            flag = next(r for r in rows if r['logic'] == ('FirstSuperCheckpoint' if slot == 1 else 'SecondSuperCheckpoint'))
            assert not flag['live'] or flag['flags'] & 0x10000, flag
            assert disk_before == {p.name:p.read_bytes() for p in (saves/'CustomSaves').glob('*.plist')},'retiring flag wrote save slots'
            report['marks'][current]['real_slot_retires_flag'] = True
            report['marks'][current]['restored_live'] = p
            report['marks'][current]['resume_does_not_resave_checkpoint'] = True
            # Finish only through owner-approved delivered MPSCULLY.
            for code in [46,35,1,8,32,37,37,16]: tap(code)
            assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',15),live()
            results = live()
            assert results['custom_level'].get('completion') is not None,results
            for _ in range(15):
                if live().get('menu_page') in (10000,10001):break
                tap(36);run(60)
            assert live().get('menu_page') in (10000,10001),live()
            assert live()['custom_level'].get('unloaded'),live()
            assert profile()==original_profile,'custom completion changed retail profile'
            report['marks'][current]['completion'] = dict(results_state=results['state_vtable'],bookkeeping=results['custom_level'].get('completion'),menu=live()['menu_page'],unloaded=True,retail_profile_unchanged=True)
            record()
        assert len(list((saves/'CustomSaves').glob('*.plist'))) == 2,'maps share a save file'
        for path,digest in hashes.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        report['marks']['original_archives_unchanged'] = hashes
        report['status']='pass'
        return report
    finally:
        if session: session.close()
        for pattern in ('hud-*.png','frame-*.png'):
            for p in out.rglob(pattern): p.unlink()
        record()
