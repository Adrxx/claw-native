// Original surface holder and renderer queue
// Recovered from the reviewed original packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x45fe40:
        return 1;
    case 0x45fe60:
        return 0;
    case 0x45fec0:
        return 0;
    case 0x4b9150:
        return 2;
    case 0x4b91f0:
        return 1;
    case 0x4bb000:
        return 0;
    case 0x4bb060:
        return 1;
    case 0x4bb080:
        return 0;
    case 0x4bc4f0:
        return 1;
    case 0x4bc670:
        return 5;
    case 0x4bc810:
        return 1;
    case 0x4bc830:
        return 0;
    case 0x4bc890:
        return 1;
    case 0x4bcf80:
        return 2;
    case 0x4bf970:
        return 6;
    case 0x4bfb80:
        return 4;
    case 0x4bfbd0:
        return 2;
    case 0x4ca6f0:
        return 4;
    case 0x4ca8b0:
        return 0;
    case 0x4ca960:
        return 3;
    case 0x4cab90:
        return 3;
    case 0x4cabc0:
        return 0;
    case 0x4cabe0:
        return 1;
    case 0x4cac00:
        return 2;
    case 0x4cac40:
        return 3;
    case 0x4caca0:
        return 0;
    case 0x4cacb0:
        return 0;
    case 0x4cf730:
        return 0;
    case 0x4cf750:
        return 0;
    case 0x4cf760:
        return 1;
    case 0x4cf780:
        return 0;
    case 0x4d4000:
        return 2;
    case 0x4d4160:
        return 0;
    case 0x4d5510:
        return 3;
    case 0x4d63c0:
        return 2;
    default:
        return -1;
    }
}

// Native internal calls retain the original callee entry frame for escaped locals.
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments);

uint32_t external(Run &run, uint32_t function, uint32_t receiver,
                  std::initializer_list<uint32_t> arguments, int32_t delta) {
    uint32_t saved = run.stackPointer;
    run.stackPointer = run.automatic(delta);
    uint32_t result = run.call(function, receiver, arguments);
    run.stackPointer = saved;
    return result;
}

uint32_t invoke(Run &run, uint32_t function, uint32_t receiver,
                std::initializer_list<uint32_t> arguments, int32_t delta) {
    if (owned(function) < 0)
        return external(run, function, receiver, arguments, delta);
    uint32_t saved = run.frame;
    run.frame = run.automatic(delta);
    uint32_t result = body(run, function, receiver, arguments.begin());
    run.frame = saved;
    return result;
}

uint32_t virt(Run &run, uint32_t receiver, uint32_t slot,
              std::initializer_list<uint32_t> arguments, int32_t delta) {
    return invoke(run, run.get(run.get(receiver) + slot), receiver, arguments, delta);
}

// Surface common constructor fields, with the original vtable store ordering.
void surface(Run &run, uint32_t receiver, uint32_t table, bool tableFirst) {
    run.call(0x4f54ea, receiver + 0x90);
    if (tableFirst)
        run.put(receiver + 0x0, table);
    run.put(receiver + 0x8, 0);
    run.put(receiver + 0x4, 0);
    run.put(receiver + 0x78, 0);
    run.put(receiver + 0xa4, 0);
    run.put(receiver + 0xb4, 0);
    if (!tableFirst)
        run.put(receiver + 0x0, table);
}

// Parent +0x38 is a sticky scene error; reload the parent after callbacks.
void error(Run &run, uint32_t receiver, uint32_t code) {
    uint32_t parent = run.get(receiver + 0xc);
    if (!run.get(parent + 0x38))
        run.put(parent + 0x38, code);
}

// 0x45fe40. Original normal-return body.
uint32_t function_45fe40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x45fe40;
    uint32_t destructor = function == 0x4cabe0 ? 0x45fec0 : function + 0x20;
        invoke(run, destructor, receiver, {}, -0x8);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
}

// 0x4bb060. Original normal-return body.
uint32_t function_4bb060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4bb060;
    uint32_t destructor = function == 0x4cabe0 ? 0x45fec0 : function + 0x20;
        invoke(run, destructor, receiver, {}, -0x8);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
}

// 0x4bc810. Original normal-return body.
uint32_t function_4bc810(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4bc810;
    uint32_t destructor = function == 0x4cabe0 ? 0x45fec0 : function + 0x20;
        invoke(run, destructor, receiver, {}, -0x8);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
}

