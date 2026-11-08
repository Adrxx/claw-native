#!/usr/bin/env python3
"""Persistent indexed presentation versus complete unchanged-original captures."""
import ctypes as C, subprocess
import effect_pid_blitter_helpers as h
root=h.ROOT; work=root/'work/native-indexed-composite'; work.mkdir(exist_ok=True)
subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-dynamiclib',*[str(root/'Sources'/f'{name}.cpp') for name in ['NativeIndexedPresentation','EffectPIDBlitter','LightPIDBlitter','PIDBlitter']],'-o',str(work/'libComposite.dylib')],check=True)
class Image(C.Structure):
 _fields_=[('rgba',C.POINTER(h.B)),('byteCount',h.Z),('left',h.U),('top',h.U),('width',h.U),('height',h.U)]
lib=C.CDLL(str(work/'libComposite.dylib'))
lib.claw_native_indexed_composite8.argtypes=[C.POINTER(h.B),h.Z,C.POINTER(h.Command),C.POINTER(h.State),C.POINTER(h.Table),C.POINTER(h.B),C.POINTER(h.B),h.Z,h.Z,C.POINTER(h.B),h.Z,C.POINTER(h.B),h.Z,h.U,h.U,C.POINTER(h.Info),C.POINTER(Image)]
lib.claw_native_indexed_image_dispose.argtypes=[C.POINTER(Image)]
w,height,pitch=64,32,68;size=pitch*height
indices=bytes((i*17+31)%256 for i in range(size));scratch=bytes(range(129));rgb=bytes(range(256))*3
pid=h.header(7,4)+bytes([7,0,1,2,3,4,5,6])*4
lut=bytes((a+b)%256 for a in range(256)for b in range(256))
rank=bytes(range(256))*2
for iteration in range(128):
 mode=(1,2,4,8,22,50)[iteration%6];tableBytes=rank if mode==50 else lut
 fx,fy=(iteration>>1)&1,(iteration>>2)&1;render=iteration&1
 src=(0,iteration%2,6,3);dst=(iteration%40+3,iteration%12+4,iteration%40+9,iteration%12+7)
 h.check(pid,src,dst,fx,fy,('persistent presentation',iteration),render=render,mode=mode,value=(52,128,255)[iteration%3],palette=tableBytes,initial=indices,pitchOverride=pitch,scratchInitial=scratch,capacityOverride=size)
 data,cmdRaw,stateRaw,words,tableData,before,scratchBefore,expected,coverage,scratchAfter,capacity,stride,accepted,writes=h.lastEvidence
 input=(h.B*len(data)).from_buffer_copy(data);out=(h.B*size).from_buffer_copy(before);mask=(h.B*size)();live=(h.B*129).from_buffer_copy(scratchBefore);tablePayload=(h.B*len(tableData)).from_buffer_copy(tableData);palette=(h.B*len(rgb)).from_buffer_copy(rgb)
 command=h.Command.from_buffer_copy(cmdRaw);state=h.State.from_buffer_copy(stateRaw);table=h.Table((h.U*3)(*words),tablePayload,len(tableData));info=h.Info();image=Image()
 result=lib.claw_native_indexed_composite8(input,len(data),C.byref(command),C.byref(state),C.byref(table),out,mask,size,pitch,live,129,palette,len(rgb),w,height,C.byref(info),C.byref(image))
 assert bytes(out)==expected and bytes(live)==scratchAfter and info.writes==writes
 assert bytes(mask)==bytes(1 if x==1 else 0 for x in coverage)
 visible=[(x,y)for y in range(height)for x in range(w)if mask[y*pitch+x]]
 assert result==bool(visible)
 if visible:
  left=min(x for x,y in visible);right=max(x for x,y in visible);top=min(y for x,y in visible);bottom=max(y for x,y in visible)
  assert (image.left,image.top,image.width,image.height)==(left,top,right-left+1,bottom-top+1)
  pixels=C.string_at(image.rgba,image.byteCount)
  for y in range(image.height):
   for x in range(image.width):
    pos=(top+y)*pitch+left+x;pixel=pixels[(y*image.width+x)*4:(y*image.width+x+1)*4]
    expectedPixel=rgb[expected[pos]*3:expected[pos]*3+3]+b'\xff' if mask[pos] else b'\0'*4
    assert pixel==expectedPixel
 lib.claw_native_indexed_image_dispose(C.byref(image));indices=expected;scratch=scratchAfter
print('PASS128 retained presentation/source comparisons: same padded indexed frame, all6 modes/allflips, original129-byte scratch tails, complete destination/coverage and every cropped RGBA byte; physical surface/fill remain transport')
