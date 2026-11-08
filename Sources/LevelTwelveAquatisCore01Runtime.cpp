// Level 12 Aquatis core
//
// Recovered from the original instruction packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4041f0:
        return 1;
    case 0x404310:
        return 1;
    case 0x404990:
        return 1;
    case 0x404e20:
        return 1;
    case 0x4050b0:
        return 0;
    case 0x405240:
        return 0;
    case 0x4053d0:
        return 0;
    case 0x4054c0:
        return 0;
    case 0x4055e0:
        return 0;
    case 0x405740:
        return 0;
    case 0x4058b0:
        return 0;
    case 0x405af0:
        return 0;
    default:
        return -1;
    }
}

// State: +0x10 current state object, +0x24 previous state; +0x12c animation.
// Animation +0x190 current frame, +0x188 frame controller. +0x4cc.. timers.
uint32_t function_404990(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4055e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_405740(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t scaled(Run &run, ClawX87State &fp, uint32_t value, uint32_t multiplier) {
    run.x87_step(CLAW_X87_I32, fp, {value});
    double factor = run.getf(multiplier);
    uint64_t bits;
    std::memcpy(&bits, &factor, sizeof(bits));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(bits), uint32_t(bits >> 32)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}
uint32_t tableSlot(Run &run, uint32_t index) {
    if (s32(index) < run.gets(0x534858) || s32(index) > run.gets(0x53485c)) {
        if (!run.call(0x4db6e0, 0x534850, {index, 0})) {
            uint32_t diagnostic = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            run.put(0x544b14, error);
            run.call(0x4db4d0, run.get(0x534854), {0x534850, diagnostic, 0xc});
            return run.get(0x534864);
        }
    }
    return (index - run.get(0x534858)) * run.get(0x534868) + run.get(0x534860);
}

// 0x4041f0. cdecl, 1 stack argument(s), returns u32.
uint32_t function_4041f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    const uint32_t context = run.get(arguments[0] + 0x6c);
    const uint32_t message = run.get(context + 0x1c);
    if (message == 0) {
        run.put(context + 0x1c, 1000);
        uint32_t boss = run.call(0x4f63ec, 0, {0x4f0});
        if (boss) {
            uint32_t input[] = {arguments[0]};
            const uint32_t savedFrame = run.frame;
            run.frame = savedFrame - 0x1c;
            boss = function_404990(run, boss, input);
            run.frame = savedFrame;
        }
        run.vcall(boss, 0x10);
        run.put(context + 0x18, boss);
    } else if (message == 0x1d) {
        run.vcall(run.get(context + 0x18), 0x20);
    } else if (message == 0x1e) {
        run.vcall(run.get(context + 0x18), 0x1c);
    } else if (message != 1000) {
        run.call(0x4dc870, 0, {run.get(context + 0x18)});
    }
    return 1;
}

// 0x404310. thiscall, 1 stack argument(s), returns void.
uint32_t function_404310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t index = arguments[0];
    run.put(0x534870, 0);
    uint32_t slot = tableSlot(run, index);
    if (run.get(slot)) {
        run.put(0x534870, 0);
        slot = tableSlot(run, index);
        run.call(run.get(slot), receiver);
    } else {
        run.call(0x40e280, receiver, {index});
    }
    return 0;
}

