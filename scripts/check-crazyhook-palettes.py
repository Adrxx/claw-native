"""Palette byte/value checks plus honest full-level integration attempts."""
import json
import base64
import fcntl
import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile
from real_input import Session, build_helper

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crazyhook/checks'


def adjust_hsl(rgb,h,s=0,l=0):
    """Independent release algorithm, including its HSV saturation input."""
    result=[]
    for at in range(0,len(rgb),3):
        r,g,b=[v/255 for v in rgb[at:at+3]]
        hi,lo=max(r,g,b),min(r,g,b);delta=hi-lo
        hue=0 if not delta else (g-b)/delta if hi==r else (b-r)/delta+2 if hi==g else (r-g)/delta+4
        hue=(hue*60+h)%360/360
        sat=max(0,min(1,(delta/hi if hi else 0)+s/100));lum=max(0,min(1,(hi+lo)/2+l/100))
        if not sat:
            result.extend([int(lum*255)]*3);continue
        q=lum*(1+sat) if lum<.5 else lum+sat-lum*sat;p=2*lum-q
        for t in (hue+1/3,hue,hue-1/3):
            t=t+1 if t<0 else t-1 if t>1 else t
            v=p+(q-p)*6*t if t<1/6 else q if t<.5 else p+(q-p)*(2/3-t)*6 if t<2/3 else p
            result.append(int(max(0,min(255,v*255))))
    return result


class PaletteSession(Session):
    def _gate_wait(self, seconds=180):
        return super()._gate_wait(seconds)


def palettes():
    # Serialize with other app checks and builds in the shared checkout.
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check()


