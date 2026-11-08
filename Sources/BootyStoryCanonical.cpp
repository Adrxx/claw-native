// Original default Booty story sequence
// Recovered from the hash-verified original packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40b600:
        return 1;
    case 0x40b620:
        return 0;
    case 0x40b860:
        return 3;
    case 0x40bc80:
        return 0;
    case 0x40bca0:
        return 1;
    case 0x40bd50:
        return 1;
    case 0x40bd60:
        return 0;
    case 0x40be60:
        return 0;
    case 0x40bed0:
        return 0;
    case 0x40bf30:
        return 2;
    case 0x40bf80:
        return 0;
    case 0x40bfd0:
        return 0;
    case 0x40c150:
        return 1;
    case 0x40c4f0:
        return 1;
    case 0x40d1a0:
        return 1;
    case 0x4b95b0:
        return 5;
    case 0x4ca900:
        return 2;
    case 0x4ca9e0:
        return 1;
    case 0x4caa20:
        return 1;
    case 0x4caa90:
        return 0;
    case 0x4d4190:
        return 1;
    default:
        return -1;
    }
}

// Story +0xc services; display +0x10/+0x14/+0x18 primary/front/back.
struct Frame {
    Run &run;
    uint32_t saved;
    Frame(Run &run, uint32_t delta) : run(run), saved(run.frame) {
        run.frame -= delta;
    }
    ~Frame() {
        run.frame = saved;
    }
};
uint32_t service(Run &run, uint32_t story, uint32_t offset) {
    return run.get(run.get(story + 0x0c) + offset);
}
uint32_t registry(Run &run, uint32_t app) {
    return run.get(run.get(app + 0x30) + 0x28);
}
void timer(Run &run, uint32_t field) {
    uint32_t remaining = run.get(field);
    uint32_t elapsed = run.get(0x53720c);
    run.put(field, elapsed < remaining ? remaining - elapsed : 0);
}
uint32_t lookup(Run &run, uint32_t app, uint32_t key, uint32_t output) {
    run.put(output, 0);
    run.call(0x4f6286, registry(run, app) + 0x10, {key, output});
    return run.get(output);
}
uint32_t audioStatus(Run &run, uint32_t audio, uint32_t depth) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.automatic(-int32_t(depth));
    uint32_t result = run.call(0x4b3e70, audio);
    run.stackPointer = saved;
    return result;
}
void hideCursor(Run &run) {
    uint32_t method = run.get(0x546d54);
    while (s32(run.call(method, 0, {0})) >= 0) {
    }
}
void postExit(Run &run, uint32_t story) {
    uint32_t app = run.get(story + 0x04);
    run.put(story + 0x158, 1);
    run.icall(0x546d50, {run.get(run.get(app + 0x04) + 0x04), 0x111, 0x807c, 0});
}
uint32_t function_40b620(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40bc80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40bf80(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_40bfd0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ca9e0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4caa20(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4caa90(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4b95b0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x40b600. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40b600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    {
        Frame frame(run, 0x08);
        function_40b620(run, receiver, nullptr);
    }
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x40b620. thiscall, 0 stack argument(s), returns void.
uint32_t function_40b620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50b544);
    {
        Frame frame(run, 0x18);
        function_40bc80(run, receiver, nullptr);
    }
    run.call(0x4f6584, receiver + 0x168);
    run.call(0x4f6584, receiver + 0x15c);
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver);
    return 0;
}

// 0x40b860. thiscall, 3 stack argument(s), returns u32.
uint32_t function_40b860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!run.call(0x48f0d0, receiver, {arguments[0], arguments[1], arguments[2]})) {
        return 0;
    }
    run.put(0x5349a0, 0);
    run.put(receiver + 0x158, 0);
    run.put(receiver + 0x160, 0);
    run.put(receiver + 0x164, 0);
    run.put(receiver + 0x154, 0);
    run.put(0x523b50, 0xffffffff);
    uint32_t dir = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523b1c});
    run.put(receiver + 0x20, dir);
    if (!dir) {
        return 0;
    }
    dir = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, dir);
    if (!dir) {
        return 0;
    }
    uint32_t images = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523ce0});
    if (!images) {
        return 0;
    }
    run.vcall(service(run, receiver, 0x10), 0x48, {images, 0x523b14, 0x523728});
    uint32_t animations = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523cd8});
    if (!animations) {
        return 0;
    }
    run.call(0x4ce0d0, service(run, receiver, 0x2c), {animations, 0x523b14, 0x523728});
    uint32_t level = run.get(receiver + 0x14);
    if (s32(level) < 1 || s32(level) > 14) {
        return 0;
    }
    uint32_t number = run.automatic(0x08);
    uint32_t logicName = run.automatic(-0x48);
    uint32_t imageName = run.automatic(0x0c);
    uint32_t animName = run.automatic(0x04);
    run.call(0x4f6439, number);
    run.call(0x4f4f58, 0, {number, 0x523cc8, level < 10 ? 0x523cd4u : 0x523cd0u, level});
    if (level & 1) {
        run.put(0x5349a0, 1);
    }
    if (!(level & 1) || level >= 12) {
        run.put(0x5349a0, 0);
    }
    run.call(0x4f65f2, logicName, {0x5224b8});
    if (!run.get(0x5349a0)) {
        run.call(0x4f66cc, logicName, {0x5224a8});
    }
    uint32_t manager = service(run, receiver, 0x08);
    uint32_t logicChars = run.call(0x4f6974, logicName, {1});
    uint32_t actor = run.call(0x4c8da0, manager, {0, 0, 0, 9999, logicChars, 0});
    run.put(receiver + 0x160, actor);
    run.call(0x4f65f2, imageName, {0x523cb0});
    run.call(0x4f695c, imageName, {number});
    if (level == 13) {
        run.call(0x4f6920, imageName, {0x523ca4});
        run.call(0x4c7900, run.get(receiver + 0x160), {run.get(imageName), 1});
        run.call(0x4c79e0, run.get(receiver + 0x160), {0x523c94, 0});
    } else {
        run.call(0x4c7900, run.get(receiver + 0x160), {run.get(imageName), 1});
        if (!run.get(0x5349a0)) {
            run.call(0x4f6439, animName);
            run.call(0x4f4f58, 0, {animName, 0x523c88, level});
            run.call(0x4c79e0, run.get(receiver + 0x160), {run.get(animName), 0});
            run.call(0x4f6584, animName);
        }
    }
    uint32_t logic = run.get(run.get(receiver + 0x160) + 0x6c);
    run.put(logic + 0x64, 1);
    run.put(logic + 0x68, level);
    run.put(logic + 0x134, 5000);
    if (level == 14) {
        run.put(logic + 0x68, 17);
    }
    if (run.get(0x5349a0) && level != 1) {
        run.put(logic + 0x64, 0);
        run.put(logic + 0x134, 2000);
        actor = run.call(0x4c8da0, service(run, receiver, 0x08), {0, 0xffffffce, 0xffffffce, 0x270e, 0x522494, 0});
        run.put(receiver + 0x164, actor);
        run.call(0x4c7900, actor, {0x523c78, 1});
        uint32_t linked = run.get(run.get(receiver + 0x164) + 0x6c);
        if (linked) {
            run.put(linked + 0x64, level);
            run.put(linked + 0x168, logic);
            run.put(linked + 0x134, 5000);
        }
    }
    uint32_t sequence = level * 2 - 1;
    run.call(0x4f4f58, 0, {number, 0x523cc8, sequence < 10 ? 0x523cd4u : 0x523cd0u, sequence});
    run.call(0x4f667d, receiver + 0x15c, {number});
    run.call(0x4f6920, receiver + 0x15c, {run.get(0x5349a0) ? 0x523c74u : 0x523c6cu});
    static const uint32_t voices[] = {0x523c58, 0x523c44, 0x523c30, 0x523c1c, 0x523c08, 0x523bf4, 0x523be0, 0x523bcc, 0x523bb8, 0x523ba4, 0x523b90, 0x523b7c, 0x523b68, 0x523b54};
    run.call(0x4f66cc, receiver + 0x168, {voices[level - 1]});
    hideCursor(run);
    run.call(0x4f6584, imageName);
    run.call(0x4f6584, logicName);
    run.call(0x4f6584, number);
    return 1;
}