// 0x404990. thiscall, 1 stack argument(s), returns u32.
uint32_t function_404990(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    run.call_x87_exact(0x40e0d0, receiver, fp, {arguments[0]});
    run.put(receiver + 0x4cc, 0);
    run.put(receiver + 0x4d0, 0);
    run.put(receiver + 0x4d4, 0);
    run.put(receiver + 0x4d8, 0);
    run.put(receiver + 0x4dc, 0);
    run.put(receiver + 0x4e0, 0);
    run.put(receiver + 0x4e4, 0);
    run.put(receiver + 0x4e8, 0);
    run.put(receiver, 0x50b0b4);
    run.put(0x534874, receiver);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x5234d8});
    uint32_t resource;
    resource = run.call(0x4062e0, receiver + 0x128, {0x5234c0});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x338, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52349c});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x334, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x523488});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x350, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x523474});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x464, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x52345c});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x374, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x523448});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x460, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x523430});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x468, resource);
    resource = run.call(0x4062e0, receiver + 0x128, {0x523418});
    if (!resource)
        resource = run.call(0x4062e0, receiver + 0x128, {0x5234b4});
    run.put(receiver + 0x46c, resource);
    const uint32_t output = run.automatic(4);
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x523400, output});
    run.put(receiver + 0x470, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x5233e8, output});
    run.put(receiver + 0x474, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x5233d0, output});
    run.put(receiver + 0x478, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x5233b8, output});
    run.put(receiver + 0x488, run.get(output));
    run.put(output, 0);
    run.call(0x4f6286, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28) + 0x10, {0x5233a0, output});
    run.put(receiver + 0x48c, run.get(output));
    resource = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28), {0x523388});
    run.put(receiver + 0x490, resource);
    resource = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28), {0x523370});
    run.put(receiver + 0x494, resource);
    resource = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28), {0x523358});
    run.put(receiver + 0x498, resource);
    resource = run.call(0x4061b0, run.get(run.get(run.get(receiver + 0x12c) + 0xc) + 0x28), {0x523340});
    run.put(receiver + 0x49c, resource);
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000026);
    uint32_t animation = run.get(receiver + 0x12c);
    run.put(animation + 0x164, run.get(animation + 0x164) & 0xfffffffe);
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x220});
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x210});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x406240, run.get(receiver + 0x12c));
    run.put(run.get(receiver + 0xc) + 0x104, 15);
    uint32_t stats = run.get(receiver + 0xc);
    uint32_t converted = scaled(run, fp, run.get(stats + 0x104), 0x5262b0);
    run.put(stats + 0x104, converted);
    run.put(receiver + 0x28c, 2500);
    run.put(receiver + 0x290, 500);
    run.put(receiver + 0x294, 2500);
    run.put(receiver + 0x298, 500);
    run.put(run.get(receiver + 0xc) + 0x10c, 100);
    stats = run.get(receiver + 0xc);
    converted = scaled(run, fp, run.get(stats + 0x10c), 0x5262b4);
    run.put(stats + 0x10c, converted);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a8, 0);
    run.put(receiver + 0x4ac, 0);
    uint32_t baseline = run.get(run.get(receiver + 0xc) + 0x50) - 50;
    run.put(receiver + 0x4b4, 0);
    run.put(receiver + 0x4b0, baseline);
    run.put(receiver + 0x4b8, 1);
    run.put(receiver + 0x4bc, 0);
    run.put(receiver + 0x4c0, 0);
    run.put(receiver + 0x4c4, 0);
    run.put(receiver + 0x4c8, 1);
    run.put(receiver + 0x4ec, 0);
    run.put(receiver + 0xc8, 1);
    run.call(0x405060, receiver);
    return receiver;
}

// 0x404e20. thiscall, 1 stack argument(s), returns u32.
uint32_t function_404e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x405fa0, receiver);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4050b0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4050b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    if (!run.get(receiver + 0x4b8))
        return 0;
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t animation = run.get(receiver + 0x12c);
        if (!(run.get8(animation + 0x40) & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            run.put(receiver + 0x138, 0u - run.get(receiver + 0x140));
            run.put(receiver + 0x140, 0u - left);
            run.put(animation + 0x40, run.get(animation + 0x40) | 2);
            animation = run.get(receiver + 0x12c);
            run.call(0x4060b0, animation);
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    run.put(receiver + 0x4d0, 1000);
    run.put(receiver + 0x4cc, run.get(0x537210));
    int32_t random = s32(run.call(0x4a3050, 0));
    uint32_t selected = random % 101 < 50 ? run.get(receiver + 0x350) : run.get(receiver + 0x464);
    uint32_t animation = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    random = s32(run.call(0x4a3050, 0));
    run.call(0x405f60, receiver, {run.get(receiver + 0x470 + uint32_t(random % 3) * 4)});
    return 0;
}

// 0x405240. thiscall, 0 stack argument(s), returns u32.
uint32_t function_405240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    int32_t choice = s32(run.call(0x4a3050, 0)) % 2;
    uint32_t animation = run.get(receiver + 0x12c);
    bool mirrored = run.get(receiver + 0x18c) == 2;
    if (mirrored != bool(run.get8(animation + 0x40) & 2)) {
        uint32_t left = run.get(receiver + 0x138);
        run.put(receiver + 0x138, 0u - run.get(receiver + 0x140));
        run.put(receiver + 0x140, 0u - left);
        run.put(animation + 0x40, mirrored ? run.get(animation + 0x40) | 2 : run.get(animation + 0x40) & 0xfffffffd);
        animation = run.get(receiver + 0x12c);
        left = run.get(animation + 0x118);
        if (left != 0x80000000) {
            run.put(animation + 0x118, 0u - run.get(animation + 0x120));
            run.put(animation + 0x120, 0u - left);
        }
        left = run.get(animation + 0x128);
        if (left != 0x80000000) {
            run.put(animation + 0x128, 0u - run.get(animation + 0x130));
            run.put(animation + 0x130, 0u - left);
        }
        left = run.get(animation + 0x138);
        if (left != 0x80000000) {
            run.put(animation + 0x138, 0u - run.get(animation + 0x140));
            run.put(animation + 0x140, 0u - left);
        }
    }
    if (choice == 0)
        function_4055e0(run, receiver, nullptr);
    else if (choice == 1)
        function_405740(run, receiver, nullptr);
    else
        run.vcall(receiver, 0x48);
    return 0;
}

// 0x4053d0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4053d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52321c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t animation = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x460);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4d8, 4000);
    run.put(receiver + 0x4d4, run.get(0x537210));
    return 0;
}

// 0x4054c0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4054c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52323c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t animation = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x468);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    run.put(receiver + 0x4b4, 1);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4e0, 4000);
    run.put(receiver + 0x4dc, run.get(0x537210));
    return 0;
}

