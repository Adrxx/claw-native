// Level 1 CrumblingPeg, TogglePegs and Start/Trigger elevators
//
// Recovered from the decompile and disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x49d860:
        return 1;
    case 0x49e470:
        return 2;
    case 0x49e4b0:
        return 3;
    case 0x49e4e0:
        return 1;
    case 0x49e7b0:
        return 1;
    case 0x49e7d0:
        return 1;
    case 0x49e7f0:
        return 1;
    case 0x4ca610:
        return 4;
    case 0x49cdd0:
        return 1;
    case 0x49daf0:
        return 1;
    case 0x49db10:
        return 1;
    case 0x49db30:
        return 1;
    case 0x49db50:
        return 1;
    case 0x49db70:
        return 1;
    case 0x49ee20:
        return 1;
    default:
        return -1;
    }
}

// Globals: 0x537960 table of four-word records, 0x537e88 player/world object,
// 0x53725c pause flag, 0x537210 clock, 0x5430c4 frame delta, 0x532c10 handle,
// 0x5371fc level object, 0x53ebf0 variant selector.
// Object fields (this = peg or elevator): +0x08 flags, +0x0c owner, +0x4c x,
// +0x50 y, +0x64 z-order, +0x6c logic record, +0xd0 draw state, +0x110 mode,
// +0x128 four-word record, +0x134 fourth word of it, +0x148 and +0x14c speeds,
// +0x158 and +0x15c velocity, +0x164 flags, +0x16c, +0x170 and +0x174 links,
// +0x188 animation object.
// Logic record: +0x10 variant function, +0x1c state, +0x20 argument, +0x2c to
// +0x38 limits, +0x4c period, +0x64 sort key, +0xbc phase.

void copyRecord(Run &run, uint32_t destination, uint32_t source) {
    uint32_t a = run.get(source + 0x0);
    run.put(destination + 0x0, a);
    uint32_t b = run.get(source + 0x4);
    run.put(destination + 0x4, b);
    uint32_t c = run.get(source + 0x8);
    run.put(destination + 0x8, c);
    uint32_t d = run.get(source + 0xc);
    run.put(destination + 0xc, d);
}

uint32_t halfSum(uint32_t a, uint32_t b) {
    uint32_t sum = a + b;
    uint32_t sign = uint32_t(s32(sum) >> 31);
    return uint32_t(s32(sum - sign) >> 1);
}

// 0x4ca610. thiscall. Looks a name up in the owner's table and, when found,
// forwards to 0x4c88e0.
uint32_t function_4ca610(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = run.get(receiver + 0xc);
    uint32_t sibling = run.get(owner + 0x24);
    if (sibling == 0)
        return 0;
    if (run.get(sibling + 0x5c) == 0)
        return 0;
    if (run.get(receiver + 0x30) != 0)
        return 0;
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    run.call(0x4f6286, receiver + 0x10, {arguments[0], local});
    uint32_t found = run.get(local);
    if (found == 0)
        return 0;
    return run.call(0x4c88e0, found, {arguments[1], 0xffffffff, arguments[2], arguments[3]});
}

// 0x49e470.
uint32_t function_49e470(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t record = arguments[1];
    if (run.get(object + 0x148) == 0)
        run.put(object + 0x148, 0x5dc);
    if (run.get(object + 0x14c) == 0)
        run.put(object + 0x14c, 0x5dc);
    uint32_t total = run.get(object + 0x14c) + run.get(object + 0x148);
    run.put(record + 0x4c, total);
    return object;
}

// 0x49e4b0. Unsigned remainder of (clock - phase) by the period, signed
// compared with the object's +0x148.
uint32_t function_49e4b0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t record = arguments[1];
    uint32_t clock = arguments[2];
    uint32_t dividend = clock - run.get(record + 0xbc);
    uint32_t divisor = run.get(record + 0x4c);
    if (divisor == 0)
        run.fail(CLAW_FAULT_MEMORY, record + 0x4c);
    uint32_t remainder = dividend % divisor;
    uint32_t limit = run.get(object + 0x148);
    return s32(remainder) <= s32(limit) ? 1 : 0;
}

