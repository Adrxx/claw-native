// Level 1 loot and breakables, batch 1
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4170b0:
        return 2;
    case 0x42df90:
        return 0;
    case 0x433070:
        return 1;
    case 0x433130:
        return 1;
    case 0x4339e0:
        return 1;
    case 0x433a00:
        return 0;
    case 0x433ad0:
        return 1;
    case 0x433ed0:
        return 0;
    case 0x433f70:
        return 1;
    case 0x434050:
        return 0;
    default:
        return -1;
    }
}

uint32_t function_433f70(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4170b0. cdecl, 2 stack arguments, returns void. Reads and discards the
// first word of the second argument, then stores a 16 by 60 rectangle
// (-16, -52, 16, 60) at +0x118 of the first argument.
uint32_t function_4170b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t object = arguments[0];
    uint32_t source = arguments[1];
    run.get(source);
    run.put(object + 0x118, 0xfffffff0);
    run.put(object + 0x11c, 0xffffffcc);
    run.put(object + 0x120, 0x10);
    run.put(object + 0x124, 0x3c);
    return 0;
}

// 0x42df90. thiscall, returns void. Spawns one BouncingGoodie per nonzero
// entry of the list at +0x2c. G = ECX.
uint32_t function_42df90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t list = receiver;
    if (s32(run.get(list + 0x28)) > 0) {
        uint32_t sound = run.get(list + 0x20);
        if (sound != 0) {
            uint32_t soundId = run.get(0x532c10);
            run.call(0x4208e0, sound, {soundId, 0, 0, 0});
        }
    }
    uint32_t kind = run.get(list + 0x28);
    uint32_t scaled = 0u - kind * 25u;
    uint32_t x = uint32_t(s32(scaled) / 2);
    uint32_t index = 0;
    uint32_t entry = list + 0x2c;
    if (s32(run.get(list + 0x24)) > 0) {
        for (;;) {
            if (run.get(entry) != 0) {
                uint32_t owner = run.get(list + 0x6c);
                uint32_t ownerY = run.get(owner + 0x50);
                uint32_t ownerX = run.get(owner + 0x4c);
                uint32_t scene = run.get(list + 0x8);
                uint32_t sceneMid = run.get(scene + 0xc);
                uint32_t factory = run.get(sceneMid + 0x8);
                uint32_t goodie = run.call(0x4c8da0, factory, {0, ownerX, ownerY, 0xfa1, 0x522cc0, 0x40000});
                uint32_t entryValue = run.get(entry);
                uint32_t resolved = run.call(0x473630, 0, {entryValue});
                run.call(0x4c7970, goodie, {resolved});
                uint32_t ownerAgain = run.get(list + 0x6c);
                if (run.get(ownerAgain + 0x100) == 0x20) {
                    uint32_t first = run.get(ownerAgain + 0x148);
                    run.put(goodie + 0x148, first);
                    uint32_t ownerSecond = run.get(list + 0x6c);
                    uint32_t second = run.get(ownerSecond + 0x14c);
                    run.put(goodie + 0x14c, second);
                    uint32_t ownerThird = run.get(list + 0x6c);
                    uint32_t third = run.get(ownerThird + 0xfc);
                    run.put(goodie + 0xfc, third);
                }
                uint32_t goodieState = run.get(goodie + 0x6c);
                uint32_t method = run.get(goodieState + 0x10);
                run.call(method, 0, {goodie});
                uint32_t mode = run.get(list + 0x28);
                if (mode != 1) {
                    uint32_t state = run.get(goodie + 0x6c);
                    uint32_t body = run.get(state + 0x18);
                    run.putd(body + 0x50, double(s32(x)));
                } else {
                    uint32_t random = run.call(0x4a3050, 0, {});
                    uint32_t velocity = uint32_t(s32(random) % 401) - 0xc8u;
                    uint32_t state = run.get(goodie + 0x6c);
                    uint32_t body = run.get(state + 0x18);
                    run.putd(body + 0x50, double(s32(velocity)));
                }
                uint32_t velocityY = 0;
                if (run.get(0x53721c) != 0) {
                    uint32_t random = run.call(0x4a3050, 0, {});
                    velocityY = 0u - (uint32_t(s32(random) % 1001) + 0x1f4u);
                } else {
                    uint32_t random = run.call(0x4a3050, 0, {});
                    velocityY = 0u - (uint32_t(s32(random) % 301) + 0xc8u);
                }
                uint32_t stateY = run.get(goodie + 0x6c);
                uint32_t bodyY = run.get(stateY + 0x18);
                run.putd(bodyY + 0x58, double(s32(velocityY)));
                uint32_t stateTop = run.get(goodie + 0x6c);
                uint32_t bodyTop = run.get(stateTop + 0x18);
                run.put(bodyTop + 0x40, 0);
                run.put(bodyTop + 0x44, 0x40890000);
                uint32_t stateLast = run.get(goodie + 0x6c);
                uint32_t savedEntry = run.get(entry);
                uint32_t bodyLast = run.get(stateLast + 0x18);
                run.put(bodyLast + 0x184, savedEntry);
            }
            uint32_t carriedX = x;
            uint32_t count = run.get(list + 0x24);
            index += 1;
            entry += 4;
            x = carriedX + 0x19;
            if (!(s32(index) < s32(count)))
                break;
        }
    }
    return 0;
}

