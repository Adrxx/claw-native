"""Read-only Level 1 discovery from the original menu; no game substitutes.

Run with work/test-env/bin/python -m Tests.NativeLevelOne.trace.
Derived output stays in ignored work/. Exit 2 retains an exact incomplete trace.
"""
import argparse
import hashlib
import json
import math
import pickle
import struct
from pathlib import Path

from unicorn import UcError
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW,
    UC_X86_REG_FPSW, UC_X86_REG_FPTAG, UC_X86_REG_FP0)
from Tests.NativeMenuBase.trace import MenuTrace, Blocked, ROOT, STACK, REZ_PATH, REZ_SHA256, game, parse_xmidi


def linear_xmidi_ticks(data):
    """Bounded AIL fixed-120-Hz sequence clock, without audio synthesis.

    AIL's XMIDI specification (archived by WildMIDI) defines real-time intervals
    independently of MIDI tempo. Branch/loop/trigger controllers require a richer
    physical sequencer and are rejected instead of silently ignored.
    https://github.com/Mindwerks/wildmidi/blob/master/docs/formats/XMIFileFormat-AIL.txt
    """
    parsed=parse_xmidi(data)
    streams=[]
    def chunks(start,end):
        while start<end:
            tag=data[start:start+4];length=int.from_bytes(data[start+4:start+8],'big')
            body=start+8;limit=body+length
            if tag in (b'FORM',b'CAT '):chunks(body+4,limit)
            elif tag==b'EVNT':streams.append(data[body:limit])
            start=limit+(length&1)
    chunks(0,len(data))
    stream=streams[0];cursor=0;tick=0
    def byte():
        nonlocal cursor
        value=stream[cursor];cursor+=1
        return value
    def variable():
        result=0
        while True:
            value=byte();result=result*128+(value&127)
            if value<128:return result
    while cursor<len(stream):
        status=byte()
        if status<128:tick+=status;continue
        if status==255:
            meta=byte();length=variable();payload=stream[cursor:cursor+length];cursor+=length
            if meta not in (0x2f,0x51,0x54,0x58,0x21,0x59) or (meta==0x51 and (tick or length!=3)):
                raise Blocked('Unsupported XMIDI clock metadata')
            if meta==0x2f:break
        elif status in (0xf0,0xf7):
            raise Blocked('XMIDI SysEx needs a physical sequencer provider')
        else:
            message=status>>4
            values=[byte() for _ in range(1 if message in (12,13) else 2)]
            if message==11 and values[0]>=110:
                raise Blocked('XMIDI branch/loop/trigger controller is outside the linear clock profile')
            if message==9:variable()
    if not parsed['duration_ticks']:raise Blocked('Zero-duration XMIDI sequence')
    return parsed['duration_ticks']


