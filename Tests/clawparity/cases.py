"""What a test case is.

A family's cases file defines `cases(random_source)` and yields Case objects.
The random source is seeded by the runner: workers and the admission gate use
different seeds, so a case that draws from it is exercised on inputs its author
never saw.
"""
from .abi import CALL_ARGUMENT_CAPACITY

from dataclasses import dataclass


@dataclass
class Case:
    label: str
    function: int                # the owned function to call
    setup: object = None         # setup(env) builds the initial memory and returns anything, usually a dict of tokens
    receiver: object = 0         # ECX: a number, or a function of what setup returned
    arguments: tuple = ()        # stack arguments: numbers, or functions of what setup returned
    compare_eax: object = None   # None follows the family's declared return type
    expect: str = "return"       # return, physical halt, or unhandled for an explicit guest graph
    covers: tuple = ()           # free-text ids of the branches or claims this case targets
    compiler_context: object = None  # NativeCompilerContext or setup-token resolver; special entries only
    source_context: object = None  # NativeSourceContext or setup-token resolver; ordinary capability only
    source_return_pc: object = 0  # genuine source continuation, resolved after setup
    receiver2: object = 0  # EDX only for explicit source fastcall
    initial_stack: object = ()  # (negative entry-ESP offset, bytes) regions, or setup-token resolver
    entry_x87: object = None  # {control, status, slots} or setup-token resolver; owned x87 entries only


def resolve(value, tokens):
    return value(tokens) if callable(value) else value


def compiler_contract_errors(manifest):
    """Validate explicit special entries independently of the schema reader."""
    errors = []
    special = []
    required, all_bits = 0x5c1, 0x7ff
    for owned in manifest.get("owned", []):
        if not isinstance(owned, dict):
            continue
        context = owned.get("compiler_context")
        is_special = owned.get("convention") == "compiler-context"
        special.append(is_special)
        if is_special:
            if (manifest.get("abi") != "canonical" or type(owned.get("argc")) is not int or
                    owned["argc"] != 0 or owned.get("returns") != "context" or
                    not isinstance(context, dict) or set(context) != {"input_mask", "output_mask"}):
                errors.append(f"{owned.get('address')}: compiler-context requires canonical ABI, argc 0, returns context and exact masks")
                continue
            for name, mask in context.items():
                if type(mask) is not int or mask < 0 or mask & ~all_bits or mask & required != required:
                    errors.append(f"{owned.get('address')}: invalid compiler-context {name}")
        elif context is not None or "compiler_context" in owned or owned.get("returns") == "context":
            errors.append(f"{owned.get('address')}: ordinary entry cannot carry compiler context")
    if any(special) and not all(special):
        errors.append("ordinary and compiler-context entries require separate modules")
    for address, callee in manifest.get("callees", {}).items():
        if not isinstance(callee, dict):
            continue
        if callee.get("convention") == "compiler-context" or "compiler_context" in callee:
            candidate = {"abi": manifest.get("abi"), "owned": [{**callee, "address": address}]}
            errors.extend(compiler_contract_errors(candidate))
            if callee.get("kind") != "whole" or "fixture" in callee or "x87_args" in callee:
                errors.append(f"{address}: compiler dependency must execute original instructions, never a fixture")
    for entry in list(manifest.get("owned", [])) + list(manifest.get("callees", {}).values()):
        if not isinstance(entry, dict) or "source_context" not in entry:
            continue
        source = entry['source_context']
        if (manifest.get('abi') != 'canonical' or entry.get('convention') not in ('cdecl', 'stdcall', 'thiscall', 'fastcall') or
                type(entry.get('argc')) is not int or not 0 <= entry['argc'] <= CALL_ARGUMENT_CAPACITY or
                entry.get('returns') not in ('u32', 'void') or 'compiler_context' in entry or 'x87_args' in entry or
                ('kind' in entry and entry['kind'] != 'whole') or not isinstance(source, dict) or
                set(source) not in ({'input_mask', 'output_mask', 'preserve_mask'},
                                    {'input_mask', 'output_mask', 'preserve_mask', 'optional'})):
            errors.append('source_context requires an ordinary canonical signature and exact masks')
            continue
        SOURCE_INPUT_REQUIRED, SOURCE_OUTPUT_REQUIRED, SOURCE_PRESERVABLE = 0x5c0, 0x581, 0x472
        if ('optional' in source and (type(source['optional']) is not bool or
                source['optional'] and entry['convention'] == 'fastcall')):
            errors.append('optional source capability requires boolean selection and an ordinary supported ABI')
            continue
        if any(type(source[key]) is not int or source[key] < 0 or source[key] & ~all_bits
               for key in ('input_mask', 'output_mask', 'preserve_mask')):
            errors.append('source_context masks must be valid uint32 register subsets')
            continue
        im, om, pm = (source[n] for n in ('input_mask', 'output_mask', 'preserve_mask'))
        if (im & SOURCE_INPUT_REQUIRED != SOURCE_INPUT_REQUIRED or om & SOURCE_OUTPUT_REQUIRED != SOURCE_OUTPUT_REQUIRED or
                pm & ~SOURCE_PRESERVABLE or pm & im != pm or pm & om != pm or
                (entry['convention'] in ('thiscall', 'fastcall') and not im & 4) or
                (entry['convention'] == 'fastcall' and not im & 8)):
            errors.append('source_context masks omit required state or include invalid preservation')
    errors.extend(caller_frame_errors(manifest))
    errors.extend(x87_result_errors(manifest))
    errors.extend(x87_environment_errors(manifest))
    return errors


