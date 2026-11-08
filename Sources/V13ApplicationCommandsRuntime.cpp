// v1.3 application commands, state transitions and orderly quit requests.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x427d10:
        return 3;
    case 0x428d70:
        return 4;
    case 0x4498f0:
    case 0x46df80:
    case 0x42c380:
        return 0;
    default:
        return -1;
    }
}

struct LocalFrame {
    Run &run;
    uint32_t stack;
    LocalFrame(Run &run, uint32_t bytes) : run(run), stack(run.stackPointer) {
        run.stackPointer = run.frame - bytes;
    }
    ~LocalFrame() {
        run.stackPointer = stack;
    }
};

uint32_t call(Run &run, uint32_t function, uint32_t receiver,
              std::initializer_list<uint32_t> arguments = {}) {
    uint32_t stack = run.stackPointer;
    run.stackPointer = stack - 4 * (uint32_t(arguments.size()) + 1);
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = stack;
    return result;
}

uint32_t icall(Run &run, uint32_t slot, std::initializer_list<uint32_t> arguments = {}) {
    return call(run, slot, 0, arguments);
}

uint32_t vcall(Run &run, uint32_t object, uint32_t slot,
               std::initializer_list<uint32_t> arguments = {}) {
    return call(run, run.get(run.get(object) + slot), object, arguments);
}

template <class F> uint32_t nested(Run &run, uint32_t argc, F function) {
    uint32_t frame = run.frame;
    uint32_t stack = run.stackPointer;
    run.frame = stack - 4 * (argc + 1);
    uint32_t result = function();
    run.frame = frame;
    run.stackPointer = stack;
    return result;
}

// 0x42c380. Application +0xa4 is the shutdown latch; +4 is the window
// owner, and +8 is the active engine with its +0x244 run flag.
uint32_t closeRequest(Run &run, uint32_t app) {
    LocalFrame frame(run, 0);
    if (!run.get(app + 0xa4)) {
        uint32_t engine = run.get(app + 0x08);
        run.put(app + 0xa4, 1);
        if (engine) {
            run.put(engine + 0x244, 0);
        }
        uint32_t window = run.get(app + 0x04);
        if (window) {
            icall(run, 0x50c4cc, {run.get(window + 0x04), 0x10, 0, 0});
        }
    }
    return 0;
}

// 0x4498f0. Statistics are assembled in a private stack buffer, with the
// original bounded fourteen-level walk and unsigned millisecond conversion.
uint32_t quitStatistics(Run &run) {
    LocalFrame frame(run, 0x218);
    uint32_t app = run.get(0x535910);
    if (!app || !run.get(0x5365d8) || !run.get(app + 0x9c)) return 0;
    uint32_t profile = run.get(app + 0x64);
    if (!profile) return 0;
    uint32_t state = call(run, 0x42db90, app);
    if (!state) state = run.get(0x5365d8);
    if (!state) return 0;
    uint32_t level = run.get(state + 0x14);
    if (!run.get(0x5365d4)) return 0;
    uint32_t complete = run.get(state + 0x25c);
    if (complete) ++level;
    uint32_t index = 1;
    uint32_t output = 2;
    uint32_t buffer = run.automatic(-0x200);
    if (s32(level) > 1) {
        profile += 0x1874;
        uint32_t offset = 0;
        while (s32(index) < s32(level)) {
            if (s32(offset) < -4 || s32(offset) >= 0x38 || !profile) return 0;
            run.put(buffer + output * 4, run.get(profile + 0x08) / 1000);
            run.put(buffer + (output + 1) * 4, run.get(0x5357a4 + offset) / 1000);
            run.put(buffer + (output + 2) * 4, run.get(0x5357e0 + offset));
            output += 12;
            profile += 0xb0;
            ++index;
            offset += 4;
        }
    }
    if (!complete && run.get(run.get(run.get(0x5365d4) + 0x7c) + 0x14)) {
        run.put(buffer + output * 4, run.get(0x535928) / 1000);
        run.put(buffer + (output + 1) * 4, run.get(0x5357a0 + index * 4) / 1000);
        run.put(buffer + (output + 2) * 4, run.get(0x5357dc + index * 4));
    }
    return 0;
}

