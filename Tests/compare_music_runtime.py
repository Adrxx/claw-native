#!/usr/bin/env python3
"""Whole source music wrappers, exact XMI bytes and ordered DLL/map services."""
import ctypes as C,itertools,json,struct
import music_runtime_helpers as h

def mapSong():h.names[b'PLAY']=h.SLOTS;h.put(h.SLOTS,[h.R]);h.put(h.M+0xc,[1]);h.put(h.M+0x1c,[h.R])
resourceFns=[(0x4b56a0,()),(0x4b5a80,(0x2222,1)),(0x4b5ad0,()),(0x4b5b00,()),(0x4b5b40,(0,)),(0x4b5b40,(1,)),(0x4b5b90,()),(0x4b5bd0,())]
for (f,args),handle,status,count,mutation in itertools.product(resourceFns,[0,0x70000100],[0,2,4,8,16,20,0xffffffff],[0,1,2,0x7fffffff,0x80000000,0xffffffff],[0,2,3,4]):
 h.prepare();h.put(h.R+0x58,[handle]);h.put(h.R+0x44,[count]);h.status=status;h.mutation=mutation;h.compare(f,h.R,args,label=('controller',hex(f),handle,status,count,mutation))
for input,driver in itertools.product(list(range(0,128))+[0x7fffffff,0x80000000,0xffffffff],[0,h.DRIVER]):
 h.prepare();h.g.midiDriver=driver;h.compare(0x4b55e0,h.M,[input],label=('master-volume-set',input,driver));h.compare(0x4b5650,h.M,label=('master-volume-roundtrip',input,driver))
for response in list(range(0,128))+[0x7fffffff,0x80000000,0xffffffff]:
 h.prepare();h.dllResults[0x546e8c]=response;h.compare(0x4b5650,h.M,label=('master-volume-get',response))
for disabled,result,driver in itertools.product([0,1,0xffffffff],[0,1,0x80004005],[0,h.DRIVER]):
 h.prepare();h.g.midiDriver=0x60000111;h.dllResults[0x546e74]=result;h.dllResults['driver']=driver;h.dllResults[0x546e70]=0xffffffff;h.compare(0x4b52a0,h.M,[0x12340000,0x2222,disabled],label=('startup',disabled,result,driver))
for (f,args),gate,current,status,mutation in itertools.product([(0x4b54a0,(h.NAME,)),(0x4b54f0,(h.NAME,0)),(0x4b54f0,(h.NAME,1)),(0x4b5550,()),(0x4b5570,(1,)),(0x4b55a0,()),(0x4b55b0,(0,)),(0x4b55b0,(1,)),(0x4b55d0,())],[0,1],[0,h.R],[4,8],[0,1,5]):
 h.prepare();mapSong();h.put(h.M+0x28,[gate]);h.put(h.M+0x1c,[current]);h.status=status;h.mutation=mutation;h.compare(f,h.M,args,label=('manager',hex(f),gate,current,status,mutation))
print('PASS source controller/manager/volume matrix',h.calls,h.eventCount,flush=True)

for data,size,cache,name,driver,init in itertools.product([0,h.DATA],[0,3,4,7,64],[0,h.CACHE],[0,h.NAME],[0,h.DRIVER],[0,1]):
 h.prepare();h.g.midiDriver=driver;h.g.resourceOrdinal=h.rng.getrandbits(32);h.put(h.R+0x5c,[cache]);h.dllResults[0x546e98]=init;h.dllResults[0x546e9c]=h.rng.choice([0,0x70000100]);h.compare(0x4b58a0,h.R,[data,size,name],label=('load',data,size,cache,name,driver,init))
for f in(0x4b53f0,0x4b58a0):
 for allocFail in([None,1]if f==0x4b53f0 else[None,0]):
  for init in[0,1]:
   h.prepare();h.put(h.R+0x58,[0]);h.failAllocation=allocFail;h.dllResults[0x546e98]=init;h.compare(f,h.M if f==0x4b53f0 else h.R,[h.DATA,65,h.NAME],label=('normal-allocation-init-fail',hex(f),allocFail,init))
