// v1.3 player movement and turbo selection, in the v1.3 object layout.
// Signed, read-modify-write and multi-field expressions remain literal so their
// exact access widths, evaluation order and legacy mutation sites stay visible.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include <cmath>

namespace {
using claw::Run;
using claw::s32;
using namespace claw::recovered::v13;
int owned(uint32_t function) {
    switch (function) {
    case 0x416ee0:
        return 1;
    case 0x4194d0:
    case 0x4198a0:
        return 3;
    default:
        return -1;
    }
}
uint32_t external(Run &run, uint32_t function, uint32_t receiver,
                  std::initializer_list<uint32_t> arguments = {}) {
    run.stackPointer = ((run.frame - 4) & ~7u) - 0x24 - 4u * uint32_t(arguments.size());
    return run.call(function, receiver, arguments);
}
uint32_t manager(Run &run, uint32_t actor) {
    MovementActorFields actorFields{run, actor};
    return run.get(actorFields.scene() + 0x24);
}
void zeroRemainders(Run &run) {
    for (uint32_t offset = 0; offset < 0x18; offset += 4) {
        run.put(0x532bb0 + offset, 0);
    }
}
void tickDown(Run &run, uint32_t address, uint32_t delta) {
    uint32_t value = run.get(address);
    run.put(address, delta < value ? value - delta : 0);
}
void doubleCall(Run &run, uint32_t function, uint32_t receiver, double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    external(run, function, receiver, {uint32_t(bits), uint32_t(bits >> 32)});
}
ClawX87State emptyFP() {
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x23f;
    return fp;
}
uint32_t exactCall(Run &run, uint32_t function, uint32_t receiver, ClawX87State &fp,
                   std::initializer_list<uint32_t> arguments = {}, uint32_t push = 0) {
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    fp.popCount = 0;
    fp.pushCount = push;
    run.stackPointer = ((run.frame - 4) & ~7u) - 0x24 - 4u * uint32_t(arguments.size());
    return run.call_x87_exact(function, receiver, fp, arguments);
}
ClawX87State updatePhysics(Run &run, ClawX87State fp = emptyFP()) {
    double delta = double(run.get(0x535924));
    uint64_t deltaBits;
    std::memcpy(&deltaBits, &delta, 8);
    run.x87_step(CLAW_X87_F64, fp, {uint32_t(deltaBits), uint32_t(deltaBits >> 32)});
    run.x87_step(CLAW_X87_MUL_F64, fp, {run.get(0x50c750), run.get(0x50c754)});
    uint64_t seconds = run.x87_step(CLAW_X87_STP_F64, fp);
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    fp.popCount = 0;
    fp.pushCount = 0;
    run.stackPointer = ((run.frame - 4) & ~7u) - 0x2c;
    run.call_x87_exact(0x403c30, 0x532af0, fp, {uint32_t(seconds), uint32_t(seconds >> 32)});
    return fp;
}
// Right uses 0x5aafd8; left uses 0x535924 in the original. Do not unify
// these countdown sources, or alter wrapped signed speed publication.
void selectSpeed(Run &run, uint32_t actor, uint32_t state, bool right) {
    MovementActorFields actorFields{run, actor};
    MovementPrivateFields stateFields{run, state};
    tickDown(run, state + 0x114, run.get(right ? 0x5aafd8 : 0x535924));
    actorFields.animationScaleBits(0x3f800000);
    uint32_t speed = right ? 225 : uint32_t(-225);
    if (run.get(0x532d34) == 0x26bc) {
        speed = right ? 300 : uint32_t(-300);
        actorFields.animationScaleBits(0x3f4ccccd);
    } else if (!stateFields.accelerationCountdown()) {
        speed = right ? 285 : uint32_t(-285);
        actorFields.animationScaleBits(0x3f666666);
    }
    if (run.get(0x535954)) {
        speed = right ? 450 : uint32_t(-450);
    }
    speed += stateFields.speedAdjustment();
    actorFields.horizontalSpeed(speed);
    run.putd(0x532b18, double(s32(speed)));
}
void platformDelta(Run &run, uint32_t actor, uint32_t &x, uint32_t &y) {
    MovementActorFields actorFields{run, actor};
    if (!(run.get8(actor + 0x08) & 0x10)) {
        return;
    }
    uint32_t platform = actorFields.platform();
    if (!platform) {
        return;
    }
    x += run.get(platform + 0x174);
    y += run.get(platform + 0x178);
}
uint32_t convertInteger(Run &run, ClawX87State &fp) {
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.stackPointer = ((run.frame - 4) & ~7u) - 0x24;
    return run.call_x87_exact(0x4a59d0, 0, fp);
}
// Keep all extended-precision x87 operations and original __ftol calls.
// Native truncation or a combined double expression changes residual motion.
uint32_t pixelX(Run &run, ClawX87State fp) {
    if (run.get(0x532ba8)) {
        return 0;
    }
    run.x87_step(CLAW_X87_F64, fp, {run.get(0x532b90), run.get(0x532b94)});
    uint32_t integral = convertInteger(run, fp);
    run.x87_step(CLAW_X87_I32, fp, {integral});
    run.x87_step(CLAW_X87_SUBR_F64, fp, {run.get(0x532b90), run.get(0x532b94)});
    run.x87_step(CLAW_X87_ADD_F64, fp, {run.get(0x532bb0), run.get(0x532bb4)});
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    run.x87_step(CLAW_X87_ADD_F64, fp, {run.get(0x532b90), run.get(0x532b94)});
    uint32_t result = convertInteger(run, fp);
    run.put(0x5acf24, result);
    run.x87_step(CLAW_X87_ST(CLAW_X87_LD_ST, 0), fp);
    uint32_t residualInteger = convertInteger(run, fp);
    run.x87_step(CLAW_X87_I32, fp, {residualInteger});
    run.x87_step(CLAW_X87_ST(CLAW_X87_SUBR_TO0, 1), fp);
    uint64_t remainder = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(0x532bb0, uint32_t(remainder));
    run.put(0x532bb4, uint32_t(remainder >> 32));
    run.x87_step(CLAW_X87_POP, fp);
    return result;
}
// 0x4194d0 and 0x4198a0. Actor +0x5c/+0x60 are position, +0x164 is horizontal speed;
// private +0x114 is the acceleration timer and +0x84 is the retained speed adjustment.
void walk(Run &run, uint32_t actor, uint32_t logic, uint32_t state, bool right) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    MovementPrivateFields stateFields{run, state};
    uint32_t x = actorFields.worldX();
    uint32_t y = actorFields.worldY();
    selectSpeed(run, actor, state, right);
    auto fp = updatePhysics(run);
    x += pixelX(run, fp);
    platformDelta(run, actor, x, y);
    external(run, 0x4cc7e0, manager(run, actor), {actor, x, y, 8});
    uint32_t movement = actorFields.movementMode();
    if (movement != 1) {
        if (movement != 4) {
            external(run, 0x4c8550, actor + 0x1a0, {run.get(0x5aafd8)});
            return;
        }
        uint32_t attack = stateFields.attackMode();
        if (attack == 8 || attack == 9 || attack == 10 || attack == 0x12) {
            uint32_t output = ((run.frame - 4) & ~7u) - 0x10;
            run.put(output, 0);
            external(run, 0x4fc6b4, run.get(actorFields.scene() + 0x2c) + 0x10, {0x52271c, output});
            stateFields.retainedAnimation(run.get(output));
        } else {
            external(run, 0x41d8a0, 0, {actor, logic, state});
            external(run, 0x4c6e40, actor, {0x52271c, 0});
        }
        logicFields.mode(0x19);
        actorFields.movementMode(4);
        actorFields.horizontalSpeed(0);
        actorFields.verticalSpeed(0);
        run.put(actor + 0x08, run.get(actor + 0x08) & 0xffffffef);
        bool facing = run.get(state) != 0;
        external(run, 0x421b80, actor, {facing ? uint32_t(-22) : uint32_t(-15), uint32_t(-45), facing ? 15u : 22u, 52});
        external(run, 0x4181c0, 0, {actor, state});
        stateFields.unknown_0x40(0);
        run.putd(0x532b20, 0);
        run.put(0x532b08, 0);
        run.put(0x532b0c, 0x40a19400);
        return;
    }
    uint32_t input = run.get(0x535918);
    run.put(input + 0x0c, run.get(input + 0x0c) & 0xfdffffff);
    input = run.get(0x535918);
    run.put(input + 0x0c, run.get(input + 0x0c) & 0xfeffffff);
    uint32_t speech = stateFields.speechActor();
    if (speech) {
        uint32_t owner = run.get(run.get(speech + 0x7c) + 0x18);
        external(run, 0x422260, owner, {0x421a80, 1});
        external(run, 0x422210, owner + 0x31c, {0});
        stateFields.speechActor(0);
    }
    stateFields.attackMode(0);
    stateFields.unknown_0x20(1);
    if (stateFields.unknown_0x4()) {
        stateFields.unknown_0x4(0);
        external(run, 0x421d10, actor, {stateFields.retainedAnimation(), 0});
        run.put(actor + 0x08, run.get(actor + 0x08) | 0x80);
    }
    logicFields.mode(0x18);
    external(run, 0x4c6e40, actor, {0x522710, 1});
    actorFields.movementMode(1);
    actorFields.horizontalSpeed(0);
    actorFields.verticalSpeed(0);
    actorFields.unknown_0x120(0);
    run.put(actor + 0x08, run.get(actor + 0x08) | 0x80);
    external(run, 0x418160, 0, {actor, state});
    external(run, 0x4181c0, 0, {actor, state});
    stateFields.unknown_0xfc(0x28a);
    stateFields.accelerationCountdown(0x5dc);
    stateFields.unknown_0x120(15000);
    stateFields.unknown_0x118(0);
    zeroRemainders(run);
    actorFields.animationScaleBits(0x3f800000);
}
void nestedWalk(Run &run, uint32_t actor, uint32_t logic, uint32_t state, bool right, bool transition) {
    uint32_t previous = run.frame;
    run.frame = ((previous - 4) & ~7u) - 0x30 - (transition ? 12 : 0);
    walk(run, actor, logic, state, right);
    run.frame = previous;
}

