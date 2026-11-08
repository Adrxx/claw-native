// Level 1 enemy shared helpers 0x43f120, 0x43fe60, 0x43ffa0, 0x404eb0, 0x404ed0, 0x404f00, 0x420370
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"
#include "V13EnemyDeathSound.h"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x43f120:
        return 1;
    case 0x43fe60:
        return 0;
    case 0x43ffa0:
        return 0;
    case 0x404eb0:
        return 1;
    case 0x404ed0:
        return 0;
    case 0x404f00:
        return 0;
    case 0x420370:
        return 1;
    default:
        return -1;
    }
}

// 0x420370. cdecl, 1 stack argument. Only when the global at 0x537e88 is set
// and the argument is 2 or 0x20: picks one of ten string tables by rand() % 10
// and calls 0x48c8a0 with it and 0.
uint32_t function_420370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t kind = arguments[0];
    if (run.get(0x537e88) == 0)
        return 0;
    if (kind != 2) {
        if (kind - 0x20 != 0)
            return 0;
    }
    uint32_t value = run.call(0x4a3050, 0, {});
    int32_t remainder = s32(value) % 10;
    if (remainder < 0)
        return 0;
    static const uint32_t names[10] = {0x524e04, 0x524df8, 0x524dec, 0x524de0, 0x524dd4,
                                       0x524dc8, 0x524db8, 0x524da8, 0x524d98, 0x524d88};
    run.call(0x48c8a0, 0, {names[remainder], 0});
    return 0;
}

