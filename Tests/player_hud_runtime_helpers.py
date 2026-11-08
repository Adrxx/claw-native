"""Disjoint hash-pinned raw PlayerHUD fixture and named transport."""
import ctypes as C,struct,subprocess,hashlib,random,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
from original_v10 import OriginalV10
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/player-hud-agent';U=C.c_uint32
sources=list((ROOT/'Sources').glob('*.cpp'))
if not(WORK/'libPlayerHUD.dylib').exists()or any(p.stat().st_mtime>(WORK/'libPlayerHUD.dylib').stat().st_mtime for p in sources):subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources'),'-dynamiclib',*[str(p)for p in sources],'-o',str(WORK/'libPlayerHUD.dylib')],check=True)
lib=C.CDLL(str(WORK/'libPlayerHUD.dylib'))
class SceneCall(C.Structure):_fields_=[('function',U),('receiver',U),('arguments',U*4),('count',U)]
Lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,U,U);Alloc=C.CFUNCTYPE(U,C.c_void_p,U);Free=C.CFUNCTYPE(None,C.c_void_p,U);Invoke=C.CFUNCTYPE(U,C.c_void_p,SceneCall);Clock=C.CFUNCTYPE(U,C.c_void_p)
class Host(C.Structure):_fields_=[('context',C.c_void_p),('lookup',Lookup),('allocate',Alloc),('free',Free),('call',Invoke),('readClock',Clock)]
class SharedGlobals(C.Structure):_fields_=[(n,U)for n in('manager','player','stageDelta','animationDelta','remaining','initialDuration','expired','multiStats','left','top','right','bottom','volume')]
class Shared(C.Structure):_fields_=[('scene',Host),('globals',C.POINTER(SharedGlobals))]+[(n,U)for n in('composeAnimation','composeImages','composeHierarchy','composeFormatting','fault')]
class Globals(C.Structure):_fields_=[(n,U)for n in('initialScore','initialHealth','powerupRemaining','audioEnabled')]
class Context(C.Structure):_fields_=[('scene',Host),('shared',C.POINTER(Shared)),('globals',C.POINTER(Globals))]+[(n,U)for n in('composeAnimation','composeImages','composeFormatting','composeControllers','fault')]
class Call(C.Structure):_fields_=[('function',U),('receiver',U),('count',U),('arguments',U*8),('name',C.c_char_p),('localMask',U),('buffer',C.c_void_p),('bufferBytes',U)]
Dep=C.CFUNCTYPE(U,C.POINTER(Context),C.POINTER(Call),C.c_void_p)
lib.claw_player_hud_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Context),Dep,C.c_void_p,C.POINTER(U)]
BASE,SIZE=0x3000000,0x80000
A,L,HUD,SC,MANAGER,PLAYER,PL,PP,MULTI,ML,OWNER,VT,DISPLAY,DVT,IR,SR,ASR,IMGROOT,LEAF,TABLE,ANI,ANITABLE,ANIRECORD,SOUND,POOL=[BASE+0x1000+i*0x1000 for i in range(25)]
D=[BASE+0x20000+i*0x1000 for i in range(10)];DL=[BASE+0x30000+i*0x1000 for i in range(10)];DH=[BASE+0x40000+i*0x1000 for i in range(10)]
DRAW=0x4000010;GETMODE=0x4000020
FUNCTIONS=(0x4908b0,0x490f80,0x490c50,0x4912a0,0x491540)
SG=(0x5371fc,0x537e88,0x53720c,0x5430c4,0x53c9f8,0x52c6e4,0x53c9f4,0x53c9fc,0x5370c8,0x5370cc,0x5370d0,0x5370d4,0x532c10);GG=(0x534cc4,0x534cc8,0x534ea8,0x532c0c)
m=OriginalV10(ROOT/'Original/claw10/CLAW.EXE');m.u.mem_map(BASE,SIZE);m.u.mem_map(0,4096);m.u.mem_map(0x4000000,4096);m.executed.clear();imageStart,imageEnd,_=next(v for v in m.u.mem_regions()if v[0]==0x400000);image=(C.c_uint8*(imageEnd-imageStart+1)).from_buffer_copy(bytes(m.u.mem_read(imageStart,imageEnd-imageStart+1)));imageSeed=bytes(image);heap=(C.c_uint8*SIZE)();g=Globals();sg=SharedGlobals();shared=Shared();ctx=Context();ctx.shared=C.pointer(shared);ctx.globals=C.pointer(g);shared.globals=C.pointer(sg)
labels={0x52c734:b'GAME_INTERFACE_TREASURECHEST',0x52c71c:b'GAME_INTERFACE_CHEST',0x52c700:b'GAME_INTERFACE_SCORENUMBERS',0x52c6f8:b'%010i',0x52c7c4:b'GAME_INTERFACE_WEAPONS_PISTOL',0x52c790:b'GAME_INTERFACE_SMALLNUMBERS',0x52c7ac:b'GAME_INTERFACE_PISTOL',0x52c7fc:b'GAME_INTERFACE_WEAPONS_MAGIC',0x52c7e4:b'GAME_INTERFACE_MAGIC',0x52c834:b'GAME_INTERFACE_WEAPONS_DYNAMITE',0x52c81c:b'GAME_INTERFACE_DYNAMITE',0x52c774:b'GAME_INTERFACE_HEALTHHEART',0x52c754:b'GAME_INTERFACE_HEALTHNUMBERS',0x52c86c:b'GAME_INTERFACE_LIVESHEAD',0x52c854:b'GAME_INTERFACE_LIVES',0x52c888:b'GAME_INTERFACE_STOPWATCH',0x5240d8:b'GAME_CYCLE100',0x52a2b8:b'GAME_EXTRALIFE',0x522994:b'StatusNumberDigit',0x52297c:b'MultiStats',0x5229d8:b'ScoreFrame',0x5229cc:b'WeaponFrame',0x5229c0:b'HealthFrame',0x5229b4:b'LivesFrame',0x5229a8:b'TimerFrame'}
rng=random.Random(0x4908b0);events=[];oe=[];errors=[];calls=eventCount=0;nextAllocation=BASE+0x50000;allocationIndex=childIndex=0;failAllocation=failChild=0;found=True;mutation=0;mode=3;currentFunction=0;formatCalls=0;recording=False;recordEffects=[];corpus=[]

