// Level 8 Gabriel core
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
    case 0x405f60:
        return 1;
    case 0x443290:
        return 1;
    case 0x4433b0:
        return 1;
    case 0x443ab0:
        return 1;
    case 0x444120:
        return 1;
    case 0x444140:
        return 0;
    case 0x4441b0:
        return 0;
    case 0x4441f0:
        return 0;
    case 0x4442c0:
        return 0;
    case 0x444330:
        return 0;
    default:
        return -1;
    }
}

// Anim lookup used by the constructor: ask the sprite for a name and fall back
// to GAME_NULL when the lookup returns zero. `animations` is receiver + 0x128.
uint32_t lookupAnimation(Run &run, uint32_t animations, uint32_t name) {
    uint32_t found = run.call(0x4062e0, animations, {name});
    if (found == 0)
        found = run.call(0x4062e0, animations, {0x5234b4});
    return found;
}

// Sound lookup through the resource finder 0x4f6286; the result goes through a
// zeroed local at the first argument slot of the constructor frame.
uint32_t lookupSound(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t scene = run.get(sprite + 0xc);
    uint32_t finder = run.get(scene + 0x28) + 0x10;
    run.call(0x4f6286, finder, {name, local});
    return run.get(local);
}

// Resource lookup through 0x4061b0 on the scene object's +0x28 member.
uint32_t lookupResource(Run &run, uint32_t receiver, uint32_t name) {
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t scene = run.get(sprite + 0xc);
    uint32_t finder = run.get(scene + 0x28);
    return run.call(0x4061b0, finder, {name});
}

// x87 transport of `ftol`: the state holds the value to convert in ST(0).
uint32_t convertTop(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, fp);
}

// Shared by the startup, idle and choose paths: sprite animation selection by
// the signed remainder of rand modulo 100.
uint32_t pickIdleAnimation(Run &run, uint32_t receiver) {
    uint32_t random = run.call(0x4a3050, 0, {});
    int32_t remainder = s32(random) % 100;
    if (remainder < 0x32)
        return run.get(receiver + 0x460);
    return run.get(receiver + 0x464);
}

// 0x405f60. Plays sound `argument` on the actor at +0xc when it is nonzero.
uint32_t function_405f60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t sound = arguments[0];
    if (sound != 0) {
        uint32_t actor = run.get(receiver + 0xc);
        run.call(0x48ce40, 0, {actor, sound, 0});
    }
    return 0;
}

uint32_t function_443ab0(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp);

// 0x443290. State driver: argument +0x6c is a record with +0x18 the Gabriel
// object and +0x1c its state number.
uint32_t function_443290(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    (void)receiver;
    uint32_t context = arguments[0];
    uint32_t record = run.get(context + 0x6c);
    uint32_t state = run.get(record + 0x1c);
    if (state > 0x1d) {
        if (state == 0x1e) {
            uint32_t object = run.get(record + 0x18);
            run.vcall(object, 0x1c);
            return 1;
        }
        if (state == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
        return 1;
    }
    if (state == 0x1d) {
        uint32_t object = run.get(record + 0x18);
        run.vcall(object, 0x20);
        return 1;
    }
    if (state != 0) {
        run.call(0x4dc870, 0, {run.get(record + 0x18)});
        return 1;
    }
    run.put(record + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x538});
    uint32_t object = 0;
    if (memory != 0) {
        uint32_t saved = run.frame;
        run.frame = saved - 0x1c;
        uint32_t constructorArguments[1] = {context};
        object = function_443ab0(run, memory, constructorArguments, fp);
        run.frame = saved;
    }
    run.vcall(object, 0x10);
    run.put(record + 0x18, object);
    return 1;
}

