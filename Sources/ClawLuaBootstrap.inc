R"CLAWLUA(
local host, source, makeProxy = _host, _source, _proxy
-- No process streams or filesystem entry points beyond map-scoped io.open.
local fileMethods
local outputFile,inputFile
function io.output(f) if f==nil then return outputFile end;if type(f)=='string' then f=assert(io.open(f,'w')) end;outputFile=f;return f end
function io.input(f) if f==nil then return inputFile end;if type(f)=='string' then f=assert(io.open(f,'r')) end;inputFile=f;return f end
function io.write(...) return assert(outputFile,'no output file'):write(...) end
function io.read(...) return assert(inputFile,'no input file'):read(...) end
function io.close(f) return assert(f or outputFile,'no output file'):close() end
function io.flush() return assert(outputFile,'no output file'):flush() end
local function lines(f,autoClose)
    return function() local line=f:read('*l');if line==nil and autoClose then f:close() end;return line end
end
function io.lines(path) if path then return lines(assert(io.open(path,'r')),true) end;return lines(assert(inputFile,'no input file'),false) end
-- The host installs this method without exposing a metatable mutation API.
_fileLines=function(f) return lines(f,false) end
OR,AND,NOT=bit.bor,bit.band,bit.bnot
bit.tobit=function(x) return bit.bor(x,0) end
bit.rol=function(x,n) n=n%32;if n==0 then return bit.tobit(x) end;return bit.bor(bit.lshift(x,n),bit.rshift(x,32-n)) end
bit.ror=function(x,n) return bit.rol(x,-n) end
bit.tohex=function(x,n) local v=bit.tobit(x);if v<0 then v=v+4294967296 end;local s=string.format('%08x',v);n=n or 8;return n<0 and s:sub(-math.min(-n,8)):upper() or s:sub(-math.min(n,8)) end
Flags={NoHit=1,AlwaysActive=2,Safe=4,AutoHitDamage=8,OnElevator=16,Destroy=0x10000,OnDeathTile=0x400000}
DrawFlags={NoDraw=1,Mirror=2,Invert=4,Flash=8}
CollisionFlags={Generic=1,Player=2,Enemy=4,Unknown1=8,ThrownObject=16,PistolBullet=32,EnemyBullet=64,Platform=128,Special=256,Curse=512,Unknown2=1024,Checkpoint=2048,JumpSwitch=4096,Unknown3=8192,Unknown4=16384,Unknown5=32768,Health=65536,Unknown6=131072,Treasure=262144,Unknown7=524288,MagicAmmo=1048576,Unknown8=2097152,Unknown9=4194304,PistolAmmo=8388608,EnvBullet=16777216,MagicBullet=33554432,Sound=67108864}
SpecialFlags={StopElevator=1,Liftable=1,StartElevator=2,OneWayElevator=256,Punchable=1024,TriggerElevator=4096,FireShot=262144,IceShot=524288,LightningShot=1048576}
PhysicsTypes={Stand=1,Walk=2,Jump=3,Fall=4,Duck=5,Climb=6,Other=7,Fly=8}
PhysicsFlags={Hit=65536,WallHit=131072,RightHit=262144,LeftHit=524288,DeathLand=1048576,ElevatorLand=2097152,GroundLand=4194304,CeilingHit=8388608,FloorHit=16777216}
ObjectType={Generic=1,Player=2,Enemy=4,PowerUp=8,Shot=16,PShot=32,EShot=64,Special=128,User1=256,User2=512,User3=1024,User4=2048}
_host, _source, _proxy = nil, nil, nil
local shared, logics, objects, modules = _G, {}, {}, {bit=bit}
local pendingAPIs=setmetatable({}, {__mode='k'})
local function unavailable(name)
    local f=function() error('NotImplemented: '..name,2) end
    pendingAPIs[f]=name;return f
end
function _assertImplemented(name)
    local value=rawget(shared,name)
    assert(value~=nil and not pendingAPIs[value],'NotImplemented: sampled API '..name)
