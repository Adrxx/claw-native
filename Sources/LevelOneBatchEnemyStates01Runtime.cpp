// Level 1 shared enemy state callbacks, batch 1
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
    case 0x43edd0:
        return 0;
    case 0x43fd10:
        return 0;
    case 0x43fdc0:
        return 0;
    case 0x43f030:
        return 0;
    case 0x43f450:
        return 0;
    case 0x43f540:
        return 0;
    case 0x43f6e0:
        return 0;
    case 0x43f720:
        return 0;
    default:
        return -1;
    }
}

// Global addresses used below: 0x5430c4 animation time step, 0x537210 clock,
// 0x52713c counter, 0x532c0c and 0x532c10 start-effect flag and argument.

// Steps the animation object at scale + 0x188. Enemy fields: +0x12c scale object.
uint32_t stepAnimation(Run &run, uint32_t enemy) {
    uint32_t step = run.get(0x5430c4);
    uint32_t scale = run.get(enemy + 0x12c);
    return run.call(0x4c82a0, scale + 0x188, {step});
}

// The double comparison of the original (fcomp, test ah, 0x40): taken when equal or unordered.
bool equalOrUnordered(double left, double right) {
    if (left < right)
        return false;
    if (left > right)
        return false;
    return true;
}

// 0x43edd0. Steps the animation, then calls virtual slot 0x48 when the owner (+0xc) field +0xcc is 1.
uint32_t function_43edd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t owner = run.get(receiver + 0xc);
    if (run.get(owner + 0xcc) == 1) {
        uint32_t table = run.get(receiver);
        uint32_t method = run.get(table + 0x48);
        run.call(method, receiver, {});
    }
    return 0;
}

// 0x43fd10. When the doubles at +0x68 and +0x80 are equal, converts -[+0x50] and calls slot 0x70.
uint32_t function_43fd10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    double left = run.getd(receiver + 0x68);
    double right = run.getd(receiver + 0x80);
    if (equalOrUnordered(left, right)) {
        double value = run.getd(receiver + 0x50);
        uint32_t table = run.get(receiver);
        uint32_t converted = run.call_x87(0x4a30e0, 0, -value, {});
        uint32_t method = run.get(table + 0x70);
        run.call(method, receiver, {converted});
    }
    return 0;
}

// 0x43fdc0. When the doubles at +0x68 and +0x98 are equal, converts [+0x50] and calls slot 0x6c.
uint32_t function_43fdc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    double left = run.getd(receiver + 0x68);
    double right = run.getd(receiver + 0x98);
    if (equalOrUnordered(left, right)) {
        double value = run.getd(receiver + 0x50);
        uint32_t table = run.get(receiver);
        uint32_t converted = run.call_x87(0x4a30e0, 0, value, {});
        uint32_t method = run.get(table + 0x6c);
        run.call(method, receiver, {converted});
    }
    return 0;
}

// 0x43f030.
uint32_t function_43f030(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t result = stepAnimation(run, receiver);
    if (result == 1) {
        uint32_t counter = run.get(0x52713c);
        if (counter != 0) {
            run.put(0x52713c, counter - 1);
            uint32_t effect = run.get(receiver + 0x3a0);
            if (effect != 0) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t argument = run.get(0x532c10);
                if (enabled != 0) {
                    uint32_t target = run.get(effect + 0x10);
                    run.call(0x4b45f0, target, {argument, 0, 0, 0});
                }
            }
            uint32_t owner = run.get(receiver + 0xc);
            uint32_t source = receiver + 0x220;
            uint32_t destination = owner + 0x138;
            run.put(destination, run.get(source));
            run.put(destination + 0x4, run.get(source + 0x4));
            run.put(destination + 0x8, run.get(source + 0x8));
            run.put(destination + 0xc, run.get(source + 0xc));
            uint32_t scale = run.get(receiver + 0x12c);
            if (run.get8(scale + 0x40) & 2) {
                owner = run.get(receiver + 0xc);
                uint32_t third = run.get(owner + 0x140);
                uint32_t first = run.get(owner + 0x138);
                run.put(owner + 0x138, 0u - third);
                owner = run.get(receiver + 0xc);
                run.put(owner + 0x140, 0u - first);
            }
        }
    }
    uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) != 0) {
        if (run.get(animation + 0x14) == 0) {
            run.put(0x52713c, 1);
            uint32_t table = run.get(receiver);
            uint32_t method = run.get(table + 0x44);
            run.call(method, receiver, {});
            run.put(receiver + 0x20, 2);
        }
    }
    return 0;
}

