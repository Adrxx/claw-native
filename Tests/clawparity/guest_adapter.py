"""Opt-in native -> original -> physical raise transport, without dispatch.

The frozen result owns memory and CPU independently of every borrowed C call.
An observed transfer is deliberately not an unhandled or caught exception.
"""
import ctypes as C
import copy
import struct
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field

from unicorn import UC_HOOK_CODE

from . import build
from .env import (HEAP_BASE, NativeHost, NativeSourceContext, SourceBudgetFault, Side, Halt,
                  HarnessError)
from .guest_exception import CPU, Raise, Unwind, PhysicalTransfer, GuestExceptionRunner, GuestResult
from .guest_contract import GuestContract
from .kernel import CONTEXT_ALL, CONTEXT_FIELDS, CONTEXT_REGISTERS, STACK_BASE, STACK_SIZE, STACK_TOP, STUB_BASE, ContextFault

U32 = C.c_uint32


class GuestConfig(C.Structure):
    _fields_ = [(n, U32) for n in ('size', 'version', 'rootFunction', 'textBegin', 'textEnd', 'raiseSlot', 'raiseStub')]


class GuestPhysicalEvent(C.Structure):
    _fields_ = ([(n, U32) for n in ('size', 'version', 'kind', 'slot', 'stub', 'code', 'flags', 'count', 'returnPC')]
                + [('cpu', NativeSourceContext), ('information', U32 * 15)])


class GuestOutcome(C.Structure):
    _fields_ = ([(n, U32) for n in ('size', 'version', 'kind', 'reserved')]
                + [('generation', C.c_uint64), ('payload', C.c_uint64), ('event', GuestPhysicalEvent)])


class GuestEHContract(C.Structure):
    _fields_ = [(n, U32) for n in ('size', 'version', 'ownerEntry', 'entryPC', 'handler', 'funcInfo',
                                  'handlerTable', 'callSite', 'returnPC')]


class GuestEHInvocation(C.Structure):
    _fields_ = ([(n, U32) for n in ('size', 'version', 'ownerEntry', 'entryPC', 'establisher',
                                   'exceptionRecord', 'contextRecord')]
                + [('serial', C.c_uint64), ('cpu', NativeSourceContext)])


@dataclass(frozen=True)
class GuestFuncletRoute:
    owner_entry: int
    entry_pc: int
    handler: int
    func_info: int
    handler_table: int
    call_site: int
    return_pc: int
    native_entry: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class GuestGraph:
    allowed_handlers: frozenset
    owned_ranges: tuple
    funclet: GuestFuncletRoute
    contract: GuestContract | None = None


@dataclass(frozen=True)
class GuestTerminalState:
    allocator_cursor: int
    names: tuple
    spans: tuple
    freed: tuple


@dataclass(frozen=True)
class GuestGraphOutcome:
    kind: str
    side: object
    result: object
    transfers: tuple
    invocations: tuple
    terminal_cpu: CPU | None
    terminal_stack: bytes | None
    terminal_provenance: str
    terminal_state: GuestTerminalState | None


@dataclass(frozen=True)
class FrozenGuestState:
    event: Raise | Unwind
    cpu: CPU
    stack: bytes
    heap: bytes
    image_data: bytes
    remaining_operations: int
    spans: tuple
    freed: tuple
    allocator_cursor: int
    names: tuple
    events: tuple
    generation: int
    _machine_context: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class GuestNativeOutcome:
    kind: str
    side: object
    snapshot: FrozenGuestState | None


