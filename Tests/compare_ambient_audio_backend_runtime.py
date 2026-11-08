#!/usr/bin/env python3
import ambient_audio_backend_runtime_helpers as h
for f,args,receiver,void in[(0x4f51c5,[h.VOICE],h.LIST,False),(0x4f5172,[],h.LIST,True),(0x4b3dc0,[50,0,0,1],h.VOICE,False),(0x4b3fe0,[0,1000,1],h.VOICE,False),(0x4b4b80,[],h.MANAGER,False),(0x4b4c10,[],h.MANAGER,False),(0x4b3fc0,[],h.VOICE,False),(0x4b4d80,[600],h.CONTROL,False)]:
 h.prepare();h.compare(f,args,receiver,('smoke',hex(f)),void)
print('PASS smoke original boundaries',flush=True)
# Complete retained MFC pooled-list ordering/ownership, reuse and RemoveAll.
for blockSize in(1,2,3,10,11,32):
 for profile in range(12):
  h.prepare();h.put(h.LIST+0x18,[blockSize]);nodes=[]
  for frame in range(24):
   if not nodes or frame%3:
    nodes.append(h.compare(0x4f51c5,[h.rng.getrandbits(32)],h.LIST,('list-add',blockSize,profile,frame)))
   else:
    i=h.rng.randrange(len(nodes));h.compare(0x4f5212,[nodes.pop(i)],h.LIST,('list-remove',blockSize,profile,frame),True)
  while nodes:h.compare(0x4f5212,[nodes.pop(h.rng.randrange(len(nodes)))],h.LIST,('list-drain',blockSize,profile),True)
  assert not h.get(h.LIST+4)[0]and not h.get(h.LIST+0x14)[0]and h.freed
  for frame in range(3):h.compare(0x4f51c5,[h.VOICE],h.LIST,('list-reallocate',blockSize,profile,frame))
  h.compare(0x4f5172,[],h.LIST,('list-remove-all',blockSize,profile),True)
# Standalone inverse volume validates actual full original CRT pow/FTOL bodies.
for value in list(range(-10099,10100,29))+[-10000,-6643,-1000,-1,0,1,1000,10000]:
 h.prepare();h.compare(0x4b3bf0,[value&0xffffffff],label=('inverse-original-CRT',value))
for method in(0x18,0x24,0x30,0x3c,0x40,0x44,0x48):
 for error in(0,1,0x80004005,0xffffffff):
  for mutation in range(4):
   for device in(0,1):
    h.prepare();h.failures[method]=error;h.mutation=mutation;h.put(h.MANAGER+0x78,[device]);h.compare(0x4b3dc0,[h.rng.randrange(101),h.rng.randrange(-100,101)&0xffffffff,h.rng.getrandbits(32),h.rng.choice([0,1,0xffffffff])],h.VOICE,('play-chain',method,error,mutation,device))
    for f,arg in[(0x4b3e30,None),(0x4b3e70,None),(0x4b3f70,None),(0x4b3fc0,None),(0x4b3d80,None),(0x4b3ef0,h.rng.getrandbits(32)),(0x4b40c0,h.rng.getrandbits(32)),(0x4b4160,h.rng.getrandbits(32))]:
     h.compare(f,[]if arg is None else[arg],h.VOICE,('voice-operation',f,error,mutation,device))
# Cancellation, allocation failure, timed vs immediate, all failure channels.
for n in range(320):
 h.prepare();h.put(h.BUFFER+4,[h.rng.choice([0,-14,-1000,-6643,-10000])&0xffffffff]);h.clockValues=[h.rng.getrandbits(32)];h.failAlloc=n%7==0;h.failures[h.rng.choice([0x18,0x24,0x3c])]=h.rng.choice([0,1,0x80004005]);duration=h.rng.choice([0,1,18,1000,0x7fffffff,0x80000000,0xffffffff]);h.compare(0x4b3fe0,[h.rng.randrange(101),duration,h.rng.choice([0,1,0xffffffff])],h.VOICE,('timed-setup',n))
 if h.get(h.MANAGER+0xc)[0]:
  h.failAlloc=n%5==0;h.compare(0x4b3fe0,[h.rng.randrange(101),h.rng.choice([0,1,1000]),n%2],h.VOICE,('timed-rebind-cancel',n))
 h.compare(0x4b4c10,[],h.MANAGER,('manager-finalize',n))