// 0x43f450. State at +0x304: 0 waits for scale +0x38 == -1, 1 and 2 wait for a clock delay.
uint32_t function_43f450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t state = run.get(receiver + 0x304);
    if (state == 0) {
        uint32_t scale = run.get(receiver + 0x12c);
        if (run.get(scale + 0x38) != 0xffffffffu)
            return 0;
        uint32_t effect = run.get(receiver + 0x38c);
        if (effect != 0) {
            uint32_t enabled = run.get(0x532c0c);
            uint32_t argument = run.get(0x532c10);
            if (enabled != 0) {
                uint32_t target = run.get(effect + 0x10);
                run.call(0x4b45f0, target, {argument, 0, 0, 0});
            }
        }
    } else if (state == 1) {
        uint32_t now = run.get(0x537210);
        uint32_t start = run.get(receiver + 0x3d8);
        uint32_t delay = run.get(receiver + 0x3dc);
        if (now - start < delay)
            return 0;
    } else if (state == 2) {
        uint32_t now = run.get(0x537210);
        uint32_t start = run.get(receiver + 0x3d8);
        uint32_t delay = run.get(receiver + 0x3dc);
        if (now - start < delay)
            return 0;
    } else {
        return 0;
    }
    uint32_t scale = run.get(receiver + 0x12c);
    run.put(scale + 0x8, run.get(scale + 0x8) | 0x10000u);
    return 0;
}

// 0x43f540. After the delay at +0x3e4 from +0x3e0, looks up the entry for index +0x24 in the array at
// 0x537698, destroys the array's pending elements and stores a new string handle.
uint32_t function_43f540(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t now = run.get(0x537210);
    uint32_t start = run.get(receiver + 0x3e0);
    uint32_t delay = run.get(receiver + 0x3e4);
    if (now - start < delay)
        return 0;
    uint32_t low = run.get(0x5376a0);
    uint32_t index = run.get(receiver + 0x24);
    run.put(0x5376b8, 0);
    uint32_t entry = 0;
    bool direct = false;
    if (!(s32(index) < s32(low))) {
        if (!(s32(index) > s32(run.get(0x5376a4))))
            direct = true;
    }
    if (direct) {
        entry = (index - low) * run.get(0x5376b0) + run.get(0x5376a8);
    } else {
        uint32_t found = run.call(0x4db6e0, 0x537698, {index, 0});
        if (found != 0) {
            uint32_t lowAgain = run.get(0x5376a0);
            uint32_t base = run.get(0x5376a8);
            entry = (index - lowAgain) * run.get(0x5376b0) + base;
        } else {
            uint32_t text = run.get(0x544b4c);
            uint32_t code = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53769c);
            run.put(0x544b14, code);
            run.call(0x4db4d0, owner, {0x537698, text, 0xc});
            entry = run.get(0x5376ac);
        }
    }
    uint32_t count = run.get(0x5376b8);
    uint32_t cursor = run.get(0x5376b4);
    while (count != 0) {
        if (cursor != 0)
            run.call(0x4f6439, cursor, {});
        cursor += 4;
        count -= 1;
    }
    uint32_t text = run.call(0x4f6974, entry, {0});
    uint32_t zed = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(zed + 0x1c));
    uint32_t handle = run.call(0x4dba00, 0x537668, {text});
    zed = run.get(receiver + 0x10);
    run.put(zed + 0x1c, handle);
    return 0;
}

// 0x43f720. Clears bit 2 of scale +8 and sets state +0x20 to 2.
uint32_t function_43f720(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t scale = run.get(receiver + 0x12c);
    run.put(scale + 0x8, run.get(scale + 0x8) & 0xfffffffbu);
    run.put(receiver + 0x20, 2);
    return 0;
}

// 0x43f6e0. When owner +0xcc is 1, runs 0x43f720 and then calls slot 0x44.
uint32_t function_43f6e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    stepAnimation(run, receiver);
    uint32_t owner = run.get(receiver + 0xc);
    if (run.get(owner + 0xcc) == 1) {
        function_43f720(run, receiver, nullptr);
        uint32_t table = run.get(receiver);
        uint32_t method = run.get(table + 0x44);
        run.call(method, receiver, {});
    }
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x43edd0:
        return function_43edd0(run, receiver, arguments);
    case 0x43fd10:
        return function_43fd10(run, receiver, arguments);
    case 0x43fdc0:
        return function_43fdc0(run, receiver, arguments);
    case 0x43f030:
        return function_43f030(run, receiver, arguments);
    case 0x43f450:
        return function_43f450(run, receiver, arguments);
    case 0x43f540:
        return function_43f540(run, receiver, arguments);
    case 0x43f6e0:
        return function_43f6e0(run, receiver, arguments);
    case 0x43f720:
        return function_43f720(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_states_01_entry, owned, body)
