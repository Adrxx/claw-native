// Recursive multiplayer player lifecycle and packet wrappers
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x479000:
        return 1;
    case 0x47a4b0:
        return 1;
    case 0x4776b0:
        return 1;
    case 0x4777d0:
        return 3;
    case 0x477810:
        return 4;
    case 0x478f30:
        return 1;
    case 0x486d50:
        return 1;
    case 0x4e0930:
        return 4;
    case 0x4e0c20:
        return 1;
    case 0x4e0c80:
        return 1;
    case 0x4e0cc0:
        return 5;
    case 0x4e0d20:
        return 5;
    case 0x4e0fc0:
        return 1;
    case 0x4e0fe0:
        return 0;
    case 0x4e1ae0:
        return 4;
    default:
        return -1;
    }
}

// Owned calls retain the original entry-relative locations of escaping locals.
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);
uint32_t nested(Run &run, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments, int32_t entryOffset) {
    const uint32_t previous = run.frame;
    struct Restore {
        Run &run;
        uint32_t frame;
        ~Restore() {run.frame = frame;}
    } restore{run, previous};
    run.frame = run.automatic(entryOffset);
    return body(run, function, receiver, arguments.begin());
}

uint32_t external(Run &run, uint32_t function, uint32_t receiver,
                  std::initializer_list<uint32_t> arguments, int32_t entryOffset) {
    const uint32_t previous = run.stackPointer;
    struct Restore {
        Run &run;
        uint32_t stack;
        ~Restore() {run.stackPointer = stack;}
    } restore{run, previous};
    run.stackPointer = run.automatic(entryOffset);
    return run.call(function, receiver, arguments);
}

// 0x479000. Remove a remote roster entry and publish its departure.
uint32_t function_479000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t player = nested(run, 0x4e0c80, run.get(receiver + 0x780), {arguments[0]}, -0x118);
    if (!player || player == run.get(receiver + 0x784))
        return 0;
    nested(run, 0x486d50, 0, {player}, -0x118);
    const uint32_t actorData = run.get(player + 0x14);
    const bool silent = actorData && run.get(actorData + 0x24);
    if (player == run.get(receiver + 0xc04)) {
        const uint32_t app = run.get(receiver + 0x4);
        run.put(receiver + 0xc04, 0);
        run.call(0x422370, run.get(app + 0x4c), {0x52ab24, 0});
    } else if (run.get(receiver + 0x7ac) && !silent) {
        const uint32_t name = run.automatic(-0x104);
        const uint32_t message = run.automatic(-0x100);
        const uint32_t copy = run.call(0x41ee40, player, {name});
        run.call(0x4a3920, 0, {message, 0x52ab10, run.get(copy)});
        run.call(0x4f6584, name);
        run.call(0x422370, run.get(run.get(receiver + 0x4) + 0x4c), {message, 0});
        const uint32_t sounds = run.get(run.get(receiver + 0xc) + 0x28);
        if (!run.get(sounds + 0x30)) {
            run.put(name, 0);
            run.call(0x4f6286, sounds + 0x10, {0x52a824, name});
            const uint32_t sound = run.get(name);
            if (sound && run.get(0x532c0c))
                run.call(0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0});
        }
    }
    if (actorData) {
        const uint32_t actor = run.get(actorData);
        if (actor)
            run.put(actor + 0x8, run.get(actor + 0x8) | 0x10000);
    }
    nested(run, 0x4e0c20, run.get(receiver + 0x780), {player}, -0x118);
    run.put(receiver + 0x794, 1);
    return 1;
}

