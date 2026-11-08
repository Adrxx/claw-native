#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x426e30:
        return 3;
    case 0x42ba10:
    case 0x436e60:
        return 1;
    case 0x42ba70:
    case 0x4cd530:
        return 2;
    case 0x42bab0:
    case 0x42bad0:
        return 0;
    default:
        return -1;
    }
}

// The dispatcher has a 0x40-byte buffer and two saved registers. Every
// outgoing call below starts from its physical ESP, F-0x48.
uint32_t menuCall(Run &run, uint32_t function, uint32_t receiver,
                  std::initializer_list<uint32_t> args = {}) {
    run.stackPointer = run.frame - 0x4c - uint32_t(args.size()) * 4;
    return run.call(function, receiver, args);
}

uint32_t stateQuery(Run &run, uint32_t app) {
    // Application +0x2c is reloaded for each state query.
    uint32_t state = run.get(app + 0x2c);
    return menuCall(run, run.get(run.get(state) + 0x10), state);
}

void postCommand(Run &run, uint32_t app, uint32_t command, uint32_t value = 0) {
    // Application +0x04 points at the window; window +0x04 is HWND.
    menuCall(run, run.get(0x546d50), 0, {run.get(run.get(app + 0x04) + 0x04), 0x111, command, value});
}

void cheatSound(Run &run, uint32_t app, uint32_t key) {
    // Application +0x30 resources, resources +0x28 audio subsystem,
    // audio +0x30 suppresses sound. The sound entry runs original code.
    uint32_t audio = run.get(run.get(app + 0x30) + 0x28);
    if (run.get(audio + 0x30) == 0) {
        uint32_t sound = menuCall(run, 0x4061b0, audio, {key});
        if (sound != 0) {
            menuCall(run, 0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
        }
    }
}

// 0x426e30. Full command is used by the primary dispatch; fallback uses LOWORD.
uint32_t function_426e30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t command = arguments[1];
    uint32_t error = 0;
    switch (command) {
    case 0x8005:
    case 0x8024:
        if (stateQuery(run, receiver) != 2 && stateQuery(run, receiver) != 5 && stateQuery(run, receiver) != 0xd)
            return 1;
        if (menuCall(run, 0x429b70, receiver, {1}) == 0)
            error = 0x3f5;
        break;
    case 0x800d:
        if (menuCall(run, 0x429b70, receiver, {1}) == 0)
            error = 0x3f6;
        break;
    case 0x807f:
        if (menuCall(run, 0x429b70, receiver, {run.get(run.automatic(0x0c))}) == 0)
            error = 0x6ac;
        break;
    case 0x807e:
        if (menuCall(run, 0x429b70, receiver, {run.get(receiver + 0xd4)}) == 0) {
            run.put(receiver + 0xa8, 0);
            error = 0x6ab;
        }
        break;
    case 0x8038:
        if (stateQuery(run, receiver) == 5 || stateQuery(run, receiver) == 2) {
            uint32_t show = run.get(0x546d54);
            while (s32(menuCall(run, show, 0, {1})) < 0) {
            }
            menuCall(run, 0x42a840, receiver, {0x525c0c});
        }
        break;
    case 0x8023:
        if (menuCall(run, 0x428c40, receiver, {5, 1, 0, 0}) == 0)
            error = 0x3f7;
        break;
    case 0x8080:
        if (menuCall(run, 0x428c40, receiver, {0xb, 1, 1, 0}) == 0)
            error = 0x6ad;
        break;
    case 0x8090:
        if (menuCall(run, 0x428c40, receiver, {0xd, 1, 1, run.get(run.automatic(0x0c))}) == 0)
            error = 0x6ad;
        break;
    case 0x8036:
        if (menuCall(run, 0x429ac0, receiver) == 0)
            error = 0x3f8;
        break;
    case 0x8021:
        if (stateQuery(run, receiver) != 2 && stateQuery(run, receiver) != 5 && stateQuery(run, receiver) != 0xa)
            return 1;
        if (menuCall(run, 0x428c40, receiver, {8, 1, 0, 0}) == 0 &&
            menuCall(run, 0x428c40, receiver, {5, 1, 0, 0}) == 0)
            error = 0x3f9;
        break;
    case 0x8027:
        if (menuCall(run, 0x428c40, receiver, {2, 1, 0, 0}) == 0)
            error = 0x3fa;
        break;
    case 0x80ab:
        if (menuCall(run, 0x428c40, receiver, {0xe, 1, 0, 0}) == 0)
            error = 0x3fa;
        break;
    case 0x8022:
    case 0x8026:
        if (stateQuery(run, receiver) == 2 || stateQuery(run, receiver) == 5) {
            uint32_t audio = run.get(run.get(receiver + 0x30) + 0x28);
            if (run.get(audio + 0x30) == 0) {
                run.put(run.automatic(0x0c), 0);
                menuCall(run, 0x4f6286, audio + 0x10, {0x525c04, run.automatic(0x0c)});
                uint32_t sound = run.get(run.automatic(0x0c));
                if (sound != 0)
                    menuCall(run, 0x4208e0, sound, {run.get(0x532c10), 0, 0, 0});
            }
        }
        break;
    case 0x807c:
        if (stateQuery(run, receiver) == 0xa && menuCall(run, 0x40b330, run.get(receiver + 0x2c)) == 0)
            error = 0x6a8;
        break;
    case 0x8007:
        if (stateQuery(run, receiver) == 3) {
            uint32_t pause = run.get(receiver + 0x0c) ^ 1;
            run.put(receiver + 0x0c, pause);
            menuCall(run, 0x42a570, receiver, {pause});
        }
        break;
    case 0x803a:
    case 0x8084:
        if (menuCall(run, 0x42a630, receiver) != 0 &&
            menuCall(run, command == 0x803a ? 0x46be40 : 0x46c110, run.get(receiver + 0x2c)) == 0)
            error = 0x3fb;
        break;
    case 0x805c:
        if (menuCall(run, 0x42a630, receiver) != 0) {
            uint32_t state = run.get(receiver + 0x2c);
            menuCall(run, run.get(run.get(state) + 0x54), state);
        }
        break;
    case 0x8062:
        run.put(receiver + 0x98, 0);
        postCommand(run, receiver, 0x8025);
        break;
    case 0x8085:
        if (run.get(receiver + 0x2c) != 0 && stateQuery(run, receiver) == 4)
            menuCall(run, 0x47c400, run.get(receiver + 0x2c));
        break;
    case 0x800e:
        if (menuCall(run, 0x42a630, receiver) != 0) {
            uint32_t state = run.get(receiver + 0x2c);
            if (menuCall(run, run.get(run.get(state) + 0x40), state) == 0)
                menuCall(run, run.get(0x546d44), 0, {run.get(run.get(receiver + 0x04) + 0x04), 0x111, 0x8023, 0});
        }
        break;
    case 0x8042:
        if (menuCall(run, 0x42a630, receiver) == 0)
            postCommand(run, receiver, 0x8090, 2);
        break;
    case 0x8075:
        if (menuCall(run, 0x429be0, receiver) == 0)
            menuCall(run, 0x429e10, receiver, {0x8007, 0x6a7});
        break;
    case 0x800f:
        if (stateQuery(run, receiver) == 3 || stateQuery(run, receiver) == 4) {
            menuCall(run, 0x429cb0, receiver);
            break;
        }
        [[fallthrough]];
    case 0x8006:
        if (run.get(receiver + 0x9c) != 0) {
            if (menuCall(run, 0x428c40, receiver, {0xc, 1, 1, 0}) == 0)
                error = 0x6ad;
        } else {
            run.put(run.get(receiver + 0x2c) + 0x38, 1);
            if (menuCall(run, 0x428c40, receiver, {5, 1, 0, 0}) == 0)
                error = 0x3fc;
        }
        break;
    case 0x8063:
        if (menuCall(run, 0x42a630, receiver) != 0) {
            uint32_t player = run.get(0x537e88);
            if (player != 0)
                menuCall(run, 0x41f490, 0, {player});
        }
        break;
    case 0x8008:
        menuCall(run, 0x42abb0, receiver);
        break;
    case 0x8025:
        if (stateQuery(run, receiver) != 2 && stateQuery(run, receiver) != 5)
            return 1;
        if (menuCall(run, 0x428c40, receiver, {4, 1, 0, 0}) == 0 &&
            menuCall(run, 0x428c40, receiver, {5, 1, 0, 0}) == 0)
            error = 0x3fe;
        break;
    case 0x8035:
        if (stateQuery(run, receiver) == 9 || stateQuery(run, receiver) == 0xd ||
            stateQuery(run, receiver) == 0xf || stateQuery(run, receiver) == 0xe || stateQuery(run, receiver) == 8)
            return 1;
        if (menuCall(run, 0x428c40, receiver, {9, 1, 1, 0}) == 0)
            error = 0x3ff;
        break;
    case 0x8041:
        menuCall(run, 0x42a9b0, receiver);
        break;
    case 0x8059:
        menuCall(run, 0x42aa10, receiver);
        break;
    case 0x8095:
        menuCall(run, 0x42d220, receiver);
        break;
    case 0x8039:
        if (stateQuery(run, receiver) == 5)
            menuCall(run, 0x42b930, receiver);
        break;
    case 0x801b:
    case 0x801c:
    case 0x802a:
    case 0x802b:
    case 0x802c:
        if (menuCall(run, 0x42afd0, receiver) != 0) {
            switch (command) {
            case 0x801b:
                menuCall(run, 0x429e70, receiver);
                break;
            case 0x801c:
                menuCall(run, 0x429e30, receiver);
                break;
            case 0x802a:
                menuCall(run, 0x42a260, receiver);
                break;
            case 0x802b:
                menuCall(run, 0x42a350, receiver);
                break;
            default:
                menuCall(run, 0x42a000, receiver, {1});
                break;
            }
        }
        break;
    case 0x800a:
        if (run.get(receiver + 0x0c) == 0) {
            uint32_t music = run.get(receiver + 0x14) ^ 1;
            run.put(receiver + 0x14, music);
            if (menuCall(run, 0x42a630, receiver) != 0 || stateQuery(run, receiver) == 0xb || stateQuery(run, receiver) == 5) {
                if (music != 0)
                    menuCall(run, 0x4b5570, run.get(receiver + 0x50), {1});
                else
                    menuCall(run, 0x4b55a0, run.get(receiver + 0x50));
            }
        }
        break;
    case 0x8009:
        if (run.get(receiver + 0x30) != 0) {
            uint32_t sound = run.get(run.get(run.get(receiver + 0x30) + 0x28) + 0x2c);
            if (sound != 0)
                menuCall(run, 0x4b4b40, sound);
            uint32_t toggle = run.get(receiver + 0x10) ^ 1;
            run.put(receiver + 0x10, toggle);
            run.put(0x532c0c, toggle);
            run.put(run.automatic(0x0c), run.get(receiver + 0x10));
            if (toggle != 0)
                menuCall(run, 0x402570, run.get(receiver + 0x5c));
            else
                menuCall(run, 0x402520, run.get(receiver + 0x5c));
        }
        break;
    case 0x8070:
        menuCall(run, 0x495be0, 0, {run.get(receiver + 0x38), receiver});
        break;
    case 0x803c:
    case 0x803d:
        if (stateQuery(run, receiver) == 4)
            menuCall(run, command == 0x803c ? 0x486a90 : 0x486bf0, 0);
        break;
    case 0x8082:
        if (stateQuery(run, receiver) == 4)
            run.put(0x525518, run.get(0x525518) ^ 1);
        break;
    case 0x8083:
        if (stateQuery(run, receiver) == 4) {
            uint32_t helper = run.get(receiver + 0x4c);
            if (helper != 0)
                menuCall(run, 0x428b40, helper);
        }
        break;
    case 0x8050:
    case 0x8051:
    case 0x8052:
    case 0x8053:
    case 0x8054:
    case 0x8055:
    case 0x8056:
        menuCall(run, 0x42aa90, receiver, {command - 0x8050});
        break;
    case 0x807d:
        break;
    default: {
        if (stateQuery(run, receiver) != 3)
            return 0;
        uint32_t low = command & 0xffff;
        switch (low) {
        case 0x8043:
            run.put(0x537214, run.get(0x537214) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525be8, run.get(0x537214)});
            break;
        case 0x8047: {
            uint32_t toggle = run.get(0x537218) ^ 1;
            run.put(0x537228, 0);
            run.put(0x537218, toggle);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525bdc, run.get(0x537218)});
            break;
        }
        case 0x806a: {
            uint32_t toggle = run.get(0x537228) ^ 1;
            run.put(0x537218, 0);
            run.put(0x537228, toggle);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525bd0, run.get(0x537228)});
            break;
        }
        case 0x8044: {
            uint32_t player = run.get(0x537e88);
            if (player != 0)
                run.put(player + 0x10c, 100);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af70, receiver, {0x525bb8});
            break;
        }
        case 0x8045:
        case 0x8046:
        case 0x806c: {
            uint32_t player = run.get(0x537e88);
            if (player != 0) {
                uint32_t stats = run.get(run.get(player + 0x6c) + 0x14);
                if (low == 0x8045)
                    run.put(stats + 0x70, 99);
                else if (low == 0x8046)
                    run.put(stats + 0x74, 99);
                else
                    run.put(stats + 0x78, 99);
            }
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af70, receiver, {low == 0x8045 ? 0x525bc4u : low == 0x8046 ? 0x525bacu : 0x525b9cu});
            break;
        }
        case 0x8049:
            run.put(0x53721c, run.get(0x53721c) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525b88, run.get(0x53721c)});
            break;
        case 0x804a:
            run.put(0x537220, run.get(0x537220) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525b78, run.get(0x537220)});
            break;
        case 0x804b:
            run.put(0x537264, run.get(0x537264) ^ 0x10);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af90, receiver, {0x525b24, run.get(0x537264) & 0x10});
            break;
        case 0x804c:
            run.put(0x537264, run.get(0x537264) ^ 4);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af90, receiver, {0x525b38, run.get(0x537264) & 4});
            break;
        case 0x804d:
            run.put(0x537264, run.get(0x537264) ^ 1);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af90, receiver, {0x525b50, run.get(0x537264) & 1});
            break;
        case 0x804e:
            run.put(0x537264, run.get(0x537264) ^ 0x20);
            cheatSound(run, receiver, 0x525b68);
            break;
        case 0x804f:
            run.put(0x537224, run.get(0x537224) ^ 1);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af90, receiver, {0x525b10, run.get(0x537224)});
            break;
        case 0x805b:
        case 0x808d:
        case 0x808e:
        case 0x8091:
        case 0x8092:
        case 0x8093: {
            uint32_t kind = low == 0x805b ? 0x26bc : low == 0x808d ? 0x26b7 : low == 0x808e ? 0x26bd : low == 0x8091 ? 0x26ba : low == 0x8092 ? 0x26b8 : 0x26b9;
            menuCall(run, 0x41fc00, 0, {kind, low <= 0x808e ? 30000u : 20000u});
            cheatSound(run, receiver, 0x525bf4);
            uint32_t message = low == 0x805b ? 0x525b00 : low == 0x808d ? 0x525ae0 : low == 0x808e ? 0x525ab4 : low == 0x8091 ? 0x5258f0 : low == 0x8092 ? 0x525904 : 0x5258d4;
            menuCall(run, 0x42af70, receiver, {message});
            break;
        }
        case 0x8064:
        case 0x8065:
        case 0x8066:
            menuCall(run, low == 0x8064 ? 0x42a750 : low == 0x8065 ? 0x42a7b0 : 0x42a7f0, receiver);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af70, receiver, {low == 0x8064 ? 0x525aa0u : low == 0x8065 ? 0x525a88u : 0x525a6cu});
            break;
        case 0x8068:
            run.put(0x537264, (run.get(0x537264) ^ 0x40) & 0xfffffeff);
            menuCall(run, 0x4f650f, 0x5371ec);
            menuCall(run, 0x4f650f, 0x5371f0);
            cheatSound(run, receiver, 0x525b68);
            break;
        case 0x806f:
            run.put(0x537264, (run.get(0x537264) ^ 0x100) & 0xffffffbf);
            menuCall(run, 0x4f650f, 0x5371ec);
            cheatSound(run, receiver, 0x525b68);
            break;
        case 0x806e:
            run.put(0x537264, run.get(0x537264) ^ 0x80);
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af90, receiver, {0x525a54, run.get(0x537264) & 0x80});
            break;
        case 0x8071:
            run.put(0x53722c, run.get(0x53722c) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525a18, run.get(0x53722c)});
            break;
        case 0x8072:
            run.put(0x537230, run.get(0x537230) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525a00, run.get(0x537230)});
            break;
        case 0x807a:
        case 0x807b:
            cheatSound(run, receiver, 0x525b68);
            menuCall(run, 0x42af70, receiver, {0x525a2c});
            break;
        case 0x8079:
            postCommand(run, receiver, 0x802c);
            menuCall(run, 0x4a3920, 0, {run.automatic(-0x40), 0x5259d8, run.get(receiver + 0x78)});
            menuCall(run, 0x42af70, receiver, {run.automatic(-0x40)});
            break;
        case 0x8077:
        case 0x8078:
            run.put(0x537268, 1);
            postCommand(run, receiver, low == 0x8077 ? 0x802a : 0x802b);
            break;
        case 0x8076:
            if (s32(run.get(receiver + 0x7c)) <= 0x140) {
                postCommand(run, receiver, 0x802c);
                menuCall(run, 0x42af70, receiver, {0x525978});
            } else if (menuCall(run, 0x42a060, receiver, {0x140, 0xc8}) != 0) {
                menuCall(run, 0x42af70, receiver, {0x525994});
            } else if (menuCall(run, 0x42a060, receiver, {0x280, 0x1e0}) != 0) {
                menuCall(run, 0x42af70, receiver, {0x5259b4});
            } else {
                menuCall(run, 0x429e10, receiver, {0x8008, 0x403});
            }
            break;
        case 0x8086:
            if (menuCall(run, 0x42c2d0, receiver) != 0) {
                cheatSound(run, receiver, 0x525968);
                menuCall(run, 0x42af70, receiver, {0x525954});
                if (run.get(receiver + 0x14) != 0) {
                    uint32_t key = run.get(0x537260) == 0 ? 0x524d80 : 0x525948;
                    menuCall(run, 0x4b54f0, run.get(receiver + 0x50), {key, 1});
                }
            }
            break;
        case 0x8087:
            if (menuCall(run, 0x42c460, receiver) != 0) {
                cheatSound(run, receiver, 0x525b68);
                menuCall(run, 0x42af70, receiver, {0x52592c});
            }
            break;
        case 0x8088:
            menuCall(run, 0x42c6f0, receiver);
            break;
        case 0x8089:
            menuCall(run, 0x42c7d0, receiver);
            break;
        case 0x808a:
            menuCall(run, 0x42c8e0, receiver);
            break;
        case 0x808b:
            run.put(0x53726c, run.get(0x53726c) ^ 1);
            cheatSound(run, receiver, 0x525bf4);
            menuCall(run, 0x42af90, receiver, {0x525918, run.get(0x53726c)});
            if (run.get(0x53726c) != 0)
                menuCall(run, 0x440de0, 0);
            else
                menuCall(run, 0x440e00, 0);
            break;
        case 0x808f: {
            uint32_t state = run.get(receiver + 0x2c);
            if (state != 0 && menuCall(run, run.get(run.get(state) + 0x10), state) == 3) {
                cheatSound(run, receiver, 0x525b68);
                menuCall(run, 0x46e360, state);
            }
            break;
        }
        case 0x809c:
        case 0x809d:
        case 0x809e:
        case 0x809f:
        case 0x80a0:
        case 0x80a1:
        case 0x80a2:
        case 0x80a3:
        case 0x80a4:
        case 0x80a5:
        case 0x80a6:
        case 0x80a7:
        case 0x80a8:
        case 0x80a9: {
            uint32_t level = low - 0x809b;
            if (menuCall(run, 0x429b70, receiver, {level}) == 0) {
                uint32_t message = level <= 4 ? 0x406 + level : level <= 8 ? 0x4b0 + level : 0x6a9 + level;
                menuCall(run, 0x429e10, receiver, {0x8007, message});
            }
            break;
        }
        case 0x80aa: {
            uint32_t world = run.get(0x537960);
            if (world != 0) {
                uint32_t first = run.get(world + 0xb4);
                if (s32(first) > 0 && s32(run.get(world + 0xb8)) > 0) {
                    run.put(0x529fa0, first);
                    run.put(0x529fa4, run.get(world + 0xb8));
                    postCommand(run, receiver, 0x805c);
                }
            }
            break;
        }
        default:
            return 0;
        }
        break;
    }
    }
    if (error != 0)
        menuCall(run, 0x429e10, receiver, {0x8005, error});
    return 1;
}