// 0x4055e0. thiscall, 0 stack argument(s), returns void.
uint32_t function_4055e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523258});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t animation = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x468);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a0, 0);
    return 0;
}

// 0x405740. thiscall, 0 stack argument(s), returns void.
uint32_t function_405740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52324c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t animation = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x46c);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    run.put(receiver + 0x4a4, 0);
    run.put(receiver + 0x4a0, 0);
    return 0;
}

// 0x4058b0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4058b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523228});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t animation = run.get(receiver + 0x12c);
        if (!(run.get8(animation + 0x40) & 2)) {
            uint32_t left = run.get(receiver + 0x138);
            run.put(receiver + 0x138, 0u - run.get(receiver + 0x140));
            run.put(receiver + 0x140, 0u - left);
            run.put(animation + 0x40, run.get(animation + 0x40) | 2);
            animation = run.get(receiver + 0x12c);
            run.call(0x406120, animation);
            run.call(0x406150, animation);
            run.call(0x406180, animation);
        }
    } else {
        run.call(0x406310, receiver + 0x128);
    }
    uint32_t animation = run.get(receiver + 0x12c);
    uint32_t selected = run.get(receiver + 0x464);
    run.put(receiver + 0x134, run.get(animation + 0x190));
    run.call(0x4c8220, animation + 0x188, {selected});
    uint32_t sound418 = run.get(receiver + 0x418);
    if (sound418 && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound418 + 0x10), {run.get(0x532c10), 0, 0, 0});
    uint32_t sound41c = run.get(receiver + 0x41c);
    if (sound41c && run.get(0x532c0c))
        run.call(0x4b45f0, run.get(sound41c + 0x10), {run.get(0x532c10), 0, 0, 0});
    uint32_t stats = run.get(receiver + 0xc);
    run.put(receiver + 0x4a0, 0);
    run.put(receiver + 0x4a4, 0);
    run.put(stats + 0x10c, run.get(stats + 0x10c) - 20);
    uint32_t hits = run.get(receiver + 0x4a8) + 1;
    run.put(receiver + 0x4a8, hits);
    if (s32(hits) >= 5) {
        run.put(run.get(receiver + 0xc) + 0x10c, 0);
        run.call(0x405d50, receiver);
    }
    return 0;
}

// 0x405af0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_405af0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (!run.get(receiver + 0x4b8) || run.get(receiver + 0x4b4))
        return 0;
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x52323c}))
            return 0;
    }
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x523228}))
            return 0;
    }
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x5234f4}))
            return 0;
    }
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x523210}))
            return 0;
    }
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x523204}))
            return 0;
    }
    {
        uint32_t name = run.call(0x406020, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        if (!run.call(0x4a3810, 0, {run.get(name), 0x5231f8}))
            return 0;
    }
    if (run.get(0x537210) - run.get(receiver + 0x4e4) < run.get(receiver + 0x4e8))
        return 0;
    uint32_t target = run.get(run.get(receiver + 0xc) + 0x74);
    if (!target)
        return 0;
    bool contact = false;
    if (run.get(target + 0xd0) == 4) {
        run.put(receiver + 0x4e8, 1000);
        run.put(receiver + 0x4e4, run.get(0x537210));
        function_4058b0(run, receiver, nullptr);
        contact = true;
    } else {
        uint32_t name = run.call(0x441030, 0x537698, {run.get(run.get(receiver + 0x10) + 0x1c)});
        uint32_t strings = run.get(0x5376b4);
        uint32_t count = run.get(0x5376b8);
        while (count) {
            if (strings)
                run.call(0x4f6439, strings);
            strings += 4;
            --count;
        }
        if (run.call(0x4a3810, 0, {run.get(name), 0x52321c})) {
            run.put(receiver + 0x4e8, 500);
            run.put(receiver + 0x4e4, run.get(0x537210));
            if (!run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0x14))
                run.call(0x44f3c0, receiver);
            else
                run.call(0x44f510, receiver);
            contact = true;
            run.put(receiver + 0xc8, 1);
        }
    }
    if (contact)
        run.call(0x440e20, receiver, {target});
    if (run.get(target + 0xd0) == 0x20)
        run.put(target + 0x8, run.get(target + 0x8) | 0x10000);
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4041f0:
        return function_4041f0(run, receiver, arguments);
    case 0x404310:
        return function_404310(run, receiver, arguments);
    case 0x404990:
        return function_404990(run, receiver, arguments);
    case 0x404e20:
        return function_404e20(run, receiver, arguments);
    case 0x4050b0:
        return function_4050b0(run, receiver, arguments);
    case 0x405240:
        return function_405240(run, receiver, arguments);
    case 0x4053d0:
        return function_4053d0(run, receiver, arguments);
    case 0x4054c0:
        return function_4054c0(run, receiver, arguments);
    case 0x4055e0:
        return function_4055e0(run, receiver, arguments);
    case 0x405740:
        return function_405740(run, receiver, arguments);
    case 0x4058b0:
        return function_4058b0(run, receiver, arguments);
    case 0x405af0:
        return function_405af0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_aquatis_core_01_entry, owned, body)
