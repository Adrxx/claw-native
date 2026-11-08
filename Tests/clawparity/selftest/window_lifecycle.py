"""Explicit first-show profile and derived original default callback transport."""
import ctypes as C
from dataclasses import replace
import hashlib,json,struct,subprocess,sys
from pathlib import Path
from .. import build
from ..env import Env,Halt,WindowShowContract,WindowShowProfile,NativeSourceContext,NativeHost,U32
from ..kernel import STACK_BASE,STACK_SIZE,STACK_TOP,ContextFault
from .source_context import context
from . import window_callbacks as base
SHOW=0x40200c;DEFAULT=0x402010
# Actual synthetic callback records execution and makes an independent physical
# child request before its actual DefWindowProc call. ACTIVATEAPP is handled.
b=bytearray.fromhex('55 89e5 8b450c a340204000 ff0544204000 ff7514 50 ff1508204000 8b450c 83f81c 7400')
branch=len(b)-1
b+=bytes.fromhex('ff7514 ff7510 50 ff7508');defaultpc=base.TARGET+len(b);b+=b'\xff\x15'+struct.pack('<I',DEFAULT)+b'\xeb\x02'
b[branch]=len(b)-(branch+1);b+=bytes.fromhex('31c0 c9 c21000');CALLBACK=bytes(b)
def source(callback=CALLBACK):
    p,w=base.source(callback);sec=p.sections[0];code=bytearray(sec.data)
    end=w.create_site[2]+5
    tail=b'\x6a\x01\x50';showpc=end+len(tail)
    tail+=b'\xff\x15'+struct.pack('<I',SHOW)+b'\xb8\x99\x00\x00\x00\xc3'
    code[end-sec.address:end-sec.address+len(tail)]=tail
    p=replace(p,name='window-lifecycle-synthetic',sections=[replace(sec,data=bytes(code)),p.sections[1]],imports=dict(p.imports,**{}))
    p.imports.update({SHOW:'USER32.dll!ShowWindow',DEFAULT:'USER32.dll!DefWindowProcA'})
    return p,w,WindowShowContract(w,(SHOW,showpc,showpc+6),((DEFAULT,base.TARGET+callback.index(b'\xff\x15'+struct.pack('<I',DEFAULT)),base.TARGET+callback.index(b'\xff\x15'+struct.pack('<I',DEFAULT))+6),))
