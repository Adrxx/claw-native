"""Native gameplay joins and confirmed window input in unchanged sample maps."""
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile
from real_input import Session, build_helper

ROOT=Path(__file__).resolve().parents[1]

def surface_pid_contract(out):
    # Compile the actual adapter method, then independently decode both streams.
    # This checks sample pixels, anchors and palette without changing the input.
    import hashlib, struct
    source=(ROOT/'Sources/ClawCustomAssets.swift').read_text()
    method=source[source.index('    static func surfacePID('):source.index('    static func bitmapPID(')]
    fixture=out/'surface-pid.swift'
    fixture.write_text('import Foundation\nimport CryptoKit\nenum AssetError:Error {case invalid(String)}\nstruct Adapter {\n'+method+'}\nlet data=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))\ntry (CommandLine.arguments[1].hasSuffix(".ani") ? Adapter.surfaceANI(data):Adapter.surfacePID(data)).write(to:URL(fileURLWithPath:CommandLine.arguments[2]))\n')
    binary=out/'surface-pid'
    compiled=subprocess.run(['xcrun','swiftc','-O',str(fixture),'-o',str(binary)],capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stderr
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/christmas_eve_adventure.zip') as z:
        raw=z.read('Christmas Eve Adventure/LEVEL/RATBOMB/FRAME019.PID')
    original=out/'sample-surface.pid';normalized=out/'normalized-surface.pid'
    original.write_bytes(raw)
    subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
    result=normalized.read_bytes();width,height=struct.unpack_from('<II',raw,8)
    def pixels(data,rows):
        at=32;out=bytearray()
        while len(out)<width*height:
            tag=data[at];at+=1;count=1
            if tag&192==192:count=tag&63;tag=data[at];at+=1
            if rows:assert len(out)%width+count<=width
            out.extend([tag]*count)
        if rows:assert len(out)==width*height
        return bytes(out[:width*height])
    assert pixels(raw,False)==pixels(result,True)
    assert result[:32]==raw[:32] and original.read_bytes()==raw
    marks=dict(pixels=width*height,original_sha256=hashlib.sha256(raw).hexdigest(),unchanged_input=True,anchors_flags_header_preserved=True,cross_row_runs_repacked=True)
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/cat_entertainment_mine.zip') as z:
        raw=z.read('Cat Entertainment Mine/LEVEL/CHAMELEON/FRAME570.pid')
    original.write_bytes(raw)
    subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
    result=normalized.read_bytes();width,height=struct.unpack_from('<II',raw,8)
    assert pixels(raw,False)==pixels(result,True) and result[:32]==raw[:32]
    marks['final_surface_padding']=dict(sample='Cat Entertainment Mine/LEVEL/CHAMELEON/FRAME570.pid',pixels=width*height,visible_pixels_preserved=True,original_sha256=hashlib.sha256(raw).hexdigest())
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/cat_entertainment_mine.zip') as z:
        raw=z.read('Cat Entertainment Mine/LEVEL/CULTIST/IDLE.ANI')
    original=out/'sample-frame-count.ani';normalized=out/'normalized-frame-count.ani'
    original.write_bytes(raw)
    subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
    result=normalized.read_bytes()
    assert struct.unpack_from('<I',raw,12)[0]==17 and struct.unpack_from('<I',result,12)[0]==11
    assert result[:12]==raw[:12] and result[16:]==raw[16:] and original.read_bytes()==raw
    marks['bounded_ani_count']=dict(declared=17,complete_records=11,records_and_padding_unchanged=True,original_sha256=hashlib.sha256(raw).hexdigest())
    negatives=[]
    altered=bytearray(raw);struct.pack_into('<I',altered,36,1);negatives.append(bytes(altered))
    negatives.append(raw[:-3])
    altered=bytearray(raw);struct.pack_into('<I',altered,12,2);negatives.append(bytes(altered))
    for fixture in negatives:
        original.write_bytes(fixture)
        subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
        assert normalized.read_bytes()==fixture
    original.write_bytes(raw)
    marks['bounded_ani_count']['synthetic_guard_cases']=len(negatives)
    marks['cultist_strikes']=[]
    with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/cat_entertainment_mine.zip') as z:
        for name,indices in [('STRIKE2',[200,201,203,205,206,207]),('STRIKE3',[200,201,202,204,206,207])]:
            raw=z.read(f'Cat Entertainment Mine/LEVEL/CULTIST/{name}.ANI')
            original.write_bytes(raw)
            subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
            result=normalized.read_bytes()
            assert result[:32]==raw[:32] and len(result)==152 and original.read_bytes()==raw
            records=[struct.unpack_from('<IIHHhhI',result,32+i*20) for i in range(6)]
            assert [r[2] for r in records]==indices and [r[3] for r in records]==[80,80,80,80,100,100]
            assert [r[1] for r in records]==[0,0,9,9,9,9]
            assert all(r[0]==0x30000 and r[4:6]==(0,0) for r in records)
            starts=[32,52,72,90,108,126,146]
            assert all(result[32+i*20:32+i*20+starts[i+1]-starts[i]]==raw[starts[i]:starts[i+1]] for i in range(6))
            marks['cultist_strikes'].append(dict(animation=name,frames=indices,milliseconds=[r[3] for r in records],original_sha256=hashlib.sha256(raw).hexdigest(),unchanged_input=True))
            altered=bytearray(raw);altered[40]^=1;original.write_bytes(altered)
            subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
            assert normalized.read_bytes()==altered,'unknown malformed export must not be guessed'
    with zipfile.ZipFile(ROOT/'work/crazyhook/CLAW-1.4.5.4.zip') as z:
        raw=z.read('CLAW-1.4.5.4/Assets/GAME/ANIS/PLASSWORDEXPLOSION.ANI')
    original.write_bytes(raw)
    subprocess.run([str(binary),str(original),str(normalized)],check=True,capture_output=True)
    assert normalized.read_bytes()==raw+b'\0'*6 and original.read_bytes()==raw
    marks['plasma_final_record']=dict(original_sha256=hashlib.sha256(raw).hexdigest(),supplied_bytes_preserved=True,zero_extension_bytes=6)
    return marks

def sample_objects(world):
    import struct,zlib
    raw=world.read_bytes();data=raw[:1524]+zlib.decompress(raw[1524:]);result=[]
    for i in range(struct.unpack_from('<I',raw,732)[0]):
        h=1524+160*i
        count=struct.unpack_from('<I',data,h+128)[0];at=struct.unpack_from('<I',data,h+140)[0]
        for _ in range(count):
            words=struct.unpack_from('<71i',data,at);at+=284;values=[]
            for length in words[1:5]:
                values.append(data[at:at+length].rstrip(b'\0').decode('latin1'));at+=length
            result.append(dict(id=words[0],name=values[0],logic=values[1],x=words[5],y=words[6],words=words))
    return result


def script_check(session,script):
    import base64
    script="assert(_callbackError==nil,_callbackError)\n"+script
    request=session.out/'gameplay-assertions.jsonl'
    with request.open('a') as output:output.write(json.dumps(dict(script=script,frame=session.frames))+'\n')
    session._command('lua-gameplay-check '+base64.b64encode(script.encode()).decode())
    session._gate_wait();session.run(1)
    if session.failed():
        failure=json.loads((session.out/'real-speed.json').read_text())
        raise AssertionError(dict(script=script,error=failure.get('error'),frame=failure.get('failing_frame')))
    return json.loads((session.out/'live.json').read_text())['custom_level']['gameplay_check']


def helpers(session,objects):
    marks={}
    marks['boss_handle']=script_check(session,"""
    assert(GetBoss()==nil)
    local o=CreateObject{logic='DoNothing'};SetBoss(o);assert(GetBoss()==o)
    SetBoss(0);assert(GetBoss()==nil)
    local flags,draw=o.Flags.flags,o.DrawFlags.flags
    o.Flags.Invisible=true;assert(o.Flags.Invisible==nil and o.Flags.flags==flags and o.DrawFlags.flags==draw)
    o.Flags.OnDeathTile=true;assert(o.Flags.OnDeathTile);o.Flags.OnDeathTile=false
    assert(o.Flags.flags==flags);o:Destroy()
    """)
    # Real serialized far-away object: lookup includes it, active iteration does
    # not. This is independent of dynamically-created always-active fixtures.
    far=max([o for o in objects if o['logic']=='CustomLogic'],key=lambda o:o['x']*o['x']+o['y']*o['y'])
    marks['active_iteration']=script_check(session,f"""
    local dormant=assert(GetObject({far['id']}),'dormant ID lookup')
    local found=LoopThroughObjects(function(o) if o==dormant then return o end end)
    assert(found==nil,'dormant object leaked into active iteration')
    local count=0
    local result=LoopThroughObjects(function(o,arg) count=count+1;assert(arg==73);return 'stop' end,73)
    assert(count==1 and result=='stop','early return and argument')
    """)
    marks['text_helpers']=script_check(session,"""
    local c=GetClaw()
    local d=CreateObject{name='TextDelayed',x=c.X,y=c.Y,State=6}
    assert(d.State==5 and d.DrawFlags.NoDraw)
    d:Logic();assert(d.State==4 and d.DrawFlags.NoDraw)
    d:Logic();assert(d.State==3 and not d.DrawFlags.NoDraw)
    local y=d.Y;d:Logic();d:Logic();d:Logic();assert(d.State==0 and d.Y==y+6)
    d.DrawFlags.Mirror=true;d:Logic();assert(d.DrawFlags.Mirror);d:Destroy()
    local f=CreateObject{name='TextFadeIn',x=c.X,y=c.Y,State=7,Last=true}
    assert(f.State==6 and f.DrawFlags.NoDraw)
    for i=1,4 do f:Logic() end
    assert(f.State==2 and f.DrawFlags.NoDraw)
    f:Logic();assert(f.State==1 and f.DrawFlags.Mirror)
    f:Logic();assert(f.State==0 and f.DrawFlags.Mirror)
    f:Logic();assert(f.DrawFlags.flags==0);f:Destroy()
    _helperCount=0;_helperOne=function(o) _helperCount=_helperCount+1 end
    CustomPowerup(_helperOne,5000)
    assert(GetCurrentPowerup()==666 and GetCurrentPowerupTime()>0)
    """)
    session.run(3)
    marks['custom_powerup']=script_check(session,"""
    assert(_helperCount>0,'custom powerup callback did not run')
    _helperOld=LoopThroughObjects(function(o) if o.CPN==_helperOne then return o end end)
    assert(_helperOld)
    CustomPowerup(_helperOne,5000)
    assert(LoopThroughObjects(function(o) if o.CPN==_helperOne then return o end end)==_helperOld)
    local count=0;LoopThroughObjects(function(o) if o.CPN==_helperOne then count=count+1 end end);assert(count==1,'duplicate refreshed handler')
    _helperTwo=function(o) _helperCount=_helperCount+10 end
    CustomPowerup(_helperTwo,5000)
    assert(_helperOld.Flags.Destroy,'replaced handler not destroyed')
    """)
    session.run(3)
    marks['custom_powerup_replacement']=script_check(session,"""
    local ok,e=pcall(function() return _helperOld.State end)
    assert(not ok and e:find('StaleHandle'))
    assert(_helperCount>=10)
    assert(LoopThroughObjects(function(o) if o.CPN==_helperTwo then return o end end))
    _helperThree=function(o) _helperCount=_helperCount+100 end
    CustomPowerup(_helperThree,100)
    _helperNew=LoopThroughObjects(function(o) if o.CPN==_helperThree then return o end end)
    assert(_helperNew and GetCurrentPowerupTime()>0)
    """)
    session.run(20)
    marks['custom_powerup_expiration']=script_check(session,"""
    assert(GetCurrentPowerupTime()==0,'custom powerup timer did not expire')
    local ok,e=pcall(function() return _helperNew.State end)
    assert(not ok and e:find('StaleHandle'),'expired helper was not removed')
    """)
    return marks


def plasma(session):
    marks={}
    marks['resource_frames']=script_check(session,"""
    for _,image in ipairs({'GAME_PROJECTILES_PLASMASWORD','GAME_EXPLOS_PLASMA'}) do
        local o=CreateObject{logic='DoNothing',image=image};o:SetFrame(1)
        assert(o.I==1);o:Destroy()
    end
    """)
    marks['setup']=script_check(session,"ClawGivePowerup(Powerup.PlasmaSword,20);assert(GetCurrentPowerup()==Powerup.PlasmaSword)")
    session.post('key',124);session.post('key',59);session.run(120)
    assert not session.failed(),json.loads((session.out/'real-speed.json').read_text()).get('error')
    state=json.loads((session.out/'live.json').read_text())['custom_level']['lua']
    events=state['events']
    projectiles=[e for e in events if e.get('service')=='PlasmaProjectile']
    explosions=[e for e in events if e.get('service')=='PlasmaExplosion']
    assert projectiles,dict(error='real sword input did not create plasma projectile',events=events)
    assert explosions,dict(error='plasma projectile did not run native explosion',events=events)
    marks['native_resources']=dict(projectiles=projectiles,explosions=explosions)
    marks['restore']=script_check(session,"ClawGivePowerup(0,0);assert(GetCurrentPowerup()==0)")
    return marks


def cat_interactions(session,marks):
    marks['callback_monitor']=script_check(session,"""
    _edgeCount=0;_dynamiteCalls=0;_dynamiteBounced=false;_explosionCalls=0;_cultistHitCount=0;_cultistDamage=false;_cultistDead=false
    local dispatch=_dispatch
    function _dispatch(h,name,event,other)
        if event=='destroy' then return dispatch(h,name,event,other) end
        local c=GetClaw();local x,state=c.X,c.State
        local ok,hp=pcall(function() return _cultist and _cultist.Health end)
        local ran,result=pcall(dispatch,h,name,event,other)
        if not ran then _callbackError=_callbackError or name..'/'..event..': '..tostring(result);return end
        if name=='Custom Conveyter' and event=='main' and state==5006 and math.abs(c.X-x)==3 then _edgeCount=_edgeCount+1 end
        if name=='CustomDynamite' and event=='main' then
            _dynamiteCalls=_dynamiteCalls+1
            local o=LoopThroughObjects(function(p) if p._handle==h then return p end end)
            if o and o.SpeedY<0 then _dynamiteBounced=true end
        end
        if name=='CustomDynamiteExplosion' and event=='main' then _explosionCalls=_explosionCalls+1 end
        if name=='Cultist' and event=='hit' and _cultist and ok then
            _cultistHitCount=_cultistHitCount+1
            if _cultist.Health<hp then _cultistDamage=true end
            if _cultist.State==404 then _cultistDead=true end
        end
        return result
    end
    """)
    marks['peg_setup']=script_check(session,"""
    _peg=assert(GetObject(3866));_belt=assert(GetObject(3860))
    local c=GetClaw();c.X=_belt.X-20;c.Y=_belt.Y-100;c.State=24
    """)
    # Hold position with delivered left-key edges on the adjacent conveyor
    # until the native peg finishes its withdrawn phase. Never set its state.
    left=False
    for _ in range(100):
        phase=script_check(session,'assert(GetClaw().Health>0)')
        peg=next((o for o in phase['objects'] if o['id']==3866),{})
        belt=next((o for o in phase['objects'] if o['id']==3860),{})
        claw=next(o for o in phase['objects'] if o['name']=='CaptainClaw')
        if peg.get('state')==1006 and peg.get('frame')==1:break
        if belt:
            desired=claw['x']>belt['x']+4 if not left else claw['x']>=belt['x']-4
            if desired!=left:
                session.post('press',123,'down' if desired else 'up');left=desired
        session.run(3)
    else:raise AssertionError('peg never entered native solid phase')
    if left:session.post('press',123,'up')
    marks['peg_approach']=script_check(session,"""
    local c=GetClaw();c.X=_peg.X-35;c.Y=_peg.Y-70;c.State=24
    _pegStartFrame=_peg.I;_pegStartState=_peg.State
    """)
    session.post('press',124,'down');session.run(3);session.post('press',124,'up');session.run(3)
    marks['peg_contact']=script_check(session,"""
    assert(_peg.HitRect.Left==-24 and _peg.HitRect.Bottom==64,'peg script rectangle')
    local c=GetClaw()
    assert(c.State==ClawStates.Stand and math.abs(c.Y+c.MoveRect.Bottom-(_peg.Y+_peg.HitRect.Top))<=1,'player did not land on custom peg: '..c.X..','..c.Y..' state='..c.State..' peg frame='.._peg.I)
    _pegFrame=_peg.I;_pegState=_peg.State
    """)
    session.post('key',49)
    for _ in range(80):
        phase=script_check(session,'assert(GetClaw().Health>0)')
        peg=next((o for o in phase['objects'] if o['id']==3866),{})
        if peg.get('state')!=1006 or peg.get('frame')!=1:break
        session.run(8)
    else:raise AssertionError('solid peg never transitioned')
    marks['peg_transition']=script_check(session,"assert(_peg.I~=_pegFrame or _peg.State~=_pegState,'peg did not transition')")
    marks['conveyor_setup']=script_check(session,"""
    _belt=GetObject(3860);assert(_belt)
    local c=GetClaw();c.X=_belt.X-20;c.Y=_belt.Y-100;c.State=24
    """)
    session.run(8)
    # The supplied conveyor script documents the native 11-12 pixel foot
    # offset and uses a 14-pixel surface tolerance in its OnEdge branch.
    marks['conveyor_rider']=script_check(session,"""
    local c=GetClaw();assert(c.State==ClawStates.Stand and math.abs(c.Y+c.MoveRect.Bottom-(_belt.Y+_belt.MoveRect.Top))<=14,'conveyor rider contact: '..c.X..','..c.Y..' state='..c.State);_beltX=c.X;_beltY=c.Y
    """)
    session.run(6)
    marks['conveyor_drift']=script_check(session,"local c=GetClaw();assert(c.State==ClawStates.Stand and c.X>_beltX and math.abs(c.Y+c.MoveRect.Bottom-(_belt.Y+_belt.MoveRect.Top))<=14,'standing rider did not move with belt')")
    session.post('press',124,'down');session.run(8);session.post('press',124,'up');session.run(12)
    marks['conveyor_movement']=script_check(session,"assert(GetClaw().X>_beltX,'conveyor rider movement')")
    # Approach the original belt edge using window events, then inspect the
    # source's OnEdge branch and callback outcome, rather than forcing its state.
    marks['conveyor_edge_setup']=script_check(session,"""
    local c=GetClaw();c.X=_belt.X+_belt.MoveRect.Right-8;c.Y=_beltY;c.State=24
    _beltEdgeX=c.X
    """)
    session.post('press',124,'down');session.run(4);session.post('press',124,'up');session.run(2)
    marks['conveyor_edge']=script_check(session,"assert(GetClaw().X>_beltEdgeX and _edgeCount>0,'conveyor OnEdge branch did not move rider')")
    marks['dynamite_setup']=script_check(session,"""
    _fall=GetObject(3909);assert(_fall and _fall.Counter~=1)
    _dynBelt=assert(GetObject(3905))
    local c=GetClaw();c.X=_dynBelt.X-40;c.Y=_dynBelt.Y-100;c.State=24
    _fallStart=GetTime()
    """)
    session.post('press',124,'down');session.run(8);session.post('press',124,'up')
    held=0
    # Remain in the original trigger box on its conveyor floor for two full
    # 2600-ms throw cycles. A late transient lookup can miss both lifetimes.
    for _ in range(100):
        phase=script_check(session,'assert(GetClaw().Health>0)')
        claw=next(o for o in phase['objects'] if o['name']=='CaptainClaw')
        desired=123 if claw['x']>26728 else 124 if claw['x']<26712 else 0
        if desired!=held:
            if held:session.post('press',held,'up')
            if desired:session.post('press',desired,'down')
            held=desired
        session.run(4)
    if held:session.post('press',held,'up')
    marks['dynamite_spawn']=script_check(session,"assert(_dynamiteCalls>0,'falling dynamite never ran its projectile callback')")
    marks['dynamite_explosion']=script_check(session,"""
    assert(_fall.IsClawIntTheBox,'falling dynamite trigger area not entered');assert(_dynamiteCalls>0 and _dynamiteBounced and _explosionCalls>0,'dynamite did not collide and run explosion')
    """)
    marks['cultist_setup']=script_check(session,"""
    _cultist=GetObject(3564);assert(_cultist)
    local c=GetClaw();c.X=_cultist.X-45;c.Y=_cultist.Y-80;c.State=24
    """)
    session.run(30);session.post('key',124)
    marks['cultist_before']=script_check(session,"assert(_cultist.Health==30);_cultistHP=_cultist.Health")
    # Hand attack is the original Control key; repeated real key edges allow
    # the script's 300-ms hit cooldown and the native attack animation to end.
    for _ in range(16):
        phase=script_check(session,'assert(GetClaw().Health>0)')
        claw=next(o for o in phase['objects'] if o['name']=='CaptainClaw')
        enemy=next((o for o in phase['objects'] if o['id']==3564),None)
        if enemy is None or enemy['state']==404 or enemy['health']<=0:break
        distance=enemy['x']-claw['x'];direction=124 if distance>=0 else 123
        # Cultist can retreat after taking a hit. Follow through the window
        # instead of teleporting the enemy or repeatedly swinging out of range.
        session.post('press',direction,'down')
        session.run(max(1,min(20,int((abs(distance)-35)/4.5))))
        session.post('press',direction,'up')
        session.post('key',59);session.run(24)
    marks['cultist_death']=script_check(session,"assert(_cultistHitCount>0 and _cultistDamage and _cultistDead,'cultist damage/death callbacks did not run')")
    return marks


def coin_interactions(session,marks):
    marks['setup']=script_check(session,"""
    _crate=nil;_points=nil;_pointsFrame=nil
    local dispatch=_dispatch
    function _dispatch(h,name,event,other)
        local result=dispatch(h,name,event,other)
        if name=='Coinn' and event=='attack' and _points then _pointsFrame=_points.I end
        return result
    end
    local create=CreateObject
    function CreateObject(v)
        local o=create(v)
        if (v.logic or v.Logic)=='PointsIcon' then _points=o end
        return o
    end
    for i=501,545 do local o=GetObject(i);if o and o.Powerup>0 then _crate=o;break end end
    assert(_crate,'RandCrates did not mark a coin crate')
    local c=GetClaw();c.X=_crate.X-45;c.Y=_crate.Y-50;c.State=24
    _coinScore=c.Score;_coinTreasures=GetTreasuresNb('Coin')
    """)
    session.run(20);session.post('key',59);session.run(12)
    marks['created']=script_check(session,"""
    assert(_crate.State==5,'real hand attack did not hit crate: claw='..GetClaw().X..','..GetClaw().Y..' state='..GetClaw().State..' crate='.._crate.X..','.._crate.Y)
    _coin=LoopThroughObjects(function(o) if o.Name=='Coinn' then return o end end)
    assert(_coin,'crate did not create Coinn')
    local c=GetClaw();c.X=_coin.X-25;c.Y=_coin.Y;c.State=24
    """)
    session.post('press',124,'down');session.run(8);session.post('press',124,'up');session.run(4)
    marks['score']=script_check(session,"""
    assert(_coin.State==3 and GetClaw().Score==_coinScore+100,'coin contact did not add score');_coinCollectTime=GetTime()
    assert(GetTreasuresNb('Coin')==_coinTreasures,'script coin must not silently register retail treasure')
    local total=GetTreasuresNb('Coin');RegisterTreasure('Coin',1);assert(GetTreasuresNb('Coin')==total+1)
    RegisterTreasure('Coin',-1);assert(GetTreasuresNb('Coin')==total)
    """)
    marks['points']=script_check(session,"assert(_points,'native PointsIcon was not created');assert(_pointsFrame==1,'points icon frame at creation')")
    session.run(300)
    # FreezeClaw warps the player to the hub on collection. Coinn is not
    # AlwaysActive, so expiration is processed when its arena is revisited.
    marks['cleanup_revisit']=script_check(session,"""
    local c=GetClaw()
    local ok,x,y=pcall(function() return _coin.X,_coin.Y end)
    if ok then c.X=x+100;c.Y=y;c.State=24 end
    """)
    session.post('press',123,'down');session.run(8);session.post('press',123,'up');session.run(240)
    marks['cleanup']=script_check(session,"""
    for _,o in ipairs({_coin,_points}) do local ok,e=pcall(function() return o.State end);assert(not ok and e:find('StaleHandle'),'coin/points lifetime cleanup after '..(GetTime()-_coinCollectTime)..' ms: '..tostring(e)) end
    """)
    return marks


def api_inventory():
    import re
    census=json.loads((ROOT/'work/crazyhook/features.json').read_text())['api_symbols']
    bootstrap=(ROOT/'Sources/ClawLuaBootstrap.inc').read_text()
    registry=(ROOT/'Sources/LogicRegistry.cpp').read_text()
    builtins=set(re.findall(r'\{"([A-Za-z0-9_]+)",',registry))
    native=set(re.findall(r'^function ([A-Za-z0-9_]+)\(',bootstrap,re.M))|{'AND','OR','PData','GetTicks'}
    palettes={'GetCurrentPalette','GetFirstPalette','GetImage','SetImgColor','SetImgFlag'}
    presentation={'CameraToObject','CameraToPoint','ChangeResolution','CreateHUDObject','Earthquake','GetBoss','GetCameraPoint','GetInput','GetResolution','MessageBox','SetBoss','SetBossFightPoint','SetCameraToPointSpeed'}
    rows={}
    for name,evidence in census.items():
        if name in palettes:status='native palette adapter; separate palettes group'
        elif name in native:status='native Lua adapter'
        elif name in builtins:status='original registered logic'
        elif name in presentation:status='later presentation service; typed NotImplemented'
        else:status='later binding service; typed NotImplemented'
        rows[name]=dict(status=status,samples=evidence['samples'])
    return rows


def gameplay():
    import fcntl
    if os.environ.get('CLAW_BUILD_LOCK_HELD')=='1':return check_gameplay()
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return check_gameplay()

def check_gameplay():
    out=ROOT/'work/crazyhook/checks/gameplay';out.mkdir(parents=True,exist_ok=True)
    path=out.parent/'gameplay.json'
    report=dict(group='gameplay',status='fail',marks={},pending=['Christmas Eve scripted play','CustomTogglePeg transition','Custom Conveyter rider/edge movement','FallingDynamite collision/explosion','Cultist damage and death','crate-hit creates Coinn','coin attack changes score','coin and points cleanup','treasure totals registration','plasma sword projectile/explosion behavior','LoopThroughObjects active-list semantics'],ipad='Mac Catalyst only; iPad runtime not tested')
    path.write_text(json.dumps(report,indent=2)+'\n')
    # The build/check lock is shared with other app lanes.
    helper=build_helper(ROOT/'work/cheat-codes/post-window-input')
    app=ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
    report['scope']='Focused Mac Catalyst objects and service joins; no whole-map or iPad acceptance'
    report['observed_later_binding']={'sample':'Cat Entertainment Mine','script':'Turtle.lua:573','operation':'nRes(11, 473)','behavior':'stun timer read; NotImplemented in legacy bindings','evidence':'gameplay-turtle-binding.json'}
    report['marks']['sampled_api_inventory']=api_inventory()
    report['limitations']={k:v for k,v in report['marks']['sampled_api_inventory'].items() if v['status'].startswith('later')}
    import hashlib
    archives={name:hashlib.sha256((ROOT/f'work/custom-levels/crazyhook-sample/{name}.zip').read_bytes()).hexdigest() for name in ['christmas_eve_adventure','cat_entertainment_mine','get_the_coin']}
    report['input_archives']=archives
    bundled=app/'Contents/Resources/GameData/CRAZYHOOK'
    manifest=json.loads((bundled/'manifest.json').read_text())
    assert len(manifest['files'])==27
    assert all(hashlib.sha256((bundled/p).read_bytes()).hexdigest()==digest for p,digest in manifest['files'].items())
    report['marks']['helper_assets']=manifest
    session=None
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location('lua_contracts',ROOT/'scripts/check-crazyhook-lua.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        report['marks']['interpreter']=module.interpreter(out)
        report['marks']['surface_pid']=surface_pid_contract(out)
        names=os.environ.get('CLAW_GAMEPLAY_SAMPLES','christmas_eve_adventure,cat_entertainment_mine,get_the_coin').split(',')
        folder=out/'input'/'session';folder.mkdir(parents=True,exist_ok=True)
        worlds={}
        for name in names:
            with zipfile.ZipFile(ROOT/f'work/custom-levels/crazyhook-sample/{name}.zip') as z:
                assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
                z.extractall(folder)
            worlds[name]=folder/next(p for p in z.namelist() if p.lower().endswith('.wwd'))
        play=out/'session';play.mkdir(exist_ok=True)
        (play/'gameplay-assertions.jsonl').unlink(missing_ok=True)
        session=Session(play,helper=helper)
        for name in names:
            world=worlds[name]
            for filename in ['real-speed.json','native-fault.json','lua-load.json']:(play/filename).unlink(missing_ok=True)
            def live():return json.loads((play/'live.json').read_text())
            def tap(code):
                session.post('key',code);session.run(12)
                assert not session.failed(),session.gate()
            try:
                if name==names[0]:
                    session.launch(app,{'CLAW_TRACE_DEPTH':'30000'},['--custom-dir',str(folder),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace','--lua-runtime-check'],start_seconds=180)
                session.run(60)
                if live().get('menu_page')==10000:tap(36)
                for _ in range(10):
                    if live().get('menu_selected')==11003:break
                    tap(125)
                tap(36);assert live().get('custom_dialog'),live()
                index=live()['custom_files'].index(world.name)
                for _ in range(index):tap(125)
                tap(36)
                assert not live().get('custom_dialog'),live().get('custom_error')
                assert live().get('state_vtable')=='0x50c264',live()
                session.run(60)
                assert not session.failed(),session.gate()
                session._command('lua-gameplay');session._gate_wait();session.run(2)
                assert not session.failed(),session.gate()
                assert live()['custom_level'].get('gameplay_values','').startswith('pass'),live()
                session._command('lua-stale');session._gate_wait();session.run(1)
                assert not session.failed(),session.gate()
                script_check(session,"assert(_helperCount==nil and _cultist==nil,'Lua globals leaked from previous map');assert(GetCurrentPowerup()==0,'powerup leaked from previous map')")
                before=session.mark(name+'-before')
                session.post('press',124,'down');session.run(30);session.post('press',124,'up')
                after=session.mark(name+'-moved')
                assert before['player']['x']!=after['player']['x'],[before['player'],after['player']]
                runtime=live()['custom_level'].get('lua',{})
                assert not runtime.get('error'),runtime
                report['marks'][name]=dict(before=before['player'],after=after['player'],runtime=runtime,input=session.transitions())
                # Named interactions remain pending until their own assertions
                # and confirmed input traces exist; loading is not acceptance.
                if name=='christmas_eve_adventure':
                    report['pending'].remove('Christmas Eve scripted play')
                    report['marks']['helpers']=helpers(session,sample_objects(world))
                    report['pending'].remove('LoopThroughObjects active-list semantics')
                    report['marks']['plasma']=plasma(session)
                    report['pending'].remove('plasma sword projectile/explosion behavior')
                elif name=='cat_entertainment_mine':
                    report['marks']['cat_interactions']={}
                    cat_interactions(session,report['marks']['cat_interactions'])
                    for mark in ['CustomTogglePeg transition','Custom Conveyter rider/edge movement','FallingDynamite collision/explosion','Cultist damage and death']:report['pending'].remove(mark)
                else:
                    report['marks']['coin_interactions']={}
                    coin_interactions(session,report['marks']['coin_interactions'])
                    for mark in ['crate-hit creates Coinn','coin attack changes score','coin and points cleanup','treasure totals registration']:report['pending'].remove(mark)
                for code in [46,35,1,8,32,37,37,16]:tap(code)
                assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',10),live()
                for _ in range(10):
                    if session.wait(lambda:live().get('state_vtable')!='0x50c0c4',12):break
                    tap(36)
                assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
                assert live()['custom_level'].get('unloaded'),live()['custom_level']
                report['marks'][name]['completion']='MPSCULLY, results, menu; Lua ended and package unmounted in shared session'
            finally:
                report['marks'].setdefault(name,{})['confirmed_input']=session.transitions()
                if play.joinpath('live.json').exists():
                    report['marks'].setdefault(name,{})['last_live']=live().get('custom_level',{})
                for filename in ['real-speed.json','native-fault.json']:
                    p=play/filename
                    if p.exists():
                        d=json.loads(p.read_text());report['marks'].setdefault(name,{})[filename]={k:d[k] for k in ['error','address','failing_frame'] if k in d}
                for pattern in ['frame-*.png','hud-*.png']:
                    for p in play.glob(pattern):
                        if p.name!='frame-fail.png':p.unlink()
                path.write_text(json.dumps(report,indent=2)+'\n')
        assert all(hashlib.sha256((ROOT/f'work/custom-levels/crazyhook-sample/{name}.zip').read_bytes()).hexdigest()==digest for name,digest in archives.items()),'sample archive changed'
        assert not report['pending'],report['pending']
        report['status']='pass'
    finally:
        if session:session.close()
        path.write_text(json.dumps(report,indent=2)+'\n')
    return report
