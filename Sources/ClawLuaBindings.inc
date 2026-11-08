R"CLAWLUA(
-- Finite legacy views. Descriptor identities stay private; numeric addresses
-- select a service and can never become a pointer into the process.
local views=setmetatable({}, {__mode='k'})
local view
view=function(name,h,kind)
    local p
    p=makeProxy({__index=function(_,i)
        assert(type(i)=='number' and i%1==0,'ValueBounds: legacy index')
        if name=='SoundHandle' and i==4 then return p end
        if name=='Game' and i==10 then return view('SoundManager') end
        return host(10,h or 0,name..':'..i)
    end,__newindex=function(_,i,v)
        assert(type(i)=='number' and i%1==0,'ValueBounds: legacy index')
        host(11,h or 0,name..':'..i,v)
    end})
    views[p]={name=name,h=h or 0,kind=kind};return p
end
function _legacyObjectView(h,kind) return view(kind,h) end
function Game(...) local p=view('Game');for _,i in ipairs({...}) do p=p[i] end;return p end
local buffers={ [0x522738]='DeathSound',[0x522170]='BulletImage',
 [0x52AB6C]='BossName',[0x52AB44]='DefeatVoice',[0x52AB30]='StageClaw',[0x52AB1C]='StageBoss'}
local words={ [0x535928]='Clock',[0x52ABF0]='BossFrame',[0x53B0F8]='PowerupMusic',
 [0x530990]='SoundVolume',[0x429BAF]='ViewportIncreaseLimit',[0x429B6F]='ViewportDecreaseLimit',
 [0x41DAC9]='BulletCollision',[0x41DE0B]='BulletHit',[0x41DA88]='BulletRight',[0x41DA96]='BulletLeft'}
local function descriptor(p,name)
    local d=views[p];assert(d and (not name or d.name==name),'ValueType: legacy '..(name or 'view'));return d
end
local function sound(name) local p=view('SoundHandle',0);views[p].resource=name;return p end
local function soundName(p) return descriptor(p).resource or error('ValueType: audio handle') end
local functions={}
functions[0x45A4E0]=function(manager,name) descriptor(manager,'SoundManager');if host(12,0,'Audio:FindSound:'..name)==0 then return nil end;return sound(name) end
functions[0x4B34D0]=function(p) return host(12,0,'Audio:StopSound:'..soundName(p)) end
functions[0x421BB0]=function(p,volume,pan,pitch,loop) return host(12,0,'Audio:PlaySound:'..volume..':'..pan..':'..pitch..':'..loop..':'..soundName(p)) end
functions[0x4B4E80]=function(manager,name) descriptor(manager,'MusicManager');if host(12,0,'Audio:FindMusic:'..name)==0 then return nil end;local p=view('MusicHandle');views[p].resource=name;return p end
functions[0x4B55B0]=function(p) return host(12,0,'Audio:MusicState:'..soundName(p)) end
local musicStop=function(p) return host(12,0,'Audio:StopMusic:'..soundName(p)) end
functions[0x44D060]=function(p) local d=descriptor(p,'private');return host(12,d.h,'CrabFall') end
functions[0x44C550]=function(p,bomber) local d=descriptor(p,'private');return host(12,d.h,'CrabType',bomber) end
functions[0x420EE0]=function(kind,ms) return host(9,0,'GivePowerup:'..kind,ms) end
functions[0x418D20]=function(o,v,p) return host(12,checked(o._handle),'Drown') end
functions[0x41EAC0]=function(h) return host(12,checked(h),'ProjectileInit') end
functions[0x4756D0]=function(h) return host(12,checked(h),'ProjectileMove')~=0 end
functions[0x4D52F0]=function(manager,_,x,y,z,logic,flags)
    descriptor(manager,'HUDManager');assert(logic==0x520624,'NotImplemented: legacy HUD logic');return CreateHUDObject{Logic='DoNothing',X=x,Y=y,Z=z,flags=flags}