// 0x433130. thiscall, 1 stack argument, returns this. Crate constructor.
uint32_t function_433130(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t crate = receiver;
    uint32_t level = arguments[0];
    run.call(0x4332f0, crate, {level});
    run.put(crate + 0x0, 0x50c77c);
    uint32_t actor = run.get(crate + 0x12c);
    run.call(0x4c7970, actor, {0x5266cc});
    uint32_t capacity = run.get(crate + 0x2fc);
    uint32_t bits = crate + 0x2f4;
    if (capacity <= 1) {
        run.call(0x4dbd20, bits, {1});
    } else {
        uint32_t word = bits + 0xc;
        if (capacity > 0x20)
            word = run.get(bits + 0xc);
        uint32_t value = run.get(word);
        run.put(word, value | 2u);
    }
    run.put(crate + 0x400, 0);
    run.put(crate + 0x404, 0);
    run.put(crate + 0x408, 0);
    uint32_t actorAgain = run.get(crate + 0x12c);
    run.call(0x406290, actorAgain, {});
    uint32_t box = run.get(crate + 0x12c);
    run.put(box + 0x128, 0xffffffec);
    run.put(box + 0x12c, 0xffffffec);
    run.put(box + 0x130, 0x14);
    run.put(box + 0x134, 0x14);
    run.icall(0x546d5c, {crate + 0x220, 0x80000000, 0, 0, 0});
    run.icall(0x546d5c, {crate + 0x210, 0x80000000, 0, 0, 0});
    uint32_t flagsOwner = run.get(crate + 0x12c);
    run.put(flagsOwner + 0xd0, 0x200);
    uint32_t flagsOwnerAgain = run.get(crate + 0x12c);
    run.put(flagsOwnerAgain + 0xd4, 0x3000072);
    uint32_t link = run.get(crate + 0x12c);
    uint32_t linkMid = run.get(link + 0xc);
    uint32_t soundTable = run.get(linkMid + 0x2c);
    uint32_t handle = run.call(0x4061b0, soundTable, {0x5266b8});
    if (handle == 0)
        handle = run.call(0x4062e0, crate + 0x128, {0x5234b4});
    uint32_t world = run.get(crate + 0xc);
    run.put(crate + 0x410, handle);
    run.put(world + 0x10c, 1);
    uint32_t worldAgain = run.get(crate + 0xc);
    double scaled = double(s32(run.get(worldAgain + 0x10c))) * double(run.getf(0x5262b4));
    uint32_t truncated = run.call_x87(0x4a30e0, 0, scaled, {});
    run.put(worldAgain + 0x10c, truncated);
    run.put(crate + 0x50, 0);
    run.put(crate + 0x58, 0);
    run.put(crate + 0x60, 0);
    run.put(crate + 0x54, 0);
    run.put(crate + 0x5c, 0);
    run.put(crate + 0x64, 0);
    run.put(crate + 0x40, 0);
    run.put(crate + 0x44, 0x409f4000);
    run.put(crate + 0x108, 0);
    run.put(crate + 0x10c, 0x407f4000);
    uint32_t worldThird = run.get(crate + 0xc);
    run.put(worldThird + 0xcc, 7);
    double speed = run.getd(crate + 0x70);
    uint32_t speedInt = run.call_x87(0x4a30e0, 0, speed, {});
    const uint32_t nested[1] = {speedInt};
    function_433f70(run, crate, nested);
    return crate;
}

