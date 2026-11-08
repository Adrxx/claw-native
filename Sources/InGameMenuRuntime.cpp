// In-game menu opened by Escape
//
// Native implementation of the thirteen owned functions, recovered from the
// decompile and the disassembly of the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x44f880:
        return 3;
    case 0x44fad0:
        return 1;
    case 0x450060:
        return 0;
    case 0x450610:
        return 0;
    case 0x451770:
        return 1;
    case 0x451900:
        return 1;
    case 0x451c40:
        return 0;
    case 0x451d50:
        return 0;
    case 0x451f00:
        return 0;
    case 0x4525a0:
        return 1;
    case 0x46dd90:
        return 0;
    case 0x46ddf0:
        return 0;
    case 0x4dd5b0:
        return 2;
    default:
        return -1;
    }
}

// Models the entry frame of an owned callee called directly from C++. The
// distance is the caller's stack in use at the CALL plus the return word.
class FrameScope {
  public:
    FrameScope(Run &run, uint32_t distance) : owner(run), saved(run.frame) { run.frame = run.frame - distance; }
    ~FrameScope() { owner.frame = saved; }

  private:
    Run &owner;
    uint32_t saved;
};

// Signed division by two with truncation toward zero (cdq, sub, sar).
uint32_t half(uint32_t value) {
    int32_t signedValue = s32(value);
    int32_t result = signedValue / 2;
    return uint32_t(result);
}

// Four-byte word count of a byte width (cdq, and 3, add, sar 2).
uint32_t wordCount(uint32_t width) {
    uint32_t bias = 0;
    if (width & 0x80000000u)
        bias = 3;
    uint32_t sum = width + bias;
    uint32_t shifted = sum >> 2;
    if (sum & 0x80000000u)
        shifted = shifted | 0xc0000000u;
    return shifted;
}

// Start of a span of the given size centred in an extent.
uint32_t spanStart(uint32_t extent, uint32_t low, uint32_t high) {
    uint32_t centre = half(extent);
    uint32_t reach = half(high - low);
    return centre - reach;
}

// End of a span of the given size centred in an extent.
uint32_t spanEnd(uint32_t extent, uint32_t low, uint32_t high) {
    uint32_t centre = half(extent);
    uint32_t reach = half(high - low);
    return reach + centre;
}

// 0x4dd5b0. thiscall, 2 stack arguments (mode, value). Moves every item of the
// container at `receiver` to the edge or centre selected by `mode`. Each item
// position comes from 0x4ded20 and each size from 0x4dece0, both written into
// a stack local; 0x4ded00 moves the item.
uint32_t function_4dd5b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t mode = arguments[0];
    uint32_t value = arguments[1];
    if (mode > 5)
        return 0;
    run.stackPointer = run.frame - 0x64;
    int32_t count = s32(run.call(0x4df630, receiver, {}));
    if (count <= 0)
        return 0;
    uint32_t index = 0;
    do {
        run.stackPointer = run.frame - 0x68;
        uint32_t item = run.call(0x4dd450, receiver, {index});
        switch (mode) {
        case 0: {
            // Left edge: x = value, y kept.
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x50)});
            uint32_t y = run.get(position + 0x4);
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {value, y});
            break;
        }
        case 1: {
            // Right edge: x = value - width, y kept.
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x48)});
            uint32_t y = run.get(position + 0x4);
            run.stackPointer = run.frame - 0x68;
            uint32_t size = run.call(0x4dece0, item, {run.automatic(-0x40)});
            uint32_t width = run.get(size);
            uint32_t x = value - width;
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {x, y});
            break;
        }
        case 2: {
            // Top edge: x kept, y = value.
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x38)});
            uint32_t x = run.get(position);
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {x, value});
            break;
        }
        case 3: {
            // Bottom edge: x kept, y = value - height.
            run.stackPointer = run.frame - 0x68;
            uint32_t size = run.call(0x4dece0, item, {run.automatic(-0x30)});
            uint32_t height = run.get(size + 0x4);
            uint32_t y = value - height;
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x28)});
            uint32_t x = run.get(position);
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {x, y});
            break;
        }
        case 4: {
            // Horizontal centre: x = value - width / 2, y kept.
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x20)});
            uint32_t y = run.get(position + 0x4);
            run.stackPointer = run.frame - 0x68;
            uint32_t size = run.call(0x4dece0, item, {run.automatic(-0x18)});
            uint32_t width = run.get(size);
            uint32_t x = value - half(width);
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {x, y});
            break;
        }
        default: {
            // Vertical centre: x kept, y = value - height / 2.
            run.stackPointer = run.frame - 0x68;
            uint32_t size = run.call(0x4dece0, item, {run.automatic(-0x10)});
            uint32_t height = run.get(size + 0x4);
            uint32_t y = value - half(height);
            run.stackPointer = run.frame - 0x68;
            uint32_t position = run.call(0x4ded20, item, {run.automatic(-0x8)});
            uint32_t x = run.get(position);
            run.stackPointer = run.frame - 0x6c;
            run.call(0x4ded00, item, {x, y});
            break;
        }
        }
        index = index + 1;
        run.stackPointer = run.frame - 0x64;
        count = s32(run.call(0x4df630, receiver, {}));
    } while (s32(index) < count);
    return 0;
}

// Binary64 memory operand of an x87 instruction, as low and high words.
void foldSubtract(Run &run, ClawX87State &fp, uint32_t address) {
    uint32_t low = run.get(address);
    uint32_t high = run.get(address + 0x4);
    run.x87_step(CLAW_X87_SUB_F64, fp, {low, high});
}

// fld st(0)
void foldDuplicate(Run &run, ClawX87State &fp) {
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
}

// call 0x4a30e0: the original float to integer conversion, popping ST(0).
uint32_t foldTruncate(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    // Called only from 0x451770, whose body uses 0x18 bytes of stack.
    run.stackPointer = run.frame - 0x1c;
    uint32_t value = run.call_x87_exact(0x4a30e0, 0, fp);
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return value;
}

