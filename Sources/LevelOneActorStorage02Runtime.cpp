// Canonical adaptation of the legacy actor-interaction and sprite projection
// algorithms, preserving the original guest-memory loads and callback order.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {
using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

int owned(uint32_t function) {
    switch (function) {
    case 0x4c9390:
        return 0;
    case 0x4c95b0:
    case 0x4c96d0:
    case 0x4c9f80:
    case 0x4ca230:
        return 2;
    case 0x4c9ae0:
    case 0x4caaa0:
        return 1;
    default:
        return -1;
    }
}

// 0x4ca230. Inclusive signed rectangle overlap; all sums wrap at 32 bits.
uint32_t rectangleOverlap(Run &run, uint32_t a, uint32_t b) {
    InteractionRectangleFields firstRectangle{run, a};
    InteractionRectangleFields secondRectangle{run, b};
    uint32_t firstLeft = firstRectangle.left();
    uint32_t secondRight = secondRectangle.right();
    if (s32(firstLeft) > s32(secondRight))
        return 0;
    uint32_t firstRight = firstRectangle.right();
    uint32_t secondLeft = secondRectangle.left();
    if (s32(firstRight) < s32(secondLeft))
        return 0;
    uint32_t firstTop = firstRectangle.top();
    uint32_t secondBottom = secondRectangle.bottom();
    if (s32(firstTop) > s32(secondBottom))
        return 0;
    uint32_t firstBottom = firstRectangle.bottom();
    uint32_t secondTop = secondRectangle.top();
    return s32(firstBottom) >= s32(secondTop);
}

// 0x4c95b0. Actor +0x128 hit bounds, +0x138 attack bounds;
// +0x4c/+0x50 world position. INT_MIN left edge disables a rectangle.
uint32_t actorOverlap(Run &run, uint32_t defender, uint32_t attacker) {
    ActorInteractionFields defenderFields{run, defender};
    ActorInteractionFields attackerFields{run, attacker};
    uint32_t attackerLeft = attackerFields.attackLeft();
    if (attackerLeft == 0x80000000u)
        return 0;
    uint32_t defenderLeft = defenderFields.hitLeft();
    if (defenderLeft == 0x80000000u)
        return 0;
    uint32_t defenderX = defenderFields.worldX();
    uint32_t defenderY = defenderFields.worldY();
    defenderLeft += defenderX;
    uint32_t defenderTop = defenderFields.hitTop();
    uint32_t defenderRight = defenderFields.hitRight();
    uint32_t defenderBottom = defenderFields.hitBottom();
    defenderRight += defenderX;
    uint32_t attackerX = attackerFields.worldX();
    defenderTop += defenderY;
    attackerLeft += attackerX;
    uint32_t attackerY = attackerFields.worldY();
    defenderBottom += defenderY;
    uint32_t attackerBottom = attackerFields.attackBottom();
    uint32_t attackerTop = attackerFields.attackTop();
    uint32_t attackerRight = attackerFields.attackRight();
    attackerTop += attackerY;
    attackerBottom += attackerY;
    attackerRight += attackerX;
    return s32(defenderLeft) <= s32(attackerRight) && s32(defenderRight) >= s32(attackerLeft) && s32(defenderTop) <= s32(attackerBottom) && s32(defenderBottom) >= s32(attackerTop);
}

// 0x4c9ae0. Actor +0x08 flags, +0x104 damage, +0x10c health;
// +0x6c primary logic, +0x70 hit logic, +0x74 peer, logic +0x1c state.
uint32_t hurt(Run &run, uint32_t defender, uint32_t attacker) {
    ActorInteractionFields defenderFields{run, defender};
    ActorInteractionFields attackerFields{run, attacker};
    ActorFlagByteFields defenderFlags{run, defender};
    ActorStorageFields defenderStorage{run, defender};
    ActorFields defenderActor{run, defender};
    if (defenderFlags.flags() & 8) {
        uint32_t damage = attackerFields.damage();
        uint32_t health = defenderFields.health() - damage;
        defenderFields.health(health);
        if (s32(health) <= 0) {
            uint32_t holder = defenderActor.holder();
            LogicHolderFields holderFields{run, holder};
            holderFields.state(0x1c);
        }
    } else {
        uint32_t logic = defenderStorage.secondaryHolder();
        if (logic) {
            defenderFields.hitPeer(attacker);
            // +0x10 is the function itself, not another vtable indirection.
            InteractionCallbackFields callbackFields{run, logic};
            uint32_t callback = callbackFields.function();
            run.call(callback, 0, {defender});
        }
    }
    return 0;
}

