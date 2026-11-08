#!/usr/bin/env python3
import message_drawing_runtime_helpers as h
for ss in((),(b'Game saved',),(b'One',b'Two',b'Three'),(b'',b'',b''),(b'\xff\x80a',b'next'),(b'a\nb',b'\r\n')):
 for requested in(0,1,2,3,10,0xffffffff,0x80000000,0x7fffffff):
  for font in(0,1,0xffffffff):
   h.prepare(ss);h.put(h.CONFIG+0x34,[font]);h.compare([requested,0x7777,h.RECT,1],label=f'lines/{ss}/{requested:x}/{font:x}')
print('PASS source signed count, empty/nonempty/ANSI/newline strings and font gates',flush=True)
for n in range(48):
 h.prepare(tuple(h.rng.randbytes(n%30).replace(b'\0',b'!')for _ in range(n%8)));h.oldFont=(0,0xffffffff,0x4567)[n%3];h.drawResult=(0,0xffffffff,17)[n%3];h.mutation=n%4;h.compare([1+n%9,0x7777,0,n*131],local=True,label=f'localRect/flags/serviceMutation/{n}')
print('PASS exact local RECT mutation, SelectObject restoration and ignored DrawText failures',flush=True)
for n in range(16):
 h.prepare((b'locked1',b'locked2',b'plain'));h.put(h.STRINGS-12,[0xffffffff]);h.put(h.STRINGS+0x200-12,[0xfffffffe]);h.mutation=4 if n%2 else 0;h.compare([3,0x7777,h.RECT,0x100],label=f'locked-CString/next-node-capture/{n}')
print('PASS frozen CString shared-copy/destruction and explicit locked-copy storage',flush=True)
for n in range(12):
 h.prepare(());h.compareController(0x4f5249,h.CONFIG,[10],f'actualStart/{n}/list');h.fontResult=0x13571357 if n%2 else 0;h.compareController(0x4222a0,h.CONFIG,[5000,2000],f'actualStart/{n}/font')
 for i,text in enumerate((b'Your game has been saved',b'first',b'second',b'third',b'fourth')):
  token=h.STRINGS+i*0x200;h.data(token,text+b'\0');h.compareController(0x422370,h.CONFIG,[token,0],f'queue/{n}/append/{i}')
 for frame,delta in enumerate((0,1999,1,2000,4999,1,5000,5000,0)):
  h.fg.values[0]=delta;h.fg.values[4:8]=[n*7,0xffffffff if n%2 else 0,640,480];h.compareController(0x46ca50,h.OWNER,[0x7777 if frame%4 else 0],f'retained/{n}/timerQueueDraw/{frame}/{delta}')
 assert h.get(h.CONFIG+12)==[0]
print('PASS actual startup5000/2000ms creator→queue insertion→source46ca50 timer/expiry/removal→draw retained ownership',flush=True)
for count in(0,0xffffffff,0x80000000,1,3,7):
 for hdc in(0,0x7777):
  h.prepare((b'only node',));h.put(h.CONFIG+12,[count]);h.compare([7,hdc,h.RECT,0x400],label=f'declared-count/missing-node/{count:x}/{hdc}')
for refs in(0,1,2,0x7fffffff,0x80000000,0xffffffff):
 h.prepare((b'one',));h.put(h.STRINGS-12,[refs]);h.compare([1,0x7777,0,0],label=f'CString-refcount/{refs:x}/nullRECT')
for n in range(8):
 h.prepare(());h.compareController(0x4f5249,h.CONFIG,[10],f'checkpointMessage/{n}/ctor');h.compareController(0x4222a0,h.CONFIG,[5000,2000],f'checkpointMessage/{n}/font')
 for msg in(0x5253a8,0x5253c4):
  h.compareController(0x42af70,h.APP,[msg],f'checkpointMessage/{n}/{msg:x}/queueReplace');h.fg.values[0]=4999;h.compareController(0x46ca50,h.OWNER,[0x7777],f'checkpointMessage/{n}/{msg:x}/draw');h.fg.values[0]=1;h.compareController(0x46ca50,h.OWNER,[0x7777],f'checkpointMessage/{n}/{msg:x}/expiry')