// 0x43f120. thiscall, 1 stack argument. Enemy state change: stores the new
// state at +0x304, then runs the per-state setup.
// Fields: +0x0c owner, +0x10 record, +0x12c sprite, +0x2f4 string header,
// +0x2fc length, +0x300 inline or pointer data, +0x304 state.
uint32_t function_43f120(Run &run, uint32_t receiver, const uint32_t *arguments, bool v13 = false) {
    uint32_t self = receiver;
    run.put(self + 0x304, arguments[0]);
    uint32_t record = run.get(self + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(self + 0x24, saved);
    uint32_t created = run.call(0x4dba00, 0x537668, {0x5234f4});
    record = run.get(self + 0x10);
    run.put(record + 0x1c, created);
    run.put(self + 0x20, 1);
    uint32_t sprite = run.get(self + 0x12c);
    uint32_t flags = run.get(sprite + 0x8);
    flags |= 0x80;
    run.put(sprite + 0x8, flags);
    run.call(0x43e9c0, self, {0});
    uint32_t state = run.get(self + 0x304);
    if (state <= 3) {
        switch (state) {
        case 0: {
            uint32_t length = run.get(self + 0x2fc);
            if (length != 0) {
                uint32_t target;
                if (length <= 0x20)
                    target = self + 0x300;
                else
                    target = run.get(self + 0x300);
                uint32_t word = run.get(target);
                run.put(target, v13 ? claw_v13_enemy_dead_bits(word) : word ^ 1);
            }
            uint32_t owner = run.get(self + 0xc);
            if (run.get(owner + 0x64) != 0x2134) {
                run.put(owner + 0x64, 0x2134);
                uint32_t ownerFlags = run.get(owner + 0x8);
                ownerFlags |= 0x20000;
                run.put(owner + 0x8, ownerFlags);
            }
            uint32_t roll = run.call(0x4a3050, 0, {});
            int32_t remainder = s32(roll) % 100;
            if (remainder < 0x19) {
                uint32_t owner2 = run.get(self + 0xc);
                uint32_t inner = run.get(owner2 + 0x74);
                uint32_t argument = run.get(inner + 0xd0);
                function_420370(run, 0, &argument);
            } else {
                uint32_t voice = run.get(self + 0x3a4);
                if (voice != 0) {
                    uint32_t cue = run.get(0x532c10);
                    run.call(0x4208e0, voice, {cue, 0, 0, 0});
                }
            }
            uint32_t low = run.get(0x513e10);
            uint32_t high = run.get(0x513e14);
            run.put(self + 0x80, low);
            run.put(self + 0x84, high);
            uint32_t low2 = run.get(0x513e18);
            uint32_t high2 = run.get(0x513e1c);
            run.put(self + 0x98, low2);
            run.put(self + 0x9c, high2);
            low = run.get(0x513e10);
            high = run.get(0x513e14);
            run.put(self + 0x88, low);
            run.put(self + 0x8c, high);
            low2 = run.get(0x513e18);
            high2 = run.get(0x513e1c);
            run.put(self + 0xa0, low2);
            run.put(self + 0xa4, high2);
            low = run.get(0x513e10);
            high = run.get(0x513e14);
            run.put(self + 0x90, low);
            run.put(self + 0x94, high);
            low2 = run.get(0x513e18);
            high2 = run.get(0x513e1c);
            run.put(self + 0xa8, low2);
            run.put(self + 0xac, high2);
            owner = run.get(self + 0xc);
            run.put(owner + 0xcc, 7);
            sprite = run.get(self + 0x12c);
            uint32_t clip = run.get(self + 0x374);
            uint32_t frame = run.get(sprite + 0x190);
            run.put(self + 0x134, frame);
            run.call(0x420a10, sprite, {clip, 0});
            run.put(self + 0x40, 0);
            run.put(self + 0x44, 0x409f4000);
            uint32_t facing = run.get(self + 0x18c);
            run.put(self + 0x50, 0);
            if (facing == 3)
                run.put(self + 0x54, 0x4062c000);
            else
                run.put(self + 0x54, 0xc062c000);
            run.put(self + 0x58, 0);
            run.put(self + 0x60, 0);
            run.put(self + 0x5c, 0xc085e000);
            run.put(self + 0x64, 0);
            break;
        }
        case 1:
        case 2: {
            if (state == 1) {
                uint32_t sound = run.get(self + 0x3b0);
                if (sound != 0) {
                    uint32_t enabled = run.get(0x532c0c);
                    uint32_t cue = run.get(0x532c10);
                    if (enabled != 0) {
                        if (v13) {
                            run.call(0x4208e0, sound, {cue, 0, 0, 0});
                        } else {
                            uint32_t channel = run.get(sound + 0x10);
                            run.call(0x4b45f0, channel, {cue, 0, 0, 0});
                        }
                    }
                }
            } else {
                uint32_t voice = run.get(self + 0x3a8);
                if (voice != 0) {
                    uint32_t cue = run.get(0x532c10);
                    run.call(0x4208e0, voice, {cue, 0, 0, 0});
                }
            }
            run.put(self + 0xc8, 1);
            sprite = run.get(self + 0x12c);
            run.put(sprite + 0x48, 0x1e);
            run.put(sprite + 0x44, 0);
            sprite = run.get(self + 0x12c);
            uint32_t spriteFlags = run.get(sprite + 0x40);
            spriteFlags |= 8;
            run.put(sprite + 0x40, spriteFlags);
            run.put(self + 0x3dc, 0x3e8);
            uint32_t clock = run.get(0x537210);
            run.put(self + 0x3d8, clock);
            break;
        }
        default: {
            uint32_t sound = run.get(self + 0x3ac);
            if (sound != 0) {
                uint32_t enabled = run.get(0x532c0c);
                uint32_t cue = run.get(0x532c10);
                if (enabled != 0) {
                    if (v13) {
                        run.call(0x4208e0, sound, {cue, 0, 0, 0});
                    } else {
                        uint32_t channel = run.get(sound + 0x10);
                        run.call(0x4b45f0, channel, {cue, 0, 0, 0});
                    }
                }
            }
            run.put(self + 0xc8, 1);
            sprite = run.get(self + 0x12c);
            uint32_t spriteFlags = run.get(sprite + 0x8);
            spriteFlags |= 0x10000;
            run.put(sprite + 0x8, spriteFlags);
            break;
        }
        }
    }
    uint32_t length = run.get(self + 0x2fc);
    uint32_t header = self + 0x2f4;
    if (length <= 4) {
        run.call(0x4dbd20, header, {4});
        return 0;
    }
    if (length > 0x20) {
        uint32_t target = run.get(header + 0xc);
        uint32_t word = run.get(target);
        word |= 0x10;
        run.put(target, word);
        return 0;
    }
    uint32_t word = run.get(header + 0xc);
    word |= 0x10;
    run.put(header + 0xc, word);
    return 0;
}

// 0x43fe60. thiscall, no stack arguments. Sets up a bounce state with a
// floating-point recompute of the +0x58 and +0x70 doubles.
uint32_t function_43fe60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t record = run.get(self + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(self + 0x24, saved);
    uint32_t created = run.call(0x4dba00, 0x537668, {0x5240e8});
    record = run.get(self + 0x10);
    run.put(record + 0x1c, created);
    uint32_t owner = run.get(self + 0xc);
    run.put(owner + 0xcc, 8);
    uint32_t sprite = run.get(self + 0x12c);
    uint32_t clip = run.get(self + 0x36c);
    uint32_t frame = run.get(sprite + 0x190);
    run.put(self + 0x134, frame);
    run.call(0x4c8220, sprite + 0x188, {clip});
    double reduced = run.getd(self + 0x70) - run.getd(0x50dba8);
    double zero = run.getd(0x50dba0);
    double speed = run.getd(self + 0x40);
    double result;
    bool unordered = speed != speed || zero != zero;
    if (speed == zero || unordered) {
        result = run.getd(self + 0x58);
    } else {
        double delta = reduced - run.getd(self + 0x70);
        double scaled = delta * run.getd(self + 0x40);
        double horizontal = run.getd(self + 0x58);
        double square = horizontal * horizontal;
        double product = scaled * run.getd(0x50dbb0);
        double discriminant = square - product;
        double root = zero;
        bool useDiscriminant = !(zero > discriminant);
        if (useDiscriminant)
            root = discriminant;
        result = __builtin_sqrt(root);
        double sign = run.getd(self + 0x58);
        bool negate = !(sign > run.getd(0x50dba0));
        if (negate)
            result = -result;
    }
    run.putd(self + 0x58, result);
    run.putd(self + 0x70, reduced);
    run.put(self + 0xb8, 0);
    run.put(self + 0xbc, 0xbff00000);
    double x = run.getd(self + 0x50);
    double y = run.getd(self + 0x58);
    double scaledY = y * run.getd(0x50dbc0);
    double scaledX = x * run.getd(0x50dbb8);
    run.putd(self + 0x58, scaledY);
    run.put(self + 0x60, 0);
    run.put(self + 0x64, 0);
    run.putd(self + 0x50, scaledX);
    return 0;
}

// 0x43ffa0. thiscall, no stack arguments. Sets sprite flags, plays the cue
// if the sound object exists and sound is enabled, and clears state fields.
uint32_t function_43ffa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t self = receiver;
    uint32_t sprite = run.get(self + 0x12c);
    uint32_t flags = run.get(sprite + 0x8);
    flags |= 2;
    run.put(sprite + 0x8, flags);
    sprite = run.get(self + 0x12c);
    uint32_t mask = run.get(sprite + 0x164);
    mask |= 0x2000;
    run.put(sprite + 0x164, mask);
    uint32_t record = run.get(self + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(self + 0x24, saved);
    uint32_t created = run.call(0x4dba00, 0x537668, {0x524418});
    record = run.get(self + 0x10);
    run.put(record + 0x1c, created);
    sprite = run.get(self + 0x12c);
    flags = run.get(sprite + 0x8);
    flags |= 4;
    run.put(sprite + 0x8, flags);
    sprite = run.get(self + 0x12c);
    run.put(sprite + 0xd0, 0x1000000);
    sprite = run.get(self + 0x12c);
    uint32_t clip = run.get(self + 0x368);
    uint32_t frame = run.get(sprite + 0x190);
    run.put(self + 0x134, frame);
    run.call(0x4c8220, sprite + 0x188, {clip});
    uint32_t sound = run.get(self + 0x3b8);
    if (sound != 0) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t cue = run.get(0x532c10);
        if (enabled != 0) {
            uint32_t channel = run.get(sound + 0x10);
            run.call(0x4b45f0, channel, {cue, 0, 0, 0});
        }
    }
    run.put(self + 0xc8, 1);
    run.put(self + 0x1a0, 0);
    return 0;
}

