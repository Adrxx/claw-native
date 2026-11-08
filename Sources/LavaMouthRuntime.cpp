// Original LavaMouth callback: creates, advances, and controls its runtime object.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

constexpr uint32_t kRuntimeData = 0x6c;
constexpr uint32_t kRuntimeObject = 0x18;
constexpr uint32_t kCommand = 0x1c;

int owned(uint32_t function) {
    return function == 0x457620 ? 1 : -1;
}

// 0x457620. The callback reads the command from the object's runtime data.
uint32_t lavaMouthCallback(Run &run, uint32_t object) {
    // Object +0x6c: runtime data; data +0x18: runtime object; +0x1c: command.
    uint32_t data = run.get(object + kRuntimeData);
    uint32_t command = run.get(data + kCommand);
    if (command == 0) {
        run.put(data + kCommand, 1000);
        uint32_t allocation = run.call(0x4f63ec, 0, {0xb8});
        uint32_t runtime = 0;
        if (allocation != 0)
            runtime = run.call(0x457b10, allocation, {object});
        run.vcall(runtime, 0x10);
        run.put(data + kRuntimeObject, runtime);
    } else if (command == 29) {
        uint32_t runtime = run.get(data + kRuntimeObject);
        run.vcall(runtime, 0x20);
    } else if (command == 30) {
        uint32_t runtime = run.get(data + kRuntimeObject);
        run.vcall(runtime, 0x1c);
    } else if (command != 1000) {
        uint32_t runtime = run.get(data + kRuntimeObject);
        run.call(0x4dc870, 0, {runtime});
    }
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *arguments) {
    switch (function) {
    case 0x457620:
        return lavaMouthCallback(run, arguments[0]);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_lava_mouth_entry, owned, body)
