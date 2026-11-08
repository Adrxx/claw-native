// Original application state, Portal shell and multiplayer helpers.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t f) {
    switch (f) {
    case 0x4299d0: return 0;
    case 0x42ce90: return 1;
    case 0x424de0: return 2;
    case 0x42bc40: return 1;
    case 0x42be30: return 1;
    case 0x4774f0: return 0;
    case 0x477840: return 0;
    case 0x478290: return 1;
    default: return -1;
    }
}

uint32_t callAt(Run &run, int32_t offset, uint32_t f, uint32_t receiver,
                std::initializer_list<uint32_t> args = {}) {
    const uint32_t prior = run.stackPointer;
    run.stackPointer = run.automatic(offset);
    const uint32_t value = run.call(f, receiver, args);
    run.stackPointer = prior;
    return value;
}

uint32_t stringLength(Run &run, uint32_t text) {
    uint32_t count = 0;
    while (run.get8(text + count) != 0) {
        ++count;
    }
    return count;
}

void copyString(Run &run, uint32_t target, uint32_t source) {
    const uint32_t count = stringLength(run, source) + 1;
    uint32_t i = 0;
    for (; i + 4 <= count; i += 4) {
        run.put(target + i, run.get(source + i));
    }
    for (; i < count; ++i) {
        run.put8(target + i, run.get8(source + i));
    }
}

// 0x4299d0. Derived shell teardown changes vtables before each base cleanup.
uint32_t function_4299d0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x50bf94);
    callAt(run, -0x18, 0x438e10, receiver);
    run.put(receiver, 0x50b4ec);
    callAt(run, -0x18, 0x48f180, receiver);
    return 0;
}

void destroyTimer(Run &run, uint32_t timer) {
    callAt(run, -0x24, 0x402270, timer);
    callAt(run, -0x24, 0x4f5192, timer + 0x08);
    callAt(run, -0x28, 0x4f6428, 0, {timer});
}

void destroyArchive(Run &run, uint32_t receiver) {
    const uint32_t archive = run.get(receiver + 0x34);
    if (archive != 0) {
        callAt(run, -0x24, 0x4b7250, archive);
        callAt(run, -0x28, 0x4f6428, 0, {archive});
        run.put(receiver + 0x34, 0);
    }
}