// 0x451770. thiscall, 1 stack argument (page id). Lays out the menu rectangle
// at +0x278 and the item rows from the screen height scaled by constants in
// the program's data, then centres the items.
uint32_t function_451770(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t page = arguments[0];
    uint32_t app = run.get(receiver + 0x4);
    uint32_t rect = receiver + 0x278;
    uint32_t width = run.get(app + 0x7c);
    uint32_t height = run.get(app + 0x80);
    // SetRect(rect, width, 0, 0, height): the argument order is the original's.
    run.stackPointer = run.frame - 0x30;
    run.icall(0x546d5c, {rect, width, 0, 0, height});
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    fp.status = 0;
    fp.count = 0;
    run.x87_step(CLAW_X87_I32, fp, {height});
    uint32_t scaleLow = run.get(0x50e1d8);
    uint32_t scaleHigh = run.get(0x50e1dc);
    run.x87_step(CLAW_X87_MUL_F64, fp, {scaleLow, scaleHigh});
    // 1: pages 0x4e22 and 0x4e25, 2: pages 0x59da and 0x4e23, 3: page 0x59db, 4: any other page.
    uint32_t kind = 4;
    if (page > 0x59da) {
        if (page == 0x59db)
            kind = 3;
    } else if (page == 0x59da) {
        kind = 2;
    } else {
        uint32_t offset = page - 0x4e22;
        if (offset == 0)
            kind = 1;
        else if (offset == 1)
            kind = 2;
        else if (offset == 3)
            kind = 1;
    }
    if (kind == 1) {
        foldDuplicate(run, fp);
        foldSubtract(run, fp, 0x50e1e0);
        uint32_t first = foldTruncate(run, fp);
        foldDuplicate(run, fp);
        foldSubtract(run, fp, 0x50e1e8);
        // +0x28c: row of the banner.
        run.put(receiver + 0x28c, first);
        uint32_t second = foldTruncate(run, fp) - 10;
        foldSubtract(run, fp, 0x50e1f0);
        // +0x27c: top of the menu rectangle.
        run.put(receiver + 0x27c, second);
    } else if (kind == 2) {
        foldDuplicate(run, fp);
        foldSubtract(run, fp, 0x50e1f8);
        uint32_t top = foldTruncate(run, fp);
        foldSubtract(run, fp, 0x50e200);
        run.put(receiver + 0x27c, top);
    } else {
        uint32_t subtrahend = 0x50e218;
        uint32_t following = 0x50e1f0;
        if (kind == 4) {
            uint32_t appAgain = run.get(receiver + 0x4);
            uint32_t flag = run.get(appAgain + 0x9c);
            if (flag != 0) {
                subtrahend = 0x50e208;
                following = 0x50e210;
            }
        }
        foldDuplicate(run, fp);
        foldSubtract(run, fp, subtrahend);
        uint32_t top = foldTruncate(run, fp);
        foldSubtract(run, fp, following);
        run.put(receiver + 0x27c, top);
    }
    uint32_t bottom = foldTruncate(run, fp);
    // +0x284: bottom of the menu rectangle.
    run.put(receiver + 0x284, bottom);
    uint32_t container = receiver + 0x154;
    uint32_t centre = half(width);
    run.stackPointer = run.frame - 0x1c;
    uint32_t itemCount = run.call(0x4df630, container, {});
    uint32_t index = 0;
    if (s32(itemCount) > 0) {
        do {
            run.stackPointer = run.frame - 0x20;
            uint32_t item = run.call(0x4dd450, container, {index});
            if (item != 0) {
                run.stackPointer = run.frame - 0x20;
                uint32_t size = run.call(0x4dece0, item, {run.automatic(-0x8)});
                uint32_t itemWidth = run.get(size);
                uint32_t reach = half(itemWidth);
                uint32_t left = centre - reach;
                uint32_t right = reach + centre;
                uint32_t current = run.get(rect);
                if (s32(left) < s32(current))
                    run.put(rect, left);
                uint32_t edge = run.get(receiver + 0x280);
                if (s32(right) > s32(edge))
                    run.put(receiver + 0x280, right);
            }
            index = index + 1;
            run.stackPointer = run.frame - 0x1c;
            itemCount = run.call(0x4df630, container, {});
        } while (s32(index) < s32(itemCount));
    }
    uint32_t rowBottom = run.get(receiver + 0x284);
    uint32_t rowTop = run.get(receiver + 0x27c);
    run.stackPointer = run.frame - 0x28;
    run.call(0x4dd800, container, {1, rowTop, rowBottom});
    const uint32_t alignArguments[2] = {4, centre};
    FrameScope scope(run, 36);
    function_4dd5b0(run, container, alignArguments);
    return 0;
}

// 0x451900. thiscall, 1 stack argument (page id). Replaces the banner actor at
// +0x260 for page 0x4e22 or 0x4e25.
uint32_t function_451900(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t page = arguments[0];
    uint32_t banner = run.get(receiver + 0x260);
    if (banner != 0) {
        uint32_t flags = run.get(banner + 0x8);
        run.put(banner + 0x8, flags | 0x10000);
        uint32_t current = run.get(receiver + 0x260);
        uint32_t owner = run.get(current + 0xc);
        uint32_t list = run.get(owner + 0x8);
        run.stackPointer = run.frame - 0x10;
        run.call(0x4c92f0, list, {current});
        run.put(receiver + 0x260, 0);
    }
    uint32_t context = run.get(receiver + 0xc);
    uint32_t actors = run.get(context + 0x8);
    uint32_t order = page - 0x4e22;
    if (order == 0) {
        uint32_t cursor = run.get(0x537e88);
        if (cursor == 0)
            return 0;
        uint32_t service = run.get(cursor + 0x6c);
        uint32_t image = run.get(service + 0x14);
        if (image == 0)
            return 0;
        uint32_t count = run.get(image + 0x7c);
        uint32_t y = run.get(receiver + 0x28c);
        uint32_t frame = 5;
        if (s32(count) <= 1)
            frame = 6;
        uint32_t x = run.get(receiver + 0x288);
        run.stackPointer = run.frame - 0x24;
        uint32_t created = run.call(0x4c8da0, actors, {0, x, y, 0x270e, 0x5225e8, 0});
        run.put(receiver + 0x260, created);
        run.stackPointer = run.frame - 0x14;
        run.call(0x4c7900, created, {0x527f5c, frame});
        return 0;
    }
    if (order - 3 == 0) {
        uint32_t y = run.get(receiver + 0x28c);
        uint32_t x = run.get(receiver + 0x288);
        run.stackPointer = run.frame - 0x24;
        uint32_t created = run.call(0x4c8da0, actors, {0, x, y, 0x270e, 0x5225e8, 0});
        run.put(receiver + 0x260, created);
        run.stackPointer = run.frame - 0x14;
        run.call(0x4c7900, created, {0x527e84, 5});
    }
    return 0;
}

