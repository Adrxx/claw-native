// Original player fade factory, runner and circular rendering
//
// Recovered from the hash-verified original instruction packet.
#include "ClawRuntime.hpp"
#include <cmath>
#include <algorithm>

namespace {

using claw::Run;
using claw::s32;

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x42d420:
        return 0;
    case 0x42d440:
        return 0;
    case 0x48fae0:
        return 4;
    case 0x48fbe0:
        return 4;
    case 0x4b8960:
        return 1;
    case 0x4c61d0:
        return 0;
    case 0x4ebf80:
        return 0;
    case 0x4ec050:
        return 2;
    case 0x4ec600:
        return 1;
    case 0x4ec8d0:
        return 0;
    case 0x4ec920:
        return 0;
    case 0x4ec990:
        return 1;
    case 0x4ec9c0:
        return 3;
    case 0x4ecb00:
        return 2;
    case 0x4ecb20:
        return 1;
    case 0x4ecb30:
        return 0;
    case 0x4ecbc0:
        return 0;
    case 0x4ed5e0:
        return 0;
    case 0x4ed600:
        return 1;
    case 0x4ed620:
        return 0;
    case 0x4ed670:
        return 1;
    case 0x4ed800:
        return 1;
    case 0x4ee170:
        return 6;
    case 0x4ee6b0:
        return 0;
    case 0x4ee820:
        return 0;
    case 0x4ee860:
        return 0;
    default:
        return -1;
    }
}

// Dynamic calls into this family execute translated owners directly.
uint32_t virtualCall(Run &run, uint32_t object, uint32_t offset, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t function = run.get(run.get(object) + offset);
    if (owned(function) >= 0) {
        return body(run, function, object, arguments.begin());
    }
    return run.call(function, object, arguments);
}

struct Outgoing {
    Run &run;
    uint32_t previous;
    Outgoing(Run &run, int32_t displacement) : run(run), previous(run.stackPointer) {
        run.stackPointer = run.automatic(displacement);
    }
    ~Outgoing() {
        run.stackPointer = previous;
    }
};

// Direct owned calls retain the original callee frame for addressable locals.
struct Frame {
    Run &run;
    uint32_t previous;
    Frame(Run &run, int32_t displacement) : run(run), previous(run.frame) {
        run.frame += uint32_t(displacement);
    }
    ~Frame() {
        run.frame = previous;
    }
};

uint32_t function_4ec050(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ed670(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ec9c0(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_4ee170(Run &run, uint32_t receiver, const uint32_t *arguments);

// 0x42d420. Owner +0x50 sound, +0x14 enabled.
uint32_t function_42d420(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sound = run.get(receiver + 0x50);
    if (sound && run.get(receiver + 0x14)) {
        run.call(0x4b55a0, sound);
    }
    return 0;
}

// 0x42d440.
uint32_t function_42d440(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t sound = run.get(receiver + 0x50);
    if (sound && run.get(receiver + 0x14)) {
        run.call(0x4b55b0, sound, {0});
    }
    return 0;
}

// 0x4b8960. Unsigned clock deadline wraps before comparison.
uint32_t function_4b8960(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t deadline = run.icall(0x546df0) + arguments[0];
    uint32_t now = run.icall(0x546df0);
    while (now < deadline) {
        now = run.icall(0x546df0);
    }
    return 0;
}

// 0x4c61d0. Embedded palette manager, vtable at +0x04.
uint32_t function_4c61d0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x04, 0x5136e8);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver, 0);
    return receiver;
}

// 0x4ebf80. Manager list/count/capacity/growth at +0x14..+0x20.
uint32_t function_4ebf80(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x10, 0x5141c0);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x20, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x0c, 0);
    return receiver;
}

// 0x4ec600.
uint32_t function_4ec600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t last = run.get(receiver + 0x18) - 1;
    if (s32(last) < 0) {
        return 0;
    }
    uint32_t list = run.get(receiver + 0x14);
    uint32_t index = 0;
    while (run.get(list + index * 4) != arguments[0]) {
        ++index;
        if (s32(index) > s32(last)) {
            return 0;
        }
    }
    uint32_t count = run.get(receiver + 0x18) - index - 1;
    list = run.get(receiver + 0x14);
    for (uint32_t i = 0; i != count; ++i) {
        run.put(list + (index + i) * 4, run.get(list + (index + i + 1) * 4));
    }
    run.put(receiver + 0x18, run.get(receiver + 0x18) - 1);
    if (arguments[0]) {
        virtualCall(run, arguments[0], 0x00, {1});
    }
    return 0;
}

// 0x4ec8d0. +0x1c gradient table, +0x30 ownership.
uint32_t function_4ec8d0(Run &run, uint32_t receiver, const uint32_t *) {
    function_4c61d0(run, receiver + 0x04, nullptr);
    run.put(receiver, 0x5141d8);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x30, 1);
    return receiver;
}

// 0x4ec920.
uint32_t function_4ec920(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x5141d8);
    if (run.get(receiver + 0x1c) && run.get(receiver + 0x30)) {
        run.call(0x4c7510, receiver + 0x04, {run.get(receiver + 0x1c)});
        run.put(receiver + 0x1c, 0);
    }
    run.call(0x4c61f0, receiver + 0x04);
    return 0;
}

// 0x4ec990.
uint32_t function_4ec990(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t deadline = run.icall(0x546a24) + arguments[0];
    uint32_t now = run.icall(0x546a24);
    while (now < deadline) {
        now = run.icall(0x546a24);
    }
    return 0;
}