// 0x42ce90. Application +30 display, +34 archive, +5c timer, +78 depth.
uint32_t function_42ce90(Run &run, uint32_t receiver, const uint32_t *a) {
    if (run.get(receiver + 0x30) == 0) {
        return 0;
    }
    const uint32_t depth = a[0];
    if (run.get(receiver + 0x78) == depth) {
        return 1;
    }
    if (depth != 8 && depth != 16) {
        return 0;
    }
    uint32_t timer = run.get(receiver + 0x5c);
    if (timer != 0) {
        run.put(run.automatic(4), timer);
        destroyTimer(run, timer);
        run.put(receiver + 0x5c, 0);
    }
    destroyArchive(run, receiver);
    run.put(receiver + 0x78, depth);
    run.put(0x537250, 0);
    run.put(0x53724c, 0);
    if (run.get(receiver + 0x78) == 16) {
        run.put(0x53724c, 1);
    }
    uint32_t display = run.get(receiver + 0x30);
    callAt(run, -0x24, run.get(run.get(display) + 0x1c), display);
    uint32_t flags = run.get(0x537234) == 0 ? 1u : 5u;
    display = run.get(receiver + 0x30);
    uint32_t method = run.get(run.get(display) + 0x18);
    uint32_t currentDepth = run.get(receiver + 0x78);
    uint32_t window = run.get(run.get(receiver + 0x04) + 0x04);
    if (callAt(run, -0x38, method, display, {window, 0x280, 0x1e0, currentDepth, flags}) == 0) {
        callAt(run, -0x28, 0x42c0b0, receiver, {0x3ea});
        return 0;
    }
    callAt(run, -0x28, 0x4cf010, 0, {0x428bc0});
    uint32_t surface = run.get(run.get(receiver + 0x30) + 0x24);
    run.put(surface + 0x64, 14);
    run.put(surface + 0x68, 14);
    callAt(run, -0x28, 0x401000, 0, {run.get(receiver + 0x30)});
    if (callAt(run, -0x24, 0x42cab0, receiver) == 0) {
        return 0;
    }
    destroyArchive(run, receiver);
    uint32_t archive = callAt(run, -0x28, 0x4f63ec, 0, {0x48});
    run.put(run.automatic(4), archive);
    if (archive != 0) {
        archive = callAt(run, -0x24, 0x4b7210, archive);
    }
    run.put(receiver + 0x34, archive);
    uint32_t nameObject = callAt(run, -0x28, 0x4268b0, receiver, {run.automatic(4)});
    const uint32_t name = run.get(nameObject);
    const uint32_t opened = callAt(run, -0x30, 0x4b72e0, run.get(receiver + 0x34), {name, 1, 0});
    callAt(run, -0x24, 0x4f6584, run.automatic(4));
    if (opened == 0) {
        const uint32_t command = run.get(receiver + 0x104) != 0 ? 0x8010u : 0x800bu;
        callAt(run, -0x2c, 0x429e10, receiver, {command, 0x3eb});
        return 0;
    }
    callAt(run, -0x28, 0x42c640, receiver, {run.get(receiver + 0x78)});
    timer = run.get(receiver + 0x5c);
    if (timer != 0) {
        destroyTimer(run, timer);
        run.put(receiver + 0x5c, 0);
    }
    timer = callAt(run, -0x28, 0x4f63ec, 0, {0x30});
    if (timer != 0) {
        callAt(run, -0x28, 0x4f5133, timer + 0x08, {10});
        run.put(timer, 0);
        run.put(timer + 0x04, 100);
    }
    run.put(receiver + 0x5c, timer);
    const uint32_t parameter = run.get(receiver + 0x12c);
    const uint32_t backend = run.get(run.get(receiver + 0x30) + 0x28);
    if (callAt(run, -0x2c, 0x402240, timer, {backend, parameter}) == 0) {
        callAt(run, -0x2c, 0x429e10, receiver, {0x800a, 0x6af});
        return 0;
    }
    timer = run.get(receiver + 0x5c);
    const uint32_t enabled = run.get(receiver + 0x11c);
    const uint32_t active = run.get(timer + 0x24);
    if (enabled != 0) {
        if (active == 0) {
            run.put(timer + 0x24, 1);
            callAt(run, -0x24, 0x402570, timer);
        }
    } else if (active != 0) {
        run.put(timer + 0x24, 0);
        callAt(run, -0x24, 0x402520, timer);
    }
    callAt(run, -0x28, 0x42cdc0, receiver, {run.get(receiver + 0x12c)});
    return 1;
}

// 0x424de0. Popup +68 is the selection context; argument 1 is unused.
uint32_t function_424de0(Run &run, uint32_t receiver, const uint32_t *a) {
    const uint32_t index = callAt(run, -0x0c, 0x424db0, receiver, {a[0]});
    if (index != 0) {
        const uint32_t object = callAt(run, -0x0c, 0x4e2110, receiver, {index});
        if (object != 0) {
            const uint32_t method = run.get(run.get(receiver) + 0x1b0);
            callAt(run, -0x10, method, receiver, {run.get(receiver + 0x68), object});
            callAt(run, -0x08, run.get(run.get(receiver) + 0x1f8), receiver);
        }
    }
    return 0;
}

