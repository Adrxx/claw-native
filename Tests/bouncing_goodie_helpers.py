"""Private BouncingGoodie harness; frozen common fixture definitions read-only."""
from pathlib import Path
source=Path(__file__).with_name('human_combat_helpers.py').read_text().split('def compare_null_create(element):')[0]
source=source.replace('\nu.hook_add(UC_HOOK_CODE,host)','\ncombatHook=u.hook_add(UC_HOOK_CODE,host)')
source=source.replace('work/human-combat-agent','work/bouncing-goodie-agent').replace("'HumanCombat.cpp','SceneActorRuntime.cpp'","'BouncingGoodieLogic.cpp','HumanCombat.cpp','SceneActorRuntime.cpp'")
exec(compile(source,str(Path(__file__).with_name('human_combat_helpers.py')),'exec'),globals())
# Resolve a registered name through the actual getter, as the host does when
# materializing its state view. This clears the bootstrap temporary-count1.
q['m'].call(0x441030,0x537698,struct.pack('<I',ids[b'LS_FALLING']))
registryTables[0x537698]=q['m'].read_words(0x537698,12)
registryHeap=bytes(q['u'].mem_read(q['HEAP'],q['SIZE']))
u.mem_write(q['HEAP'],registryHeap)
class Loot(C.Structure):_fields_=[('words',C.c_uint32*341)]+[(n,C.c_uint32)for n in('itemCount','audioVolume','highLaunch','configurationWord')]
class GoodieContext(C.Structure):_fields_=[('generic',C.POINTER(GenericContext)),('shared',C.POINTER(Extra)),('scene',SceneHost),('sequenceRegistryToken',C.c_uint32),('loot',C.POINTER(Loot)),('states',C.POINTER(State)),('stateCount',C.c_size_t),('imageMinimum',C.c_int32),('imageMaximum',C.c_int32),('minimumImageToken',C.c_uint32),('imageHeader',C.c_uint32*16),('fault',C.c_uint32)]
lib.claw_bouncing_goodie_context_defaults.argtypes=[C.POINTER(GoodieContext)]
lib.claw_bouncing_goodie_entry.argtypes=[C.POINTER(Enemy),C.POINTER(GoodieContext),C.c_uint32,C.c_uint32,Dependency,C.c_void_p,C.POINTER(C.c_uint32)]
lib.claw_bouncing_goodie_callback.argtypes=[C.POINTER(Enemy),C.POINTER(GoodieContext),Dependency,C.c_void_p]
baseFresh=fresh;baseInstall=install;baseEffects=effects;baseHost=host;baseSerialized=serialized;baseSnapshot=snapshot;baseWrite=write
allocationFailure=False;freeMutation=False
GOODIE_IMAGE=0x10b3000;goodieView=None;collisionResult=0;pickupMode=0;loot=Loot();loot.itemCount=62;loot.words[340]=1
for n in range(66):loot.words[n]=0x10b4000+n*32;loot.words[66+n]=100*n;loot.words[132+n]=0x40<<n%8;loot.words[274+n]=0x10a4000+n*0x80
classTable=registryTables[0x5349e0];lo,hi,data=classTable[2:5]
goodieStates=(State*len(profile))(*[State(id,q['m'].read_words(data+4*(id-lo),1)[0]if lo<=id<=hi else 0,token,name)for id,token,name in profile])