// 0x4ecb00. +0x24/+0x28 default surfaces.
uint32_t function_4ecb00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x24, arguments[0]);
    run.put(receiver + 0x28, arguments[1]);
    return 0;
}

// 0x4ecb20. +0x2c surface manager.
uint32_t function_4ecb20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x2c, arguments[0]);
    return 0;
}

// 0x4ecb30.
uint32_t function_4ecb30(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0);
    return receiver;
}

// 0x4ecbc0. Init +0x0c is intentionally untouched.
uint32_t function_4ecbc0(Run &run, uint32_t receiver, const uint32_t *) {
    function_4ecb30(run, receiver, nullptr);
    run.put(receiver + 0x18, 0x140);
    run.put(receiver, 2);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x08, 0);
    run.put(receiver + 0x10, 1);
    run.put(receiver + 0x14, 0);
    run.put(receiver + 0x1c, 0xf0);
    run.put(receiver + 0x20, 0);
    return receiver;
}

// 0x4ed5e0. Circle +0x40 temporary surface.
uint32_t function_4ed5e0(Run &run, uint32_t receiver, const uint32_t *) {
    function_4ec8d0(run, receiver, nullptr);
    run.put(receiver, 0x514250);
    run.put(receiver + 0x40, 0);
    return receiver;
}

// 0x4ed620.
uint32_t function_4ed620(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x514250);
    run.call(0x4bc110, receiver);
    function_4ec920(run, receiver, nullptr);
    return 0;
}

// 0x4ed600.
uint32_t function_4ed600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4ed620(run, receiver, nullptr);
    if (arguments[0] & 1) {
        run.call(0x4f6428, 0, {receiver});
    }
    return receiver;
}

// 0x4ed670. Dimensions +0x2064/+0x2068; row bounds +0x60/+0x1060.
uint32_t function_4ed670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t init = arguments[0];
    run.put(receiver + 0x20, 0);
    uint32_t destination = run.get(init + 0x04);
    if (!destination) {
        destination = run.get(receiver + 0x24);
    }
    run.put(receiver + 0x38, destination);
    uint32_t source = run.get(init + 0x08);
    if (!source) {
        source = run.get(receiver + 0x28);
    }
    run.put(receiver + 0x3c, source);
    run.put(receiver + 0x48, run.get(init + 0x10));
    run.put(receiver + 0x4c, run.get(init + 0x18));
    run.put(receiver + 0x50, run.get(init + 0x1c));
    uint32_t palette = run.get(init + 0x0c);
    run.put(receiver + 0x44, palette);
    uint32_t gradient = run.get(init + 0x14);
    run.put(receiver + 0x2060, gradient);
    if (s32(gradient) > 0 && !run.get(init + 0x20) && !palette) {
        return 0;
    }
    destination = run.get(receiver + 0x38);
    if (!destination) {
        return 0;
    }
    if (!run.get(receiver + 0x3c) && !run.get(receiver + 0x48)) {
        return 0;
    }
    uint32_t rect = run.automatic(-0x10);
    uint32_t width = run.get(destination + 0x18);
    run.put(receiver + 0x2064, width);
    uint32_t height = run.get(destination + 0x14);
    run.put(receiver + 0x2068, height);
    run.put(rect + 0x08, width);
    run.put(rect + 0x0c, height);
    run.put(rect, 0);
    run.put(rect + 0x04, 0);
    if (!run.icall(0x546cd4, {rect, run.get(receiver + 0x4c), run.get(receiver + 0x50)})) {
        return 0;
    }
    if (run.get(receiver + 0x48)) {
        for (uint32_t row = 0; s32(row) < run.gets(receiver + 0x2068); ++row) {
            run.put(receiver + 0x60 + row * 4, 0);
            run.put(receiver + 0x1060 + row * 4, run.get(receiver + 0x2064));
        }
    } else {
        for (uint32_t row = 0; s32(row) < run.gets(receiver + 0x2068); ++row) {
            run.put(receiver + 0x60 + row * 4, run.get(receiver + 0x4c));
            run.put(receiver + 0x1060 + row * 4, run.get(receiver + 0x4c));
        }
    }
    gradient = run.get(receiver + 0x2060);
    if (s32(gradient) > 0) {
        uint32_t table = run.get(init + 0x20);
        if (!table) {
            table = run.call(0x4c6bd0, receiver + 0x04, {run.get(run.get(receiver + 0x44) + 0x0c), gradient, 0});
            run.put(receiver + 0x1c, table);
            run.put(receiver + 0x30, 1);
            return 1;
        }
        run.put(receiver + 0x1c, table);
    }
    return 1;
}

