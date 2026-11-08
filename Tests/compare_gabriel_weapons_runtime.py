"""Whole pinned original Gabriel weapon closure, real source asset profiles."""
import gabriel_weapons_helpers as h
h.composeCommon=True
for kind,ctor in(('cannon',0x446a70),('bomb',0x445ef0),('ball',0x414be0)):
 for n in range(12):
  h.capture=n<2;h.weaponFresh(kind);h.resourceTokens.clear();h._childAllocation=0;h.g.audioEnabled=n%2;h.put(h.A+0x40,[n%2*2]);h.put(h.A+0x170,[0 if n%3 else h.ROOTIMAGE]);h.put(h.A+0x104,[0 if n%3 else 42]);h.put(h.A+0x148,[[0,-500,500,-2147483648][n%4],n]);h.found=n%3!=0;h.compare(ctor,('whole ctor',kind,n),(h.A,),meaningful=True)
print('PASS constructors',h.calls,h.eventCount,flush=True)
for f in(0x414030,0x4145b0,0x4145f0,0x414640,0x414660,0x414860,0x414a60,0x446c20,0x446ca0,0x446d70,0x446e10,0x446eb0,0x446340,0x4463f0,0x446490,0x432550,0x432560):
 for n in range(20):
  h.capture=n<2;h.weaponFresh('bomb'if f in(0x432550,0x432560,0x446340,0x4463f0,0x446490)else'cannon');h._childAllocation=0;h.resourceTokens.clear();h.put(h.A+0x1a4,[n%2]);h.put(h.A+0x19c,[(n//2)%2]);h.put(h.A+0x40,[n%2*2]);h.put(h.E+0x78,[0 if n%2 else 2000]);h.put(h.E+0x74,[n*200]);h.put(h.E+0x70,[n%2]);h.put(h.E+0x8c,[(n//2)%2]);h.put(h.E+0x90,[(n//4)%2]);h.put(h.E+0x18c,[n%2]);h.put(h.E+400,[n%2]);h.put(0x53774c,[h.OTHER if n%3 else 0]);h.put(h.OTHER+0x518,[n%2,(n//3)%2,(n//5)%2]);h.put(h.OTHER+0x534,[n%2]);h.randomValues=[[-2,-1,0,1,2,3][n%6]];h.g.audioEnabled=n%2;h.put(h.A+0x148,[[0,-500,500,-2147483648][n%4]]);h.compare(f,('whole state',hex(f),n),(h.A,)if f==0x414030 else())
print('PASS states',h.calls,h.eventCount,flush=True)
for kind,ctor in(('cannon',0x446a70),('bomb',0x445ef0),('ball',0x414be0)):
 h.weaponFresh(kind);h._childAllocation=0;inventory=h.weaponResources();h.compare(ctor,('real ctor',kind),(h.A,),meaningful=True)
print('PASS real constructors',h.calls,h.eventCount,flush=True)
# Real firing marker joins creator->whole CannonBall init; no callback stand-in.
for vertical in(False,True):
 for direction in(-1,1):
  for n in range(4):
   h.capture=n<2;h.weaponFresh('cannon');h._childAllocation=0;h.fireCreation=True;inventory=h.weaponResources();h.compare(0x446a70,('retained cannon init',vertical,direction,n),(h.A,),meaningful=True);h.put(h.A+0x148,[direction*500,0]);h.put(h.A+0x14c,[0 if not vertical else -500]);h.compare(0x414860 if vertical else 0x414660,('fire entry',vertical,direction,n));made=False
   for tick in range(180):
    h.capture=n<2 and tick%25==0;h.g.tick+=17;h.compare(0x4148b0 if vertical else 0x4146b0,('real marker fire',vertical,direction,n,tick));made|=bool(h.get(h.GL+24)[0]==h.GP)
    if h.get(h.L+28)[0]==h.stateIDs['LS_HOME']:break
   assert made and h.get(h.L+28)[0]==h.stateIDs['LS_HOME'];assert h.get(h.GP+0x50,2)!=[0,0];assert h.get(h.GEM+0xd0)[0]==0x40
   h.capture=True;h.put(h.GL+28,[29]);h.compare(0x414b20,('whole child cleanup29',vertical,direction,n),(h.GEM,),receiver=0,meaningful=True)
   h.fireCreation=False
print('PASS marker->actual CannonBall',h.calls,h.eventCount,flush=True)
# Full actual class FSM and shadow-preserving inherited motion.
for kind in('cannon','bomb','ball'):
 for n in range(3):
  callback=h.weaponFresh(kind);h._childAllocation=0;h.fireCreation=kind=='cannon';inventory=h.weaponResources();h.put(h.A+0x170,[0]);h.capture=True;h.compare(callback,('whole wrapper startup',kind,n),(h.A,),receiver=0,meaningful=True)
  if kind=='cannon':h.put(h.OTHER+0x518,[1])
  if kind=='bomb':h.number(h.E+64,2000.);h.compare(0x446130,('real bomb inline retarget',n),(120+n*50,));h.put(h.OTHER+0x530,[5200])
  for tick in range(200):
   h.capture=tick%40==0;h.g.tick+=17;h.compare(callback,('whole retained facade/FSM',kind,n,tick),(h.A,),receiver=0,meaningful=True)
   if kind=='bomb'and h.get(h.A+8)[0]&0x10000:break
  if kind=='bomb':assert h.get(h.A+8)[0]&0x10000 and h.get(h.E+0x18c)[0]==1
  h.fireCreation=False
print('PASS source whole facades/FSM terminal',h.calls,h.eventCount,flush=True)
# Entire original4cbb60 executes on the original side, paired with frozen native
# collision. Controlled tile fixture is explicit and distinct from retail WWD.
collisionHistories=[]
for kind in('bomb','ball'):
 for direction in(-1,1):
  callback=h.weaponFresh(kind);h._childAllocation=0;h.fireCreation=False;h.weaponResources();h.realCollision=True;h.solidWorld();h.put(h.A+76,[280,220]);h.put(h.A+0x148,[direction*500,0]);h.put(h.A+0x170,[0]);h.capture=True;h.compare(callback,('whole collision creator',kind,direction),(h.A,),receiver=0,meaningful=True)
  if kind=='bomb':h.put(h.OTHER+0x530,[300]);h.compare(0x446130,('physical bomb target',direction),(direction*120,))
  hit=None
  for tick in range(900):
   h.capture=tick%60==0;h.g.tick+=17;h.compare(callback,('whole source collision flight',kind,direction,tick),(h.A,),receiver=0,meaningful=True)
   if h.get(h.E+0x120)[0]&0x10000 and hit is None:hit=tick
   if h.get(h.A+8)[0]&0x10000:break
  assert h.get(h.A+8)[0]&0x10000
  if kind=='ball':assert hit is not None
  else:assert h.get(h.E+0x18c)[0]==1
  collisionHistories.append({'kind':kind,'direction':direction,'frames':tick+1,'collision':hit,'position':h.get(h.A+76,2),'state':h.get(h.L+28)[0],'delete':True});h.realCollision=False
print('PASS collision whole flight/explosion/deletion',h.calls,h.eventCount,flush=True)
# Source raw lifecycle stores/free order and normal/failure wrapper prefixes.
for kind,callback in(('cannon',0x446550),('bomb',0x4459d0),('ball',0x414b20)):
 for state in(0,29,30,1000,h.stateIDs['LS_FALLING']if kind!='cannon'else h.stateIDs['LS_HOME']):
  for n in range(5):
   h.weaponFresh(kind,state);h._childAllocation=0;h.weaponResources();h.capture=n==0;h.compare({'cannon':0x446a70,'bomb':0x445ef0,'ball':0x414be0}[kind],('lifecycle valid constructor',kind,state,n),(h.A,),meaningful=True);h.put(h.L+28,[state]);h.compare(callback,('facade lifecycle',kind,state,n),(h.A,),receiver=0,meaningful=True)
 for mode in(0,1,2,3,0xffffffff):
  h.weaponFresh(kind);h._childAllocation=0;h.capture=True;h.compare(0x484d90,('raw generic deleting destructor',kind,mode),(mode,),meaningful=True)
# Original dereferences null creation/allocation. Native diagnoses after the
# identical already-written prefix and callback snapshots; no invented success.
for kind,callback in(('cannon',0x446550),('bomb',0x4459d0),('ball',0x414b20)):
 h.weaponFresh(kind);h._childAllocation=0;h.allocated=0;h.resourceTokens.clear();h.capture=False;h.unsafeCompare(callback,'null allocation/'+kind,(h.A,),receiver=0)
for f in(0x4146b0,0x4148b0):
 h.weaponFresh('cannon');h._childAllocation=0;h.resourceTokens.clear();h.fireCreation=True;h.created=0;h.put(h.E+88,[0]);h.capture=False;h.unsafeCompare(f,'null named CannonBall/'+hex(f));h.fireCreation=False
# Whole actual retail Cannon WWD profile from frozen original decoder, retaining
# real resources and the source boss/private handshake. Arena residency remains
# a distinct host acceptance requirement.
retailHistories=[]
for n in range(8):
 h.weaponFresh('cannon');h._childAllocation=0;h.fireCreation=True;inventory=h.weaponResources();row=h.retailCannonRecord();h.capture=True;h.compare(0x446550,('actual Level8 Cannon row startup',n),(h.A,),receiver=0,meaningful=True);assert h.get(h.E+0x5c)[0]==0xffffffce
 h.put(h.OTHER+0x51c,[n%2]);h.put(h.OTHER+0x518,[1])
 made=False;raised=False;homeFrames=0
 for tick in range(200):
  h.capture=tick%40==0;h.g.tick+=17;h.compare(0x446550,('actual WWD retained controller/fire',n,tick),(h.A,),receiver=0,meaningful=True);made|=h.get(h.GL+24)[0]==h.GP;raised|=bool(h.get(h.E+0x90)[0]);homeFrames+=h.get(h.L+28)[0]==h.stateIDs['LS_HOME']
 assert made and homeFrames and not h.get(h.OTHER+0x518)[0]
 if n%2:assert raised and not h.get(h.E+0x90)[0] and not h.get(h.OTHER+0x51c)[0]
 h.put(h.OTHER+0x534,[1]);h.capture=True;h.compare(0x446ca0,('actual controller reset handshake',n));assert h.get(h.E+0x8c,2)==[0,0]and not(h.get(h.OTHER+0x534)[0]&1)
 retailHistories.append({'recordID':row['words'][0],'profile':n,'frames':200,'createdBall':made,'raised':raised,'homeFrames':homeFrames,'resetConsumed':True});h.fireCreation=False
print('PASS8 actual WWD controller/fire/reset histories',h.calls,h.eventCount,flush=True)
# Directed unsigned source-clock endpoints and exact mirror sentinel/wrap gates.
for now in(0,1,0x7fffffff,0x80000000,0xffffff00,0xffffffff):
 for base in(0,1,0xffffff00,0xffffffff):
  for timeout in(0,1,3000,0xffffffff):
   h.weaponFresh('cannon');h.resourceTokens.clear();h.g.tick=now;h.put(h.E+0x74,[base,timeout]);h.capture=False;h.compare(0x4145f0,('scheduler wrapping',now,base,timeout))
for x in(0,1,0xffffffff,0x80000000,0x7fffffff):
 for flip in(0,2):
  h.weaponFresh('cannon');h.resourceTokens.clear();h.put(h.A+64,[flip]);h.put(h.A+0x148,[x]);h.put(h.E+56,[x,0,0x80000000,0]);h.put(h.A+0x118,[0x80000000,0,x,0]);h.put(h.A+0x128,[x,0,0x80000000,0]);h.put(h.A+0x138,[0x80000000,0,0x7fffffff,0]);h.compare(0x414a60,('mirror sentinel/wrap',x,flip))
report={'calls':h.calls,'events':h.eventCount,'addresses':len(h.m.executed),'unsafe':h.unsafeCases,'resources':inventory,'collisionHistories':collisionHistories,'retailHistories':retailHistories,'corpus':h.dumpCorpus(),'scope':'Complete registered Cannon/Bomb/CannonBall facades, specialized constructors/states and composed original Bullet/arching/FSM/ANI/motion; physical creation/resource/free/sound transport explicit. Controlled original collision tile fixture distinct from retail Level8 arena acceptance.'}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print('PASS final weapons',h.calls,h.eventCount,len(h.m.executed),'corpus',len(h.corpusCases),'unsafe',len(h.unsafeCases),flush=True)