// 0x47a4b0. Accept or reject an announced peer and send current state.
uint32_t function_47a4b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t packet = arguments[0];
    if (!packet || run.get(packet + 0x4) != 1)
        return 0;
    uint32_t player = nested(run, 0x4e0c80, run.get(receiver + 0x780), {run.get(packet + 0x8)}, -0x130);
    if (!player) {
        player = nested(run, 0x4e0930, run.get(receiver + 0x780),
            {run.get(packet + 0x8), run.get(packet + 0x20), run.get(packet + 0x24), 0}, -0x13c);
        if (!player)
            return 0;
    }
    const uint32_t name = run.automatic(-0x118);
    const uint32_t copy = external(run, 0x41ee40, player, {name}, -0x130);
    uint32_t left = run.get(copy);
    uint32_t right = 0x52ac30;
    bool equal;
    for (;;) {
        const uint8_t a = run.get8(left);
        const uint8_t b = run.get8(right);
        if (a != b) {
            equal = false;
            break;
        }
        if (!a) {
            equal = true;
            break;
        }
        ++left;
        ++right;
    }
    external(run, 0x4f6584, name, {}, -0x12c);
    if (equal)
        run.put(receiver + 0xc04, player);
    if ((run.get(receiver + 0x7a8) || run.get(receiver + 0x7ac)) &&
        run.get(receiver + 0x7b0) && (!player || player != run.get(receiver + 0xc04))) {
        const uint32_t local = run.get(receiver + 0x784);
        const uint32_t reply = run.automatic(-0x114);
        run.put(reply, 0x3f1);
        run.put(reply + 0xc, run.get(local + 0x4));
        nested(run, 0x4e0d20, run.get(receiver + 0x780),
            {run.get(local + 0x4), run.get(packet + 0x8), 1, reply, 0x14}, -0x140);
        if (player)
            nested(run, 0x479000, receiver, {run.get(player + 0x4)}, -0x130);
        return 0;
    }
    if (!nested(run, 0x478f30, receiver, {player}, -0x130)) {
        nested(run, 0x4e0c20, run.get(receiver + 0x780), {player}, -0x130);
        return 0;
    }
    if (run.get(receiver + 0x7ac)) {
        const uint32_t message = run.automatic(-0x100);
        const uint32_t copied = external(run, 0x41ee40, player, {name}, -0x130);
        external(run, 0x4a3920, 0, {message, 0x52ac18, run.get(copied)}, -0x138);
        external(run, 0x4f6584, name, {}, -0x12c);
        external(run, 0x422370, run.get(run.get(receiver + 0x4) + 0x4c), {message, 0}, -0x134);
        const uint32_t sounds = run.get(run.get(receiver + 0xc) + 0x28);
        if (!run.get(sounds + 0x30)) {
            run.put(name, 0);
            external(run, 0x4f6286, sounds + 0x10, {0x52a824, name}, -0x134);
            const uint32_t sound = run.get(name);
            if (sound && run.get(0x532c0c))
                external(run, 0x4b45f0, run.get(sound + 0x10), {run.get(0x532c10), 0, 0, 0}, -0x13c);
        }
        if (run.get(receiver + 0x79c)) {
            const uint32_t context = run.get(receiver + 0xc);
            nested(run, 0x477810, receiver,
                {player, 0x3f5, run.get(run.get(context + 0x24) + 0xac), 1}, -0x13c);
            if (run.get(receiver + 0x79c) && run.get(receiver + 0x7b8))
                nested(run, 0x477810, receiver, {player, 0x3f4, run.get(receiver + 0x14), 1}, -0x13c);
        }
    } else if (run.get(receiver + 0x79c) && run.get(receiver + 0x7b8)) {
        nested(run, 0x477810, receiver, {player, 0x3f4, run.get(receiver + 0x14), 1}, -0x13c);
    }
    if (run.get(receiver + 0x7a4))
        nested(run, 0x4777d0, receiver, {player, 0x3ed, 1}, -0x138);
    if (run.get(receiver + 0x79c)) {
        if (run.get(receiver + 0x7ac))
            nested(run, 0x4777d0, receiver, {player, 0x3ef, 1}, -0x138);
        else if (run.get(receiver + 0x7a8))
            nested(run, 0x4777d0, receiver, {player, 0x3ee, 1}, -0x138);
    }
    if (run.get(receiver + 0x78c)) {
        run.put(0x53c0c8, 1);
        nested(run, 0x4776b0, receiver, {player}, -0x130);
    }
    run.put(receiver + 0x794, 1);
    return 1;
}

// 0x4776b0. The global packet has a fixed original publication order.
uint32_t function_4776b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t app = run.get(0x537e88);
    run.put(0x53bea0, 0x3ec);
    run.put(0x53bea4, run.get(receiver + 0xbc4));
    run.put(0x53bea8, 0);
    run.put(0x53beb0, 0);
    run.put(0x53beac, run.get(app + 0xf8));
    run.call(0x477790, receiver, {arguments[0], 0x53bea0, 1});
    return 0;
}

