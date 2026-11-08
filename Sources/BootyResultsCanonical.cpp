// Booty Results
//
// Canonical owned bodies recovered from the original v1.0 packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x40b020:
        return 1;
    case 0x40b040:
        return 0;
    case 0x40d470:
        return 3;
    case 0x40db10:
        return 1;
    case 0x40db60:
        return 0;
    case 0x40dc10:
        return 0;
    case 0x40dc50:
        return 0;
    case 0x40dca0:
        return 1;
    case 0x40dcb0:
        return 1;
    case 0x40dd50:
        return 0;
    case 0x40de90:
        return 0;
    case 0x40df00:
        return 0;
    case 0x40df60:
        return 0;
    case 0x40e020:
        return 2;
    case 0x40e040:
        return 0;
    case 0x48f470:
        return 1;
    case 0x48ffa0:
        return 4;
    case 0x490370:
        return 0;
    case 0x4903c0:
        return 7;
    case 0x498930:
        return 1;
    case 0x498f90:
        return 1;
    case 0x499170:
        return 1;
    case 0x499450:
        return 1;
    case 0x4995d0:
        return 0;
    case 0x499630:
        return 1;
    case 0x4997c0:
        return 1;
    case 0x4998c0:
        return 1;
    case 0x499c30:
        return 1;
    case 0x499cd0:
        return 1;
    case 0x499d60:
        return 1;
    case 0x4c89e0:
        return 0;
    case 0x4c89f0:
        return 0;
    default:
        return -1;
    }
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);
uint32_t own(Run &run, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}, uint32_t frameBytes = 0x200) {
    uint32_t saved = run.frame;
    run.frame -= frameBytes;
    uint32_t result = body(run, function, receiver, arguments.begin());
    run.frame = saved;
    return result;
}
// Original-backed callees can expose stack-local output addresses through
// physical callbacks, so retain their actual entry ESP at those boundaries.
uint32_t callAt(Run &run, uint32_t depth, uint32_t function, uint32_t receiver, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.frame - depth;
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = saved;
    return result;
}
// Field map: state +0x0c services, +0x20 resources, +0x2c background;
// animation +0x6c logic, +0x170 image set; counter +0x60..0x88 children,
// +0x8c category, +0x90 initial count, +0x94 remaining, +0x98 step,
// +0x9c maximum, +0xa0/+0xa4 destination, +0xa8 scale, +0xb0/+0xb4 totals.
uint32_t service(Run &run, uint32_t object, uint32_t offset) {
    return run.get(run.get(object + 0x0c) + offset);
}
void hideCursor(Run &run) {
    uint32_t method = run.get(0x546d54);
    while (s32(run.call(method, 0, {0})) >= 0) {}
}
void imageDigit(Run &run, uint32_t object, uint32_t digit) {
    uint32_t images = run.get(object + 0x170);
    if (images) {
        uint32_t image = 0;
        if (s32(digit) >= run.gets(images + 0x64) && s32(digit) <= run.gets(images + 0x68))
            image = run.get(run.get(images + 0x14) + digit * 4);
        run.put(object + 0x174, image);
        run.put(object + 0x16c, digit);
    }
}
uint32_t length(Run &run, uint32_t string) {
    uint32_t count = 0;
    while (run.get8(string + count))
        ++count;
    return count;
}
void digits(Run &run, uint32_t counter, uint32_t value, uint32_t buffer, bool external) {
    if (run.get(counter + 0x04) == value)
        return;
    run.put(counter + 0x04, value);
    run.call(0x4a3920, 0, {buffer, 0x52c6f8, value});
    uint32_t cursor = buffer + length(run, buffer) - run.get(counter + 0x08);
    for (uint32_t i = 0; s32(i) < run.gets(counter + 0x08); ++i) {
        uint32_t child = run.get(counter + 0x0c + i * 4);
        uint32_t digit = uint32_t(int32_t(int8_t(run.get8(cursor++)))) - 0x30;
        if (external)
            run.call(0x4209d0, child, {digit});
        else imageDigit(run, child, digit);
        run.put(run.get(child + 0x6c) + 0x68, 0xffffffff);
    }
}
uint32_t allocateCounter(Run &run, uint32_t size) {
    uint32_t object = run.call(0x4f63ec, 0, {size});
    if (object) {
        if (size != 0x34)
            run.put(object + 0x28, 0x50b5cc);
        run.put(object, size == 0x34 ? 0x50b5cc : 0x50b5c4);
    }
    return object;
}
ClawX87State xstate() {
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    return state;
}
void fp(Run &run, ClawX87State &state, uint32_t operation, double operand) {
    uint64_t bits;
    std::memcpy(&bits, &operand, 8);
    run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
}
uint32_t ftol(Run &run, ClawX87State &state) {
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}
uint32_t movement(Run &run, uint32_t logic, uint32_t offset, ClawX87State &state) {
    fp(run, state, CLAW_X87_F64, double(run.getf(logic + offset)));
    fp(run, state, CLAW_X87_MUL_F64, double(run.get(0x53720c)));
    fp(run, state, CLAW_X87_MUL_F64, run.getd(0x50fc48));
    return ftol(run, state);
}
void countdown(Run &run, uint32_t address) {
    uint32_t value = run.get(address);
    uint32_t elapsed = run.get(0x53720c);
    run.put(address, elapsed < value ? value - elapsed : 0);
}
// 0x40b020.
uint32_t function_40b020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    own(run, 0x40b040, receiver, {}, 0x8);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x40b040.
uint32_t function_40b040(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50b494);
    own(run, 0x40dc10, receiver, {}, 0x18);
    run.call(0x4f6584, receiver + 0x180);
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver);
    return 0;
}

// 0x40db10.
uint32_t function_40db10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    own(run, 0x40db60, receiver, {}, 0x8);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x40db60.
uint32_t function_40db60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.put(receiver, 0x50b5bc);
    for (uint32_t offset : {0x60u, 0x64u, 0x68u, 0x6cu}) {
        uint32_t child = run.get(receiver + offset);
        if (child)
            run.vcall(child, 0x00, {1});
    }
    uint32_t count = run.get(0x53cac4) - 1;
    run.put(0x53cac4, count);
    if (!count) {
        for (uint32_t address : {0x53cac8u, 0x53caccu}) {
            uint32_t child = run.get(address);
            if (child)
                run.vcall(child, 0x00, {1});
        }
    }
    run.put(receiver + 0x28, 0x50b014);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x40dc10.