// 0x4433b0. Dispatch through the callback table at 0x537728 by signed key.
uint32_t function_4433b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t key = arguments[0];
    uint32_t low = run.get(0x537730);
    run.put(0x537748, 0);
    uint32_t cell = 0;
    bool outside = s32(key) < s32(low);
    if (!outside)
        outside = s32(key) > s32(run.get(0x537734));
    if (outside) {
        uint32_t grown = run.call(0x4db6e0, 0x537728, {key, 0});
        if (grown == 0) {
            uint32_t context = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53772c);
            run.put(0x544b14, site);
            run.call(0x4db4d0, owner, {0x537728, context, 0xc});
            cell = run.get(0x53773c);
            low = run.get(0x537730);
        } else {
            low = run.get(0x537730);
            uint32_t offset = (key - low) * run.get(0x537740);
            cell = offset + run.get(0x537738);
        }
    } else {
        uint32_t offset = (key - low) * run.get(0x537740);
        cell = offset + run.get(0x537738);
    }
    if (run.get(cell) == 0) {
        run.call(0x40e280, receiver, {key});
        return 0;
    }
    run.put(0x537748, 0);
    bool outsideAgain = s32(key) < s32(low);
    if (!outsideAgain)
        outsideAgain = s32(key) > s32(run.get(0x537734));
    if (outsideAgain) {
        uint32_t grown = run.call(0x4db6e0, 0x537728, {key, 0});
        if (grown == 0) {
            uint32_t context = run.get(0x544b4c);
            uint32_t site = run.call(0x4db5f0, 0, {});
            uint32_t owner = run.get(0x53772c);
            run.put(0x544b14, site);
            run.call(0x4db4d0, owner, {0x537728, context, 0xc});
            uint32_t fallback = run.get(0x53773c);
            run.call(run.get(fallback), receiver, {});
            return 0;
        }
        low = run.get(0x537730);
    }
    uint32_t offset = (key - low) * run.get(0x537740);
    uint32_t target = offset + run.get(0x537738);
    run.call(run.get(target), receiver, {});
    return 0;
}

