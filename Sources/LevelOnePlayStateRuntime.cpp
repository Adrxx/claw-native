// Level 1 Play state vtable slots and helpers
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
    case 0x429470:
        return 1;
    case 0x429480:
        return 1;
    case 0x4294a0:
        return 0;
    case 0x46a840:
        return 1;
    case 0x46a870:
        return 0;
    case 0x46b8f0:
        return 0;
    case 0x46ba80:
        return 0;
    case 0x46bc00:
        return 0;
    case 0x46ca50:
        return 1;
    case 0x46ef80:
        return 0;
    case 0x48fcf0:
        return 5;
    case 0x40af60:
        return 1;
    default:
        return -1;
    }
}

// 0x429470. Ignores its argument and returns zero.
uint32_t function_429470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

uint32_t function_4294a0(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x429480. Scalar deleting destructor: runs the destructor, frees the object when bit 0 of the flag is set.
uint32_t function_429480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4294a0(run, receiver, nullptr);
    if ((arguments[0] & 1) != 0) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

uint32_t function_46a870(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4294a0. Destructor of the Level 1 Play state: +0x250 is the MFC string.
uint32_t function_4294a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x50c264);
    function_46a870(run, receiver, nullptr);
    run.call(0x4f6584, receiver + 0x250);
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver);
    return 0;
}

// 0x46a840. Copies the string at +0xc0 into the destination object and returns it.
uint32_t function_46a840(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t destination = arguments[0];
    run.put(run.automatic(-0x4), 0);
    run.call(0x4f6449, destination, {receiver + 0xc0});
    return destination;
}

// 0x46a870. Clear: +0x774 GDI object, +0x4 owner, +0x768 +0x76c +0x770 counters.
uint32_t function_46a870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t object = run.get(receiver + 0x774);
    if (object != 0) {
        run.icall(0x54686c, {object});
        run.put(receiver + 0x774, 0);
    }
    run.call(0x46b7b0, receiver);
    uint32_t owner = run.get(receiver + 0x4);
    if (owner != 0) {
        run.call(0x4f650f, owner + 0xc0);
    }
    run.put(receiver + 0x768, 0);
    run.put(receiver + 0x76c, 0);
    run.put(receiver + 0x770, 0);
    run.call(0x48f180, receiver);
    return 0;
}

// ShowCursor(0) until the display counter is negative.
void hideCursor(Run &run) {
    run.stackPointer = 0;
    uint32_t count = run.icall(0x546d54, {0});
    if (s32(count) >= 0) {
        do {
            count = run.icall(0x546d54, {0});
        } while (s32(count) >= 0);
    }
}