for (f,args),handle,data,mutation in itertools.product([(0x4b5a40,()),(0x4b56d0,()),(0x4b56b0,(0,)),(0x4b56b0,(1,)),(0x4b56b0,(2,)),(0x4b56b0,(0xffffffff,))],[0,0x70000100],[0,h.CACHE],[0,6]):
 h.prepare();h.put(h.R+0x58,[handle,data]);h.mutation=mutation;h.compare(f,h.R,args,label=('teardown',hex(f),handle,data,mutation))
for missing in(0x546ac8,0x546acc,0x546ac4,None):
 h.prepare();h.dllResults[missing]=0 if missing else 1;h.compare(0x4b59c0,h.R,[h.NAME,h.NAME],label=('PE-resource-transport',missing))
print('PASS memory/factory/PE/load/teardown matrix',h.calls,h.eventCount,flush=True)

# All recovered disc XMI files are opaque source bytes; every complete original
# source-copy buffer and DLL init argument is compared without a guessed parser.
files=sorted((h.ROOT/'work/original-disc-assets').rglob('*.XMI'));assert files
for file in files:
 h.prepare();h.status=None;size=h.installAsset(file);h.putBytes(h.NAME,file.stem.encode()+b'\0');name=h.text(h.NAME);r=h.compare(0x4b53f0,h.M,[h.DATA,size,h.NAME],label=('asset-create',file.relative_to(h.ROOT)));assert r
 for loop in[0,1,0xffffffff]:
  h.compare(0x4b54f0,h.M,[h.NAME,loop],label=('asset-select',file.name,loop))
  for pause in range(3):h.compare(0x4b55a0,h.M,label=('asset-pause',file.name,loop,pause))
  for resume in[0,0,1,0]:h.compare(0x4b55b0,h.M,[resume],label=('asset-resume',file.name,loop,resume))
  h.compare(0x4b55d0,h.M,label=('asset-end',file.name,loop));h.compare(0x4b5b90,r,label=('asset-restart',file.name,loop))
 h.compare(0x4b5300,h.M,label=('asset-shutdown',file.name));assert not h.names and not h.g.midiDriver and not h.get(h.M+0x1c)[0]
print('PASS all actual XMI retained creation/play/pause/resume/end/restart/shutdown',len(files),h.calls,h.eventCount,flush=True)

# Reload retains the existing copied bytes and does not release an overwritten
# old sequence handle before allocation. Same-name registration replaces map
# value while retaining the first current pointer; cleanup frees only map values.
for history in range(24):
 h.prepare();h.status=None;size=h.installAsset(files[history%len(files)]);r=h.compare(0x4b53f0,h.M,[h.DATA,size,h.NAME],label=('reload-create',history));oldBuffer=h.get(r+0x5c)[0];oldHandle=h.get(r+0x58)[0]
 h.putBytes(h.DATA,b'OTHER-BYTES\0');h.compare(0x4b58a0,r,[h.DATA,12,h.NAME],label=('reload-existing-cache',history));assert h.get(r+0x5c)[0]==oldBuffer and oldHandle in h.handles
 new=h.compare(0x4b53f0,h.M,[h.DATA,12,h.NAME],label=('replace-map-name',history));assert new!=r and h.get(h.M+0x1c)[0]==r and h.get(h.names[b'PLAY'])[0]==new
 h.compare(0x4b5340,h.M,label=('replace-clear',history));assert new in h.freed and r not in h.freed
 h.compare(0x4b56b0,r,[1],label=('external-own-old-resource',history));h.compare(0x4b5300,h.M,label=('reload-shutdown',history))
for history in range(16):
 h.prepare();h.status=None
 for ordinal in range(5):
  h.putBytes(h.NAME,f'PLAY{ordinal}'.encode()+b'\0');size=h.installAsset(files[(history+ordinal)%len(files)]);h.compare(0x4b53f0,h.M,[h.DATA,size,h.NAME],label=('many-create',history,ordinal))
 h.compare(0x4b5300,h.M,label=('many-shutdown',history));assert not h.names and h.get(h.KEY)[0]==1

