"""Presentation services exercised by unchanged downloaded level scripts."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile
from PIL import Image
from real_input import Session, build_helper

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crazyhook/checks'

class PresentationSession(Session):
    def _gate_wait(self,seconds=180):return super()._gate_wait(seconds)
    def live(self):return json.loads((self.out/'live.json').read_text())
    def healthy(self):
        if self.failed():
            raise AssertionError(json.loads((self.out/'real-speed.json').read_text()).get('error',self.gate()))
    def tap(self,key):self.healthy();self.post('key',key);self.run(8);self.healthy()
    def script(self,text):
        self._command('lua-gameplay-check '+base64.b64encode(text.encode()).decode())
        self._gate_wait();self.run(1);self.healthy()
        return self.live()['custom_level']['gameplay_check']
    def load(self):
        self.run(30);self.healthy()
        if self.live().get('menu_page')==10000:self.tap(36)
        for _ in range(10):
            if self.live().get('menu_selected')==11003:break
            self.tap(125)
        self.tap(36);assert self.live().get('custom_dialog'),self.live()
        self.tap(36);assert not self.live().get('custom_dialog'),self.live().get('custom_error')
        self.run(30);self.healthy()
        assert self.live().get('state_vtable')=='0x50c264'


def presentation():
    OUT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check()


def check():
    out=OUT/'presentation';out.mkdir(parents=True,exist_ok=True)
    report=dict(group='presentation',status='fail',marks={},ipad='Shared UIKit keyboard and touch implementation built for Mac Catalyst; physical iPad runtime not tested')
    def save():(OUT/'presentation.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    names=os.environ.get('CLAW_PRESENTATION_SAMPLES','clawopiano,bricks,get_the_coin').split(',')
    try:
        for name in names:
            folder=out/'input'/name;folder.mkdir(parents=True,exist_ok=True)
            archive=ROOT/f'work/custom-levels/crazyhook-sample/{name}.zip'
            with zipfile.ZipFile(archive) as z:
                assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
                z.extractall(folder)
                world=folder/next(p for p in z.namelist() if p.lower().endswith('.wwd'))
            if name=='clawopiano':
                # Synthetic cross-package fixture: the original piano scripts
                # are unchanged; Arcana's ResChanger is invoked explicitly later.
                with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/arcana_v13.zip') as z:
                    path=next(p for p in z.namelist() if p.endswith('/ResChanger.lua'))
                    target=world.with_suffix('')/'LOGICS/ArcanaResolution.lua'
                    target.write_bytes(z.read(path))
                report['arcana_scope']='Unchanged Arcana ResChanger in explicitly synthetic piano package; no whole Arcana load/play claim'
            play=out/name;play.mkdir(exist_ok=True)
            for path in list(play.glob('*.json'))+list(play.glob('*.png')):path.unlink()
            session=PresentationSession(play,helper=helper)
            marks=report['marks'][name]=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest());save()
            try:
                session.launch(app,{},['--custom-dir',str(folder),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace','--lua-runtime-check','--presentation-check'],start_seconds=180)
                session.load();marks['loaded']=True;save()
                if name=='clawopiano':
                    marks['resolution']=session.script('local w,h=GetResolution();assert(w==800 and h==600,tostring(w).."x"..tostring(h))')
                    marks['edge_monitor']=session.script("_edges=0;_held=0;local old=OnGameplay;function OnGameplay() if old then old() end;if GetKeyInput('U') then _edges=_edges+1 end;if KeyPressed('U') then _held=_held+1 end end")
                    before=session.mark('notes-before')
                    session.post('press',32,'down');session.run(3)
                    held=session.mark('notes-held')
                    marks['held']=session.script("assert(KeyPressed('U') and KeyPressed(0x55));assert(not KeyPressed('Q'));_note=LoopThroughObjects(function(o) if o.Name=='RightC4' then return o end end);assert(_note and _note.State==2);assert(_note.KeyR1C4.I==GetObject(3).SpeedX);assert(_edges==1 and _held>1)")
                    session.post('press',32,'up');session.run(3)
                    released=session.mark('notes-released')
                    marks['release']=session.script("assert(not KeyPressed('U'));assert(_note.State==1 and _note.KeyR1C4.I==1)")
                    notes=session.live()['custom_level'].get('presentation_audio',[])
                    assert any(n['sound']=='CUSTOM_RIGHT1_C4' and n['nonzero_frames']>0 for n in notes),notes
                    marks['offline_notes']=notes
                    assert hashlib.sha256((play/'notes-before.png').read_bytes()).digest()!=hashlib.sha256((play/'notes-held.png').read_bytes()).digest()
                    marks['visuals']={'before':before,'held':held,'released':released}
                    marks['hud']=session.script("_hud=CreateHUDObject{logic='DoNothing',image='CUSTOM_PIANOKEYPRESSED',x=80,y=80};assert(_hud);_hud:Destroy();TextOut('Presentation lifetime check')")
                    session.run(3)
                    marks['hud_destroy']=session.script("local ok,e=pcall(function() return _hud.X end);assert(not ok and e:find('StaleHandle'))")
                    marks['id_cache_retire']=session.script("_retired=CreateObject{id=700001,logic='DoNothing',flags=2};assert(GetObject(700001)==_retired);_retired:Destroy()")
                    session.run(3)
                    marks['id_cache_reuse']=session.script("assert(GetObject(700001)==nil);local fresh=CreateObject{id=700001,logic='DoNothing',flags=2};assert(GetObject(700001)==fresh and fresh~=_retired);local ok,e=pcall(function() return _retired.X end);assert(not ok and e:find('StaleHandle'));fresh:Destroy()")
                    marks['boss_meter_setup']=session.script("_boss=CreateObject{logic='DoNothing',image='CUSTOM_PIANOKEYPRESSED',Health=100};SetBoss(_boss);assert(GetBoss()==_boss);_meter=CreateObject{logic='BossHealthMeter',flags=0x200002};assert(_meter);_meter.Z=20000")
                    session.run(3);marks['boss_full']=session.mark('boss-full')
                    marks['boss_meter_damage']=session.script("_boss.Health=40;assert(GetBoss().Health==40)")
                    session.run(3);marks['boss_damaged']=session.mark('boss-damaged')
                    def meter_red(name):
                        with Image.open(play/(name+'.png')) as picture:
                            w,h=picture.size
                            return sum(pixel==(255,0,0) for pixel in picture.convert('RGB').crop((w//2-150,h-65,w//2+150,h-10)).getdata())
                    full,damaged=meter_red('boss-full'),meter_red('boss-damaged')
                    assert full>1000 and 0.35<damaged/full<0.45,(full,damaged)
                    marks['boss_meter_rendering']=dict(full_red_pixels=full,damaged_red_pixels=damaged,health_percent=40)
                    marks['boss_meter_cleanup']=session.script("SetBoss(nil);_boss:Destroy();assert(GetBoss()==nil)")
                    marks['arcana_viewport_request']=session.script("_res=CreateObject{name='ArcanaResolution',Smarts=0}")
                    session.run(20)
                    marks['arcana_viewport']=session.script("local w,h=GetResolution();assert(w==864 and h==486);local r=ffi.cast('Rect*',0x535840)[0];assert(r.Right==863 and r.Bottom<=485)")
                    marks['arcana_4_3_request']=session.script("_res.State=20")
                    session.run(20)
                    marks['arcana_4_3']=session.script("local w,h=GetResolution();assert(w==640 and h==480);_res:Destroy()")
                    marks['restore_test_request']=session.script("ChangeResolution(800,600)")
                    session.run(3)
                elif name=='bricks':
                    marks['background_logic']=session.script("assert(GetObject(1)~=GetClaw(),'map/player ID collision');_background=GetObject(1).BgLayer;assert(_background,'background absent');assert(_background.State==2000,'background state '..tostring(_background.State));assert(_background.XMin==-2147483648 and _background.XMax==2147483647 and _background.YMin==-2147483648 and _background.YMax==2147483647,'background bounds '.._background.XMin..','.._background.XMax..','.._background.YMin..','.._background.YMax)")
                    session.run(200);session.tap(36);session.run(45)
                    marks['started']=session.script("assert(GetObject(5).State~=0)")
                    board_before=session.script('assert(GetObject(5).State~=0)')['objects']
                    before=session.mark('board-before')
                    session.post('press',123,'down');session.run(8)
                    marks['action_held']=session.script("assert(KeyPressed('Left'));assert(GetInput('Left') and GetInput(InputFlags.Left))")
                    after=session.mark('board-left')
                    session.post('press',123,'up');session.run(8)
                    marks['board']=session.script("assert(not KeyPressed('LEFT_ARROW'))")
                    old={o['handle']:o for o in board_before}
                    moved=[o for o in marks['board']['objects'] if o['handle'] in old and o['name']=='DoNothing' and 1900<=old[o['handle']]['x']<=2100 and old[o['handle']]['y']>=6300 and o['x']<old[o['handle']]['x']]
                    assert moved,'Bricks left key did not move any board objects'
                    marks['moved_board_objects']=moved
                    assert hashlib.sha256((play/'board-before.png').read_bytes()).digest()!=hashlib.sha256((play/'board-left.png').read_bytes()).digest()
                    marks['visuals']=dict(before=before,after=after)
                else:
                    session._command('lua-place BellBoom');session._gate_wait();session.run(12);session.healthy()
                    marks['camera_setup']=session.script("_bell=LoopThroughObjects(function(o) if o.Name=='BellBoom' then return o end end);if not _bell then _bell=GetObject(901) end;assert(_bell,'BellBoom absent')")
                    marks['camera_contract']=session.script("local p=GetCameraPoint();SetCameraPoint(p.x+7,p.y+9);local q=GetCameraPoint();assert(q.x==p.x+7 and q.y==p.y+9);SetCameraPoint(p.x,p.y);_cx=p.x;_cy=p.y;SetCameraToPointSpeed(120,200);CameraToPoint(p.x+100,p.y+100)")
                    session.run(30)
                    marks['camera_moved']=session.script("local p=GetCameraPoint();assert(p.x>_cx and p.y>_cy);assert(p.y-_cy>p.x-_cx,'camera speeds not applied');CameraToClaw()")
                    session.run(30)
                    marks['camera_return']=session.script("local p=GetCameraPoint();assert(p.x~=_cx+100 or p.y~=_cy+100)")
                    marks['scripted_bell_hit_fixture']=session.script("_dispatch(_bell._handle,'BellBoom','hit',0);assert(_bell.State==2 and GetClaw().State==-1);_bellStartY=_bell.Y;_bellCameraY=GetCameraPoint().y")
                    session.run(20)
                    marks['scripted_bell_camera']=session.script("assert(_bell.Y>_bellStartY);local p=GetCameraPoint();assert(p.X==p.x and p.Y==p.y);assert(p.y~=_bellCameraY,'scripted camera did not move')")
                    session.run(900)
                    marks['scripted_return_to_claw']=session.script("local ok,e=pcall(function() return _bell.X end);assert(not ok and e:find('StaleHandle'));assert(GetClaw().State~=-1);local p=GetCameraPoint();assert(math.abs(p.x-GetClaw().X)<500 and math.abs(p.y-GetClaw().Y)<500,'camera did not return to Claw')")
                if name=='clawopiano':
                    for key in [46,35,1,8,32,37,37,16]:session.tap(key)
                    assert session.wait(lambda:session.live().get('state_vtable')=='0x50c0c4',10),session.live()
                    for _ in range(10):
                        if session.wait(lambda:session.live().get('state_vtable')!='0x50c0c4',12):break
                        session.tap(36)
                    assert session.wait(lambda:session.live().get('menu_page') in (10000,10001),20),session.live()
                    session.run(3)
                    assert session.live()['logical_resolution']==[640,480],session.live()['logical_resolution']
                    assert not session.live()['level_actions_available']
                    marks['menu_restoration']=dict(resolution=session.live()['logical_resolution'],level_actions=False,completion='MPSCULLY')
                marks['input']=session.transitions();save()
            except Exception as error:
                marks['error']=str(error);report.setdefault('errors',[]).append(dict(sample=name,error=str(error)));save()
            finally:
                session.close()
                for pattern in ('hud-*.png','frame-*.png'):
                    for path in play.glob(pattern):
                        if path.name!='frame-fail.png':path.unlink()
        report['status']='fail' if report.get('errors') else 'pass'
    except Exception as error:
        report['error']=str(error)
    finally:save()
    return report