// 0x4ec050. Constructors and nonowned initializers execute original code.
uint32_t function_4ec050(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t kind = arguments[0];
    uint32_t init = arguments[1];
    auto error = [&](uint32_t message) {
        uint32_t text = run.automatic(-0x54);
        run.call(0x4f65f2, text, {message});
        run.call(0x4ec6b0, 0, {run.get(text)});
    };
    if (kind > 3) {
        error(0x53401c);
        return 0;
    }
    if (init && run.get(init) != kind + 1) {
        error(0x53404c);
        return 0;
    }
    const uint32_t sizes[] = {0x494, 0x206c, 0x7d5c, 0x5c};
    uint32_t object = run.call(0x4f63ec, 0, {sizes[kind]});
    if (object) {
        if (kind == 1) {
            object = function_4ed5e0(run, object, nullptr);
        } else {
            const uint32_t constructors[] = {0x4ee880, 0, 0x4ed060, 0x4ecc60};
            object = run.call(constructors[kind], object);
        }
    }
    uint32_t surfaces[] = {run.get(receiver), run.get(receiver + 0x04)};
    function_4ecb00(run, object, surfaces);
    uint32_t manager[] = {run.get(receiver + 0x24)};
    function_4ecb20(run, object, manager);
    bool defaultInit = !init;
    if (defaultInit) {
        init = run.automatic(-0x38);
        if (kind == 1) {
            function_4ecbc0(run, init, nullptr);
        } else {
            const uint32_t constructors[] = {0x4ecb40, 0, 0x4ecc00, 0x4ecc30};
            run.call(constructors[kind], init);
        }
    }
    uint32_t success;
    if (kind == 1) {
        uint32_t args[] = {init};
        Frame frame(run, -0x58);
        success = function_4ed670(run, object, args);
    } else {
        const uint32_t initializers[] = {0x4ee9a0, 0, 0x4ed0b0, 0x4ecd00};
        if (kind == 3) {
            // The byte-only local in 0x4ecd00 retains the earlier setter return PC.
            // Its high bytes become part of the radial pixel record.
            run.put(run.automatic(-0x5c), 0x4ec53f);
            Outgoing outgoing(run, -0x58);
            success = run.call(initializers[kind], object, {init});
        } else {
            success = run.call(initializers[kind], object, {init});
        }
    }
    if (!success) {
        error(0x5340a0);
        if (object) {
            virtualCall(run, object, 0x00, {1});
        }
        if (kind == 0 && defaultInit) {
            run.call(0x4f6584, run.automatic(-0x14));
        }
        return 0;
    }
    if (kind == 0 && defaultInit) {
        run.call(0x4f6584, run.automatic(-0x14));
    }
    if (!object) {
        return 0;
    }
    uint32_t count = run.get(receiver + 0x18);
    uint32_t list = run.get(receiver + 0x14);
    uint32_t next = count + 1;
    if (!next) {
        if (list) {
            run.call(0x4f6428, 0, {list});
            run.put(receiver + 0x14, 0);
        }
        run.put(receiver + 0x1c, 0);
        run.put(receiver + 0x18, 0);
    } else if (!list) {
        uint32_t bytes = next * 4;
        list = run.call(0x4f63ec, 0, {bytes});
        run.put(receiver + 0x14, list);
        for (uint32_t i = 0; i != (bytes >> 2); ++i) {
            run.put(list + i * 4, 0);
        }
        run.put(receiver + 0x1c, next);
        run.put(receiver + 0x18, next);
    } else if (s32(next) > run.gets(receiver + 0x1c)) {
        uint32_t capacity = run.get(receiver + 0x1c);
        uint32_t growth = run.get(receiver + 0x20);
        if (!growth) {
            growth = uint32_t(s32(count) / 8);
            if (s32(growth) < 4) {
                growth = 4;
            } else if (s32(growth) > 0x400) {
                growth = 0x400;
            }
        }
        capacity += growth;
        if (s32(next) >= s32(capacity)) {
            capacity = next;
        }
        uint32_t replacement = run.call(0x4f63ec, 0, {capacity * 4});
        uint32_t oldCount = run.get(receiver + 0x18);
        list = run.get(receiver + 0x14);
        for (uint32_t i = 0; i != ((oldCount * 4) >> 2); ++i) {
            run.put(replacement + i * 4, run.get(list + i * 4));
        }
        oldCount = run.get(receiver + 0x18);
        for (uint32_t i = 0; i != next - oldCount; ++i) {
            run.put(replacement + (oldCount + i) * 4, 0);
        }
        run.call(0x4f6428, 0, {run.get(receiver + 0x14)});
        run.put(receiver + 0x14, replacement);
        run.put(receiver + 0x18, next);
        run.put(receiver + 0x1c, capacity);
    } else {
        if (s32(next) > s32(count)) {
            for (uint32_t i = 0; i != next - count; ++i) {
                run.put(list + (count + i) * 4, 0);
            }
        }
        run.put(receiver + 0x18, next);
    }
    run.put(run.get(receiver + 0x14) + count * 4, object);
    return object;
}

