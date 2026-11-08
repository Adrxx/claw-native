"""Required evidence for the currently bounded whole-singleton guest family."""
def evidence_errors(evidence, *, require_native=True):
    if type(evidence) is not dict:
        return ['missing guest graph evidence']
    errors=[]
    outcomes=evidence.get('outcomes')
    if (type(outcomes) is not dict or
            any(type(outcomes.get(kind)) is not int or outcomes[kind]<=0 for kind in ('returned','unhandled'))):
        errors.append('guest cases must cover returned and unhandled outcomes')
    if evidence.get('policy_verified') is not True:
        errors.append('guest immutable metadata and factory policy was not enforced')
    factories=evidence.get('factory_outcomes')
    for factory in ('0x502369','0x502bde','0x502c0f'):
        counts=factories.get(factory) if type(factories) is dict else None
        if (type(counts) is not dict or
                any(type(counts.get(kind)) is not int or counts[kind]<=0 for kind in ('returned','unhandled'))):
            errors.append(f'original factory {factory} must execute on returned and unhandled paths')
    catches=evidence.get('original_catch_cases')
    if type(catches) is not int or catches<=0:
        errors.append('original reachable catch was not exercised')
    elif type(outcomes) is dict and catches!=outcomes.get('unhandled'):
        errors.append('every unhandled case must exercise the original catch')
    if require_native:
        invocations=evidence.get('native_attached_invocations')
        if type(invocations) is not int or invocations<=0:
            errors.append('native attached catch was not invoked')
        elif type(outcomes) is dict and invocations!=outcomes.get('unhandled'):
            errors.append('every unhandled case must invoke its native catch exactly once')
        if evidence.get('ownership_guard')!='stop-before-execution' or evidence.get('owned_ranges_guarded')!=[[0x503420,0x50348b]]:
            errors.append('complete original singleton body was not guarded on the native side')
    return errors
