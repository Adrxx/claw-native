// Gameplay key-down handler and cheat-code buffer
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
    case 0x46bb30:
        return 2;
    case 0x422e00:
        return 2;
    default:
        return -1;
    }
}

// 0x422e00. Cheat-code key buffer. Keys outside 0x30..0x5a clear the buffer;
// others append (key + 0x11) and, from five characters on, look the buffer up
// in the map at +4 and post the command found.
void cheatCodeKey(Run &run, uint32_t cheat, uint32_t key, uint32_t now) {
    if (s32(key) < 0x30 || s32(key) > 0x5a) {
        run.put8(cheat + 0x20, 0);
        run.put(cheat + 0x120, 0);
        return;
    }
    if (run.get(cheat + 0x124) + 0x5dc < now || s32(run.get(cheat + 0x120)) > 0xc8) {
        run.put8(cheat + 0x20, 0);
        run.put(cheat + 0x120, 0);
    }
    run.put(cheat + 0x124, now);
    uint32_t count = run.get(cheat + 0x120);
    run.put8(cheat + count + 0x20, uint8_t(key + 0x11));
    count = run.get(cheat + 0x120);
    count = count + 1;
    run.put(cheat + 0x120, count);
    run.put8(cheat + count + 0x20, 0);
    if (s32(run.get(cheat + 0x120)) < 5)
        return;
    uint32_t slot = run.automatic(4);
    run.put(slot, 0);
    uint32_t found = run.call(0x4f6286, cheat + 4, {cheat + 0x20, slot});
    uint32_t value = run.get(slot);
    uint32_t command = found != 0 ? value : 0;
    if (command == 0)
        return;
    uint32_t id = run.get(command);
    if (s32(id) <= 0)
        return;
    run.call(0x546d50, 0, {run.get(cheat), 0x111, id, 0});
    uint8_t flags = run.get8(command + 4);
    if ((flags & 1) == 0)
        run.put(cheat + 0x128, 1);
    run.put8(cheat + 0x20, 0);
    run.put(cheat + 0x120, 0);
}

// 0x46bb30. Gameplay key-down: feeds the key to the cheat buffer and turns
// Escape into a window command. Always returns 1.
uint32_t gameplayKeyDown(Run &run, uint32_t state, uint32_t key) {
    uint32_t app = run.get(state + 4);
    if (run.get(app + 0xc) != 0)
        return 1;
    uint32_t clock = run.get(0x537208);
    cheatCodeKey(run, run.get(app + 0x48), key, clock);
    if (key != 0x1b)
        return 1;
    uint32_t again = run.get(state + 4);
    uint32_t wrapper = run.get(again + 4);
    uint32_t window = run.get(wrapper + 4);
    run.call(0x546d50, 0, {window, 0x111, 0x8080, 0});
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x46bb30:
        return gameplayKeyDown(run, receiver, arguments[0]);
    case 0x422e00:
        cheatCodeKey(run, receiver, arguments[0], arguments[1]);
        return 0;
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_gameplay_key_down_entry, owned, body)