def support_library(flavor='O2'):
    library = C.CDLL(str(build.guest_support(flavor)))
    ptr, host = C.c_void_p, C.POINTER(NativeHost)
    library.claw_guest_create.argtypes = [host, C.POINTER(GuestConfig)]
    library.claw_guest_create.restype = ptr
    library.claw_guest_generation.argtypes = [ptr, host]
    library.claw_guest_generation.restype = C.c_uint64
    library.claw_guest_destroy.argtypes = [ptr, host, C.c_uint64]
    library.claw_guest_destroy.restype = U32
    library.claw_guest_status.argtypes = [host]
    library.claw_guest_status.restype = U32
    library.claw_guest_capture_original.argtypes = [ptr, host, C.c_uint64, ptr, C.POINTER(GuestPhysicalEvent), C.c_uint64]
    library.claw_guest_capture_original.restype = U32
    library.claw_guest_run.argtypes = [ptr, host, C.c_uint64, ptr, U32, U32, C.POINTER(U32), U32,
                                      C.POINTER(U32), C.POINTER(GuestOutcome)]
    library.claw_guest_run.restype = U32
    library.claw_guest_bind_eh.argtypes = [ptr, host, C.c_uint64, C.POINTER(GuestEHContract), ptr]
    library.claw_guest_bind_eh.restype = U32
    library.claw_guest_run_eh.argtypes = [ptr, host, C.c_uint64, C.POINTER(GuestEHInvocation), C.POINTER(GuestOutcome)]
    library.claw_guest_run_eh.restype = U32
    library.claw_guest_prepare_eh.argtypes = [ptr, host, C.c_uint64, C.POINTER(GuestEHInvocation)]
    library.claw_guest_prepare_eh.restype = U32
    library.claw_guest_sizeof.argtypes, library.claw_guest_sizeof.restype = [U32], C.c_size_t
    library.claw_guest_offset.argtypes, library.claw_guest_offset.restype = [U32, U32], C.c_size_t
    for kind, structure in enumerate((GuestConfig, GuestPhysicalEvent, GuestOutcome, GuestEHContract, GuestEHInvocation)):
        expected = (C.sizeof(structure), *(getattr(structure, n).offset for n, _ in structure._fields_))
        actual = (library.claw_guest_sizeof(kind), *(library.claw_guest_offset(kind, i) for i in range(len(structure._fields_))))
        if actual != expected:
            raise HarnessError(f'guest ABI layout mismatch: {actual} != {expected}')
    return library


