"""Original-only full-source guest baseline; no native entry or owned handoff.

The caller supplies a prepared, frozen Env and explicit physical import effects.
Every executable guest instruction, including catch bodies, remains original.
This helper is not family admission and does not load guest native support.
"""
import copy
import ctypes as C
from contextlib import nullcontext
from dataclasses import dataclass

from unicorn import UC_HOOK_CODE, UcError

from .env import HEAP_BASE, NativeSourceContext, Side, Halt, SourceBudgetFault, HarnessError
from .guest_exception import CPU, GuestExceptionRunner, GuestResult, PhysicalTransfer
from .kernel import (CONTEXT_ALL, CONTEXT_FIELDS, CONTEXT_REGISTERS, STACK_BASE, STACK_SIZE, STUB_BASE, STOP,
                     ContextFault, EmulationFault, validate_source, validate_source_operands)
from .program import claw


class _HostFault(Exception):
    def __init__(self, code, address):
        super().__init__(f'physical callback set host fault {code} at {address:#x}')
        self.code, self.address = code, address


@dataclass(frozen=True)
class OriginalGuestState:
    event: object
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


@dataclass(frozen=True)
class OriginalGuestOutcome:
    kind: str  # returned, unhandled, halt, or fault
    side: Side
    result: GuestResult | None
    transfers: tuple
    terminal_cpu: CPU
    terminal_stack: bytes
    terminal_state: OriginalGuestState
    coverage: frozenset
    operations: int
    remaining_operations: int
    terminal_provenance: str = 'original-machine'