// 0x46b8f0. Loads the TILES and IMAGES pictures through the loader at +0xc +0x10 (vtable slot 0x4c).
uint32_t function_46b8f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.stackPointer = run.frame - 0xc;
    uint32_t ready = run.call(0x4ca930, run.get(run.get(receiver + 0xc) + 0x4));
    if (ready == 0) {
        return 0;
    }
    uint32_t block = run.get(run.get(receiver + 0xc) + 0x4);
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b97c0, run.get(run.get(block + 0x14) + 0x2c), {0});
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b98b0, run.get(run.get(block + 0x10) + 0x2c), {0});
    block = run.get(run.get(receiver + 0xc) + 0x4);
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b97c0, run.get(run.get(block + 0x14) + 0x2c), {0});
    run.stackPointer = run.frame - 0x10;
    run.call(0x4b98b0, run.get(run.get(block + 0x10) + 0x2c), {0});
    hideCursor(run);
    run.stackPointer = run.frame - 0x10;
    uint32_t picture = run.call(0x4b7cd0, run.get(receiver + 0x1c), {0x529fe4});
    if (picture == 0) {
        return 0;
    }
    run.stackPointer = run.frame - 0x18;
    uint32_t loaded = run.vcall(run.get(run.get(receiver + 0xc) + 0x10), 0x4c, {picture, 0x534938, 0x523728});
    if (loaded == 0xffffffff) {
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    picture = run.call(0x4b7cd0, run.get(receiver + 0x28), {0x523ce0});
    if (picture == 0) {
        return 0;
    }
    run.stackPointer = run.frame - 0x18;
    loaded = run.vcall(run.get(run.get(receiver + 0xc) + 0x10), 0x4c, {picture, 0x5254ec, 0x523728});
    if (loaded == 0xffffffff) {
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    picture = run.call(0x4b7cd0, run.get(receiver + 0x24), {0x523ce0});
    if (picture == 0) {
        return 0;
    }
    run.stackPointer = run.frame - 0x18;
    loaded = run.vcall(run.get(run.get(receiver + 0xc) + 0x10), 0x4c, {picture, 0x523734, 0x523728});
    if (loaded == 0xffffffff) {
        return 0;
    }
    run.stackPointer = run.frame - 0x10;
    picture = run.call(0x4b7cd0, run.get(receiver + 0x1c), {0x523ce0});
    if (picture == 0) {
        return 0;
    }
    run.stackPointer = run.frame - 0x18;
    loaded = run.vcall(run.get(run.get(receiver + 0xc) + 0x10), 0x4c, {picture, 0x524d80, 0x523728});
    if (loaded == 0xffffffff) {
        return 0;
    }
    run.stackPointer = run.frame - 0xc;
    run.call(0x431300, run.get(0x537204));
    run.stackPointer = run.frame - 0x10;
    run.call(0x429eb0, run.get(0x5371fc), {0});
    hideCursor(run);
    uint32_t owner = run.get(receiver + 0x4);
    if (run.get(owner + 0xc) != 0) {
        run.stackPointer = run.frame - 0xc;
        uint32_t result = run.vcall(receiver, 0x4c);
        if (result == 0) {
            return 0;
        }
    }
    return 1;
}

// 0x46ba80. Prepares the display and runs 0x48f470 with 0xfa.
uint32_t function_46ba80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t ready = run.vcall(receiver, 0xc);
    if (ready == 0) {
        return 0;
    }
    if (run.get(receiver + 0x2c) == 0) {
        return 0;
    }
    uint32_t owner = run.get(receiver + 0x4);
    uint32_t sizeX = run.get(owner + 0x84);
    uint32_t currentX = run.get(owner + 0x7c);
    uint32_t sizeY = run.get(owner + 0x88);
    uint32_t currentY = run.get(owner + 0x80);
    if (sizeX != currentX || sizeY != currentY) {
        uint32_t resized = run.call(0x42a060, owner, {sizeX, sizeY});
        if (resized == 0) {
            return 0;
        }
    }
    uint32_t parent = run.get(receiver + 0xc);
    uint32_t third = run.get(parent + 0x8);
    uint32_t block = run.get(parent + 0x4);
    run.call(0x4cb9b0, run.get(parent + 0x24), {run.get(block + 0x14), third});
    parent = run.get(receiver + 0xc);
    uint32_t target = run.get(parent + 0xc);
    block = run.get(parent + 0x4);
    uint32_t height = run.get(block + 0x18);
    uint32_t width = run.get(block + 0x14);
    run.vcall(target, 0x34, {width, height});
    parent = run.get(receiver + 0xc);
    block = run.get(parent + 0x4);
    run.call(0x4b98b0, run.get(run.get(block + 0x10) + 0x2c), {0});
    uint32_t result = run.call(0x48f470, receiver, {0xfa});
    return result != 0 ? 1 : 0;
}

// 0x46bc00. Starts the single-frame message and redraws.
uint32_t function_46bc00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t message = run.call(0x4c8da0, run.get(run.get(receiver + 0xc) + 0x8), {2, 0, 0, 0x1869f, 0x522604, 0x200000});
    uint32_t parent = run.get(receiver + 0xc);
    uint32_t third = run.get(parent + 0x8);
    uint32_t block = run.get(parent + 0x4);
    run.call(0x4cb9b0, run.get(parent + 0x24), {run.get(block + 0x14), third});
    parent = run.get(receiver + 0xc);
    uint32_t target = run.get(parent + 0xc);
    block = run.get(parent + 0x4);
    uint32_t height = run.get(block + 0x18);
    uint32_t width = run.get(block + 0x14);
    run.vcall(target, 0x34, {width, height});
    if (message != 0) {
        run.call(0x46ddf0, receiver);
        parent = run.get(receiver + 0xc);
        block = run.get(parent + 0x4);
        run.vcall(message, 0x2c, {run.get(block + 0x14)});
    }
    parent = run.get(receiver + 0xc);
    block = run.get(parent + 0x4);
    run.call(0x4b98b0, run.get(run.get(block + 0x10) + 0x2c), {0});
    return 1;
}

