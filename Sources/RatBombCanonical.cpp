// RatBomb and its existing shared utility surface
//
// Canonical translation from the pinned original decompile and disassembly.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x47e1d0:
        return 0;
    case 0x406240:
        return 0;
    case 0x484d90:
        return 1;
    case 0x456030:
        return 0;
    case 0x473c50:
        return 1;
    case 0x47d890:
        return 1;
    case 0x4741f0:
        return 0;
    case 0x47e050:
        return 0;
    case 0x47df20:
        return 0;
    case 0x47e180:
        return 0;
    case 0x47dfc0:
        return 0;
    case 0x4742f0:
        return 0;
    case 0x47db20:
        return 1;
    case 0x473f40:
        return 1;
    case 0x47d7d0:
        return 1;
    case 0x406150:
        return 0;
    case 0x406180:
        return 0;
    default:
        return -1;
    }
}

// 0x47e1d0. Actor +0x170 manager, +0x16c index, +0x174 frame.
uint32_t function_47e1d0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t manager = run.get(receiver + 0x170);
    if (manager) {
        uint32_t index = run.get(manager + 0x64);
        run.put(receiver + 0x16c, index);
        uint32_t minimum = run.get(manager + 0x64);
        uint32_t frame = 0;
        if (s32(index) >= s32(minimum) && s32(index) <= s32(run.get(manager + 0x68))) {
            frame = run.get(run.get(manager + 0x14) + index * 4u);
        }
        run.put(receiver + 0x174, frame);
    }
    return 0;
}

// 0x406240. Frame RECT at +0x18; actor derived RECT at +0x128.
uint32_t function_406240(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t frame = run.get(receiver + 0x174);
    if (frame) {
        uint32_t right = run.get(frame + 0x20);
        uint32_t left = run.get(frame + 0x18);
        run.put(receiver + 0x128, right - left);
        uint32_t bottom = run.get(frame + 0x24);
        uint32_t top = run.get(frame + 0x1c);
        run.put(receiver + 0x12c, bottom - top);
        left = run.get(frame + 0x18);
        right = run.get(frame + 0x20);
        run.put(receiver + 0x130, left + right - 1u);
        bottom = run.get(frame + 0x24);
        top = run.get(frame + 0x1c);
        run.put(receiver + 0x134, bottom + top - 1u);
    }
    return 0;
}

// 0x456030.
uint32_t function_456030(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x50b014);
    return 0;
}

// 0x484d90.
uint32_t function_484d90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_456030(run, receiver, nullptr);
    if (arguments[0] & 1u) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x406150. Horizontal frame endpoints +0x128/+0x130.
uint32_t function_406150(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t left = run.get(receiver + 0x128);
    if (left != 0x80000000u) {
        uint32_t right = run.get(receiver + 0x130);
        run.put(receiver + 0x128, 0u - right);
        run.put(receiver + 0x130, 0u - left);
    }
    return 0;
}

// 0x406180. Horizontal collision endpoints +0x138/+0x140.
uint32_t function_406180(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t left = run.get(receiver + 0x138);
    if (left != 0x80000000u) {
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
    }
    return 0;
}

// 0x4741f0. Two independent actor/frame loads, then current virtual callback.
uint32_t function_4741f0(Run &run, uint32_t receiver, const uint32_t *) {
    for (uint32_t pass = 0; pass < 2; ++pass) {
        uint32_t actor = run.get(receiver + 0x12c);
        uint32_t frame = run.get(actor + 0x174);
        uint32_t base = pass ? 0x138 : 0x118;
        if (frame) {
            uint32_t right = run.get(frame + 0x20);
            uint32_t left = run.get(frame + 0x18);
            run.put(actor + base, right - left);
            uint32_t bottom = run.get(frame + 0x24);
            uint32_t top = run.get(frame + 0x1c);
            run.put(actor + base + 0x04, bottom - top);
            right = run.get(frame + 0x20);
            left = run.get(frame + 0x18);
            run.put(actor + base + 0x08, right + left - 1u);
            uint32_t first = run.get(frame + (pass ? 0x24 : 0x1c));
            uint32_t second = run.get(frame + (pass ? 0x1c : 0x24));
            run.put(actor + base + 0x0c, first + second - 1u);
        }
    }
    run.vcall(receiver, 0x28);
    return 0;
}