class _Adapter:
    def __init__(self, env, function, flavor):
        self.env = env
        self.library = support_library(flavor)
        slots = [slot for slot, name in env.program.imports.items()
                 if name.lower() == 'kernel32.dll!raiseexception']
        if len(slots) != 1:
            raise ContextFault('guest transport requires one exact physical RaiseException import')
        self.slot = slots[0]
        self.stub = env.machine.import_stub[self.slot]
        self.config = GuestConfig(C.sizeof(GuestConfig), 1, function, *env.program.text, self.slot, self.stub)
        self.session = self.library.claw_guest_create(C.byref(env._host), C.byref(self.config))
        if not self.session:
            raise ContextFault('could not create guest transport session')
        self.generation = self.library.claw_guest_generation(self.session, C.byref(env._host))
        self.callbacks = []
        self.pending = None
        self.outcome = GuestOutcome()
        self.kind = 0
        self.capture_sequence = 0
        # No handler executes in this capture-only scope. The identity satisfies
        # the driver's existing executable allowlist contract without dispatch.
        self.runner = GuestExceptionRunner(env.machine, allowed_handlers={function})

    def enter_callback(self, pointer):
        if self.pending is not None:
            raise ContextFault('callback entered after guest transfer')
        self.callbacks.append(pointer)

    def leave_callback(self):
        self.callbacks.pop()

    def capture_original(self, event, call):
        e, machine = self.env, self.env.machine
        if (not isinstance(event, Raise) or not self.callbacks or self.pending is not None or
                machine.guest_exceptions is not self.runner or not self.runner._active or
                not self.runner.transitions or self.runner.transitions[-1] is not event or
                e._host.guestSession != self.session or e._host.fault or
                call.function not in e.source_callees or e._lookup(call.function) is not None):
            raise ContextFault('physical event lacks its live original bridge capability')
        pointer = self.callbacks[-1]
        raw = pointer.contents
        if raw.function != call.function or not raw.sourceContext or raw.compilerContext:
            raise ContextFault('physical event does not belong to the active source call')
        cpu = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                                  *event.cpu.values, event.cpu.fs_head, 0, 0, 0)
        if cpu.eip != self.stub:
            raise ContextFault('physical event is not at this Machine RaiseException stub')
        snapshot = FrozenGuestState(event, event.cpu, machine.read(STACK_BASE, STACK_SIZE),
            machine.read(HEAP_BASE, e.heap_bytes),
            machine.read(e.program.data_start, e.program.size - e.data_offset),
            e._source_budget.value, tuple(sorted(e.spans.items())), tuple(e.freed), e._bump,
            tuple(sorted(e.names.items())), tuple(copy.deepcopy(e.events)), self.generation,
            machine.uc.context_save())
        # C capture validates physical stack via host.bytes; synchronize all
        # native buffers from the same frozen instant before calling it.
        C.memmove(e._stack, snapshot.stack, len(snapshot.stack))
        C.memmove(e._heap, snapshot.heap, len(snapshot.heap))
        C.memmove(C.addressof(e._image) + e.data_offset, snapshot.image_data, len(snapshot.image_data))
        native = GuestPhysicalEvent(C.sizeof(GuestPhysicalEvent), 1, 1, self.slot, self.stub,
            event.code, event.flags, len(event.information), event.return_pc, cpu,
            (U32 * 15)(*event.information))
        # The registry payload token is scoped to this one-shot adapter, not a
        # memory address or authority to revive a retired snapshot.
        if not self.library.claw_guest_capture_original(self.session, C.byref(e._host), self.generation,
                                                        pointer, C.byref(native), self.capture_sequence + 1):
            raise ContextFault('guest physical capture rejected its retained witnesses')
        # C validated its leased call and physical stack across host.bytes.
        # The Python-owned payload must still describe exactly the same instant,
        # including bytes unrelated to exception arguments and allocator state.
        if (bytes(e._stack) != snapshot.stack or bytes(e._heap) != snapshot.heap or
                bytes(e._image)[e.data_offset:] != snapshot.image_data or
                machine.read(STACK_BASE, STACK_SIZE) != snapshot.stack or
                machine.read(HEAP_BASE, e.heap_bytes) != snapshot.heap or
                machine.read(e.program.data_start, len(snapshot.image_data)) != snapshot.image_data or
                tuple(machine.register(r) for r in CONTEXT_REGISTERS) != event.cpu.values or
                machine.fs_head != event.cpu.fs_head or e._source_budget.value != snapshot.remaining_operations or
                tuple(sorted(e.spans.items())) != snapshot.spans or tuple(e.freed) != snapshot.freed or
                e._bump != snapshot.allocator_cursor or tuple(sorted(e.names.items())) != snapshot.names or
                tuple(e.events) != snapshot.events):
            raise ContextFault('memory, CPU, budget or bookkeeping changed during guest capture')
        self.pending = snapshot
        self.capture_sequence += 1

    def run_entry(self, entry, function, receiver, words, count, host, result):
        e = self.env
        def consume(uc, address, size, user):
            if not e._source_budget.value:
                e.machine._pending = SourceBudgetFault('shared guest graph operations exhausted')
                uc.emu_stop()
            else:
                e._source_budget.value -= 1
        hook = e.machine.uc.hook_add(UC_HOOK_CODE, consume)
        try:
            with self.runner.capture_scope():
                self.kind = self.library.claw_guest_run(self.session, host, self.generation, C.cast(entry, C.c_void_p),
                    function, receiver, words, count, result, C.byref(self.outcome))
        finally:
            e.machine.uc.hook_del(hook)
        if self.kind == 2:
            if (self.callbacks or self.pending is None or self.outcome.generation != self.generation or
                    self.outcome.payload != self.capture_sequence or self.outcome.kind != 2 or e._host.fault):
                e._host.fault = e._host.fault or 5
                self.kind = 0
        return int(self.kind == 1)

    def close(self):
        if not self.library.claw_guest_destroy(self.session, C.byref(self.env._host), self.generation):
            raise ContextFault('guest transport session did not retire')


def run_native_guest(env, entry, function, receiver, arguments, *, source_context,
                     source_return_pc, source_convention='cdecl', receiver2=0, flavor='O2'):
    """Run one opted-in source entry and own its first real original raise.

    flavor must match the entry library's guest-support linkage. No exception
    dispatch or native catch is performed. Existing source declarations and
    physical fixtures are configured on Env before calling this function.
    """
    if getattr(env, '_guest_adapter', None) is not None or env._source_graph or env._host.guestSession:
        raise ContextFault('cannot recursively enter an active guest graph')
    if source_context.inputMask != CONTEXT_ALL or source_context.outputMask != CONTEXT_ALL:
        raise ContextFault('guest root requires complete source CPU inputs and outputs')
    adapter = _Adapter(env, function, flavor)
    env._guest_adapter = adapter
    try:
        def invoke(*args):
            return adapter.run_entry(entry, *args)
        side = env.run_native(invoke, function, receiver, arguments, source_context=source_context,
                              source_return_pc=source_return_pc, source_convention=source_convention,
                              receiver2=receiver2)
        kind = 'fault' if side.fault else {0: 'fault', 1: 'returned', 2: 'transfer'}[adapter.kind]
        return GuestNativeOutcome(kind, side, adapter.pending if kind == 'transfer' else None)
    finally:
        env._guest_adapter = None
        adapter.close()


