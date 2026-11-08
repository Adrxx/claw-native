"""Cases for application_configuration_writes: registry string write, value delete and close.

Every registry import is scripted and logged into surviving heap memory; nothing here
asserts expected behavior, the comparison judges the recorded values."""
from clawparity.cases import Case
from clawparity.fixtures import returns

SET_VALUE = 0x546824
DELETE_VALUE = 0x546820
CLOSE_KEY = 0x546830
WRITE = 0x4B5DF0
DELETE = 0x4B5F80
CLOSE = 0x4B5D70


def text(env, value, name):
    return env.object(len(value) + 1, name, data=value + b"\0")


def record(env, flag=1, handles=(0x11110008, 0x22220009, 0x3333000A, 0x4444000B, 0x5555000C)):
    obj = env.object(540, "configuration", data=bytes((i * 29 + 7) % 256 for i in range(540)))
    env.put(obj, flag)
    env.put(obj + 0x08, *handles[:3])
    env.put(obj + 0x14, handles[3], handles[4])
    return obj


def logging(env, address, size, statuses, bytes_of=None):
    """Script a fixture: log receiver, arguments and strings into a heap object; return scripted statuses."""
    log = env.object(16 * size, "log %#x" % address, fill=0xA5)

    def effect(e, call):
        n = e.calls_so_far(address) - 1
        slot = log + (n % 16) * size
        e.put(slot, call.receiver, *call.arguments)
        if bytes_of:
            e.write(slot + 32, bytes_of(e, call))
        return statuses[min(n, len(statuses) - 1)]

    env.override(address, effect)
    return log


def write_setup(value_name, value, status=0, flag=1, handles=None):
    def setup(env):
        obj = record(env, flag) if handles is None else record(env, flag, handles)
        name = 0 if value_name is None else text(env, value_name, "name")
        data = 0 if value is None else text(env, value, "string")
        logging(env, SET_VALUE, 96, (status,),
                lambda e, c: e.read(c.arguments[4], min(len(e.cstr(c.arguments[4])) + 1, 40)).ljust(24, b"\0")[:24]
                + e.cstr(c.arguments[1])[:30].ljust(31, b"\0") if c.arguments[1] and c.arguments[4] else b"")
        env.override(CLOSE_KEY, returns(0))
        return {"obj": obj, "name": name, "data": data}
    return setup


def write_case(label, value_name, value, **options):
    return Case(label, WRITE, write_setup(value_name, value, **options),
                receiver=lambda t: t["obj"], arguments=(lambda t: t["name"], lambda t: t["data"]))


def delete_setup(value_name, status=0, flag=1):
    def setup(env):
        obj = record(env, flag)
        name = 0 if value_name is None else text(env, value_name, "name")
        logging(env, DELETE_VALUE, 64, (status,),
                lambda e, c: e.cstr(c.arguments[1])[:30].ljust(31, b"\0") if c.arguments[1] else b"")
        env.override(CLOSE_KEY, returns(0))
        return {"obj": obj, "name": name}
    return setup


def delete_case(label, value_name, **options):
    return Case(label, DELETE, delete_setup(value_name, **options),
                receiver=lambda t: t["obj"], arguments=(lambda t: t["name"],))


def close_setup(flag=1, handles=(0x11110008, 0x22220009, 0x3333000A, 0x4444000B, 0x5555000C), statuses=(0,),
                alias=False, change_flag=False):
    def setup(env):
        obj = record(env, flag, handles)
        if alias:
            env.put(obj + 0x14, handles[4])
        logging(env, CLOSE_KEY, 32, statuses,
                lambda e, c: e.read(obj, 32) if obj else b"")
        return {"obj": obj}
    return setup


def close_case(label, **options):
    return Case(label, CLOSE, close_setup(**options), receiver=lambda t: t["obj"])


def cases(random_source):
    # writeString: success, lengths, boundary strings
    for i, (n, v) in enumerate([(b"Language", b"English"), (b"A", b"B"), (b"Path", b"C:\\CLAW\\Data"),
                                (b"Name", b""), (b"X" * 40, b"Y" * 33), (b"Mixed Case_1", b"\x01\x7f\x80\xfe abc")]):
        yield write_case(f"write {i} success", n, v)
    for status in (1, 2, 5, 0x80000000, 0xFFFFFFFF, 234):
        yield write_case(f"write status {status:#x} fails", b"Key", b"Value", status=status)
    yield write_case("write closed object", b"Key", b"Value", flag=0)
    yield write_case("write closed object null name", None, b"Value", flag=0)
    yield write_case("write closed object null string", b"Key", None, flag=0)
    yield write_case("write null name", None, b"Value")
    yield write_case("write null string", b"Key", None)
    yield write_case("write both null", None, None)
    yield write_case("write flag 2 counts as open", b"Key", b"Value", flag=2)
    yield write_case("write flag high bit", b"Key", b"Value", flag=0x80000000)
    for i in range(40):
        yield write_case(
            f"write random {i}",
            bytes(random_source.randrange(33, 127) for _ in range(random_source.randrange(1, 30))),
            bytes(random_source.randrange(1, 256) for _ in range(random_source.randrange(0, 60))),
            status=random_source.choice((0, 0, 1, 5, random_source.randrange(0, 1 << 32))),
            handles=tuple(random_source.randrange(1, 1 << 32) for _ in range(5)))

    # deleteValue
    for i, n in enumerate([b"Language", b"Q", b"Some Longer Value Name 123", b"\x80\xff"]):
        yield delete_case(f"delete {i} success", n)
    for status in (1, 2, 0x80000000, 0xFFFFFFFF):
        yield delete_case(f"delete status {status:#x}", b"Key", status=status)
    yield delete_case("delete null name", None)
    yield delete_case("delete null name closed", None, flag=0)
    yield delete_case("delete closed", b"Key", flag=0)
    yield delete_case("delete flag 2", b"Key", flag=2)
    for i in range(20):
        yield delete_case(f"delete random {i}",
                          bytes(random_source.randrange(33, 127) for _ in range(random_source.randrange(1, 30))),
                          status=random_source.choice((0, 0, 2, random_source.randrange(0, 1 << 32))))

    # close
    yield close_case("close open")
    yield close_case("close closed", flag=0)
    yield close_case("close flag 2", flag=2)
    yield close_case("close base equals selected", alias=True)
    for statuses in ((1,), (0, 5, 0, 7, 9), (0xFFFFFFFF,)):
        yield close_case(f"close statuses {statuses}", statuses=statuses)
    yield close_case("close zero handles", handles=(0, 0, 0, 0, 0))
    yield close_case("close all same handle", handles=(0x777, 0x777, 0x777, 0x777, 0x777))
    yield close_case("close base zero selected nonzero", handles=(1, 2, 3, 0, 9))
    yield close_case("close base nonzero selected zero", handles=(1, 2, 3, 9, 0))
    yield close_case("close base equals first parent", handles=(0x55, 0x66, 0x77, 0x55, 0x88))
    for i in range(25):
        h = tuple(random_source.randrange(0, 1 << 32) for _ in range(5))
        if random_source.randrange(3) == 0:
            h = h[:3] + (h[4], h[4])
        yield close_case(f"close random {i}", handles=h, flag=random_source.choice((0, 1, 1, 3)))
