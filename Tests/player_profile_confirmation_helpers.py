"""Isolated state13/profile-confirmation oracle; private frozen support output."""
from pathlib import Path
source=Path(__file__).with_name('player_menu_management_helpers.py').read_text()
source=source.replace("WORK=ROOT/'work/player-menu-management-agent'","WORK=ROOT/'work/player-profile-confirmation-agent'")
source=source.replace("'PlayerMenuManagementRuntime','CStringAssignmentRuntime'","'PlayerProfileConfirmationRuntime','PlayerMenuManagementRuntime','CStringAssignmentRuntime'")
source=source.replace('work/application-level-progression-agent/libProgressionFrozenSupport.dylib','work/player-profile-confirmation-agent/libConfirmationFrozenSupport.dylib')
exec(compile(source,str(Path(__file__).with_name('player_menu_management_helpers.py')),'exec'),globals())
CONF_AUTO=BASE+0x2c000;OWNER=BASE+0x2d000;PREVIOUS=BASE+0x2e000;DISPLAY=BASE+0x40000;FRONT=BASE+0x41000;WRAPPER=BASE+0x42000;BITMAP=BASE+0x43000;CURSOR=BASE+0x44000;IMAGE=BASE+0x45000;PREVIOUS_VT=BASE+0x46000
MODE=0x10fe100;FRAME_FN=0x10fe110;POPUP_INIT=0x423840
class ConfirmationContext(C.Structure):_fields_=[('scene',Host),('menu',C.c_void_p),('base',C.c_void_p)]+[(n,U)for n in('automaticToken','composeBase','composeStrings','maximumOperations','fault')]
ConfirmationDependency=C.CFUNCTYPE(U,C.POINTER(ConfirmationContext),C.POINTER(RichCall),C.c_void_p)
cc=ConfirmationContext();cc.menu=C.addressof(mc);cc.automaticToken=CONF_AUTO;cc.maximumOperations=5000000;cc.composeStrings=0
lib.claw_player_profile_confirmation_entry.argtypes=[U,U,UP,U,C.POINTER(ConfirmationContext),ConfirmationDependency,C.c_void_p,UP]
lib.claw_player_profile_confirmation_construct.argtypes=[U,U,C.POINTER(ConfirmationContext),ConfirmationDependency,C.c_void_p,UP]
SIZES.update({CONF_AUTO:4,CONF_AUTO+4:4,CONF_AUTO+8:4,CONF_AUTO+12:8,CONF_AUTO+20:16,CONF_AUTO+36:16,CONF_AUTO+52:16})
CONF_OWN={0x438c40,0x4399d0,0x43a760,0x439480,0x485160,0x4247c0,0x4247e0,0x424800,0x4299a0}
EXTERNAL.update({0x40b5c0:0,0x48f0d0:3,0x42bfd0:0,0x4236c0:2,0x423840:3,0x499ff0:3,0x499e70:2,0x4f6439:0,0x4f6449:1,0x43a720:0,0x45fdd0:0,0x452af0:0,0x4bc4f0:1,0x4bc670:5,0x4cab10:0,0x546d58:2,0x4b9ce0:5,0x546cd0:1,0x4c8da0:6,0x4c7970:1,0x4c79e0:2,MODE:0,FRAME_FN:0})
for vt in(0x50d794,0x50ce74,0x50cc2c,0x50d54c,0x50c9e4,0x50d0bc,0x50d304):EXTERNAL[get(vt)[0]]=1
CDECL.update({0x546d58,0x546cd0})
for i,slot in enumerate((0x546d58,0x546cd0)):
 at=STUB+0x900+i*16;STUBS[at]=slot;IMPORTS[slot]=EXTERNAL[slot];m.write_words(slot,[at]);C.memmove(C.addressof(image)+slot-IS,struct.pack('<I',at),4);u.mem_write(at,b'\xc3')
sourceOriginalSeed=globalSeed=bytes(image[GS-IS:GS-IS+GN])
baseConfCanonical=canonical;baseConfPrepare=prepare;baseConfEffect=effect
previousMode=5;previousAvailable=PREVIOUS;baseResult=1;popupResult=1;captureResult=BITMAP;cursorImage=IMAGE;failure=0

def canonical():
 b=bytearray(baseConfCanonical());b[CONF_AUTO-BASE:CONF_AUTO-BASE+68]=bytes(68)
 if currentRoot==0x485160:b[F-BASE:F-BASE+16]=bytes(16)
 return bytes(b)