def fresh():
 s,c=baseFresh();g=c.generic;g.defaults[12]=rng.choice([24,0x80000000,0xffffffff]);g.tick=rng.choice([0,123,0x80000000,0xffffffff]);s.primary[7]=rng.choice([ids[b'LS_FALLING'],ids[b'LS_BOUNCE'],ids[b'LS_DEAD']]);s.primary[6]=E;s.actor[0x174//4]=GOODIE_IMAGE;s.actor[0x170//4]=rng.choice([0,loot.words[rng.randrange(66)]]);s.actor[0x190//4]=rng.choice([0,0x10a8000]);s.actor[0x148//4]=rng.choice([0,100,0xffffffff]);s.actor[0x14c//4]=rng.choice([0,300,0xfffffff0]);s.actor[2]=rng.randrange(16);s.actor[0xcc//4]=rng.choice([1,7,8]);s.actor[0x164//4]=rng.choice([0,0x200]);s.actor[0x64//4]=rng.choice([0,4001]);s.enemy[0]=0x50b68c;s.enemy[0x198//4]=rng.getrandbits(32);s.enemy[0x19c//4]=rng.choice([0,125,1000,0xffffffff]);s.enemy[0x194//4]=rng.choice([0,1,3,4,0x7fffffff,0x80000000,0xffffffff]);s.enemy[0x188//4]=rng.choice([0,resourceViews[0].token]);s.enemy[0x18c//4]=0x10a8000;s.enemy[0xc8//4]=rng.choice([0,1]);s.enemy[5]=s.enemy[6]=0;s.enemy[0x184//4]=rng.choice([0,1,33,61,65,0xffffffff]);s.enemy[0x128//4]=s.enemy[0x12c//4]=A;s.enemy[0x130//4]=L
 return s,c

def view(c):
 x=GoodieContext();x.generic=C.pointer(c.generic);x.shared=C.pointer(c.sharedStates);x.sequenceRegistryToken=SEQ;x.loot=C.pointer(loot);x.states=goodieStates;x.stateCount=len(goodieStates);x.imageMinimum=0;x.imageMaximum=0;x.minimumImageToken=GOODIE_IMAGE;x.imageHeader[:]=[0]*6+[0xfffffff0,0xffffffe0,16,32]+[0]*6
 lib.claw_bouncing_goodie_context_defaults(C.byref(x));return x

def serialized(s):return baseSerialized(s)+bytes(loot)
def snapshot():
 s=baseSnapshot();loot.words[:]=m.read_words(0x537ec8,341);loot.itemCount=m.read_words(0x52a190,1)[0];return s
def write(s):baseWrite(s);m.write_words(0x537ec8,loot.words);m.write_words(0x52a190,[loot.itemCount])
def effects(s,event):
 f,receiver,args,name=event
 if f==0x4f63ec:return 0 if allocationFailure else E
 if f==0x4f6428 and freeMutation:current.generic.enemyToken=0;return 0
 if f==0x4f6286:return resourceViews[0].token
 if f==0x4cbb60:
  s.actor[0x4c//4]=args[1];s.actor[0x50//4]=args[2];return collisionResult
 if f==0x473660:
  if pickupMode:s.primary[7]=0;s.primary[4]=0x40f690;s.actor[2]|=0x10000
  return 1
 if f==0x4719e0:loot.words[340]=1;return 1
 return baseEffects(s,event)
def host(uc,address,size,user):
 if address in(0x4dc870,0x40e690,0x40e750,0x40ebe0,0x40efa0,0x40f010,0x40f0e0,0x40f200,0x40f2a0,0x40f390,0x40f400,0x4736b0):return
 if address in(0x473660,0x4719e0):
  sp=u.reg_read(UC_X86_REG_ESP);n=2 if address==0x473660 else 1;event=(address,0,tuple(m.read_words(sp+4,n)),None);s=snapshot();events.append((event,serialized(s)));result=effects(s,event);write(s);returned(0,result);return
 baseHost(uc,address,size,user)
u.hook_del(combatHook);u.hook_add(UC_HOOK_CODE,host)
def install(s,c):
 baseInstall(s,c);write(s);m.write_words(GOODIE_IMAGE,goodieView.imageHeader);m.write_words(0x50b68c,c.generic.virtualFunctions[:10])
 m.write_words(0x50b2a4+0x24,[0x4dca10])

def compare(s,c,entry,label,arg=0):
 global current,native,random_index,calls,event_count,goodieView
 before,bc=bytes(s),bytes(c);beforeLoot=bytes(loot);current=c;native=True;events.clear();random_index=0;goodieView=view(c);result=C.c_uint32()
 if entry==0x40e690:ret=lib.claw_bouncing_goodie_callback(C.byref(s),C.byref(goodieView),dependency,None)
 else:
  support=lib.claw_bouncing_goodie_entry(C.byref(s),C.byref(goodieView),entry,arg,dependency,None,C.byref(result));assert support
 assert not goodieView.fault,(label,'native fault',goodieView.fault)
 expected,ee=serialized(s),list(events)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);loot.words[:]=Loot.from_buffer_copy(beforeLoot).words;loot.itemCount=Loot.from_buffer_copy(beforeLoot).itemCount;goodieView=view(oc);install(old,oc);native=False;events.clear();random_index=0
 args=struct.pack('<I',A)if entry in(0x40e750,0x40e690,0x4736b0)else struct.pack('<I',E)if entry==0x4dc870 else struct.pack('<I',arg)if entry in(0x40ebe0,0x484d90)else b''
 receiver=0 if entry in(0x40e690,0x4dc870,0x4736b0)else E
 try:r=m.call(entry,receiver,args)
 except Exception:print('original fault',label,hex(u.reg_read(UC_X86_REG_EIP)));raise
 actual=serialized(snapshot())
 # Valid captured IDs leave original registry tables and CString heap intact.
 assert all(m.read_words(t,12)==(words[:10]+list(loot.words[:2]) if t==0x537ea0 else words) for t,words in registryTables.items()),(label,'registry raw tables including overlapping loot view')
 assert bytes(u.mem_read(q['HEAP'],q['SIZE']))==registryHeap,(label,'registry entire heap')
 if actual!=expected:
  for n,(a,b)in enumerate(zip(struct.unpack('<'+'I'*(len(actual)//4),actual),struct.unpack('<'+'I'*(len(expected)//4),expected))):
   if a!=b:print(label,'word',n,hex(a),hex(b))
  raise AssertionError((label,'full buffers'))
 if entry not in(0x40ebe0,0x40f2a0,0x4736b0):assert r==(ret if entry==0x40e690 else result.value),(label,'result',r,result.value)
 if events!=ee:
  for n,(a,b)in enumerate(zip(events,ee)):
   if a!=b:print(label,'event',n,a[0],b[0],'snapshot',a[1]==b[1]);break
  print('original',[x[0]for x in events]);print('native',[x[0]for x in ee]);raise AssertionError((label,'events'))
 calls+=1;event_count+=len(events);current=c;return s,c

def compare_null_allocation():
 global current,native,random_index,calls,event_count,goodieView,allocationFailure
 from unicorn import UcError
 from unicorn.x86_const import UC_X86_REG_GDTR,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_FS
 s,c=fresh();s.primary[7]=0;before,bc=bytes(s),bytes(c);current=c;native=True;events.clear();random_index=0;goodieView=view(c);allocationFailure=True
 assert lib.claw_bouncing_goodie_callback(C.byref(s),C.byref(goodieView),dependency,None)==0 and goodieView.fault==2
 expected,ee=serialized(s),list(events)
 old,oc=Enemy.from_buffer_copy(before),Context.from_buffer_copy(bc);goodieView=view(oc);install(old,oc);native=False;events.clear();random_index=0
 cpu=u.context_save();TEB,GDT=0x10ed000,0x10ee000
 def descriptor(base,access):return struct.pack('<HHBBBB',0xffff,base&0xffff,(base>>16)&0xff,access,0xcf,(base>>24)&0xff)
 u.mem_write(GDT+8,descriptor(0,0x9b));u.mem_write(GDT+16,descriptor(0,0x93));u.mem_write(GDT+24,descriptor(TEB,0x93));u.reg_write(UC_X86_REG_GDTR,(0,GDT,0x100,0))
 for reg,value in((UC_X86_REG_SS,16),(UC_X86_REG_DS,16),(UC_X86_REG_ES,16),(UC_X86_REG_CS,8),(UC_X86_REG_FS,24)):u.reg_write(reg,value)
 m.write_words(TEB,[0xdeadbeef]);u.mem_unmap(0,4096)
 try:
  m.call(0x40e690,0,struct.pack('<I',A));raise AssertionError('original null allocation unexpectedly returned')
 except UcError:
  assert u.reg_read(UC_X86_REG_EIP)==0x40e6ee
  assert serialized(snapshot())==expected and events==ee
 finally:u.context_restore(cpu);u.mem_map(0,4096);allocationFailure=False
 calls+=1;event_count+=len(events)
