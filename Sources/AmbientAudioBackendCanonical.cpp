// Original ambient voice, intrusive list and fade game logic.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x4b3bf0: case 0x4b3ec0: case 0x4b3ef0: case 0x4b3f40:
    case 0x4b3fe0: case 0x4b40c0: case 0x4b4110: case 0x4b4160:
    case 0x4b41b0: case 0x4b4d80: case 0x4b5210: case 0x4b5270:
        return function == 0x4b3fe0 ? 3 : 1;
    case 0x4b3dc0:
        return 4;
    case 0x4b4c80:
        return 2;
    case 0x4b4d00:
        return 5;
    case 0x4b3d80: case 0x4b3e30: case 0x4b3e70: case 0x4b3f70:
    case 0x4b3fc0: case 0x4b4b80: case 0x4b4c10: case 0x4b4df0:
        return 0;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

// Owned calls with stack-addressed locals retain the actual original entry ESP.
uint32_t child(Run &run, uint32_t function, uint32_t receiver, int32_t displacement,
               std::initializer_list<uint32_t> arguments = {}) {
    uint32_t saved = run.frame;
    run.frame += uint32_t(displacement);
    uint32_t result = body(run, function, receiver, arguments.begin());
    run.frame = saved;
    return result;
}

bool enabled(Run &run, uint32_t voice) {
    // Voice +0x10 manager; manager +0x78 enabled.
    return run.get(run.get(voice + 0x10) + 0x78) != 0;
}

uint32_t diagnostic(Run &run, uint32_t error, uint32_t line) {
    if (!error)
        return 1;
    run.call(0x4b4ed0, 0, {0x53228c, line, error});
    return 0;
}

// 0x4b3e70 and 0x4b3f70. COM writes the local initially containing ECX.
uint32_t getter(Run &run, uint32_t receiver, uint32_t slot, uint32_t line, bool status) {
    uint32_t output = run.automatic(-4);
    run.put(output, receiver);
    if (!enabled(run, receiver))
        return 0;
    // Voice +0x0c physical DirectSound interface.
    uint32_t interface = run.get(receiver + 0x0c);
    uint32_t error = run.call(run.get(run.get(interface) + slot), 0, {interface, output});
    if (!diagnostic(run, error != 0, line))
        return 0;
    uint32_t value = run.get(output);
    return status ? value & 1u : value;
}

// 0x4b3ef0, 0x4b40c0 and 0x4b4160.
uint32_t setter(Run &run, uint32_t receiver, uint32_t value, uint32_t slot, uint32_t line) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t interface = run.get(receiver + 0x0c);
    uint32_t error = run.call(run.get(run.get(interface) + slot), 0, {interface, value});
    if (!diagnostic(run, slot == 0x44 ? error : uint32_t(error != 0), line))
        return 0;
    if (slot == 0x44) {
        // Voice +0x24 last successfully applied frequency.
        run.put(receiver + 0x24, value);
    }
    return 1;
}

// 0x4b5210. Receiver head/tail; node next/previous at +0/+4.
void insert(Run &run, uint32_t receiver, uint32_t node) {
    run.put(node, run.get(receiver));
    run.put(node + 0x04, 0);
    uint32_t head = run.get(receiver);
    if (head) {
        run.put(head + 0x04, node);
    } else {
        run.put(receiver + 0x04, node);
    }
    run.put(receiver, node);
}

// 0x4b5270. Reload link fields after each store for aliased lists.
void remove(Run &run, uint32_t receiver, uint32_t node) {
    uint32_t previous = run.get(node + 0x04);
    if (previous) {
        run.put(previous, run.get(node));
    } else {
        run.put(receiver, run.get(node));
    }
    uint32_t next = run.get(node);
    if (next) {
        run.put(next + 0x04, run.get(node + 0x04));
    } else {
        run.put(receiver + 0x04, run.get(node + 0x04));
    }
}

void destroy(Run &run, uint32_t list, uint32_t object) {
    remove(run, list, object + 0x04);
    run.put(object, 0x513518);
    run.call(0x4f6428, 0, {object});
}