# Complete actual original SpecialCommand pause/resume callers are composed;
# admission remains application+50 and application+14, separate from audio.
import music_runtime_joined_helpers as joined
for music,audio,current,status,count in itertools.product([0,h.M],[0,1,0xffffffff],[0,h.R],[4,8,16],[0,1,2]):
 h.prepare();mapSong();h.put(joined.APP+0x50,[music]);h.put(joined.APP+0x14,[audio]);h.put(h.M+0x1c,[current]);h.put(h.R+0x44,[count]);h.status=status
 h.compare(0x42d420,joined.APP,label=('SpecialCommand-pause',music,audio,current,status,count));h.compare(0x42d440,joined.APP,label=('SpecialCommand-resume',music,audio,current,status,count))

# Five exact original invalid-span/nonadvancing prefixes, never source success.
prefixes=0
for f,t,args,case in [(0x4b58a0,h.R,[0xdead0000,65,h.NAME],'bad-input'),(0x4b53f0,h.M,[h.DATA,65,h.NAME],'null-object'),(0x4b56a0,0xdead0000,[],'bad-receiver'),(0x4b5570,h.M,[1],'callback-current0'),(0x4b5340,h.M,[],'nonadvancing-map')]:
 h.prepare();mapSong()
 if case=='null-object':h.failAllocation=0
 if case=='callback-current0':h.mutation=8
 if case=='nonadvancing-map':h.mutation=7;h.ctx.maximumTraversal=3
 old=bytes(h.heap);og=h.globalBytes();state=(h.freed[:],h.cursor,h.allocCalls,h.names.copy(),h.handles.copy(),h.nextHandle,h.volume);h.events=[];out=h.U();aa=(h.U*len(args))(*args);ok=h.lib.claw_music_entry(f,t,aa,len(args),C.byref(h.ctx),h.dependency,None,C.byref(out));assert not ok and h.ctx.fault in(1,3),('native prefix',case,h.ctx.fault,h.errors)
 expected=bytes(h.heap);eg=h.globalBytes();ne=h.events[:];after=(h.freed[:],h.cursor,h.allocCalls,h.names.copy(),h.handles.copy(),h.nextHandle,h.volume);h.native=False;h.u.mem_write(h.BASE,old);h.u.mem_write(h.GS,og);h.freed,h.cursor,h.allocCalls,h.names,h.handles,h.nextHandle,h.volume=state;h.events=[]
 if h.ctx.fault==3:h.prefixStop=len(ne)
 halt=None
 if case in('null-object','callback-current0'):
  from unicorn import UC_HOOK_CODE
  def zero(uc,address,size,_):
   if address==0:uc.emu_stop()
  halt=h.u.hook_add(UC_HOOK_CODE,zero)
 try:h.m.call(f,t,struct.pack('<'+'I'*len(args),*args))
 except Exception:pass
 else:raise AssertionError(('source prefix unexpectedly returned',case))
 finally:
  h.prefixStop=None
  if halt:h.u.hook_del(halt)
 assert bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and h.globalBytes()==eg and h.events==ne and(h.freed,h.cursor,h.allocCalls,h.names,h.handles,h.nextHandle,h.volume)==after,('prefix',case)
 h.native=True;prefixes+=1
h.prepare();out=h.U();assert not h.lib.claw_music_entry(0x4b58a0,h.R,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and h.ctx.fault==2
h.prepare();assert not h.lib.claw_music_entry(0x4b5720,h.R,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and not h.ctx.fault
report={'calls':h.calls,'events':h.eventCount,'instructions':len(h.m.executed),'failurePrefixes':prefixes,'assets':list({a['path']:a for a in h.assetProfiles}.values()),'exeSha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',h.calls,'whole originals /',h.eventCount,'ordered full snapshots /',len(h.m.executed),'original addresses /',len(files),'actual XMI assets /',prefixes,'failure prefixes',flush=True)