// 0x451c40. thiscall, 0 stack arguments. Rebuilds the dimming surface at +0x270
// and blits it centred; returns 1, or 0 when the surface cannot be created.
uint32_t function_451c40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t old = run.get(receiver + 0x270);
    if (old != 0) {
        uint32_t context = run.get(receiver + 0xc);
        uint32_t factory = run.get(context + 0x1c);
        run.stackPointer = run.frame - 0x48;
        run.call(0x4bc4f0, factory, {old});
    }
    uint32_t app = run.get(receiver + 0x4);
    uint32_t context = run.get(receiver + 0xc);
    uint32_t width = run.get(app + 0x7c);
    uint32_t height = run.get(app + 0x80);
    uint32_t factory = run.get(context + 0x1c);
    run.stackPointer = run.frame - 0x58;
    uint32_t surface = run.call(0x4bc670, factory, {width, height, 0, 0, 0xffffffff});
    run.put(receiver + 0x270, surface);
    if (surface == 0)
        return 0;
    uint32_t source = surface + 0x7c;
    uint32_t contextAgain = run.get(receiver + 0xc);
    uint32_t chain = run.get(contextAgain + 0x4);
    uint32_t renderer = run.get(chain + 0x14);
    uint32_t sourceLeft = run.get(source);
    // Locals: copied rectangle at -0x30, source rectangle at -0x20, target at -0x10.
    uint32_t copy = run.automatic(-0x30);
    uint32_t sourceCopy = run.automatic(-0x20);
    uint32_t target = run.automatic(-0x10);
    uint32_t surfaceUnit = run.get(renderer + 0x2c);
    run.put(sourceCopy, sourceLeft);
    uint32_t sourceTop = run.get(source + 0x4);
    run.put(sourceCopy + 0x4, sourceTop);
    uint32_t sourceRight = run.get(source + 0x8);
    run.put(sourceCopy + 0x8, sourceRight);
    uint32_t sourceBottom = run.get(source + 0xc);
    run.put(sourceCopy + 0xc, sourceBottom);
    run.stackPointer = run.frame - 0x4c;
    run.icall(0x546d58, {copy, sourceCopy});
    uint32_t copyLeft = run.get(copy);
    uint32_t copyRight = run.get(copy + 0x8);
    uint32_t left = spanStart(width, copyLeft, copyRight);
    uint32_t right = spanEnd(width, copyLeft, copyRight);
    run.put(target, left);
    uint32_t copyTop = run.get(copy + 0x4);
    uint32_t copyBottom = run.get(copy + 0xc);
    uint32_t top = spanStart(height, copyTop, copyBottom);
    uint32_t bottom = spanEnd(height, copyTop, copyBottom);
    run.put(target + 0xc, bottom);
    run.put(target + 0x4, top);
    run.put(target + 0x8, right);
    uint32_t held = run.get(receiver + 0x270);
    run.stackPointer = run.frame - 0x58;
    run.call(0x4b9ce0, held, {copy, surfaceUnit, target, 0x1000000, 0});
    return 1;
}

// 0x451d50. thiscall, 0 stack arguments. Enables or disables the option
// widgets from the presence of the "GAME_SELECT" sound entry and two app fields.
uint32_t function_451d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t found = run.automatic(-0x4);
    run.put(found, 0);
    uint32_t context = run.get(receiver + 0xc);
    uint32_t sounds = run.get(context + 0x28);
    run.stackPointer = run.frame - 0x20;
    run.call(0x4f6286, sounds + 0x10, {0x5279e4, found});
    uint32_t lookup = run.get(found);
    uint32_t app = run.get(receiver + 0x4);
    uint32_t video = run.get(app + 0x10);
    uint32_t hasSound = 0;
    if (lookup != 0)
        hasSound = 1;
    uint32_t extra = run.get(app + 0x50);
    uint32_t flagValue = run.get(extra + 0x28);
    uint32_t optionsEnabled = 1;
    if (hasSound == 0) {
        if (flagValue == 0)
            optionsEnabled = 0;
    }
    uint32_t container = receiver + 0x154;
    run.stackPointer = run.frame - 0x20;
    run.call(0x4dceb0, container, {0x59db, optionsEnabled});
    run.stackPointer = run.frame - 0x20;
    run.call(0x4dceb0, container, {0x5aa1, hasSound});
    uint32_t both = 0;
    if (hasSound != 0) {
        if (video != 0)
            both = 1;
    }
    run.stackPointer = run.frame - 0x20;
    run.call(0x4dceb0, container, {0x5aa2, both});
    run.stackPointer = run.frame - 0x20;
    run.call(0x4dceb0, container, {0x5aa3, both});
    run.stackPointer = run.frame - 0x20;
    run.call(0x4dceb0, container, {0x5aa4, flagValue});
    return 0;
}

// 0x451f00. thiscall, 0 stack arguments. Registers the eighteen menu entries
// in the string map at +0x2b4, each with its hotkey letter.
uint32_t function_451f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t map = receiver + 0x2b4;
    run.stackPointer = run.frame - 0xc;
    uint32_t slot = run.call(0x4f62a8, map, {0x528114});
    run.put(slot, 0x52);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x528108});
    run.put(slot, 0x4c);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x528100});
    run.put(slot, 0x4f);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280f8});
    run.put(slot, 0x48);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280ec});
    run.put(slot, 0x45);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x52700c});
    run.put(slot, 0x59);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x527024});
    run.put(slot, 0x4e);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280e0});
    run.put(slot, 0x43);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280d8});
    run.put(slot, 0x49);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280d0});
    run.put(slot, 0x41);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280c8});
    run.put(slot, 0x42);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x525704});
    run.put(slot, 0x53);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5256f4});
    run.put(slot, 0x41);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5256fc});
    run.put(slot, 0x56);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x52570c});
    run.put(slot, 0x4d);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280c0});
    run.put(slot, 0x46);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280b8});
    run.put(slot, 0x47);
    run.stackPointer = run.frame - 0xc;
    slot = run.call(0x4f62a8, map, {0x5280b0});
    run.put(slot, 0x4d);
    return 0;
}

// Sets bit 0 of the flags at +0x40 of an actor.
void disableActor(Run &run, uint32_t actor) {
    uint32_t flags = run.get(actor + 0x40);
    run.put(actor + 0x40, flags | 1);
}

