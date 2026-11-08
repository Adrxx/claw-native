"""Whole original default movie child and bounded807c controller proof."""
import itertools,json
import booty_progression_helpers as h
entryCases=((0x40b6a0,(h.APP,1,3)),(0x40b720,(3,)),(0x40b740,()),(0x40b780,()),(0x40b7a0,()),(0x40b7c0,()),(0x40b700,()),(0x40b7d0,(13,0)),(0x40b330,()),(0x42b140,(0,)),(0x42b4b0,()),(0x42d4a0,()),(0x42d4c0,()),(0x40af20,()),(0x40af30,(2,)),(0x40af40,(1,2)),(0x40af50,(1,2,3)),(0x40af90,()),(0x40afa0,(1,)),(0x40afc0,()),(0x48f180,()),(0x4ca930,()),(0x48d320,(2,)),(0x4bd240,()),(0x4bd250,()),(0x4ce8b0,()),(0x4bb030,()),(0x426e30,(0,0x807c,0)))
void=(0x40b700,0x40afc0,0x48f180,0x42d4a0,0x42d4c0)
for seed in range(12):
 for f,args in entryCases:
  h.fresh();h.capture=seed==0
  receiver=h.OWNER if f==0x40b330 else h.APP if f in(0x42b140,0x426e30)else h.HOLDER if f==0x4ca930 else h.CHILD
  h.compare(f,(hex(f),seed),args,receiver=receiver,meaningful=f not in void)
h.capture=False
# Whole original movie table: all14 retail level arguments plus signed/index16.
for level,exists,init,opened,extra,palette,target in itertools.product((-2,-1,0,*range(1,15),15,16,0x7fffffff,0x80000000),range(2),range(2),range(2),range(2),range(2),range(2)):
 h.fresh(level);h.movieExists=exists;h.movieInit=init;h.movieOpen=opened
 if not extra:h.put(h.SC+32,[0])
 if not palette:h.put(h.PAL,[0])
 if not target:h.put(h.TARGET+0x42c,[0])
 h.compare(0x42b140,('movie branch',level,exists,init,opened,extra,palette,target),(level&0xffffffff,),receiver=h.APP)
for level in (-2,-1,0,1,14,15,0x80000000):
 h.fresh();h.put(h.APP+0x9c,[1]);h.compare(0x42b140,('alternate movie gate',level),(level&0xffffffff,),receiver=h.APP)
# Resource failures incl composed unchanged48f0d0 and40b5c0 bodies.
for level in range(1,15):
 for resource in (0,1,2,3,4,0xffffffff):
  h.fresh(level);h.ctx.composeBase=1;h.resource=resource;h.compare(0x40b6a0,('source base init',level,resource),(h.APP,level,3))
 for vt in (0x50b43c,0x50b544):
  h.fresh(level);h.ctx.composeBase=1;h.resource=0xffffffff;h.put(h.CHILD,[vt]);h.compare(0x40b330,('source base constructor joined',level,hex(vt)),receiver=h.OWNER)
# Default movie publication: frame and handled inputs queue at most once.
for key in (0,1,13,27,32,65,0xffffffff):
 h.fresh();h.compare(0x40b7d0,('first key',key),(key,0xdeadbeef));h.compare(0x40b740,('first frame after key',key));assert h.get(h.CHILD+0x154)==[1]
 for i in range(3):h.compare(0x40b740,('latched frame',key,i));assert not h.events
# Result mode2 defers actual application commands, preserves exact ordering.
for level,previous,mode,completed,saved in itertools.product(range(1,15),range(2),(1,3),range(2),range(2)):
 h.fresh(level);h.put(h.CHILD,[0x50b494]);h.previousPresent=h.PREVIOUS if previous else 0;h.put(h.BASE+0xf010,[0x40af90 if mode==3 else 0x4bd250]);h.put(h.PREVIOUS+0x258,[saved,completed]);h.compare(0x40b330,('result exit',level,previous,mode,completed,saved),receiver=h.OWNER)
 posts=[e[2][2]for e in h.events if e[0]==0x546d50];expected=[]if not previous or mode!=3 else [0x8023]if saved else [0x8021]if completed else[0x8036,0x8075];assert posts==expected;assert h.get(h.OWNER+0x158)==[1]