def check():
    out=OUT/'palettes';out.mkdir(parents=True,exist_ok=True)
    report=dict(group='palettes',status='fail',marks={},errors=[],ipad='Not built or run on iPad')
    path=OUT/'palettes.json'
    def save(): path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    while float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])>=16:
        time.sleep(10)
    blob=out/'check-blob'
    subprocess.run(['xcrun','swiftc','-O',str(ROOT/'Sources/ClawCustomBlob.swift'),str(ROOT/'scripts/check-crazyhook-blob.swift'),'-o',str(blob)],check=True,timeout=300)
    report['marks']['blob_fixtures']=json.loads(subprocess.check_output([str(blob)],text=True))
    save()
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report['binary_sha256']=hashlib.sha256((app/'Contents/MacOS/Claw').read_bytes()).hexdigest()
    report['reference']='work/crazyhook/palette-flag-reference.json'
    maps={}
    for name,archive in [('arcana','arcana_v13.zip'),('city','citd.zip'),('base','cannonballin.zip')]:
        folder=out/'input'/name;folder.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample'/archive) as z:
            assert all((folder/i.filename).resolve().is_relative_to(folder.resolve()) for i in z.infolist())
            z.extractall(folder)
        maps[name]=next(p for p in folder.rglob('*') if p.suffix.lower()=='.wwd')
    arcana=maps['arcana'].with_suffix('')/'PALETTES'
    rgb=(arcana/'MAIN.PAL').read_bytes()[:768]
    report['marks']['arcana_palette_bytes']=list(rgb)
    # Execute only these unchanged source calls in the synthetic fixture. This
    # is deliberately separate from acceptance of City's full boss/save flow.
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/citd.zip') as archive:
        boss=archive.read('City in the Depth/LOGICS/Areti2.lua').decode('latin1')
        expansion=boss.split('v["spread_type"] == "domain_expansion" then',1)[1].split('v["spread_type"] == "domain_collapse" then',1)[0]
        domain_calls='\n'.join(line.strip() for line in expansion.splitlines() if line.strip().startswith('Get') and 'Palette()' in line)
        assert domain_calls.count('AdjustRGB')==6 and domain_calls.count('AdjustHSL')==6
        collapse=boss.split('v["spread_type"] == "domain_collapse" then',1)[1].split('v["spread_type"] == "victory" then',1)[0]
        restore_call=next(line.strip() for line in collapse.splitlines() if 'GetFirstPalette():Set()' in line)
        stager=archive.read('City in the Depth/LOGICS/BossStager2.lua').decode('latin1')
        grayscale=next(line.strip() for line in stager.splitlines() if 'GetCurrentPalette():BlackAndWhite():Set()' in line)
    for ext in ('PAL','ACT','TXT'):
        fixture=out/'input'/('synthetic-'+ext);fixture.mkdir(exist_ok=True)
        world=fixture/'Palette Fixture.wwd';shutil.copy2(maps['base'],world)
        package=world.with_suffix('')
        shutil.copytree(maps['base'].with_suffix(''),package,dirs_exist_ok=True)
        (package/'LOGICS').mkdir(exist_ok=True)
        (package/'LOGICS/MAIN.LUA').write_text('-- Synthetic palette-only fixture; not a sampled script.\n')
        (package/'PALETTES').mkdir(exist_ok=True)
        payload=rgb if ext!='TXT' else ''.join('#%02x%02x%02x\n'%tuple(rgb[i:i+3]) for i in range(0,768,3)).encode()
        (package/'PALETTES'/('MAIN.'+ext)).write_bytes(payload)
        for table in ('LIGHT','AVERAGE'):
            shutil.copy2(arcana/(table+'.CLT'),package/'PALETTES'/(table+'.CLT'))
        (package/'PALETTES/NAMED.CLT').write_bytes(bytes([0,0,1,0])+bytes((i*3+j*7)%256 for i in range(256) for j in range(256)))
        maps['synthetic-'+ext]=world
    def play(name,world):
        folder=out/name;folder.mkdir(exist_ok=True)
        shutil.rmtree(folder/'saves',ignore_errors=True)
        shutil.rmtree(folder/'settings',ignore_errors=True)
        for pattern in ('*.json','*.png'):
            for stale in folder.glob(pattern): stale.unlink()
        session=PaletteSession(folder,helper=helper)
        def live(): return json.loads((folder/'live.json').read_text())
        def tap(k):
            session.post('key',k);session.run(15)
            assert not session.failed(),session.gate()
        def script(text):
            session._command('lua-gameplay-check '+base64.b64encode(text.encode()).decode())
            session._gate_wait(180);session.run(1)
            assert not session.failed(),session.gate()
            return live()['custom_level']['gameplay_check']
        def current_rgb():
            session._command('palette-values');session.run(1)
            assert not session.failed(),session.gate()
            return live()['custom_level']['palette_current_rgb']
        result=dict(status='fail')
        try:
            session.launch(app,{},['--custom-dir',str(world.parent),'--no-paper-startup','--lua-runtime-check','--long-trace','--save-dir',str(folder/'saves'),'--settings-dir',str(folder/'settings')],start_seconds=180)
            session.run(60)
            if live().get('menu_page')==10000: tap(36)
            menu_before=session.mark(name+'-menu-before')
            for _ in range(10):
                if live().get('menu_selected')==11003: break
                tap(125)
            assert live().get('menu_selected')==11003,live()
            tap(36);assert live().get('custom_dialog'),live()
            tap(36)
            assert not live().get('custom_dialog'),live().get('custom_error')
            session.run(30)
            if name=='arcana':
                # Original resolution and difficulty menus, with delivered keys.
                for key in (125,125,36,126,126,36,125,36): tap(key)
                session.run(45)
            evidence=live()['custom_level'];result['loaded']=evidence
            assert evidence.get('palettes',{}).get('installed'),evidence
            session._command('palette-values');session.run(1)
            assert not session.failed(),session.gate()
            package_raster=live()['custom_level']['palette_package_raster']
            for table,probe in package_raster.items():
                data=(world.with_suffix('')/'PALETTES'/(table+'.CLT')).read_bytes()[4:65540]
                assert probe['sha256']==hashlib.sha256(data).hexdigest(),table
                assert len(probe['pixels'])==9,(table,probe)
                for pixel in probe['pixels']:
                    s,d,c=(pixel[k] for k in ('source','destination','color'))
                    # Mode 2 indexes destination/source; modes 4 and 8 use
                    # destination/color and source/color respectively.
                    index=data[{2:d*256+s,4:d*256+c,8:s*256+c}[pixel['mode']]]
                    assert pixel['index']==index and pixel['rgb']==evidence['palettes']['first_rgb'][index*3:index*3+3],pixel
            result['package_raster']=package_raster
            if name=='arcana':
                assert evidence['palettes']['first_rgb']==list(rgb)
                assert sorted(package_raster)==['AVERAGE','LIGHT']
                result['clt_effect']=dict(tables=package_raster,reference='Unchanged package CLT bytes, native indexed raster, and MAIN.PAL RGB entries')
                result['star_ladder']=script("""
assert(GetObject(3206).Difficulty==1)
assert(GetMainPlane():GetTile(117,164)==203)
assert(_planeCheckCollision(117*64+32,164*64+32)==3)
local star=LoopThroughObjects(function(o) if o.Name=='BackgroundStarsPlacing' and o.State>0 then return o end end)
assert(star and star.back:GetTile(star.tx,star.ty)==star.State)
assert(star.back2:GetTile(star.tx2,star.ty2)==star.State)
""")
                native=live()['custom_level']
                assert {'CUSTOM_SPARKLE','CUSTOM_SPARKLEBLUE'}.issubset({v for k,v in native.items() if k.startswith('lua_tileset_')})
                assert sum(v.get('indexed_frame',False) for k,v in native.items() if k.startswith('lua_indexed_tile_'))>=2
                result['star_ladder_native']={k:v for k,v in native.items() if k.startswith(('lua_tileset_','lua_indexed_tile_','lua_tile_'))}
            if name.startswith('synthetic'):
                assert evidence['palettes']['first_rgb']==list(rgb)
                assert evidence['palettes']['tables']==['AVERAGE','LIGHT','NAMED']
                values=live()['custom_level']['palette_values']
                assert values['rgb'][:3]==[190,60,255] and values['rgb'][-3:]==[1,2,3],values
                # Independent reference calculation for release hue -5 operation.
                r,g,b=200/255,40/255,80/255
                hi,lo=max(r,g,b),min(r,g,b);h=(((g-b)/(hi-lo))*60-5)%360/360
                s=(hi-lo)/hi;l=(hi+lo)/2;q=l*(1+s) if l<.5 else l+s-l*s;p=2*l-q
                def channel(t):
                    t=t+1 if t<0 else t-1 if t>1 else t
                    v=p+(q-p)*6*t if t<1/6 else q if t<.5 else p+(q-p)*(2/3-t)*6 if t<2/3 else p
                    return int(max(0,min(255,v*255)))
                expected=[channel(h+1/3),channel(h),channel(h-1/3)]
                assert values['hsl'][:3]==expected,(values['hsl'][:3],expected)
                assert values['restored']==list(rgb) and values['display_matches']
                result['values']=values
                probe=live()['custom_level']
                assert probe['palette_raster']['outputs']=={'2':88,'3':13,'4':102,'5':13,'6':13,'7':139,'8':84,'22':9,'50':139},probe['palette_raster']
                assert probe['palette_flag_modes']=={'1':1,'2':2,'3':4,'5':22,'6':50,'7':7,'8':0x43480008},probe['palette_flag_modes']
                assert probe['palette_blob_bytes']==[0,0],probe['palette_blob_bytes']
                result['raster']=probe['palette_raster']
                result['flag_modes']=probe['palette_flag_modes']
                result['palette_events']=probe['palette_events']
                if name=='synthetic-PAL':
                    def evaluate(script):
                        encoded=base64.b64encode(script.encode()).decode()
                        session._command('lua-gameplay-check '+encoded);session.run(1)
                        assert not session.failed(),session.gate()
                        session._command('palette-values');session.run(1)
                        assert not session.failed(),session.gate()
                        return live()['custom_level']['palette_current_rgb']
                    # palette-values also runs the synthetic value tests and
                    # restores First. Its retained current_rgb is sampled first.
                    actual=evaluate(domain_calls)
                    expected=list(rgb)
                    for _ in range(6):
                        expected=[max(0,min(255,v+(-10,-10,5)[i%3])) for i,v in enumerate(expected)]
                        expected=adjust_hsl(expected,-5)
                    assert actual==expected,(actual,expected)
                    gray=evaluate(grayscale)
                    expected_gray=[]
                    for i in range(0,768,3):
                        n=int(.3*rgb[i]+.59*rgb[i+1]+.11*rgb[i+2]);expected_gray.extend([n]*3)
                    assert gray==expected_gray,(gray,expected_gray)
                    restored=evaluate(restore_call)
                    assert restored==list(rgb)
                    evaluate("local ok,err=pcall(function() while true do end end);assert(not ok and tostring(err):find('ScriptLimit'))")
                    result['city_palette_source_fixture']=dict(status='pass',scope='Original Areti2 domain calls and BossStager2 grayscale call in a synthetic map; full City save/boss not exercised',domain_rgb=actual,grayscale_rgb=gray,restored_rgb=restored,runaway_script_rejected=True)
            if name=='city':
                first=evidence['palettes']['first_rgb']
                result['save_boss']=dict(scope='Controlled save trigger and boss stage placement in the unchanged full City package')
                result['save_boss']['save_trigger']=script("_a=assert(GetObject(4088));assert(_a.achievements_input);_a.achievements_input[2]=1;GetClaw().Health=73;PData().PistolAmmo=37;PData().CollectedCoin=5;GetObject(820).State=6")
                session.run(8)
                result['save_boss']['saved']=script("assert(GetObject(4088).achievements_statuses[2]==1);local f=assert(io.open(GetMapFolder()..'/save.txt'));local row=assert(f:read());local fields={};for n in row:gmatch('[^;]+') do fields[#fields+1]=tonumber(n) end;assert(#fields==19 and fields[10]~=0 and fields[15]>0);f:close()")
                # Keep the player at the normal spawn; place the real script's
                # boss in its late stage, without changing any attack tables.
                result['save_boss']['boss_initialized']=script("_extraBefore=GetObject(4088).extra;GetObject(4088).extra=true;_boss=CreateObject{name='Areti2',image='CUSTOM_ARETI'};_boss.Flags.AlwaysActive=true")
                result['save_boss']['domain_stage']=script("assert(_boss.State==1 and _boss.movementInput[22].bullets[2].spread_type=='domain_expansion');_boss.stage=22;_boss.hotX=11950;_boss.hotY=2100;_boss.spellcycle=GetTime()-2600;_boss.spellcycleflag=0;for i=1,20 do _boss.bulletlastused[i]=GetTime()+100000 end;_boss.bulletlastused[2]=GetTime()-28000")
                expanded=current_rgb()
                expected=list(first)
                for _ in range(6):
                    expected=[max(0,min(255,v+(-10,-10,5)[i%3])) for i,v in enumerate(expected)]
                    expected=adjust_hsl(expected,-5)
                assert expanded==expected and expanded!=first,(expanded,expected)
                expanded_mark=session.mark('city-domain-expanded')
                result['save_boss']['collapse_stage']=script("assert(_boss.movementInput[26].bullets[2].spread_type=='domain_collapse');_boss.stage=26;_boss.spellcycle=GetTime();_boss.spellcycleflag=0;for i=1,20 do _boss.bulletlastused[i]=GetTime()+100000 end;_boss.bulletlastused[2]=GetTime()-1000")
                restored=current_rgb()
                assert restored==first
                restored_mark=session.mark('city-domain-restored')
                assert expanded_mark['palette_sha256']!=restored_mark['palette_sha256']
                result['scripted_palette_effect']=dict(scope='Original Areti2 main callback at placed stages 22 and 26; attack tables unchanged',expanded_rgb=expanded,restored_rgb=restored,expanded_palette_sha256=expanded_mark['palette_sha256'],restored_palette_sha256=restored_mark['palette_sha256'],events=live()['custom_level']['palette_events'])
                script("_boss:Destroy();GetObject(4088).extra=_extraBefore;CameraToClaw()")
            before=session.mark(name+'-before')
            session.post('press',124,'down');session.run(20);session.post('press',124,'up')
            after=session.mark(name+'-moved')
            assert before['player']['x']!=after['player']['x'],(before['player'],after['player'])
            result['movement']=[before['player'],after['player']]
            for k in [46,35,1,8,32,37,37,16]: tap(k)
            assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',10),live()
            for _ in range(10):
                if session.wait(lambda:live().get('state_vtable')!='0x50c0c4',12):break
                tap(36)
            assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
            assert live()['custom_level'].get('unloaded'),live()['custom_level']
            session.run(60)
            menu_after=session.mark(name+'-menu-after')
            assert menu_before['palette_sha256']==menu_after['palette_sha256'],(menu_before['palette_sha256'],menu_after['palette_sha256'])
            result['menu_palette_sha256']=menu_after['palette_sha256']
            result['image_restore']=live()['custom_level'].get('palette_image_restore')
            result['exit']='MPSCULLY, results, menu; package unloaded'
            result['input_transitions']=session.transitions()
            result['status']='pass'
        except Exception as e:
            result['error']=str(e)
            for filename in ('lua-load.json','real-speed.json','palette-values.json'):
                if (folder/filename).exists():result[filename]=json.loads((folder/filename).read_text())
            failure=result.get('lua-load.json',{}).get('evidence',{})
            result['load_error']=failure.get('lua_map_error') or failure.get('lua',{}).get('error') or result.get('real-speed.json',{}).get('error')
        finally:
            session.close()
            for pattern in ('hud-*.png','frame-*.png'):
                for f in folder.glob(pattern):f.unlink()
        report['marks'][name]=result;save()
        return result['status']=='pass'
    # All three formats pass the live backend and Lua value path.
    selected=os.environ.get('CLAW_PALETTE_ONLY','').split(',')
    for name in ['synthetic-PAL','synthetic-ACT','synthetic-TXT','arcana','city']:
        if selected==[''] or name in selected: play(name,maps[name])
    report['errors']=[k for k,v in report['marks'].items() if isinstance(v,dict) and v.get('status')=='fail']
    # Do not pass on early gameplay alone. These require the corresponding
    # bindings, planes and persistence implementations and actual interaction.
    required={'arcana':['star_ladder','clt_effect'],'city':['scripted_palette_effect','save_boss']}
    report['integration_required']=[name+': '+mark for name,marks in required.items() for mark in marks if not report['marks'].get(name,{}).get(mark)]
    report['status']='pass' if not report['errors'] and not report['integration_required'] and all(report['marks'].get(k,{}).get('status')=='pass' for k in ['synthetic-PAL','synthetic-ACT','synthetic-TXT','arcana','city','blob_fixtures']) else 'fail'
    save();return report
