"""Whole-family guest comparison; source-only, never app acceptance."""
import ctypes as C
from dataclasses import replace
from .env import NativeSourceContext, HarnessError
from .guest_adapter import GuestFuncletRoute, GuestGraph, run_native_guest_graph
from .guest_reference import run_original_guest_source
from .guest_compare import compare_guest_outcomes


def run_case(env, entry, library, plan, case, receiver, receiver2, arguments, source, source_pc,
             *, flavor, original_only):
    if type(source) is not NativeSourceContext or case.compare_eax is not None:
        raise HarnessError('guest case requires explicit complete source state and declared comparisons')
    expected={'return':'returned','unhandled':'unhandled','halt':'halt'}.get(case.expect)
    if expected is None:
        raise HarnessError('guest case requires return, unhandled or physical halt expectation')
    if case.function!=plan.root or len(arguments)!=1 or arguments[0] not in plan.allowed_factories:
        raise HarnessError('guest case root or factory is outside the normalized original contract')
    original_source=NativeSourceContext.from_buffer_copy(source)
    native=None
    if not original_only:
        route=plan.attached_entry
        graph=GuestGraph(allowed_handlers=plan.allowed_handlers,owned_ranges=plan.owned_ranges,
            funclet=GuestFuncletRoute(owner_entry=route.owner_entry,entry_pc=route.entry_pc,
                handler=route.handler,func_info=route.func_info,handler_table=route.handler_table,
                call_site=route.call_site,return_pc=route.return_pc,
                native_entry=getattr(library,route.native_entry)),contract=plan)
        native=run_native_guest_graph(env,entry,plan.root,receiver,arguments,graph=graph,
            source_context=NativeSourceContext.from_buffer_copy(source),source_return_pc=source_pc,
            source_convention='thiscall',receiver2=receiver2,flavor=flavor)
        if native.kind=='fault' and native.side.halted and native.side.fault==2 and native.terminal_cpu is not None:
            native=replace(native,kind='halt')
    original=run_original_guest_source(env,plan.root,receiver,arguments,allowed_handlers=plan.allowed_handlers,
        source_context=original_source,source_return_pc=source_pc,source_convention='thiscall',
        receiver2=receiver2,trace=True,contract=plan,check_objects=original_only)
    if original_only: native=original
    difference=compare_guest_outcomes(env,native,original,expected=expected,expected_return_sp=source.esp+8)
    catch=plan.attached_entry.entry_pc
    original_catch=any(address==catch for address,size in original.coverage)
    invocations=() if original_only else native.invocations
    if difference is None and expected=='unhandled':
        if not original_catch or (not original_only and
                (len(invocations)!=1 or invocations[0].entry_pc!=catch)):
            difference={'kind':'guest-owned-entry','detail':'unhandled case lacks original catch or unique native attached invocation'}
    if difference is None and expected=='returned' and (original_catch or invocations):
        difference={'kind':'guest-owned-entry','detail':'normal singleton return unexpectedly entered its catch'}
    executed_factories=sorted({address for address,size in original.coverage if address in plan.allowed_factories})
    evidence={'outcome':original.kind,'original_catch':int(original_catch),'native_invocations':len(invocations),
              'executed_factories':executed_factories}
    return native.side,original.side,difference,evidence
