"""Original-only inputs for tower cannon left dispatch and construction."""
from clawparity.cases import Case
from clawparity.world import world, sprite, animation, cstring

ENTRY = 0x495D40
NEW = 0x4F63EC


def cases(random_source):
    for status in (1, 28, 29, 30, 31, 999, 1000, 1001, 0xFFFFFFFF, 0x80000000):
        salt = random_source.randrange(1, 0x100000000)
        def setup(env, status=status, salt=salt):
            owner = env.object(0x200, "dispatch-owner", fill=0xA7)
            state = env.object(0x80, "dispatch-state", fill=0x39)
            obj = env.object(0x80, "existing-cannon", fill=0xC2)
            alternate = env.object(0x80, "alternate-cannon", fill=0x71)
            record = env.object(0x80, "captured-callbacks", fill=0)
            table = env.object(0x24, "callback-table", fill=0)
            identity = env.object(0x20, "logic-identity", fill=0)
            env.put(identity + 0x1C, 42)
            env.put(obj, table)
            env.put(obj + 0x10, identity)
            env.put(owner + 0x6C, state)
            env.put(state + 0x18, obj, status)
            text = cstring(env, "record-state")
            string_slot = env.object(4, "state-string-slot", words=[text])
            env.put(0x5376A0, 42, 42, string_slot)
            env.put(0x5376B0, 4)
            def callback(slot):
                def effect(env, call):
                    index = env.get(record)
                    at = record + 4 + index * 20
                    env.put(at, slot, call.receiver, env.get(state + 0x18), env.get(state + 0x1C), call.arguments[0] if call.arguments else salt)
                    env.put(record, index + 1)
                    env.put(state + 0x18, alternate)
                    env.put(state + 0x1C, salt)
                    return salt
                return effect
            for slot, argc in ((4, 1), (8, 1), (12, 1), (28, 0), (32, 0)):
                env.put(table + slot, env.stub(f"callback-{slot}", "thiscall", argc, callback(slot)))
            return owner
        yield Case(f"dispatch {status:#x}", ENTRY, setup, arguments=(lambda owner: owner,))

    for hit, alias in ((False, False), (True, False), (True, True)):
        velocity = random_source.randrange(1, 100000)
        duration = random_source.randrange(1, 1000)
        def setup(env, hit=hit, alias=alias, velocity=velocity, duration=duration):
            resource = sprite(env, 17, 23, origin=(-7, 11))
            home = animation(env, duration)
            firing = animation(env, duration + 19)
            resources = {"sprites": {"LEVEL_TOWERCANNONLEFT": resource}, "animations": {"LEVEL_TOWERCANNONLEFT_HOME": home, "LEVEL_TOWERCANNONLEFT_FIRING": firing}} if hit else {}
            tokens = world(env, owner_words={0x148: velocity, 0x104: 9}, resources=resources)
            owner, state = tokens["owner"], tokens["state"]
            old = env.object(0x80, "unpublished-old-object", fill=0x53)
            env.put(state + 0x18, old, 0)
            env.put(0x50B9C4, velocity + 7)
            captured = env.object(0x60, "construction-observations", fill=0)
            # This backed alias is overwritten by the original sprite lookup
            # after the constructor has installed its normal vtable.
            if alias:
                owner2 = env.object(0x400, "owner-with-backed-constructor-alias", fill=0)
                env.write(owner2, env.read(owner, 0x200))
                owner = owner2
                def activate(env, call):
                    env.put(captured + 16, call.receiver, env.get(state + 0x18), env.get(state + 0x1C), env.get(call.receiver + 0x5C), env.get(call.receiver + 0x48), env.get(call.receiver + 0x4C))
                    env.put(state + 0x18, old + 4)
                    env.put(state + 0x1C, velocity)
                    return velocity
                env.put(resource + 0x10, env.stub("constructor-activation", "thiscall", 0, activate))
            def allocation(env, call):
                env.put(captured, call.arguments[0], env.get(state + 0x18), env.get(state + 0x1C), owner)
                return owner + 0x170 if alias else env.object(call.arguments[0], "new-cannon", fill=0x91)
            env.override(NEW, allocation)
            return owner
        yield Case(f"construct resources {'hit' if hit else 'miss'} alias={alias}", ENTRY, setup, arguments=(lambda owner: owner,))