// 0x49e4e0. TogglePeg state machine.
uint32_t function_49e4e0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state <= 0x3ea) {
        if (state == 0x3ea) {
            uint32_t owner = run.get(object + 0xc);
            uint32_t sibling = run.get(owner + 0x28);
            uint32_t x = run.get(object + 0x4c);
            const uint32_t slide[4] = {0x528a3c, x, 0, 0};
            function_4ca610(run, sibling, slide);
            run.put(record + 0x1c, 0x3ed);
            return 1;
        }
        if (state != 0)
            return 1;
        uint32_t link = run.get(object + 0x170);
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        if (link != 0) {
            uint32_t key = run.get(link + 0x64);
            run.put(object + 0x16c, key);
            uint32_t value = run.call(0x40f680, link, {key});
            run.put(object + 0x174, value);
        }
        uint32_t flags = run.get(object + 0x8);
        run.put(object + 0xd0, 0x80);
        flags = flags | 1;
        run.put(object + 0x8, flags);
        copyRecord(run, object + 0x128, run.get(0x537960) + 0x58);
        uint32_t lower = run.get(object + 0x134);
        run.put(object + 0x134, lower + 0x20);
        if (run.get(object + 0x64) == 0) {
            flags = flags | 0x20000;
            run.put(object + 0x64, 0x7d0);
            run.put(object + 0x8, flags);
        }
        uint32_t variant = run.get(record + 0x10);
        if (variant == 0x49e7b0)
            run.put(record + 0xbc, 0x2ee);
        else if (variant == 0x49e7d0)
            run.put(record + 0xbc, 0x5dc);
        else if (variant == 0x49e7f0)
            run.put(record + 0xbc, 0x8ca);
        const uint32_t pair[2] = {object, record};
        function_49e470(run, 0, pair);
        run.put(record + 0x1c, 0x3ee);
        uint32_t parent = run.get(object + 0x170);
        if (parent != 0) {
            uint32_t middle = halfSum(run.get(parent + 0x64), run.get(parent + 0x68));
            run.put(record + 0x64, middle);
        }
        if (run.get(0x53725c) == 0) {
            if (run.get(object + 0x108) != 1)
                return 1;
        }
        run.put(record + 0x1c, 5);
        return 1;
    }
    uint32_t index = state - 0x3eb;
    if (index > 4)
        return 1;
    switch (index) {
    case 0: {
        // 0x3eb
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        if (run.get(object + 0x16c) == run.get(record + 0x64))
            run.put(object + 0xd0, 1);
        if (run.get(object + 0x1a4) == 0)
            return 1;
        if (run.get(object + 0x19c) != 0)
            return 1;
        run.put(object + 0xd0, 1);
        run.call(0x4c79e0, object, {0x52dd14, 0});
        run.put(record + 0x1c, 0x3ef);
        return 1;
    }
    case 1: {
        // 0x3ec
        run.put(object + 0xd0, 1);
        run.call(0x4c79e0, object, {0x52dd04, 0});
        uint32_t owner = run.get(object + 0xc);
        uint32_t sibling = run.get(owner + 0x28);
        uint32_t x = run.get(object + 0x4c);
        const uint32_t slide[4] = {0x528a3c, x, 0, 0};
        function_4ca610(run, sibling, slide);
        run.put(record + 0x1c, 0x3eb);
        return 1;
    }
    case 2: {
        // 0x3ed
        run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
        if (run.get(object + 0x16c) == run.get(record + 0x64))
            run.put(object + 0xd0, 0x80);
        if (run.get(object + 0x1a4) == 0)
            return 1;
        if (run.get(object + 0x19c) != 0)
            return 1;
        run.put(object + 0xd0, 0x80);
        run.call(0x4c79e0, object, {0x52dd04, 0});
        run.put(record + 0x1c, 0x3ee);
        return 1;
    }
    case 3: {
        // 0x3ee
        const uint32_t triple[3] = {object, record, run.get(0x537210)};
        if (function_49e4b0(run, 0, triple) == 0)
            run.put(record + 0x1c, 0x3ec);
        return 1;
    }
    default: {
        // 0x3ef
        const uint32_t triple[3] = {object, record, run.get(0x537210)};
        if (function_49e4b0(run, 0, triple) != 0)
            run.put(record + 0x1c, 0x3ea);
        return 1;
    }
    }
}

