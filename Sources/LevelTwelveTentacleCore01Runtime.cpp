// Level 12 tentacle core
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
    case 0x4923e0:
        return 1;
    case 0x4928f0:
        return 1;
    case 0x492c40:
        return 1;
    case 0x492c60:
        return 0;
    case 0x492ce0:
        return 0;
    case 0x492d30:
        return 1;
    case 0x492da0:
        return 0;
    case 0x492f70:
        return 0;
    case 0x492fb0:
        return 0;
    case 0x493110:
        return 0;
    case 0x493450:
        return 0;
    case 0x4936d0:
        return 0;
    default:
        return -1;
    }
}

// Owned cross-calls stay in this translation unit.
uint32_t function_492ce0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_492c60(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_493450(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x4923e0. Dispatch table bounds and stride are global signed-index data.
uint32_t function_4923e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t index = arguments[0];
    uint32_t lower = run.get(0x53ca10);
    run.put(0x53ca28, 0);
    uint32_t entry;
    if ((s32(index) < s32(lower) || s32(index) > run.gets(0x53ca14)) && !run.call(0x4db6e0, 0x53ca08, {index, 0})) {
        uint32_t name = run.get(0x544b4c);
        uint32_t error = run.call(0x4db5f0, 0);
        run.put(0x544b14, error);
        run.call(0x4db4d0, run.get(0x53ca0c), {0x53ca08, name, 0xc});
        entry = run.get(0x53ca1c);
        lower = run.get(0x53ca10);
    } else {
        lower = run.get(0x53ca10);
        entry = (index - lower) * run.get(0x53ca20) + run.get(0x53ca18);
    }
    if (!run.get(entry)) {
        run.call(0x43d490, receiver, {index});
        return 0;
    }
    run.put(0x53ca28, 0);
    if ((s32(index) < s32(lower) || s32(index) > run.gets(0x53ca14)) && !run.call(0x4db6e0, 0x53ca08, {index, 0})) {
        uint32_t name = run.get(0x544b4c);
        uint32_t error = run.call(0x4db5f0, 0);
        run.put(0x544b14, error);
        run.call(0x4db4d0, run.get(0x53ca0c), {0x53ca08, name, 0xc});
        entry = run.get(0x53ca1c);
    } else {
        entry = (index - run.get(0x53ca10)) * run.get(0x53ca20) + run.get(0x53ca18);
    }
    run.call(run.get(entry), receiver);
    return 0;
}

// 0x4928f0. Constructs the enemy base, animation slots and Tentacle state.
uint32_t function_4928f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    fp.popCount = 0;
    fp.pushCount = 0;
    run.call_x87_exact(0x4332f0, receiver, fp, {arguments[0]});
    // +0x414..+0x440 hold the state clocks and durations.
    run.put(receiver + 0x414, 0);
    run.put(receiver + 0x418, 0);
    run.put(receiver + 0x41c, 0);
    run.put(receiver + 0x420, 0);
    run.put(receiver + 0x424, 0);
    run.put(receiver + 0x428, 0);
    run.put(receiver + 0x42c, 0);
    run.put(receiver + 0x430, 0);
    run.put(receiver + 0x434, 0);
    run.put(receiver + 0x438, 0);
    run.put(receiver + 0x43c, 0);
    run.put(receiver + 0x440, 0);
    run.put(receiver, 0x50f8e4);
    // +0x12c is the animation actor, +0x128 its resource facade.
    run.call(0x4c7970, run.get(receiver + 0x12c), {0x52ca60});
    uint32_t facade = receiver + 0x128;
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t value = run.call(0x4061b0, run.get(run.get(actor + 0xc) + 0x2c), {0x52ca44});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x400, value);
    actor = run.get(facade + 0x4);
    value = run.call(0x4061b0, run.get(run.get(actor + 0xc) + 0x2c), {0x52ca24});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x410, value);
    value = run.call(0x4062e0, facade, {0x52ca04});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x408, value);
    value = run.call(0x4062e0, facade, {0x52c9e4});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x404, value);
    value = run.call(0x4062e0, facade, {0x52c9c4});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x374, value);
    value = run.call(0x4062e0, facade, {0x52c9a8});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x364, value);
    value = run.call(0x4062e0, facade, {0x52c988});
    if (!value) {
        value = run.call(0x4062e0, facade, {0x5234b4});
    }
    run.put(receiver + 0x40c, value);
    uint32_t resultSlot = run.automatic(0x4);
    run.put(resultSlot, 0);
    actor = run.get(receiver + 0x12c);
    run.call(0x4f6286, run.get(run.get(actor + 0xc) + 0x28) + 0x10, {0x52c968, resultSlot});
    run.put(receiver + 0x3a4, run.get(resultSlot));
    actor = run.get(receiver + 0x12c);
    run.put(resultSlot, 0);
    run.call(0x4f6286, run.get(run.get(actor + 0xc) + 0x28) + 0x10, {0x52c948, resultSlot});
    run.put(receiver + 0x448, run.get(resultSlot));
    actor = run.get(receiver + 0x12c);
    run.put(resultSlot, 0);
    run.call(0x4f6286, run.get(run.get(actor + 0xc) + 0x28) + 0x10, {0x52c928, resultSlot});
    run.put(receiver + 0x444, run.get(resultSlot));
    // +0x2f4 is the compact/indirect bitset, +8 is its bit capacity.
    uint32_t bits = receiver + 0x2f4;
    uint32_t count = run.get(bits + 0x8);
    if (!count) {
        run.call(0x4dbd20, bits, {0});
    } else {
        uint32_t words = count > 0x20 ? run.get(bits + 0xc) : bits + 0xc;
        run.put(words, run.get(words) | 1);
    }
    run.put(run.get(receiver + 0x12c) + 0xd0, 4);
    run.put(run.get(receiver + 0x12c) + 0xd4, 0x3000022);
    run.icall(0x546d5c, {receiver + 0x220, 0xffffff78, 0xffffffd4, 0, 0x27});
    run.icall(0x546d5c, {receiver + 0x210, 0x80000000, 0, 0, 0});
    run.call(0x406290, run.get(receiver + 0x12c));
    run.call(0x406240, run.get(receiver + 0x12c));
    run.put(receiver + 0x2a4, 0xc8);
    run.put(receiver + 0x2ac, 0x32);
    run.put(receiver + 0x2b0, 0x32);
    run.put(receiver + 0x2a8, 0x12c);
    uint32_t object = run.get(receiver + 0xc);
    if (!run.get(object + 0x104)) {
        run.put(object + 0x104, 0xa);
    }
    run.put(run.get(receiver + 0xc) + 0x10c, 0xa);
    object = run.get(receiver + 0xc);
    run.x87_step(CLAW_X87_I32, fp, {run.get(object + 0x10c)});
    double factor = static_cast<double>(run.getf(0x5262b4));
    uint64_t factorBits;
    std::memcpy(&factorBits, &factor, sizeof(factorBits));
    run.x87_step(CLAW_X87_MUL_F64, fp, {uint32_t(factorBits), uint32_t(factorBits >> 32)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    value = run.call_x87_exact(0x4a30e0, 0, fp);
    run.put(object + 0x10c, value);
    run.put(receiver + 0x45c, 0);
    uint32_t ordinal = run.get(0x53ca30);
    if (ordinal < run.get(0x5231dc)) {
        run.put(receiver + 0x45c, run.get(0x5231d0 + ordinal * 4));
        run.put(0x53ca30, run.get(0x53ca30) + 1);
    }
    run.put(receiver + 0xc8, 1);
    function_492ce0(run, receiver, nullptr);
    return receiver;
}

// 0x492c40. Scalar deleting destructor.
uint32_t function_492c40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_492c60(run, receiver, nullptr);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x492c60. Member destruction and global instance-count decrement.
uint32_t function_492c60(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50f8e4);
    run.put(0x53ca30, run.get(0x53ca30) - 1);
    run.put(receiver, 0x50b16c);
    run.call(0x4dbcd0, receiver + 0x2f4);
    run.call(0x4f6584, receiver + 0x1a8);
    run.call(0x4f6584, receiver + 0x1a4);
    run.put(receiver, 0x50b014);
    return 0;
}