// Real constructed fade vtables name owned game code, never physical fixtures.
uint32_t nodeCall(Run &run, uint32_t object, uint32_t slot, int32_t displacement,
                  std::initializer_list<uint32_t> arguments = {}) {
    uint32_t target = run.get(run.get(object) + slot);
    if (owned(target) >= 0)
        return child(run, target, object, displacement, arguments);
    return run.call(target, object, arguments);
}

// 0x4b3bf0.
uint32_t function_4b3bf0(Run &run, uint32_t, const uint32_t *arguments) {
    if (!arguments[0])
        return 100;
    uint32_t input = arguments[0];
    uint32_t magnitude = s32(input) < 0 ? 0u - input : input;
    uint32_t quotient = uint32_t(s32(magnitude) / 100);
    ClawX87State state{};
    state.size = sizeof(state);
    state.version = CLAW_X87_VERSION;
    state.control = 0x023f;
    // The signed quotient is exactly representable in the original double local.
    run.x87_step(CLAW_X87_I32, state, {quotient});
    run.x87_step(CLAW_X87_POP, state);
    run.x87_step(CLAW_X87_F64, state, {run.get(0x513500), run.get(0x513504)});
    run.x87_step(CLAW_X87_I32, state, {quotient});
    run.x87_step(CLAW_X87_CHS, state);
    run.x87_step(CLAW_X87_DIV_F64, state, {run.get(0x5134f8), run.get(0x5134fc)});
    state.popCount = 2;
    state.pushCount = 1;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    run.call_x87_exact(0x4f1b30, 0, state);
    run.x87_step(CLAW_X87_SUBR_F64, state, {run.get(0x5134f0), run.get(0x5134f4)});
    run.x87_step(CLAW_X87_MUL_F64, state, {run.get(0x5134e8), run.get(0x5134ec)});
    run.x87_step(CLAW_X87_SUBR_F64, state, {run.get(0x5134e8), run.get(0x5134ec)});
    run.x87_step(CLAW_X87_ROUND_F64, state);
    if (s32(input) >= 0)
        run.x87_step(CLAW_X87_CHS, state);
    state.popCount = 1;
    state.pushCount = 0;
    state.returned = 0;
    state.eax = 0;
    state.edx = 0;
    return run.call_x87_exact(0x4a30e0, 0, state);
}

// 0x4b3d80.
uint32_t function_4b3d80(Run &run, uint32_t receiver, const uint32_t *) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t interface = run.get(receiver + 0x0c);
    // Voice +0x14 playback flags.
    uint32_t flags = run.get(receiver + 0x14);
    uint32_t error = run.call(run.get(run.get(interface) + 0x30), 0, {interface, 0, 0, flags});
    return diagnostic(run, error != 0, 0x5f);
}

// 0x4b3dc0.
uint32_t function_4b3dc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t result = 1;
    if (!child(run, 0x4b3f40, receiver, -16, {arguments[0]}))
        result = 0;
    if (!child(run, 0x4b4110, receiver, -16, {arguments[1]}))
        result = 0;
    if (!child(run, 0x4b41b0, receiver, -16, {arguments[2]}))
        result = 0;
    child(run, 0x4b3ec0, receiver, -16, {arguments[3]});
    if (!child(run, 0x4b3d80, receiver, -12))
        result = 0;
    return result;
}

// 0x4b3e30.
uint32_t function_4b3e30(Run &run, uint32_t receiver, const uint32_t *) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t interface = run.get(receiver + 0x0c);
    uint32_t error = run.call(run.get(run.get(interface) + 0x48), 0, {interface});
    return diagnostic(run, error != 0, 0x7a);
}

// 0x4b3e70.
uint32_t function_4b3e70(Run &run, uint32_t receiver, const uint32_t *) {
    return getter(run, receiver, 0x24, 0x88, true);
}

// 0x4b3ec0.
uint32_t function_4b3ec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (enabled(run, receiver)) {
        uint32_t flags = run.get(receiver + 0x14);
        run.put(receiver + 0x14, arguments[0] ? flags | 1u : flags & ~1u);
    }
    return 0;
}

// 0x4b3ef0.
uint32_t function_4b3ef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return setter(run, receiver, arguments[0], 0x3c, 0xaf);
}

// 0x4b3f40.
uint32_t function_4b3f40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!enabled(run, receiver))
        return 0;
    return child(run, 0x4b3ef0, receiver, -8, {run.get(0x541178 + arguments[0] * 4u)});
}

