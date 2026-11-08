#!/usr/bin/env python3
"""Opt-in fixed-seed, delivered-key app fuzzing, with exact action-plan replay.

Defaults: both profiles, all 14 retail levels and the retained custom samples,
three seeds, 180 seconds of gameplay per session. Use --resume to continue an
interrupted sweep of the *same binary*. A short/selected run is explicitly a
partial run and cannot satisfy the complete-sweep result. Missing behavioral
coverage is reported separately from faults. No game-state writes or invincible
cheats are used; custom checkpoint shortcuts go through real window events.
Three additional placement fixtures per profile exercise grabbing,
powerups and a retail checkpoint through normal collision and delivered keys.
Their placement is explicit in each replay plan, never counted as traversal.
Complete archives are staged without changing retained downloads. After game
over/menu transitions a new muted instance restarts the same map and continues
the input plan; each retired instance retains its delivery and runtime logs.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import random
import select
import shutil
import signal
import stat
import subprocess
import time
import zipfile

from real_input import Session, build_helper, alive
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crash-sweep'
SEEDS=[7,29,101]
KEYS={'left':123,'right':124,'up':126,'down':125,'jump':49,'attack':59,'fire':58,'grab':6}


class SweepSession(Session):
    """Keep the CGEvent sender alive; Session.post still verifies each arrival.

    The helper posts exactly one real key transition per request. Only process
    startup/exit delay changes; the existing frame gate and delivery proof do
    not. A pipe EOF ends this session-owned child, with no background service.
    """
    sender = None

    def _post(self, args):
        if self.sender is None:
            self.sender = subprocess.Popen([self.helper,str(self.pid),'serve'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,bufsize=1)
        self.sender.stdin.write(json.dumps(list(map(str,args)))+'\n')
        self.sender.stdin.flush()
        if not select.select([self.sender.stdout],[],[],10)[0]:
            raise RuntimeError('streaming event helper timed out')
        line=self.sender.stdout.readline()
        if not line:raise RuntimeError('streaming event helper exited')
        posted=json.loads(line)
        if posted.get('status')!='posted' or posted.get('pid')!=self.pid:
            raise RuntimeError(f'event helper failed: {posted}')
        return posted

    def close(self):
        try:
            super().close()
        finally:
            if self.sender:
                self.sender.stdin.close()
                try:self.sender.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.sender.terminate();self.sender.wait(timeout=3)
                self.sender.stdout.close();self.sender.stderr.close()
                self.sender=None


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def driver_inputs():
    return {p:sha(ROOT/p) for p in ('scripts/check-crash-sweep.py','scripts/real_input.py',
                                   'scripts/post-window-input.swift')}


def read(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    temporary.replace(path)


def samples(stage, selected=None):
    """Stage complete immutable archives, including WWD companion assets."""
    result=[]
    source=ROOT/'work/custom-levels/samples.json'
    for row in json.loads(source.read_text()):
        directory=Path(row['url']).stem
        if selected and directory not in selected:continue
        archive=ROOT/'work/custom-levels'/directory/Path(row['url']).name
        if not archive.is_file():raise ValueError(f'Missing retained custom archive: {archive}')
        archive_hash=sha(archive)
        folder=stage/(directory+'-'+archive_hash[:16])
        marker=folder/'.extracted.json'
        if read(marker).get('archive_sha256')!=archive_hash:
            if folder.exists():shutil.rmtree(folder)
            folder.mkdir(parents=True)
            with zipfile.ZipFile(archive) as bundle:
                if sum(entry.file_size for entry in bundle.infolist())>256*1024*1024:
                    raise ValueError(f'Custom archive exceeds package limit: {archive}')
                for entry in bundle.infolist():
                    name=PurePosixPath(entry.filename.replace('\\','/'))
                    if name.is_absolute() or '..' in name.parts or stat.S_ISLNK(entry.external_attr>>16):
                        raise ValueError(f'Unsafe custom archive entry: {entry.filename}')
                    target=folder.joinpath(*name.parts)
                    if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True,exist_ok=True)
                        with bundle.open(entry) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            write(marker,dict(archive_sha256=archive_hash))
        for name in row['files']:
            path=folder/name
            retained=ROOT/'work/custom-levels'/directory/name
            if not path.is_file() or sha(path)!=sha(retained):
                raise ValueError(f'Staged WWD differs from retained sample: {path}')
            result.append(dict(id='custom-'+directory,custom=str(path),wwd_sha256=sha(path),
                               archive_sha256=archive_hash))
    return result


def plan(seed,seconds,level=None):
    rng=random.Random(seed)
    actions=[]
    total=0
    # The first three epochs deliberately select and fire each weapon. Later
    # epochs combine movement, jumping, lift/throw and attack with fixed RNG.
    while total<seconds*60:
        index=len(actions)
        count=min(rng.choice([30,60,90,120]),seconds*60-total)
        held=[rng.choice(['left','right','right','right','up','down'])]
        if rng.randrange(3):held.append('jump')
        held.append(rng.choice(['attack','attack','fire','grab']))
        action=dict(frame=total,frames=count,held=sorted(set(held)))
        if index<3:
            action['weapon']=index+1
            action['held']=sorted(set(held+['fire']))
        elif index%11==0:action['weapon']=rng.randrange(1,4)
        if index==5:action['checkpoint']='save'
        if index==10 or index>15 and index%23==0:action['checkpoint']='restore'
        if index==12:action['end_life']=True
        if level==7 and index in (3,6,8):
            action.update(place_callback=0x409860,held=['grab'])
        if level==7 and index in (4,7,9):action['held']=['right','attack']
        actions.append(action);total+=count
    return actions


def feature_plan(feature):
    """Use the existing placement seam; never assign pickup/carry/save state."""
    callbacks={'grab':0x48a980,'powerup':0x470430,'retail-checkpoint':0x4232c0}
    actions=[]
    for index in range(30):
        action=dict(frame=index*60,frames=60,held=['right' if index%2==0 else 'left'])
        if index==0:
            action['place_callback']=callbacks[feature]
            if feature!='grab':action['place_mode']='center'
        if feature=='grab':
            if index%3==0:action.update(place_callback=callbacks[feature],held=['grab'])
            elif index%3==1:action['held']=['right','attack']
        actions.append(action)
    return actions


def signature(row):
    state=row.get('state',{})
    error=row.get('error','')
    # Native address/code and trace distinguish faults; infrastructure errors
    # remain separate and must not be presented as game crashes.
    return hashlib.sha256(json.dumps([error,state.get('trace',[])],sort_keys=True).encode()).hexdigest()[:16]


def session_run(spec,app,helper,out):
    started=time.monotonic()
    execution_inputs=driver_inputs()
    out.mkdir(parents=True,exist_ok=True)
    write(out/'plan.json',spec)
    session=SweepSession(out,fast=True,helper=helper)
    evidence=[];coverage=set();held=set();initial=None
    result=dict(spec=spec,status='fail',kind='infrastructure',coverage=[],actions_completed=0)
    previous_ammo=[]
    counts=Counter();all_retries=[];episodes=[];frame_offset=0
    def snapshot():
        live=read(out/'live.json')
        p=live.get('player',live)
        keys=('level','x','y','health','score','player_state','logic_state','ammo','lives','lives_lost',
              'combat','checkpoint_position','random_snapshot')
        return {k:p[k] for k in keys if k in p},live
    def health():
        if session.failed():
            raise RuntimeError(read(out/'real-speed.json').get('error') or read(out/'live-state.json').get('error') or 'native app fault')
        if session.pid and not alive(session.pid):raise RuntimeError('app process exited')
    def retire_episode(reason=None, index=None):
        nonlocal session,frame_offset,held,previous_ammo
        session.close()
        counts.update(read(out/'real-speed.json').get('invoke_counts',{}))
        all_retries.extend(session.retries)
        if reason is None:return
        episode=out/'episodes'/f'{len(episodes):03d}'
        episode.mkdir(parents=True,exist_ok=True)
        episodes.append(dict(reason=reason,before_action=index,frames=session.frames,
                             directory=str(episode),input=session.input_state()))
        frame_offset+=session.frames
        # Keep the delivered-input and runtime logs for every retired instance.
        for path in out.iterdir():
            if path.is_file() and path.suffix in ('.json','.txt') and path.name not in ('plan.json','progress.json','result.json'):
                shutil.move(str(path),episode/path.name)
            elif path.is_file() and path.suffix=='.png':path.unlink()
        held=set();previous_ammo=[]
        session=SweepSession(out,fast=True,helper=helper)
        session.launch(app,{'CLAW_GAME_VERSION':spec['profile'],'CLAW_LIVES_BOSS_PROFILE':'claw-v'+spec['profile']},args,start_seconds=90)
        session.run(1);health()
        player,live=snapshot()
        if live.get('state_vtable')!='0x50c264':raise RuntimeError('restart did not reach requested gameplay')
        if expected and player.get('level')!=expected:raise RuntimeError('restart reached wrong retail level')
        previous_ammo=player.get('ammo',[])
    try:
        args=['--save-dir',str(out/'saves'),'--settings-dir',str(out/'settings'),'--menu-live-check',str(out),'-ClawCheckDirectory',str(out),'--crash-sweep','--enemy-grab-check']
        if spec.get('full_telemetry'):args+=['--crash-sweep-every-frame']
        if 'custom' in spec['level']:
            args+=['--crash-sweep-custom',spec['level']['custom']]
        else:
            args+=['--crash-sweep-level',str(spec['level']['level'])]
        session.launch(app,{'CLAW_GAME_VERSION':spec['profile'],'CLAW_LIVES_BOSS_PROFILE':'claw-v'+spec['profile']},args,start_seconds=90)
        session.run(1);health()
        initial,live=snapshot()
        if live.get('state_vtable')!='0x50c264':raise RuntimeError('requested gameplay state was not reached')
        previous_ammo=initial.get('ammo',[])
        expected=spec['level'].get('level')
        if expected and initial.get('level',live.get('level'))!=expected:raise RuntimeError('wrong retail level')
        for index,action in enumerate(spec['actions']):
            health()
            player,live=snapshot()
            if live.get('state_vtable')!='0x50c264' or expected and player.get('level')!=expected:
                retire_episode('gameplay-ended',index)
            wanted=set(action['held'])
            for key in sorted(held-wanted):session.post('press',KEYS[key],'up')
            held &= wanted
            if action.get('checkpoint') or action.get('weapon') or action.get('end_life') or action.get('place_callback'):
                for key in sorted(held):session.post('press',KEYS[key],'up')
                held=set()
            if action.get('place_callback'):
                command='sweep-place' if action.get('place_mode')=='center' else 'grab-place'
                session._command(f"{command} {action['place_callback']}");session._gate_wait();health()
                session.run(10);health()
            if action.get('end_life'):
                for code in (53,125,36,36):session.post('key',code)
                session.run(120);health()
            if 'weapon' in action:
                session.post('key',{1:18,2:19,3:20}[action['weapon']])
            if action.get('checkpoint'):
                flags='command' if action['checkpoint']=='save' else 'command,shift'
                session.post('key',20,flags)
            for key in sorted(wanted-held):session.post('press',KEYS[key],'down')
            held=wanted
            session.run(action['frames']);health()
            p,live=snapshot()
            combat=p.get('combat',{})
            if combat.get('carrying'):coverage.add('grab')
            if combat.get('attack') or combat.get('attack_code'):coverage.add('attack')
            if combat.get('power_ms',0)>0:coverage.add('powerup')
            if p.get('lives_lost',0)>initial.get('lives_lost',0):coverage.add('death')
            if combat.get('weapon') is not None:coverage.add('weapon-'+str(combat['weapon']))
            for weapon,(before,after) in enumerate(zip(previous_ammo,p.get('ammo',[]))):
                if 0<=after<before:coverage.add('fired-'+str(weapon))
            previous_ammo=p.get('ammo',[])
            if read(out/'custom-restore.json').get('status')=='pass':coverage.add('custom-checkpoint')
            # Record compact replay evidence; no per-frame PNG collection.
            evidence.append(dict(index=index,frame=frame_offset+session.frames,player=p,random=live.get('random_snapshot')))
            result['actions_completed']=index+1
            if index%10==0:
                write(out/'progress.json',dict(actions_completed=index+1,frame=session.frames,coverage=sorted(coverage)))
        for key in sorted(held):session.post('press',KEYS[key],'up')
        health()
        result.update(status='pass',kind='fault-free',input=session.input_state(),retries=session.retries)
        # A retried key is evidence of delivery trouble, not an exact replay.
        if session.retries:result.update(status='fail',kind='input-retry',error='input needed retries; replay timing is not certified')
    except Exception as error:
        result['error']=str(error)
        result['state']=read(out/'live-state.json')
        result['runtime']=read(out/'real-speed.json')
        if 'No live grab target' in str(error):result['kind']='fixture-unavailable'
        elif str(error).startswith('unsupported('):result['kind']='unsupported-level'
        elif read(out/'quit.json').get('status')=='pass':
            result.update(kind='requested-exit',quit=read(out/'quit.json'),
                          error='Recorded WM_CLOSE ended the session before the action plan completed')
        elif session.failed():result['kind']='native-fault'
        elif session.pid and not alive(session.pid):result['kind']='process-exit'
        result['signature']=signature(result)
    finally:
        retire_episode()
        for path in out.glob('*.png'):
            if result['status']=='pass' or path.name not in ('frame-fail.png','live.png'):path.unlink()
    result['episodes']=episodes
    result['retries']=all_retries
    if all_retries and result['status']=='pass':
        result.update(status='fail',kind='input-retry',error='input needed retries in an episode')
    # Custom restore also rewrites the respawn position. Only a real retail
    # activation entry is checkpoint coverage, not a changed coordinate.
    if counts.get('422ff0',0) or counts.get('4231a0',0):coverage.add('retail-checkpoint')
    result['transports']=read(out/'live-state.json').get('transports',{})
    result['invoke_counts']=counts
    result['initial_player']=initial
    if spec.get('feature') and spec['feature'] not in coverage and result['status']=='pass':
        result.update(status='fail',kind='coverage-missing',error='Fixture did not exercise '+spec['feature'])
    # Checkpoints are recreated by the action plan; retain JSON evidence, not
    # hundreds of megabytes of regenerable snapshots for every seed/profile.
    for path in (out/'saves').glob('custom-checkpoint*'):
        if path.is_file():path.unlink()
    if driver_inputs()!=execution_inputs:
        result.update(status='fail',kind='driver-changed',error='Input driver changed during the session')
    result.update(coverage=sorted(coverage),observations=evidence,wall_seconds=round(time.monotonic()-started,3),
                  execution_driver_inputs=execution_inputs,input_sender='streaming-cgevent-confirmed')
    write(out/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',nargs='+',choices=['1.0','1.3'],default=['1.3','1.0'])
    parser.add_argument('--levels',nargs='+',type=int,default=list(range(1,15)))
    parser.add_argument('--seeds',nargs='+',type=int,default=SEEDS)
    parser.add_argument('--seconds',type=int,default=180)
    parser.add_argument('--no-custom',action='store_true')
    parser.add_argument('--custom-only',nargs='*',metavar='ARCHIVE',
                        help='partial check of custom archives only; optionally select archive stems')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--replay',type=Path,help='verify identical observations/fault from saved plan.json in a new replay directory')
    parser.add_argument('--list',action='store_true',help='write plans, without launching or building')
    parser.add_argument('--features-only',action='store_true',help='focused placement fixtures in both profiles; not the full fuzz sweep')
    parser.add_argument('--full-telemetry',action='store_true',help='retain every-frame diagnostics; replay can verify compact recording equivalence')
    parser.add_argument('--budget-seconds',type=int,default=0,
                        help='stop between sessions after this wall-clock budget; resume retains the full manifest')
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    args.output=args.output.resolve()
    if args.replay:args.replay=args.replay.resolve()
    if not 1<=args.seconds<=600 or any(not 1<=n<=14 for n in args.levels):parser.error('seconds 1...600; levels 1...14')
    if args.budget_seconds<0:parser.error('budget-seconds must be nonnegative')
    if args.custom_only is not None and (args.no_custom or args.features_only):
        parser.error('--custom-only cannot be combined with --no-custom or --features-only')
    app=Path(os.environ.get('CLAW_DERIVED_DATA',ROOT/'work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
    executable=app/'Contents/MacOS/Claw'
    fingerprint=sha(executable) if executable.exists() else 'not-built'
    levels=[dict(id=f'level-{n:02d}',level=n,wwd_sha256=sha(ROOT/f'App/GameData/LEVEL{n}/WORLDS/WORLD.WWD')) for n in args.levels]
    # Exercise package loading before long retail runs. Plan identity does not
    # depend on batch order, so resume keeps already completed retail sessions.
    if not args.no_custom and not args.replay:
        custom=samples(args.output/'inputs',args.custom_only)
        if args.custom_only:
            unknown=set(args.custom_only)-{r['id'].removeprefix('custom-') for r in custom}
            if unknown:parser.error('Unknown custom archives: '+', '.join(sorted(unknown)))
            custom=[r for r in custom if r['id'].removeprefix('custom-') in args.custom_only]
        levels=custom+([] if args.custom_only is not None else levels)
    specs=[dict(schema=1,profile=profile,level=level,seed=seed,seconds=args.seconds,binary_sha256=fingerprint,
                driver_sha256=sha(Path(__file__)),driver_inputs=driver_inputs(),actions=plan(seed,args.seconds,level.get('level')))
           # Cover both profiles and every level before spending a second seed
           # on the same level. Individual plan identity is order-independent.
           for seed in args.seeds for level in levels for profile in args.profiles]
    first=dict(id='level-01',level=1,wwd_sha256=sha(ROOT/'App/GameData/LEVEL1/WORLDS/WORLD.WWD'))
    # Retail Level 1 has warps and an extra life, but no placed timed pickup.
    # Level 2 supplies genuine ghost/fire-sword pickups for normal collision.
    powerup_level=dict(id='level-02',level=2,wwd_sha256=sha(ROOT/'App/GameData/LEVEL2/WORLDS/WORLD.WWD'))
    features=[dict(schema=1,profile=profile,level=dict(powerup_level if feature=='powerup' else first,id='feature-'+feature),feature=feature,seed=7,seconds=30,
                   binary_sha256=fingerprint,driver_sha256=sha(Path(__file__)),driver_inputs=driver_inputs(),actions=feature_plan(feature))
              for feature in ('grab','powerup','retail-checkpoint') for profile in args.profiles]
    specs=features if args.features_only else specs if args.custom_only is not None else features+specs
    if args.replay:
        specs=[read(args.replay)]
        if specs[0].get('binary_sha256')!=fingerprint:raise ValueError('Replay requires the identical binary; rebuilds need a fresh sweep')
    if args.full_telemetry:
        for spec in specs:spec['full_telemetry']=True
    args.output.mkdir(parents=True,exist_ok=True)
    write(args.output/'manifest.json',dict(specs=specs))
    if args.list:
        print(json.dumps(dict(check='crash-sweep',status='planned',sessions=len(specs),output=str(args.output))));return 0
    if not executable.is_file():raise ValueError('Build Release with scripts/run-mac.sh --version-only first')
    results=[]
    stop_requested=False
    def request_stop(signum,frame):
        nonlocal stop_requested
        stop_requested=True
    signal.signal(signal.SIGINT,request_stop)
    signal.signal(signal.SIGTERM,request_stop)
    # Serializes this opt-in sweep with other instances of itself. The build
    # helper has its own shared lock; each launch separately waits for low load.
    with (ROOT/'work/.claw-crash-sweep.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
        # A selected batch owns one stable bundle, just as a build owns it.
        # Releasing between levels lets another lane replace the binary halfway
        # through a deterministic sweep. This OS lock dies with the process.
        with (ROOT/'work/.claw-app-build.lock').open('a') as build_lock:
            fcntl.flock(build_lock,fcntl.LOCK_EX)
            fingerprint=sha(executable)
            if args.replay and specs[0]['binary_sha256']!=fingerprint:
                raise ValueError('Binary changed while waiting; replay needs its original build')
            for spec in specs:spec['binary_sha256']=fingerprint
            write(args.output/'manifest.json',dict(specs=specs))
            started=time.monotonic()
            for spec in specs:
                suffix=f"{spec['profile']}-{spec['level']['id']}-seed-{spec['seed']}"
                if args.replay:suffix+='-replay-'+str(time.time_ns())
                folder=args.output/suffix
                existing=read(folder/'result.json')
                if args.resume and existing.get('spec')==spec:
                    result=existing
                else:
                    if stop_requested or args.budget_seconds and time.monotonic()-started>=args.budget_seconds:
                        break
                    if folder.exists():shutil.rmtree(folder)
                    result=session_run(spec,app,helper,folder)
                if args.replay:
                    original=read(args.replay.with_name('result.json'))
                    result['replay_match']=(result.get('observations')==original.get('observations') and
                        result.get('signature')==original.get('signature') and
                        result.get('kind')==original.get('kind') and not result.get('retries') and
                        result.get('kind') in ('fault-free','native-fault','process-exit','unsupported-level','requested-exit'))
                    if not result['replay_match']:result.update(status='fail',kind='replay-mismatch')
                    write(folder/'result.json',result)
                summary={k:result.get(k) for k in ('status','kind','coverage','error','signature','actions_completed','replay_match','wall_seconds')}
                summary.update(restarts=len(result.get('episodes',[])),plan=str(folder/'plan.json'),profile=spec['profile'],level=spec['level']['id'],seed=spec['seed'])
                results.append(summary)
                write(args.output/'progress.json',dict(completed=len(results),expected=len(specs),results=results))
                print(json.dumps(summary),flush=True)
    complete=(len(results)==len(specs) and not args.replay and not args.features_only and args.custom_only is None and set(args.profiles)=={'1.0','1.3'} and set(args.levels)==set(range(1,15)) and
              set(args.seeds)>=set(SEEDS) and args.seconds>=180 and not args.no_custom)
    coverage=set().union(*(set(row['coverage'] or []) for row in results))
    required={'grab','attack','death','powerup','custom-checkpoint','retail-checkpoint',
              'weapon-1','weapon-2','weapon-3','fired-0','fired-1','fired-2'}
    profile_coverage={p:sorted(set().union(*(set(r['coverage'] or []) for r in results if r['profile']==p)))
                      for p in args.profiles}
    missing_by_profile={p:sorted(required-set(c)) for p,c in profile_coverage.items()}
    missing=sorted(required-coverage)
    failures=[row for row in results if row['status']!='pass']
    feature_complete=args.features_only and len(results)==len(specs) and not args.replay and not failures
    # Reproducing the original crash is a successful replay check, not a
    # fault-free run. Keep the native-fault result and its seed in failures.
    replay_complete=bool(args.replay) and len(results)==1 and results[0].get('replay_match') is True
    report=dict(check='crash-sweep',status='pass' if replay_complete or feature_complete or complete and not failures and not any(missing_by_profile.values()) else 'fail',
                scope='replay' if args.replay else 'features-only' if args.features_only else 'full' if complete else 'partial',sessions=len(results),failures=failures,missing_coverage=missing,
                expected_sessions=len(specs),interrupted=stop_requested,coverage_by_profile=profile_coverage,
                missing_coverage_by_profile=missing_by_profile,
                results=results,binary_sha256=fingerprint)
    write(args.output/'result.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','failures')}))
    return int(report['status']!='pass')


if __name__=='__main__':
    raise SystemExit(main())
