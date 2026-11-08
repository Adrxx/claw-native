"""Independent inputs derived from the original ambient-audio instructions."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

CLOCK = 0x546DF0


def initialized_thread(tls_index, prior_errno, last_error, voice=False):
    """Physical thread services only; the overflow arithmetic stays original."""
    def setup(env):
        tokens = setup_voice(volume=0x80000000)(env) if voice else {}
        thread = env.object(0x74, 'initialized CRT thread storage', fill=0)
        observations = env.object(0x200, 'thread service observations', fill=0)
        state = env.object(4, 'physical last error', words=[last_error])
        env.put(thread + 8, prior_errno)
        env.put(0x52EDD8, tls_index)

        def record(env, call, service):
            index = env.get(observations)
            env.put(observations + 4 + index * 28, service, call.receiver,
                    len(call.arguments), call.arguments[0] if call.arguments else 0,
                    env.get(thread + 8), env.get(state), env.get(0x52EDD8))
            env.put(observations, index + 1)

        def get_last_error(env, call):
            record(env, call, 1)
            return env.get(state)

        def tls_get_value(env, call):
            record(env, call, 2)
            env.put(state, 0)  # Successful Win32 lookup clears last error.
            return thread

        def set_last_error(env, call):
            record(env, call, 3)
            env.put(state, call.arguments[0])

        env.override(0x546B0C, get_last_error)
        env.override(0x546A7C, tls_get_value)
        env.override(0x546AB8, set_last_error)
        tokens.update(thread=thread, thread_observations=observations)
        return tokens
    return setup


def setup_voice(enabled=1, errors=None, status=1, volume=-1600, base=22050,
                mutate=None, beep=0):
    errors = {} if errors is None else errors

    def setup(env):
        manager = env.object(0x80, 'manager', fill=0x69)
        voice = env.object(0x28, 'voice', fill=0xA6)
        interface = env.object(4, 'DirectSound buffer')
        methods = env.object(0x4C, 'DirectSound methods', fill=0)
        log = env.object(0x400, 'physical callback observations', fill=0)
        env.put(manager + 0x0C, 0, 0)
        env.put(manager + 0x78, enabled, 17)
        env.put(voice + 0x0C, interface, manager, 0xCAFE0102, base)
        env.put(voice + 0x24, 0x98765432)
        env.put(interface, methods)
        for index in range(101):
            env.put(0x541178 + index * 4, (0xFFF00001 + index * 37) & 0xFFFFFFFF)
        for index in range(9):
            env.put(0x541308 - index * 4, 0x80001001 + index * 131)
        env.put(0x54130C, 0, 0, beep, 0)
        tokens = dict(voice=voice, manager=manager, interface=interface, log=log)

        def method(name, argc):
            def effect(env, call):
                count = env.get(log)
                at = log + 4 + count * 28
                env.put(at, call.receiver, len(call.arguments), *call.arguments)
                env.put(at + 24, env.get(voice + 0x14))
                env.put(log, count + 1)
                if name in ('status', 'get-volume'):
                    pointer = call.arguments[1]
                    # Observe the stack output's initial contents as well as its address.
                    env.put(at + 20, env.get(pointer))
                    value = status if name == 'status' else volume
                    env.put(pointer, value & 0xFFFFFFFF)
                if mutate is not None:
                    mutate(env, tokens, name)
                return errors.get(name, 0)
            return env.stub('physical DirectSound ' + name, 'stdcall', argc, effect)

        for offset, name, argc in ((0x30, 'play', 4), (0x48, 'stop', 1),
                                   (0x24, 'status', 2), (0x18, 'get-volume', 2),
                                   (0x3C, 'volume', 2), (0x40, 'pan', 2),
                                   (0x44, 'frequency', 2)):
            env.put(methods + offset, method(name, argc))

        def clock(env, call):
            env.put(log + 0x3E0, env.get(manager + 0x0C), env.get(manager + 0x7C))
            return 73
        env.override(CLOCK, clock)
        return tokens
    return setup


def voice_case(label, address, args=(), **options):
    return Case(label, address, setup_voice(**options),
                receiver=lambda t: t['voice'], arguments=args)


def fade_setup(status=1, stop=0, initial=17, target=63, duration=23,
               start=50, errors=None, mutate_fields=False, real_list=False):
    def setup(env):
        holder = {}

        def mutate(env, tokens, name):
            if name == 'status' and mutate_fields:
                env.put(holder['fade'] + 0x14, 0, 39, 11, 29)
        t = setup_voice(status=status, errors=errors, mutate=mutate)(env)
        fade = env.object(0x28, 'real fade node', fill=0xC3)
        holder['fade'] = fade
        env.put(fade, 0x513520, 0, 0, 1, t['voice'], stop,
                target, initial, duration, start)
        t['fade'] = fade
        if real_list:
            env.put(t['manager'] + 0x0C, fade + 4, fade + 4)
        return t
    return setup


def list_setup(count=0, results=(), now=73, last=17, types=None,
               voices=None, mutation=False):
    def setup(env):
        t = setup_voice()(env)
        manager, log = t['manager'], t['log']
        env.put(manager + 0x7C, last)
        nodes = [env.object(0x28, 'synthetic node %d' % n, fill=0x40+n)
                 for n in range(count)]
        table = env.object(8, 'synthetic node callback table')

        def record(env, call, stopping):
            n = env.get(log)
            at = log + 4 + n * 28
            env.put(at, call.receiver, env.get(manager + 0x0C),
                    env.get(manager + 0x10), env.get(manager + 0x7C),
                    call.arguments[0] if call.arguments else 0xDEAD1234,
                    env.get(call.receiver + 4), env.get(call.receiver + 8))
            env.put(log, n + 1)
            index = nodes.index(call.receiver)
            if mutation:
                env.put(manager + 0x7C, 0xFFFFFFFE)
                # The cached next must still be traversed even after this edit.
                if index == 0:
                    env.put(call.receiver + 4, 0)
            return 0x92345678 if stopping else results[index]
        env.put(table, env.stub('synthetic generic node update', 'thiscall', 1,
                                lambda e, c: record(e, c, False)),
                env.stub('synthetic generic node stop', 'thiscall', 0,
                         lambda e, c: record(e, c, True)))
        for index, node in enumerate(nodes):
            env.put(node, table, nodes[index+1]+4 if index+1<count else 0,
                    nodes[index-1]+4 if index else 0,
                    types[index] if types else 1,
                    voices[index] if voices else t['voice'])
        env.put(manager + 0x0C, nodes[0]+4 if nodes else 0,
                nodes[-1]+4 if nodes else 0)
        env.override(CLOCK, lambda e, c: now)
        t.update(nodes=nodes, list=manager+0x0C)
        return t
    return setup


def cases(random_source):
    # Signed division by 100 happens before exponent construction.
    for value in (0, 1, -1, 99, -99, 100, -100, 101, -101, 199, -199,
                  200, -200, 999, -999, 1000, -1000, 10000, -10000,
                  100000, -100000, 2147483647, -2147483647):
        yield Case('volume inverse quotient/sign %d' % value, 0x4B3BF0,
                   arguments=(value & 0xFFFFFFFF,))
    for _ in range(12):
        value = random_source.randrange(-20000, 20001)
        yield Case('random inverse %d' % value, 0x4B3BF0,
                   arguments=(value & 0xFFFFFFFF,))
    for address, args in ((0x4B3D80, ()), (0x4B3DC0, (19, 3, 7, 1)),
                          (0x4B3E30, ()), (0x4B3E70, ()), (0x4B3EC0, (1,)),
                          (0x4B3EF0, (0xFFFFD817,)), (0x4B3F40, (19,)),
                          (0x4B3F70, ()), (0x4B3FC0, ()),
                          (0x4B3FE0, (19, 7, 1)), (0x4B40C0, (0xFFFFD151,)),
                          (0x4B4110, (3,)), (0x4B4160, (55123,)),
                          (0x4B41B0, (7,))):
        yield voice_case('disabled guard %x' % address, address, args, enabled=0)
        yield voice_case('enabled %x' % address, address, args)
    for address, args, name in ((0x4B3D80, (), 'play'), (0x4B3E30, (), 'stop'),
                                (0x4B3E70, (), 'status'),
                                (0x4B3EF0, (0x87654321,), 'volume'),
                                (0x4B3F70, (), 'get-volume'),
                                (0x4B40C0, (0x11223344,), 'pan'),
                                (0x4B4160, (0x55667788,), 'frequency')):
        for error in (1, 0x80004005, 0xFFFFFFFF):
            yield voice_case('COM failure %s %x' % (name,error), address,
                             args, errors={name:error}, beep=1)
    for status in (0, 2, 3, 0x80000000, 0xFFFFFFFF):
        yield voice_case('status low bit %x' % status, 0x4B3E70, status=status)
    for volume in (0, 1, 0x87654321, -99, -100, -1600):
        yield voice_case('getter full output %d' % volume, 0x4B3F70, volume=volume)
    yield voice_case('failed getter still inverse-converts zero', 0x4B3FC0,
                     errors={'get-volume':0x80004005})
    for loop in (0, 1, 0x80000000, 0xFFFFFFFF):
        yield voice_case('loop preserves other flags %x' % loop, 0x4B3EC0, (loop,))
    for pan in (-8,-3,-1,0,1,3,8):
        yield voice_case('centered pan %d' % pan, 0x4B4110, (pan & 0xFFFFFFFF,))
    for index in (0,1,17,73,99,100):
        yield voice_case('table volume %d' % index, 0x4B3F40, (index,))
    for base, adjustment in ((0,0),(100,0),(101,0),(99999,0),(100000,0),
                             (22050,-101),(22050,-100),(22050,-99),
                             (22050,333),(0x7FFFFFFF,2),(0xFFFFFFFF,1),
                             (0x80000000,0xFFFFFFFF)):
        yield voice_case('frequency wrapping %x %d' % (base,adjustment),
                         0x4B41B0, (adjustment & 0xFFFFFFFF,), base=base)
    for name in ('volume','pan','frequency','play'):
        yield voice_case('aggregate continues after '+name,0x4B3DC0,
                         (27,0xFFFFFFFD,31,0),errors={name:0x80004005})
    yield voice_case('aggregate all failures',0x4B3DC0,(27,3,31,1),
                     errors={n:1 for n in ('volume','pan','frequency','play')})

    def disable_after_volume(env,t,name):
        if name == 'volume':
            env.put(t['manager']+0x78,0)
    yield voice_case('aggregate rechecks enable after callback',0x4B3DC0,
                     (19,3,7,1),mutate=disable_after_volume)
    def frequency_mutation(env,t,name):
        if name == 'frequency':
            env.put(t['voice']+0x24,0x13579BDF)
            env.put(t['voice']+0x18,0x2468ACE0)
    yield voice_case('frequency stores saved argument after callback',0x4B4160,
                     (54321,),mutate=frequency_mutation)
    for duration in (0,1,29):
        for failure in (False,True):
            def setup(env,duration=duration,failure=failure):
                t=setup_voice(errors={'volume':1} if duration==0 else {})(env)
                if failure:
                    env.override(0x4F63EC,allocate(fail=True))
                return t
            yield Case('start fade duration %d allocation fail %s'%(duration,failure),
                       0x4B3FE0,setup,receiver=lambda t:t['voice'],
                       arguments=(31,duration,0x80000000))
    for stop in (0,1,0x80000000):
        for status in (0,1,2,3):
            for tick in (50,51,72,73,74,0xFFFFFFFF):
                yield Case('fade update %x status %d stop %x'%(tick,status,stop),
                           0x4B4D80,fade_setup(status=status,stop=stop),
                           receiver=lambda t:t['fade'],arguments=(tick,))
            yield Case('fade finalizer status %d stop %x'%(status,stop),0x4B4DF0,
                       fade_setup(status=status,stop=stop,errors={'stop':1,'volume':1}),
                       receiver=lambda t:t['fade'])
    for target,initial in ((7,83),(100,0),(0,100),(39,39)):
        yield Case('descending/equal interpolation %d %d'%(target,initial),0x4B4D80,
                   fade_setup(target=target,initial=initial),receiver=lambda t:t['fade'],
                   arguments=(61,))
    yield Case('fade wraps elapsed tick',0x4B4D80,fade_setup(start=0xFFFFFFF0),
               receiver=lambda t:t['fade'],arguments=(3,))
    for address,args in ((0x4B4D80,(61,)),(0x4B4DF0,())):
        yield Case('fade reloads fields after status %x'%address,address,
                   fade_setup(stop=1,mutate_fields=True),receiver=lambda t:t['fade'],
                   arguments=args)
    def constructor(env):
        t=setup_voice()(env)
        t['fade']=env.object(0x28,'constructor receiver',fill=0xD7)
        def clock(env,call):
            env.write(t['log']+0x200,env.read(t['fade'],0x28))
            return 0xFFFFFFE1
        env.override(CLOCK,clock)
        return t
    yield Case('constructor publishes fields before clock',0x4B4D00,constructor,
               receiver=lambda t:t['fade'],arguments=(73,19,0x80000001,
                                                        lambda t:t['voice'],0x12345678))
    for address in (0x4B4B80,0x4B4C10):
        yield Case('empty manager %x'%address,address,list_setup(),
                   receiver=lambda t:t['manager'])
        for results in ((1,),(0,),(1,0,0x80000000),(0,0,0)):
            yield Case('synthetic traversal %x %s'%(address,results),address,
                       list_setup(len(results),results),receiver=lambda t:t['manager'])
    for now,last in ((17,17),(16,17),(0,0xFFFFFFFF),(0xFFFFFFFF,0x80000000)):
        yield Case('unsigned manager clock %x %x'%(now,last),0x4B4B80,
                   list_setup(2,(1,1),now=now,last=last),receiver=lambda t:t['manager'])
    yield Case('cached next and captured clock survive synthetic callback',0x4B4B80,
               list_setup(3,(1,1,1),mutation=True),receiver=lambda t:t['manager'])
    for address in (0x4B4B80,0x4B4C10):
        for stop in (0,1):
            yield Case('real fade vtable dispatched through manager %x stop %d'%(address,stop),
                       address,fade_setup(stop=stop,real_list=True),receiver=lambda t:t['manager'])
    for wildcard in (False,True):
        for voices in ((0x11223344,)*3,(0x11223344,0x55667788,0x11223344)):
            yield Case('filter matching type/wildcard %s voices %s'%(wildcard,voices),
                       0x4B4C80,list_setup(3,(1,1,1),types=(1,2,3) if wildcard else (1,1,1),
                                           voices=voices),receiver=lambda t:t['list'],
                       arguments=(0x11223344,0xFFFF if wildcard else 1))
    yield Case('filter empty',0x4B4C80,list_setup(),receiver=lambda t:t['list'],
               arguments=(0x11223344,1))
    for count in (0,1,3):
        def insertion(env,count=count):
            t=list_setup(count,(1,)*count)(env)
            t['link']=env.object(8,'incoming distinct link',words=[0x11223344,0x55667788])
            return t
        yield Case('insert head count %d'%count,0x4B5210,insertion,
                   receiver=lambda t:t['list'],arguments=(lambda t:t['link'],))
    for count,index in ((1,0),(3,0),(3,1),(3,2)):
        yield Case('unlink count %d index %d'%(count,index),0x4B5270,
                   list_setup(count,(1,)*count),receiver=lambda t:t['list'],
                   arguments=(lambda t,index=index:t['nodes'][index]+4,))
    # All alias addresses remain backed; these are deliberate reread-order probes.
    for address in (0x4B5210,0x4B5270):
        def aliases(env):
            block=env.object(32,'aliased list/link backing',fill=0)
            env.put(block,block+8,block+8,0,0,0x12345678,0x87654321)
            return dict(list=block,link=block)
        yield Case('list receiver aliases incoming link %x'%address,address,aliases,
                   receiver=lambda t:t['list'],arguments=(lambda t:t['link'],))
    for scale, one, divisor, power_base in ((127.5,1.0,10.0,2.0),
                                             (100.0,1.125,10.0,2.0),
                                             (100.0,1.0,7.0,2.0),
                                             (100.0,1.0,10.0,4.0),
                                             (31.25,0.75,13.0,0.5)):
        def constants(env,scale=scale,one=one,divisor=divisor,power_base=power_base):
            env.write(0x5134E8,struct.pack('<dddd',scale,one,divisor,power_base))
        for value in (-1379,1379):
            yield Case('inverse reads constants %s %d'%((scale,one,divisor,power_base),value),
                       0x4B3BF0,constants,arguments=(value & 0xFFFFFFFF,))
    # Wrapped NEG leaves INT_MIN negative. Original CRT overflow handling uses
    # the existing TLS object and restores the captured physical last error.
    for tls_index, prior_errno, last_error in ((0,0,0), (7,33,123),
                                              (0xFFFFFFFF,0x87654321,0xFFFFFFFF),
                                              (31,34,0x80000000)):
        yield Case('INT_MIN original overflow TLS %x errno %x error %x' %
                   (tls_index,prior_errno,last_error), 0x4B3BF0,
                   initialized_thread(tls_index,prior_errno,last_error),
                   arguments=(0x80000000,))
    for _ in range(4):
        tls_index = random_source.randrange(0,64)
        prior_errno = random_source.getrandbits(32)
        last_error = random_source.getrandbits(32)
        yield Case('random INT_MIN thread state %x %x %x' %
                   (tls_index,prior_errno,last_error), 0x4B3BF0,
                   initialized_thread(tls_index,prior_errno,last_error),
                   arguments=(0x80000000,))
    yield Case('getter INT_MIN reaches original overflow thread services',
               0x4B3FC0, initialized_thread(19,0xA5A5A5A5,0x13579BDF,voice=True),
               receiver=lambda t:t['voice'])
    # These constants keep pow in its normal positive-base domain. In the
    # DBL_MAX case the owned multiplication exceeds binary64 while remaining
    # finite in x87, before subtraction and the explicit binary64 store.
    for label, scale, one, divisor, power_base in (
            ('finite extended multiplication overflow', float.fromhex('0x1.fffffffffffffp+1023'),2.0,10.0,2.0),
            ('negative extended multiplication overflow', -float.fromhex('0x1.fffffffffffffp+1023'),2.0,10.0,2.0),
            ('near-one cancellation', 100.0,float.fromhex('0x1.0000000000001p+0'),10.0,1.0),
            ('subnormal scale', float.fromhex('0x0.0000000000001p-1022'),1.0,10.0,2.0),
            ('minimum normal scale', float.fromhex('0x1p-1022'),2.0,10.0,2.0),
            ('negative scale', -127.5,1.125,7.0,4.0),
            ('unit base exact cancellation', 8191.75,1.0,3.0,1.0),
            ('negative divisor reverses exponent', 255.5,0.75,-7.0,0.5)):
        def arithmetic_constants(env,scale=scale,one=one,divisor=divisor,power_base=power_base):
            env.write(0x5134E8,struct.pack('<dddd',scale,one,divisor,power_base))
        for value in (-100,100):
            yield Case('inverse %s sign %d'%(label,value),0x4B3BF0,
                       arithmetic_constants,arguments=(value & 0xFFFFFFFF,))
    def start_reloads_manager(env):
        t=setup_voice(volume=0)(env)
        replacement=env.object(0x80,'manager published by physical clock',fill=0x57)
        env.put(replacement+0x0C,0,0)
        env.put(replacement+0x78,1,29)
        old=env.object(0x28,'old matching fade removed before allocation',fill=0x83)
        env.put(old,0x513520,0,0,1,t['voice'],0,61,23,19,7)
        env.put(t['manager']+0x0C,old+4,old+4)
        def clock(env,call):
            env.put(t['voice']+0x10,replacement)
            return 0xFEDCBA98
        env.override(CLOCK,clock)
        return t
    yield Case('fade removes previous node and rereads manager after constructor clock',
               0x4B3FE0,start_reloads_manager,receiver=lambda t:t['voice'],
               arguments=(67,83,0))