uint32_t function_40dc10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (run.get(receiver + 0x0c)) {
        run.call(0x4caa90, service(run, receiver, 0x04));
        run.vcall(service(run, receiver, 0x10), 0x58);
        run.call(0x4cdf40, service(run, receiver, 0x2c));
        own(run, 0x4c89e0, service(run, receiver, 0x08), {}, 0x8);
    }
    run.call(0x48f180, receiver);
    return 0;
}

// 0x40dc50.
uint32_t function_40dc50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    own(run, 0x48ffa0, receiver, {run.get(receiver + 0x180), 1, 0, 0}, 0x18);
    uint32_t manager = service(run, receiver, 0x04);
    callAt(run, 0xc, 0x4ca9e0, manager, {run.get(manager + 0x14)});
    callAt(run, 0x8, 0x4caa90, service(run, receiver, 0x04));
    callAt(run, 0xc, 0x4caa20, service(run, receiver, 0x04), {1});
    return 1;
}

// 0x40dca0.
uint32_t function_40dca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    return own(run, 0x40dc50, receiver, {}, 0x4);
}

// 0x40dcb0.
uint32_t function_40dcb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t local = run.automatic(-4);
    run.put(local, 0);
    run.call(0x4f6286, service(run, receiver, 0x28) + 0x10, {0x52374c, local});
    if (run.get(receiver + 0x2c)) {
        run.call(0x4bb990, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 0x1f4});
        for (uint32_t i = 0; i < 2; ++i) {
            uint32_t manager = service(run, receiver, 0x04);
            run.stackPointer = run.frame - 0x14;
            run.call(0x4b97c0, run.get(run.get(manager + 0x14) + 0x2c), {0});
            run.stackPointer = 0;
            run.call(0x4b98b0, run.get(run.get(manager + 0x10) + 0x2c), {0});
        }
    }
    return 1;
}

// 0x40dd50.
uint32_t function_40dd50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    run.call(0x4b3490, run.get(0x537200));
    if (run.get(run.get(0x537200) + 0x210) & 0xffffff)
        own(run, 0x40e040, receiver, {}, 0x10);
    if (run.get(run.get(receiver + 0x04) + 0x9c)) {
        run.stackPointer = run.frame - 0x24;
        run.call(0x45fbb0, 0, {run.get(run.get(service(run, receiver, 0x04) + 0x14) + 0x2c), 5, 0, 0x27b, 0x19});
        run.stackPointer = 0;
    }
    run.vcall(service(run, receiver, 0x08), 0x24, {1});
    uint32_t services = run.get(receiver + 0x0c);
    uint32_t manager = run.get(services + 0x04);
    run.vcall(run.get(services + 0x0c), 0x34, {run.get(manager + 0x14), run.get(manager + 0x18)});
    run.vcall(run.get(services + 0x08), 0x28, {run.get(run.get(services + 0x04) + 0x14)});
    manager = service(run, receiver, 0x04);
    run.call(0x4b98b0, run.get(run.get(manager + 0x10) + 0x2c), {0});
    uint32_t back = run.get(manager + 0x18);
    run.call(0x4b9d80, run.get(run.get(manager + 0x14) + 0x2c), {0, 0, run.get(back + 0x2c), back + 0x1c, 0x10});
    bool complete = true;
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t child = run.get(receiver + 0x15c + i * 4);
        if (child && run.get(run.get(child + 0x6c) + 0x1c) != 0x2331)
            complete = false;
    }
    if (complete && !run.get(receiver + 0x154)) {
        run.put(receiver + 0x154, 1);
        run.icall(0x546d50, {run.get(run.get(run.get(receiver + 0x04) + 0x04) + 0x04), 0x111, 0x807c, 0});
    }
    return 1;
}

// 0x40de90.
uint32_t function_40de90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.call(0x4ca930, service(run, receiver, 0x04)))
        return 0;
    uint32_t result = own(run, 0x40dc50, receiver, {}, 0xc);
    uint32_t images = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523ce0});
    if (!images)
        return 0;
    if (run.vcall(service(run, receiver, 0x10), 0x4c, {images, 0x523b14, 0x523728}) == 0xffffffff)
        return 0;
    hideCursor(run);
    return result;
}

// 0x40df00.
uint32_t function_40df00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.vcall(receiver, 0x0c))
        return 0;
    if (!run.get(receiver + 0x2c))
        return 0;
    uint32_t result = own(run, 0x40dc50, receiver, {}, 0x10);
    hideCursor(run);
    return own(run, 0x48f470, receiver, {0xfa}, 0x14) ? result : 0;
}

// 0x40df60.
uint32_t function_40df60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.vcall(receiver, 0x0c))
        return 0;
    if (!own(run, 0x490370, receiver, {}, 0x10))
        return 0;
    uint32_t manager = service(run, receiver, 0x04);
    uint32_t back = run.get(manager + 0x18);
    uint32_t front = run.get(manager + 0x14);
    if (back && front)
        run.call(0x4b9d80, run.get(front + 0x2c), {0, 0, run.get(back + 0x2c), back + 0x1c, 0x10});
    uint32_t services = run.get(receiver + 0x0c);
    manager = run.get(services + 0x04);
    run.vcall(run.get(services + 0x0c), 0x34, {run.get(manager + 0x14), run.get(manager + 0x18)});
    run.vcall(run.get(services + 0x08), 0x28, {run.get(run.get(services + 0x04) + 0x14)});
    manager = service(run, receiver, 0x04);
    run.call(0x4b98b0, run.get(run.get(manager + 0x10) + 0x2c), {0});
    back = run.get(manager + 0x18);
    run.call(0x4b9d80, run.get(run.get(manager + 0x14) + 0x2c), {0, 0, run.get(back + 0x2c), back + 0x1c, 0x10});
    hideCursor(run);
    return 1;
}

// 0x40e020.
uint32_t function_40e020(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t key = arguments[0];
    if (key == 0x1b || key == 0x20 || key == 0x0d)
        own(run, 0x40e040, receiver, {}, 0x4);
    return 1;
}

// 0x40e040.
uint32_t function_40e040(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t child = run.get(receiver + 0x15c + i * 4);
        if (!child)
            continue;
        uint32_t logic = run.get(child + 0x6c);
        uint32_t state = run.get(logic + 0x1c);
        if (run.get(0x52d4e0) == 0xffffffff && state == 0x2334)
            run.put(logic + 0x138, 0);
        else if (state == 0x2331 || state == 0x232c || state == 0x232d || state == 0x232e || state == 0x232f || state == 0x2329 || state == 0x2334)
            run.put(logic + 0x138, run.get(0x52d4e4));
        else run.put(logic + 0x1c, 0x2330);
    }
    return 1;
}