// 0x433a00. thiscall, returns void. Crate base destructor.
uint32_t function_433a00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t crate = receiver;
    run.put(crate + 0x0, 0x50b16c);
    run.call(0x4dbcd0, crate + 0x2f4, {});
    run.call(0x4f6584, crate + 0x1a8, {});
    run.call(0x4f6584, crate + 0x1a4, {});
    run.put(crate + 0x0, 0x50b014);
    return 0;
}

// 0x4339e0. thiscall, 1 stack argument, returns this. Scalar deleting destructor.
uint32_t function_4339e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t crate = receiver;
    function_433a00(run, crate, arguments);
    if ((arguments[0] & 1u) != 0)
        run.call(0x4f6428, 0, {crate});
    return crate;
}

// 0x433070. cdecl, 1 stack argument, returns 1. Logic-state tick.
uint32_t function_433070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t level = arguments[0];
    uint32_t logic = run.get(level + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state > 0x1d) {
        if (state == 0x1e) {
            uint32_t object = run.get(logic + 0x18);
            run.vcall(object, 0x1c, {});
        } else if (state != 0x3e8) {
            uint32_t object = run.get(logic + 0x18);
            run.call(0x4dc870, 0, {object});
        }
    } else if (state == 0x1d) {
        uint32_t object = run.get(logic + 0x18);
        run.vcall(object, 0x20, {});
    } else if (state != 0) {
        uint32_t object = run.get(logic + 0x18);
        run.call(0x4dc870, 0, {object});
    } else {
        run.put(logic + 0x1c, 0x3e8);
        uint32_t block = run.call(0x4f63ec, 0, {0x418});
        uint32_t crate = 0;
        if (block != 0) {
            const uint32_t nested[1] = {level};
            crate = function_433130(run, block, nested);
        }
        run.get(crate);
        run.vcall(crate, 0x10, {});
        run.put(logic + 0x18, crate);
    }
    return 1;
}

// 0x433ad0. thiscall, 1 stack argument, returns void. Dispatches the handler
// registered for an index in the table at 0x537308, growing it on demand.
uint32_t function_433ad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    uint32_t index = arguments[0];
    uint32_t low = run.get(0x537310);
    run.put(0x537328, 0);
    uint32_t entry = 0;
    bool outside = s32(index) < s32(low);
    if (!outside)
        outside = s32(index) > s32(run.get(0x537314));
    if (outside) {
        uint32_t grown = run.call(0x4db6e0, 0x537308, {index, 0});
        if (grown == 0)
            run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x433b25);
        low = run.get(0x537310);
    }
    uint32_t offset = index - low;
    uint32_t base = run.get(0x537318);
    offset = offset * run.get(0x537320);
    entry = offset + base;
    if (run.get(entry) == 0) {
        run.call(0x43d490, self, {index});
        return 0;
    }
    run.put(0x537328, 0);
    bool outsideAgain = s32(index) < s32(low);
    if (!outsideAgain)
        outsideAgain = s32(run.get(0x537314)) < s32(index);
    if (outsideAgain) {
        uint32_t grownAgain = run.call(0x4db6e0, 0x537308, {index, 0});
        if (grownAgain == 0)
            run.fail(CLAW_FAULT_UNIMPLEMENTED, 0x433b9f);
        low = run.get(0x537310);
    }
    uint32_t slotOffset = index - low;
    uint32_t slotBase = run.get(0x537318);
    slotOffset = slotOffset * run.get(0x537320);
    uint32_t slot = slotOffset + slotBase;
    uint32_t handler = run.get(slot);
    run.call(handler, self, {});
    return 0;
}