def run_original_guest_source(env, function, receiver, arguments, *, allowed_handlers,
                              source_context, source_return_pc, source_convention='cdecl',
                              receiver2=0, trace=True, max_operations=None,
                              max_depth=8, max_frames=64, contract=None, check_objects=False):
    """Execute one frozen original source graph, preserving the caller's context.

    Malformed preflight inputs raise ContextFault. Execution failures return a
    fault outcome. Unhandled exceptions keep the genuine terminal CPU/stack;
    only normal returns use Machine.call_source's ordinary return validation.
    Memory/ownership/events are copied into the result. Temporary Env state and
    the complete native host are restored even on error; Machine retains the
    terminal original state for inspection. Coverage is instruction coverage.
    An optional normalized GuestContract additionally enforces the finite
    family root, factories, handlers and immutable exception metadata.
    """
    e, m = env, env.machine
    if (getattr(e, '_guest_adapter', None) is not None or e._source_graph or e._bridge_depth or
            e._host.guestSession or m.guest_exceptions is not None or m._owned_scope is not None or
            m._execution_depth):
        raise ContextFault('cannot recursively enter an active guest graph')
    if getattr(m, '_heap_hook', None) is not None:
        raise ContextFault('guest baseline requires no preexisting heap watcher')
    if not isinstance(source_context, NativeSourceContext):
        raise ContextFault('guest baseline requires NativeSourceContext')
    context = NativeSourceContext.from_buffer_copy(source_context)
    if context.inputMask != CONTEXT_ALL or context.outputMask != CONTEXT_ALL:
        raise ContextFault('guest baseline requires complete CPU input and output masks')
    arguments = tuple(arguments)
    validate_source(context, function, source_return_pc, e.program)
    validate_source_operands(context, source_convention, receiver, receiver2, arguments)
    if max_operations is None and type(e.maximum_operations) is not int:
        raise ContextFault('guest baseline requires an integer Env operation budget')
    limit = (e.maximum_operations or 200000000) if max_operations is None else max_operations
    if type(limit) is not int or not 1 <= limit <= 0xffffffffffffffff:
        raise ContextFault('guest baseline requires a positive finite integer budget')
    if not hasattr(e, '_frozen'):
        raise ContextFault('guest baseline requires frozen Env input')
    # Recheck the pinned file before reading original executable bytes. The
    # frozen case can seed data, but cannot supply an alternative code oracle.
    original = claw()
    if (e.program.sha256 != original.sha256 or e.program.base != original.base or
            e.program.size != original.size or e.program.text != original.text or
            e.program.imports != original.imports):
        raise ContextFault('guest baseline requires the pinned original program')
    text_begin, text_end = original.text
    section = next(s for s in original.sections
                   if s.address <= text_begin < text_end <= s.address + len(s.data))
    code = section.data[text_begin - section.address:text_end - section.address]
    code_offset = text_begin - original.base
    runner = GuestExceptionRunner(m, allowed_handlers=allowed_handlers, max_depth=max_depth,
                                 max_frames=max_frames, max_operations=limit)
    physical_transports = dict(runner._physical)
    heap, image, _, _, _ = e._frozen
    stack = bytes(e._initial['stack'])
    if len(heap) != e.heap_bytes or len(image) != e.program.size or len(stack) != STACK_SIZE:
        raise ContextFault('malformed frozen guest memory')
    if (bytes(image[code_offset:code_offset + len(code)]) != code or
            e.pristine_image[code_offset:code_offset + len(code)] != code):
        raise ContextFault('frozen or pristine executable bytes differ from the pinned original')
    if m.on_external != e._external:
        raise ContextFault('guest baseline requires the Env physical import dispatcher')
    policy = None
    if contract is not None:
        from .guest_policy import GuestPolicy
        policy = GuestPolicy(e, contract)
        policy.validate_root(function, receiver, arguments, context, source_return_pc,
                             source_convention, receiver2, allowed_handlers)
        for address, data in contract.immutable_regions:
            offset = address - e.program.base
            if offset < 0 or offset + len(data) > len(image) or bytes(image[offset:offset + len(data)]) != data:
                raise ContextFault('frozen guest input changed protected contract metadata')

    import_stubs = {slot: STUB_BASE + i for i, slot in enumerate(sorted(original.imports))}
    stub_slots = {stub: slot for slot, stub in import_stubs.items()}

    def physical_only():
        fixtures = set(e.fixtures) | set(e._case_fixtures) | set(e._case_overrides)
        # An out-of-text Env.stub can still replace a game factory. Only the
        # real PE import slots grant fixture authority, and only their fixed
        # Machine stub identities may resolve back to those physical services.
        if (fixtures - original.imports.keys() or m._intercepted or
                m.import_stub != import_stubs or e.stub_function != stub_slots):
            raise ContextFault('original guest baseline allows only pinned physical imports; '
                               'synthetic stubs and extra interceptions are forbidden')

    physical_only()
    host_bytes = bytes(e._host)
    expected_host = None
    missing = object()
    saved = {name: getattr(e, name, missing) for name in (
        'side', 'backend', 'spans', 'names', '_bump', 'freed', 'events', 'errors', 'bridged',
        '_source_stop', '_source_graph', '_source_budget', '_guest_adapter', '_strays')}
    budget = C.c_uint64(limit)
    transfers, executed = [], set()
    side, result, kind = Side(), None, 'fault'
    hook = None
    heap_hook = None

    def verify(boundary='original instruction'):
        if e._host.fault:
            raise _HostFault(e._host.fault, e._host.faultAddress)
        if (bytes(e._host) != expected_host or e._source_budget is not budget or
                e._guest_adapter is not guard or not e._source_graph or
                e.side != 'original' or e.backend != 'machine' or m.on_external != e._external or
                m._owned_scope is not None or getattr(m, '_heap_hook', None) != heap_hook):
            raise ContextFault('original guest graph authority changed during execution')
        physical_only()
        if m.read(text_begin, len(code)) != code:
            raise ContextFault('original executable bytes changed during the guest graph')
        if policy is not None:
            if (m.guest_exceptions is not runner or runner.machine is not m or
                    runner.allowed_handlers != contract.allowed_handlers or
                    runner._physical != physical_transports or runner.on_physical is not physical):
                raise ContextFault('original guest dispatch policy authority changed')
            policy.verify(boundary)

    class PhysicalGuard:
        def before_physical_effect(self):
            verify('before original physical effect')
            return budget.value

        def after_physical_effect(self, remaining):
            verify('after original physical effect')
            if budget.value != remaining:
                raise ContextFault('physical callback changed the shared original budget')

    guard = PhysicalGuard()

    def snapshot(event=None):
        cpu = CPU(tuple(m.register(r) for r in CONTEXT_REGISTERS), m.fs_head)
        return OriginalGuestState(event, cpu, m.read(STACK_BASE, STACK_SIZE),
            m.read(HEAP_BASE, e.heap_bytes), m.read(e.program.data_start, e.program.size - e.data_offset),
            budget.value, tuple(sorted(e.spans.items())), tuple(e.freed), e._bump,
            tuple(sorted(e.names.items())), tuple(copy.deepcopy(e.events)))

    def physical(event):
        verify('original physical transfer')
        transfers.append(snapshot(event))

    def instruction(uc, address, size, user):
        if m._pending is not None:
            return
        try:
            verify()
            if not text_begin <= address < text_end:
                if address in stub_slots or address == STOP:
                    return  # Physical import/driver boundary, not guest code.
                raise ContextFault('original guest execution reached nonoriginal executable memory')
            # A real ordinary return stops before this continuation executes.
            if m._source_return_boundary(address) and not runner._searches:
                return
            if policy is not None:
                policy.instruction(address, size)
            if not budget.value:
                raise SourceBudgetFault('shared original guest graph operations exhausted')
            budget.value -= 1
            runner.operations += 1
            if trace:
                executed.add((address, size))
        except Exception as error:
            m._pending = error
            uc.emu_stop()

    try:
        e.side, e.backend = 'original', 'machine'
        e._reset_run()
        e._strays = []
        e._source_graph, e._source_budget, e._guest_adapter = True, budget, guard
        e._host.fault = e._host.faultAddress = 0
        expected_host = bytes(e._host)
        m.write(HEAP_BASE, bytes(heap))
        m.write(e.program.base, bytes(image))
        m.write(STACK_BASE, stack)
        m.reset_x87()
        if check_objects:
            m.watch_heap(e._stray_access)
            heap_hook = m._heap_hook
        runner.on_physical = physical
        hook = m.uc.hook_add(UC_HOOK_CODE, instruction)
        try:
            with policy.scope() if policy is not None else nullcontext(), runner.capture_scope():
                verify('original root entry')
                try:
                    returned = m.call_source(function, context, source_return_pc, source_convention,
                                             receiver, receiver2, arguments)
                    result = GuestResult('returned', returned.eax, returned.stack_pointer, None,
                                         tuple(runner.transitions), runner.operations)
                except PhysicalTransfer as stop:
                    result = runner.resume_raise(stop.event)
                verify('original graph completion')
                kind = result.kind
        except Exception as error:
            side.halted = isinstance(error, Halt)
            if isinstance(error, _HostFault):
                side.halted = error.code == 2
            kind = 'halt' if side.halted else 'fault'
            side.fault = (error.code if isinstance(error, _HostFault) else
                          2 if side.halted else 3 if isinstance(error, SourceBudgetFault) else
                          5 if isinstance(error, ContextFault) else 1 if isinstance(error, (UcError, EmulationFault)) else 6)
            side.fault_address = (error.address if isinstance(error, _HostFault)
                                  else m.register(CONTEXT_REGISTERS[8]))
            side.errors.append(error)
            result = None
        if e._strays:
            side.errors.append(HarnessError('the original touched heap memory outside every live object: ' +
                                            '; '.join(e._strays)))
            kind, result = 'fault', None
            if not side.fault:
                side.fault = 6
                side.fault_address = m.register(CONTEXT_REGISTERS[8])
        terminal = snapshot()
        side.completed = kind == 'returned'
        side.eax = result.eax if side.completed else 0
        side.stack_pointer = terminal.cpu.values[7]
        side.events, side.heap, side.image = list(terminal.events), terminal.heap, terminal.image_data
        side.spans, side.freed = dict(terminal.spans), list(terminal.freed)
        side.errors.extend(e.errors)
        side.bridged = list(e.bridged)
        side.source_stop = copy.deepcopy(e._source_stop)
        side.compiler_context = dict(zip(CONTEXT_FIELDS, (*terminal.cpu.values, terminal.cpu.fs_head)))
        if trace:
            e.coverage |= executed
        return OriginalGuestOutcome(kind, side, result, tuple(transfers), terminal.cpu,
            terminal.stack, terminal, frozenset(executed), runner.operations, budget.value)
    finally:
        if hook is not None:
            m.uc.hook_del(hook)
        if getattr(m, '_heap_hook', None) is not None:
            m.watch_heap(None)
        C.memmove(C.addressof(e._host), host_bytes, len(host_bytes))
        for name, value in saved.items():
            if value is missing:
                if hasattr(e, name):
                    delattr(e, name)
            else:
                setattr(e, name, value)