// 0x46df80. State +0xc points to its application/service owner;
// +0x168 bit zero chooses the exit message layer. The deadline uses uint32 wrap.
uint32_t exitMessage(Run &run, uint32_t state) {
    LocalFrame frame(run, 0x0c);
    uint32_t layer = (run.get8(state + 0x168) & 1) ? 3 : 4;
    uint32_t message = call(run, 0x4c9480, run.get(run.get(state + 0x0c) + 0x08),
                                {layer, 0, 0, 99999, 0x520634, 0x200000});
    uint32_t app = run.get(state + 0x0c);
    call(run, 0x4cc640, run.get(app + 0x24),
             {run.get(run.get(app + 0x04) + 0x14), run.get(app + 0x08)});
    app = run.get(state + 0x0c);
    uint32_t display = run.get(app + 0x04);
    vcall(run, run.get(app + 0x0c), 0x2c, {run.get(display + 0x14), run.get(display + 0x18)});
    if (message) {
        call(run, 0x46fd50, state);
        vcall(run, message, 0x24, {run.get(run.get(run.get(state + 0x0c) + 0x04) + 0x14)});
    }
    uint32_t device = run.get(run.get(run.get(run.get(state + 0x0c) + 0x04) + 0x10) + 0x2c);
    call(run, 0x4ba320, device, {0});
    uint32_t deadline = icall(run, 0x50c58c) + 4000;
    uint32_t now = icall(run, 0x50c58c);
    run.stackPointer += 8;
    if (now < deadline) {
        call(run, 0x4b9380, 0, {deadline - now});
    }
    return 1;
}