def environment(profile=WindowShowProfile((0,0,640,480)),show_change=None,default_change=None,halt=0,callback=CALLBACK):
    p,w,c=source(callback);e=Env(p);saved=[];frames=[]
    e.fixture(base.REG,'stdcall',1,lambda env,call:env.register_window_class(call,0x1234))
    def create(env,call):
        with env.window_operation(call,0x99) as l:
            for msg,ptr in ((0x24,l.minmax_info),(0x81,l.create_struct),(0x83,l.window_rect),(1,l.create_struct)):
                env.invoke_window_callback(call,l,msg,0,ptr)
        return 0x99
    e.fixture(base.CREATE,'stdcall',12,create)
    def nested(env,call):
        if e._window_callback_lineage:
            frames.append((call.arguments[0],call.stack_pointer,e._window_callback_lineage[-1]['scope']['request'].stack_pointer))
            if halt==call.arguments[0]:raise Halt('lifecycle deepest physical')
        return 0
    e.fixture(base.NESTED,'stdcall',2,nested)
    def default(env,call):
        if not e._window_callback_lineage:return int(call.arguments[1]==0x81)
        if default_change:return default_change(env,call,saved)
        with env.window_default(call) as l:
            saved.append((call,l))
            for args in env.window_messages(call,l):env.invoke_window_message(call,l,*args)
        return int(call.arguments[1]==0x86)
    e.fixture(DEFAULT,'stdcall',4,default)
    def show(env,call):
        if show_change:return show_change(env,call,saved)
        with env.window_show(call,profile) as l:
            saved.append((call,l))
            for args in env.window_messages(call,l):env.invoke_window_message(call,l,*args)
        return 0
    e.fixture(SHOW,'stdcall',2,show);e.window_callback(w);e.window_show_callback(c)
    e.source_callees[0x401000]=dict(kind='whole',convention='cdecl',argc=0,returns='u32',source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
    e._initial['stack'][:]=bytes(range(256))*(STACK_SIZE//256);e._freeze();return e,saved,frames

def entry(flavor):
    lib=C.CDLL(str(build.library('window-lifecycle-selftest',[Path(__file__).with_name('window_lifecycle_module.cpp')],flavor)))
    f=lib.claw_window_lifecycle_entry;f.argtypes=[U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)];f.restype=U32;return f
run=base.run

def checks(flavor='O2'):
    f=entry(flavor);found={}
    profiles=(WindowShowProfile((0,0,640,480)),WindowShowProfile((10,-20,320,240),0x40),WindowShowProfile((0,0,640,480),0x63))
    for pi,p in enumerate(profiles):
      messages=(0x46,0x47,0x1c,0x86,6,7) if pi==0 else (0x46,0x83,0x47,5,3,0x1c,0x86,6,7) if pi==1 else (0x46,0x83,0x47,0x1c,0x86,6,7)
      for halt in (0,*messages):
       for route in ('native','bridge'):
        e,saved,frames=environment(p,halt=halt);fn=0x401300 if route=='bridge' else 0x401000
        n=context(fn,head=STACK_TOP+0x100);o=NativeSourceContext.from_buffer_copy(n)
        a=run(e,f,route,n);stack=bytes(e._stack);history=list(e.window_history);records=list(e.callback_executions);native_frames=list(frames)
        frames.clear();b=run(e,f,'original',o) if route=='native' else e.run_original_context(fn,o,source_return_pc=0x401700)
        key=f'{pi}_{halt:x}_{route}'
        found[key+'_memory']=not a.errors and not b.errors and a.heap==b.heap and a.image==b.image and a.spans==b.spans and a.freed==b.freed and stack==e.machine.read(STACK_BASE,STACK_SIZE)
        found[key+'_events']=a.events==b.events and records==e.callback_executions and history==e.window_history and native_frames==frames
        found[key+'_cpu']=(a.halted and b.halted and a.source_stop==b.source_stop and a.source_stop['function']==base.NESTED) if halt else a.completed and b.completed and bytes(n)==bytes(o) and a.eax==0x99
        found[key+'_lineage']=all(child<parent for msg,child,parent in frames) and (halt or not e._window_callback_lineage) and e.machine.maximum_active_emulations==1
        found[key+'_retirement']=not e._window_show_pending and not e._window_message_sessions and not e._window_handles and not e.machine._physical_pump
        if not all(v for k,v in found.items() if k.startswith(key+'_')):print(key,[str(x) for x in a.errors],[str(x) for x in b.errors],file=sys.stderr)
    found.update(negative_checks(f));found.update(extra_checks(f));return found

def negative_checks(f):
    found={}
    def first(e,c,l):return e.invoke_window_message(c,l,*e.window_messages(c,l)[0])
    attacks={
      'copy_call':lambda e,c,l:first(e,replace(c),l),'copy_lease':lambda e,c,l:first(e,c,replace(l)),
      'generation':lambda e,c,l:(setattr(e,'_callback_generation',object()),first(e,c,l))[1],
      'handle':lambda e,c,l:first(e,c,replace(l,hwnd=0x98)),
      'active_code':lambda e,c,l:(e.write(base.TARGET,b'\x90'),first(e,c,l))[1],
      'machine_code':lambda e,c,l:(e.machine.write(base.TARGET,b'\x90'),first(e,c,l))[1],
      'show_call':lambda e,c,l:(e.write(source()[2].show_site[1],b'\x90'),first(e,c,l))[1],
      'default_call':lambda e,c,l:(e.write(defaultpc,b'\x90'),first(e,c,l))[1],
      'frame':lambda e,c,l:(e.put(c.stack_pointer+4,0x98),first(e,c,l))[1],
      'cpu':lambda e,c,l:(setattr(c.source_context,'ebp',1),first(e,c,l))[1],
      'program':lambda e,c,l:(setattr(e,'program',replace(e.program)),first(e,c,l))[1],
      'no_registration':lambda e,c,l:(e._window_classes.clear(),first(e,c,l))[1],
      'no_handle':lambda e,c,l:(e._window_handles.clear(),first(e,c,l))[1],
      'message':lambda e,c,l:e.invoke_window_message(c,l,0x18,1,0),
      'pointer':lambda e,c,l:e.invoke_window_message(c,l,0x46,0,0),
      'windowpos':lambda e,c,l:(e.put(e.window_messages(c,l)[0][2],0x98),first(e,c,l))[1],
      'retired_transient':lambda e,c,l:(e.release(e.window_messages(c,l)[0][2]),first(e,c,l))[1],
    }
    for name,attack in attacks.items():
      for route in ('original','native','bridge'):
        def show(e,c,saved):
            with e.window_show(c,WindowShowProfile((0,0,640,480))) as l:return attack(e,c,l)
        e,_,_=environment(show_change=show);out=run(e,f,route)
        found[name+'_'+route]=bool(out.errors) and not out.completed and len(e.callback_executions)==4
    for profile in (WindowShowProfile((1,0,640,480)),WindowShowProfile((0,0,320,240)),WindowShowProfile((0,0,640,480),0x53),WindowShowProfile((0,0,640,480),0),WindowShowProfile((0,0,65536,480)),replace(WindowShowProfile((0,0,640,480)),rect=[0,0,640,480])):
      e,_,_=environment(profile);out=run(e,f,'original');found['profile_'+repr(profile)]=bool(out.errors) and len(e.callback_executions)==4
    for route in ('original','native','bridge'):
      for name in ('missing_show','empty_show','wrong_return','retired_show','repeat_show','default_copy','missing_children','wrong_child','outer_cpu','default_twice'):
        def show(e,c,saved):
            if name=='missing_show':return 0
            with e.window_show(c,WindowShowProfile((1,2,320,240),0x40)) as l:
                saved.append((c,l))
                if name!='empty_show':
                    for args in e.window_messages(c,l):e.invoke_window_message(c,l,*args)
            if name=='retired_show':return first(e,c,l)
            if name=='repeat_show':
                with e.window_show(c,WindowShowProfile((0,0,640,480))):pass
            return 1 if name=='wrong_return' else 0
        def default(e,c,saved):
            if name=='default_copy':c=replace(c)
            with e.window_default(c) as l:
                if name=='default_twice':
                    with e.window_default(c):pass
                for args in e.window_messages(c,l):
                    if name=='missing_children':break
                    if name=='wrong_child':args=(0x18,0,0)
                    e.invoke_window_message(saved[0][0] if name=='outer_cpu' else c,l,*args)
            return int(c.arguments[1]==0x86)
        e,_,_=environment(show_change=show,default_change=default);out=run(e,f,route)
        found[name+'_'+route]=bool(out.errors) and not out.completed
      for action in ('swallow','write','release','return'):
        def show(e,c,saved):
            with e.window_show(c,WindowShowProfile((1,2,320,240),0x40)) as l:
                try:
                    for args in e.window_messages(c,l):e.invoke_window_message(c,l,*args)
                except Halt:
                    if action=='write':e.put(0x402050,0xbeef)
                    if action=='release':e.release(e._window_message_sessions[-1]['wp'])
                    if action=='return':return 0
            return 0
        e,_,_=environment(show_change=show,halt=5);out=run(e,f,route)
        found['deep_'+action+'_'+route]=out.halted and not out.errors and out.source_stop['function']==base.NESTED and any(r['arguments'][1]==5 and not r['returned'] for r in e.callback_executions) and e.get(0x402050)==0x99 and not any(x[0]=='shown' for x in e.window_history)
    return found

def extra_checks(f):
    found={}
    profile=WindowShowProfile((10,-20,320,240),0x40)
    def faulty(code):
        # Execute malformed behavior only in SIZE, below original47/default.
        return CALLBACK[:3]+b'\x83\x7d\x0c\x05\x75'+bytes([len(code)])+code+CALLBACK[3:]
    for route in ('original','native','bridge'):
      for name,code in {
          'ret':bytes.fromhex('c9c21400'), 'nonvolatile':bytes.fromhex('43c9c21000'),
          'fs':bytes.fromhex('64c70500000000 ffffffff c9c21000'),
          'parent_FS':bytes.fromhex('64a100000000 c70000000000 c9c21000'),
          'parent_frame':bytes.fromhex('c74554 efbeadde c9c21000'),
          'jmp_token':bytes.fromhex('c9 83c414 b800007200 ffe0'),
          'bad_read':bytes.fromhex('a100000000c9c21000'),'budget':bytes.fromhex('ebfe')}.items():
        e,_,_=environment(profile,callback=faulty(code));e.maximum_operations=2000
        out=run(e,f,route);found['nested_'+name+'_'+route]=bool(out.errors) and not out.completed and not out.halted and not any(x[0]=='shown' for x in e.window_history) and len(e.callback_executions)>4
      e,_,_=environment(profile,callback=faulty(bytes.fromhex('ebfe')));e.callback_timeout_seconds=.01
      out=run(e,f,route);found['nested_deadline_'+route]=bool(out.errors) and 'deadline' in str(out.errors[0])
      e,_,_=environment(profile)
      def hook(m,pc):
          if e._window_callback_lineage and e._window_callback_lineage[-1]['arguments'][1]==5:raise RuntimeError('nested callback observer')
      e.machine.observe(base.TARGET,hook)
      try:out=run(e,f,route);ok=bool(out.errors)
      except RuntimeError as x:ok=str(x)=='nested callback observer'
      found['nested_hook_'+route]=ok and not e.machine._physical_pump and not e._window_callback_lineage
      e,saved,_=environment(profile);out=run(e,f,route);old=saved[0]
      def stale(state,call):return state.invoke_window_message(call,old[1],0x46,0,0)
      e.override(SHOW,stale);out=run(e,f,route)
      found['cross_run_'+route]=bool(out.errors) and len(e.callback_executions)==4
      other,oldleases,_=environment(profile);run(other,f,'original');old=oldleases[0]
      def cross(state,call):return state.invoke_window_message(call,old[1],0x46,0,0)
      e,_,_=environment(profile);e.override(SHOW,cross);out=run(e,f,route)
      found['cross_VM_'+route]=bool(out.errors) and len(e.callback_executions)==4
      for action in ('swallow','write','continue'):
        def default(e,c,saved):
            with e.window_default(c) as l:
                for args in e.window_messages(c,l):
                    try:e.invoke_window_message(c,replace(l),*args)
                    except ContextFault:
                        if action=='write':e.put(0x402050,0xbeef)
                        if action=='continue':e.invoke_window_message(c,l,*args)
            return int(c.arguments[1]==0x86)
        e,_,_=environment(profile,default_change=default);out=run(e,f,route)
        found['fault_latch_'+action+'_'+route]=bool(out.errors) and not out.completed and e.get(0x402050)==0x99 and not any(x[0]=='shown' for x in e.window_history)
    # Independent flag gating; the active first-show profile does not mask children.
    for p,expected in ((WindowShowProfile((0,0,320,240),0x42),(5,7)),(WindowShowProfile((3,4,640,480),0x41),(3,7))):
        e,_,_=environment(p);out=run(e,f,'original');children=tuple(x['arguments'][1] for x in e.callback_executions if x['arguments'][1] in (3,5,7))
        found['flags_'+str(p.flags)]=out.completed and not out.errors and children==expected
    # A source handler consumes47. No physical default request means no invented
    # SIZE/MOVE dispatch; activation still derives SETFOCUS from its real default.
    handled=CALLBACK.replace(bytes.fromhex('83f81c'),bytes.fromhex('83f847'))
    e,_,_=environment(profile,callback=handled)
    # ACTIVATEAPP now reaches its declared leaf default, which is supported.
    out=run(e,f,'original');found['handled47_no_fabricated_children']=out.completed and not out.errors and not any(x['arguments'][1] in (3,5) for x in e.callback_executions) and any(x['arguments'][1]==7 for x in e.callback_executions)
    p,w,c=source()
    for name,change in {'list_sites':dict(default_sites=list(c.default_sites)),'bad_show':dict(show_site=(SHOW,0x401000,0x401006)),'copy_window':dict(window=replace(w)), 'empty_defaults':dict(default_sites=()),'duplicate_defaults':dict(default_sites=c.default_sites*2)}.items():
        e=Env(p);e.fixture(base.REG,'stdcall',1,0);e.fixture(base.CREATE,'stdcall',12,0);e.fixture(SHOW,'stdcall',2,0);e.fixture(DEFAULT,'stdcall',4,0);e.window_callback(w)
        try:e.window_show_callback(replace(c,**change));ok=False
        except ContextFault:ok=True
        found['declaration_'+name]=ok
    return found

def sanitized_checks():
    command,env=build.sanitized_python()
    if command is None:return {'passed':False,'detail':'sanitizer unavailable'}
    child=subprocess.run(command+['-m',__name__,'--sanitize'],env=env,capture_output=True,text=True,timeout=180)
    try:result=json.loads(child.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):result={}
    return dict(result,passed=child.returncode==0 and result.get('failed')==[],returncode=child.returncode,stderr=child.stderr[-4000:])
if __name__=='__main__':
    result=checks('sanitize' if '--sanitize' in sys.argv else 'O0' if '--O0' in sys.argv else 'O2');print(json.dumps({'checked':len(result),'failed':[k for k,v in result.items() if not v]}));raise SystemExit(not all(result.values()))
