// Level 1 enemy contact helper 0x44f510
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
    case 0x44f510:
        return 0;
    default:
        return -1;
    }
}

// 0x44f510. Enemy contact helper: saves and replaces the animation at +0x10,
// copies a field from the object at +0x12c, plays up to two sounds picked at
// random, and sets a signed direction constant at +0x54.
// Fields: +0x10 animation object, +0x12c linked object, +0x18c direction,
// +0x338 argument for 0x4c8220, +0x390..+0x39c four sound objects,
// +0x418 sound object. Globals: 0x532c0c enable flag, 0x532c10 sound argument.
void playSound(Run &run, uint32_t sound) {
    uint32_t enabled = run.get(0x532c0c);
    uint32_t argument = run.get(0x532c10);
    if (enabled == 0)
        return;
    uint32_t target = run.get(sound + 0x10);
    run.call(0x4b45f0, target, {argument, 0, 0, 0});
}

uint32_t function_44f510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x20, 1);
    uint32_t animation = run.get(receiver + 0x10);
    run.put(receiver + 0x24, run.get(animation + 0x1c));
    uint32_t created = run.call(0x4dba00, 0x537668, {0x523210});
    uint32_t animationAgain = run.get(receiver + 0x10);
    run.put(animationAgain + 0x1c, created);
    uint32_t linked = run.get(receiver + 0x12c);
    uint32_t argument = run.get(receiver + 0x338);
    uint32_t linkedField = run.get(linked + 0x190);
    run.put(receiver + 0x134, linkedField);
    run.call(0x4c8220, linked + 0x188, {argument});
    uint32_t first = run.get(receiver + 0x418);
    if (first != 0)
        playSound(run, first);
    uint32_t random = run.call(0x4a3050, 0);
    uint32_t sign = uint32_t(s32(random) >> 31);
    uint32_t index = (((random ^ sign) - sign) & 3) ^ sign;
    index = index - sign;
    uint32_t sound = 0;
    switch (index) {
    case 0:
        sound = run.get(receiver + 0x390);
        break;
    case 1:
        sound = run.get(receiver + 0x394);
        break;
    case 2:
        sound = run.get(receiver + 0x398);
        break;
    case 3:
        sound = run.get(receiver + 0x39c);
        break;
    default:
        break;
    }
    if (sound != 0)
        playSound(run, sound);
    uint32_t direction = run.get(receiver + 0x18c);
    run.put(receiver + 0x50, 0);
    if (direction == 3)
        run.put(receiver + 0x54, 0x40690000);
    else
        run.put(receiver + 0x54, 0xc0690000);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44f510:
        return function_44f510(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_enemy_base_callee_01_entry, owned, body)