// 0x42ba10. Application +0x64 is the active profile.
uint32_t function_42ba10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    if (s32(level) <= 0 || s32(level) > 14)
        return 0;
    if (level == 1)
        return 1;
    uint32_t profile = run.get(receiver + 0x64);
    if (profile == 0)
        return 0;
    uint32_t previous = level - 1;
    if (previous == 0)
        return 1;
    run.stackPointer = run.frame - 0x0c;
    uint32_t record = run.call(0x49ae60, profile, {previous, 3});
    if (record == 0)
        return 0;
    return (run.get(record) & 1) != 0;
}

// 0x42ba70.
uint32_t function_42ba70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t level = arguments[0];
    if (s32(level) <= 0 || s32(level) > 14)
        return 0;
    uint32_t profile = run.get(receiver + 0x64);
    if (profile == 0)
        return 0;
    if (level == 1 && arguments[1] == 0)
        return 1;
    run.stackPointer = run.frame - 0x0c;
    return run.call(0x49af30, profile, {level, arguments[1]}) != 0;
}

// 0x42bab0. Application +0x60 list; list +0x0c is the signed count.
uint32_t function_42bab0(Run &run, uint32_t receiver, const uint32_t *) {
    if (run.get(receiver + 0x64) == 0)
        return 0;
    return s32(run.get(run.get(receiver + 0x60) + 0x0c)) > 1;
}

