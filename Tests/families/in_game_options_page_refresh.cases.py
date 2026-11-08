"""Display and Audio page refresh, using original tree and resource lookups."""
from clawparity.cases import Case

DISPLAY = 0x452800
AUDIO = 0x452870
RESOURCE_NAME = 0x527E60


def scenario(function, flags, *, present=(True, True, True), page=None,
             active=1, missing_target=None, resource_mode="loaded", root_match=False,
             reverse=False, salt=0x398A21C7):
    def setup(env):
        owner = env.object(0x2C0, "options", fill=0x93)
        env.put(owner + 4, active)
        env.put(owner + 0x298, (0x59DA if function == DISPLAY else 0x59DB) if page is None else page)
        root = owner + 0x19C
        env.put(root + 0x50, 0xDEAD)
        targets = []
        for index, offset in enumerate((0x26C, 0x264, 0x268)):
            sprite = env.object(0x190, "sprite-%s" % index, fill=0x51 + index)
            manager = env.object(0x20, "manager-%s" % index)
            resources = env.object(0x30, "resources-%s" % index)
            env.put(sprite + 0xC, manager)
            env.put(manager + 0x10, resources)
            # The original resource hash table uses one bucket here, with a
            # distinct per-sprite frame array to expose target/index mistakes.
            table = resources + 0x10
            buckets = env.object(4, "buckets-%s" % index)
            env.put(table + 4, buckets, 1)
            resource = env.object(0x70, "resource-%s" % index, fill=0x62 + index)
            frames = env.object(0x100, "frames-%s" % index)
            for frame in range(64):
                env.put(frames + frame * 4, (salt ^ (index * 0x173AC17) ^ (frame * 0x1020301)) & 0xFFFFFFFF)
            low, high = (0, 63)
            if resource_mode == "below":
                low, high = 47, 63
            elif resource_mode == "above":
                low, high = 0, 40
            elif resource_mode == "exact":
                low = high = (0x2D if index == 0 else 0x29 if index == 1 else 0x2B) + bool(flags[index] & 6)
            env.put(resource + 0x14, frames)
            env.put(resource + 0x64, low, high)
            item = env.object(0x10, "resource-node-%s" % index,
                              words=[0, 0, RESOURCE_NAME, resource])
            env.put(buckets, 0 if resource_mode == "missing" else item)
            env.put(owner + offset, 0 if missing_target == index else sprite)
            targets.append(sprite)

        children = []
        for index, identifier in enumerate((0x5B06, 0x5AA1, 0x5AA4)):
            if not present[index]:
                continue
            node = env.object(0xB0, "widget-%s" % index, fill=0x71 + index)
            env.put(node + 0x20, 0)
            env.put(node + 0x50, identifier)
            env.put(node + 0x80, flags[index])
            children.append(node)
        # Include a harmless nested sibling so an incorrect identifier or
        # lookup receiver is visible without touching unbacked memory.
        distractor = env.object(0xB0, "unmatched-widget", fill=0x41)
        env.put(distractor + 0x50, 0x5B07)
        env.put(distractor + 0x20, 0)
        children.insert(0, distractor)
        if reverse:
            children.reverse()
        vector = env.object(len(children) * 4, "children", words=children)
        env.put(root + 0x1C, vector, len(children))
        if root_match:
            index = 0 if function == DISPLAY else 1
            env.put(root + 0x50, (0x5B06, 0x5AA1)[function == AUDIO])
            env.put(root + 0x80, flags[index])
        return owner
    return setup


def cases(random_source):
    for function in (DISPLAY, AUDIO):
        def emit(label, flags=(0, 0, 0), **options):
            return Case(label, function, scenario(function, flags, **options), receiver=lambda owner: owner)

        for page in (0, 0x59D9, 0x59DA, 0x59DB, 0xFFFFFFFF):
            yield emit("page-%x-%x" % (function, page), page=page)
        for active in (0, 1, 0x80000000, 0xFFFFFFFF):
            yield emit("active-%x-%x" % (function, active), active=active)
        for missing_target in range(3):
            yield emit("missing-target-%x-%s" % (function, missing_target), missing_target=missing_target)
        for bits in range(8):
            present = tuple(bool(bits & (1 << i)) for i in range(3))
            yield emit("presence-%x-%s" % (function, bits), present=present)
        for flag in (0, 1, 2, 4, 6, 7, 8, 0x100, 0x80000000, 0xFFFFFFF9, 0xFFFFFFFF):
            for index in range(3):
                flags = [0x29, 0x71, 0xA1]
                flags[index] = flag
                yield emit("flags-%x-%s-%x" % (function, index, flag), tuple(flags))
        for flags in ((0, 0, 0), (2, 2, 2), (4, 0, 2), (1, 2, 0)):
            for mode in ("loaded", "missing", "below", "above", "exact"):
                yield emit("resources-%x-%s-%s" % (function, flags, mode), flags, resource_mode=mode)
        yield emit("root-match-%x" % function, (4, 0, 4), root_match=True)
        yield emit("reverse-order-%x" % function, (1, 2, 4), reverse=True)
        for index in range(16):
            flags = tuple(random_source.getrandbits(32) for _ in range(3))
            yield emit("random-%x-%s" % (function, index), flags,
                       salt=random_source.getrandbits(32), reverse=bool(index & 1))