// 0x40bc80. thiscall, 0 stack argument(s), returns void.
uint32_t function_40bc80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.call(0x4c89e0, service(run, receiver, 0x08));
    run.call(0x48f180, receiver);
    return 0;
}

// 0x40bca0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_40bca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t result;
    {
        Frame frame(run, 0x10);
        result = function_40bf80(run, receiver, nullptr);
    }
    run.call(0x4f66cc, 0x53499c, {run.get(0x5349a0) ? 0x523cf8u : 0x523ce8u});
    uint32_t output = run.automatic(-0x04);
    uint32_t entry = lookup(run, run.get(receiver + 0x04), run.get(0x53499c), output);
    if (entry) {
        if (run.get(0x5349a0)) {
            if (run.get(0x532c0c)) {
                run.call(0x4b3dc0, run.get(entry + 0x10), {0x19, 0, 0, 1});
            }
            uint32_t savedStack = run.stackPointer;
            // 0x40bd25: three arguments below the saved EDI/ESI/local frame.
            run.stackPointer = run.automatic(-0x1c);
            run.call(0x4b3fe0, run.get(entry + 0x10), {0x50, 0x2ee, 0});
            run.stackPointer = savedStack;
        } else if (run.get(0x532c0c)) {
            run.call(0x4b3dc0, run.get(entry + 0x10), {100, 0, 0, 0});
        }
    }
    return result;
}

