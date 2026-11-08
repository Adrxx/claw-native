"""Shared preflight, precise dynamic refusals and late full-package interactions."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile
from real_input import Session, alive, build_helper

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crazyhook/checks'


def diagnostics():
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check()


def check():
    out=OUT/'diagnostics';out.mkdir(parents=True,exist_ok=True)
    report=dict(group='diagnostics',status='fail',marks={},errors=[],ipad='Shared Files/open-in importer checked on Mac Catalyst; iPad build/runtime not tested')
    report_path=OUT/'diagnostics.json'
    def save(): report_path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    census=json.loads((ROOT/'work/crazyhook/features.json').read_text())
    maps={}
    for sample in census['samples']:
        archive=ROOT/sample['archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==sample['sha256'],sample['name']
        folder=out/'input'/archive.stem;folder.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            assert all((folder/i.filename).resolve().is_relative_to(folder.resolve()) and not ((i.external_attr>>16)&0o170000)==0o120000 for i in z.infolist())
            z.extractall(folder)
        maps[sample['name']]=next(p for p in folder.rglob('*') if p.suffix.lower()=='.wwd')
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report['binary_sha256']=hashlib.sha256((app/'Contents/MacOS/Claw').read_bytes()).hexdigest()
    probe=out/'preflight';probe.mkdir(exist_ok=True)
    (probe/'apis.json').write_text(json.dumps(sorted(census['api_symbols'])))
    request=probe/'request.json';request.write_text(json.dumps({k:str(v) for k,v in maps.items()}))
    session=Session(probe,helper=helper)
    try:
        session.launch(app,{},['--no-paper-startup','--capability-package-check',str(request),'--save-dir',str(probe/'saves'),'--settings-dir',str(probe/'settings')],start_seconds=180)
        session.run(1)
        result=json.loads((probe/'capabilities.json').read_text())
        report['marks']['preflights']=result;save()
        assert len(result['packages'])==30
        assert all(v=='same shared preflight accepted' for v in result['imports'].values()),result['imports']
        assert all('error' not in v for v in result['packages'].values()),{k:v for k,v in result['packages'].items() if 'error' in v}
        pending={k:v for k,v in result['apis'].items() if v!='implemented'}
        report['pending_portable_apis']=pending
        assert result['apis']
        registry={feature:group for group,features in result['registry'].items() for feature in features}
        assert set(registry)==set(census['features']),(set(census['features'])-set(registry),set(registry)-set(census['features']))
        classified={}
        for sample in census['samples']:
            classified[sample['name']]={}
            for feature in sample['features']:
                entry=census['features'][feature]
                assert registry[feature]==entry['implementation_task'].removeprefix('app-crazyhook-')
                provenance=sample['features'][feature]
                assert provenance, (sample['name'],feature)
                status={'png-files':'preserved file candidates; runtime PNG registration not inferred; assets evidence resolves siblings and uses','bundled-core-script':'retained as data; portable services supplied by bounded host; core replacement never executed'}.get(feature,'native operation; focused group evidence; dynamic callbacks guarded')
                classified[sample['name']][feature]=dict(group=registry[feature],provenance=provenance,status=status)
        report['marks']['feature_provenance']=classified
        groups={}
        for group in result['registry']:
            if group=='diagnostics': continue
            path=OUT/(group+'.json');evidence=json.loads(path.read_text())
            assert evidence['status']=='pass',(group,evidence.get('error'))
            groups[group]=dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status=evidence['status'])
        report['marks']['focused_evidence']=groups;save()
    finally:
        session.close()
        clean(probe)

    base=maps["Cannonballin'"]
    def fixture(name,source):
        folder=out/'synthetic'/name
        shutil.rmtree(folder,ignore_errors=True);folder.mkdir(parents=True)
        world=folder/(name+'.wwd');shutil.copy2(base,world)
        shutil.copytree(base.with_suffix(''),world.with_suffix(''))
        logics=world.with_suffix('')/'LOGICS';logics.mkdir(exist_ok=True)
        (logics/'MAIN.LUA').write_text('-- Clearly synthetic diagnostics fixture\n'+source+'\n')
        return world
    synthetic={
        'dll':(fixture('dll',"function OnGameplay() MultClawSpeed(.75);SetNormalJumpHeight(292);SetClawFallSpeedCap(500);SetMusicVolume(23);ffi.load('RequiredWeather.dll') end"),'Unsupported execution','RequiredWeather.dll'),
        'module':(fixture('module',"function OnMapLoad() require('native_weather') end"),'Unsupported execution','MODULES/NATIVE_WEATHER.DLL'),
        'x86':(fixture('x86',"function OnGameplay() PrivateChamAdd(0x12345678) end"),'Unsupported execution','305419896'),
        'missing':(fixture('missing',"function OnMapLoad() require('missing_weather') end"),'Missing companion file','MODULES/missing_weather.LUA'),
        'asset':(fixture('asset',"function OnGameplay() PlaySound('CUSTOM_REQUIRED_MISSING') end"),'Missing companion file','CUSTOM_REQUIRED_MISSING'),
        'object':(fixture('object',"function OnGameplay() CreateObject{name='Failure'} end"),'Unsupported execution','object Failure'),
        'exit':(fixture('exit',"-- ExitLevel is triggered after ordinary load."),None,None),
        'pending':(fixture('pending',"function OnGameplay() ffi.cast('int*',0x12345678)[0]=1 end"),'Not implemented','305419896'),
        'message':(fixture('message',"function OnGameplay() if _messageRequested and not _shown then _shown=true;MessageBox('Diagnostics native sheet','Synthetic') end end"),None,None),
        'dormant':(fixture('dormant',"if false then ffi.load('Unused.dll') end; MultiMessage[0]=3;MultiMessage[1]=5;MultiMessage[2]=7;ResetMultiMessage();assert(MultiMessage[0]==0 and MultiMessage[1]==0 and MultiMessage[2]==0);SetMusicVolume(0);assert(GetMusicVolume()==0);SetMusicVolume(100);assert(GetMusicVolume()==100);SetMusicVolume(23);assert(GetMusicVolume()==22,'quantized music volume '..tostring(GetMusicVolume()));assert(mdl_exe._GetSoundA(Game(10),'GAME_NULL')[4],'null sound handle')"),None,None),
    }
    if report.get('pending_portable_apis'):
        synthetic['physics-pending']=(fixture('physics-pending',"function OnGameplay() SetNormalJumpHeight(292) end"),'Not implemented','SetNormalJumpHeight')
    (synthetic['object'][0].with_suffix('')/'LOGICS/FAILURE.LUA').write_text("function main(self) ffi.load('ObjectWeather.dll') end\n")
    for key in ('module','dormant'):
        package=synthetic[key][0].with_suffix('')/'MODULES';package.mkdir(exist_ok=True)
        (package/'native_weather.dll').write_bytes(b'Synthetic inert file; never executed')
    malformed=out/'synthetic'/'malformed';malformed.mkdir(exist_ok=True)
    (malformed/'malformed.wwd').write_bytes(b'not a WWD')
    synthetic['malformed']=(malformed/'malformed.wwd','Invalid custom level',None)
    missing_file=out/'synthetic'/'missing-file';missing_file.mkdir(exist_ok=True)
    missing_world=missing_file/'Missing Companion.wwd';shutil.copy2(maps['Pixelcove'],missing_world)
    synthetic['missing-file']=(missing_world,'Missing companion file',None)
    # The native document importer uses the same preflight as the picker.
    negative=out/'negative-preflight';negative.mkdir(exist_ok=True)
    request=negative/'request.json';request.write_text(json.dumps({k:str(v[0]) for k,v in synthetic.items()}))
    session=Session(negative,helper=helper)
    try:
        session.launch(app,{},['--no-paper-startup','--capability-package-check',str(request),'--save-dir',str(negative/'saves'),'--settings-dir',str(negative/'settings')],start_seconds=180)
        session.run(1)
        preflight=json.loads((negative/'capabilities.json').read_text())
        for name in ('malformed','missing-file'):
            message=preflight['packages'][name]['error']
            assert message==preflight['imports'][name],(name,message,preflight['imports'][name])
        assert 'error' not in preflight['packages']['dormant']
        assert 'error' not in preflight['packages']['module']
        report['marks']['negative_preflights']=preflight;save()
    finally:
        session.close();clean(negative)
    for name,(world,kind,detail) in synthetic.items():
        result=play(out,name,world,app,helper,kind,detail)
        report['marks'][name]=result;save()
        if result['status']!='pass':report['errors'].append(name)
    for name,label in [('Arcana v1.3','arcana'),('City in the Depth','city')]:
        result=play(out,label,maps[name],app,helper)
        report['marks'][label]=result;save()
        if result['status']!='pass':report['errors'].append(label)
    report['marks']['original_archives_unchanged']=all(hashlib.sha256((ROOT/s['archive']).read_bytes()).hexdigest()==s['sha256'] for s in census['samples'])
    assert report['marks']['original_archives_unchanged']
    if report.get('pending_portable_apis'):report['errors'].append('pending portable APIs')
    report['status']='pass' if not report['errors'] else 'fail';save()
    return report


def clean(folder):
    for pattern in ('hud-*.png','frame-*.png'):
        for path in folder.glob(pattern):
            if path.name!='frame-fail.png':path.unlink()


class DiagnosticSession(Session):
    def _gate_wait(self, seconds=180):
        end=time.monotonic()+seconds
        posted=False
        while time.monotonic()<end:
            message=self.out/'script-message.json'
            if message.exists() and json.loads(message.read_text()).get('waiting') and not posted:
                self.dialog_input=self._post(('key',36))
                posted=True
            gate=self.gate()
            if gate.get('status')=='fail' or gate.get('seq',-1)>=self.seq:
                self.frames=gate.get('frame',self.frames)
                return gate
            if self.pid and not alive(self.pid):
                raise RuntimeError('diagnostic instance exited before answering input')
            time.sleep(.01)
        raise RuntimeError('diagnostic gate timed out')


def physics_check(session,script,live):
    """Controlled starts, original Arcana callbacks, and confirmed window keys."""
    def state(): return live()['custom_level']['lua']['physics']
    def evaluate(text):
        session._command('lua-gameplay-check '+base64.b64encode(text.encode()).decode())
        session._gate_wait()
        assert not session.failed(),session.gate()
    def frame():
        session.run(1)
        assert not session.failed(),session.gate()
        return dict(state()['player'],uptime_ms=live()['uptime_ms'])
    defaults='MultClawSpeed(1);SetNormalJumpHeight(145);SetRunningJumpHeight(170);SetCatnipJumpHeight(195);SetJordanJumpHeight(195);SetClawFallSpeedCap(1000)'
    result={'scope':'Controlled player starts in the full unmodified Arcana package; movement and jump/hold use confirmed real window events'}
    # Dormant proxies receive Name on first callback; identify this unchanged
    # serialized controller by its ID and coordinates before activating it.
    script('_physicsOrigin={GetClaw().X,GetClaw().Y};_moon=GetObject(589);assert(_moon and _moon.X==42371 and _moon.Y==5694);_moon.Flags.AlwaysActive=true;TeleportClaw(42371,4000);_moon:Logic();assert(_moon.Name=="MoonGravity" and _moon.State==2)')
    session.run(2)
    moon=state()
    assert moon['speeds']==[169,225,214,-169,-225,-214,169,-169,169,-169],moon
    assert moon['jump_bases']==[503,429,374,374] and moon['fall_cap']==500,moon
    result['moon_entry']=moon
    (session.out/'physics.json').write_text(json.dumps(result,indent=2)+'\n')
    script('TeleportClaw(_physicsOrigin[1],_physicsOrigin[2]);_moon:Logic();assert(_moon.State==1)')
    session.run(2)
    restored=state()
    assert restored['speeds']==[225,300,285,-225,-300,-285,225,-225,225,-225],restored
    assert restored['jump_bases']==[250,249,250,250] and restored['fall_cap']==1000,restored
    result['moon_exit']=restored
    # Keep tests away from the original controller's region. The package is
    # unchanged; only the live actor's initial conditions are controlled.
    start='local c=GetClaw();c.X=2450;c.Y=3770;c.State=24;c.PhysicsType=1;c.SpeedX=0;c.SpeedY=0;c.Flags.OnElevator=false;c.Flags.NoHit=true;c.Flags.Safe=true;PlayerData().ConveyorBeltForce=0;PlayerData().RunningSpeedTime=1500;ClawGivePowerup(0,0);'
    speeds=[]
    for multiplier in (1,.75,.5,.75,'r'):
        evaluate(start+'MultClawSpeed('+repr(multiplier)+')')
        before=frame()
        session.post('press',124,'down')
        samples=[frame() for _ in range(10)]
        session.post('press',124,'up')
        delta=samples[-1]['x']-before['x']
        assert delta>0,(multiplier,before,samples)
        expected=225 if multiplier=='r' else int(225*multiplier+.5)
        assert any(p['speed_x']==expected for p in samples) and all(p['speed_x'] in (0,expected) for p in samples),(multiplier,samples)
        elapsed=sum(p['frame_ms'] for p in samples)
        speeds.append(dict(multiplier=multiplier,delta=delta,elapsed_ms=elapsed,samples=samples))
    result['horizontal']=speeds
    (session.out/'physics.json').write_text(json.dumps(result,indent=2)+'\n')
    # The admitted integrator retains fractional carry, so integer positions
    # need not match between resets. Require the measured displacement order
    # as well as the exact per-frame native speeds above.
    rates=[s['delta']/s['elapsed_ms'] for s in speeds]
    assert rates[0]>rates[1]>rates[2] and rates[4]>rates[3]>rates[2],speeds
    assert abs(speeds[0]['delta']-speeds[4]['delta'])<=2 and abs(speeds[1]['delta']-speeds[3]['delta'])<=2,speeds
    # The four jump branches have distinct height bases. Hold and release
    # affect the original timer and resulting trajectory, not a host offset.
    jumps=[]
    setters=['SetNormalJumpHeight','SetRunningJumpHeight','SetCatnipJumpHeight','SetJordanJumpHeight']
    # The spawn room has a low ceiling. Use the controller's open region for
    # full-height trajectories, after checking its real entry/exit callbacks.
    script('_moon.State=3')
    for mode in range(4):
        if mode==3:
            for key in (46,35,38,31,15,2,0,45):
                session.post('key',key);session.run(5)
        for height,hold in ((145 if mode==0 else 170 if mode==1 else 195,40),(292,40),(292,2)):
            setup=start+defaults+';c.X=42371;c.Y=4000;'+setters[mode]+'('+str(height)+');'
            if mode==1:setup+='PlayerData().RunningSpeedTime=0;'
            if mode==2:setup+='ClawGivePowerup(Powerup.Catnip,30);'
            evaluate(setup)
            session.post('press',49,'down')
            samples=[frame() for _ in range(hold)]
            session.post('press',49,'up')
            samples += [frame() for _ in range(65)]
            apex=min(p['y'] for p in samples)
            assert apex<4000 and any(p['state']==4 for p in samples),(mode,height,hold,samples)
            if hold==40:assert abs((4000-apex)-height)<=1,(mode,height,apex)
            if mode==3:assert samples[0]['jordan']!=0,samples[0]
            if mode==2:assert samples[0]['powerup']==0x26bc,samples[0]
            if mode==1:assert samples[0]['running_timer']==0,samples[0]
            jumps.append(dict(mode=mode,height=height,hold=hold,apex=apex,samples=samples))
            (session.out/'physics.json').write_text(json.dumps(dict(result,jumps=jumps),indent=2)+'\n')
        group=jumps[-3:]
        assert group[1]['apex']<group[0]['apex'] and group[1]['apex']<group[2]['apex'],group
    result['jumps']=jumps
    for key in (46,35,38,31,15,2,0,45):
        session.post('key',key);session.run(5)
    falls=[]
    for cap in (500,1000):
        evaluate(start+defaults+';GetClaw().X=42371;GetClaw().Y=4000;SetClawFallSpeedCap('+str(cap)+');')
        # One delivered step lets the original support check enter falling.
        session.post('press',124,'down')
        samples=[frame() for _ in range(80)]
        session.post('press',124,'up')
        peak=max(p['velocity_y'] for p in samples)
        assert peak<=cap and peak>=cap-1,(cap,peak,samples)
        falls.append(dict(cap=cap,peak=peak,samples=samples))
    result['falls']=falls
    # Invalid values must fail before changing storage; repeated speed calls
    # are absolute-base operations, and 'r' restores both signs exactly.
    script(defaults+";local a=pcall(SetNormalJumpHeight,0/0);local b=pcall(SetClawFallSpeedCap,math.huge);local c=pcall(MultClawSpeed,math.huge);assert(not a and not b and not c);MultClawSpeed(.75);MultClawSpeed(.75);MultClawSpeed('r')")
    result['negative_values']=state()
    # Leave settings changed so normal teardown must restore the originals.
    script('SetNormalJumpHeight(292);SetRunningJumpHeight(292);SetCatnipJumpHeight(292);SetJordanJumpHeight(292);MultClawSpeed(.75);SetClawFallSpeedCap(500);TeleportClaw(_physicsOrigin[1],_physicsOrigin[2])')
    return result


def play(out,name,world,app,helper,kind=None,detail=None):
    folder=out/name;folder.mkdir(exist_ok=True)
    for pattern in ('*.json','*.png'):
        for path in folder.glob(pattern):path.unlink()
    shutil.rmtree(folder/'saves',ignore_errors=True)
    session=DiagnosticSession(folder,helper=helper)
    result=dict(status='fail')
    def live():return json.loads((folder/'live.json').read_text())
    def tap(key):
        session.post('key',key);session.run(15)
        assert not session.failed(),session.gate()
    def script(text):
        session._command('lua-gameplay-check '+base64.b64encode(text.encode()).decode());session.run(1)
        assert not session.failed(),session.gate()
        return live()['custom_level']['gameplay_check']
    try:
        session.launch(app,{},['--custom-dir',str(world.parent),'--no-paper-startup','--lua-runtime-check','--long-trace','--save-dir',str(folder/'saves'),'--settings-dir',str(folder/'settings')],start_seconds=180)
        session.run(60)
        if live().get('menu_page')==10000:tap(36)
        for _ in range(10):
            if live().get('menu_selected')==11003:break
            tap(125)
        assert live().get('menu_selected')==11003,live()
        tap(36);assert live().get('custom_dialog'),live()
        tap(36);session.run(10)
        if kind:
            message=live().get('custom_error','')
            assert kind in message,(kind,message,live().get('custom_level'))
            if detail:assert detail in message,(detail,message)
            if name not in ('malformed','missing-file'):
                assert ('LOGICS/FAILURE.LUA:1' if name=='object' else 'LOGICS/MAIN.LUA:2') in message,message
                assert live()['custom_level'].get('failure_cleanup'),live()['custom_level']
                if name=='dll':
                    physics=live()['custom_level']['lua']['physics']
                    assert physics['speeds']==[225,300,285,-225,-300,-285,225,-225,225,-225] and physics['jump_bases']==[250]*4 and not physics['modified'],physics
                    result['physics_failure_restoration']=physics
                    assert live()['custom_level'].get('music_volume_restored'),live()['custom_level']
                    result['music_failure_restoration']=True
            result.update(message=message,cleanup=live().get('custom_level'),menu=live().get('menu_page'))
            # Dismiss selector failures and prove the menu still accepts input.
            if live().get('custom_dialog'):tap(53)
            assert live().get('menu_page') in (10000,10001),live()
            before=live().get('menu_selected');tap(125)
            assert before!=live().get('menu_selected'),live()
        else:
            assert not live().get('custom_dialog') and live().get('custom_flag')==1,live()
            session.run(30)
            if name=='arcana':
                for key in (125,125,36,126,126,36,125,36):tap(key)
                session.run(45)
                result['late_interaction']=script("assert(GetObject(3206).Difficulty==1);assert(GetMainPlane():GetTile(117,164)==203);assert(_planeCheckCollision(117*64+32,164*64+32)==3);local star=LoopThroughObjects(function(o) if o.Name=='BackgroundStarsPlacing' and o.State>0 then return o end end);assert(star and star.back:GetTile(star.tx,star.ty)==star.State)")
                result['interaction_scope']='Delivered resolution/difficulty keys; original star placement and ladder collision in full unchanged Arcana package'
                result['physics']=physics_check(session,script,live)
            elif name=='city':
                result['late_interaction']=script("_extraBefore=GetObject(4088).extra;GetObject(4088).extra=true;_boss=CreateObject{name='Areti2',image='CUSTOM_ARETI'};_boss.Flags.AlwaysActive=true")
                script("assert(_boss.State==1 and _boss.movementInput[22].bullets[2].spread_type=='domain_expansion');_boss.stage=22;_boss.hotX=11950;_boss.hotY=2100;_boss.spellcycle=GetTime()-2600;_boss.spellcycleflag=0;for i=1,20 do _boss.bulletlastused[i]=GetTime()+100000 end;_boss.bulletlastused[2]=GetTime()-28000")
                expanded=session.mark('city-domain-expanded')
                script("assert(_boss.movementInput[26].bullets[2].spread_type=='domain_collapse');_boss.stage=26;_boss.spellcycle=GetTime();_boss.spellcycleflag=0;for i=1,20 do _boss.bulletlastused[i]=GetTime()+100000 end;_boss.bulletlastused[2]=GetTime()-1000")
                restored=session.mark('city-domain-restored')
                assert expanded['palette_sha256']!=restored['palette_sha256']
                result['late_interaction'].update(expanded=expanded['palette_sha256'],restored=restored['palette_sha256'])
                result['interaction_scope']='Controlled late stages 22/26; original Areti2 callbacks and unchanged attack tables in full City package'
                script('_boss:Destroy();GetObject(4088).extra=_extraBefore;CameraToClaw()')
            if name=='dormant':
                result['native_helpers']=script("local old=nRes(11,473);StunClaw(250);assert(nRes(11,473)==250);StunClaw(old);StopSound('GAME_NULL');assert(mdl_exe._GetSoundA(Game(10),'CUSTOM_REQUIRED_MISSING')==nil)")
            if name=='message':
                # Start the synchronous sheet after the menu Enter key is up.
                script('_messageRequested=true')
            before=session.mark(name+'-before')
            session.post('press',124,'down');session.run(20);session.post('press',124,'up')
            after=session.mark(name+'-after')
            assert before['player']['x']!=after['player']['x']
            result['movement']=[before['player'],after['player']]
            if name=='message':
                message=json.loads((folder/'script-message.json').read_text())
                assert message==dict(title='Synthetic',text='Diagnostics native sheet',waiting=False),message
                result['native_sheet']=message
                result['dialog_real_input']=session.dialog_input

            if name=='exit':
                script('ExitLevel()')
                assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
                assert live()['custom_level'].get('script_exit_requested') and live()['custom_level'].get('unloaded'),live()
                result['exit']='Lua ExitLevel posts original 0x8023 and returns to menu with teardown'
                result['input_transitions']=session.transitions();result['status']='pass'
                return result
            for key in (46,35,1,8,32,37,37,16):tap(key)
            assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',10),live()
            for _ in range(10):
                if session.wait(lambda:live().get('state_vtable')!='0x50c0c4',12):break
                tap(36)
            assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
            assert live()['custom_level'].get('unloaded'),live()
            if name=='dormant':
                assert live()['custom_level'].get('music_volume_restored'),live()['custom_level']
                result['music_volume_restored']=True
            result['exit']='MPSCULLY, results, menu; package unloaded'
            if name=='arcana':
                physics=live()['custom_level']['lua']['physics']
                assert physics['speeds']==[225,300,285,-225,-300,-285,225,-225,225,-225] and physics['jump_bases']==[250]*4 and not physics['modified'],physics
                result['physics']['teardown']=physics
        result['input_transitions']=session.transitions()
        result['status']='pass'
    except Exception as error:
        result['error']=str(error)
        for filename in ('lua-load.json','real-speed.json','native-fault.json'):
            if (folder/filename).exists():result[filename]=json.loads((folder/filename).read_text())
    finally:
        session.close();clean(folder)
    return result
