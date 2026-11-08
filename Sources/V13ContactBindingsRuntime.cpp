#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"
#include "ClawRecoveredNames.h"

namespace {
using claw::Run;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    switch (function) {
    case 0x40b630:
    case 0x4c8440:
        return 0;
    case 0x4c83f0:
        return 2;
    case 0x404400:
    case 0x4c7690:
    case 0x4c7770:
    case 0x4c7850:
    case 0x4c78f0:
    case 0x4def30:
        return 1;
    default:
        return -1;
    }
}

// 0x404400. Scene registry is actor+0x0c -> scene+0x14; entries live
// in its map at +0x10. The second and third outputs reuse the argument slot.
uint32_t registerContacts(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ContactActorFields actorFields{run, actor};
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    run.stackPointer = run.frame - 0x14;
    uint32_t hitLookupScene = actorFields.scene();
    ContactSceneFields hitLookupSceneFields{run, hitLookupScene};
    [[maybe_unused]] uint32_t hitLookupRegistry = hitLookupSceneFields.registry();
    run.call(0x4fc6b4, hitLookupRegistry + ContactRegistryMapOffset, {0x520d84, output});
    if (!run.get(output)) {
        run.stackPointer = run.frame - 0x18;
        uint32_t hitRegistrationScene = actorFields.scene();
        ContactSceneFields hitRegistrationSceneFields{run, hitRegistrationScene};
        [[maybe_unused]] uint32_t hitRegistrationRegistry = hitRegistrationSceneFields.registry();
        run.vcall(hitRegistrationRegistry, 0x1c, {0x4def10, 0x520d84, 2});
    }
    output = run.frame + 4;
    run.put(output, 0);
    run.stackPointer = run.frame - 0x14;
    uint32_t attackLookupScene = actorFields.scene();
    ContactSceneFields attackLookupSceneFields{run, attackLookupScene};
    [[maybe_unused]] uint32_t attackLookupRegistry = attackLookupSceneFields.registry();
    run.call(0x4fc6b4, attackLookupRegistry + ContactRegistryMapOffset, {0x520d78, output});
    if (!run.get(output)) {
        run.stackPointer = run.frame - 0x18;
        uint32_t attackRegistrationScene = actorFields.scene();
        ContactSceneFields attackRegistrationSceneFields{run, attackRegistrationScene};
        [[maybe_unused]] uint32_t attackRegistrationRegistry = attackRegistrationSceneFields.registry();
        run.vcall(attackRegistrationRegistry, 0x1c, {0x4def20, 0x520d78, 2});
    }
    run.put(output, 0);
    run.stackPointer = run.frame - 0x14;
    uint32_t bumpLookupScene = actorFields.scene();
    ContactSceneFields bumpLookupSceneFields{run, bumpLookupScene};
    [[maybe_unused]] uint32_t bumpLookupRegistry = bumpLookupSceneFields.registry();
    run.call(0x4fc6b4, bumpLookupRegistry + ContactRegistryMapOffset, {0x521178, output});
    if (!run.get(output)) {
        run.stackPointer = run.frame - 0x18;
        uint32_t bumpRegistrationScene = actorFields.scene();
        ContactSceneFields bumpRegistrationSceneFields{run, bumpRegistrationScene};
        [[maybe_unused]] uint32_t bumpRegistrationRegistry = bumpRegistrationSceneFields.registry();
        run.vcall(bumpRegistrationRegistry, 0x1c, {0x4def30, 0x521178, 2});
    }
    return 0;
}