// 0x433ed0. thiscall, returns 0. Enters the damage state and unlinks the crate.
uint32_t function_433ed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t crate = receiver;
    run.put(crate + 0xc8, 1);
    uint32_t previous = run.get(crate + 0x400);
    if (previous != 0) {
        uint32_t next = run.get(crate + 0x404);
        run.put(previous + 0x404, next);
    }
    uint32_t nextLink = run.get(crate + 0x404);
    if (nextLink != 0) {
        uint32_t prior = run.get(crate + 0x400);
        run.put(nextLink + 0x400, prior);
    }
    uint32_t stateOwner = run.get(crate + 0x10);
    uint32_t oldState = run.get(stateOwner + 0x1c);
    run.put(crate + 0x24, oldState);
    uint32_t damage = run.call(0x4dba00, 0x537668, {0x526700});
    uint32_t stateOwnerAgain = run.get(crate + 0x10);
    run.put(stateOwnerAgain + 0x1c, damage);
    return 0;
}

// 0x433f70. thiscall, 1 stack argument, returns 0. Enters the fall state.
uint32_t function_433f70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t crate = receiver;
    run.putd(crate + 0xa0, double(s32(arguments[0])));
    uint32_t stateOwner = run.get(crate + 0x10);
    uint32_t oldState = run.get(stateOwner + 0x1c);
    run.put(crate + 0x24, oldState);
    uint32_t fall = run.call(0x4dba00, 0x537668, {0x5266f8});
    uint32_t stateOwnerAgain = run.get(crate + 0x10);
    run.put(stateOwnerAgain + 0x1c, fall);
    return 0;
}

// 0x434050. thiscall, returns 1. Crate break action.
uint32_t function_434050(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t crate = receiver;
    uint32_t actor = run.get(crate + 0x12c);
    uint32_t sound = run.get(crate + 0x410);
    uint32_t savedField = run.get(actor + 0x190);
    run.put(crate + 0x134, savedField);
    run.call(0x4c8220, actor + 0x188, {sound});
    uint32_t actorAgain = run.get(crate + 0x12c);
    uint32_t flags = run.get(actorAgain + 0x8);
    run.put(actorAgain + 0x8, flags | 4u);
    uint32_t actorThird = run.get(crate + 0x12c);
    uint32_t flagsAgain = run.get(actorThird + 0x8);
    run.put(actorThird + 0x8, flagsAgain | 2u);
    run.vcall(crate, 0xa8, {});
    uint32_t world = run.get(crate + 0xc);
    uint32_t view = run.get(world + 0x74);
    if (run.get(view + 0xd0) == 0x20) {
        uint32_t viewFlags = run.get(view + 0x8);
        run.put(view + 0x8, viewFlags | 0x10000u);
    }
    function_42df90(run, crate + 0x128, arguments);
    uint32_t random = run.call(0x4a3050, 0, {});
    int32_t roll = s32(random) % 100;
    uint32_t stateOwner = run.get(crate + 0x10);
    uint32_t stateMid = run.get(stateOwner + 0xc);
    uint32_t map = run.get(stateMid + 0x28);
    uint32_t guard = run.get(map + 0x30);
    uint32_t keyName = 0x526730;
    if (roll >= 0x32)
        keyName = 0x52671c;
    if (guard != 0)
        return 1;
    uint32_t found = run.automatic(-4);
    run.put(found, 0);
    run.call(0x4f6286, map + 0x10, {keyName, found});
    uint32_t result = run.get(found);
    if (result == 0)
        return 1;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t soundId = run.get(0x532c10);
    if (enabled == 0)
        return 1;
    uint32_t target = run.get(result + 0x10);
    run.call(0x4b45f0, target, {soundId, 0, 0, 0});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4170b0:
        return function_4170b0(run, receiver, arguments);
    case 0x42df90:
        return function_42df90(run, receiver, arguments);
    case 0x433070:
        return function_433070(run, receiver, arguments);
    case 0x433130:
        return function_433130(run, receiver, arguments);
    case 0x4339e0:
        return function_4339e0(run, receiver, arguments);
    case 0x433a00:
        return function_433a00(run, receiver, arguments);
    case 0x433ad0:
        return function_433ad0(run, receiver, arguments);
    case 0x433ed0:
        return function_433ed0(run, receiver, arguments);
    case 0x433f70:
        return function_433f70(run, receiver, arguments);
    case 0x434050:
        return function_434050(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_loot_breakables_01_entry, owned, body)