// 0x48fae0 / 0x48fbe0. Wrapper-local init occupies 0x24 bytes.
uint32_t wrapper(Run &run, uint32_t receiver, const uint32_t *arguments, bool opening) {
    uint32_t manager = run.get(receiver + 0x10);
    if (!manager) {
        return 0;
    }
    uint32_t context = run.get(receiver + 0x0c);
    if (!run.get(context + 0x1c)) {
        return 0;
    }
    uint32_t state = run.get(context + 0x04);
    uint32_t destination = run.get(run.get(state + 0x10) + 0x2c);
    if (!destination) {
        return 0;
    }
    uint32_t source = 0;
    if (opening) {
        source = run.get(run.get(state + 0x14) + 0x2c);
        if (!source) {
            return 0;
        }
    }
    uint32_t init = run.automatic(-0x24);
    function_4ecbc0(run, init, nullptr);
    if (opening) {
        run.put(init + 0x1c, arguments[1]);
        run.put(init + 0x10, 0);
        run.put(init + 0x18, arguments[0]);
        run.put(init + 0x04, destination);
        run.put(init + 0x08, source);
    } else {
        run.put(init + 0x10, 1);
        run.put(init + 0x18, arguments[0]);
        run.put(init + 0x1c, arguments[1]);
        run.put(init + 0x04, destination);
        run.put(init + 0x08, 0);
    }
    uint32_t factoryArgs[] = {1, init};
    uint32_t object;
    {
        Frame frame(run, opening ? -0x40 : -0x3c);
        object = function_4ec050(run, manager, factoryArgs);
    }
    if (!object) {
        return 0;
    }
    function_42d420(run, run.get(receiver + 0x04), nullptr);
    if (run.get(0x537238)) {
        function_4b8960(run, 0, arguments + 2);
        destination = run.get(run.get(run.get(run.get(receiver + 0x0c) + 0x04) + 0x10) + 0x2c);
        if (opening) {
            run.call(0x4b9c50, destination, {source});
        } else {
            Outgoing outgoing(run, -0x38);
            run.call(0x4b97c0, destination, {0});
        }
    } else {
        uint32_t args[] = {arguments[2], arguments[3], 0};
        function_4ec9c0(run, object, args);
    }
    function_42d440(run, run.get(receiver + 0x04), nullptr);
    uint32_t removeArgs[] = {object};
    function_4ec600(run, manager, removeArgs);
    return 1;
}
uint32_t function_48fae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return wrapper(run, receiver, arguments, false);
}
uint32_t function_48fbe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return wrapper(run, receiver, arguments, true);
}

// 0x4ee820.
uint32_t function_4ee820(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.gets(receiver + 0x2060) > 0 && run.get(receiver + 0x48)) {
        uint32_t surface = run.call(0x4bc960, run.get(receiver + 0x2c), {run.get(receiver + 0x2064), run.get(receiver + 0x2068), 0, 0, 0xffffffff});
        uint32_t destination = run.get(receiver + 0x38);
        run.put(receiver + 0x40, surface);
        run.call(0x4b9c50, surface, {destination});
    }
    return 0;
}

// 0x4ee860.
uint32_t function_4ee860(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t surface = run.get(receiver + 0x40);
    if (surface) {
        run.call(0x4bc4f0, run.get(receiver + 0x2c), {surface});
        run.put(receiver + 0x40, 0);
    }
    return 0;
}

