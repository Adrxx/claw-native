"""Cases for level_one_batch_projectile_base_01: Level 1 projectile base slot 0x474290."""
from clawparity.cases import Case

SLOT = 0x474290
REGISTRY = 0x537668  # global string registry passed to the lookup; its head is at +0x18
NAME = b"LS_FALLING"
NAME_BITS = len(NAME) * 8 + 7  # 87, the highest bit index the lookup accepts


def name_bit(index):
    return (NAME[index >> 3] >> (index & 7) & 1) if (index >> 3) < len(NAME) else 0


def nonzero_bytes(random_source, count):
    return bytes(random_source.randrange(1, 256) for _ in range(count))


class Trie:
    """Builds registry nodes: +0 left, +4 right, +8 bit index, +0xc key pointer, +0x10 value."""

    def __init__(self, env, random_source):
        self.env = env
        self.random = random_source

    def key(self, text):
        return self.env.object(len(text) + 1, "key", data=text + b"\0")

    def node(self, bit, left=0, right=0, key=NAME, value=None):
        value = self.random.randrange(0x1000, 0xFFFFFFF) if value is None else value
        token = self.env.object(0x28, "node", data=nonzero_bytes(self.random, 0x28))
        self.env.put(token, left, right, bit, self.key(key) if isinstance(key, bytes) else key, value)
        return token

    def path(self, bits, key=NAME, leaf_bit=None, leaf_null=False, other_key=b"OTHER"):
        """A chain of test nodes along NAME's own bits, ending in a back edge to a leaf holding `key`.

        Every wrong-side child is a leaf that holds NAME with a different value, so a flipped
        branch returns a different value."""
        values = {}
        leaf_bit = bits[-1] if leaf_bit is None else leaf_bit
        leaf = 0 if leaf_null else self.node(leaf_bit, key=key)
        values["leaf"] = leaf
        decoy = self.node(0, key=NAME)
        child = leaf
        for position in range(len(bits) - 1, -1, -1):
            bit = bits[position]
            sides = [decoy, decoy]
            sides[name_bit(bit)] = child
            child = self.node(bit, sides[0], sides[1], key=other_key)
        return child, values


def build(label, root_builder, with_param, random_source, alias=None, registry_head=True):
    def setup(env):
        trie = Trie(env, random_source)
        slot = env.object(0x170, "slot", data=nonzero_bytes(random_source, 0x170))
        record = env.object(0x40, "record", data=nonzero_bytes(random_source, 0x40))
        owner = env.object(0x100, "owner", data=nonzero_bytes(random_source, 0x100))
        host = env.object(0x1D0, "host", data=nonzero_bytes(random_source, 0x1D0))
        element = env.object(0x40, "element", data=nonzero_bytes(random_source, 0x40))
        param = env.object(0x30, "param", data=nonzero_bytes(random_source, 0x30))
        array = env.object(0x20, "array", data=nonzero_bytes(random_source, 0x20))
        if alias == "record_is_element":
            element = record
        if alias == "owner_is_record":
            owner = record
        if alias == "host_is_record":
            host = record
        if alias == "host_is_owner":
            host = owner
        env.put(record + 0x1C, random_source.randrange(0x100, 0xFFFFFFF))
        env.put(element + 0x1C, random_source.randrange(0x100, 0xFFFFFFF))
        env.put(array, element, random_source.randrange(1, 0xFFFFFFF))
        env.put(param + 0x0C, array)
        env.put(param + 0x10, random_source.choice((1, 2, 3, 50, 0x7FFFFFFF)))
        env.put(host + 0x190, random_source.randrange(0x100, 0xFFFFFFF))
        env.put(slot + 0x0C, owner)
        env.put(slot + 0x10, record)
        env.put(slot + 0x12C, host)
        env.put(slot + 0x134, random_source.randrange(0x100, 0xFFFFFFF))
        env.put(slot + 0x148, param if with_param else 0)
        if registry_head:
            root = root_builder(trie) if root_builder else 0
            env.put(REGISTRY + 0x18, root)
            env.put(REGISTRY + 0x1C, *[random_source.randrange(1, 0xFFFFFFF) for _ in range(4)])
            env.put(REGISTRY + 0x2C, random_source.randrange(1, 0xFFFFFFF))
        return {"slot": slot}

    return Case(label, SLOT, setup, receiver=lambda tokens: tokens["slot"])


def cases(random_source):
    scenarios = []

    def add(name, builder):
        scenarios.append((name, builder))

    add("empty registry", lambda t: 0)
    add("head bit above the name length", lambda t: t.node(NAME_BITS + 1, key=NAME))
    add("head bit far above the name length", lambda t: t.node(0x7FFF, key=NAME))
    for bits in ([0], [1], [2], [3], [5], [6], [7], [8], [16], [40], [79], [80], [86], [87],
                 [0, 20], [2, 40, 79], [1, 9, 33, 64, 87], [4, 13, 22, 31, 50, 69, 87]):
        add(f"path {bits}", lambda t, bits=bits: t.path(bits)[0])
    add("back edge to a lower bit", lambda t: t.path([6, 30], leaf_bit=3)[0])
    add("leaf bit equals the parent bit", lambda t: t.path([5, 30], leaf_bit=30)[0])
    add("leaf bit above the parent: keep descending, then null", lambda t: t.path([5, 30], leaf_bit=50, leaf_null=True)[0])
    add("null child on the first test", lambda t: t.path([2], leaf_null=True)[0])
    add("null child deep", lambda t: t.path([2, 30, 60, 87], leaf_null=True)[0])
    add("node below the name length ends the walk at the bit test", lambda t: t.path([87, 90], leaf_bit=95, leaf_null=True)[0])
    for text in (b"", b"A" + NAME[1:], b"M" + NAME[1:], b"LT_FALLING", b"LR_FALLING", b"LS_GALLING", b"LS_FALLINF",
                 b"LS_FALLINH", b"LS_FALLIN", b"LS_FALLING!", b"LS_FALLING\x01", b"LS_FALLINGS", b"ls_falling",
                 NAME[:4], b"LS_FAKLING", b"LS_FALLXNG", b"\xffS_FALLING", b"LS_FALLING"[:9] + b"\xff"):
        add(f"key {text!r}", lambda t, text=text: t.path([3, 40], key=text)[0])
    add("single node tree keyed by the name", lambda t: t.node(NAME_BITS, key=NAME, left=0, right=0))

    for name, builder in scenarios:
        for with_param in (False, True):
            suffix = "with head object" if with_param else "no head object"
            yield build(f"{name}: {suffix}", builder, with_param, random_source)

    # Registry left as the program image has it.
    for with_param in (False, True):
        yield build(f"registry untouched: {with_param}", None, with_param, random_source, registry_head=False)

    exact = lambda t: t.path([3, 40])[0]
    for alias in ("record_is_element", "owner_is_record", "host_is_record", "host_is_owner"):
        for with_param in (False, True):
            yield build(f"{alias}: {with_param}", exact, with_param, random_source, alias=alias)

    # Seeded variety on top of the fixed coverage above.
    for index in range(24):
        bits = sorted(random_source.sample(range(0, NAME_BITS + 1), random_source.randrange(1, 5)))
        text = random_source.choice((NAME, NAME, b"LS_FALLING"[:random_source.randrange(0, 10)], b"XS_FALLING"))
        yield build(f"random path {bits} key {text!r} {index}", lambda t, bits=bits, text=text: t.path(bits, key=text)[0],
                    bool(index & 1), random_source)