// 0x42bad0. Profile +0x14 stores the name inline.
uint32_t function_42bad0(Run &run, uint32_t receiver, const uint32_t *) {
    uint32_t profile = run.get(receiver + 0x64);
    if (profile == 0)
        return 0;
    run.stackPointer = run.frame - 0x0c;
    return run.call(0x4a3cf0, 0, {profile + 0x14, 0x5255e8}) != 0;
}

// 0x4cd530. CFile at F-0x610, raw header at F-0x600,
// description at F-0x5f0. No bounds validation absent from the original.
uint32_t function_4cd530(Run &run, uint32_t, const uint32_t *arguments) {
    run.put(run.automatic(-0x08), 0x509a0b);
    run.put(run.automatic(-0x04), 0xffffffff);
    uint32_t path = arguments[0];
    uint32_t output = arguments[1];
    if (path == 0 || output == 0)
        return 0;
    uint32_t file = run.automatic(-0x610);
    run.stackPointer = run.frame - 0x620;
    run.call(0x4f72c9, file);
    run.put(run.automatic(-0x04), 0);
    run.stackPointer = run.frame - 0x62c;
    uint32_t opened = run.call(0x4f7448, file, {path, 0, 0});
    uint32_t success = 0;
    if (opened != 0) {
        run.stackPointer = run.frame - 0x628;
        uint32_t count = run.call(0x4f7570, file, {run.automatic(-0x600), 0x5f4});
        if (count == 0x5f4 && run.get(run.automatic(-0x600)) <= 0x5f4) {
            run.put(run.automatic(-0x04), 0xffffffff);
            uint32_t text = run.automatic(-0x5f0);
            uint32_t length = 0;
            while (run.get8(text + length) != 0)
                ++length;
            ++length;
            uint32_t offset = 0;
            while (offset < (length & 0xfffffffc)) {
                run.put(output + offset, run.get(text + offset));
                offset += 4;
            }
            while (offset < length) {
                run.put8(output + offset, run.get8(text + offset));
                ++offset;
            }
            success = 1;
        }
    }
    run.put(run.automatic(-0x04), 0xffffffff);
    run.stackPointer = run.frame - 0x620;
    run.call(0x4f7369, file);
    return success;
}