// Actor +0x78 contact logic and +0x7c contact peer; callbacks are cdecl1.
void contact(Run &run, uint32_t actor, uint32_t peer) {
    ActorStorageFields actorStorage{run, actor};
    ActorInteractionFields actorFields{run, actor};
    uint32_t logic = actorStorage.contactHolder();
    if (logic) {
        actorFields.contactPeer(peer);
        InteractionCallbackFields callbackFields{run, logic};
        uint32_t callback = callbackFields.function();
        run.call(callback, 0, {actor});
    }
}

// 0x4c9390. Scene +0x14 list head; node +0 next, +0x08 actor.
// Actor +0xd0/+0xd4/+0xd8 select interaction masks.
uint32_t interactions(Run &run, uint32_t scene) {
    // Preload each next node before callbacks; re-read flags/masks afterward.
    ActorContainerFields containerFields{run, scene};
    uint32_t nextOuterNode = containerFields.head();
    while (nextOuterNode) {
        ActorListNodeFields outerNode{run, nextOuterNode};
        uint32_t firstActorToken = outerNode.actor();
        nextOuterNode = outerNode.next();
        ActorInteractionFields firstActor{run, firstActorToken};
        ActorFlagByteFields firstFlags{run, firstActorToken};
        if (firstFlags.flags() & 1)
            continue;
        uint32_t nextInnerNode = nextOuterNode;
        while (nextInnerNode) {
            ActorListNodeFields innerNode{run, nextInnerNode};
            uint32_t secondActorToken = innerNode.actor();
            nextInnerNode = innerNode.next();
            ActorInteractionFields secondActor{run, secondActorToken};
            ActorFlagByteFields secondFlags{run, secondActorToken};
            uint32_t secondActorFlags = secondActor.flags();
            if (secondActorFlags & 1)
                continue;
            uint32_t firstActorFlags = firstActor.flags();
            if ((secondActorFlags ^ firstActorFlags) & 0x40000)
                continue;
            if (!(firstActorFlags & 4) && !(secondActorFlags & 0x80)) {
                uint32_t hitFirst = firstActor.unknown_0xd4();
                uint32_t hitSecond = secondActor.unknown_0xd0();
                uint32_t hitMask = hitFirst & hitSecond;
                uint32_t contactFirst = firstActor.unknown_0xd0();
                uint32_t contactSecond = secondActor.unknown_0xd8();
                uint32_t contactMask = contactFirst & contactSecond;
                if (hitMask || contactMask) {
                    uint32_t attackerLeft = secondActor.attackLeft();
                    uint32_t overlap = 0;
                    if (attackerLeft != 0x80000000u) {
                        uint32_t defenderLeft = firstActor.hitLeft();
                        if (defenderLeft != 0x80000000u) {
                            uint32_t defenderRectangle = run.automatic(-0x10);
                            uint32_t attackerRectangle = run.automatic(-0x20);
                            uint32_t defenderX = firstActor.worldX();
                            uint32_t defenderTop = firstActor.hitTop();
                            run.put(defenderRectangle, defenderLeft + defenderX);
                            uint32_t defenderY = firstActor.worldY();
                            run.put(defenderRectangle + 0x04, defenderTop + defenderY);
                            uint32_t defenderRight = firstActor.hitRight() + defenderX;
                            uint32_t defenderBottom = firstActor.hitBottom() + defenderY;
                            run.put(defenderRectangle + 0x08, defenderRight);
                            run.put(defenderRectangle + 0x0c, defenderBottom);
                            uint32_t attackerX = secondActor.worldX();
                            uint32_t attackerTop = secondActor.attackTop();
                            run.put(attackerRectangle, attackerX + attackerLeft);
                            uint32_t attackerY = secondActor.worldY();
                            run.put(attackerRectangle + 0x04, attackerTop + attackerY);
                            uint32_t attackerRight = secondActor.attackRight() + attackerX;
                            uint32_t attackerBottom = secondActor.attackBottom() + attackerY;
                            run.put(attackerRectangle + 0x08, attackerRight);
                            run.put(attackerRectangle + 0x0c, attackerBottom);
                            overlap = rectangleOverlap(run, defenderRectangle, attackerRectangle);
                        }
                    }
                    if (overlap) {
                        if (contactMask)
                            contact(run, secondActorToken, firstActorToken);
                        if (hitMask)
                            hurt(run, firstActorToken, secondActorToken);
                    }
                }
            }
            if (!(secondFlags.flags() & 4) &&
                !(firstFlags.flags() & 0x80)) {
                uint32_t hitFirst = firstActor.unknown_0xd0();
                uint32_t hitSecond = secondActor.unknown_0xd4();
                uint32_t hitMask = hitFirst & hitSecond;
                uint32_t contactFirst = firstActor.unknown_0xd8();
                uint32_t contactSecond = secondActor.unknown_0xd0();
                uint32_t contactMask = contactFirst & contactSecond;
                if ((hitMask || contactMask) && actorOverlap(run, secondActorToken, firstActorToken)) {
                    if (contactMask)
                        contact(run, firstActorToken, secondActorToken);
                    if (hitMask)
                        hurt(run, secondActorToken, firstActorToken);
                }
            }
        }
    }
    return 0;
}

