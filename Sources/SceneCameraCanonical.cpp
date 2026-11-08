// Original scene input and camera runtime, recovered from the scene packet.
#include "ClawRuntime.hpp"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;

int owned(uint32_t function) {
    switch (function) {
    case 0x42d5f0: return 2;
    case 0x46c860: return 0;
    case 0x486240: return 1;
    case 0x486d30: return 0;
    case 0x486d70: return 1;
    case 0x4d0a60: return 0;
    case 0x4d0c50: return 1;
    default: return -1;
    }
}

struct Frame {
    Run &run;
    uint32_t previous;
    uint32_t outgoing;
    Frame(Run &run, uint32_t entry) : run(run), previous(run.frame), outgoing(run.stackPointer) {
        run.frame = entry;
        run.stackPointer = 0;
    }
    ~Frame() {
        run.frame = previous;
        run.stackPointer = outgoing;
    }
};

// 0x4d0a60. Plane +0x08 flags; +0x10/+0x14 coordinates; +0x30/+0x34 world size.
void clampPlane(Run &run, uint32_t plane) {
    uint32_t flags = run.get(plane + 0x08);
    for (uint32_t axis = 0; axis < 2; ++axis) {
        uint32_t position = plane + 0x10 + axis * 4;
        uint32_t dimension = plane + 0x30 + axis * 4;
        double value = run.getf(position);
        double minimum = run.getf(0x513d74);
        bool below = std::isnan(value) || std::isnan(minimum) || value < minimum;
        if (flags & (4u << axis)) {
            if (below) {
                double size = s32(run.get(dimension));
                do {
                    run.tick();
                    value += size;
                } while (std::isnan(value) || value < minimum);
                run.putf(position, float(value));
            }
            value = run.getf(position);
            double roundedSize = float(s32(run.get(dimension)));
            if (!std::isnan(value) && value >= roundedSize) {
                do {
                    run.tick();
                    value -= roundedSize;
                } while (!std::isnan(value) && value >= roundedSize);
                run.putf(position, float(value));
            }
        } else if (below) {
            run.put(position, 0);
        } else {
            uint32_t size = run.get(dimension);
            if (!(double(s32(size)) > value)) {
                run.putf(position, float(s32(size - 1)));
            }
        }
    }
    run.stackPointer = run.frame - 0x20;
    uint32_t x = run.call_x87(0x4a30e0, 0, run.getf(plane + 0x10));
    run.put(plane + 0x84, x);
    uint32_t y = run.call_x87(0x4a30e0, 0, run.getf(plane + 0x14));
    uint32_t left = x - run.get(plane + 0x78);
    run.put(plane + 0x88, y);
    run.put(plane + 0x40, left);
    if (s32(left) < 0) {
        run.put(plane + 0x40, flags & 4 ? run.get(plane + 0x30) + left : 0);
    }
    uint32_t top = y - run.get(plane + 0x7c);
    run.put(plane + 0x44, top);
    if (s32(top) < 0) {
        run.put(plane + 0x44, flags & 8 ? run.get(plane + 0x34) + top : 0);
    }
    left = run.get(plane + 0x40);
    uint32_t width = run.get(plane + 0x70);
    top = run.get(plane + 0x44);
    uint32_t height = run.get(plane + 0x74);
    uint32_t worldWidth = run.get(plane + 0x30);
    uint32_t right = left + width - 1;
    uint32_t bottom = top + height - 1;
    run.put(plane + 0x48, right);
    run.put(plane + 0x4c, bottom);
    if (s32(right) >= s32(worldWidth) && !(flags & 4)) {
        uint32_t distance = right - worldWidth + 1;
        run.put(plane + 0x48, right - distance);
        run.put(plane + 0x40, left - distance);
    }
    uint32_t worldHeight = run.get(plane + 0x34);
    if (s32(bottom) >= s32(worldHeight) && !(flags & 8)) {
        uint32_t distance = bottom - worldHeight + 1;
        run.put(plane + 0x4c, bottom - distance);
        run.put(plane + 0x44, top - distance);
    }
}

void setPlane(Run &run, uint32_t plane, uint32_t x, uint32_t y, uint32_t entry) {
    double fx = s32(x);
    double fy = s32(y);
    if (!(run.get8(plane + 0x08) & 1)) {
        fx *= run.getf(plane + 0x18);
        fy *= run.getf(plane + 0x1c);
    }
    run.putf(plane + 0x10, float(fx));
    run.putf(plane + 0x14, float(fy));
    Frame frame(run, entry);
    clampPlane(run, plane);
}