end
local function checked(h) host(5,h,''); return h end
local scalar = {'X','Y','Z','State','Health','Direction','SpeedX','SpeedY','Counter','Score','Powerup','UserValue1','UserValue2','UserValue3','UserValue4','UserValue5','UserValue6','UserValue7','UserValue8','ID','ObjectType','HitType','AttackType','ObjectTypeFlags','HitTypeFlags','AttackTypeFlags','FacingDir','Points','Damage','Smarts','XMin','XMax','YMin','YMax','XTweak','YTweak','Width','Height','TimeDelay','FrameDelay','Speed','MoveResX','MoveResY','UserFlags','I','AX','AY','EditorX','EditorY','EditorZ','PhysicsType','MoveClawX','MoveClawY','OnScreenWidth','OnScreenHeight','OnScreen','_field_F4'}
local scalarSet = {}; for _,k in ipairs(scalar) do scalarSet[k]=true end
local rectangles = {MoveRect=true,HitRect=true,AttackRect=true,ClipRect=true,UserRect1=true,UserRect2=true}
local flags = {Flags=true,DrawFlags=true,BumpFlags=true,HitFlags=true,AttackFlags=true,SpecialFlags=true}
local reserved={Logic=true,Image=true,Graph=true,Sound=true,_Game_=true,_Animation_=true,ObjectBelow=true,HitRef=true,AttRef=true,BumpRef=true,GlitterPointer=true}
function _paletteService(key,value) return host(9,0,'Palette:'..key,value or 0) end
local rectIndex={Left=0,Top=1,Right=2,Bottom=3,left=0,top=1,right=2,bottom=3}
local function array(h,field,count)
    return makeProxy({
        __index=function(_,i) checked(h); if type(i)~='number' or i<0 or i>=count or i%1~=0 then error('ValueBounds: '..field,2) end;return host(0,h,field..':'..i) end,
        __newindex=function(_,i,v) checked(h);if type(i)~='number' or i<0 or i>=count or i%1~=0 then error('ValueBounds: '..field,2) end;host(1,h,field..':'..i,v) end})
end
local function rect(h,field)
    local a=array(h,field,4)
    return makeProxy({
        __index=function(_,k) local i=rectIndex[k];if i==nil and type(k)=='number' then i=k-1 end;return a[i] end,
        __newindex=function(_,k,v) local i=rectIndex[k];if i==nil and type(k)=='number' then i=k-1 end;a[i]=v end})
end
-- The release flag metatype returns nil and ignores writes for absent names;
-- e.g. Cat Sensor uses the undefined Flags.Invisible. Do not invent a bit.
local function flag(h,field)
    local bits=field=='DrawFlags' and DrawFlags or field=='Flags' and Flags or field=='SpecialFlags' and SpecialFlags or CollisionFlags
    return makeProxy({
        __index=function(_,k) checked(h);local v=host(0,h,field);if k=='flags' then return v end;local b=bits[k];if not b then return nil end;return bit.band(v,b)~=0 end,
        __newindex=function(_,k,v) checked(h);if k=='flags' then host(1,h,field,v);return end;local b=bits[k];if not b or type(v)~='boolean' then return end;local old=host(0,h,field);host(1,h,field,v and bit.bor(old,b) or bit.band(old,bit.bnot(b))) end})
end
local methods = {}
function methods:Destroy() host(4,checked(self._handle),'') end
function methods:CreateGlitter(img)
    if self.GlitterPointer then return end
    -- The release module selects GAME_GLITTER for every supplied color name.
    if img~=nil then assert(type(img)=='string','ValueType: glitter image') end
    local g=CreateObject{X=self.X,Y=self.Y,Z=self.Z,logic='PowerupGlitter',image=img and 'GAME_GLITTER'}
    host(8,checked(self._handle),'GlitterAttach',g._handle)
