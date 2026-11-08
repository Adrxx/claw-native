// Downstream application and multiplayer policy, compared with retail v1.0.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;

int owned(uint32_t function) {
    switch (function) {
    case 0x424db0:
    case 0x4268b0:
    case 0x42c0b0:
    case 0x42c640:
        return 1;
    case 0x477790:
    case 0x477a10:
        return 3;
    default:
        return -1;
    }
}

uint32_t popupResource(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t value = run.automatic(-0x4);
    run.put(value, 0);
    run.stackPointer = run.automatic(-0x10);
    const uint32_t found = run.call(0x4f5ff2, receiver + 0x278, {arguments[0], value});
    return found ? run.get(value) : 0;
}

uint32_t archiveName(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t field = receiver + (run.get(receiver + 0x104) ? 0xfc : 0xf8);
    run.stackPointer = run.automatic(-0x10);
    run.call(0x4f6449, arguments[0], {field});
    return arguments[0];
}

uint32_t displayError(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.stackPointer = run.automatic(-0x18);
    if (!run.get(receiver + 0x30)) {
        run.call(0x429e10, receiver, {0x800a, arguments[0]});
    }
    const uint32_t error = run.get(run.get(receiver + 0x30) + 0x38);
    if (!error) {
        run.call(0x429e10, receiver, {0x800a, arguments[0]});
    }
    uint32_t message = 0x8011;
    switch (error) {
    case 0x3f0: message = 0x8015; break;
    case 0x3f1: message = 0x8013; break;
    case 0x3f2: message = 0x8012; break;
    case 0x7d1: message = 0x8019; break;
    case 0x7d2: message = 0x8018; break;
    case 0x7d3: message = 0x8017; break;
    case 0xbb9: message = 0x8014; break;
    case 0xbba: message = 0x8016; break;
    case 0x80e9: message = 0x801e; break;
    case 0x80ea: message = 0x801d; break;
    case 0x80eb: message = 0x801c; break;
    case 0x80ec: message = 0x801b; break;
    case 0x80ed: message = 0x801a; break;
    }
    run.call(0x429e10, receiver, {message, error});
    return 0;
}

uint32_t colorKey(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t depth = arguments[0];
    if (depth != 8 && depth != 0x10 && depth != 0x18) {
        return 0;
    }
    if (!run.get(receiver + 0x30)) {
        return 0;
    }
    if (depth == 8) {
        run.put(0x543170, 0);
    } else if (depth == 0x10) {
        const uint32_t red = ((0xffu >> (run.get(0x541368) & 0x1f)) << (run.get(0x54135c) & 0x1f)) & 0xffff;
        // The green input is zero, including after both masked shifts.
        const uint32_t blue = (0x84u >> (run.get(0x541370) & 0x1f)) & 0xffff;
        run.put(0x543170, red | blue);
    } else {
        run.put(0x543170, 0xff0084);
    }
    return 1;
}

uint32_t sendPacket(Run &run, uint32_t receiver, const uint32_t *arguments) {
    if (!arguments[0]) {
        return 0;
    }
    run.stackPointer = run.automatic(-0x18);
    const uint32_t result = run.call(0x4e0cc0, run.get(receiver + 0x780), {run.get(receiver + 0x784), arguments[0], arguments[2], arguments[1], 0x14});
    return result == 0;
}