// 0x4525a0. thiscall, 1 stack argument (page id). Sets or clears the disabled
// bit of the three audio option actors at +0x264, +0x268 and +0x26c from the
// state of the matching widgets, then refreshes the page.
uint32_t function_4525a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t page = arguments[0];
    uint32_t container = receiver + 0x154;
    if (page == 0x59da) {
        uint32_t actor = run.get(receiver + 0x26c);
        if (actor != 0) {
            run.stackPointer = run.frame - 0x10;
            uint32_t widget = run.call(0x4dd020, container, {0x5b06});
            if (widget != 0) {
                uint32_t state = widget + 0x3c;
                if (state != 0) {
                    run.stackPointer = run.frame - 0xc;
                    uint32_t bits = run.call(0x4ed050, state, {});
                    uint32_t actorAgain = run.get(receiver + 0x26c);
                    uint32_t flags = run.get(actorAgain + 0x40);
                    if (bits & 0x20)
                        flags = flags | 1;
                    else
                        flags = flags & 0xfffffffe;
                    run.put(actorAgain + 0x40, flags);
                }
            }
        }
        run.stackPointer = run.frame - 0xc;
        run.call(0x452800, receiver, {});
        return 0;
    }
    if (page == 0x59db) {
        uint32_t first = run.get(receiver + 0x264);
        if (first != 0) {
            run.stackPointer = run.frame - 0x10;
            uint32_t widget = run.call(0x4dd020, container, {0x5aa1});
            if (widget != 0) {
                uint32_t state = widget + 0x3c;
                if (state != 0) {
                    run.stackPointer = run.frame - 0xc;
                    uint32_t bits = run.call(0x4ed050, state, {});
                    uint32_t actorAgain = run.get(receiver + 0x264);
                    uint32_t flags = run.get(actorAgain + 0x40);
                    if (bits & 0x20)
                        flags = flags | 1;
                    else
                        flags = flags & 0xfffffffe;
                    run.put(actorAgain + 0x40, flags);
                }
            }
        }
        uint32_t second = run.get(receiver + 0x268);
        if (second != 0) {
            run.stackPointer = run.frame - 0x10;
            uint32_t widget = run.call(0x4dd020, container, {0x5aa4});
            if (widget != 0) {
                uint32_t state = widget + 0x3c;
                if (state != 0) {
                    run.stackPointer = run.frame - 0xc;
                    uint32_t bits = run.call(0x4ed050, state, {});
                    uint32_t actorAgain = run.get(receiver + 0x268);
                    uint32_t flags = run.get(actorAgain + 0x40);
                    if (bits & 0x20)
                        flags = flags | 1;
                    else
                        flags = flags & 0xfffffffe;
                    run.put(actorAgain + 0x40, flags);
                }
            }
        }
        run.stackPointer = run.frame - 0xc;
        run.call(0x452870, receiver, {});
        return 0;
    }
    uint32_t first = run.get(receiver + 0x264);
    if (first != 0)
        disableActor(run, first);
    uint32_t second = run.get(receiver + 0x268);
    if (second != 0)
        disableActor(run, second);
    uint32_t third = run.get(receiver + 0x26c);
    if (third != 0)
        disableActor(run, third);
    return 0;
}

// 0x46ddf0. thiscall, 0 stack arguments. For 8 bit surfaces, masks alternate
// rows of the back buffer to two colour channels; for 16 bit surfaces calls
// 0x46df20 instead.
uint32_t function_46ddf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t app = run.get(receiver + 0x4);
    uint32_t depth = run.get(app + 0x78);
    if (depth == 0x10) {
        run.stackPointer = run.frame - 0x24;
        run.call(0x46df20, receiver, {});
        return 0;
    }
    if (depth != 8)
        return 0;
    uint32_t context = run.get(receiver + 0xc);
    uint32_t palette = run.get(context + 0x8);
    uint32_t chain = run.get(context + 0x4);
    uint32_t source = run.get(chain + 0x14);
    uint32_t unit = run.get(context + 0x24);
    run.stackPointer = run.frame - 0x2c;
    run.call(0x4cb9b0, unit, {source, palette});
    uint32_t contextAgain = run.get(receiver + 0xc);
    uint32_t chainAgain = run.get(contextAgain + 0x4);
    uint32_t target = run.get(chainAgain + 0x14);
    uint32_t surface = run.get(target + 0x2c);
    run.stackPointer = run.frame - 0x28;
    uint32_t pixels = run.call(0x4b9730, surface, {0});
    if (pixels == 0)
        return 0;
    uint32_t rows = run.get(surface + 0x14);
    uint32_t row = 0;
    if (rows != 0) {
        do {
            uint32_t pitch = run.get(surface + 0x1c);
            uint32_t width = run.get(surface + 0x18);
            uint32_t cursor = pitch * row + pixels;
            uint32_t words = wordCount(width);
            if (s32(words) > 0) {
                uint32_t odd = row & 1;
                uint32_t column = 0;
                do {
                    uint32_t pixel = run.get(cursor);
                    uint32_t byte0 = pixel & 0xff;
                    uint32_t byte1 = (pixel >> 8) & 0xff;
                    uint32_t byte2 = (pixel >> 16) & 0xff;
                    uint32_t byte3 = pixel >> 24;
                    if (odd != 0) {
                        byte0 = 0;
                        byte2 = 0;
                    } else {
                        byte1 = 0;
                        byte3 = 0;
                    }
                    uint32_t packed = (byte3 << 24) | (byte2 << 16) | (byte1 << 8) | byte0;
                    run.put(cursor, packed);
                    cursor = cursor + 4;
                    column = column + 1;
                    uint32_t widthAgain = run.get(surface + 0x18);
                    words = wordCount(widthAgain);
                } while (s32(column) < s32(words));
            }
            row = row + 1;
            rows = run.get(surface + 0x14);
        } while (row < rows);
    }
    uint32_t direct = run.get(surface + 0x8);
    uint32_t vtable = run.get(direct);
    uint32_t unlock = run.get(vtable + 0x80);
    run.stackPointer = run.frame - 0x2c;
    run.call(unlock, 0, {direct, 0});
    return 0;
}

// 0x46dd90. thiscall, 0 stack arguments.
uint32_t function_46dd90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_46ddf0(run, receiver, arguments);
    uint32_t context = run.get(receiver + 0xc);
    uint32_t chain = run.get(context + 0x4);
    uint32_t screen = run.get(chain + 0x10);
    uint32_t unit = run.get(screen + 0x2c);
    run.stackPointer = run.frame - 0xc;
    run.call(0x4b98b0, unit, {0});
    uint32_t contextAgain = run.get(receiver + 0xc);
    uint32_t chainAgain = run.get(contextAgain + 0x4);
    run.stackPointer = run.frame - 0x8;
    run.call(0x4cab10, chainAgain, {});
    return 0;
}