// 0x4777d0. Only the message and identity fields are initialized.
uint32_t function_4777d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t packet = run.automatic(-0x14);
    run.put(packet, arguments[1]);
    run.put(packet + 0xc, run.get(run.get(receiver + 0x784) + 0x4));
    run.call(0x477790, receiver, {arguments[0], packet, arguments[2]});
    return 0;
}

// 0x477810. The remaining packet bytes retain guest stack contents.
uint32_t function_477810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t packet = run.automatic(-0x14);
    run.put(packet, arguments[1]);
    run.put(packet + 0xc, arguments[2]);
    run.call(0x477790, receiver, {arguments[0], packet, arguments[3]});
    return 0;
}

// 0x478f30. Allocate missing per-peer storage, then create its remote actor.
uint32_t function_478f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t player = arguments[0];
    if (!player)
        return 0;
    if (!run.get(player + 0x18)) {
        const uint32_t buffer = run.call(0x4f63ec, 0, {0x400});
        if (!buffer)
            return 0;
        for (uint32_t i = 0; i < 0x100; ++i)
            run.put(buffer + i * 4, 0);
        run.put(player + 0x18, buffer);
        run.put(player + 0x1c, 0x400);
    }
    if (!run.get(player + 0x14)) {
        const uint32_t data = run.call(0x4f63ec, 0, {0x2c});
        if (!data)
            return 0;
        for (uint32_t i = 0; i < 0xb; ++i)
            run.put(data + i * 4, 0);
        run.put(player + 0x14, data);
    }
    if (run.get(player + 0x4) != run.get(receiver + 0x788)) {
        const uint32_t context = run.get(receiver + 0xc);
        const uint32_t actor = run.call(0x4c8f60, run.get(context + 0x8), {1, 0, 0, 100, 0x522e2c, 0x40002});
        if (!actor)
            return 0;
        run.put(actor + 0xc8, player);
        run.put(run.get(player + 0x14), actor);
    }
    return 1;
}

// 0x486d50. Clear only the currently selected player.
uint32_t function_486d50(Run &run, uint32_t, const uint32_t *arguments) {
    if (run.get(0x53c25c) && arguments[0] == run.get(0x53c264))
        run.call(0x486d30, 0);
    return 0;
}

// 0x4e0930. Construct a peer, publish it to DirectPlay, then append its list node.
uint32_t function_4e0930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t allocation = run.call(0x4f63ec, 0, {0x24});
    const uint32_t local = run.automatic(-0x14);
    if (allocation) {
        run.put(allocation, 0x50becc);
        run.call(0x4f6439, allocation + 0x8);
        run.call(0x4f6439, allocation + 0xc);
        run.put(allocation, 0x513fb0);
        run.put(allocation + 0x4, 0);
        run.put(allocation + 0x20, 0);
        run.put(allocation + 0x18, 0);
        run.put(allocation + 0x14, 0);
    }
    run.put(local, allocation);
    const uint32_t ok = nested(run, 0x4e1ae0, allocation,
        {arguments[0], arguments[1], arguments[2], arguments[3]}, -0x34);
    if (ok) {
        const uint32_t com = run.get(receiver + 0x18);
        const uint32_t result = run.call(run.get(run.get(com) + 0x74), 0,
            {com, run.get(run.get(local) + 0x4), local, 4, 1});
        if (!result) {
            const uint32_t position = run.call(0x4f51c5, receiver + 0x54, {run.get(local)});
            const uint32_t player = run.get(local);
            if (position) {
                run.put(player + 0x20, position);
                return run.get(local);
            }
            if (player)
                run.vcall(player, 0x4, {1});
            return 0;
        }
        run.call(0x4e10d0, 0, {0x533500, 0x342, result, 0});
    }
    const uint32_t player = run.get(local);
    if (player)
        run.vcall(player, 0x4, {1});
    return 0;
}

// 0x4e0c20. Save list membership before the virtual destructor releases the peer.
uint32_t function_4e0c20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t player = arguments[0];
    if (!player)
        return 0;
    const uint32_t position = run.get(player + 0x20);
    run.vcall(player, 0x4, {1});
    if (position)
        run.call(0x4f5212, receiver + 0x54, {position});
    return 1;
}

