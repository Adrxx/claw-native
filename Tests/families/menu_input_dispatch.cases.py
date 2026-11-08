"""Original-only inputs for the application's four menu forwarding methods."""
from clawparity.cases import Case


def forwarding_setup(argc, present, result, salt):
    def setup(env):
        application = env.object(0x60, "application", fill=0xA7)
        menu = env.object(0x40, "menu", fill=0xB9)
        alternate = env.object(0x40, "alternate-menu", fill=0xCD)
        methods = env.object(0x60, "menu-methods", fill=0xE3)
        receipt = env.object(0x40, "callback-receipt", fill=0x57)
        env.put(menu, methods)
        env.put(alternate, methods)
        env.put(application + 0x28, alternate, menu if present else 0, alternate)
        env.put(menu + 0x10, salt, salt ^ 0xC3D2E1F0)

        def callback(slot):
            def effect(env, call):
                # Persist the actual receiver, operand order and entry state.
                env.put(receipt, slot, call.receiver, *call.arguments)
                env.put(receipt + 0x20, env.get(application + 0x2C),
                        env.get(menu + 0x10), env.get(menu + 0x14))
                # Mutations survive the wrapper return and expose unwanted stores.
                env.put(application + 0x2C, alternate)
                env.put(menu + 0x10, salt ^ 0xFFFFFFFF, result)
                return result
            return effect

        for slot in range(0, 0x60, 4):
            env.put(methods + slot, env.stub(f"menu-slot-{slot:02x}", "thiscall", argc, callback(slot)))
        return {"application": application}
    return setup


def cases(random_source):
    boundary_operands = (
        (0, 1, 0xFFFFFFFF),
        (1, 0xFFFFFFFF, 0),
        (0x80000000, 0x7FFFFFFF, 0x80000001),
        (0x12345678, 0x89ABCDEF, 0xFEDCBA98),
    )
    for function, argc in ((0x429D60, 2), (0x429D80, 3), (0x429DB0, 3), (0x429DE0, 3)):
        for present in (False, True):
            for index, result in enumerate((0, 1, 0x80004005, 0xFFFFFFFF)):
                arguments = boundary_operands[index][:argc]
                yield Case(
                    f"{function:x} {'menu' if present else 'absent'} result {result:08x}",
                    function, forwarding_setup(argc, present, result, 0x164B29D3 + index),
                    receiver=lambda tokens: tokens["application"], arguments=arguments,
                )
        for index in range(12):
            arguments = tuple(random_source.getrandbits(32) for _ in range(argc))
            result = random_source.getrandbits(32)
            salt = random_source.getrandbits(32)
            yield Case(
                f"{function:x} random forwarding {index}", function,
                forwarding_setup(argc, True, result, salt),
                receiver=lambda tokens: tokens["application"], arguments=arguments,
            )