// 0x450610. thiscall, 0 stack arguments. Reads the input state, moves the
// selection, and returns 1 unless the repeat delay is still running with no
// key held.
uint32_t function_450610(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t input = run.get(0x537200);
    run.stackPointer = run.frame - 0x20;
    run.call(0x4b3490, input, {});
    uint32_t container = receiver + 0x154;
    uint32_t result = 1;
    run.stackPointer = run.frame - 0x20;
    uint32_t selected = run.call(0x4dd480, container, {});
    input = run.get(0x537200);
    uint32_t keys = run.get(input + 0x210);
    if (keys & 0x80000000u) {
        run.stackPointer = run.frame - 0x20;
        run.vcall(container, 0x4);
        uint32_t repeat = run.get(0x528a60);
        run.put(receiver + 0x2a4, repeat);
    } else if (keys & 0x40000000u) {
        run.stackPointer = run.frame - 0x20;
        run.vcall(container, 0x0);
        uint32_t repeat = run.get(0x528a60);
        run.put(receiver + 0x2a4, repeat);
    } else if (keys & 0x10000000u) {
        run.stackPointer = run.frame - 0x24;
        run.call(0x452080, receiver, {1});
        uint32_t repeat = run.get(0x528a60);
        run.put(receiver + 0x2a4, repeat);
    } else if (keys & 0x20000000u) {
        run.stackPointer = run.frame - 0x24;
        run.call(0x452080, receiver, {0});
        uint32_t repeat = run.get(0x528a60);
        run.put(receiver + 0x2a4, repeat);
    } else if (keys & 0x100) {
        run.stackPointer = run.frame - 0x24;
        run.call(0x450cf0, receiver, {0x4e21});
    } else if (keys & 0xffffff) {
        run.stackPointer = run.frame - 0x20;
        run.call(0x4ddbc0, container, {});
    } else {
        uint32_t held = run.get(input + 0x214);
        if ((held & 0xf0000000u) == 0) {
            result = 0;
        } else {
            uint32_t timer = run.get(receiver + 0x2a4);
            uint32_t elapsed = run.get(0x53720c);
            if (elapsed < timer)
                run.put(receiver + 0x2a4, timer - elapsed);
            else
                run.put(receiver + 0x2a4, 0);
            uint32_t remaining = run.get(receiver + 0x2a4);
            if (remaining != 0) {
                result = 0;
            } else {
                uint32_t inputAgain = run.get(0x537200);
                uint32_t pressed = run.get(inputAgain + 0x214);
                if (pressed & 0x80000000u) {
                    run.stackPointer = run.frame - 0x20;
                    run.vcall(container, 0x4);
                    uint32_t repeat = run.get(0x528a64);
                    run.put(receiver + 0x2a4, repeat);
                } else if (pressed & 0x40000000u) {
                    run.stackPointer = run.frame - 0x20;
                    run.vcall(container, 0x0);
                    uint32_t repeat = run.get(0x528a64);
                    run.put(receiver + 0x2a4, repeat);
                } else {
                    uint32_t flag = 0;
                    if (pressed & 0x10000000u)
                        flag = 1;
                    run.stackPointer = run.frame - 0x24;
                    run.call(0x452080, receiver, {flag});
                    uint32_t repeat = run.get(0x528a64);
                    run.put(receiver + 0x2a4, repeat);
                }
            }
        }
    }
    if (result != 0) {
        run.stackPointer = run.frame - 0x20;
        uint32_t now = run.call(0x4dd480, container, {});
        if (selected != now) {
            run.stackPointer = run.frame - 0x20;
            uint32_t current = run.call(0x4dd480, container, {});
            run.stackPointer = run.frame - 0x24;
            uint32_t item = run.call(0x4dd450, container, {current});
            if (item != 0) {
                uint32_t app = run.get(receiver + 0x4);
                uint32_t services = run.get(app + 0x30);
                uint32_t sounds = run.get(services + 0x28);
                uint32_t muted = run.get(sounds + 0x30);
                if (muted == 0) {
                    uint32_t found = run.automatic(-0xc);
                    run.put(found, 0);
                    run.stackPointer = run.frame - 0x28;
                    run.call(0x4f6286, sounds + 0x10, {0x524678, found});
                    uint32_t entry = run.get(found);
                    if (entry != 0) {
                        uint32_t soundOn = run.get(0x532c0c);
                        uint32_t soundId = run.get(0x532c10);
                        if (soundOn != 0) {
                            uint32_t player = run.get(entry + 0x10);
                            run.stackPointer = run.frame - 0x30;
                            run.call(0x4b45f0, player, {soundId, 0, 0, 0});
                        }
                    }
                }
                uint32_t position = run.automatic(-0x8);
                run.stackPointer = run.frame - 0x24;
                run.call(0x4ded20, item, {position});
                uint32_t y = run.get(position + 0x4);
                uint32_t coinLeft = run.get(receiver + 0x258);
                run.put(coinLeft + 0x50, y + 0x11);
                uint32_t yAgain = run.get(position + 0x4);
                uint32_t coinRight = run.get(receiver + 0x25c);
                run.put(coinRight + 0x50, yAgain + 0x11);
            }
        }
    }
    return result;
}