// 0x4c7690. Actor+0x80 owns its hit logic, with object/scene identity
// at actor+0x04/+0x0c. The metadata callback is at entry+0x10.
uint32_t bindHitContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = receiver;
    uint32_t metadata = arguments[0];
    ContactActorFields actorFields{run, actor};
    if (!metadata)
        return 0;
    uint32_t logic = actorFields.hitLogic();
    if (logic) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(logic, 0x14);
    } else {
        run.stackPointer = run.frame - 0x14;
        logic = run.call(0x4fcaea, 0, {ContactLogicAllocationBytes});
        if (logic) {
            ContactLogicFields logicFields{run, logic};
            [[maybe_unused]] uint32_t identity = actorFields.identity();
            [[maybe_unused]] uint32_t scene = actorFields.scene();
            logicFields.identity(identity);
            logicFields.context(0);
            logicFields.scene(scene);
            logicFields.vtable(ContactLogicVtable);
            logicFields.callback(0);
            logicFields.data(0);
            logicFields.child(0);
            logicFields.unknown_0x170(0);
            logicFields.unknown_0x1c(0);
            logicFields.unknown_0x174(0);
            logicFields.unknown_0x178(0);
        }
        actorFields.hitLogic(logic);
    }
    logic = actorFields.hitLogic();
    if (!logic)
        return 0;
    ContactMetadataFields metadataFields{run, metadata};
    [[maybe_unused]] uint32_t callback = metadataFields.callback();
    run.stackPointer = run.frame - 0x18;
    return run.vcall(logic, 0x1c, {callback, 0});
}

// 0x4c7770. Actor+0x88 owns its attack logic, with object/scene identity
// at actor+0x04/+0x0c. The metadata callback is at entry+0x10.
uint32_t bindAttackContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = receiver;
    uint32_t metadata = arguments[0];
    ContactActorFields actorFields{run, actor};
    if (!metadata)
        return 0;
    uint32_t logic = actorFields.attackLogic();
    if (logic) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(logic, 0x14);
    } else {
        run.stackPointer = run.frame - 0x14;
        logic = run.call(0x4fcaea, 0, {ContactLogicAllocationBytes});
        if (logic) {
            ContactLogicFields logicFields{run, logic};
            [[maybe_unused]] uint32_t identity = actorFields.identity();
            [[maybe_unused]] uint32_t scene = actorFields.scene();
            logicFields.identity(identity);
            logicFields.context(0);
            logicFields.scene(scene);
            logicFields.vtable(ContactLogicVtable);
            logicFields.callback(0);
            logicFields.data(0);
            logicFields.child(0);
            logicFields.unknown_0x170(0);
            logicFields.unknown_0x1c(0);
            logicFields.unknown_0x174(0);
            logicFields.unknown_0x178(0);
        }
        actorFields.attackLogic(logic);
    }
    logic = actorFields.attackLogic();
    if (!logic)
        return 0;
    ContactMetadataFields metadataFields{run, metadata};
    [[maybe_unused]] uint32_t callback = metadataFields.callback();
    run.stackPointer = run.frame - 0x18;
    return run.vcall(logic, 0x1c, {callback, 0});
}

// 0x4c7850. Actor+0x90 owns its bump logic, with object/scene identity
// at actor+0x04/+0x0c. The metadata callback is at entry+0x10.
uint32_t bindContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = receiver;
    uint32_t metadata = arguments[0];
    ContactActorFields actorFields{run, actor};
    if (!metadata)
        return 0;
    uint32_t logic = actorFields.bumpLogic();
    if (logic) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(logic, 0x14);
    } else {
        run.stackPointer = run.frame - 0x14;
        logic = run.call(0x4fcaea, 0, {ContactLogicAllocationBytes});
        if (logic) {
            ContactLogicFields logicFields{run, logic};
            [[maybe_unused]] uint32_t identity = actorFields.identity();
            [[maybe_unused]] uint32_t scene = actorFields.scene();
            logicFields.identity(identity);
            logicFields.context(0);
            logicFields.scene(scene);
            logicFields.vtable(ContactLogicVtable);
            logicFields.callback(0);
            logicFields.data(0);
            logicFields.child(0);
            logicFields.unknown_0x170(0);
            logicFields.unknown_0x1c(0);
            logicFields.unknown_0x174(0);
            logicFields.unknown_0x178(0);
        }
        actorFields.bumpLogic(logic);
    }
    logic = actorFields.bumpLogic();
    if (!logic)
        return 0;
    ContactMetadataFields metadataFields{run, metadata};
    [[maybe_unused]] uint32_t callback = metadataFields.callback();
    run.stackPointer = run.frame - 0x18;
    return run.vcall(logic, 0x1c, {callback, 0});
}