// 0x404eb0. thiscall, 1 stack argument. Calls virtual slot 0x28 with the
// argument, then 0x440e20.
uint32_t function_404eb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t argument = arguments[0];
    uint32_t method = run.get(run.get(receiver) + 0x28);
    run.call(method, receiver, {argument});
    run.call(0x440e20, receiver, {argument});
    return 0;
}

// 0x404ed0. thiscall. Saves the record string pointer and replaces it with
// the result of 0x4dba00 for the string at 0x5234ec.
uint32_t function_404ed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t record = run.get(receiver + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t created = run.call(0x4dba00, 0x537668, {0x5234ec});
    record = run.get(receiver + 0x10);
    run.put(record + 0x1c, created);
    return 0;
}

// 0x404f00. Same as 0x404ed0 with the string at 0x523148.
uint32_t function_404f00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t record = run.get(receiver + 0x10);
    uint32_t saved = run.get(record + 0x1c);
    run.put(receiver + 0x24, saved);
    uint32_t created = run.call(0x4dba00, 0x537668, {0x523148});
    record = run.get(receiver + 0x10);
    run.put(record + 0x1c, created);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x43f120:
        return function_43f120(run, receiver, arguments);
    case 0x43fe60:
        return function_43fe60(run, receiver, arguments);
    case 0x43ffa0:
        return function_43ffa0(run, receiver, arguments);
    case 0x404eb0:
        return function_404eb0(run, receiver, arguments);
    case 0x404ed0:
        return function_404ed0(run, receiver, arguments);
    case 0x404f00:
        return function_404f00(run, receiver, arguments);
    case 0x420370:
        return function_420370(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

// The app retains its established layouts and elects the v1.3 death change.
int compatOwned(uint32_t function) {
    return function == 0x43f120 ? 1 : -1;
}
uint32_t compatBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    (void)function;
    return function_43f120(run, receiver, arguments, true);
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_callee_03_entry, owned, body)

CLAW_MODULE_ENTRY(claw_v13_enemy_death_compat_entry, compatOwned, compatBody)