# Retained movie→story→results→request; next-child methods explicit addressed services.
for level in range(1,15):
 h.fresh(level);h.ctx.composeBase=1;h.resource=0xffffffff;h.capture=True
 h.compare(0x40b6a0,('retained init',level),(h.APP,level,3));h.compare(0x40b720,('retained enter',level),(3,));h.compare(0x40b740,('retained publish',level));assert [e[2][2]for e in h.events]==[0x807c]
 h.compare(0x426e30,('retained first807c',level),(0,0x807c,0),receiver=h.APP);assert h.get(h.NEW)==[0x50b544]and h.get(h.NEW+24)==[3]
 h.allocation=h.BASE+0x16000
 h.compare(0x426e30,('retained story807c',level),(0,0x807c,0),receiver=h.APP);assert h.get(h.allocation)==[0x50b494]and h.get(h.allocation+24)==[1]
 h.compare(0x426e30,('retained result807c',level),(0,0x807c,0),receiver=h.APP);assert [e[2][2]for e in h.events if e[0]==0x546d50]==[0x8036,0x8075]
 h.capture=False
# Queued repeat after mode2 publication follows source footer on existing child.
# Explicit inert next-child destructor transport preserves the released storage;
# this proves the instruction order under that profile, not allocator safety.
for level,compose in itertools.product(range(1,15),range(2)):
 h.fresh(level);h.ctx.composeBase=compose;h.put(h.CHILD,[0x50b494]);h.put(h.OWNER+0x158,[1]);h.compare(0x426e30,('already-sent result source footer',level,compose),(0,0x807c,0),receiver=h.APP)
 assert h.get(h.OWNER+0x154)==[h.CHILD]and h.get(h.CHILD)==[0x50b4ec]
# Rejected owner readiness and failed mode report use original full426e30 entry.
for modeFunction in (0x40af90,0x4bd240,0x4bd250,0x4bb030):
 h.fresh();h.put(h.OWNER,[h.BASE+0xf800]);h.put(h.BASE+0xf810,[modeFunction]);before=h.raw(True);h.compare(0x426e30,('rejected807c',modeFunction),(0,0x807c,0),receiver=h.APP);assert h.raw(True)==before
h.fresh();h.put(h.CHILD,[h.BASE+0xf800]);h.put(h.BASE+0xf810,[0x4bb030]);h.compare(0x426e30,'unsupported child mode',(0,0x807c,0),receiver=h.APP);assert h.events[-1][:3]==(0x429e10,h.APP,(0x8005,0x6a8))
# Actual readiness, cleanup/null-resource and handled input boundaries.
for ready,hasPalette,hasSound in itertools.product(range(2),repeat=3):
 h.fresh();h.renderReady=ready
 if not hasPalette:h.put(h.CHILD+44,[0])
 if not hasSound:h.put(h.SOUND+44,[0])
 for f,a in ((0x40b780,()),(0x40b7a0,()),(0x40b7c0,()),(0x48d320,(2,)),(0x40afa0,(1,))):h.compare(f,('cleanup',ready,hasPalette,hasSound,f),a)
for vt in (0x50b43c,0x50b544):
 h.fresh();h.put(h.CHILD,[vt]);h.allocation=0;h.unsafe(0x40b330,'null child allocation',receiver=h.OWNER)
report=dict(wholeOriginalCalls=h.calls,orderedFullSnapshots=h.eventCount,originalAddresses=len(h.m.executed),unsafePrefixes=h.unsafeCases,retained14LevelHistories=True,sourceCorrection='default movie mode3→story mode1→results mode2; initializer/enter receive old mode, not old pointer',missing=['40b860/40bca0/story lifecycle','40d470/40dca0/results counters/draw/lifecycle','application8021/8036/8075 branches and final next-level reload'],transports='base composition original48f0d0/40b5c0; addressed next-child/UI/movie/resource/time/allocator adapters explicit')
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');h.saveCorpus();print('PASS',report,flush=True)
