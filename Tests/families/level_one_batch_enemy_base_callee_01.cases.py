"""Cases for level_one_batch_enemy_base_callee_01: Level 1 enemy contact helper 0x44f510."""
from clawparity.cases import Case
from clawparity.fixtures import returns

HELPER = 0x44F510
RAND = 0x4A3050
TRIE = 0x537668          # table object handed to the string lookup
SOUND_FLAG = 0x532C0C
SOUND_ID = 0x532C10
KEY = 0x523210           # "LS_HITHIGH"

SLOT_OFFSETS = (0x390, 0x394, 0x398, 0x39C)

# Scripted rand results. abs()&3 style switch: 0..3 pick a slot directly; negative values
# with low bits 1..3 land on the default arm; -4 and INT_MIN fold back to case 0.
RAND_VALUES = (0, 1, 2, 3, 4, 5, 6, 7, 0x7FFFFFFF, -1, -2, -3, -4, -5, -0x80000000)


def words(random_source, count):
    return [random_source.randrange(1, 0xFFFFFFFF) | 0x01010101 for _ in range(count)]


def build(random_source, mask=0xF, head=True, flag=1, mode=3, unit=True, sound_id=None, trie=None, dead=0, live_head=True):
    """setup() for one enemy. mask selects which of the four +0x390.. sound objects exist."""
    def setup(env):
        enemy = env.object(0x440, "enemy")
        env.write(enemy, bytes(random_source.randrange(1, 256) for _ in range(0x440)))
        link = env.object(0x30, "link", data=bytes(random_source.randrange(1, 256) for _ in range(0x30)))
        owner = env.object(0x1D0, "owner", data=bytes(random_source.randrange(1, 256) for _ in range(0x1D0)))
        element = env.object(0x40, "element", data=bytes(random_source.randrange(1, 256) for _ in range(0x40)))
        sprite_set = env.object(0x20, "sprite-set")
        env.put(sprite_set + 0x0C, element)
        env.put(sprite_set + 0x10, random_source.randrange(1, 5))
        env.put(element + 0x1C, *words(random_source, 1))
        env.put(link + 0x1C, *words(random_source, 1))
        env.put(owner + 0x190 - 0x0, words(random_source, 1)[0])
        env.put(enemy + 0x10, link)
        env.put(enemy + 0x12C, owner)
        env.put(enemy + 0x338, sprite_set)
        env.put(enemy + 0x18C, mode)
        sprite_pointer = env.object(8, "sprite-pointer")
        # the first sprite element is placed so that its +0x1C word is the enemy's +0x134 field:
        # the sprite-set binder then copies whatever the enemy holds there at that moment
        env.put(sprite_pointer, enemy + 0x118)
        env.put(sprite_set + 0x0C, sprite_pointer)
        rnd = random_source

        def sound(live=True):
            """sound object -> channel (+0x10) -> device (+0x10, word +0x78 nonzero when live).
            A live channel owns one voice node on its list (+0x30) and a COM-like object whose
            vtable slots are recording stubs, so the receiver and arguments of every call
            identify which sound object the helper used."""
            outer = env.object(0x30, "sound", data=bytes(rnd.randrange(1, 256) for _ in range(0x30)))
            channel = env.object(0x40, "channel", data=bytes(rnd.randrange(1, 256) for _ in range(0x40)))
            device = env.object(0x80, "device", data=bytes(rnd.randrange(1, 256) for _ in range(0x80)))
            env.put(device + 0x78, words(rnd, 1)[0] if live else 0)
            env.put(channel + 0x10, device)
            env.put(outer + 0x10, channel)
            if not live:
                return outer
            voice = env.object(0x40, "voice", data=bytes(rnd.randrange(1, 256) for _ in range(0x40)))
            com = env.object(0x10, "com")
            vtable = env.object(0x50, "vtable")
            env.put(com, vtable)
            env.put(voice + 0x0C, com)
            env.put(voice + 0x10, device)
            env.put(voice + 0x04, 0)
            env.put(voice + 0x08, 0)
            env.put(voice + 0x30, words(rnd, 1)[0])      # busy voice: the channel scans it, finds it idle and reuses it
            env.put(channel + 0x30, voice + 4)
            env.put(vtable + 0x24, 0x4B8890)   # original "xor eax,eax; ret 8": its out-parameter is a stack address, which cannot be logged stably
            env.put(vtable + 0x30, env.stub("com play", "stdcall", 4, lambda e, c: 0))
            env.put(vtable + 0x3C, env.stub("com frequency", "stdcall", 2, lambda e, c: 0))
            env.put(vtable + 0x40, env.stub("com pan", "stdcall", 2, lambda e, c: 0))
            env.put(vtable + 0x44, env.stub("com volume", "stdcall", 2, lambda e, c: 0))
            return outer
        env.put(enemy + 0x418, sound(live_head) if head else 0)
        for bit, offset in enumerate(SLOT_OFFSETS):
            env.put(enemy + offset, sound(not (dead >> bit & 1)) if mask >> bit & 1 else 0)
        env.put(SOUND_FLAG, flag)
        env.put(SOUND_ID, sound_id if sound_id is not None else random_source.randrange(0, 100))
        tokens = {"enemy": enemy, "link": link, "owner": owner}
        if trie is not None:
            trie(env, tokens)
        return tokens
    return setup


