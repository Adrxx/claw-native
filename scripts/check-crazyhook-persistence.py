"""Map-scoped text IO and unchanged sampled save/achievement scripts."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile
from real_input import Session, build_helper

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/crazyhook/checks'

class PersistenceSession(Session):
    def live(self):return json.loads((self.out/'live.json').read_text())
    def healthy(self):
        assert not self.failed(),json.loads((self.out/'real-speed.json').read_text()).get('error',self.gate())
    def tap(self,key):self.post('key',key);self.run(8);self.healthy()
    def script(self,text):
        self._command('lua-gameplay-check '+base64.b64encode(text.encode()).decode())
        self._gate_wait(180);self.run(1);self.healthy()
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
        assert self.live().get('state_vtable')=='0x50c264',self.live()


def persistence():
    OUT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check()


def check():
    out=OUT/'persistence';out.mkdir(parents=True,exist_ok=True)
    report=dict(group='persistence',status='fail',marks={},errors=[],ipad='Mac Catalyst only; iPad runtime not tested')
    def save():(OUT/'persistence.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    for name in os.environ.get('CLAW_PERSISTENCE_SAMPLES','synthetic,citd,rotsa,arcana_v13,claw_tower').split(','):
        folder=out/'input'/name;folder.mkdir(parents=True,exist_ok=True)
        archive=ROOT/f"work/custom-levels/crazyhook-sample/{'cannonballin' if name=='synthetic' else name}.zip"
        with zipfile.ZipFile(archive) as z:
            assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
            z.extractall(folder)
        if name=='synthetic':
            world=next(folder.glob('*.wwd'))
            logics=world.with_suffix('')/'LOGICS';logics.mkdir(parents=True,exist_ok=True)
            (logics/'MAIN.LUA').write_text('function OnMapLoad() end')
        play=out/name;play.mkdir(exist_ok=True)
        # Only this check's isolated writable directory is reset.
        shutil.rmtree(play/'saves',ignore_errors=True)
        marks=report['marks'][name]=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        for restart in (False,True):
            session=PersistenceSession(play,helper=helper)
            try:
                for log in ('real-speed.json','lua-load.json','native-fault.json','before.json','moved.json'):(play/log).unlink(missing_ok=True)
                session.launch(app,{},['--custom-dir',str(folder),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace','--lua-runtime-check'],start_seconds=180)
                session.load();marks['restart_loaded' if restart else 'loaded']=True;save()
                if name=='arcana_v13':
                    if restart:
                        session.tap(125);session.run(15)
                        session.tap(36);session.run(15);session.tap(36);session.run(45)
                    else:
                        # Real menu selection: classic aspect ratio, then Easy.
                        session.tap(125);session.tap(125);session.tap(36)
                        session.tap(126);session.tap(126);session.tap(36)
                        session.tap(125);session.tap(36);session.run(45)
                    marks['delivered_load_menu' if restart else 'delivered_new_game_menu']=True

                if not restart:
                    before=session.mark('before');session.post('press',124,'down');session.run(12);session.post('press',124,'up');session.run(2);after=session.mark('moved')
                    assert before['player']['x']!=after['player']['x'],[before['player'],after['player']]
                    marks['delivered_movement']=[before['player'],after['player']]
                    marks['file_semantics']=session.script(r"""
