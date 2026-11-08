#include "ClawRuntime.hpp"

namespace {
using claw::Run;
int owned(uint32_t function) {
    return function == 0x428c40 ? 4 : -1;
}

// The inlined mode-5 constructor, shared by the original transition and native startup.
void menuConstructor(Run &run, uint32_t state) {
    run.call(0x40b5c0, state);
    run.call(0x4dcc40, state + 0x154, {640, 480});
    run.put(state + 0x154, 0x50c23c);
    run.call(0x4f5cbd, state + 0x2ac, {10});
    run.put(state, 0x50c1e4);
    run.put(state + 0x25c, 0);
    run.put(state + 0x260, 0);
    run.put(state + 0x264, 0);
    run.put(state + 0x26c, 0);
    run.put(state + 0x268, 0);
    run.put(state + 0x270, 0);
    run.put(state + 0x274, 0);
    run.put(state + 0x278, 0);
    run.put(state + 0x294, 0);
    run.put(state + 0x298, 0);
    run.put(state + 0x29c, 0);
    run.put(state + 0x2a8, 0x3e8);
    run.put(state + 0x2a0, 0);
    run.put(state + 0x2a4, 0);
    run.put(state + 0x28c, 0);
    run.put(state + 0x290, 0);
    run.icall(0x546d5c, {state + 0x27c, 480, 0, 640, 0});
}

// 0x428c40. Owner +0x2c is current state, +0xa0 bypass, +8 application.
uint32_t transition(Run &run, uint32_t owner, const uint32_t *args) {
    uint32_t previous = 0;
    if (run.get(owner + 0x2c)) {
        previous = run.vcall(run.get(owner + 0x2c), 0x10);
        run.vcall(run.get(owner + 0x2c), 0x28, {args[0]});
        if (args[2]) {
            run.call(0x42bff0, owner, {run.get(owner + 0x2c)});
        } else {
            uint32_t current = run.get(owner + 0x2c);
            if (current)
                run.vcall(current, 0, {1});
            run.call(0x42c060, owner);
        }
        run.put(owner + 0x2c, 0);
    } else if (!args[2]) {
        run.call(0x42c060, owner);
    }
    if (run.get(owner + 0xa0)) {
        uint32_t state = run.call(0x4f63ec, 0, {0x154});
        if (state) {
            run.put(state, 0x50b4ec);
            run.put(state + 0x4, 0);
            run.put(state + 0x8, 0);
            run.put(state + 0xc, 0);
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
        run.put(owner + 0x2c, state);
        return 1;
    }
    uint32_t state = 0;
    switch (args[0]) {
    case 2:
        state = run.call(0x4f63ec, 0, {0x158});
        if (state) {
            run.call(0x40b5c0, state);
            run.put(state, 0x50c2d4);
        }
        run.put(owner + 0x2c, state);
        break;
    case 3:
        state = run.call(0x4f63ec, 0, {0x778});
        if (state) {
            run.call(0x40b5c0, state);
            run.call(0x4f6439, state + 0x250);
            run.put(state, 0x50c264);
            run.put(state + 0x154, 1);
            run.put(state + 0x258, 0);
            run.put(state + 0x25c, 0);
            run.put(state + 0x764, 0);
            run.put(state + 0x768, 0);
            run.put(state + 0x76c, 0);
            run.put(state + 0x770, 0);
            run.put(state + 0x774, 0);
        }
        run.put(owner + 0x2c, state);
        break;
    case 4:
        state = run.call(0x4f63ec, 0, {0xc1c});
        if (state) {
            state = run.call(0x474fa0, state);
        }
        run.put(owner + 0x2c, state);
        break;
    case 5:
        state = run.call(0x4f63ec, 0, {0x2c8});
        if (state) {
            menuConstructor(run, state);
        }
        run.put(owner + 0x2c, state);
        break;
    case 8:
        state = run.call(0x4f63ec, 0, {0x1b8});
        if (state) {
            run.call(0x40b5c0, state);
            run.call(0x429710, state + 0x188);
            run.put(state + 0x188, 0x50c1cc);
            run.call(0x4f6439, state + 0x190);
            run.put(state + 0x198, 0);
            run.put(state + 0x1a0, 0);
            run.put(state, 0x50c174);
            run.put(state + 0x158, 0);
            run.put(state + 0x15c, 0);
            run.put(state + 0x160, 0);
            run.put(state + 0x164, 0);
            run.put(state + 0x194, 0);
            run.put(state + 0x19c, 0);
            run.put(state + 0x1a4, 0);
            run.call(0x4296f0, state + 0x168, {0, 0, 640, 480});
            run.call(0x4296f0, state + 0x178, {0, 0, 640, 480});
            run.put(state + 0x1ac, 1);
            run.put(state + 0x1b0, 0);
            run.put(state + 0x1a8, 0);
            run.put(state + 0x154, 0);
        }
        run.put(owner + 0x2c, state);
        break;
    case 9:
        state = run.call(0x4f63ec, 0, {0x158});
        if (state) {
            run.call(0x40b5c0, state);
            run.put(state, 0x50c11c);
        }
        run.put(owner + 0x2c, state);
        break;
    case 10:
        state = run.call(0x4f63ec, 0, {0x160});
        if (state) {
            run.call(0x40b5c0, state);
            run.put(state, 0x50c0c4);
            run.put(state + 0x158, 0);
            run.put(state + 0x154, 0);
            run.put(state + 0x15c, 0xa);
        }
        run.put(owner + 0x2c, state);
        break;
    case 11:
        state = run.call(0x4f63ec, 0, {0x2d0});
        if (state) {
            run.call(0x40b5c0, state);
            run.call(0x4dcc40, state + 0x154, {640, 480});
            run.put(state + 0x154, 0x50c09c);
            run.call(0x4f5cbd, state + 0x2b4, {10});
            run.put(state, 0x50c044);
            run.put(state + 0x258, 0);
            run.put(state + 0x25c, 0);
            run.put(state + 0x260, 0);
            run.put(state + 0x270, 0);
            run.put(state + 0x264, 0);
            run.put(state + 0x268, 0);
            run.put(state + 0x26c, 0);
            run.put(state + 0x274, 0);
            run.put(state + 0x298, 0);
            run.put(state + 0x29c, 0);
            run.put(state + 0x2a4, 0x3e8);
            run.put(state + 0x2a0, 0);
            run.put(state + 0x2a8, 0);
            run.put(state + 0x2ac, 0);
            run.put(state + 0x2b0, 0);
            run.call(0x4296f0, state + 0x278, {160, 120, 480, 360});
            run.put(state + 0x288, 0);
            run.put(state + 0x28c, 0);
            run.put(state + 0x290, 0);
            run.put(state + 0x294, 0);
        }
        run.put(owner + 0x2c, state);
        break;
    case 12:
        state = run.call(0x4f63ec, 0, {0x2c8});
        if (state) {
            run.call(0x40b5c0, state);
            run.call(0x429980, state + 0x154);
            run.call(0x4f5cbd, state + 0x2a4, {10});
            run.put(state, 0x50bfec);
            run.put(state + 0x254, 0);
            run.put(state + 0x258, 0);
            run.put(state + 0x25c, 0);
            run.put(state + 0x260, 0);
            run.put(state + 0x264, 0);
            run.put(state + 0x29c, 0x280);
            run.put(state + 0x2a0, 0x1e0);
            run.put(state + 0x268, 0);
            run.put(state + 0x27c, 0);
            run.put(state + 0x280, 0);
            run.put(state + 0x284, 1000);
            run.put(state + 0x288, 1000);
            run.put(state + 0x28c, 1000);
            run.put(state + 0x290, 0xa);
            run.put(state + 0x294, 0);
            run.put(state + 0x298, 0);
            run.call(0x4296f0, state + 0x26c, {160, 120, 480, 360});
        }
        run.put(owner + 0x2c, state);
        break;
    case 13:
        state = run.call(0x4f63ec, 0, {0x17c});
        if (state) {
            run.call(0x40b5c0, state);
            run.put(state, 0x50bf94);
            run.put(state + 0x158, args[3]);
            run.put(state + 0x15c, 0);
            run.put(state + 0x160, 0);
            run.put(state + 0x164, 0);
            run.put(state + 0x154, 0);
            run.put(state + 0x168, 0);
            run.put(state + 0x16c, 0x3e8);
            run.put(state + 0x170, 0);
            run.put(state + 0x174, 0);
            run.put(state + 0x178, 0);
        }
        run.put(owner + 0x2c, state);
        break;
    case 14:
        state = run.call(0x4f63ec, 0, {0x15c});
        if (state) {
            run.call(0x40b5c0, state);
            run.put(state, 0x50bf3c);
            run.put(state + 0x154, 0);
        }
        run.put(owner + 0x2c, state);
        break;
    default:
        break;
    }
    if (!run.get(owner + 0x2c)) {
        run.put(run.get(owner + 8) + 0x244, 0);
        return 0;
    }
    run.call(0x42abf0, owner);
    uint32_t result = run.vcall(run.get(owner + 0x2c), 4, {owner, args[1], previous});
    uint32_t current = run.get(owner + 0x2c);
    if (!result) {
        if (current)
            run.vcall(current, 0, {1});
        run.put(owner + 0x2c, 0);
        return 0;
    }
    run.vcall(current, 0x24, {previous});
    run.put(run.get(owner + 8) + 0x244, 1);
    run.call(0x431300, run.get(0x537204));
    run.put(run.get(0x537204) + 0xc, 0xffffffff);
    run.call(0x4b3ab0, run.get(0x537200));
    run.put(run.get(0x537200) + 0x20c, 0xffffffff);
    run.call(0x42abf0, owner);
    return 1;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x428c40)
        return transition(run, receiver, arguments);
    run.fail(CLAW_FAULT_ABI, function);
}
} // namespace
CLAW_MODULE_ENTRY(claw_application_state_factory_entry, owned, body)

// Native seam for the existing inlined constructor after a successful 0x2c8
// allocation. This is not an original function address or a state transition.
extern "C" uint32_t claw_application_menu_construct(uint32_t state, ClawHost *host) {
    if (!host || host->fault) return 0;
    Run run(*host);
    try { menuConstructor(run, state); }
    catch (claw::Failure &) { return 0; }
    return 1;
}