uint32_t function_444140(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x443ab0. Constructor of the Gabriel actor; returns the receiver.
uint32_t function_443ab0(Run &run, uint32_t receiver, const uint32_t *arguments, ClawX87State &fp) {
    uint32_t context = arguments[0];
    // Base construction produces C0 while retaining inherited exception flags.
    fp.popCount = 0;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(0x40e0d0, receiver, fp, {context});
    run.put(receiver + 0x4dc, 0);
    run.put(receiver + 0x4e0, 0);
    run.put(receiver + 0x4e4, 0);
    run.put(receiver + 0x4e8, 0);
    run.put(receiver + 0x4ec, 0);
    run.put(receiver + 0x4f0, 0);
    run.put(receiver + 0x4f4, 0);
    run.put(receiver + 0x4f8, 0);
    run.put(receiver + 0x4fc, 0);
    run.put(receiver + 0x500, 0);
    run.put(receiver + 0x504, 0);
    run.put(receiver + 0x508, 0);
    run.put(receiver, 0x50de1c);
    run.put(0x53774c, receiver);
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x527788});
    uint32_t animations = receiver + 0x128;
    // Animation handles: +0x338 hit high, +0x334 hit low, +0x460.. idle, kill and strike.
    run.put(receiver + 0x338, lookupAnimation(run, animations, 0x527770));
    run.put(receiver + 0x334, lookupAnimation(run, animations, 0x527758));
    run.put(receiver + 0x460, lookupAnimation(run, animations, 0x527744));
    run.put(receiver + 0x464, lookupAnimation(run, animations, 0x527730));
    run.put(receiver + 0x468, lookupAnimation(run, animations, 0x527718));
    run.put(receiver + 0x46c, lookupAnimation(run, animations, 0x527700));
    run.put(receiver + 0x470, lookupAnimation(run, animations, 0x5276e8));
    run.put(receiver + 0x474, lookupAnimation(run, animations, 0x5276d0));
    run.put(receiver + 0x478, lookupAnimation(run, animations, 0x5276b8));
    run.put(receiver + 0x47c, lookupAnimation(run, animations, 0x5276a0));
    run.put(receiver + 0x480, lookupAnimation(run, animations, 0x527688));
    run.put(receiver + 0x484, lookupAnimation(run, animations, 0x527670));
    run.put(receiver + 0x488, lookupAnimation(run, animations, 0x527658));
    run.put(receiver + 0x48c, lookupAnimation(run, animations, 0x527640));
    run.put(receiver + 0x490, lookupAnimation(run, animations, 0x527628));
    run.put(receiver + 0x494, lookupAnimation(run, animations, 0x527610));
    // Sound handles +0x498..+0x4a8, then resource handles +0x4ac..+0x4d8.
    run.put(receiver + 0x498, lookupSound(run, receiver, 0x5275f8));
    run.put(receiver + 0x49c, lookupSound(run, receiver, 0x5275e0));
    run.put(receiver + 0x4a0, lookupSound(run, receiver, 0x5275c8));
    run.put(receiver + 0x4a4, lookupSound(run, receiver, 0x5275b0));
    run.put(receiver + 0x4a8, lookupSound(run, receiver, 0x527598));
    run.put(receiver + 0x4ac, lookupResource(run, receiver, 0x527580));
    run.put(receiver + 0x4b0, lookupResource(run, receiver, 0x527580));
    run.put(receiver + 0x4b4, lookupResource(run, receiver, 0x527568));
    run.put(receiver + 0x4b8, lookupResource(run, receiver, 0x527550));
    run.put(receiver + 0x4bc, lookupResource(run, receiver, 0x527538));
    run.put(receiver + 0x4c0, lookupResource(run, receiver, 0x527520));
    run.put(receiver + 0x4c4, lookupResource(run, receiver, 0x527508));
    run.put(receiver + 0x4c8, lookupResource(run, receiver, 0x5274f0));
    run.put(receiver + 0x4cc, lookupResource(run, receiver, 0x5274f0));
    run.put(receiver + 0x4d0, lookupResource(run, receiver, 0x5274d8));
    run.put(receiver + 0x4d4, lookupResource(run, receiver, 0x5274c0));
    run.put(receiver + 0x4d8, lookupResource(run, receiver, 0x5274a8));
    // Sprite at +0x12c: +0xd0 mode, +0xd4 flags, +0x164 flag word.
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000062);
    uint32_t flags = run.get(run.get(receiver + 0x12c) + 0x164);
    flags = flags & 0xfffffffe;
    run.put(run.get(receiver + 0x12c) + 0x164, flags);
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x220});
    run.call(0x4061e0, run.get(receiver + 0x12c), {receiver + 0x210});
    run.call(0x406290, run.get(receiver + 0x12c), {});
    run.call(0x406240, run.get(receiver + 0x12c), {});
    run.put(receiver + 0x28c, 0xbb8);
    run.put(receiver + 0x290, 0x7d0);
    run.put(receiver + 0x294, 0xbb8);
    run.put(receiver + 0x298, 0x7d0);
    run.put(receiver + 0x29c, 0xbb8);
    run.put(receiver + 0x2a0, 0x7d0);
    run.put(receiver + 0x2a4, 0xbb8);
    run.put(receiver + 0x2a8, 0x7d0);
    run.put(receiver + 0x2ac, 0xbb8);
    run.put(receiver + 0x2b0, 0x7d0);
    uint32_t sprite = run.get(receiver + 0x12c);
    uint32_t height = run.get(sprite + 0x50);
    run.put(sprite + 0x50, height + 0xffffffe0);
    uint32_t anchor = run.get(receiver + 0x128);
    uint32_t anchorScene = run.get(anchor + 0xc);
    uint32_t anchorTarget = run.get(anchorScene + 0x24);
    run.call(0x4cd800, anchorTarget, {anchor, 0});
    run.put(run.get(receiver + 0x128) + 0xcc, 1);
    // Actor at +0xc: +0x10c scaled by the float at 0x5262b4 through ftol.
    uint32_t actor = run.get(receiver + 0xc);
    run.put(actor + 0x10c, 0x64);
    uint32_t scaled = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(scaled + 0x10c)});
    float factor = run.getf(0x5262b4);
    double widened = factor;
    uint64_t factorBits;
    std::memcpy(&factorBits, &widened, 8);
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(factorBits), uint32_t(factorBits >> 32)});
    uint32_t converted = convertTop(run, fp);
    run.put(scaled + 0x10c, converted);
    run.put(receiver + 0x534, 0);
    run.put(receiver + 0x514, 0);
    run.put(receiver + 0x524, 0);
    uint32_t low = run.get(receiver + 0x68);
    uint32_t high = run.get(receiver + 0x6c);
    run.x87_step(CLAW_X87_F64, fp, {low, high});
    uint32_t offsetLow = run.get(0x50dde8);
    uint32_t offsetHigh = run.get(0x50ddec);
    run.x87_step(CLAW_X87_SUB_F64, fp, {offsetLow, offsetHigh});
    uint32_t position = convertTop(run, fp);
    run.put(receiver + 0x528, position);
    run.put(receiver + 0x52c, position + 0xffffff6a);
    run.put(receiver + 0x530, 0x1472);
    run.put(receiver + 0x514, 0);
    run.put(receiver + 0x524, 0);
    run.put(receiver + 0x518, 0);
    run.put(receiver + 0x51c, 0);
    run.put(receiver + 0x520, 0);
    run.put(receiver + 0x534, 1);
    function_444140(run, receiver, nullptr);
    return receiver;
}

