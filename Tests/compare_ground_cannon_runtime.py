"""Whole pinned original GroundCannon child closure and retail asset profiles."""
import ground_cannon_helpers as h
h.composeCommon=True
for n in range(12):
 h.weaponFresh('cannon');h._childAllocation=0;h.resourceTokens.clear();h.put(h.A+0x40,[n%2*2]);h.put(h.A+0x148,[[0,-500,500,-2147483648][n%4],n]);h.found=n%3!=0;h.capture=n<2
 h.compare(0x449480,('constructor',n),(h.A,),meaningful=True)
for level in(2,8):
 h.weaponFresh('cannon');h.g.level=level;h._childAllocation=0;h.weaponResources();h.compare(0x4493c0,('real wrapper startup',level),(h.A,),receiver=0,meaningful=True)
 assert h.get(h.L+24)[0]==h.E and h.get(h.L+28)[0]==1000 and h.get(h.E)[0]==0x50dfd4
 h.compare(0x4145b0,('enter actual Ground HOME',level));assert h.get(h.L+28)[0]==h.stateIDs['LS_HOME']
 for frame in range(3):h.g.tick+=3001;h.compare(0x4493c0,('HOME override no automatic firing',level,frame),(h.A,),receiver=0,meaningful=True)
print('PASS',h.calls,h.eventCount)
# Actual parent startup creates the actor through its exact six-argument
# service, then the genuine GroundCannon callback constructs it immediately.
# All28 source parents are used, not fabricated GroundCannon WWD placements.
import json,hashlib
retail=[]
for row in json.load(open(h.WORK/'inventory.json'))['records']:
 h.sceneMode=False;h.weaponFresh('cannon');h.g.level=row['level'];h._childAllocation=0;h.fireCreation=True;h.weaponResources();h.parentProfile(row);h.capture=True
 h.compare(0x474bc0,('actual parent child startup',row['level'],row['index']),receiver=h.PUNK_PRIVATE)
 assert h.get(h.PUNK_PRIVATE+0x408)[0]==h.A and h.get(h.L+24)[0]==h.E and h.get(h.L+28)[0]==1000
 mirrored=bool(h.get(h.PUNK_ACTOR+64)[0]&2);h.capture=False;h.compare(0x414640,('actual source parent fire request',row['level'],row['index']))
 made=False
 for frame in range(90):
  h.capture=frame in(0,10,20);h.g.tick+=17;h.compare(0x4493c0,('retained real firing',row['level'],row['index'],frame),(h.A,),receiver=0,meaningful=True);made|=h.get(h.GL+24)[0]==h.GP
  if h.get(h.L+28)[0]==h.stateIDs['LS_HOME']:break
 assert made and h.get(h.E+88)[0]==1 and h.get(h.L+28)[0]==h.stateIDs['LS_HOME']
 assert h.get(h.GP+80,2)!=[0,0] and h.get(h.GP+64,2)==[0,0]
 h.capture=True;h.realCollision=True;world=h.retailWorld(row['level']);grid=h.setupSpatial(row['worldWidth'],row['worldHeight']);h.compare(0x4c9320,('source scene insert fired ball',row['index']),(h.GEM,),receiver=h.CONTAINER);hit=None;terminal=None
 for tick in range(900):
  h.capture=tick in(0,10,50) or tick%150==0;h.g.tick+=17;h.compare(0x414b20,('actual retail tile cannonball flight',row['level'],row['index'],tick),(h.GEM,),receiver=0,meaningful=True)
  if h.get(h.GP+0x120)[0]&0x10000 and hit is None:hit=tick
  if h.get(h.GEM+8)[0]&0x10000:
   h.capture=True;h.compare(0x4c8fc0,('source active collision deletion',row['index']),(0,),receiver=h.CONTAINER);terminal='collision';break
  h.capture=tick%150==0;h.compare(0x4d4d10,('source camera residency flight',row['index'],tick),tuple(h.get(h.A+76,2)),receiver=grid)
  if not h.get(h.GEM+8)[0]:terminal='residency20';break
 assert terminal and h.get(h.GEM+8)[0]==0 and h.get(h.GL+24)[0]==0,(row['level'],row['index'],tick,h.get(h.GEM+76,2))
 h.realCollision=False;h.capture=True
 # Ground has no linked parent token or automatic ownership cleanup;29/30
 # are the inherited no-op slots. Parent private408 retains its child.
 for state in(29,30):
  h.put(h.L+28,[state]);h.compare(0x4493c0,('ground29/30 reset ownership',row['level'],row['index'],state),(h.A,),receiver=0,meaningful=True);assert h.get(h.PUNK_PRIVATE+0x408)[0]==h.A
 h.put(h.L+28,[h.stateIDs['LS_HOME']]);h.g.tick+=100000;h.compare(0x4493c0,('ground HOME remains silent',row['level'],row['index']),(h.A,),receiver=0,meaningful=True);assert h.get(h.E+88)[0]==1
 retail.append({'level':row['level'],'parentID':row['words'][0],'parentIndex':row['index'],'mirrored':mirrored,'creation':h.get(h.A+76,2),'firingFrames':frame+1,'ballFrames':tick+1,'collisionFrame':hit,'terminal':terminal,'parentRetainsChild':True,'tileProfile':world})
 h.fireCreation=False;h.sceneMode=False