// 0x4742f0. +0x148 animation enabled, +0x120 pending flags.
uint32_t function_4742f0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x148)) {
        uint32_t delta = run.get(0x5430c4);
        uint32_t actor = run.get(receiver + 0x12c);
        run.call(0x4c82a0, actor + 0x188, {delta});
    }
    if (run.get(receiver + 0x120) & 0x10000u) {
        uint32_t actor = run.get(receiver + 0x12c);
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000u);
    }
    return 0;
}

// 0x47df20. +0x10 config, +0x24 saved state, +0x134 saved animation.
uint32_t function_47df20(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x524418});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x1000000);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x158);
    uint32_t previous = run.get(actor + 0x190);
    run.put(receiver + 0x134, previous);
    run.call(0x4c8220, actor + 0x188, {animation});
    run.put(receiver + 0xc8, 1);
    uint32_t sound = run.get(receiver + 0x164);
    if (sound) {
        uint32_t enabled = run.get(0x532c0c);
        uint32_t volume = run.get(0x532c10);
        if (enabled) {
            // PUSH ESI, four arguments and CALL at 0x47dfa3.
            uint32_t stackPointer = run.stackPointer;
            run.stackPointer = run.frame - 0x18;
            run.call(0x4b45f0, run.get(sound + 0x10), {volume, 0, 0, 0});
            run.stackPointer = stackPointer;
        }
    }
    run.put(receiver + 0x168, 0);
    return 0;
}

// 0x47dfc0. +0x168 explosion applied once; actor flags +0x08.
uint32_t function_47dfc0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t actor = run.get(receiver + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 0x80u);
    uint32_t delta = run.get(0x5430c4);
    actor = run.get(receiver + 0x12c);
    uint32_t done = run.call(0x4c82a0, actor + 0x188, {delta});
    if (done == 1 && run.get(receiver + 0x168) == 0) {
        uint32_t rectangle = run.get(receiver + 0x0c) + 0x138;
        run.put(receiver + 0x168, 1);
        run.icall(0x546d24, {rectangle, 0x28, 0x28});
        actor = run.get(receiver + 0x12c);
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xffffff7fu);
    }
    actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x1a4) && run.get(actor + 0x19c) == 0) {
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x10000u);
    }
    return 0;
}

// 0x47e180. Both current virtual +0x2c callbacks may run.
uint32_t function_47e180(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t delta = run.get(0x5430c4);
    uint32_t actor = run.get(receiver + 0x12c);
    run.call(0x4c82a0, actor + 0x188, {delta});
    if (run.get(run.get(receiver + 0x0c) + 0xcc) == 1) {
        run.vcall(receiver, 0x2c);
    }
    if (run.get(receiver + 0x120) & 0x10000u) {
        run.vcall(receiver, 0x2c);
    }
    return 0;
}

