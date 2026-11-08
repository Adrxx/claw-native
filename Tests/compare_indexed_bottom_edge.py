#!/usr/bin/env python3
"""Mirrored bottom-edge pixels versus the unchanged original dispatcher."""
import ctypes as C,json,hashlib,subprocess
from pathlib import Path
import indexed_bottom_edge_helpers as h
root=h.ROOT;work=h.WORK
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(root/'Sources'/f'{n}.cpp')for n in('NativeIndexedPresentation','EffectPIDBlitter','LightPIDBlitter','PIDBlitter')],'-o',str(work/'libBottomEdge.dylib')],check=True)
class Image(C.Structure):_fields_=[('rgba',C.POINTER(h.B)),('byteCount',h.Z),('left',h.U),('top',h.U),('width',h.U),('height',h.U)]
lib=C.CDLL(str(work/'libBottomEdge.dylib'))
lib.claw_native_indexed_composite8.argtypes=[C.POINTER(h.B),h.Z,C.POINTER(h.Command),C.POINTER(h.State),C.POINTER(h.Table),C.POINTER(h.B),C.POINTER(h.B),h.Z,h.Z,C.POINTER(h.B),h.Z,C.POINTER(h.B),h.Z,h.U,h.U,C.POINTER(h.Info),C.POINTER(Image)]
lib.claw_native_indexed_composite8.restype=h.U;lib.claw_native_indexed_image_dispose.argtypes=[C.POINTER(Image)]
WIDTH,HEIGHT,STRIDE=640,480,640;VISIBLE=STRIDE*HEIGHT;PHYSICAL=STRIDE*(HEIGHT+1)
pid=h.header(2,1)+bytes((2,241,73));src=(0,0,1,0);dst=(638,479,639,479)
palette=(root/'work/original-disc-assets/LEVEL1/PALETTES/MAIN.PAL').read_bytes();assert len(palette)==768
average=(root/'work/original-disc-assets/LEVEL1/PALETTES/AVERAGE.CLT').read_bytes()[4:]
light=(root/'work/original-disc-assets/LEVEL1/PALETTES/LIGHT.CLT').read_bytes()[4:]
ranks=json.loads((root/'work/effect-pid-blit-agent/ranks.json').read_text())['records'];rank=bytes.fromhex(next(r['rank']for r in ranks if r['level']=='LEVEL1'))
initial=bytes((17*i+31)%256 for i in range(PHYSICAL));scratch=bytes(range(129));checks=tightRejections=0;corpus=[]
cases=[(mode,0,fx,fy)for mode in(1,2,4,8,22,50)for fx,fy in((0,0),(0,1),(1,0),(1,1))]+[(2,1,0,0)]
for mode,render,flipX,flipY in cases:
   lut=rank if mode==50 else light if mode==2 else average
   h.check(pid,src,dst,flipX,flipY,('original bottom edge',mode,render,flipX,flipY),render=render,mode=mode,value=52,palette=lut,initial=initial,pitchOverride=STRIDE,scratchInitial=scratch,capacityOverride=PHYSICAL)
   data,cmdRaw,stateRaw,words,tableData,before,scratchBefore,expected,coverage,scratchAfter,capacity,stride,accepted,writes=h.lastEvidence
   written=[i for i,v in enumerate(coverage)if v==1]
   #Assert the exact bug profile independently of the composite crop calculation.
   if mode==2 and render==1:
    assert written==[VISIBLE-2,VISIBLE-1,PHYSICAL-2,PHYSICAL-1]
   elif flipX:
    assert written==[VISIBLE-1,VISIBLE],(mode,render,flipY,written)
    assert any(offset==VISIBLE for offset,n,value in h.stores)
   else:assert written==[VISIBLE-2,VISIBLE-1],(mode,render,flipY,written)
   for offered in(PHYSICAL,VISIBLE):
    encoded=(h.B*len(data)).from_buffer_copy(data);out=(h.B*offered).from_buffer_copy(before[:offered]);mask=(h.B*offered)(*([0x41]*offered));live=(h.B*129).from_buffer_copy(scratchBefore);payload=(h.B*len(tableData)).from_buffer_copy(tableData);rgb=(h.B*768).from_buffer_copy(palette)
    command=h.Command.from_buffer_copy(cmdRaw);state=h.State.from_buffer_copy(stateRaw);table=h.Table((h.U*3)(*words),payload,len(tableData));info=h.Info();image=Image()
    result=lib.claw_native_indexed_composite8(encoded,len(data),C.byref(command),C.byref(state),C.byref(table),out,mask,offered,STRIDE,live,129,rgb,768,WIDTH,HEIGHT,C.byref(info),C.byref(image))
    if offered==VISIBLE and(flipX or(mode==2 and render==1)):
     #Native safety extension: this is a rejection, not original zero-write parity.
     assert result==0 and not image.rgba and bytes(out)==before[:offered]
     assert bytes(mask)==bytes(offered) and bytes(live)==scratchBefore
     tightRejections+=1
    else:
     assert result==1 and bytes(out)==expected[:offered] and bytes(live)==scratchAfter
     assert bytes(mask)==bytes(1 if v==1 else 0 for v in coverage[:offered])
     assert info.writes==writes and(info.locks,info.unlocks)==(1,1)
     #Only the visible write is presented; the source offscreen write persists.
     left=639 if flipX else 638;w=1 if flipX else 2
     assert(image.left,image.top,image.width,image.height)==(left,479,w,1)
     rgba=C.string_at(image.rgba,image.byteCount)
     assert image.byteCount==w*4
     want=b''.join(palette[expected[479*640+x]*3:expected[479*640+x]*3+3]+b'\xff'for x in range(left,left+w));assert rgba==want
     if offered==PHYSICAL and flipX:assert out[VISIBLE]==expected[VISIBLE] and out[VISIBLE-1]==expected[VISIBLE-1]
    lib.claw_native_indexed_image_dispose(C.byref(image));checks+=1
   corpus.append({'mode':mode,'render':render,'flipX':flipX,'flipY':flipY,'command':cmdRaw.hex(),'state':stateRaw.hex(),'words':words,'table':tableData.hex(),'expected':expected.hex(),'coverage':bytes(1 if v==1 else 0 for v in coverage).hex(),'scratch':scratchAfter.hex(),'writes':writes})