// x87 stack operations at the original startup CW 0x023f.
// Signed-int32 squares and their sums fit the finite binary64 exponent range.
// Ordered binary64 ADD/SQRT therefore retain the original 53-bit results.
// The reference interpreter leaves sticky arithmetic exceptions unchanged for
// these two instructions; FLD/FXCH/FSQRT clear C1. Original pow/ftol receipts
// retain their complete returned SW and raw extended slots, including live TOP.
// A caller's radius/render status is shared across owned virtual calls.
struct X87 {
    ClawX87State state{};
    X87() {
        state.size = sizeof(state);
        state.version = CLAW_X87_VERSION;
        state.control = 0x023f;
    }
    void top(int delta) {
        state.status = (state.status & ~0x3800u) | (((((state.status >> 11) & 7) + delta) & 7) << 11);
    }
    static ClawX87Value raw(double value) {
        uint64_t bits;
        std::memcpy(&bits, &value, sizeof(bits));
        ClawX87Value result{};
        uint32_t exponent = uint32_t((bits >> 52) & 0x7ff);
        uint64_t fraction = bits & 0xfffffffffffffu;
        result.signExponent = uint32_t(bits >> 63) << 15;
        if (exponent == 0x7ff) {
            result.signExponent |= 0x7fff;
            result.significand = fraction ? 0xc000000000000000ull : 0x8000000000000000ull;
            if (fraction) {
                result.signExponent = 0xffff;
            }
        } else if (exponent) {
            result.signExponent |= exponent + 16383 - 1023;
            result.significand = (fraction | 0x10000000000000ull) << 11;
        } else if (fraction) {
            int shift = 0;
            while (!(fraction & 0x10000000000000ull)) {
                fraction <<= 1;
                ++shift;
            }
            result.signExponent |= uint32_t(1 + 16383 - 1023 - shift);
            result.significand = fraction << 11;
        }
        return result;
    }
    double value(uint32_t index = 0) const {
        const auto &slot = state.slots[index];
        uint32_t exponent = slot.signExponent & 0x7fff;
        double result;
        if (exponent == 0x7fff) {
            result = slot.significand == 0x8000000000000000ull ? INFINITY : NAN;
        } else {
            result = std::ldexp(double(slot.significand), int(exponent) - 16383 - 63);
        }
        return slot.signExponent & 0x8000 ? -result : result;
    }
    void duplicate(uint32_t index) {
        auto slot = state.slots[index];
        for (uint32_t i = state.count; i; --i) {
            state.slots[i] = state.slots[i - 1];
        }
        state.slots[0] = slot;
        ++state.count;
        top(-1);
        state.status &= ~0x200u;
    }
    void exchange(uint32_t index) {
        std::swap(state.slots[0], state.slots[index]);
        state.status &= ~0x200u;
    }
    void pop() {
        --state.count;
        for (uint32_t i = 0; i < state.count; ++i) {
            state.slots[i] = state.slots[i + 1];
        }
        state.slots[state.count] = {};
        top(1);
        state.status &= ~0x200u;
    }
    void load(Run &run, double value) {
        uint64_t bits;
        std::memcpy(&bits, &value, sizeof(bits));
        run.x87_step(CLAW_X87_F64, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void integer(Run &run, uint32_t value) {
        run.x87_step(CLAW_X87_I32, state, {value});
    }
    void arithmetic(Run &run, uint32_t operation, double operand) {
        uint64_t bits;
        std::memcpy(&bits, &operand, sizeof(bits));
        run.x87_step(operation, state, {uint32_t(bits), uint32_t(bits >> 32)});
    }
    void squareRoot() {
        volatile double input = value();
        volatile double result = std::sqrt(input);
        state.status &= ~0x200u;
        state.slots[0] = raw(result);
    }
    void add(double operand) {
        volatile double input = value();
        volatile double result = input + operand;
        state.status &= ~0x200u;
        state.slots[0] = raw(result);
    }
    double spill() {
        double result = value();
        pop();
        return result;
    }
    void compare(double operand) {
        double input = value();
        state.status &= ~0x4700u;
        if (std::isnan(input) || std::isnan(operand)) {
            state.status |= 0x4501;
        } else if (input < operand) {
            state.status |= 0x100;
        } else if (input == operand) {
            state.status |= 0x4000;
        }
        pop();
    }
    bool lessEqual() const {
        return (state.status & 0x4100) != 0;
    }
    uint32_t call(Run &run, uint32_t function, uint32_t pops, uint32_t pushes) {
        state.popCount = pops;
        state.pushCount = pushes;
        state.returned = 0;
        state.eax = 0;
        state.edx = 0;
        return run.call_x87_exact(function, 0, state);
    }
    uint32_t convert(Run &run) {
        return call(run, 0x4a30e0, 1, 0);
    }
    uint32_t rootInteger(Run &run, uint32_t radicand) {
        integer(run, radicand);
        squareRoot();
        return convert(run);
    }
};

uint32_t extentCore(Run &run, uint32_t receiver, X87 &fp);
uint32_t renderCore(Run &run, uint32_t receiver, const uint32_t *arguments, X87 &fp);

uint32_t fadeVirtual(Run &run, uint32_t object, uint32_t offset, X87 &fp, std::initializer_list<uint32_t> arguments = {}) {
    uint32_t function = run.get(run.get(object) + offset);
    if (function == 0x4ee6b0) {
        return extentCore(run, object, fp);
    }
    if (function == 0x4ed800) {
        return renderCore(run, object, arguments.begin(), fp);
    }
    return virtualCall(run, object, offset, arguments);
}

// 0x4ec9c0. Duration/start/max frame are rounded through original float spills.
uint32_t function_4ec9c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    X87 fp;
    uint32_t maximum = fadeVirtual(run, receiver, 0x08, fp);
    if (s32(maximum) < 1) {
        return 0;
    }
    fadeVirtual(run, receiver, 0x0c, fp);
    fadeVirtual(run, receiver, 0x04, fp, {0});
    function_4ec990(run, receiver, arguments + 1);
    uint32_t start = run.icall(0x546a24);
    float startFloat = float(start);
    float durationFloat = float(arguments[0]);
    float maximumFloat = float(s32(maximum));
    if (double(startFloat) != double(start) || double(durationFloat) != double(arguments[0]) || double(maximumFloat) != double(s32(maximum))) {
        fp.state.status |= 0x20;
    }
    uint32_t previous = 0;
    uint32_t current = 0;
    uint32_t frames = 0;
    do {
        uint32_t now = run.icall(0x546a24);
        fp.load(run, double(now));
        fp.arithmetic(run, CLAW_X87_SUBR_F64, double(startFloat));
        run.x87_step(CLAW_X87_CHS, fp.state);
        fp.arithmetic(run, CLAW_X87_DIV_F64, double(durationFloat));
        fp.arithmetic(run, CLAW_X87_MUL_F64, double(maximumFloat));
        current = fp.convert(run);
        if (current != previous && s32(current) <= s32(maximum) && s32(current) > 0) {
            if (arguments[2] && run.get(receiver + 0x2c)) {
                uint32_t child = run.get(run.get(receiver + 0x2c));
                run.call(run.get(run.get(child) + 0x58), 0, {child, 1, 0});
            }
            fadeVirtual(run, receiver, 0x04, fp, {current});
            ++frames;
        }
        previous = current;
    } while (s32(current) <= s32(maximum));
    if (current != maximum) {
        fadeVirtual(run, receiver, 0x04, fp, {maximum});
        ++frames;
    }
    float frameFloat = float(s32(frames));
    if (double(frameFloat) != double(s32(frames))) {
        fp.state.status |= 0x20;
    }
    uint32_t now = run.icall(0x546a24);
    fp.load(run, double(now - start));
    fp.arithmetic(run, CLAW_X87_MUL_F64, double(run.getf(0x5141ec)));
    fp.load(run, double(frameFloat));
    run.x87_step(CLAW_X87_DIV_ST1, fp.state);
    fp.exchange(1);
    fp.pop();
    uint32_t rate = fp.convert(run);
    run.put(receiver + 0x34, rate);
    fadeVirtual(run, receiver, 0x10, fp);
    return 0;
}

// 0x4ee6b0. Keep all four original power boundaries and the selection tree.
uint32_t extentCore(Run &run, uint32_t receiver, X87 &fp) {
    uint32_t x = run.get(receiver + 0x4c);
    fp.integer(run, x);
    fp.load(run, run.getd(0x514268));
    fp.call(run, 0x4f1b30, 2, 1);
    uint32_t y = run.get(receiver + 0x50);
    fp.load(run, run.getd(0x514268));
    fp.integer(run, y);
    fp.exchange(2);
    double xSquared = fp.spill();
    fp.call(run, 0x4f1b30, 2, 1);
    double ySquared = fp.value();
    fp.add(xSquared);
    uint32_t surface = run.get(receiver + 0x38);
    fp.squareRoot();
    uint32_t oppositeY = run.get(surface + 0x14) - y;
    fp.integer(run, oppositeY);
    fp.load(run, run.getd(0x514268));
    fp.exchange(2);
    double firstRadius = fp.spill();
    fp.exchange(1);
    fp.call(run, 0x4f1b30, 2, 1);
    uint32_t oppositeX = run.get(surface + 0x18) - x;
    fp.integer(run, oppositeX);
    fp.load(run, run.getd(0x514268));
    fp.exchange(2);
    double oppositeYSquared = fp.spill();
    fp.exchange(1);
    fp.call(run, 0x4f1b30, 2, 1);
    fp.duplicate(0);
    fp.add(oppositeYSquared);
    fp.load(run, oppositeYSquared);
    fp.exchange(1);
    fp.squareRoot();
    fp.exchange(2);
    fp.add(ySquared);
    fp.exchange(1);
    fp.add(xSquared);
    fp.load(run, firstRadius);
    fp.exchange(2);
    fp.squareRoot();
    fp.exchange(1);
    fp.squareRoot();
    fp.exchange(1);
    fp.exchange(2);
    fp.compare(fp.value(3));
    fp.exchange(1);
    double secondRadius = fp.value();
    fp.exchange(1);
    double fourthRadius = fp.spill();
    if (!fp.lessEqual()) {
        fp.load(run, firstRadius);
    } else {
        fp.duplicate(1);
    }
    fp.compare(fp.value(1));
    if (!fp.lessEqual()) {
        fp.load(run, firstRadius);
        fp.compare(fp.value(2));
        if (!fp.lessEqual()) {
            fp.load(run, firstRadius);
        } else {
            fp.duplicate(1);
        }
    } else {
        fp.duplicate(0);
    }
    fp.compare(fourthRadius);
    uint32_t result;
    if (!fp.lessEqual()) {
        fp.load(run, firstRadius);
        fp.compare(fp.value(2));
        if (!fp.lessEqual()) {
            fp.load(run, firstRadius);
        } else {
            fp.duplicate(1);
        }
        fp.compare(fp.value(1));
        bool comparison = fp.lessEqual();
        fp.pop();
        if (!comparison) {
            fp.load(run, firstRadius);
            fp.compare(fp.value(1));
            if (!fp.lessEqual()) {
                fp.pop();
                fp.load(run, firstRadius);
            }
        } else {
            fp.pop();
            fp.load(run, secondRadius);
        }
        result = fp.convert(run);
    } else {
        fp.pop();
        fp.pop();
        fp.load(run, fourthRadius);
        result = fp.convert(run);
    }
    run.put(receiver + 0x5c, result);
    return result;
}

// Shared arithmetic and byte raster of 0x4ee170 and the inlined fade-out arm.
void gradientRow(Run &run, uint32_t receiver, uint32_t row, uint32_t radiusSquared, uint32_t radius, uint32_t lookup, uint32_t destination, uint32_t source, X87 &fp) {
    uint32_t gradient = run.get(receiver + 0x2060);
    if (s32(gradient) < 1) {
        return;
    }
    uint32_t centerY = run.get(receiver + 0x50);
    uint32_t centerX = run.get(receiver + 0x4c);
    uint32_t dy = row - centerY;
    uint32_t ySquared = dy * dy;
    uint32_t x = centerX - fp.rootInteger(run, radiusSquared - ySquared) + 1;
    uint32_t dx = x - centerX;
    uint32_t distance = fp.rootInteger(run, dx * dx + ySquared);
    uint32_t destinationPitch = run.get(run.get(receiver + 0x38) + 0x1c);
    uint32_t leftDestination = destination + row * destinationPitch + x;
    uint32_t sourcePitch = run.get(run.get(receiver + 0x3c) + 0x1c);
    uint32_t leftSource = source + row * sourcePitch + x;
    uint32_t rightDestination = destination - x + row * destinationPitch + centerX * 2;
    uint32_t rightSource = source - x + row * sourcePitch + centerX * 2;
    int32_t half = run.gets(receiver + 0x2068) / 2;
    uint32_t destinationMirror = 0;
    uint32_t sourceMirror = 0;
    bool mirror = false;
    if (s32(centerY) >= half) {
        if (s32(row) > s32(centerY)) {
            return;
        }
        uint32_t delta = (centerY - row) * 2;
        if (s32(delta + row) < run.gets(receiver + 0x2068)) {
            destinationMirror = delta * destinationPitch;
            sourceMirror = delta * sourcePitch;
            mirror = true;
        }
    } else {
        if (s32(row) < s32(centerY)) {
            return;
        }
        uint32_t delta = (row - centerY) * 2;
        if (s32(row - delta) >= 0) {
            destinationMirror = 0 - delta * destinationPitch;
            sourceMirror = 0 - delta * sourcePitch;
            mirror = true;
        }
    }
    while (s32(distance) >= s32(radius - gradient)) {
        if (s32(x) > s32(centerX)) {
            return;
        }
        uint32_t level = distance - radius + gradient;
        if (s32(x) >= 0) {
            run.put8(leftDestination, run.get8(lookup + uint32_t(run.get8(leftSource)) * gradient + level));
            if (mirror) {
                run.put8(leftDestination + destinationMirror, run.get8(lookup + uint32_t(run.get8(leftSource + sourceMirror)) * run.get(receiver + 0x2060) + level));
            }
        }
        ++leftDestination;
        ++leftSource;
        if (s32(run.get(receiver + 0x4c) * 2 - x) < run.gets(receiver + 0x2064)) {
            run.put8(rightDestination, run.get8(lookup + uint32_t(run.get8(rightSource)) * run.get(receiver + 0x2060) + level));
            if (mirror) {
                run.put8(rightDestination + destinationMirror, run.get8(lookup + uint32_t(run.get8(rightSource + sourceMirror)) * run.get(receiver + 0x2060) + level));
            }
        }
        centerX = run.get(receiver + 0x4c);
        --rightDestination;
        --rightSource;
        ++x;
        dx = x - centerX;
        distance = fp.rootInteger(run, dx * dx + ySquared);
        gradient = run.get(receiver + 0x2060);
    }
}

// 0x4ee170.
uint32_t function_4ee170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    X87 fp;
    gradientRow(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5], fp);
    return 0;
}