// 0x40bd50. stdcall, 1 stack argument(s), returns u32.
uint32_t function_40bd50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 1;
}

// 0x40bd60. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40bd60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (run.get(0x523b50) != 0xffffffff) {
        timer(run, 0x523b50);
    }
    {
        Frame frame(run, 0x10);
        function_40bfd0(run, receiver, nullptr);
    }
    run.call(0x4b3490, run.get(0x537200));
    if (((run.get(run.get(0x537200) + 0x210) & 0xffffff) || !run.get(0x523b50)) && !run.get(receiver + 0x158)) {
        postExit(run, receiver);
    }
    run.vcall(service(run, receiver, 0x08), 0x24, {1});
    uint32_t services = run.get(receiver + 0x0c);
    uint32_t display = run.get(services + 0x04);
    run.vcall(run.get(services + 0x0c), 0x34, {run.get(display + 0x14), run.get(display + 0x18)});
    run.vcall(run.get(services + 0x08), 0x28, {run.get(run.get(services + 0x04) + 0x14)});
    display = service(run, receiver, 0x04);
    run.call(0x4b98b0, run.get(run.get(display + 0x10) + 0x2c), {0});
    uint32_t back = run.get(display + 0x18);
    run.call(0x4b9d80, run.get(run.get(display + 0x14) + 0x2c), {0, 0, run.get(back + 0x2c), back + 0x1c, 0x10});
    return 1;
}

// 0x40be60. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40be60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!run.call(0x4ca930, service(run, receiver, 0x04))) {
        return 0;
    }
    uint32_t result;
    {
        Frame frame(run, 0x0c);
        result = function_40bf80(run, receiver, nullptr);
    }
    uint32_t images = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523ce0});
    if (!images) {
        return 0;
    }
    if (run.vcall(service(run, receiver, 0x10), 0x4c, {images, 0x523b14, 0x523728}) == 0xffffffff) {
        return 0;
    }
    hideCursor(run);
    return result;
}

// 0x40bed0. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40bed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!run.vcall(receiver, 0x0c) || !run.get(receiver + 0x2c)) {
        return 0;
    }
    uint32_t result;
    {
        Frame frame(run, 0x10);
        result = function_40bf80(run, receiver, nullptr);
    }
    hideCursor(run);
    return run.call(0x48f470, receiver, {0xfa}) ? result : 0;
}

