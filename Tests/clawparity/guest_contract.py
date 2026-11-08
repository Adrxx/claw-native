"""Strict, inactive contract normalization for the bounded singleton EH graph.

This module grants no execution capability. Both comparison sides must validate
its immutable regions against their own initialized memory before execution.
"""
from .abi import CALL_ARGUMENT_CAPACITY

from dataclasses import dataclass
import re
import struct

from .program import claw, CLAW_SHA256
from tools.claw.owned_ranges import resolve_owned_ranges


class GuestContractError(ValueError):
    pass


@dataclass(frozen=True)
class AttachedEntry:
    owner_entry: int
    entry_pc: int
    native_entry: str
    handler: int
    func_info: int
    handler_table: int
    call_site: int
    return_pc: int
    frame_delta_ebp: int
    input_mask: int
    output_mask: int
    normal_return: bool


@dataclass(frozen=True)
class GuestService:
    address: int
    name: str
    convention: str
    argc: int
    arguments: tuple
    returns: str


@dataclass(frozen=True, slots=True)
class GuestDependency:
    address: int
    convention: str
    argc: int
    returns: str
    channel: str
    input_mask: int
    output_mask: int
    preserve_mask: int | None


@dataclass(frozen=True)
class GuestContract:
    version: int
    root: int
    owned_ranges: tuple
    attached_entry: AttachedEntry
    allowed_handlers: frozenset
    allowed_factories: frozenset
    factory_call_site: int
    required_outcomes: frozenset
    require_native_attached_entries: bool
    guest_services: tuple
    dependencies: tuple
    immutable_regions: tuple
    reference_sha256: str


_ROOT = 0x503420
_HANDLERS = frozenset((0x508539, 0x5089cd, 0x508bf8, 0x4a3260, 0x4a9348, 0x4a3490))
_FACTORIES = frozenset((0x502369, 0x502bde, 0x502c0f))
_DEPENDENCIES = {
    0x4a48c0: ('compiler-context', 0, 'context', None),
    0x502e95: ('stdcall', 1, 'void', 0),
    0x502f05: ('stdcall', 1, 'void', 0),
    0x4a5690: ('stdcall', 2, 'void', 0),
    0x502369: ('cdecl', 0, 'u32', 0x472),
    0x502bde: ('cdecl', 0, 'u32', 0),
    0x502c0f: ('cdecl', 0, 'u32', 0),
}
_SERVICES = {0x546958: 'RaiseException', 0x546a38: 'RtlUnwind'}
_ADDRESS = re.compile(r'0x[0-9a-f]{6,8}\Z')
_SYMBOL = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


def _fail(message):
    raise GuestContractError(message)


def _shape(value, required, optional=(), *, where):
    if type(value) is not dict or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        _fail(f'{where}: missing or unknown fields')
    return value


def _address(value):
    if type(value) is not str or not _ADDRESS.fullmatch(value):
        _fail('address must be lowercase 6-8 digit hexadecimal text')
    return int(value, 16)


def _exact(value, expected, where):
    if type(value) is not type(expected) or value != expected:
        _fail(f'{where}: unsupported value')


def _addresses(value, expected, where):
    if type(value) is not list:
        _fail(f'{where}: expected an explicit list')
    result = tuple(_address(v) for v in value)
    if len(result) != len(set(result)) or frozenset(result) != expected:
        _fail(f'{where}: duplicate or unsupported graph domain')
    return frozenset(result)


def _masks(value, *, source=False, preserve=0):
    fields = ('input_mask', 'output_mask', 'preserve_mask') if source else ('input_mask', 'output_mask')
    _shape(value, fields, where='CPU contract')
    for name in fields:
        _exact(value[name], preserve if name == 'preserve_mask' else 0x7ff, name)