// 0x4b3f70.
uint32_t function_4b3f70(Run &run, uint32_t receiver, const uint32_t *) {
    return getter(run, receiver, 0x18, 0xc7, false);
}

// 0x4b3fc0.
uint32_t function_4b3fc0(Run &run, uint32_t receiver, const uint32_t *) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t volume = child(run, 0x4b3f70, receiver, -4);
    return child(run, 0x4b3bf0, 0, -8, {volume});
}

// 0x4b3fe0.
uint32_t function_4b3fe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!enabled(run, receiver))
        return 0;
    child(run, 0x4b4c80, run.get(receiver + 0x10) + 0x0c, -36, {receiver, 1});
    uint32_t duration = arguments[1];
    if (!duration) {
        child(run, 0x4b3f40, receiver, -32, {arguments[0]});
        return 1;
    }
    uint32_t object = run.call(0x4f63ec, 0, {0x28});
    if (!object)
        return 0;
    uint32_t initial = child(run, 0x4b3fc0, receiver, -40);
    uint32_t constructed = child(run, 0x4b4d00, object, -48, {arguments[0], initial, duration, receiver, arguments[2]});
    if (!constructed)
        return 0;
    insert(run, run.get(receiver + 0x10) + 0x0c, constructed + 0x04);
    return 1;
}

// 0x4b40c0.
uint32_t function_4b40c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return setter(run, receiver, arguments[0], 0x40, 0xf6);
}

// 0x4b4110.
uint32_t function_4b4110(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!enabled(run, receiver))
        return 0;
    uint32_t pan = arguments[0];
    uint32_t value = s32(pan) < 0 ? run.get(0x541308 + pan * 4u) : 0u - run.get(0x541308 - pan * 4u);
    return child(run, 0x4b40c0, receiver, -8, {value});
}

// 0x4b4160.
uint32_t function_4b4160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return setter(run, receiver, arguments[0], 0x44, 0x12a);
}

// 0x4b41b0.
uint32_t function_4b41b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!enabled(run, receiver))
        return 0;
    // Voice +0x18 base frequency.
    uint32_t base = run.get(receiver + 0x18);
    uint32_t frequency = uint32_t(s32(arguments[0] * base) / 100) + base;
    if (frequency >= 100000u)
        frequency = 99999u;
    if (frequency <= 100u)
        frequency = 101u;
    return child(run, 0x4b4160, receiver, -12, {frequency});
}

// 0x4b4b80.
uint32_t function_4b4b80(Run &run, uint32_t receiver, const uint32_t *) {
    // Manager +0x0c list head; +0x7c last update time.
    uint32_t head = run.get(receiver + 0x0c);
    uint32_t object = head ? head - 4u : 0;
    if (!object)
        return 0;
    uint32_t now = run.icall(0x546df0);
    if (now <= run.get(receiver + 0x7c))
        return 1;
    run.put(receiver + 0x7c, now);
    do {
        uint32_t nextLink = run.get(object + 0x04);
        uint32_t next = nextLink ? nextLink - 4u : 0;
        if (!nodeCall(run, object, 0x00, -28, {now}))
            destroy(run, receiver + 0x0c, object);
        object = next;
    } while (object);
    return 1;
}

// 0x4b4c10.
uint32_t function_4b4c10(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t head = run.get(receiver + 0x0c);
    uint32_t object = head ? head - 4u : 0;
    while (object) {
        uint32_t nextLink = run.get(object + 0x04);
        uint32_t next = nextLink ? nextLink - 4u : 0;
        nodeCall(run, object, 0x04, -20);
        destroy(run, receiver + 0x0c, object);
        object = next;
    }
    return 1;
}

// 0x4b4c80.
uint32_t function_4b4c80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t head = run.get(receiver);
    uint32_t object = head ? head - 4u : 0;
    while (object) {
        uint32_t nextLink = run.get(object + 0x04);
        uint32_t next = nextLink ? nextLink - 4u : 0;
        // Generic node +0x0c type and +0x10 associated voice.
        if (arguments[1] != 0xffff && run.get(object + 0x0c) != arguments[1])
            continue;
        if (run.get(object + 0x10) == arguments[0])
            destroy(run, receiver, object);
        object = next;
    }
    return 0;
}