end
function methods:DestroyGlitter() local g=self.GlitterPointer;if g then g:Destroy() end end
function methods:SetAnimation(name,n) return host(8,checked(self._handle),'SetAnimation:'..name,n or 0) end
function methods:SetImage(name) return host(8,checked(self._handle),'SetImage:'..name) end
function methods:SetSound(name) return host(8,checked(self._handle),'SetSound:'..name) end
function methods:SetFrame(n) return host(8,checked(self._handle),'SetFrame',n) end
function methods:AnimationStep() return host(8,checked(self._handle),'AnimationStep') end
function methods:AlignToGround() return host(8,checked(self._handle),'AlignToGround') end
function methods:Physics(x,y,p) return host(8,checked(self._handle),'Physics:'..x..':'..y,p or 8) end
function methods:IsBelow(other) return other.Flags.OnElevator and other.ObjectBelow==self end
function methods:InMinMax(other) assert(other,'ValueType: bounds object');return self.X>other.XMin and self.X<other.XMax and self.Y>other.YMin and self.Y<other.YMax end
function methods:GetSelf() return checked(self._handle) end
function methods:Logic() return host(8,checked(self._handle),'Logic') end
function RemoveSound(name) return host(9,0,'RemoveSound:'..name)~=0 end
function RestoreSound(name) return host(9,0,'RestoreSound:'..name)~=0 end
function PlaySound(name) return host(9,0,'Sound:'..name) end
function methods:PlaySound(name) return PlaySound(name) end
function ClawSound(name) host(9,0,'Voice:'..name) end
function TextOut(text) return host(9,0,'Text:'..tostring(text)) end
InputFlags={Jump=1,Attack=2,Projectile=4,ToggleProjectile=8,Unused=16,Lift=32,Pistol=64,Magic=128,Dynamite=256,Special=512,Left=0x1000000,Right=0x2000000,Up=0x4000000,Down=0x8000000}
VKey={LEFT_MOUSE=1,RIGHT_MOUSE=2,MIDDLE_MOUSE=4,BACKSPACE=8,TAB=9,ENTER=13,SHIFT=16,CONTROL=17,ALT=18,PAUSE=19,ESCAPE=27,SPACE=32,LEFT_ARROW=37,UP_ARROW=38,RIGHT_ARROW=39,DOWN_ARROW=40}
for i=48,90 do VKey[string.char(i)]=i end
for i=1,12 do VKey['F'..i]=111+i end
local function keyCode(key)
    local code=type(key)=='number' and key or VKey[key] or (type(key)=='string' and VKey[key:upper()])
    if not code and InputFlags[key] then code=host(9,0,'ActionKey:'..key) end
    assert(code,'KeyPressed: unknown key or action')
    return code
end
function KeyPressed(key) return host(9,0,'Key:'..keyCode(key))~=0 end
function GetKeyInput(key) return host(9,0,'KeyEdge:'..keyCode(key))~=0 end
function GetInput(input)
    local state=host(9,0,'Input')
    if input==nil then return state end
    local mask=type(input)=='number' and input or assert(InputFlags[input],'Unknown input action')
    return bit.band(state,mask)~=0
end
local function point(x,y) return {x=x,y=y,X=x,Y=y} end
function GetCursorPos() return point(host(9,0,'PointerX'),host(9,0,'PointerY')) end
function CameraToClaw() return host(9,0,'CameraToClaw') end
local function xy(x,y) if type(x)~='number' then return x.x or x.X,x.y or x.Y end;return x,y end
function CameraToPoint(x,y) x,y=xy(x,y);return host(9,0,'CameraPoint:'..x,y) end
function CameraToObject(o) if o then return CameraToPoint(o.X,o.Y) end end
function SetCameraPoint(x,y) x,y=xy(x,y);return host(9,0,'CameraSet:'..x,y) end
SetCameraPos=SetCameraPoint
function GetCameraPoint() return point(host(9,0,'CameraX'),host(9,0,'CameraY')) end
GetCameraPos=GetCameraPoint
function SetCameraToPointSpeed(x,y) return host(9,0,'CameraSpeed:'..x,y) end
function Earthquake(t) return host(9,0,'Quake',tonumber(t) or 1000) end
function ChangeResolution(w,h) return host(9,0,'Resolution:'..w,h) end
function GetResolution() return host(9,0,'ResolutionWidth'),host(9,0,'ResolutionHeight') end

local object
object=function(h)
    if h==0 then error('ValueType: zero object handle',2) end
    checked(h)
    if objects[h] then return objects[h] end
    local values={}
    local proxy=makeProxy({
        __index=function(_,k)
            checked(h)
            if k=='_handle' then return h end
            if k=='Image' then return {_imageObject=h} end
            if k=='_v' then return objects[h] end
            if k=='_userdata' then return _legacyObjectView(h,'private') end
            if k=='_Game_' then return _legacyObjectView(h,'Game') end
            if k=='_p' or k=='PData' then return makeProxy({
                __index=function(_,k) checked(h);if k=='_unkns' then return makeProxy({__index=function(_,i) assert(type(i)=='number' and i%1==0 and i>=-1 and i<35,'PData array bounds');return host(0,h,'PDataArray:'..i) end,__newindex=function(_,i,v) assert(type(i)=='number' and i%1==0 and i>=-1 and i<35,'PData array bounds');host(1,h,'PDataArray:'..i,v) end}) end;return host(0,h,'PData:'..k) end,
                __newindex=function(_,k,v) checked(h);host(1,h,'PData:'..k,v) end}) end
            if k=='User' then return array(h,'User',8) end
            if scalarSet[k] then return host(0,h,k) end
            if rectangles[k] then return rect(h,k) end
            if flags[k] then return flag(h,k) end
            if k=='Logic' then return _legacyLogic and _legacyLogic(h) or methods.Logic end
            if k=='ObjectBelow' or k=='HitRef' or k=='AttRef' or k=='BumpRef' or k=='GlitterPointer' then local peer=host(8,h,k);return peer~=0 and object(peer) or nil end
            if reserved[k] then error('NotImplemented: object pointer/service '..k,2) end
            return methods[k] or values[k]
        end,
        __newindex=function(_,k,v)
            checked(h)
            if reserved[k] or k=='_handle' or k=='_v' or k=='_p' or k=='PData' then error('NotImplemented: object pointer/service '..k,2) end
            if k=='Name' then host(6,h,v);values[k]=v
            elseif scalarSet[k] then host(1,h,k,v)
            elseif rectangles[k] then for i=1,4 do host(1,h,k..':'..(i-1),v[i] or v[({'Left','Top','Right','Bottom'})[i]]) end
            elseif flags[k] then host(1,h,k,type(v)=='number' and v or v.flags)
            else values[k]=v end
        end,
        __metatable='typed game object'})
    objects[h]=proxy
    return proxy
