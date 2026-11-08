#!/usr/bin/env python3
"""Complete source save-file bytes, encryption and exact CFile write lifetime."""
import ctypes as C,itertools,json,struct
import save_file_runtime_helpers as h
for size in[0,1,2,3,7,15,16,31,32,33,63,64,127,128,255,256]:
 for seed in range(3):
  h.prepare();h.putBytes(h.DATA,bytes(h.rng.randrange(256)for _ in range(size)));h.compare(0x49bf70,h.M,[h.DATA,size],('checksum',size,seed));h.compare(0x49c030,h.M,[h.DATA,size],('xor',size,seed));h.compare(0x49c070,h.M,[h.DATA,size],('inverse',size,seed))
h.prepare();h.compare(0x49bf70,h.M,[0,0xffffffff],'null-checksum')
for limit in[0,1,2,3,4,7,8,15,16,31,0xff,0x100,0xffff,0x1000000,0x80000000,0xffffffff]:
 h.prepare();h.compare(0x49bfb0,h.M,[limit],('limit-init',limit))
 if limit:
  for i in range(8):h.compare(0x49c000,h.M,[],('retained-permutation',limit,i))
print('PASS source checksum/XOR/inverse/permutation',h.calls,h.eventCount,flush=True)
for flags in[0,1,2,3,0x10,0x20,0x30,0x40,0x50,0x70,0x80,0x1000,0x3000,0x8001,0x8020,0xffff]:
 for fail in[None,0]:
  h.prepare();h.failOpen=fail;h.compare(0x4f72c9,h.F,label=('file-ctor',flags,fail));h.compare(0x4f7448,h.F,[h.STR+12,flags,0],('open',flags,fail));h.compare(0x4f766e,h.F,label=('close',flags,fail));h.compare(0x4f7369,h.F,label=('destructor',flags,fail))
for errorObject in[0,h.ERR]:
 h.prepare();h.put(h.ERR+16,[h.ctx.emptyStringToken]);h.failOpen=0;h.compare(0x4f7448,h.F,[h.STR+12,1,errorObject],('open-error-object',errorObject))
for count,nodes,failOpen,failAlloc in[(0,0,None,False),(0x80000000,0,None,False),(0xffffffff,0,None,False),(1,1,0,False),(1,1,1,False),(1,1,None,True),(1,1,None,False),(2,2,None,False),(3,3,None,False),(3,1,None,False),(1,0,None,False)]:
 h.prepare(count,nodes);h.failOpen=failOpen;h.failAllocate=failAlloc;plain=h.get(h.M+0x20,8);h.compare(0x49bbc0,h.M,label=('writer',count,nodes,failOpen,failAlloc))
 if count in(1,2,3)and failOpen is None and not failAlloc:
  assert h.get(h.M+0x20,1)==plain[:1]and h.get(h.M+0x2c)[0]==count
  assert len(h.files[b'CLAW.USR'])==32+count*0x2644 and not h.handles and not h.live[h.BUFFER]
for i in range(8):
 h.prepare();h.put(h.STR+4,[0]);h.compare(0x49bbc0,h.M,label=('empty-CString-length',i));assert h.files[b'CLAW.USR']==b'OLD-SAVE'
# Retained identical writes, count sampled before allocation vs live count header.
for history in range(6):
 h.prepare(1);before=h.get(h.M+0x20,8)
 for i in range(3):h.compare(0x49bbc0,h.M,label=('retained-write',history,i))
 assert h.get(h.M+0x20)[0]==before[0]
h.prepare();h.mutation=1;h.compare(0x49bbc0,h.M,label='allocator-changes-live-count');assert h.get(h.M+0x2c)[0]==2 and len(h.files[b'CLAW.USR'])==32+0x2644
print('PASS complete writer success/reopen/allocation/cache-count and retained physical bytes',h.calls,h.eventCount,flush=True)
# Source inline manager construction is checked against its actual instruction
# interval with original CPtrList/CString bodies, stopped before unrelated path boot.
h.prepare();h.put(h.M,[h.rng.getrandbits(32)for _ in range(22)]);initial=bytes(h.heap);h.events=[];assert h.lib.claw_save_file_initialize_manager(h.M,C.byref(h.ctx));expected=h.canonical();h.native=False;h.u.mem_write(h.BASE,initial);h.u.mem_write(h.GS,h.globalSeed)
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_ESP
stopped=[]
def endCtor(uc,at,size,_):
 if at==0x426594:stopped.append(at);uc.emu_stop()