// 0x46ca50. Draws the text strip: the rectangle is a local at entry-relative -0x10.
uint32_t function_46ca50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t hdc = arguments[0];
    uint32_t rect = run.automatic(-0x10);
    run.call(0x4224f0, run.get(run.get(receiver + 0x4) + 0x4c), {run.get(0x53720c)});
    uint32_t left = run.get(0x5370c8);
    uint32_t top = run.get(0x5370cc) + 0x6e;
    uint32_t right = run.get(0x5370d0);
    run.put(rect + 0x0, left);
    run.put(rect + 0x4, top);
    run.put(rect + 0xc, top + 0x40);
    run.put(rect + 0x8, right);
    run.call(0x4226b0, run.get(run.get(receiver + 0x4) + 0x4c), {1, hdc, rect, 1});
    return 0;
}

// 0x46ef80. Marks entities whose flag 0x2000 is set with 0x10000, then runs 0x4d51f0 on the owner's helper.
uint32_t function_46ef80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t parent = run.get(receiver + 0xc);
    if (parent == 0) {
        return 0;
    }
    uint32_t list = run.get(parent + 0x8) + 0x10;
    if (list == 0) {
        return 0;
    }
    uint32_t node = run.get(list + 0x4);
    while (node != 0) {
        uint32_t next = run.get(node);
        uint32_t entity = run.get(node + 0x8);
        node = next;
        if (entity != 0 && (run.get(entity + 0x164) & 0x2000) != 0) {
            run.put(entity + 0x8, run.get(entity + 0x8) | 0x10000);
        }
    }
    uint32_t inner = run.get(run.get(receiver + 0xc) + 0x24);
    if (inner == 0) {
        return 0;
    }
    inner = run.get(inner + 0x5c);
    if (inner == 0) {
        return 0;
    }
    inner = run.get(inner + 0xb0);
    if (inner == 0) {
        return 0;
    }
    run.call(0x4d51f0, inner, {0x46eff0});
    return 0;
}

// 0x48fcf0. Draws a string: arguments are x, y, string, text colour, background mode. The a3 stack slot
// (entry-relative +0xc) is reused as the local that receives the device context.
uint32_t function_48fcf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t x = arguments[0];
    uint32_t y = arguments[1];
    uint32_t text = arguments[2];
    uint32_t color = arguments[3];
    uint32_t mode = arguments[4];
    if (text == 0) {
        return 0;
    }
    uint32_t surface = run.get(run.get(run.get(run.get(receiver + 0xc) + 0x4) + 0x10) + 0x2c);
    if (surface == 0) {
        return 0;
    }
    uint32_t slot = run.automatic(0xc);
    run.put(slot, 0);
    uint32_t com = run.get(surface + 0x8);
    run.call(run.get(run.get(com) + 0x44), 0, {com, slot});
    uint32_t hdc = run.get(slot);
    if (hdc == 0) {
        return 0;
    }
    run.icall(0x546888, {hdc, mode});
    run.icall(0x546880, {hdc, color});
    uint32_t length = 0;
    while (run.get8(text + length) != 0) {
        length = length + 1;
    }
    run.icall(0x546890, {hdc, x, y, text, length});
    com = run.get(surface + 0x8);
    run.call(run.get(run.get(com) + 0x68), 0, {com, run.get(slot)});
    return 1;
}

// 0x40af60. Base-class scalar deleting destructor.
uint32_t function_40af60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver, 0x50b4ec);
    run.call(0x48f180, receiver);
    if ((arguments[0] & 1) != 0) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x429470:
        return function_429470(run, receiver, arguments);
    case 0x429480:
        return function_429480(run, receiver, arguments);
    case 0x4294a0:
        return function_4294a0(run, receiver, arguments);
    case 0x46a840:
        return function_46a840(run, receiver, arguments);
    case 0x46a870:
        return function_46a870(run, receiver, arguments);
    case 0x46b8f0:
        return function_46b8f0(run, receiver, arguments);
    case 0x46ba80:
        return function_46ba80(run, receiver, arguments);
    case 0x46bc00:
        return function_46bc00(run, receiver, arguments);
    case 0x46ca50:
        return function_46ca50(run, receiver, arguments);
    case 0x46ef80:
        return function_46ef80(run, receiver, arguments);
    case 0x48fcf0:
        return function_48fcf0(run, receiver, arguments);
    case 0x40af60:
        return function_40af60(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_play_state_entry, owned, body)