// 0x4c78f0. Resolve a named bump logic and pass the resulting metadata
// to the owned binder in its real nested entry frame.
uint32_t bindNamedContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = receiver;
    [[maybe_unused]] uint32_t name = arguments[0];
    ContactActorFields actorFields{run, actor};
    uint32_t output = run.automatic(-4);
    run.put(output, 0);
    run.stackPointer = run.frame - 0x14;
    uint32_t namedLookupScene = actorFields.scene();
    ContactSceneFields namedLookupSceneFields{run, namedLookupScene};
    [[maybe_unused]] uint32_t namedLookupRegistry = namedLookupSceneFields.registry();
    run.call(0x4fc6b4, namedLookupRegistry + ContactRegistryMapOffset, {name, output});
    uint32_t metadata = run.get(output);
    uint32_t frame = run.frame;
    run.frame -= 0x10;
    const uint32_t bindingArguments[] = {metadata};
    bindContact(run, actor, bindingArguments);
    run.frame = frame;
    return 0;
}

// 0x4def30. The tail jump leaves the incoming actor argument untouched;
// its selected thiscall virtual target has no stack arguments.
uint32_t bumpTrampoline(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t actor = arguments[0];
    ContactActorFields actorFields{run, actor};
    uint32_t holder = actorFields.logicHolder();
    ContactHolderFields holderFields{run, holder};
    uint32_t child = holderFields.child();
    run.stackPointer = run.frame;
    return run.vcall(child, 0x20);
}

// 0x4c83f0. Logic callback is at +0x10 and its context at +0x08.
// +0x14/+0x18 own callback data and a child; the remaining fields are state.
uint32_t initializeContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    [[maybe_unused]] uint32_t callback = arguments[0];
    [[maybe_unused]] uint32_t context = arguments[1];
    ContactLogicFields logicFields{run, receiver};
    if (!callback)
        return 0;
    logicFields.callback(callback);
    logicFields.data(0);
    logicFields.child(0);
    logicFields.unknown_0x20(0);
    logicFields.unknown_0x24(0);
    logicFields.unknown_0x2c(0);
    logicFields.unknown_0x34(0);
    logicFields.unknown_0x30(0);
    logicFields.unknown_0x38(0);
    logicFields.unknown_0x168(0);
    logicFields.unknown_0x16c(0);
    logicFields.unknown_0x28(0);
    logicFields.context(context);
    return 1;
}

// 0x4c8440. Read data before clearing the callback; release data and child
// in order. The meanings of the state words at +0x178/+0x170 remain unknown.
uint32_t cleanupContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    ContactLogicFields logicFields{run, receiver};
    uint32_t data = logicFields.data();
    logicFields.callback(0);
    if (data) {
        run.stackPointer = run.frame - 0x10;
        run.call(0x4fcb13, 0, {data});
        logicFields.data(0);
        logicFields.unknown_0x178(0);
    }
    uint32_t child = logicFields.child();
    if (child) {
        run.stackPointer = run.frame - 0x10;
        run.vcall(child, 0x00, {1});
        logicFields.child(0);
    }
    logicFields.unknown_0x170(0);
    return 0;
}

// 0x40b630. The default bump handler accepts every contact.
uint32_t acceptContact(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x40b630:
        return acceptContact(run, receiver, arguments);
    case 0x404400:
        return registerContacts(run, receiver, arguments);
    case 0x4c7690:
        return bindHitContact(run, receiver, arguments);
    case 0x4c7770:
        return bindAttackContact(run, receiver, arguments);
    case 0x4c83f0:
        return initializeContact(run, receiver, arguments);
    case 0x4c8440:
        return cleanupContact(run, receiver, arguments);
    case 0x4c7850:
        return bindContact(run, receiver, arguments);
    case 0x4c78f0:
        return bindNamedContact(run, receiver, arguments);
    case 0x4def30:
        return bumpTrampoline(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_contact_bindings_entry, owned, body)
