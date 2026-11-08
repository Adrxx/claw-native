"""Independent synthetic x86 controls. No original code or derived fixtures."""
import struct
import unittest

from Tests.clawparity.program import Program, Section
from Tests.clawparity.kernel import Machine, STACK_BASE, STACK_SIZE, STACK_TOP, STOP
from Tests.clawparity.guest_exception import (GuestExceptionRunner, GuestDispatchFault,
                                             Raise, Unwind, CPP_EXCEPTION, CPP_MAGIC)

BASE = 0x401000
RAISE_SLOT, UNWIND_SLOT, MARK = 0x402000, 0x402004, 0x402080
INNER, OUTER = STACK_TOP + 0x100, STACK_TOP + 0x120
H1, H2 = BASE + 0x100, BASE + 0x200
INFO = STACK_TOP + 0x300

def u32(v):
    return struct.pack('<I', v & 0xffffffff)

def push(v):
    return b'\x68' + u32(v)

def emit_raise(code=0x1234, flags=1, count=0, info=0):
    return push(info) + push(count) + push(flags) + push(code) + b'\xff\x15' + u32(RAISE_SLOT)

def disposition(value):
    return b'\xb8' + u32(value) + b'\xc3'

def program(root=None, h1=None, h2=None):
    text = bytearray(b'\xcc' * 0x1000)
    root = root if root is not None else emit_raise() + b'\xc7\x05' + u32(MARK) + u32(0xbad) + b'\xc3'
    for offset, code in [(0, root), (0x100, h1 or disposition(1)), (0x200, h2 or disposition(1)),
                         (0x800, disposition(77))]:
        text[offset:offset+len(code)] = code
    return Program('synthetic-guest-exceptions', '', 0x400000, 0x3000,
                   [Section('.text', BASE, len(text), bytes(text)),
                    Section('.data', 0x402000, 0x1000, bytes(0x1000))],
                   (BASE, BASE + len(text)),
                   {RAISE_SLOT:'KERNEL32.dll!RaiseException', UNWIND_SLOT:'KERNEL32.dll!RtlUnwind'})

def machine(**kw):
    m = Machine(program(**kw), 0x3000000, 0x10000)
    m.on_external = lambda m, a: (_ for _ in ()).throw(AssertionError('unexpected ordinary service'))
    return m

def words(m, a, *values):
    m.write(a, b''.join(u32(v) for v in values))

def chain(m, two=False):
    words(m, INNER, OUTER if two else 0xffffffff, H1, 0)
    if two:
        words(m, OUTER, 0xffffffff, H2, 0)
    m.fs_head = INNER

def run(m, **kw):
    return GuestExceptionRunner(m, allowed_handlers={H1,H2}, **kw).call(BASE, reset_thread=False)

def unwind_handler(nullable=False, target=OUTER, record_override=None, pc_override=None):
    # Independently authored handler: preserve platform registration identity,
    # request physical unwind, re-link its active invocation, then ContinueSearch.
    start = b'\x56\x64\x8b\x35' + u32(0)  # save ESI, ESI=FS head
    record = push(0) if nullable else b'\xff\x74\x24\x0c'
    if record_override is not None:
        record = push(record_override)
    prefix = start + push(0) + record
    pc = H2 + len(prefix) + 5 + 5 + 6
    call = push(pc if pc_override is None else pc_override) + push(target) + b'\xff\x15' + u32(UNWIND_SLOT)
    # EAX=FS head; [ESI]=EAX; FS head=ESI; restore ESI; return1.
    suffix = b'\x64\xa1' + u32(0) + b'\x89\x06\x64\x89\x35' + u32(0) + b'\x5e' + disposition(1)
    return prefix + call + suffix