uint32_t dispatchPacket(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t packet = arguments[1];
    if (!packet) {
        return 0;
    }
    const uint32_t pointerLocal = run.automatic(-0x710);
    const uint32_t nameLocal = run.automatic(-0x70c);
    const uint32_t scoreNameLocal = run.automatic(-0x708);
    const uint32_t lastNameLocal = run.automatic(-0x704);
    const uint32_t messageLocal = run.automatic(-0x700);
    const uint32_t worldLocal = run.automatic(-0x600);
    run.stackPointer = run.automatic(-0x728);
    const uint32_t player = run.call(0x4e0c80, run.get(receiver + 0x780), {arguments[0]});
    const uint32_t kind = run.get(packet);
    switch (kind) {
    case 3:
        run.stackPointer = run.automatic(-0x728);
        run.call(0x47a4b0, receiver, {packet});
        return 1;
    case 5:
        if (run.get(packet + 0x4) == 1) {
            run.stackPointer = run.automatic(-0x728);
            run.call(0x479000, receiver, {run.get(packet + 0x8)});
            run.put(0x53c0c8, 1);
        }
        return 1;
    case 0x31:
        run.put(receiver + 0x7a0, 1);
        if (run.get(receiver + 0x7ac)) {
            run.stackPointer = run.automatic(-0x72c);
            run.call(0x47c4b0, receiver, {0x52aa40, 0});
            if (run.get(receiver + 0x7bc)) {
                run.stackPointer = run.automatic(-0x724);
                run.call(0x42abb0, run.get(receiver + 0x4));
            } else {
                run.stackPointer = run.automatic(-0x734);
                run.icall(0x546d50, {run.get(run.get(run.get(receiver + 0x4) + 0x4) + 0x4), 0x111, 0x8023, 0});
            }
        }
        return 1;
    case 0x101:
        run.put(receiver + 0x79c, 1);
        return 1;
    case 0x3e8:
    case 0x3ee:
        run.put(receiver + 0x7a8, 1);
        return 1;
    case 0x3e9: {
        if (!player) {
            return 0;
        }
        const uint32_t state = run.get(player + 0x14);
        if (!state || !run.get(state)) {
            return 0;
        }
        run.put(run.get(state) + 0x4c, run.get(packet + 0x4));
        run.put(run.get(state) + 0xf8, run.get(packet + 0xc));
        run.put(run.get(state) + 0x104, run.get(packet + 0x10));
        const bool lowered = (run.get8(packet + 0x10) & 2) != 0;
        const uint32_t object = run.get(state);
        run.put(object + 0x50, run.get(packet + 0x8) + (lowered ? 0x10u : -0x24u));
        return 1;
    }
    case 0x3ea:
        if (!run.get(receiver + 0x790)) {
            run.stackPointer = run.automatic(-0x728);
            run.call(0x479000, receiver, {run.get(packet + 0xc)});
        }
        return 1;
    case 0x3eb:
        if (!run.get(receiver + 0x78c)) {
            if (run.get(receiver + 0xbcc) == 1) {
                if (!run.get(receiver + 0x790)) {
                    const uint32_t sounds = run.get(run.get(run.get(receiver + 0x4) + 0x30) + 0x28);
                    if (!run.get(sounds + 0x30)) {
                        run.put(pointerLocal, 0);
                        run.stackPointer = run.automatic(-0x72c);
                        run.call(0x4f6286, sounds + 0x10, {0x52a568, pointerLocal});
                        const uint32_t sound = run.get(pointerLocal);
                        if (sound) {
                            run.stackPointer = run.automatic(-0x734);
                            run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
                        }
                    }
                    if (!run.get(receiver + 0x790)) {
                        run.stackPointer = run.automatic(-0x734);
                        run.icall(0x546d50, {run.get(run.get(run.get(receiver + 0x4) + 0x4) + 0x4), 0x111, 0x800e, 0});
                    }
                }
                run.put(receiver + 0x78c, 1);
                if (!run.get(receiver + 0x7b8)) {
                    run.stackPointer = run.automatic(-0x724);
                    run.call(0x477650, receiver);
                } else if (player) {
                    run.stackPointer = run.automatic(-0x728);
                    const uint32_t result = run.call(0x41ee40, player, {lastNameLocal});
                    const uint32_t name = run.get(result);
                    run.stackPointer = run.automatic(-0x730);
                    run.call(0x4f4f58, 0, {receiver + 0xbe4, 0x52aa24, name});
                    run.stackPointer = run.automatic(-0x724);
                    run.call(0x4f6584, lastNameLocal);
                }
            } else if (player) {
                run.stackPointer = run.automatic(-0x728);
                const uint32_t result = run.call(0x41ee40, player, {nameLocal});
                const uint32_t name = run.get(result);
                run.stackPointer = run.automatic(-0x730);
                run.call(0x4a3920, 0, {messageLocal, 0x52aa00, name});
                run.stackPointer = run.automatic(-0x724);
                run.call(0x4f6584, nameLocal);
                const uint32_t sounds = run.get(run.get(run.get(receiver + 0x4) + 0x30) + 0x28);
                if (!run.get(sounds + 0x30)) {
                    run.put(pointerLocal, 0);
                    run.stackPointer = run.automatic(-0x72c);
                    run.call(0x4f6286, sounds + 0x10, {0x52a568, pointerLocal});
                    const uint32_t sound = run.get(pointerLocal);
                    if (sound) {
                        run.stackPointer = run.automatic(-0x734);
                        run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
                    }
                }
                run.stackPointer = run.automatic(-0x72c);
                run.call(0x422370, run.get(run.get(receiver + 0x4) + 0x4c), {messageLocal, 0});
            }
        } else if (run.get(receiver + 0xbcc) == 2) {
            const uint32_t sounds = run.get(run.get(run.get(receiver + 0x4) + 0x30) + 0x28);
            if (!run.get(sounds + 0x30)) {
                run.put(pointerLocal, 0);
                run.stackPointer = run.automatic(-0x72c);
                run.call(0x4f6286, sounds + 0x10, {0x52a568, pointerLocal});
                const uint32_t sound = run.get(pointerLocal);
                if (sound) {
                    run.stackPointer = run.automatic(-0x734);
                    run.call(0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
                }
            }
        }
        return 1;
    case 0x3ec: {
        if (!player) {
            return 0;
        }
        const uint32_t state = run.get(player + 0x14);
        if (!state || !run.get(state)) {
            return 0;
        }
        run.put(run.get(state) + 0xf8, run.get(packet + 0xc));
        run.put(run.get(state) + 0x104, run.get(packet + 0x10));
        run.put(state + 0x18, 1);
        run.put(state + 0x24, 1);
        run.put(run.get(state) + 0x4c, 0);
        run.put(run.get(state) + 0x50, 0);
        run.stackPointer = run.automatic(-0x728);
        run.call(0x486d50, 0, {player});
        if (run.get(receiver + 0xbcc) == 2) {
            run.put(state + 0x28, run.get(packet + 0x4));
            run.put(state + 0x20, 1);
            run.stackPointer = run.automatic(-0x728);
            const uint32_t record = run.call(0x4f63ec, 0, {0x2c});
            run.put(pointerLocal, record);
            run.stackPointer = run.automatic(-0x728);
            const uint32_t result = run.call(0x41ee40, player, {scoreNameLocal});
            const uint32_t name = run.get(result);
            uint32_t length = 0;
            do {
                ++length;
            } while (run.get8(name + length - 1));
            const uint32_t destination = run.get(pointerLocal);
            uint32_t offset = 0;
            for (; offset + 4 <= length; offset += 4) {
                run.put(destination + offset, run.get(name + offset));
            }
            for (; offset < length; ++offset) {
                run.put8(destination + offset, run.get8(name + offset));
            }
            run.stackPointer = run.automatic(-0x724);
            run.call(0x4f6584, scoreNameLocal);
            const uint32_t scoreRecord = run.get(pointerLocal);
            run.put(scoreRecord + 0x20, run.get(run.get(state) + 0xf8));
            run.put(scoreRecord + 0x24, run.get(state + 0x28));
            run.put(scoreRecord + 0x28, 0);
            run.stackPointer = run.automatic(-0x72c);
            run.call(0x4f582f, receiver + 0xc08, {run.get(receiver + 0xc10), scoreRecord});
        }
        run.put(0x53c0c8, 1);
        return 1;
    }
    case 0x3ed: {
        run.stackPointer = run.automatic(-0x728);
        const uint32_t other = run.call(0x4e0c80, run.get(receiver + 0x780), {run.get(packet + 0xc)});
        if (other) {
            const uint32_t state = run.get(other + 0x14);
            if (state) {
                run.put(state + 0x1c, 1);
            }
        }
        return 1;
    }
    case 0x3ef:
        run.put(receiver + 0x7a8, 1);
        run.put(receiver + 0x7ac, 1);
        return 1;
    case 0x3f0: {
        run.stackPointer = run.automatic(-0x72c);
        run.call(0x422370, run.get(run.get(receiver + 0x4) + 0x4c), {packet + 0x8, run.get(packet + 0x4)});
        const uint32_t sounds = run.get(run.get(receiver + 0xc) + 0x28);
        if (!run.get(sounds + 0x30)) {
            run.put(pointerLocal, 0);
            run.stackPointer = run.automatic(-0x72c);
            run.call(0x4f6286, sounds + 0x10, {0x52a824, pointerLocal});
            const uint32_t sound = run.get(pointerLocal);
            if (sound && run.get(0x532c0c)) {
                const uint32_t channel = run.get(0x532c10);
                run.stackPointer = run.automatic(-0x734);
                run.call(0x4b45f0, run.get(sound + 0x10), {channel, 0, 0, 0});
            }
        }
        return 1;
    }
    case 0x3f1:
        run.put(receiver + 0x7b4, 1);
        run.put(receiver + 0x7a8, 1);
        return 1;
    case 0x3f2:
        run.stackPointer = run.automatic(-0x734);
        run.call(0x47aa10, receiver, {run.get(packet + 0x4), run.get(packet + 0x8), run.get(packet + 0xc), player});
        return 1;
    case 0x3f3:
        if (run.get(receiver + 0x79c) && player) {
            run.stackPointer = run.automatic(-0x734);
            run.call(0x477810, receiver, {player, 0x3f4, run.get(receiver + 0x14), 1});
        }
        return 1;
    case 0x3f4:
        run.put(receiver + 0xbec, run.get(packet + 0xc));
        return 1;
    case 0x3f5:
        if (run.get(receiver + 0x258)) {
            uint32_t hash = run.get(run.get(run.get(receiver + 0xc) + 0x24) + 0xac);
            if (!hash) {
                run.stackPointer = run.automatic(-0x728);
                run.call(0x46a840, run.get(receiver + 0x4), {pointerLocal});
                const uint32_t filename = run.get(pointerLocal);
                if (run.get(filename - 0x8)) {
                    run.stackPointer = run.automatic(-0x72c);
                    const uint32_t found = run.call(0x4cd400, run.get(run.get(receiver + 0xc) + 0x24), {filename, worldLocal});
                    if (found) {
                        hash = run.get(run.automatic(-0x314));
                    }
                }
                run.stackPointer = run.automatic(-0x724);
                run.call(0x4f6584, pointerLocal);
            }
            if (hash != run.get(packet + 0xc)) {
                run.stackPointer = run.automatic(-0x734);
                run.icall(0x546d50, {run.get(run.get(run.get(receiver + 0x4) + 0x4) + 0x4), 0x111, 0x8085, 0});
            }
        }
        return 1;
    default:
        return 0;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x424db0:
        return popupResource(run, receiver, arguments);
    case 0x4268b0:
        return archiveName(run, receiver, arguments);
    case 0x42c0b0:
        return displayError(run, receiver, arguments);
    case 0x42c640:
        return colorKey(run, receiver, arguments);
    case 0x477790:
        return sendPacket(run, receiver, arguments);
    case 0x477a10:
        return dispatchPacket(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_downstream_application_entry, owned, body)
