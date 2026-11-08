"""Lua interpreter contract checks; native gameplay evidence is checked separately."""
import ctypes
import json
from pathlib import Path
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def interpreter(out):
    while subprocess.run(['pgrep','-f','^/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -project Claw.xcodeproj'],capture_output=True).returncode == 0:
        time.sleep(10)
    while float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]) >= 16:
        time.sleep(10)
    # Use the same embedded interpreter/host as the app, with a deliberately
    # synthetic service fixture. This fixture never claims native gameplay.
    library = out/'lua-host.dylib'
    sources = sorted((ROOT/'Sources').glob('ClawLua51_*.cpp'))+[ROOT/'Sources/ClawLuaHost.cpp']
    subprocess.run(['xcrun','clang++','-std=c++17','-O1','-dynamiclib',*[str(p) for p in sources],'-o',str(library)],check=True,capture_output=True)
    lib = ctypes.CDLL(str(library))
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_uint32,ctypes.c_char_p,ctypes.c_double,ctypes.POINTER(ctypes.c_double),ctypes.c_void_p,ctypes.c_size_t)
    live = {1,2,3,4,5}
    fields = {}
    calls = []
    pending_destroy = []
    @callback_type
    def callback(_,op,h,key,v,result,error,capacity):
        key = key.decode()
        if (h and h not in live) or (op==2 and key not in ['HermitCrab','CrumblingPeg','SpringBoard','Seagull']):
            msg = ('StaleHandle' if h not in live else 'NotImplemented').encode()+b'\0'
            ctypes.memmove(error,msg,min(len(msg),capacity));return 0
        if op==0: result[0] = fields.get((h,key),0)
        elif op==1: fields[h,key] = v
        elif op==2: calls.append((h,key))
        elif op==3:
            result[0] = max(live|{0})+1;live.add(int(result[0]))
        elif op==4: pending_destroy.append(h)
        elif op==7: result[0] = 1
        elif op==9 and key=='ID': result[0] = v if v in live else 0
        elif op==9:
            msg=b'NotImplemented: synthetic host service\0'
            ctypes.memmove(error,msg,min(len(msg),capacity));return 0
        return 1
    lib.claw_lua_create.argtypes=[ctypes.c_void_p,callback_type];lib.claw_lua_create.restype=ctypes.c_void_p
    vm = lib.claw_lua_create(None,callback)
    assert vm, 'interpreter bootstrap'
    for name in ['claw_lua_start','claw_lua_eval','claw_lua_error','claw_lua_hook','claw_lua_close','claw_lua_file','claw_lua_object']:
        getattr(lib,name).restype = ctypes.c_char_p if name=='claw_lua_error' else ctypes.c_int
    lib.claw_lua_error.argtypes=[ctypes.c_void_p]
    lib.claw_lua_start.argtypes=[ctypes.c_void_p]
    lib.claw_lua_close.argtypes=[ctypes.c_void_p]
    lib.claw_lua_eval.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
    lib.claw_lua_hook.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
    lib.claw_lua_object.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint32]
    lib.claw_lua_file.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t]
    def error(): return lib.claw_lua_error(vm).decode()
    def file(path,text):
        text=text.encode() if isinstance(text,str) else text
        assert lib.claw_lua_file(vm,path.upper().encode(),text,len(text)),error()
    def run(text): assert lib.claw_lua_eval(vm,text.encode()),error()
    def dispatch(h,name,event): assert lib.claw_lua_object(vm,h,name.encode(),event.encode(),0),error()
    marks = {}
    try:
        for archive in ['pixelcove','las_almenas']:
            with zipfile.ZipFile(ROOT/f'work/custom-levels/crazyhook-sample/{archive}.zip') as z:
                for p in z.namelist():
                    if '/LOGICS/' in p.upper() and p.lower().endswith('.lua') and not p.endswith('/.lua') and not p.lower().endswith('/main.lua'):
                        file(p.split('/',1)[1],z.read(p))
        with zipfile.ZipFile(ROOT/'work/custom-levels/crazyhook-sample/pre2claw.zip') as z:
            core=next(p for p in z.namelist() if p.rsplit('/',1)[-1].lower()=='crazyhook.lua')
            file('CRAZYHOOK.LUA',z.read(core))
        file('MODULES/binary.lua',b'\x1bLua synthetic rejected bytecode')
        file('LOGICS/main.lua', '''order={}; shared=40
function OnMapLoad() table.insert(order,'map1') end
function OnMapLoad2() table.insert(order,'map2') end
function OnGameplay() table.insert(order,'game') end
function OnLevelEnd() table.insert(order,'end') end''')
        file('LOGICS/Nested/Test.lua', '''local count=0
function init(self) self.value=shared+2;table.insert(order,'init') end
function main(self) count=count+1;self.count=count;table.insert(order,'main') end
function hit(self) self.Health=self.Health-1;table.insert(order,'hit') end
function attack(self) table.insert(order,'attack') end
function destroy(self) table.insert(order,'destroy') end''')
        file('LOGICS/Dormant.lua',"function init(self) error('dormant init during destruction') end;function destroy(self) error('dormant destroy without initialization') end")
        file('MODULES/localmod.lua','local hidden=7; return {value=hidden}')
        file('MODULES/classic.lua',"module('classic',package.seeall);value=23;function answer() return value end")
        file('MODULES/folder/INIT.lua','return {value=29}')
        file('MODULES/cycle.lua',"return require('cycle')")
        assert lib.claw_lua_start(vm),error()
        for name in ['OnMapLoad','OnMapLoad2','OnGameplay']:
            assert lib.claw_lua_hook(vm,name.encode()),error()
        dispatch(1,'Crab1','main')
        dispatch(2,'CrumblePeg','main')
        dispatch(3,'SpringBox','main')
        dispatch(4,'Seagull','main')
        assert calls == [(1,'HermitCrab'),(2,'CrumblingPeg'),(3,'SpringBoard'),(4,'Seagull')],calls
        assert [fields[1,f'MoveRect:{i}'] for i in range(4)] == [-28,-18,26,28]
        assert [fields[1,f'HitRect:{i}'] for i in range(4)] == [-16,-14,16,24]
        assert bytes(int(fields[0,f'SpringBoardAnimationIdle:{i}']) for i in range(21)) == b'LEVEL_SPRINGBOX_IDLE\0'
        marks['unchanged_sample_callbacks'] = dict(calls=calls,crab_rectangles=True,level_animation_name=True,host='synthetic service fixture, not canonical game logic')
        for event in ['main','main','hit','attack','destroy']: dispatch(5,'nested:test',event)
        assert lib.claw_lua_hook(vm,b'OnLevelEnd'),error()
        run("assert(table.concat(order,',')=='map1,map2,game,init,main,main,hit,attack,destroy,end');assert(GetObject(5).value==42 and GetObject(5).count==2)")
        dispatch(5,'nested:test','destroy')
        run("assert(table.concat(order,',')=='map1,map2,game,init,main,main,hit,attack,destroy,end')")
        live.add(99);dispatch(99,'dormant','destroy');live.remove(99)
        marks['dormant_and_repeated_destroy_do_not_initialize'] = True
        marks['lifecycle_namespaced_locals_shared_main'] = True
        run("assert(type(GetObject(1))=='userdata');local ok=pcall(function() rawset(GetObject(1),'State',2) end);assert(not ok)")
        run("assert(require('localmod').value==7);assert(require('classic').answer()==23 and classic==require('classic') and require('folder').value==29);local ok,e=pcall(function() require('cycle') end);assert(not ok and e:find('ModuleCycle'));assert(require('bit')==bit);assert(bit.band(255,15)==15 and bit.bnot(0)==-1 and bit.rshift(-1,31)==1);local f=function() return value end;setfenv(f,{value=17});assert(f()==17)")
        run("local ffi=require('ffi');local r=ffi.new('Rect',{-1,-2,3,4});assert(r.Left==-1 and r.Bottom==4);local p=ffi.new('Point',{3,5});assert(p.X==3 and p.Y==5);local f=ffi.new('Flags_t');f.AlwaysActive=true;assert(f.AlwaysActive);local a=ffi.new('int[4]');a[0]=9;assert(a[0]==9)")
        marks['modules_bit_setfenv_ffi_values'] = True
        run("local o=GetObject(2);o.User[0]=37;assert(o._v.UserValue1==37 or o.User[0]==37);o.extra={1,2};assert(o.extra[2]==2)")
        run("staleObject=CreateObject{Logic='CustomLogic',Name='nested:test'};staleObject.State=3;staleObject:Destroy();assert(staleObject.State==3)")
        for h in pending_destroy:
            dispatch(h,'nested:test','destroy');live.remove(h)
        run("local ok,e=pcall(function() return staleObject.State end);assert(not ok and e:find('StaleHandle'))")
        marks['dynamic_creation_destruction_stale_handles'] = True
        run("local o=CreateObject{Logic='DoNothing',X=12,Y=14};assert(type(o.Logic)=='function');o:Logic();o:Destroy()")
        run("local ok,e=pcall(function() require('ffi').cast('int*',123) end);assert(not ok and e:find('NotImplemented'));ok,e=pcall(function() PlaySound('missing') end);assert(not ok and e:find('NotImplemented'));assert(type(io)=='table' and type(io.open)=='function' and io.popen==nil and io.tmpfile==nil and type(os.time)=='function' and os.execute==nil and type(package)=='table' and debug==nil)")
        run("local ok,e=pcall(function() require('binary') end);assert(not ok and e:find('UnsupportedExecution'));ok,e=pcall(function() package.loadlib('x.dll') end);assert(not ok and e:find('UnsupportedExecution'));ok,e=pcall(function() GetObject(4294967297) end);assert(not ok and e:find('ValueType'))")
        assert not lib.claw_lua_eval(vm,b'while true do end') and 'ScriptLimit' in error(),error()
        assert not lib.claw_lua_eval(vm,b"local s=string.rep('a',40*1024*1024)"), 'allocation budget was not enforced'
        run('assert(1+1==2)')
        marks['instruction_and_memory_limits'] = True
        marks['pre2claw_optional_core_excluded'] = core
        marks['unsupported_services_and_no_native_access'] = True
    finally:
        lib.claw_lua_close(vm)
    # A fresh VM must not inherit Lua globals, object tables or module cache.
    vm = lib.claw_lua_create(None,callback)
    try: run("assert(shared==nil and order==nil);assert(type(io)=='table' and type(io.open)=='function' and io.popen==nil and io.tmpfile==nil and type(os.time)=='function' and os.execute==nil)")
    finally: lib.claw_lua_close(vm)
    marks['isolated_session'] = True
    return marks


