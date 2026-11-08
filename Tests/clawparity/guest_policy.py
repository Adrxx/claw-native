"""Shared runtime enforcement for the normalized bounded guest contract.

No native library, execution driver, or family admission is selected here.
"""
import ctypes as C
import hashlib
from contextlib import contextmanager

from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EBP

from .guest_contract import (GuestContract, AttachedEntry, GuestService, GuestDependency,
                             normalize_guest_contract)
from .kernel import (ContextFault, CONTEXT_ALL, STACK_BASE, STACK_SIZE,
                     validate_source, validate_source_operands, validate_context)
from .program import claw


def _validated(contract):
    """Reject loose/forged reduced plans by rebuilding their pinned semantics."""
    try:
        if (type(contract) is not GuestContract or type(contract.attached_entry) is not AttachedEntry or
                type(contract.owned_ranges) is not tuple or type(contract.guest_services) is not tuple or
                any(type(v) is not GuestService for v in contract.guest_services) or
                type(contract.dependencies) is not tuple or
                any(type(v) is not GuestDependency for v in contract.dependencies) or
                type(contract.allowed_handlers) is not frozenset or type(contract.allowed_factories) is not frozenset or
                type(contract.required_outcomes) is not frozenset or type(contract.immutable_regions) is not tuple):
            raise ValueError('runtime guest policy requires an exact normalized GuestContract')
        program = claw()
        def read(address, size):
            section = next(s for s in program.sections if s.address <= address < address + size <= s.address + len(s.data))
            return section.data[address - section.address:address - section.address + size]
        for row in contract.immutable_regions:
            if type(row) is not tuple or len(row) != 2 or type(row[0]) is not int or type(row[1]) is not bytes:
                raise ValueError('invalid immutable region type')
        for row in contract.owned_ranges:
            if type(row) is not tuple or len(row) != 2 or any(type(v) is not int for v in row):
                raise ValueError('invalid ownership range type')
        if any(type(v) is not int for v in contract.allowed_handlers | contract.allowed_factories):
            raise ValueError('invalid executable address type')
        a = contract.attached_entry
        if type(a.owner_entry) is not int or a.owner_entry != contract.root:
            raise ValueError('attached root mismatch')
        source = dict(input_mask=CONTEXT_ALL, output_mask=CONTEXT_ALL, preserve_mask=0)
        dependencies = {}
        for dependency in contract.dependencies:
            for name in ('address', 'argc', 'input_mask', 'output_mask'):
                if type(getattr(dependency, name)) is not int:
                    raise ValueError('invalid dependency integer field')
            for name in ('convention', 'returns', 'channel'):
                if type(getattr(dependency, name)) is not str:
                    raise ValueError('invalid dependency text field')
            if dependency.channel not in ('source_context', 'compiler_context'):
                raise ValueError('invalid dependency channel')
            compiler = dependency.channel == 'compiler_context'
            if (dependency.preserve_mask is not None if compiler else type(dependency.preserve_mask) is not int):
                raise ValueError('invalid dependency preservation field')
            key = f'{dependency.address:#x}'
            if key in dependencies:
                raise ValueError('duplicate dependency record')
            masks = dict(input_mask=dependency.input_mask, output_mask=dependency.output_mask)
            if not compiler:
                masks['preserve_mask'] = dependency.preserve_mask
            dependencies[key] = dict(kind='whole', convention=dependency.convention,
                argc=dependency.argc, returns=dependency.returns, **{dependency.channel: masks})
        for service in contract.guest_services:
            if type(service.address) is not int or type(service.arguments) is not tuple:
                raise ValueError('invalid physical service type')
            key = f'{service.address:#x}'
            if key in dependencies:
                raise ValueError('duplicate physical service')
            dependencies[key] = dict(kind='guest-service', name=service.name, convention=service.convention,
                argc=service.argc, arguments=list(service.arguments), returns=service.returns, reason='runtime contract validation')
        spec = dict(abi='canonical', owned=[dict(address=f'{contract.root:#x}', convention='thiscall', argc=1,
            returns='u32', source_context=source,
            body_ranges=[dict(start=f'{lo:#x}', end=f'{hi:#x}', sha256=hashlib.sha256(read(lo, hi-lo)).hexdigest())
                         for lo, hi in contract.owned_ranges],
            attached_entries=[dict(address=f'{a.entry_pc:#x}', kind='eh-funclet', native_entry=a.native_entry,
                handler=f'{a.handler:#x}', func_info=f'{a.func_info:#x}', handler_table=f'{a.handler_table:#x}',
                call_site=f'{a.call_site:#x}', return_pc=f'{a.return_pc:#x}', frame_delta_ebp=a.frame_delta_ebp,
                cpu=dict(input_mask=a.input_mask, output_mask=a.output_mask), normal_return=a.normal_return)])],
            callees=dependencies, oracle=dict(kind='clawparity', entry='policy_root_validation', guest_graph=dict(
                version=contract.version, allowed_handlers=[f'{v:#x}' for v in sorted(contract.allowed_handlers)],
                factory_call_site=f'{contract.factory_call_site:#x}',
                allowed_factories=[f'{v:#x}' for v in sorted(contract.allowed_factories)],
                required_outcomes=sorted(contract.required_outcomes),
                require_native_attached_entries=contract.require_native_attached_entries)))
        rebuilt = normalize_guest_contract(spec)
        if rebuilt != contract:
            raise ValueError('runtime contract differs from independently normalized pinned plan')
        return rebuilt, program
    except (ValueError, TypeError, AttributeError, StopIteration, OSError) as error:
        raise ContextFault(f'invalid normalized runtime guest contract: {error}') from error