class LevelOneTrace(MenuTrace):
    # Opaque stock SYSTEM_FONT token. It is never guest memory or a game object.
    STOCK_FONT = 0x8000000d

    # Reviewed game-owned spatial-grid bodies lie between CRT and MFC code.
    # Never replace them with a platform fixture merely because of their range.
    @staticmethod
    def is_game(address):
        return game(address) or 0x4f4490 <= address < 0x4f4a8c or 0x4f4a90 <= address < 0x4f4aa0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer_fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.parent_fingerprint = hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest()
        self.machine.mem_map(0x62000000,0x7000000)
        self.heap_limit=0x69000000
        self.sort_frame = None
        self.checkpoint_path = None
        self.navigation = []
        self.play_frames = []
        self.pickup_events = []
        self.pickup_pending = None
        self.completed_play_ms = 0
        self.level_one_loaded = False
        self.input_bindings = None
        self.resumed_checkpoint = False
        self.fonts = {}
        self.entries.update((0x4f4490,0x4f45f0,0x4f4630,0x4f4680,0x4f46b0,
                             0x4f4860,0x4f48a0,0x4f49c0,0x4f4a90))
        self.input_plan = [
            dict(start_ms=0, end_ms=2000, action='stand', keys=[]),
            dict(start_ms=2000, end_ms=3500, action='walk-right', keys=[0x27]),
            dict(start_ms=3500, end_ms=3900, action='attack', keys=[0x11]),
            dict(start_ms=3900, end_ms=4100, action='stand', keys=[]),
            dict(start_ms=4100, end_ms=4500, action='attack', keys=[0x11]),
            dict(start_ms=4500, end_ms=4700, action='stand', keys=[]),
            dict(start_ms=4700, end_ms=5100, action='attack', keys=[0x11]),
            dict(start_ms=5100, end_ms=8000, action='walk-right-toward-treasure', keys=[0x27]),
            dict(start_ms=8000, end_ms=10000, action='jump-right', keys=[0x27, 0x20]),
            dict(start_ms=10000, end_ms=12000, action='attack', keys=[0x11]),
            dict(start_ms=12000, end_ms=20000, action='walk-right-toward-treasure', keys=[0x27]),
            dict(start_ms=20000, end_ms=30000, action='stand', keys=[]),
        ]

    def allocate(self, size):
        if not 0<=size<=0x800000:
            raise Blocked(f'Invalid physical allocation size {size}')
        address=self.heap_next
        following=address+((max(size,1)+15)&~15)
        if following>=getattr(self,'heap_limit',0x62000000):
            raise Blocked('Bounded Level 1 fixture heap exhausted')
        self.heap_next=following
        self.allocations[address]=size
        self.machine.mem_write(address,b'\xa5'*max(size,1))
        return address

    def run(self, *args, **kwargs):
        phase = kwargs.get('phase', '')
        if phase == 'menu-text-static-initialization':
            result = 0
            # Hash-pinned CRT initializer table. Native startup replaces CRT/MFC
            # initialization, but every game initializer runs in table order.
            if self.word(0x522000) or self.word(0x522244):
                raise Blocked('Original static initializer table sentinel mismatch')
            for slot in range(0x522004,0x522244,4):
                entry = self.word(slot)
                if entry == 0x4251e0:
                    self.startup_evidence.append(dict(table_slot=hex(slot), native_replacement='CWinApp process/window startup; original 0x4251e0 is only its wrapper'))
                    continue
                if game(entry):
                    result = super().run(entry,0,phase=f'game-static-{entry:06x}')
                    self.startup_evidence.append(dict(table_slot=hex(slot), original_initializer=hex(entry)))
            return result
        if not phase.startswith('play-'):
            print(json.dumps(dict(event='phase', phase=phase, instructions=self.instructions)), flush=True)
        return super().run(*args, **kwargs)

    def hook(self, machine, address, size, user):
        if address == 0x41f850:
            sp = machine.reg_read(UC_X86_REG_ESP)
            item, private = self.word(sp+4), self.word(sp+8)
            if self.word(sp) != 0x41d135 or self.pickup_pending is not None:
                raise Blocked('Unreviewed treasure counter caller')
            self.pickup_pending = dict(item=hex(item), item_type=self.word(item+4),
                value=self.word(item+0xfc), private=hex(private), phase=self.phase,
                milliseconds=self.milliseconds, before=[self.word(private+0x88+4*i) for i in range(10)])
        if address == 0x41d135 and self.pickup_pending is not None:
            event = self.pickup_pending
            private = int(event['private'],16)
            event['after'] = [self.word(private+0x88+4*i) for i in range(10)]
            event['increment'] = sum(event['after'])-sum(event['before'])
            self.pickup_events.append(event)
            self.pickup_pending = None
        if address == 0x7000f020:
            frame=self.sort_frame
            if frame is None:
                raise Blocked('Unexpected sort callback return')
            cpu=self.cpu_state()
            if (machine.reg_read(UC_X86_REG_ESP)!=frame['callback_sp']+4 or self.word(0)!=frame['fs']
                    or any(cpu[i]!=frame['cpu'][i] for i in (1,4,5,6,10,12))
                    or (cpu[11]&0x3800)!=(frame['cpu'][11]&0x3800)
                    or any(cpu[13+i]!=frame['cpu'][13+i] for i in range(8)
                           if (cpu[12]>>(2*i))&3 != 3)):
                raise Blocked('Sort comparator corrupted preserved CPU/stack/exception state')
            value=machine.reg_read(UC_X86_REG_EAX)
            machine.context_restore(frame['context'])
            frame['event']['comparisons']+=1
            if 0 < value < 0x80000000:
                left,right=frame['base']+frame['j']-1,frame['base']+frame['j']
                a,b=bytes(machine.mem_read(left,1)),bytes(machine.mem_read(right,1))
                machine.mem_write(left,b);machine.mem_write(right,a)
                frame['event']['swaps']+=1
                frame['j']-=1
            else:
                frame['j']=0
            if not frame['j']:
                frame['i']+=1;frame['j']=frame['i']
            if frame['i'] == 256:
                frame['event']['completed']=True
                self.sort_frame=None
                self.returned(0)
            else:
                self.sort_compare()
            return
        # Every state initializer shares this factory continuation. The parent
        # receipt is specifically the menu's initial invocation, not later states.
        if address == 0x429335 and self.phase != 'menu-initialization':
            saved = self.initializer_return
            self.initializer_return = None
            try:
                super().hook(machine,address,size,user)
            finally:
                self.initializer_return = saved
            return
        super().hook(machine,address,size,user)

    def setup_resources(self, application, scene):
        with REZ_PATH.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != REZ_SHA256:
            raise Blocked('Original disc archive hash mismatch')
        self.resource_evidence = dict(archive=str(REZ_PATH.relative_to(ROOT)), sha256=digest,
                                      status='constructing')
        archive = self.allocate(0x48)
        self.run(0x4b7210, archive, phase='archive-construction', stack=STACK - 0x4000)
        path = self.cstring(b'CLAW.REZ')
        result = self.run(0x4b72e0, archive, (path, 1, 0),
                          phase='archive-open', stack=STACK - 0x4000)
        self.resource_evidence.update(archive_object=hex(archive), open_result=result,
                                     root=hex(self.word(archive + 0x24)))
        if not result or not self.word(archive + 0x24):
            raise Blocked('Original archive open failed; resource root is unavailable')
        self.resource_evidence['status'] = 'opened'
        # Native startup publishes actual objects and physical dimensions. No
        # directory nodes, readiness results, or game resources are fabricated.
        self.put(application + 0x30, scene)
        self.put(application + 0x34, archive)
        # Original IFC image callbacks obtain this same application through
        # the process-wide application slot supplied by native startup.
        self.put(0x5371fc, application)
        self.put(application + 0x7c, 640)
        self.put(application + 0x80, 480)
        self.setup_settings(application)
        self.setup_window(application)
        self.setup_input()
        self.setup_profile(application)
        self.setup_music(application)
        self.setup_volumes(application)
        if self.startup_paper:
            self.setup_paper_startup(application)
        # Execute the complete unchanged game registration routine. Its
        # callbacks and per-class setup are part of the discovery census.
        self.run(0x401000, 0, (scene,), phase='game-logic-registration', stack=STACK-0x4000)
        self.startup_evidence.append(dict(registration='0x401000', scene=hex(scene),
            profile='all original registrations in original order'))

    def com_fixture(self, address):
        kind, method = self.com_methods[address]
        sp = self.machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i: self.word(sp+4*i)
        if (kind,method)==('IDirectDrawSurface','Blt') and arg(5)==0x01000400 and arg(2):
            self.platform_call(address, 'IDirectDrawSurface::Blt')
            obj = self.com_objects.get(arg(1))
            fx = arg(6)
            if (not obj or obj['kind'] != kind or not obj['references'] or obj['lost'] or obj['locked']
                    or arg(3) or arg(4) or not fx or self.word(fx)!=100
                    or self.word(fx+80)>255
                    or any(self.word(fx+4*i) for i in range(1,25) if i!=20)):
                raise Blocked('Invalid rectangular indexed fill descriptor or surface')
            left,top,right,bottom=struct.unpack('<4i',bytes(self.machine.mem_read(arg(2),16)))
            if not (0<=left<right<=obj['width'] and 0<=top<bottom<=obj['height']):
                raise Blocked(f'Unsupported fill rectangle {(left,top,right,bottom)}')
            color=self.word(fx+80)
            for y in range(top,bottom):
                self.machine.mem_write(obj['pixels']+y*obj['pitch']+left,bytes([color])*(right-left))
            self.physical_events.append(dict(service='IDirectDrawSurface::Blt',object=hex(arg(1)),
                phase=self.phase,milliseconds=self.milliseconds,caller=self.last_transfer,
                rectangle=[left,top,right,bottom],fill_color=color,flags=arg(5)))
            self.returned(0,24)
            return
        return super().com_fixture(address)

    def text_fixture(self, api, arg):
        # Both the stock font and the elected CreateFontA profile use the
        # explicitly reported embedded physical font, not Windows glyph parity.
        handle = self.dcs.get(arg(1), {}).get('font', self.STOCK_FONT)
        if handle != self.STOCK_FONT and handle not in self.fonts:
            raise Blocked('Text DC refers to a deleted physical font')
        super().text_fixture(api, arg)
        if api == 'DrawTextA':
            self.physical_events[-1].update(selected_font=hex(handle),
                physical_font=self.font_evidence,
                logical_font=self.fonts.get(handle, {'stock': 'SYSTEM_FONT'}).copy())

    def sort_compare(self):
        f=self.sort_frame
        sp=f['callback_sp']
        for i,value in enumerate((0x7000f020,f['base']+f['j']-1,f['base']+f['j'])):
            self.put(sp+4*i,value)
        self.machine.reg_write(UC_X86_REG_ESP,sp)
        self.machine.reg_write(UC_X86_REG_EIP,0x4c70b0)
        self.pending=(0x4f1e20,'platform_callback')

    def fixture(self, address):
        if address == 0x4f2190:
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            if self.bytestring(self.word(sp+4)) != b'' or self.word(sp+8) != 0:
                raise Blocked('Paper access probe is outside the empty optional path profile')
            self.platform_call(address, 'CRT _access empty path')
            self.returned(0xffffffff)
            return
        if address == 0x4f650f:
            self.platform_call(address,'MFC CString Empty')
            receiver=self.machine.reg_read(UC_X86_REG_ECX)
            if not receiver:raise Blocked('Null native CString receiver')
            pointer=self.word(receiver)
            if not pointer:raise Blocked('Null native CString storage')
            length,capacity=self.word(pointer-8),self.word(pointer-4)
            if length>capacity or capacity>0x100000:
                raise Blocked('Invalid native CString clear capacity')
            if length:self.put(receiver,self.cstring(b''))
            self.returned(0)
            return
        if address == 0x4f5288:
            self.platform_call(address,'MFC CStringList RemoveAll empty list')
            receiver=self.machine.reg_read(UC_X86_REG_ECX)
            if not receiver or self.word(receiver)!=0x510224 or any(
                    self.word(receiver+offset) for offset in (4,8,12,16,20)):
                raise Blocked('Only a validated empty native string list can be cleared')
            self.physical_events.append(dict(service='CStringList RemoveAll',receiver=hex(receiver),count=0))
            self.returned(0)
            return
        if address == 0x4ffa56:
            self.platform_call(address,'MFC CRect InflateRect four sides')
            receiver=self.machine.reg_read(UC_X86_REG_ECX)
            if not receiver:raise Blocked('Null physical rectangle')
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            left,top,right,bottom=(self.word(sp+4*i) for i in range(1,5))
            rectangle=[self.word(receiver+4*i) for i in range(4)]
            for i,delta in enumerate((-left,-top,right,bottom)):
                self.put(receiver+4*i,(rectangle[i]+delta)&0xffffffff)
            self.returned(0,16)
            return
        if address in (0x4f6974,0x4f69eb,0x4f69c3):
            self.platform_call(address,{0x4f6974:'CString GetBuffer',0x4f69eb:'CString GetBufferSetLength',
                                       0x4f69c3:'CString ReleaseBuffer'}[address])
            receiver=self.machine.reg_read(UC_X86_REG_ECX)
            size=self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            pointer=self.word(receiver);length=self.word(pointer-8);capacity=self.word(pointer-4)
            if capacity>0x100000 or length>capacity:raise Blocked('Invalid native CString capacity')
            if address==0x4f69c3:
                if size==0xffffffff:
                    data=bytes(self.machine.mem_read(pointer,capacity+1))
                    if b'\0' not in data:raise Blocked('Unterminated CString ReleaseBuffer')
                    size=data.index(0)
                if size>capacity:raise Blocked('CString release length exceeds its buffer')
                self.put(pointer-8,size);self.machine.mem_write(pointer+size,b'\0')
                self.returned(0,4)
                return
            if size>0x100000:raise Blocked('Unbounded CString buffer request')
            references=self.word(pointer-12)
            if size>capacity or 1<references<0x80000000:
                capacity=max(size,length)
                data=bytes(self.machine.mem_read(pointer,length+1))
                pointer=self.allocate(capacity+13)+12
                self.machine.mem_write(pointer-12,struct.pack('<3I',1,length,capacity))
                self.machine.mem_write(pointer,data);self.put(receiver,pointer)
            if address==0x4f69eb:
                self.put(pointer-8,size);self.machine.mem_write(pointer+size,b'\0')
            self.returned(pointer,4)
            return
        if address == 0x4f5249:
            self.platform_call(address,'MFC CStringList constructor')
            receiver=self.machine.reg_read(UC_X86_REG_ECX)
            block=self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            if not 0<block<=4096:raise Blocked('Unsupported string-list block size')
            self.machine.mem_write(receiver,struct.pack('<7I',0x510224,0,0,0,0,0,block))
            self.returned(receiver,4)
            return
        if address == 0x4a5290:
            self.platform_call(address,'CRT memmove')
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            destination,source,count=(self.word(sp+4*i) for i in range(1,4))
            if count>0x800000 or (count and (not destination or not source)):
                raise Blocked('Unsupported physical memory move range')
            if count:
                self.machine.mem_write(destination,bytes(self.machine.mem_read(source,count)))
            self.returned(destination)
            return
        if address in (0x4b0d30,0x4b0d60,0x4b0d90):
            name={0x4b0d30:'isdigit',0x4b0d60:'isspace',0x4b0d90:'isprint'}[address]
            self.platform_call(address,'CRT '+name)
            value=self.word(self.machine.reg_read(UC_X86_REG_ESP)+4)
            if value!=0xffffffff and value>127:
                raise Blocked('Character classification requires the elected ASCII C locale')
            bits=0
            if 65<=value<=90:bits=0x101
            elif 97<=value<=122:bits=0x102
            elif 48<=value<=57:bits=4
            elif 33<=value<=126:bits=0x10
            elif value==32:bits=0x48
            elif value in (9,10,11,12,13):bits=8
            result=bits&{0x4b0d30:4,0x4b0d60:8,0x4b0d90:0x157}[address]
            self.returned(result)
            return
        if address == 0x4a4590 and self.word(self.machine.reg_read(UC_X86_REG_ESP)+12)>4096:
            self.platform_call(address,'CRT vector constructor iterator')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            base,stride,count,constructor,destructor = (self.word(sp+4*i) for i in range(1,6))
            if (stride,constructor,destructor)!=(8,0x4f4a90,0x4c96b0) or count>65536 or not any(
                    start<=base and base+stride*count<=start+length for start,length in self.allocations.items()):
                raise Blocked('Unsupported or unallocated large grid vector')
            event = dict(service='CRT vector constructor iterator',base=hex(base),stride=stride,count=count,
                constructor=hex(constructor),destructor=hex(destructor),completed=0)
            self.physical_events.append(event)
            self.array_callbacks.append(dict(context=self.machine.context_save(),fs=self.word(0),sp=sp,
                cpu=self.cpu_state(),base=base,stride=stride,count=count,constructor=constructor,index=0,
                event=event,pop=20,service=address))
            self.start_array_element(self.array_callbacks[-1])
            return
        if address == 0x4a49b0:
            self.platform_call(address, 'CRT free')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            pointer = self.word(sp+4)
            if pointer and pointer not in self.allocations:
                raise Blocked('Free of unknown or retired allocation')
            size = self.allocations.pop(pointer, None)
            self.physical_events.append(dict(service='CRT free', pointer=hex(pointer), size=size))
            self.returned(0)
            return
        if address == 0x4adf50:
            self.platform_call(address, 'CRT calloc')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            count, width = self.word(sp+4), self.word(sp+8)
            size = count * width
            if size > 0x800000:
                raise Blocked('Unsupported physical calloc size or overflow')
            result = self.allocate(size)
            self.machine.mem_write(result, bytes(max(size, 1)))
            self.physical_events.append(dict(service='CRT calloc', count=count, width=width, result=hex(result)))
            self.returned(result)
            return
        if address == 0x4f1e20:
            self.platform_call(address,'CRT qsort')
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            base,count,width,compare=(self.word(sp+4*i) for i in range(1,5))
            if self.sort_frame or (count,width,compare)!=(256,1,0x4c70b0) or sp-64<0x01ff0000:
                raise Blocked('Unsupported physical qsort profile')
            self.machine.mem_read(base,count)
            event=dict(service='CRT qsort',base=hex(base),count=count,width=width,
                comparator=hex(compare),algorithm='deterministic adjacent insertion sort',comparisons=0,swaps=0,completed=False)
            self.physical_events.append(event)
            self.sort_frame=dict(base=base,i=1,j=1,callback_sp=sp-64,fs=self.word(0),
                cpu=self.cpu_state(),context=self.machine.context_save(),event=event)
            self.sort_compare()
            return
        if address == 0x4a9070:
            self.platform_call(address, 'CRT realloc')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            old,size = self.word(sp+4),self.word(sp+8)
            if old and old not in self.allocations:
                raise Blocked('Realloc of unknown allocation')
            result = self.allocate(size) if size else 0
            if result and old:
                self.machine.mem_write(result, bytes(self.machine.mem_read(old,min(size,self.allocations[old]))))
            self.allocations.pop(old,None)
            self.physical_events.append(dict(service='CRT realloc', previous=hex(old), result=hex(result), size=size))
            self.returned(result)
            return
        if address == 0x4a3040:
            self.platform_call(address, 'CRT srand')
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            self.random_state = self.word(sp+4)
            self.physical_events.append(dict(service='CRT srand', seed=self.random_state))
            self.returned(0)
            return
        if address == 0x4f5d00:
            receiver = self.machine.reg_read(UC_X86_REG_ECX)
            self.platform_call(address, 'CMapStringToPtr destructor')
            mapping = self.maps.get(receiver)
            if mapping is None:
                raise Blocked('Destructor of unknown native string map')
            cells = list(mapping.values())
            if len(set(cells)) != len(cells) or any(c not in self.allocations for c in cells):
                raise Blocked('Invalid native string-map association lifetime')
            for cell in cells:
                self.allocations.pop(cell)
            del self.maps[receiver]
            for offset in (4,12,16,20):
                self.put(receiver+offset,0)
            self.put(receiver,0x50becc)
            self.physical_events.append(dict(service='CMapStringToPtr destructor', receiver=hex(receiver), removed=len(cells)))
            self.returned(0)
            return
        api = self.imports.get(address, (None, ''))[1].split('!')[-1]
        if api in ('PtInRect','IsRectEmpty','OffsetRect','InflateRect','IntersectRect','UnionRect'):
            self.platform_call(address,self.imports[address][1])
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            arg=lambda i:self.word(sp+4*i)
            signed=lambda value:value if value<0x80000000 else value-0x100000000
            def rectangle(pointer):
                if not pointer:raise Blocked('Rectangle service requires valid storage')
                return tuple(struct.unpack('<4i',bytes(self.machine.mem_read(pointer,16))))
            def empty(rect):return rect[0]>=rect[2] or rect[1]>=rect[3]
            if api in ('PtInRect','IsRectEmpty','OffsetRect','InflateRect'):
                left,top,right,bottom=rectangle(arg(1))
                if api=='PtInRect':
                    x,y=signed(arg(2)),signed(arg(3))
                    self.returned(int(left<=x<right and top<=y<bottom),12)
                    return
                if api=='IsRectEmpty':
                    self.returned(int(left>=right or top>=bottom),4)
                    return
                x,y=signed(arg(2)),signed(arg(3))
                result=(left+x,top+y,right+x,bottom+y) if api=='OffsetRect' else (left-x,top-y,right+x,bottom+y)
                pop,success=12,1
            else:
                a,b=rectangle(arg(2)),rectangle(arg(3))
                if api=='IntersectRect':
                    result=(max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]))
                elif empty(a):result=b
                elif empty(b):result=a
                else:result=(min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
                pop,success=12,int(not empty(result))
                if not success:result=(0,0,0,0)
            if not arg(1):raise Blocked('Rectangle output storage is null')
            self.machine.mem_write(arg(1),struct.pack('<4I',*(v&0xffffffff for v in result)))
            self.returned(success,pop)
            return
        if api in ('SelectObject', 'DeleteObject'):
            self.platform_call(address, self.imports[address][1])
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            handle = self.word(sp + (8 if api == 'SelectObject' else 4))
            event = dict(service=api, font=hex(handle), phase=self.phase,
                         milliseconds=self.milliseconds, caller=self.last_transfer)
            if api == 'SelectObject':
                dc_handle = self.word(sp + 4)
                dc = self.dcs.get(dc_handle)
                if not dc:
                    raise Blocked('Unknown or released physical text DC')
                surface = self.com_objects[dc['surface']]
                if (not surface['references'] or surface['lost'] or not surface['locked']
                        or surface.get('dc') != dc_handle or dc['pixels'] != surface['pixels']):
                    raise Blocked('Physical text DC lost its surface lease')
                # Only fonts are elected here; other GDI object kinds need
                # their own physical providers, never scripted success.
                if handle != self.STOCK_FONT and handle not in self.fonts:
                    raise Blocked('Unknown, deleted or non-font physical GDI object')
                previous = dc.get('font', self.STOCK_FONT)
                dc['font'] = handle
                event.update(dc=hex(dc_handle), previous=hex(previous))
                self.returned(previous, 8)
            else:
                # Win32 DeleteObject fails for an invalid or selected object.
                # https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-deleteobject
                if handle == self.STOCK_FONT:
                    raise Blocked('Stock font deletion is outside the elected GDI profile')
                selected = any(dc.get('font', self.STOCK_FONT) == handle for dc in self.dcs.values())
                result = int(handle in self.fonts and not selected)
                if result:
                    del self.fonts[handle]
                    self.allocations.pop(handle)
                event.update(selected=selected, result=result)
                self.returned(result, 4)
            self.physical_events.append(event)
            return
        if api == 'CreateFontA':
            self.platform_call(address,self.imports[address][1])
            sp=self.machine.reg_read(UC_X86_REG_ESP)
            args=[self.word(sp+4*i) for i in range(1,15)]
            if args[:13] != [12,8,0,0,100,0,0,0,1,0,0,0,0]:
                raise Blocked('Unsupported native logical-font request')
            face=self.bytestring(args[13]).decode('ascii') if args[13] else ''
            handle=self.allocate(16)
            self.fonts[handle]=dict(height=12,width=8,requested_face=face,
                physical_font='Pillow embedded default')
            self.physical_events.append(dict(service=api,font=hex(handle),**self.fonts[handle]))
            self.returned(handle,56)
            return
        if api in ('_AIL_sequence_status@4','_AIL_start_sequence@4','_AIL_stop_sequence@4',
                   '_AIL_resume_sequence@4','_AIL_end_sequence@4','_AIL_set_sequence_loop_count@8',
                   '_AIL_release_sequence_handle@4'):
            self.platform_call(address,self.imports[address][1])
            sp=self.machine.reg_read(UC_X86_REG_ESP);handle=self.word(sp+4)
            sequence=self.sequences.get(handle)
            if not sequence or not sequence['initialized']:
                raise Blocked('Unknown/uninitialized physical XMIDI sequence')
            self.advance_sequences(self.milliseconds)
            if api in ('_AIL_start_sequence@4','_AIL_resume_sequence@4'):
                self.verify_sequence_clock(handle,sequence)
                if api=='_AIL_start_sequence@4':sequence['elapsed_units']=0
                sequence.update(status=4,started_ms=self.milliseconds,clock_ms=self.milliseconds)
            elif api=='_AIL_stop_sequence@4':sequence['status']=8
            elif api=='_AIL_end_sequence@4':sequence['status']=2
            elif api=='_AIL_set_sequence_loop_count@8':sequence['loops']=self.word(sp+8)
            elif api=='_AIL_release_sequence_handle@4':
                del self.sequences[handle];self.allocations.pop(handle)
            self.physical_events.append(dict(service=api,sequence=hex(handle),status=sequence['status'],
                elapsed_units=sequence.get('elapsed_units',0)))
            self.returned(sequence['status'] if api=='_AIL_sequence_status@4' else 0,
                8 if api=='_AIL_set_sequence_loop_count@8' else 4)
            return
        if api == 'CopyRect':
            # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-copyrect
            self.platform_call(address, self.imports[address][1])
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            destination, source = self.word(sp+4), self.word(sp+8)
            if not destination or not source:
                raise Blocked('CopyRect requires two valid rectangle pointers')
            data = bytes(self.machine.mem_read(source,16))
            self.machine.mem_write(destination,data)
            self.physical_events.append(dict(service=api, source=hex(source), destination=hex(destination),
                rectangle=list(struct.unpack('<4i',data))))
            self.returned(1,8)
            return
        if api == 'UpdateWindow':
            self.platform_call(address, self.imports[address][1])
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            if self.word(sp+4) != 1 or not self.presentations or getattr(self,'window_dirty',False):
                raise Blocked('UpdateWindow needs an established clean native window; dirty-region callbacks are unsupported')
            # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-updatewindow
            # The elected native window has already presented; no invalidation
            # service is supported silently, so an empty region sends no paint.
            self.physical_events.append(dict(service=api, window=1, update_region='empty', callbacks=0))
            self.returned(1,4)
            return
        if api == 'PostMessageA':
            sp = self.machine.reg_read(UC_X86_REG_ESP)
            values = tuple(self.word(sp+4*i) for i in range(1,5))
            if values[0] != 1 or values[1] != 0x111:
                return super().fixture(address)
            self.platform_call(address, self.imports[address][1])
            self.messages.append(values)
            self.physical_events.append(dict(service=api, window=values[0], message=values[1],
                wparam=values[2], lparam=values[3], delivery='queued, never inline'))
            self.returned(1,16)
            return
        return super().fixture(address)

    def math_fixture(self, address):
        if address == 0x4f1b30 and self.last_transfer and self.last_transfer['site'] in ('0x4f4532','0x4f454b'):
            before = self.x87_state()
            exponent, base = self.x87_value(0), self.x87_value(1)
            if before['control'] != 0x027f or base != 2 or not 0 <= exponent <= 30 or exponent != int(exponent):
                raise Blocked('Unsupported spatial-grid CRT power operands')
            result = math.ldexp(1.,int(exponent))
            eax = self.machine.reg_read(UC_X86_REG_EAX)
            self.x87_result(2,result)
            self.math_events.append(dict(address=hex(address),operands=[exponent,base],result=result,
                before=before,after=self.x87_state()))
            self.returned(eax)
            return
        return super().math_fixture(address)

    def verify_sequence_clock(self,handle,sequence):
        if sequence.get('clock_verified'):return
        event=next(e for e in reversed(self.physical_events)
            if e['service']=='_AIL_init_sequence@12' and e['sequence']==hex(handle))
        for address,length in self.allocations.items():
            if length!=event['bytes']:continue
            data=bytes(self.machine.mem_read(address,length))
            if hashlib.sha256(data).hexdigest()==sequence['sha256']:
                if linear_xmidi_ticks(data)!=sequence['duration_ticks']:
                    raise Blocked('XMIDI initialization and clock durations disagree')
                sequence['clock_verified']=True
                return
        raise Blocked('XMIDI clock could not validate its original initialized bytes')

    def advance_sequences(self,milliseconds):
        for handle,sequence in self.sequences.items():
            if sequence['status']!=4:continue
            self.verify_sequence_clock(handle,sequence)
            previous=sequence.get('clock_ms',sequence['started_ms'])
            if milliseconds<previous:raise Blocked('XMIDI physical clock moved backwards')
            elapsed=sequence.get('elapsed_units',0)+(milliseconds-previous)*120
            limit=sequence['duration_ticks']*1000*sequence['loops']
            sequence.update(elapsed_units=min(elapsed,limit) if limit else elapsed,clock_ms=milliseconds)
            if limit and elapsed>=limit:sequence.update(status=2,loops=1)

    def advance_time(self,milliseconds):
        if milliseconds<=self.milliseconds:raise Blocked('Physical frame clock must advance')
        self.advance_sequences(milliseconds)
        elapsed=milliseconds-self.milliseconds
        for obj in self.com_objects.values():
            if obj['kind']=='IDirectSoundBuffer' and obj.get('playing'):
                alignment=struct.unpack('<HHIIHHH',bytes.fromhex(obj['format']))[4]
                frames,obj['sample_remainder']=divmod(obj.get('sample_remainder',0)+elapsed*obj['frequency'],1000)
                position=obj['position']+frames*alignment
                if obj['looping']:obj['position']=position%obj['length']
                else:obj.update(position=min(position,obj['length']),playing=position<obj['length'])
        self.milliseconds=milliseconds

    def drain_messages(self, application):
        for _ in range(128):
            if not self.messages:
                return
            hwnd, message, wparam, lparam = self.messages.pop(0)
            if hwnd != 1 or message != 0x111:
                raise Blocked('No native delivery for queued window message')
            target = self.word(self.word(application)+0x14)
            self.navigation.append(dict(phase='posted-command-delivery', target=hex(target),
                message=message, wparam=wparam, lparam=lparam))
            if wparam == 0x807f:
                self.checkpoint_command = (target, application, (message,wparam,lparam))
                self.save_checkpoint()
            self.run(target, application, (message,wparam,lparam), phase=f'command-{wparam:04x}')
        raise Blocked('Bounded physical message queue did not drain')

    def menu_state(self, application):
        menu = self.word(application + 0x2c)
        if self.word(menu) != 0x50c1e4:
            return dict(object=hex(menu), vtable=hex(self.word(menu)), menu_id=None)
        return dict(object=hex(menu), vtable=hex(self.word(menu)),
                    menu_id=self.word(menu + 0x29c),
                    selection=self.word(menu + 0x154 + 0x1c),
                    launch_pending=self.word(menu + 0x294),
                    launch_command=self.word(menu + 0x298))

    def frame(self, application, phase, keys=()):
        self.pressed_keys = set(keys)
        self.advance_time(self.milliseconds + 17)
        before = len(self.presentations)
        result = self.run(0x428b60, application, phase=phase)
        self.frame_cycles.append(dict(phase=phase, milliseconds=self.milliseconds,
            keys=sorted(keys), presentations=len(self.presentations)-before, result=result))
        self.drain_messages(application)
        return result

    def save_checkpoint(self):
        if self.checkpoint_path is None:
            return
        excluded = {'machine', 'program', 'decoder', 'font', 'files', 'factory_context', 'checkpoint_path'}
        state = {k:v for k,v in self.__dict__.items() if k not in excluded}
        payload = dict(version=3, parent_sha256=hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest(),
            state=state, cpu=self.cpu_state(),
            memory=[(a, bytes(self.machine.mem_read(a, b-a+1))) for a,b,_ in self.machine.mem_regions()],
            files={k:(str(v.name),v.tell()) for k,v in self.files.items()})
        self.checkpoint_path.write_bytes(pickle.dumps(payload))

    def resume_checkpoint(self, path, *, completed_frame=False):
        # Only locally produced ignored research checkpoints are accepted. The
        # final retained run can bypass this cache; it is never admission proof.
        payload = pickle.loads(path.read_bytes())
        if payload['version'] != 3 or payload['parent_sha256'] != hashlib.sha256((ROOT/'Tests/NativeMenuBase/trace.py').read_bytes()).hexdigest():
            raise Blocked('Stale initialization checkpoint')
        if payload['state'].get('startup_paper', False) != self.startup_paper:
            raise Blocked('Checkpoint startup paper profile differs from the requested trace')
        with REZ_PATH.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != REZ_SHA256:
                raise Blocked('Original archive hash mismatch')
        instruction_limit, deny_platform = self.instruction_limit, self.deny_platform
        input_plan = self.input_plan
        tracer_fingerprint,parent_fingerprint=self.tracer_fingerprint,self.parent_fingerprint
        self.__dict__.update(payload['state'])
        self.instruction_limit, self.deny_platform = instruction_limit, deny_platform
        self.input_plan=input_plan
        self.tracer_fingerprint,self.parent_fingerprint=tracer_fingerprint,parent_fingerprint
        self.resumed_checkpoint = True
        for address, data in payload['memory']:
            self.machine.mem_write(address, data)
        registers = (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
            UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
            UC_X86_REG_EIP, UC_X86_REG_EFLAGS, UC_X86_REG_FPCW, UC_X86_REG_FPSW, UC_X86_REG_FPTAG)
        for r, v in zip(registers, payload['cpu']):
            self.machine.reg_write(r,v)
        for i,v in enumerate(payload['cpu'][len(registers):]):
            self.machine.reg_write(UC_X86_REG_FP0+i,v)
        for handle,(name,position) in payload['files'].items():
            if Path(name).resolve() != REZ_PATH.resolve():
                raise Blocked('Unexpected checkpoint file')
            self.files[handle] = open(name,'rb')
            self.files[handle].seek(position)
        self.checkpoint_path = path
        if completed_frame:
            self.navigate(self.application)
            return
        if hasattr(self, 'resume_pc'):
            self.stop = None
            self.machine.emu_start(self.resume_pc, 0x70000080)
            if self.machine.reg_read(UC_X86_REG_EIP) != 0x70000080 or self.machine.reg_read(UC_X86_REG_ESP) != STACK+16:
                raise Blocked('Resumed launch did not return with its stdcall3 stack')
            self.phase_results.append(dict(phase=self.phase,entry='0x426e30',
                result=self.machine.reg_read(UC_X86_REG_EAX),disposition='resumed-and-returned',pc='0x70000080'))
            del self.resume_pc
            self.drain_messages(self.application)
            self.finish_launch(self.application)
        elif hasattr(self, 'checkpoint_command'):
            target, application, arguments = self.checkpoint_command
            self.run(target, application, arguments, phase='command-807f')
            self.finish_launch(application)
        else:
            self.navigate(self.application)

    def finish_launch(self, application):
        self.navigation.append(dict(phase='launch-command-returned', state=self.menu_state(application)))
        state = self.word(application+0x2c)
        if self.word(state) != 0x50c264 or self.word(state+0x14) != 1:
            raise Blocked('Launch did not reach original single-player Level 1')
        controller = self.word(0x537204)
        bindings = {name:self.word(controller+offset) for name,offset in
            (('left',0x38),('right',0x3c),('up',0x40),('down',0x44),('jump',0x48),('attack',0x4c))}
        if bindings != dict(left=0x25,right=0x27,up=0x26,down=0x28,jump=0x20,attack=0x11):
            raise Blocked('Original input bindings differ from the scripted physical keys')
        self.input_bindings = dict(controller=hex(controller),keys=bindings,
            initializer='0x430d80',poller='0x430ec0',service='GetAsyncKeyState')
        self.level_one_loaded = True
        if not any(e.get('binding')=='application+0x12c' for e in self.startup_evidence):
            self.setup_audio_preferences(application)
        if not self.word(application+0x4c):self.setup_overlay(application)
        self.play(application)

    def setup_audio_preferences(self,application):
        # Native fresh-install configuration provider. Original startup asks
        # for Sound Volume with default 80 at 0x425ac1, then publishes at
        # 0x425ad9. This is a physical preference, not a game result.
        self.put(application+0x12c,80)
        self.startup_evidence.append(dict(binding='application+0x12c',setting='Sound Volume',
            value=80,profile='fresh install, no stored override',original_default='0x425ac1',publication='0x425ad9'))

    def setup_overlay(self,application):
        overlay=self.allocate(0x38)
        self.machine.reg_write(UC_X86_REG_EDI,overlay)
        self.machine.reg_write(UC_X86_REG_ESI,0)
        self.run(0x42614c,overlay,phase='message-overlay-inline-construction',boundary=0x42616b)
        if not self.paused:raise Blocked('Original message overlay constructor missed its continuation')
        self.put(application+0x4c,overlay)
        if not self.run(0x4222a0,overlay,(5000,2000),phase='message-overlay-initialization'):
            raise Blocked('Original message overlay initialization failed')
        self.startup_evidence.append(dict(object=hex(overlay),binding='application+0x4c',
            constructor='0x42614c..0x42616b',initializer='0x4222a0'))

    def player_snapshot(self, application):
        state = self.word(application+0x2c)
        actor = self.word(0x537e88)
        if not actor or actor not in self.allocations:
            raise Blocked('Original player actor is not live')
        logic = self.word(actor+0x6c)
        private = self.word(logic+0x14)
        if not private or private not in self.allocations:
            raise Blocked('Original player private state is not live')
        return dict(state=hex(state),vtable=hex(self.word(state)),level=self.word(state+0x14),
            actor=hex(actor),private=hex(private),x=self.word(actor+0x4c),y=self.word(actor+0x50),
            health=self.word(actor+0x10c),score=self.word(actor+0xf8),
            player_state=self.word(private),logic_state=self.word(logic+0x1c),
            treasure_counts=[self.word(private+0x88+4*i) for i in range(10)],
            input_mask=self.word(self.word(0x537204)+8),game_ms=self.word(0x537210))

    def play(self, application):
        self.clock_step = 0
        self.play_frames=[]
        self.completed_play_ms=0
        start = self.milliseconds
        self.play_frames.append(dict(elapsed_ms=0,action='loaded',player=self.player_snapshot(application)))
        while self.milliseconds-start < 30000:
            elapsed = self.milliseconds-start
            action = next(a for a in self.input_plan if a['start_ms']<=elapsed<a['end_ms'])
            self.frame(application, f'play-{action["action"]}', action['keys'])
            self.completed_play_ms = self.milliseconds-start
            if self.word(self.word(application+0x2c)) != 0x50c264:
                raise Blocked('Original gameplay left the single-player state')
            self.play_frames.append(dict(elapsed_ms=self.completed_play_ms,action=action['action'],
                player=self.player_snapshot(application)))
            if len(self.play_frames)%120 == 0:
                print(json.dumps(dict(event='gameplay',**self.play_frames[-1])),flush=True)
        if not any(e['increment']>0 and e['phase'].startswith('play-') for e in self.pickup_events):
            raise Blocked('Thirty seconds completed without observed original treasure pickup')

    def execute_frames(self, application):
        self.application = application
        self.frame(application, 'main-menu-first-presentation')
        self.save_checkpoint()
        self.navigate(application)

    def setup_navigation(self, application):
        # Deterministic physical timer queries advance by 1 ms, including busy
        # palette fades. Frame scheduling remains an additional 17 ms step.
        self.clock_step = 1
        if not self.word(application+0x58):
            palette_tables=self.allocate(0x18)
            self.run(0x4c61d0,palette_tables,phase='palette-table-construction')
            self.put(application+0x58,palette_tables)
            if not self.run(0x4c6260,palette_tables,phase='palette-table-initialization'):
                raise Blocked('Original palette-table manager initialization failed')
            self.startup_evidence.append(dict(object=hex(palette_tables),binding='application+0x58',
                constructor='0x4c61d0',initializer='0x4c6260'))
        sound_events = self.allocate(0x30)
        self.machine.reg_write(UC_X86_REG_EDI,sound_events)
        self.machine.reg_write(UC_X86_REG_ESI,0)
        self.run(0x4262c4,sound_events,phase='sound-events-inline-construction',boundary=0x4262d7)
        if not self.paused:
            raise Blocked('Sound-events constructor did not reach its continuation')
        self.put(application+0x5c,sound_events)
        scene=self.word(application+0x30)
        if not self.run(0x402240,sound_events,(self.word(scene+0x28),80),phase='sound-events-initialization'):
            raise Blocked('Original sound-events initialization failed')
        self.startup_evidence.append(dict(object=hex(sound_events),binding='application+0x5c',
            constructor='0x4262c4..0x4262d7',initializer='0x402240',volume=80))
        command_manager = self.allocate(0x12c)
        self.machine.reg_write(UC_X86_REG_EDI, command_manager)
        self.machine.reg_write(UC_X86_REG_ESI, 0)
        self.run(0x4260d3, command_manager, phase='command-manager-inline-construction', boundary=0x4260f5)
        if not self.paused:
            raise Blocked('Command-manager constructor did not reach its continuation')
        self.put(application+0x48, command_manager)
        self.run(0x422890, command_manager, (1,), phase='command-manager-initialization')
        self.startup_evidence.append(dict(object=hex(command_manager), binding='application+0x48',
            constructor='0x4260d3..0x4260f5', initializer='0x422890', physical_window=1))
        self.setup_overlay(application)

    def navigate(self, application):
        self.setup_navigation(application)
        self.navigation.append(dict(phase='main-menu', state=self.menu_state(application)))
        # Native event delivery replaces the Windows message pump. Invoke the
        # current state's original key-down virtual method, with a physical
        # Return key and one scan-code repeat. Do not alter game selection data.
        for label in ('single-player', 'new-game', 'new-game-confirmation'):
            menu = self.word(application + 0x2c)
            target = self.word(self.word(menu) + 0x30)
            self.navigation.append(dict(phase=label+'-key-delivery', key=13,
                target=hex(target), receiver=hex(menu), before=self.menu_state(application)))
            self.run(target, menu, (13, 0x001c0001), phase=label+'-key-down')
            for i in range(24):
                self.frame(application, label+f'-release-{i:02d}')
                if self.menu_state(application)['menu_id'] is None:
                    return self.finish_launch(application)
            self.navigation.append(dict(phase=label, state=self.menu_state(application)))
        raise Blocked('Navigation completed; Level 1 update identity still needs observation before scripted play')

    def report(self):
        result = super().report()
        result.update(tracer_sha256=self.tracer_fingerprint,
            startup_paper=self.startup_paper, clock_query_ms=1 if self.startup_paper else None,
            frame_step_ms=17,
            game_ranges=result['game_ranges']+[['0x4f4490','0x4f4a8c'],['0x4f4a90','0x4f4aa0']],
            menu_tracer_sha256=self.parent_fingerprint,
            scope='Original New Game discovery prefix; no native parity or admission claim',
            requested_play_ms=30000, completed_play_ms=self.completed_play_ms,
            limitations=['CRT qsort executes the original comparator but equivalent-key ordering is not original CRT parity; discovery only.', 'XMIDI provides validated linear 120 Hz timing and sequence status, not audible synthesis.', 'No native gameplay or rendered-pixel parity claimed.'],
            navigation=self.navigation, scripted_input=self.input_plan, play_frames=self.play_frames,
            level_one_loaded=self.level_one_loaded, input_bindings=self.input_bindings,
            player_field_evidence=dict(position='0x415ed6/0x415ed9: actor+0x4c/+0x50',
                health='0x41d0de..0x41d0fe: actor+0x10c, capped at 100',
                score='0x41d10d..0x41d11c: actor+0xf8 plus treasure value',
                treasure='0x41f850 called from 0x41d130: player private+0x88, ten category counters'),
            resumed_checkpoint=self.resumed_checkpoint,
            pickup_events=self.pickup_events,
            midi_clocks={hex(k):v for k,v in self.sequences.items()},
            treasure_pickup_observed=any(e['increment']>0 and e['phase'].startswith('play-') for e in self.pickup_events))
        if self.stop is None and self.completed_play_ms >= 30000 and result['treasure_pickup_observed']:
            result.update(status='pass',scope='Original Level 1 loading and 30000 ms input census; no native parity or admission claim')
        for entry in result['game_functions']:
            spans={'0x4260d3':'0x4260f5','0x4262c4':'0x4262d7','0x42614c':'0x42616b'}
            if entry['address'] in spans:
                entry.update(entry_kind='inline_startup_span', inline_end=spans[entry['address']])
                result['counts']['game_functions'] -= 1
                result['counts']['inline_startup_spans'] += 1
                result['counts']['game_entries'] -= entry['count']
        result.pop('requested_idle_frames', None)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/level-one-map/trace.json')
    parser.add_argument('--instruction-limit', type=int, default=2_000_000_000)
    parser.add_argument('--checkpoint', type=Path, help='Local startup cache under work/; omit for a fresh trace')
    parser.add_argument('--stop-checkpoint', type=Path, help='Save an unsupported launch boundary locally for diagnostic continuation')
    parser.add_argument('--deny-platform', type=lambda x: int(x, 0))
    parser.add_argument('--paper-startup', action='store_true',
                        help='Construct the original startup fader and palette before menu initialization')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT/'work').resolve()):
        parser.error('Derived output must stay under ignored work/')
    trace = LevelOneTrace(args.instruction_limit, args.deny_platform, startup_paper=args.paper_startup)
    try:
        if args.checkpoint:
            checkpoint = args.checkpoint.resolve()
            if not checkpoint.is_relative_to((ROOT/'work').resolve()):
                parser.error('Checkpoint must stay under work/')
            if checkpoint.exists():
                trace.resume_checkpoint(checkpoint)
            else:
                trace.checkpoint_path = checkpoint
                trace.execute()
        else:
            trace.execute()
    except (Blocked, UcError) as error:
        if trace.stop is None:
            trace.stop = dict(kind='unsupported_boundary', address=hex(trace.machine.reg_read(UC_X86_REG_EIP)), reason=str(error))
        trace.stop.update(phase=trace.phase, last_transfer=trace.last_transfer)
        if args.stop_checkpoint and trace.phase == 'command-807f' and not (trace.sort_frame or trace.callback or trace.array_callbacks):
            checkpoint = args.stop_checkpoint.resolve()
            if not checkpoint.is_relative_to((ROOT/'work').resolve()):
                parser.error('Checkpoint must stay under work/')
            trace.resume_pc = trace.machine.reg_read(UC_X86_REG_EIP)
            trace.checkpoint_path = checkpoint
            trace.save_checkpoint()
    finally:
        for stream in trace.files.values():
            stream.close()
    report = trace.report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], counts=report['counts'], stop=report['stop'], navigation=report['navigation'], output=str(output))), flush=True)
    return 0 if report['status']=='pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