def lua():
    import fcntl
    import os
    # A coordinator may hold the same lock across a fresh build and this check.
    if os.environ.get('CLAW_BUILD_LOCK_HELD') == '1':
        return check_lua()
    # Use the build's existing process-scoped lock across the interpreter
    # compile and native probes, so queued app builds cannot race this check.
    with (ROOT/'work/.claw-app-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return check_lua()


def check_lua():
    import os
    import shutil
    from real_input import Session, build_helper
    out = ROOT/'work/crazyhook/checks/lua'
    out.mkdir(parents=True,exist_ok=True)
    report_path = out.parent/'lua.json'
    for filename in ['lua-load.json','real-speed.json','native-fault.json']:
        (out/'play'/filename).unlink(missing_ok=True)
    report = dict(group='lua',status='fail',marks={},pending=['Audio playback and later gameplay/binding/presentation services have typed errors until their own tasks implement them'],ipad='Mac Catalyst only; no iPad build or runtime acceptance')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    try:
        report['marks']['interpreter'] = interpreter(out)
        # Import unchanged sample copies; never mutate the downloaded archives.
        unpacked = out/'input';unpacked.mkdir(exist_ok=True)
        custom = out/'Custom';custom.mkdir(exist_ok=True)
        worlds = {}
        for name in ['pixelcove','las_almenas','flying_carpet_ride']:
            folder = unpacked/name;folder.mkdir(exist_ok=True)
            with zipfile.ZipFile(ROOT/f'work/custom-levels/crazyhook-sample/{name}.zip') as z:
                assert all((folder/p).resolve().is_relative_to(folder.resolve()) for p in z.namelist())
                z.extractall(folder)
            world = next(folder.rglob('*.wwd'));worlds[name] = world.name
            shutil.copy2(world,custom/world.name)
            if world.with_suffix('').exists(): shutil.copytree(world.with_suffix(''),custom/world.stem,dirs_exist_ok=True)
        helper = build_helper(ROOT/'work/cheat-codes/post-window-input')
        app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
        play = out/'play';play.mkdir(exist_ok=True)
        session = Session(play,helper=helper)
        def live(): return json.loads((play/'live.json').read_text())
        def tap(code):
            session.post('key',code);session.run(12)
            assert not session.failed(),session.gate()
        def command(text):
            session._command(text);session._gate_wait();session.run(1)
            assert not session.failed(),session.gate()
        def load(name):
            if live().get('menu_page') == 10000: tap(36)
            for _ in range(10):
                if live().get('menu_selected') == 11003:break
                tap(125)
            assert live().get('menu_selected') == 11003,live()
            tap(36)
            assert live().get('custom_dialog'),live()
            index=live()['custom_files'].index(worlds[name])
            for _ in range(index):tap(125)
            tap(36)
            assert not live().get('custom_dialog'),live().get('custom_error')
            assert live().get('state_vtable') == '0x50c264',live()
        def complete():
            for code in [46,35,1,8,32,37,37,16]:tap(code)
            assert session.wait(lambda:live().get('state_vtable')=='0x50c0c4',10),live()
            for _ in range(10):
                if session.wait(lambda:live().get('state_vtable')!='0x50c0c4',12):break
                tap(36)
            assert session.wait(lambda:live().get('menu_page') in (10000,10001),20),live()
        try:
            session.launch(app,{'CLAW_TRACE_DEPTH':'30000'},['--custom-dir',str(custom),'--no-paper-startup','--save-dir',str(play/'saves'),'--settings-dir',str(play/'settings'),'--long-trace','--lua-runtime-check'])
            session.run(60)
            for name,wrappers in [('pixelcove',['Crab1']),('las_almenas',['SpringBox','CrumblePeg','Seagull'])]:
                load(name)
                report['marks'][name]={}
                for wrapper in wrappers:
                    command('lua-place '+wrapper)
                    session.run(10)
                    before = session.mark(name+'-'+wrapper+'-before')
                    session.post('press',124,'down');session.run(20);session.post('press',124,'up')
                    after = session.mark(name+'-'+wrapper+'-after')
                    if name=='pixelcove':
                        assert before['player']['x'] != after['player']['x'],[before['player'],after['player']]
                    evidence=live()['custom_level'];runtime=evidence.get('lua',{})
                    assert not runtime.get('error'),runtime
                    callback = [e for e in runtime['events'] if e.get('name')==wrapper and e.get('callback')=='main']
                    assert callback,(wrapper,runtime)
                    expected={'Crab1':[-16,-14,16,24],'CrumblePeg':[-24,-46,24,64],'Seagull':[-40,-20,40,50],'SpringBox':[-34,-1,40,40]}[wrapper]
                    assert any(e['hit_rect']==expected for e in callback),callback
                    if wrapper=='Crab1': assert any(e['move_rect']==[-28,-18,26,28] for e in callback),callback
                    builtin={'Crab1':'HermitCrab','CrumblePeg':'CrumblingPeg','Seagull':'Seagull','SpringBox':'SpringBoard'}[wrapper]
                    assert any(e.get('builtin')==builtin for e in runtime['events']),runtime
                    if wrapper=='SpringBox':
                        arrays={e['level_array']:e['value'] for e in runtime['events'] if 'level_array' in e}
                        assert arrays=={'SpringBoardAnimationIdle':'LEVEL_SPRINGBOX_IDLE','SpringBoardAnimationSpring':'LEVEL_SPRINGBOX_SPRING'},arrays
                    report['marks'][name][wrapper]=dict(native_callback=callback,player_before=before['player'],player_after=after['player'],fixture=evidence['lua_check_placement'])
                command('lua-values')
                session.run(2)
                command('lua-stale')
                assert live()['custom_level'].get('lua_native_values','').startswith('pass'),live()
                report['marks'][name]['native_values']=live()['custom_level']['lua_native_values']
                report['marks'][name]['runtime']=live()['custom_level']['lua']
                hooks=[e['hook'] for e in live()['custom_level']['lua']['events'] if 'hook' in e]
                assert hooks[:3]==['OnMapLoad','OnMapLoad2','OnGameplay'],hooks
                complete()
                ended=live()['custom_level']
                assert ended.get('unloaded') and any(e.get('hook')=='OnLevelEnd' for e in ended['lua']['events']),ended
                report['marks'][name]['menu_cleanup']=ended
            load('flying_carpet_ride')
            assert 'lua' not in live()['custom_level'],live()['custom_level']
            session.post('press',124,'down');session.run(20);session.post('press',124,'up')
            assert not session.failed(),session.gate()
            complete()
            report['marks']['retail_control_isolation']='Flying Carpet Ride played after both Lua maps; no Lua state mounted'
            report['marks']['confirmed_input_transitions']=session.transitions()
        finally:
            session.close()
            for pattern in ['hud-*.png','frame-*.png']:
                for p in play.glob(pattern):p.unlink()
        report['status']='pass'
    finally:
        if report['status'] != 'pass':
            diagnostics = {}
            for filename in ['lua-load.json','real-speed.json','native-fault.json']:
                path = out/'play'/filename
                if not path.exists(): continue
                value = json.loads(path.read_text())
                if filename == 'real-speed.json':
                    value = {k:value[k] for k in ['status','error','failing_frame'] if k in value}
                if filename == 'native-fault.json':
                    value = {k:value[k] for k in ['address','missing_tile_frames'] if k in value}
                diagnostics[filename] = value
            report['native_failure'] = diagnostics
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report
