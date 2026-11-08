#!/usr/bin/env python3
"""Original complete save startup/reader/default player/lifetime round trips."""
import ctypes as C,itertools,json,struct
import save_load_runtime_helpers as h
for flags,nameSize,descSize,emailSize in itertools.product([0,4,0x104,0xffffffff],[0,1,6,31,32],[0,1,79,80,96],[0,1,79,80,96]):
 h.prepare();h.putBytes(h.DATA,b'N'*nameSize+b'\0');h.putBytes(h.DATA+0x200,b'D'*descSize+b'\0');h.putBytes(h.DATA+0x400,b'E'*emailSize+b'\0');h.compare(0x49a5a0,h.RECORDS,[h.DATA,h.DATA+0x200,h.DATA+0x400,flags],('record-init-quirks',flags,nameSize,descSize,emailSize))
for nameSize in[0,1,31,32]:
 h.prepare();h.putBytes(h.DATA+0x10,b'N'*nameSize+b'\0');h.compare(0x49a6d0,h.RECORDS,[h.DATA],('payload-name-bound',nameSize))
for fn in[0x49ad50,0x49adc0]:
 h.prepare();h.compare(fn,h.RECORDS,label=('bindings',hex(fn)))
for field in[0,1,2,0xffffffff]:
 for valid in[False,True]:
  h.prepare();h.put(h.RECORDS+8,[field]);h.compare(0x49a720,h.RECORDS,label=('frozen-reset',field,valid))
  if not valid:h.put(h.RECORDS+0x21c8,[123])
  h.compare(0x49a8f0,h.RECORDS,label=('import-validation',field,valid))
for fn,args in[(0x49bdb0,[0,0,0,0]),(0x49be50,[0]),(0x49bee0,[0]),(0x49bf30,[0]),(0x49b970,[])]:h.prepare();h.compare(fn,h.M,args,('empty',hex(fn)))
for history in range(12):
 h.prepare();h.putBytes(h.DATA,b'Player\0');record=h.compare(0x49bdb0,h.M,[h.DATA,0,0,history&4],('create-player',history));assert record
 h.putBytes(h.DATA,b'pLaYeR\0');assert h.compare(0x49bee0,h.M,[h.DATA],('case-find',history))==record
 assert h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],('duplicate',history))==0
 h.compare(0x49bf30,h.M,[record],('remove-player',history));assert not h.live[record]and h.get(h.M+0xc)[0]==0
print('PASS record/default validation, case-insensitive duplicate election and lifetimes',h.calls,h.eventCount,flush=True)
for cwd,windir,drive in itertools.product([b'',b'C:\\CLAW'],[b'',b'C:\\WINDOWS'],[3,5]):
 h.prepare();h.currentDirectory=cwd;h.windowsDirectory=windir;h.driveType=drive;h.files={};result=h.compare(0x49b840,h.M,[0x525618],('startup-absent',cwd,windir,drive))
 assert result==bool((cwd and drive!=5)or windir)
 if result:assert h.get(h.M+0xc)[0]==1;h.compare(0x49b950,h.M,label=('shutdown-after-default',cwd,windir,drive));assert h.get(h.M+0xc)[0]==0
print('PASS whole directory/startup/default-player branches',h.calls,h.eventCount,flush=True)
# Source writer→reader retained graphs across all45 checkpoint slots. Fixtures
# use the recovered49a990 score positions and actual immutable source weights.
weights=h.m.read_words(0x52d698,10);roundtrips=[]
for history in range(3):
 h.prepare();h.putBytes(h.DATA,b'Player\0');record=h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],('roundtrip-create',history));h.compare(0x49a720,record,label=('roundtrip-reset',history))
 for level in range(15):
  for kind in[1,2,3]:
   counts=[history+level+kind+i for i in range(10)];score=sum(a*b for a,b in zip(counts,weights))&0xffffffff;sub=[0,score,0,0,0,0,0]+counts;packet=[0]*44;packet[3:20]=sub;packet[20:37]=sub;h.put(h.DATA,packet);h.compare(0x49a860,record,[level,h.DATA,kind],('roundtrip-slot',history,level,kind))
  h.put(h.DATA,sub);h.compare(0x49a800,record,[level,h.DATA],('roundtrip-best',history,level))
 assert h.compare(0x49a8f0,record,label=('valid45-slot-before-save',history))==1
 plain=h.readBytes(record+4,0x2644);h.compare(0x49bbc0,h.M,label=('roundtrip-save',history));cipher=h.files[b'CLAW.USR'];roundtrips.append(cipher);h.compare(0x49b970,h.M,label=('roundtrip-clear',history));h.put(h.M+0x40,[100+history]);assert h.compare(0x49b9a0,h.M,label=('roundtrip-load-version-mismatch',history))==1
 node=h.get(h.M+4)[0];loaded=h.get(node+8)[0];assert h.readBytes(loaded+4,0x2644)==plain and h.get(h.M+0x28)[0]==100+history
 h.compare(0x49b950,h.M,label=('roundtrip-shutdown',history))