class _GraphAdapter(_Adapter):
    def __init__(self, env, function, graph, flavor):
        if not isinstance(graph, GuestGraph) or not isinstance(graph.funclet, GuestFuncletRoute):
            raise ContextFault('guest graph requires an explicit finite funclet contract')
        route = graph.funclet
        ranges = tuple(tuple(r) for r in graph.owned_ranges)
        if (route.owner_entry != function or route.handler not in graph.allowed_handlers or
                not any(lo <= route.entry_pc < hi for lo, hi in ranges) or
                any(a[1] > b[0] for a, b in zip(sorted(ranges), sorted(ranges)[1:]))):
            raise ContextFault('guest ownership ranges or root/handler identity disagree')
        intercepted = set(env.fixtures) | set(env._case_fixtures) | set(env.machine._intercepted)
        if any(lo <= address < hi for address in intercepted for lo, hi in ranges):
            raise ContextFault('an existing fixture or interception overlaps owned instructions')
        super().__init__(env, function, flavor)
        self.graph = GuestGraph(frozenset(graph.allowed_handlers), ranges, route, graph.contract)
        self.policy = None
        self._dispatch_bound = False
        self.transfers, self.invocations = [], []
        self.result = None
        self.terminal_cpu = None
        self.terminal_stack = b''
        self.terminal_provenance = 'original-machine'
        self._native_funclet_unresolved = False
        self._graph_host = None
        self._graph_budget = None
        self._import_routes = {slot: STUB_BASE + i for i, slot in enumerate(sorted(env.program.imports))}
        self._physical_stubs = frozenset(self._import_routes.values())
        try:
            if graph.contract is not None:
                from .guest_policy import GuestPolicy
                self.policy = GuestPolicy(env, graph.contract)
                self.policy.validate_graph(self.graph)
            self._verify_owned_intercepts()
            self.runner = GuestExceptionRunner(env.machine, allowed_handlers=graph.allowed_handlers)
            self.runner.on_physical = self._physical
            self.runner.on_owned_validate = self._verify_metadata
            self._bound_runner = self.runner
            self._bound_physical = dict(self.runner._physical)
            self._metadata = self._metadata_witness()
            contract = GuestEHContract(C.sizeof(GuestEHContract), 1, route.owner_entry, route.entry_pc,
                route.handler, route.func_info, route.handler_table, route.call_site, route.return_pc)
            if not self.library.claw_guest_bind_eh(self.session, C.byref(env._host), self.generation,
                                                   C.byref(contract), C.cast(route.native_entry, C.c_void_p)):
                raise ContextFault('native funclet binding rejected')
        except BaseException:
            self.close()
            raise

    def _metadata_witness(self):
        e, route = self.env, self.graph.funclet
        def original(address, size):
            offset = address - e.program.base
            if offset < 0 or offset + size > len(e.pristine_image):
                raise ContextFault('funclet metadata is outside the pinned image')
            return e.pristine_image[offset:offset + size]
        thunk = original(route.handler, 10)
        info = original(route.func_info, 28)
        handler = original(route.handler_table, 16)
        fi = struct.unpack('<7I', info)
        if (thunk[:1] != b'\xb8' or struct.unpack('<I', thunk[1:5])[0] != route.func_info or
                thunk[5:6] != b'\xe9' or fi[0] != 0x19930520 or fi[1] != 2 or fi[3] != 1 or
                struct.unpack('<4I', handler)[2:] != (0xffffffe8, route.entry_pc) or
                original(route.call_site, 2) != b'\xff\xd0' or route.return_pc != route.call_site + 2):
            raise ContextFault('unsupported pinned typed-funclet metadata')
        try_block = original(fi[4], 20)
        if struct.unpack('<5I', try_block) != (0, 0, 1, 1, route.handler_table):
            raise ContextFault('funclet handler table is not attached to its original try block')
        return ((route.handler, thunk), (route.func_info, info), (route.handler_table, handler),
                (fi[4], try_block), (route.call_site, b'\xff\xd0'))

    def _verify_metadata(self):
        self._verify_graph_host()
        self._verify_owned_intercepts()
        if self.policy:
            self.policy.verify('dispatch', native=True)
        if any(self.env.machine.read(a, len(data)) != data for a, data in self._metadata):
            raise ContextFault('original funclet selection metadata changed during the graph')

    def _host_identity(self):
        h = self.env._host
        address = lambda pointer: C.cast(pointer, C.c_void_p).value
        return (h.user, h.bytes, address(h.call), h.maximumOperations, address(h.remainingOperations),
                address(h.sourceContext), address(h.compilerContext), h.sourceReturnPC, h.entryStackPointer)

    def _verify_graph_host(self):
        if self._graph_host is None:
            return
        e = self.env
        if self.policy and self._dispatch_bound:
            runner = self._bound_runner
            if (self.runner is not runner or e.machine.guest_exceptions is not runner or
                    runner.machine is not e.machine or not runner._active or
                    runner.allowed_handlers != self.graph.allowed_handlers or
                    runner._physical != self._bound_physical or runner.on_physical != self._physical or
                    runner.on_owned_validate != self._verify_metadata or e._guest_adapter is not self):
                raise ContextFault('contracted native guest dispatch authority changed')
        if e._host.fault:
            raise ContextFault('guest graph stopped by an existing native fault')
        current = self._host_identity()
        if (e._source_budget is not self._graph_budget or current[:5] != self._graph_host[:5] or
                current[4] != C.addressof(self._graph_budget)):
            raise ContextFault('guest graph host or shared counter authority changed')
        if e._host.guestSession:
            if e._host.guestSession != self.session or self.library.claw_guest_status(C.byref(e._host)) == 2:
                raise ContextFault('active native guest scope changed during original execution')
        elif current != self._graph_host:
            raise ContextFault('suspended graph host scope changed during original execution')

    def before_physical_effect(self):
        self._verify_graph_host()
        self._verify_owned_intercepts()
        if self.policy:
            self.policy.verify('before physical effect', native=True)
        return self._graph_budget.value

    def after_physical_effect(self, remaining):
        self._verify_graph_host()
        self._verify_owned_intercepts()
        if self.policy:
            self.policy.verify('after physical effect', native=True)
        if self._graph_budget.value != remaining:
            raise ContextFault('physical callback changed the shared operation budget')

    def _verify_owned_intercepts(self):
        e = self.env
        intercepted = set(e.fixtures) | set(e._case_fixtures) | set(e.machine._intercepted)
        if any(lo <= address < hi for address in intercepted for lo, hi in self.graph.owned_ranges):
            raise ContextFault('fixture or interception overlaps owned instructions')
        if (e._case_fixtures or e.machine._intercepted or set(e.fixtures) - self._import_routes.keys() or
                e.machine.import_stub != self._import_routes or
                e.stub_function != {stub: slot for slot, stub in self._import_routes.items()} or
                e.machine.on_external != e._external):
            raise ContextFault('guest graph permits only exact original physical import routes')

    def _verify_execution_origin(self, address, size):
        e = self.env
        if address in self._physical_stubs:
            return
        low, high = e.program.text
        if not (low <= address < address + size <= high):
            raise ContextFault('guest original execution escaped pinned text or physical import stubs')
        offset = address - e.program.base
        if e.machine.read(address, size) != e.pristine_image[offset:offset + size]:
            raise ContextFault('guest original instruction differs from pinned code')

    def _snapshot(self, event):
        e, m = self.env, self.env.machine
        return FrozenGuestState(event, self.runner._cpu(), m.read(STACK_BASE, STACK_SIZE),
            m.read(HEAP_BASE, e.heap_bytes), m.read(e.program.data_start, e.program.size - e.data_offset),
            e._source_budget.value, tuple(sorted(e.spans.items())), tuple(e.freed), e._bump,
            tuple(sorted(e.names.items())), tuple(copy.deepcopy(e.events)), self.generation, m.uc.context_save())

    def _physical(self, event):
        self._verify_graph_host()
        self._verify_owned_intercepts()
        if self.policy:
            self.policy.verify('physical transfer', native=True)
        self.transfers.append(self._snapshot(event))

    def enter_callback(self, pointer):
        if self.policy:
            self.policy.verify('native source call', native=True)
            self.policy.native_call(pointer.contents)
        super().enter_callback(pointer)

    def leave_callback(self):
        try:
            if self.policy:
                self.policy.verify('native source completion', native=True)
        except BaseException as error:
            # Env invokes this from a ctypes callback finally block. Preserve
            # the first fault without throwing through the foreign C boundary.
            self._fault(error)
        finally:
            super().leave_callback()

    def _sync_native(self):
        e, m = self.env, self.env.machine
        C.memmove(e._stack, m.read(STACK_BASE, STACK_SIZE), STACK_SIZE)
        C.memmove(e._heap, m.read(HEAP_BASE, e.heap_bytes), e.heap_bytes)
        data = m.read(e.program.data_start, e.program.size - e.data_offset)
        C.memmove(C.addressof(e._image) + e.data_offset, data, len(data))

    def _restore_transfer(self, snapshot):
        e, m = self.env, self.env.machine
        self._verify_graph_host()
        if snapshot.generation != self.generation or e._source_budget.value != snapshot.remaining_operations:
            raise ContextFault('guest transfer lost its graph or shared budget')
        m.write(STACK_BASE, snapshot.stack)
        m.write(HEAP_BASE, snapshot.heap)
        m.write(e.program.data_start, snapshot.image_data)
        m.uc.context_restore(snapshot._machine_context)
        m.fs_head = snapshot.cpu.fs_head

    def _invoke_owned(self, invocation):
        # Until a validated transfer is restored, the private native invocation
        # may have advanced beyond the stopped Machine CPU and stack.
        self._native_funclet_unresolved = True
        e, m = self.env, self.env.machine
        self._verify_graph_host()
        if (m._execution_depth or self.callbacks or e._bridge_depth or e._host.guestSession or
                e._host.fault or invocation.cpu != self.runner._cpu()):
            raise ContextFault('native funclet requires a stopped, unborrowed original invocation')
        self._verify_metadata()
        self._sync_native()
        frozen = self._snapshot(self.runner._searches[-1].event)
        cpu = NativeSourceContext(72, 1, CONTEXT_ALL, CONTEXT_ALL,
                                  *invocation.cpu.values, invocation.cpu.fs_head, 0, 0, 0)
        native = GuestEHInvocation(C.sizeof(GuestEHInvocation), 1, invocation.owner_entry,
            invocation.entry_pc, invocation.establisher, invocation.exception_record, invocation.context_record,
            invocation.serial, cpu)
        self.pending = None
        previous_backend = e.backend
        e.backend = 'native'
        outcome = GuestOutcome()
        try:
            if not self.library.claw_guest_prepare_eh(self.session, C.byref(e._host), self.generation,
                                                     C.byref(native)):
                raise ContextFault('native funclet preflight rejected its invocation')
            if (self.runner._cpu() != frozen.cpu or bytes(e._stack) != frozen.stack or
                    bytes(e._heap) != frozen.heap or bytes(e._image)[e.data_offset:] != frozen.image_data or
                    m.read(STACK_BASE, STACK_SIZE) != frozen.stack or m.read(HEAP_BASE, e.heap_bytes) != frozen.heap or
                    m.read(e.program.data_start, len(frozen.image_data)) != frozen.image_data or
                    e._source_budget.value != frozen.remaining_operations or
                    tuple(sorted(e.spans.items())) != frozen.spans or tuple(e.freed) != frozen.freed or
                    e._bump != frozen.allocator_cursor or tuple(sorted(e.names.items())) != frozen.names or
                    tuple(e.events) != frozen.events):
                raise ContextFault('guest state changed during native funclet preflight')
            self._verify_metadata()
            kind = self.library.claw_guest_run_eh(self.session, C.byref(e._host), self.generation,
                                                 C.byref(native), C.byref(outcome))
        finally:
            e.backend = previous_backend
        self.invocations.append(invocation)
        if (kind != 2 or e._host.fault or self.pending is None or self.callbacks or
                outcome.generation != self.generation or outcome.payload != self.capture_sequence):
            raise ContextFault('native owned funclet did not produce its nonreturning transfer')
        self._restore_transfer(self.pending)
        self._native_funclet_unresolved = False
        return self.pending.event

    @contextmanager
    def scope(self):
        e = self.env
        self._graph_host = self._host_identity()
        self._graph_budget = e._source_budget
        self._verify_graph_host()
        def consume(uc, address, size, user):
            if e.machine._pending is not None and not isinstance(e.machine._pending, PhysicalTransfer):
                return
            try:
                self._verify_graph_host()
                self._verify_execution_origin(address, size)
                if self.policy:
                    self.policy.instruction(address, size)
                if any(lo <= address < hi for lo, hi in self.graph.owned_ranges):
                    return  # The stopped owned instruction has not executed.
                self.runner.operations += 1
                if not self._graph_budget.value:
                    raise SourceBudgetFault('shared guest graph operations exhausted')
                self._graph_budget.value -= 1
            except BaseException as error:
                e.machine._pending = error
                uc.emu_stop()
        hook = e.machine.uc.hook_add(UC_HOOK_CODE, consume)
        try:
            with (self.policy.scope() if self.policy else nullcontext()), self.runner.capture_scope(), self.runner.owned_scope(self.graph.funclet,
                    self.graph.owned_ranges, self._invoke_owned):
                self._dispatch_bound = True
                self._verify_metadata()
                yield
        finally:
            self._dispatch_bound = False
            e.machine.uc.hook_del(hook)

    def _fault(self, error):
        e = self.env
        e.errors.append(error)
        kind = 3 if isinstance(error, SourceBudgetFault) else 2 if isinstance(error, Halt) else 5 if isinstance(error, ContextFault) else 6
        e._host.fault = e._host.fault or kind

    def run_entry(self, entry, function, receiver, words, count, host, result):
        e = self.env
        root_context = e._host.sourceContext.contents
        original_resumed = False
        with self.scope():
            try:
                self.kind = self.library.claw_guest_run(self.session, host, self.generation, C.cast(entry, C.c_void_p),
                    function, receiver, words, count, result, C.byref(self.outcome))
                if self.policy:
                    self.policy.verify('native root completion', native=True)
                if self.kind == 2 and not e._host.fault:
                    if self.pending is None or self.outcome.payload != self.capture_sequence or self.callbacks:
                        raise ContextFault('root transfer lost its owned snapshot')
                    self._restore_transfer(self.pending)
                    e.backend = 'machine'
                    original_resumed = True
                    self.result = self.runner.resume_raise(self.pending.event)
                    self._sync_native()
                elif self.kind == 1 and not e._host.fault:
                    self.result = GuestResult('returned', C.cast(result, C.POINTER(U32)).contents.value,
                        e._host.sourceContext.contents.esp, None, tuple(self.runner.transitions), self.runner.operations)
                elif not e._host.fault:
                    raise ContextFault('native guest root ended without a typed outcome')
            except BaseException as error:
                self._fault(error)
            finally:
                if not original_resumed:
                    self.terminal_provenance = 'native-root'
                    context = root_context
                    self.terminal_cpu = CPU(tuple(getattr(context, n) for n in CONTEXT_FIELDS[:-1]), context.fsHead)
                    self.terminal_stack = bytes(e._stack)
                else:
                    self.terminal_cpu = self.runner._cpu()
                    self.terminal_stack = e.machine.read(STACK_BASE, STACK_SIZE)
                e.backend = 'native'
        return int(self.kind == 1 and not e._host.fault)

    def graph_outcome(self, side):
        unavailable = self._native_funclet_unresolved
        e = self.env
        terminal_state = None if unavailable else GuestTerminalState(e._bump,
            tuple(sorted(e.names.items())), tuple(sorted(e.spans.items())), tuple(e.freed))
        return GuestGraphOutcome('fault' if side.fault or self.result is None else self.result.kind,
            side, self.result, tuple(self.transfers), tuple(self.invocations),
            None if unavailable else self.terminal_cpu,
            None if unavailable else self.terminal_stack,
            'unavailable-native-funclet-fault' if unavailable else self.terminal_provenance,
            terminal_state)