// 0x450060. thiscall, 0 stack arguments. Runs one frame of the menu: input,
// audio state, actor updates, background blit, cursor, actor draws and the
// closing countdown. Returns 0 only when the menu is not ready.
uint32_t function_450060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t context = run.get(receiver + 0xc);
    uint32_t chain = run.get(context + 0x4);
    uint32_t screen = run.get(chain + 0x10);
    uint32_t unit = run.get(screen + 0x2c);
    uint32_t flip = run.get(unit + 0x8);
    bool ready = false;
    if (flip != 0) {
        uint32_t flipTable = run.get(flip);
        run.stackPointer = run.frame - 0x50;
        uint32_t status = run.call(run.get(flipTable + 0x60), 0, {flip});
        if (status == 0)
            ready = true;
    }
    if (!ready) {
        run.stackPointer = run.frame - 0x4c;
        uint32_t answer = run.vcall(receiver, 0x18);
        if (answer == 0) {
            uint32_t app = run.get(receiver + 0x4);
            run.stackPointer = run.frame - 0x54;
            run.call(0x429e10, app, {0x8006, 0x7d0});
            return 0;
        }
    }
    uint32_t closing = run.get(receiver + 0x2a0);
    if (closing != 0)
        return 1;
    {
        FrameScope scope(run, 0x4c);
        function_450610(run, receiver, arguments);
    }
    uint32_t page = run.get(receiver + 0x298);
    const uint32_t audioArguments[1] = {page};
    function_4525a0(run, receiver, audioArguments);
    uint32_t elapsed = run.get(0x53720c);
    uint32_t source = run.get(0x537208);
    run.put(0x5430c4, elapsed);
    run.put(0x5430c8, source);
    uint32_t cursorActor = run.get(receiver + 0x254);
    if (cursorActor != 0) {
        uint32_t service = run.get(cursorActor + 0x6c);
        run.stackPointer = run.frame - 0x50;
        run.call(run.get(service + 0x10), 0, {cursorActor});
    }
    uint32_t coinLeft = run.get(receiver + 0x258);
    if (coinLeft != 0) {
        uint32_t service = run.get(coinLeft + 0x6c);
        run.stackPointer = run.frame - 0x50;
        run.call(run.get(service + 0x10), 0, {coinLeft});
    }
    uint32_t coinRight = run.get(receiver + 0x25c);
    if (coinRight != 0) {
        uint32_t service = run.get(coinRight + 0x6c);
        run.stackPointer = run.frame - 0x50;
        run.call(run.get(service + 0x10), 0, {coinRight});
    }
    // Locals: cursor point at -0x38, copied rectangle at -0x30, source
    // rectangle at -0x20, target rectangle at -0x10.
    uint32_t point = run.automatic(-0x38);
    uint32_t copy = run.automatic(-0x30);
    uint32_t sourceCopy = run.automatic(-0x20);
    uint32_t target = run.automatic(-0x10);
    uint32_t surface = run.get(receiver + 0x270);
    uint32_t sourceRect = surface + 0x7c;
    uint32_t contextAgain = run.get(receiver + 0xc);
    uint32_t sourceLeft = run.get(sourceRect);
    uint32_t chainAgain = run.get(contextAgain + 0x4);
    uint32_t renderer = run.get(chainAgain + 0x14);
    run.put(sourceCopy, sourceLeft);
    uint32_t sourceTop = run.get(sourceRect + 0x4);
    run.put(sourceCopy + 0x4, sourceTop);
    uint32_t sourceRight = run.get(sourceRect + 0x8);
    run.put(sourceCopy + 0x8, sourceRight);
    uint32_t sourceBottom = run.get(sourceRect + 0xc);
    run.put(sourceCopy + 0xc, sourceBottom);
    run.stackPointer = run.frame - 0x54;
    run.icall(0x546d58, {copy, sourceCopy});
    uint32_t app = run.get(receiver + 0x4);
    uint32_t width = run.get(app + 0x7c);
    uint32_t height = run.get(app + 0x80);
    uint32_t copyLeft = run.get(copy);
    uint32_t copyRight = run.get(copy + 0x8);
    uint32_t left = spanStart(width, copyLeft, copyRight);
    uint32_t right = spanEnd(width, copyLeft, copyRight);
    run.put(target, left);
    uint32_t copyTop = run.get(copy + 0x4);
    uint32_t copyBottom = run.get(copy + 0xc);
    uint32_t top = spanStart(height, copyTop, copyBottom);
    uint32_t bottom = spanEnd(height, copyTop, copyBottom);
    run.put(target + 0xc, bottom);
    run.put(target + 0x4, top);
    run.put(target + 0x8, right);
    uint32_t blitter = run.get(renderer + 0x2c);
    uint32_t held = run.get(receiver + 0x270);
    run.stackPointer = run.frame - 0x60;
    run.call(0x4b9ce0, blitter, {target, held, copy, 0x1000000, 0});
    run.stackPointer = run.frame - 0x50;
    run.icall(0x546cd0, {point});
    uint32_t cursorAgain = run.get(receiver + 0x254);
    if (cursorAgain != 0) {
        uint32_t offsetX = run.get(receiver + 0x2ac);
        uint32_t x = run.get(point);
        run.put(cursorAgain + 0x4c, offsetX + x);
        uint32_t offsetY = run.get(receiver + 0x2b0);
        uint32_t y = run.get(point + 0x4);
        uint32_t cursorFinal = run.get(receiver + 0x254);
        run.put(cursorFinal + 0x50, offsetY + y);
    }
    uint32_t banner = run.get(receiver + 0x260);
    if (banner != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(banner, 0x2c, {renderer});
    }
    uint32_t coinLeftDraw = run.get(receiver + 0x258);
    if (coinLeftDraw != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(coinLeftDraw, 0x2c, {renderer});
    }
    uint32_t coinRightDraw = run.get(receiver + 0x25c);
    if (coinRightDraw != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(coinRightDraw, 0x2c, {renderer});
    }
    uint32_t drawTarget = run.get(renderer + 0x2c);
    run.stackPointer = run.frame - 0x50;
    run.call(0x4dd270, receiver + 0x154, {drawTarget});
    uint32_t firstOption = run.get(receiver + 0x264);
    if (firstOption != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(firstOption, 0x2c, {renderer});
    }
    uint32_t secondOption = run.get(receiver + 0x268);
    if (secondOption != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(secondOption, 0x2c, {renderer});
    }
    uint32_t thirdOption = run.get(receiver + 0x26c);
    if (thirdOption != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(thirdOption, 0x2c, {renderer});
    }
    uint32_t cursorLast = run.get(receiver + 0x254);
    if (cursorLast != 0) {
            run.stackPointer = run.frame - 0x50;
            run.vcall(cursorLast, 0x2c, {renderer});
    }
    uint32_t contextLast = run.get(receiver + 0xc);
    uint32_t chainLast = run.get(contextLast + 0x4);
    uint32_t screenLast = run.get(chainLast + 0x10);
    uint32_t unitLast = run.get(screenLast + 0x2c);
    run.stackPointer = run.frame - 0x50;
    run.call(0x4b98b0, unitLast, {0});
    uint32_t appLast = run.get(receiver + 0x4);
    uint32_t timed = run.get(appLast + 0x9c);
    if (timed == 0)
        return 1;
    uint32_t countdown = run.get(receiver + 0x29c);
    uint32_t step = run.get(0x54132c);
    if (step < countdown) {
        run.put(receiver + 0x29c, countdown - step);
        return 1;
    }
    run.put(receiver + 0x29c, 0);
    run.put(receiver + 0x2a0, 1);
    run.stackPointer = run.frame - 0x50;
    run.call(0x450cf0, receiver, {0x4e21});
    return 1;
}