// 0x47e050. C3 alone selects equality, including unordered x87 comparisons.
uint32_t function_47e050(Run &run, uint32_t receiver, const uint32_t *) {
    double direction = run.getd(receiver + 0x50);
    double zero = run.getd(0x50f170);
    bool equalOrUnordered = !(direction < zero) && !(direction > zero);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + (equalOrUnordered ? 0x150 : 0x154));
    uint32_t previous = run.get(actor + 0x190);
    run.put(receiver + 0x134, previous);
    run.call(0x4c8220, actor + 0x188, {animation});
    if (!equalOrUnordered && run.getd(receiver + 0x50) > run.getd(0x50f170)) {
        actor = run.get(receiver + 0x12c);
        if (!(run.get8(actor + 0x40) & 2u)) {
            uint32_t left = run.get(receiver + 0x138);
            uint32_t right = run.get(receiver + 0x140);
            run.put(receiver + 0x138, 0u - right);
            run.put(receiver + 0x140, 0u - left);
            run.put(actor + 0x40, run.get(actor + 0x40) | 2u);
            actor = run.get(receiver + 0x12c);
            left = run.get(actor + 0x118);
            if (left != 0x80000000u) {
                right = run.get(actor + 0x120);
                run.put(actor + 0x118, 0u - right);
                run.put(actor + 0x120, 0u - left);
            }
            function_406150(run, actor, nullptr);
            function_406180(run, actor, nullptr);
        }
    }
    uint32_t delta = run.get(0x5430c4);
    actor = run.get(receiver + 0x12c);
    run.call(0x4c82a0, actor + 0x188, {delta});
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5236fc});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    run.put(run.get(receiver + 0x0c) + 0xcc, 8);
    return 0;
}

// 0x47db20 / 0x473f40 lookup sequence. Descriptor +0x08 minimum,
// +0x0c maximum, +0x10 table, +0x14 fallback, +0x18 stride, +0x20 scratch.
uint32_t lookupState(Run &run, uint32_t descriptor, uint32_t state, uint32_t &minimum) {
    if (s32(state) < s32(minimum) || s32(state) > s32(run.get(descriptor + 0x0c))) {
        uint32_t found = run.call(0x4db6e0, descriptor, {state, 0});
        if (!found) {
            uint32_t text = run.get(0x544b4c);
            uint32_t error = run.call(0x4db5f0, 0);
            uint32_t type = run.get(descriptor + 0x04);
            run.put(0x544b14, error);
            run.call(0x4db4d0, type, {descriptor, text, 0x0c});
            uint32_t entry = run.get(descriptor + 0x14);
            minimum = run.get(descriptor + 0x08);
            return entry;
        }
        minimum = run.get(descriptor + 0x08);
    }
    uint32_t table = run.get(descriptor + 0x10);
    uint32_t stride = run.get(descriptor + 0x18);
    return table + (state - minimum) * stride;
}

// 0x473f40.
uint32_t function_473f40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    uint32_t minimum = run.get(0x538430);
    run.put(0x538448, 0);
    uint32_t entry = lookupState(run, 0x538428, state, minimum);
    if (run.get(entry) == 0) {
        run.call(0x4a36f0, 0, {receiver});
    } else {
        run.put(0x538448, 0);
        entry = lookupState(run, 0x538428, state, minimum);
        run.call(run.get(entry), receiver);
    }
    return 0;
}

// 0x47db20.
uint32_t function_47db20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t state = arguments[0];
    uint32_t minimum = run.get(0x53c120);
    run.put(0x53c138, 0);
    uint32_t entry = lookupState(run, 0x53c118, state, minimum);
    if (run.get(entry) == 0) {
        function_473f40(run, receiver, arguments);
    } else {
        run.put(0x53c138, 0);
        entry = lookupState(run, 0x53c118, state, minimum);
        run.call(run.get(entry), receiver);
    }
    return 0;
}

uint32_t lowDouble(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return uint32_t(bits);
}

uint32_t highDouble(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return uint32_t(bits >> 32);
}

// Copy both source words before either store, as in the original MOV pair.
void copyDouble(Run &run, uint32_t destination, uint32_t source) {
    uint32_t low = run.get(source);
    uint32_t high = run.get(source + 0x04);
    run.put(destination, low);
    run.put(destination + 0x04, high);
}