uint32_t variant_toggle(Run &run, uint32_t object, uint32_t selector) {
    run.put(0x53ebf0, selector);
    const uint32_t one[1] = {object};
    return function_49e4e0(run, 0, one);
}

// 0x49e7b0, 0x49e7d0, 0x49e7f0.
uint32_t function_49e7b0(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_toggle(run, arguments[0], 2);
}

uint32_t function_49e7d0(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_toggle(run, arguments[0], 3);
}

uint32_t function_49e7f0(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_toggle(run, arguments[0], 4);
}

// Unsigned (a * b) / 1000 on the low 32 bits of the product.
uint32_t scaledStep(uint32_t speed, uint32_t delta) {
    uint32_t product = speed * delta;
    return product / 1000;
}

// 0x49cdd0. Start/Trigger elevator state machine.
uint32_t function_49cdd0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    if (run.get(record + 0x1c) == 0) {
        // Initialization.
        uint32_t flags = run.get(object + 0x8);
        uint32_t extent = run.get(object + 0x174);
        flags = flags | 1;
        run.put(object + 0xd0, 0x80);
        run.put(object + 0x8, flags);
        if (extent != 0) {
            run.put(object + 0x118, run.get(extent + 0x20) - run.get(extent + 0x18));
            run.put(object + 0x11c, run.get(extent + 0x24) - run.get(extent + 0x1c));
            run.put(object + 0x120, run.get(extent + 0x20) + run.get(extent + 0x18) - 1);
            run.put(object + 0x124, run.get(extent + 0x1c) + run.get(extent + 0x24) - 1);
        }
        copyRecord(run, object + 0x128, run.get(0x537960) + 0x68);
        uint32_t level = run.get(0x5371fc);
        uint32_t levelInfo = run.get(level + 0x2c);
        if (run.get(levelInfo + 0x14) == 0xa) {
            uint32_t owner = run.get(object + 0xc);
            uint32_t link = run.get(object + 0x170);
            uint32_t trap = run.call(0x4061b0, run.get(owner + 0x10), {0x528a4c});
            if (link == trap)
                copyRecord(run, object + 0x128, run.get(0x537960) + 0x98);
        }
        uint32_t variant = run.get(record + 0x10);
        bool alternateBlock = false;
        if (variant == 0x49daf0) {
            run.put(object + 0x164, run.get(object + 0x164) | 2);
        } else if (variant == 0x49e810) {
            alternateBlock = true;
        } else if (variant == 0x49eb30) {
            run.put(object + 0x164, run.get(object + 0x164) | 2);
            alternateBlock = true;
        } else if (variant == 0x49db30) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x102);
        } else if (variant == 0x49ee20) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x102);
            alternateBlock = true;
        } else if (variant == 0x49db50) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x1102);
        } else if (variant == 0x49db10) {
            run.put(object + 0x164, run.get(object + 0x164) | 0x1002);
        } else if (variant == 0x49db70) {
            run.put(object + 0x164, run.get(object + 0x164) | 1);
        }
        if (alternateBlock) {
            copyRecord(run, object + 0x128, run.get(0x537960) + 0x88);
            run.put(object + 0x110, 2);
        }
        run.put(object + 0x134, run.get(object + 0x134) + 0x20);
        if (run.get(record + 0x2c) == 0)
            run.put(record + 0x2c, run.get(object + 0x4c));
        if (run.get(record + 0x30) == 0)
            run.put(record + 0x30, run.get(object + 0x4c));
        if (run.get(record + 0x34) == 0)
            run.put(record + 0x34, run.get(object + 0x50));
        if (run.get(record + 0x38) == 0)
            run.put(record + 0x38, run.get(object + 0x50));
        uint32_t speed = run.get(object + 0x148);
        uint32_t mode = run.get(object + 0x110);
        if (speed == 0)
            run.put(object + 0x148, 0x7d);
        if (run.get(object + 0x14c) == 0)
            run.put(object + 0x14c, 0x7d);
        if (mode == 6 || mode == 4)
            run.put(object + 0x14c, 0);
        if (mode == 8 || mode == 2)
            run.put(object + 0x148, 0);
        if (mode == 6 || mode == 2 || mode == 3)
            run.put(record + 0x1c, 0x3e9);
        else
            run.put(record + 0x1c, 0x3e8);
        uint32_t world = run.get(0x537e88);
        uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
        run.put(record + 0x64, run.get(table + 0x80));
        return 1;
    }
    uint32_t flags = run.get(object + 0x164);
    bool resetToStart = false;
    if ((flags & 2) != 0) {
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        uint32_t world = run.get(0x537e88);
        bool carried = (run.get8(world + 0x8) & 0x10) != 0 && run.get(world + 0x80) == object;
        if (!carried) {
            uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
            if (run.get(record + 0x64) == run.get(table + 0x80))
                return 1;
            resetToStart = true;
        } else if ((flags & 0x1000) != 0) {
            run.put(object + 0x164, flags & 0xfffffffd);
        }
    } else if ((flags & 1) != 0) {
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        uint32_t world = run.get(0x537e88);
        if ((run.get8(world + 0x8) & 0x10) != 0 && run.get(world + 0x80) == object)
            return 1;
    }
    if (!resetToStart) {
        if ((run.get(object + 0x164) & 0x1000) != 0) {
            uint32_t world = run.get(0x537e88);
            uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
            if (run.get(record + 0x64) != run.get(table + 0x80))
                resetToStart = true;
        }
    }
    if (resetToStart) {
        run.put(object + 0x4c, run.get(object + 0xe8));
        run.put(object + 0x50, run.get(object + 0xec));
        uint32_t world = run.get(0x537e88);
        uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
        uint32_t key = run.get(table + 0x80);
        run.put(record + 0x1c, 0);
        run.put(record + 0x64, key);
        return 1;
    }
    uint32_t state = run.get(record + 0x1c);
    if (state == 5) {
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        return 1;
    }
    if (state == 0x3e8) {
        // Moving toward the low limits.
        if (s32(run.get(object + 0x4c)) > s32(run.get(record + 0x2c)))
            run.put(object + 0x158, 0 - scaledStep(run.get(object + 0x148), run.get(0x5430c4)));
        else
            run.put(object + 0x158, 0);
        uint32_t stepX = run.get(object + 0x158);
        if (s32(stepX) < -0x10)
            stepX = 0xfffffff0;
        uint32_t y = run.get(object + 0x50);
        run.put(object + 0x158, stepX);
        if (s32(y) > s32(run.get(record + 0x34)))
            run.put(object + 0x15c, 0 - scaledStep(run.get(object + 0x14c), run.get(0x5430c4)));
        else
            run.put(object + 0x15c, 0);
        uint32_t stepY = run.get(object + 0x15c);
        if (s32(stepY) < -0x10)
            stepY = 0xfffffff0;
        uint32_t newX = run.get(object + 0x4c) + stepX;
        run.put(object + 0x15c, stepY);
        uint32_t newY = stepY + y;
        run.put(object + 0x4c, newX);
        run.put(object + 0x50, newY);
        if (s32(newX) > s32(run.get(record + 0x2c)))
            return 1;
        if (s32(newY) > s32(run.get(record + 0x34)))
            return 1;
        run.put(record + 0x1c, 0x3e9);
    } else if (state == 0x3e9) {
        // Moving toward the high limits.
        if (s32(run.get(object + 0x4c)) < s32(run.get(record + 0x30)))
            run.put(object + 0x158, scaledStep(run.get(object + 0x148), run.get(0x5430c4)));
        else
            run.put(object + 0x158, 0);
        uint32_t stepX = run.get(object + 0x158);
        if (s32(stepX) > 0x10)
            stepX = 0x10;
        uint32_t y = run.get(object + 0x50);
        run.put(object + 0x158, stepX);
        if (s32(y) < s32(run.get(record + 0x38)))
            run.put(object + 0x15c, scaledStep(run.get(object + 0x14c), run.get(0x5430c4)));
        else
            run.put(object + 0x15c, 0);
        uint32_t stepY = run.get(object + 0x15c);
        if (s32(stepY) > 0x10)
            stepY = 0x10;
        uint32_t newX = run.get(object + 0x4c) + stepX;
        run.put(object + 0x15c, stepY);
        uint32_t newY = stepY + y;
        run.put(object + 0x4c, newX);
        run.put(object + 0x50, newY);
        if (s32(newX) < s32(run.get(record + 0x30)))
            return 1;
        if (s32(newY) < s32(run.get(record + 0x38)))
            return 1;
        run.put(record + 0x1c, 0x3e8);
    } else {
        return 1;
    }
    if ((run.get(object + 0x164) & 0x100) == 0)
        return 1;
    run.put(record + 0x1c, 5);
    return 1;
}