// 0x40bf30. thiscall, 2 stack argument(s), returns u32.
uint32_t function_40bf30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t key = arguments[0];
    if ((key == 0x1b || key == 0x20 || key == 0x0d) && !run.get(receiver + 0x158)) {
        postExit(run, receiver);
    }
    return 1;
}

// 0x40bf80. thiscall, 0 stack argument(s), returns u32.
uint32_t function_40bf80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.call(0x48ffa0, receiver, {run.get(receiver + 0x15c), 1, 0, 1});
    {
        Frame frame(run, 0x0c);
        uint32_t display = service(run, receiver, 0x04);
        uint32_t arg[] = {run.get(display + 0x14)};
        function_4ca9e0(run, display, arg);
    }
    {
        Frame frame(run, 0x08);
        function_4caa90(run, service(run, receiver, 0x04), nullptr);
    }
    {
        Frame frame(run, 0x0c);
        uint32_t arg[] = {1};
        function_4caa20(run, service(run, receiver, 0x04), arg);
    }
    return 1;
}

// 0x40bfd0. thiscall, 0 stack argument(s), returns void.
uint32_t function_40bfd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (run.get(0x523b50)) {
        return 0;
    }
    uint32_t text = run.automatic(-0x18);
    uint32_t output = run.automatic(-0x14);
    run.call(0x4f65f2, text, {0x523d28});
    if (run.get(receiver + 0x14) == 0x0e) {
        run.call(0x4f66cc, text, {0x523d18});
    }
    if (run.get(0x5349a0)) {
        run.call(0x4f66cc, text, {0x523d08});
    }
    uint32_t entry = lookup(run, run.get(0x5371fc), run.get(text), output);
    bool hold = entry && audioStatus(run, run.get(entry + 0x10), 0x24);
    if (!hold) {
        entry = lookup(run, run.get(receiver + 0x04), run.get(receiver + 0x168), output);
        if (entry) {
            if (audioStatus(run, run.get(entry + 0x10), 0x24)) {
                hold = true;
            } else if (!run.get(receiver + 0x154)) {
                if (run.get(0x532c0c)) {
                    run.call(0x4b3dc0, run.get(entry + 0x10), {100, 0, 0, 0});
                }
                run.put(receiver + 0x154, 1);
                hold = true;
            } else if (!run.get(0x5349a0)) {
                entry = lookup(run, run.get(receiver + 0x04), run.get(0x53499c), output);
                hold = entry && audioStatus(run, run.get(entry + 0x10), 0x24);
            }
        }
    }
    if (hold) {
        run.put(0x523b50, 1);
    }
    run.call(0x4f6584, text);
    return 0;
}