// 0x4b4d00.
uint32_t function_4b4d00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x0c, 1);
    run.put(receiver + 0x10, arguments[3]);
    run.put(receiver + 0x14, arguments[4]);
    run.put(receiver, 0x513520);
    // Fade +0x18 target, +0x1c initial, +0x20 duration, +0x24 start tick.
    run.put(receiver + 0x18, arguments[0]);
    run.put(receiver + 0x1c, arguments[1]);
    run.put(receiver + 0x20, arguments[2]);
    run.put(receiver + 0x24, run.icall(0x546df0));
    return receiver;
}

// 0x4b4d80.
uint32_t function_4b4d80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t elapsed = arguments[0] - run.get(receiver + 0x24);
    uint32_t duration = run.get(receiver + 0x20);
    bool complete = elapsed >= duration;
    if (complete)
        elapsed = duration;
    uint32_t playing = child(run, 0x4b3e70, run.get(receiver + 0x10), -16);
    if (!playing) {
        complete = true;
    } else {
        uint32_t initial = run.get(receiver + 0x1c);
        uint32_t target = run.get(receiver + 0x18);
        uint32_t product = (target - initial) * elapsed;
        uint32_t value = uint32_t(s32(product) / run.gets(receiver + 0x20)) + initial;
        child(run, 0x4b3f40, run.get(receiver + 0x10), -20, {value});
    }
    if (complete && run.get(receiver + 0x14))
        child(run, 0x4b3e30, run.get(receiver + 0x10), -16);
    return !complete;
}

// 0x4b4df0.
uint32_t function_4b4df0(Run &run, uint32_t receiver, const uint32_t *) {
    if (child(run, 0x4b3e70, run.get(receiver + 0x10), -8)) {
        if (run.get(receiver + 0x14)) {
            child(run, 0x4b3e30, run.get(receiver + 0x10), -8);
        } else {
            uint32_t target = run.get(receiver + 0x18);
            child(run, 0x4b3f40, run.get(receiver + 0x10), -12, {target});
        }
    }
    return 1;
}

// 0x4b5210.
uint32_t function_4b5210(Run &run, uint32_t receiver, const uint32_t *arguments) {
    insert(run, receiver, arguments[0]);
    return 0;
}

// 0x4b5270.
uint32_t function_4b5270(Run &run, uint32_t receiver, const uint32_t *arguments) {
    remove(run, receiver, arguments[0]);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b3bf0:
        return function_4b3bf0(run, receiver, arguments);
    case 0x4b3d80:
        return function_4b3d80(run, receiver, arguments);
    case 0x4b3dc0:
        return function_4b3dc0(run, receiver, arguments);
    case 0x4b3e30:
        return function_4b3e30(run, receiver, arguments);
    case 0x4b3e70:
        return function_4b3e70(run, receiver, arguments);
    case 0x4b3ec0:
        return function_4b3ec0(run, receiver, arguments);
    case 0x4b3ef0:
        return function_4b3ef0(run, receiver, arguments);
    case 0x4b3f40:
        return function_4b3f40(run, receiver, arguments);
    case 0x4b3f70:
        return function_4b3f70(run, receiver, arguments);
    case 0x4b3fc0:
        return function_4b3fc0(run, receiver, arguments);
    case 0x4b3fe0:
        return function_4b3fe0(run, receiver, arguments);
    case 0x4b40c0:
        return function_4b40c0(run, receiver, arguments);
    case 0x4b4110:
        return function_4b4110(run, receiver, arguments);
    case 0x4b4160:
        return function_4b4160(run, receiver, arguments);
    case 0x4b41b0:
        return function_4b41b0(run, receiver, arguments);
    case 0x4b4b80:
        return function_4b4b80(run, receiver, arguments);
    case 0x4b4c10:
        return function_4b4c10(run, receiver, arguments);
    case 0x4b4c80:
        return function_4b4c80(run, receiver, arguments);
    case 0x4b4d00:
        return function_4b4d00(run, receiver, arguments);
    case 0x4b4d80:
        return function_4b4d80(run, receiver, arguments);
    case 0x4b4df0:
        return function_4b4df0(run, receiver, arguments);
    case 0x4b5210:
        return function_4b5210(run, receiver, arguments);
    case 0x4b5270:
        return function_4b5270(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_ambient_audio_backend_entry, owned, body)