# Actual ordinary interpolation, terminal stop, strict unsigned clock gating.
for n in range(96):
 h.prepare();h.clockValues=[h.rng.choice([0,100,0xfffffff0])];duration=h.rng.choice([1,18,1000]);h.compare(0x4b3fe0,[h.rng.randrange(101),duration,n%2],h.VOICE,('retained-create',n));start=h.clockValues[0]
 for frame,offset in enumerate([0,0,1,duration//2,duration-1,duration,duration+1]):
  h.clockValues=[(start+offset)&0xffffffff];h.clockIndex=0;h.compare(0x4b4b80,[],h.MANAGER,('retained-fade',n,frame))
 h.compare(0x4b4c10,[],h.MANAGER,('retained-stop',n))
# Multiple controls cache next before callbacks/destruction. Normal lists have
# type1 throughout; same-voice rebinding cancels only its own controllers.
for n in range(64):
 h.prepare();h.clockValues=[100];h.compare(0x4b3fe0,[0,1000,1],h.VOICE,('multi-first',n));h.compare(0x4b3fe0,[50,500,0],h.VOICE2,('multi-second',n))
 h.compare(0x4b3fe0,[75,750,0],h.VOICE,('multi-rebind',n))
 for time in(100,101,350,600,900,1100):h.clockValues=[time];h.clockIndex=0;h.compare(0x4b4b80,[],h.MANAGER,('multi-update',n,time))
 h.compare(0x4b4c10,[],h.MANAGER,('multi-stop',n))
print(f'PASS {h.calls} whole source calls / {h.eventCount} ordered heap/globals/clock/ownership events',flush=True)
import ambient_audio_backend_joined_helpers as joined
records=h.json.loads((h.ROOT/'work/sound-trigger-agent/level1-records.json').read_text());actual=[r for r in records if r['strings'][1]in('AmbientSound','GlobalAmbientSound','SpotAmbientSound')];assert len(actual)==15
for row in actual:
 joined.prepare();callback=joined.sourceRecord(row);joined.compare(callback,[joined.ACTOR],label=('actual-Level1-ambient-create',row['index'],row['strings'][1]))
 x,y=row['words'][5:7]
 for frame,(xx,yy)in enumerate([(x,y),(x,y),(x+100,y),(x+640,y),(x+1000,y),(x,y),(x,y)]):
  h.clockValues=[100+frame*250];h.clockIndex=0;joined.sg.stageDelta=250
  joined.compare(0x4025c0,[xx,yy],joined.AMBIENT,('actual-retained-ambient/backend',row['index'],frame),True)
 if row['strings'][1]=='SpotAmbientSound':h.put(joined.LOGIC+0x1c,[30]);joined.compare(callback,[joined.ACTOR],label=('actual-spot-remove',row['index']))
 joined.compare(0x402270,[],joined.AMBIENT,('actual-manager-clear',row['index']),True)
print(f'PASS {joined.joinedCalls} joined calls / all15 actual ambient records with real source pooled lists, physical calls, clock and fades',flush=True)
# Preserve invalid-allocation and source nonadvancing-loop prefixes separately.
h.nativeOverride=None;h.extraGlobals=None
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
prefixes=0
for kind in('list-null-block','list-zero-blocksize','cancel-kind-mismatch','cancel-rebind-kind-mismatch','zero-fade-duration','fade-division-overflow'):
 h.prepare();fn=0x4f51c5;receiver=h.LIST;args=[h.VOICE];stop=0x4f5ac1;repeats=1
 if kind=='list-null-block':h.failAlloc=True
 elif kind=='list-zero-blocksize':h.put(h.LIST+0x18,[0]);stop=0x4f56ca
 elif kind in('zero-fade-duration','fade-division-overflow'):
  fn=0x4b4d80;receiver=h.CONTROL;args=[101];stop=0x4b4dbd
  h.put(h.CONTROL+0x18,[0x80000000 if 'overflow'in kind else 0,0,0xffffffff if 'overflow'in kind else 0,100])
 else:
  h.put(h.MANAGER+0xc,[h.CONTROL+4,h.CONTROL+4]);h.put(h.CONTROL+0xc,[2]);fn=0x4b4c80;receiver=h.MANAGER+0xc;args=[h.VOICE,1];stop=0x4b4c9b;repeats=2
  if kind=='cancel-rebind-kind-mismatch':fn=0x4b3fe0;receiver=h.VOICE;args=[0,1000,1]
 before=bytes(h.heap);h.events=[];old=(h.cursor,h.freed[:],h.clockIndex);result=h.C.c_uint32();aa=(h.C.c_uint32*len(args))(*args)
 assert not h.lib.claw_ambient_audio_backend_entry(fn,receiver,aa,len(args),h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))and h.ctx.fault==(3 if 'mismatch'in kind else 2 if kind in('zero-fade-duration','fade-division-overflow')else 1)
 expected=bytes(h.heap);ne=list(h.events);after=(h.cursor,h.freed[:],h.clockIndex);h.native=False;h.u.mem_write(h.BASE,before);h.u.mem_write(h.GLOBAL_START,h.seedGlobals);h.cursor,h.freed,h.clockIndex=old;h.events=[];observed=[0]
 def prefixHook(u,address,size,_):
  if address==stop:
   observed[0]+=1
   if observed[0]==repeats:u.emu_stop()
 hook=h.u.hook_add(UC_HOOK_CODE,prefixHook);h.u.mem_write(h.m.stack,h.struct.pack('<I',h.m.stop)+h.struct.pack('<'+'I'*len(args),*args));h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.reg_write(UC_X86_REG_ECX,receiver);h.u.emu_start(fn,h.m.stop,count=500000);h.u.hook_del(hook)
 assert observed[0]==repeats and h.u.reg_read(UC_X86_REG_EIP)==stop and bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and h.events==ne and(h.cursor,h.freed,h.clockIndex)==after,(kind,'whole source prefix')
 h.native=True;prefixes+=1
addresses={a for a in h.m.executed if 0x400000<=a<0x550000 and a not in(0x4f63ec,0x4f6428,0x4b4ed0,0x4a3050)}
report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','completeCalls':h.calls,'orderedSnapshots':h.eventCount,'joinedCalls':joined.joinedCalls,'actualAmbientRecords':len(actual),'failurePrefixes':prefixes,'originalInstructionAddresses':[hex(a)for a in sorted(addresses)]}
(h.WORK/'verification.json').write_text(h.json.dumps(report,indent=2)+'\n')
print(f'PASS FINAL {h.calls} complete original calls / {h.eventCount} ordered snapshots / {len(addresses)} original instruction addresses / {prefixes} failure prefixes',flush=True)
h.prepare();before=bytes(h.heap);result=h.C.c_uint32()
assert not h.lib.claw_ambient_audio_backend_entry(0x4b45f0,h.VOICE,None,0,h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))and not h.ctx.fault and bytes(h.heap)==before
assert not h.lib.claw_ambient_audio_backend_entry(0x4b3dc0,h.VOICE,None,4,h.C.byref(h.ctx),h.dependency,None,h.C.byref(result))and h.ctx.fault==2 and bytes(h.heap)==before
print('PASS unsupported/malformed ABI checks, separate from original parity',flush=True)