void unlock(Run &run, uint32_t surface) {
    uint32_t interface = run.get(surface + 0x08);
    run.call(run.get(run.get(interface) + 0x80), 0, {interface, 0});
}

uint32_t clipped(uint32_t value, uint32_t limit) {
    if (s32(value) < 0) {
        value = 0;
    }
    return s32(value) < s32(limit) ? value : limit;
}

void copyBytes(Run &run, uint32_t destination, uint32_t source, uint32_t count) {
    if (s32(count) > 0) {
        for (uint32_t i = 0; i != count; ++i) {
            run.put8(destination + i, run.get8(source + i));
        }
    }
}

void clearBytes(Run &run, uint32_t destination, uint32_t count) {
    if (s32(count) > 0) {
        for (uint32_t i = 0; i != (count >> 2); ++i) {
            run.put(destination + i * 4, 0);
        }
        for (uint32_t i = count & ~3u; i != count; ++i) {
            run.put8(destination + i, 0);
        }
    }
}

// 0x4ed800. Incremental circle row boundaries and optional palette gradients.
uint32_t renderCore(Run &run, uint32_t receiver, const uint32_t *arguments, X87 &fp) {
    uint32_t frame = arguments[0];
    uint32_t delta = frame - run.get(receiver + 0x20);
    uint32_t destination = run.get(receiver + 0x38);
    if (destination) {
        uint32_t pixels = run.call(0x4b9730, destination, {0});
        run.put(receiver + 0x54, pixels);
    }
    uint32_t source = run.get(receiver + 0x3c);
    if (source) {
        uint32_t pixels = run.call(0x4b9730, source, {0});
        run.put(receiver + 0x58, pixels);
    }
    uint32_t pixelSize = run.get(run.get(receiver + 0x38) + 0xac);
    uint32_t lookup = 0;
    uint32_t table = run.get(receiver + 0x1c);
    if (table) {
        lookup = run.get(table + 0x08);
    }
    if (!run.get(receiver + 0x48)) {
        uint32_t row = run.get(receiver + 0x50) - delta - frame - run.get(receiver + 0x2060);
        if (s32(row) < 0) {
            row = 0;
        }
        uint32_t bounds = receiver + row * 4 + 0x1060;
        uint32_t squared = frame * frame;
        while (true) {
            uint32_t centerY = run.get(receiver + 0x50);
            uint32_t end = delta + frame + run.get(receiver + 0x2060) + centerY;
            if (run.gets(receiver + 0x2068) <= s32(end)) {
                end = run.get(receiver + 0x2068);
            }
            if (s32(row) >= s32(end)) {
                break;
            }
            if (s32(row) > s32(centerY - frame) && s32(row) < s32(frame + centerY)) {
                uint32_t dy = row - centerY;
                uint32_t extent = fp.rootInteger(run, squared - dy * dy);
                uint32_t width = run.get(receiver + 0x2064);
                uint32_t right = clipped(run.get(receiver + 0x4c) + extent, width);
                uint32_t left = clipped(run.get(receiver + 0x4c) - extent - 1, width);
                uint32_t count = (run.get(bounds - 0x1000) - left) * pixelSize;
                uint32_t sourcePointer = run.get(run.get(receiver + 0x3c) + 0x1c) * row + left * pixelSize + run.get(receiver + 0x58);
                uint32_t destinationPointer = run.get(run.get(receiver + 0x38) + 0x1c) * row + left * pixelSize + run.get(receiver + 0x54);
                copyBytes(run, destinationPointer, sourcePointer, count);
                uint32_t oldRight = run.get(bounds);
                uint32_t offset = pixelSize * oldRight;
                count = (right - oldRight) * pixelSize;
                sourcePointer = run.get(run.get(receiver + 0x3c) + 0x1c) * row + offset + run.get(receiver + 0x58);
                destinationPointer = run.get(run.get(receiver + 0x38) + 0x1c) * row + offset + run.get(receiver + 0x54);
                copyBytes(run, destinationPointer, sourcePointer, count);
                run.put(bounds - 0x1000, left);
                run.put(bounds, right);
            }
            uint32_t gradient = run.get(receiver + 0x2060);
            if (s32(row) > s32(run.get(receiver + 0x50) - frame - gradient) && s32(row) < s32(frame + gradient + run.get(receiver + 0x50))) {
                uint32_t radius = frame - 1 + gradient;
                gradientRow(run, receiver, row, radius * radius, radius, lookup, run.get(receiver + 0x54), run.get(receiver + 0x58), fp);
            }
            ++row;
            bounds += 4;
        }
    } else {
        uint32_t temporaryPixels = run.get(run.automatic(-0x1c));
        uint32_t temporary = run.get(receiver + 0x40);
        if (temporary) {
            temporaryPixels = run.call(0x4b9730, temporary, {0});
        }
        uint32_t radius = run.get(receiver + 0x5c) - frame;
        uint32_t squared = radius * radius;
        uint32_t row = run.get(receiver + 0x50) - radius - delta;
        if (s32(row) < 0) {
            row = 0;
        }
        uint32_t bounds = receiver + row * 4 + 0x60;
        while (true) {
            uint32_t centerY = run.get(receiver + 0x50);
            uint32_t end = delta + radius + centerY;
            if (run.gets(receiver + 0x2068) <= s32(end)) {
                end = run.get(receiver + 0x2068);
            }
            if (s32(row) >= s32(end)) {
                break;
            }
            if (s32(row) < s32(centerY - radius + 1) || s32(row) > s32(radius - 1 + centerY)) {
                uint32_t width = run.get(receiver + 0x2064);
                uint32_t pointer = run.get(run.get(receiver + 0x38) + 0x1c) * row + run.get(receiver + 0x54);
                clearBytes(run, pointer, width);
            } else {
                uint32_t dy = row - centerY;
                uint32_t extent = fp.rootInteger(run, squared - dy * dy);
                uint32_t width = run.get(receiver + 0x2064);
                uint32_t right = clipped(run.get(receiver + 0x4c) + extent, width);
                uint32_t left = clipped(run.get(receiver + 0x4c) - extent + 1, width);
                uint32_t previousLeft = run.get(bounds);
                uint32_t count = (left - previousLeft) * pixelSize;
                uint32_t pointer = run.get(run.get(receiver + 0x38) + 0x1c) * row + pixelSize * previousLeft + run.get(receiver + 0x54);
                clearBytes(run, pointer, count);
                count = (run.get(bounds + 0x1000) - right) * pixelSize;
                pointer = run.get(run.get(receiver + 0x38) + 0x1c) * row + right * pixelSize + run.get(receiver + 0x54);
                clearBytes(run, pointer, count);
                if (run.gets(receiver + 0x2060) > 0) {
                    gradientRow(run, receiver, row, squared, radius, lookup, run.get(receiver + 0x54), temporaryPixels, fp);
                }
                run.put(bounds, left);
                run.put(bounds + 0x1000, right);
            }
            ++row;
            bounds += 4;
        }
        temporary = run.get(receiver + 0x40);
        if (temporary) {
            unlock(run, temporary);
        }
    }
    run.put(receiver + 0x20, frame);
    destination = run.get(receiver + 0x38);
    if (destination) {
        unlock(run, destination);
    }
    source = run.get(receiver + 0x3c);
    if (source) {
        unlock(run, source);
    }
    return 0;
}


