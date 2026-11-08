#!/usr/bin/env python3
"""Execute the full original uncompressed image loader with audited host adapters."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
import json
import hashlib
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP
from original_v10 import OriginalV10

class Info(C.Structure):
    _fields_ = [('width', C.c_uint32), ('height', C.c_uint32), ('offsetX', C.c_int32),
                ('offsetY', C.c_int32), ('consumed', C.c_size_t), ('colorKeyEnabled', C.c_uint32)]
def packed(*x): return struct.pack('<'+'I'*len(x), *(v & 0xffffffff for v in x))
def header(w, h, flags=1, ox=0, oy=0): return packed(10, flags, w, h, ox, oy, 0, 0)

p = argparse.ArgumentParser()
p.add_argument('exe', type=Path); p.add_argument('library', type=Path); p.add_argument('--assets', type=Path)
p.add_argument('--capture-native', type=Path, help='Ignored capture directory for native factory replay')
a = p.parse_args()
captures = []
if a.capture_native:
    assert a.capture_native.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'work')
    a.capture_native.mkdir(parents=True,exist_ok=True)
lib = C.CDLL(str(a.library.resolve())); decode = lib.claw_pid_decode_surface_raster8
decode.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, C.c_uint32, C.POINTER(C.c_uint8),
                   C.POINTER(C.c_uint8), C.c_size_t, C.c_size_t, C.POINTER(Info)]
decode.restype = C.c_uint32
m = OriginalV10(a.exe); u = m.u; u.mem_map(0, 4096)
image, context, manager = 0x1000000, 0x1001000, 0x1002000
surface, node, display, display_vtable = 0x1004000, 0x1005000, 0x1006000, 0x1007000
dd, dd_vtable, raw, pixels = 0x1008000, 0x1009000, 0x1020000, 0x1080000
create, describe, lock, key, unlock = (0x10ef000 + i*16 for i in range(5))
m.write_words(display, [display_vtable]); m.write_words(display_vtable+0x18, [create])
m.write_words(dd, [dd_vtable])
for slot, entry in [(0x58, describe), (0x64, lock), (0x74, key), (0x80, unlock)]: m.write_words(dd_vtable+slot, [entry])
guard = 64; calls = decoded_pixels = zero_pixels = 0; rng = random.Random(1997)
events = []; current = {}
def host_return(pop, result):
    sp = u.reg_read(UC_X86_REG_ESP); ret = m.read_words(sp, 1)[0]
    u.reg_write(UC_X86_REG_EAX, result); u.reg_write(UC_X86_REG_ESP, sp+4+pop); u.reg_write(UC_X86_REG_EIP, ret)
def descriptor(address):
    u.mem_write(address, bytes(108))
    for off, value in [(0,108),(4,7),(8,current['h']),(12,current['w']),(16,current['pitch']),
                       (36,pixels+guard),(72,32),(76,32),(84,8)]: m.write_words(address+off, [value])
def host(uc, address, size, user):
    if address not in (0x4f63ec, create, describe, lock, key, unlock): return
    sp = u.reg_read(UC_X86_REG_ESP)
    if address == 0x4f63ec:
        assert m.read_words(sp+4,1) == [188]
        events.append(('malloc',188)); u.mem_write(surface, bytes(188)); host_return(0,surface)
    elif address == create:
        obj, desc, result, aggregation = m.read_words(sp+4,4)
        assert obj == display and result == surface+8 and aggregation == 0
        assert m.read_words(desc,4) == [108,7,current['h'],current['w']]
        current['creationFlags'] = m.read_words(surface+0x74,1)[0]
        m.write_words(result,[dd]); events.append(('create',)); host_return(16,0)
    elif address == describe:
        obj, desc = m.read_words(sp+4,2); assert obj == dd and desc == surface+12
        descriptor(desc); events.append(('describe',)); host_return(8,0)
    elif address == lock:
        obj, rect, desc, flags, event = m.read_words(sp+4,5)
        assert [obj,rect,desc,flags,event] == [dd,0,surface+12,1,0]
        descriptor(desc); events.append(('lock',)); host_return(20,0)
    elif address == key:
        obj, flags, value = m.read_words(sp+4,3); assert [obj,flags] == [dd,8]
        pair = m.read_words(value,2); assert pair[0] == pair[1]
        events.append(('key',pair[0])); host_return(12,0)
    else:
        assert m.read_words(sp+4,2) == [dd,0]
        events.append(('unlock',)); host_return(8,0)
u.hook_add(UC_HOOK_CODE,host)

def check(data, label, color_modes=(0,1), asset=False):
    global calls, decoded_pixels, zero_pixels
    _, flags, w, h, ox, oy, _, _ = struct.unpack('<8I',data[:32]); assert not flags & 32
    pitch = w+rng.randrange(0,12); size = pitch*h
    assert len(data) < pixels-raw and size+guard*2 < 0x10ef000-pixels
    source = (C.c_uint8*len(data)).from_buffer_copy(data)
    for use_key in color_modes:
        native = (C.c_uint8*size)(*([0x79]*size)); cov = (C.c_uint8*size)(*([0x41]*size)); info = Info()
        assert decode(source,len(data),use_key,native,cov,size,pitch,C.byref(info)) == 1,label
        assert (info.width, info.height, info.offsetX, info.offsetY, info.colorKeyEnabled) == (w,h,C.c_int32(ox).value,C.c_int32(oy).value,bool(flags&1 and use_key))
        for y in range(h):
            assert bytes(native)[y*pitch+w:(y+1)*pitch] == bytes([0x79])*(pitch-w)
            assert bytes(cov)[y*pitch+w:(y+1)*pitch] == bytes([0x41])*(pitch-w)
            for x in range(w): assert cov[y*pitch+x] == (0 if info.colorKeyEnabled and native[y*pitch+x]==0 else 1)
        before = bytes([0x9a])*(size+guard*2); expected = bytearray(before)
        for y in range(h): expected[guard+y*pitch:guard+y*pitch+w] = bytes(native)[y*pitch:y*pitch+w]
        current.clear(); current.update(w=w,h=h,pitch=pitch)
        u.mem_write(pixels,before); u.mem_write(raw,data); u.mem_write(image,bytes(64)); u.mem_write(manager,bytes(0x900))
        m.write_words(image+12,[context]); m.write_words(context+0x1c,[manager])
        m.write_words(manager,[display]); m.write_words(manager+0x474,[8])
        # Preexisting free list node avoids an unrelated MFC block allocation;
        # registration 0x4bc490 / 0x4f51c5 / 0x4f5692 still executes unchanged.
        u.mem_write(node,bytes(12)); m.write_words(manager+0x3c8,[node])
        m.write_words(0x54316c,[0]); m.write_words(0x543170,[0]); events.clear()
        #Shared GAME assets include large interface screens. Keep an explicit
        #size-derived instruction bound while executing their complete loader.
        result = m.call(0x4d2410,image,packed(raw,4,len(data),use_key),max_instructions=max(500000,w*h*40))
        assert result == 1,(label,'image load')
        required = [('malloc',188),('create',),('describe',),('lock',),('unlock',)]
        if flags&1: required.append(('key',0 if use_key else 0xffffffff))
        assert events == required,(label,events)
        assert bytes(u.mem_read(pixels,size+guard*2)) == expected,(label,'full original decoder writes')
        if asset and use_key and a.capture_native:
            index=len(captures);visible=b''.join(bytes(u.mem_read(pixels+guard+y*pitch,w))for y in range(h))
            (a.capture_native/f'{index}.surface').write_bytes(visible)
            captures.append(dict(index=index,path=str(label),width=w,height=h,flags=flags,
                fileBytes=len(data),fileSHA256=hashlib.sha256(data).hexdigest(),pixelSHA256=hashlib.sha256(visible).hexdigest()))
        fields = m.read_words(image+0x10,8)
        assert fields == [w,h,w//2,h//2,ox,oy,17 if info.colorKeyEnabled else 16,surface],(label,fields)
        assert m.read_words(surface+0xb8,1) == [info.colorKeyEnabled]
        assert m.read_words(surface+4,1) == [node] and m.read_words(node+8,1)==[surface]
        expected_flags = 0x840 if flags&4 else 0x40
        assert current['creationFlags'] == expected_flags
        assert bytes(u.mem_read(raw,len(data))) == data,(label,'source mutation')
        calls += 1
    decoded_pixels += w*h
    zero_pixels += sum(native[y*pitch+x]==0 for y in range(h) for x in range(w))
    return bytes(native), bytes(cov), info

# 0xc0 consumes its following byte but contributes zero pixels. Literal 0x80,
# 0xbf and zero remain literal. Repeat 0xff emits 63 values. Rows reset pitch.
check(header(8,2,1,-7,9)+bytes([0xc0,0xee,0,0x80,0xbf,0xc2,0,0xc3,255,0xc8,7]),'zero-run/literal-zero/row-boundary')
for first_word in (0,0x1869f,0xffffffff):
    check(packed(first_word)+header(4,1)[4:]+bytes([0xc4,7]),('opaque header word',first_word))
for flags in (0,1,2,3,4,5,8,16,64,128,129):
    body = bytes([0xc4,0,0xc4,192])
    check(header(4,2,flags)+body+(bytes(range(256))*3 if flags&128 else b''),('flags',flags))
for index in range(1000):
    w,h = rng.randrange(1,33)*4,rng.randrange(1,17); body = bytearray()
    for y in range(h):
        x=0
        while x<w:
            if rng.randrange(8)==0: body.extend([0xc0,rng.randrange(256)])
            n=rng.randrange(1,min(63,w-x)+1); value=rng.randrange(256)
            if n==1 and value<192 and rng.randrange(2): body.append(value)
            else: body.extend([192+n,value])
            x+=n
    check(header(w,h,rng.randrange(4),rng.getrandbits(32),rng.getrandbits(32))+body,('generated',index))
print('PASS 1,000 generated uncompressed rasters, literal zero, 0xc0 zero runs, index>=192, row boundaries, all header flag probes and embedded palettes through full original image loader',flush=True)
if a.assets:
    counts = {}; tile_count=0
    for path in sorted(a.assets.rglob('*.PID')):
        data = path.read_bytes(); flags = struct.unpack_from('<I',data,4)[0]
        if not flags&32:
            check(data,str(path),asset=True); counts[flags]=counts.get(flags,0)+1
            if 'TILES' in path.parts: tile_count+=1
    print(f'PASS all {sum(counts.values())} actual uncompressed assets under {a.assets} ({tile_count} tiles), flags {counts}, color key both enabled/disabled',flush=True)

valid=header(4,1)+bytes([0xc4,0])
for invalid in [b'',valid[:31],valid[:-1],header(4,1,32)+valid[32:],header(3,1)+bytes([0xc3,1]),
                header(4,1)+bytes([0xc5,1]),header(4,1)+bytes([0xc0,1]),header(4,1,128)+valid[32:]]:
    source=(C.c_uint8*len(invalid)).from_buffer_copy(invalid); out=(C.c_uint8*24)(*([0x99]*24)); cov=(C.c_uint8*24)(*([0x77]*24)); info=Info(123,456,7,8,999,42); before=bytes(info)
    assert decode(source,len(invalid),1,out,cov,24,6,C.byref(info))==0
    assert bytes(out)==bytes([0x99])*24 and bytes(cov)==bytes([0x77])*24 and bytes(info)==before
# Independent original rejection for non-four-aligned width happens before allocation.
u.mem_write(raw,header(3,1)+bytes([1,2,3])); events.clear()
assert m.call(0x4bf310,surface,packed(manager,raw,35,0x40,0))==0 and events==[]
# Execute the original 8-bit mode setter rather than assume its key constant.
m.write_words(context+0x30,[manager]); m.write_words(0x543170,[123])
assert m.call(0x42c640,context,packed(8))==1 and m.read_words(0x543170,1)==[0]
assert {0x4d2410,0x4bc520,0x4bf9c0,0x4bf310,0x4b9180,0x4b9380,0x4babe0,0x4b9730,0x4bb0e0,0x4b9990,0x4b9950,0x4bc490,0x4f51c5,0x4f5692} <= m.executed
print('PASS native malformed rejection without output mutation and original 8-bit zero color-key initialization',flush=True)
original_addresses = m.executed - {0x4f63ec, create, describe, lock, key, unlock, m.stop}
print(f'{calls} full original image-loader calls; {decoded_pixels} source pixels; {zero_pixels} zero-index pixels; {len(original_addresses)} original instruction addresses (adapter/stop entries excluded). Adapters only CRT allocation and five DirectDraw COM methods; no original pixel or image-loader stubs.',flush=True)

if a.capture_native:
    assert a.assets and len(captures)==sum(counts.values()) and captures
    (a.capture_native/'profiles.json').write_text(json.dumps(captures,indent=2)+'\n')
    print(f'PASS{len(captures)} original-captured whole PID image-loader visible surfaces for native factory replay; source/asset hashes and captures private',flush=True)