def x87_result_errors(manifest):
    """Owned ordinary entries returning in ST(0): exactly pop 0/push 1 and returns x87."""
    errors = []
    for entry in manifest.get('owned', []):
        if not isinstance(entry, dict) or ('x87_result' not in entry and entry.get('returns') != 'x87'):
            continue
        if (manifest.get('abi') != 'canonical' or entry.get('returns') != 'x87' or
                entry.get('x87_result') != {'pop': 0, 'push': 1} or
                any(type(v) is not int for v in entry['x87_result'].values()) or
                entry.get('convention') not in ('cdecl', 'stdcall', 'thiscall') or
                type(entry.get('argc')) is not int or not 0 <= entry['argc'] <= CALL_ARGUMENT_CAPACITY or
                any(k in entry for k in ('x87_args', 'x87_exact', 'source_context', 'compiler_context',
                                         'attached_entries'))):
            errors.append(f"{entry.get('address')}: x87_result requires an ordinary canonical entry, "
                          "returns x87 and exactly {pop: 0, push: 1}")
    return errors


def x87_environment_errors(manifest):
    """Ordinary owners consuming inherited x87 state, preserving their live stack."""
    errors = []
    for entry in manifest.get('owned', []):
        if not isinstance(entry, dict) or 'x87_environment' not in entry:
            continue
        effect = entry['x87_environment']
        if (manifest.get('abi') != 'canonical' or entry.get('returns') not in ('u32', 'void') or
                not isinstance(effect, dict) or effect != {'pop': 0, 'push': 0} or
                any(type(v) is not int for v in effect.values()) or
                entry.get('convention') not in ('cdecl', 'stdcall', 'thiscall') or
                type(entry.get('argc')) is not int or not 0 <= entry['argc'] <= CALL_ARGUMENT_CAPACITY or
                any(k in entry for k in ('x87_result', 'x87_args', 'x87_exact', 'source_context',
                                         'compiler_context', 'attached_entries')) or
                'guest_graph' in manifest.get('oracle', {})):
            errors.append(f"{entry.get('address')}: x87_environment requires an ordinary canonical u32/void "
                          "owner and exactly {pop: 0, push: 0}, exclusive with other entry capabilities")
    for address, entry in manifest.get('callees', {}).items():
        if isinstance(entry, dict) and 'x87_environment' in entry:
            errors.append(f"{address}: x87_environment is an owned-entry capability only")
    return errors


CALLER_FRAME_BASES = ('receiver', 'entry_esp')


def caller_frame_base(base, argc):
    """('receiver'|'entry_esp', None) or ('argument', N); None when malformed for an entry taking argc words."""
    if not isinstance(base, str):
        return None
    if base in CALLER_FRAME_BASES:
        return base, None
    head, _, index = base.partition(':')
    if head != 'argument' or not index.isdigit() or str(int(index)) != index or int(index) >= argc:
        return None
    return 'argument', int(index)


def caller_frame_errors(manifest):
    """Declared caller EBP for original whole callees: structure only; sites are decoded by Env.caller_frame."""
    errors = []
    owned = {e.get('address'): e for e in manifest.get('owned', []) if isinstance(e, dict)}
    sites = set()
    for address, callee in manifest.get('callees', {}).items():
        if not isinstance(callee, dict) or 'caller_frame' not in callee:
            continue
        declarations = callee['caller_frame']
        if (callee.get('kind') != 'whole' or callee.get('convention') not in ('cdecl', 'stdcall', 'thiscall') or
                type(callee.get('argc')) is not int or not 0 <= callee['argc'] <= CALL_ARGUMENT_CAPACITY or
                any(k in callee for k in ('fixture', 'x87_args', 'x87_exact', 'source_context', 'compiler_context')) or
                manifest.get('abi') != 'canonical'):
            errors.append(f'{address}: caller_frame requires an exclusive original whole ordinary callee with convention and argc')
            continue
        if not isinstance(declarations, list) or not declarations:
            errors.append(f'{address}: caller_frame must be a nonempty list')
            continue
        callers = set()
        for index, item in enumerate(declarations):
            where = f'{address}: caller_frame[{index}]'
            if not isinstance(item, dict) or set(item) != {'caller', 'site', 'ebp'}:
                errors.append(f'{where} requires exactly caller, site and ebp')
                continue
            caller, site, ebp = item['caller'], item['site'], item['ebp']
            entry = owned.get(caller)
            if (entry is None or entry.get('convention') == 'compiler-context' or 'source_context' in entry or
                    entry.get('convention') not in ('cdecl', 'stdcall', 'thiscall', 'fastcall')):
                errors.append(f'{where}: caller {caller!r} must be an owned ordinary entry of this family')
                continue
            if caller in callers:
                errors.append(f'{where}: caller {caller} is declared twice; one site and one EBP rule per caller')
            callers.add(caller)
            if not isinstance(site, str) or not site.startswith('0x') or site in sites:
                errors.append(f'{where}: site must be a unique hexadecimal CALL address')
            sites.add(site)
            if not isinstance(ebp, dict) or set(ebp) != {'base', 'offset'}:
                errors.append(f'{where}: ebp requires exactly base and offset')
                continue
            if caller_frame_base(ebp['base'], entry.get('argc', 0)) is None:
                errors.append(f"{where}: ebp base must be receiver, entry_esp or argument:N below the caller's argc")
            if (type(ebp['offset']) is not int or not -0x80000000 <= ebp['offset'] <= 0xFFFFFFFF or
                    (ebp['base'] == 'receiver' and entry.get('convention') not in ('thiscall', 'fastcall'))):
                errors.append(f'{where}: ebp offset must be a 32-bit integer and receiver needs a thiscall or fastcall caller')
    return errors