// 0x42d5f0 and the matching propagation sequence in 0x486d70.
// Scene +0x5c primary, +0x38 planes, +0x3c count, +0x60 primary index.
void propagate(Run &run, uint32_t scene, uint32_t x, uint32_t y, uint32_t childEntry) {
    setPlane(run, run.get(scene + 0x5c), x, y, childEntry);
    uint32_t primary = run.get(scene + 0x5c);
    x = run.get(primary + 0x84);
    y = run.get(primary + 0x88);
    if (s32(run.get(scene + 0x3c)) <= 0) {
        return;
    }
    uint32_t index = 0;
    do {
        if (index != run.get(scene + 0x60)) {
            uint32_t plane = run.get(run.get(scene + 0x38) + index * 4);
            setPlane(run, plane, x, y, childEntry);
        }
        ++index;
    } while (s32(index) < s32(run.get(scene + 0x3c)));
}

// 0x46c860. Scene +0x764 remaining input timeout, +4 application pointer.
void pollScene(Run &run, uint32_t scene) {
    run.stackPointer = run.frame - 0x08;
    if (run.get(run.get(run.get(scene + 0x04) + 0x4c) + 0x30)) {
        run.call(0x431300, run.get(0x537204));
        return;
    }
    uint32_t timeout = run.get(scene + 0x764);
    uint32_t elapsed = run.get(0x53720c);
    run.put(scene + 0x764, elapsed < timeout ? timeout - elapsed : 0);
    if (run.get(scene + 0x764)) {
        run.call(0x431300, run.get(0x537204));
        return;
    }
    run.call(0x430ec0, run.get(0x537204));
    if ((run.get(run.get(0x537200) + 0x210) & 0x100) && !run.get(0x537258)) {
        uint32_t application = run.get(scene + 0x04);
        uint32_t window = run.get(run.get(application + 0x04) + 0x04);
        run.stackPointer = run.frame - 0x18;
        run.icall(0x546d50, {window, 0x111, 0x8080, 0});
    }
}

// 0x486d30.
uint32_t unlockCamera(Run &run) {
    run.put(0x53c25c, 0);
    run.put(0x53c264, 0);
    return 1;
}

// 0x486d70.
uint32_t lockedCamera(Run &run, uint32_t object) {
    uint32_t target = run.get(0x53c264);
    if (target) {
        uint32_t current = run.get(run.get(0x537204) + 0x08);
        if (!(current & 3) && !(current & 0x0f000000)) {
            uint32_t indirect = run.get(target + 0x14);
            if (indirect) {
                target = run.get(indirect);
                if (target) {
                    uint32_t y = run.get(target + 0x50);
                    uint32_t x = run.get(target + 0x4c);
                    uint32_t scene = run.get(run.get(object + 0x0c) + 0x24);
                    propagate(run, scene, x, y, run.frame - 0x18);
                    return 1;
                }
            }
        }
    }
    unlockCamera(run);
    return 0;
}

uint32_t absolute(uint32_t value) {
    uint32_t sign = s32(value) < 0 ? 0xffffffff : 0;
    return (value ^ sign) - sign;
}

void targetPlayer(Run &run, uint32_t state, uint32_t adjustment = 0) {
    run.put(state + 0x08, run.get(run.get(0x537e88) + 0x4c));
    run.put(state + 0x0c, run.get(run.get(0x537e88) + 0x50) + adjustment);
}

void moveCamera(Run &run, uint32_t object, uint32_t logic, uint32_t state, uint32_t speed) {
    run.stackPointer = run.frame - 0x28;
    run.call(0x486940, 0, {object, logic, state, speed, speed});
}

void cameraHelper(Run &run, uint32_t function, uint32_t object, uint32_t logic, uint32_t state) {
    run.stackPointer = run.frame - 0x20;
    run.call(function, 0, {object, logic, state});
}

