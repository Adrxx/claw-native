#include "BossStagerPlayerResetOwner.h"
#include <cstring>
extern "C" uint32_t claw_boss_stager_player_reset_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
extern "C" uint32_t claw_rat_bomb_canonical_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
namespace {
struct Owner {
    ClawHost *memory;
    ClawHost host{};
    ClawSceneActorHost scene;
    ClawActorAnimationGlobals *animation;
    ClawLiftThrowGlobals liftGlobals{};
    ClawLiftThrowContext lift{};
    uint32_t *fault;
    void fail(uint32_t value = CLAW_FAULT_HOST) {
        if (!*fault)
            *fault = value;
        host.fault = *fault;
    }
};
uint8_t *bytes(void *user, uint32_t token, uint32_t count) {
    auto &o = *static_cast<Owner *>(user);
    auto *p = o.memory->bytes ? o.memory->bytes(o.memory->user, token, count) : nullptr;
    if (!p)
        o.fail(CLAW_FAULT_MEMORY);
    return p;
}
uint64_t liftPhysical(ClawLiftThrowContext *, const ClawLiftThrowCall *call, void *user) {
    auto &o = *static_cast<Owner *>(user);
    // Only malloc is reachable from the elected bit-zero expansion. There is
    // no general game-code callback or guest fallback on this boundary.
    if (call->function == 0x4a48e0 && call->receiver == 0 && call->argumentCount == 1 && o.scene.allocate)
        return o.scene.allocate(o.scene.context, call->arguments[0]);
    o.fail();
    return 0;
}
uint32_t dispatch(void *user, const ClawCall *call) {
    auto &o = *static_cast<Owner *>(user);
    if (*o.fault || !call)
        return 0;
    const uint32_t f = call->function;
    uint32_t result = 0, completed = 0, childFault = 0;
    switch (f) {
    case 0x4dbd20:
    case 0x41c4e0:
        // Cleanup rereads the same live input pointer as the root.
        if (f == 0x41c4e0) {
            auto *input = bytes(&o, 0x537204, 4);
            if (!input)
                break;
            std::memcpy(&o.liftGlobals.inputToken, input, 4);
        }
        completed = claw_lift_throw_entry(f, call->receiver, call->arguments, call->argumentCount,
            &o.lift, liftPhysical, &o, &result);
        childFault = o.lift.fault;
        break;
    case 0x4c8220:
    case 0x4c79e0:
        if (call->argumentCount != (f == 0x4c8220 ? 1u : 2u)) {
            o.fail(CLAW_FAULT_ABI);
            break;
        }
        completed = claw_actor_animation_entry(f, call->receiver, call->arguments[0], call->arguments[1],
            o.animation, o.scene, &childFault, &result);
        break;
    case 0x4208b0: {
        ClawRauxGlobals globals{};
        ClawRauxContext context{};
        context.scene = o.scene;
        context.globals = &globals;
        completed = claw_raux_entry(f, call->receiver, call->arguments, call->argumentCount,
            &context, nullptr, nullptr, &result);
        childFault = context.fault;
        break;
    }
    case 0x4170b0: {
        // The retained portable owner accepts actor only. The original also
        // reads private[0] (its TEST has no observable output) before bounds.
        if (call->receiver || call->argumentCount != 2) {
            o.fail(CLAW_FAULT_ABI);
            break;
        }
        if (!bytes(&o, call->arguments[1], 4))
            break;
        ClawPowerupObjectContext context{};
        context.scene = o.scene;
        ClawPowerupObjectArguments args{};
        args.words[0] = call->arguments[0];
        args.count = 1;
        completed = claw_powerup_object_entry(f, 0, args, &context, nullptr, nullptr, &result);
        childFault = context.fault;
        break;
    }
    case 0x406150:
    case 0x406180: {
        const uint32_t parentFrame = o.host.entryStackPointer;
        o.host.entryStackPointer = call->stackPointer;
        completed = claw_rat_bomb_canonical_entry(f, call->receiver, call->arguments,
            call->argumentCount, &o.host, &result);
        childFault = o.host.fault;
        o.host.entryStackPointer = parentFrame;
        break;
    }
    default:
        o.fail(CLAW_FAULT_UNIMPLEMENTED);
        break;
    }
    if (!completed || childFault)
        o.fail(childFault ? childFault : CLAW_FAULT_HOST);
    return result;
}
}
extern "C" uint32_t claw_boss_stager_player_reset_source(ClawHost *memory, ClawSceneActorHost scene,
    ClawActorAnimationGlobals *animation, uint32_t *fault) {
    if (!memory || !fault || *fault || memory->fault || !animation || !scene.lookup ||
        memory->compilerContext || memory->sourceContext || memory->guestSession)
        return 0;
    Owner o{memory, {}, scene, animation, {}, {}, fault};
    o.host.user = &o;
    o.host.bytes = bytes;
    o.host.call = dispatch;
    o.host.maximumOperations = memory->maximumOperations;
    o.host.remainingOperations = memory->remainingOperations;
    o.host.entryStackPointer = memory->entryStackPointer;
    o.lift.scene = scene;
    o.lift.globals = &o.liftGlobals;
    uint32_t result = 0;
    const uint32_t completed = claw_boss_stager_player_reset_entry(0x420170, 0, nullptr, 0, &o.host, &result);
    if (o.host.fault)
        o.fail(o.host.fault);
    return completed && !*fault;
}