// 0x4cabe0. Original normal-return body.
uint32_t function_4cabe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4cabe0;
    uint32_t destructor = function == 0x4cabe0 ? 0x45fec0 : function + 0x20;
        invoke(run, destructor, receiver, {}, -0x8);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
}

// 0x4cf760. Original normal-return body.
uint32_t function_4cf760(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4cf760;
    uint32_t destructor = function == 0x4cabe0 ? 0x45fec0 : function + 0x20;
        invoke(run, destructor, receiver, {}, -0x8);
        if (arguments[0] & 1)
            run.call(0x4f6428, 0, {receiver});
        return receiver;
}

// 0x45fe60. Original normal-return body.
uint32_t function_45fe60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x0, 0x50e8e4);
        invoke(run, 0x4d4160, receiver, {}, -0x1c);
        run.put(receiver + 0x10, 0);
        run.put(receiver + 0x8, 0);
        run.put(receiver + 0xc, 0);
        run.put(receiver + 0x4, 0xffffffff);
        run.put(receiver + 0x0, 0x50becc);
        return 0;
}

// 0x45fec0. Original normal-return body.
uint32_t function_45fec0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x4, 0xffffffff);
        run.put(receiver + 0x10, 0);
        run.put(receiver + 0x8, 0);
        run.put(receiver + 0xc, 0);
        run.put(receiver + 0x0, 0x50becc);
        return 0;
}

// 0x4b9150. Original normal-return body.
uint32_t function_4b9150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (arguments[1]) {
            for (uint32_t offset = 0; offset < 0x6c; offset += 4)
                run.put(receiver + 0xc + offset, run.get(arguments[1] + offset));
        }
        return virt(run, receiver, 0x20, {arguments[0]}, -0xc);
}

// 0x4b91f0. Original normal-return body.
uint32_t function_4b91f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x8, arguments[0]);
        for (uint32_t offset = 0; offset < 0x6c; offset += 4)
            run.put(receiver + 0xc + offset, 0);
        uint32_t interface = run.get(receiver + 0x8);
        run.put(receiver + 0xc, 0x6c);
        uint32_t result = run.call(run.get(run.get(interface) + 0x58), 0, {interface, receiver + 0xc});
        if (result)
            run.call(0x4bd260, 0, {0x5324dc, 0x7b, result});
        uint32_t depth = run.get(receiver + 0x60);
        run.put(receiver + 0xb8, 0);
        run.put(receiver + 0xa4, depth);
        uint32_t width = run.get(receiver + 0x18);
        uint32_t bytes = depth == 0x10 ? 2 : depth == 0x18 ? 3 : depth == 0x20 ? 4 : 1;
        run.put(receiver + 0xa8, width * bytes);
        run.put(receiver + 0xac, bytes);
        uint32_t pitch = run.get(receiver + 0x1c) / run.get(receiver + 0xac);
        run.put(receiver + 0x84, width);
        uint32_t rowBytes = run.get(receiver + 0xa8);
        run.put(receiver + 0x7c, 0);
        run.put(receiver + 0x80, 0);
        run.put(receiver + 0xb0, pitch);
        uint32_t height = run.get(receiver + 0x14);
        run.put(receiver + 0x88, height);
        uint32_t flags = run.get(receiver + 0x78);
        run.put(receiver + 0x8c, rowBytes * height);
        run.put(receiver + 0x78, flags | 1);
        return 1;
}

// 0x4bb000. Original normal-return body.
uint32_t function_4bb000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.get(receiver + 0x8) && run.gets(receiver + 0x84) > 0 && run.gets(receiver + 0x88) > 0;
}

// 0x4bb080. Original normal-return body.
uint32_t function_4bb080(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x0, 0x513588);
        external(run, 0x4b9540, receiver, {}, -0x18);
        external(run, 0x4f551d, receiver + 0x90, {}, -0x18);
        return 0;
}

// 0x4bc830. Original normal-return body.
uint32_t function_4bc830(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x0, 0x513588);
        external(run, 0x4b9540, receiver, {}, -0x18);
        external(run, 0x4f551d, receiver + 0x90, {}, -0x18);
        return 0;
}