def run_native_guest_graph(env, entry, function, receiver, arguments, *, graph, source_context,
                           source_return_pc, source_convention='cdecl', receiver2=0, flavor='O2'):
    if getattr(env, '_guest_adapter', None) is not None or env._source_graph or env._host.guestSession:
        raise ContextFault('cannot recursively enter an active guest graph')
    if source_context.inputMask != CONTEXT_ALL or source_context.outputMask != CONTEXT_ALL:
        raise ContextFault('guest root requires complete source CPU')
    adapter = _GraphAdapter(env, function, graph, flavor)
    env._guest_adapter = adapter
    try:
        if adapter.policy:
            adapter.policy.validate_root(function, receiver, tuple(arguments), source_context, source_return_pc,
                                         source_convention, receiver2, graph.allowed_handlers)
        side = env.run_native(lambda *args: adapter.run_entry(entry, *args), function, receiver, arguments,
            source_context=source_context, source_return_pc=source_return_pc,
            source_convention=source_convention, receiver2=receiver2)
        return adapter.graph_outcome(side)
    finally:
        env._guest_adapter = None
        adapter.close()


def run_original_guest_graph(env, function, receiver, arguments, *, graph, stack_pointer=STACK_TOP,
                             flavor='O2'):
    """Transport-only original root with an explicitly owned native interior.

    The declared owned ranges are stopped before execution. This cannot serve
    as whole-root parity if the original root lies outside those owned ranges.
    """
    e = env
    if getattr(e, '_guest_adapter', None) is not None or e._source_graph or e._host.guestSession:
        raise ContextFault('cannot recursively enter an active guest graph')
    adapter = _GraphAdapter(e, function, graph, flavor)
    previous_host = NativeHost.from_buffer_copy(e._host)
    e._guest_adapter = adapter
    try:
        heap, image, _, _, _ = e._frozen
        e.side, e.backend = 'native', 'machine'
        e._reset_run()
        e.machine.reset_x87()
        e.machine.write(HEAP_BASE, heap)
        e.machine.write(e.program.data_start, image[e.data_offset:])
        e.machine.write(STACK_BASE, bytes(e._initial['stack']))
        e._spans_changed()
        e._source_graph = True
        e._source_budget = C.c_uint64(e.maximum_operations or 200000000)
        e._host.remainingOperations = C.pointer(e._source_budget)
        e._host.fault = e._host.faultAddress = 0
        e._host.sourceContext = e._host.compilerContext = None
        e._host.sourceReturnPC = 0
        e._host.entryStackPointer = stack_pointer
        with adapter.scope():
            try:
                returned = e.machine.call(function, receiver, arguments=arguments, stack_pointer=stack_pointer)
                if not returned.completed:
                    raise ContextFault('original guest root did not return or transfer')
                adapter.result = GuestResult('returned', returned.eax, returned.stack_pointer, None,
                                             tuple(adapter.runner.transitions), adapter.runner.operations)
            except PhysicalTransfer as stop:
                try:
                    adapter.result = adapter.runner.resume_raise(stop.event)
                except BaseException as error:
                    adapter._fault(error)
            except BaseException as error:
                adapter._fault(error)
        adapter.terminal_cpu = adapter.runner._cpu()
        adapter.terminal_stack = e.machine.read(STACK_BASE, STACK_SIZE)
        adapter._sync_native()
        side = Side(completed=bool(adapter.result and adapter.result.kind == 'returned'),
            halted=e._host.fault == 2, fault=e._host.fault, fault_address=e._host.faultAddress,
            eax=adapter.result.eax if adapter.result else 0,
            stack_pointer=adapter.result.stack_pointer if adapter.result else 0,
            events=list(e.events), heap=bytes(e._heap), image=bytes(e._image)[e.data_offset:],
            spans=dict(e.spans), freed=list(e.freed), errors=list(e.errors), bridged=list(e.bridged))
        return adapter.graph_outcome(side)
    finally:
        e._source_graph = False
        e._guest_adapter = None
        e._host.compilerContext = previous_host.compilerContext
        e._host.sourceContext = previous_host.sourceContext
        e._host.sourceReturnPC = previous_host.sourceReturnPC
        e._host.entryStackPointer = previous_host.entryStackPointer
        e._host.remainingOperations = previous_host.remainingOperations
        e.backend = 'native'
        adapter.close()
