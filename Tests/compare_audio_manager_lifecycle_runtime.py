#!/usr/bin/env python3
"""Whole constructor/startup/stop/shutdown and actual composed ownership."""
import ctypes as C,itertools,json,struct
import audio_manager_lifecycle_runtime_helpers as h
for i in range(64):
 h.prepare();h.put(h.M,[h.rng.getrandbits(32)for _ in range(32)]);h.put(0x541178,[h.rng.getrandbits(32)for _ in range(101)]);h.compare(0x4b4710,label=('constructor-preservation',i))
for i in range(16):
 h.prepare();h.put(0x541178,[h.rng.getrandbits(32)for _ in range(101)]);h.compare(0x4b3c80,receiver=h.rng.getrandbits(32),label=('whole-volume-initialize',i))
for create,coop,gate,mutation in itertools.product([0,1,0x80004005,0xffffffff],[0,1,0x80004005,0xffffffff],[0,1,99,0xffffffff],[0,1,2,3,6]):
 h.prepare();h.createResult=create;h.coopResult=coop;h.mutation=mutation;h.put(h.M+0x78,[gate,h.rng.getrandbits(32)]);h.compare(0x4b47e0,args=(h.rng.getrandbits(32),h.rng.getrandbits(32)),label=('startup',create,coop,gate,mutation))
for f,pools,gate,mutation in itertools.product([0x4b4860,0x4b4790,0x4b4770],[0,1,4],[0,1,0xffffffff],[0,4,5,6,10]):
 h.prepare(pools,2,3);h.put(h.M+0x78,[gate]);h.mutation=mutation;h.releaseResult=h.rng.getrandbits(32);h.compare(f,args=(h.rng.choice([0,1,2,3,0x100,0xffffffff]),)if f==0x4b4770 else(),label=('shutdown-adapter',hex(f),pools,gate,mutation))
for f,pools,voices,gate,mutation in itertools.product([0x4b4b40,0x4b4670],[0,1,3],[0,1,4],[0,1,0xffffffff],[0,7,8]):
 h.prepare(pools,voices,3);h.put(h.M+0x78,[gate]);h.mutation=mutation
 if f==0x4b4670 and not pools:continue
 h.compare(f,receiver=h.P if f==0x4b4670 else h.M,label=('stop-adapter',hex(f),pools,voices,gate,mutation))
print('PASS complete branch/service matrix',h.calls,h.eventCount,flush=True)

for f,pools,voices,fades,gate in itertools.product([0x4b4860,0x4b4790,0x4b4770,0x4b4b40,0x4b4670],[0,1,3],[0,1,4],[0,1,5],[0,1,99]):
 if f==0x4b4670 and not pools:continue
 h.prepare(pools,voices,fades);h.compose=True;h.put(h.M+0x78,[gate]);
 for index,control in enumerate(h.controls):h.put(control+0xc,[[0,1,2,0xffff,0xffffffff][index%5]])
 h.stopResult=h.rng.choice([0,0,0x80004005]);h.releaseResult=h.rng.getrandbits(32);h.compare(f,receiver=h.P if f==0x4b4670 else h.M,args=(h.rng.choice([0,1,3,0xffffffff]),)if f==0x4b4770 else(),label=('whole-PCM-ambient',hex(f),pools,voices,fades,gate))
 # Orphan controls survive source shutdown when not owned by a resource.
 if f in(0x4b4860,0x4b4790,0x4b4770)and not pools and fades:assert h.get(h.M+0xc)[0]==h.FA+4
print('PASS whole PCM and Stop graphs',h.calls,h.eventCount,flush=True)

# Retained startup/restart/failure/stop/shutdown/repeated shutdown/deletion.
for history in range(40):
 h.prepare();h.compare(0x4b4710,label=('retained-ctor',history));h.compare(0x4b47e0,args=(0xabcdef,1),label=('retained-open',history));h.put(h.M+0x7c,[0xffffffff]);h.compare(0x4b47e0,args=(0,3),label=('retained-reopen',history));h.createResult=0x80004005;h.createdDevice=h.D2;h.compare(0x4b47e0,args=(1,1),label=('retained-create-fail',history));assert h.get(h.M+0x78)[0]==1
 h.createResult=0;h.coopResult=0x80004005;h.compare(0x4b47e0,args=(1,1),label=('retained-coop-fail',history));assert h.get(h.M+0x78)[0]==1
 h.coopResult=0;h.compare(0x4b47e0,args=(1,1),label=('retained-recover',history));h.compose=True;h.compare(0x4b4b40,label=('retained-stop-empty',history));h.compare(0x4b4860,label=('retained-close',history));h.compare(0x4b4860,label=('retained-close-again',history));h.compare(0x4b4770,args=(1,),label=('retained-delete',history))