// 0x492ce0. Reset activation clocks and withdraw this tentacle's boss bit.
uint32_t function_492ce0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(0x53ca2c, 0);
    run.put(receiver + 0x44c, 0);
    run.put(receiver + 0x450, 0);
    run.put(receiver + 0x454, 0);
    run.call(0x493be0, receiver);
    run.vcall(receiver, 0x48);
    uint32_t boss = run.get(0x534874);
    if (boss) {
        run.put(boss + 0x4ec, run.get(boss + 0x4ec) & ~run.get(receiver + 0x45c));
    }
    return 0;
}

// 0x492d30. Select the reset or ordinary idle timer.
uint32_t function_492d30(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t boss = run.get(0x534874);
    if (boss && (run.get(boss + 0x4ec) & run.get(receiver + 0x45c))) {
        function_492ce0(run, receiver, nullptr);
        return 0;
    }
    uint32_t delay = 0x1fffffff;
    if (!run.get(0x541334)) {
        delay = uint32_t(s32(run.call(0x4a3050, 0)) % 0x3e9);
    }
    run.put(receiver + 0x3c4, delay);
    run.call(0x43e420, receiver);
    return 0;
}

// 0x492da0. Enter idle and unmirror the actor's collision rectangles.
uint32_t function_492da0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x523148});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x400);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    uint32_t random = run.call(0x4a3050, 0);
    run.put(receiver + 0x420, uint32_t(s32(random) % 0x12d) + 0x3e8);
    run.put(receiver + 0x41c, run.get(0x537210));
    actor = run.get(receiver + 0x12c);
    if ((run.get8(actor + 0x40) & 2) && (run.get8(actor + 0x40) & 2)) {
        uint32_t left = run.get(receiver + 0x138);
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        actor = run.get(receiver + 0x12c);
        left = run.get(actor + 0x118);
        if (left != 0x80000000) {
            right = run.get(actor + 0x120);
            run.put(actor + 0x118, 0u - right);
            run.put(actor + 0x120, 0u - left);
        }
        left = run.get(actor + 0x128);
        if (left != 0x80000000) {
            right = run.get(actor + 0x130);
            run.put(actor + 0x128, 0u - right);
            run.put(actor + 0x130, 0u - left);
        }
        left = run.get(actor + 0x138);
        if (left != 0x80000000) {
            right = run.get(actor + 0x140);
            run.put(actor + 0x138, 0u - right);
            run.put(actor + 0x140, 0u - left);
        }
    }
    return 0;
}