uint32_t variant_elevator(Run &run, uint32_t object, uint32_t selector) {
    run.put(0x53ebf0, selector);
    const uint32_t one[1] = {object};
    return function_49cdd0(run, 0, one);
}

// 0x49daf0, 0x49db10, 0x49db30, 0x49db50, 0x49db70.
uint32_t function_49daf0(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_elevator(run, arguments[0], 0x14);
}

uint32_t function_49db10(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_elevator(run, arguments[0], 0x15);
}

uint32_t function_49db30(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_elevator(run, arguments[0], 0x16);
}

uint32_t function_49db50(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_elevator(run, arguments[0], 0x17);
}

uint32_t function_49db70(Run &run, uint32_t, const uint32_t *arguments) {
    return variant_elevator(run, arguments[0], 0x18);
}

// 0x49ee20. Forwards to 0x49eb30.
uint32_t function_49ee20(Run &run, uint32_t, const uint32_t *arguments) {
    return run.call(0x49eb30, 0, {arguments[0]});
}

// 0x49d860. CrumblingPeg state machine.
uint32_t function_49d860(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t object = arguments[0];
    uint32_t record = run.get(object + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state <= 5) {
        if (state == 5) {
            if (run.get(0x53725c) != 0)
                return 1;
            uint32_t world = run.get(0x537e88);
            if ((run.get8(world + 0x8) & 0x10) == 0)
                return 1;
            if (run.get(world + 0x80) != object)
                return 1;
            uint32_t speed = run.get(object + 0x148);
            run.put(record + 0x1c, 0x3ea);
            run.put(record + 0x20, speed);
            return 1;
        }
        if (state != 0)
            return 1;
        uint32_t link = run.get(object + 0x170);
        if (link != 0) {
            uint32_t key = run.get(link + 0x64);
            run.put(object + 0x16c, key);
            uint32_t value = run.call(0x40f680, link, {key});
            run.put(object + 0x174, value);
        }
        uint32_t flags = run.get(object + 0x8);
        flags = flags | 1;
        run.put(object + 0xd0, 0x80);
        run.put(object + 0x8, flags);
        run.call(0x4c79e0, object, {0x52dd04, 0});
        run.put(object + 0x158, 0);
        run.put(object + 0x15c, 0);
        copyRecord(run, object + 0x128, run.get(0x537960) + 0x78);
        uint32_t lowFlags = run.get(object + 0x40);
        uint32_t lower = run.get(object + 0x134);
        uint32_t highFlags = run.get(object + 0x164);
        lowFlags = lowFlags & 0xfffffffe;
        lower = lower + 0x20;
        run.put(object + 0x40, lowFlags);
        highFlags = highFlags | 0x8000;
        uint32_t key = run.get(object + 0x64);
        run.put(object + 0x134, lower);
        run.put(object + 0x164, highFlags);
        if (key == 0) {
            uint32_t again = run.get(object + 0x8);
            run.put(object + 0x64, 0x7d0);
            again = again | 0x20000;
            run.put(object + 0x8, again);
        }
        if (run.get(object + 0x148) == 0)
            run.put(object + 0x148, 0x19);
        if (run.get(object + 0x110) == 0)
            run.put(object + 0x110, 4);
        run.put(record + 0x1c, 5);
        uint32_t parent = run.get(object + 0x170);
        if (parent == 0)
            return 1;
        uint32_t middle = halfSum(run.get(parent + 0x64), run.get(parent + 0x68));
        run.put(record + 0x64, middle);
        return 1;
    }
    if (state == 0x3ea) {
        uint32_t owner = run.get(object + 0xc);
        uint32_t sibling = run.get(owner + 0x28);
        if (run.get(sibling + 0x30) == 0) {
            uint32_t local = run.automatic(4);
            run.put(local, 0);
            run.call(0x4f6286, sibling + 0x10, {0x52dd24, local});
            uint32_t found = run.get(local);
            if (found != 0)
                run.call(0x4208e0, found, {run.get(0x532c10), 0, 0, 0});
        }
        run.put(record + 0x1c, 0x3ed);
        return 1;
    }
    if (state > 0x3ea) {
        if (state == 0x3ed) {
            run.call(0x4c82a0, object + 0x188, {run.get(0x5430c4)});
            if (run.get(object + 0x16c) == run.get(record + 0x64))
                run.put(object + 0xd0, 1);
            if (run.get(object + 0x1a4) == 0)
                return 1;
            if (run.get(object + 0x19c) != 0)
                return 1;
            uint32_t flags = run.get(object + 0x40);
            flags = flags | 1;
            run.put(object + 0x40, flags);
            run.put(record + 0x1c, 0x17);
            uint32_t world = run.get(0x537e88);
            uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
            run.put(record + 0x64, run.get(table + 0x80));
            return 1;
        }
        if (state == 0x457) {
            if (run.get(0x53725c) != 0)
                return 1;
            uint32_t speed = run.get(object + 0x148);
            run.put(record + 0x1c, 0x3ea);
            run.put(record + 0x20, speed);
            return 1;
        }
        return 1;
    }
    if (state == 0x17) {
        uint32_t world = run.get(0x537e88);
        uint32_t table = run.get(run.get(world + 0x6c) + 0x14);
        uint32_t key = run.get(record + 0x64);
        if (s32(key) >= s32(run.get(table + 0x80)))
            return 1;
        run.put(record + 0x1c, 0);
        return 1;
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x49d860:
        return function_49d860(run, receiver, arguments);
    case 0x49e470:
        return function_49e470(run, receiver, arguments);
    case 0x49e4b0:
        return function_49e4b0(run, receiver, arguments);
    case 0x49e4e0:
        return function_49e4e0(run, receiver, arguments);
    case 0x49e7b0:
        return function_49e7b0(run, receiver, arguments);
    case 0x49e7d0:
        return function_49e7d0(run, receiver, arguments);
    case 0x49e7f0:
        return function_49e7f0(run, receiver, arguments);
    case 0x4ca610:
        return function_4ca610(run, receiver, arguments);
    case 0x49cdd0:
        return function_49cdd0(run, receiver, arguments);
    case 0x49daf0:
        return function_49daf0(run, receiver, arguments);
    case 0x49db10:
        return function_49db10(run, receiver, arguments);
    case 0x49db30:
        return function_49db30(run, receiver, arguments);
    case 0x49db50:
        return function_49db50(run, receiver, arguments);
    case 0x49db70:
        return function_49db70(run, receiver, arguments);
    case 0x49ee20:
        return function_49ee20(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_pegs_and_elevators_01_entry, owned, body)
