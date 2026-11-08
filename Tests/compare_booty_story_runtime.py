import booty_story_helpers as h
for f,states in ((0x40c150,(0,5,0x2330,0x2331,0x232f)),(0x40d1a0,(0,5,0x232f)),(0x40c4f0,(0,0x232b,0x232c,0x232d,0x232e,0x232f,0x2332))):
 for state in states:
  h.fresh(1,state);h.compare(f,(hex(f),state))
print('PASS actors initial',h.calls,h.eventCount)
import itertools
for f,states in ((0x40c150,(0,5,0x2330,0x2331,0x232f)),(0x40d1a0,(0,5,0x232f)),(0x40c4f0,(0,0x232b,0x232c,0x232d,0x232e,0x232f,0x2332))):
 for level,state,delta,timer in itertools.product(range(1,15),states,(0,1,16,400,5000,0xffffffff),(0,1,5000)):
  if f==0x40c150 and level>11:continue
  h.fresh(level,state,delta);h.put(h.L+304,[timer,timer]);h.compare(f,(hex(f),level,state,delta,timer))
for f in (0x40c150,0x40d1a0):
 for level in range(1,15):
  if f==0x40c150 and(level>11 or not level&1):continue
  h.fresh(level,0,17);h.compare(f,('retained init',f,level));h.put(h.L+308,[0]);h.put(h.L+100,[1]);
  for i in range(170):h.compare(f,('retained update',f,level,i))
print('PASS directed actors',h.calls,h.eventCount,flush=True)
for f,args in((0x40b860,(h.APP,1,3)),(0x40bca0,(3,)),(0x40bd60,()),(0x40bf80,()),(0x40bfd0,()),(0x40be60,()),(0x40bed0,()),(0x40bd50,(2,)),(0x40bf30,(13,0)),(0x40bc80,()),(0x40b620,()),(0x40b600,(1,))):
 h.fresh();h.compare(f,('initial controller',hex(f)),args,meaningful=f not in(0x40bfd0,0x40bc80,0x40b620))
print('PASS controllers initial',h.calls,h.eventCount,flush=True)
# Whole initializer/election across retail levels and resource failure prefixes.
for level,failure in itertools.product(range(1,15),range(5)):
 h.fresh(level);h.resourceFailure=failure;h.compare(0x40b860,('initializer resources',level,failure),(h.APP,level,3))
 if failure==0:
  assert h.get(h.L+104)==[17 if level==14 else level]
  assert h.get(0x5349a0)==[int(bool(level&1)and level<=11)]
  assert h.get(h.CHILD+0x164)==([h.A2]if level&1 and 1<level<12 else[0])
for level in (0,15,0xffffffff,0x80000000):
 h.fresh();h.compare(0x40b860,('rejected level',level),(h.APP,level,3))
# Physical audio queries are explicit; native and original consume same sequence.
for f,timer,mode,latch,found,busy in itertools.product((0x40bfd0,0x40bca0,0x40bd60),(0,1,0xffffffff),range(2),range(2),range(2),(0,1)):
 h.fresh(14);h.put(0x523b50,[timer]);h.put(0x5349a0,[mode]);h.put(h.CHILD+0x154,[latch]);h.soundFound=found;h.busyValues=[busy];h.compare(f,('audio gate',f,timer,mode,latch,found,busy),(3,)if f==0x40bca0 else(),meaningful=f!=0x40bfd0)
for key in (0,13,27,32,65,0xffffffff):
 h.fresh();h.compare(0x40bf30,('first input',key),(key,0xfedcba98));h.compare(0x40bf30,('repeat input',key),(key,0));
 posts=[e for e in h.events if e[0]==0x546d50];assert not posts
print('PASS story controller matrix',h.calls,h.eventCount,flush=True)
# Joined source creator→deferred original scene frame→retail ANI→807c→real cleanup.
joined=[]
for level in range(1,15):
 h.fresh(level);h.realResources();h.realCreation();h.realFrame();h.compare(0x40b860,('joined source init',level),(h.APP,level,3));posts=0
 for i in range(400):
  h.clockNow=(i+1)*100;h.put(0x53720c,[100]);h.compare(0x40bd60,('joined scene tick',level,i));posts+=sum(e[0]==0x546d50 for e in h.events)
 nodes=[];node=h.get(h.SC+0x200+20)[0]
 while node:
  actor=h.get(node+8)[0];logic=h.get(actor+108)[0];nodes.append({'actor':actor,'logic':logic,'state':h.get(logic+28)[0],'x':h.get(actor+76)[0],'y':h.get(actor+80)[0]});node=h.get(node)[0]
 assert posts==1,(level,'request count',posts)
 assert h.get(h.CHILD+0x158)==[1]
 assert all(a['state']==0x232f for a in nodes),(level,nodes)
 assert len(nodes)==(2 if level==13 else 1 if not(level&1)or level==1 else {3:10,5:13,7:8,9:31,11:5}[level]),(level,len(nodes))
 joined.append({'level':level,'actors':len(nodes),'posts':posts,'terminalStates':[a['state']for a in nodes]})
 h.realCleanup();h.compare(0x40bc80,('joined source cleanup',level),meaningful=False);assert h.get(h.SC+0x200+20,5)==[0]*5