// 0x40c150. cdecl, 1 stack argument(s), returns u32.
uint32_t function_40c150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    static const uint32_t coords[] = {0xffffff9c, 0xffffff10, 0x2e4, 0xffffff10, 0xffffff9c, 0xffffff06, 0x2e4, 0xffffff06, 0xffffff9c, 0xffffff10, 0xffffff9c, 0x280, 0x230, 0x181, 0x6d, 0x13c, 0x113, 0xde, 0x13c, 0x16b, 0x1f6, 0x125, 0x1e3, 0x70};
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    uint32_t scratch = run.automatic(0x04);
    if (!state) {
        uint32_t level = run.get(logic + 0x68);
        run.put(logic + 0x1c, 5);
        uint32_t index = uint32_t(s32(level + 1) / 2) - 1;
        run.put(logic + 0x94, index);
        run.put(actor + 0x4c, coords[index * 2]);
        run.put(actor + 0x50, coords[index * 2 + 1]);
    } else if (state == 5) {
        timer(run, logic + 0x134);
        if (!run.get(logic + 0x134) && run.get(logic + 0x64)) {
            run.put(logic + 0x1c, 0x2330);
        }
    } else if (state == 0x2330) {
        uint32_t index = run.get(logic + 0x94) * 2;
        run.put(logic + 0x130, 2000);
        uint32_t endX = coords[index + 12];
        uint32_t startX = coords[index];
        run.put(logic + 0x30, endX);
        uint32_t startY = coords[index + 1];
        uint32_t endY = coords[index + 13];
        run.put(scratch, endX - startX);
        double dx = double(s32(endX - startX));
        run.put(logic + 0x2c, startX);
        run.put(logic + 0x38, endY);
        volatile double speed = dx * run.getd(0x50b5a8);
        run.put(scratch, endY - startY);
        run.put(logic + 0x34, startY);
        volatile double scaled = speed * run.getd(0x50b5b0);
        run.putf(logic + 0x160, float(scaled));
        run.putf(logic + 0x140, float(double(s32(endY - startY)) / dx));
        if (run.get(0x5371fc)) {
            uint32_t entry = lookup(run, run.get(0x5371fc), 0x523d34, scratch);
            if (entry && run.get(0x532c0c)) {
                run.call(0x4b3dc0, run.get(entry + 0x10), {100, 0, 0, 0});
            }
        }
        run.put(logic + 0x1c, 0x2331);
    } else if (state == 0x2331) {
        timer(run, logic + 0x130);
        volatile double step1 = double(run.get(0x53720c)) * double(run.getf(logic + 0x160));
        volatile double step = step1 * run.getd(0x50b598);
        uint32_t current = run.get(actor + 0x4c);
        uint32_t target = run.get(logic + 0x30);
        bool positive = step > run.getd(0x50b5a0);
        bool complete = true;
        if ((positive && s32(current) < s32(target)) || (!positive && s32(current) > s32(target))) {
            uint32_t moved = current + run.call_x87(0x4a30e0, 0, step);
            run.put(actor + 0x4c, moved);
            target = run.get(logic + 0x30);
            if ((positive && s32(moved) < s32(target)) || (!positive && s32(moved) > s32(target))) {
                complete = false;
            } else {
                run.put(actor + 0x4c, target);
            }
        }
        uint32_t dx = run.get(actor + 0x4c) - run.get(logic + 0x2c);
        run.put(scratch, dx);
        double dy = double(s32(dx)) * double(run.getf(logic + 0x140));
        uint32_t converted = run.call_x87(0x4a30e0, 0, dy);
        run.put(actor + 0x50, converted + run.get(logic + 0x34));
        if (complete) {
            run.put(actor + 0x4c, run.get(logic + 0x30));
            run.put(actor + 0x50, run.get(logic + 0x38));
            if (run.get(0x523b50) == 0xffffffff) {
                run.put(0x523b50, 0);
            }
            if (run.get(0x5371fc)) {
                uint32_t entry = lookup(run, run.get(0x5371fc), 0x523d34, scratch);
                if (entry && audioStatus(run, run.get(entry + 0x10), 0x7c)) {
                    run.call(0x4b3e30, run.get(entry + 0x10));
                }
                entry = lookup(run, run.get(0x5371fc), 0x523d08, scratch);
                if (entry && run.get(0x532c0c)) {
                    run.call(0x4b3dc0, run.get(entry + 0x10), {100, 0, 0, 0});
                }
            }
            run.put(logic + 0x1c, 0x232f);
        }
    }
    return 1;
}

