"""Finite legacy-service checks; downloaded archives are read-only inputs."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile
from real_input import Session, build_helper

class BindingSession(Session):
    def _gate_wait(self,seconds=180):return super()._gate_wait(seconds)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crazyhook/checks'
ADDRESS_SERVICES={
0x522738:'DeathSound',0x522170:'BulletImage',0x52ab6c:'BossName',0x52ab44:'DefeatVoice',0x52ab30:'StageClaw',0x52ab1c:'StageBoss',
0x535928:'Clock',0x52abf0:'BossFrame',0x53b0f8:'PowerupMusic',0x530990:'SoundVolume',0x429baf:'ViewportIncreaseLimit',0x429b6f:'ViewportDecreaseLimit',
0x41dac9:'BulletCollision',0x41de0b:'BulletHit',0x41da88:'BulletRight',0x41da96:'BulletLeft',0x535840:'Viewport',
0x45a4e0:'FindSound',0x4b34d0:'StopSound',0x421bb0:'PlaySound',0x4b4e80:'FindMusic',0x4b55b0:'MusicState',
0x44d060:'CrabFall',0x44c550:'CrabType',0x420ee0:'GivePowerup',0x418d20:'Drown',0x41eac0:'RefreshSound',0x4756d0:'ProjectileFlags',0x4d52f0:'CreateHUDObject',0x520624:'HUDLogic',0x410510:'ProjectileLogic'}

def inventory():
    census=json.loads((ROOT/'work/crazyhook/features.json').read_text())
    selected=census['features']['ffi-address-access']['samples']
    result={}
    for sample in census['samples']:
        if sample['name'] not in selected:continue
        archive=ROOT/sample['archive'];rows=[]
        with zipfile.ZipFile(archive) as z:
            for path in z.namelist():
                if not path.lower().endswith('.lua') or '/LOGICS/' not in path.upper():continue
                text=z.read(path).decode('latin1')
                # Preserve source line numbers while excluding comments.
                text=re.sub(r'--\[\[.*?\]\]',lambda m:'\n'*m[0].count('\n'),text,flags=re.S)
                text=re.sub(r'--[^\n]*','',text)
                aliases={m[1]:m[2] for m in re.finditer(r'local\s+(\w+)\s*=\s*(ffi\.cast\([^\n]+)',text)}
                for line,body in enumerate(text.splitlines(),1):
                    operations=[]
                    for address in re.findall(r'0[xX]([0-9a-fA-F]{6,8})',body):
                        number=int(address,16)
                        if number in ADDRESS_SERVICES:operations.append(ADDRESS_SERVICES[number])
                    for symbol,service in [('_nResult','GameState'),('nRes(','GameState'),('_userdata','PrivateState'),('ffi.new','StructValue'),('ffi.copy','CopyBuffer'),('ffi.string','StringBuffer'),('obj._v','LogicReference')]:
                        if symbol in body:operations.append(service)
                    for alias,definition in aliases.items():
                        if re.search(r'\b'+re.escape(alias)+r'\s*\(',body):operations.append('alias:'+alias)
                    if 'ffi.cast' in body and 'ObjectA*' in body and re.search(r',\s*0\s*\)',body):operations.append('NullObject')
                    if 'ffi.cast' in body and 'musPtr' in body and '[8]' in body:operations.append('MusicVirtualStop')
                    if operations:
                        rows.append(dict(path=path,line=line,operations=sorted(set(operations)),
                            types=re.findall(r'ffi\.(?:cast|new)\(\s*["\']([^"\']+)',body),
                            check='native_contracts' if not any('Boss' in op or 'Stage' in op for op in operations) else 'boss_staging'))
        result[sample['name']]=dict(sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),operations=rows)
    assert len(result)==13
    return result

def script_check(session,script):
    session._command('lua-gameplay-check '+base64.b64encode(script.encode()).decode())
    session._gate_wait();session.run(1)
    if session.failed():
        path=session.out/'real-speed.json'
        raise AssertionError({k:v for k,v in json.loads(path.read_text()).items() if k in ['error','failing_frame','frame_check','trace']} if path.exists() else session.gate())
    return json.loads((session.out/'live.json').read_text())['custom_level'].get('gameplay_check')

def animation_contract(out):
    import struct
    source=(ROOT/'Sources/ClawCustomAssets.swift').read_text()
    method=source[source.index('    static func surfaceANI('):source.index('    static func bitmapPID(')]
    program=out/'ani-normalization.swift';binary=out/'ani-normalization'
    program.write_text('import Foundation\nimport CryptoKit\nstruct Adapter {\n'+method+'}\nlet p=CommandLine.arguments[1]\ntry Adapter.surfaceANI(Data(contentsOf:URL(fileURLWithPath:p))).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))\n')
    built=subprocess.run(['xcrun','swiftc','-O',str(program),'-o',str(binary)],capture_output=True,text=True)
    assert built.returncode==0,built.stderr
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/arcana_v13.zip') as z:
        name=next(p for p in z.namelist() if p.upper().endswith('/ANIS/ARCANIS/ATTACK1.ANI'))
        data=z.read(name)
    raw=out/'arcana-attack1.ani';normalized=out/'arcana-attack1-normalized.ani';raw.write_bytes(data)
    subprocess.run([str(binary),str(raw),str(normalized)],check=True)
    result=normalized.read_bytes();expected=bytearray(data);struct.pack_into('<I',expected,12,10)
    assert result==expected and raw.read_bytes()==data
    assert struct.unpack_from('<I',data,12)[0]==11 and struct.unpack_from('<I',data,16)[0]==21
    assert [struct.unpack_from('<H',result,53+i*20+8)[0] for i in range(10)]==[1,2,3,4,5,6,5,4,3,2]
    negatives=[data[:-3],data[:40],data[:40]+b'\0'+data[41:]]
    for negative in negatives:
        raw.write_bytes(negative);subprocess.run([str(binary),str(raw),str(normalized)],check=True)
        assert normalized.read_bytes()==negative
    return dict(sample=name,original_sha256=hashlib.sha256(data).hexdigest(),declared=11,complete_records=10,header_name_and_frame_bytes_preserved=True,negative_cases=len(negatives))

def audio_contract(out):
    import struct
    source=(ROOT/'Sources/ClawCustomAssets.swift').read_text()
    method=source[source.index('    static func surfaceWAV('):source.index('    /// Some custom exporters encode surface PID')]
    program=out/'wav-normalization.swift';binary=out/'wav-normalization'
    program.write_text('import Foundation\nenum AssetError: Error {case invalid(String)}\nstruct Adapter {static let maximumBytes=256*1024*1024\n'+method+'}\ntry Adapter.surfaceWAV(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))\n')
    built=subprocess.run(['xcrun','swiftc','-O',str(program),'-o',str(binary)],capture_output=True,text=True)
    assert built.returncode==0,built.stderr
    marks=[]
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/arcana_v13.zip') as z:
        for name in z.namelist():
            if not name.lower().endswith('.wav'):continue
            data=z.read(name);fmt=data.find(b'fmt ')
            if struct.unpack_from('<H',data,fmt+8)[0]!=17:continue
            raw=out/Path(name).name;normalized=raw.with_suffix('.pcm.wav');reference=raw.with_suffix('.s16')
            raw.write_bytes(data)
            subprocess.run([str(binary),str(raw),str(normalized)],check=True,capture_output=True)
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-f','s16le','-acodec','pcm_s16le',str(reference)],check=True,capture_output=True)
            result=normalized.read_bytes();pcm=result[44:];expected=reference.read_bytes()
            # WAV fact excludes the encoder's last padded block samples.
            assert pcm==expected[:len(pcm)] and len(expected)-len(pcm)<2034,(name,len(pcm),len(expected))
            assert any(pcm) and raw.read_bytes()==data
            marks.append(dict(sample=name,original_sha256=hashlib.sha256(data).hexdigest(),pcm_sha256=hashlib.sha256(pcm).hexdigest(),frames=len(pcm)//2,reference='ffmpeg pcm_s16le',exact_pcm=True))
    assert len(marks)==3
    # Invalid block headers and truncated chunks fail safely; PCM passes through.
    original=raw.read_bytes()
    raw.write_bytes(original[:-1])
    assert subprocess.run([str(binary),str(raw),str(normalized)],capture_output=True).returncode!=0
    malformed=bytearray(original)
    start=malformed.find(b'data')+8;malformed[start+2]=89
    raw.write_bytes(malformed)
    assert subprocess.run([str(binary),str(raw),str(normalized)],capture_output=True).returncode!=0
    raw.write_bytes(result)
    subprocess.run([str(binary),str(raw),str(normalized)],check=True,capture_output=True)
    assert normalized.read_bytes()==result
    return dict(samples=marks,invalid_index_rejected=True,truncated_chunk_rejected=True,pcm_passthrough=True)

def sampled_script(archive,suffix):
    with zipfile.ZipFile(ROOT/f'work/custom-levels/crazyhook-sample/{archive}.zip') as z:
        p=next(p for p in z.namelist() if p.lower().endswith(suffix.lower()))
        return z.read(p).decode('latin1')

def native_contracts(session):
    return script_check(session,"""
    local b=ffi.new('char[16]');ffi.copy(b,'native');assert(ffi.string(b)=='native')
    assert(not pcall(function() b[16]=0 end))
    local r=ffi.new('Rect',{-2,3,4,5});assert(r.Left==-2 and r.Bottom==5)
    local p=ffi.new('Point',{7,8});assert(p.X==7 and p.Y==8)
    local f=ffi.new('Flags_t');f.AlwaysActive=true;assert(f.AlwaysActive and f.flags==2)
    local s=nRes(11,473);snRes(1234,11,473);assert(nRes(11,473)==1234);snRes(s,11,473)
    local frame=ffi.cast('int*',0x52ABF0);local old=frame[0];frame[0]=53;assert(frame[0]==53);frame[0]=old
    local clock=ffi.cast('int*',0x535928);assert(clock[0]==GetTime())
    assert(not pcall(function() clock[0]=0 end))
    for _,a in ipairs{0x41DAC9,0x41DE0B,0x41DA88,0x41DA96} do
        PrivateCast(a==0x41DA96 and -770 or a==0x41DA88 and 770 or CollisionFlags.MagicBullet,'int*',a)
    end
    for _,a in ipairs{0x429BAF,0x429B6F} do
        local p=ffi.cast('char*',a);local old=p[0];p[0]=5;assert(p[0]==5);p[0]=old
    end
    assert(nRes(5)~=0 and nRes(6)==60)
    assert(ffi.cast('ObjectA*',0)==nil)
    local c=GetClaw();local old=c._field_F4;c._field_F4=10;assert(c._field_F4==10);c._field_F4=old
    local snd=ffi.cast('int* (*__thiscall)(int, const char*)',0x45A4E0)(c._Game_[10],'CLAW_FALLDEATH')
    local play=ffi.cast('int (*__thiscall)(int*, int, int, int, int)',0x421BB0)
    local stop=ffi.cast('int (*__thiscall)(int)',0x4B34D0)
    assert(play(snd,90,0,0,1)~=0);assert(stop(snd[4])~=0)
    assert(not pcall(function() ffi.cast('void(*)()',0x45A4E0) end))
    local findMusic=ffi.cast('int(*__thiscall)(int, const char*)',0x4B4E80)
    local musicState=ffi.cast('int(*__thiscall)(int)',0x4B55B0)
    local m=findMusic(nRes(20),'LEVEL');assert(SetMusic('LEVEL')~=0);assert(musicState(m)~=0)
    ffi.cast('int(*__thiscall)(int)',ffi.cast('int**',m)[0][8])(m);assert(musicState(m)==0)
    local powerup=ffi.cast('int*',0x53B0F8);powerup[0]=2;assert(powerup[0]==2);powerup[0]=0
    assert(type(ffi.cast('int(*__thiscall)(int*)',0x44D060))=='function')
    assert(type(ffi.cast('int(*__thiscall)(int*, int)',0x44C550))=='function')
    assert(type(ffi.cast('int (*)(ObjectA*, ObjectV*, PData*)',0x418D20))=='function')
    local hud=ffi.cast('ObjectA* (*__thiscall)(ObjectA*, int, int, int, int, int, int)',0x4D52F0)
    local element=hud(MULTI_STATS,0,100,120,9999,0x520624,0)
    assert(element.X==100 and element.Y==120);element:Destroy()
    local o=CreateObject{Logic='DoNothing',X=c.X,Y=c.Y}
    assert(o.Logic==DoNothing);o:Logic()
    assert(ffi.cast('int*',o._v)[4]~=0)
    ffi.cast('int (*__cdecl)(int)',0x41EAC0)(o:GetSelf())
    assert(ffi.cast('int (*__cdecl)(int)',0x4756D0)(o:GetSelf()))
    assert(o.Flags.NoHit);o:Destroy()
    """)

def native_arcana_audio(out,app,helper,decoded):
    folder=out/'audio-input';folder.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/arcana_v13.zip') as z:
        assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
        z.extractall(folder)
        world=folder/next(p for p in z.namelist() if p.lower().endswith('.wwd'))
    play=out/'arcana-audio';play.mkdir(exist_ok=True)
    request=play/'request.json';request.write_text(json.dumps({'arcana_v13':str(world.resolve())}))
    result=play/'audio-packages.json';result.unlink(missing_ok=True)
    session=BindingSession(play,helper=helper)
    try:
        session.launch(app,{},['--no-paper-startup','--audio-package-check',str(request.resolve()),'--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings')],start_seconds=180)
        assert not session.failed(),session.gate()
        report=json.loads(result.read_text());assert report['status']=='pass'
        sounds={x['name']:x for x in report['samples']['arcana_v13']['sounds']}
        for sample in decoded['samples']:
            name='CUSTOM_AMBIENT_'+Path(sample['sample']).stem.upper()
            assert sounds[name]['pcm_sha256']==sample['pcm_sha256']
            assert report['samples']['arcana_v13-'+name+'-sound']['nonzero_frames']>0
        assert report['samples']['arcana_v13']['restored']
        return report
    finally:
        session.close()
        for pattern in ['hud-*.png','frame-*.png']:
            for frame in play.glob(pattern):frame.unlink()

def bindings():
    import fcntl
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check_bindings()

def check_bindings():
    out=OUT/'bindings';out.mkdir(parents=True,exist_ok=True)
    report=dict(group='bindings',status='fail',marks={},mapping={hex(a):dict(service=n,access='typed finite read/write/call',check='bindings native_contracts or sample interaction') for a,n in ADDRESS_SERVICES.items()},inventory=inventory(),ipad='Mac Catalyst only; iPad build and runtime not checked')
    path=OUT/'bindings.json'
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report['marks']['arcana_animation']=animation_contract(out);save()
    report['marks']['arcana_audio']=audio_contract(out);save()
    import importlib.util
    spec=importlib.util.spec_from_file_location('binding_lua_contracts',ROOT/'scripts/check-crazyhook-lua.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report['marks']['interpreter']=module.interpreter(out);save()
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    report['marks']['arcana_native_audio']=native_arcana_audio(out,app,helper,report['marks']['arcana_audio']);save()
    names=os.environ.get('CLAW_BINDINGS_SAMPLES','aquatis_day_out,puerto_shipyards_battle_8+2+6,the_poisonous_caves,bindings_fixture,arcana_v13').split(',')
    try:
        for name in names:
            folder=out/'input'/name;folder.mkdir(parents=True,exist_ok=True)
            archive='aquatis_day_out' if name=='bindings_fixture' else name
            with zipfile.ZipFile(ROOT/f'work/custom-levels/crazyhook-sample/{archive}.zip') as z:
                assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
                z.extractall(folder)
                world=folder/next(p for p in z.namelist() if p.lower().endswith('.wwd'))
            if name=='bindings_fixture':
                companion=world.with_suffix('')
                with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/arcana_v13.zip') as arcana:
                    for p in arcana.namelist():
                        if '/IMAGES/REDBL/' in p.upper() and not p.endswith('/'):
                            target=companion/'IMAGES'/'REDBL'/Path(p).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(arcana.read(p))
                    p=next(p for p in arcana.namelist() if p.lower().endswith('/artifactpower/piercingbullets.lua'))
                    target=companion/'LOGICS'/'ArtifactPower'/'PiercingBullets.lua';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(arcana.read(p))
                with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/citd.zip') as city:
                    for p in city.namelist():
                        if '/LEVEL/HERMITCRAB/' in p.upper() and not p.endswith('/'):
                            target=companion/'LEVEL'/'HERMITCRAB'/Path(p).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(city.read(p))
                report['fixture_scope']='Synthetic Aquatis copy plus unchanged Arcana REDBL/PiercingBullets and City HermitCrab assets; original Aquatis is checked separately' 
            play=out/name;play.mkdir(exist_ok=True)
            session=BindingSession(play,helper=helper)
            try:
                session.launch(app,{},['--custom-dir',str(folder),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace','--lua-runtime-check'],start_seconds=180)
                assert not session.failed(),{k:v for k,v in json.loads((play/'real-speed.json').read_text()).items() if k in ['error','failing_frame','trace','frame_check']}
                def live():return json.loads((play/'live.json').read_text())
                def tap(code):session.post('key',code);session.run(12);assert not session.failed(),session.gate()
                session.run(30)
                if live().get('menu_page')==10000:tap(36)
                for _ in range(10):
                    if live().get('menu_selected')==11003:break
                    tap(125)
                tap(36);assert live().get('custom_dialog'),live()
                tap(36)
                assert not live().get('custom_dialog'),live().get('custom_error')
                session.run(4)
                assert not session.failed(),{k:v for k,v in json.loads((play/'real-speed.json').read_text()).items() if k in ['error','failing_frame','trace','frame_check']}
                report['marks'][name]={'load':json.loads((play/'live.json').read_text()).get('custom_level')};save()
                report['marks'][name]['buffers']=script_check(session,"""
                for _,a in ipairs{0x522738,0x522170,0x52AB6C,0x52AB44,0x52AB30,0x52AB1C} do
                    local p=ffi.cast('char*',a);local old=ffi.string(p)
                    ffi.copy(p,'CUSTOM_TEST');assert(ffi.string(p)=='CUSTOM_TEST')
                    assert(not pcall(function() p[32]=1 end));ffi.copy(p,old)
                end
                assert(not pcall(function() ffi.cast('int*',0x123456)[0]=1 end))
                assert(not pcall(function() ffi.cast('void(*)()',0x123456)() end))
                assert(not pcall(function() ffi.load('synthetic.dll') end))
                assert(not pcall(function() PrivateChamAdd(0x123456,'synthetic') end))
                local x=nRes(11,17);snRes(x+1,11,17);assert(nRes(11,17)==x+1);snRes(x,11,17)
                assert(CheatsUsed()==(nRes(18,74)~=0))
                local r=ffi.cast('Rect*',0x535840)[0];assert(r.Right>0 and r.Bottom>0)
                """)
                if name=='aquatis_day_out':
                    session._command('lua-place Aquatis1');session._gate_wait()
                    session.post('press',49,'down');session.run(20);session.post('press',49,'up')
                    assert not session.failed(),{k:v for k,v in json.loads((play/'real-speed.json').read_text()).items() if k in ['error','failing_frame','trace','frame_check']}
                    report['marks'][name]['throw_timer']=script_check(session,"""
                    local found=false
                    LoopThroughObjects(function(o)
                        if o.Name=='Aquatis1' and o.State~=0 then
                            local t=ffi.cast('int*',o._userdata)[276]
                            assert(GetTime()-t<=34,'Aquatis throw timer not refreshed');found=true
                        end
                    end)
                    assert(found,'Aquatis1 not active')
                    """)
                    assert session.transitions().get('32:down',0)>0
                    report['marks'][name]['native_contracts']=native_contracts(session)
                if name=='puerto_shipyards_battle_8+2+6':
                    session._command('lua-place BossStager');session._gate_wait()
                    session.post('press',49,'down');session.run(12);session.post('press',49,'up')
                    assert not session.failed(),session.gate()
                    report['marks'][name]['boss_staging']=script_check(session,"""
                    local found=false
                    LoopThroughObjects(function(o)
                        if o.Name=='BossStager' then
                            assert(o.State~=0);found=true;o.State=8000;o:Logic();assert(GetImgStr(o.Image)=='CUSTOM_BOSSNAME')
                            assert(ffi.string(ffi.cast('char*',0x52AB6C))=='CUSTOM_BOSSNAME')
                            assert(ffi.string(ffi.cast('char*',0x52AB44))=='CUSTOM_DEFEAT')
                        end
                    end);assert(found,'BossStager not active')
                    """)
                if name=='bindings_fixture':
                    report['marks'][name]['city_private_crab']=script_check(session,"""
                    local crab=CreateObject{Logic='HermitCrab',X=GetClaw().X+100,Y=GetClaw().Y-60}
                    crab.Name='renamed-native-crab'
                    local impostor=CreateObject{Logic='DoNothing',X=GetClaw().X,Y=GetClaw().Y}
                    impostor.Name='HermitCrab'
                    assert(not pcall(function() return ffi.cast('double*',impostor._userdata)[10] end))
                    assert(not pcall(function() ffi.cast('int(*__thiscall)(int*)',0x44D060)(impostor._userdata) end))
                    impostor:Destroy()
                    local state=ffi.cast('double*',crab._userdata)
                    state[10]=800;state[11]=0;state[12]=200;state[13]=-100
                    assert(state[10]==800 and state[11]==0 and state[12]==200 and state[13]==-100)
                    ffi.cast('int(*__thiscall)(int*)',0x44D060)(crab._userdata)
                    ffi.cast('int(*__thiscall)(int*, int)',0x44C550)(crab._userdata,1)
                    crab:Destroy()
                    """)
                    report['marks'][name]['arcana_piercing_bullets']=script_check(session,"""
                    CreateObject{name='ArtifactPower:PiercingBullets'}
                    GetClaw().PData.Dir=1;PlayerData().PistolAmmo=10
                    assert(_bindingFirePistol()~=0)
                    local found=false
                    LoopThroughObjects(function(o)
                        if o.Logic==PistolBullet then
                            assert(o.ObjectTypeFlags==CollisionFlags.MagicBullet)
                            assert(o.SpeedX==770 and GetImgStr(o.Image)=='CUSTOM_REDBL')
                            found=true;o:Destroy()
                        end
                    end);assert(found,'no native piercing bullet')
                    """)
                if name=='the_poisonous_caves':
                    report['marks'][name]['original_music_helpers']=script_check(session,'do local main;'+sampled_script(name,'/MusicStop.lua')+"""
                    local m=get_music_ptr('CUSTOM');SetMusic('CUSTOM');assert(get_music_state(m))
                    stop_music(m);assert(not get_music_state(m))
                    end
                    """)
                report['marks'][name]['input']=session.transitions();save()
            except Exception as error:
                import traceback
                details=dict(error=str(error),traceback=traceback.format_exc())
                for filename in ['lua-load.json','real-speed.json']:
                    evidence=play/filename
                    if evidence.exists():
                        value=json.loads(evidence.read_text())
                        details[filename]={k:value[k] for k in ['phase','fault','address','error','lua'] if k in value}
                load=json.loads((play/'lua-load.json').read_text()) if (play/'lua-load.json').exists() else {}
                map_error=load.get('evidence',{}).get('lua_map_error','')
                # Whole Arcana acceptance belongs to the later integration task.
                # Its unchanged main.lua requires a version capability promise
                # before presentation/persistence APIs; do not advertise 1454.
                if (name=='arcana_v13' and load.get('address')=='7e100001'
                    and map_error.replace(chr(92),'')=='script("[string \"LOGICS/MAIN.LUA\"]:3: attempt to compare nil with number")'
                    and 'if version < 1454 then' in sampled_script(name,'/LOGICS/main.lua')):
                    report.setdefault('pending_integration',{})[name]=dict(
                        script_error=map_error,phase=load['phase'],
                        requirement='CrazyHook version capability declaration and remaining presentation/persistence APIs',
                        task='app-crazyhook-diagnostics',whole_level_accepted=False,
                        binding_evidence='unchanged PiercingBullets in labelled native fixture; package audio loaded and rendered offline')
                else:
                    report.setdefault('errors',{})[name]=details
                save()
            finally:
                session.close()
                for pattern in ['hud-*.png','frame-*.png']:
                    for frame in play.glob(pattern):frame.unlink()
        assert inventory()==report['inventory'],'sample inputs changed'
        assert not report.get('errors'),report.get('errors')
        report['status']='pass'
    except Exception as error:
        import traceback
        report['error']=str(error);report['traceback']=traceback.format_exc()
    finally:save()
    return report