// 0x44fad0. thiscall, 1 stack argument (reason). Builds the menu actors and
// cursor when the menu opens; reason 0xd does nothing and 9 plays the opening
// sequence. Returns 1.
uint32_t function_44fad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t reason = arguments[0];
    if (reason == 0xd)
        return 1;
    uint32_t app = run.get(receiver + 0x4);
    uint32_t rect = receiver + 0x278;
    uint32_t width = run.get(app + 0x7c);
    uint32_t height = run.get(app + 0x80);
    run.stackPointer = run.frame - 0x30;
    run.icall(0x546d5c, {rect, 0, 0, width, height});
    uint32_t centreX = half(width);
    run.put(receiver + 0x288, centreX);
    uint32_t centreY = half(height) - 0x64;
    run.put(receiver + 0x29c, 0x1b58);
    run.put(receiver + 0x28c, centreY);
    run.put(receiver + 0x2a8, 0);
    {
        const uint32_t layoutArguments[1] = {0x2710};
        FrameScope scope(run, 32);
        function_451770(run, receiver, layoutArguments);
    }
    // The cursor point and the lookup result share the local at -0x8.
    uint32_t point = run.automatic(-0x8);
    if (reason == 9) {
        uint32_t state = run.get(receiver + 0x274);
        if (state != 0) {
            run.stackPointer = run.frame - 0x20;
            run.call(0x48f470, state, {0xfa});
            uint32_t stateAgain = run.get(receiver + 0x274);
            function_46dd90(run, stateAgain, arguments);
            uint32_t stateThird = run.get(receiver + 0x274);
            run.stackPointer = run.frame - 0x1c;
            run.call(0x46dde0, stateThird, {});
            uint32_t context = run.get(receiver + 0xc);
            uint32_t chain = run.get(context + 0x4);
            uint32_t screen = run.get(chain + 0x10);
            uint32_t unit = run.get(screen + 0x2c);
            run.stackPointer = run.frame - 0x20;
            run.call(0x4b98b0, unit, {0});
            uint32_t stateLast = run.get(receiver + 0x274);
            run.stackPointer = run.frame - 0x1c;
            run.call(0x46dde0, stateLast, {});
        }
    } else {
        uint32_t ui = run.get(0x5371fc);
        uint32_t services = run.get(ui + 0x30);
        uint32_t sounds = run.get(services + 0x28);
        uint32_t muted = run.get(sounds + 0x30);
        if (muted == 0) {
            run.put(point, 0);
            run.stackPointer = run.frame - 0x24;
            run.call(0x4f6286, sounds + 0x10, {0x5279e4, point});
            uint32_t entry = run.get(point);
            if (entry != 0) {
                uint32_t soundOn = run.get(0x532c0c);
                uint32_t soundId = run.get(0x532c10);
                if (soundOn != 0) {
                    uint32_t player = run.get(entry + 0x10);
                    run.stackPointer = run.frame - 0x2c;
                    run.call(0x4b45f0, player, {soundId, 0, 0, 0});
                }
            }
        }
    }
    uint32_t context = run.get(receiver + 0xc);
    uint32_t cursor = run.get(receiver + 0x254);
    uint32_t actors = run.get(context + 0x8);
    if (cursor == 0) {
        run.stackPointer = run.frame - 0x20;
        run.icall(0x546cd0, {point});
        uint32_t y = run.get(point + 0x4);
        uint32_t x = run.get(point);
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, x, y, 0x4e1e, 0x522658, 0});
        run.put(receiver + 0x254, created);
        run.stackPointer = run.frame - 0x20;
        run.call(0x4c7970, created, {0x526d90});
        uint32_t cursorAgain = run.get(receiver + 0x254);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c79e0, cursorAgain, {0x526d90, 0});
        uint32_t cursorHeld = run.get(receiver + 0x254);
        uint32_t image = run.get(cursorHeld + 0x174);
        if (image != 0) {
            uint32_t imageWidth = run.get(image + 0x10);
            run.put(receiver + 0x2ac, half(imageWidth));
            uint32_t imageHeight = run.get(image + 0x14);
            run.put(receiver + 0x2b0, half(imageHeight));
        }
        uint32_t offsetX = run.get(receiver + 0x2ac);
        uint32_t pointX = run.get(point);
        run.put(cursorHeld + 0x4c, offsetX + pointX);
        uint32_t offsetY = run.get(receiver + 0x2b0);
        uint32_t pointY = run.get(point + 0x4);
        uint32_t cursorLast = run.get(receiver + 0x254);
        run.put(cursorLast + 0x50, offsetY + pointY);
    }
    uint32_t coinLeft = run.get(receiver + 0x258);
    if (coinLeft == 0) {
        uint32_t top = run.get(receiver + 0x27c);
        uint32_t left = run.get(rect);
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, left - 0x1e, top + 0x11, 0x270e, 0x5224d8, 0});
        run.put(receiver + 0x258, created);
        run.stackPointer = run.frame - 0x20;
        run.call(0x4c7970, created, {0x5279b8});
        uint32_t coinAgain = run.get(receiver + 0x258);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c79e0, coinAgain, {0x5240d8, 0});
    }
    uint32_t coinRight = run.get(receiver + 0x25c);
    if (coinRight == 0) {
        uint32_t top = run.get(receiver + 0x27c);
        uint32_t right = run.get(receiver + 0x280);
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, right + 0x1e, top + 0x11, 0x270e, 0x5224d8, 0});
        run.put(receiver + 0x25c, created);
        run.stackPointer = run.frame - 0x20;
        run.call(0x4c7970, created, {0x5279b8});
        uint32_t coinAgain = run.get(receiver + 0x25c);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c79e0, coinAgain, {0x5240d8, 0});
    }
    uint32_t firstOption = run.get(receiver + 0x264);
    if (firstOption == 0) {
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, 0xffffffce, 0xffffffce, 0x270f, 0x5225e8, 0});
        run.put(receiver + 0x264, created);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c7900, created, {0x527e60, 0x2a});
    }
    uint32_t secondOption = run.get(receiver + 0x268);
    if (secondOption == 0) {
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, 0xffffffce, 0xffffffce, 0x270f, 0x5225e8, 0});
        run.put(receiver + 0x268, created);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c7900, created, {0x527e60, 0x2b});
    }
    uint32_t thirdOption = run.get(receiver + 0x26c);
    if (thirdOption == 0) {
        run.stackPointer = run.frame - 0x34;
        uint32_t created = run.call(0x4c8da0, actors, {0, 0xffffffce, 0xffffffce, 0x270f, 0x5225e8, 0});
        run.put(receiver + 0x26c, created);
        run.stackPointer = run.frame - 0x24;
        run.call(0x4c7900, created, {0x527e60, 0x2d});
    }
    if (reason == 9) {
            run.stackPointer = run.frame - 0x20;
            run.call(0x451680, receiver, {0x2710});
    }
    uint32_t appLast = run.get(receiver + 0x4);
    uint32_t input = run.get(appLast + 0x4);
    run.stackPointer = run.frame - 0x24;
    run.call(0x4b8910, input, {0x100, 0x40});
    run.stackPointer = run.frame - 0x20;
    uint32_t shown = run.icall(0x546d54, {0});
    if (s32(shown) >= 0) {
        do {
            run.stackPointer = run.frame - 0x20;
            shown = run.icall(0x546d54, {0});
        } while (s32(shown) >= 0);
    }
    run.stackPointer = run.frame - 0x1c;
    run.call(0x452ae0, receiver, {});
    return 1;
}

