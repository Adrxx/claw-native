"""Opt-in bounded x86 guest exception dispatch, separate from harness faults.

Only physical RaiseException/RtlUnwind are supplied here. Guest handlers, type
search, local unwind, filters and funclets remain executable original code.
The first supported nested exception is the MSVC rethrow protocol. Continuation,
collided unwind, nested raises during unwind and arbitrary nested throws fail
closed. This is machine transport, not native ABI support or Windows emulation.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import struct

from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP
from .kernel import (CONTEXT_FIELDS, CONTEXT_REGISTERS, ContextFault, EmulationFault, OwnedEntryStop,
                     STACK_BASE, STACK_SIZE, STACK_TOP, STOP)

END = 0xffffffff
NONCONTINUABLE = 1
UNWINDING = 2
CPP_EXCEPTION = 0xe06d7363
CPP_MAGIC = 0x19930520
STATUS_UNWIND = 0xc0000027


class GuestDispatchFault(ContextFault):
    """Malformed/unsupported physical transport, never a guest outcome."""


@dataclass(frozen=True)
class CPU:
    values: tuple
    fs_head: int


@dataclass(frozen=True)
class Raise:
    code: int
    flags: int
    information: tuple
    return_pc: int
    cpu: CPU


@dataclass(frozen=True)
class Unwind:
    target_frame: int
    target_pc: int
    exception_record: int
    return_value: int
    return_pc: int
    cpu: CPU


class PhysicalTransfer(Exception):
    """Internal stop from the physical hook; never escapes the public runner."""
    def __init__(self, event):
        self.event = event


@dataclass(frozen=True)
class ExceptionSnapshot:
    record: int
    context: int
    words: tuple
    cpu: CPU


@dataclass(frozen=True)
class GuestResult:
    kind: str  # returned or unhandled; faults raise GuestDispatchFault
    eax: int
    stack_pointer: int
    exception: ExceptionSnapshot | None
    transitions: tuple
    operations: int


@dataclass
class _Search:
    record: int
    context: int
    event: Raise
    frames: tuple


@dataclass(frozen=True)
class OwnedInvocation:
    owner_entry: int
    entry_pc: int
    establisher: int
    exception_record: int
    context_record: int
    serial: int
    cpu: CPU
    _authority: object


class _ReturnToInvocation(Exception):
    def __init__(self, stack_pointer, eax):
        self.stack_pointer, self.eax = stack_pointer, eax


class GuestExceptionRunner:
    """Single-use scoped driver; call() leaves guest terminal state inspectable.

    allowed_handlers is an exact set of executable guest handler identities.
    It grants no fabricated frame: registrations must be on the live bounded
    guest stack, aligned, acyclic and strictly increasing toward END.
    Caller installs ordinary physical imports through Machine.on_external.
    """
    def __init__(self, machine, *, allowed_handlers, max_depth=8,
                 max_operations=1000000, max_frames=64):
        self.machine = machine
        self.allowed_handlers = frozenset(allowed_handlers)
        if (not self.allowed_handlers or any(type(a) is not int or not machine.program.in_text(a) for a in self.allowed_handlers)
                or any(type(v) is not int for v in (max_depth, max_operations, max_frames))
                or not 1 <= max_depth <= 32 or not 1 <= max_frames <= 256 or max_operations < 1):
            raise GuestDispatchFault('invalid guest driver limits or handler identities')
        self.max_depth, self.max_operations, self.max_frames = max_depth, max_operations, max_frames
        self.operations = 0
        self.transitions = []
        self._searches = []
        self._services = {}  # platform-owned registration -> active generation
        self._invocations = []  # physical return SPs, not arbitrary continuation PCs
        self._unwinding = False
        self._active = False
        self._used = False
        self._generation = 0
        self._records = set()
        self._physical = {}
        self._handler_calls = []
        self._owned_route = None
        self._owned_handler = None
        self._owned_authority = None
        self._selected = None
        self._owned_serial = 0
        self._pending_owned = None
        self.on_physical = None
        self.on_owned_validate = None
        for slot, name in machine.program.imports.items():
            dll, _, function = name.partition('!')
            if dll.lower() == 'kernel32.dll' and function in ('RaiseException', 'RtlUnwind'):
                self._physical[machine.import_stub[slot]] = function

    def _stack(self, address, size):
        if (type(address) is not int or address & 3 or size < 0
                or not STACK_BASE <= address <= STACK_BASE + STACK_SIZE - size):
            raise GuestDispatchFault('guest exception frame outside bounded stack')

    @contextmanager
    def capture_scope(self):
        """Single-use physical capture only; the external graph owns its budget.

        This does not dispatch or imply an unhandled exception. Captured events
        still surface from Machine._execute after emulation has stopped.
        """
        if self._used or self.machine.guest_exceptions is not None:
            raise GuestDispatchFault('guest exception session already used or active')
        self._used = self._active = True
        self._generation += 1
        self.machine.guest_exceptions = self
        try:
            yield self
        finally:
            self.machine.guest_exceptions = None
            self._active = False
            self._services.clear()
            self._records.clear()

    @contextmanager
    def owned_scope(self, route, ranges, handler):
        """Permit one finite original-selected interior handoff in this graph."""
        if not self._active or self._owned_route is not None:
            raise GuestDispatchFault('owned route requires its live guest graph')
        self._owned_route, self._owned_handler = route, handler
        self._owned_authority = object()
        def selected(uc, pc, size, user):
            if self.machine._pending is not None:
                return
            try:
                self._select_owned()
            except BaseException as error:
                self.machine._pending = error
                uc.emu_stop()
        hook = self.machine.uc.hook_add(UC_HOOK_CODE, selected, begin=route.call_site, end=route.call_site)
        try:
            with self.machine.stop_owned_entries(ranges, self._capture_owned):
                yield
        finally:
            self.machine.uc.hook_del(hook)
            self._owned_route = self._owned_handler = self._owned_authority = None
            self._selected = self._pending_owned = None

    def _owned_frame(self):
        route = self._owned_route
        if self.on_owned_validate is not None:
            self.on_owned_validate()
        if (route is None or not self._searches or not self._handler_calls or self._unwinding or
                not self._invocations):
            raise GuestDispatchFault('owned funclet lacks a live handler search')
        frame, handler, search = self._handler_calls[-1]
        if (handler != route.handler or search is not self._searches[-1] or
                search.record not in self._records or
                not any(f == frame and h == handler for f, h, _ in self._chain()) or
                self.machine.words(frame + 8, 1)[0] != 1):
            raise GuestDispatchFault('owned funclet parent is not the selected live registration')
        return frame, search

    def _select_owned(self):
        route = self._owned_route
        # Other real CRT invocations can use the same CALL EAX helper. Only
        # the exact declared target grants this owned entry's capability.
        if self.machine.register(UC_X86_REG_EAX) != route.entry_pc:
            self._selected = None
            return
        frame, search = self._owned_frame()
        cpu = self._cpu()
        values = dict(zip(CONTEXT_FIELDS[:-1], cpu.values))
        if values['ebp'] != frame + 12 or values['eip'] != route.call_site:
            raise GuestDispatchFault('owned funclet selected with a changed parent CPU')
        self._selected = (frame, search, cpu, self._owned_authority)

    def _capture_owned(self, address):
        route = self._owned_route
        if address != route.entry_pc or self._selected is None or self._pending_owned is not None:
            raise GuestDispatchFault('original execution entered an unleased owned instruction')
        frame, search = self._owned_frame()
        old_frame, old_search, old_cpu, authority = self._selected
        self._selected = None
        cpu = self._cpu()
        expected = list(old_cpu.values)
        expected[7] -= 4
        expected[8] = route.entry_pc
        if (old_frame != frame or old_search is not search or authority is not self._owned_authority or
                tuple(expected) != cpu.values or old_cpu.fs_head != cpu.fs_head or
                self.machine.words(cpu.values[7], 1)[0] != route.return_pc):
            raise GuestDispatchFault('owned entry did not follow the observed original CALL')
        self._owned_serial += 1
        invocation = OwnedInvocation(route.owner_entry, address, frame, search.record, search.context,
                                     self._owned_serial, cpu, authority)
        self._pending_owned = invocation
        return invocation

    def resume_raise(self, event):
        """Resume a captured root raise inside this still-active driver scope."""
        if (not self._active or self.machine.guest_exceptions is not self or self._searches or
                not isinstance(event, Raise) or not self.transitions or self.transitions[-1] is not event):
            raise GuestDispatchFault('root raise has no live captured driver authority')
        try:
            exception = self._dispatch(event)
        except _ReturnToInvocation:
            raise GuestDispatchFault('unowned nonlocal return escaped guest graph') from None
        return GuestResult('unhandled', 0, self.machine.register(UC_X86_REG_ESP), exception,
                           tuple(self.transitions), self.operations)

    def _put(self, address, *words):
        self._stack(address, len(words) * 4)
        self.machine.write(address, struct.pack('<' + 'I' * len(words), *words))

    def _cpu(self):
        return CPU(tuple(self.machine.register(r) for r in CONTEXT_REGISTERS), self.machine.fs_head)

    def capture(self, address):
        """Called only by Machine's opt-in physical hook; ordinary imports pass."""
        if not self._active or self.machine.guest_exceptions is not self:
            raise GuestDispatchFault('expired guest exception session')
        name = self._physical.get(address)
        if name is None:
            return
        sp = self.machine.register(UC_X86_REG_ESP)
        self._stack(sp, 20)
        pc, *args = self.machine.words(sp, 5)
        if not self.machine.program.in_text(pc):
            raise GuestDispatchFault('physical exception return PC is not original code')
        if name == 'RaiseException':
            code, flags, count, info = args
            if flags != NONCONTINUABLE or count > 15:
                raise GuestDispatchFault('unsupported exception flags or parameter count')
            if count:
                self._stack(info, count * 4)
                if info < sp:
                    raise GuestDispatchFault('exception information is below the live stack')
            event = Raise(code, flags, self.machine.words(info, count), pc, self._cpu())
        else:
            event = Unwind(*args, pc, self._cpu())
        self.transitions.append(event)
        if self.on_physical is not None:
            self.on_physical(event)
        raise PhysicalTransfer(event)

    def _chain(self, head=None):
        at = self.machine.fs_head if head is None else head
        frames = []
        while at != END:
            self._stack(at, 12)
            if at < self.machine.register(UC_X86_REG_ESP):
                raise GuestDispatchFault('registration is below the live stack')
            if len(frames) >= self.max_frames:
                raise GuestDispatchFault('guest registration chain exceeds bound')
            link, handler = self.machine.words(at, 2)
            if link != END and (link <= at or link & 3):
                raise GuestDispatchFault('cyclic or nonmonotonic guest registration chain')
            if at in self._services:
                if handler != self._service_handler or self._services[at] != self._generation:
                    raise GuestDispatchFault('changed platform invocation registration')
            elif handler not in self.allowed_handlers:
                raise GuestDispatchFault('unregistered guest exception handler')
            frames.append((at, handler, link))
            at = link
        return tuple(frames)

    @property
    def _service_handler(self):
        # This address is a platform-owned identity, never executed as a guest
        # callback. Its nested-search behavior is implemented by the driver.
        return 0xfffffff0

    def _storage(self, event):
        # Put records below the suspended physical frame and execute handlers
        # below them. Never overlap the live source/previous dispatcher stack.
        sp = self.machine.register(UC_X86_REG_ESP)
        record = (sp - 0x400) & ~15
        context = record + 0x60
        self._stack(record - 0x100, 0x500)
        self.machine.write(record, bytes(0x60 + 716))
        info = event.information
        self._put(record, event.code, event.flags, 0, event.return_pc, len(info), *info)
        self._put(context, 0x10003)  # x86 CONTEXT_CONTROL | CONTEXT_INTEGER
        values = dict(zip(CONTEXT_FIELDS[:-1], event.cpu.values))
        offsets = {'edi': 0x9c, 'esi': 0xa0, 'ebx': 0xa4, 'edx': 0xa8, 'ecx': 0xac,
                   'eax': 0xb0, 'ebp': 0xb4, 'eip': 0xb8, 'eflags': 0xc0, 'esp': 0xc4}
        for name, offset in offsets.items():
            self._put(context + offset, values[name])
        self._records.add(record)
        return record, context

    def _execute(self, address):
        try:
            result = self.machine._execute(address, STOP, 10)
        except OwnedEntryStop as stop:
            invocation = stop.invocation
            if (self.machine._execution_depth or invocation is not self._pending_owned or
                    invocation._authority is not self._owned_authority or self._owned_handler is None):
                raise GuestDispatchFault('owned entry stop has no live driver capability')
            self._pending_owned = None
            event = self._owned_handler(invocation)
            if (not isinstance(event, Raise) or not self.transitions or self.transitions[-1] is not event):
                raise GuestDispatchFault('nonreturning owned funclet failed to transfer')
            raise PhysicalTransfer(event)
        if not result.completed:
            raise GuestDispatchFault('guest handler failed to reach scoped transport boundary')
        raise _ReturnToInvocation(result.stack_pointer, result.eax)

    def _drive(self, address):
        while True:
            try:
                self._execute(address)
            except PhysicalTransfer as stop:
                if isinstance(stop.event, Raise):
                    self._dispatch(stop.event)
                    raise GuestDispatchFault('nested unhandled exception cannot resume its raise')
                self._unwind(stop.event)
                address = self.machine.register(UC_X86_REG_EIP)

    def _invoke(self, handler, frame, search, stack_top):
        # Real original handler, ordinary cdecl4 with a physical invocation
        # frame. Matching return-SP identifies nonlocal returns to ancestors.
        self._stack(stack_top - 0x60, 0x60)
        service = stack_top - 0x20
        entry_sp = stack_top - 0x50
        self._put(service, self.machine.fs_head, self._service_handler, 0)
        self._services[service] = self._generation
        self.machine.fs_head = service
        self._put(entry_sp, STOP, search.record, frame, search.context, 0)
        expected_sp = entry_sp + 4
        self._invocations.append(expected_sp)
        self._handler_calls.append((frame, handler, search))
        self.machine.uc.reg_write(UC_X86_REG_ESP, entry_sp)
        try:
            try:
                self._drive(handler)
            except _ReturnToInvocation as returned:
                if returned.stack_pointer != expected_sp:
                    if returned.stack_pointer not in self._invocations[:-1]:
                        raise GuestDispatchFault('handler returned outside live invocation chain')
                    raise
                if self.machine.fs_head != service:
                    raise GuestDispatchFault('handler did not restore its platform invocation head')
                self._chain()
                self.machine.fs_head = self.machine.words(service, 1)[0]
                return returned.eax
        finally:
            if self.machine.fs_head == service:
                self.machine.fs_head = self.machine.words(service, 1)[0]
            self._invocations.pop()
            self._handler_calls.pop()
            self._services.pop(service, None)

    def _dispatch(self, event):
        if self._unwinding:
            raise GuestDispatchFault('nested exception during unwind is unsupported')
        if len(self._searches) >= self.max_depth:
            raise GuestDispatchFault('guest exception nesting exceeds bound')
        if self._searches and not (event.code == CPP_EXCEPTION
                                  and event.information == (CPP_MAGIC, 0, 0)):
            raise GuestDispatchFault('only original C++ rethrow nesting is supported')
        frames = self._chain(event.cpu.fs_head)
        record, context = self._storage(event)
        search = _Search(record, context, event, frames)
        self._searches.append(search)
        try:
            for frame, handler, _ in frames:
                if frame in self._services:
                    # The driver owns these physical invocation records; never
                    # invent a source callback or execute a RET stand-in.
                    continue
                if not any(f[0] == frame and f[1] == handler for f in self._chain()):
                    raise GuestDispatchFault('search registration is no longer live')
                disposition = self._invoke(handler, frame, search, record - 0x40)
                if disposition != 1:
                    raise GuestDispatchFault('unsupported continuation, nested or collided disposition')
            return ExceptionSnapshot(record, context, self.machine.words(record, 20), event.cpu)
        finally:
            self._searches.pop()
            self._records.discard(record)

    def _unwind(self, event):
        if self._unwinding or not self._searches:
            raise GuestDispatchFault('unwind lacks live search or is collided')
        if event.target_pc != event.return_pc or not self.machine.program.in_text(event.target_pc):
            raise GuestDispatchFault('unsupported unwind target continuation')
        frames = self._chain()
        positions = [i for i, f in enumerate(frames) if f[0] == event.target_frame]
        if len(positions) != 1 or event.target_frame in self._services:
            raise GuestDispatchFault('unwind target is not a live source registration')
        suspended = self.machine.uc.context_save()
        search = self._searches[-1]
        if event.exception_record:
            if (event.exception_record not in self._records
                    or not any(s.record == event.exception_record for s in self._searches)):
                raise GuestDispatchFault('unwind record is outside live dispatch lifetime')
            record = event.exception_record
        else:
            # RtlUnwind(NULL record) supplies a platform unwind record. Source
            # handlers still execute and decide local cleanup from flags/state.
            record = (self.machine.register(UC_X86_REG_ESP) - 0x100) & ~15
            self._stack(record, 80)
            self.machine.write(record, bytes(80))
            self._put(record, STATUS_UNWIND, 0, 0, event.return_pc, 0)
        flags = self.machine.words(record + 4, 1)[0]
        self._put(record + 4, flags | UNWINDING)
        unwind_search = _Search(record, search.context, search.event, frames)
        self._unwinding = True
        try:
            for frame, handler, _ in frames[:positions[0]]:
                if frame in self._services:
                    continue
                if not any(f[0] == frame and f[1] == handler for f in self._chain()):
                    raise GuestDispatchFault('unwind registration is no longer live')
                disposition = self._invoke(handler, frame, unwind_search,
                                           min(record, self.machine.register(UC_X86_REG_ESP)) - 0x80)
                if disposition != 1:
                    raise GuestDispatchFault('unsupported unwind handler disposition')
        finally:
            self._unwinding = False
        target_handler = frames[positions[0]][1]
        if not any(f[0] == event.target_frame and f[1] == target_handler for f in self._chain()):
            raise GuestDispatchFault('unwind target is no longer live')
        self.machine.uc.context_restore(suspended)
        self.machine.fs_head = event.target_frame
        # This is the physical RtlUnwind target operation, not a return from
        # RaiseException. The admitted scope requires targetPC == saved return.
        self.machine.return_from_external(event.return_value, 16)

    def call(self, function, ecx=0, edx=0, arguments=(), *, stack_pointer=STACK_TOP,
             reset_thread=True):
        if self._used or self.machine.guest_exceptions is not None:
            raise GuestDispatchFault('guest exception session already used or active')
        if not self.machine.program.in_text(function):
            raise GuestDispatchFault('guest root is not original executable code')
        self._used = self._active = True
        self._generation += 1
        self.machine.guest_exceptions = self
        def instruction(uc, address, size, user):
            self.operations += 1
            if self.operations > self.max_operations:
                self.machine._pending = GuestDispatchFault('guest graph instruction budget exhausted')
                uc.emu_stop()
        hook = self.machine.uc.hook_add(UC_HOOK_CODE, instruction)
        try:
            try:
                result = self.machine.call(function, ecx, edx, arguments, stack_pointer=stack_pointer,
                                           reset_thread=reset_thread)
                if not result.completed:
                    raise GuestDispatchFault('guest root did not complete')
                return GuestResult('returned', result.eax, result.stack_pointer, None,
                                   tuple(self.transitions), self.operations)
            except PhysicalTransfer as stop:
                if not isinstance(stop.event, Raise):
                    raise GuestDispatchFault('root unwind without a dispatch search')
                exception = self._dispatch(stop.event)
                return GuestResult('unhandled', 0, self.machine.register(UC_X86_REG_ESP), exception,
                                   tuple(self.transitions), self.operations)
            except _ReturnToInvocation:
                raise GuestDispatchFault('unowned nonlocal return escaped guest graph') from None
        finally:
            self.machine.uc.hook_del(hook)
            self.machine.guest_exceptions = None
            self._active = False
            self._services.clear()
            self._records.clear()
