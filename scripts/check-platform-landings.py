"""Retail platform landing regression, with delivered keys and pinned v1.0 collision replay.

Checkpoint edits are labelled placement recipes. Retail WWD geometry is unchanged.
The only time override is the opt-in muted frame-gate's 17/33/50/100 ms step.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
import plistlib
import subprocess
import time
from pathlib import Path

from real_input import Session, build_helper
from platform_landing_oracle import LandingOracle
from tools.claw.test_level import entries

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--arcana', type=Path, help='Optional full Arcana package instead of the bounded retail-geometry Lua fixture')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='fail', cases=[], errors=[], input='Confirmed real window key events',
                  scope='Mac Catalyst Release; iPad compilation is a separate check',
                  original='Pinned v1.0 CLAW.EXE via claw(); retail REZ hash checked by entries(); only tile attribute virtual is a declared fixture',
                  root_cause='Native startup omitted original 0x42ce90 stores of 14 to collision manager +0x64/+0x68; constructor default 64 tunnels through thin floors.')
    session = None
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    helper = build_helper(ROOT/'work/platform-landings/post-window-input')
    report['binary_sha256'] = hashlib.sha256((app/'Contents/MacOS/Claw').read_bytes()).hexdigest()
    oracles = {}
    def oracle(level):
        if level not in oracles: oracles[level] = LandingOracle(level)
        return oracles[level]
    def save(): (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    def live(): return json.loads((session.out/'live.json').read_text())
    def run(frames):
        result = session.run(frames)
        assert result.get('status') != 'fail', result
    def tap(key, *flags):
        session.post('key', key, *flags); run(4)
    def launch(name, level=None, custom=None):
        nonlocal session
        if session: session.close()
        folder = out/name;folder.mkdir()
        session = Session(folder, helper=helper)
        session.launch(app, {}, ['--save-dir', str(out/'saves'), '--settings-dir', str(out/'settings'),
            '--stationary-cursor', '--no-paper-startup', '--custom-checkpoint-check', '--platform-landing-check',
            *(['--custom-checkpoint-level', str(level)] if level else []),
            *(['--custom-dir', str(custom.resolve().parent), '--lua-runtime-check'] if custom else []),
            '-ClawCheckDirectory', str(folder)], start_seconds=180)
        run(120 if level else 60)
        if custom:
            if live().get('menu_page') == 10000: tap(36)
            for _ in range(10):
                if live().get('menu_selected') == 11003: break
                tap(125)
            assert live().get('menu_selected') == 11003, live()
            tap(36)
            assert live().get('custom_dialog'), live()
            tap(36);run(30)
            assert not live().get('custom_error') and live().get('custom_flag') == 1, live()
    def placement(template, level, x, y):
        # Same checksummed format as the native checkpoint writer. No engine state,
        # collision mode, velocities, or physics settings are injected.
        data = dict(template, level=level, x=x, y=y, removedPlacements=[])
        payload = plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
        path = out/'saves/custom-checkpoint.clawcheckpoint'
        path.write_bytes(plistlib.dumps(dict(payload=payload, digest=hashlib.sha256(payload).digest()), fmt=plistlib.FMT_BINARY))
        tap(20, 'command,shift')
        assert live()['custom_checkpoint'][-1]['action'] == 'restore', live()
    def fall(name, template, level, x, floor, height, ms, jump=False):
        session._command('landing-frame-ms 17');run(0)
        placement(template, level, x, floor-61-height)
        assert live()['collision_steps'] == [14,14], live()
        assert live()['landing_physics'] == dict(speed=225, jump_base=250, fall_cap=1000), live()['landing_physics']
        if jump:
            # The placement is a real supporting floor. A delivered Space jumps
            # through the player state machine; release early and land on it.
            session.post('press',49,'down');run(8);session.post('press',49,'up')
            assert live()['y'] < floor-61, (name, 'delivered jump did not rise', live())
        else:
            # Delivered movement makes the original standing support check enter fall.
            session.post('press',124,'down');run(1);session.post('press',124,'up')
        session._command('landing-frame-ms '+str(ms));run(0)
        samples=[]
        compared=0
        for _ in range(160):
            run(1);state=live()
            move=state.get('landing_move',{})
            row={k:state[k] for k in ['frame','x','y','logic_state','motion_state','collision_steps','frame_ms']}
            if move.get('frame') == state['frame'] and move['mode'] == 4:
                expected=oracle(level).move(move['x'],move['y'],move['target_y'],mode=move['mode'],record=move)
                actual=dict(x=state['x'],y=state['y'],mode=state['motion_state'])
                row.update(move=move,original=expected)
                assert actual==expected,(name,row)
                compared+=1
            samples.append(row)
            if state['motion_state']==1 and state['y']==floor-61:break
            assert state['y']<=floor-61,(name,'tunnelled',samples)
        assert samples[-1]['motion_state']==1 and samples[-1]['y']==floor-61,(name,samples)
        assert compared>0,(name,'original replay never exercised')
        run(8)
        assert live()['y']==floor-61 and live()['motion_state']==1,(name,'lost support',live())
        report['cases'].append(dict(name=name,level=level,frame_ms=ms,height=height,original_moves=compared,
                                    delivery=session.input_state(),samples=samples))
        save()
        for frame in session.out.glob('frame-*.png'):frame.unlink()
    try:
        # The original's exact startup instructions install decimal 14. Execute
        # its complete collision path on the observed normal-speed missed ledge.
        controls=[]
        for level,x,old_y,target_y,landing_y in [(5,3299,2418,2436,2421),(8,3359,4610,4670,4631)]:
            original=oracle(level).move(x,old_y,target_y)
            constructor=oracle(level).move(x,old_y,target_y,step=64)
            assert original==dict(x=x,y=landing_y,mode=1),original
            assert constructor==dict(x=x,y=target_y,mode=4),constructor
            controls.append(dict(level=level,old_y=old_y,target_y=target_y,original=original,constructor_default=constructor))
        report['original_controls']=controls
        launch('retail',5)
        tap(20,'command')
        envelope=plistlib.loads((out/'saves/custom-checkpoint.clawcheckpoint').read_bytes())
        template=plistlib.loads(envelope['payload'])
        # Level 5's original one-way tile is exactly 14 pixels high. Level 8's
        # original solid tile is 24 pixels high. Both have empty space beneath.
        for level,x,floor,height,kind in [(5,3295,2482,500,'ledge'),(8,3359,4692,500,'solid')]:
            for ms in (17,33,50,100):
                fall(f'{kind}-drop-{ms}',template,level,x,floor,height,ms)
            fall(f'{kind}-jump-return',template,level,x,floor,0,17,jump=True)
        source='MultClawSpeed(.75);SetNormalJumpHeight(292);SetRunningJumpHeight(292);SetClawFallSpeedCap(500)'
        custom=args.arcana
        if custom is None:
            folder=out/'physics-package';folder.mkdir()
            custom=folder/'PlatformPhysics.wwd'
            custom.write_bytes(next(data for name,data in entries() if name=='LEVEL5/WORLDS/WORLD.WWD'))
            logics=custom.with_suffix('')/'LOGICS';logics.mkdir(parents=True)
            (logics/'MAIN.LUA').write_text('function OnGameplay() if not _landingPhysics then _landingPhysics=true;'+source+' end end\n')
            report['custom_fixture']='Unchanged retail Level 5 WWD; synthetic OnGameplay calls the public physics APIs once'
        assert custom.is_file(), custom
        launch('after-custom',custom=custom)
        if args.arcana:
            session._command('lua-gameplay-check '+base64.b64encode(source.encode()).decode());run(1)
        # MultClawSpeed uses floor(base * multiplier + .5): 225 * .75 -> 169.
        assert live()['landing_physics']==dict(speed=169,jump_base=503,fall_cap=500),live()['landing_physics']
        report['custom_modified_physics']=live()['landing_physics']
        fall('solid-after-custom-physics',template,8,3359,4692,500,50)
        fall('ledge-after-custom-physics',template,5,3295,2482,500,17)
        report['restored_physics']=live()['landing_physics']
        report['status']='pass'
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if session:session.close()
        for frame in out.rglob('frame-*.png'):frame.unlink()
        save()
    print(json.dumps(dict(status=report['status'],errors=report['errors'],result=str(out/'result.json'))))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':
    # Same shared lock as the app builder: no overlapping heavy app checks/builds.
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        while float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]) >= 16:
            time.sleep(10)
        raise SystemExit(main())
