// Original menu actor and sound cleanup services
//
// Recovered ordinary cleanup behavior from the original instruction packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4c92f0:
        return 1;
    case 0x4b4240:
        return 1;
    case 0x4b4260:
        return 0;
    case 0x4b3d70:
        return 0;
    case 0x4b43e0:
        return 1;
    case 0x4b46e0:
        return 1;
    case 0x4b4700:
        return 0;
    default:
        return -1;
    }
}

// 0x4b3d70. Base destructor replaces the vtable at +0x00.
uint32_t function_4b3d70(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x513508);
    return 0;
}

// 0x4b43e0. +0x10 is the sound owner; its +0x78 enables cleanup.
uint32_t function_4b43e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t owner = run.get(receiver + 0x10);
    if (!run.get(owner + 0x78))
        return 0;
    uint32_t node = arguments[0];
    // Node +0x0c holds an interface whose vtable +0x08 is stdcall Release.
    uint32_t interface = run.get(node + 0x0c);
    uint32_t release = run.get(run.get(interface + 0x00) + 0x08);
    run.call(release, 0, {interface});
    run.put(node + 0x0c, 0);
    // The node link begins at +0x04; receiver +0x30 is the list head.
    uint32_t link = node ? node + 0x04 : 0;
    run.call(0x4b5270, receiver + 0x30, {link});
    if (node)
        run.vcall(node, 0x00, {1});
    return 0;
}

// 0x4b4260. List destructor reloads the head after each node callback.
uint32_t function_4b4260(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x51350c);
    uint32_t head = run.get(receiver + 0x30);
    uint32_t node = head ? head - 0x04 : 0;
    while (node) {
        uint32_t arguments[] = {node};
        function_4b43e0(run, receiver, arguments);
        head = run.get(receiver + 0x30);
        node = head ? head - 0x04 : 0;
    }
    function_4b3d70(run, receiver, nullptr);
    return 0;
}

// 0x4b4240. Scalar deleting list destructor returns its saved receiver.
uint32_t function_4b4240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4b4260(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4b4700. Leaf vtable installation precedes the base destructor tail call.
uint32_t function_4b4700(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver + 0x00, 0x513510);
    return function_4b3d70(run, receiver, nullptr);
}

// 0x4b46e0. Scalar deleting leaf destructor returns its saved receiver.
uint32_t function_4b46e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4b4700(run, receiver, nullptr);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4c92f0. Actor +0x68 is its link in the owner's list at +0x10.
uint32_t function_4c92f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t actor = arguments[0];
    uint32_t link = run.get(actor + 0x68);
    run.call(0x4f5212, receiver + 0x10, {link});
    if (actor)
        run.vcall(actor, 0x04, {1});
    return 0;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4c92f0:
        return function_4c92f0(run, receiver, arguments);
    case 0x4b4240:
        return function_4b4240(run, receiver, arguments);
    case 0x4b4260:
        return function_4b4260(run, receiver, arguments);
    case 0x4b3d70:
        return function_4b3d70(run, receiver, arguments);
    case 0x4b43e0:
        return function_4b43e0(run, receiver, arguments);
    case 0x4b46e0:
        return function_4b46e0(run, receiver, arguments);
    case 0x4b4700:
        return function_4b4700(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_cleanup_services_entry, owned, body)