// 0x444120. Destructor wrapper: runs 0x445950, frees on flag bit 0.
uint32_t function_444120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.call(0x445950, receiver, {});
    if ((arguments[0] & 1) != 0)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x444140. Startup state: record +0x1c is the state number.
uint32_t function_444140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t record = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(record + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x523268});
    run.put(run.get(receiver + 0x10) + 0x1c, next);
    uint32_t animation = pickIdleAnimation(run, receiver);
    uint32_t sprite = run.get(receiver + 0x12c);
    run.put(receiver + 0x134, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    return 0;
}

// 0x4441b0. Animation tick; mode 2 calls virtual +0xb0.
uint32_t function_4441b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t sprite = run.get(receiver + 0x12c);
    run.call(0x4c82a0, sprite + 0x188, {run.get(0x5430c4)});
    if (run.get(0x53c9c0) == 2)
        run.vcall(receiver, 0xb0);
    return 0;
}

// 0x4441f0. Idle state; +0x520 nonzero skips everything after the state change.
uint32_t function_4441f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t record = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(record + 0x1c));
    uint32_t next = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, next);
    if (run.get(receiver + 0x520) != 0)
        return 0;
    uint32_t embedded = receiver + 0x128;
    if (run.get(receiver + 0x18c) == 2) {
        uint32_t sprite = run.get(embedded + 4);
        if ((run.get8(sprite + 0x40) & 2) == 0) {
            uint32_t first = run.get(embedded + 0x10);
            uint32_t second = run.get(embedded + 0x18);
            second = 0u - second;
            first = 0u - first;
            run.put(embedded + 0x10, second);
            run.put(embedded + 0x18, first);
            uint32_t bits = run.get(sprite + 0x40);
            bits = bits | 2;
            run.put(sprite + 0x40, bits);
            run.call(0x4060b0, run.get(embedded + 4), {});
        }
    } else {
        run.call(0x406310, embedded, {});
    }
    uint32_t animation = pickIdleAnimation(run, receiver);
    uint32_t sprite = run.get(embedded + 4);
    run.put(embedded + 0xc, run.get(sprite + 0x190));
    run.call(0x4c8220, sprite + 0x188, {animation});
    run.put(receiver + 0x4e0, 0x3e8);
    run.put(receiver + 0x4dc, run.get(0x537210));
    return 0;
}