end
function GetObject(id) assert(type(id)=='number' and id==math.floor(id) and id>=0 and id<=4294967295,'ValueType: object ID');local h=host(9,0,'ID',id);return h~=0 and object(h) or nil end
function GetClaw() return object(host(7,0,'player')) end
function GetTime() return host(9,0,'Time') end
GetTicks=GetTime
os={time=function() return host(9,0,'Epoch') end}
function PlayerData() return GetClaw().PData end
PData=PlayerData
function Attempt() return PlayerData().AttemptNb end
function GetGameType() return 3 end
GameType={SinglePlayer=3,MultiPlayer=4}
-- Release message bookkeeping is three level-scoped words. Single-player
-- scripts can use/reset these values without enabling network transport.
MultiMessage={[0]=0,[1]=0,[2]=0}
function ResetMultiMessage() MultiMessage[0]=0;MultiMessage[1]=0;MultiMessage[2]=0 end
function StopSound(name) return host(12,0,'Audio:StopSound:'..name) end
function StunClaw(ms) snRes(ms or 0,11,473) end
function ExitLevel() return host(12,0,'ExitLevel:') end
function GetMusicVolume() return host(12,0,'Audio:GetVolume:LEVEL') end
function SetMusicVolume(value) assert(type(value)=='number' and value>=0 and value<=100 and value%1==0,'ValueRange: music volume');return host(12,0,'Audio:SetVolume:LEVEL',value) end
function MessageBox(text,title) return host(12,0,'MessageBox:'..tostring(title or '')..'\n'..tostring(text)) end
-- API dialect targeted by the native adapter; unsupported services still error.
version=1454
ClawStates={Jump=4,MoveRight=8,MoveLeft=9,Stand=24,Fall=25,Crouch=26,Climb=27,Hit=31,Lift=5000,Throw=5001,Land=5002,LookUp=5003,DeathFall=5004,Death=5005,OnEdge=5006,OnRope=5007,Swing=5007,Bearhug=5008,Freeze=5009}
TreasureType={Coin=0,Goldbar=1,Ring=2,Chalice=3,Cross=4,Scepter=5,Gecko=6,Crown=7,Skull=8}
function GetTreasuresNb(t) return host(9,0,'Treasure:'..tostring(TreasureType[t] or t)) end
function RegisterTreasure(t,n) return host(9,0,'RegisterTreasure:'..tostring(TreasureType[t] or t),n or 1) end
function LoadBaseLevDefaults(n) return host(9,0,'LoadBaseLevDefaults',n) end
function SetDeathType(t) LevelBasedData[0].DeathTileType=t end
-- Freeze is an inert player state in the native host; the image stays bound.
-- NoHit and Safe are the release helper's explicit protection flags.
function BlockClaw() local c=GetClaw();c.State=ClawStates.Freeze;c.SpeedX=0;c.SpeedY=0;c.Flags.NoHit=true;c.Flags.Safe=true end
function UnblockClaw() local c=GetClaw();c.State=24;c.Flags.NoHit=false;c.Flags.Safe=false end
function ClawTakeDamage(n) return host(9,0,'Damage',n) end
function KillClaw() return host(9,0,'Kill') end
function ClawJump(n) return host(9,0,'Jump',n or 1) end
function MultClawSpeed(n) if n=='r' then n=1 end;assert(type(n)=='number','ValueType: MultClawSpeed');return host(9,0,'MovementSpeed',n) end
function SetNormalJumpHeight(n) assert(type(n)=='number','ValueType: SetNormalJumpHeight');return host(9,0,'JumpHeight:0',n) end
function SetRunningJumpHeight(n) assert(type(n)=='number','ValueType: SetRunningJumpHeight');return host(9,0,'JumpHeight:1',n) end
function SetCatnipJumpHeight(n) assert(type(n)=='number','ValueType: SetCatnipJumpHeight');return host(9,0,'JumpHeight:2',n) end
function SetJordanJumpHeight(n) assert(type(n)=='number','ValueType: SetJordanJumpHeight');return host(9,0,'JumpHeight:3',n) end
function SetClawFallSpeedCap(n) assert(type(n)=='number','ValueType: SetClawFallSpeedCap');return host(9,0,'FallSpeedCap',n) end
function Teleport(x,y) return host(9,0,'Teleport:'..x,y) end
TeleportClaw=Teleport
function SetRespawnPoint(x,y) PlayerData().SpawnPointX=x or GetClaw().X;PlayerData().SpawnPointY=y or GetClaw().Y end
local function createObject(v,hud)
    assert(type(v)=='table','CreateObject expects values')
    local logic=v.Logic or v.logic or 'CustomLogic'
    local id=v.ID or v.id or -1
    local h=host(hud and 14 or 3,0,logic..'|'..id..'|'..(v.X or v.x or GetClaw().X)..'|'..(v.Y or v.y or GetClaw().Y)..'|'..(v.Z or v.z or 0)..'|'..(v.flags or 0x40000))
    local o=object(h)
    local aliases={x='X',y='Y',z='Z',id='ID',name='Name',image='Image',animation='Animation',i='I'}
    local name=v.Name or v.name
    if name then o.Name=name end
    local image=v.Image or v.image
    local animation=v.Animation or v.animation
    local sound=v.Sound or v.sound
    if image then o:SetImage(image) end
    if animation then o:SetAnimation(animation) end
    if sound then o:SetSound(sound) end
    for k,value in pairs(v) do
        local field=aliases[k] or k
        if field~='Image' and field~='Animation' and field~='Sound' and field~='sound' and field~='I' and field~='Logic' and field~='logic' and field~='Name' and field~='flags' then o[field]=value end
    end
    local frame=v.I or v.i
    if frame and frame>0 then o:SetFrame(frame) end
    if logic=='CustomLogic' and name then _dispatch(h,name,'main',0) else o:Logic() end
    return o