// 0x492f70. Choose strike or growth from a signed rand remainder.
uint32_t function_492f70(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(0x53ca2c)) {
        run.vcall(receiver, 0x48);
    }
    if (s32(run.call(0x4a3050, 0)) % 0x65 < 0x4b) {
        run.vcall(receiver, 0x58);
    } else {
        run.call(0x493830, receiver);
    }
    return 0;
}

// 0x492fb0. Enter the strike state and select its animation.
uint32_t function_492fb0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sound = run.get(receiver + 0x448);
    if (sound && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52720c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x404);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    return 0;
}

// 0x493110. Enter frenzy, normalize facing and reset its timer.
uint32_t function_493110(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x52323c});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    uint32_t actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x404);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    actor = run.get(receiver + 0x12c);
    if (run.get8(actor + 0x40) & 2) {
        uint32_t left = run.get(receiver + 0x138);
        uint32_t right = run.get(receiver + 0x140);
        run.put(receiver + 0x138, 0u - right);
        run.put(receiver + 0x140, 0u - left);
        run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffffd);
        actor = run.get(receiver + 0x12c);
        left = run.get(actor + 0x118);
        if (left != 0x80000000) {
            right = run.get(actor + 0x120);
            run.put(actor + 0x118, 0u - right);
            run.put(actor + 0x120, 0u - left);
        }
        left = run.get(actor + 0x128);
        if (left != 0x80000000) {
            right = run.get(actor + 0x130);
            run.put(actor + 0x128, 0u - right);
            run.put(actor + 0x130, 0u - left);
        }
        run.call(0x406180, actor);
    }
    run.put(receiver + 0x440, uint32_t(s32(run.call(0x4a3050, 0)) % 0xc9));
    run.put(receiver + 0x43c, run.get(0x537210));
    return 0;
}