uint32_t function_444330(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4442c0. Idle tick; fires the attack chooser when the timer elapses.
uint32_t function_4442c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    if (run.get(receiver + 0x520) != 0)
        return 0;
    uint32_t sprite = run.get(receiver + 0x12c);
    run.call(0x4c82a0, sprite + 0x188, {run.get(0x5430c4)});
    uint32_t animation = run.get(receiver + 0x12c) + 0x188;
    if (run.get(animation + 0x1c) == 0)
        return 0;
    if (run.get(animation + 0x14) != 0)
        return 0;
    uint32_t clock = run.get(0x537210);
    uint32_t started = run.get(receiver + 0x4dc);
    uint32_t period = run.get(receiver + 0x4e0);
    uint32_t elapsed = clock - started;
    if (elapsed < period)
        return 0;
    if (run.get(receiver + 0x534) != 0)
        return 0;
    function_444330(run, receiver, nullptr);
    return 0;
}

// Negate and swap a pair of signed words in place: first = -second, second = -first.
void flipPair(Run &run, uint32_t first, uint32_t second) {
    uint32_t a = run.get(first);
    uint32_t b = run.get(second);
    b = 0u - b;
    a = 0u - a;
    run.put(first, b);
    run.put(second, a);
}

// Flip the three sprite rectangles at +0x118, +0x128, +0x138 unless a first
// word holds the 0x80000000 sentinel. Returns after all three pairs.
void flipSpriteRects(Run &run, uint32_t sprite) {
    if (run.get(sprite + 0x118) != 0x80000000)
        flipPair(run, sprite + 0x118, sprite + 0x120);
    if (run.get(sprite + 0x128) != 0x80000000)
        flipPair(run, sprite + 0x128, sprite + 0x130);
    if (run.get(sprite + 0x138) != 0x80000000)
        flipPair(run, sprite + 0x138, sprite + 0x140);
}

// 0x444330. Pick one of three attacks by rand modulo 3, facing the player first.
uint32_t function_444330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t random = run.call(0x4a3050, 0, {});
    int32_t remainder = s32(random) % 3;
    uint32_t selector = uint32_t(remainder) + 1;
    uint32_t sprite = run.get(receiver + 0x12c);
    uint8_t facing = run.get8(sprite + 0x40);
    if (run.get(receiver + 0x18c) == 2) {
        if ((facing & 2) == 0) {
            flipPair(run, receiver + 0x138, receiver + 0x140);
            uint32_t bits = run.get(sprite + 0x40);
            bits = bits | 2;
            run.put(sprite + 0x40, bits);
            flipSpriteRects(run, run.get(receiver + 0x12c));
        }
    } else {
        if ((facing & 2) != 0) {
            flipPair(run, receiver + 0x138, receiver + 0x140);
            uint32_t bits = run.get(sprite + 0x40);
            bits = bits & 0xfffffffd;
            run.put(sprite + 0x40, bits);
            flipSpriteRects(run, run.get(receiver + 0x12c));
        }
    }
    selector = selector - 1;
    if (selector == 0) {
        run.call(0x4444d0, receiver, {});
        return 0;
    }
    selector = selector - 1;
    if (selector == 0) {
        run.call(0x4446f0, receiver, {});
        return 0;
    }
    selector = selector - 1;
    if (selector == 0) {
        run.call(0x444850, receiver, {});
        return 0;
    }
    run.vcall(receiver, 0x48);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x405f60:
        return function_405f60(run, receiver, arguments);
    case 0x443290: {
        auto fp = run.x87_entry(function);
        uint32_t result = function_443290(run, receiver, arguments, fp);
        run.x87_finish(function, fp);
        return result;
    }
    case 0x4433b0:
        return function_4433b0(run, receiver, arguments);
    case 0x443ab0: {
        auto fp = run.x87_entry(function);
        uint32_t result = function_443ab0(run, receiver, arguments, fp);
        run.x87_finish(function, fp);
        return result;
    }
    case 0x444120:
        return function_444120(run, receiver, arguments);
    case 0x444140:
        return function_444140(run, receiver, arguments);
    case 0x4441b0:
        return function_4441b0(run, receiver, arguments);
    case 0x4441f0:
        return function_4441f0(run, receiver, arguments);
    case 0x4442c0:
        return function_4442c0(run, receiver, arguments);
    case 0x444330:
        return function_444330(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_eight_gabriel_core_01_entry, owned, body)