// 0x4bc4f0. Original normal-return body.
uint32_t function_4bc4f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t item = arguments[0];
        run.call(0x4f5212, receiver + 0x3b8, {run.get(item + 0x4)});
        if (item)
            virt(run, item, 0x0, {1}, -0xc);
        return 0;
}

// 0x4bc670. Original normal-return body.
uint32_t function_4bc670(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t item = run.call(0x4f63ec, 0, {0xbc});
        if (item)
            surface(run, item, 0x513690, false);
        if (!virt(run, item, 0x2c, {receiver, arguments[0], arguments[1], arguments[2], arguments[3], arguments[4]}, -0x38)) {
            if (item)
                virt(run, item, 0x0, {1}, -0x24);
            return 0;
        }
        external(run, 0x4bc490, receiver, {item}, -0x24);
        return item;
}

// 0x4bc890. Original normal-return body.
uint32_t function_4bc890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t item = run.call(0x4f63ec, 0, {0xbc});
        if (item)
            surface(run, item, 0x5136c0, false);
        if (!virt(run, item, 0x24, {receiver, 0x18, 0x21, arguments[0]}, -0x30)) {
            if (item)
                virt(run, item, 0x0, {1}, -0x24);
            return 0;
        }
        external(run, 0x4bc490, receiver, {item}, -0x24);
        run.put(receiver + 0x474, run.get(item + 0xa4));
        return item;
}

// 0x4bcf80. Original normal-return body.
uint32_t function_4bcf80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t flags = run.automatic(0x8);
        uint32_t output = run.automatic(-0x10);
        run.put(flags, arguments[1]);
        uint32_t interface = run.get(arguments[0] + 0x8);
        run.put(output, 0);
        uint32_t result = run.call(run.get(run.get(interface) + 0x30), 0, {interface, flags, output});
        if (result) {
            run.call(0x4bd260, 0, {0x532524, 0x64a, result});
            return 0;
        }
        uint32_t item = run.call(0x4f63ec, 0, {0xbc});
        if (item)
            surface(run, item, 0x513588, true);
        if (!virt(run, item, 0x4, {run.get(output)}, -0x24)) {
            if (item)
                virt(run, item, 0x0, {1}, -0x24);
            return 0;
        }
        external(run, 0x4bc490, receiver, {item}, -0x24);
        return item;
}

// 0x4bf970. Original normal-return body.
uint32_t function_4bf970(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (!external(run, 0x4b9180, receiver, {arguments[0], arguments[1], arguments[2], arguments[3], arguments[4] | 0x40}, -0x1c))
            return 0;
        if (arguments[5] != 0xffffffff)
            external(run, 0x4b9990, receiver, {arguments[5]}, -0xc);
        return 1;
}

// 0x4bfb80. Original normal-return body.
uint32_t function_4bfb80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    for (uint32_t offset = 0; offset < 0x6c; offset += 4)
            run.put(receiver + 0xc + offset, 0);
        run.put(receiver + 0x10, arguments[2]);
        run.put(receiver + 0x74, arguments[1] | 0x200);
        run.put(receiver + 0xc, 0x6c);
        run.put(receiver + 0x20, arguments[3]);
        return invoke(run, 0x4b9150, receiver, {arguments[0], 0}, -0x14) != 0;
}

// 0x4bfbd0. Original normal-return body.
uint32_t function_4bfbd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return invoke(run, 0x4b9150, receiver, {arguments[0], arguments[1]}, -0xc) != 0;
}

