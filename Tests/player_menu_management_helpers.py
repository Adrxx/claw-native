"""Ordinary isolated profile-menu oracle; no OS/user file access."""
from pathlib import Path
source=Path(__file__).with_name('player_cache_application_helpers.py').read_text()
source=source.replace("WORK=ROOT/'work/player-cache-application-agent'","WORK=ROOT/'work/player-menu-management-agent'")
source=source.replace("'PlayerCacheApplicationRuntime','SaveLoadRuntime'","'PlayerMenuManagementRuntime','CStringAssignmentRuntime','PlayerCacheApplicationRuntime','SaveLoadRuntime'")
source=source.replace("exec(compile(base,", "base=base.replace(\"],'-o',str(WORK/\",\"],str(ROOT/'work/application-level-progression-agent/libProgressionFrozenSupport.dylib'),'-o',str(WORK/\")\nexec(compile(base,")
exec(compile(source,str(Path(__file__).with_name('player_cache_application_helpers.py')),'exec'),globals())
MENU_AUTO=BASE+0x2a000;TIME_CELL=BASE+0x2b000;CONTROL2=0x1235
class MenuContext(C.Structure):_fields_=[('scene',Host),('playerCache',C.c_void_p),('strings',C.c_void_p),('startup',C.c_void_p)]+[(n,U)for n in('automaticToken','composeStrings','maximumOperations','fault')]
MenuDependency=C.CFUNCTYPE(U,C.POINTER(MenuContext),C.POINTER(RichCall),C.c_void_p)
class StringContext(C.Structure):_fields_=[('scene',Host)]+[(n,C.c_void_p)for n in('lifecycle','allocation','arrays','byteContext')]+[('bytes',ByteLookup),('maximum',U),('fault',U)]
class FadeContext(C.Structure):_fields_=[('scene',Host),('globals',C.c_void_p)]+[(n,U)for n in('descriptorWord','descriptorToken','maximum','fault')]
class BlendContext(C.Structure):_fields_=[('fade',C.c_void_p)]+[(n,U)for n in('temporary','empty','capture')]
class StartupContext(C.Structure):_fields_=[('scene',Host),('singlePlayer',C.c_void_p)]+[(n,U)for n in('composeCache','composeCamera','maximumPlanes','fault')]
strings=StringContext();fade=FadeContext();blend=BlendContext();startup=StartupContext();strings.allocation=C.addressof(blend);blend.fade=C.addressof(fade);strings.bytes=loadBytes;strings.maximum=100000
mc=MenuContext();mc.playerCache=C.addressof(ac);mc.strings=C.addressof(strings);mc.startup=C.addressof(startup);mc.automaticToken=MENU_AUTO;mc.composeStrings=1;mc.maximumOperations=100000
lib.claw_player_menu_management_entry.argtypes=[U,U,UP,U,C.POINTER(MenuContext),MenuDependency,C.c_void_p,UP]
OWN_MENU={0x426e30,0x49b160,0x49b630,0x49afd0,0x49b3a0,0x49b470,0x49c860,0x49aed0}
SIZES.update({MENU_AUTO:128,MENU_AUTO+128:256,MENU_AUTO+384:4,MENU_AUTO+388:4,MENU_AUTO+392:64,TIME_CELL:4})
EXTERNAL.update({0x546d1c:4,0x4a3920:3,0x428c40:4,0x5469e4:1,0x5469ec:1})
CDECL.update({0x546d1c,0x4a3920,0x5469e4,0x5469ec})
for i,slot in enumerate((0x546d1c,0x5469e4,0x5469ec)):
 at=STUB+0x800+16*i;STUBS[at]=slot;IMPORTS[slot]=EXTERNAL[slot];m.write_words(slot,[at]);C.memmove(C.addressof(image)+slot-IS,struct.pack('<I',at),4);u.mem_write(at,b'\xc3')
globalSeed=bytes(image[GS-IS:GS-IS+GN]);sourceOriginalSeed=globalSeed
baseMenuCanonical=canonical;baseMenuSnapshot=snapshot;baseMenuEffect=effect;baseMenuPrepare=prepare
labels={};numbers={};endings=[];transitionResult=1;controlLists={};controlIndices={}

def text(t):
 if not t:return b''
 value=bytearray()
 for i in range(4096):
  b=readBytes(t+i,1)[0]
  if not b:return bytes(value)
  value.append(b)
 raise AssertionError('unterminated fixture text')