class GuestPolicy:
    def __init__(self, env, contract):
        self.contract, program = _validated(contract)
        self.env = env
        self._program = program
        self._active = False
        if (env.program.sha256 != program.sha256 or env.program.base != program.base or
                env.program.text != program.text or env.program.size != program.size or
                env.program.imports != program.imports):
            raise ContextFault('guest contract requires the pinned original program')
        self._regions = self.contract.immutable_regions
        if not hasattr(env, '_frozen'):
            raise ContextFault('guest policy requires frozen initial memory')
        frozen_image = env._frozen[1]
        for address, data in self._regions:
            offset = address - program.base
            if (bytes(frozen_image[offset:offset + len(data)]) != data or
                    env.pristine_image[offset:offset + len(data)] != data):
                raise ContextFault('initial guest code or exception metadata differs from pinned bytes')

    def validate_root(self, function, receiver, arguments, source_context, source_return_pc,
                      source_convention, receiver2, allowed_handlers):
        p = self.contract
        if (type(function) is not int or function != p.root or source_convention != 'thiscall' or
                type(receiver) is not int or type(receiver2) is not int or receiver2 != 0 or
                len(arguments) != 1 or type(arguments[0]) is not int or arguments[0] not in p.allowed_factories or
                frozenset(allowed_handlers) != p.allowed_handlers or source_context.inputMask != CONTEXT_ALL or
                source_context.outputMask != CONTEXT_ALL or source_context.preserveMask != 0 or
                not self.env.program.in_text(source_return_pc)):
            raise ContextFault('source root does not match normalized guest contract')
        validate_source(source_context, function, source_return_pc, self.env.program)
        validate_source_operands(source_context, source_convention, receiver, receiver2, arguments)
        # The bounded root has direct original callers. Merely choosing any
        # executable continuation does not establish a source CALL boundary.
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        from capstone.x86_const import X86_INS_CALL, X86_OP_IMM
        from tools.claw import index
        anchors = []
        for function_row in index.functions().values():
            for lo, hi in function_row.get('ranges', ()):
                lo = int(lo, 16) if isinstance(lo, str) else lo
                hi = int(hi, 16) if isinstance(hi, str) else hi
                if lo <= source_return_pc - 5 < source_return_pc <= hi:
                    anchors.append(lo)
        if not anchors:
            raise ContextFault('root source CALL lacks an original instruction anchor')
        anchor = max(anchors)
        section = next((s for s in self._program.sections if
                        s.address <= anchor < source_return_pc <= s.address + len(s.data)), None)
        if section is None:
            raise ContextFault('root continuation is not backed by original code')
        offset = anchor - section.address
        decoder = Cs(CS_ARCH_X86, CS_MODE_32)
        decoder.detail = True
        decoded = tuple(decoder.disasm(section.data[offset:source_return_pc - section.address], anchor))
        call = decoded[-1] if decoded else None
        if (call is None or call.address != source_return_pc - 5 or call.id != X86_INS_CALL or call.size != 5 or len(call.operands) != 1 or
                call.operands[0].type != X86_OP_IMM or call.operands[0].imm != p.root):
            raise ContextFault('root continuation does not follow an original singleton CALL')

    def validate_graph(self, graph):
        p, a, r = self.contract, self.contract.attached_entry, graph.funclet
        if (tuple(graph.owned_ranges) != p.owned_ranges or frozenset(graph.allowed_handlers) != p.allowed_handlers or
                any(getattr(r, name) != getattr(a, name) for name in
                    ('owner_entry', 'entry_pc', 'handler', 'func_info', 'handler_table', 'call_site', 'return_pc')) or
                getattr(r.native_entry, '__name__', None) != a.native_entry):
            raise ContextFault('native graph route or ownership differs from normalized contract')

    def verify(self, boundary, *, native=False):
        e = self.env
        for address, data in self._regions:
            if e.machine.read(address, len(data)) != data:
                raise ContextFault(f'protected guest bytes changed at {boundary}')
            if native:
                offset = address - e.program.base
                if C.string_at(C.addressof(e._image) + offset, len(data)) != data:
                    raise ContextFault(f'protected native guest bytes changed at {boundary}')

    def instruction(self, address, size=None):
        if address == self.contract.factory_call_site:
            ebp = self.env.machine.register(UC_X86_REG_EBP)
            if ebp & 3 or not STACK_BASE <= ebp + 8 <= STACK_BASE + STACK_SIZE - 4:
                raise ContextFault('original factory source slot is outside its stack frame')
            if self.env.machine.words(ebp + 8, 1)[0] not in self.contract.allowed_factories:
                raise ContextFault('original factory CALL target is outside the normalized domain')

    def native_call(self, raw):
        p = self.contract
        continuation = p.factory_call_site + 3
        if raw.sourceReturnPC == continuation or raw.function in p.allowed_factories:
            if (raw.sourceReturnPC != continuation or raw.function not in p.allowed_factories or
                    not raw.sourceContext or raw.compilerContext or raw.argumentCount or raw.receiver or raw.receiver2):
                raise ContextFault('native factory source call is outside the normalized domain')
        dependency = next((d for d in p.dependencies if d.address == raw.function), None)
        if dependency is None:
            return  # Physical imports and owned-code guards retain their existing authority.
        if (raw.argumentCount != dependency.argc or raw.x87ArgumentCount or
                raw.receiver or raw.receiver2):
            raise ContextFault('native dependency operands differ from normalized contract')
        if dependency.channel == 'compiler_context':
            if not raw.compilerContext or raw.sourceContext or raw.sourceReturnPC or raw.stackPointer:
                raise ContextFault('native dependency requires the normalized compiler channel')
            context = raw.compilerContext.contents
            validate_context(context, raw.function, self._program)
        else:
            if not raw.sourceContext or raw.compilerContext:
                raise ContextFault('native dependency requires the normalized source channel')
            context = raw.sourceContext.contents
            validate_source(context, raw.function, raw.sourceReturnPC, self._program)
            validate_source_operands(context, dependency.convention, raw.receiver, raw.receiver2,
                                     tuple(raw.arguments[:raw.argumentCount]))
            if context.preserveMask != dependency.preserve_mask or raw.stackPointer != context.esp:
                raise ContextFault('native dependency preservation or frame differs from normalized contract')
        if (context.inputMask != dependency.input_mask or context.outputMask != dependency.output_mask):
            raise ContextFault('native dependency masks differ from normalized contract')


    @contextmanager
    def scope(self):
        if self._active:
            raise ContextFault('guest policy scope is already active')
        self._active = True
        def write(uc, access, address, size, value, user):
            if any(address < start + len(data) and start < address + size for start, data in self._regions):
                if self.env.machine._pending is None:
                    self.env.machine._pending = ContextFault('original guest instruction wrote protected code or metadata')
                uc.emu_stop()
        hook = None
        try:
            hook = self.env.machine.uc.hook_add(UC_HOOK_MEM_WRITE, write)
            yield self
        finally:
            if hook is not None:
                self.env.machine.uc.hook_del(hook)
            self._active = False