// 0x4ca6f0. Original normal-return body.
uint32_t function_4ca6f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t primary = run.call(0x4f63ec, 0, {0x30});
        if (primary) {
            invoke(run, 0x4cab90, primary, {run.get(receiver + 0xc), 0, 0}, -0x30);
            run.put(primary + 0x0, 0x5138d8);
            run.put(primary + 0x2c, 0);
        }
        run.put(receiver + 0x10, primary);
        uint32_t secondary = run.call(0x4f63ec, 0, {0x34});
        if (secondary) {
            external(run, 0x45fde0, secondary, {run.get(receiver + 0xc), 1, 0}, -0x30);
            run.put(secondary + 0x10, 0);
            run.put(secondary + 0x0, 0x50e8e4);
            run.put(secondary + 0x2c, 0);
            run.put(secondary + 0x30, 1);
        }
        run.put(receiver + 0x14, secondary);
        uint32_t third = run.call(0x4f63ec, 0, {0x34});
        if (third) {
            external(run, 0x45fde0, third, {run.get(receiver + 0xc), 2, 0}, -0x30);
            run.put(third + 0x10, 0);
            run.put(third + 0x0, 0x50e8e4);
            run.put(third + 0x2c, 0);
            run.put(third + 0x30, 1);
        }
        primary = run.get(receiver + 0x10);
        uint32_t width = arguments[0];
        uint32_t height = arguments[1];
        uint32_t depth = arguments[2];
        run.put(receiver + 0x18, third);
        if (!virt(run, primary, 0x2c, {width, height, depth}, -0x30)) {
            error(run, receiver, 0x7d1);
            return 0;
        }
        if (!virt(run, run.get(receiver + 0x14), 0x24, {width, height}, -0x2c)) {
            error(run, receiver, 0x7d2);
            return 0;
        }
        if (!(arguments[3] & 1) && !virt(run, run.get(receiver + 0x18), 0x24, {width, height}, -0x2c)) {
            error(run, receiver, 0x7d3);
            return 0;
        }
        return 1;
}

// 0x4ca8b0. Original normal-return body.
uint32_t function_4ca8b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    if (run.get(receiver + 0x10)) {
            virt(run, run.get(receiver + 0x10), 0x4, {1}, -0xc);
            run.put(receiver + 0x10, 0);
        }
        if (run.get(receiver + 0x14)) {
            virt(run, run.get(receiver + 0x14), 0x4, {1}, -0xc);
            run.put(receiver + 0x14, 0);
        }
        if (run.get(receiver + 0x18)) {
            virt(run, run.get(receiver + 0x18), 0x4, {1}, -0xc);
            run.put(receiver + 0x18, 0);
        }
        return 0;
}

// 0x4ca960. Original normal-return body.
uint32_t function_4ca960(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t primary = run.get(receiver + 0x10);
        uint32_t width = arguments[0];
        uint32_t height = arguments[1];
        uint32_t depth = arguments[2];
        if (run.get(primary + 0x10) == width && run.get(primary + 0x14) == height && run.get(primary + 0x18) == depth)
            return 1;
        if (!virt(run, primary, 0x28, {width, height, depth}, -0x20))
            return 0;
        if (!virt(run, run.get(receiver + 0x14), 0x28, {width, height, depth}, -0x20))
            return 0;
        uint32_t third = run.get(receiver + 0x18);
        if (third && virt(run, third, 0x14, {}, -0x14)) {
            if (!virt(run, run.get(receiver + 0x18), 0x28, {width, height, depth}, -0x20))
                return 0;
        }
        return 1;
}

// 0x4cab90. Original normal-return body.
uint32_t function_4cab90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x4, arguments[1]);
        run.put(receiver + 0x8, arguments[2]);
        run.put(receiver + 0xc, arguments[0]);
        run.put(receiver + 0x0, 0x513908);
        run.put(receiver + 0x10, 0);
        return receiver;
}

// 0x4cabc0. Original normal-return body.
uint32_t function_4cabc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.gets(receiver + 0x10) > 0 && run.get(receiver + 0xc) && run.get(receiver + 0x4) != 0xffffffff;
}

// 0x4cac00. Original normal-return body.
uint32_t function_4cac00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4cac00;
    if (s32(arguments[0]) <= 0 || s32(arguments[1]) <= 0)
            return 0;
        if (function == 0x4cac40 && arguments[2] != 8 && arguments[2] != 0x10 && arguments[2] != 0x18 && arguments[2] != 0x20)
            return 0;
        run.put(receiver + 0x14, arguments[1]);
        run.put(receiver + 0x28, arguments[1]);
        run.put(receiver + 0x10, arguments[0]);
        if (function == 0x4cac40)
            run.put(receiver + 0x18, arguments[2]);
        run.put(receiver + 0x1c, 0);
        run.put(receiver + 0x20, 0);
        run.put(receiver + 0x24, arguments[0]);
        return 1;
}

