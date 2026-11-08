// v1.3 cheat registration and mode reset
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x423e40:
        return 3;
    case 0x423e80:
        return 0;
    case 0x42a960:
        return 0;
    default:
        return -1;
    }
}

// 0x423e40. Registers a key with an allocated command/flag pair.
uint32_t registerCheat(Run &run, uint32_t receiver, uint32_t key, uint32_t command, uint32_t flag) {
    uint32_t entry = run.call(0x4fcaea, 0, {8});
    if (entry) {
        // Entry +0x04 is the mode flag; +0x00 is the command.
        run.put(entry + 0x04, flag);
        run.put(entry + 0x00, command);
        // The key map starts at receiver +0x04.
        uint32_t slot = run.call(0x4fc6d6, receiver + 0x04, {key});
        run.put(slot, entry);
    }
    return 0;
}

uint32_t function_423e40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    return registerCheat(run, receiver, arguments[0], arguments[1], arguments[2]);
}

// 0x423e80. Preserves the original encoded key addresses and insertion order.
uint32_t function_423e80(Run &run, uint32_t receiver, const uint32_t *) {
    static const uint32_t registrations[][3] = {
        {0x5233d4, 0x8044, 0},
        {0x5233cc, 0x8043, 0},
        {0x5233c0, 0x8045, 0},
        {0x5233b4, 0x8046, 0},
        {0x5233ac, 0x8047, 0},
        {0x52339c, 0x8049, 0},
        {0x523390, 0x804a, 0},
        {0x523380, 0x804f, 0},
        {0x523378, 0x805b, 0},
        {0x52336c, 0x8064, 0},
        {0x523360, 0x8065, 0},
        {0x523354, 0x8066, 0},
        {0x52334c, 0x806a, 0},
        {0x523340, 0x806c, 0},
        {0x523330, 0x8071, 0},
        {0x523324, 0x808b, 0},
        {0x523318, 0x808d, 0},
        {0x523310, 0x808e, 0},
        {0x523304, 0x8091, 0},
        {0x5232f8, 0x8092, 0},
        {0x5232ec, 0x8093, 0},
        {0x5232e0, 0x80b2, 0},
        {0x5232d4, 0x80b5, 0},
        {0x5232c8, 0x80b6, 0},
        {0x5232b8, 0x809c, 0},
        {0x5232ac, 0x809d, 0},
        {0x52329c, 0x809e, 0},
        {0x523290, 0x809f, 0},
        {0x523284, 0x80a0, 0},
        {0x523278, 0x80a1, 0},
        {0x523268, 0x80a2, 0},
        {0x52325c, 0x80a3, 0},
        {0x523250, 0x80a4, 0},
        {0x523244, 0x80a5, 0},
        {0x523238, 0x80a6, 0},
        {0x523224, 0x80a7, 0},
        {0x523218, 0x80a8, 0},
        {0x523208, 0x80a9, 0},
        {0x5231fc, 0x800e, 0},
        {0x5231f0, 0x800f, 0},
        {0x5231e4, 0x80aa, 0},
        {0x5231dc, 0x8076, 0},
        {0x5231d0, 0x8077, 0},
        {0x5231c4, 0x8078, 0},
        {0x5231b8, 0x8079, 0},
        {0x5231b0, 0x804b, 1},
        {0x5231a8, 0x804c, 1},
        {0x52319c, 0x804d, 1},
        {0x523190, 0x804e, 1},
        {0x523184, 0x806e, 1},
        {0x523178, 0x807a, 1},
        {0x523170, 0x807b, 1},
        {0x523168, 0x8086, 1},
        {0x523160, 0x8086, 1},
        {0x523154, 0x8086, 1},
        {0x52314c, 0x8086, 1},
        {0x523140, 0x8087, 1},
        {0x523134, 0x8088, 1},
        {0x523128, 0x8089, 1},
        {0x52311c, 0x808a, 1},
        {0x523110, 0x80ad, 1},
        {0x523108, 0x80ae, 1},
        {0x5230fc, 0x80af, 1},
        {0x5230f0, 0x80b0, 1},
        {0x5230e0, 0x80b1, 1},
        {0x5230d0, 0x80b3, 1},
        {0x5230c4, 0x80b4, 1},
    };
    for (const auto &registration : registrations) {
        registerCheat(run, receiver, registration[0], registration[1], registration[2]);
    }
    return 0;
}

// 0x42a960. Clears the fourteen global cheat mode words.
uint32_t function_42a960(Run &run, uint32_t, const uint32_t *) {
    run.put(0x53599c, 0);
    run.put(0x53592c, 0);
    run.put(0x535930, 0);
    run.put(0x535934, 0);
    run.put(0x535938, 0);
    run.put(0x535940, 0);
    run.put(0x53593c, 0);
    run.put(0x535944, 0);
    run.put(0x535948, 0);
    run.put(0x53594c, 0);
    run.put(0x535950, 0);
    run.put(0x535958, 0);
    run.put(0x535954, 0);
    run.put(0x535998, 0);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x423e40:
        return function_423e40(run, receiver, arguments);
    case 0x423e80:
        return function_423e80(run, receiver, arguments);
    case 0x42a960:
        return function_42a960(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_v13_cheat_registration_entry, owned, body)