// 0x4c96d0. Projection +0x30/+0x34 extents, +0x40/+0x44 camera,
// +0x48/+0x4c visible ends, +0x50/+0x54 screen offsets.
uint32_t project(Run &run, uint32_t projection, uint32_t x, uint32_t y) {
    // Outputs may alias this record or each other. Preserve all reloads/stores.
    ProjectionFields projectionFields{run, projection};
    ProjectionFlagByteFields projectionFlags{run, projection};
    if (projectionFlags.flags() & 4) {
        uint32_t value = run.get(x);
        uint32_t extent = projectionFields.extentX();
        if (s32(value) < 0)
            run.put(x, extent + value);
        else if (s32(value) >= s32(extent))
            run.put(x, value - extent);
        uint32_t end = projectionFields.visibleEndX();
        extent = projectionFields.extentX();
        if (s32(end) >= s32(extent)) {
            value = run.get(x);
            uint32_t camera = projectionFields.cameraX();
            if (s32(value) < s32(camera) && s32(value) <= s32(end - extent))
                run.put(x, extent + value);
        }
    }
    if (projectionFlags.flags() & 8) {
        uint32_t value = run.get(y);
        uint32_t extent = projectionFields.extentY();
        if (s32(value) < 0)
            run.put(y, extent + value);
        else if (s32(value) >= s32(extent))
            run.put(y, value - extent);
        uint32_t end = projectionFields.visibleEndY();
        extent = projectionFields.extentY();
        if (s32(end) >= s32(extent)) {
            value = run.get(y);
            uint32_t camera = projectionFields.cameraY();
            if (s32(value) < s32(camera) && s32(value) <= s32(end - extent))
                run.put(y, extent + value);
        }
    }
    uint32_t cameraX = projectionFields.cameraX();
    run.put(x, run.get(x) - cameraX);
    uint32_t cameraY = projectionFields.cameraY();
    run.put(y, run.get(y) - cameraY);
    uint32_t offsetX = projectionFields.screenOffsetX();
    run.put(x, run.get(x) + offsetX);
    uint32_t offsetY = projectionFields.screenOffsetY();
    run.put(y, run.get(y) + offsetY);
    return 0;
}