// 0x40c4f0. cdecl, 1 stack argument(s), returns u32.
uint32_t function_40c4f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    static const uint32_t coords[] = {
        0xe1, 0x3d, 0xd4, 0x45, 0xc5, 0x47, 0xb5, 0x46, 0xa6, 0x43,
        0x96, 0x43, 0x88, 0x47, 0x79, 0x49, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0x24, 0x67, 0x1e, 0x73, 0x1e, 0x81, 0x24, 0x8d, 0x2b, 0x99,
        0x31, 0xa5, 0x31, 0xb3, 0x2f, 0xc1, 0x2c, 0xcf, 0x30, 0xdc,
        0x39, 0xe7, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0x77, 0xe4, 0x85, 0xe3, 0x91, 0xea, 0x98, 0xf6, 0x9a, 0x104,
        0xa1, 0x110, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xe0, 0x12d, 0xd6, 0x138, 0xce, 0x144, 0xc4, 0x14f, 0xba, 0x15a,
        0xae, 0x164, 0xa1, 0x16d, 0x98, 0x17b, 0x97, 0x18a, 0x9b, 0x198,
        0xa3, 0x1a4, 0xad, 0x1af, 0xba, 0x1b9, 0xc9, 0x1bf, 0xda, 0x1bf,
        0xe8, 0x1b6, 0xf8, 0x1b2, 0x108, 0x1b1, 0x119, 0x1b0, 0x12a, 0x1ad,
        0x13a, 0x1aa, 0x14b, 0x1a6, 0x15c, 0x1a2, 0x16a, 0x198, 0x176, 0x18c,
        0x17b, 0x17e, 0x179, 0x16f, 0x172, 0x162, 0x168, 0x159, 0x15e, 0x150,
        0x16f, 0x132, 0x17c, 0x134, 0x186, 0x12c, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
        0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
    };
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state == 0) {
        timer(run, logic + 0x134);
        if (!run.get(logic + 0x134)) {
            run.put(logic + 0x1c, 0x2332);
        }
    } else if (state == 0x232b) {
        run.put(logic + 0x130, 400);
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        run.put(logic + 0x1c, 0x232c);
    } else if (state == 0x2332) {
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        uint32_t level = run.get(logic + 0x64) + 1;
        run.put(logic + 0x1c, 0x232b);
        uint32_t index = uint32_t(s32(level) / 2) - 1;
        if (s32(index) <= 0) {
            run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000);
        } else {
            --index;
            uint32_t step = run.get(0x5349a4);
            if (s32(index) < 0 || s32(index) >= 5 || s32(step) < 0 || s32(step) >= 30) {
                run.put(logic + 0x1c, 0x232f);
            } else {
                uint32_t offset = (step + index * 30) * 2;
                if (coords[offset] == 0xffffffff || coords[offset + 1] == 0xffffffff) {
                    run.put(logic + 0x1c, 0x232d);
                } else {
                    run.put(actor + 0x4c, coords[offset]);
                    run.put(actor + 0x50, coords[(run.get(0x5349a4) + index * 30) * 2 + 1]);
                }
            }
        }
    } else if (state == 0x232c) {
        timer(run, logic + 0x130);
        if (!run.get(logic + 0x130)) {
            if (run.get(0x5371fc)) {
                uint32_t text = run.automatic(-0x4cc);
                uint32_t output = run.automatic(-0x4c8);
                run.call(0x4f65f2, text, {(run.get(0x5349a4) & 1) ? 0x523d50u : 0x523d44u});
                uint32_t audio = registry(run, run.get(0x5371fc));
                if (!run.get(audio + 0x30)) {
                    run.put(output, 0);
                    run.call(0x4f6286, audio + 0x10, {run.get(text), output});
                    uint32_t entry = run.get(output);
                    if (entry && run.get(0x532c0c)) {
                        run.call(0x4b45f0, run.get(entry + 0x10), {run.get(0x532c10), 0, 0, 0});
                    }
                }
                run.call(0x4f6584, text);
            }
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffe);
            run.put(logic + 0x1c, 0x232f);
            uint32_t step = run.get(0x5349a4) + 1;
            run.put(0x5349a4, step);
            if (step == 30) {
                run.put(logic + 0x1c, 0x232d);
            } else {
                uint32_t child = run.call(0x4c8da0, run.get(run.get(run.get(0x5371fc) + 0x30) + 0x08), {0, 0xffffffce, 0xffffffce, 0x270e, 0x522494, 0});
                if (child) {
                    run.call(0x4c7900, child, {0x523c78, 1});
                }
                uint32_t next = run.get(child + 0x6c);
                if (next) {
                    run.put(next + 0x64, run.get(logic + 0x64));
                    run.put(next + 0x168, run.get(logic + 0x168));
                    run.put(next + 0x134, 0);
                }
            }
        }
    } else if (state == 0x232d) {
        run.put(0x5349a4, 0);
        run.put(logic + 0x130, 300);
        run.put(logic + 0x1c, 0x232e);
    } else if (state == 0x232e) {
        timer(run, logic + 0x130);
        if (!run.get(logic + 0x130)) {
            uint32_t linked = run.get(logic + 0x168);
            if (linked) {
                run.put(linked + 0x64, 1);
                run.put(logic + 0x1c, 0x232f);
            }
        }
    }
    return 1;
}

