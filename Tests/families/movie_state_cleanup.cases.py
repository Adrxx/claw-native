"""Original-derived movie stop and array cleanup cases."""
from clawparity.cases import Case
from clawparity.fixtures import halt

STOP = 0x4EFD00
CLEANUP = 0x4EFCD0
DELETE = 0x4F6428


def movie(initialized, first, second, status, growth, *, count=3,
          close_result=0, close_effect=False, close_halt=False, release_halt=False):
    def setup(env):
        owner = env.object(0x14C, 'movie-state', fill=0xA7)
        table = env.object(0x58, 'embedded-file-vtable', fill=0xB9)
        data = env.object(max(4, count * 4), 'array-data', fill=0xC3) if count else 0
        replacement = env.object(20, 'replacement-array-data', fill=0xD5)
        observations = env.object(80, 'callback-observations', fill=0xE1)
        env.put(owner, initialized, first, second)
        env.put(owner + 0x124, table)
        env.put(owner + 0x134, status)
        env.put(owner + 0x138, 0x12345678, data, count, count + 2, growth)

        def record(offset, call):
            env.put(observations + offset, call.receiver, len(call.arguments),
                    env.get(owner), env.get(owner + 4), env.get(owner + 8),
                    env.get(owner + 0x134), env.get(owner + 0x13C),
                    env.get(owner + 0x140), env.get(owner + 0x144))

        def close(env, call):
            record(0, call)
            if close_effect:
                # Change every flag and the embedded array behind the caller.
                env.put(owner, 0x89ABCDEF, 0x76543210, 0xFEDCBA98)
                env.put(owner + 0x134, 0x10293847)
                env.put(owner + 0x13C, replacement, 4, 5, 0x96325874)
            if close_halt:
                return halt()(env, call)
            return close_result

        def delete(env, call):
            record(40, call)
            env.put(observations + 76, call.arguments[0])
            if release_halt:
                return halt()(env, call)
            if call.arguments[0]:
                env.release(call.arguments[0])
            # These side effects expose the exact post-release reset stores.
            env.put(owner + 0x13C, replacement, 0x13579BDF, 0x2468ACE0)
            return 0xBADF00D

        env.put(table + 0x54, env.stub('embedded-file-close', 'thiscall', 0, close))
        env.override(DELETE, delete)
        return {'owner': owner}
    return setup


def cases(random_source):
    for entry in (STOP, CLEANUP):
        for initialized, first, second in (
                (0, 0, 0), (0, 0xFFFFFFFF, 0x80000000),
                (1, 0, 0), (1, 1, 0), (1, 0, 1),
                (0x80000000, 0xFFFFFFFF, 0x12345678)):
            yield Case(f'{entry:x} boolean {initialized:x}/{first:x}/{second:x}',
                       entry, movie(initialized, first, second, 0x76543210, 0xABCDEF01),
                       receiver=lambda t: t['owner'])
        for result in (0, 1, 0x80004005, 0xFFFFFFFF):
            yield Case(f'{entry:x} close result {result:x} with effects', entry,
                       movie(1, 0, 0x80000000, 0x87654321, 7,
                             close_result=result, close_effect=True),
                       receiver=lambda t: t['owner'])
        yield Case(f'{entry:x} close halt after effects', entry,
                   movie(1, 9, 0, 0x87654321, 11, close_effect=True, close_halt=True),
                   receiver=lambda t: t['owner'], expect='halt')
    for count in (0, 1, 7):
        for active in (0, 0x80000000):
            yield Case(f'cleanup release halt count {count} active {active:x}', CLEANUP,
                       movie(0xFFFFFFFF, active, 0, 0x18273645, 0xFEDCBA98,
                             count=count, release_halt=True),
                       receiver=lambda t: t['owner'], expect='halt')
            yield Case(f'cleanup array count {count} active {active:x}', CLEANUP,
                       movie(0xFFFFFFFF, active, 0, 0x18273645, 0xFEDCBA98, count=count),
                       receiver=lambda t: t['owner'])
    for index in range(24):
        words = [random_source.randrange(1, 0x100000000) for _ in range(6)]
        for entry in (STOP, CLEANUP):
            yield Case(f'{entry:x} random nonzero flags {index}', entry,
                       movie(*words[:5], count=random_source.randrange(0, 16),
                             close_result=words[5], close_effect=bool(index % 2)),
                       receiver=lambda t: t['owner'])