for history in range(32):
 h.prepare(3,4,5);h.compose=True
 for iteration in range(3):h.compare(0x4b4b40,label=('retained-stop-pools-voices',history,iteration))
 h.compare(0x4b4860,label=('retained-shutdown-owned',history));assert h.get(h.M+4,2)==[0,0]and h.get(h.M+0xc,2)==[0,0]
 h.compare(0x4b4770,args=(1,),label=('retained-delete-owned',history))

# Real extracted Level1 WAV parse/create/upload graphs are joined to source
# ctor/device startup and shutdown; physical COM buffers remain services.
import audio_manager_lifecycle_joined_helpers as j
files=sorted((h.ROOT/'App/GameData/LEVEL1/SOUNDS').rglob('*.WAV'),key=lambda f:f.stat().st_size)[:6]
for file,failure in itertools.product(files,range(4)):
 j.prepare(file,failure);h.compare(0x4b4710,label=('WAV-ctor',file.name,failure));h.compare(0x4b47e0,args=(0x1234,1),label=('WAV-open',file.name,failure));h.compare(0x4b4a20,args=(j.INPUT,),label=('WAV-load',file.name,failure));h.compare(0x4b4b40,label=('WAV-stop',file.name,failure));h.compare(0x4b4860,label=('WAV-close',file.name,failure));h.compare(0x4b4770,args=(1,),label=('WAV-delete',file.name,failure))
for history in range(8):
 j.prepare(files[0]);h.compare(0x4b4710,label=('many-WAV-ctor',history));h.compare(0x4b47e0,args=(0x1234,1),label=('many-WAV-open',history))
 for index,file in enumerate(files):
  j.profile=file.read_bytes();C.memmove(C.addressof(h.heap)+j.INPUT-h.BASE,j.profile,len(j.profile));j.nextBuffer=h.B+index*0x100;h.put(j.nextBuffer,[h.BVT]);h.compare(0x4b4a20,args=(j.INPUT,),label=('many-WAV-load',history,index))
 h.compare(0x4b4b40,label=('many-WAV-stop',history));h.compare(0x4b4860,label=('many-WAV-close',history));assert h.get(h.M+4,2)==[0,0];h.compare(0x4b4770,args=(1,),label=('many-WAV-delete',history))
print('PASS actual source WAV constructor/factory/upload/stop/shutdown histories',h.calls,h.eventCount,flush=True)

# Invalid span and nonadvancing-source-loop prefixes; extensions do not claim
# source success. Stop original at the next callback entry after native limit.
prefixes=0
for f,receiver,args,mut,cycle in [(0x4b4710,0xdead0000,(),0,None),(0x4b47e0,h.M,(1,1),0,('vtable',)),(0x4b4860,h.M,(),9,None),(0x4b4b40,h.M,(),0,('pool',)),(0x4b4670,h.P,(),0,('voice',))]:
 h.prepare(1,1,1);h.ctx.maximumTraversal=4;h.mutation=mut
 if cycle==('vtable',):h.put(h.D,[0xdead0000])
 if cycle==('pool',):h.put(h.P+4,[h.P+4])
 if cycle==('voice',):h.put(h.V+4,[h.V+4])
 old=bytes(h.heap);og=bytes(h.globals);h.events=[];out=h.U();aa=(h.U*len(args))(*args);assert not h.lib.claw_audio_manager_lifecycle_entry(f,receiver,aa,len(args),C.byref(h.ctx),h.dependency,None,C.byref(out))and h.ctx.fault in(1,3);expected=bytes(h.heap);eg=bytes(h.globals);ne=h.events[:];nf=h.freed[:];h.native=False;h.u.mem_write(h.BASE,old);h.u.mem_write(h.GS,og);h.events=[];h.freed=[]
 if h.ctx.fault==3:h.prefixStop=len(ne)
 try:h.m.call(f,receiver,struct.pack('<'+'I'*len(args),*args))
 except Exception:pass
 else:raise AssertionError(('source failure unexpectedly returned',hex(f)))
 finally:h.prefixStop=None
 assert bytes(h.u.mem_read(h.BASE,h.SIZE))==expected and bytes(h.u.mem_read(h.GS,h.GN))==eg and h.events==ne and h.freed==nf
 h.native=True;prefixes+=1
h.prepare();out=h.U();assert not h.lib.claw_audio_manager_lifecycle_entry(0x4b47e0,h.M,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and h.ctx.fault==2
h.prepare();assert not h.lib.claw_audio_manager_lifecycle_entry(0x123456,h.M,None,0,C.byref(h.ctx),h.dependency,None,C.byref(out))and not h.ctx.fault
report={'calls':h.calls,'events':h.eventCount,'instructions':len(h.m.executed),'failurePrefixes':prefixes,'assets':list({asset['path']:asset for asset in j.assets}.values()),'exeSha256':'350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'};(h.WORK/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',h.calls,'complete original calls /',h.eventCount,'ordered full snapshots /',len(h.m.executed),'original instruction addresses /',prefixes,'failure prefixes',flush=True)