// 0x4cac40. Original normal-return body.
uint32_t function_4cac40(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    const uint32_t function = 0x4cac40;
    if (s32(arguments[0]) <= 0 || s32(arguments[1]) <= 0)
            return 0;
        if (function == 0x4cac40 && arguments[2] != 8 && arguments[2] != 0x10 && arguments[2] != 0x18 && arguments[2] != 0x20)
            return 0;
        run.put(receiver + 0x14, arguments[1]);
        run.put(receiver + 0x28, arguments[1]);
        run.put(receiver + 0x10, arguments[0]);
        if (function == 0x4cac40)
            run.put(receiver + 0x18, arguments[2]);
        run.put(receiver + 0x1c, 0);
        run.put(receiver + 0x20, 0);
        run.put(receiver + 0x24, arguments[0]);
        return 1;
}

// 0x4caca0. Original normal-return body.
uint32_t function_4caca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x10, 0);
        return 0;
}

// 0x4cacb0. Original normal-return body.
uint32_t function_4cacb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.get(receiver + 0x2c) && run.gets(receiver + 0x10) > 0 && run.get(receiver + 0xc) && run.get(receiver + 0x4) != 0xffffffff;
}

// 0x4cf730. Original normal-return body.
uint32_t function_4cf730(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return run.get(receiver + 0x14) && run.get(receiver + 0x18) && run.get(receiver + 0x10);
}

// 0x4cf750. Original normal-return body.
uint32_t function_4cf750(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    return 0xf;
}

// 0x4cf780. Original normal-return body.
uint32_t function_4cf780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    run.put(receiver + 0x0, 0x513c68);
        invoke(run, 0x4ca8b0, receiver, {}, -0x18);
        run.put(receiver + 0x4, 0xffffffff);
        run.put(receiver + 0x8, 0);
        run.put(receiver + 0xc, 0);
        run.put(receiver + 0x0, 0x50becc);
        return 0;
}

// 0x4d4000. Original normal-return body.
uint32_t function_4d4000(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t width = arguments[0];
        uint32_t height = arguments[1];
        if (s32(width) <= 0 || s32(height) <= 0) {
            uint32_t code = run.get(receiver + 0x4) == 1 ? 0xfa1 : 0xfa2;
            error(run, receiver, code);
            return 0;
        }
        uint32_t type = run.get(receiver + 0x4);
        run.put(receiver + 0x10, width);
        run.put(receiver + 0x14, height);
        run.put(receiver + 0x1c, 0);
        run.put(receiver + 0x20, 0);
        run.put(receiver + 0x24, width);
        run.put(receiver + 0x28, height);
        if (type == 1) {
            uint32_t parent = run.get(receiver + 0xc);
            uint32_t source = run.get(run.get(run.get(parent + 0x4) + 0x10) + 0x2c);
            uint32_t item = invoke(run, 0x4bcf80, run.get(parent + 0x1c), {source, 4}, -0x18);
            run.put(receiver + 0x2c, item);
            if (!item) {
                error(run, receiver, 0xfa3);
                return 0;
            }
            if (run.get(receiver + 0x4) == 1) {
                run.put(receiver + 0x30, 1);
                return 1;
            }
        }
        uint32_t manager = run.get(run.get(receiver + 0xc) + 0x1c);
        uint32_t item = invoke(run, 0x4bc670, manager, {width, height, 0, 0, 0xffffffff}, -0x24);
        run.put(receiver + 0x2c, item);
        if (!item) {
            error(run, receiver, 0xfa4);
            return 0;
        }
        run.put(receiver + 0x30, 1);
        return 1;
}

// 0x4d4160. Original normal-return body.
uint32_t function_4d4160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t item = run.get(receiver + 0x2c);
        if (item && run.get(receiver + 0x30)) {
            invoke(run, 0x4bc4f0, run.get(run.get(receiver + 0xc) + 0x1c), {item}, -0xc);
            run.put(receiver + 0x2c, 0);
        }
        run.put(receiver + 0x10, 0);
        return 0;
}

