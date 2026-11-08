// Level 1 actor storage batch 1
//
// Canonical guest-memory translation of the six owned actor storage entries.
#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {

using claw::Run;
using claw::s32;
using namespace claw::recovered::v10;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c7f20:
        return 1;
    case 0x4c7fa0:
        return 1;
    case 0x4c7fe0:
        return 1;
    case 0x4c8060:
        return 1;
    case 0x4c8a20:
        return 4;
    case 0x4c8b90:
        return 4;
    default:
        return -1;
    }
}

// 0x4c7f20. thiscall, 1 stack argument(s), returns u32.
uint32_t bindSecondaryLogic(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t metadata = arguments[0];
    if (!metadata)
        return 0;
    ActorStorageFields actorFields{run, receiver};
    uint32_t object = actorFields.secondaryHolder();
    if (object) {
        run.vcall(object, 0x1c);
    } else {
        object = run.call(0x4f63ec, 0, {ActorLogicHolderAllocationBytes});
        if (object) {
            ResourceStorageFields resourceFields{run, object};
            LogicHolderFields holderFields{run, object};
            uint32_t id = actorFields.id();
            uint32_t scene = actorFields.scene();
            resourceFields.id(id);
            resourceFields.flags(0);
            resourceFields.scene(scene);
            resourceFields.vtable(ActorLogicHolderVtable);
            resourceFields.initializer(0);
            resourceFields.unknown_0x14(0);
            holderFields.logic(0);
            holderFields.state(0);
        }
        actorFields.secondaryHolder(object);
    }
    // Reset callbacks may replace the selected holder; reload its published token.
    object = actorFields.secondaryHolder();
    if (!object)
        return 0;
    LogicMetadataFields metadataFields{run, metadata};
    uint32_t callback = metadataFields.initializer();
    return run.vcall(object, 0x24, {callback, 0});
}

// 0x4c7fa0. thiscall, 1 stack argument(s), returns void.
uint32_t bindSecondaryLogicNamed(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t local = run.automatic(-4);
    ActorStorageFields receiverFields{run, receiver};
    uint32_t scene = receiverFields.scene();
    run.put(local, 0);
    // Scene +0x14 owns the registry whose map starts at +0x10.
    ActorStorageSceneFields sceneFields{run, scene};
    uint32_t registry = sceneFields.registry();
    run.call(0x4f6286, registry + 0x10, {arguments[0], local});
    uint32_t bindingArguments[] = {run.get(local)};
    return bindSecondaryLogic(run, receiver, bindingArguments);
}

// 0x4c7fe0. thiscall, 1 stack argument(s), returns u32.
uint32_t bindContactLogic(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t metadata = arguments[0];
    if (!metadata)
        return 0;
    ActorStorageFields actorFields{run, receiver};
    uint32_t object = actorFields.contactHolder();
    if (object) {
        run.vcall(object, 0x1c);
    } else {
        object = run.call(0x4f63ec, 0, {ActorLogicHolderAllocationBytes});
        if (object) {
            ResourceStorageFields resourceFields{run, object};
            LogicHolderFields holderFields{run, object};
            uint32_t id = actorFields.id();
            uint32_t scene = actorFields.scene();
            resourceFields.id(id);
            resourceFields.flags(0);
            resourceFields.scene(scene);
            resourceFields.vtable(ActorLogicHolderVtable);
            resourceFields.initializer(0);
            resourceFields.unknown_0x14(0);
            holderFields.logic(0);
            holderFields.state(0);
        }
        actorFields.contactHolder(object);
    }
    // Reset callbacks may replace the selected holder; reload its published token.
    object = actorFields.contactHolder();
    if (!object)
        return 0;
    LogicMetadataFields metadataFields{run, metadata};
    uint32_t callback = metadataFields.initializer();
    return run.vcall(object, 0x24, {callback, 0});
}