// 0x48f470.
uint32_t function_48f470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t background = run.get(receiver + 0x2c);
    if (!background)
        return 0;
    run.call(0x4bbd20, run.get(background + 0x10));
    uint32_t duration = arguments[0];
    background = run.get(receiver + 0x2c);
    uint32_t palette = run.get(background + 0x10);
    if (duration)
        run.call(0x4bb910, palette, {0, 0x100, 0, 0, 0, 0});
    else run.call(0x4bb8c0, palette, {0});
    background = run.get(receiver + 0x2c);
    run.put(service(run, receiver, 0x18) + 0x64, background);
    run.vcall(background, 0x34);
    if (duration) {
        palette = run.get(run.get(receiver + 0x2c) + 0x10);
        run.call(0x4bbd90, palette, {0, 0x100, run.get(palette + 0x10), duration});
    }
    return 1;
}

// 0x48ffa0.
uint32_t function_48ffa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.get(receiver + 0x0c) || !run.get(receiver + 0x08) || !run.get(receiver + 0x20))
        return 0;
    uint32_t name = arguments[0];
    uint32_t buffer = run.automatic(-0x40);
    run.call(0x4a3920, 0, {buffer, 0x528e54, name});
    uint32_t resource = run.call(0x4b7dc0, run.get(receiver + 0x20), {buffer, 0x504358});
    if (!resource)
        return 0;
    uint32_t background = run.get(receiver + 0x2c);
    if (background) {
        run.call(0x4d46f0, service(run, receiver, 0x18), {background});
        run.put(receiver + 0x2c, 0);
    }
    uint32_t count = length(run, name) + 1;
    for (uint32_t i = 0; i < count; ++i)
        run.put8(buffer + i, run.get8(name + i));
    background = run.vcall(service(run, receiver, 0x18), 0x30, {resource, buffer, arguments[2] ? 1u : 0u});
    run.put(receiver + 0x2c, background);
    if (!background)
        return 0;
    if (arguments[3]) {
        run.call(0x4bb870, run.get(background + 0x10));
        run.call(0x4bb910, run.get(run.get(receiver + 0x2c) + 0x10), {0, 0x100, 0, 0, 0, 0});
    }
    background = run.get(receiver + 0x2c);
    run.put(service(run, receiver, 0x18) + 0x64, background);
    run.vcall(background, 0x34);
    uint32_t result = run.call(0x4ca900, service(run, receiver, 0x04), {resource, 1});
    if (!result)
        return 0;
    if (arguments[1])
        callAt(run, 0x58, 0x4b98b0, run.get(run.get(service(run, receiver, 0x04) + 0x10) + 0x2c), {0});
    if (arguments[3] && run.get(receiver + 0x2c)) {
        uint32_t palette = run.get(run.get(receiver + 0x2c) + 0x10);
        run.call(0x4bbd90, palette, {0, 0x100, run.get(palette + 0x10), 0x2ee});
    }
    return 1;
}

// 0x490370.
uint32_t function_490370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t application = run.get(receiver + 0x04);
    if (!application)
        return 0;
    uint32_t window = run.get(application + 0x04);
    if (!window)
        return 0;
    uint32_t buffer = run.automatic(-0x40);
    run.icall(0x546cb4, {run.get(window + 0x04), buffer});
    run.icall(0x546cb8, {run.get(run.get(run.get(receiver + 0x04) + 0x04) + 0x04), buffer});
    return 1;
}

// 0x4903c0.
uint32_t function_4903c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t parent = arguments[0];
    if (!run.get(run.get(parent + 0x6c) + 0x18))
        return 0;
    uint32_t count = arguments[2];
    if (s32(count) >= 10)
        count = 10;
    run.put(receiver + 0x08, count);
    uint32_t source = run.get(run.get(parent + 0x6c) + 0x18);
    uint32_t x = arguments[4];
    for (uint32_t i = 0; s32(i) < run.gets(receiver + 0x08); ++i) {
        uint32_t child = run.call(0x4c8da0, service(run, parent, 0x08), {0, 0, 0, run.get(parent + 0x64) + 1, 0x522994, 0});
        if (!child)
            return 0;
        run.put(receiver + 0x0c + i * 4, child);
        uint32_t logic = run.get(child + 0x6c);
        if (!logic)
            return 0;
        run.call(0x4c7970, child, {arguments[6]});
        uint32_t counter = allocateCounter(run, 0x60);
        run.call(0x490760, counter, {child, run.get(source + 0x14), run.get(source + 0x18), run.get(source + 0x04), x, run.get(source + 0x0c), run.get(source + 0x10) + arguments[5]});
        run.put(logic + 0x18, counter);
        x += arguments[3];
    }
    run.put(receiver + 0x04, 0xffffcfc7);
    if (arguments[1] != 0xffffcfc7) {
        run.put(receiver + 0x04, arguments[1]);
        uint32_t buffer = run.automatic(-0x10);
        run.call(0x4a3920, 0, {buffer, 0x52c6f8, arguments[1]});
        uint32_t cursor = buffer + length(run, buffer) - run.get(receiver + 0x08);
        for (uint32_t i = 0; s32(i) < run.gets(receiver + 0x08); ++i) {
            uint32_t child = run.get(receiver + 0x0c + i * 4);
            imageDigit(run, child, uint32_t(int32_t(int8_t(run.get8(cursor++)))) - 0x30);
            run.put(run.get(child + 0x6c) + 0x68, 0xffffffff);
        }
    }
    return 1;
}

// 0x4995d0.
uint32_t function_4995d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t total = run.get(receiver + 0x90);
    if (!total)
        return 1;
    ClawX87State state = xstate();
    run.x87_step(CLAW_X87_I32, state, {run.get(receiver + 0x94)});
    fp(run, state, CLAW_X87_MUL_F64, run.getd(0x50fc50));
    fp(run, state, CLAW_X87_DIV_F64, double(s32(total)));
    uint32_t difference = 0x19 - ftol(run, state);
    uint32_t sign = s32(difference) < 0 ? 0xffffffffu : 0;
    uint32_t absolute = (difference ^ sign) - sign;
    run.x87_step(CLAW_X87_I32, state, {absolute});
    fp(run, state, CLAW_X87_MUL_F64, run.getd(receiver + 0xa8));
    return ftol(run, state);
}

