"""Pinned source results/treasure/ordinary score-digit raw differential."""
import booty_results_helpers as h
import random,json,hashlib,struct
from pathlib import Path
r=random.Random(0x40d470)
# Result controller, meaningful shared UI setup, no inferred app command handler.
for level in range(1,15):
 h.fresh(level);counts=[(level*7+i*3)%23 for i in range(9)];maxima=[x+(i%3) for i,x in enumerate(counts)];h.put(0x534d08,counts);h.put(0x5381e0,maxima);h.compare(0x40d470,f'init-level{level}',(h.APP,level,1));h.compare(0x40dca0,'enter',(1,));
 actors=h.get(h.CHILD+348,9)
 for actor in actors:h.compare(0x498930,'counter-start',(actor,),0,cdecl=True)
 # Explicit source skip/count/shuffle stages, retaining heap allocations from actual initializer.
 for actor in actors:
  l=h.get(actor+108)[0];h.compare(0x40e020,'skip-key',(32,0));h.compare(0x498930,'skip-all',(actor,),0,cdecl=True)
 for actor in actors:
  l=h.get(actor+108)[0]
  for frame in range(180):
   h.put(0x53720c,[1000]);h.compare(0x498930,'retained-shuffle',(actor,),0,cdecl=True)
   if h.get(l+28)[0]==0x2331:break
  assert h.get(l+28)[0]==0x2331,('terminal',level,hex(h.get(l+28)[0]))
 h.compare(0x40dd50,'results-terminal-request');assert h.get(h.CHILD+340)[0]==1
 h.compare(0x40dd50,'repeated-terminal');h.compare(0x40df60,'results-paint');h.compare(0x40dcb0,'departure',(1,))
# No synthetic registry translation: states literal2329..2334 exactly.
for count in (0,1,2,11,99,1000,0xffffffff,0x80000000,0x7fffffff):
 for remaining in (0,1,count,0xffffffff,0x80000000):
  h.fresh();h.put(h.PRIVATE+144,[count,remaining]);h.writeBytes(h.PRIVATE+168,struct.pack('<d',4.0));h.compare(0x4995d0,'signed-interval',receiver=h.PRIVATE)
for i in range(240):
 h.fresh();h.put(h.PRIVATE+144,[r.randrange(1,1000000),r.getrandbits(32)]);h.writeBytes(h.PRIVATE+168,struct.pack('<d',r.uniform(-100,100)));h.compare(0x4995d0,'random-interval',receiver=h.PRIVATE)
for state in (0,1,4,5,6,0x2329,0x232a,0x232b,0x232c,0x232d,0x232e,0x232f,0x2330,0x2331,0x2332,0x2333,0x2334,0xffffffff):
 for delta in (0,1,16,75,300,0x80000000,0xffffffff):
  h.fresh();h.compare(0x40d470,'fixture-init',(h.APP,4,1));actor=h.get(h.CHILD+348)[0];l=h.get(actor+108)[0];p=h.get(l+24)[0]
  # Populate all generated groups for shuffle/fast-skip states through actual source helpers.
  h.compare(0x499450,'visual',(actor,),p);h.compare(0x499170,'numbers',(actor,),p)
  h.put(l+28,[state]);h.put(l+100,[25,25,25]);h.put(l+304,[300,50,60000]);h.put(l+172,[1]);h.put(0x52d4e0,[h.get(p+140)[0]if state in(5,0x2330)else 0xffffffff]);h.put(0x53720c,[delta]);h.compare(0x498930,'state-delta',(actor,),0,cdecl=True)
  h.put(l+28,[state]);h.put(l+304,[300]);h.put(l+100,[160,600]);h.put(actor+76,[0,0]);h.compare(0x498f90,'treasure-state-delta',(actor,),0,cdecl=True)
# Full natural count-up without key skip; actual source ordering nine rows.
h.fresh();h.put(0x534d08,[12,2,1,3,1,2,1,1,2]);h.put(0x5381e0,[12,2,1,3,1,2,1,1,2]);h.compare(0x40d470,'natural-init',(h.APP,2,1));actors=h.get(h.CHILD+348,9)
for frame in range(800):
 h.put(0x53720c,[1000])
 for actor in actors:h.compare(0x498930,'natural-count',(actor,),0,cdecl=True)
 if all(h.get(h.get(a+108)[0]+28)[0]==0x2331 for a in actors):break
assert frame<799 and h.get(0x52d4e0)[0]==0xffffffff
h.compare(0x40dd50,'natural-request')
# Source composition with immutable retail assets and exact HUD stores.
for level in range(1,15):
 h.fresh(level);h.enableNumbers();h.enableAssets();h.put(0x534d08,[2,1,1,0,1,0,1,0,1]);h.put(0x5381e0,[2,1,1,0,1,0,1,0,1]);h.capture=True;h.compare(0x40d470,'retail-initializer',(h.APP,level,1));h.capture=False
 actors=h.get(h.CHILD+348,9)
 for frame in range(220):
  h.put(0x53720c,[1000]);h.put(0x5430c4,[33])
  for actor in actors:
   h.capture=level==1 and frame in(0,1,2,3)and actor==actors[0];h.compare(0x498930,'retail-retained',(actor,),0,cdecl=True);h.capture=False
  if all(h.get(h.get(a+108)[0]+28)[0]==0x2331 for a in actors):break
 assert frame<219
 for actor in actors:
  p=h.get(h.get(actor+108)[0]+24)[0];h.capture=level==1;h.compare(0x40db10,'counter-delete',(1,),p);h.capture=False
 assert h.get(0x53cac4)[0]==0