// 0x473c50. Normal-return constructor; +0x28 embedded physics.
uint32_t function_473c50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    run.call(0x4082f0, receiver, {actor});
    run.call(0x4080a0, receiver + 0x28);
    uint32_t config = run.get(receiver + 0x10);
    run.put(receiver + 0x00, 0x50b2a4);
    uint32_t value = run.get(config + 0x2c);
    run.put(run.automatic(4), value);
    if (value) {
        run.putd(receiver + 0x80, double(s32(value)));
    } else {
        copyDouble(run, receiver + 0x80, 0x513e10);
    }
    value = run.get(run.get(receiver + 0x10) + 0x34);
    run.put(run.automatic(4), value);
    if (value) {
        run.putd(receiver + 0x88, double(s32(value)));
    } else {
        copyDouble(run, receiver + 0x88, 0x513e10);
    }
    value = run.get(run.get(receiver + 0x10) + 0x30);
    run.put(run.automatic(4), value);
    if (value) {
        run.putd(receiver + 0x98, double(s32(value)));
    } else {
        copyDouble(run, receiver + 0x98, 0x513e18);
    }
    value = run.get(run.get(receiver + 0x10) + 0x38);
    run.put(run.automatic(4), value);
    if (value) {
        run.putd(receiver + 0xa0, double(s32(value)));
    } else {
        copyDouble(run, receiver + 0xa0, 0x513e18);
    }
    double scale = double(run.get(0x537210));
    uint32_t physicalActor = run.get(receiver + 0x0c);
    double rate = scale * run.getd(0x50eec0);
    double h = double(run.gets(physicalActor + 0x14c));
    double w = double(run.gets(physicalActor + 0x148));
    double y = double(run.gets(physicalActor + 0x50));
    double x = double(run.gets(physicalActor + 0x4c));
    run.call(0x408220, receiver + 0x28, {lowDouble(x), highDouble(x), lowDouble(y), highDouble(y), 0, 0, lowDouble(w), highDouble(w), lowDouble(h), highDouble(h), 0, 0, 0, 0, 0, 0, 0, 0, lowDouble(rate), highDouble(rate), 0, 0});
    double limit = double(run.get(0x513e40));
    run.putd(receiver + 0xe8, limit);
    run.putd(receiver + 0xf0, limit);
    run.putd(receiver + 0xf8, limit);
    physicalActor = run.get(receiver + 0x0c);
    run.put(receiver + 0x120, 0);
    run.put(receiver + 0x124, 0);
    run.put(physicalActor + 0xcc, 7);
    run.call(0x4dca10, receiver);
    run.put(receiver + 0x128, actor);
    run.put(receiver + 0x12c, actor);
    uint32_t actorConfig = run.get(actor + 0x6c);
    run.put(receiver + 0x130, actorConfig);
    run.put(receiver + 0x00, 0x50ee8c);
    physicalActor = run.get(receiver + 0x12c);
    run.put(physicalActor + 0x08, run.get(physicalActor + 0x08) | 0x40u);
    physicalActor = run.get(receiver + 0x12c);
    run.put(physicalActor + 0x08, run.get(physicalActor + 0x08) | 0x20u);
    physicalActor = run.get(receiver + 0x12c);
    run.put(physicalActor + 0x164, run.get(physicalActor + 0x164) | 0x2000u);
    run.put(receiver + 0x148, 0);
    copyDouble(run, receiver + 0x80, 0x513e10);
    copyDouble(run, receiver + 0x98, 0x513e18);
    copyDouble(run, receiver + 0x88, 0x513e10);
    copyDouble(run, receiver + 0xa0, 0x513e18);
    copyDouble(run, receiver + 0x90, 0x513e10);
    copyDouble(run, receiver + 0xa8, 0x513e18);
    return receiver;
}

