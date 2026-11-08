// Level 1 Rat construction and update, batch 1
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

uint32_t function_47c910(Run &run, uint32_t receiver, const uint32_t *arguments);
uint32_t function_408050(Run &run, uint32_t receiver, const uint32_t *arguments);

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x47c850:
        return 1;
    case 0x47c910:
        return 1;
    case 0x408050:
        return 0;
    case 0x406310:
        return 0;
    case 0x4357a0:
        return 0;
    default:
        return -1;
    }
}

// 0x47c850. cdecl, one stack argument (the owner object). Drives the Rat's
// state at [[owner + 0x6c] + 0x1c]: 0 creates the Rat, 0x1d and 0x1e call
// virtual methods of the Rat at [state + 0x18], 1000 does nothing, and any other
// value calls 0x4dc870 on the Rat. Always returns 1.
uint32_t function_47c850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t owner = arguments[0];
    uint32_t state = run.get(owner + 0x6c);
    uint32_t mode = run.get(state + 0x1c);
    if (mode > 0x1d) {
        if (mode == 0x1e) {
            uint32_t rat = run.get(state + 0x18);
            run.vcall(rat, 0x1c);
            return 1;
        }
        if (mode == 0x3e8)
            return 1;
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    if (mode == 0x1d) {
        uint32_t rat = run.get(state + 0x18);
        run.vcall(rat, 0x20);
        return 1;
    }
    if (mode != 0) {
        run.call(0x4dc870, 0, {run.get(state + 0x18)});
        return 1;
    }
    run.put(state + 0x1c, 0x3e8);
    uint32_t memory = run.call(0x4f63ec, 0, {0x420});
    uint32_t rat = 0;
    if (memory)
        rat = function_47c910(run, memory, &owner);
    run.vcall(rat, 0x10);
    run.put(state + 0x18, rat);
    return 1;
}

// Sets one bit of the bit set at `set`: small sets (capacity up to 0x20) keep
// their word inline at +0xc, larger ones through the pointer at +0xc.
uint32_t bitWordAddress(Run &run, uint32_t set) {
    if (run.get(set + 0x8) > 0x20)
        return run.get(set + 0xc);
    return set + 0xc;
}

// Looks a name up in the table at `table`, falling back to GAME_NULL (0x5234b4).
uint32_t lookupOrNull(Run &run, uint32_t table, uint32_t name) {
    uint32_t found = run.call(0x4062e0, table, {name});
    if (found == 0)
        found = run.call(0x4062e0, table, {0x5234b4});
    return found;
}

// 0x47c910. thiscall, one stack argument. Rat constructor; returns the object.
// Fields: +0xc owner state, +0x70 double, +0x128 animation table,
// +0x12c the Rat's actor record, +0x2d0, +0x2e4 hit points, +0x2f4 bit set.
uint32_t function_47c910(Run &run, uint32_t receiver, const uint32_t *arguments) {
    uint32_t self = receiver;
    run.call(0x4332f0, self, {arguments[0]});
    run.put(self + 0x418, 0);
    run.put(self + 0x41c, 0);
    run.put(self + 0x0, 0x50f084);
    double position = run.getd(self + 0x70);
    double offset = run.getd(0x50f068);
    run.putd(self + 0x70, position - offset);
    run.put(self + 0x2d0, 5);
    run.put(self + 0x2e4, 0xa);
    double scaledHealth = double(run.getf(0x5262b8)) * double(run.getf(0x50f070));
    uint32_t health = run.call_x87(0x4a30e0, 0, scaledHealth);
    if (health <= 0x63)
        health = 0x63;
    uint32_t shared = run.get(self + 0xc);
    run.put(self + 0x2e4, health);
    run.put(shared + 0x10c, 1);
    uint32_t sharedA = run.get(self + 0xc);
    double valueA = double(s32(run.get(sharedA + 0x10c))) * double(run.getf(0x5262b4));
    uint32_t convertedA = run.call_x87(0x4a30e0, 0, valueA);
    run.put(sharedA + 0x10c, convertedA);
    uint32_t sharedB = run.get(self + 0xc);
    run.put(sharedB + 0x104, 5);
    uint32_t sharedC = run.get(self + 0xc);
    double valueC = double(s32(run.get(sharedC + 0x104))) * double(run.getf(0x5262b0));
    uint32_t convertedC = run.call_x87(0x4a30e0, 0, valueC);
    run.put(sharedC + 0x104, convertedC);
    uint32_t sharedD = run.get(self + 0xc);
    if (run.get(sharedD + 0x148) == 0)
        run.put(sharedD + 0x148, 0x3c);
    run.call(0x4c7970, run.get(self + 0x12c), {0x52b0a4});
    uint32_t actor = run.get(self + 0x12c);
    uint32_t frames = run.get(actor + 0x170);
    if (frames != 0) {
        uint32_t copy = run.call(0x40f680, frames, {0xc});
        run.put(actor + 0x174, copy);
        run.put(actor + 0x16c, 0xc);
    }
    uint32_t table = self + 0x128;
    uint32_t walk = lookupOrNull(run, table, 0x52b094);
    run.put(self + 0x354, walk);
    uint32_t idle = lookupOrNull(run, table, 0x52b084);
    run.put(self + 0x350, idle);
    uint32_t throwSouth = lookupOrNull(run, table, 0x52b06c);
    run.put(self + 0x35c, throwSouth);
    uint32_t throwEastWest = lookupOrNull(run, table, 0x52b054);
    run.put(self + 0x360, throwEastWest);
    uint32_t dead = lookupOrNull(run, table, 0x52b044);
    run.put(self + 0x374, dead);
    uint32_t local = run.automatic(4);
    run.put(local, 0);
    uint32_t registry = run.get(run.get(run.get(self + 0x12c) + 0xc) + 0x28) + 0x10;
    run.call(0x4f6286, registry, {0x52a6f8, local});
    uint32_t eehh = run.get(local);
    run.put(local, 0);
    run.put(self + 0x400, eehh);
    uint32_t registry2 = run.get(run.get(run.get(self + 0x12c) + 0xc) + 0x28) + 0x10;
    run.call(0x4f6286, registry2, {0x52a6e8, local});
    uint32_t mouseKill = run.get(local);
    run.put(self + 0x3a4, mouseKill);
    run.call(0x47d150, self);
    uint32_t bits = self + 0x2f4;
    if (run.get(self + 0x2fc) <= 3) {
        run.call(0x4dbd20, bits, {3});
    } else {
        uint32_t word = bitWordAddress(run, bits);
        run.put(word, run.get(word) | 8);
    }
    if (run.get(bits + 0x8) == 0) {
        run.call(0x4dbd20, bits, {0});
    } else {
        uint32_t word = bitWordAddress(run, bits);
        run.put(word, run.get(word) | 1);
    }
    uint32_t flagsOwner = run.get(self + 0x12c);
    run.put(flagsOwner + 0x8, run.get(flagsOwner + 0x8) | 0x40);
    run.put(run.get(self + 0x12c) + 0xd0, 4);
    run.put(run.get(self + 0x12c) + 0xd4, 0x3000022);
    uint32_t sized = run.get(self + 0x12c);
    uint32_t sizedFrames = run.get(sized + 0x170);
    if (sizedFrames != 0) {
        uint32_t count = run.get(sizedFrames + 0x64);
        run.put(sized + 0x16c, count);
        uint32_t copy2 = run.call(0x40f680, sizedFrames, {count});
        run.put(sized + 0x174, copy2);
    }
    function_408050(run, run.get(self + 0x12c), nullptr);
    run.call(0x406240, run.get(self + 0x12c));
    uint32_t box = run.get(self + 0x12c);
    run.put(box + 0x118, 0xfffffff6);
    run.put(box + 0x11c, 0x14);
    run.put(box + 0x120, 0xa);
    run.put(box + 0x124, 0x1e);
    uint32_t owner = run.get(self + 0xc);
    run.put(owner + 0x124, run.get(owner + 0x124) + 3);
    uint32_t actor2 = run.get(table + 4);
    run.put(actor2 + 0x50, run.get(actor2 + 0x50) + 0xffffffe0);
    uint32_t head = run.get(table);
    uint32_t scene = run.get(run.get(head + 0xc) + 0x24);
    run.call(0x4cd800, scene, {head, 0});
    run.put(run.get(table) + 0xcc, 1);
    return self;
}