def effect(f,t,a):
 if f==0x40b5c0:
  put(t,[0x50b4ec]);
  for off in(4,8,12,24,28,32,36,44,48,52,60,64):put(t+off,[0])
  putBytes(t+76,b'\0');return 0
 if f==0x42bfd0:return previousAvailable
 if f==0x48f0d0:
  put(t+4,[a[0]]);put(t+8,[FRAME]);put(t+12,[SCENE]);return baseResult
 if f==MODE:return previousMode
 if f in(FRAME_FN,0x43a720,0x45fdd0,0x452af0,0x4bc4f0,0x4cab10,0x4c7970):return 0
 if f==0x4f6439:put(t,[ctx.emptyStringToken]);return t
 if f==0x4f6449:
  data=get(a[0])[0];put(t,[data]);put(data-12,[get(data-12)[0]+1]);return t
 if f in(0x4236c0,0x499e70):
  put(t,[0x50bc6c if f==0x4236c0 else 0x50fc64]);put(t+684,[ctx.emptyStringToken]);put(t+688,[ctx.emptyStringToken]);put(t+692,[0]);return t
 if f in(set(get(vt)[0]for vt in(0x50d794,0x50ce74,0x50cc2c,0x50d54c,0x50c9e4,0x50d0bc,0x50d304))):
  assert a==(1,);free(None,t);return t
 if f in(0x423840,0x499ff0):
  # Named CWnd graph-initialization boundary consumes its by-value title;
  # this fixture retains source refcount/lifetime, and does not execute GDI.
  data=a[2];put(data-12,[get(data-12)[0]-1]);put(t+672,[a[0]]);put(t+676,[a[1]]);return popupResult
 if f==0x4bc670:return captureResult
 if f==0x546d58:putBytes(a[0],readBytes(a[1],16));return 1
 if f==0x4b9ce0:return 1
 if f==0x546cd0:put(a[0],[24,35]);return 1
 if f==0x4c8da0:return CURSOR
 if f==0x4c79e0:put(CURSOR+372,[cursorImage]);return 1
 return baseConfEffect(f,t,a)
@ConfirmationDependency
def confirmationDependency(c,e,_):
 q=e.contents
 if q.function in(0x4f63ec,0x4f6428):return appDependency(C.byref(ac),e,None)
 a=tuple(q.arguments[:q.count]);scope=tuple(get(SEC,3))if q.function==0x546b00 else tuple(get(COUNT))if q.function in(0x546af8,0x546afc)else tuple(text(DIR))if q.function==0x546a2c else()
 if currentRoot==0x485160 and q.function in(0x4f777f,0x546b00,0x546a04,0x546af8,0x546afc):scope+=tuple(get(F,4))
 events.append((q.function,q.receiver,a,snapshot(),scope))
 try:return effect(q.function,q.receiver,a)
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0
# Delegate source window/string/renderer leaves only. Actual save/list/record
# bodies and the confirmation actions remain original instructions.
baseMenuHook=menuHook;baseMenuHook.__code__=inactiveHook.__code__
def confirmationHook(uc,address,size,_):
 sp=u.reg_read(UC_X86_REG_ESP);f=STUBS.get(address,address);receiver=u.reg_read(UC_X86_REG_ECX)
 if f==0x4f72c9 and currentRoot==0x485160:maps[F]=receiver
 if f==0x4f6439 and receiver==maps.get(F,F)+12:return
 if f==0x4f6449 and m.stack-0x1000<receiver<m.stack+0x1000:maps[CONF_AUTO+4]=receiver
 if cc.composeStrings and currentRoot in CONF_OWN and f in(0x4f66cc,0x4f6449,0x4f6584):return
 if f==0x5469ec:
  a=tuple(normalize(v)for v in m.read_words(sp+4,1));value=effect(f,0,a);returned(4,value);return
 if f==0x4f6439 and m.stack-0x1000<receiver<m.stack+0x1000:maps[CONF_AUTO]=receiver
 if f==0x4f66cc and m.stack-0x1000<receiver<m.stack+0x1000:maps[CONF_AUTO]=receiver
 if f==0x4f6449 and m.stack-0x1000<receiver<m.stack+0x1000:maps[CONF_AUTO+4]=receiver
 if f==0x546cd0:maps[CONF_AUTO+12]=m.read_words(sp+4,1)[0]
 if f==0x546d58:
  a=m.read_words(sp+4,2);maps[CONF_AUTO+20]=a[0];maps[CONF_AUTO+36]=a[1]
 if f==0x4b9ce0:maps[CONF_AUTO+52]=m.read_words(sp+12,1)[0]
 savedLoadHook(uc,address,size,_)
