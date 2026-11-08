"""Focused physical-transport controls, not game parity or family admission."""
import unittest
import struct
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP
from Tests.NativeMenuBase.trace import STACK, STOP, Blocked
from Tests.NativeLevelOne.trace import LevelOneTrace, linear_xmidi_ticks


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.trace = LevelOneTrace()

    def call(self, address, receiver=0, args=()):
        t=self.trace
        for i,value in enumerate((STOP,*args)):
            t.put(STACK+4*i,value)
        t.machine.reg_write(UC_X86_REG_ESP,STACK)
        t.machine.reg_write(UC_X86_REG_ECX,receiver)
        t.fixture(address)
        return t.machine.reg_read(UC_X86_REG_EAX)

    def api(self,name):
        return next(a for a,(_,n) in self.trace.imports.items() if n.split('!')[-1]==name)

    def test_four_sided_rectangle_inflation(self):
        t=self.trace;rect=t.allocate(16)
        t.machine.mem_write(rect,struct.pack('<4i',-5,8,20,30))
        self.call(0x4ffa56,rect,(10,2,3,0xffffffff))
        self.assertEqual(struct.unpack('<4i',t.machine.mem_read(rect,16)),(-15,6,23,29))
        self.assertEqual(t.machine.reg_read(UC_X86_REG_ESP),STACK+20)
        with self.assertRaises(Blocked):self.call(0x4ffa56,0,(1,1,1,1))
        t.deny_platform=0x4ffa56
        with self.assertRaises(Blocked):self.call(0x4ffa56,rect,(1,1,1,1))

    def test_empty_string_list_clear_rejects_live_or_corrupt_nodes(self):
        t=self.trace;obj=t.allocate(28)
        self.call(0x4f5249,obj,(10,))
        self.call(0x4f5288,obj)
        self.assertEqual(t.word(obj+24),10)
        for offset in (0,4,8,12,16,20):
            old=t.word(obj+offset);t.put(obj+offset,1)
            with self.assertRaises(Blocked):self.call(0x4f5288,obj)
            t.put(obj+offset,old)
        t.deny_platform=0x4f5288
        with self.assertRaises(Blocked):self.call(0x4f5288,obj)

    def test_string_empty_preserves_other_aliases(self):
        t=self.trace;obj=t.allocate(4);old=t.cstring(b'overlay')
        t.put(obj,old);self.call(0x4f650f,obj)
        self.assertEqual(t.bytestring(t.word(obj)),b'')
        self.assertEqual(t.bytestring(old),b'overlay')
        empty=t.word(obj);self.call(0x4f650f,obj);self.assertEqual(t.word(obj),empty)
        t.put(empty-8,t.word(empty-4)+1)
        with self.assertRaises(Blocked):self.call(0x4f650f,obj)
        t.deny_platform=0x4f650f
        with self.assertRaises(Blocked):self.call(0x4f650f,obj)

    def test_seed_and_reallocation_preserve_storage(self):
        t=self.trace
        self.call(0x4a3040,args=(1,))
        self.assertEqual(self.call(0x4a3050),41)
        old=t.allocate(6)
        t.machine.mem_write(old,b'abcdef')
        new=self.call(0x4a9070,args=(old,10))
        self.assertEqual(bytes(t.machine.mem_read(new,6)),b'abcdef')
        self.assertNotIn(old,t.allocations)
        smaller=self.call(0x4a9070,args=(new,3))
        self.assertEqual(bytes(t.machine.mem_read(smaller,3)),b'abc')
        self.assertEqual(self.call(0x4a9070,args=(smaller,0)),0)
        with self.assertRaises(Blocked):
            self.call(0x4a9070,args=(smaller,4))

    def test_free_validates_lifetime_and_cdecl_stack(self):
        t=self.trace
        pointer=t.allocate(12)
        self.call(0x4a49b0,args=(0,))
        self.assertIn(pointer,t.allocations)
        t.deny_platform=0x4a49b0
        with self.assertRaises(Blocked):self.call(0x4a49b0,args=(pointer,))
        self.assertIn(pointer,t.allocations)
        t.deny_platform=None
        with self.assertRaises(Blocked):self.call(0x4a49b0,args=(pointer+1,))
        self.call(0x4a49b0,args=(pointer,))
        self.assertNotIn(pointer,t.allocations)
        self.assertEqual(t.machine.reg_read(UC_X86_REG_ESP),STACK+4)
        self.assertEqual(t.machine.reg_read(UC_X86_REG_EIP),STOP)
        with self.assertRaises(Blocked):self.call(0x4a49b0,args=(pointer,))

    def test_copy_rectangle_preserves_signed_values_and_aliases(self):
        t=self.trace;address=self.api('CopyRect')
        source=t.allocate(16);destination=t.allocate(16)
        data=struct.pack('<4i',-100,20,300,-40)
        t.machine.mem_write(source,data)
        t.deny_platform=address
        with self.assertRaises(Blocked):self.call(address,args=(destination,source))
        self.assertEqual(bytes(t.machine.mem_read(destination,16)),b'\xa5'*16)
        t.deny_platform=None
        self.assertEqual(self.call(address,args=(destination,source)),1)
        self.assertEqual(bytes(t.machine.mem_read(destination,16)),data)
        self.assertEqual(t.machine.reg_read(UC_X86_REG_ESP),STACK+12)
        self.call(address,args=(source,source))
        self.assertEqual(bytes(t.machine.mem_read(source,16)),data)
        with self.assertRaises(Blocked):self.call(address,args=(destination,0))

    def test_map_destructor_retires_cells_not_values(self):
        t=self.trace
        receiver=t.allocate(28)
        self.call(0x4f5cbd,receiver,(10,))
        key=t.cstring(b'test')
        cell=self.call(0x4f62a8,receiver,(key,))
        value=t.allocate(4)
        t.put(cell,value)
        t.deny_platform=0x4f5d00
        with self.assertRaises(Blocked):
            self.call(0x4f5d00,receiver)
        self.assertIn(cell,t.allocations)
        self.assertIn(receiver,t.maps)
        t.deny_platform=None
        self.call(0x4f5d00,receiver)
        self.assertNotIn(receiver,t.maps)
        self.assertNotIn(cell,t.allocations)
        self.assertIn(value,t.allocations)
        with self.assertRaises(Blocked):
            self.call(0x4f5d00,receiver)

    def test_posted_commands_are_queued_and_delivered_in_order(self):
        t=self.trace
        address=self.api('PostMessageA')
        t.deny_platform=address
        with self.assertRaises(Blocked):
            self.call(address,args=(1,0x111,0x807f,1))
        self.assertEqual(t.messages,[])
        t.deny_platform=None
        self.call(address,args=(1,0x111,0x807f,1))
        self.call(address,args=(1,0x111,0x8042,0))
        self.assertEqual(len(t.messages),2)
        app=t.allocate(4);vtable=t.allocate(24)
        t.put(app,vtable);t.put(vtable+0x14,0x426e30)
        calls=[]
        t.run=lambda target,receiver,args,**kw:calls.append((target,receiver,args))
        t.drain_messages(app)
        self.assertEqual(calls,[(0x426e30,app,(0x111,0x807f,1)),(0x426e30,app,(0x111,0x8042,0))])
        self.assertEqual(t.messages,[])

    def test_window_update_does_not_fabricate_paint(self):
        t=self.trace;address=self.api('UpdateWindow')
        with self.assertRaises(Blocked):
            self.call(address,args=(1,))
        t.presentations.append({'test':'already presented'})
        self.assertEqual(self.call(address,args=(1,)),1)
        self.assertEqual(t.physical_events[-1]['callbacks'],0)
        t.window_dirty=True
        before=len(t.physical_events)
        with self.assertRaises(Blocked):
            self.call(address,args=(1,))
        self.assertEqual(len(t.physical_events),before)

    def test_sort_callbacks_preserve_parent_and_sort_real_storage(self):
        t=self.trace
        data=t.allocate(256)
        t.machine.mem_write(data,bytes(reversed(range(256))))
        self.call(0x4f1e20,args=(data,256,1,0x4c70b0))
        while t.sort_frame:
            sp=t.machine.reg_read(UC_X86_REG_ESP)
            left,right=t.word(sp+4),t.word(sp+8)
            self.assertTrue(data<=left<right<data+256)
            a,b=t.machine.mem_read(left,1)[0],t.machine.mem_read(right,1)[0]
            t.machine.reg_write(UC_X86_REG_EAX,(a-b)&0xffffffff)
            t.machine.reg_write(UC_X86_REG_ESP,sp+4)
            t.hook(t.machine,0x7000f020,1,None)
        self.assertEqual(bytes(t.machine.mem_read(data,256)),bytes(range(256)))
        self.assertEqual(t.machine.reg_read(UC_X86_REG_ESP),STACK+4)
        self.assertEqual(t.machine.reg_read(UC_X86_REG_EIP),STOP)
        self.assertTrue(t.physical_events[-1]['completed'])
        with self.assertRaises(Blocked):
            self.call(0x4f1e20,args=(data,255,1,0x4c70b0))

    def test_rectangular_fill_bounds_and_withheld_service(self):
        t=self.trace
        surface=t.surface(4,3,64)
        pixels=t.com_objects[surface]['pixels']
        t.machine.mem_write(pixels,bytes(12))
        rectangle=t.allocate(16);fx=t.allocate(100)
        t.machine.mem_write(rectangle,struct.pack('<4i',1,1,3,3))
        t.machine.mem_write(fx,bytes(100));t.put(fx,100);t.put(fx+80,7)
        address=next(a for a,pair in t.com_methods.items() if pair==('IDirectDrawSurface','Blt'))
        def fill():
            for i,value in enumerate((STOP,surface,rectangle,0,0,0x1000400,fx)):
                t.put(STACK+4*i,value)
            t.machine.reg_write(UC_X86_REG_ESP,STACK)
            t.com_fixture(address)
        t.deny_platform=address
        with self.assertRaises(Blocked):fill()
        self.assertEqual(bytes(t.machine.mem_read(pixels,12)),bytes(12))
        t.deny_platform=None;fill()
        expected=bytes([0,0,0,0,0,7,7,0,0,7,7,0])
        self.assertEqual(bytes(t.machine.mem_read(pixels,12)),expected)
        t.machine.mem_write(rectangle,struct.pack('<4i',-1,1,3,3))
        with self.assertRaises(Blocked):fill()
        self.assertEqual(bytes(t.machine.mem_read(pixels,12)),expected)

    def test_calloc_zeroes_real_storage_and_rejects_overflow(self):
        t=self.trace
        pointer=self.call(0x4adf50,args=(7,13))
        self.assertEqual(t.allocations[pointer],91)
        self.assertEqual(bytes(t.machine.mem_read(pointer,91)),bytes(91))
        before=t.heap_next
        with self.assertRaises(Blocked):
            self.call(0x4adf50,args=(0xffffffff,4))
        self.assertEqual(t.heap_next,before)

    def test_unknown_platform_never_reports_success(self):
        with self.assertRaises(Blocked):
            self.call(0x4f0000)

    def test_memory_move_handles_overlap_and_zero_size(self):
        t=self.trace;p=t.allocate(8)
        t.machine.mem_write(p,b'abcdefgh')
        self.assertEqual(self.call(0x4a5290,args=(p+2,p,6)),p+2)
        self.assertEqual(bytes(t.machine.mem_read(p,8)),b'ababcdef')
        self.call(0x4a5290,args=(p,p+2,6))
        self.assertEqual(bytes(t.machine.mem_read(p,8)),b'abcdefef')
        self.assertEqual(self.call(0x4a5290,args=(0,0,0)),0)
        with self.assertRaises(Blocked):self.call(0x4a5290,args=(p,p,0xffffffff))

    def test_cstring_buffer_growth_and_release_are_bounded(self):
        t=self.trace;receiver=t.allocate(4);old=t.cstring(b'hello');t.put(receiver,old)
        self.assertEqual(self.call(0x4f6974,receiver,(0,)),old)
        new=self.call(0x4f6974,receiver,(20,))
        self.assertNotEqual(new,old)
        self.assertEqual(t.bytestring(new),b'hello')
        self.assertEqual(t.word(new-4),20)
        t.machine.mem_write(new,b'changed\0')
        self.call(0x4f69c3,receiver,(0xffffffff,))
        self.assertEqual(t.word(new-8),7)
        self.call(0x4f69eb,receiver,(3,))
        self.assertEqual(t.bytestring(new),b'cha')
        with self.assertRaises(Blocked):self.call(0x4f69c3,receiver,(21,))

    def test_xmidi_linear_clock_finite_loop_pause_and_unsupported_controller(self):
        def chunk(tag,data):return tag+len(data).to_bytes(4,'big')+data+b'\0'*(len(data)&1)
        def midi(events):return chunk(b'FORM',b'XMID'+chunk(b'INFO',b'\1\0')+chunk(b'EVNT',events))
        data=midi(b'\x90\x3c\x40\x05\x0a\xff\x2f\0')
        self.assertEqual(linear_xmidi_ticks(data),10)
        with self.assertRaises(Blocked):linear_xmidi_ticks(midi(b'\xb0\x74\x01\x0a\xff\x2f\0'))
        import hashlib
        t=self.trace;source=t.allocate(len(data));t.machine.mem_write(source,data);handle=t.allocate(16)
        sequence=dict(initialized=True,status=2,loops=1,sha256=hashlib.sha256(data).hexdigest(),duration_ticks=10)
        t.sequences[handle]=sequence
        t.physical_events.append(dict(service='_AIL_init_sequence@12',sequence=hex(handle),bytes=len(data)))
        self.call(self.api('_AIL_start_sequence@4'),args=(handle,))
        t.advance_time(1041)
        self.assertEqual(sequence['elapsed_units'],4920)
        self.call(self.api('_AIL_stop_sequence@4'),args=(handle,));t.advance_time(1200)
        self.assertEqual(sequence['elapsed_units'],4920)
        self.call(self.api('_AIL_resume_sequence@4'),args=(handle,));t.advance_time(1243)
        self.assertEqual(sequence['status'],2)
        self.call(self.api('_AIL_start_sequence@4'),args=(handle,))
        self.call(self.api('_AIL_set_sequence_loop_count@8'),args=(handle,0));t.advance_time(2000)
        self.assertEqual(sequence['status'],4)
        self.assertGreater(sequence['elapsed_units'],10000)

    def test_overlay_string_list_and_logical_font_validate_physical_arguments(self):
        t=self.trace;obj=t.allocate(28)
        self.call(0x4f5249,obj,(10,))
        self.assertEqual([t.word(obj+i*4) for i in range(7)],[0x510224,0,0,0,0,0,10])
        with self.assertRaises(Blocked):self.call(0x4f5249,obj,(0,))
        face=t.cstring(b'ARIAL');args=(12,8,0,0,100,0,0,0,1,0,0,0,0,face)
        font=self.call(self.api('CreateFontA'),args=args)
        self.assertIn(font,t.fonts)
        with self.assertRaises(Blocked):self.call(self.api('CreateFontA'),args=(13,*args[1:]))

    def test_rectangle_services_edges_empty_aliasing_and_signed_offsets(self):
        t=self.trace;a=t.allocate(16);b=t.allocate(16)
        def put(p,r):t.machine.mem_write(p,struct.pack('<4i',*r))
        def read(p):return struct.unpack('<4i',bytes(t.machine.mem_read(p,16)))
        put(a,(-10,-20,10,20));put(b,(0,0,15,30))
        for x,y,inside in [(-10,-20,1),(9,19,1),(10,0,0),(0,20,0),(-11,0,0)]:
            self.assertEqual(self.call(self.api('PtInRect'),args=(a,x&0xffffffff,y&0xffffffff)),inside)
        self.assertEqual(self.call(self.api('IntersectRect'),args=(a,a,b)),1)
        self.assertEqual(read(a),(0,0,10,20))
        self.call(self.api('OffsetRect'),args=(a,0xffffffff,2));self.assertEqual(read(a),(-1,2,9,22))
        self.call(self.api('InflateRect'),args=(a,1,2));self.assertEqual(read(a),(-2,0,10,24))
        self.call(self.api('UnionRect'),args=(a,a,b));self.assertEqual(read(a),(-2,0,15,30))
        put(b,(15,0,20,30))
        self.assertEqual(self.call(self.api('IntersectRect'),args=(a,a,b)),0)
        self.assertEqual(read(a),(0,0,0,0))
        self.assertEqual(self.call(self.api('IsRectEmpty'),args=(a,)),1)
        with self.assertRaises(Blocked):self.call(self.api('PtInRect'),args=(0,0,0))

    def test_ascii_character_classification_and_unsupported_locale(self):
        for value in range(128):
            self.assertEqual(bool(self.call(0x4b0d60,args=(value,))),value in (9,10,11,12,13,32))
            self.assertEqual(bool(self.call(0x4b0d30,args=(value,))),48<=value<=57)
            self.assertEqual(bool(self.call(0x4b0d90,args=(value,))),32<=value<=126)
        for address in (0x4b0d30,0x4b0d60,0x4b0d90):
            self.assertEqual(self.call(address,args=(0xffffffff,)),0)
            with self.assertRaises(Blocked):self.call(address,args=(128,))

    def test_spatial_grid_is_original_game_code_bounded_by_reviewed_bodies(self):
        t=self.trace
        for address in (0x4f4490,0x4f45f0,0x4f4630,0x4f4680,0x4f46b0,0x4f4860,0x4f48a0,0x4f49c0,0x4f4a8b):
            self.assertTrue(t.is_game(address))
        self.assertTrue(t.is_game(0x4f4a90))
        for address in (0x4f448f,0x4f4a8c,0x4f4aa0,0x4a49b0,0x4f1b30):
            self.assertFalse(t.is_game(address))
        from Tests.NativeMenuBase.trace import MenuTrace
        self.assertFalse(MenuTrace.is_game(0x4f4490))

    def test_large_grid_vector_runs_original_constructor_for_every_cell(self):
        t=self.trace;count=4608
        base=t.allocate(count*8+4)
        t.put(base,count)
        t.run(0x4a4590,0,(base+4,8,count,0x4f4a90,0x4c96b0),phase='grid-vector-control')
        self.assertEqual(bytes(t.machine.mem_read(base+4,count*8)),bytes(count*8))
        self.assertEqual(t.word(base),count)
        self.assertEqual(t.physical_events[-1]['completed'],count)
        self.assertEqual(t.functions[0x4f4a90],count)
        with self.assertRaises(Blocked):self.call(0x4a4590,args=(base+4,8,count+1,0x4f4a90,0x4c96b0))
        with self.assertRaises(Blocked):self.call(0x4a4590,args=(base+4,8,count,0x4f4aa0,0x4c96b0))

    def test_grid_power_preserves_lower_live_x87_values(self):
        t=self.trace
        t.x87_result(0,7.25)
        t.x87_result(0,2.)
        t.x87_result(0,6.)
        t.last_transfer=dict(site='0x4f4532')
        self.call(0x4f1b30)
        self.assertEqual(t.x87_value(0),64.)
        self.assertEqual(t.x87_value(1),7.25)
        t.x87_result(1)
        t.x87_result(0,2.)
        t.x87_result(0,6.5)
        with self.assertRaises(Blocked):self.call(0x4f1b30)
        self.assertEqual(t.x87_value(0),6.5)
        self.assertEqual(t.x87_value(1),2.)


if __name__=='__main__':
    unittest.main()