// 0x4997c0.
uint32_t function_4997c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t delta = arguments[0];
    if (!(run.get8(receiver + 0x8c) & 1))
        delta = 0 - delta;
    const uint32_t singles[] = {0x70, 0x74, 0x78, 0x7c};
    const uint32_t arrays[] = {0x64, 0x6c, 0x68, 0x60};
    for (uint32_t group = 0; group < 4; ++group) {
        uint32_t child = run.get(receiver + singles[group]);
        run.put(child + 0x4c, run.get(child + 0x4c) + delta);
        for (uint32_t i = 0; s32(i) < run.gets(run.get(receiver + arrays[group]) + 0x08); ++i) {
            uint32_t digit = run.get(run.get(receiver + arrays[group]) + 0x0c + i * 4);
            run.put(digit + 0x4c, run.get(digit + 0x4c) + delta);
        }
    }
    uint32_t glitter = run.get(receiver + 0x80);
    if (glitter)
        run.put(glitter + 0x4c, run.get(glitter + 0x4c) + delta);
    return 1;
}

// 0x499c30.
uint32_t function_499c30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    digits(run, receiver, arguments[0], run.automatic(-0x10), false);
    return 0;
}

// 0x499cd0.
uint32_t function_499cd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t delta = arguments[0];
    uint32_t child = run.get(receiver + 0x88);
    run.put(child + 0x4c, run.get(child + 0x4c) - delta);
    for (uint32_t i = 0; s32(i) < run.gets(run.get(0x53cac8) + 0x08); ++i) {
        child = run.get(run.get(0x53cac8) + 0x0c + i * 4);
        run.put(child + 0x4c, run.get(child + 0x4c) - delta);
    }
    child = run.get(receiver + 0x84);
    run.put(child + 0x4c, run.get(child + 0x4c) + delta);
    for (uint32_t i = 0; s32(i) < run.gets(run.get(0x53cacc) + 0x08); ++i) {
        child = run.get(run.get(0x53cacc) + 0x0c + i * 4);
        run.put(child + 0x4c, run.get(child + 0x4c) + delta);
    }
    return 1;
}

// 0x499d60.
uint32_t function_499d60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t parent = arguments[0];
    if (run.get(receiver + 0x90) == run.get(receiver + 0x9c)) {
        uint32_t local = run.automatic(4);
        run.put(local, 0);
        run.call(0x4f6286, run.get(run.get(run.get(0x5371fc) + 0x30) + 0x28) + 0x10, {0x52d540, local});
        uint32_t sound = run.get(local);
        if (sound) {
            ClawX87State state = xstate();
            run.x87_step(CLAW_X87_I32, state, {run.get(0x532c10)});
            fp(run, state, CLAW_X87_MUL_F64, run.getd(0x50fc58));
            uint32_t volume = ftol(run, state);
            if (s32(volume) > 100)
                volume = 100;
            if (run.get(0x532c0c))
                callAt(run, 0x20, 0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
        }
        uint32_t glitter = run.call(0x4c8da0, service(run, parent, 0x08), {0, run.get(receiver + 0xa0), run.get(receiver + 0xa4), run.get(parent + 0x64) + 1, 0x5224d8, 0});
        run.put(receiver + 0x80, glitter);
        run.call(0x4c7970, glitter, {0x52d530});
        run.call(0x4c79e0, run.get(receiver + 0x80), {0x52d510, 0});
        uint32_t random = run.call(0x4a3050, 0);
        run.put(run.get(run.get(receiver + 0x80) + 0x6c) + 0x20, uint32_t(s32(random) % 0xfb));
    }
    run.put(parent + 0x4c, run.get(0x52d4ec));
    run.put(parent + 0x50, run.get(0x53cad0));
    run.put(0x52d4e0, run.get(0x52d4e0) - 1);
    return 1;
}

// 0x4c89e0.
uint32_t function_4c89e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    return run.vcall(receiver, 0x3c);
}

// 0x4c89f0.
uint32_t function_4c89f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t node = run.get(receiver + 0x14);
    while (node) {
        uint32_t next = run.get(node);
        uint32_t object = run.get(node + 0x08);
        if (object)
            run.vcall(object, 0x04, {1});
        node = next;
    }
    run.call(0x4f5172, receiver + 0x10);
    return 0;
}

// 0x499170.
uint32_t function_499170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (run.get(receiver + 0x64))
        return 0;
    uint32_t parent = arguments[0];
    run.put(receiver + 0x64, allocateCounter(run, 0x34));
    uint32_t local = run.automatic(-0x10);
    run.call(0x4f6439, local);
    run.call(0x4f4f58, 0, {local, 0x524094, run.get(receiver + 0x90)});
    own(run, 0x4903c0, run.get(receiver + 0x64), {parent, 0, run.get(run.get(local) - 0x08), 0x0b, run.get(receiver + 0xa0) + 0x28, 0, 0x524070}, 0x3c);
    uint32_t manager = run.get(run.get(run.get(0x5371fc) + 0x30) + 0x08);
    uint32_t child = run.call(0x4c8da0, manager, {0, run.get(receiver + 0xa0) + 0x6e, run.get(receiver + 0xa4) + 4, 0x270e, 0x5224d8, 0});
    run.put(receiver + 0x74, child);
    if (child)
        run.call(0x4c7900, child, {0x524084, 1});
    run.put(receiver + 0x6c, allocateCounter(run, 0x34));
    run.call(0x4f4f58, 0, {local, 0x524094, run.get(receiver + 0x9c)});
    own(run, 0x4903c0, run.get(receiver + 0x6c), {parent, run.get(receiver + 0x9c), run.get(run.get(local) - 0x08), 0x0b, run.get(receiver + 0xa0) + 0x96, 0, 0x524070}, 0x3c);
    child = run.call(0x4c8da0, manager, {0, run.get(receiver + 0xa0) + 0xd7, run.get(receiver + 0xa4) + 4, 0x270e, 0x5224d8, 0});
    run.put(receiver + 0x78, child);
    if (child)
        run.call(0x4c7900, child, {0x524084, 2});
    run.put(receiver + 0x68, allocateCounter(run, 0x34));
    run.call(0x4f4f58, 0, {local, 0x524094, run.get(0x523d98 + run.get(receiver + 0x8c) * 0x20)});
    own(run, 0x4903c0, run.get(receiver + 0x68), {parent, run.get(0x523d98 + run.get(receiver + 0x8c) * 0x20), run.get(run.get(local) - 0x08), 0x0b, run.get(receiver + 0xa0) + 0xe9, 0, 0x524070}, 0x3c);
    child = run.call(0x4c8da0, manager, {0, run.get(receiver + 0xa0) + 0x12b, run.get(receiver + 0xa4), 0x270e, 0x5224d8, 0});
    run.put(receiver + 0x7c, child);
    if (child)
        run.call(0x4c7900, child, {0x524084, 3});
    run.put(receiver + 0x60, allocateCounter(run, 0x34));
    run.call(0x4f4f58, 0, {local, 0x524094, run.get(0x523d98 + run.get(receiver + 0x8c) * 0x20) * run.get(receiver + 0x90)});
    own(run, 0x4903c0, run.get(receiver + 0x60), {parent, 0, run.get(run.get(local) - 0x08), 0x0b, run.get(receiver + 0xa0) + 0x141, 0, 0x524070}, 0x3c);
    run.call(0x4f6584, local);
    return 1;
}

