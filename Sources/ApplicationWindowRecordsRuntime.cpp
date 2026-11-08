// Whole original outer window-owner constructors. Source window creation and
// application registration are separate dependencies.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
int owned(uint32_t function) {
    switch (function) {
    case 0x423300:
    case 0x4b8990:
        return 0;
    default:
        return -1;
    }
}
uint32_t function_4b8990(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver, 0x50bc24);
    run.put(receiver + 4, 0);
    run.put(receiver + 8, 0);
    run.put(receiver + 0x10, 0);
    run.put(receiver + 0x0c, 0);
    run.put(receiver + 0x240, 0);
    run.put(receiver + 0x248, 0);
    run.put(receiver + 0x24c, 0);
    run.put(receiver + 0x250, 0);
    uint32_t count = run.get(0x541340);
    run.put(0x541340, count + 1);
    return receiver;
}
uint32_t function_423300(Run &run, uint32_t receiver, const uint32_t *arguments) {
    function_4b8990(run, receiver, arguments);
    run.put(receiver, 0x50bbdc);
    return receiver;
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x423300:
        return function_423300(run, receiver, arguments);
    case 0x4b8990:
        return function_4b8990(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
}
CLAW_MODULE_ENTRY(claw_application_window_records_entry, owned, body)