end
local functionTypes={
 [0x45A4E0]='int*(*__thiscall)(int,char*)',[0x4B34D0]='int(*__thiscall)(int)',
 [0x421BB0]='int(*__thiscall)(int*,int,int,int,int)',[0x4B4E80]='int(*__thiscall)(int,char*)',
 [0x4B55B0]='int(*__thiscall)(int)',[0x44D060]='int(*__thiscall)(int*)',
 [0x44C550]='int(*__thiscall)(int*,int)',[0x420EE0]='int(*)(int,int)',
 [0x418D20]='int(*)(ObjectA*,ObjectV*,PData*)',[0x41EAC0]='int(*__cdecl)(int)',
 [0x4756D0]='int(*__cdecl)(int)',[0x4D52F0]='ObjectA*(*__thiscall)(ObjectA*,int,int,int,int,int,int)'}
local logicRefs={}
function _legacyRegister(name,f) logicRefs[host(13,0,name)]=f end
function _legacyLogic(h) return logicRefs[host(10,h,'LogicRef:4')] or methods.Logic end
local realCast=function(kind,p)
    local t=kind:gsub('%s',''):gsub('const','')
    if t:find('%(') then
        if type(p)=='function' and p==musicStop and t==functionTypes[0x4B55B0] then return p end
        local f=functions[p];if f and functionTypes[p]==t then return f end
        error('NotImplemented: legacy call '..tostring(p)..' as '..kind,2)
    end
    if t=='ObjectA*' and p==0 then return nil end
    local d=views[p]
    if d then
        if t=='int*' or t=='double*' then
            if d.name=='private' then return view(t=='int*' and 'PrivateInt' or 'PrivateDouble',d.h) end
            return p
        end
        if t=='int**' and d.name=='MusicHandle' then return {[0]={[8]=musicStop}} end
    end
    if t=='int*' and type(p)=='userdata' then return view('LogicRef',checked(p._handle)) end
    if (t=='char*' and buffers[p]) then return view(buffers[p],0,'char') end
    if ((t=='int*' and words[p] and p~=0x429BAF and p~=0x429B6F) or (t=='char*' and (p==0x429BAF or p==0x429B6F))) then return view(words[p]) end
    if t=='Rect*' and p==0x535840 then
        local r=makeProxy({__index=function(_,k) local i=rectIndex[k];assert(i,'ValueBounds: viewport');return host(10,0,'Viewport:'..i) end,
            __newindex=function() error('ValueType: read-only viewport') end})
        return {[0]=r}
    end
    error('NotImplemented: legacy cast '..kind..' at '..tostring(p),2)
end
ffi.cast=realCast
function ffi.copy(dest,text,n)
    assert(type(text)=='string','ValueType: ffi.copy source');n=n or #text+1
    assert(n>=0 and n<=4096 and n%1==0,'ValueBounds: ffi.copy size')
    for i=0,n-1 do dest[i]=text:byte(i+1) or 0 end
    return dest