// 0x44f880. thiscall, 3 stack arguments. Initializes the menu object for the
// state returned by 0x42bfd0 (kind 3 or 4). Returns 1 on success.
uint32_t function_44f880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t first = arguments[0];
    uint32_t second = arguments[1];
    uint32_t third = arguments[2];
    run.stackPointer = run.frame - 0x14;
    uint32_t state = run.call(0x42bfd0, first, {});
    run.put(receiver + 0x274, state);
    run.stackPointer = run.frame - 0x14;
    uint32_t kind = run.vcall(state, 0x10);
    if (kind != 3) {
        uint32_t stateAgain = run.get(receiver + 0x274);
        run.stackPointer = run.frame - 0x14;
        kind = run.vcall(stateAgain, 0x10);
        if (kind != 4)
            return 0;
    }
    run.put(0x53789c, receiver);
    run.put(receiver + 0x254, 0);
    run.put(receiver + 0x260, 0);
    run.put(receiver + 0x258, 0);
    run.put(receiver + 0x25c, 0);
    run.put(receiver + 0x270, 0);
    run.put(receiver + 0x264, 0);
    run.put(receiver + 0x268, 0);
    run.put(receiver + 0x26c, 0);
    run.put(receiver + 0x2a0, 0);
    run.put(receiver + 0x298, 0x2710);
    run.put(receiver + 0x29c, 0x1b58);
    uint32_t repeat = run.get(0x528a60);
    run.put(receiver + 0x2a4, repeat);
    run.put(receiver + 0x2a8, 0);
    run.put(receiver + 0x290, 0);
    run.put(receiver + 0x294, 0);
    run.put(receiver + 0x2ac, 0);
    run.put(receiver + 0x2b0, 0);
    uint32_t holder = run.get(0x537204);
    run.stackPointer = run.frame - 0x14;
    run.call(0x431300, holder, {});
    uint32_t holderAgain = run.get(0x537204);
    run.put(holderAgain + 0xc, 0xffffffff);
    uint32_t input = run.get(0x537200);
    run.stackPointer = run.frame - 0x14;
    run.call(0x4b3ab0, input, {});
    uint32_t inputAgain = run.get(0x537200);
    run.put(inputAgain + 0x20c, 0xffffffff);
    run.stackPointer = run.frame - 0x20;
    uint32_t built = run.call(0x48f0d0, receiver, {first, second, third});
    if (built == 0)
        return 0;
    uint32_t app = run.get(receiver + 0x4);
    uint32_t rect = receiver + 0x278;
    uint32_t width = run.get(app + 0x7c);
    uint32_t height = run.get(app + 0x80);
    run.stackPointer = run.frame - 0x28;
    run.icall(0x546d5c, {rect, 0, 0, width, height});
    run.put(receiver + 0x288, half(width));
    run.put(receiver + 0x28c, half(height) - 0x64);
    uint32_t appAgain = run.get(receiver + 0x4);
    uint32_t font = run.get(appAgain + 0xf0);
    if (font != 0) {
        uint32_t context = run.get(receiver + 0xc);
        uint32_t extent = run.get(font + 0x14);
        uint32_t manager = run.get(context + 0x1c);
        run.stackPointer = run.frame - 0x28;
        uint32_t resource = run.call(0x4b61c0, font, {});
        run.stackPointer = run.frame - 0x30;
        uint32_t loaded = run.call(0x4dcdf0, receiver + 0x154, {manager, resource, extent, 0x4529f0, 0, 0, 0});
        if (loaded == 0)
            return 0;
    }
    function_451f00(run, receiver, arguments);
    {
        const uint32_t layoutArguments[1] = {0x2710};
        FrameScope scope(run, 24);
        function_451770(run, receiver, layoutArguments);
    }
    {
        const uint32_t bannerArguments[1] = {0x2710};
        function_451900(run, receiver, bannerArguments);
    }
    {
        FrameScope scope(run, 20);
        function_451d50(run, receiver, arguments);
    }
    run.stackPointer = run.frame - 0x18;
    run.call(0x4dd0d0, receiver + 0x154, {0});
    run.put(receiver + 0x174, 1);
    uint32_t appThird = run.get(receiver + 0x4);
    uint32_t inputThird = run.get(appThird + 0x4);
    run.stackPointer = run.frame - 0x1c;
    run.call(0x4b8910, inputThird, {0x100, 0x40});
    uint32_t appFourth = run.get(receiver + 0x4);
    uint32_t inputFourth = run.get(appFourth + 0x4);
    run.stackPointer = run.frame - 0x1c;
    run.call(0x4b8910, inputFourth, {0x201, 0x40});
    {
        const uint32_t audioArguments[1] = {0x2710};
        function_4525a0(run, receiver, audioArguments);
    }
    uint32_t surfaceOk = 0;
    {
        FrameScope scope(run, 20);
        surfaceOk = function_451c40(run, receiver, arguments);
    }
    if (surfaceOk != 0)
        return 1;
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44f880:
        return function_44f880(run, receiver, arguments);
    case 0x44fad0:
        return function_44fad0(run, receiver, arguments);
    case 0x450060:
        return function_450060(run, receiver, arguments);
    case 0x450610:
        return function_450610(run, receiver, arguments);
    case 0x451770:
        return function_451770(run, receiver, arguments);
    case 0x451900:
        return function_451900(run, receiver, arguments);
    case 0x451c40:
        return function_451c40(run, receiver, arguments);
    case 0x451d50:
        return function_451d50(run, receiver, arguments);
    case 0x451f00:
        return function_451f00(run, receiver, arguments);
    case 0x4525a0:
        return function_4525a0(run, receiver, arguments);
    case 0x46dd90:
        return function_46dd90(run, receiver, arguments);
    case 0x46ddf0:
        return function_46ddf0(run, receiver, arguments);
    case 0x4dd5b0:
        return function_4dd5b0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_in_game_menu_entry, owned, body)