halt=h.u.hook_add(UC_HOOK_CODE,endCtor);h.u.reg_write(UC_X86_REG_EBX,h.M);h.u.reg_write(UC_X86_REG_ESI,0);h.u.reg_write(UC_X86_REG_EDI,0);h.u.reg_write(UC_X86_REG_ESP,h.m.stack);h.u.emu_start(0x426565,h.m.stop,count=10000);h.u.hook_del(halt);assert stopped==[0x426594]and h.canonical()==expected and not h.events;h.native=True
# Retained real source cache contents for all15 level indices and45 checkpoint
# slots, composed from frozen whole49a720/49a860/49a800, then source file writes.
checkpointCalls=0
for history in range(3):
 h.prepare(1);h.compare(0x49a720,h.RECORDS,label=('frozen-cache-reset',history));checkpointCalls+=1
 for level in range(15):
  for kind in[1,2,3]:
   h.put(h.DATA,[h.rng.getrandbits(32)for _ in range(44)]);h.compare(0x49a860,h.RECORDS,[level,h.DATA,kind],('frozen-cache-write',history,level,kind));checkpointCalls+=1
  h.put(h.DATA,[0,1000+level,level]+[h.rng.getrandbits(32)for _ in range(14)]);h.compare(0x49a800,h.RECORDS,[level,h.DATA],('frozen-best-write',history,level));checkpointCalls+=1
 plain=h.readBytes(h.RECORDS+4,0x2644);h.compare(0x49bbc0,h.M,label=('save-composed45-checkpoints',history));cipher=h.files[b'CLAW.USR'];target=h.BASE+0x70000
 h.putBytes(target,cipher[32:]);h.compare(0x49c070,h.M,[target,len(cipher)-32],('source-file-payload-roundtrip',history));assert h.readBytes(target,0x2644)==plain
 h.putBytes(target,cipher[:32]);h.compare(0x49c070,h.M,[target,32],('source-file-header-roundtrip',history));assert h.readBytes(target,32)==h.readBytes(h.M+0x20,32)
# Source caller mutation and exact destination alias profiles.
h.prepare();h.mutation=2;h.compare(0x49bbc0,h.M,label='physical-write-mutates-source-key')
for token,size in[(h.M+0x44,4),(h.M+0x54,1),(h.M+0x20,32)]:
 h.prepare();h.compare(0x49c030,h.M,[token,size],('source-aliased-key/state/header',token,size))
# Whole write failures/short writes and failed close stop at actual reached
# MFCthrow boundary. No fabricated exception return, cleanup or saved result.
prefixes=0
for fn,t,args,kind in[(0x49bbc0,h.M,[],'short-write'),(0x49bbc0,h.M,[],'failed-write'),(0x49bbc0,h.M,[],'failed-close'),(0x49c030,h.M,[0xdead0000,1],'bad-cipher-input')]:
 h.prepare();h.prefix=True
 if kind=='short-write':h.writePolicy=1
 if kind=='failed-write':h.writePolicy=2
 if kind=='failed-close':h.closeFailure=True
 before=bytes(h.heap);state=h.state();h.events=[];h.currentRoot=fn;ok,_=h.entry(fn,t,args);assert not ok and h.ctx.fault in(1,3),(kind,h.ctx.fault);expected=h.canonical();ne=h.events[:];after=h.state();h.native=False;h.maps={};h.u.mem_write(h.BASE,before);h.u.mem_write(h.GS,h.globalSeed);h.restore(state);h.events=[]
 try:h.originalCall(fn,t,args)
 except Exception:pass
 else:raise AssertionError(('source prefix returned',kind))
 assert h.canonical()==expected and h.events==ne and h.state()==after and bytes(h.u.mem_read(h.GS,h.GN))==h.globalSeed,('prefix',kind)
 h.native=True;prefixes+=1
h.prepare();h.ctx.maximumSteps=4;h.put(h.M+0x48,[0,2,3,1]);ok,_=h.entry(0x49c000,h.M,[]);assert not ok and h.ctx.fault==4
h.prepare();out=h.U();assert not h.lib.claw_save_file_entry(0x49bbc0,h.M,None,1,C.byref(h.ctx),h.dependency,None,C.byref(out))and h.ctx.fault==2
print('PASS composed45-slot cache, full source-format roundtrips, constructor interval and four failure prefixes',h.calls,h.eventCount,flush=True)
report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','completeCalls':h.calls,'orderedSnapshots':h.eventCount,'originalInstructionAddresses':[hex(a)for a in sorted(h.m.executed)if 0x400000<=a<0x500000],'failurePrefixes':prefixes,'composedCheckpointCacheCalls':checkpointCalls,'constructorIntervals':1,'heapBytesCompared':h.SIZE,'globalBytesCompared':h.GN}
(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',h.calls,h.eventCount,len(report['originalInstructionAddresses']),flush=True)