print('PASS all45 checkpoint source-native writer/read roundtrips and version correction',h.calls,h.eventCount,flush=True)
# Missing, empty, <=32-byte and malformed/nonmultiple payloads use complete
# source normal failure paths. Positive short reads are not pre-rejected.
for size in[0,1,7,31,32,33,63,64,96,128]:
 h.prepare();h.files[b'CLAW.USR']=bytes([0xa5])*size;h.compare(0x49b9a0,h.M,label=('bad/empty-file-size',size))
for corrupt,readPolicy,failOpen,failAt in[(None,0,None,None),('header',0,None,None),('payload',0,None,None),('extra',0,None,None),(None,1,None,None),(None,2,None,None),(None,3,None,None),(None,0,0,None),(None,0,None,0),(None,0,None,1)]:
 h.prepare();blob=bytearray(roundtrips[0])
 if corrupt=='header':blob[5]^=1
 if corrupt=='payload':blob[100]^=1
 if corrupt=='extra':blob+=b'X'
 h.files[b'CLAW.USR']=bytes(blob);h.readPolicy=readPolicy;h.failOpen=failOpen;h.failAt=failAt
 # Failed record allocation reaches unchecked receiver0 construction and is
 # covered as a prefix below, never a fabricated normal return.
 if failAt==1:continue
 h.compare(0x49b9a0,h.M,label=('load-domains',corrupt,readPolicy,failOpen,failAt))