def helper(label, setup, rand=0):
    def with_rand(env):
        tokens = setup(env)
        env.override(RAND, returns(rand & 0xFFFFFFFF))
        return tokens
    return Case(label, HELPER, with_rand, receiver=lambda tokens: tokens["enemy"])


def trie_with(root, key_bytes=b"LS_HITHIGH\0", child_bit=0, grandchild=True, found_value=0x77AA55CC):
    """Install a one-node trie below TRIE (root at TRIE+0x18). Returns a trie callback."""
    def install(env, tokens):
        env.put(TRIE + 0x1C, 0x11111111)
        env.put(TRIE + 0x20, 0x22222222)
        env.put(TRIE + 0x24, 0x33333333)
        env.put(TRIE + 0x28, 0x44444444)
        if root == "empty":
            env.put(TRIE + 0x18, 0)
            return
        node = env.object(0x20, "trie-root")
        leaf = env.object(0x20, "trie-leaf")
        text = env.object(16, "trie-key", data=key_bytes.ljust(16, b"\0"))
        env.put(TRIE + 0x18, node)
        if root == "deep":              # first test bit lies beyond the key: stop at the root
            env.put(node + 0x08, 1000)
            return
        env.put(node, leaf, 0)          # key bit 0 of 'L' is 0, so the left link is followed
        env.put(node + 0x04, leaf)
        env.put(node + 0x08, child_bit)
        if root == "dangling":
            env.put(node, 0, 0)
            return
        env.put(leaf + 0x08, 0)         # not deeper than its parent: compare the stored key
        env.put(leaf + 0x0C, text)
        env.put(leaf + 0x10, found_value)
        tokens["leaf"] = leaf
    return install


def cases(random_source):
    # every scripted rand outcome against every presence pattern of the four slots
    for rand in RAND_VALUES:
        for mask in (0xF, 0x0, 0x1, 0x2, 0x4, 0x8, 0xE, 0xD, 0xB, 0x7):
            yield helper(f"rand {rand:#x} slots {mask:04b}", build(random_source, mask), rand)
    # the guards: head sound object, global flag, mode word
    for rand in (0, 2, -1):
        for head in (True, False):
            for flag in (0, 1):
                for mode in (3, 2):
                    mask = 0xF if (rand + flag + mode) & 1 else 0b1010
                    yield helper(f"rand {rand} head {head} flag {flag:#x} mode {mode:#x}",
                                 build(random_source, mask, head, flag, mode), rand)
    # inputs drawn from the random source
    for index in range(12):
        rand = random_source.randrange(-0x80000000, 0x80000000)
        yield helper(f"random {index} rand {rand:#x}", build(random_source, random_source.randrange(16),
                     bool(random_source.randrange(2)), random_source.randrange(2), random_source.choice((3, 3, 5))), rand)
    # the string lookup in the original callee, along each of its paths
    yield helper("lookup: empty table", build(random_source, trie=trie_with("empty")), 0)
    yield helper("lookup: test bit beyond key", build(random_source, trie=trie_with("deep")), 1)
    yield helper("lookup: link is null", build(random_source, trie=trie_with("dangling")), 2)
    yield helper("lookup: key found", build(random_source, trie=trie_with("found")), 3)
    yield helper("lookup: key found, other value", build(random_source, trie=trie_with("found", found_value=5)), -4)
    yield helper("lookup: stored key differs in first byte", build(random_source, trie=trie_with("found", b"XS_HITHIGH\0")), 0)
    yield helper("lookup: stored key differs in second byte", build(random_source, trie=trie_with("found", b"LX_HITHIGH\0")), 1)
    yield helper("lookup: stored key differs late", build(random_source, trie=trie_with("found", b"LS_HITHIGI\0")), 2)
    yield helper("lookup: stored key is a prefix", build(random_source, trie=trie_with("found", b"LS_HIT\0")), 3)
    yield helper("lookup: odd-length stored key", build(random_source, trie=trie_with("found", b"LS_HITHIG\0")), 0)
    yield helper("lookup: stored key sorts above", build(random_source, trie=trie_with("found", b"\xffS_HITHIGH\0")), 1)
    # sound objects whose device is silent (early return in the sound start) mixed with live ones
    for rand in (0, 1, 2, 3):
        yield helper(f"dead slots rand {rand}", build(random_source, 0xF, dead=0b1010 >> (rand & 1)), rand)
    yield helper("dead head", build(random_source, 0xF, live_head=False), 2)
    for sound_id in (0, 1, 99):
        for rand in (0, 3):
            yield helper(f"sound id {sound_id} rand {rand}", build(random_source, 0xF, sound_id=sound_id), rand)