// 0x42bc40. Stack resident registry object and executable pathname.
uint32_t function_42bc40(Run &run, uint32_t, const uint32_t *a) {
    const uint32_t registry = run.automatic(-0x228);
    const uint32_t path = run.automatic(-0x328);
    const uint32_t lengthSlot = run.automatic(-0x32c);
    run.put(registry, 0);
    uint32_t result = callAt(run, -0x350, 0x4b5c50, registry, {0x5258b8, 0x525f6c, 0x5258d0, 0, 0x80000002, 0});
    if (result == 0) {
        callAt(run, -0x338, 0x4b5d70, registry);
        return 0;
    }
    run.put8(path, 0);
    run.put(lengthSlot, 0xde);
    result = callAt(run, -0x348, 0x4b5e90, registry, {0x525f64, path, lengthSlot, 0});
    if (result == 0) {
        callAt(run, -0x338, 0x4b5d70, registry);
        return 0;
    }
    uint32_t length = stringLength(run, path);
    if (s32(length) < 1) {
        callAt(run, -0x338, 0x4b5d70, registry);
        return 0;
    }
    if (run.get8(path + length - 1) != 0x5c) {
        copyString(run, path + length, 0x525f60);
    }
    length = stringLength(run, path);
    copyString(run, path + length, 0x525f54);
    if (callAt(run, -0x33c, 0x48c190, 0, {path}) == 0) {
        callAt(run, -0x338, 0x4b5d70, registry);
        return 0;
    }
    if (a[0] != 0) {
        copyString(run, a[0], path);
    }
    callAt(run, -0x338, 0x4b5d70, registry);
    return 1;
}

// 0x42be30. Owned helper receives the exact stack frame of the original CALL.
uint32_t function_42be30(Run &run, uint32_t receiver, const uint32_t *a) {
    const uint32_t path = run.automatic(-0x100);
    run.put8(path, 0);
    const uint32_t frame = run.frame;
    run.frame = frame - 0x10c;
    const uint32_t args[] = {path};
    uint32_t found = function_42bc40(run, 0, args);
    run.frame = frame;
    if (found == 0 || run.get8(path) == 0) {
        return 0;
    }
    if (callAt(run, -0x110, 0x42beb0, receiver, {path, 0}) == 0) {
        return 0;
    }
    if (a[0] != 0) {
        callAt(run, -0x108, 0x42abb0, receiver);
    }
    return 1;
}

// 0x4774f0. Packet contents and cached player coordinates are independent.
uint32_t function_4774f0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t timeout = run.get(receiver + 0xbf4);
    const uint32_t delta = run.get(0x53720c);
    run.put(receiver + 0xbf4, delta < timeout ? timeout - delta : 0);
    if (run.get(receiver + 0xbf4) != 0) {
        return 0;
    }
    const uint32_t count = run.get(run.get(receiver + 0x780) + 0x60);
    run.put(receiver + 0xbf4, run.get(receiver + 0xc00) * (count - 1) + run.get(receiver + 0xbfc));
    const uint32_t actor = run.get(0x537e88);
    run.put(0x53abc0, 0x3e9);
    const uint32_t x = run.get(actor + 0x4c);
    run.put(0x53abc4, x);
    const uint32_t y = run.get(actor + 0x50);
    run.put(0x53abc8, y);
    const uint32_t state = run.get(actor + 0xf8);
    run.put(0x53abcc, state);
    run.put(0x53abd0, 0);
    uint32_t status = 0;
    if (run.get(run.get(run.get(actor + 0x6c) + 0x14)) == 0) {
        status = 1;
        run.put(0x53abd0, 1);
    }
    if (x == run.get(0x52a7bc) && y == run.get(0x52a7c0) &&
        state == run.get(0x52a7c4) && status == run.get(0x52a7c8)) {
        timeout = run.get(receiver + 0xbf8);
        const uint32_t resendDelta = run.get(0x53720c);
        run.put(receiver + 0xbf8, resendDelta < timeout ? timeout - resendDelta : 0);
        if (run.get(receiver + 0xbf8) != 0) {
            return 0;
        }
    } else {
        run.put(0x52a7bc, x);
        run.put(0x52a7c0, y);
        run.put(0x52a7c4, state);
        run.put(0x52a7c8, status);
    }
    const uint32_t peer = run.get(receiver + 0xc04);
    run.put(receiver + 0xbf8, 10000);
    if (peer != 0) {
        if (peer != run.get(receiver + 0x784)) {
            callAt(run, -0x1c, 0x477790, receiver, {peer, 0x53abc0, 0});
        }
    } else {
        callAt(run, -0x20, 0x4e0d70, run.get(receiver + 0x780), {run.get(receiver + 0x784), 0, 0x53abc0, 0x14});
    }
    return 0;
}