// 0x499450.
uint32_t function_499450(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t services = run.get(run.get(0x5371fc) + 0x30);
    uint32_t manager = run.get(services + 0x08);
    if (run.get(receiver + 0x70))
        return 0;
    uint32_t sounds = run.get(services + 0x28);
    uint32_t name = run.get(0x523d94 + run.get(receiver + 0x8c) * 0x20);
    uint32_t local = run.automatic(-0x10);
    if (!run.get(sounds + 0x30)) {
        run.put(local, 0);
        run.call(0x4f6286, sounds + 0x10, {name, local});
        uint32_t sound = run.get(local);
        if (sound && run.get(0x532c0c))
            callAt(run, 0x30, 0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    uint32_t child = run.call(0x4c8da0, manager, {0, run.get(receiver + 0xa0), run.get(receiver + 0xa4), 0x270e, 0x5224d8, 0});
    run.put(receiver + 0x70, child);
    uint32_t string = run.automatic(-0x14);
    run.call(0x4f65f2, string, {run.get(0x523d90 + run.get(receiver + 0x8c) * 0x20)});
    uint32_t suffix = run.get(0x523dac + run.get(receiver + 0x8c) * 0x20);
    if (s32(suffix) >= 0)
        run.call(0x4f6920, string, {run.get(0x523eb0 + suffix * 4)});
    run.call(0x4c7970, run.get(receiver + 0x70), {run.get(string)});
    uint32_t image = run.get(run.get(receiver + 0x70) + 0x170);
    run.put(local, 0);
    run.call(0x4f6286, service(run, arguments[0], 0x10) + 0x10, {0x523ff8, local});
    if (image == run.get(local))
        run.call(0x4c79e0, run.get(receiver + 0x70), {0x52d510, 0});
    run.call(0x4f6584, string);
    return 1;
}

// 0x499630.
uint32_t function_499630(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t manager = run.get(run.get(run.get(0x5371fc) + 0x30) + 0x08);
    uint32_t interval = own(run, 0x4995d0, receiver, {}, 0x38);
    uint32_t count = uint32_t(int64_t(run.gets(0x52d4e8)) / int64_t(s32(interval))) + 1;
    if (s32(count) >= run.gets(receiver + 0x94))
        count = run.get(receiver + 0x94);
    if (s32(count) <= 0)
        return count;
    uint32_t delay = 0;
    uint32_t string = run.automatic(-0x24);
    uint32_t local = run.automatic(-0x1c);
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t child = run.call(0x4c8da0, manager, {0, run.get(0x52d4ec), run.get(0x53cad0), 0x270e, 0x5224c8, 0});
        run.call(0x4f65f2, string, {run.get(0x523d90 + run.get(receiver + 0x8c) * 0x20)});
        if (run.gets(0x523dac + run.get(receiver + 0x8c) * 0x20) >= 0) {
            uint32_t random = run.call(0x4a3050, 0);
            uint32_t index = uint32_t(s32(random) % 4);
            run.call(0x4f6920, string, {run.get(0x523eb0 + index * 4)});
        }
        run.call(0x4c7970, child, {run.get(string)});
        uint32_t image = run.get(child + 0x170);
        run.put(local, 0);
        run.call(0x4f6286, service(run, arguments[0], 0x10) + 0x10, {0x523ff8, local});
        if (image == run.get(local))
            run.call(0x4c79e0, child, {0x52d510, 0});
        uint32_t logic = run.get(child + 0x6c);
        run.put(logic + 0x130, delay);
        run.put(logic + 0x64, run.get(receiver + 0xa0));
        run.put(logic + 0x68, run.get(receiver + 0xa4));
        run.call(0x4f6584, string);
        delay += interval;
    }
    return count;
}

// 0x4998c0.
uint32_t function_4998c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t buffer = run.automatic(-0x10);
    if (!arguments[0]) {
        uint32_t sounds = run.get(run.get(run.get(0x5371fc) + 0x30) + 0x28);
        if (!run.get(sounds + 0x30)) {
            uint32_t sound = run.call(0x4061b0, sounds, {0x52d520});
            if (sound)
                callAt(run, 0x3c, 0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
        }
        uint32_t counter = run.get(receiver + 0x64);
        uint32_t step = run.get(receiver + 0x98);
        uint32_t old = run.get(counter + 0x04);
        if (run.gets(receiver + 0x90) < s32(old + step))
            step = run.get(receiver + 0x90) - old;
        digits(run, counter, old + step, buffer, true);
        uint32_t score = run.get(0x523d98 + run.get(receiver + 0x8c) * 0x20) * step;
        counter = run.get(receiver + 0x60);
        own(run, 0x499c30, counter, {run.get(counter + 0x04) + score}, 0x30);
        counter = run.get(0x53cac8);
        own(run, 0x499c30, counter, {run.get(counter + 0x04) + score}, 0x30);
        counter = run.get(0x53cacc);
        own(run, 0x499c30, counter, {run.get(counter + 0x04) + score}, 0x30);
        uint32_t remaining = run.get(receiver + 0x94) - run.get(receiver + 0x98);
        run.put(receiver + 0x94, remaining);
        run.put(receiver + 0x94, s32(remaining) < 0 ? 0 : remaining);
    } else {
        uint32_t count = run.get(receiver + 0x90);
        digits(run, run.get(receiver + 0x64), count, buffer, true);
        digits(run, run.get(receiver + 0x60), run.get(0x523d98 + run.get(receiver + 0x8c) * 0x20) * count, buffer, true);
        digits(run, run.get(0x53cac8), run.get(receiver + 0xb0), buffer, true);
        digits(run, run.get(0x53cacc), run.get(receiver + 0xb4), buffer, true);
    }
    return 1;
}

// 0x498f90.
uint32_t function_498f90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t parent = arguments[0];
    uint32_t logic = run.get(parent + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    if (state <= 5) {
        if (state != 5) {
            if (state)
                return 1;
            run.put(logic + 0x168, 0);
            run.put(parent + 0xc8, 0);
            run.put(logic + 0x1c, 5);
            return 1;
        }
        countdown(run, logic + 0x130);
        if (!run.get(logic + 0x130))
            run.put(logic + 0x1c, 0x2332);
    } else if (state == 0x2332) {
        uint32_t duration = run.get(0x52d4e8);
        run.put(logic + 0x130, duration);
        double divisor = double(duration);
        run.putf(logic + 0x160, float((double(s32(run.get(logic + 0x64) - run.get(0x52d4ec))) * run.getd(0x50fc40)) / divisor));
        run.put(logic + 0x1c, 0x2333);
        run.putf(logic + 0x164, float((double(s32(run.get(logic + 0x68) - run.get(0x53cad0))) * run.getd(0x50fc40)) / divisor));
    } else if (state == 0x2333) {
        countdown(run, logic + 0x130);
        ClawX87State fpstate = xstate();
        for (uint32_t axis = 0; axis < 2; ++axis) {
            uint32_t old = run.get(parent + 0x4c + axis * 4);
            if (s32(old) < run.gets(logic + 0x64 + axis * 4)) {
                uint32_t value = old + movement(run, logic, 0x160 + axis * 4, fpstate);
                run.put(parent + 0x4c + axis * 4, value);
                uint32_t limit = run.get(logic + 0x64 + axis * 4);
                if (s32(value) > s32(limit))
                    run.put(parent + 0x4c + axis * 4, limit);
            }
        }
        if (!run.get(logic + 0x130)) {
            run.put(parent + 0x08, run.get(parent + 0x08) | 0x10000);
            return 0;
        }
    } else return 1;
    run.call(0x4c82a0, parent + 0x188, {run.get(0x5430c4)});
    return 1;
}

// 0x498930.
uint32_t function_498930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t parent = arguments[0];
    uint32_t logic = run.get(parent + 0x6c);
    uint32_t state = run.get(logic + 0x1c);
    uint32_t counter = run.get(logic + 0x18);
    if (state <= 5) {
        if (state != 5) {
            if (state)
                return 1;
            run.put(0x53cad4, 0);
            run.put(0x53cad8, 0);
            run.put(logic + 0x138, run.get(0x52d4e4));
            run.put(logic + 0x168, 0);
            run.put(parent + 0xc8, 0);
            run.put(parent + 0x4c, run.get(0x52d4ec));
            run.put(parent + 0x50, run.get(0x53cad0));
            if (!run.get(parent + 0x190)) {
                uint32_t image = run.get(parent + 0x170);
                uint32_t local = run.automatic(4);
                run.put(local, 0);
                run.call(0x4f6286, service(run, parent, 0x10) + 0x10, {0x523ff8, local});
                if (image == run.get(local))
                    run.call(0x4c79e0, parent, {0x52d510, 0});
            }
            run.put(logic + 0x1c, 5);
            return 1;
        }
        if (run.get(0x52d4e0) == run.get(counter + 0x8c))
            run.put(logic + 0x1c, 0x232a);
    } else {
        switch (state) {
        case 0x2329:
            if (run.get(0x52d4e0) == 0xffffffff) {
                if (!run.get(run.get(0x5371fc) + 0x130) && run.get(0x5349a8) && !run.get(0x53cad4)) {
                    uint32_t perfect = run.call(0x4c8da0, run.get(run.get(run.get(0x5371fc) + 0x30) + 0x08), {0, 0x140, 0xf0, 0x186a0, 0x5224d8, 0});
                    run.put(0x53cad4, perfect);
                    if (perfect) {
                        run.call(0x4c7900, perfect, {0x52d500, 1});
                        run.call(0x4c79e0, run.get(0x53cad4), {0x52d4f0, 0});
                        uint32_t sounds = run.get(run.get(run.get(0x5371fc) + 0x30) + 0x28);
                        if (!run.get(sounds + 0x30)) {
                            uint32_t local = run.automatic(4);
                            run.put(local, 0);
                            run.call(0x4f6286, sounds + 0x10, {0x52d500, local});
                            uint32_t sound = run.get(local);
                            if (sound && run.get(0x532c0c))
                                callAt(run, 0x2c, 0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
                        }
                    }
                    if (run.gets(0x534cfc) < 10)
                        run.put(0x534cfc, run.get(0x534cfc) + 1);
                }
                run.put(logic + 0x1c, 0x2334);
                if (run.get(run.get(0x53499c) - 0x08) && !run.get(0x53cad8)) {
                    uint32_t local = run.automatic(4);
                    run.put(local, 0);
                    run.call(0x4f6286, run.get(run.get(run.get(0x5371fc) + 0x30) + 0x28) + 0x10, {run.get(0x53499c), local});
                    uint32_t sound = run.get(local);
                    if (sound && !run.get(0x5349a0) && run.get(0x532c0c))
                        callAt(run, 0x2c, 0x4b3dc0, run.get(sound + 0x10), {100, 0, 0, 0});
                    run.put(0x53cad8, 1);
                }
            }
            break;
        case 0x232a:
            run.put(logic + 0x130, run.get(0x52d4e8));
            run.put(logic + 0x134, own(run, 0x4995d0, counter, {}, 0x1c));
            run.putf(logic + 0x160, float((double(s32(run.get(counter + 0xa0) - run.get(0x52d4ec))) * run.getd(0x50fc40)) / double(run.get(logic + 0x130))));
            run.put(parent + 0x50, run.get(counter + 0xa4));
            run.put(logic + 0xac, 0);
            run.put(logic + 0x1c, 0x232b);
            break;
        case 0x232b:
            countdown(run, logic + 0x130);
            if (!run.get(logic + 0xac)) {
                uint32_t old = run.get(parent + 0x4c);
                if (s32(old) < run.gets(counter + 0xa0)) {
                    ClawX87State fpstate = xstate();
                    uint32_t value = old + movement(run, logic, 0x160, fpstate);
                    run.put(parent + 0x4c, value);
                    uint32_t limit = run.get(counter + 0xa0);
                    if (s32(value) > s32(limit))
                        run.put(parent + 0x4c, limit);
                }
            }
            if (!run.get(logic + 0x130)) {
                if (!run.get(logic + 0xac)) {
                    run.put(parent + 0x4c, run.get(0x52d4ec));
                    run.put(parent + 0x50, run.get(0x53cad0));
                    own(run, 0x499450, counter, {parent}, 0x20);
                    own(run, 0x499170, counter, {parent}, 0x20);
                    run.put(logic + 0xac, 1);
                }
                run.put(logic + 0x130, run.get(0x52d4e8));
                own(run, 0x499630, counter, {parent}, 0x20);
            }
            if (run.get(logic + 0xac) == 1) {
                if (!run.get(counter + 0x90)) {
                    own(run, 0x499d60, counter, {parent}, 0x20);
                    run.put(logic + 0x138, run.get(0x52d4e4));
                    run.put(logic + 0x1c, 0x2329);
                } else {
                    countdown(run, logic + 0x134);
                    if (!run.get(logic + 0x134)) {
                        if (run.gets(counter + 0x94) <= 0) {
                            own(run, 0x499d60, counter, {parent}, 0x20);
                            run.put(logic + 0x138, run.get(0x52d4e4));
                            run.put(logic + 0x1c, 0x2329);
                        } else {
                            own(run, 0x4998c0, counter, {0}, 0x20);
                            run.put(logic + 0x134, own(run, 0x4995d0, counter, {}, 0x1c));
                        }
                    }
                }
            }
            break;
        case 0x232c:
            if (run.get(0x52d4e0) == 0xffffffff) {
                uint32_t delay = 0x12 - run.get(counter + 0x8c) * 2;
                run.put(logic + 0x1c, 0x232d);
                run.put(logic + 0x130, delay);
                run.put(logic + 0x64, 0x19);
                run.put(logic + 0x68, 0x19);
            }
            break;
        case 0x232d: {
            countdown(run, logic + 0x130);
            if (run.get(logic + 0x130))
                return 1;
            uint32_t left = run.get(logic + 0x68);
            run.put(logic + 0x68, left - 1);
            if (s32(left) <= 0)
                run.put(logic + 0x1c, run.get(counter + 0x8c) == 1 ? 0x232e : 0x2331);
            else {
                own(run, 0x4997c0, counter, {run.get(logic + 0x64)}, 0x20);
                run.put(logic + 0x130, 0x12 - run.get(counter + 0x8c) * 2);
            }
            return 1;
        }
        case 0x232e:
            run.put(logic + 0x130, 0x4b);
            run.put(logic + 0x64, 0x19);
            run.put(logic + 0x6c, 0x19);
            run.put(logic + 0x1c, 0x232f);
            break;
        case 0x232f: {
            countdown(run, logic + 0x130);
            uint32_t left = run.get(logic + 0x6c);
            run.put(logic + 0x6c, left - 1);
            if (s32(left) <= 0)
                run.put(logic + 0x1c, 0x2331);
            else {
                own(run, 0x499cd0, counter, {run.get(logic + 0x64)}, 0x20);
                run.put(logic + 0x130, 0x4b);
            }
            return 1;
        }
        case 0x2330:
            if (run.get(counter + 0x8c) == run.get(0x52d4e0)) {
                own(run, 0x499450, counter, {parent}, 0x20);
                own(run, 0x499170, counter, {parent}, 0x20);
                own(run, 0x4998c0, counter, {1}, 0x20);
                own(run, 0x499d60, counter, {parent}, 0x20);
                run.put(logic + 0x138, run.get(0x52d4e4));
                run.put(logic + 0x1c, 0x2329);
            }
            break;
        case 0x2331:
            break;
        case 0x2334:
            countdown(run, logic + 0x138);
            if (!run.get(logic + 0x138))
                run.put(logic + 0x1c, 0x232c);
            break;
        default:
            return 1;
        }
    }
    run.call(0x4c82a0, parent + 0x188, {run.get(0x5430c4)});
    return 1;
}

// 0x40d470.
uint32_t function_40d470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    if (!run.call(0x48f0d0, receiver, {arguments[0], arguments[1], arguments[2]}))
        return 0;
    uint32_t resource = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523b1c});
    run.put(receiver + 0x20, resource);
    if (!resource)
        return 0;
    resource = run.call(0x4b7f20, run.get(receiver + 0x08), {0x523734});
    run.put(receiver + 0x24, resource);
    if (!resource)
        return 0;
    if (run.get(run.get(receiver + 0x04) + 0x130)) {
        resource = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523ce0});
        if (!resource)
            return 0;
        run.vcall(service(run, receiver, 0x10), 0x48, {resource, 0x523b14, 0x523728});
        resource = run.call(0x4b7cd0, run.get(receiver + 0x20), {0x523cd8});
        if (!resource)
            return 0;
        run.call(0x4ce0d0, service(run, receiver, 0x2c), {resource, 0x523b14, 0x523728});
    }
    uint32_t string = run.automatic(0x0c);
    run.call(0x4f6439, string);
    for (uint32_t i = 0; i < 9; ++i)
        run.call(0x4f4f58, 0, {string, 0x524094, run.get(0x523d98 + i * 0x20)});
    uint32_t total = 0;
    for (uint32_t i = 0; i < 9; ++i)
        total += run.get(0x534d08 + i * 4) * run.get(0x523d98 + i * 0x20);
    uint32_t initial = run.get(0x534cc4);
    uint32_t score = initial - total;
    uint32_t first = run.call(0x4c8da0, service(run, receiver, 0x08), {0, 0x1a4, 0x1d2, 0x270e, 0x5224d8, 0});
    run.call(0x4c7900, first, {0x524084, 5});
    uint32_t logic = run.get(first + 0x6c);
    uint32_t counter = allocateCounter(run, 0x60);
    run.call(0x490760, counter, {first, 10, 99, 1, 0x1a4, 4, 0x1d2});
    run.put(logic + 0x18, counter);
    uint32_t firstCounter = allocateCounter(run, 0x34);
    run.call(0x4f4f58, 0, {string, 0x524094, total});
    own(run, 0x4903c0, firstCounter, {first, 0, run.get(run.get(string) - 0x08), 0x0b, 0x1ea, 0xffffffff, 0x524070}, 0x90);
    uint32_t second = run.call(0x4c8da0, service(run, receiver, 0x08), {0, 0x5a, 0x1d2, 0x270e, 0x5224d8, 0});
    run.call(0x4c7900, second, {0x524084, 4});
    logic = run.get(second + 0x6c);
    counter = allocateCounter(run, 0x60);
    run.call(0x490760, counter, {second, 10, 99, 1, 0x5a, 4, 0x1d2});
    run.put(logic + 0x18, counter);
    uint32_t secondCounter = allocateCounter(run, 0x34);
    run.call(0x4f4f58, 0, {string, 0x524094, initial});
    own(run, 0x4903c0, secondCounter, {second, score, run.get(run.get(string) - 0x08), 0x0b, 0x9b, 0xffffffff, 0x524070}, 0x90);
    run.put(0x5349a8, 1);
    uint32_t temporary = run.automatic(-0x60);
    for (uint32_t i = 0; i < 9; ++i) {
        uint32_t table = 0x523eac - i * 0x20;
        uint32_t child = run.call(0x4c8da0, service(run, receiver, 0x08), {0, 0xffffff9c, 0xffffff9c, i + 0x270e, 0x5224e8, 0});
        run.put(receiver + 0x15c + i * 4, child);
        if (!child)
            continue;
        run.call(0x4f65f2, temporary, {run.get(table - 0x1c)});
        uint32_t suffix = run.get(table);
        if (s32(suffix) >= 0)
            run.call(0x4f6920, temporary, {run.get(0x523eb0 + suffix * 4)});
        run.call(0x4c7970, child, {run.get(temporary)});
        logic = run.get(child + 0x6c);
        counter = run.call(0x4f63ec, 0, {0xb8});
        if (counter) {
            run.put(counter + 0x28, 0x50b5cc);
            run.put(counter, 0x50b5bc);
            for (uint32_t offset : {0x60u, 0x64u, 0x68u, 0x6cu, 0x74u, 0x78u, 0x7cu, 0x70u, 0x80u, 0x84u, 0x88u})
                run.put(counter + offset, 0);
            run.put(0x52d4e0, 8);
            run.put(counter + 0xa8, 0);
            run.put(counter + 0x8c, 0);
            run.put(counter + 0x90, 0);
            run.put(counter + 0x94, 0);
            run.put(counter + 0x98, 1);
            run.put(counter + 0x9c, 0);
            run.put(counter + 0xa0, 0);
            run.put(counter + 0xa4, 0);
            run.put(counter + 0xac, 0x3ff00000);
            run.put(counter + 0xb0, 0);
            run.put(counter + 0xb4, 0);
            run.put(0x53cac4, run.get(0x53cac4) + 1);
        }
        uint32_t actual = run.get(0x534d28 - i * 4);
        run.put(counter + 0x8c, 8 - i);
        run.put(counter + 0x90, actual);
        run.put(counter + 0x94, actual);
        run.put(counter + 0x98, run.get(table - 0x04));
        uint32_t maximum = run.get(0x538200 - i * 4);
        if (s32(maximum) > s32(actual))
            actual = maximum;
        run.put(counter + 0x9c, actual);
        run.put(counter + 0xa0, 0xa0);
        run.put(counter + 0xa4, 0x37 + i * 0x2c);
        run.put(0x53cac8, firstCounter);
        run.put(0x53cacc, secondCounter);
        run.put(counter + 0xa8, run.get(table - 0x0c));
        run.put(counter + 0xac, run.get(table - 0x08));
        run.put(counter + 0x84, second);
        run.put(counter + 0xb4, initial);
        run.put(counter + 0x88, first);
        run.put(counter + 0xb0, total);
        run.call(0x490760, counter, {child, 10, 99, 1, run.get(counter + 0xa0), 4, run.get(counter + 0xa4)});
        run.put(logic + 0x18, counter);
        if (run.get(counter + 0x90) != run.get(counter + 0x9c))
            run.put(0x5349a8, 0);
        run.call(0x4f6584, temporary);
    }
    if (run.get(run.get(receiver + 0x04) + 0x130))
        run.call(0x4f66cc, receiver + 0x180, {0x524064});
    else {
        uint32_t level = run.get(receiver + 0x14) * 2;
        uint32_t local = run.automatic(0x08);
        run.call(0x4f6439, local);
        run.call(0x4f4f58, 0, {local, 0x523cc8, s32(level) < 10 ? 0x523cd4u : 0x523cd0u, level});
        run.call(0x4f667d, receiver + 0x180, {local});
        run.call(0x4f6920, receiver + 0x180, {run.get(0x5349a0) ? 0x523c74u : 0x523c6cu});
        run.call(0x4f6584, local);
    }
    run.call(0x4f6584, string);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40b020:
        return function_40b020(run, receiver, arguments);
    case 0x40b040:
        return function_40b040(run, receiver, arguments);
    case 0x40d470:
        return function_40d470(run, receiver, arguments);
    case 0x40db10:
        return function_40db10(run, receiver, arguments);
    case 0x40db60:
        return function_40db60(run, receiver, arguments);
    case 0x40dc10:
        return function_40dc10(run, receiver, arguments);
    case 0x40dc50:
        return function_40dc50(run, receiver, arguments);
    case 0x40dca0:
        return function_40dca0(run, receiver, arguments);
    case 0x40dcb0:
        return function_40dcb0(run, receiver, arguments);
    case 0x40dd50:
        return function_40dd50(run, receiver, arguments);
    case 0x40de90:
        return function_40de90(run, receiver, arguments);
    case 0x40df00:
        return function_40df00(run, receiver, arguments);
    case 0x40df60:
        return function_40df60(run, receiver, arguments);
    case 0x40e020:
        return function_40e020(run, receiver, arguments);
    case 0x40e040:
        return function_40e040(run, receiver, arguments);
    case 0x48f470:
        return function_48f470(run, receiver, arguments);
    case 0x48ffa0:
        return function_48ffa0(run, receiver, arguments);
    case 0x490370:
        return function_490370(run, receiver, arguments);
    case 0x4903c0:
        return function_4903c0(run, receiver, arguments);
    case 0x498930:
        return function_498930(run, receiver, arguments);
    case 0x498f90:
        return function_498f90(run, receiver, arguments);
    case 0x499170:
        return function_499170(run, receiver, arguments);
    case 0x499450:
        return function_499450(run, receiver, arguments);
    case 0x4995d0:
        return function_4995d0(run, receiver, arguments);
    case 0x499630:
        return function_499630(run, receiver, arguments);
    case 0x4997c0:
        return function_4997c0(run, receiver, arguments);
    case 0x4998c0:
        return function_4998c0(run, receiver, arguments);
    case 0x499c30:
        return function_499c30(run, receiver, arguments);
    case 0x499cd0:
        return function_499cd0(run, receiver, arguments);
    case 0x499d60:
        return function_499d60(run, receiver, arguments);
    case 0x4c89e0:
        return function_4c89e0(run, receiver, arguments);
    case 0x4c89f0:
        return function_4c89f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_booty_results_entry, owned, body)