for delta in(0,1,2,0x80000000,0xffffffff):
 h.prepare(());h.put(h.CONFIG+0x2c,[9999]);h.put(h.CONFIG+0x30,[1]);h.fg.values[0]=delta;h.compareController(0x46ca50,h.OWNER,[0x7777],f'message-field-expiry/wrappedDelta/{delta:x}')
print('PASS missing-node asymmetry, refcount/empty/nullRECT, actual checkpoint literal replacement and wrapped timer gates',flush=True)
h.prepare((b'ab',b'alias'));h.c.composeStrings=0;h.put(h.NODES+12+8,[0x534ef8]);h.aliasMode=True;h.compare([2,0x7777,h.RECT,1],label='explicit-CString-transport/source-global-alias-DWORD-copy',record=True);assert h.string(0x534ef8)==b'ab\nab\n';h.aliasMode=False
prefixes=0
from unicorn import UcError
for kind in('unmapped-CString','text-limit','locked-storage-cancel','draw-cancel','missing-GDI-service'):
 h.prepare((b'x'*50,));h.stopService=0;h.sourceStopped=False;stop=None
 if kind=='unmapped-CString':h.put(h.NODES+8,[0xdeadbeef]);expected=1
 if kind=='text-limit':h.c.textLimit=32;stop=0x422758;expected=2
 if kind=='locked-storage-cancel':h.put(h.STRINGS-12,[0xffffffff]);h.stopService=0x4f66cc;expected=99
 if kind=='draw-cancel':h.stopService=0x546d30;expected=99
 if kind=='missing-GDI-service':h.put(h.CONFIG+0x34,[0]);stop=0x4227ee;expected=3
 h.sync();h.native_events.clear();h.original_events.clear();h.errors.clear();out=h.U(0xabcd);args=(h.U*4)(1,0x7777,h.RECT,1);done=h.lib.claw_message_drawing_entry(0x4226b0,h.CONFIG,args,4,None,h.C.byref(h.c),h.Dep()if kind=='missing-GDI-service'else h.dependency,None,h.C.byref(out));assert not done and h.c.fault==expected and out.value==0xabcd,(kind,done,h.c.fault)
 h.selectCount=h.storageCount=h.freeCount=h.allocCount=0
 def stopHook(u,at,size,user):
  if at==stop:h.sourceStopped=True;u.emu_stop()
 hook=h.m.u.hook_add(h.UC_HOOK_CODE,stopHook)if stop else None
 try:h.m.call(0x4226b0,h.CONFIG,h.pack(*args));raise AssertionError('expected original prefix')
 except UcError:assert kind=='unmapped-CString'
 except AssertionError as e:assert h.sourceStopped and str(e)=='Original routine exceeded instruction bound',(kind,str(e))
 finally:
  if hook:h.m.u.hook_del(hook)
 assert h.raw(True)==h.raw(False)and h.native_events==h.original_events,(kind,'full prefix');prefixes+=1;h.stopService=0
h.prepare();before=h.raw(True);out=h.U(123)
assert not h.lib.claw_message_drawing_entry(0x422810,h.CONFIG,(h.U*4)(1,1,1,1),4,None,h.C.byref(h.c),h.dependency,None,h.C.byref(out))and out.value==123 and before==h.raw(True)
assert not h.lib.claw_message_drawing_entry(0x4226b0,h.CONFIG,None,0,None,h.C.byref(h.c),h.dependency,None,h.C.byref(out))and h.c.fault==4 and before==h.raw(True)
import json,gzip
(h.WORK/'draw-replay.bin.gz').write_bytes(gzip.compress(h.replay.getvalue()));report={'originalSHA256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263','wholeCalls':h.calls,'orderedFullSnapshots':h.eventCount,'distinctOriginalInstructions':len(h.m.executed),'heapBytes':h.SIZE,'globalBytes':h.GN,'localRectBytes':16,'guardedOriginalPrefixes':prefixes,'retainedQueueHistories':20,'sourceStartupProfile':{'callsite':'426185','duration':5000,'delay':2000},'replayCalls':h.replayCases,'physicalBoundaries':'GDI SelectObject/DrawText/CreateFont, locked CString storage/allocator; single-thread Interlocked adapters; queue CString services output-only locals normalized'};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report,flush=True)