uint32_t function_4ed800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    X87 fp;
    return renderCore(run, receiver, arguments, fp);
}

uint32_t function_4ee6b0(Run &run, uint32_t receiver, const uint32_t *) {
    X87 fp;
    return extentCore(run, receiver, fp);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42d420:
        return function_42d420(run, receiver, arguments);
    case 0x42d440:
        return function_42d440(run, receiver, arguments);
    case 0x48fae0:
        return function_48fae0(run, receiver, arguments);
    case 0x48fbe0:
        return function_48fbe0(run, receiver, arguments);
    case 0x4b8960:
        return function_4b8960(run, receiver, arguments);
    case 0x4c61d0:
        return function_4c61d0(run, receiver, arguments);
    case 0x4ebf80:
        return function_4ebf80(run, receiver, arguments);
    case 0x4ec050:
        return function_4ec050(run, receiver, arguments);
    case 0x4ec600:
        return function_4ec600(run, receiver, arguments);
    case 0x4ec8d0:
        return function_4ec8d0(run, receiver, arguments);
    case 0x4ec920:
        return function_4ec920(run, receiver, arguments);
    case 0x4ec990:
        return function_4ec990(run, receiver, arguments);
    case 0x4ec9c0:
        return function_4ec9c0(run, receiver, arguments);
    case 0x4ecb00:
        return function_4ecb00(run, receiver, arguments);
    case 0x4ecb20:
        return function_4ecb20(run, receiver, arguments);
    case 0x4ecb30:
        return function_4ecb30(run, receiver, arguments);
    case 0x4ecbc0:
        return function_4ecbc0(run, receiver, arguments);
    case 0x4ed5e0:
        return function_4ed5e0(run, receiver, arguments);
    case 0x4ed600:
        return function_4ed600(run, receiver, arguments);
    case 0x4ed620:
        return function_4ed620(run, receiver, arguments);
    case 0x4ed670:
        return function_4ed670(run, receiver, arguments);
    case 0x4ed800:
        return function_4ed800(run, receiver, arguments);
    case 0x4ee170:
        return function_4ee170(run, receiver, arguments);
    case 0x4ee6b0:
        return function_4ee6b0(run, receiver, arguments);
    case 0x4ee820:
        return function_4ee820(run, receiver, arguments);
    case 0x4ee860:
        return function_4ee860(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_player_fade_canonical_entry, owned, body)