u.hook_add(UC_HOOK_CODE,confirmationHook)
# Keep defined CFile fields in each physical file callback, while excluding
# the source automatic object's dead storage from full heap comparisons.
loadSource=Path(__file__).with_name('save_load_runtime_helpers.py').read_text();begin=loadSource.index('def loadHook(');end=loadSource.index('u.hook_add(UC_HOOK_CODE,loadHook)',begin);loadBody=loadSource[begin:end].replace('def loadHook(','def confirmationLoadHook(')
loadBody=loadBody.replace('events.append((f,receiver,args,snapshot(),scope))',"scope+=tuple(get(F,4))if currentRoot==0x485160 and f in(0x4f777f,0x546b00,0x546a04,0x546af8,0x546afc)else();events.append((f,receiver,args,snapshot(),scope))")
exec(loadBody,globals());savedLoadHook.__code__=confirmationLoadHook.__code__

def prepare(count=3,nodes=None):
 global previousMode,previousAvailable,baseResult,popupResult,captureResult,cursorImage,failure
 baseConfPrepare(count,nodes);cc.scene=ctx.scene;cc.composeBase=0;cc.composeStrings=0;cc.fault=0;previousMode=5;previousAvailable=PREVIOUS;baseResult=popupResult=1;captureResult=BITMAP;cursorImage=IMAGE;failure=0
 putBytes(CONF_AUTO,bytes(68));put(OWNER,[0x50bf94]);put(OWNER+4,[APP]);put(OWNER+8,[FRAME]);put(OWNER+12,[SCENE]);put(OWNER+344,[6]);put(OWNER+348,[0]);put(OWNER+352,[0]);put(OWNER+356,[PREVIOUS]);put(PREVIOUS,[PREVIOUS_VT]);put(PREVIOUS_VT+16,[MODE]);put(PREVIOUS_VT+20,[FRAME_FN]);put(SCENE+4,[DISPLAY]);put(SCENE+8,[HOLDER]);put(SCENE+28,[HOLDER]);put(DISPLAY+20,[FRONT]);put(FRONT+44,[WRAPPER]);put(BITMAP+124,[0,0,640,480]);put(CURSOR+372,[IMAGE]);put(IMAGE+16,[24,30]);put(APP+124,[640,480]);put(0x5375bc,[0]);put(0x5375c0,[0]);put(0x5375c4,[0]);put(0x52545c,[0xffffffff]);put(0x53ebe0,[RECORDS+0x3000])

def compareConfirmation(f,t,a=(),label='',meaningful=True,construct=False):
 global native,events,maps,currentRoot,calls,eventCount
 native=True;currentRoot=f;maps={};events=[];errors.clear();cc.fault=0;before=bytes(heap);bi=bytes(image);old=state();extra=extraState();ms=menuState();out=U();args=(U*len(a))(*a)
 ok=lib.claw_player_profile_confirmation_construct(t,a[0],C.byref(cc),confirmationDependency,None,C.byref(out))if construct else lib.claw_player_profile_confirmation_entry(f,t,args,len(a),C.byref(cc),confirmationDependency,None,C.byref(out));assert ok and not cc.fault and not errors,('native',hex(f),label,cc.fault,errors)
 expected=canonical();eg=bytes(image[GS-IS:GS-IS+GN]);ne=list(events);after=state();ae=extraState();am=menuState()
 native=False;maps={};u.mem_write(BASE,before);u.mem_write(GS,bi[GS-IS:GS-IS+GN]);restore(old);extraRestore(extra);menuRestore(ms);events=[];syncHook();u.mem_write(m.stack-0x1000,bytes(0x2000))
 if construct:
  u.reg_write(UC_X86_REG_ESP,m.stack);u.reg_write(UC_X86_REG_ESI,t);u.reg_write(UC_X86_REG_EBX,0);u.mem_write(m.stack+0x30,struct.pack('<I',a[0]));u.emu_start(0x429275,0x4292c6,count=100000);value=t
 else:
  value=m.call(f,t,struct.pack('<'+'I'*len(a),*a),max_instructions=10000000);assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+len(a)*4
 if ne!=events:
  print('heap mismatch details',[(hex(BASE+i),expected[i:i+4].hex(),canonical()[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=canonical()[i:i+4]][:12])
  raise AssertionError(('events',hex(f),label,len(ne),len(events),next(((i,a,b)for i,(a,b)in enumerate(zip(ne,events))if a!=b),None)))
 if expected!=canonical():raise AssertionError(('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),canonical()[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=canonical()[i:i+4]][:12]))
 assert eg==bytes(u.mem_read(GS,GN)),('globals',hex(f),label)
 assert state()==after and extraState()==ae and menuState()==am,('state',hex(f),label)
 if meaningful:assert out.value==value,('eax',hex(f),out.value,value)
 native=True;C.memmove(C.addressof(heap),expected,SIZE);C.memmove(C.addressof(image)+GS-IS,eg,GN);restore(after);extraRestore(ae);menuRestore(am);maps={};calls+=1;eventCount+=len(ne);return out.value