// 0x4d5510. Original normal-return body.
uint32_t function_4d5510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t width = arguments[0];
        uint32_t height = arguments[1];
        uint32_t depth = arguments[2];
        uint32_t parent = run.get(receiver + 0xc);
        run.put(receiver + 0x10, width);
        run.put(receiver + 0x14, height);
        run.put(receiver + 0x18, depth);
        uint32_t manager = run.get(parent + 0x1c);
        uint32_t flags = s32(width) > 0x140 ? 0x11 : 0x51;
        uint32_t cooperative = (run.get8(parent + 0x34) & 0x10) ? 2 : 0;
        if (!external(run, 0x4bc220, manager, {run.get(parent + 0x30), cooperative, width, height, depth, flags}, -0x2c)) {
            uint32_t code = run.get(manager + 0x880);
            error(run, receiver, code - 0x3e9 <= 4 ? code + 0x7d00 : 0xbb9);
            return 0;
        }
        uint32_t createFlags = (run.get8(run.get(receiver + 0xc) + 0x34) & 2) ? 2 : 1;
        uint32_t item = invoke(run, 0x4bc890, manager, {createFlags}, -0x18);
        run.put(receiver + 0x2c, item);
        if (item && virt(run, item, 0x14, {}, -0x14))
            return 1;
        error(run, receiver, 0xbba);
        return 0;
}

// 0x4d63c0. Original normal-return body.
uint32_t function_4d63c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)run;
    (void)receiver;
    (void)arguments;
    uint32_t node = run.get(receiver + 0x14);
        while (node) {
            uint32_t item = run.get(node + 0x8);
            uint32_t next = run.get(node + 0x0);
            virt(run, item, 0x28, {arguments[0], arguments[1]}, -0x20);
            run.put(item + 0x64, run.get(item + 0x64) - 1);
            uint32_t ready = virt(run, arguments[1], 0x14, {}, -0x18);
            if (ready || run.gets(item + 0x64) <= 0) {
                run.call(0x4f5212, receiver + 0x10, {node});
                if (item)
                    virt(run, item, 0x4, {1}, -0x1c);
            }
            node = next;
        }
        return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x45fe40:
        return function_45fe40(run, receiver, arguments);
    case 0x4bb060:
        return function_4bb060(run, receiver, arguments);
    case 0x4bc810:
        return function_4bc810(run, receiver, arguments);
    case 0x4cabe0:
        return function_4cabe0(run, receiver, arguments);
    case 0x4cf760:
        return function_4cf760(run, receiver, arguments);
    case 0x45fe60:
        return function_45fe60(run, receiver, arguments);
    case 0x45fec0:
        return function_45fec0(run, receiver, arguments);
    case 0x4b9150:
        return function_4b9150(run, receiver, arguments);
    case 0x4b91f0:
        return function_4b91f0(run, receiver, arguments);
    case 0x4bb000:
        return function_4bb000(run, receiver, arguments);
    case 0x4bb080:
        return function_4bb080(run, receiver, arguments);
    case 0x4bc830:
        return function_4bc830(run, receiver, arguments);
    case 0x4bc4f0:
        return function_4bc4f0(run, receiver, arguments);
    case 0x4bc670:
        return function_4bc670(run, receiver, arguments);
    case 0x4bc890:
        return function_4bc890(run, receiver, arguments);
    case 0x4bcf80:
        return function_4bcf80(run, receiver, arguments);
    case 0x4bf970:
        return function_4bf970(run, receiver, arguments);
    case 0x4bfb80:
        return function_4bfb80(run, receiver, arguments);
    case 0x4bfbd0:
        return function_4bfbd0(run, receiver, arguments);
    case 0x4ca6f0:
        return function_4ca6f0(run, receiver, arguments);
    case 0x4ca8b0:
        return function_4ca8b0(run, receiver, arguments);
    case 0x4ca960:
        return function_4ca960(run, receiver, arguments);
    case 0x4cab90:
        return function_4cab90(run, receiver, arguments);
    case 0x4cabc0:
        return function_4cabc0(run, receiver, arguments);
    case 0x4cac00:
        return function_4cac00(run, receiver, arguments);
    case 0x4cac40:
        return function_4cac40(run, receiver, arguments);
    case 0x4caca0:
        return function_4caca0(run, receiver, arguments);
    case 0x4cacb0:
        return function_4cacb0(run, receiver, arguments);
    case 0x4cf730:
        return function_4cf730(run, receiver, arguments);
    case 0x4cf750:
        return function_4cf750(run, receiver, arguments);
    case 0x4cf780:
        return function_4cf780(run, receiver, arguments);
    case 0x4d4000:
        return function_4d4000(run, receiver, arguments);
    case 0x4d4160:
        return function_4d4160(run, receiver, arguments);
    case 0x4d5510:
        return function_4d5510(run, receiver, arguments);
    case 0x4d63c0:
        return function_4d63c0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_scene_display_canonical_entry, owned, body)
