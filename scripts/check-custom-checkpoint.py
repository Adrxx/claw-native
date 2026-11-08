"""Exact-moment super-checkpoint restore with delivered real keys and unmuted offline audio.
Own --mute Catalyst instances only; verifies Level 2 kills/loot and disk relaunch.
"""
from collections import Counter
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys
import time
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('level','x','y','facing','health','score','lives','ammo','weapon','treasure','elapsed_ms','lives_lost','extra_life_threshold','hud_extra_life_threshold','power_kind','power_ms','removed_count')
TREASURE_KINDS = (*range(1,19),33,*range(41,53))
# The admitted original counter excludes necklace item 6; it still awards score.
COUNTED_KINDS = tuple(k for k in TREASURE_KINDS if k != 6)
KEYS = {'M':46,'P':35,'H':4,'O':31,'T':17,'S':1,'U':32,'F':3}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--slots-only', action='store_true', help='Three-slot FIFO, chooser, migration and disk persistence')
    parser.add_argument('--flags-only', action='store_true', help='Golden super checkpoint flags before and after custom restore')
    parser.add_argument('--custom-only', action='store_true', help='Debug just the custom-map scenario; default checks both')
    parser.add_argument('--sources-only', action='store_true', help='Real Level 5 statue drop lifecycle')
    parser.add_argument('--owner-save-only', action='store_true', help='Reproduce the iPad Level 2 settled drops')
    parser.add_argument('--loot-only', action='store_true', help='Focused remaining native drop persistence')
    parser.add_argument('--progress-only', action='store_true', help='Focused native platform continuation and event progress')
    parser.add_argument('--controllers-only', action='store_true', help='Native staging and mechanism controller reconstruction')
    parser.add_argument('--retail-only', action='store_true', help='Isolate the retail focused scenario')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    store = out/'saves'
    helper = build_helper(out/'post-window-input')
    app = ROOT/Path(os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
    session = None
    custom_world_active = False
    report = {'check':'custom-checkpoint-exact-moment','status':'fail','errors':[],'scenario':'custom' if args.custom_only else 'retail-and-custom'}

    def profile():
        file = store/'CLAW.USR'
        return file.read_bytes() if file.exists() else None

    def checkpoint_payload(slot=0):
        for path in (store/'ManualSuperCheckpoints').glob('*.clawcheckpoint'):
            envelope = plistlib.loads(path.read_bytes())
            if slot:envelope = plistlib.loads(envelope['previous'][slot-1])
            payload = plistlib.loads(envelope['payload'])
            if bool(payload.get('customPath')) == custom_world_active:
                return payload
        raise RuntimeError('No checkpoint for the active map')

    def live():
        return json.loads((session.out/'live.json').read_text())

    def run(frames):
        if session.run(frames).get('status') == 'fail':
            raise RuntimeError(f'Game failed: {session.gate()}')

    def tap(code, flags=None):
        modifiers = (flags,) if flags else ()
        session.post('press',code,'down',*modifiers)
        run(4)
        session.post('press',code,'up',*modifiers)
        run(4)

    def hold(code, frames, *flags):
        session.post('press',code,'down',*flags);run(frames)
        session.post('press',code,'up',*flags);run(1)

    def launch(name, level=None, custom_world=None):
        nonlocal session, custom_world_active
        custom_world_active = custom_world is not None
        if session:
            session.close()
        directory = out/name;directory.mkdir()
        session = Session(directory, helper=helper)
        session.launch(app,{'CLAW_AUDIO_EVIDENCE':'1'},['--save-dir',str(store),'--settings-dir',str(out/'settings'),
            '--stationary-cursor','--no-paper-startup','--long-trace','--checkpoint-audio-offline','--custom-checkpoint-check',
            *(['--custom-checkpoint-level',str(level)] if level else []),
            *(['--custom-dir',str(custom_world.parent),'--crazyhook-checkpoint-check'] if custom_world else []),'-ClawCheckDirectory',str(directory)],start_seconds=120)
        if args.progress_only:session.query_step(0)
        run(120)
        if custom_world:
            if live().get('menu_page') == 10000:tap(36)
            for _ in range(12):
                if live().get('menu_selected') == 11003:break
                tap(125)
            if live().get('menu_selected') != 11003:raise RuntimeError('Load Custom Level menu missing')
            tap(36);tap(36);run(180)
            if live().get('custom_flag') != 1:raise RuntimeError('Custom sample did not load')

    def gone(records):
        return {(r['plane'],r['id']) for r in records if not r['live'] or r['flags'] & 0x10000 or (r['logic']=='BehindStatue' and r['flags'] & 4)}

    def restore(name, menu=False, resume_frames=30, slot=0, chooser=False):
        path = session.out/'custom-restore.json';path.unlink(missing_ok=True)
        if chooser:
            tap(20,'command,option,shift')
            if not live()['checkpoint_chooser']['visible']:raise RuntimeError('Chooser shortcut did not open overlay')
            for _ in range(slot):tap(125)
            tap(36)
        elif menu:tap(36)
        else:tap(20,'command,shift')
        result = json.loads(path.read_text())
        if result['status'] != 'pass':
            raise RuntimeError(f'{name}: {result}')
        if any(result[k] != saved[k] for k in FIELDS):
            raise RuntimeError(f'{name} changed stats: {saved} != { {k:result[k] for k in FIELDS} }')
        if gone(result['placements']) != expected:
            raise RuntimeError(f'{name} did not preserve removed placements')
        if any(r.get('children_live',0) for r in result['placements'] if (r['plane'],r['id']) in expected):
            raise RuntimeError(f'{name} left a collectible descendant of a removed placement')
        initial = {(r['plane'],r['id']):r for r in result['initial_placements']}
        payload = checkpoint_payload(slot)
        mechanisms = payload.get('mechanisms',[])
        if 'mechanisms' in result:
            restored = {(r['placement']['plane'],r['placement']['id']):r for r in result['mechanisms']}
            for recipe in mechanisms:
                key = (recipe['placement']['plane'],recipe['placement']['id'])
                if recipe != restored.get(key):
                    raise RuntimeError(f'{name}: native controller recipe changed: {recipe} != {restored.get(key)}')
        progress = {(r['placement']['plane'],r['placement']['id']):r for r in mechanisms}
        for r in result['placements']:
            if r['live']:
                mechanism = progress.get((r['plane'],r['id']))
                if mechanism:
                    if [r['x'],r['y'],r['state']] != [*mechanism['actor'][:2],mechanism['primary'][0]]:
                        raise RuntimeError(f'{name}: mechanism progress changed: {r}')
                    continue
                original = initial[(r['plane'],r['id'])]
                if any(r[k] != original[k] for k in ('x','y','health')):
                    raise RuntimeError(f'{name}: surviving placement did not restart: {r}')
        camera = result.get('camera_rect',[])
        if len(camera) != 4 or not (camera[0] <= result['x'] <= camera[2] and camera[1] <= result['y'] <= camera[3]):
            raise RuntimeError(f'{name}: camera did not center at Claw: {camera}')
        if resume_frames:run(resume_frames)
        if live()['lives'] != saved['lives']:
            raise RuntimeError(f'{name}: HUD awarded the saved extra life again')
        resumed = live()
        if resumed['treasure_counts'] != saved['treasure']:
            raise RuntimeError(f'{name}: saved treasure counted twice after resuming: '
                               f"{saved['treasure']} -> {resumed['treasure_counts']}")
        report[name] = {k:result[k] for k in FIELDS}
        report[name]['input'] = session.input_state()
        (out/(name+'.json')).write_text(json.dumps(result))
        if profile() != original_profile:
            raise RuntimeError(f'{name} changed original save records')

    def audio(name):
        time.sleep(1)
        mark = session.mark(name, seconds=30)
        output = mark['audio_output']
        if not (output['offline'] and output['running'] and not output['muted'] and output['mixer_volume'] == 1
                and output['music_attached'] and output['offline_nonzero_samples'] > 0):
            raise RuntimeError(f'Audio not running unmuted offline: {output}')
        report[name] = output

    def collect_drops(name):
        if any(r['bouncing'] for r in live()['checkpoint_pickups']['remaining']):run(240)
        before = live()
        remaining = before['checkpoint_pickups']['remaining']
        count = len(remaining)
        treasures = sum(r['item'] in COUNTED_KINDS for r in remaining)
        extra_treasures = 0
        def key(r):return (r['item'],r['x'],r['y'])
        for _ in range(count):
            previous = live()
            if not previous['checkpoint_pickups']['remaining']:break
            if previous['health']==100 and any(r['item'] in range(24,28) for r in previous['checkpoint_pickups']['remaining']):
                # The original deliberately refuses health at full health.
                # Labelled saved-health fixture makes the remaining potions
                # useful without manufacturing pickup flags or awards.
                tap(20,'command')
                file = store/f"ManualSuperCheckpoints/retail-{previous['level']}.clawcheckpoint"
                payload = plistlib.loads(plistlib.loads(file.read_bytes())['payload'])
                payload['values'][1] = 50
                raw = plistlib.dumps(payload,fmt=plistlib.FMT_BINARY)
                file.write_bytes(plistlib.dumps({'payload':raw,'digest':hashlib.sha256(raw).digest()},fmt=plistlib.FMT_BINARY))
                tap(20,'command,shift');run(2)
                previous = live()
                report[name+'_health_fixture'] = 'Saved health lowered to 50; original refuses potions at full health'
            session._command('checkpoint-drop');session._gate_wait()
            hold(124,8);run(30)
            current = live()
            removed = Counter(map(key,previous['checkpoint_pickups']['remaining']))-Counter(map(key,current['checkpoint_pickups']['remaining']))
            if not removed:raise RuntimeError(f'{name}: visible runtime drop was not collectible')
            collected = sum(n for (item,x,y),n in removed.items() if item in COUNTED_KINDS)
            awards = current['checkpoint_pickups']['awards'][len(previous['checkpoint_pickups']['awards']):]
            pending = removed.copy();extras = []
            for award in awards:
                k = key(award)
                if pending[k]:pending[k] -= 1
                else:extras.append(award)
            if len({a['actor'] for a in awards}) != len(awards):
                raise RuntimeError(f'{name}: one actor awarded treasure twice')
            if any(a['placement'] is None or a['item'] != 33 for a in extras):
                raise RuntimeError(f'{name}: unexpected additional runtime award: {extras}')
            placed = sum(r['item'] in COUNTED_KINDS for r in extras)
            extra_treasures += placed
            if extras:report.setdefault(name+'_nearby_pickups',[]).extend(extras)
            if sum(current['treasure_counts']) != sum(previous['treasure_counts'])+collected+placed:
                raise RuntimeError(f'{name}: runtime treasure did not count exactly once')
            score = 0
            for (item,x,y),n in removed.items():
                recipe = next((r for r in checkpoint_payload().get('loot',[]) if r['actor'][1:3]==[x,y]),None)
                if recipe is None:
                    recipe = next((r for r in checkpoint_payload().get('loot',[]) if r.get('bounce',{}).get('item',r['actor'][0])==item),None)
                if item in TREASURE_KINDS and recipe:score += recipe['actor'][9]*n
                if any(r['callback']==0x470110 and not r['flags'] & 0x10000 and
                       (r['x'],r['y'])==(x,y) for r in current['checkpoint_pickups']['nearby']):
                    raise RuntimeError(f'{name}: collected drop left its glitter silhouette')
            if extras and all(r['item']==33 for r in extras):score += 100*len(extras)
            if score and (not extras or all(r['item']==33 for r in extras)) and current['score'] != previous['score']+score:
                raise RuntimeError(f'{name}: treasure score did not count exactly once')
        if live()['checkpoint_pickups']['remaining']:raise RuntimeError(f'{name}: drops remain')
        run(60)
        if sum(live()['treasure_counts']) != sum(before['treasure_counts'])+treasures+extra_treasures:
            raise RuntimeError(f'{name}: treasure counted again')
        report[name] = {'drops':remaining,'score_before':before['score'],'score_after':live()['score'],
                        'input':session.input_state()}

    try:
        if args.flags_only or not any((args.slots_only,args.owner_save_only,args.sources_only,args.loot_only,args.progress_only,args.controllers_only,args.custom_only)):
            import zipfile
            flag_store = store
            custom = out/'flag-custom';custom.mkdir()
            with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/just_keep_calm.zip') as archive:
                archive.extractall(custom)
            world = next(p for p in custom.rglob('*') if p.suffix.lower()=='.wwd')
            for label,custom_world in [('retail',None),('custom',world)]:
                store = out/('flag-saves-'+label)
                launch('flags-'+label,2 if custom_world is None else None,custom_world)
                def flags():
                    return {(r['plane'],r['id']):r for r in live()['placements'] if r['logic'] in ('FirstSuperCheckpoint','SecondSuperCheckpoint')}
                def original_files():
                    return {str(p.relative_to(store)):p.read_bytes() for p in store.rglob('*') if p.is_file() and 'ManualSuperCheckpoints' not in p.parts}
                assert len(flags()) == 2, flags()
                first,second = sorted(flags().values(),key=lambda r:r['x'])
                first_key,second_key = (first['plane'],first['id']),(second['plane'],second['id'])
                # Labelled position fixture only. The original scanner must
                # receive delivered movement to activate and save the flag.
                session._command(f"checkpoint-source {first['id']}");session._gate_wait();run(2)
                original_profile = profile();before_files = original_files()
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                restore(label+'_before_flag')
                assert original_files() == before_files, 'Custom restore wrote original slots'
                untriggered = flags()[first_key]
                assert untriggered['live'] and not untriggered['flags'] & 0x10001 and untriggered['state'] == 5, untriggered
                hold(124,24);run(150)
                triggered = flags()[first_key]
                assert triggered['live'] and triggered['flags'] & 1 and triggered['state'] == 1, triggered
                after_contact = original_files()
                assert after_contact != before_files, 'Touching restored flag did not write original slot'
                if custom_world:
                    assert live()['custom_level']['checkpoint_saved']['slot'] == 1
                else:
                    assert profile() != original_profile, 'Retail flag did not write CLAW.USR'
                original_profile = profile()
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                recipe = next(r for r in checkpoint_payload()['mechanisms'] if (r['placement']['plane'],r['placement']['id'])==first_key)
                assert recipe['superFlags'] & 1 and recipe['animation'], recipe
                for disk in (False,True):
                    if disk:launch('flags-'+label+'-disk',2 if custom_world is None else None,custom_world)
                    restore(label+'_triggered_'+str(disk),resume_frames=0)
                    restored = flags()[first_key]
                    assert restored['live'] and restored['state'] == triggered['state'] and restored['flags'] & 5 == triggered['flags'] & 5, restored
                    # Walk back and across the spent flag; its save must not run again.
                    session._command(f"checkpoint-source {first['id']}");session._gate_wait();run(2)
                    hold(124,24);run(150)
                    assert original_files() == after_contact, 'Triggered flag saved again'
                    second = flags()[second_key]
                    session._command(f"checkpoint-source {second['id']}");session._gate_wait();run(2)
                    second = flags()[second_key]
                    assert second['live'] and second['state']==5 and not second['flags'] & 0x10001, second
                if custom_world is None:
                    hold(124,24);run(150)
                    second = flags()[second_key]
                    assert second['live'] and second['flags'] & 1 and second['state']==1, second
                    assert original_files() != after_contact, 'Second restored flag did not save'
                report[label+'_super_flags'] = {'untriggered':untriggered,'triggered':triggered,'input':session.input_state(),'disk_restore':True,'original_slot_written_on_contact_only':True}
            store = flag_store
        if args.slots_only or not any((args.flags_only,args.owner_save_only,args.sources_only,args.loot_only,args.progress_only,args.controllers_only,args.custom_only)):
            launch('slots',2)
            original_profile = profile()
            tap(20,'command,option,shift')
            chooser = live()['checkpoint_chooser']
            if not chooser['visible'] or chooser['count'] != 0 or not all('Empty' in x for x in chooser['labels']):
                raise RuntimeError(f'Empty chooser incorrect: {chooser}')
            tap(36)
            if not live()['checkpoint_chooser']['visible']:raise RuntimeError('Empty restore was enabled')
            tap(53)
            session._command('checkpoint-enemy');session._gate_wait();run(2)
            # Kill the enemy through delivered input before moving between saves.
            for _ in range(10):
                hold(58,20,'option');run(20)
                if (1,1490) in gone(live()['placements']):break
            records = []
            file = store/'ManualSuperCheckpoints/retail-2.clawcheckpoint'
            for i in range(4):
                hold(123,4);run(4)
                tap(20,'command')
                records.append([e for e in live()['custom_checkpoint'] if e['action']=='save'][-1])
                if i == 0:
                    # A format-6 single-slot envelope from before this change.
                    legacy = plistlib.loads(file.read_bytes())
                    legacy.pop('previous',None);legacy.pop('savedAt',None)
                    file.write_bytes(plistlib.dumps(legacy,fmt=plistlib.FMT_BINARY))
                envelope = plistlib.loads(file.read_bytes())
                if len(envelope.get('previous',[])) != min(i,2):raise RuntimeError('Wrong FIFO slot count')
                if i == 1 and checkpoint_payload(1)['values'] != plistlib.loads(legacy['payload'])['values']:
                    raise RuntimeError('Single-slot migration lost the old checkpoint')
            if len({(r['x'],r['y']) for r in records}) != 4:raise RuntimeError(f'Saves must be at four different spots: {records}')
            snapshots = [checkpoint_payload(i) for i in range(3)]
            if [p['values'][2:4] for p in snapshots] != [[r['x'],r['y']] for r in records[:0:-1]]:
                raise RuntimeError('FIFO did not retain saves 4, 3, 2')
            intact = file.read_bytes()
            for slot in (2,1):
                saved = records[3-slot]
                expected = {(r['plane'],r['id']) for r in snapshots[slot].get('removedPlacements',[])}
                restore(f'slot_{slot+1}',slot=slot,chooser=True,resume_frames=0)
                if file.read_bytes() != intact:raise RuntimeError('Restore reordered, deleted or saved slots')
            tap(53)
            saved = records[1];expected = {(r['plane'],r['id']) for r in snapshots[2].get('removedPlacements',[])}
            restore('pause_slot_3',slot=2,chooser=True,resume_frames=0)
            launch('slots-disk',2)
            tap(20,'command,option,shift')
            chooser = live()['checkpoint_chooser']
            if chooser['count'] != 3 or not all('ago' in x for x in chooser['labels']):
                raise RuntimeError(f'Persistent chooser labels incorrect: {chooser}')
            report['chooser_newest_first'] = chooser
            tap(53)
            for slot in (2,1,0):
                saved = records[3-slot]
                expected = {(r['plane'],r['id']) for r in snapshots[slot].get('removedPlacements',[])}
                restore(f'disk_slot_{slot+1}',slot=slot,chooser=slot>0,resume_frames=0)
                if file.read_bytes() != intact:raise RuntimeError('Disk restore changed slots')
            report['fifo_saves_2_3_4'] = records[1:]
            report['single_slot_migrated'] = True
        if args.slots_only or args.flags_only:
            pass
        elif args.owner_save_only:
            import shutil
            folder = store/'ManualSuperCheckpoints';folder.mkdir(parents=True)
            shutil.copy2(ROOT/'work/ipad-save-2026-11-06/retail-2.clawcheckpoint',folder)
            launch('owner-save',2)
            tap(20,'command,shift');run(30)
            result = json.loads((session.out/'custom-restore.json').read_text())
            if result['status'] != 'pass':raise RuntimeError(str(result))
            if len(live()['checkpoint_pickups']['remaining']) != 4:raise RuntimeError('Owner save lost its four drops')
            collect_drops('owner_settled_drops')
            tap(20,'command');tap(20,'command,shift');run(30)
            if live()['checkpoint_pickups']['remaining']:raise RuntimeError('Collected owner drops reappeared')
        elif args.sources_only:
            launch('statue',5)
            original_profile = profile()
            source = next(r for r in live()['placements'] if r['id']==7080 and r['live'])
            report['statue_before'] = source
            session._command(f"checkpoint-source {source['id']}");session._gate_wait();run(2)
            hold(124,6)
            for _ in range(12):
                hold(59,20,'control');run(20)
                if (source['plane'],source['id']) in gone(live()['placements']):break
            report['statue_after'] = next(r for r in live()['placements'] if r['id']==source['id'])
            if (source['plane'],source['id']) not in gone(live()['placements']):raise RuntimeError('Real input did not break the statue')
            run(240)
            if not live()['checkpoint_pickups']['remaining']:raise RuntimeError('Broken statue left no runtime loot')
            tap(20,'command')
            saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
            expected = gone(live()['placements'])
            restore('statue_floor_drop',resume_frames=0)
            collect_drops('statue_drop_collection')
            tap(20,'command')
            saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
            expected = gone(live()['placements'])
            restore('statue_collected_drop')
            if live()['checkpoint_pickups']['remaining']:raise RuntimeError('Collected statue drop returned')
        elif args.progress_only or args.loot_only or args.controllers_only:
            import zipfile
            custom = out/'custom-assets';custom.mkdir()
            with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/just_keep_calm.zip') as archive:
                archive.extractall(custom)
            world = next(p for p in custom.rglob('*') if p.suffix.lower()=='.wwd')
            scenarios = [('custom',world)] if args.custom_only else [('retail',None),('custom',world)]
            if args.retail_only:scenarios = [('retail',None)]
            if args.controllers_only and not args.custom_only:scenarios.reverse()
            for label, custom_world in scenarios:
                launch(label,2 if custom_world is None else None,custom_world)
                original_profile = profile()
                if args.controllers_only:
                    available = [r for r in live()['placements'] if r['logic'] in ('JumpSwitch','PathElevator','StartSteppingStone','BossStager') and r['live']]
                    report[label+'_controllers'] = available
                    representatives = {r['logic']:r for r in available if r['logic']!='BossStager'}
                    for mechanism in representatives.values():
                        session._command(f"checkpoint-mechanism {mechanism['id']}");session._gate_wait()
                        run(2)
                        session._command(f"checkpoint-mechanism {mechanism['id']}");session._gate_wait()
                        hold(124,1)
                        if mechanism['logic']=='StartSteppingStone':
                            for _ in range(180):
                                row = next(r for r in live()['placements'] if r['id']==mechanism['id'])
                                if row['state'] in (1002,1003,1004,1005,1006):break
                                run(1)
                            else:raise RuntimeError('Delivered movement did not activate native stepping stone')
                        elif mechanism['logic']=='PathElevator':
                            run(60)
                            row = next(r for r in live()['placements'] if r['id']==mechanism['id'])
                            if (row['x'],row['y'])==(mechanism['x'],mechanism['y']):raise RuntimeError('Native path did not move')
                        else:
                            hold(49,4);run(30)
                        tap(20,'command')
                        saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                        expected = gone(live()['placements'])
                        recipes = checkpoint_payload().get('mechanisms',[])
                        recipe = next((r for r in recipes if r['placement']['id']==mechanism['id']),None)
                        if not recipe:raise RuntimeError(f"Native controller recipe missing: {mechanism['logic']}")
                        restore(label+'_'+mechanism['logic'],resume_frames=0)
                        tap(53);restore(label+'_'+mechanism['logic']+'_pause',resume_frames=0)
                        launch(label+'-'+mechanism['logic']+'-disk',2 if custom_world is None else None,custom_world)
                        restore(label+'_'+mechanism['logic']+'_disk',resume_frames=0)
                    boss = next((r for r in available if r['logic']=='BossStager'),None)
                    if boss:
                        if custom_world is None:
                            # Wake the arena from an actual nearby placement,
                            # above its floor, before walking through the marker.
                            anchor = min((r for r in live()['placements'] if r['logic'] in ('BehindCandy','BehindAniCandy') and 0 < r['x']-boss['x'] < 200),key=lambda r:abs(r['y']-boss['y']))
                            session._command(f"checkpoint-mechanism {anchor['id']}");session._gate_wait()
                            run(45);hold(123,12);hold(124,8)
                        else:
                            session._command(f"checkpoint-mechanism {boss['id']}");session._gate_wait()
                            run(2);hold(124,8)
                        for _ in range(30):
                            if live()['checkpoint_boss_phase']==2:break
                            run(90)
                        if live()['checkpoint_boss_phase']!=2:raise RuntimeError(f'{label}: delivered movement did not complete native boss staging')
                        tap(20,'command')
                        saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                        expected = gone(live()['placements'])
                        if checkpoint_payload().get('bossStage',{}).get('phase')!=2:raise RuntimeError('Passed boss staging recipe missing')
                        restore(label+'_boss_play',resume_frames=0)
                        if live()['checkpoint_boss_phase']!=2:raise RuntimeError('Completed staging fired again after play restore')
                        tap(53);restore(label+'_boss_pause',resume_frames=0)
                        launch(label+'-boss-disk',2 if custom_world is None else None,custom_world)
                        restore(label+'_boss_disk',resume_frames=0)
                        if live()['checkpoint_boss_phase']!=2:raise RuntimeError('Completed staging fired again after disk restore')
                    continue
                if not args.loot_only:
                    candidates = [r for r in live()['placements'] if r.get('logic') in ('TriggerElevator','OneWayTriggerElevator','OneWayStartElevator') and r['live']]
                    if not candidates:raise RuntimeError(f'{label}: no real activated platform')
                    for platform in candidates:
                        identifier = platform['id']
                        session._command(f'checkpoint-mechanism {identifier}');session._gate_wait();run(2)
                        # Allow the native grid to wake the platform, then position
                        # above it again before delivered movement lands Claw.
                        session._command(f'checkpoint-mechanism {identifier}');session._gate_wait()
                        hold(124,4);run(120)
                        row = next(r for r in live()['placements'] if r['id']==identifier)
                        if (row['x'],row['y']) != (platform['x'],platform['y']):break
                    else:raise RuntimeError(f'{label}: no triggered platform moved: {row}')
                    tap(20,'command')
                    saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                    report[label+'_saved_clock'] = live().get('checkpoint_clock')
                    expected = gone(live()['placements'])
                    passed_events = {str(r['id']):r['state'] for r in live()['placements'] if r.get('logic')=='ClawDialogSoundTrigger' and r['state']==23}
                    if label=='retail' and not passed_events:raise RuntimeError('No completed retail dialog event to restore')
                    def positions():
                        return {str(r['id']):[r['x'],r['y'],r['state']] for r in live()['placements'] if r.get('logic') in ('TriggerElevator','OneWayTriggerElevator','OneWayStartElevator')}
                    run(30);future = positions();future_ms = live()['game_ms']
                    restore(label+'_progress_restore',resume_frames=0)
                    report[label+'_restored_clock'] = live().get('checkpoint_clock')
                    for _ in range(100):
                        if live()['game_ms'] >= future_ms:break
                        run(1)
                    report[label+'_trajectory'] = {'saved_ms':saved['elapsed_ms'],'future_ms':future_ms,'restored_ms':live()['game_ms']}
                    if live()['game_ms'] != future_ms or positions() != future:
                        raise RuntimeError(f'{label}: platform clock/continuation mismatch: {positions()} != {future}; {report[label+"_trajectory"]}')
                    tap(53);restore(label+'_progress_pause')
                    launch(label+'-disk',2 if custom_world is None else None,custom_world)
                    restore(label+'_progress_disk')
                    restored_events = {str(r['id']):r['state'] for r in live()['placements'] if str(r['id']) in passed_events}
                    if restored_events != passed_events:raise RuntimeError(f'{label}: completed event restarted')
                    report[label+'_activated_platform'] = {'initial':platform,'saved':row,'future':future,'input':session.input_state()}
                # Every treasure image/collision/award kind, through the same
                # native inventory-drop factory used by enemies and breakables.
                # Reuse a safe area and test one at a time to prevent overlap.
                # Labelled setup uses the actual native runtime-pickup factory.
                # It does not inject score, collection or a deleted placement.
                # Reuse the established core check's safe combat/checkpoint
                # area; the starting retail alcove has a wall and death tiles.
                if custom_world is None:
                    session._command('checkpoint-enemy');session._gate_wait();run(2)
                    for _ in range(10):
                        hold(58,20,'option');run(20)
                        if (1,1490) in gone(live()['placements']):break
                else:
                    session._command('checkpoint-place 1');session._gate_wait();run(2)
                session._command('checkpoint-loot');session._gate_wait();hold(124,8);run(30);hold(123,4)
                if live()['health']==0:raise RuntimeError(f'{label}: loot setup reached a death tile')
                session._command('checkpoint-loot-spawn');session._gate_wait();run(1)
                remaining = live()['checkpoint_pickups']['remaining']
                if not remaining:raise RuntimeError(f'{label}: native spawned treasure fixture missing')
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                remaining = live()['checkpoint_pickups']['remaining']
                restore(label+'_remaining_loot')
                tap(53);restore(label+'_remaining_loot_pause',resume_frames=0)
                launch(label+'-loot-disk',2 if custom_world is None else None,custom_world)
                restore(label+'_remaining_loot_disk')
                if len(live()['checkpoint_pickups']['remaining']) != len(remaining):
                    raise RuntimeError(f'{label}: remaining spawned treasure lost or duplicated')
                report[label+'_remaining_loot_count'] = len(remaining)
                report[label+'_remaining_loot_kinds'] = [r.get('bounce',{}).get('item',r['actor'][0]) for r in checkpoint_payload().get('loot',[])]
                restored_kinds = [r['item'] for r in live()['checkpoint_pickups']['remaining']]
                if sorted(restored_kinds) != sorted(report[label+'_remaining_loot_kinds']):
                    raise RuntimeError(f'{label}: restored drop item kinds changed')
                before = sum(live()['treasure_counts'])
                session._command('checkpoint-drop');session._gate_wait();hold(124,8);run(30)
                remaining_after_collection = len(remaining)-1
                if len(live()['checkpoint_pickups']['remaining']) != remaining_after_collection or sum(live()['treasure_counts']) != before+1:
                    raise RuntimeError(f'{label}: spawned treasure did not collect exactly once')
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                restore(label+'_collected_loot')
                if len(live()['checkpoint_pickups']['remaining']) != remaining_after_collection:raise RuntimeError(f'{label}: collected drop respawned or another drop was lost')
                if args.loot_only and custom_world is None:
                    collect_drops(label+'_initial_remaining')
                    tap(20,'command')
                    kind_file = store/'ManualSuperCheckpoints/retail-2.clawcheckpoint'
                    kind_baseline = kind_file.read_bytes()
                    crate = next(r for r in live()['placements'] if r['id']==1482 and r['live'])
                    session._command(f"checkpoint-source {crate['id']}");session._gate_wait();run(2)
                    for _ in range(10):
                        hold(58,20,'option');run(20)
                        if (crate['plane'],crate['id']) in gone(live()['placements']):break
                    if (crate['plane'],crate['id']) not in gone(live()['placements']):raise RuntimeError('Real input did not break the crate')
                    run(240)
                    if not live()['checkpoint_pickups']['remaining']:raise RuntimeError('Broken crate left no runtime loot')
                    tap(20,'command')
                    saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                    expected = gone(live()['placements'])
                    restore('crate_floor_drop',resume_frames=0)
                    collect_drops('crate_drop_collection')
                    tap(20,'command')
                    saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                    expected = gone(live()['placements'])
                    restore('crate_collected_drop')
                    for item in TREASURE_KINDS:
                        kind_file.write_bytes(kind_baseline)
                        tap(20,'command,shift');run(2)
                        session._command(f'checkpoint-loot-kind {item}');session._gate_wait();run(240)
                        if not live()['checkpoint_pickups']['remaining']:raise RuntimeError(f'Item {item} fixture missing')
                        tap(20,'command')
                        saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                        expected = gone(live()['placements'])
                        restore(f'kind_{item}_settled',resume_frames=0)
                        collect_drops(f'kind_{item}_collected')
                        tap(20,'command')
                        saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                        expected = gone(live()['placements'])
                        restore(f'kind_{item}_absent')
                        if live()['checkpoint_pickups']['remaining']:raise RuntimeError(f'Collected item {item} returned')
        else:
            if not args.custom_only:
                launch('route',2)
                if live().get('level') != 2:
                    raise RuntimeError('Diagnostic original New Game did not reach Level 2')
                baseline = gone(live()['placements'])
                # Labelled score fixture: the real loot route crosses the original
                # current HUD threshold and earns the life before saving.
                session._command('checkpoint-score');session._gate_wait();run(1)
                # Labelled position fixture at the real Level 2 enemy. Damage,
                # death and pickup removal still require confirmed real input.
                session._command('checkpoint-enemy');session._gate_wait();run(2)
                for _ in range(10):
                    hold(58,20,'option');run(20)
                    if (1,1490) in gone(live()['placements']):break
                if (1,1490) not in gone(live()['placements']):raise RuntimeError('Level 2 enemy survived delivered attacks')
                # Leave the actual killed enemy's drop on the floor, save,
                # restart, then collect it through confirmed window input.
                run(240)
                drops = live()['checkpoint_pickups']['remaining']
                if not drops or any(r['bouncing'] for r in drops):raise RuntimeError('Killed enemy left no settled drop')
                original_profile = profile()
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                restore('enemy_floor_drop',resume_frames=0)
                collect_drops('enemy_floor_drop_collection')
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                restore('enemy_collected_drop',resume_frames=30)
                if live()['checkpoint_pickups']['remaining']:raise RuntimeError('Collected enemy drop reappeared')
                session._command('checkpoint-loot');session._gate_wait()
                hold(124,8);run(30);hold(123,4)
                before = live();expected = gone(before['placements']) - baseline
                if (1,1490) not in expected or sum(before['treasure_counts']) < 1:
                    raise RuntimeError('Real input did not kill the enemy and collect treasure')
                (out/'before-save.json').write_text(json.dumps(before))
                for c in 'MPHOTSTUFF':
                    tap(KEYS[c])
                audio('audio-before-save')
                original_profile = profile()
                tap(20,'command')
                saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
                expected = gone(live()['placements'])
                if not any(identifier & 0x80000000 for _,identifier in expected):
                    raise RuntimeError('Retail route did not retain the collected duplicate-ID placement')

                if saved['score'] < 500000 or saved['lives'] <= 3 or saved['hud_extra_life_threshold'] <= saved['score']:
                    raise RuntimeError(f'Real loot route did not earn the extra life: {saved}')
                if saved['power_kind'] == 0 or saved['power_ms'] == 0:
                    raise RuntimeError('No timed powerup saved')
                report['saved'] = saved
                file = store/'ManualSuperCheckpoints/retail-2.clawcheckpoint'
                valid = file.read_bytes()
                envelope = plistlib.loads(valid);payload = plistlib.loads(envelope['payload'])
                if hashlib.sha256(envelope['payload']).digest() != envelope['digest']:
                    raise RuntimeError('Checkpoint checksum failed')
                if payload['version'] != 6 or len(payload['values']) != 18 or {(r['plane'],r['id']) for r in payload['removedPlacements']} != expected:
                    raise RuntimeError('Not a super-checkpoint stats record')
                hold(123,30);run(90)
                restore('direct_restore');audio('audio-after-restore')
                tap(53)
                if live().get('state_vtable') != '0x50c044':
                    raise RuntimeError(f'Pause menu did not open: {live().get("state_vtable")}')
                tap(20,'command')
                if file.read_bytes() != valid:
                    raise RuntimeError('Save was available in the pause menu')
                restore('pause_restore')
                launch('relaunch',2)
                fresh = live()
                if fresh['health'] == saved['health'] and fresh['ammo'] == saved['ammo'] and fresh['treasure_counts'][:9] == saved['treasure'][:9] and fresh['score'] == saved['score']:
                    raise RuntimeError('Fresh retail level did not change health/ammo/treasure before disk restore')
                report['retail_fresh_before_disk_restore'] = {k:fresh[k] for k in ('health','ammo','treasure_counts','score','game_ms')}
                restore('relaunch_restore');audio('audio-after-relaunch')
                launch('load-game-menu')
                # Menu navigation is checked by page/selection observations below.
                if live().get('menu_page') == 10000:tap(36)
                for _ in range(12):
                    if live().get('menu_selected') == 11002:break
                    tap(125)
                if live().get('menu_selected') != 11002:raise RuntimeError('Load Game missing')
                tap(36)
                # With no original save records, disabled rows lead back to
                # Main (10001); a manual slot must not unlock those rows or replace
                # the original IFC checkpoint pages with a native chooser.
                source = (ROOT/'App/ClawApp.swift').read_text()
                native = (ROOT/'Sources/ClawNativeMenuInterface.swift').read_text()
                if any(token in source+native for token in ('showCheckpointChoices','chooseCheckpoint','retailCustomCheckpointURL','checkpointChoicesActive')):
                    raise RuntimeError('Custom Load Game chooser remains')
                menu_before = live()
                tap(125);tap(36)
                if live().get('menu_page') not in (10001,11200,11202):
                    raise RuntimeError(f'Original Load Game flow changed: {live().get("menu_page")}')
                if len(live()['custom_checkpoint']):raise RuntimeError('Load Game restored a manual checkpoint')
                report['original_load_game'] = {'before':menu_before['menu_page'],'after':live()['menu_page']}
                # Corruption and a valid envelope with an invalid format are rejected before a level load.
                for name,data in [('corrupt',b'invalid checkpoint'),('wrong-version',None),('legacy-format-2',2),('invalid-mechanism',None),('invalid-loot',None),('invalid-motion',None),('invalid-bounce',None),('invalid-frame-phase',None),('invalid-boss-stage',None)]:
                    if data is None or data == 2:
                        payload = plistlib.loads(plistlib.loads(valid)['payload'])
                        if name=='invalid-mechanism':
                            if not payload.get('mechanisms'):raise RuntimeError('No mechanism recipe to validate')
                            payload['mechanisms'][0]['primary']=[]
                        elif name=='invalid-loot':
                            payload['loot']=[{'logic':'unknown','identifier':1,'z':901,'flags':262144,'actor':[]}]
                        elif name=='invalid-motion':payload['mechanisms'][0]['motion']=[]
                        elif name=='invalid-bounce':payload['loot']=[{'logic':'BouncingGoodie','identifier':0,'z':4001,'flags':262144,'actor':[0,200,300]+[0]*10,'bounce':{'item':62,'gravity':800.0,'velocityX':0.0,'velocityY':0.0}}]
                        elif name=='invalid-frame-phase':payload['framePhase']=3
                        elif name=='invalid-boss-stage':payload['bossStage']={'phase':1,'healthMeter':False}
                        else:payload['version'] = 2 if data == 2 else 999
                        raw = plistlib.dumps(payload,fmt=plistlib.FMT_BINARY)
                        data = plistlib.dumps({'payload':raw,'digest':hashlib.sha256(raw).digest()},fmt=plistlib.FMT_BINARY)
                    file.write_bytes(data)
                    count = len(live()['custom_checkpoint']);tap(20,'command,shift')
                    result = json.loads((session.out/'custom-restore.json').read_text())
                    if result['status'] != 'fail' or len(live()['custom_checkpoint']) != count:
                        raise RuntimeError(f'{name} checkpoint was accepted')
                    if name == 'legacy-format-2' and 'legacy' not in result['error']:
                        raise RuntimeError('Old checkpoint did not get the short legacy message')
                    report[name] = result
                file.write_bytes(valid)
            # Custom map uses the same app slot, independent from its placed checkpoints.
            import zipfile
            custom = out/'custom';custom.mkdir()
            with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/just_keep_calm.zip') as archive:
                archive.extractall(custom)
            world = next(p for p in custom.rglob('*') if p.suffix.lower()=='.wwd')
            launch('custom-route',custom_world=world)
            if args.custom_only:original_profile = profile()
            original_custom_load = live()['custom_level']['state_load_arguments']
            report['original_custom_load_arguments'] = original_custom_load
            session._command('checkpoint-place 1');session._gate_wait();run(2)
            baseline = gone(live()['placements'])
            session._command('checkpoint-loot');session._gate_wait()
            hold(124,8);run(30);hold(123,4)
            loot = live()['custom_level']['manual_checkpoint_loot_fixture']['id']
            if not any(key[1] == loot for key in gone(live()['placements']) - baseline):
                raise RuntimeError('Custom map original treasure was not collected')
            report['custom_collected_placement'] = loot
            tap(20,'command')
            saved = [e for e in live()['custom_checkpoint'] if e['action']=='save'][-1]
            report['custom_saved'] = saved
            expected = gone(live()["placements"])
            hold(58,20,'option');hold(124,20)
            automatic = {p.name:p.read_bytes() for p in (store/'CustomSaves').glob('*')}
            restore('custom_direct_restore')
            if not live().get('custom_flag'):raise RuntimeError('Custom restore loaded retail map')
            if live()['custom_level']['state_load_arguments'] != original_custom_load:
                raise RuntimeError('Custom restart did not use the original custom constructor arguments')
            launch('custom-relaunch',custom_world=world)
            fresh = live()
            if fresh['health'] == saved['health'] and fresh['ammo'] == saved['ammo'] and fresh['treasure_counts'][:9] == saved['treasure'][:9] and fresh['score'] == saved['score']:
                raise RuntimeError('Fresh custom level did not change health/ammo/treasure before disk restore')
            report['custom_fresh_before_disk_restore'] = {k:fresh[k] for k in ('health','ammo','treasure_counts','score','game_ms')}
            restore('custom_relaunch_restore')
            if not live().get('custom_flag'):raise RuntimeError('Disk custom restore loaded retail map')
            if automatic != {p.name:p.read_bytes() for p in (store/'CustomSaves').glob('*')}:
                raise RuntimeError('Manual slot changed level-owned super checkpoints')
            if len(list((store/'ManualSuperCheckpoints').glob('*.clawcheckpoint'))) != (1 if args.custom_only else 2):
                raise RuntimeError('Retail and custom maps did not retain separate slots')
            # The original save file and retired feature files stay untouched/absent.
            if profile() != original_profile:
                raise RuntimeError('Custom checkpoint modified CLAW.USR')
            if any(p.exists() for p in (store/'save-anywhere.json',out/'settings/save-anywhere-setting.json')):
                raise RuntimeError('Retired checkpoint files were written')
            source = (ROOT/'App/ClawApp.swift').read_text()
            overlay = source.split('if menu.checkpointOverlay {')[1].split('if let toast')[0]
            if 'ForEach(0..<3' not in overlay or 'Save custom checkpoint' not in overlay or 'hasCustomCheckpointSlot(slot)' not in overlay:
                raise RuntimeError('Overlay must contain only the custom checkpoint controls')
            for path in (ROOT/'Sources').glob('*.swift'):
                text = path.read_text()
                if any(token in text for token in ('customReplay','ClawCustomReplay','audio.status.', 'saveAnywhere','ClawAnywherePosition')):
                    raise RuntimeError(f'Retired implementation remains: {path}')
        report['status'] = 'pass'
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if session:
            session.close()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    for frame in out.rglob('*.png'):
        if report['status'] != 'fail' or frame.name != 'frame-fail.png':
            frame.unlink()
    print(json.dumps(report))
    return 0 if report['status']=='pass' else 1


if __name__ == '__main__':
    # Serialize with app builds and the other app-lane gameplay checks.
    with open(ROOT/'work/.claw-app-build.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sys.exit(main())