end
function ffi.string(p,n)
    if type(p)=='string' then return n and p:sub(1,n) or p end
    local bytes={};assert(not n or n>=0 and n<=4096 and n%1==0,'ValueBounds: ffi.string size')
    for i=0,(n or 4096)-1 do local c=p[i];if not n and c==0 then return table.concat(bytes) end;bytes[#bytes+1]=string.char(c%256) end
    if n then return table.concat(bytes) end;error('ValueBounds: unterminated ffi.string')
end
function PrivateCast(v,kind,address,index) ffi.cast(kind,address)[index or 0]=v end
function PrivateCopyCast(text,address,force) return ffi.copy(ffi.cast('char*',address),text) end
function PrivateChamAdd(address) error('UnsupportedExecution: PrivateChamAdd unknown x86 patch at '..tostring(address),2) end
-- Sound handles expose the historical secondary handle without exposing storage.
local originalNew=ffi.new
function ffi.new(kind,initial)
    local element,n=kind:match('^(%a+)%[(%d+)%]$');n=tonumber(n)
    if (element=='char' or element=='int') and n then
        assert(n<=4096,'ValueBounds: ffi.new count')
        local values={};for i=0,n-1 do values[i]=type(initial)=='string' and (initial:byte(i+1) or 0) or type(initial)=='table' and (initial[i+1] or 0) or 0 end
        local function index(i) assert(type(i)=='number' and i%1==0 and i>=0 and i<n,'ValueBounds: buffer index') end
        return makeProxy({__index=function(_,i) index(i);return values[i] end,__newindex=function(_,i,v) index(i);assert(type(v)=='number' and v%1==0,'ValueType: buffer element');values[i]=element=='char' and v%256 or bit.tobit(v) end})
    end
    return originalNew(kind,initial)
end
DeathType={Spikes=0,Goo=1}
function _legacyImageName(image)
    assert(type(image)=='table' and image._imageObject,'ValueType: image handle')
    local h=checked(image._imageObject);local bytes={}
    for i=0,127 do local b=host(8,h,'ImageName:'..i);if b==0 then return table.concat(bytes) end;bytes[#bytes+1]=string.char(b) end
    error('ValueBounds: image name')
end
GetImgStr=_legacyImageName
-- The result/application table has only the observed single-player services.
local sceneView=view('Scene');local cheatView=view('Cheats');local musicView=view('MusicManager')
local root=makeProxy({__index=function(_,i)
    if i==11 then return sceneView elseif i==18 then return cheatView elseif i==20 then return musicView end
    return host(10,0,'Result:'..tostring(i))
end,__newindex=function(_,i,v) return host(11,0,'Result:'..tostring(i),v) end})
_nResult={[0]=root}
function nRes(...) local p=root;for _,i in ipairs({...}) do p=p[i] end;return p end
function snRes(v,...) local a={...};assert(#a>0,'ValueType: snRes');local p=root;for i=1,#a-1 do p=p[a[i]] end;p[a[#a]]=v end
function CheatsUsed() return cheatView[74]~=0 end
function _bindingFirePistol() return host(9,0,'FirePistolCheck') end
function SetMusic(name) return host(12,0,'Audio:SetMusic:'..name) end
PlayMusic=SetMusic
function StopMusic(name) return host(12,0,'Audio:StopMusic:'..(name or 'LEVEL')) end
function SetBossFightPoint(x,y) sceneView[17]=x;sceneView[18]=y end
-- Named release aliases select the same finite services as address views.
local singlePlayerCurses=makeProxy({__index=function(_,i) assert(i==0,'ValueBounds: EnableCurses');return 0 end,__newindex=function() error('Single-player EnableCurses is read-only') end})
local cheatSetting=makeProxy({__index=function(_,i) assert(i==0,'ValueBounds: Cheats');return cheatView[74] end,__newindex=function(_,i,v) assert(i==0,'ValueBounds: Cheats');cheatView[74]=v end})
local namedExe={EnableCurses=singlePlayerCurses,Cheats=cheatSetting,DisablePowerupMusic=view('PowerupMusic'),_GetSoundA=functions[0x45A4E0],_StopSound=functions[0x4B34D0]}
mdl_exe=makeProxy({__index=function(_,name) return namedExe[name] or error('NotImplemented: mdl_exe.'..tostring(name)) end,__newindex=function() error('Native service namespace is read-only') end})
local function readSetting(name,read)
    return makeProxy({__index=function(_,i) assert(i==0,'ValueBounds: '..name);return read() end,__newindex=function() error('Read-only setting: '..name) end})
end
_CurrentPowerup=readSetting('CurrentPowerup',GetCurrentPowerup)
_PowerupTime=readSetting('PowerupTime',GetCurrentPowerupTime)
MULTI_STATS=view('HUDManager')
)CLAWLUA"
