"""Compare explicit guest outcomes without treating an unwind as an ordinary RET."""


def compare_guest_outcomes(env, native, original, *, expected, expected_return_sp):
    if expected not in ('returned', 'unhandled', 'halt'):
        return {'kind':'guest-outcome','detail':'unsupported expected guest outcome'}
    if native.kind != expected or original.kind != expected:
        return {'kind':'guest-outcome','detail':f'expected {expected}; native={native.kind}, original={original.kind}'}
    if native.side.errors or original.side.errors:
        # Physical Halt is an explicit expected stop, not arbitrary failure.
        from .env import Halt
        errors=[e for side in (native.side,original.side) for e in side.errors
                if expected != 'halt' or not isinstance(e,Halt)]
        if errors:
            return {'kind':'guest-state','detail':'; '.join(f'{type(e).__name__}: {e}' for e in errors)}
    permitted_fault=2 if expected=='halt' else 0
    if native.side.fault != permitted_fault or original.side.fault != permitted_fault:
        return {'kind':'guest-state','detail':'guest outcome carries an unexpected fault'}
    if (native.terminal_cpu is None or original.terminal_cpu is None or
            native.terminal_stack is None or original.terminal_stack is None):
        return {'kind':'guest-state','detail':'terminal guest state is unavailable'}
    if native.terminal_cpu != original.terminal_cpu:
        return {'kind':'guest-state','detail':'terminal CPU/FS differs'}
    if native.terminal_stack != original.terminal_stack:
        return {'kind':'stack','detail':'terminal guest stack differs'}
    if native.terminal_state is None or original.terminal_state is None:
        return {'kind':'guest-state','detail':'terminal ownership state is unavailable'}
    for field in ('allocator_cursor','names','spans','freed'):
        if getattr(native.terminal_state,field) != getattr(original.terminal_state,field):
            return {'kind':'guest-state','detail':f'terminal ownership {field} differs'}
    if native.side.fault_address != original.side.fault_address:
        return {'kind':'guest-state','detail':'fault address differs'}
    for field in ('events','heap','image','spans','freed'):
        if getattr(native.side,field) != getattr(original.side,field):
            return {'kind':'guest-state','detail':f'terminal {field} differs'}
    if len(native.transfers) != len(original.transfers):
        return {'kind':'guest-state','detail':'physical transfer count differs'}
    fields=('event','cpu','stack','heap','image_data','spans','freed','allocator_cursor','names','events')
    for index,(ours,theirs) in enumerate(zip(native.transfers,original.transfers)):
        for field in fields:
            if getattr(ours,field) != getattr(theirs,field):
                return {'kind':'guest-state','detail':f'physical transfer {index} {field} differs'}
    if expected=='halt':
        if not native.side.halted or not original.side.halted or native.side.completed or original.side.completed:
            return {'kind':'guest-outcome','detail':'physical Halt flags disagree'}
        return None
    if native.result is None or original.result is None:
        return {'kind':'guest-outcome','detail':'missing terminal guest result'}
    for outcome in (native,original):
        if (outcome.result.kind != expected or
                outcome.result.stack_pointer != outcome.terminal_cpu.values[7]):
            return {'kind':'guest-state','detail':'terminal result disagrees with outcome or CPU stack'}
    if native.result.transitions != original.result.transitions:
        return {'kind':'guest-state','detail':'exception transition sequence differs'}
    if expected=='unhandled':
        if native.side.completed or original.side.completed or native.side.halted or original.side.halted:
            return {'kind':'guest-outcome','detail':'unhandled outcome carries ordinary completion or Halt'}
        if native.result.exception is None or original.result.exception is None:
            return {'kind':'guest-state','detail':'missing terminal exception record'}
        if native.result.exception != original.result.exception:
            return {'kind':'guest-state','detail':'terminal exception record differs'}
        return None
    if (not native.side.completed or not original.side.completed or
            native.side.halted or original.side.halted):
        return {'kind':'guest-outcome','detail':'returned outcome did not complete'}
    if original.terminal_cpu.values[7] != expected_return_sp:
        return {'kind':'specification','detail':'ordinary source return stack disagrees with its declared ABI'}
    if native.side.eax != original.side.eax:
        return {'kind':'return-value','detail':'guest return value differs'}
    if any(outcome.result.eax != outcome.side.eax or outcome.result.eax != outcome.terminal_cpu.values[0]
           for outcome in (native,original)):
        return {'kind':'return-value','detail':'returned result, side and terminal CPU disagree'}
    return None