// 0x428d70. Application +0x2c is current state, +0xb0 temporarily
// selects the developer route, and +0xa4 selects the minimal shutdown state.
uint32_t transition(Run &run, uint32_t app, uint32_t requested, uint32_t initialize,
                    uint32_t suspend, uint32_t payload) {
    LocalFrame frame(run, 0x0c);
    if (requested == 13 && run.get(0x535978)) {
        run.put(app + 0xb0, 1);
        uint32_t result = call(run, 0x42f0d0, app, {payload});
        run.put(app + 0xb0, 0);
        return result != 0;
    }
    uint32_t previous = 0;
    uint32_t state = run.get(app + 0x2c);
    if (state) {
        previous = vcall(run, state, 0x10);
        vcall(run, run.get(app + 0x2c), 0x28, {requested});
        state = run.get(app + 0x2c);
        if (!suspend) {
            if (state) vcall(run, state, 0x00, {1});
            run.put(app + 0x2c, 0);
            call(run, 0x42dc20, app);
            run.put(app + 0x2c, 0);
        } else {
            call(run, 0x42dbb0, app, {state});
            run.put(app + 0x2c, 0);
        }
    } else if (!suspend) {
        call(run, 0x42dc20, app);
    }
    if (run.get(app + 0xa4)) {
        state = call(run, 0x4fcaea, 0, {0x154});
        if (state) {
            run.put(state, 0x50cc74);
            run.put(state + 0x04, 0);
            run.put(state + 0x08, 0);
            run.put(state + 0x0c, 0);
            run.put(state + 0x1c, 0);
            run.put(state + 0x20, 0);
            run.put(state + 0x24, 0);
            run.put(state + 0x2c, 0);
            run.put(state + 0x30, 0);
            run.put(state + 0x3c, 0);
            run.put(state + 0x40, 0);
            run.put(state + 0x34, 0);
            run.put8(state + 0x4c, 0);
            run.put(state + 0x18, 0);
            run.put(state + 0x150, 0);
        }
        run.put(app + 0x2c, state);
        return 1;
    }
    run.stackPointer -= 4;
    uint32_t bytes = 0;
    switch (requested) {
    case 2:
        bytes = 0x158;
        break;
    case 3:
        bytes = 0x778;
        break;
    case 4:
        bytes = 0xc1c;
        break;
    case 5:
        bytes = 0x2c0;
        break;
    case 8:
        bytes = 0x1b8;
        break;
    case 9:
        bytes = 0x158;
        break;
    case 10:
        bytes = 0x160;
        break;
    case 11:
        bytes = 0x2c8;
        break;
    case 12:
        bytes = 0x33c;
        break;
    case 13:
        bytes = 0x17c;
        break;
    case 14:
        bytes = 0x15c;
        break;
    default: break;
    }
    if (bytes) {
        state = call(run, 0x4fcaea, 0, {bytes});
        if (state) {
            if (requested == 4) {
                state = call(run, 0x476b70, state);
            } else if (requested == 14) {
                state = call(run, 0x429760, state);
            } else {
                call(run, 0x40bbf0, state);
                switch (requested) {
                case 2:
                    run.put(state, 0x50db40);
                    break;
                case 3:
                    run.put(state + 0x250, run.get(0x52c668));
                    run.put(state, 0x50dacc);
                    run.put(state + 0x154, 1);
                    run.put(state + 0x258, 0);
                    run.put(state + 0x25c, 0);
                    run.put(state + 0x764, 0);
                    run.put(state + 0x768, 0);
                    run.put(state + 0x76c, 0);
                    run.put(state + 0x770, 0);
                    run.put(state + 0x774, 0);
                    break;
                case 5:
                    call(run, 0x4df8d0, state + 0x154, {0x280, 0x1e0});
                    run.put(state + 0x154, 0x50daa0);
                    call(run, 0x4fc3da, state + 0x2a4, {10});
                    run.put(state, 0x50da44);
                    run.put(state + 0x254, 0);
                    run.put(state + 0x258, 0);
                    run.put(state + 0x25c, 0);
                    run.put(state + 0x264, 0);
                    run.put(state + 0x260, 0);
                    run.put(state + 0x268, 0);
                    run.put(state + 0x26c, 0);
                    run.put(state + 0x270, 0);
                    run.put(state + 0x28c, 0);
                    run.put(state + 0x290, 0);
                    run.put(state + 0x294, 0);
                    run.put(state + 0x2a0, 1000);
                    run.put(state + 0x298, 0);
                    run.put(state + 0x29c, 0);
                    run.put(state + 0x284, 0);
                    run.put(state + 0x288, 0);
                    call(run, 0x40b2e0, state + 0x274, {0x1e0, 0, 0x280, 0});
                    break;
                case 8:
                    call(run, 0x4295d0, state + 0x188);
                    run.put(state + 0x188, 0x50da34);
                    run.put(state + 0x190, run.get(0x52c668));
                    run.put(state + 0x198, 0);
                    run.put(state + 0x1a0, 0);
                    run.put(state, 0x50d9d8);
                    run.put(state + 0x158, 0);
                    run.put(state + 0x15c, 0);
                    run.put(state + 0x160, 0);
                    run.put(state + 0x164, 0);
                    run.put(state + 0x194, 0);
                    run.put(state + 0x19c, 0);
                    run.put(state + 0x1a4, 0);
                    call(run, 0x40b2e0, state + 0x168, {0, 0, 0x280, 0x1e0});
                    call(run, 0x40b2e0, state + 0x178, {0, 0, 0x280, 0x1e0});
                    run.put(state + 0x1ac, 1);
                    run.put(state + 0x1b0, 0);
                    run.put(state + 0x1a8, 0);
                    run.put(state + 0x154, 0);
                    break;
                case 9:
                    run.put(state, 0x50d97c);
                    break;
                case 10:
                    run.put(state, 0x50d920);
                    run.put(state + 0x158, 0);
                    run.put(state + 0x154, 0);
                    run.put(state + 0x15c, 10);
                    break;
                case 11:
                    call(run, 0x429670, state + 0x154);
                    call(run, 0x4fc3da, state + 0x2ac, {10});
                    run.put(state, 0x50d8c4);
                    run.put(state + 0x250, 0);
                    run.put(state + 0x254, 0);
                    run.put(state + 0x258, 0);
                    run.put(state + 0x268, 0);
                    run.put(state + 0x25c, 0);
                    run.put(state + 0x260, 0);
                    run.put(state + 0x264, 0);
                    run.put(state + 0x26c, 0);
                    run.put(state + 0x290, 0);
                    run.put(state + 0x294, 0);
                    run.put(state + 0x29c, 1000);
                    run.put(state + 0x298, 0);
                    run.put(state + 0x2a0, 0);
                    run.put(state + 0x2a4, 0);
                    run.put(state + 0x2a8, 0);
                    icall(run, 0x50c4d8, {state + 0x270, 0xa0, 0x78, 0x1e0, 0x168});
                    run.put(state + 0x280, 0);
                    run.put(state + 0x284, 0);
                    run.put(state + 0x288, 0);
                    run.put(state + 0x28c, 0);
                    break;
                case 12:
                    call(run, 0x4296f0, state + 0x154);
                    call(run, 0x4fc3da, state + 0x29c, {10});
                    run.put(state, 0x50d868);
                    run.put(state + 0x24c, 0);
                    run.put(state + 0x250, 0);
                    run.put(state + 0x254, 0);
                    run.put(state + 0x258, 0);
                    run.put(state + 0x25c, 0);
                    run.put(state + 0x294, 0x280);
                    run.put(state + 0x298, 0x1e0);
                    run.put(state + 0x260, 0);
                    run.put(state + 0x274, 0);
                    run.put(state + 0x278, 0);
                    run.put(state + 0x27c, 1000);
                    run.put(state + 0x280, 1000);
                    run.put(state + 0x284, 1000);
                    run.put(state + 0x288, 10);
                    run.put(state + 0x28c, 0);
                    run.put(state + 0x290, 0);
                    call(run, 0x40b2e0, state + 0x264, {0xa0, 0x78, 0x1e0, 0x168});
                    break;
                case 13:
                    run.put(state, 0x50d80c);
                    run.put(state + 0x158, payload);
                    run.put(state + 0x15c, 0);
                    run.put(state + 0x160, 0);
                    run.put(state + 0x164, 0);
                    run.put(state + 0x154, 0);
                    run.put(state + 0x168, 0);
                    run.put(state + 0x16c, 1000);
                    run.put(state + 0x170, 0);
                    run.put(state + 0x174, 0);
                    run.put(state + 0x178, 0);
                    break;
                default: break;
                }
            }
        }
        run.put(app + 0x2c, state);
    }
    run.stackPointer += 4;
    state = run.get(app + 0x2c);
    if (!state) {
        run.put(run.get(app + 0x08) + 0x244, 0);
        return 0;
    }
    call(run, 0x42c3c0, app);
    uint32_t result = vcall(run, run.get(app + 0x2c), 0x04, {app, initialize, previous});
    state = run.get(app + 0x2c);
    if (!result) {
        if (state) vcall(run, state, 0x00, {1});
        run.put(app + 0x2c, 0);
        return 0;
    }
    vcall(run, state, 0x24, {previous});
    run.put(run.get(app + 0x08) + 0x244, 1);
    call(run, 0x432b50, run.get(0x535918));
    run.put(run.get(0x535918) + 0x0c, 0xffffffff);
    call(run, 0x4b3150, run.get(0x535914));
    run.put(run.get(0x535914) + 0x20c, 0xffffffff);
    call(run, 0x42c3c0, app);
    return 1;
}