// 0x40d1a0. cdecl, 1 stack argument(s), returns u32.
uint32_t function_40d1a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t actor = arguments[0];
    uint32_t logic = run.get(actor + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (!state) {
        static const uint32_t coords[] = {0x16c, 0xa2, 0xef, 0x156, 0x161, 0x16c, 0xd6, 0x106, 0x113, 0xa3, 0x18e, 0x155, 0x11c, 0x170, 0x1a7, 0x107, 0x140, 0xf9};
        run.put(actor + 0x40, run.get(actor + 0x40) | 1);
        uint32_t incremented = run.get(logic + 0x68) + 1;
        run.put(logic + 0xa4, 0);
        uint32_t index = uint32_t(s32(incremented) / 2) - 1;
        if (s32(index) < 0 || s32(index) >= 9) {
            run.put(logic + 0x1c, 0x232f);
            return 0;
        }
        run.put(actor + 0x4c, coords[index * 2]);
        run.put(actor + 0x50, coords[index * 2 + 1]);
        run.put(logic + 0x1c, 5);
        return 1;
    }
    if (state != 5) {
        return 1;
    }
    timer(run, logic + 0x134);
    if (run.get(logic + 0x134)) {
        return 1;
    }
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffe);
    run.call(0x4c82a0, actor + 0x188, {run.get(0x5430c4)});
    uint32_t text = run.automatic(0x04);
    uint32_t output = run.automatic(-0x58);
    run.call(0x4f65f2, text, {0x523d28});
    if (run.get(logic + 0x68) == 17) {
        run.call(0x4f66cc, text, {0x523d18});
    }
    uint32_t entry = lookup(run, run.get(0x5371fc), run.get(text), output);
    if (!run.get(logic + 0xa4) && entry) {
        if (!audioStatus(run, run.get(entry + 0x10), 0x6c)) {
            if (run.get(0x532c0c)) {
                run.call(0x4b3dc0, run.get(entry + 0x10), {100, 0, 0, 0});
            }
            run.put(logic + 0xa4, 1);
        }
    }
    uint32_t playing = entry ? audioStatus(run, run.get(entry + 0x10), 0x6c) : 0;
    if (run.get(actor + 0x1a4) && !run.get(actor + 0x19c) && !playing) {
        if (run.get(logic + 0x68) == 13) {
            uint32_t child = run.call(0x4c8da0, run.get(run.get(run.get(0x5371fc) + 0x30) + 0x08), {0, 0xffffff9c, 0xffffff9c, 9999, 0x5224a8, 0});
            run.put(child + 0x40, run.get(child + 0x40) | 1);
            run.call(0x4c7900, child, {0x523d6c, 1});
            run.call(0x4c79e0, child, {0x523d5c, 0});
            uint32_t linked = run.get(child + 0x6c);
            run.put(linked + 0x68, 15);
            run.put(linked + 0x134, 2000);
        } else {
            run.put(0x523b50, 0);
        }
        run.put(logic + 0x1c, 0x232f);
    }
    run.call(0x4f6584, text);
    return 1;
}

// 0x4b95b0. thiscall, 5 stack argument(s), returns u32.
uint32_t function_4b95b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!arguments[3]) {
        return 0;
    }
    uint32_t result = 0;
    if (arguments[2] == 1) {
        result = run.call(0x4bdda0, receiver, {arguments[0], arguments[1], arguments[3]});
    } else if (arguments[2] == 2) {
        result = run.call(0x4bebc0, receiver, {arguments[0], arguments[1], arguments[3]});
    } else if (arguments[2] == 4) {
        result = run.call(0x4bf680, receiver, {arguments[0], arguments[1], arguments[3], arguments[4]});
    }
    return result ? 1 : 0;
}