// 0x408050. Recomputes the cached extents at +0x138..+0x144 from the frame
// record at +0x174, when there is one.
uint32_t function_408050(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t frame = run.get(receiver + 0x174);
    if (frame == 0)
        return 0;
    run.put(receiver + 0x138, run.get(frame + 0x20) - run.get(frame + 0x18));
    run.put(receiver + 0x13c, run.get(frame + 0x24) - run.get(frame + 0x1c));
    run.put(receiver + 0x140, run.get(frame + 0x18) + run.get(frame + 0x20) - 1);
    run.put(receiver + 0x144, run.get(frame + 0x24) + run.get(frame + 0x1c) - 1);
    return 0;
}

// Negates and swaps one pair of rectangle edges unless the first is the
// 0x80000000 sentinel.
void flipPair(Run &run, uint32_t base, uint32_t first, uint32_t second) {
    uint32_t value = run.get(base + first);
    if (value == 0x80000000)
        return;
    uint32_t other = run.get(base + second);
    run.put(base + first, 0 - other);
    run.put(base + second, 0 - value);
}

// 0x406310. Clears the mirrored flag (bit 1 of [this+4]+0x40) and mirrors the
// extents back, only when the flag was set.
uint32_t function_406310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t owner = run.get(receiver + 4);
    if ((run.get(owner + 0x40) & 2) == 0)
        return 0;
    uint32_t left = run.get(receiver + 0x10);
    uint32_t right = run.get(receiver + 0x18);
    run.put(receiver + 0x10, 0 - right);
    run.put(receiver + 0x18, 0 - left);
    run.put(owner + 0x40, run.get(owner + 0x40) & 0xfffffffd);
    uint32_t shape = run.get(receiver + 4);
    flipPair(run, shape, 0x118, 0x120);
    flipPair(run, shape, 0x128, 0x130);
    flipPair(run, shape, 0x138, 0x140);
    return 0;
}

// 0x4357a0. The mirror of 0x406310: sets the flag and mirrors the extents,
// only when the flag was clear.
uint32_t function_4357a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t owner = run.get(receiver + 4);
    if ((run.get(owner + 0x40) & 2) != 0)
        return 0;
    uint32_t left = run.get(receiver + 0x10);
    uint32_t right = run.get(receiver + 0x18);
    run.put(receiver + 0x10, 0 - right);
    run.put(receiver + 0x18, 0 - left);
    run.put(owner + 0x40, run.get(owner + 0x40) | 2);
    uint32_t shape = run.get(receiver + 4);
    flipPair(run, shape, 0x118, 0x120);
    flipPair(run, shape, 0x128, 0x130);
    flipPair(run, shape, 0x138, 0x140);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x47c850:
        return function_47c850(run, receiver, arguments);
    case 0x47c910:
        return function_47c910(run, receiver, arguments);
    case 0x408050:
        return function_408050(run, receiver, arguments);
    case 0x406310:
        return function_406310(run, receiver, arguments);
    case 0x4357a0:
        return function_4357a0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_rat_and_speech_01_entry, owned, body)
