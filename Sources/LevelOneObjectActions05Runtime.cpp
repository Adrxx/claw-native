// Level 1 closure object action table entries
//
// Twelve object initialisers. Each takes a record pointer and returns 0 for a
// null record, else fills the record and returns 1. All of them call SetRect
// through the import slot 0x546d5c and set three global scale floats.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x452d50:
        return 1;
    case 0x452db0:
        return 1;
    case 0x452ea0:
        return 1;
    case 0x452f80:
        return 1;
    case 0x453070:
        return 1;
    case 0x453150:
        return 1;
    case 0x453240:
        return 1;
    case 0x453310:
        return 1;
    case 0x453410:
        return 1;
    case 0x453500:
        return 1;
    case 0x453600:
        return 1;
    case 0x4536f0:
        return 1;
    default:
        return -1;
    }
}

// SetRect through the import-table slot: the slot holds the real function.
void setRect(Run &run, uint32_t rect, int32_t left, int32_t top, int32_t right, int32_t bottom) {
    uint32_t function = run.get(0x546d5c);
    run.call(function, 0, {rect, uint32_t(left), uint32_t(top), uint32_t(right), uint32_t(bottom)});
}

// Copies the NUL-terminated string at `source`, terminator included.
void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t length = 0;
    while (run.get8(source + length) != 0)
        length = length + 1;
    length = length + 1;
    for (uint32_t index = 0; index < length; ++index) {
        uint8_t value = run.get8(source + index);
        run.put8(destination + index, value);
    }
}

// Three global scale floats, all 1.0f.
void setScales(Run &run) {
    run.put(0x5262b0, 0x3f800000);
    run.put(0x5262b4, 0x3f800000);
    run.put(0x5262b8, 0x3f800000);
}

// 0x452d50. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_452d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x44 flag is cleared before the rectangles.
    run.put(record + 0x44, 0);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x22, -0x10, 0x24, 0x20);
    setScales(run);
    return 1;
}

// 0x452db0. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_452db0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x2c, -0x12, 0x2e, 0x20);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x28);
    run.put(record + 0xb4, 0x3e52);
    run.put(record + 0xb8, 0x5c0);
    setScales(run);
    return 1;
}

// 0x452ea0. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_452ea0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x1b, -0x5, 0x1b, 0x23);
    setRect(run, record + 0x58, -0x1b, -0x6, 0x19, 0x23);
    run.put(record + 0x44, 0x0);
    run.put(record + 0xac, 0xffffffc4);
    run.put(record + 0xa8, 0x40);
    setScales(run);
    return 1;
}

// 0x452f80. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_452f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x78, -0x24, -0x20, 0x23, 0x42);
    setRect(run, record + 0x68, -0x24, -0x3, 0x23, 0x42);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0xa);
    run.put(record + 0xb4, 0x77a0);
    run.put(record + 0xb8, 0x1014);
    setScales(run);
    return 1;
}

// 0x453070. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281e0);
    copyString(run, record + 0x24, 0x5281c8);
    setRect(run, record + 0x48, -0x18, 0x59, 0x17, 0x82);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x3c, 0x46, 0x4a, 0x6e);
    setRect(run, record + 0x88, -0x7, -0xa, 0x16, 0x1e);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x3c);
    setScales(run);
    return 1;
}

// 0x453150. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x2c, -0x8, 0x2e, 0x20);
    setRect(run, record + 0x88, -0x18, -0xa, 0x1e, 0x1e);
    setRect(run, record + 0x58, -0x18, -0x8, 0x20, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x0);
    run.put(record + 0xb4, 0x7a3e);
    run.put(record + 0xb8, 0x151f);
    setScales(run);
    return 1;
}

// 0x453240. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453240(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x528210);
    copyString(run, record + 0x24, 0x5281f8);
    setRect(run, record + 0x48, -0x18, 0x0, 0x16, 0x28);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x2c, -0x8, 0x29, 0x20);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x32);
    setScales(run);
    return 1;
}

// 0x453310. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453310(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x58, -0x18, -0x8, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x2c, -0x8, 0x2e, 0x20);
    setRect(run, record + 0x98, -0x58, -0x14, 0x5e, 0x14);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x0);
    run.put(record + 0xb4, 0x7dd9);
    run.put(record + 0xb8, 0x1e24);
    setScales(run);
    return 1;
}

// 0x453410. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x58, -0x20, -0x6, 0x1e, 0x28);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x20, -0x6, 0x1e, 0x28);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x0);
    run.put(record + 0xac, 0xffffffbe);
    run.put(record + 0xa8, 0x40);
    setScales(run);
    return 1;
}

// 0x453500. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453500(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281e0);
    copyString(run, record + 0x24, 0x5281c8);
    setRect(run, record + 0x48, -0x18, 0x59, 0x17, 0x82);
    setRect(run, record + 0x58, -0x18, -0x8, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x16, -0x12, 0x12, 0x28);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x32);
    run.put(record + 0xb4, 0x8d63);
    run.put(record + 0xb8, 0x7df);
    setScales(run);
    return 1;
}

// 0x453600. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_453600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x58, -0x18, -0x8, 0x18, 0x20);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x2c, -0x8, 0x2e, 0x20);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x32);
    run.put(record + 0xb4, 0x809f);
    run.put(record + 0xb8, 0x7eb);
    setScales(run);
    return 1;
}

// 0x4536f0. Fills one object record; returns 0 for a null record, else 1.
uint32_t function_4536f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    uint32_t record = arguments[0];
    if (record == 0)
        return 0;
    // +0x04 idle name, +0x24 spring name.
    copyString(run, record + 0x4, 0x5281b0);
    copyString(run, record + 0x24, 0x528194);
    setRect(run, record + 0x48, -0x20, 0xa, 0x18, 0x20);
    setRect(run, record + 0x58, -0x22, -0x6, 0x18, 0x28);
    setRect(run, record + 0x78, -0x18, -0x2e, 0x18, 0x20);
    setRect(run, record + 0x68, -0x22, -0x6, 0x17, 0x28);
    setRect(run, record + 0x88, -0x10, -0x1, 0x10, 0x20);
    run.put(record + 0x44, 0x1);
    run.put(record + 0xb0, 0x32);
    run.put(record + 0xb4, 0x792c);
    run.put(record + 0xb8, 0x902);
    setScales(run);
    return 1;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x452d50:
        return function_452d50(run, receiver, arguments);
    case 0x452db0:
        return function_452db0(run, receiver, arguments);
    case 0x452ea0:
        return function_452ea0(run, receiver, arguments);
    case 0x452f80:
        return function_452f80(run, receiver, arguments);
    case 0x453070:
        return function_453070(run, receiver, arguments);
    case 0x453150:
        return function_453150(run, receiver, arguments);
    case 0x453240:
        return function_453240(run, receiver, arguments);
    case 0x453310:
        return function_453310(run, receiver, arguments);
    case 0x453410:
        return function_453410(run, receiver, arguments);
    case 0x453500:
        return function_453500(run, receiver, arguments);
    case 0x453600:
        return function_453600(run, receiver, arguments);
    case 0x4536f0:
        return function_4536f0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_object_actions_05_entry, owned, body)