// 0x4e0c80. DirectPlay writes the actual player pointer through the local slot.
uint32_t function_4e0c80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t local = run.automatic(-0x8);
    const uint32_t size = run.automatic(-0x4);
    const uint32_t com = run.get(receiver + 0x18);
    run.put(local, 0);
    run.put(size, 4);
    const uint32_t result = run.call(run.get(run.get(com) + 0x50), 0, {com, arguments[0], local, size, 1});
    return result ? 0 : run.get(local);
}

// 0x4e0cc0. Convert nullable peer arguments independently before the COM send.
uint32_t function_4e0cc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t first = arguments[0] ? run.get(arguments[0] + 0x4) : 0;
    const uint32_t second = arguments[1] ? run.get(arguments[1] + 0x4) : 0;
    const uint32_t com = run.get(receiver + 0x18);
    const uint32_t result = run.call(run.get(run.get(com) + 0x68), 0,
        {com, first, second, arguments[2], arguments[3], arguments[4]});
    if (result)
        run.call(0x4e10d0, 0, {0x533500, 0x442, result, 0});
    return result;
}

// 0x4e0d20. Send with already selected raw network identities.
uint32_t function_4e0d20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    const uint32_t com = run.get(receiver + 0x18);
    const uint32_t result = run.call(run.get(run.get(com) + 0x68), 0,
        {com, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]});
    if (result)
        run.call(0x4e10d0, 0, {0x533500, 0x452, result, 0});
    return result;
}

// 0x4e0fc0. Deleting destructor returns the original receiver token.
uint32_t function_4e0fc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    nested(run, 0x4e0fe0, receiver, {}, -0x8);
    if (arguments[0] & 1)
        run.call(0x4f6428, 0, {receiver});
    return receiver;
}

// 0x4e0fe0. Destroy packet data before the two CString members.
uint32_t function_4e0fe0(Run &run, uint32_t receiver, const uint32_t *) {
    run.put(receiver, 0x513fb0);
    const uint32_t buffer = run.get(receiver + 0x18);
    run.put(receiver + 0x4, 0);
    run.put(receiver + 0x20, 0);
    if (buffer)
        run.call(0x4f6428, 0, {buffer});
    const uint32_t data = run.get(receiver + 0x14);
    run.put(receiver + 0x18, 0);
    if (data)
        run.call(0x4f6428, 0, {data});
    run.put(receiver + 0x14, 0);
    run.call(0x4f6584, receiver + 0xc);
    run.call(0x4f6584, receiver + 0x8);
    run.put(receiver, 0x50becc);
    return 0;
}

// 0x4e1ae0. Assign names in order, then clear transient player storage.
uint32_t function_4e1ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    run.put(receiver + 0x4, arguments[0]);
    run.call(0x4f66cc, receiver + 0x8, {arguments[1]});
    run.call(0x4f66cc, receiver + 0xc, {arguments[2]});
    run.put(receiver + 0x10, arguments[3]);
    run.put(receiver + 0x18, 0);
    run.put(receiver + 0x1c, 0);
    run.put(receiver + 0x14, 0);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x479000:
        return function_479000(run, receiver, arguments);
    case 0x47a4b0:
        return function_47a4b0(run, receiver, arguments);
    case 0x4776b0:
        return function_4776b0(run, receiver, arguments);
    case 0x4777d0:
        return function_4777d0(run, receiver, arguments);
    case 0x477810:
        return function_477810(run, receiver, arguments);
    case 0x478f30:
        return function_478f30(run, receiver, arguments);
    case 0x486d50:
        return function_486d50(run, receiver, arguments);
    case 0x4e0930:
        return function_4e0930(run, receiver, arguments);
    case 0x4e0c20:
        return function_4e0c20(run, receiver, arguments);
    case 0x4e0c80:
        return function_4e0c80(run, receiver, arguments);
    case 0x4e0cc0:
        return function_4e0cc0(run, receiver, arguments);
    case 0x4e0d20:
        return function_4e0d20(run, receiver, arguments);
    case 0x4e0fc0:
        return function_4e0fc0(run, receiver, arguments);
    case 0x4e0fe0:
        return function_4e0fe0(run, receiver, arguments);
    case 0x4e1ae0:
        return function_4e1ae0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_call_closure_multiplayer_tail_entry, owned, body)