def canonical():
 b=bytearray(baseMenuCanonical());b[MENU_AUTO-BASE:MENU_AUTO-BASE+456]=bytes(456);return bytes(b)
def snapshot():return baseMenuSnapshot()+(tuple(sorted(labels.items())),tuple(sorted(numbers.items())),tuple(endings),tuple(sorted((k,tuple(v))for k,v in controlLists.items())),tuple(sorted(controlIndices.items())))
def effect(f,t,a):
 if f==0x546d1c:numbers[a[1]]=a[2];return 1
 if f==0x546d34:endings.append(a[1]);return 1
 if f==0x546d3c:labels[a[1]]=text(a[2]);return 1
 if f==0x546d40:return CONTROL2 if a[1]==0x446 else controlResult
 if f==0x5469e4:return len(text(a[0]))
 if f==0x5469ec:put(a[0],[get(a[0])[0]+1]);return get(a[0])[0]
 if f==0x428c40:return transitionResult
 if f==0x4a3920:
  out,fmt,*values=a;pattern=text(fmt)
  if pattern==b'Info for %s':v=b'Info for '+text(values[0])
  elif pattern==b'Level %i':v=b'Level '+str(values[0]).encode()
  elif pattern==b'%i:%02i:%02i':v=f'{values[0]}:{values[1]:02}:{values[2]:02}'.encode()
  else:assert not values,(pattern,values);v=pattern
  putBytes(out,v+b'\0');return len(v)
 if f==0x546d44 and a[0] in(CONTROL,CONTROL2) and a[1] in(0x180,0x184,0x186,0x188,0x189,399):
  control,msg,index,value=a
  if msg==0x184:controlLists[control]=[];controlIndices[control]=0xffffffff;return 0
  if msg==0x180:controlLists.setdefault(control,[]).append(text(value));return len(controlLists[control])-1
  if msg==0x186:controlIndices[control]=index;return 0
  if msg==0x188:return controlIndices.get(control,0xffffffff)
  if msg==399:
   v=text(value);return controlLists.get(control,[]).index(v)if v in controlLists.get(control,[])else 0xffffffff
  if msg==0x189:
   rows=controlLists.get(control,[])
   if index>=len(rows):return 0xffffffff
   putBytes(value,rows[index]+b'\0');return len(rows[index])
 return baseMenuEffect(f,t,a)
@MenuDependency
def menuDependency(c,e,_):
 q=e.contents
 if q.function in(0x4f63ec,0x4f6428):return appDependency(C.byref(ac),e,None)
 args=tuple(q.arguments[:q.count]);events.append((q.function,q.receiver,args,snapshot(),()))
 try:return effect(q.function,q.receiver,args)
 except BaseException as ex:errors.append(ex);c.contents.fault=1;return 0
# Original automatic variables are mapped only when the unchanged instruction
# bodies pass them to a service. Undefined automatic storage is excluded.
baseAppHook=appHook
baseAppHook.__code__=inactiveHook.__code__

def menuHook(uc,address,size,_):
 sp=u.reg_read(UC_X86_REG_ESP);f=STUBS.get(address,address);receiver=u.reg_read(UC_X86_REG_ECX)
 if f==0x4a3920:
  fmt=m.read_words(sp+8,1)[0];isTime=fmt==0x52dcf4;SIZES[MENU_AUTO+392 if isTime else MENU_AUTO]=64 if isTime else 128;maps[MENU_AUTO+392 if isTime else MENU_AUTO]=m.read_words(sp+4,1)[0]
  count=5 if isTime else 2 if fmt==0x5280b8 else 3
  EXTERNAL[0x4a3920]=count
  args=tuple(normalize(v)for v in m.read_words(sp+4,count));events.append((f,0,args,snapshot(),()));value=effect(f,0,args);returned(0,value);return
 if f==0x546d44:
  a=m.read_words(sp+4,4)
  if a[1]==0x189:maps[MENU_AUTO+128]=a[3]
 if f==0x4f6584 and mc.composeStrings and currentRoot in OWN_MENU:return
 if f==0x4f65f2:maps[MENU_AUTO+388]=receiver
 if f==0x49c860:
  a=m.read_words(sp+4,2)
  if m.stack-0x1000<a[0]<m.stack+0x1000:maps[MENU_AUTO+384]=a[0]
 # Atomic increment has no observable source call event in frozen copy helper.
 if f==0x5469ec:
  a=m.read_words(sp+4,1);effect(f,0,tuple(normalize(v)for v in a));returned(4,get(normalize(a[0]))[0]);return
 savedLoadHook(uc,address,size,_)