local p=GetMapFolder()..'/probe.txt';assert(io.open('missing.txt','r')==nil)
local f=assert(io.open(p,'w+'));assert(f:write('one\n','two\r\n',42));assert(f:seek('set',0)==0)
assert(f:read()=='one');assert(f:read('*line')=='two');assert(f:read('*n')==42);assert(f:read()==nil);assert(f:seek('set',0)==0)
local t={};for line in f:lines() do t[#t+1]=line end;assert(#t==3 and t[3]=='42');assert(f:close());assert(not pcall(function()f:read()end))
local a=assert(io.open(p,'a'));a:write('\ntail');a:close();local r=assert(io.open(p));assert(r:read('*a')=='one\ntwo\r\n42\ntail');r:close()
for _,p in ipairs({'../escape','/tmp/escape','C:\\escape','Custom/Other/save.txt','a/../escape','LOGICS/MAIN.LUA'}) do assert(io.open(p,'w')==nil,p) end
assert(loadfile==nil and dofile==nil and loadstring==nil and io.popen==nil and io.tmpfile==nil)
""")

                    roots=list((play/'saves'/'ScriptSaves'/'v1').iterdir());assert len(roots)==1
                    root=roots[0];sentinel=play/'sentinel.txt';sentinel.write_text('untouched')
                    for path in (root/'SYMLINK.TXT',root/'HARDLINK.TXT'):
                        path.unlink(missing_ok=True)
                    (root/'SYMLINK.TXT').symlink_to(sentinel)
                    os.link(sentinel,root/'HARDLINK.TXT')
                    marks['links_denied']=session.script("for _,p in ipairs({'symlink.txt','hardlink.txt'}) do assert(io.open(p,'w')==nil);assert(io.open(p,'r')==nil) end")
                    assert sentinel.read_text()=='untouched'
                    for path in (root/'SYMLINK.TXT',root/'HARDLINK.TXT'):path.unlink()
                    marks['corrupt_text_is_data']=session.script("local f=assert(io.open('corrupt.txt','w'));f:write('error(123)');f:close();local r=assert(io.open('corrupt.txt'));assert(r:read('*a')=='error(123)');r:close();local t=assert(io.open('truncated.txt','w'));t:write('0');t:close();local r=assert(io.open('truncated.txt'));assert(r:read()=='0');assert(r:read()==nil);r:close()")
                    if name=='synthetic':
                        marks['stream_bound']=session.script("local files={};for i=1,64 do files[i]=assert(io.open('probe.txt')) end;assert(io.open('probe.txt')==nil);for _,f in ipairs(files) do f:close() end;assert(io.open('nul'..string.char(0)..'.txt','w')==nil);local f=assert(io.open('probe.txt'));assert(f:read(3)=='one');assert(f:seek('set',0)==0);io.input(f);assert(io.read()=='one');io.close(f);local n=0;for line in io.lines('probe.txt') do n=n+1 end;assert(n==4)")

                else:
                    marks['file_restart']=session.script("local f=assert(io.open('probe.txt'));assert(f:read()=='one');f:close()")
                # SaveSystem and Achievements are the map's own objects/callbacks.
                if name in ('citd','rotsa'):
                    achievement=4088 if name=='citd' else 7250
                    if not restart:
                        marks['save_trigger']=session.script(f"_a=assert(GetObject({achievement}));assert(_a.achievements_input);_a.achievements_input[2]=1;GetClaw().Health=73;PData().PistolAmmo=37;PData().CollectedCoin=5;GetObject({820 if name=='citd' else 1967}).State=6")
                        session.run(8)
                        marks['saved']=session.script(f"assert(GetObject({achievement}).achievements_statuses[2]==1);local f=assert(io.open(GetMapFolder()..'/save.txt'));local row=f:read('*l');assert(row:find(';'));local fields={{}};for n in row:gmatch('[^;]+') do fields[#fields+1]=tonumber(n) end;assert(#fields==19 and fields[10]~=0 and fields[15]>0);f:close()")
                    else:
                        marks['restored']=session.script(f"assert(GetObject({achievement}).achievements_statuses[2]==1);_save=LoopThroughObjects(function(o) if o.Name=='SaveSystem' then return o end end);assert(_save and _save.TreasureTable[1][10]~=0)")
                    if restart:
                        marks['warp_placement_fixture']=session.script("_warp=LoopThroughObjects(function(o) if o.Name=='SaveWarp' and o.Damage==1 then return o end end);assert(_warp);GetClaw().Health=10;PData().PistolAmmo=1;GetClaw().X=_warp.X-40;GetClaw().Y=_warp.Y")
                        session.post('press',124,'down');session.run(8);session.post('press',124,'up');session.run(2)
                        marks['warp_restored_player']=session.script("assert(GetClaw().Health==73 and PData().PistolAmmo==37 and PData().CollectedCoin==5);assert(GetClaw().X>_warp.X+100)")
                    assert session.live()['custom_level']['checkpoint_owner']=='script SaveSystem'
                    if restart:
                        marks['original_parser_corruption']=session.script("local f=assert(io.open('save.txt'));local original=f:read('*a');f:close();local o=CreateObject{name='SaveSystem'};for _,bad in ipairs({'','0',[[error('saved text must not execute')]]}) do local w=assert(io.open('save.txt','w'));w:write(bad);w:close();o.State=0;local ok,e=pcall(_dispatch,o._handle,'SaveSystem','main',0);assert(not ok and tostring(e):find('string expected'),tostring(e));local r=assert(io.open('save.txt'));assert(r:read('*a')==bad);r:close() end;local w=assert(io.open('save.txt','w'));w:write(original);w:close();o:Destroy()")
                elif name=='arcana_v13':
                    marks['save_system']=session.script("_save=GetObject(2672);assert(_save and _save.statsTable)")
                    native=session.live()['custom_level']
                    marks['star_ladder_native']={k:v for k,v in native.items() if k.startswith(('lua_tileset_','lua_indexed_tile_','lua_tile_'))}
                    assert {'CUSTOM_SPARKLE','CUSTOM_SPARKLEBLUE'}.issubset({v for k,v in native.items() if k.startswith('lua_tileset_')})
                    assert sum(v.get('indexed_frame',False) for k,v in native.items() if k.startswith('lua_indexed_tile_'))>=2
                    if not restart:
                        marks['missing_file_initialized']=session.script("assert(tonumber(_save.savedFlags)==0);local f=assert(io.open('save.txt'));assert(f:read()=='0');for i=1,3 do assert(f:read():match('^0;0;')) end;assert(f:read()==nil);f:close()")
                        marks['lua_plane_join']=session.script("""
local p=GetMainPlane();assert(p==GetPlane('Action'));assert(GetPlane('missing')==nil)
local o=CreateObject{Logic='DoNothing'};o.BumpFlags.EnemyBullet=true;o.HitFlags.MagicBullet=true;o.AttackFlags.Player=true;o.SpecialFlags.TriggerElevator=true;assert(AND(o.SpecialFlags.flags,4096)~=0);local c=GetClaw();o.X=c.X+100;o.Y=c.Y+100;o.XMin=c.X-1;o.XMax=c.X+1;o.YMin=c.Y-1;o.YMax=c.Y+1;assert(c:InMinMax(o) and not o:InMinMax(o));assert(AND(o.ObjectTypeFlags,64)~=0 and AND(o.HitTypeFlags,33554432)~=0 and AND(o.AttackTypeFlags,2)~=0);o:Destroy()
assert(GetImage('CUSTOM_SPARKLE')==GetImage('custom_sparkle'))
local img=GetImage('CUSTOM_SPARKLE');SetImgFlag(img,ImageFlag.Ghost);SetImgColor(img,9);SetImgCLT(img,'LIGHT');SetImgFlag(img,ImageFlag.Normal)
assert(not pcall(GetImage,'MISSING_IMAGE'))
local star=GetPlane('BackStars1');star.Tileset[0]=GetImage('CUSTOM_SPARKLE')
local old=star:GetTile(0,0);star:PlaceTile(0,0,1);assert(star:GetTile(0,0)==1);star:PlaceTile(0,0,old)
local old=p:GetTile(117,164);p:PlaceTile(117,164,-1);assert(p:GetTile(117,164)==-1 and _planeCheckCollision(117*64+32,164*64+32)==0);p:PlaceTile(117,164,203);assert(p:GetTile(117,164)==203 and _planeCheckCollision(117*64+32,164*64+32)==3);p:PlaceTile(117,164,old)
assert(p.ScreenA.Right>p.ScreenA.Left and p.ScreenA.Bottom>p.ScreenA.Top)
for _,f in ipairs({function()p:PlaceTile(-1,0,1)end,function()p:GetTile(999999,0)end,function()p:PlaceTile(117,164,65535)end,function()star.Tileset[999]=GetImage('CUSTOM_SPARKLE')end,function()star.Tileset[0]={_imageName='CUSTOM_SPARKLE'}end,function()p:PlaceTile(0/0,0,1)end}) do assert(not pcall(f)) end
""")
                        marks['glitter_lifecycle']=session.script("local o=CreateObject{Logic='DoNothing',X=GetClaw().X,Y=GetClaw().Y,Z=500};assert(o.GlitterPointer==nil);o:CreateGlitter();local g=assert(o.GlitterPointer);assert(g.X==o.X and g.Y==o.Y and GetImgStr(g.Image)=='GAME_GLITTER');o:CreateGlitter();assert(o.GlitterPointer==g);o:DestroyGlitter();assert(g.Flags.Destroy);o:Destroy()")
                        marks['save_fixture']=session.script("GetClaw().Health=73;GetClaw().Score=12345;PData().PistolAmmo=37;PData().MagicAmmo=19;PData().TNTAmmo=11;PData().Lives=7;PData().CollectedCoin=5;GetObject(3206).ArtifactsOwned=1;assert(GetObject(3206).Difficulty==1 and GetObject(3206).Resolution==1);GetObject(645).State=6");session.run(8)
                        marks['saved']=session.script("assert(AND(_save.savedFlags,16)~=0)")
                    else:
                        marks['restored']=session.script("assert(AND(_save.savedFlags,16)~=0);assert(GetClaw().Health==73 and PData().PistolAmmo==37 and PData().MagicAmmo==19 and PData().TNTAmmo==11 and PData().Lives==7 and PData().CollectedCoin==5);assert(GetClaw().Score==12345 and PData().SpawnPointX>0);local d=GetObject(3206);assert(d.ArtifactsOwned==1 and d.Difficulty==1 and d.Resolution==1 and d.ScreenW==640);assert(LoopThroughObjects(function(o) if o.Name=='ArtifactPower:Amulet' then return o end end));assert(GetMainPlane():GetTile(117,164)==203)")
                        marks['original_parser_corruption']=session.script("local f=assert(io.open('save.txt'));local original=f:read('*a');f:close();local o=CreateObject{name='SaveSystem'};for _,bad in ipairs({'','0',[[error('saved text must not execute')]]}) do local w=assert(io.open('save.txt','w'));w:write(bad);w:close();o.State=0;local ok,e=pcall(_dispatch,o._handle,'SaveSystem','main',0);assert(not ok and tostring(e):find('string expected'),tostring(e));local r=assert(io.open('save.txt'));assert(r:read('*a')==bad);r:close() end;local w=assert(io.open('save.txt','w'));w:write(original);w:close();o:Destroy()")
                elif name=='claw_tower':
                    if not restart:
                        marks['score_trigger']=session.script("GetObject(29).BestScore=54321;GetObject(30).BestCombo=17;GetClaw().Score=54321;GetClaw().I=402")
                        session.run(2)
                    marks['scores']=session.script("local f=assert(io.open(GetMapFolder()..'/BestScore.txt'));assert(f:read()=='Your best score:');assert(f:read('*n')==54321);f:close();local c=assert(io.open('BestCombo.txt'));assert(c:read()=='Your best combo:');assert(c:read('*n')==17);c:close()")
                if name in ('citd','rotsa','arcana_v13'):
                    assert not list((play/'saves'/'CustomSaves').glob('*.plist'))
                    assert not (play/'saves'/'custom-checkpoint.clawcheckpoint').exists()
                    marks['automatic_and_manual_stores_separate']=True
                with zipfile.ZipFile(archive) as z:
                    for path in z.namelist():
                        if path.lower().endswith('.txt'):assert (folder/path).read_bytes()==z.read(path),path
                marks['package_text_unchanged']=True
                marks['restart_input_transitions' if restart else 'input_transitions']=session.transitions()
                save()
            except Exception as error:
                detail=str(error)
                if (play/'real-speed.json').exists():detail=json.loads((play/'real-speed.json').read_text()).get('error') or detail
                marks['error']=detail;report['errors'].append(dict(sample=name,restart=restart,error=detail));save();break
            finally:
                session.close()
                for pattern in ('hud-*.png','frame-*.png'):
                    for path in play.glob(pattern):path.unlink()
    report['status']='fail' if report['errors'] else 'pass';save();return report
