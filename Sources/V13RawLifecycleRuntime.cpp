#include "ClawRuntime.hpp"
#include "ClawRecoveredLayout.h"

namespace {
using claw::Run;
using namespace claw::recovered::v13;

int owned(uint32_t function) {
    switch (function) {
    case 0x4c7930:
    case 0x4d6590:
        return 4;
    case 0x4ce9b0:
        return 0;
    default:
        return -1;
    }
}

// 0x4d6590. A missing serialized identity leaves the logic peer unchanged;
// the raw-actor entry below instead clears its peer in that situation.
uint32_t serializeLogic(Run &run, uint32_t logic, const uint32_t *arguments) {
    LifecycleLogicFields logicFields{run, logic};
    uint32_t stream = arguments[0];
    uint32_t operation = arguments[1];
    if (!stream)
        return 0;
    switch (operation) {
    case uint32_t(SerializationOperation::CapturePeerIdentity): {
        uint32_t peer = logicFields.peer();
        logicFields.serializedPeerIdentity(0);
        if (peer) {
            LifecycleActorFields peerFields{run, peer};
            uint32_t identity = peerFields.numericIdentity();
            logicFields.serializedPeerIdentity(identity);
        }
        break;
    }
    case uint32_t(SerializationOperation::WriteFields):
        run.stackPointer = run.frame - 0x14;
        if (!run.call(0x4d6680, logic, {stream}))
            return 0;
        break;
    case uint32_t(SerializationOperation::ReadFields):
        run.stackPointer = run.frame - 0x14;
        if (!run.call(0x4d6aa0, logic, {stream}))
            return 0;
        break;
    case uint32_t(SerializationOperation::ResolvePeerIdentity): {
        uint32_t identity = logicFields.serializedPeerIdentity();
        if (identity) {
            uint32_t scene = logicFields.scene();
            LifecycleSceneFields sceneFields{run, scene};
            uint32_t objects = sceneFields.objects();
            uint32_t map = objects + LifecycleNumericIdentityMapOffset;
            uint32_t output = run.automatic(4);
            run.put(output, 0);
            run.stackPointer = run.frame - 0x18;
            uint32_t found = run.call(0x4fc9aa, map, {identity, output});
            logicFields.peer(found ? run.get(output) : found);
        }
        break;
    }
    default:
        break;
    }
    uint32_t child = logicFields.child();
    if (child) {
        run.stackPointer = run.frame - 0x20;
        if (!run.vcall(child, 0x04, {stream, operation, arguments[2], arguments[3]}))
            return 0;
    }
    return 1;
}

// 0x4c7930. Publish a temporary event to the current logic callback record.
// The callback can replace that record or change its event; reload it each time
// and restore the saved event only when the published event still survives.
uint32_t serializeActor(Run &run, uint32_t actor, const uint32_t *arguments) {
    LifecycleActorFields actorFields{run, actor};
    uint32_t stream = arguments[0];
    uint32_t operation = arguments[1];
    if (!stream)
        return 0;
    uint32_t event = 0;
    switch (operation) {
    case uint32_t(SerializationOperation::CapturePeerIdentity): {
        uint32_t peer = actorFields.peer();
        actorFields.serializedPeerIdentity(0);
        if (peer) {
            LifecycleActorFields peerFields{run, peer};
            uint32_t identity = peerFields.numericIdentity();
            actorFields.serializedPeerIdentity(identity);
        }
        event = uint32_t(SerializationEvent::PeerIdentityCaptured);
        break;
    }
    case uint32_t(SerializationOperation::WriteFields):
        run.stackPointer = run.frame - 0x18;
        if (!run.call(0x4c7ab0, actor, {stream}))
            return 0;
        event = uint32_t(SerializationEvent::FieldsWritten);
        break;
    case uint32_t(SerializationOperation::ReadFields):
        run.stackPointer = run.frame - 0x18;
        if (!run.call(0x4c7f10, actor, {stream}))
            return 0;
        event = uint32_t(SerializationEvent::FieldsRead);
        break;
    case uint32_t(SerializationOperation::ResolvePeerIdentity): {
        uint32_t identity = actorFields.serializedPeerIdentity();
        if (!identity) {
            actorFields.peer(0);
        } else {
            uint32_t scene = actorFields.scene();
            uint32_t output = run.automatic(4);
            run.put(output, 0);
            LifecycleSceneFields sceneFields{run, scene};
            uint32_t objects = sceneFields.objects();
            uint32_t map = objects + LifecycleNumericIdentityMapOffset;
            run.stackPointer = run.frame - 0x1c;
            uint32_t found = run.call(0x4fc9aa, map, {identity, output});
            actorFields.peer(found ? run.get(output) : found);
        }
        event = uint32_t(SerializationEvent::PeerIdentityResolved);
        break;
    }
    default:
        break;
    }
    if (event) {
        uint32_t logic = actorFields.logicHolder();
        if (!logic)
            return 0;
        LifecycleLogicFields previousLogicFields{run, logic};
        uint32_t previous = previousLogicFields.event();
        previousLogicFields.event(event);
        logic = actorFields.logicHolder();
        run.stackPointer = run.frame - 0x18;
        LifecycleLogicFields callbackLogicFields{run, logic};
        uint32_t callback = callbackLogicFields.callback();
        run.call(callback, 0, {actor});
        logic = actorFields.logicHolder();
        LifecycleLogicFields currentLogicFields{run, logic};
        if (currentLogicFields.event() == event)
            currentLogicFields.event(previous);
    }
    uint32_t oldFrame = run.frame;
    run.frame -= 0x24;
    uint32_t logic = actorFields.logicHolder();
    uint32_t result = serializeLogic(run, logic, arguments);
    run.frame = oldFrame;
    return result != 0;
}

// 0x4ce9b0 is a bare RET. Its void result is normalized only at this ABI.
uint32_t ignoreLifecycleNotification(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c7930:
        return serializeActor(run, receiver, arguments);
    case 0x4d6590:
        return serializeLogic(run, receiver, arguments);
    case 0x4ce9b0:
        return ignoreLifecycleNotification(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}

CLAW_MODULE_ENTRY(claw_v13_raw_lifecycle_entry, owned, body)
