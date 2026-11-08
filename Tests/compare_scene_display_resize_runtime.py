import itertools,json
import scene_display_resize_helpers as h
# Equality wins even when the stored/requested dimensions are inadmissible.
for f,kind in((0x4d4280,1),(0x4d4280,2),(0x4d5720,0)):
 for width,height,depth in itertools.product((0,1,640,0xffffffff,0x80000000),(0,1,480,0xffffffff),(0,8,16,24,32,15,0xffffffff)):
  p=h.fresh(kind,width,height,depth);assert h.compare(f,p,(width,height,depth),('equal',f,kind,width,height,depth))==1;assert not h.events
# Isolated complete method bodies, with explicit bounded factory/HRESULT services.
for f,kind in((0x4d4280,1),(0x4d4280,2),(0x4d5720,0)):
 for width,height,depth in itertools.product((0,1,639,640,800,0xffffffff,0x80000000),(0,1,479,480,600,0xffffffff),(0,8,16,24,32,15,0xffffffff)):
  p=h.fresh(kind);h.compare(f,p,(width,height,depth),('admission',f,kind,width,height,depth))
for f,kind in((0x4d4280,1),(0x4d4280,2),(0x4d5720,0)):
 for factory,mode,ready,flags in itertools.product((0,h.NEW),(0,1,0x80004005),(0,1),(0,2,0xffffffff)):
  p=h.fresh(kind);h.factoryResult=factory;h.modeResult=mode;h.ready=ready;h.put(h.PARENT+52,[flags]);h.compare(f,p,(800,600,16),('dependency branches',f,kind,factory,mode,ready,flags))
# Cache re-reading after external dependencies is source behavior.
for mutation,f,kind in(('typeAfterDelete',0x4d4280,1),('typeAfterAttach',0x4d4280,1),('flagsAfterMode',0x4d5720,0)):
 p=h.fresh(kind);h.mutation=mutation;h.compare(f,p,(800,600,16),('reentrant fields',mutation))
p=h.fresh(0);h.put(h.PARENT+28,[0]);assert h.compare(0x4d5720,p,(800,600,16),'missing manager')==0;assert not h.events
print('PASS complete resize methods',h.calls,h.snapshotCount,flush=True)
# Whole shared factories, real list removal/insertion, source surface lifecycle,
# GameImage create/describe/color-key bodies, source mode and channel masks.
for f,kind in((0x4d4280,1),(0x4d4280,2),(0x4d5720,0)):
 for depth,flags,mode,display in itertools.product((8,16,24,32),(0,2),(0,1),(0,1)):
  p=h.fresh(kind,compose=True);h.modeResult=mode;h.displayResult=display;h.put(h.PARENT+52,[flags]);h.compare(f,p,(800,600,depth),('composed creation',f,kind,depth,flags,mode,display))
 for seed in range(20):
  p=h.fresh(kind,compose=True)
  for i,args in enumerate(((800,600,16),(1024,768,32),(1024,768,32),(640,480,8),(0,0,15),(640,480,8))):
   h.compare(f,p,args,('retained surfaces',f,kind,seed,i))
for f,kind,mutation in((0x4d4280,1,'typeAfterAttach'),(0x4d5720,0,'flagsAfterMode')):
 p=h.fresh(kind,compose=True);h.mutation=mutation;h.compare(f,p,(800,600,16),('composed mutation',f,kind,mutation))
print('PASS composed resize histories',h.calls,h.snapshotCount,flush=True)
# Unknown and strict argument rejection are native safety checks only.
p=h.fresh();out=h.U(123);args=(h.U*3)(800,600,16)
assert not h.lib.claw_scene_display_resize_entry(0x4d4281,p,args,3,h.C.byref(h.ctx),h.dep,None,h.C.byref(out))and out.value==123 and h.ctx.fault==0
assert not h.lib.claw_scene_display_resize_entry(0x4d4280,p,args,2,h.C.byref(h.ctx),h.dep,None,h.C.byref(out))and h.ctx.fault==2
# Count only original PE.text addresses separately from all instrumentation.
data=(h.ROOT/'Original/claw10/CLAW.EXE').read_bytes();pe=h.struct.unpack_from('<I',data,0x3c)[0];n=h.struct.unpack_from('<H',data,pe+6)[0];opt=h.struct.unpack_from('<H',data,pe+20)[0];imageBase=h.struct.unpack_from('<I',data,pe+24+28)[0]
for i in range(n):
 at=pe+24+opt+i*40
 if data[at:at+8].split(b'\0')[0]==b'.text':size,va=h.struct.unpack_from('<II',data,at+8);lo,hi=imageBase+va,imageBase+va+size;break
source=sum(lo<=a<hi for a in h.m.executed);h.WORK.joinpath('verification.json').write_text(json.dumps({'calls':h.calls,'orderedFullSnapshots':h.snapshotCount,'instrumentedAddresses':len(h.m.executed),'originalTextAddresses':source,'originalTextRange':[hex(lo),hex(hi)]},indent=2)+'\n')
print('PASS FINAL',h.calls,h.snapshotCount,len(h.m.executed),source,flush=True)
for f,kind in((0x4d4280,1),(0x4d4280,2),(0x4d5720,0)):
 p=h.fresh(kind,compose=True);h.allocFail=1;h.unsafe(f,p,(800,600,16),('allocation failure',hex(f),kind))
 p=h.fresh(kind,compose=True);h.put(p+44,[0]);h.unsafe(f,p,(800,600,16),('null existing surface',hex(f),kind))
print('PASS unsafe prefixes',h.unsafeCases,flush=True)
v=json.loads(h.WORK.joinpath('verification.json').read_text());v['unsafePrefixes']=h.unsafeCases;v['instrumentedAddresses']=len(h.m.executed);v['originalTextAddresses']=sum(lo<=a<hi for a in h.m.executed);h.WORK.joinpath('verification.json').write_text(json.dumps(v,indent=2)+'\n')