// 0x4caaa0. Scene +0x14/+0x10 surface owners (+0x2c surface),
// +0x0c configuration with optional third update selected by +0x34 bit 2.
uint32_t updateSurfaces(Run &run, uint32_t scene, uint32_t value) {
    // Two saved registers, one argument and the CALL return word.
    run.stackPointer = run.frame - 0x10;
    // A callback may replace either wrapper, so reload every owner/surface.
    SurfaceUpdateSceneFields sceneFields{run, scene};
    uint32_t primaryOwner0 = sceneFields.primaryOwner();
    SurfaceOwnerFields primaryFields0{run, primaryOwner0};
    uint32_t primarySurface0 = primaryFields0.surface();
    run.call(0x4b97c0, primarySurface0, {value});
    uint32_t secondaryOwner0 = sceneFields.secondaryOwner();
    SurfaceOwnerFields secondaryFields0{run, secondaryOwner0};
    uint32_t secondarySurface0 = secondaryFields0.surface();
    run.call(0x4b98b0, secondarySurface0, {0});
    uint32_t primaryOwner1 = sceneFields.primaryOwner();
    SurfaceOwnerFields primaryFields1{run, primaryOwner1};
    uint32_t primarySurface1 = primaryFields1.surface();
    run.call(0x4b97c0, primarySurface1, {value});
    uint32_t secondaryOwner1 = sceneFields.secondaryOwner();
    SurfaceOwnerFields secondaryFields1{run, secondaryOwner1};
    uint32_t secondarySurface1 = secondaryFields1.surface();
    run.call(0x4b98b0, secondarySurface1, {0});
    uint32_t configuration = sceneFields.configuration();
    SurfaceUpdateConfigurationFields configurationFields{run, configuration};
    if (configurationFields.flags() & 2) {
        uint32_t primaryOwner2 = sceneFields.primaryOwner();
        SurfaceOwnerFields primaryFields2{run, primaryOwner2};
        uint32_t primarySurface2 = primaryFields2.surface();
        run.call(0x4b97c0, primarySurface2, {value});
        uint32_t secondaryOwner2 = sceneFields.secondaryOwner();
        SurfaceOwnerFields secondaryFields2{run, secondaryOwner2};
        uint32_t secondarySurface2 = secondaryFields2.surface();
        run.call(0x4b98b0, secondarySurface2, {0});
    }
    return 0;
}

// Canonical ABI adapters retain the original addresses in body(). The typed
// cores above are also called internally without creating another Run/frame.
uint32_t initializeActorAtOrigin(Run &run, uint32_t receiver, const uint32_t *arguments) {
    // 0x4c9f80 forwards the full initialization EAX, not a void result.
    run.stackPointer = run.frame - 0x14;
    return run.call(0x4c7df0, receiver, {0, 0, arguments[0], arguments[1]});
}

uint32_t dispatchActorInteractions(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return interactions(run, receiver);
}

uint32_t testActorOverlap(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return actorOverlap(run, arguments[0], arguments[1]);
}

uint32_t projectActorPosition(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return project(run, receiver, arguments[0], arguments[1]);
}

uint32_t applyActorHit(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return hurt(run, receiver, arguments[0]);
}

uint32_t testRectangleOverlap(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    return rectangleOverlap(run, arguments[0], arguments[1]);
}

uint32_t updateSceneSurfaces(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return updateSurfaces(run, receiver, arguments[0]);
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c9390:
        return dispatchActorInteractions(run, receiver, arguments);
    case 0x4c95b0:
        return testActorOverlap(run, receiver, arguments);
    case 0x4c96d0:
        return projectActorPosition(run, receiver, arguments);
    case 0x4c9ae0:
        return applyActorHit(run, receiver, arguments);
    case 0x4c9f80:
        return initializeActorAtOrigin(run, receiver, arguments);
    case 0x4ca230:
        return testRectangleOverlap(run, receiver, arguments);
    case 0x4caaa0:
        return updateSceneSurfaces(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_level_one_actor_storage_02_entry, owned, body)