end
function CreateObject(v) return createObject(v,false) end
function CreateHUDObject(v) return createObject(v,true) end
function CreateGoodie(v)
    v=v or {};host(9,0,'Goodie:'..(v.X or v.x or GetClaw().X)..':'..(v.Y or v.y or GetClaw().Y)..':'..(v.Z or v.z or 1000),v.Powerup or v.powerup or 33)
end
function LoopThroughObjects(fun,arg)
    local snapshot={};local h=0
    repeat h=host(9,0,'Next',h);if h~=0 then snapshot[#snapshot+1]=h end until h==0
    for _,id in ipairs(snapshot) do
        if host(9,0,'Alive',id)~=0 then
            local result
            if type(fun)=='function' then result=fun(object(id),arg) else object(id):Logic() end
            if result then return result end
        end
    end
end
Powerup={Custom=666,FireSword=0x26b8,LightningSword=0x26b9,IceSword=0x26ba,PlasmaSword=0x26bb,Catnip=0x26bc,Ghost=0x26b7,Vader=0x26bd}
function GetCurrentPowerup() return host(9,0,'Powerup') end
function GetBoss() local h=host(9,0,'Boss');return h~=0 and object(h) or nil end
function SetBoss(o) return host(9,0,'SetBoss',(o==nil or o==0) and 0 or checked(o._handle)) end
function GetCurrentPowerupTime() return host(9,0,'PowerupTime') end
function ClawGivePowerup(kind,seconds) return host(9,0,'GivePowerup:'..kind,seconds and seconds*1000 or 30000) end
local customPowerupHandler
function CustomPowerup(callback,milliseconds)
    if callback==nil then return end
    assert(type(callback)=='function','CustomPowerup expects a function')
    if GetCurrentPowerup()~=666 or GetCurrentPowerupTime()==0 then customPowerupHandler=nil end
    if customPowerupHandler and customPowerupHandler.CPN~=callback then
        customPowerupHandler:Destroy();customPowerupHandler=nil;ClawGivePowerup(0,0)
    end
    host(9,0,'GivePowerup:666',milliseconds or 30000)
    if not customPowerupHandler then customPowerupHandler=CreateObject{name='_CustomPowerupHandler'} end
    customPowerupHandler.Flags.AlwaysActive=true;customPowerupHandler.CPN=callback
end
logics._custompoweruphandler={main=function(o)
    o.Flags.AlwaysActive=true
    if GetCurrentPowerup()~=666 or GetCurrentPowerupTime()==0 or GetClaw().Health<=0 then o:Destroy() end
    if type(o.CPN)=='function' then o.CPN(o) end
end}
logics.textdelayed={main=function(o)
    local state=o.State
    if state>0 and state<4 then o.Y=o.Y+state end
    if state>0 then o.DrawFlags.flags=state>4 and DrawFlags.NoDraw or 0;o.State=state-1 end
end}
logics.textfadein={main=function(o)
    local state=o.State
    if state>0 and state%6==1 then PlaySound('GAME_MRF') end
    if state==1 and o.Last then PlaySound('GAME_SDPT2') end
    o.DrawFlags.flags=state>2 and DrawFlags.NoDraw or state>0 and DrawFlags.Mirror or 0
    if state>0 then o.State=state-1 end
end}
local ffi={}
function ffi.new(kind,initial)
    if kind=='RECT' or kind=='Rect' or kind=='RECT[1]' then
        local r={Left=0,Top=0,Right=0,Bottom=0}
        if initial then for i,k in ipairs({'Left','Top','Right','Bottom'}) do r[k]=initial[k] or initial[i] or 0 end end
        return kind=='RECT[1]' and {[0]=r} or r
    end
    if kind=='Point' then return {X=initial and (initial.X or initial[1]) or 0,Y=initial and (initial.Y or initial[2]) or 0} end
    if kind=='ObjectFlags' or kind=='DrawFlags' or kind=='DrawFlags_t' or kind=='Flags_t' or kind=='CollisionFlags_t' or kind=='SpecialFlags_t' then local bits=kind=='SpecialFlags_t' and SpecialFlags or kind=='CollisionFlags_t' and CollisionFlags or (kind=='DrawFlags' or kind=='DrawFlags_t') and DrawFlags or Flags;local v=type(initial)=='table' and initial.flags or initial;local state={flags=v or 0};return setmetatable(state,{__index=function(t,k)local b=bits[k];if not b then return nil end;return bit.band(t.flags,b)~=0 end,__newindex=function(t,k,v)local b=bits[k];if not b or type(v)~='boolean' then return end;t.flags=v and bit.bor(t.flags,b) or bit.band(t.flags,bit.bnot(b)) end}) end
    local n=kind:match('^char%[(%d+)%]$') or kind:match('^int%[(%d+)%]$')
    if n and tonumber(n)<=4096 then local t={};for i=0,tonumber(n)-1 do t[i]=0 end;return t end
    error('NotImplemented: ffi.new '..tostring(kind),2)
end
-- ffi.cast is installed by the finite legacy service registry.
local function denyLibrary(name) error('UnsupportedExecution: Windows DLL/native library '..tostring(name),2) end
ffi.load=denyLibrary
modules.ffi=ffi; shared.ffi=ffi
local function modulePath(name)
    assert(type(name)=='string' and not name:find('[/\\:]') and not name:find('%.%.'),'ModulePath: invalid module')
    return 'MODULES/'..name:gsub('%.','/')..'.LUA'
end
local preload,loading,nativeModules={},{},{}
function _nativeModule(name,path) nativeModules[name:lower()]=path end
local function seeall(env) setmetatable(env,{__index=shared}) end
package=setmetatable({}, {
    __index=function(_,k)
        if k=='loaded' then return modules elseif k=='preload' then return preload elseif k=='seeall' then return seeall
        elseif k=='path' then return 'MODULES/?.lua;MODULES/?/init.lua;LOGICS/?.lua'
        elseif k=='cpath' then return '' elseif k=='loadlib' then return denyLibrary end
    end,
    __newindex=function(_,k) error('NotImplemented: package.'..tostring(k),2) end})
function module(name,...)
    modulePath(name)
    local env=modules[name]
    if type(env)~='table' then env={};modules[name]=env end
    local parts={};for part in name:gmatch('[^%.]+') do table.insert(parts,part) end
    local target=shared
    for i=1,#parts-1 do target[parts[i]]=target[parts[i]] or {};assert(type(target[parts[i]])=='table','ModuleNamespace: '..name);target=target[parts[i]] end
    target[parts[#parts]]=env
    env._M,env._NAME,env._PACKAGE=env,name,name:match('^(.*%.)') or ''
    setfenv(2,env)
    for _,option in ipairs({...}) do option(env) end
end
function require(name)
    if modules[name] then return modules[name] end
    if loading[name] then error('ModuleCycle: '..name,2) end
    local path=modulePath(name)
    local chunk=preload[name] or source(path) or source(path:gsub('%.LUA$','/INIT.LUA')) or source('LOGICS/'..path:sub(9))
    if not chunk then
        local native=nativeModules[name:lower()]
        if native then error('UnsupportedExecution: native Lua module '..name..' at '..native,2) end
        error('ModuleNotFound: '..name..' (expected '..path..')',2)
    end
    loading[name]=true;setfenv(chunk,shared)
    local ok,result=pcall(chunk,name);loading[name]=nil
    if not ok then error(result,2) end
    if result~=nil then modules[name]=result elseif modules[name]==nil then modules[name]=true end
    return modules[name]
end
local levelRects={SpringBoardDefRect=true,TogglePegDefRect=true,ElevatorDefRect=true,CrumblingPegDefRect=true,SteppingStoneDefRect=true,BigElevatorDefRect=true}
local levelFields={LevelNb=true,DeathTileType=true,BreakPlankWidth=true,field_AC=true,SplashY=true,MPSkinnerPosX=true,MPSkinnerPosY=true}
local level=makeProxy({
    __index=function(_,k)
        if k=='SpringBoardAnimationIdle' or k=='SpringBoardAnimationSpring' then return array(0,k,32) end
        if levelRects[k] then return rect(0,k) end
        if levelFields[k] then return host(0,0,k) end
        error('NotImplemented: LevelBasedData.'..tostring(k),2)
    end,
    __newindex=function(_,k,v)
        if levelFields[k] then host(1,0,k,v)
        elseif levelRects[k] then for i,key in ipairs({'Left','Top','Right','Bottom'}) do host(1,0,k..':'..(i-1),v[key] or v[i]) end
        else error('NotImplemented: LevelBasedData.'..tostring(k),2) end
    end})
LevelBasedData=setmetatable({[0]=level},{__index=function() error('NotImplemented: non-active LevelBasedData index',2) end})
-- PData is a finite per-object value view, exposed as _p and PData aliases.
function _start(files)
    local main=source('LOGICS/MAIN.LUA')
    if main then setfenv(main,shared);main() end
    for _,path in ipairs(files) do
        if path:sub(1,7)=='LOGICS/' and path~='LOGICS/MAIN.LUA' then
            local chunk=source(path);local env=setmetatable({}, {__index=shared});setfenv(chunk,env);chunk()
            logics[path:sub(8,-5):gsub('/',':'):lower()]=env
        end
    end
end
function _hook(name) local f=rawget(shared,name);if f then f() end end
local initialized={}
function _forget(h) objects[h]=nil;initialized[h]=nil end
function _dispatch(h,name,event,other)
    local env=logics[name:lower()];if not env then error('LogicNotFound: '..name,2) end
    -- Dormant objects have no Lua lifetime to destroy. Teardown must not
    -- initialize them after the player or their dependencies have been freed.
    if event=='destroy' and not initialized[h] then return end
    local o=object(h);o.Name=name
    local function invoke(callback,...)
        local ok,err=pcall(env[callback],...)
        if not ok then error('object '..name..' (handle '..h..'), callback '..callback..': '..tostring(err),0) end
    end
    if not initialized[h] then initialized[h]=true;if rawget(env,'init') then invoke('init',o) end end
    if event~='init' and rawget(env,event) then invoke(event,o,other~=0 and object(other) or nil) end
    if event=='destroy' then initialized[h]=nil end
end
function _builtin(name) shared[name]=function(o) return host(2,checked(o._handle),name) end;if _legacyRegister then _legacyRegister(name,shared[name]) end end
for _,name in ipairs({'HermitCrab','CrumblingPeg','SpringBoard','Seagull'}) do _builtin(name) end
-- Known portable APIs keep a typed pending error until their native service joins.
for _,name in ipairs({'AND','AniCycle','AniCycleNormal','AniRope','Aquatis','Attempt','BearSailor','BlockClaw','BossStager','BreakPlank','CameraToClaw','CameraToObject','CameraToPoint','Chameleon','ChangeResolution','CheatsUsed','ClawGivePowerup','ClawJump','ClawSound','ClawTakeDamage','ConveyorBelt','CreateGoodie','CreateHUDObject','CreateObject','CrumblingPeg','CustomPowerup','CutThroat','Earthquake','Elevator','ExitLevel','FireBullet','Fish','Flare','FloorSpike','FrontStatue','Game','GetBoss','GetCameraPoint','GetClaw','GetCurrentPalette','GetFirstPalette','GetGameType','GetImage','GetImgStr','GetInput','GetMainPlane','GetMapFolder','GetMusicVolume','GetObject','GetPlane','GetResolution','GetTicks','GetTime','GetTreasuresNb','HermitCrab','Katherine','KeyPressed','KillClaw','LavaGeyser','LavaHand','LavaHandProjectile','LavaMouth','LoopThroughObjects','Marrow','MarrowFloor','Mercat','MessageBox','MultClawSpeed','OR','Officer','PData','PathElevator','PegLeg','PlayMusic','PlaySound','PlayerData','PrivateCast','PunkRat','Rat','Raux','RedTailPirate','RedTailSpikes','RegisterTreasure','RemoveSound','ResetMultiMessage','RobberThief','Seagull','SetBoss','SetBossFightPoint','SetCamera','SetCameraToPointSpeed','SetCatnipJumpHeight','SetClaw','SetClawFallSpeedCap','SetDeathType','SetImgColor','SetImgFlag','SetJordanJumpHeight','SetMusic','SetMusicVolume','SetNormalJumpHeight','SetRespawnPoint','SetRunningJumpHeight','Siren','Soldier','SpringBoard','StartElevator','StartSteppingStone','StopElevator','StopMusic','StopSound','StunClaw','TProjectile','TextOut','TigerGuard','TogglePeg','TogglePeg2','TriggerElevator','UnblockClaw','Wolvington','nRes'}) do
    if rawget(shared,name)==nil then shared[name]=unavailable(name..' (later service pending)') end
end
for _,name in ipairs({'Game','nRes'}) do
    shared[name]=setmetatable({}, {__index=unavailable(name..' (bindings pending)'),__newindex=unavailable(name..' (bindings pending)'),__call=unavailable(name..' (bindings pending)')})
end
-- Session-local descriptors select native services; no host addresses enter Lua.
local planeCache,imageCache,imageNames={},{},setmetatable({}, {__mode='k'})
local function planeInteger(n) assert(type(n)=='number' and n%1==0 and n>=-2147483648 and n<=2147483647,'ValueBounds: plane index');return n end
function _planeImage(name)
    assert(type(name)=='string','ValueType: image name');name=name:upper()
    host(9,0,'Plane:Image:'..name)
    if not imageCache[name] then
        local img=makeProxy({__index=function(_,k) if k=='_imageName' then return name end end,__newindex=function() error('Read-only image handle') end})
        imageCache[name]=img;imageNames[img]=name
    end
    return imageCache[name]
end
local function plane(h)
    if h==0 then return nil end
    if planeCache[h] then return planeCache[h] end
    local prefix=tostring(h)
    local function coords(x,y) return prefix..':'..planeInteger(x)..':'..planeInteger(y) end
    local tileset=makeProxy({__newindex=function(_,i,img)
        local name=imageNames[img];assert(name,'ValueType: image handle')
        host(9,0,'Plane:Tileset:'..prefix..':'..planeInteger(i)..':'..name)
    end,__index=function() error('NotImplemented: tileset read') end})
    local screen=makeProxy({__index=function(_,k) local i=rectIndex[k];assert(i,'ValueBounds: plane screen');return host(9,0,'Plane:Screen:'..prefix..':'..i) end,__newindex=function() error('Read-only plane screen') end})
    local methods={PlaceTile=function(_,x,y,tile) return host(9,0,'Plane:Place:'..coords(x,y),planeInteger(tile)) end,
        GetTile=function(_,x,y) return host(9,0,'Plane:Get:'..coords(x,y)) end}
    local obj=makeProxy({__index=function(_,k) if k=='Tileset' then return tileset elseif k=='ScreenA' then return screen end;return methods[k] or error('NotImplemented: plane field '..tostring(k)) end,__newindex=function() error('Read-only plane descriptor') end})
    planeCache[h]=obj;return obj
end
function GetPlane(name) assert(type(name)=='string','ValueType: plane name');return plane(host(9,0,'Plane:Find:'..name)) end
function GetMainPlane() return plane(host(9,0,'Plane:Main')) end
function _planeCheckCollision(x,y) return host(9,0,'Plane:CheckCollision:'..planeInteger(x)..':'..planeInteger(y)) end
)CLAWLUA"