// 0x486240. Logic +0x14 private state and +0x1c state enum; private +0/+4
// current position, +8/+0xc target, +0x10 shake timer.
uint32_t camera(Run &run, uint32_t object) {
    if (!run.get(0x537e88)) {
        return 0;
    }
    if (run.get(0x53c25c)) {
        Frame frame(run, run.frame - 0x18);
        return lockedCamera(run, object);
    }
    uint32_t logic = run.get(object + 0x6c);
    uint32_t state = run.get(logic + 0x14);
    if (run.get(0x52be14) != 0xffffffff && run.get(logic + 0x1c)) {
        run.put(logic + 0x1c, 0x22b8);
    }
    uint32_t mode = run.get(logic + 0x1c);
    bool ordinary = false;
    bool initializing = false;
    if (!mode) {
        run.put(0x52be14, 0xffffffff);
        run.put(0x52be18, 0xffffffff);
        run.stackPointer = run.frame - 0x18;
        state = run.call(0x4f63ec, 0, {0x14});
        run.put(logic + 0x14, state);
        run.put(state, 0);
        run.put(state + 0x04, 0);
        run.put(state + 0x08, 0);
        run.put(state + 0x0c, 0);
        run.put(state + 0x10, 0);
        run.put(state, run.get(run.get(0x537e88) + 0x4c));
        run.put(state + 0x04, run.get(run.get(0x537e88) + 0x50));
        run.put(logic + 0x1c, 0x18);
        targetPlayer(run, state);
        targetPlayer(run, state);
        initializing = true;
        ordinary = true;
    } else if (mode == 0x18) {
        uint32_t playerLogic = run.get(run.get(0x537e88) + 0x6c);
        uint32_t playerState = run.get(playerLogic + 0x1c);
        if (playerState == 0x138c) {
            ordinary = false;
        } else if ((playerState == 0x1a || playerState == 0x138b) && !run.get(run.get(playerLogic + 0x14) + 0x110)) {
            run.put(logic + 0x1c, playerState);
            targetPlayer(run, state, playerState == 0x1a ? 200 : uint32_t(-200));
            cameraHelper(run, playerState == 0x1a ? 0x4868e0 : 0x486910, object, logic, state);
            moveCamera(run, object, logic, state, 250);
        } else {
            targetPlayer(run, state);
            ordinary = true;
        }
    } else if (mode == 0x1a || mode == 0x138b) {
        uint32_t playerLogic = run.get(run.get(0x537e88) + 0x6c);
        if (run.get(playerLogic + 0x1c) == mode && !run.get(run.get(playerLogic + 0x14) + 0x110)) {
            cameraHelper(run, mode == 0x1a ? 0x4868e0 : 0x486910, object, logic, state);
            moveCamera(run, object, logic, state, 250);
        } else {
            run.put(logic + 0x1c, 0x18);
            targetPlayer(run, state);
            cameraHelper(run, 0x486650, object, logic, state);
        }
    } else if (mode == 0x22b8) {
        if (run.get(0x52be14) != 0xffffffff) {
            moveCamera(run, object, logic, state, 400);
        } else {
            cameraHelper(run, 0x486620, object, logic, state);
            cameraHelper(run, 0x486650, object, logic, state);
        }
    }
    if (ordinary) {
        // Includes the original, unreachable state-24 override arm at 0x48644a.
        if (run.get(0x52be14) != 0xffffffff) {
            run.put(state + 0x08, run.get(0x52be14));
            run.put(state + 0x0c, run.get(0x52be18));
        }
        uint32_t x = run.get(state + 0x08);
        uint32_t y = run.get(state + 0x0c);
        if (s32(absolute(x - run.get(state))) > 500 || s32(absolute(y - run.get(state + 0x04))) > 500) {
            if (initializing) {
                run.put(state + 0x04, y);
                run.put(state, x);
            } else {
                run.put(state, x);
                run.put(state + 0x04, y);
            }
        }
        uint32_t movement = run.get(run.get(0x537e88) + 0xcc);
        moveCamera(run, object, logic, state, movement == 3 || movement == 4 ? 4000 : movement == 8 ? 99999 : 500);
    }
    if (run.get(0x5430c8) < run.get(0x53c260)) {
        cameraHelper(run, 0x486a00, object, logic, state);
    }
    if (state) {
        uint32_t y = run.get(state + 0x04);
        uint32_t scene = run.get(run.get(object + 0x0c) + 0x24);
        uint32_t x = run.get(state);
        Frame frame(run, run.frame - 0x1c);
        propagate(run, scene, x, y, run.frame - 0x10);
    }
    return 1;
}

// 0x4d0c50. Plane +0x50..+0x5c viewport, +0x70/+0x74 sizes and
// +0x78/+0x7c signed half sizes. CopyRect local is entry ESP-16.
void rectangle(Run &run, uint32_t plane, uint32_t input) {
    if (run.get(input) == 0x80000000) {
        return;
    }
    uint32_t local = run.automatic(-0x10);
    run.stackPointer = run.frame - 0x20;
    run.icall(0x546d58, {local, input});
    run.put(plane + 0x50, run.get(local));
    run.put(plane + 0x54, run.get(local + 0x04));
    run.put(plane + 0x58, run.get(local + 0x08));
    run.put(plane + 0x5c, run.get(local + 0x0c));
    uint32_t width = run.get(plane + 0x58) - run.get(plane + 0x50) + 1;
    uint32_t height = run.get(plane + 0x5c) - run.get(plane + 0x54) + 1;
    run.put(plane + 0x70, width);
    run.put(plane + 0x74, height);
    run.put(plane + 0x78, uint32_t(s32(width) / 2));
    run.put(plane + 0x7c, uint32_t(s32(height) / 2));
    Frame frame(run, run.frame - 0x18);
    clampPlane(run, plane);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x42d5f0:
        propagate(run, receiver, arguments[0], arguments[1], run.frame - 0x10);
        return 0;
    case 0x46c860:
        pollScene(run, receiver);
        return 0;
    case 0x486240:
        return camera(run, arguments[0]);
    case 0x486d30:
        return unlockCamera(run);
    case 0x486d70:
        return lockedCamera(run, arguments[0]);
    case 0x4d0a60:
        clampPlane(run, receiver);
        return 0;
    case 0x4d0c50:
        rectangle(run, receiver, arguments[0]);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_scene_camera_canonical_entry, owned, body)