# Whole startup admits an existing case-folded Player; non-Player save inserts
# the source default record. Existing duplicates cause reader failure without
# clearing/rolling back the already live records.
for case in['valid','case','no-player','duplicate','checksum-invalid']:
 h.prepare();blob=roundtrips[0]
 if case in('case','no-player'):
  target=h.BUFFER;h.putBytes(target,blob[32:]);h.compare(0x49c070,h.M,[target,len(blob)-32],('modify-payload-decode',case));h.putBytes(target+0x10,(b'pLaYeR'if case=='case'else b'Other')+b'\0');checksum=h.compare(0x49bf70,h.M,[target,len(blob)-32],('modified-payload-checksum',case));h.compare(0x49c030,h.M,[target,len(blob)-32],('modified-payload-encode',case));payload=h.readBytes(target,len(blob)-32)
  h.putBytes(target,blob[:32]);h.compare(0x49c070,h.M,[target,32],('modify-header-decode',case));h.put(target+4,[checksum]);h.compare(0x49c030,h.M,[target,32],('modify-header-encode',case));blob=h.readBytes(target,32)+payload
 if case=='duplicate':h.putBytes(h.DATA,b'Player\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],('preexisting-player',case))
 if case=='checksum-invalid':b=bytearray(blob);b[70]^=1;blob=bytes(b)
 h.files={b'C:\\CLAW\\CLAW.USR':blob};result=h.compare(0x49b840,h.M,[0x525618],('startup-file',case));assert result==(case!='duplicate')
 h.compare(0x49b950,h.M,label=('startup-file-cleanup',case))
print('PASS missing/corrupt/short/version/default/duplicate startup and complete cleanup graphs',h.calls,h.eventCount,flush=True)
# Declared count zero/overstated/max does not become a guessed header error.
for declared in[0,1,2,0x80000000,0xffffffff]:
 h.prepare();blob=roundtrips[0];target=h.BUFFER;h.putBytes(target,blob[:32]);h.compare(0x49c070,h.M,[target,32],('declared-count-decode',declared));h.put(target+12,[declared]);h.compare(0x49c030,h.M,[target,32],('declared-count-encode',declared));h.files[b'CLAW.USR']=h.readBytes(target,32)+blob[32:];result=h.compare(0x49b9a0,h.M,label=('declared-count',declared));assert result==(0 if declared==0 else 1);h.compare(0x49b970,h.M,label=('declared-count-cleanup',declared))
# A later invalid record leaves the earlier admitted Player live. Startup then
# fails its duplicate default creation rather than rolling that Player back.
h.prepare();h.putBytes(h.DATA,b'Player\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],label='partial-create-first');h.putBytes(h.DATA,b'Second\0');h.compare(0x49bdb0,h.M,[h.DATA,0,0,0],label='partial-create-second');h.compare(0x49bbc0,h.M,label='partial-write-two');blob=h.files[b'CLAW.USR'];h.compare(0x49b970,h.M,label='partial-clear-two');target=h.BUFFER;h.putBytes(target,blob[32:]);h.compare(0x49c070,h.M,[target,len(blob)-32],label='partial-payload-decode');h.putBytes(target+0x2644+16,b'\0');sum=h.compare(0x49bf70,h.M,[target,len(blob)-32],label='partial-checksum');h.compare(0x49c030,h.M,[target,len(blob)-32],label='partial-payload-encode');payload=h.readBytes(target,len(blob)-32);h.putBytes(target,blob[:32]);h.compare(0x49c070,h.M,[target,32],label='partial-header-decode');h.put(target+4,[sum]);h.compare(0x49c030,h.M,[target,32],label='partial-header-encode');h.files={b'C:\\CLAW\\CLAW.USR':h.readBytes(target,32)+payload};assert h.compare(0x49b840,h.M,[0x525618],label='partial-startup-no-rollback')==0 and h.get(h.M+12)[0]==1;h.compare(0x49b950,h.M,label='partial-final-cleanup')
# Stopped exact source exceptions/unchecked-null receiver prefixes. These are
# not counted as normal startup/load success, and no rollback is invented.
prefixes=0
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX
for kind in['read-throw','seek-throw','record-allocation-null','default-allocation-null']:
 h.prepare();h.files[b'CLAW.USR']=roundtrips[0];fn=0x49b9a0;args=[];h.prefix=True
 if kind=='read-throw':h.readPolicy=4
 if kind=='seek-throw':h.seekFailure=True
 if kind=='record-allocation-null':h.failAt=1
 if kind=='default-allocation-null':h.failAt=0;h.files={};fn=0x49b840;args=[0x525618]
 before=bytes(h.heap);old=h.state();h.events=[];h.currentRoot=fn;h.maps={};h.fileAlive=False;ok,_=h.entry(fn,h.M,args);assert not ok and h.ctx.fault in(1,3),(kind,h.ctx.fault);expected=h.canonical();ne=h.events[:];after=h.state();h.native=False;h.maps={};h.fileAlive=False;h.fileReleaseReturn=0;h.u.mem_write(h.BASE,before);h.u.mem_write(h.GS,h.globalSeed);h.restore(old);h.events=[]
 stopped=[]
 def nullReceiver(uc,at,size,_):
  if at in(0x49a5a0,0x49a6d0)and uc.reg_read(UC_X86_REG_ECX)==0:stopped.append(at);uc.emu_stop()
 hook=h.u.hook_add(UC_HOOK_CODE,nullReceiver)
 try:h.originalCall(fn,h.M,args)
 except Exception:pass
 else:raise AssertionError(('source failure prefix returned',kind))
 finally:h.u.hook_del(hook)
 assert h.canonical()==expected and h.events==ne and h.state()==after and bytes(h.u.mem_read(h.GS,h.GN))==h.globalSeed,('prefix',kind)
 h.native=True;prefixes+=1
# Known new roots have no hidden reads for null parameter guards.
for fn,args in[(0x49bee0,[0]),(0x49bf30,[0]),(0x49bdb0,[0,0,0,0]),(0x49be50,[0]),(0x49a5a0,[0,0,0,0]),(0x49a6d0,[0])]:h.prepare();h.compare(fn,0xdead0000,args,('null-guard-invalid-receiver',hex(fn)))
h.prepare();h.lc.maximumTraversal=3;h.put(h.M+4,[h.NODES]);h.put(h.NODES,[h.NODES,0,h.RECORDS]);h.putBytes(h.RECORDS+0x14,b'A\0');h.putBytes(h.DATA,b'B\0');ok,_=h.entry(0x49bee0,h.M,[h.DATA]);assert not ok and h.ctx.fault==4
h.prepare();out=h.U();assert not h.lib.claw_save_load_entry(0x49b840,h.M,None,0,C.byref(h.lc),h.loadDependency,None,C.byref(out))and h.lc.fault==2
print('PASS four stopped unsafe/exception prefixes, null guards and native runaway bound',h.calls,h.eventCount,flush=True)
report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','completeCalls':h.calls,'orderedSnapshots':h.eventCount,'all45CheckpointRoundtrips':len(roundtrips),'failurePrefixes':prefixes,'originalInstructionAddresses':[hex(a)for a in sorted(h.m.executed)if 0x400000<=a<0x500000]}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',h.calls,h.eventCount,len(report['originalInstructionAddresses']),flush=True)