u.hook_add(UC_HOOK_CODE,menuHook)

def prepare(count=3,nodes=None):
 global labels,numbers,endings,transitionResult,controlLists,controlIndices,globalSeed
 globalSeed=sourceOriginalSeed;C.memmove(C.addressof(image)+GS-IS,globalSeed,GN);u.mem_write(GS,globalSeed);baseMenuPrepare(count,nodes)
 mc.scene=ctx.scene;mc.fault=0;mc.composeStrings=1;ac.scene=ctx.scene;strings.scene=fade.scene=startup.scene=ctx.scene;strings.fault=fade.fault=startup.fault=0;startup.composeCache=1
 putBytes(MENU_AUTO,bytes(456));put(TIME_CELL,[0]);put(0x52e1cc,[ctx.emptyStringToken]);put(0x52e1c8,[ctx.emptyStringToken-12]);put(0x53ebe0,[RECORDS]);put(0x53ebe4,[CONTROL]);put(0x53ebe8,[CONTROL2]);labels={};numbers={};endings=[];transitionResult=1;controlLists={};controlIndices={}
 for i,name in enumerate((b'Player',b'Ada',b'Lin')[:count]):
  r=RECORDS+i*0x3000;putBytes(r+20,name+b'\0');putBytes(r+54,b'Fictional island\0');putBytes(r+136,b'fixture.invalid\0');put(r+4,[4 if i else 0]);
  for k in range(15):
   put(r+0x21c4+k*68+4,[1000+k]);put(r+0x21c4+k*68+8,[3723000]);
   for kind in range(1,4):put(r+0x2d4+(kind-1)*0xa50+k*0xb0,[2]);
   cache=r+0x1774+k*0xb0;put(cache+16,[2000+k]);put(cache+20,[3723000]);
   for off in(0x94,0x98,0x9c,0xa0,0xa4):put(cache+off,[off+k])

def menuState():return labels.copy(),numbers.copy(),endings[:],{k:v[:]for k,v in controlLists.items()},controlIndices.copy()
def menuRestore(s):
 global labels,numbers,endings,controlLists,controlIndices
 labels,numbers,endings,controlLists,controlIndices=s

def compareMenu(f,t,a=(),label='',meaningful=True):
 global native,events,maps,currentRoot,calls,eventCount
 native=True;currentRoot=f;maps={};events=[];errors.clear();mc.fault=0;before=bytes(heap);bi=bytes(image);old=state();extra=extraState();ms=menuState();out=U();args=(U*len(a))(*a)
 ok=lib.claw_player_menu_management_entry(f,t,args,len(a),C.byref(mc),menuDependency,None,C.byref(out));assert ok and not mc.fault and not errors,('native',hex(f),label,mc.fault,errors)
 expected=canonical();eg=bytes(image[GS-IS:GS-IS+GN]);ne=list(events);after=state();ae=extraState();am=menuState()
 native=False;maps={};u.mem_write(BASE,before);u.mem_write(GS,bi[GS-IS:GS-IS+GN]);restore(old);extraRestore(extra);menuRestore(ms);events=[];syncHook();u.mem_write(m.stack-0x1000,bytes(0x2000));value=m.call(f,t,struct.pack('<'+'I'*len(a),*a));pop=0 if f in(0x49afd0,0x49b3a0,0x49b470,0x49c860)else len(a)*4;assert u.reg_read(UC_X86_REG_ESP)==m.stack+4+pop
 if ne!=events:raise AssertionError(('events',hex(f),label,len(ne),len(events),next(((i,a,b)for i,(a,b)in enumerate(zip(ne,events))if a!=b),None)))
 if expected!=canonical():raise AssertionError(('heap',hex(f),label,[(hex(BASE+i),expected[i:i+4].hex(),canonical()[i:i+4].hex())for i in range(0,SIZE,4)if expected[i:i+4]!=canonical()[i:i+4]][:10]))
 assert eg==bytes(u.mem_read(GS,GN)),('globals',hex(f),label)
 assert state()==after and extraState()==ae and menuState()==am,('state',hex(f),label)
 if meaningful:assert out.value==value,('eax',hex(f),out.value,value)
 native=True;C.memmove(C.addressof(heap),expected,SIZE);C.memmove(C.addressof(image)+GS-IS,eg,GN);restore(after);extraRestore(ae);menuRestore(am);maps={};calls+=1;eventCount+=len(ne);return out.value