// 0x4c8060. thiscall, 1 stack argument(s), returns void.
uint32_t bindContactLogicNamed(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t local = run.automatic(-4);
    ActorStorageFields receiverFields{run, receiver};
    uint32_t scene = receiverFields.scene();
    run.put(local, 0);
    // Scene +0x14 owns the registry whose map starts at +0x10.
    ActorStorageSceneFields sceneFields{run, scene};
    uint32_t registry = sceneFields.registry();
    run.call(0x4f6286, registry + 0x10, {arguments[0], local});
    uint32_t bindingArguments[] = {run.get(local)};
    return bindContactLogic(run, receiver, bindingArguments);
}

// 0x4c8a20. thiscall, 4 stack argument(s), returns u32.
uint32_t createPlainActor(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = run.call(0x4f63ec, 0, {PlainActorAllocationBytes});
    ActorStorageFields actorFields{run, actor};
    ActorFields primaryFields{run, actor};
    ActorContainerFields containerFields{run, receiver};
    if (actor) {
        uint32_t scene = containerFields.scene();
        run.call(0x4c9780, actor, {scene, arguments[0], arguments[3]});
        // +0x88 and +0xa4: constructed actor members.
        run.call(0x4c96c0, actor + 0x88);
        run.call(0x4c9690, actor + 0xa4);
        actorFields.vtable(PlainActorBaseVtable);
        actorFields.unknown_0x4c(0x80000000);
        actorFields.listNode(0);
        uint32_t primary = run.call(0x4f63ec, 0, {ActorLogicHolderAllocationBytes});
        if (primary)
            primary = run.call(0x4c9830, primary, {scene, arguments[0], 0});
        primaryFields.holder(primary);
        actorFields.unknown_0x84(0);
        actorFields.unknown_0x80(0);
        actorFields.secondaryHolder(0);
        actorFields.contactHolder(0);
        actorFields.vtable(PlainActorVtable);
    }
    if (!run.vcall(actor, 0x3c, {arguments[1], arguments[2]})) {
        if (actor)
            run.vcall(actor, 0x4, {1});
        return 0;
    }
    uint32_t node = containerFields.head();
    uint32_t depth = actorFields.depth();
    uint32_t position = 0;
    while (node) {
        uint32_t current = node;
        ActorListNodeFields nodeFields{run, node};
        node = nodeFields.next();
        uint32_t other = nodeFields.actor();
        ActorStorageFields otherFields{run, other};
        if (s32(otherFields.depth()) > s32(depth) &&
            !(otherFields.flags() & SkipDepthInsertionFlag)) {
            position = current;
            break;
        }
    }
    uint32_t inserted;
    // Container +0x10: embedded list.
    if (position)
        inserted = run.call(0x4f572a, receiver + 0x10, {position, actor});
    else
        inserted = run.call(0x4f51c5, receiver + 0x10, {actor});
    actorFields.listNode(inserted);
    if (arguments[3] & CallPrimaryInitializerFlag) {
        uint32_t primary = primaryFields.holder();
        ResourceStorageFields primaryResourceFields{run, primary};
        // This is a cdecl callback field, not a virtual slot.
        uint32_t callback = primaryResourceFields.initializer();
        run.call(callback, 0, {actor});
    }
    return actor;
}

// 0x4c8b90. thiscall, 4 stack argument(s), returns void.
uint32_t createPlainActorNamed(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t local = run.automatic(-4);
    ActorContainerFields namedContainerFields{run, receiver};
    uint32_t scene = namedContainerFields.scene();
    run.put(local, 0);
    ActorStorageSceneFields sceneFields{run, scene};
    uint32_t registry = sceneFields.registry();
    run.call(0x4f6286, registry + 0x10, {arguments[2], local});
    uint32_t createArguments[] = {arguments[0], arguments[1], run.get(local), arguments[3]};
    return createPlainActor(run, receiver, createArguments);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c7f20:
        return bindSecondaryLogic(run, receiver, arguments);
    case 0x4c7fa0:
        return bindSecondaryLogicNamed(run, receiver, arguments);
    case 0x4c7fe0:
        return bindContactLogic(run, receiver, arguments);
    case 0x4c8060:
        return bindContactLogicNamed(run, receiver, arguments);
    case 0x4c8a20:
        return createPlainActor(run, receiver, arguments);
    case 0x4c8b90:
        return createPlainActorNamed(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_actor_storage_01_entry, owned, body)