# Retained moving TreasureLogic child, including stage delta distinct from ANI.
h.fresh();h.enableAssets();h.put(h.PRIMARY+100,[160,55]);h.put(h.PRIMARY+304,[100]);h.put(h.PRIMARY+28,[0]);h.put(h.ACTOR+76,[0xffffffe0,0]);h.put(h.ACTOR+368,[h.assetTokens[b'BOOTY_TREASURE_COINS']]);h.capture=True
for i in range(40):
 h.put(0x53720c,[17]);h.put(0x5430c4,[9]);value=h.compare(0x498f90,'retail-moving-child',(h.ACTOR,),0,cdecl=True)
 if not value:break
h.capture=False;assert not value and h.get(h.ACTOR+8)[0]&0x10000
# Repeated input, mode distinctions, missing title/resource and exact four-argument palette/fade.
for custom in(0,1):
 for fade in(0,1):
  for paletteMode in(0,1,0xffffffff):
   h.fresh();h.put(h.APP+304,[custom]);h.capture=True;h.compare(0x48ffa0,'shared-background',(h.CHILD+0x500,1,paletteMode,fade));h.capture=False
for f,args in((0x40de90,()),(0x40df00,()),(0x48f470,(0,)),(0x48f470,(0xffffffff,)),(0x490370,()),(0x40b040,()),(0x40b020,(1,))):
 h.fresh();h.enableNumbers();h.capture=True;h.compare(f,'UI-lifetime',args,meaningful=f not in(0x40b040,));h.capture=False
for key in(0,12,13,27,32,0xffffffff):
 h.fresh();h.compare(0x40e020,'input-key',(key,0xffffffff))
for fail in(0,1,2,3):
 h.fresh();h.resource=fail;h.compare(0x40d470,'resource-prefix',(h.APP,2,1))
for fail in(1,2,12):
 h.fresh();h.enableNumbers();h.enableAssets();h.allocationFail=fail;h.unsafe(0x40d470,'allocation-prefix'+str(fail),(h.APP,1,1))
h.fresh();h.enableNumbers();h.enableAssets();h.createFail=1;h.unsafe(0x40d470,'symbol-creation-prefix',(h.APP,1,1))
h.fresh();h.enableNumbers();h.enableAssets();h.createFail=10;h.compare(0x40d470,'counter-creation-skips-row',(h.APP,1,1));assert 0 in h.get(h.CHILD+348,9)
# Scene owns every actor, and caches node-next through actor/private/group teardown.
h.fresh();h.enableNumbers();h.enableAssets();h.compare(0x40d470,'teardown-init',(h.APP,1,1));actors=[]
for token in range(h.BASE+0x30000,h.allocationCursor,16):
 if h.get(token)[0]==0x5137f0:actors.append(token)
nodes=[h.alloc(12,True)for a in actors]
for i,(node,actor)in enumerate(zip(nodes,actors)):h.put(node,[nodes[i+1]if i+1<len(nodes)else 0,nodes[i-1]if i else 0,actor])
h.put(h.CONTAINER+20,[nodes[0],nodes[-1],len(nodes),0,0]);h.capture=True;h.compare(0x4c89f0,'all-source-scene-actors-clear',receiver=h.CONTAINER,meaningful=False);h.capture=False
assert h.get(0x53cac4)[0]==0 and h.get(h.CONTAINER+20,5)==[0]*5
h.fresh();h.paintMutation=True;h.capture=True;h.compare(0x490370,'BeginPaint-owner-mutation');h.capture=False;h.paintMutation=False
h.fresh();h.put(h.PRIVATE+144,[1,1]);h.writeBytes(h.PRIVATE+168,struct.pack('<d',0.0));h.unsafe(0x499630,'zero-interval',(h.ACTOR,),h.PRIVATE)
h.saveCorpus()
print('PASS',h.calls,'whole original calls;',h.eventCount,'ordered full heap events;',len(h.m.executed),'executed source addresses')
(h.WORK/'verification.json').write_text(json.dumps(dict(calls=h.calls,events=h.eventCount,addresses=len(h.m.executed),rawBytes=h.SIZE+0x30000,levels=14,fixtureStats='directed source-statistics profiles, not full played-level totals',unsafePrefixes=h.unsafeCases,sanitizerCases=len(h.corpus),retailAssets=h.assetInventory,transport='CString/resource/creation/audio/renderer/OS explicit; actual frozen HUD/ANI/image composition exercised'),indent=2)+'\n')