// 0x477840. COM pending count/packet receipt outputs reside on the guest stack.
uint32_t function_477840(Run &run, uint32_t receiver, const uint32_t *) {
    const uint32_t sizeSlot = run.automatic(-0x10);
    const uint32_t countSlot = run.automatic(-0x0c);
    const uint32_t senderSlot = run.automatic(-0x08);
    const uint32_t recipientSlot = run.automatic(-0x04);
    uint32_t pending = 0;
    uint32_t player = run.get(receiver + 0x784);
    if (player != 0) {
        const uint32_t network = run.get(run.get(receiver + 0x780) + 0x18);
        const uint32_t method = run.get(run.get(network) + 0x44);
        const uint32_t ok = callAt(run, -0x30, method, 0, {network, run.get(player + 0x04), countSlot});
        pending = ok == 0 ? run.get(countSlot) : 0;
    }
    run.put(receiver + 0x14c, pending);
    if (s32(pending) <= 0) {
        if (run.get(receiver + 0x7ac) == 0 || s32(callAt(run, -0x24, run.get(run.get(receiver) + 0x50), receiver)) <= 1) {
            return 0;
        }
        uint32_t timeout = run.get(receiver + 0xbf0);
        const uint32_t delta = run.get(0x53720c);
        run.put(receiver + 0xbf0, delta < timeout ? timeout - delta : 0);
        if (run.get(receiver + 0xbf0) != 0) {
            return 0;
        }
        const uint32_t application = run.get(receiver + 0x04);
        run.put(receiver + 0xbf0, 60000);
        callAt(run, -0x2c, 0x422370, run.get(application + 0x4c), {0x52a9d4, 2});
        const uint32_t sounds = run.get(run.get(receiver + 0x0c) + 0x28);
        if (run.get(sounds + 0x30) == 0) {
            run.put(countSlot, 0);
            callAt(run, -0x2c, 0x4f6286, sounds + 0x10, {0x52a824, countSlot});
            const uint32_t sound = run.get(countSlot);
            if (sound != 0 && run.get(0x532c0c) != 0) {
                callAt(run, -0x34, 0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
            }
        }
        return 0;
    }
    player = run.get(receiver + 0x784);
    run.put(receiver + 0xbf0, 60000);
    run.put(countSlot, 0);
    const uint32_t buffer = run.get(player + 0x18);
    run.put(sizeSlot, run.get(player + 0x1c));
    run.put(senderSlot, 0);
    if (buffer == 0) {
        return 0;
    }
    while (s32(pending) > 0) {
        player = run.get(receiver + 0x784);
        run.put(sizeSlot, run.get(player + 0x1c));
        run.put(recipientSlot, run.get(player + 0x04));
        const uint32_t network = run.get(run.get(receiver + 0x780) + 0x18);
        const uint32_t method = run.get(run.get(network) + 0x64);
        const uint32_t error = callAt(run, -0x3c, method, 0, {network, senderSlot, recipientSlot, 1, buffer, sizeSlot});
        if (error != 0) {
            callAt(run, -0x34, 0x4e10d0, 0, {0x52a9bc, 0x12e, error, 0});
            break;
        }
        --pending;
        run.put(countSlot, run.get(countSlot) + 1);
        if (run.get(senderSlot) != run.get(run.get(receiver + 0x784) + 0x04)) {
            callAt(run, -0x30, 0x477a10, receiver, {run.get(senderSlot), buffer, run.get(sizeSlot)});
        }
    }
    return run.get(countSlot);
}

// 0x478290. Descending exchange-selection sort and competition ranks.
uint32_t function_478290(Run &run, uint32_t receiver, const uint32_t *a) {
    if (run.get(receiver + 0x7ac) == 0) {
        return 0;
    }
    if (a[0] == 0 && run.get(receiver + 0x794) == 0) {
        const uint32_t delta = run.get(0x53720c);
        const uint32_t throttle = run.get(0x52a7cc);
        if (delta < throttle) {
            run.put(0x52a7cc, throttle - delta);
            return 0;
        }
        run.put(0x52a7cc, 500);
    }
    if (run.get(receiver + 0x794) != 0) {
        uint32_t manager = run.get(receiver + 0x780);
        uint32_t node = run.get(manager + 0x58);
        run.put(manager + 0x84, node);
        uint32_t player = 0;
        if (node != 0) {
            run.put(manager + 0x84, run.get(node));
            player = run.get(node + 0x08);
        }
        uint32_t count = 0;
        while (player != 0) {
            run.put(receiver + 0x7c0 + count * 4, player);
            ++count;
            manager = run.get(receiver + 0x780);
            node = run.get(manager + 0x84);
            if (node != 0) {
                const uint32_t next = run.get(node);
                player = run.get(node + 0x08);
                run.put(manager + 0x84, next);
            } else {
                player = 0;
            }
        }
        run.put(receiver + 0xbc0, count);
        run.put(receiver + 0x794, 0);
    }
    if (run.get(receiver + 0xbcc) == 2) {
        return 0;
    }
    uint32_t count = run.get(receiver + 0xbc0);
    if (s32(count - 1) > 0) {
        uint32_t first = 0;
        uint32_t start = 1;
        do {
            uint32_t selected = run.get(run.get(receiver + 0x7c0 + first * 4) + 0x14);
            uint32_t index = start;
            while (s32(index) < s32(count)) {
                const uint32_t player = run.get(receiver + 0x7c0 + index * 4);
                const uint32_t candidate = run.get(player + 0x14);
                const uint32_t candidateScore = run.get(run.get(candidate) + 0xf8);
                const uint32_t selectedScore = run.get(run.get(selected) + 0xf8);
                if (s32(candidateScore) > s32(selectedScore)) {
                    const uint32_t old = run.get(receiver + 0x7c0 + first * 4);
                    run.put(receiver + 0x7c0 + first * 4, player);
                    run.put(receiver + 0x7c0 + index * 4, old);
                    selected = candidate;
                }
                ++index;
                count = run.get(receiver + 0xbc0);
            }
            ++first;
            ++start;
            count = run.get(receiver + 0xbc0);
        } while (s32(first) < s32(count - 1));
    }
    uint32_t tied = 0;
    uint32_t rank = 0;
    uint32_t previous = 0xffffffff;
    for (uint32_t index = 0; s32(index) < s32(run.get(receiver + 0xbc0)); ++index) {
        const uint32_t scoreObject = run.get(run.get(run.get(receiver + 0x7c0 + index * 4) + 0x14));
        if (run.get(receiver + 0xbcc) == 1) {
            const uint32_t score = run.get(scoreObject + 0xf8);
            if (a[0] == 0 && s32(score) <= 0) {
                run.put(scoreObject + 0xfc, 0);
            } else if (score == previous) {
                ++tied;
                run.put(scoreObject + 0xfc, rank);
            } else {
                rank = rank + tied + 1;
                previous = score;
                tied = 0;
                run.put(scoreObject + 0xfc, rank);
            }
        } else {
            run.put(scoreObject + 0xfc, 0);
        }
    }
    return 0;
}

uint32_t body(Run &run, uint32_t f, uint32_t receiver, const uint32_t *a) {
    switch (f) {
    case 0x4299d0: return function_4299d0(run, receiver, a);
    case 0x42ce90: return function_42ce90(run, receiver, a);
    case 0x424de0: return function_424de0(run, receiver, a);
    case 0x42bc40: return function_42bc40(run, receiver, a);
    case 0x42be30: return function_42be30(run, receiver, a);
    case 0x4774f0: return function_4774f0(run, receiver, a);
    case 0x477840: return function_477840(run, receiver, a);
    case 0x478290: return function_478290(run, receiver, a);
    default: run.fail(CLAW_FAULT_ABI, f);
    }
}
}
CLAW_MODULE_ENTRY(claw_call_closure_application_helpers_entry, owned, body)