// 0x4ca900. thiscall, 2 stack argument(s), returns u32.
uint32_t function_4ca900(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t image = run.get(receiver + (arguments[1] == 2 ? 0x18 : 0x14));
    return image ? run.vcall(image, 0x30, {arguments[0]}) : 0;
}

// 0x4ca9e0. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4ca9e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t primary = run.get(receiver + 0x10);
    if (!primary) {
        return 0;
    }
    uint32_t surface = run.get(primary + 0x2c);
    if (!surface) {
        return 0;
    }
    uint32_t other = run.get(arguments[0] + 0x2c);
    if (!other) {
        return 0;
    }
    return run.call(0x4b9c50, other, {surface}) == 0;
}

// 0x4caa20. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4caa20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (run.vcall(run.get(receiver + 0x18), 0x14)) {
        return 0;
    }
    uint32_t front = run.get(receiver + 0x14);
    if (!run.vcall(run.get(receiver + 0x18), 0x24, {run.get(front + 0x10), run.get(front + 0x14)})) {
        return 0;
    }
    if (arguments[0]) {
        front = run.get(receiver + 0x14);
        uint32_t surface = run.get(front + 0x2c);
        run.call(0x4b9d80, run.get(run.get(receiver + 0x18) + 0x2c), {0, 0, surface, front + 0x1c, 0x10});
    }
    return 1;
}

// 0x4caa90. thiscall, 0 stack argument(s), returns void.
uint32_t function_4caa90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t back = run.get(receiver + 0x18);
    if (back) {
        run.vcall(back, 0x1c);
    }
    return 0;
}

// 0x4d4190. thiscall, 1 stack argument(s), returns u32.
uint32_t function_4d4190(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t resource = arguments[0];
    uint32_t type = run.call(0x4b61b0, resource);
    uint32_t kind;
    switch (type) {
    case 0x424d50:
        kind = 1;
        break;
    case 0x504358:
        kind = 2;
        break;
    case 0x524944:
        kind = 3;
        break;
    case 0x504944:
        kind = 4;
        break;
    default:
        return 0;
    }
    uint32_t data = run.call(0x4b61c0, resource);
    if (!data) {
        return 0;
    }
    uint32_t args[] = {run.get(run.get(receiver + 0x0c) + 0x1c), data, kind, run.get(resource + 0x14), 0};
    uint32_t result;
    {
        Frame frame(run, 0x24);
        result = function_4b95b0(run, run.get(receiver + 0x2c), args);
    }
    run.call(0x4b6230, resource);
    return result;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40b600:
        return function_40b600(run, receiver, arguments);
    case 0x40b620:
        return function_40b620(run, receiver, arguments);
    case 0x40b860:
        return function_40b860(run, receiver, arguments);
    case 0x40bc80:
        return function_40bc80(run, receiver, arguments);
    case 0x40bca0:
        return function_40bca0(run, receiver, arguments);
    case 0x40bd50:
        return function_40bd50(run, receiver, arguments);
    case 0x40bd60:
        return function_40bd60(run, receiver, arguments);
    case 0x40be60:
        return function_40be60(run, receiver, arguments);
    case 0x40bed0:
        return function_40bed0(run, receiver, arguments);
    case 0x40bf30:
        return function_40bf30(run, receiver, arguments);
    case 0x40bf80:
        return function_40bf80(run, receiver, arguments);
    case 0x40bfd0:
        return function_40bfd0(run, receiver, arguments);
    case 0x40c150:
        return function_40c150(run, receiver, arguments);
    case 0x40c4f0:
        return function_40c4f0(run, receiver, arguments);
    case 0x40d1a0:
        return function_40d1a0(run, receiver, arguments);
    case 0x4b95b0:
        return function_4b95b0(run, receiver, arguments);
    case 0x4ca900:
        return function_4ca900(run, receiver, arguments);
    case 0x4ca9e0:
        return function_4ca9e0(run, receiver, arguments);
    case 0x4caa20:
        return function_4caa20(run, receiver, arguments);
    case 0x4caa90:
        return function_4caa90(run, receiver, arguments);
    case 0x4d4190:
        return function_4d4190(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_booty_story_entry, owned, body)