def normalize_guest_contract(spec, *, corpus=None):
    """Validate a complete version-1 singleton manifest and return frozen data.

    The caller may supply corpus index data to the whole-body resolver, never
    executable bytes or a substitute reference hash. General manifest schema
    validation remains the caller's responsibility; all guest-bearing objects
    and their dependency signatures are checked here without authority defaults.
    """
    if type(spec) is not dict:
        _fail('manifest must be an object')
    _exact(spec.get('abi'), 'canonical', 'ABI')
    if 'program' in spec:
        _exact(spec['program'], 'claw-v1.0', 'program')
    oracle = spec.get('oracle')
    if type(oracle) is not dict or 'guest_graph' not in oracle:
        _fail('explicit oracle.guest_graph is required')
    _exact(oracle.get('kind'), 'clawparity', 'oracle kind')
    if type(oracle.get('entry')) is not str or not _SYMBOL.fullmatch(oracle['entry']):
        _fail('public root requires an explicit native C export')
    graph = _shape(oracle['guest_graph'], ('version', 'allowed_handlers', 'factory_call_site',
        'allowed_factories', 'required_outcomes', 'require_native_attached_entries'), where='guest_graph')
    _exact(graph['version'], 1, 'guest graph version')
    _exact(graph['require_native_attached_entries'], True, 'native attached obligation')
    handlers = _addresses(graph['allowed_handlers'], _HANDLERS, 'allowed handlers')
    factories = _addresses(graph['allowed_factories'], _FACTORIES, 'allowed factories')
    factory_site = _address(graph['factory_call_site'])
    _exact(factory_site, 0x50344d, 'factory call site')
    outcomes = graph['required_outcomes']
    if type(outcomes) is not list or len(outcomes) != 2 or any(type(v) is not str for v in outcomes) or set(outcomes) != {'returned', 'unhandled'}:
        _fail('required outcomes must explicitly contain returned and unhandled once each')
    owned = spec.get('owned')
    if type(owned) is not list or len(owned) != 1:
        _fail('bounded guest graph requires exactly one owned root')
    root = _shape(owned[0], ('address', 'convention', 'argc', 'returns', 'source_context',
        'body_ranges', 'attached_entries'), ('name', 'confidence'), where='owned root')
    _exact(_address(root['address']), _ROOT, 'singleton root')
    for name, value in (('convention', 'thiscall'), ('argc', 1), ('returns', 'u32')):
        _exact(root[name], value, name)
    _masks(root['source_context'], source=True)
    attached = root['attached_entries']
    if type(attached) is not list or len(attached) != 1:
        _fail('exactly one explicitly attached native funclet is required')
    route = _shape(attached[0], ('address', 'kind', 'native_entry', 'handler', 'func_info',
        'handler_table', 'call_site', 'return_pc', 'frame_delta_ebp', 'cpu', 'normal_return'), where='attached entry')
    _exact(route['kind'], 'eh-funclet', 'attached kind')
    _exact(route['normal_return'], False, 'funclet completion')
    _exact(route['frame_delta_ebp'], 12, 'parent frame')
    _masks(route['cpu'])
    if type(route['native_entry']) is not str or not _SYMBOL.fullmatch(route['native_entry']):
        _fail('native funclet export must be an explicit C identifier')
    if route['native_entry'] == oracle.get('entry'):
        _fail('native funclet export must differ from public root export')
    addresses = {name: _address(route[name]) for name in
                 ('address', 'handler', 'func_info', 'handler_table', 'call_site', 'return_pc')}
    for name, expected in zip(addresses, (0x503454, 0x508bf8, 0x51ebc0, 0x51ec08, 0x4a8f25, 0x4a8f27)):
        _exact(addresses[name], expected, name)
    try:
        ranges = resolve_owned_ranges(spec, corpus=corpus)
    except (ValueError, OSError, ImportError) as error:
        raise GuestContractError(f'invalid whole ownership: {error}') from error
    if ranges != {_ROOT: [(0x503420, 0x50348b)]}:
        _fail('whole singleton ownership must include all 107 bytes and its attached catch')

    callees = spec.get('callees')
    if type(callees) is not dict:
        _fail('callees must be an object')
    dependencies = {}
    for key, declaration in callees.items():
        address = _address(key)
        if address in dependencies or type(declaration) is not dict:
            _fail('duplicate dependency address or malformed declaration')
        dependencies[address] = declaration
        if any(lo <= address < hi for lo, hi in ranges[_ROOT]):
            _fail('owned code cannot also be declared as an outside dependency')
    required = _DEPENDENCIES
    normalized_dependencies = []
    for address, (convention, argc, returns, preserve) in sorted(required.items()):
        context = 'compiler_context' if convention == 'compiler-context' else 'source_context'
        d = _shape(dependencies.get(address), ('kind', 'convention', 'argc', 'returns', context),
                   ('name',), where=f'original dependency {address:#x}')
        for name, expected in (('kind', 'whole'), ('convention', convention), ('argc', argc), ('returns', returns)):
            _exact(d[name], expected, f'{address:#x} {name}')
        _masks(d[context], source=context == 'source_context', preserve=preserve)
        normalized_dependencies.append(GuestDependency(address, convention, argc, returns, context,
            d[context]['input_mask'], d[context]['output_mask'], d[context].get('preserve_mask')))
    services = []
    for address, name in _SERVICES.items():
        d = _shape(dependencies.get(address), ('kind', 'name', 'convention', 'argc', 'arguments', 'returns', 'reason'),
                   where=f'guest service {name}')
        for key, expected in (('kind', 'guest-service'), ('name', name), ('convention', 'stdcall'),
                              ('argc', 4), ('arguments', ['u32'] * 4), ('returns', 'void')):
            _exact(d[key], expected, f'{name} {key}')
        if type(d['reason']) is not str or not d['reason'].strip():
            _fail('guest service requires a nonempty reason')
        services.append(GuestService(address, name, 'stdcall', 4, ('u32',) * 4, 'void'))
    for address, d in dependencies.items():
        if address not in required and address not in _SERVICES and d.get('kind') != 'fixture':
            _fail('additional original targets or guest services are outside this bounded graph')
        if address in handlers:
            _fail('original exception handlers cannot be replaced by outside declarations')
        if d.get('kind') == 'fixture':
            _shape(d, ('kind', 'name', 'convention', 'argc', 'arguments', 'returns', 'fixture', 'reason'),
                   where='physical fixture declaration')
            if (type(d['argc']) is not int or not 0 <= d['argc'] <= CALL_ARGUMENT_CAPACITY or
                    type(d['arguments']) is not list or len(d['arguments']) != d['argc'] or
                    any(type(v) is not str for v in d['arguments'])):
                _fail('malformed physical fixture signature')
            for name in ('name', 'convention', 'returns', 'fixture', 'reason'):
                if type(d[name]) is not str or not d[name].strip():
                    _fail('physical fixture fields require explicit nonempty text')

    program = claw()  # Always recheck the complete original file hash.
    if program.sha256 != CLAW_SHA256:
        _fail('reference hash changed')
    def read(address, count):
        section = next((s for s in program.sections if s.address <= address < address + count <= s.address + len(s.data)), None)
        if section is None:
            _fail('immutable metadata must be backed by pinned original bytes')
        return bytes(section.data[address - section.address:address - section.address + count])
    for address in handlers | factories:
        if not program.in_text(address):
            _fail('handler or factory is not original executable code')
    for address, name in _SERVICES.items():
        if program.imports.get(address, '').lower() != f'kernel32.dll!{name}'.lower():
            _fail('guest service does not identify the pinned physical import')
    for address, d in dependencies.items():
        if d.get('kind') == 'fixture' and address not in program.imports:
            _fail('guest graph fixtures must be original physical import slots')

    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86_const import X86_INS_CALL, X86_INS_MOV, X86_INS_JMP, X86_OP_REG, X86_OP_MEM, X86_OP_IMM, X86_REG_EAX, X86_REG_EBP
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    def instruction(address):
        ins = next(decoder.disasm(read(address, 15), address), None)
        if ins is None:
            _fail('missing original instruction')
        return ins
    factory_call, catch_call = instruction(factory_site), instruction(addresses['call_site'])
    if (factory_call.id != X86_INS_CALL or factory_call.size != 3 or len(factory_call.operands) != 1 or
            factory_call.operands[0].type != X86_OP_MEM or factory_call.operands[0].mem.base != X86_REG_EBP or
            factory_call.operands[0].mem.index or factory_call.operands[0].mem.disp != 8):
        _fail('factory call does not use the original source argument slot')
    if (catch_call.id != X86_INS_CALL or catch_call.size != 2 or len(catch_call.operands) != 1 or
            catch_call.operands[0].type != X86_OP_REG or catch_call.operands[0].reg != X86_REG_EAX or
            catch_call.address + catch_call.size != addresses['return_pc']):
        _fail('funclet invocation is not the pinned original indirect CALL')

    # Freeze original code and each compiler handler's transitive selection
    # tables. Runtime thread/exception records remain mutable graph state.
    immutable = {program.text: read(program.text[0], program.text[1] - program.text[0])}
    def retain(address, count):
        data = read(address, count)
        immutable[(address, address + count)] = data
        return data
    infos = {}
    for handler in handlers:
        first = instruction(handler)
        if (first.id != X86_INS_MOV or len(first.operands) != 2 or first.operands[0].type != X86_OP_REG or
                first.operands[0].reg != X86_REG_EAX or first.operands[1].type != X86_OP_IMM):
            continue
        if instruction(handler + first.size).id != X86_INS_JMP:
            _fail('compiler handler lacks its original dispatch jump')
        info_address = first.operands[1].imm
        info = struct.unpack('<7I', retain(info_address, 28))
        if info[0] != 0x19930520 or not 0 < info[1] <= 64 or info[3] > 32 or info[5:7] != (0, 0):
            _fail('unsupported original compiler exception metadata')
        infos[handler] = (info_address, info)
        retain(info[2], info[1] * 8)
        if not info[3]:
            continue
        tries = retain(info[4], info[3] * 20)
        for offset in range(0, len(tries), 20):
            low, high, catch_high, count, table = struct.unpack_from('<5I', tries, offset)
            if not 0 < count <= 32 or low > high or high >= info[1] or catch_high >= info[1]:
                _fail('unsupported original try/catch map')
            entries = retain(table, count * 16)
            for at in range(0, len(entries), 16):
                _, type_address, _, target = struct.unpack_from('<4I', entries, at)
                if not program.in_text(target):
                    _fail('catch target is not executable')
                if type_address:
                    name = bytearray()
                    for i in range(512):
                        byte = read(type_address + 8 + i, 1)
                        name.extend(byte)
                        if byte == b'\0':
                            break
                    else:
                        _fail('unbounded exception type name')
                    retain(type_address, 8 + len(name))
    if infos.get(addresses['handler'], (None,))[0] != addresses['func_info']:
        _fail('root handler does not identify declared FuncInfo')
    info = infos[addresses['handler']][1]
    if (info[1] != 2 or info[3] != 1 or struct.unpack('<5I', read(info[4], 20)) !=
            (0, 0, 1, 1, addresses['handler_table']) or
            struct.unpack('<4I', read(addresses['handler_table'], 16))[2:] != (0xffffffe8, addresses['address'])):
        _fail('attached catch is not selected by the original root try table')
    entry = AttachedEntry(_ROOT, addresses['address'], route['native_entry'], addresses['handler'],
        addresses['func_info'], addresses['handler_table'], addresses['call_site'], addresses['return_pc'],
        12, 0x7ff, 0x7ff, False)
    return GuestContract(1, _ROOT, tuple(ranges[_ROOT]), entry, handlers, factories, factory_site,
        frozenset(outcomes), True, tuple(services), tuple(normalized_dependencies),
        tuple((low, data) for (low, _), data in sorted(immutable.items())), program.sha256)


def guest_contract_errors(spec):
    """Validate only manifests bearing any part of the explicit guest extension."""
    if type(spec) is not dict:
        return ['manifest must be an object']
    oracle, owned, callees = spec.get('oracle'), spec.get('owned'), spec.get('callees')
    present = (type(oracle) is dict and 'guest_graph' in oracle or
        type(owned) is list and any(type(e) is dict and 'attached_entries' in e for e in owned) or
        type(callees) is dict and any(type(d) is dict and d.get('kind') == 'guest-service' for d in callees.values()))
    if not present:
        return []
    try:
        normalize_guest_contract(spec)
    except (ValueError, OSError, ImportError) as error:
        return [f'invalid guest contract: {error}']
    return []