void callPlayer(Run &run, uint32_t function, uint32_t actor, uint32_t logic, uint32_t state, uint32_t retained = 0) {
    run.stackPointer = ((run.frame - 4) & ~7u) - 0x30 - retained;
    run.call(function, 0, {actor, logic, state});
}
// Repeated guest reads and forward word-copy loops retain callback and alias order.
void initialize(Run &run, uint32_t actor, uint32_t logic, uint32_t &state) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    run.put(0x52a314, 0xffffffff);
    run.put(0x52a318, 0xffffffff);
    logicFields.minimumX(50);
    uint32_t map = run.get(manager(run, actor) + 0x5c);
    logicFields.minimumY(50);
    logicFields.maximumX(run.get(map + 0x30) - 50);
    logicFields.maximumY(run.get(run.get(manager(run, actor) + 0x5c) + 0x34) - 50);
    if (!logicFields.privateState()) {
        uint32_t allocation = external(run, 0x4fcaea, 0, {0x138});
        logicFields.privateState(allocation);
        logicFields.privateStateBytes(0x138);
    }
    run.put(0x532d30, 0);
    run.put(0x532d34, 0);
    state = logicFields.privateState();
    MovementPrivateFields stateFields{run, state};
    for (uint32_t offset = 0; offset < 0x138; offset += 4) {
        run.put(state + offset, 0);
    }
    for (uint32_t offset = 0; offset < 0x138; offset += 4) {
        run.put(state + offset, run.get(0x532bf8 + offset));
    }
    run.put(actor + 0x128, run.get(state + 0x48));
    run.put(actor + 0x114, run.get(state + 0x44));
    map = run.get(manager(run, actor) + 0x5c);
    uint32_t x = run.get(map + 0x84);
    uint32_t y = run.get(map + 0x88);
    external(run, 0x4c6d60, actor, {0x521774, 11});
    actorFields.worldX(x);
    actorFields.worldY(y);
    external(run, 0x40fc00, actor, {4000});
    external(run, 0x4c7730, actor, {0x520ea0});
    run.put(actor + 0x08, (run.get(actor + 0x08) & 0xffffffef) | 0x80);
    actorFields.unknown_0xe8(2);
    actorFields.unknown_0xec(0x1b50544);
    actorFields.horizontalSpeed(0);
    actorFields.verticalSpeed(0);
    actorFields.unknown_0x110(1);
    actorFields.platform(0);
    external(run, 0x40fc20, actor, {uint32_t(-16), uint32_t(-52), 16, 60});
    external(run, 0x421b80, actor, {uint32_t(-25), uint32_t(-45), 12, 52});
    external(run, 0x4071a0, actor, {uint32_t(-15), uint32_t(-45), 22, 34});
    external(run, 0x4ce420, manager(run, actor), {actor});
    run.put(state, 0);
    stateFields.unknown_0x18(0);
    stateFields.unknown_0xe8(0);
    stateFields.unknown_0x2c(5);
    stateFields.unknown_0x4(0);
    stateFields.retainedAnimation(0);
    run.put(state + 0x4c, run.get(actor + 0x5c));
    run.put(state + 0x50, run.get(actor + 0x60));
    stateFields.unknown_0x110(0);
    stateFields.unknown_0x130(0);
    stateFields.unknown_0x134(0);
    stateFields.speechActor(0);
    stateFields.retainedAnimation(0);
    stateFields.unknown_0x128(0);
    stateFields.speedAdjustment(0);
    stateFields.unknown_0x11c(0);
    if (!stateFields.unknown_0x24()) {
        for (uint32_t offset = 0x88; offset < 0xb0; offset += 4) {
            run.put(state + offset, 0);
        }
    }
    run.put(state, 1);
    callPlayer(run, 0x4182e0, actor, logic, state);
    external(run, 0x406390, actor);
    run.put(state, 0);
    callPlayer(run, 0x419210, actor, logic, state);
    if (run.vcall(run.get(run.get(0x535910) + 0x2c), 0x10) == 4) {
        stateFields.unknown_0x7c(9);
    }
    external(run, 0x421d40, 0x532af0, {0,0,0,0,0,0,0,0,0,0x40a19400,0,0,0,0});
    run.put(0x532bc8, 0);
    run.put(0x532bcc, 0x40400000);
    run.put(0x532bd0, 0);
    run.put(0x532bd4, 0x40400000);
    external(run, 0x421de0, 0x532af0, {0,0x408f4000});
    external(run, 0x4e0aa0, run.get(0x535910));
    uint32_t animation = actorFields.animation();
    if (!run.get(0x532d3c) && animation) {
        static const uint32_t increments[] = {4,8,12,16,40,54,58};
        for (uint32_t i = 0; i < 7; ++i) {
            uint32_t frame = external(run, 0x40fbe0, animation, {0x17f + i});
            if (frame) {
                run.put(frame + 0x24, run.get(frame + 0x24) + increments[i]);
            }
        }
    }
    state = logicFields.privateState();
}
void respawn(Run &run, uint32_t actor, uint32_t logic, uint32_t state) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    MovementPrivateFields stateFields{run, state};
    run.put(0x52a314, 0xffffffff);
    run.put(0x52a318, 0xffffffff);
    uint32_t current = run.get(run.get(0x535910) + 0x2c);
    uint32_t x = run.get(current + 0x44);
    uint32_t y = run.get(current + 0x48);
    stateFields.health(100);
    actorFields.health(100);
    if (x == 0xffffffff || y == 0xffffffff) {
        x = stateFields.spawnX();
        y = stateFields.spawnY();
    }
    external(run, 0x4c6d60, actor, {0x521774, 11});
    actorFields.worldY(y);
    actorFields.worldX(x);
    external(run, 0x40fc00, actor, {4000});
    run.put(actor + 0x08, run.get(actor + 0x08) & 0xffbffffa);
    run.put(actor + 0xec, run.get(actor + 0xec) | 0x1000004);
    actorFields.horizontalSpeed(0);
    actorFields.verticalSpeed(0);
    run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffff6);
    external(run, 0x4ce420, manager(run, actor), {actor});
    callPlayer(run, 0x4182e0, actor, logic, state);
    logicFields.unknown_0x130(0);
    stateFields.unknown_0x2c(5);
    stateFields.retainedAnimation(0);
    stateFields.unknown_0x4(0);
    stateFields.unknown_0x18(0);
    stateFields.unknown_0x1c(0);
    stateFields.unknown_0x20(0);
    stateFields.speedAdjustment(0);
    stateFields.unknown_0x11c(0);
    if (run.get(actor + 0x5c) != run.get(state + 0x4c)) {
        external(run, 0x421c00, run.get(actorFields.scene() + 0x28), {0x5226f4});
    }
    if (run.vcall(run.get(run.get(0x535910) + 0x2c), 0x10) == 4) {
        stateFields.unknown_0x7c(9);
    }
    uint32_t next = run.get(0x53b130) + run.get(0x52abec);
    run.put(0x53b130, next);
    if (next < run.get(0x52abe4)) {
        run.put(0x53b130, run.get(0x52abe4));
    }
    external(run, 0x4e0aa0, run.get(0x535910));
    external(run, 0x420c70, 0, {actor, logic, state, 0, 0});
    uint32_t peer = run.get(0x532864);
    if (peer) {
        run.vcall(run.get(run.get(peer + 0x7c) + 0x18), 0xcc);
    }
}
void standWalk(Run &run, uint32_t actor, uint32_t logic, uint32_t state, bool right) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    MovementPrivateFields stateFields{run, state};
    callPlayer(run, 0x41d8a0, actor, logic, state);
    logicFields.mode(right ? 8 : 9);
    callPlayer(run, right ? 0x419210 : 0x419170, actor, logic, state);
    external(run, 0x4c6e40, actor, {0x5226dc, 0});
    actorFields.movementMode(2);
    actorFields.horizontalSpeed(right ? 225 : uint32_t(-225));
    actorFields.verticalSpeed(0);
    stateFields.unknown_0xf8(0);
    zeroRemainders(run);
    uint32_t x = actorFields.worldX();
    uint32_t y = actorFields.worldY();
    selectSpeed(run, actor, state, right);
    auto fp = updatePhysics(run);
    x += exactCall(run, 0x421f90, 0x532af0, fp);
    platformDelta(run, actor, x, y);
    external(run, 0x4cc7e0, manager(run, actor), {actor, x, y, 8});
    uint32_t movement = actorFields.movementMode();
    if (movement == 1) {
        callPlayer(run, 0x4182e0, actor, logic, state);
    } else if (movement == 4) {
        external(run, 0x418a00, 0, {actor, logic, state, 0});
    } else {
        external(run, 0x4c8550, actor + 0x1a0, {run.get(0x5aafd8)});
    }
}
void standJump(Run &run, uint32_t actor, uint32_t logic, uint32_t state) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    MovementPrivateFields stateFields{run, state};
    callPlayer(run, 0x41d8a0, actor, logic, state);
    logicFields.mode(4);
    external(run, 0x4c6e40, actor, {0x5226e8, 0});
    actorFields.movementMode(3);
    actorFields.horizontalSpeed(0);
    actorFields.verticalSpeed(0);
    run.put(actor + 0x08, run.get(actor + 0x08) & 0xffffffef);
    external(run, 0x418160, 0, {actor, state});
    external(run, 0x4181c0, 0, {actor, state});
    run.put(0x532b24, 0xc07f4000);
    if (run.get(0x532d34) != 0x26bc && stateFields.accelerationCountdown()) {
        run.put(0x532b24, 0xc07a9000);
    }
    run.put(0x532b20, 0);
    stateFields.unknown_0x118(250);
    stateFields.unknown_0x5c(0);
    run.put(state + 0x60, run.get(actor + 0x60));
    stateFields.unknown_0x10c(0);
    run.put(state + 0x64, run.get(actor + 0x60) - 45);
    run.put(0x532b08, 0);
    run.put(0x532b0c, 0x40a19400);
    run.putd(0x532b30, double(run.gets(actor + 0x5c)));
    run.putd(0x532b38, double(run.gets(actor + 0x60)));
    uint64_t xBits;
    uint64_t yBits;
    double xValue = run.getd(0x532b30);
    double yValue = double(run.gets(state + 0x64));
    std::memcpy(&xBits, &xValue, 8);
    std::memcpy(&yBits, &yValue, 8);
    auto fp = emptyFP();
    exactCall(run, 0x422070, 0x532af0, fp, {uint32_t(xBits), uint32_t(xBits >> 32), uint32_t(yBits), uint32_t(yBits >> 32), 0, 0}, 1);
    run.x87_step(CLAW_X87_POP, fp);
    uint32_t oldY = actorFields.worldY();
    uint32_t oldX = actorFields.worldX();
    callPlayer(run, 0x420850, actor, logic, state);
    uint32_t held = run.get(run.get(0x535918) + 0x08);
    if (held & 0x2000000) {
        callPlayer(run, 0x419210, actor, logic, state);
        actorFields.horizontalSpeed(225);
    } else if (held & 0x1000000) {
        callPlayer(run, 0x419170, actor, logic, state);
        actorFields.horizontalSpeed(uint32_t(-225));
    } else {
        actorFields.horizontalSpeed(0);
    }
    uint32_t speed = run.get(actor + 0x164) + run.get(state + 0x84);
    actorFields.horizontalSpeed(speed);
    run.putd(0x532b18, double(s32(speed)));
    fp = updatePhysics(run, fp);
    uint32_t dx = exactCall(run, 0x421f90, 0x532af0, fp);
    uint32_t dy = exactCall(run, 0x422000, 0x532af0, fp);
    uint32_t y = oldY + dy;
    run.put(state + 0x10c, run.get(state + 0x10c) + run.get(0x535924));
    if (run.getd(0x50c758) <= run.getd(0x532b20)) {
        doubleCall(run, 0x421f20, 0x532af0, double(run.gets(state + 0x64)));
        y = stateFields.jumpLimitY();
    }
    uint32_t mode = (run.get(run.get(0x535918) + 0x08) & 0x4000000) ? 0x11 : 0;
    uint32_t previousY = actorFields.worldY();
    if (s32(y) < run.gets(state + 0x64)) {
        y = stateFields.jumpLimitY();
    }
    external(run, 0x4cc7e0, manager(run, actor), {actor, oldX + dx, y, mode});
    run.put(state + 0x5c, run.get(state + 0x5c) + previousY - run.get(actor + 0x60));
    uint32_t movement = actorFields.movementMode();
    if (movement == 4) {
        external(run, 0x418a00, 0, {actor, logic, state, 0});
    } else if (movement == 6) {
        callPlayer(run, 0x418200, actor, logic, state);
    } else {
        if (!stateFields.unknown_0x4()) {
            external(run, 0x4c8550, actor + 0x1a0, {run.get(0x5aafd8)});
        } else {
            callPlayer(run, 0x41d960, actor, logic, state);
        }
        if (run.gets(actor + 0x60) <= run.gets(state + 0x64)) {
            external(run, 0x418a00, 0, {actor, logic, state, 1});
        }
    }
}
void standIdle(Run &run, uint32_t actor, uint32_t logic, uint32_t state) {
    MovementActorFields actorFields{run, actor};
    MovementHolderFields logicFields{run, logic};
    MovementPrivateFields stateFields{run, state};
    bool teeter = false;
    if (run.get8(actor + 0x08) & 0x10) {
        teeter = external(run, 0x40b620, 0) != 0;
    } else {
        uint32_t collision = manager(run, actor);
        if (external(run, 0x4cddf0, collision, {actor, actorFields.hitRight()})) {
            uint32_t left = actorFields.hitLeft();
            uint32_t probe = actorFields.hitRight() - 12;
            if (s32(left) < s32(probe)) {
                bool supported = false;
                do {
                    if (external(run, 0x4cddf0, collision, {actor, probe})) {
                        supported = true;
                        break;
                    }
                    probe -= 4;
                } while (s32(left) < s32(probe));
                if (!supported) {
                    teeter = external(run, 0x4cddf0, collision, {actor, left}) == 0;
                }
            }
        }
    }
    if (teeter) {
        if (run.get(state)) {
            run.put(actor + 0x40, run.get(actor + 0x40) | 2);
            external(run, 0x406390, actor);
            run.put(state, 0);
            stateFields.accelerationCountdown(1500);
        }
        callPlayer(run, 0x41d8a0, actor, logic, state);
        logicFields.mode(0x138e);
        external(run, 0x4c6e40, actor, {0x5226d0, 1});
        actorFields.movementMode(1);
        actorFields.horizontalSpeed(0);
        actorFields.verticalSpeed(0);
        stateFields.accelerationCountdown(1500);
        if (s32(external(run, 0x4a595b, 0)) % 100 < 45) {
            external(run, 0x48fb00, 0, {0x5226c4, 0});
        }
        uint32_t mode = 0x18;
        actorFields.horizontalSpeed(0);
        actorFields.verticalSpeed(0);
        uint32_t held = run.get(run.get(0x535918) + 0x08);
        if (held & 0x4000000) {
            mode = 0x19;
        } else if (held & 0x8000000) {
            mode = 0x1a;
        }
        uint32_t x = actorFields.worldX();
        uint32_t y = actorFields.worldY();
        platformDelta(run, actor, x, y);
        external(run, 0x4cc7e0, manager(run, actor), {actor, x, y, mode});
        uint32_t movement = actorFields.movementMode();
        if (movement == 4) {
            external(run, 0x418a00, 0, {actor, logic, state, 0});
        } else if (movement == 6) {
            callPlayer(run, 0x418200, actor, logic, state);
        } else {
            external(run, 0x4c8550, actor + 0x1a0, {run.get(0x5aafd8)});
        }
        uint32_t supported = external(run, run.get(state) ? 0x41fb40 : 0x41fbc0, 0, {actor});
        if (!supported) {
            callPlayer(run, 0x4182e0, actor, logic, state);
        }
        return;
    }
    if (!external(run, 0x41fb40, 0, {actor})) {
        callPlayer(run, 0x41ec30, actor, logic, state);
        callPlayer(run, 0x41a160, actor, logic, state);
    } else {
        callPlayer(run, 0x419210, actor, logic, state);
        callPlayer(run, 0x418590, actor, logic, state, 12);
        callPlayer(run, 0x41ae00, actor, logic, state, 24);
    }
}
void activeWalk(Run &run, uint32_t actor, uint32_t logic, uint32_t state, bool right) {
    uint32_t held = run.get(run.get(0x535918) + 0x08);
    if (held & 0x8000000 || !(held & (0x1000000 | 0x2000000))) {
        callPlayer(run, 0x4182e0, actor, logic, state);
        callPlayer(run, 0x41a160, actor, logic, state, 12);
    } else if (right) {
        if (held & 0x2000000) {
            nestedWalk(run, actor, logic, state, true, false);
        } else {
            callPlayer(run, 0x418ec0, actor, logic, state);
            nestedWalk(run, actor, logic, state, false, true);
        }
    } else if (held & 0x1000000) {
        nestedWalk(run, actor, logic, state, false, false);
    } else {
        callPlayer(run, 0x419010, actor, logic, state);
        nestedWalk(run, actor, logic, state, true, true);
    }
    if (external(run, 0x41ec30, 0, {actor, logic, state})) {
        callPlayer(run, 0x418490, actor, logic, state);
    } else if (run.get8(run.get(0x535918) + 0x04) & 1) {
        callPlayer(run, 0x4186a0, actor, logic, state);
    }
}
// 0x416ee0. Read the holder/mode/private token at the original entry points.
// Dispatch may replace private state, so its tail view is constructed afterwards.
uint32_t player(Run &run, uint32_t actor) {
    MovementActorFields actorFields{run, actor};
    uint32_t logic = actorFields.logicHolder();
    MovementHolderFields logicFields{run, logic};
    uint32_t mode = logicFields.mode();
    uint32_t state = logicFields.privateState();
    switch (mode) {
    case 0:
        initialize(run, actor, logic, state);
        break;
    case 4:
        callPlayer(run, 0x41ec30, actor, logic, state);
        callPlayer(run, 0x41ca10, actor, logic, state, 12);
        break;
    case 8:
    case 9:
        activeWalk(run, actor, logic, state, mode == 8);
        break;
    case 0x17:
        respawn(run, actor, logic, state);
        break;
    case 0x18: {
        uint32_t pressed = run.get(run.get(0x535918) + 0x04);
        if ((!run.get(state + 0x04) || run.get(state + 0x20)) && (pressed & 1)) {
            standJump(run, actor, logic, state);
        } else if ((!run.get(state + 0x04) || run.get(state + 0x20)) && (pressed & 0x2000000)) {
            standWalk(run, actor, logic, state, true);
        } else if ((!run.get(state + 0x04) || run.get(state + 0x20)) && (pressed & 0x1000000)) {
            standWalk(run, actor, logic, state, false);
        } else {
            standIdle(run, actor, logic, state);
        }
        break;
    }
    case 0x19:
        callPlayer(run, 0x41ec30, actor, logic, state);
        callPlayer(run, 0x419c70, actor, logic, state, 12);
        break;
    case 0x1a:
        callPlayer(run, 0x41ec30, actor, logic, state);
        callPlayer(run, 0x41b340, actor, logic, state, 12);
        break;
    case 0x1b:
        callPlayer(run, 0x41cf40, actor, logic, state);
        break;
    case 0x1f:
        callPlayer(run, 0x41d3f0, actor, logic, state);
        break;
    case 0x1388:
        callPlayer(run, 0x41bbc0, actor, logic, state);
        break;
    case 0x1389:
        callPlayer(run, 0x41c640, actor, logic, state);
        break;
    case 0x138a:
        callPlayer(run, 0x41aa40, actor, logic, state);
        break;
    case 0x138b:
        if (!(run.get8(run.get(0x535918) + 0x04) & 1)) {
            callPlayer(run, 0x41b7e0, actor, logic, state);
            break;
        }
        callPlayer(run, 0x4186a0, actor, logic, state);
        callPlayer(run, 0x41ca10, actor, logic, state, 12);
        break;
    case 0x138c:
        callPlayer(run, 0x41d670, actor, logic, state);
        break;
    case 0x138d:
        callPlayer(run, 0x41d800, actor, logic, state);
        break;
    case 0x138e:
        if (run.get8(run.get(0x535918) + 0x04) & 1) {
            callPlayer(run, 0x4186a0, actor, logic, state);
            callPlayer(run, 0x41ca10, actor, logic, state, 12);
        } else if (run.get(run.get(0x535918) + 0x08) & 0x2000000) {
            callPlayer(run, 0x419010, actor, logic, state);
            nestedWalk(run, actor, logic, state, true, true);
        } else if (run.get(run.get(0x535918) + 0x08) & 0x1000000) {
            callPlayer(run, 0x418ec0, actor, logic, state);
            nestedWalk(run, actor, logic, state, false, true);
        } else {
            callPlayer(run, 0x41ae00, actor, logic, state);
        }
        break;
    case 0x138f:
        callPlayer(run, 0x4192b0, actor, logic, state);
        break;
    case 0x1391:
        callPlayer(run, 0x41b150, actor, logic, state);
        break;
    default:
        break;
    }
    MovementPrivateFields stateFields{run, state};
    if ((run.get8(run.get(0x535918) + 0x04) & 8) && !stateFields.unknown_0x4()) {
        uint32_t weapon = stateFields.weapon() + 1;
        stateFields.weapon(weapon);
        if (s32(weapon) > 3) {
            stateFields.weapon(1);
        }
        external(run, 0x421c00, run.get(actorFields.scene() + 0x28), {0x5226b8});
    }
    uint32_t remaining = logicFields.unknown_0x130();
    if (remaining) {
        uint32_t delta = run.get(0x535924);
        if (delta < remaining) {
            logicFields.unknown_0x130(remaining - delta);
        } else {
            logicFields.unknown_0x130(0);
            run.put(actor + 0xec, run.get(actor + 0xec) | 0x1000004);
            run.put(actor + 0x40, run.get(actor + 0x40) & 0xfffffff7);
        }
    }
    tickDown(run, state + 0xf8, run.get(0x535924));
    tickDown(run, state + 0x11c, run.get(0x535924));
    external(run, 0x420f10, 0, {actor, logic, state, run.get(0x535924)});
    if (logicFields.mode() != 0x138c) {
        uint32_t x = actorFields.worldX();
        if (s32(x) < run.gets(logic + 0x2c)) {
            x = logicFields.minimumX();
        }
        if (run.gets(logic + 0x30) < s32(x)) {
            x = logicFields.maximumX();
        }
        uint32_t y = actorFields.worldY();
        if (s32(y) < run.gets(logic + 0x34)) {
            y = logicFields.minimumY();
        }
        if (run.gets(logic + 0x38) < s32(y)) {
            y = logicFields.maximumY();
        }
        actorFields.worldX(x);
        actorFields.worldY(y);
    }
    uint32_t flags = actorFields.flags();
    bool clearFlag = true;
    if (!run.get(0x535948)) {
        if (!(flags & 0x400000)) {
            if ((flags & 0x10) && external(run, 0x4ce360, manager(run, actor), {actor, 0}) == 4 &&
                    run.get(logic + 0x1c) != 0x138c && run.get(logic + 0x1c) != 0x138d) {
                callPlayer(run, 0x418d20, actor, logic, state);
            }
            clearFlag = false;
        } else {
            if (run.get(logic + 0x1c) != 0x138c && run.get(logic + 0x1c) != 0x138d) {
                callPlayer(run, 0x418d20, actor, logic, state);
            }
            flags = actorFields.flags();
        }
    }
    if (clearFlag) {
        actorFields.flags(flags & 0xffbfffff);
    }
    if (run.get(0x53592c)) {
        actorFields.health(100);
        stateFields.unknown_0x70(99);
        stateFields.unknown_0x74(99);
        stateFields.unknown_0x78(99);
        stateFields.unknown_0x7c(10);
    }
    return 1;
}
// Original cdecl entry 0x416ee0, one actor argument and u32 result.
uint32_t updateTurboPlayer(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return player(run, arguments[0]);
}
// Original cdecl entries 0x4194d0 / 0x4198a0, actor/holder/private-state order.
uint32_t advanceWalkRight(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    walk(run, arguments[0], arguments[1], arguments[2], true);
    return 0;
}
uint32_t advanceWalkLeft(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    walk(run, arguments[0], arguments[1], arguments[2], false);
    return 0;
}
struct MovementEntry {
    uint32_t address;
    uint32_t (*implementation)(Run &, uint32_t, const uint32_t *);
};
const MovementEntry movementEntries[] = {
    {0x416ee0, updateTurboPlayer},
    {0x4194d0, advanceWalkRight},
    {0x4198a0, advanceWalkLeft},
};
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (function == 0x416ee0) {
        return movementEntries[0].implementation(run, receiver, arguments);
    }
    return movementEntries[function == 0x4194d0 ? 1 : 2].implementation(run, receiver, arguments);
}
}
CLAW_MODULE_ENTRY(claw_v13_cheat_movement_entry, owned, body)