// 0x493450. Enter death, publish collision bounds and start the death clock.
uint32_t function_493450(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sound = run.get(receiver + 0x3a4);
    if (sound && run.get(0x532c0c)) {
        run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
    }
    uint32_t object = run.get(receiver + 0xc);
    run.put(object + 0x138, run.get(receiver + 0x210));
    run.put(object + 0x13c, run.get(receiver + 0x214));
    run.put(object + 0x140, run.get(receiver + 0x218));
    run.put(object + 0x144, run.get(receiver + 0x21c));
    uint32_t actor = run.get(receiver + 0x12c);
    if (run.get8(actor + 0x40) & 2) {
        object = run.get(receiver + 0xc);
        uint32_t right = run.get(object + 0x140);
        uint32_t left = run.get(object + 0x138);
        run.put(object + 0x138, 0u - right);
        run.put(run.get(receiver + 0xc) + 0x140, 0u - left);
    }
    run.put(receiver + 0x24, run.get(run.get(receiver + 0x10) + 0x1c));
    uint32_t state = run.call(0x4dba00, 0x537668, {0x5234f4});
    run.put(run.get(receiver + 0x10) + 0x1c, state);
    actor = run.get(receiver + 0x12c);
    uint32_t animation = run.get(receiver + 0x374);
    run.put(receiver + 0x134, run.get(actor + 0x190));
    run.call(0x4c8220, actor + 0x188, {animation});
    actor = run.get(receiver + 0x12c);
    run.put(actor + 0x8, run.get(actor + 0x8) | 0x80);
    run.put(receiver + 0x418, 0x4e20);
    run.put(receiver + 0x414, run.get(0x537210));
    run.put(receiver + 0x458, 0);
    return 0;
}

// 0x4936d0. React to the current world attack after state exclusions.
uint32_t function_4936d0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t state = run.get(run.get(receiver + 0x10) + 0x1c);
    uint32_t name = run.call(0x406020, 0x537698, {state});
    if (!run.call(0x4a3810, 0, {run.get(name), 0x5234f4})) {
        return 0;
    }
    state = run.get(run.get(receiver + 0x10) + 0x1c);
    name = run.call(0x406020, 0x537698, {state});
    if (!run.call(0x4a3810, 0, {run.get(name), 0x52c8d8})) {
        return 0;
    }
    state = run.get(run.get(receiver + 0x10) + 0x1c);
    name = run.call(0x441030, 0x537698, {state});
    uint32_t string = run.get(0x5376b4);
    uint32_t count = run.get(0x5376b8);
    while (count) {
        if (string) {
            run.call(0x4f6439, string);
        }
        string += 4;
        --count;
    }
    if (!run.call(0x4a3810, 0, {run.get(name), 0x52c8e4})) {
        return 0;
    }
    state = run.get(run.get(receiver + 0x10) + 0x1c);
    name = run.call(0x441030, 0x537698, {state});
    string = run.get(0x5376b4);
    count = run.get(0x5376b8);
    while (count) {
        if (string) {
            run.call(0x4f6439, string);
        }
        string += 4;
        --count;
    }
    if (!run.call(0x4a3810, 0, {run.get(name), 0x52323c})) {
        return 0;
    }
    uint32_t attack = run.get(run.get(run.get(run.get(0x537e88) + 0x6c) + 0x14) + 0xe8);
    if (attack == run.get(receiver + 0x19c)) {
        return 0;
    }
    run.put(receiver + 0x19c, attack);
    uint32_t target = run.get(run.get(receiver + 0xc) + 0x74);
    run.call(0x440e20, receiver, {target});
    if (run.get(target + 0xd0) == 0x20) {
        run.put(target + 0x8, run.get(target + 0x8) | 0x10000);
    }
    function_493450(run, receiver, nullptr);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4923e0:
        return function_4923e0(run, receiver, arguments);
    case 0x4928f0:
        return function_4928f0(run, receiver, arguments);
    case 0x492c40:
        return function_492c40(run, receiver, arguments);
    case 0x492c60:
        return function_492c60(run, receiver, arguments);
    case 0x492ce0:
        return function_492ce0(run, receiver, arguments);
    case 0x492d30:
        return function_492d30(run, receiver, arguments);
    case 0x492da0:
        return function_492da0(run, receiver, arguments);
    case 0x492f70:
        return function_492f70(run, receiver, arguments);
    case 0x492fb0:
        return function_492fb0(run, receiver, arguments);
    case 0x493110:
        return function_493110(run, receiver, arguments);
    case 0x493450:
        return function_493450(run, receiver, arguments);
    case 0x4936d0:
        return function_4936d0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_twelve_tentacle_core_01_entry, owned, body)