// 0x436e60. CString data is the incoming value, its physical argument slot
// is passed to the destructor. The owned reader is invoked in a nested frame.
uint32_t function_436e60(Run &run, uint32_t, const uint32_t *arguments) {
    uint32_t path = arguments[0];
    run.put(run.automatic(-0x08), 0x505ad8);
    run.put(run.automatic(-0x04), 0);
    uint32_t result = 0xffffffff;
    if (run.get(path - 0x08) != 0 && run.get(run.get(run.get(0x5371fc) + 0x30) + 0x24) != 0) {
        uint32_t parent = run.frame;
        uint32_t nestedArguments[2] = {path, run.automatic(-0x10c)};
        run.frame = parent - 0x11c;
        run.put(run.automatic(0x04), nestedArguments[0]);
        run.put(run.automatic(0x08), nestedArguments[1]);
        uint32_t success = function_4cd530(run, 0, nestedArguments);
        run.frame = parent;
        if (success != 0) {
            uint32_t text = run.automatic(-0x10c);
            uint32_t ch = run.get8(text);
            while (ch != 0 && (ch >= 0x80 || ch < 0x30 || ch > 0x39)) {
                ++text;
                ch = run.get8(text);
            }
            run.stackPointer = run.frame - 0x118;
            result = run.call(0x4a3ce0, 0, {text});
        }
    }
    run.put(run.automatic(-0x04), 0xffffffff);
    run.stackPointer = run.frame - 0x114;
    run.call(0x4f6584, run.automatic(0x04));
    return result;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x426e30:
        return function_426e30(run, receiver, arguments);
    case 0x42ba10:
        return function_42ba10(run, receiver, arguments);
    case 0x42ba70:
        return function_42ba70(run, receiver, arguments);
    case 0x42bab0:
        return function_42bab0(run, receiver, arguments);
    case 0x42bad0:
        return function_42bad0(run, receiver, arguments);
    case 0x436e60:
        return function_436e60(run, receiver, arguments);
    case 0x4cd530:
        return function_4cd530(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_menu_game_launch_entry, owned, body)
