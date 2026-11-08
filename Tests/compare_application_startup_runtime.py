"""Ordinary whole bootstrap source decisions, explicit helper endpoints."""
import application_startup_helpers as h
import gzip,hashlib,json,struct
commands=[b'',b'SINGLE',b'RACING',b'MENU',b'NOSHELL',b'NANI',b'8BIT',b'16BIT',b'USER:Player',b'USER:Jane_Doe',b'USER:Jane+Doe',b'SINGLE RACING MENU NANI 8BIT 16BIT USER:Jane_Doe']
#Read literal command names from the pinned executable, avoiding invented switches.
h.fresh();commands=[b'']+[h.text(x)for x in(0x5256a8,0x5256a0,0x525698,0x525690,0x52568c,0x525684,0x52567c)]+[b'USER:Player',b'USER:Jane_Doe',b'USER:Jane+Doe',b'USER:Jane_Doe extra']
commands.append(b' '.join(commands[1:8])+b' USER:Player')
for seed in range(5):
 for command in commands:
  h.fresh(seed,command,old=seed%2==1);h.capture=seed==0
  h.compare(('ordinaryCommand',seed,command.decode('ascii')))
h.capture=False
failures=[0x4b5c50,0x42cab0,0x493c20,0x4b3240,0x430590,0x49b840,0x428c40]
for seed in range(3):
 for f in failures:
  h.fresh(seed,old=True);h.failure[f]=0;h.capture=seed==0;assert h.compare(('admissionFailure',seed,hex(f)))==0
 #Source8-bit admission failure continues;16-bit retry failure is reported.
 for high,results in [(0,[0]),(1,[0,0]),(1,[0,1])]:
  h.fresh(seed);h.options[0x5257dc]=high
  oldEffect=h.effect;index={True:0,False:0}
  def effect(f,t,a,b):
   if f==0x700018:index[h.native]+=1;return results[min(index[h.native]-1,len(results)-1)]
   return oldEffect(f,t,a,b)
  h.effect=effect;h.capture=seed==0;result=h.compare(('graphicsAdmission',seed,high,results));assert result==(0 if high and results[-1]==0 else 1);h.effect=oldEffect
 for compatible in(0,1):
  h.fresh(seed);h.failure[0x4b72e0]=0;h.put(h.APP+0x104,[compatible]);h.capture=seed==0;h.compare(('archiveOpenFailure',seed,compatible))
  if compatible:h.fresh(seed);h.failure[0x4b72e0]=0;h.failure[0x42ce90]=0;h.put(h.APP+0x104,[1]);h.compare(('archiveFallbackFailure',seed))
 for stateResults in([0,1],[0,0]):
  h.fresh(seed,h.text(0x52568c));h.failure[(0x428c40,1)]=stateResults[0];h.failure[(0x428c40,2)]=stateResults[1];h.capture=seed==0;assert h.compare(('state4Fallback',seed,stateResults))==stateResults[1]
h.capture=False
for key in [0x525850,0x525840,0x52582c,0x525818,0x5257fc,0x5257ec,0x5257dc,0x5257c8,0x5257b4,0x525798,0x5256f4,0x525624,0x5255d4,0x5255c0]:
 h.fresh(23);h.options[key]=1;h.compare(('ordinaryOption',hex(key)))
for runs,movies,movie in [(0,0,0),(0,0,0x12340000),(1,1,0),(4,8,0)]:
 h.fresh(7);h.options[0x52589c]=runs;h.options[0x525890]=movies;h.failure[0x42b140]=movie;h.capture=True;h.compare(('mediaAdmission',runs,movies,movie))
for prior,legacy in [(b'Missing',b''),(b'Missing',b'Player'),(b'Player',b'')]:
 h.fresh(11);h.registry[0x525714]=prior;h.registry[0x52560c]=legacy;h.capture=True;h.compare(('retainedRegistrySelection',prior.decode(),legacy.decode()))
h.capture=False
for seed in range(3):
 h.fresh(seed);h.put(h.WIN+4,[0]);h.capture=True;assert h.compare(('windowAdmissionMissingHandle',seed))==0
 h.fresh(seed);h.context.archive=h.C.addressof(h.archive);h.capture=True;assert h.compare(('frozenArchiveFopenFailure',seed))==0;h.context.archive=None
for factor in (0,99,100,299,0xffffffff):
 h.fresh(factor);h.put(h.APP+0x9c,[1]);h.put(0x527130,[factor,factor,factor]);h.capture=True;assert h.compare(('ordinaryNaniFactors',factor))==1
for alias in ('timingCounter','publishedApplication','finalFactors'):
 h.fresh(17);peer=h.BASE+0x4d00;h.put(peer,[0]*77);h.put(peer+0x9c,[1]);h.put(h.APP+0x9c,[1]);h.capture=True
 def mutation(f,t,a):
  if f!=0x546df0:return
  if alias=='timingCounter'and h.timeIndex==1:h.put(h.APP+0x20,[7]);h.put(h.APP+0x28,[61])
  if alias=='publishedApplication'and h.timeIndex==5:h.put(0x5371fc,[peer])
  if alias=='finalFactors'and h.timeIndex==6:h.put(0x527130,[0xffffffff,100,99])
 h.mutation=mutation;assert h.compare(('clockCallbackAlias',alias))==1
for disabled in (0,1):
 for hr in (0,1,5):
  h.fresh(47);h.options[0x525850]=disabled;h.context.music=h.C.addressof(h.music);h.failure[0x546e74]=hr;h.capture=True;assert h.compare(('frozenMusicPhysicalAdmission',disabled,hr))==1;h.context.music=None
h.capture=False
report={'originalSha256':hashlib.sha256((h.ROOT/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'wholeEntry':'425730','wholeBytes':4465,'wholeCalls':h.calls,'orderedFullSnapshots':h.snapshots,'exactReplayCases':len(h.corpus),'composedInterval':['426546','4266e0'],'measuredBoundary':'whole425730+original4b8280/frozenGameTiming+selected-cache interval; three frozen archive fopen failures and six frozen music physical admissions; remaining helpers are exact addressed fixtures','sourceCodeAddresses':len([a for a in h.m.executed if 0x425730<=a<0x4268a1]),'limits':['no Windows registry/window/user-file access','whole retail REZ recursion and native initial state rendering are not measured by these boundary tests','ordinary returns only; source SEH throw paths not transported']}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
with gzip.open(h.WORK/'sanitizer-corpus.bin.gz','wb')as out:
 out.write(b'APST');out.write(h.pack(h.SIZE,h.IS,h.IN,len(h.corpus),len(h.OBJECTS)))
 for t,n in h.OBJECTS:out.write(h.pack(t,n))
 for label,value,before,expected,initial,events,profile in h.corpus:
  out.write(h.pack(value,len(initial),len(events),profile));out.write(before)
  for t,n in initial:out.write(h.pack(t,n))
  for f,t,a,v,mask,buffers,outputs,digest,patches in events:
   out.write(h.pack(f,t,len(a),v,mask,len(buffers),len(patches)));out.write(h.pack(*a));out.write(digest)
   for b,e in zip(buffers,outputs):out.write(h.pack(len(b)));out.write(b);out.write(e)
   for i,y in patches:out.write(struct.pack('<IB',i,y))
  out.write(expected)
print('PASS whole425730',h.calls,'calls /',h.snapshots,'full snapshots;',len(h.corpus),'exact replay cases',flush=True)