uint32_t transitionNested(Run &run, uint32_t app, uint32_t requested,
                          uint32_t initialize, uint32_t suspend, uint32_t payload) {
    return nested(run, 4, [&] {
        return transition(run, app, requested, initialize, suspend, payload);
    });
}

uint32_t quitStatisticsNested(Run &run) {
    return nested(run, 0, [&] {
        return quitStatistics(run);
    });
}

uint32_t exitMessageNested(Run &run, uint32_t state) {
    return nested(run, 0, [&] {
        return exitMessage(run, state);
    });
}

uint32_t closeRequestNested(Run &run, uint32_t app) {
    return nested(run, 0, [&] {
        return closeRequest(run, app);
    });
}

uint32_t stateId(Run &run, uint32_t app) {
    return vcall(run, run.get(app + 0x2c), 0x10);
}

void applicationError(Run &run, uint32_t app, uint32_t resource, uint32_t command = 0x8005) {
    call(run, 0x429b30, app, {command, resource});
}

// 0x427d10. Complete application command switch; first incoming word
// is unused, command is second, and payload is third.
uint32_t applicationCommand(Run &run, uint32_t app, uint32_t command, uint32_t payload) {
    LocalFrame frame(run, 0x110);
    switch (command) {
    case 0x8005:
    case 0x8024:
        if (stateId(run, app) != 2 && stateId(run, app) != 5 && stateId(run, app) != 13) break;
        if (!call(run, 0x429890, app, {1})) applicationError(run, app, 0x3f5);
        break;
    case 0x8006:
    quit:
        if (!run.get(app + 0x9c)) {
            run.put(run.get(app + 0x2c) + 0x38, 1);
            if (!transitionNested(run, app, 5, 1, 0, 0)) applicationError(run, app, 0x3fc);
        } else if (!run.get(0x523580)) {
            quitStatisticsNested(run);
            {
                uint32_t state = run.get(app + 0x2c);
                if (state && vcall(run, state, 0x10) == 3) exitMessageNested(run, state);
            }
            closeRequestNested(run, app);
        } else {
            run.put(0x523580, run.get(0x523580) - 1);
            if (!transitionNested(run, app, 12, 1, 1, 0)) applicationError(run, app, 0x6ad);
        }
        break;
    case 0x8007:
        if (stateId(run, app) == 3) {
            uint32_t mode = run.get(app + 0x0c) ^ 1;
            run.put(app + 0x0c, mode);
            call(run, 0x42a280, app, {mode});
        }
        break;
    case 0x8008:
        closeRequestNested(run, app);
        break;
    case 0x8009:
        if (run.get(app + 0x30)) {
            uint32_t sound = run.get(run.get(run.get(app + 0x30) + 0x28) + 0x2c);
            if (sound) call(run, 0x4b48c0, sound);
            uint32_t enabled = run.get(app + 0x10) ^ 1;
            run.put(app + 0x10, enabled);
            run.put(0x53098c, enabled);
            if (run.get(app + 0x10)) call(run, 0x402560, run.get(app + 0x5c));
            else call(run, 0x402510, run.get(app + 0x5c));
        }
        break;
    case 0x800a:
        if (!run.get(app + 0x0c)) {
            uint32_t enabled = run.get(app + 0x14) ^ 1;
            run.put(app + 0x14, enabled);
            if (call(run, 0x42a340, app) || stateId(run, app) == 11 || stateId(run, app) == 5) {
                if (enabled) call(run, 0x4b4f50, run.get(app + 0x50), {1});
                else call(run, 0x4b4f80, run.get(app + 0x50));
            }
        }
        break;
    case 0x800d:
        if (!call(run, 0x429890, app, {1})) applicationError(run, app, 0x3f6);
        break;
    case 0x800e:
        if (call(run, 0x42a340, app) && !vcall(run, run.get(app + 0x2c), 0x40)) {
            icall(run, 0x50c4c4, {run.get(run.get(app + 0x04) + 0x04), 0x111, 0x8023, 0});
        }
        break;
    case 0x800f:
        if (stateId(run, app) == 3 || stateId(run, app) == 4) call(run, 0x4299d0, app);
        else goto quit;
        break;
    case 0x801b:
        if (call(run, 0x42c7e0, app)) call(run, 0x429b90, app);
        break;
    case 0x801c:
        if (call(run, 0x42c7e0, app)) call(run, 0x429b50, app);
        break;
    case 0x8021:
        if (stateId(run, app) != 2 && stateId(run, app) != 5 && stateId(run, app) != 10) break;
        if (!transitionNested(run, app, 8, 1, 0, 0) && !transitionNested(run, app, 5, 1, 0, 0)) applicationError(run, app, 0x3f9);
        break;
    case 0x8022:
    case 0x8026:
        if (stateId(run, app) == 2 || stateId(run, app) == 5) {
            uint32_t sound = run.get(run.get(app + 0x30) + 0x28);
            if (!run.get(sound + 0x30)) {
                uint32_t value = run.automatic(-0x104);
                run.put(value, 0);
                call(run, 0x4fc6b4, sound + 0x10, {0x52398c, value});
                if (run.get(value)) call(run, 0x421bb0, run.get(value), {run.get(0x530990), 0, 0, 0});
            }
        }
        break;
    case 0x8023:
        if (!transitionNested(run, app, 5, 1, 0, 0)) applicationError(run, app, 0x3f7);
        break;
    case 0x8025:
        if (stateId(run, app) != 2 && stateId(run, app) != 5) break;
        if (!transitionNested(run, app, 4, 1, 0, 0) && !transitionNested(run, app, 5, 1, 0, 0)) applicationError(run, app, 0x3fe);
        break;
    case 0x8027:
        if (!transitionNested(run, app, 2, 1, 0, 0)) applicationError(run, app, 0x3fa);
        break;
    case 0x802a:
        if (call(run, 0x42c7e0, app)) call(run, 0x429f80, app);
        break;
    case 0x802b:
        if (call(run, 0x42c7e0, app)) call(run, 0x42a070, app);
        break;
    case 0x802c:
        if (call(run, 0x42c7e0, app)) call(run, 0x429d20, app, {1});
        break;
    case 0x8035:
        if (stateId(run, app) == 9 || stateId(run, app) == 13 || stateId(run, app) == 15 ||
            stateId(run, app) == 14 || stateId(run, app) == 8) break;
        if (!transitionNested(run, app, 9, 1, 1, 0)) applicationError(run, app, 0x3ff);
        break;
    case 0x8036:
        if (!call(run, 0x4297e0, app)) applicationError(run, app, 0x3f8);
        break;
    case 0x8038:
        if (stateId(run, app) == 5 || stateId(run, app) == 2) {
            while (s32(icall(run, 0x50c4d0, {1})) < 0) {}
            call(run, 0x42a6c0, app, {0x523994});
        }
        break;
    case 0x8039:
        if (stateId(run, app) == 5) call(run, 0x42d560, app);
        break;
    case 0x803a:
        if (call(run, 0x42a340, app) && !call(run, 0x46e0d0, run.get(app + 0x2c))) applicationError(run, app, 0x3fb);
        break;
    case 0x803c:
        if (stateId(run, app) == 4) call(run, 0x489c60, 0);
        break;
    case 0x803d:
        if (stateId(run, app) == 4) call(run, 0x489da0, 0);
        break;
    case 0x8041:
        call(run, 0x42a820, app);
        break;
    case 0x8042:
        if (!call(run, 0x42a340, app)) icall(run, 0x50c4cc, {run.get(run.get(app + 0x04) + 0x04), 0x111, 0x8090, 2});
        break;
    case 0x8050:
    case 0x8051:
    case 0x8052:
    case 0x8053:
    case 0x8054:
    case 0x8055:
    case 0x8056:
        if (run.get(app + 0x2c) && stateId(run, app) == 4 && run.get(app + 0x64)) {
            uint32_t value = run.automatic(-0x104);
            call(run, 0x4fce17, value, {run.get(app + 0x64) + 0xe0 + (command - 0x8050) * 0x48});
            uint32_t text = run.get(value);
            if (run.get(text - 0x08)) {
                uint32_t size = 0;
                do {
                    ++size;
                } while (run.get8(text + size - 1));
                uint32_t copy = run.automatic(-0x100);
                uint32_t i = 0;
                for (; i + 4 <= size; i += 4) {
                    run.put(copy + i, run.get(text + i));
                }
                for (; i < size; ++i) {
                    run.put8(copy + i, run.get8(text + i));
                }
                call(run, 0x47bba0, run.get(app + 0x2c), {copy, 0, 1, 1});
            }
            call(run, 0x4fcda9, value);
        }
        break;
    case 0x8059:
        call(run, 0x42a880, app);
        break;
    case 0x805c:
        if (call(run, 0x42a340, app)) vcall(run, run.get(app + 0x2c), 0x5c);
        break;
    case 0x8062:
        run.put(app + 0x98, 0);
        icall(run, 0x50c4cc, {run.get(run.get(app + 0x04) + 0x04), 0x111, 0x8025, 0});
        break;
    case 0x8063:
        if (call(run, 0x42a340, app) && run.get(0x5365d4)) call(run, 0x420820, 0, {run.get(0x5365d4)});
        break;
    case 0x8070:
        call(run, 0x499530, 0, {run.get(app + 0x38), app});
        break;
    case 0x8075:
        if (!call(run, 0x429900, app)) applicationError(run, app, 0x6a7, 0x8007);
        break;
    case 0x807c:
        if (stateId(run, app) == 10 && !call(run, 0x40b990, run.get(app + 0x2c))) applicationError(run, app, 0x6a8);
        break;
    case 0x807d:
        break;
    case 0x807e:
        if (!call(run, 0x429890, app, {run.get(app + 0x154)})) {
            run.put(app + 0xac, 0);
            applicationError(run, app, 0x6ab);
        }
        break;
    case 0x807f:
        if (!call(run, 0x429890, app, {payload})) applicationError(run, app, 0x6ac);
        break;
    case 0x8080:
        if (!transitionNested(run, app, 11, 1, 1, 0)) applicationError(run, app, 0x6ad);
        break;
    case 0x8082:
        if (stateId(run, app) == 4) {
            run.put(0x52357c, run.get(0x52357c) ^ 1);
        }
        break;
    case 0x8083:
        if (stateId(run, app) == 4 && run.get(app + 0x4c) && run.get(run.get(app + 0x4c) + 0x0c)) {
            uint32_t value = run.automatic(-0x104);
            call(run, 0x4fb8fa, run.get(app + 0x4c), {value});
            call(run, 0x4fcda9, value);
        }
        break;
    case 0x8084:
        if (call(run, 0x42a340, app) && !call(run, 0x46e3a0, run.get(app + 0x2c))) applicationError(run, app, 0x3fb);
        break;
    case 0x8085:
        if (run.get(app + 0x2c) && stateId(run, app) == 4) call(run, 0x47dff0, run.get(app + 0x2c));
        break;
    case 0x8090:
        if (!transitionNested(run, app, 13, 1, 1, payload)) applicationError(run, app, 0x6ad);
        break;
    case 0x8095:
        call(run, 0x42ed10, app);
        break;
    case 0x80ab:
        if (!transitionNested(run, app, 14, 1, 0, 0)) applicationError(run, app, 0x3fa);
        break;
    case 0x80ac:
        if (!transitionNested(run, app, 15, 1, 0, 0)) applicationError(run, app, 0x44a);
        break;
    default:
        return call(run, 0x42a9b0, app, {command}) != 0;
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x427d10:
        return applicationCommand(run, receiver, arguments[1], arguments[2]);
    case 0x428d70:
        return transition(run, receiver, arguments[0], arguments[1], arguments[2], arguments[3]);
    case 0x4498f0:
        return quitStatistics(run);
    case 0x46df80:
        return exitMessage(run, receiver);
    case 0x42c380:
        return closeRequest(run, receiver);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_v13_application_commands_entry, owned, body)