class GuestExceptionTests(unittest.TestCase):
    def test_no_opt_in_keeps_ordinary_import_semantics(self):
        m=machine(); calls=[]
        def physical(m,a):
            calls.append(a); m.return_from_external(0,16)
        m.on_external=physical
        result=m.call(BASE)
        self.assertTrue(result.completed)
        self.assertEqual(m.words(MARK,1),(0xbad,))
        self.assertEqual(len(calls),1)

    def test_explicit_unhandled_never_returns_from_raise(self):
        m=machine(); chain(m)
        r=run(m)
        self.assertEqual(r.kind,'unhandled')
        self.assertEqual(r.exception.words[:5],(0x1234,1,0,BASE+26,0))
        self.assertEqual(m.words(MARK,1),(0,))
        self.assertEqual([type(e) for e in r.transitions],[Raise])
        self.assertEqual(m.fs_head,INNER)
        self.assertIsNone(m.guest_exceptions)

    def test_returning_root(self):
        m=machine(root=disposition(99)); r=run(m)
        self.assertEqual((r.kind,r.eax,r.exception),('returned',99,None))

    def test_empty_chain_is_unhandled(self):
        self.assertEqual(run(machine()).kind,'unhandled')

    def test_valid_context_copies_cpu(self):
        m=machine();chain(m);r=run(m)
        # Physical snapshot EIP and ESP, not a fabricated normal return frame.
        self.assertEqual(m.words(r.exception.context+0xb8,1)[0],r.transitions[0].cpu.values[8])
        self.assertEqual(m.words(r.exception.context+0xc4,1)[0],r.transitions[0].cpu.values[7])

    def test_chain_rejects_cycles_backward_and_unaligned(self):
        for link in (INNER,INNER-4,INNER+1):
            with self.subTest(link=link):
                m=machine();chain(m);words(m,INNER,link)
                with self.assertRaisesRegex(GuestDispatchFault,'cyclic|nonmonotonic'):run(m)

    def test_zero_and_unregistered_handlers(self):
        for h in (0,BASE+0x700):
            m=machine();chain(m);words(m,INNER+4,h)
            with self.assertRaisesRegex(GuestDispatchFault,'unregistered'):run(m)

    def test_stack_bounds_for_chain_and_information(self):
        for head in (STACK_BASE-4,STACK_BASE+STACK_SIZE-4):
            m=machine();m.fs_head=head
            with self.assertRaisesRegex(GuestDispatchFault,'bounded stack'):run(m)
        m=machine(root=emit_raise(count=1,info=0x3000000));chain(m)
        with self.assertRaisesRegex(GuestDispatchFault,'bounded stack'):run(m)

    def test_flags_and_information_bound(self):
        for kw in ({'flags':0},{'flags':3},{'count':16,'info':INFO}):
            m=machine(root=emit_raise(**kw));chain(m)
            with self.assertRaisesRegex(GuestDispatchFault,'flags|parameter'):run(m)

    def test_frame_and_storage_bounds(self):
        m=machine();chain(m,True)
        with self.assertRaisesRegex(GuestDispatchFault,'chain exceeds'):run(m,max_frames=1)
        m=machine();chain(m)
        runner=GuestExceptionRunner(m,allowed_handlers={H1})
        with self.assertRaisesRegex(GuestDispatchFault,'bounded stack'):
            runner.call(BASE,stack_pointer=STACK_BASE+128,reset_thread=False)

    def test_unsupported_search_dispositions(self):
        for d in (0,2,3,0xffffffff):
            m=machine(h1=disposition(d));chain(m)
            with self.assertRaisesRegex(GuestDispatchFault,'disposition'):run(m)
            self.assertEqual(m.words(MARK,1),(0,))

    def test_arbitrary_nested_throw_rejected(self):
        m=machine(h1=emit_raise(code=0x9999));chain(m)
        with self.assertRaisesRegex(GuestDispatchFault,'rethrow nesting'):run(m)

    def test_rethrow_nesting_limit(self):
        m=machine(h1=emit_raise(CPP_EXCEPTION,count=3,info=INFO));chain(m)
        words(m,INFO,CPP_MAGIC,0,0)
        with self.assertRaisesRegex(GuestDispatchFault,'nesting exceeds'):run(m,max_depth=2)

    def test_nullable_and_nonnullable_unwind(self):
        for nullable in (False,True):
            with self.subTest(nullable=nullable):
                m=machine(h2=unwind_handler(nullable));chain(m,True)
                r=run(m)
                self.assertEqual(r.kind,'unhandled')
                self.assertEqual([type(e) for e in r.transitions],[Raise,Unwind])
                self.assertEqual(bool(r.transitions[1].exception_record),not nullable)
                self.assertEqual(m.fs_head,OUTER)
                self.assertEqual(m.words(MARK,1),(0,))

    def test_bad_unwind_record_target_and_pc(self):
        variants=[{'record_override':INFO},{'target':STACK_TOP+0x200},{'pc_override':BASE+0x700}]
        for kw in variants:
            m=machine(h2=unwind_handler(**kw));chain(m,True)
            with self.assertRaisesRegex(GuestDispatchFault,'lifetime|target|continuation'):run(m)

    def test_unwind_outside_search_rejected(self):
        m=machine(root=push(0)*4+b'\xff\x15'+u32(UNWIND_SLOT))
        with self.assertRaisesRegex(GuestDispatchFault,'root unwind'):run(m)

    def test_collided_unwind_disposition(self):
        # Return2 only in unwind mode; search still returns ContinueSearch1.
        inner=b'\x8b\x4c\x24\x04\xf7\x41\x04'+u32(2)+b'\x74\x06'+disposition(2)+disposition(1)
        m=machine(h1=inner,h2=unwind_handler());chain(m,True)
        with self.assertRaisesRegex(GuestDispatchFault,'unwind handler disposition'):run(m)

    def test_nested_raise_during_unwind(self):
        raised=emit_raise()
        inner=b'\x8b\x4c\x24\x04\xf7\x41\x04'+u32(2)+b'\x74'+bytes([len(raised)])+raised+disposition(1)
        m=machine(h1=inner,h2=unwind_handler());chain(m,True)
        with self.assertRaisesRegex(GuestDispatchFault,'during unwind'):run(m)

    def test_shared_instruction_budget_includes_unwind_handlers(self):
        m=machine(h2=unwind_handler());chain(m,True);count=run(m).operations
        m=machine(h2=unwind_handler());chain(m,True)
        runner=GuestExceptionRunner(m,allowed_handlers={H1,H2},max_operations=count-1)
        with self.assertRaisesRegex(GuestDispatchFault,'budget exhausted'):runner.call(BASE,reset_thread=False)
        self.assertEqual([type(e) for e in runner.transitions],[Raise,Unwind])

    def test_failure_cleans_session_and_hook_ordinary_call_still_works(self):
        m=machine(h1=disposition(3));chain(m)
        runner=GuestExceptionRunner(m,allowed_handlers={H1})
        with self.assertRaises(GuestDispatchFault):runner.call(BASE,reset_thread=False)
        count=runner.operations
        self.assertIsNone(m.guest_exceptions)
        self.assertFalse(runner._services)
        self.assertFalse(runner._records)
        self.assertEqual(m.call(BASE+0x800).eax,77)
        self.assertEqual(runner.operations,count)
        with self.assertRaisesRegex(GuestDispatchFault,'used'):runner.call(BASE)
        with self.assertRaisesRegex(GuestDispatchFault,'expired'):runner.capture(m.import_stub[RAISE_SLOT])

    def test_removed_captured_registration_is_not_called(self):
        remove=b'\xc7\x05'+u32(INNER)+u32(0xffffffff)+disposition(1)
        mark=b'\xc7\x05'+u32(MARK)+u32(0xdeadbeef)+disposition(1)
        m=machine(h1=remove,h2=mark);chain(m,True)
        with self.assertRaisesRegex(GuestDispatchFault,'no longer live'):run(m)
        self.assertEqual(m.words(MARK,1),(0,))

    def test_unwind_cannot_restore_target_removed_by_cleanup(self):
        remove=b'\xc7\x05'+u32(INNER)+u32(0xffffffff)
        inner=b'\x8b\x4c\x24\x04\xf7\x41\x04'+u32(2)+b'\x74'+bytes([len(remove)])+remove+disposition(1)
        m=machine(h1=inner,h2=unwind_handler());chain(m,True)
        with self.assertRaisesRegex(GuestDispatchFault,'target is no longer live'):run(m)
        self.assertNotEqual(m.fs_head,OUTER)

    def test_registration_below_live_stack_is_rejected(self):
        m=machine();words(m,STACK_TOP-0x300,0xffffffff,H1,0);m.fs_head=STACK_TOP-0x300
        with self.assertRaisesRegex(GuestDispatchFault,'below the live stack'):run(m)

    def test_completed_record_cannot_be_reused_for_unwind(self):
        m=machine();chain(m);old=run(m).exception.record
        code=unwind_handler(record_override=old)
        m.write(H2,code);m.uc.ctl_remove_cache(*m.program.text);chain(m,True)
        runner=GuestExceptionRunner(m,allowed_handlers={H1,H2})
        with self.assertRaisesRegex(GuestDispatchFault,'lifetime'):
            runner.call(BASE,stack_pointer=STACK_TOP-0x1000,reset_thread=False)

    def test_stale_record_set_alone_does_not_grant_active_lifetime(self):
        m=machine();chain(m);old=run(m).exception.record
        m.write(H2,unwind_handler(record_override=old));m.uc.ctl_remove_cache(*m.program.text);chain(m,True)
        runner=GuestExceptionRunner(m,allowed_handlers={H1,H2})
        # Simulate retained bookkeeping: only a live search grants authority.
        m.observe(H2,lambda m,a:runner._records.add(old))
        with self.assertRaisesRegex(GuestDispatchFault,'lifetime'):
            runner.call(BASE,stack_pointer=STACK_TOP-0x1000,reset_thread=False)
        self.assertFalse(runner._records)

    def test_completed_nested_search_records_are_retired(self):
        nested=emit_raise(CPP_EXCEPTION,count=3,info=INFO)
        # First handler invocation raises; nested search returns ContinueSearch.
        handler=b'\x83\x3d'+u32(MARK+4)+b'\x00\x75'+bytes([10+len(nested)])
        handler+=b'\xc7\x05'+u32(MARK+4)+u32(1)+nested+disposition(1)
        m=machine(h1=handler);chain(m);words(m,INFO,CPP_MAGIC,0,0)
        runner=GuestExceptionRunner(m,allowed_handlers={H1})
        with self.assertRaisesRegex(GuestDispatchFault,'nested unhandled'):
            runner.call(BASE,reset_thread=False)
        self.assertEqual(len(runner.transitions),2)
        self.assertFalse(runner._records)
        self.assertFalse(runner._searches)
        with self.assertRaisesRegex(GuestDispatchFault,'used'):runner.call(BASE)

    def test_platform_identity_does_not_alias_any_import(self):
        m=machine();r=GuestExceptionRunner(m,allowed_handlers={H1})
        self.assertNotIn(r._service_handler,m.import_stub.values())
        self.assertFalse(m.program.in_text(r._service_handler))

    def test_constructor_rejects_noninteger_limits(self):
        for name in ('max_depth','max_frames','max_operations'):
            for value in (True,False,1.5,'4'):
                with self.subTest(name=name,value=value):
                    with self.assertRaises(GuestDispatchFault):
                        GuestExceptionRunner(machine(),allowed_handlers={H1},**{name:value})

if __name__=='__main__':unittest.main()