print('PASS actual28 parent/fire/retail collision/terminal histories',h.calls,h.eventCount,flush=True)
# Directed ordinary Source ABI/lifecycle and both firing-mode bodies. Retail
# GroundCannon has no vertical ANI binding; compare its actual null selection
# separately from explicit caller-published vertical firing sequence profiles.
for state in(0,29,30,1000,h.stateIDs['LS_HOME'],h.stateIDs['LS_FIRING'],h.stateIDs['LS_VERTFIRING']):
 for n in range(6):
  h.sceneMode=False;h.weaponFresh('cannon');h.g.level=2 if n%2 else 8;h._childAllocation=0;h.fireCreation=False;h.weaponResources();h.capture=False;h.compare(0x449480,('lifecycle ctor',state,n),(h.A,),meaningful=True);h.put(h.L+28,[state]);h.compare(0x4493c0,('whole facade lifecycle',state,n),(h.A,),receiver=0,meaningful=True)
for level in(2,8):
 for facing in(0,2):
  h.weaponFresh('cannon');h.g.level=level;h._childAllocation=0;h.weaponResources();h.compare(0x4493c0,('vertical null startup',level,facing),(h.A,),receiver=0,meaningful=True);h.put(h.E+112,[1]);h.compare(0x414640,('actual zero vertical ANI selector',level,facing));assert h.get(h.E+80)[0]==0
  for i in range(8):h.compare(0x4493c0,('actual null vertical ANI update',level,facing,i),(h.A,),receiver=0,meaningful=True)
  assert h.get(h.E+88)[0]==0
for vertical in(False,True):
 for facing in(0,2):
  for level in(2,8):
   h.weaponFresh('cannon');h.g.level=level;h._childAllocation=0;h.fireCreation=True;h.weaponResources();h.compare(0x4493c0,('both mode explicit profile startup',vertical,facing,level),(h.A,),receiver=0,meaningful=True)
   if facing:h.compare(0x414a60,('source facing request',vertical,facing,level))
   if vertical:h.put(h.E+80,[h.get(h.E+76)[0]]);h.put(h.A+0x148,[0,-500])
   h.put(h.E+112,[int(vertical)]);h.compare(0x414640,('source mode selector',vertical,facing,level));count=0
   for frame in range(90):
    h.g.tick+=17;before=h.get(h.E+88)[0];h.compare(0x4493c0,('retained explicit mode controller',vertical,facing,level,frame),(h.A,),receiver=0,meaningful=True);count+=int(not before and bool(h.get(h.E+88)[0]))
    if h.get(h.L+28)[0]==h.stateIDs['LS_HOME']:break
   assert count==1 and h.get(h.GL+24)[0]==h.GP and h.get(h.L+28)[0]==h.stateIDs['LS_HOME']
   h.fireCreation=False
# Exact unknown dispatch delegates the inherited no-state service. No state
# inference or replacement attack is accepted for absent table callbacks.
for state in(2000,2001,2018,2027,2032,2033):
 h.weaponFresh('cannon');h.resourceTokens.clear();h._childAllocation=0;h.compare(0x449480,('dispatch ctor',state),(h.A,),meaningful=True);h.put(h.E+88,[1]);h.compare(0x449590,('whole derived class dispatch',state),(state,))
# Clock wrapping cannot awaken Ground's source HOME override.
for now in(0,1,0x7fffffff,0x80000000,0xffffff00,0xffffffff):
 h.weaponFresh('cannon');h._childAllocation=0;h.weaponResources();h.compare(0x4493c0,('wrapped clock startup',now),(h.A,),receiver=0,meaningful=True);h.compare(0x4145b0,('wrapped clock HOME entry',now));h.g.tick=now;before=h.get(h.E+116,2);h.compare(0x4493c0,('wrapped clock HOME override',now),(h.A,),receiver=0,meaningful=True);assert h.get(h.E+116,2)==before
for mode in(0,1,2,3,0xffffffff):
 h.weaponFresh('cannon');h._childAllocation=0;h.compare(0x449480,('private destroy ctor',mode),(h.A,),meaningful=True);h.compare(0x484d90,('actual deleting scalar',mode),(mode,),meaningful=True)
h.weaponFresh('cannon');h._childAllocation=0;h.resourceTokens.clear();h.allocated=0;h.capture=False;h.unsafeCompare(0x4493c0,'unchecked Ground private allocation',(h.A,),receiver=0)
for f in(0x4146b0,0x4148b0):
 h.weaponFresh('cannon');h._childAllocation=0;h.resourceTokens.clear();h.fireCreation=True;h.created=0;h.put(h.E+88,[0]);h.capture=False;h.unsafeCompare(f,'unchecked CannonBall named creator/'+hex(f));h.fireCreation=False
corpus=h.dumpCorpus()
result={'originalSHA256':hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'wholeCalls':h.calls,'orderedFullBufferEvents':h.eventCount,'snapshotBytes':h.SIZE+0x30000,'sourceAddresses':len(h.m.executed),'unsafePrefixes':h.unsafeCases,'sanitizerReplays':corpus,'retailHistories':retail,'retailGroundRows':0,'retailPunkRatParents':28,'vt':'50dfd4/9words','class':'537818; inherited534bf8','privateWords':31,'registry':29,'callback':'4493c0','meaningfulReturns':['4493c0=1','449480=receiver','484d90=receiver']}
(h.WORK/'verification.json').write_text(json.dumps(result,indent=2));print('PASS',json.dumps({k:v for k,v in result.items()if k!='retailHistories'}))
