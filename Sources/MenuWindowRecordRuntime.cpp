// Menu window record initialization
//
#include "ClawRuntime.hpp"

namespace {

using claw::Run;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x4b8410:
        return 0;
    default:
        return -1;
    }
}

// 0x4b8410 WindowRecord::initialize. thiscall, 0 stack argument(s), returns u32.
uint32_t function_4b8410(Run &run, uint32_t receiver, const uint32_t *) {
    // +0x00 vtable, +0x04 and +0x0c cleared record fields; +0x08 is preserved.
    run.put(receiver + 0x00, 0x50c3cc);
    run.put(receiver + 0x04, 0);
    run.put(receiver + 0x0c, 0);
    return receiver;
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x4b8410:
        return function_4b8410(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_menu_window_record_entry, owned, body)