// 0x47d890. Resource lookup output aliases the incoming actor stack slot.
uint32_t function_47d890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t frame = run.frame;
    run.frame -= 0x24;
    function_473c50(run, receiver, arguments);
    run.frame = frame;
    run.put(receiver + 0x00, 0x50f13c);
    uint32_t actor = run.get(receiver + 0x12c);
    if (run.get(actor + 0x170) == 0) {
        run.call(0x4c7970, actor, {0x52b150});
    }
    uint32_t output = run.automatic(4);
    const uint32_t names[] = {0x52b13c, 0x52b120, 0x52b108, 0x52b0f0, 0x527bc4, 0x52b0e0};
    for (uint32_t i = 0; i < 6; ++i) {
        actor = run.get(receiver + 0x12c);
        uint32_t owner = run.get(actor + 0x0c);
        run.put(output, 0);
        uint32_t table = run.get(owner + (i < 4 ? 0x2c : 0x28)) + 0x10;
        run.call(0x4f6286, table, {names[i], output});
        uint32_t resource = run.get(output);
        if (i == 5) {
            run.put(receiver + 0x168, 0);
        }
        run.put(receiver + 0x150 + i * 4u, resource);
    }
    function_47e1d0(run, run.get(receiver + 0x12c), nullptr);
    function_406240(run, run.get(receiver + 0x12c), nullptr);
    run.put(run.get(receiver + 0x12c) + 0xd0, 0x40);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x118, 0xfffffff6u);
    run.put(actor + 0x11c, 0xffffff38u);
    run.put(actor + 0x120, 0x0a);
    run.put(actor + 0x124, 0x14);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 4u);
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x08, run.get(actor + 0x08) | 0x80u);
    run.put(run.get(receiver + 0x0c) + 0x104, 0x0f);
    uint32_t config = run.get(receiver + 0x0c);
    double ticks = double(run.gets(config + 0x104)) * double(run.getf(0x5262b0));
    uint32_t duration = run.call_x87(0x4a30e0, 0, ticks);
    run.put(config + 0x104, duration);
    config = run.get(receiver + 0x0c);
    if (run.get(config + 0x64) == 0) {
        if (run.get(config + 0x64) != 0x137e) {
            run.put(config + 0x64, 0x137e);
            run.put(config + 0x08, run.get(config + 0x08) | 0x20000u);
        }
    }
    return receiver;
}

// 0x47d7d0. Normal-return factory/dispatch; null allocation still dereferences null.
uint32_t function_47d7d0(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t config = run.get(actor + 0x6c);
    uint32_t state = run.get(config + 0x1c);
    if (state == 0) {
        run.put(config + 0x1c, 0x3e8);
        uint32_t logic = run.call(0x4f63ec, 0, {0x170});
        if (logic) {
            uint32_t frame = run.frame;
            run.frame -= 0x1c;
            logic = function_47d890(run, logic, arguments);
            run.frame = frame;
        }
        run.vcall(logic, 0x10);
        run.put(config + 0x18, logic);
    } else if (state == 0x1d) {
        run.vcall(run.get(config + 0x18), 0x20);
    } else if (state == 0x1e) {
        run.vcall(run.get(config + 0x18), 0x1c);
    } else if (state != 0x3e8) {
        run.call(0x4dc870, 0, {run.get(config + 0x18)});
    }
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47e1d0:
        return function_47e1d0(run, receiver, arguments);
    case 0x406240:
        return function_406240(run, receiver, arguments);
    case 0x484d90:
        return function_484d90(run, receiver, arguments);
    case 0x456030:
        return function_456030(run, receiver, arguments);
    case 0x473c50:
        return function_473c50(run, receiver, arguments);
    case 0x47d890:
        return function_47d890(run, receiver, arguments);
    case 0x4741f0:
        return function_4741f0(run, receiver, arguments);
    case 0x47e050:
        return function_47e050(run, receiver, arguments);
    case 0x47df20:
        return function_47df20(run, receiver, arguments);
    case 0x47e180:
        return function_47e180(run, receiver, arguments);
    case 0x47dfc0:
        return function_47dfc0(run, receiver, arguments);
    case 0x4742f0:
        return function_4742f0(run, receiver, arguments);
    case 0x47db20:
        return function_47db20(run, receiver, arguments);
    case 0x473f40:
        return function_473f40(run, receiver, arguments);
    case 0x47d7d0:
        return function_47d7d0(run, receiver, arguments);
    case 0x406150:
        return function_406150(run, receiver, arguments);
    case 0x406180:
        return function_406180(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_rat_bomb_canonical_entry, owned, body)
