// Audio and display diagnostic policy.
#include "ClawRuntime.hpp"

namespace {
using claw::Run;
using claw::s32;

struct Selection {
    uint32_t code;
    uint32_t description;
};

Selection audioSelection(uint32_t value) {
    switch (value) {
    case 0x00000000:
        return {0x532330, 0x532324};
    case 0x80004001:
        return {0x53240c, 0x532300};
    case 0x80004005:
        return {0x5323fc, 0x532300};
    case 0x80040110:
        return {0x5323e8, 0x532300};
    case 0x8007000e:
        return {0x5323d4, 0x532300};
    case 0x80070057:
        return {0x5323c0, 0x532300};
    case 0x8878000a:
        return {0x5323b0, 0x532300};
    case 0x8878001e:
        return {0x532398, 0x532300};
    case 0x88780032:
        return {0x532384, 0x532300};
    case 0x88780046:
        return {0x53236c, 0x532300};
    case 0x88780064:
        return {0x53235c, 0x532300};
    case 0x88780078:
        return {0x53234c, 0x532300};
    case 0x88780096:
        return {0x532338, 0x532300};
    case 0x887800a0:
        return {0x53230c, 0x532300};
    default:
        return {0, 0};
    }
}

Selection displaySelection(uint32_t value) {
    switch (value) {
    case 0x00000000:
        return {0x5325a8, 0x532324};
    case 0x80004001:
        return {0x532bf4, 0x532bdc};
    case 0x80004005:
        return {0x532bcc, 0x532bbc};
    case 0x8007000e:
        return {0x532ba8, 0x532300};
    case 0x80070057:
        return {0x532b94, 0x532300};
    case 0x88760064:
        return {0x532b80, 0x532b3c};
    case 0x88760078:
        return {0x532b28, 0x532300};
    case 0x88760082:
        return {0x532b14, 0x532300};
    case 0x88760091:
        return {0x532af8, 0x532ad0};
    case 0x88760096:
        return {0x532abc, 0x532300};
    case 0x887600a0:
        return {0x532590, 0x532300};
    case 0x887600aa:
        return {0x532ab0, 0x532300};
    case 0x887600b4:
        return {0x532aa0, 0x532300};
    case 0x887600d2:
        return {0x532a14, 0x532300};
    case 0x887600d4:
        return {0x532a84, 0x532a28};
    case 0x887600e1:
        return {0x5329fc, 0x532300};
    case 0x887600f0:
        return {0x5329f0, 0x5329d8};
    case 0x887600fa:
        return {0x5329c4, 0x53296c};
    case 0x887600ff:
        return {0x53295c, 0x532940};
    case 0x88760104:
        return {0x53292c, 0x532300};
    case 0x88760118:
        return {0x532918, 0x532300};
    case 0x88760122:
        return {0x532904, 0x532300};
    case 0x88760136:
        return {0x5328f0, 0x532300};
    case 0x88760140:
        return {0x5328dc, 0x532300};
    case 0x8876014a:
        return {0x5328c8, 0x532300};
    case 0x8876014f:
        return {0x5328b8, 0x532300};
    case 0x88760154:
        return {0x5328a4, 0x532300};
    case 0x88760168:
        return {0x532894, 0x532300};
    case 0x8876017c:
        return {0x53287c, 0x532300};
    case 0x88760183:
        return {0x532868, 0x532300};
    case 0x887601ae:
        return {0x532854, 0x532300};
    case 0x887601b8:
        return {0x53283c, 0x532300};
    case 0x887601c2:
        return {0x532828, 0x532300};
    case 0x887601cc:
        return {0x53280c, 0x5327e4};
    case 0x887601e0:
        return {0x5327d0, 0x532300};
    case 0x887601ea:
        return {0x5327bc, 0x532300};
    case 0x88760219:
        return {0x53279c, 0x532300};
    case 0x8876021c:
        return {0x532784, 0x53272c};
    case 0x88760230:
        return {0x5326e4, 0x5326a0};
    case 0x88760232:
        return {0x5326f4, 0x532300};
    case 0x88760233:
        return {0x532714, 0x532300};
    case 0x88760234:
        return {0x532604, 0x5325d0};
    case 0x8876023a:
        return {0x532688, 0x532300};
    case 0x8876023b:
        return {0x532670, 0x532300};
    case 0x8876023d:
        return {0x53265c, 0x532628};
    case 0x88760245:
        return {0x5325b0, 0x532300};
    case 0x88760248:
        return {0x532590, 0x532300};
    default:
        return {0, 0};
    }
}

void copyString(Run &run, uint32_t destination, uint32_t source) {
    uint32_t count = 0;
    do {
        ++count;
    } while (run.get8(source + count - 1) != 0);
    uint32_t offset = 0;
    for (; offset + 4 <= count; offset += 4) {
        run.put(destination + offset, run.get(source + offset));
    }
    for (; offset < count; ++offset) {
        run.put8(destination + offset, run.get8(source + offset));
    }
}

void format(Run &run, uint32_t output, uint32_t formatAddress, uint32_t filename, uint32_t line, uint32_t code, uint32_t low, uint32_t description) {
    if (filename && s32(line) > 0) {
        run.stackPointer = run.automatic(-0x370);
        run.call(0x4a3920, 0, {output, formatAddress, filename, line, code, low, description});
    } else {
        run.stackPointer = run.automatic(-0x368);
        run.call(0x4a3920, 0, {output, formatAddress, code, low, description});
    }
}

// 0x4b4ed0 and 0x4bd260. The policies differ in selection and output service.
uint32_t diagnostic(Run &run, bool display) {
    const uint32_t flags = display ? 0x54139c : 0x54130c;
    if (run.get(flags + 0x08)) {
        run.stackPointer = run.automatic(-0x358);
        run.icall(0x546ca4, {0x30});
    }
    if (!run.get(flags) && !run.get(flags + 0x04) && !run.get(flags + 0x0c)) {
        return 0;
    }
    const uint32_t value = run.get(run.automatic(0x0c));
    const uint32_t low = value & 0xffff;
    const uint32_t code = run.automatic(-0x340);
    const uint32_t description = run.automatic(-0x300);
    const uint32_t output = run.automatic(-0x200);
    copyString(run, description, 0x532434);
    run.stackPointer = run.automatic(-0x35c);
    run.call(0x4a3920, 0, {code, 0x532420});
    copyString(run, output, 0x534938);
    const Selection selection = display ? displaySelection(value) : audioSelection(value);
    if (selection.code) {
        copyString(run, code, selection.code);
        copyString(run, description, selection.description);
    }
    const uint32_t outputEnabled = run.get(flags);
    const uint32_t line = run.get(run.automatic(0x08));
    const uint32_t filename = run.get(run.automatic(0x04));
    const bool location = filename && s32(line) > 0;
    if (outputEnabled) {
        format(run, output, location ? 0x5322e4 : 0x5322d4, filename, line, code, low, description);
        run.stackPointer = run.automatic(-0x358);
        if (display) {
            run.call(0x4bc110, 0, {output});
        } else {
            run.icall(0x546a08, {output});
        }
    }
    if (run.get(flags + 0x04)) {
        format(run, output, location ? 0x5322b8 : 0x5322ac, filename, line, code, low, description);
        run.stackPointer = run.automatic(-0x364);
        run.icall(0x546d48, {0, output, display ? 0x532580u : 0x53229cu, 0x30});
    }
    return 0;
}

int owned(uint32_t function) {
    switch (function) {
    case 0x4b4ed0:
    case 0x4bd260:
        return 3;
    default:
        return -1;
    }
}

uint32_t body(Run &run, uint32_t function, uint32_t, const uint32_t *) {
    switch (function) {
    case 0x4b4ed0:
        return diagnostic(run, false);
    case 0x4bd260:
        return diagnostic(run, true);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}
} // namespace

CLAW_MODULE_ENTRY(claw_menu_diagnostic_policy_entry, owned, body)
