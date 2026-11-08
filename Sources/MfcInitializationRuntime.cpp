// Original MFC application initialization coordinator
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x5028ec:
        return 4;
    default:
        return -1;
    }
}

// 0x5028ec. stdcall, 4 stack argument(s), returns u32.
uint32_t function_5028ec(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    uint32_t setErrorMode = run.get(0x546b18);
    // Saved ESI, one outgoing operand, and the CALL return word.
    run.stackPointer = run.frame - 12;
    uint32_t previousMode = run.call(setErrorMode, 0, {0});
    run.call(setErrorMode, 0, {previousMode | 0x8001u});
    // The zero-operand callees enter below saved ESI and their return word.
    run.stackPointer = run.frame - 8;
    uint32_t module = run.call(0x50228f, 0);
    uint32_t instance = run.get(run.automatic(4));
    // Module fields: +8 instance and +0xc resource instance.
    run.put(module + 0x08, instance);
    run.put(module + 0x0c, instance);
    module = run.call(0x50228f, 0);
    // Module +4 holds the application object.
    uint32_t application = run.get(module + 0x04);
    if (application) {
        uint32_t previousInstance = run.get(run.automatic(8));
        // Application +0x68..0x74 holds the four initialization operands.
        run.put(application + 0x68, instance);
        run.put(application + 0x6c, previousInstance);
        uint32_t commandLine = run.get(run.automatic(12));
        run.put(application + 0x70, commandLine);
        uint32_t showCommand = run.get(run.automatic(16));
        run.put(application + 0x74, showCommand);
        run.call(0x50294f, application);
    }
    module = run.call(0x50228f, 0);
    // Module +0x14 is the byte controlling hook initialization.
    if (run.get8(module + 0x14) == 0)
        run.call(0x4fb8b9, 0);
    return 1;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x5028ec:
        return function_5028ec(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_mfc_initialization_entry, owned, body)