def pack(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def ptr(t,n=1):
 if t%4:return 0
 if BASE<=t and t+n*4<=BASE+SIZE:return C.addressof(heap)+t-BASE
 if imageStart<=t and t+n*4<=imageEnd+1:return C.addressof(image)+t-imageStart
 return 0
def put(t,v,native=True):
 data=pack(*v)
 if native:C.memmove(ptr(t,len(v)),data,len(data))
 else:m.u.mem_write(t,data)
def get(t,n=1,native=True):return list(struct.unpack('<'+'I'*n,C.string_at(ptr(t,n),n*4)if native else m.u.mem_read(t,n*4)))
def sync():
 for t,v in zip(SG,list(struct.unpack('<13I',bytes(sg)))):put(t,[v])
 for t,v in zip(GG,list(struct.unpack('<4I',bytes(g)))):put(t,[v])
def raw(native):
 if native:sync();return bytes(heap)+C.string_at(ptr(0x520000),0x30000)
 return bytes(m.u.mem_read(BASE,SIZE))+bytes(m.u.mem_read(0x520000,0x30000))
def snap(native):return hashlib.sha256(raw(native)).digest()
@Lookup
def lookup(_,t,n):
 p=ptr(t,n)
 if not p:errors.append(('lookup',hex(t),n))
 return p
@Invoke
def sceneCall(_,e):return 0
ctx.scene=Host(None,lookup,Alloc(),Free(),sceneCall,Clock());shared.scene=ctx.scene
@Dep
def dependency(_,e,user):
 try:
  e=e.contents;a=tuple(e.arguments[:e.count]);name=e.name
  if name is None and e.function==0x4f6286:name=labels.get(a[0])
  before=raw(True)if recording else None;digest=snap(True);events.append((e.function,e.receiver,a,name,e.localMask,b'\0'*e.bufferBytes if e.buffer else None,digest))
  if e.function==0x4a3920:
   text=f'{C.c_int32(a[2]).value:010d}'.encode()+b'\0';C.memmove(e.buffer,text,len(text));value=len(text)-1
  else:value=effect(e.function,e.receiver,a,True)or 0
  if recording:
   assert not e.buffer,'corpus uses composed original formatter';after=raw(True);patches=[(i,v)for i,(u,v)in enumerate(zip(struct.unpack('<'+'I'*(len(before)//4),before),struct.unpack('<'+'I'*(len(after)//4),after)))if u!=v];recordEffects.append((e.function,e.receiver,a,value,digest,patches))
  return value
 except Exception as exc:errors.append(exc);return 0

def effect(f,t,a,native):
 global allocationIndex,nextAllocation,childIndex
 if f==0x4f63ec:
  allocationIndex+=1
  if allocationIndex==failAllocation:return 0
  token=nextAllocation;nextAllocation+=(a[0]+15)&~15;assert nextAllocation<BASE+SIZE
  return token
 if f==0x4f6428:return 0
 if f==0x4f6286:
  if not found:return 0
  name=labels.get(a[0],b'')
  if name==b'GAME_EXTRALIFE':return SOUND
  if a[0]==0x522994:return BASE+0x1b000
  return ANI if name in(b'GAME_INTERFACE_CHEST',b'GAME_INTERFACE_PISTOL',b'GAME_INTERFACE_MAGIC',b'GAME_INTERFACE_DYNAMITE',b'GAME_INTERFACE_LIVES',b'GAME_CYCLE100')else IMGROOT
 if f==0x4c7970:
  if found:put(t+0x170,[IMGROOT,LEAF],native);put(t+0x16c,[0],native)
  else:put(t+0x170,[0],native)
  return int(found)
 if f==0x4c79e0:
  if found:put(t+0x190,[ANI],native)
  return int(found)
 if f==0x4c82a0:return 0
 if f==0x4d3e50:
  childIndex+=1
  if childIndex==failChild:return 0
  token=D[childIndex-1];put(token+100,[a[3]],native);return token
 if f==DRAW:
  if mutation&1:put(HUD+0x24,[D[0]],native);put(D[0]+0x40,[0xabcd0000],native)
  return 0
 if f==GETMODE:return mode
 if f in(0x4b45f0,0x4bc110):return 0
 raise AssertionError(('unexpected',hex(f),hex(t),a))
ABIS={0x4c7970:(1,4),0x4c79e0:(2,8),0x4c82a0:(1,4),0x4d3e50:(6,24),0x4f63ec:(1,0),0x4f6428:(1,0),0x4f6286:(2,8),DRAW:(3,12),GETMODE:(0,0),0x4b45f0:(4,16)}
def hook(uc,f,size,user):
 global formatCalls
 if f==0x4a3920:
  formatCalls+=1
  if ctx.composeFormatting:return
  sp=uc.reg_read(UC_X86_REG_ESP);buffer,fmt,value=m.read_words(sp+4,3);oe.append((f,0,(0,fmt,value),labels.get(fmt),1,b'\0'*16,snap(False)));text=f'{C.c_int32(value).value:010d}'.encode()+b'\0';uc.mem_write(buffer,text);value=len(text)-1;n,pop=3,0
 elif f in ABIS:
  if f==0x4d3e50 and shared.composeHierarchy:return
  if f in(0x4c7970,)and ctx.composeImages:return
  if f in(0x4c79e0,0x4c82a0)and ctx.composeAnimation:return
  sp=uc.reg_read(UC_X86_REG_ESP);n,pop=ABIS[f];a=tuple(m.read_words(sp+4,n));t=uc.reg_read(UC_X86_REG_ECX);name=next((labels[v]for v in a if v in labels),None);norm=a
  if f in(0x4f63ec,0x4f6428,0x4bc110):t=0
  if f==0x4f6286:norm=(a[0],)
  oe.append((f,t,norm,name,0,None,snap(False)));value=effect(f,t,norm,False)or 0
  if f==0x4f6286:m.write_words(a[1],[value]);value=int(bool(value))
 else:return
 uc.reg_write(UC_X86_REG_EAX,value&0xffffffff);uc.reg_write(UC_X86_REG_ESP,sp+4+pop);uc.reg_write(UC_X86_REG_EIP,m.read_words(sp,1)[0])
m.u.hook_add(UC_HOOK_CODE,hook)
def fresh(f=0x4908b0,state=0):
 global nextAllocation,allocationIndex,childIndex,failAllocation,failChild,found,mutation,mode
 C.memmove(C.addressof(image),imageSeed,len(imageSeed));C.memmove(C.addressof(heap),rng.randbytes(SIZE),SIZE);C.memset(C.addressof(g),0,C.sizeof(g));C.memset(C.addressof(sg),0,C.sizeof(sg));sg.manager=MANAGER;sg.player=PLAYER;sg.stageDelta=17;sg.animationDelta=17;sg.remaining=0;sg.initialDuration=35000;sg.multiStats=MULTI;sg.right=640;sg.bottom=480;sg.volume=100;g.initialScore=0;g.initialHealth=100;g.powerupRemaining=0;g.audioEnabled=1;shared.fault=ctx.fault=ctx.composeImages=ctx.composeAnimation=0;shared.composeHierarchy=0;ctx.composeControllers=ctx.composeFormatting=1
 put(A,[0x5137f0]);put(A+8,[0,SC]);put(A+76,[0,0]);put(A+100,[9999,0,L]);put(A+0x170,[IMGROOT,LEAF]);put(A+0x16c,[0]);put(A+0x188,[0x513870,A,0,0,0,0,1,0,0,0,0x3f800000]);put(A+0xfc,[1000000]);put(L,[0x513740]);put(L+12,[SC,f,0,HUD,state]);put(L+0x168,[PP]);put(L+0x130,[0]);put(MANAGER+0x2c,[OWNER]);put(MANAGER+0x68,[2,0]);put(OWNER,[VT]);put(VT+16,[0x40af90]);put(PLAYER+108,[PL]);put(PLAYER+0xf8,[0]);put(PLAYER+0x10c,[100]);put(PL+0x14,[PP]);put(PP,[0]*78);put(PP+0x30,[1]);put(PP+0x70,[10,20,30,3]);put(SC+12,[DISPLAY,IR]);put(SC+0x14,[BASE+0x1a000]);put(SC+0x28,[SR,ASR]);put(SR+0x30,[0]);put(DISPLAY,[DVT]);put(DVT+0x28,[DRAW]);put(HUD,[0x50b5c4,2,3,4,15,2,99,0,1,A,0x50b5cc,0,3,*D[:3]]);put(IMGROOT+20,[TABLE]);put(IMGROOT+100,[0,9]);put(TABLE,[LEAF+i*64 for i in range(10)]);put(SOUND+16,[POOL]);put(MULTI+12,[SC]);put(MULTI+108,[ML]);put(ML+0x10,[0x491ed0]);put(MULTI+0x1b4,[0x5107bc,0,0,0,0,0,10]);put(BASE+0x1b000+8,[0,0,0x4919f0])
 for i in range(10):
  put(LEAF+i*64+24,[8,12,2,0]);put(D[i]+12,[SC]);put(D[i]+100,[10000,0,DL[i]]);put(D[i]+0x170,[IMGROOT,LEAF]);put(DL[i]+16,[0x4919f0,0,DH[i],0]);put(DH[i],[0x50b5c4,2,3+i*11,4,15,2,99,0,1,D[i],0x50b5cc])
 nextAllocation=BASE+0x50000;allocationIndex=childIndex=failAllocation=failChild=mutation=0;found=True;mode=3;sync()
def compare(f,label,actor=A):
 global calls,eventCount,nextAllocation,allocationIndex,childIndex,currentFunction,recording
 recording=label[0]=='real-resource-init'or(label[0]=='real-resource-retained'and label[-1]in(0,1,5,20,29))or(label[0]=='seeded-frame'and label[-1]==0);recordEffects.clear()
 flags=(ctx.composeAnimation,ctx.composeImages,ctx.composeFormatting,ctx.composeControllers,shared.composeHierarchy)
 ctx.fault=shared.fault=0;sync();before=bytes(heap);bi=bytes(image);bg=bytes(g);bsg=bytes(sg);start=nextAllocation;events.clear();errors.clear();allocationIndex=childIndex=0;out=U();arg=(U*1)(actor);ok=lib.claw_player_hud_entry(f,0,arg,1,C.byref(ctx),dependency,None,C.byref(out));assert ok and not ctx.fault and not errors,(label,'native',ctx.fault,errors);expected=raw(True);ev=list(events);end=nextAllocation;
 if recording:corpus.append((0,f,0,(actor,),flags,bg,bsg,out.value,1,before,bi[0x520000-imageStart:0x550000-imageStart],expected,list(recordEffects)))
 recording=False;C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(g),bg,len(bg));C.memmove(C.addressof(sg),bsg,len(bsg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);oe.clear();nextAllocation=start;allocationIndex=childIndex=0;currentFunction=f;result=m.call(f,0,pack(actor));got=raw(False)
 if got!=expected:raise AssertionError((label,'buffer',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:24]))
 if ev!=oe:
  diff=next(((i,x,y)for i,(x,y)in enumerate(zip(ev,oe))if x!=y),None);raise AssertionError((label,'events',len(ev),len(oe),diff))
 assert result==out.value,(label,'EAX',result,out.value);assert nextAllocation==end,(label,'allocation history');C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000)
 for (n,_),t in zip(SharedGlobals._fields_,SG):setattr(sg,n,get(t)[0])
 for (n,_),t in zip(Globals._fields_,GG):setattr(g,n,get(t)[0])
 calls+=1;eventCount+=len(ev);return result
# Original-disc transport inventory; image IDs follow the frozen loader's first
# numeric substring rule, not REZ ordinal or an assumed last suffix.
_assets=None;resourceTokens={};resourceInventory=[]
def assets():
 global _assets
 if _assets is not None:return _assets
 blob=(ROOT/'Original/claw-disc/files/DATA/CLAW.REZ').read_bytes();assert hashlib.sha256(blob).hexdigest()=='b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596';_assets={}
 def w(t):return struct.unpack_from('<I',blob,t)[0]
 def walk(t,n,path=()):
  end=t+n
  while t<end:
   kind,target,size=w(t),w(t+4),w(t+8);start=t+(16 if kind else 28);nul=blob.index(0,start,end);name=blob[start:nul].decode()
   if kind:walk(target,size,path+(name,));t=nul+1
   else:ext=blob[t+20:t+24].split(b'\0')[0][::-1].decode();_assets['/'.join(path+(name+'.'+ext,))]=blob[target:target+size];t=nul+2
 walk(w(131),w(135));return _assets
class Geometry(C.Structure):_fields_=[(n,U)for n in('width','height','halfWidth','halfHeight','offsetX','offsetY','compressed','surface','compressedToken','kind')]
class Record(C.Structure):_fields_=[(n,U)for n in('flags','image','control','movement','parameter','duration','code','dx','dy','event')]
lib.claw_sprite_set_geometry.argtypes=[C.POINTER(Geometry),U,U,U,U];lib.claw_animation_decode_record.argtypes=[C.POINTER(C.c_uint8),U,U,C.POINTER(Record),C.POINTER(U)]
def realResources():
 import re
 resourceTokens.clear();resourceInventory.clear();groups=('TREASURECHEST','SCORENUMBERS','WEAPONS/PISTOL','WEAPONS/MAGIC','WEAPONS/DYNAMITE','SMALLNUMBERS','HEALTHHEART','HEALTHNUMBERS','LIVESHEAD','STOPWATCH');leafAt=BASE+0x60000
 for i,group in enumerate(groups):
  prefix='GAME/IMAGES/INTERFACE/'+group+'/';rows=[];root=BASE+0x1c000+i*0x200;table=BASE+0x1e000+i*0x100
  for path,data in sorted(assets().items()):
   if not path.startswith(prefix)or not path.endswith('.PID'):continue
   match=re.search(r'[0-9]+',Path(path).stem);ident=int(match[0])if match else 0;_,_,w,ht,x,y=struct.unpack_from('<6I',data);geo=Geometry();lib.claw_sprite_set_geometry(C.byref(geo),w,ht,x,y);put(leafAt+16,list(struct.unpack('<10I',bytes(geo)))[:6]);rows.append({'path':path,'id':ident,'token':leafAt,'width':w,'height':ht,'offsetX':C.c_int32(x).value,'offsetY':C.c_int32(y).value});leafAt+=64
  assert rows;minimum=min(r['id']for r in rows);maximum=max(r['id']for r in rows);put(root+20,[table]);put(root+100,[minimum,maximum]);put(table,[0]*(maximum+1))
  for row in rows:put(table+row['id']*4,[row['token']])
  name='GAME_INTERFACE_'+group.replace('/','_');resourceTokens[name.encode()]=root;resourceInventory.append({'name':name,'minimum':minimum,'maximum':maximum,'images':rows})
 recordAt=BASE+0x72000
 for i,group in enumerate(('INTERFACE/CHEST','INTERFACE/PISTOL','INTERFACE/MAGIC','INTERFACE/DYNAMITE','INTERFACE/LIVES','CYCLE100')):
  path='GAME/ANIS/'+group+'.ANI';data=assets()[path];sig,_,flags,count,pl=struct.unpack_from('<5I',data);assert sig==32;at=32+pl;root=BASE+0x6a000+i*0x400;table=root+0x100;pointers=[];names=[]
  for n in range(count):
   tail=data[at:];buffer=(C.c_uint8*len(tail)).from_buffer_copy(tail);record=Record();length=U();used=lib.claw_animation_decode_record(buffer,len(tail),SOUND,C.byref(record),C.byref(length));assert used;vals=list(struct.unpack('<10I',bytes(record)));put(recordAt,[0x513af0,vals[0],*vals[1:9],0,vals[9]]);pointers.append(recordAt);recordAt+=48
   if length.value:names.append(tail[20:20+length.value].decode())
   at+=used
  assert at==len(data)and len(pointers)*4<=0x300;put(root+12,[table,count]);put(table,pointers);name='GAME_'+group.replace('/','_');resourceTokens[name.encode()]=root;resourceInventory.append({'name':name,'path':path,'count':count,'events':names})
 assert recordAt<BASE+SIZE
 return list(resourceInventory)
_oldEffect=effect
def effect(f,t,a,native):
 if f==0x4f6286 and resourceTokens:
  name=labels.get(a[0]);return SOUND if name==b'GAME_EXTRALIFE'and found else resourceTokens.get(name,0)if found else 0
 if f in(0x4c88e0,0x4208e0):return 0
 return _oldEffect(f,t,a,native)
ABIS.update({0x4c88e0:(4,16),0x4208e0:(4,16)})
SharedDep=C.CFUNCTYPE(U,C.POINTER(Shared),C.POINTER(Call),C.c_void_p)
lib.claw_checkpoint_timer_entry.argtypes=[U,U,C.POINTER(U),U,C.POINTER(Shared),SharedDep,C.c_void_p,C.POINTER(U)]
FRAME_NAMES=(0x5229d8,0x5229cc,0x5229c0,0x5229b4,0x5229a8);CONTAINER=BASE+0x1a800
@SharedDep
def sharedDependency(_,e,user):
 try:
  v=e.contents
  if v.function in FUNCTIONS:
   result=U();a=(U*v.count)(*v.arguments[:v.count]);ok=lib.claw_player_hud_entry(v.function,v.receiver,a,v.count,C.byref(ctx),dependency,None,C.byref(result));assert ok and not ctx.fault;return result.value
  return dependency(C.pointer(ctx),e,user)
 except Exception as exc:errors.append(exc);return 0
_previousEffect=effect
def effect(f,t,a,native):
 if f==0x4f6286 and a[0]in(0x52297c,*FRAME_NAMES,0x522994):
  if not found:return 0
  return BASE+0x1b000 if a[0]==0x522994 else BASE+0x1b040 if a[0]==0x52297c else BASE+0x1b080+FRAME_NAMES.index(a[0])*32
 if f==0x4c9e00:return 0
 return _previousEffect(f,t,a,native)
ABIS[0x4c9e00]=(1,4)
# Creation composes original bodies rather than the child-return transport.
_oldHook=hook
# Existing hook is retained; a branch inside it recognizes this flag below.
def compoundSetup():
 fresh();realResources();ctx.composeImages=ctx.composeAnimation=1;shared.composeImages=shared.composeAnimation=0;shared.composeHierarchy=shared.composeFormatting=1;put(SC+24,[2]);put(CONTAINER+12,[SC]);put(CONTAINER+0x10,[0x5107bc,0,0,0,0,0,10]);put(BASE+0x1b040+8,[0,0,0x491ed0])
 for i,f in enumerate(FUNCTIONS):put(BASE+0x1b080+i*32+8,[0,0,f])
def compound(f,receiver,arguments,label,void=False):
 global calls,eventCount,nextAllocation,allocationIndex,childIndex,recording
 recording=label[1]==2;recordEffects.clear();flags=(ctx.composeAnimation,ctx.composeImages,ctx.composeFormatting,ctx.composeControllers,shared.composeHierarchy)
 ctx.fault=shared.fault=0;sync();before=bytes(heap);bi=bytes(image);bg=bytes(g);bsg=bytes(sg);start=nextAllocation;events.clear();errors.clear();allocationIndex=childIndex=0;out=U();a=(U*len(arguments))(*arguments);ok=lib.claw_checkpoint_timer_entry(f,receiver,a,len(arguments),C.byref(shared),sharedDependency,None,C.byref(out));assert ok and not shared.fault and not ctx.fault and not errors,(label,'native',shared.fault,ctx.fault,errors);expected=raw(True);ev=list(events);end=nextAllocation;
 if recording:corpus.append((1,f,receiver,tuple(arguments),flags,bg,bsg,out.value,int(not void),before,bi[0x520000-imageStart:0x550000-imageStart],expected,list(recordEffects)))
 recording=False;C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(g),bg,len(bg));C.memmove(C.addressof(sg),bsg,len(bsg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);oe.clear();nextAllocation=start;allocationIndex=childIndex=0;result=m.call(f,receiver,pack(*arguments));got=raw(False)
 if got!=expected:raise AssertionError((label,'compound-buffer',[(hex(BASE+i if i<SIZE else 0x520000+i-SIZE),got[i],expected[i])for i in range(len(got))if got[i]!=expected[i]][:24]))
 if ev!=oe:raise AssertionError((label,'compound-events',len(ev),len(oe),next(((i,x,y)for i,(x,y)in enumerate(zip(ev,oe))if x!=y),None)))
 if not void:assert result==out.value,(label,'EAX',result,out.value)
 assert nextAllocation==end,(label,'allocation-history');C.memmove(C.addressof(heap),expected[:SIZE],SIZE);C.memmove(C.addressof(image)+0x520000-imageStart,expected[SIZE:],0x30000)
 for (n,_),t in zip(SharedGlobals._fields_,SG):setattr(sg,n,get(t)[0])
 for (n,_),t in zip(Globals._fields_,GG):setattr(g,n,get(t)[0])
 calls+=1;eventCount+=len(ev);return result

def writeCorpus():
 import gzip
 with gzip.open(WORK/'sanitizer-replay.bin.gz','wb',compresslevel=1)as stream:
  stream.write(b'HUDR'+pack(imageStart,len(imageSeed),SIZE,0x520000,0x30000,len(corpus)));stream.write(imageSeed)
  for kind,f,receiver,args,flags,bg,bsg,result,meaningful,before,globalsBefore,after,ev in corpus:
   stream.write(pack(kind,f,receiver,len(args),*list(args)+[0]*(8-len(args)),*flags,*struct.unpack('<4I',bg),*struct.unpack('<13I',bsg),result,meaningful,len(ev)));stream.write(before);stream.write(globalsBefore)
   for fn,t,a,value,digest,patches in ev:
    stream.write(pack(fn,t,len(a),*list(a)+[0]*(8-len(a)),value,len(patches)));stream.write(digest)
    for index,word in patches:stream.write(pack(index,word))
   stream.write(after)
 return len(corpus)
unsafeCases=[]
def nullPageOff():
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 saved=m.u.context_save();teb,gdt=0x10ed000,0x10ee000
 def desc(base,access):return struct.pack('<I',0xffff|(base&0xffff)<<16)+struct.pack('<I',((base>>16)&255)|access<<8|0xcf<<16|(base&0xff000000))
 m.u.mem_write(gdt+8,desc(0,0x9b));m.u.mem_write(gdt+16,desc(0,0x93));m.u.mem_write(gdt+24,desc(teb,0x93));m.u.reg_write(UC_X86_REG_GDTR,(0,gdt,0x100,0))
 for reg in(UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES):m.u.reg_write(reg,0x10)
 m.u.reg_write(UC_X86_REG_CS,8);m.u.reg_write(UC_X86_REG_FS,0x18);m.u.mem_write(teb,pack(0));m.u.mem_unmap(0,4096);return saved

def unsafeCompare(f,label):
 from unicorn import UcError
 global nextAllocation,allocationIndex,childIndex,eventCount
 sync();before=bytes(heap);bi=bytes(image);bg=bytes(g);bsg=bytes(sg);start=nextAllocation;events.clear();errors.clear();allocationIndex=childIndex=0;out=U();arg=(U*1)(A);ok=lib.claw_player_hud_entry(f,0,arg,1,C.byref(ctx),dependency,None,C.byref(out));assert not ok and ctx.fault,(label,'native diagnostic');expected=raw(True);ev=list(events);C.memmove(C.addressof(heap),before,SIZE);C.memmove(C.addressof(image),bi,len(image));C.memmove(C.addressof(g),bg,len(bg));C.memmove(C.addressof(sg),bsg,len(bsg));m.u.mem_write(BASE,before);m.u.mem_write(imageStart,bi);oe.clear();nextAllocation=start;allocationIndex=childIndex=0;saved=nullPageOff()
 try:
  try:m.call(f,0,pack(A));raise AssertionError((label,'expected original null fault'))
  except UcError:pass
  originalEIP=m.u.reg_read(UC_X86_REG_EIP);got=raw(False);assert got==expected,(label,'unsafe prefix buffers');assert ev==oe,(label,'unsafe prefix events',ev,oe);unsafeCases.append({'label':label,'callback':hex(f),'nativeFault':ctx.fault,'originalEIP':hex(originalEIP),'events':len(ev)});eventCount+=len(ev)
 finally:m.u.mem_map(0,4096);m.u.context_restore(saved)