report={'originalSHA256':hashlib.sha256((root/'Original/claw10/CLAW.EXE').read_bytes()).hexdigest(),'originalWholeCalls':h.calls,'orderedOriginalSnapshots':h.snapshots,'originalWrites':h.totalWrites,'compositeChecks':checks,'tightCapacityRejections':tightRejections,'instrumentedTextAddresses':sum(0x401000<=x<0x50adb5 for x in h.m.executed),'physicalBytes':PHYSICAL,'visibleBytes':VISIBLE,'modes':[1,2,4,8,22,50],'allFlips':True,'renderWords':'0 all modes/flips;1 mode2 unmirrored control only','remainingProfile':'Other renderWord1 bottom-edge paths are not claimed by this481-row regression','physicalDD':'Lock/Unlock transport only','tightProfile':'Native safety rejection; no original out-of-bounds equivalence claim'}
(work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
#Compact exact-buffer replay evidence: unchanged initial/scratch/palette shared;
#each result preserves the complete physical framebuffer and source scratch.
(work/'initial.bin').write_bytes(initial);(work/'scratch.bin').write_bytes(scratch);(work/'palette.bin').write_bytes(palette);(work/'fixture.pid').write_bytes(pid)
manifest=[]
for i,r in enumerate(corpus):
 prefix=work/f'case-{i}';parts=['command','state','table','expected','coverage','scratch']
 for part in parts:Path(str(prefix)+'-'+part+'.bin').write_bytes(bytes.fromhex(r[part]))
 manifest.append(f'{i} {r["mode"]} {r["render"]} {r["flipX"]} {r["flipY"]} {r["writes"]} '+str(prefix))
(work/'manifest.txt').write_text('\n'.join(manifest)+'\n');print('PASS indexed bottom edge',json.dumps(report,sort_keys=True))