print('PASS joined retail story closure',h.calls,h.eventCount,joined,flush=True)
# Original shared48ffa0/48f470 + actual holder/file/format dispatch. Physical
# palette factory, PCX decoder and front/back buffer storage remain transports.
for level in range(1,15):
 h.fresh(level);h.realResources();h.realCreation();h.compare(0x40b860,('shared setup init',level),(h.APP,level,3));h.realPalette(level)
 for f,args in((0x40bca0,(3,)),(0x40be60,()),(0x40bed0,())):h.compare(f,('real shared setup',level,f),args)
for which,present in itertools.product((0,1,2,3,0xffffffff),(0,1)):
 h.fresh();h.put(h.RES+20,[123]);h.put(h.HOLDER+(24 if which==2 else 20),[h.TARGET+0x500 if present else 0]);h.compare(0x4ca900,('holder select',which,present),(h.RES,which),h.HOLDER)
for kind,data,size,result in itertools.product((0,0x424d50,0x504358,0x504944,0x524944,0xffffffff),(0,h.BASE+0x10000),(0,1,0xffffffff),(0,1,0xffffffff)):
 h.fresh();h.bitmapType=kind;h.bitmapData=data;h.bitmapResult=result;h.put(h.RES+20,[size]);h.compare(0x4d4190,('bitmap dispatch',kind,data,size,result),(h.RES,),h.TARGET+0x500)
print('PASS story + shared display dispatch',h.calls,h.eventCount,flush=True)
for failure in (1,2,3):
 h.fresh(2);h.realResources();h.realCreation();h.allocationFail=failure;h.unsafe(0x40b860,('actual creator allocation prefix',failure),(h.APP,2,3))
for f,level,state in((0x40d1a0,13,5),(0x40c4f0,3,0x232c)):
 h.fresh(level,state);h.realResources();h.realCreation();h.put(h.L+308,[0]);h.put(h.L+304,[0]);h.allocationFail=1;h.unsafe(f,('dynamic child allocation',f),(h.A,),0)
print('PASS unsafe prefixes',h.unsafeCases,flush=True)
# Strict API rejection is a native safety extension, without an original claim.
args=(h.U*1)(h.A);out=h.U();h.ctx.fault=0
assert not h.lib.claw_booty_story_entry(0x40d1a0,h.A,args,1,h.C.byref(h.ctx),h.dep,None,h.C.byref(out))and h.ctx.fault==3
# Stage delay100 vs ANI clock33 remain distinct; source actor reads each alias.
for level in (2,4,6,8,10,12,13,14):
 h.fresh(level);h.realResources();h.realCreation();h.realFrame();h.compare(0x40b860,('unequal clocks init',level),(h.APP,level,3))
 for i in range(80):
  h.clockNow=(i+1)*33;h.put(0x53720c,[100]);h.compare(0x40bd60,('unequal stageANI clocks',level,i))
# Busy/expiry + repeated keyboard request use original latch, no inferred timer.
h.fresh(2);h.put(0x523b50,[0]);h.busyValues=[1];h.compare(0x40bd60,'voice held busy');assert h.get(0x523b50)==[1]and h.get(h.CHILD+0x158)==[0]
h.busyValues=[0];h.compare(0x40bd60,'voice starts');assert h.get(h.CHILD+0x154)==[1]
h.compare(0x40bd60,'voice expires');assert len([e for e in h.events if e[0]==0x546d50])==1
h.compare(0x40bf30,'already requested key',(13,0));assert not any(e[0]==0x546d50 for e in h.events)
h.ctx.fault=0
h.WORK.joinpath('verification.json').write_text(h.json.dumps({'normalCalls':h.calls,'orderedSnapshots':h.eventCount,'originalAddresses':len(h.m.executed),'unsafePrefixes':h.unsafeCases,'joinedProfiles':joined,'resources':h.resourceInventory,'screens':h.screenInventory},indent=2)+'\n')
print('PASS FINAL',h.calls,h.eventCount,len(h.m.executed),flush=True)
