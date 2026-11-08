// Original static table wrappers with genuine CALL and source JMP transfers
//
// Each wrapper retains the original constructor CALL frame and inherited tail frame.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

void copy_cpu(ClawSourceContext &context, const ClawSourceContext &child) {
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
}

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x501fbd:
        return 0;
    case 0x50226e:
        return 0;
    case 0x502c90:
        return 0;
    case 0x502876:
        return 0;
    case 0x502c51:
        return 0;
    case 0x503722:
        return 0;
    case 0x503748:
        return 0;
    case 0x403540:
        return 0;
    case 0x4042b0:
        return 0;
    case 0x4064c0:
        return 0;
    case 0x406e90:
        return 0;
    case 0x4074a0:
        return 0;
    case 0x408520:
        return 0;
    case 0x409150:
        return 0;
    case 0x409fe0:
        return 0;
    case 0x40b820:
        return 0;
    case 0x40e220:
        return 0;
    case 0x40eb80:
        return 0;
    case 0x40fad0:
        return 0;
    case 0x410a20:
        return 0;
    case 0x410fd0:
        return 0;
    case 0x411480:
        return 0;
    case 0x411930:
        return 0;
    case 0x411e10:
        return 0;
    case 0x412400:
        return 0;
    case 0x412970:
        return 0;
    case 0x412e20:
        return 0;
    case 0x413600:
        return 0;
    case 0x413b20:
        return 0;
    case 0x414190:
        return 0;
    case 0x414d80:
        return 0;
    case 0x415410:
        return 0;
    case 0x415aa0:
        return 0;
    case 0x4212c0:
        return 0;
    case 0x4251e0:
        return 0;
    case 0x425220:
        return 0;
    case 0x425260:
        return 0;
    case 0x4252a0:
        return 0;
    case 0x4252e0:
        return 0;
    case 0x425320:
        return 0;
    case 0x425360:
        return 0;
    case 0x4253a0:
        return 0;
    case 0x4253e0:
        return 0;
    case 0x425420:
        return 0;
    case 0x425460:
        return 0;
    case 0x4313e0:
        return 0;
    case 0x431d90:
        return 0;
    case 0x432630:
        return 0;
    case 0x433a70:
        return 0;
    case 0x4348f0:
        return 0;
    case 0x436890:
        return 0;
    case 0x4368d0:
        return 0;
    case 0x436910:
        return 0;
    case 0x437500:
        return 0;
    case 0x437550:
        return 0;
    case 0x4380a0:
        return 0;
    case 0x43acc0:
        return 0;
    case 0x43cd60:
        return 0;
    case 0x43d330:
        return 0;
    case 0x43d3e0:
        return 0;
    case 0x43d430:
        return 0;
    case 0x441270:
        return 0;
    case 0x441ca0:
        return 0;
    case 0x443350:
        return 0;
    case 0x445a90:
        return 0;
    case 0x446610:
        return 0;
    case 0x4487f0:
        return 0;
    case 0x448dd0:
        return 0;
    case 0x449530:
        return 0;
    case 0x449d00:
        return 0;
    case 0x44c7e0:
        return 0;
    case 0x453cb0:
        return 0;
    case 0x453cf0:
        return 0;
    case 0x454380:
        return 0;
    case 0x4555a0:
        return 0;
    case 0x455aa0:
        return 0;
    case 0x456280:
        return 0;
    case 0x456bc0:
        return 0;
    case 0x4576e0:
        return 0;
    case 0x458220:
        return 0;
    case 0x458740:
        return 0;
    case 0x45a3a0:
        return 0;
    case 0x45aca0:
        return 0;
    case 0x4606b0:
        return 0;
    case 0x462a90:
        return 0;
    case 0x463ae0:
        return 0;
    case 0x465140:
        return 0;
    case 0x465d50:
        return 0;
    case 0x468a70:
        return 0;
    case 0x46f640:
        return 0;
    case 0x473ee0:
        return 0;
    case 0x474780:
        return 0;
    case 0x474ed0:
        return 0;
    case 0x474f20:
        return 0;
    case 0x474f60:
        return 0;
    case 0x47cd10:
        return 0;
    case 0x47dac0:
        return 0;
    case 0x47e880:
        return 0;
    case 0x47f7a0:
        return 0;
    case 0x483120:
        return 0;
    case 0x484370:
        return 0;
    case 0x484870:
        return 0;
    case 0x485900:
        return 0;
    case 0x487340:
        return 0;
    case 0x488980:
        return 0;
    case 0x489090:
        return 0;
    case 0x4897f0:
        return 0;
    case 0x48b060:
        return 0;
    case 0x48d1d0:
        return 0;
    case 0x48e560:
        return 0;
    case 0x492380:
        return 0;
    case 0x493f70:
        return 0;
    case 0x4970d0:
        return 0;
    case 0x498160:
        return 0;
    case 0x49f160:
        return 0;
    case 0x49f850:
        return 0;
    case 0x49f890:
        return 0;
    case 0x4a01d0:
        return 0;
    case 0x4ff951:
        return 0;
    case 0x502405:
        return 0;
    case 0x502426:
        return 0;
    case 0x50245e:
        return 0;
    case 0x502546:
        return 0;
    case 0x5028d7:
        return 0;
    case 0x502b00:
        return 0;
    case 0x502b4d:
        return 0;
    case 0x4f821d:
        return 0;
    case 0x4f8233:
        return 0;
    case 0x4f8271:
        return 0;
    case 0x4f82af:
        return 0;
    case 0x4f82ed:
        return 0;
    case 0x502cc6:
        return 0;
    case 0x502cfe:
        return 0;
    case 0x502d30:
        return 0;
    case 0x4ffce4:
        return 0;
    case 0x4ffd07:
        return 0;
    case 0x4b9110:
        return 0;
    case 0x4bc0d0:
        return 0;
    case 0x4db600:
        return 0;
    case 0x4dbb70:
        return 0;
    case 0x4dc160:
        return 0;
    case 0x4dc260:
        return 0;
    case 0x4dc380:
        return 0;
    case 0x503813:
        return 0;
    default:
        return -1;
    }
}

// 0x501fbd StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_501fbd(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x501fc7;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x501fc2);
    try {
        run.source_call(0x501fc7, 0, 0x501fc2, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x501fc2;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x501fc8;
    run.source_tail(0x501fc8, 0, 0x501fc2, tail);
}

// 0x50226e StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_50226e(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502278;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502273);
    try {
        run.source_call(0x502278, 0, 0x502273, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502273;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502279;
    run.source_tail(0x502279, 0, 0x502273, tail);
}

// 0x502c90 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502c9a;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502c95);
    try {
        run.source_call(0x502c9a, 0, 0x502c95, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502c95;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502ca4;
    run.source_tail(0x502ca4, 0, 0x502c95, tail);
}

// 0x502876 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502876(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502880;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x50287b);
    try {
        run.source_call(0x502880, 0, 0x50287b, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x50287b;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502881;
    run.source_tail(0x502881, 0, 0x50287b, tail);
}

// 0x502c51 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502c51(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502c5b;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502c56);
    try {
        run.source_call(0x502c5b, 0, 0x502c56, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502c56;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502c5c;
    run.source_tail(0x502c5c, 0, 0x502c56, tail);
}

// 0x503722 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_503722(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x50372c;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x503727);
    try {
        run.source_call(0x50372c, 0, 0x503727, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x503727;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x50372d;
    run.source_tail(0x50372d, 0, 0x503727, tail);
}

// 0x503748 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_503748(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x503752;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x50374d);
    try {
        run.source_call(0x503752, 0, 0x50374d, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x50374d;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x503753;
    run.source_tail(0x503753, 0, 0x50374d, tail);
}

// 0x403540 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_403540(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403550;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x403545);
    try {
        run.source_call(0x403550, 0, 0x403545, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x403545;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x403570;
    run.source_tail(0x403570, 0, 0x403545, tail);
}

// 0x4042b0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4042b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4042c0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4042b5);
    try {
        run.source_call(0x4042c0, 0, 0x4042b5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4042b5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4042e0;
    run.source_tail(0x4042e0, 0, 0x4042b5, tail);
}

// 0x4064c0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4064c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4064d0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4064c5);
    try {
        run.source_call(0x4064d0, 0, 0x4064c5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4064c5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4064f0;
    run.source_tail(0x4064f0, 0, 0x4064c5, tail);
}

// 0x406e90 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_406e90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x406ea0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x406e95);
    try {
        run.source_call(0x406ea0, 0, 0x406e95, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x406e95;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x406ec0;
    run.source_tail(0x406ec0, 0, 0x406e95, tail);
}

// 0x4074a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4074a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4074b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4074a5);
    try {
        run.source_call(0x4074b0, 0, 0x4074a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4074a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4074d0;
    run.source_tail(0x4074d0, 0, 0x4074a5, tail);
}

// 0x408520 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_408520(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x408530;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x408525);
    try {
        run.source_call(0x408530, 0, 0x408525, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x408525;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x408550;
    run.source_tail(0x408550, 0, 0x408525, tail);
}

// 0x409150 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_409150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x409160;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x409155);
    try {
        run.source_call(0x409160, 0, 0x409155, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x409155;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x409180;
    run.source_tail(0x409180, 0, 0x409155, tail);
}

// 0x409fe0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_409fe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x409ff0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x409fe5);
    try {
        run.source_call(0x409ff0, 0, 0x409fe5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x409fe5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x40a010;
    run.source_tail(0x40a010, 0, 0x409fe5, tail);
}

// 0x40b820 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_40b820(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x40b830;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x40b825);
    try {
        run.source_call(0x40b830, 0, 0x40b825, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x40b825;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x40b840;
    run.source_tail(0x40b840, 0, 0x40b825, tail);
}

// 0x40e220 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_40e220(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x40e230;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x40e225);
    try {
        run.source_call(0x40e230, 0, 0x40e225, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x40e225;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x40e250;
    run.source_tail(0x40e250, 0, 0x40e225, tail);
}

// 0x40eb80 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_40eb80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x40eb90;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x40eb85);
    try {
        run.source_call(0x40eb90, 0, 0x40eb85, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x40eb85;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x40ebb0;
    run.source_tail(0x40ebb0, 0, 0x40eb85, tail);
}

// 0x40fad0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_40fad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x40fae0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x40fad5);
    try {
        run.source_call(0x40fae0, 0, 0x40fad5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x40fad5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x40fb00;
    run.source_tail(0x40fb00, 0, 0x40fad5, tail);
}

// 0x410a20 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_410a20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x410a30;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x410a25);
    try {
        run.source_call(0x410a30, 0, 0x410a25, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x410a25;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x410a50;
    run.source_tail(0x410a50, 0, 0x410a25, tail);
}

// 0x410fd0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_410fd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x410fe0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x410fd5);
    try {
        run.source_call(0x410fe0, 0, 0x410fd5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x410fd5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x411000;
    run.source_tail(0x411000, 0, 0x410fd5, tail);
}

// 0x411480 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_411480(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x411490;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x411485);
    try {
        run.source_call(0x411490, 0, 0x411485, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x411485;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4114b0;
    run.source_tail(0x4114b0, 0, 0x411485, tail);
}

// 0x411930 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_411930(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x411940;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x411935);
    try {
        run.source_call(0x411940, 0, 0x411935, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x411935;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x411960;
    run.source_tail(0x411960, 0, 0x411935, tail);
}

// 0x411e10 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_411e10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x411e20;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x411e15);
    try {
        run.source_call(0x411e20, 0, 0x411e15, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x411e15;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x411e40;
    run.source_tail(0x411e40, 0, 0x411e15, tail);
}

// 0x412400 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_412400(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x412410;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x412405);
    try {
        run.source_call(0x412410, 0, 0x412405, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x412405;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x412430;
    run.source_tail(0x412430, 0, 0x412405, tail);
}

// 0x412970 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_412970(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x412980;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x412975);
    try {
        run.source_call(0x412980, 0, 0x412975, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x412975;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4129a0;
    run.source_tail(0x4129a0, 0, 0x412975, tail);
}

// 0x412e20 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_412e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x412e30;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x412e25);
    try {
        run.source_call(0x412e30, 0, 0x412e25, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x412e25;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x412e50;
    run.source_tail(0x412e50, 0, 0x412e25, tail);
}

// 0x413600 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_413600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x413610;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x413605);
    try {
        run.source_call(0x413610, 0, 0x413605, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x413605;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x413630;
    run.source_tail(0x413630, 0, 0x413605, tail);
}

// 0x413b20 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_413b20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x413b30;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x413b25);
    try {
        run.source_call(0x413b30, 0, 0x413b25, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x413b25;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x413b50;
    run.source_tail(0x413b50, 0, 0x413b25, tail);
}

// 0x414190 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_414190(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4141a0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x414195);
    try {
        run.source_call(0x4141a0, 0, 0x414195, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x414195;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4141c0;
    run.source_tail(0x4141c0, 0, 0x414195, tail);
}

// 0x414d80 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_414d80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x414d90;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x414d85);
    try {
        run.source_call(0x414d90, 0, 0x414d85, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x414d85;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x414db0;
    run.source_tail(0x414db0, 0, 0x414d85, tail);
}

// 0x415410 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_415410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x415420;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x415415);
    try {
        run.source_call(0x415420, 0, 0x415415, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x415415;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x415440;
    run.source_tail(0x415440, 0, 0x415415, tail);
}

// 0x415aa0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_415aa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x415ab0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x415aa5);
    try {
        run.source_call(0x415ab0, 0, 0x415aa5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x415aa5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x415cc0;
    run.source_tail(0x415cc0, 0, 0x415aa5, tail);
}

// 0x4212c0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4212c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4212d0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4212c5);
    try {
        run.source_call(0x4212d0, 0, 0x4212c5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4212c5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4212f0;
    run.source_tail(0x4212f0, 0, 0x4212c5, tail);
}

// 0x4251e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4251e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4251f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4251e5);
    try {
        run.source_call(0x4251f0, 0, 0x4251e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4251e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425200;
    run.source_tail(0x425200, 0, 0x4251e5, tail);
}

// 0x425220 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425220(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425220;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425230;
    run.source_tail(0x425230, 0, 0x425220, tail);
}

// 0x425260 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425260(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x425270;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x425265);
    try {
        run.source_call(0x425270, 0, 0x425265, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x425265;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425280;
    run.source_tail(0x425280, 0, 0x425265, tail);
}

// 0x4252a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4252a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4252b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4252a5);
    try {
        run.source_call(0x4252b0, 0, 0x4252a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4252a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4252c0;
    run.source_tail(0x4252c0, 0, 0x4252a5, tail);
}

// 0x4252e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4252e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4252f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4252e5);
    try {
        run.source_call(0x4252f0, 0, 0x4252e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4252e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425300;
    run.source_tail(0x425300, 0, 0x4252e5, tail);
}

// 0x425320 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425320(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x425330;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x425325);
    try {
        run.source_call(0x425330, 0, 0x425325, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x425325;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425340;
    run.source_tail(0x425340, 0, 0x425325, tail);
}

// 0x425360 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425360(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x425370;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x425365);
    try {
        run.source_call(0x425370, 0, 0x425365, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x425365;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425380;
    run.source_tail(0x425380, 0, 0x425365, tail);
}

// 0x4253a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4253a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4253b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4253a5);
    try {
        run.source_call(0x4253b0, 0, 0x4253a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4253a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4253c0;
    run.source_tail(0x4253c0, 0, 0x4253a5, tail);
}

// 0x4253e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4253e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4253f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4253e5);
    try {
        run.source_call(0x4253f0, 0, 0x4253e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4253e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425400;
    run.source_tail(0x425400, 0, 0x4253e5, tail);
}

// 0x425420 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425420(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x425430;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x425425);
    try {
        run.source_call(0x425430, 0, 0x425425, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x425425;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425440;
    run.source_tail(0x425440, 0, 0x425425, tail);
}

// 0x425460 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_425460(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x425470;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x425465);
    try {
        run.source_call(0x425470, 0, 0x425465, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x425465;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x425480;
    run.source_tail(0x425480, 0, 0x425465, tail);
}

// 0x4313e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4313e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4313f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4313e5);
    try {
        run.source_call(0x4313f0, 0, 0x4313e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4313e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x431410;
    run.source_tail(0x431410, 0, 0x4313e5, tail);
}

// 0x431d90 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_431d90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x431da0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x431d95);
    try {
        run.source_call(0x431da0, 0, 0x431d95, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x431d95;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x431dc0;
    run.source_tail(0x431dc0, 0, 0x431d95, tail);
}

// 0x432630 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_432630(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x432640;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x432635);
    try {
        run.source_call(0x432640, 0, 0x432635, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x432635;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x432660;
    run.source_tail(0x432660, 0, 0x432635, tail);
}

// 0x433a70 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_433a70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x433a80;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x433a75);
    try {
        run.source_call(0x433a80, 0, 0x433a75, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x433a75;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x433aa0;
    run.source_tail(0x433aa0, 0, 0x433a75, tail);
}

// 0x4348f0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4348f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x434900;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4348f5);
    try {
        run.source_call(0x434900, 0, 0x4348f5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4348f5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x434920;
    run.source_tail(0x434920, 0, 0x4348f5, tail);
}

// 0x436890 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_436890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4368a0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x436895);
    try {
        run.source_call(0x4368a0, 0, 0x436895, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x436895;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4368b0;
    run.source_tail(0x4368b0, 0, 0x436895, tail);
}

// 0x4368d0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4368d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4368e0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4368d5);
    try {
        run.source_call(0x4368e0, 0, 0x4368d5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4368d5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4368f0;
    run.source_tail(0x4368f0, 0, 0x4368d5, tail);
}

// 0x436910 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_436910(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x436920;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x436915);
    try {
        run.source_call(0x436920, 0, 0x436915, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x436915;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x436930;
    run.source_tail(0x436930, 0, 0x436915, tail);
}

// 0x437500 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_437500(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x437510;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x437505);
    try {
        run.source_call(0x437510, 0, 0x437505, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x437505;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x437520;
    run.source_tail(0x437520, 0, 0x437505, tail);
}

// 0x437550 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_437550(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x437560;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x437555);
    try {
        run.source_call(0x437560, 0, 0x437555, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x437555;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x437570;
    run.source_tail(0x437570, 0, 0x437555, tail);
}

// 0x4380a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4380a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4380b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4380a5);
    try {
        run.source_call(0x4380b0, 0, 0x4380a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4380a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4380d0;
    run.source_tail(0x4380d0, 0, 0x4380a5, tail);
}

// 0x43acc0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_43acc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x43acd0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x43acc5);
    try {
        run.source_call(0x43acd0, 0, 0x43acc5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x43acc5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x43acf0;
    run.source_tail(0x43acf0, 0, 0x43acc5, tail);
}

// 0x43cd60 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_43cd60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x43cd70;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x43cd65);
    try {
        run.source_call(0x43cd70, 0, 0x43cd65, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x43cd65;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x43cd90;
    run.source_tail(0x43cd90, 0, 0x43cd65, tail);
}

// 0x43d330 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x43d340;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x43d335);
    try {
        run.source_call(0x43d340, 0, 0x43d335, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x43d335;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x43d350;
    run.source_tail(0x43d350, 0, 0x43d335, tail);
}

// 0x43d3e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d3e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x43d3f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x43d3e5);
    try {
        run.source_call(0x43d3f0, 0, 0x43d3e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x43d3e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x43d410;
    run.source_tail(0x43d410, 0, 0x43d3e5, tail);
}

// 0x43d430 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x43d440;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x43d435);
    try {
        run.source_call(0x43d440, 0, 0x43d435, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x43d435;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x43d460;
    run.source_tail(0x43d460, 0, 0x43d435, tail);
}

// 0x441270 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_441270(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x441280;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x441275);
    try {
        run.source_call(0x441280, 0, 0x441275, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x441275;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4412a0;
    run.source_tail(0x4412a0, 0, 0x441275, tail);
}

// 0x441ca0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_441ca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x441cb0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x441ca5);
    try {
        run.source_call(0x441cb0, 0, 0x441ca5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x441ca5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x441cd0;
    run.source_tail(0x441cd0, 0, 0x441ca5, tail);
}

// 0x443350 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_443350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x443360;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x443355);
    try {
        run.source_call(0x443360, 0, 0x443355, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x443355;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x443380;
    run.source_tail(0x443380, 0, 0x443355, tail);
}

// 0x445a90 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_445a90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x445aa0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x445a95);
    try {
        run.source_call(0x445aa0, 0, 0x445a95, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x445a95;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x445ac0;
    run.source_tail(0x445ac0, 0, 0x445a95, tail);
}

// 0x446610 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_446610(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x446620;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x446615);
    try {
        run.source_call(0x446620, 0, 0x446615, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x446615;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x446640;
    run.source_tail(0x446640, 0, 0x446615, tail);
}

// 0x4487f0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4487f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x448800;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4487f5);
    try {
        run.source_call(0x448800, 0, 0x4487f5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4487f5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x448820;
    run.source_tail(0x448820, 0, 0x4487f5, tail);
}

// 0x448dd0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_448dd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x448de0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x448dd5);
    try {
        run.source_call(0x448de0, 0, 0x448dd5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x448dd5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x448e00;
    run.source_tail(0x448e00, 0, 0x448dd5, tail);
}

// 0x449530 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_449530(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x449540;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x449535);
    try {
        run.source_call(0x449540, 0, 0x449535, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x449535;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x449560;
    run.source_tail(0x449560, 0, 0x449535, tail);
}

// 0x449d00 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_449d00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x449d10;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x449d05);
    try {
        run.source_call(0x449d10, 0, 0x449d05, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x449d05;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x449d30;
    run.source_tail(0x449d30, 0, 0x449d05, tail);
}

// 0x44c7e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_44c7e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x44c7f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x44c7e5);
    try {
        run.source_call(0x44c7f0, 0, 0x44c7e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x44c7e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x44c810;
    run.source_tail(0x44c810, 0, 0x44c7e5, tail);
}

// 0x453cb0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_453cb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x453cb0;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x453cc0;
    run.source_tail(0x453cc0, 0, 0x453cb0, tail);
}

// 0x453cf0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_453cf0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x453cf0;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x453d00;
    run.source_tail(0x453d00, 0, 0x453cf0, tail);
}

// 0x454380 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_454380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x454390;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x454385);
    try {
        run.source_call(0x454390, 0, 0x454385, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x454385;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4543b0;
    run.source_tail(0x4543b0, 0, 0x454385, tail);
}

// 0x4555a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4555a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4555b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4555a5);
    try {
        run.source_call(0x4555b0, 0, 0x4555a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4555a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4555d0;
    run.source_tail(0x4555d0, 0, 0x4555a5, tail);
}

// 0x455aa0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_455aa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x455ab0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x455aa5);
    try {
        run.source_call(0x455ab0, 0, 0x455aa5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x455aa5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x455ad0;
    run.source_tail(0x455ad0, 0, 0x455aa5, tail);
}

// 0x456280 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_456280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x456290;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x456285);
    try {
        run.source_call(0x456290, 0, 0x456285, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x456285;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4562b0;
    run.source_tail(0x4562b0, 0, 0x456285, tail);
}

// 0x456bc0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_456bc0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x456bd0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x456bc5);
    try {
        run.source_call(0x456bd0, 0, 0x456bc5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x456bc5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x456bf0;
    run.source_tail(0x456bf0, 0, 0x456bc5, tail);
}

// 0x4576e0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4576e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4576f0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4576e5);
    try {
        run.source_call(0x4576f0, 0, 0x4576e5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4576e5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x457710;
    run.source_tail(0x457710, 0, 0x4576e5, tail);
}

// 0x458220 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_458220(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x458230;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x458225);
    try {
        run.source_call(0x458230, 0, 0x458225, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x458225;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x458250;
    run.source_tail(0x458250, 0, 0x458225, tail);
}

// 0x458740 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_458740(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x458750;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x458745);
    try {
        run.source_call(0x458750, 0, 0x458745, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x458745;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x458770;
    run.source_tail(0x458770, 0, 0x458745, tail);
}

// 0x45a3a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_45a3a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x45a3b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x45a3a5);
    try {
        run.source_call(0x45a3b0, 0, 0x45a3a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x45a3a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x45a3d0;
    run.source_tail(0x45a3d0, 0, 0x45a3a5, tail);
}

// 0x45aca0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_45aca0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x45aca0;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x45acb0;
    run.source_tail(0x45acb0, 0, 0x45aca0, tail);
}

// 0x4606b0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4606b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4606c0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4606b5);
    try {
        run.source_call(0x4606c0, 0, 0x4606b5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4606b5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4606e0;
    run.source_tail(0x4606e0, 0, 0x4606b5, tail);
}

// 0x462a90 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_462a90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x462aa0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x462a95);
    try {
        run.source_call(0x462aa0, 0, 0x462a95, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x462a95;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x462ac0;
    run.source_tail(0x462ac0, 0, 0x462a95, tail);
}

// 0x463ae0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_463ae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x463af0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x463ae5);
    try {
        run.source_call(0x463af0, 0, 0x463ae5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x463ae5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x463b10;
    run.source_tail(0x463b10, 0, 0x463ae5, tail);
}

// 0x465140 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_465140(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x465150;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x465145);
    try {
        run.source_call(0x465150, 0, 0x465145, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x465145;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x465170;
    run.source_tail(0x465170, 0, 0x465145, tail);
}

// 0x465d50 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_465d50(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x465d60;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x465d55);
    try {
        run.source_call(0x465d60, 0, 0x465d55, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x465d55;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x465d80;
    run.source_tail(0x465d80, 0, 0x465d55, tail);
}

// 0x468a70 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_468a70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x468a80;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x468a75);
    try {
        run.source_call(0x468a80, 0, 0x468a75, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x468a75;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x468aa0;
    run.source_tail(0x468aa0, 0, 0x468a75, tail);
}

// 0x46f640 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_46f640(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x46f650;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x46f645);
    try {
        run.source_call(0x46f650, 0, 0x46f645, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x46f645;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x46f670;
    run.source_tail(0x46f670, 0, 0x46f645, tail);
}

// 0x473ee0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_473ee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x473ef0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x473ee5);
    try {
        run.source_call(0x473ef0, 0, 0x473ee5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x473ee5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x473f10;
    run.source_tail(0x473f10, 0, 0x473ee5, tail);
}

// 0x474780 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_474780(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x474790;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x474785);
    try {
        run.source_call(0x474790, 0, 0x474785, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x474785;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4747b0;
    run.source_tail(0x4747b0, 0, 0x474785, tail);
}

// 0x474ed0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_474ed0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x474ee0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x474ed5);
    try {
        run.source_call(0x474ee0, 0, 0x474ed5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x474ed5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x474ef0;
    run.source_tail(0x474ef0, 0, 0x474ed5, tail);
}

// 0x474f20 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_474f20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x474f30;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x474f25);
    try {
        run.source_call(0x474f30, 0, 0x474f25, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x474f25;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x474f40;
    run.source_tail(0x474f40, 0, 0x474f25, tail);
}

// 0x474f60 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_474f60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x474f70;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x474f65);
    try {
        run.source_call(0x474f70, 0, 0x474f65, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x474f65;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x474f80;
    run.source_tail(0x474f80, 0, 0x474f65, tail);
}

// 0x47cd10 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_47cd10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x47cd20;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x47cd15);
    try {
        run.source_call(0x47cd20, 0, 0x47cd15, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x47cd15;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x47cd40;
    run.source_tail(0x47cd40, 0, 0x47cd15, tail);
}

// 0x47dac0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_47dac0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x47dad0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x47dac5);
    try {
        run.source_call(0x47dad0, 0, 0x47dac5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x47dac5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x47daf0;
    run.source_tail(0x47daf0, 0, 0x47dac5, tail);
}

// 0x47e880 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_47e880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x47e890;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x47e885);
    try {
        run.source_call(0x47e890, 0, 0x47e885, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x47e885;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x47e8b0;
    run.source_tail(0x47e8b0, 0, 0x47e885, tail);
}

// 0x47f7a0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_47f7a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x47f7b0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x47f7a5);
    try {
        run.source_call(0x47f7b0, 0, 0x47f7a5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x47f7a5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x47f7d0;
    run.source_tail(0x47f7d0, 0, 0x47f7a5, tail);
}

// 0x483120 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_483120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x483130;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x483125);
    try {
        run.source_call(0x483130, 0, 0x483125, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x483125;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x483150;
    run.source_tail(0x483150, 0, 0x483125, tail);
}

// 0x484370 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_484370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x484380;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x484375);
    try {
        run.source_call(0x484380, 0, 0x484375, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x484375;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4843a0;
    run.source_tail(0x4843a0, 0, 0x484375, tail);
}

// 0x484870 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_484870(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x484880;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x484875);
    try {
        run.source_call(0x484880, 0, 0x484875, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x484875;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4848a0;
    run.source_tail(0x4848a0, 0, 0x484875, tail);
}

// 0x485900 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_485900(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x485910;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x485905);
    try {
        run.source_call(0x485910, 0, 0x485905, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x485905;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x485930;
    run.source_tail(0x485930, 0, 0x485905, tail);
}

// 0x487340 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_487340(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x487350;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x487345);
    try {
        run.source_call(0x487350, 0, 0x487345, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x487345;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x487370;
    run.source_tail(0x487370, 0, 0x487345, tail);
}

// 0x488980 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_488980(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x488990;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x488985);
    try {
        run.source_call(0x488990, 0, 0x488985, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x488985;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4889b0;
    run.source_tail(0x4889b0, 0, 0x488985, tail);
}

// 0x489090 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_489090(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4890a0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x489095);
    try {
        run.source_call(0x4890a0, 0, 0x489095, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x489095;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4890c0;
    run.source_tail(0x4890c0, 0, 0x489095, tail);
}

// 0x4897f0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4897f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x489800;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4897f5);
    try {
        run.source_call(0x489800, 0, 0x4897f5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4897f5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x489820;
    run.source_tail(0x489820, 0, 0x4897f5, tail);
}

// 0x48b060 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_48b060(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x48b070;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x48b065);
    try {
        run.source_call(0x48b070, 0, 0x48b065, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x48b065;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x48b090;
    run.source_tail(0x48b090, 0, 0x48b065, tail);
}

// 0x48d1d0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_48d1d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x48d1e0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x48d1d5);
    try {
        run.source_call(0x48d1e0, 0, 0x48d1d5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x48d1d5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x48d1f0;
    run.source_tail(0x48d1f0, 0, 0x48d1d5, tail);
}

// 0x48e560 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_48e560(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x48e570;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x48e565);
    try {
        run.source_call(0x48e570, 0, 0x48e565, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x48e565;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x48e590;
    run.source_tail(0x48e590, 0, 0x48e565, tail);
}

// 0x492380 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_492380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x492390;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x492385);
    try {
        run.source_call(0x492390, 0, 0x492385, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x492385;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4923b0;
    run.source_tail(0x4923b0, 0, 0x492385, tail);
}

// 0x493f70 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_493f70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x493f80;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x493f75);
    try {
        run.source_call(0x493f80, 0, 0x493f75, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x493f75;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x493fa0;
    run.source_tail(0x493fa0, 0, 0x493f75, tail);
}

// 0x4970d0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4970d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4970e0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4970d5);
    try {
        run.source_call(0x4970e0, 0, 0x4970d5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4970d5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x497100;
    run.source_tail(0x497100, 0, 0x4970d5, tail);
}

// 0x498160 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_498160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x498170;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x498165);
    try {
        run.source_call(0x498170, 0, 0x498165, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x498165;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x498190;
    run.source_tail(0x498190, 0, 0x498165, tail);
}

// 0x49f160 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x49f170;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x49f165);
    try {
        run.source_call(0x49f170, 0, 0x49f165, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x49f165;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x49f190;
    run.source_tail(0x49f190, 0, 0x49f165, tail);
}

// 0x49f850 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f850(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x49f860;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x49f855);
    try {
        run.source_call(0x49f860, 0, 0x49f855, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x49f855;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x49f870;
    run.source_tail(0x49f870, 0, 0x49f855, tail);
}

// 0x49f890 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x49f8a0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x49f895);
    try {
        run.source_call(0x49f8a0, 0, 0x49f895, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x49f895;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x49f8b0;
    run.source_tail(0x49f8b0, 0, 0x49f895, tail);
}

// 0x4a01d0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4a01d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a01e0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4a01d5);
    try {
        run.source_call(0x4a01e0, 0, 0x4a01d5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4a01d5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4a0200;
    run.source_tail(0x4a0200, 0, 0x4a01d5, tail);
}

// 0x4ff951 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4ff951(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4ff95b;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4ff956);
    try {
        run.source_call(0x4ff95b, 0, 0x4ff956, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4ff956;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4ff95c;
    run.source_tail(0x4ff95c, 0, 0x4ff956, tail);
}

// 0x502405 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502405(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502405;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x50240a;
    run.source_tail(0x50240a, 0, 0x502405, tail);
}

// 0x502426 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502426(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502430;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x50242b);
    try {
        run.source_call(0x502430, 0, 0x50242b, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x50242b;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502442;
    run.source_tail(0x502442, 0, 0x50242b, tail);
}

// 0x50245e StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_50245e(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502468;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502463);
    try {
        run.source_call(0x502468, 0, 0x502463, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502463;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x50247a;
    run.source_tail(0x50247a, 0, 0x502463, tail);
}

// 0x502546 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502546(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502546;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x50254b;
    run.source_tail(0x50254b, 0, 0x502546, tail);
}

// 0x5028d7 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_5028d7(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x5028d7;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x5028dc;
    run.source_tail(0x5028dc, 0, 0x5028d7, tail);
}

// 0x502b00 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502b00(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502b00;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502b05;
    run.source_tail(0x502b05, 0, 0x502b00, tail);
}

// 0x502b4d StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502b4d(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502b4d;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502b52;
    run.source_tail(0x502b52, 0, 0x502b4d, tail);
}

// 0x4f821d StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f821d(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4f821d;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4f8222;
    run.source_tail(0x4f8222, 0, 0x4f821d, tail);
}

// 0x4f8233 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f8233(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f823d;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4f8238);
    try {
        run.source_call(0x4f823d, 0, 0x4f8238, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4f8238;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4f824a;
    run.source_tail(0x4f824a, 0, 0x4f8238, tail);
}

// 0x4f8271 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f8271(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f827b;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4f8276);
    try {
        run.source_call(0x4f827b, 0, 0x4f8276, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4f8276;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4f8288;
    run.source_tail(0x4f8288, 0, 0x4f8276, tail);
}

// 0x4f82af StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f82af(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f82b9;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4f82b4);
    try {
        run.source_call(0x4f82b9, 0, 0x4f82b4, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4f82b4;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4f82c6;
    run.source_tail(0x4f82c6, 0, 0x4f82b4, tail);
}

// 0x4f82ed StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f82ed(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f82f7;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4f82f2);
    try {
        run.source_call(0x4f82f7, 0, 0x4f82f2, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4f82f2;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4f8304;
    run.source_tail(0x4f8304, 0, 0x4f82f2, tail);
}

// 0x502cc6 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502cc6(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502cd0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502ccb);
    try {
        run.source_call(0x502cd0, 0, 0x502ccb, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502ccb;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502ce2;
    run.source_tail(0x502ce2, 0, 0x502ccb, tail);
}

// 0x502cfe StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502cfe(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502d08;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502d03);
    try {
        run.source_call(0x502d08, 0, 0x502d03, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502d03;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502d1a;
    run.source_tail(0x502d1a, 0, 0x502d03, tail);
}

// 0x502d30 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_502d30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502d3a;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x502d35);
    try {
        run.source_call(0x502d3a, 0, 0x502d35, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x502d35;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x502d44;
    run.source_tail(0x502d44, 0, 0x502d35, tail);
}

// 0x4ffce4 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4ffce4(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4ffce4;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4ffce9;
    run.source_tail(0x4ffce9, 0, 0x4ffce4, tail);
}

// 0x4ffd07 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4ffd07(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4ffd07;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4ffd0c;
    run.source_tail(0x4ffd0c, 0, 0x4ffd07, tail);
}

// 0x4b9110 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4b9110(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4b9120;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4b9115);
    try {
        run.source_call(0x4b9120, 0, 0x4b9115, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4b9115;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4b9130;
    run.source_tail(0x4b9130, 0, 0x4b9115, tail);
}

// 0x4bc0d0 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4bc0d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4bc0e0;
    child.esp = run.frame - 0x4;
    run.put(child.esp, 0x4bc0d5);
    try {
        run.source_call(0x4bc0e0, 0, 0x4bc0d5, child);
    } catch (const claw::Failure &) {
        copy_cpu(context, child);
        throw;
    }
    copy_cpu(context, child);
    context.eip = 0x4bc0d5;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4bc0f0;
    run.source_tail(0x4bc0f0, 0, 0x4bc0d5, tail);
}

// 0x4db600 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4db600(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4db600;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4db610;
    run.source_tail(0x4db610, 0, 0x4db600, tail);
}

// 0x4dbb70 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4dbb70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4dbb70;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4dbb80;
    run.source_tail(0x4dbb80, 0, 0x4dbb70, tail);
}

// 0x4dc160 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4dc160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4dc160;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4dc170;
    run.source_tail(0x4dc170, 0, 0x4dc160, tail);
}

// 0x4dc260 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4dc260(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4dc260;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4dc270;
    run.source_tail(0x4dc270, 0, 0x4dc260, tail);
}

// 0x4dc380 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_4dc380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4dc380;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x4dc390;
    run.source_tail(0x4dc390, 0, 0x4dc380, tail);
}

// 0x503813 StaticInitializerWrapper. cdecl, 0 stack argument(s), returns void.
uint32_t function_503813(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x503813;
    auto tail = context;
    tail.inputMask = 0x7ff;
    tail.outputMask = 0x7ff;
    tail.preserveMask = 0;
    tail.eip = 0x503818;
    run.source_tail(0x503818, 0, 0x503813, tail);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x501fbd:
        return function_501fbd(run, receiver, arguments);
    case 0x50226e:
        return function_50226e(run, receiver, arguments);
    case 0x502c90:
        return function_502c90(run, receiver, arguments);
    case 0x502876:
        return function_502876(run, receiver, arguments);
    case 0x502c51:
        return function_502c51(run, receiver, arguments);
    case 0x503722:
        return function_503722(run, receiver, arguments);
    case 0x503748:
        return function_503748(run, receiver, arguments);
    case 0x403540:
        return function_403540(run, receiver, arguments);
    case 0x4042b0:
        return function_4042b0(run, receiver, arguments);
    case 0x4064c0:
        return function_4064c0(run, receiver, arguments);
    case 0x406e90:
        return function_406e90(run, receiver, arguments);
    case 0x4074a0:
        return function_4074a0(run, receiver, arguments);
    case 0x408520:
        return function_408520(run, receiver, arguments);
    case 0x409150:
        return function_409150(run, receiver, arguments);
    case 0x409fe0:
        return function_409fe0(run, receiver, arguments);
    case 0x40b820:
        return function_40b820(run, receiver, arguments);
    case 0x40e220:
        return function_40e220(run, receiver, arguments);
    case 0x40eb80:
        return function_40eb80(run, receiver, arguments);
    case 0x40fad0:
        return function_40fad0(run, receiver, arguments);
    case 0x410a20:
        return function_410a20(run, receiver, arguments);
    case 0x410fd0:
        return function_410fd0(run, receiver, arguments);
    case 0x411480:
        return function_411480(run, receiver, arguments);
    case 0x411930:
        return function_411930(run, receiver, arguments);
    case 0x411e10:
        return function_411e10(run, receiver, arguments);
    case 0x412400:
        return function_412400(run, receiver, arguments);
    case 0x412970:
        return function_412970(run, receiver, arguments);
    case 0x412e20:
        return function_412e20(run, receiver, arguments);
    case 0x413600:
        return function_413600(run, receiver, arguments);
    case 0x413b20:
        return function_413b20(run, receiver, arguments);
    case 0x414190:
        return function_414190(run, receiver, arguments);
    case 0x414d80:
        return function_414d80(run, receiver, arguments);
    case 0x415410:
        return function_415410(run, receiver, arguments);
    case 0x415aa0:
        return function_415aa0(run, receiver, arguments);
    case 0x4212c0:
        return function_4212c0(run, receiver, arguments);
    case 0x4251e0:
        return function_4251e0(run, receiver, arguments);
    case 0x425220:
        return function_425220(run, receiver, arguments);
    case 0x425260:
        return function_425260(run, receiver, arguments);
    case 0x4252a0:
        return function_4252a0(run, receiver, arguments);
    case 0x4252e0:
        return function_4252e0(run, receiver, arguments);
    case 0x425320:
        return function_425320(run, receiver, arguments);
    case 0x425360:
        return function_425360(run, receiver, arguments);
    case 0x4253a0:
        return function_4253a0(run, receiver, arguments);
    case 0x4253e0:
        return function_4253e0(run, receiver, arguments);
    case 0x425420:
        return function_425420(run, receiver, arguments);
    case 0x425460:
        return function_425460(run, receiver, arguments);
    case 0x4313e0:
        return function_4313e0(run, receiver, arguments);
    case 0x431d90:
        return function_431d90(run, receiver, arguments);
    case 0x432630:
        return function_432630(run, receiver, arguments);
    case 0x433a70:
        return function_433a70(run, receiver, arguments);
    case 0x4348f0:
        return function_4348f0(run, receiver, arguments);
    case 0x436890:
        return function_436890(run, receiver, arguments);
    case 0x4368d0:
        return function_4368d0(run, receiver, arguments);
    case 0x436910:
        return function_436910(run, receiver, arguments);
    case 0x437500:
        return function_437500(run, receiver, arguments);
    case 0x437550:
        return function_437550(run, receiver, arguments);
    case 0x4380a0:
        return function_4380a0(run, receiver, arguments);
    case 0x43acc0:
        return function_43acc0(run, receiver, arguments);
    case 0x43cd60:
        return function_43cd60(run, receiver, arguments);
    case 0x43d330:
        return function_43d330(run, receiver, arguments);
    case 0x43d3e0:
        return function_43d3e0(run, receiver, arguments);
    case 0x43d430:
        return function_43d430(run, receiver, arguments);
    case 0x441270:
        return function_441270(run, receiver, arguments);
    case 0x441ca0:
        return function_441ca0(run, receiver, arguments);
    case 0x443350:
        return function_443350(run, receiver, arguments);
    case 0x445a90:
        return function_445a90(run, receiver, arguments);
    case 0x446610:
        return function_446610(run, receiver, arguments);
    case 0x4487f0:
        return function_4487f0(run, receiver, arguments);
    case 0x448dd0:
        return function_448dd0(run, receiver, arguments);
    case 0x449530:
        return function_449530(run, receiver, arguments);
    case 0x449d00:
        return function_449d00(run, receiver, arguments);
    case 0x44c7e0:
        return function_44c7e0(run, receiver, arguments);
    case 0x453cb0:
        return function_453cb0(run, receiver, arguments);
    case 0x453cf0:
        return function_453cf0(run, receiver, arguments);
    case 0x454380:
        return function_454380(run, receiver, arguments);
    case 0x4555a0:
        return function_4555a0(run, receiver, arguments);
    case 0x455aa0:
        return function_455aa0(run, receiver, arguments);
    case 0x456280:
        return function_456280(run, receiver, arguments);
    case 0x456bc0:
        return function_456bc0(run, receiver, arguments);
    case 0x4576e0:
        return function_4576e0(run, receiver, arguments);
    case 0x458220:
        return function_458220(run, receiver, arguments);
    case 0x458740:
        return function_458740(run, receiver, arguments);
    case 0x45a3a0:
        return function_45a3a0(run, receiver, arguments);
    case 0x45aca0:
        return function_45aca0(run, receiver, arguments);
    case 0x4606b0:
        return function_4606b0(run, receiver, arguments);
    case 0x462a90:
        return function_462a90(run, receiver, arguments);
    case 0x463ae0:
        return function_463ae0(run, receiver, arguments);
    case 0x465140:
        return function_465140(run, receiver, arguments);
    case 0x465d50:
        return function_465d50(run, receiver, arguments);
    case 0x468a70:
        return function_468a70(run, receiver, arguments);
    case 0x46f640:
        return function_46f640(run, receiver, arguments);
    case 0x473ee0:
        return function_473ee0(run, receiver, arguments);
    case 0x474780:
        return function_474780(run, receiver, arguments);
    case 0x474ed0:
        return function_474ed0(run, receiver, arguments);
    case 0x474f20:
        return function_474f20(run, receiver, arguments);
    case 0x474f60:
        return function_474f60(run, receiver, arguments);
    case 0x47cd10:
        return function_47cd10(run, receiver, arguments);
    case 0x47dac0:
        return function_47dac0(run, receiver, arguments);
    case 0x47e880:
        return function_47e880(run, receiver, arguments);
    case 0x47f7a0:
        return function_47f7a0(run, receiver, arguments);
    case 0x483120:
        return function_483120(run, receiver, arguments);
    case 0x484370:
        return function_484370(run, receiver, arguments);
    case 0x484870:
        return function_484870(run, receiver, arguments);
    case 0x485900:
        return function_485900(run, receiver, arguments);
    case 0x487340:
        return function_487340(run, receiver, arguments);
    case 0x488980:
        return function_488980(run, receiver, arguments);
    case 0x489090:
        return function_489090(run, receiver, arguments);
    case 0x4897f0:
        return function_4897f0(run, receiver, arguments);
    case 0x48b060:
        return function_48b060(run, receiver, arguments);
    case 0x48d1d0:
        return function_48d1d0(run, receiver, arguments);
    case 0x48e560:
        return function_48e560(run, receiver, arguments);
    case 0x492380:
        return function_492380(run, receiver, arguments);
    case 0x493f70:
        return function_493f70(run, receiver, arguments);
    case 0x4970d0:
        return function_4970d0(run, receiver, arguments);
    case 0x498160:
        return function_498160(run, receiver, arguments);
    case 0x49f160:
        return function_49f160(run, receiver, arguments);
    case 0x49f850:
        return function_49f850(run, receiver, arguments);
    case 0x49f890:
        return function_49f890(run, receiver, arguments);
    case 0x4a01d0:
        return function_4a01d0(run, receiver, arguments);
    case 0x4ff951:
        return function_4ff951(run, receiver, arguments);
    case 0x502405:
        return function_502405(run, receiver, arguments);
    case 0x502426:
        return function_502426(run, receiver, arguments);
    case 0x50245e:
        return function_50245e(run, receiver, arguments);
    case 0x502546:
        return function_502546(run, receiver, arguments);
    case 0x5028d7:
        return function_5028d7(run, receiver, arguments);
    case 0x502b00:
        return function_502b00(run, receiver, arguments);
    case 0x502b4d:
        return function_502b4d(run, receiver, arguments);
    case 0x4f821d:
        return function_4f821d(run, receiver, arguments);
    case 0x4f8233:
        return function_4f8233(run, receiver, arguments);
    case 0x4f8271:
        return function_4f8271(run, receiver, arguments);
    case 0x4f82af:
        return function_4f82af(run, receiver, arguments);
    case 0x4f82ed:
        return function_4f82ed(run, receiver, arguments);
    case 0x502cc6:
        return function_502cc6(run, receiver, arguments);
    case 0x502cfe:
        return function_502cfe(run, receiver, arguments);
    case 0x502d30:
        return function_502d30(run, receiver, arguments);
    case 0x4ffce4:
        return function_4ffce4(run, receiver, arguments);
    case 0x4ffd07:
        return function_4ffd07(run, receiver, arguments);
    case 0x4b9110:
        return function_4b9110(run, receiver, arguments);
    case 0x4bc0d0:
        return function_4bc0d0(run, receiver, arguments);
    case 0x4db600:
        return function_4db600(run, receiver, arguments);
    case 0x4dbb70:
        return function_4dbb70(run, receiver, arguments);
    case 0x4dc160:
        return function_4dc160(run, receiver, arguments);
    case 0x4dc260:
        return function_4dc260(run, receiver, arguments);
    case 0x4dc380:
        return function_4dc380(run, receiver, arguments);
    case 0x503813:
        return function_503813(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x501fbd: return {2047u, 2047u, 0u, 0u};
    case 0x50226e: return {2047u, 2047u, 0u, 0u};
    case 0x502c90: return {2047u, 2047u, 0u, 0u};
    case 0x502876: return {2047u, 2047u, 0u, 0u};
    case 0x502c51: return {2047u, 2047u, 0u, 0u};
    case 0x503722: return {2047u, 2047u, 0u, 0u};
    case 0x503748: return {2047u, 2047u, 0u, 0u};
    case 0x403540: return {2047u, 2047u, 0u, 0u};
    case 0x4042b0: return {2047u, 2047u, 0u, 0u};
    case 0x4064c0: return {2047u, 2047u, 0u, 0u};
    case 0x406e90: return {2047u, 2047u, 0u, 0u};
    case 0x4074a0: return {2047u, 2047u, 0u, 0u};
    case 0x408520: return {2047u, 2047u, 0u, 0u};
    case 0x409150: return {2047u, 2047u, 0u, 0u};
    case 0x409fe0: return {2047u, 2047u, 0u, 0u};
    case 0x40b820: return {2047u, 2047u, 0u, 0u};
    case 0x40e220: return {2047u, 2047u, 0u, 0u};
    case 0x40eb80: return {2047u, 2047u, 0u, 0u};
    case 0x40fad0: return {2047u, 2047u, 0u, 0u};
    case 0x410a20: return {2047u, 2047u, 0u, 0u};
    case 0x410fd0: return {2047u, 2047u, 0u, 0u};
    case 0x411480: return {2047u, 2047u, 0u, 0u};
    case 0x411930: return {2047u, 2047u, 0u, 0u};
    case 0x411e10: return {2047u, 2047u, 0u, 0u};
    case 0x412400: return {2047u, 2047u, 0u, 0u};
    case 0x412970: return {2047u, 2047u, 0u, 0u};
    case 0x412e20: return {2047u, 2047u, 0u, 0u};
    case 0x413600: return {2047u, 2047u, 0u, 0u};
    case 0x413b20: return {2047u, 2047u, 0u, 0u};
    case 0x414190: return {2047u, 2047u, 0u, 0u};
    case 0x414d80: return {2047u, 2047u, 0u, 0u};
    case 0x415410: return {2047u, 2047u, 0u, 0u};
    case 0x415aa0: return {2047u, 2047u, 0u, 0u};
    case 0x4212c0: return {2047u, 2047u, 0u, 0u};
    case 0x4251e0: return {2047u, 2047u, 0u, 0u};
    case 0x425220: return {2047u, 2047u, 0u, 0u};
    case 0x425260: return {2047u, 2047u, 0u, 0u};
    case 0x4252a0: return {2047u, 2047u, 0u, 0u};
    case 0x4252e0: return {2047u, 2047u, 0u, 0u};
    case 0x425320: return {2047u, 2047u, 0u, 0u};
    case 0x425360: return {2047u, 2047u, 0u, 0u};
    case 0x4253a0: return {2047u, 2047u, 0u, 0u};
    case 0x4253e0: return {2047u, 2047u, 0u, 0u};
    case 0x425420: return {2047u, 2047u, 0u, 0u};
    case 0x425460: return {2047u, 2047u, 0u, 0u};
    case 0x4313e0: return {2047u, 2047u, 0u, 0u};
    case 0x431d90: return {2047u, 2047u, 0u, 0u};
    case 0x432630: return {2047u, 2047u, 0u, 0u};
    case 0x433a70: return {2047u, 2047u, 0u, 0u};
    case 0x4348f0: return {2047u, 2047u, 0u, 0u};
    case 0x436890: return {2047u, 2047u, 0u, 0u};
    case 0x4368d0: return {2047u, 2047u, 0u, 0u};
    case 0x436910: return {2047u, 2047u, 0u, 0u};
    case 0x437500: return {2047u, 2047u, 0u, 0u};
    case 0x437550: return {2047u, 2047u, 0u, 0u};
    case 0x4380a0: return {2047u, 2047u, 0u, 0u};
    case 0x43acc0: return {2047u, 2047u, 0u, 0u};
    case 0x43cd60: return {2047u, 2047u, 0u, 0u};
    case 0x43d330: return {2047u, 2047u, 0u, 0u};
    case 0x43d3e0: return {2047u, 2047u, 0u, 0u};
    case 0x43d430: return {2047u, 2047u, 0u, 0u};
    case 0x441270: return {2047u, 2047u, 0u, 0u};
    case 0x441ca0: return {2047u, 2047u, 0u, 0u};
    case 0x443350: return {2047u, 2047u, 0u, 0u};
    case 0x445a90: return {2047u, 2047u, 0u, 0u};
    case 0x446610: return {2047u, 2047u, 0u, 0u};
    case 0x4487f0: return {2047u, 2047u, 0u, 0u};
    case 0x448dd0: return {2047u, 2047u, 0u, 0u};
    case 0x449530: return {2047u, 2047u, 0u, 0u};
    case 0x449d00: return {2047u, 2047u, 0u, 0u};
    case 0x44c7e0: return {2047u, 2047u, 0u, 0u};
    case 0x453cb0: return {2047u, 2047u, 0u, 0u};
    case 0x453cf0: return {2047u, 2047u, 0u, 0u};
    case 0x454380: return {2047u, 2047u, 0u, 0u};
    case 0x4555a0: return {2047u, 2047u, 0u, 0u};
    case 0x455aa0: return {2047u, 2047u, 0u, 0u};
    case 0x456280: return {2047u, 2047u, 0u, 0u};
    case 0x456bc0: return {2047u, 2047u, 0u, 0u};
    case 0x4576e0: return {2047u, 2047u, 0u, 0u};
    case 0x458220: return {2047u, 2047u, 0u, 0u};
    case 0x458740: return {2047u, 2047u, 0u, 0u};
    case 0x45a3a0: return {2047u, 2047u, 0u, 0u};
    case 0x45aca0: return {2047u, 2047u, 0u, 0u};
    case 0x4606b0: return {2047u, 2047u, 0u, 0u};
    case 0x462a90: return {2047u, 2047u, 0u, 0u};
    case 0x463ae0: return {2047u, 2047u, 0u, 0u};
    case 0x465140: return {2047u, 2047u, 0u, 0u};
    case 0x465d50: return {2047u, 2047u, 0u, 0u};
    case 0x468a70: return {2047u, 2047u, 0u, 0u};
    case 0x46f640: return {2047u, 2047u, 0u, 0u};
    case 0x473ee0: return {2047u, 2047u, 0u, 0u};
    case 0x474780: return {2047u, 2047u, 0u, 0u};
    case 0x474ed0: return {2047u, 2047u, 0u, 0u};
    case 0x474f20: return {2047u, 2047u, 0u, 0u};
    case 0x474f60: return {2047u, 2047u, 0u, 0u};
    case 0x47cd10: return {2047u, 2047u, 0u, 0u};
    case 0x47dac0: return {2047u, 2047u, 0u, 0u};
    case 0x47e880: return {2047u, 2047u, 0u, 0u};
    case 0x47f7a0: return {2047u, 2047u, 0u, 0u};
    case 0x483120: return {2047u, 2047u, 0u, 0u};
    case 0x484370: return {2047u, 2047u, 0u, 0u};
    case 0x484870: return {2047u, 2047u, 0u, 0u};
    case 0x485900: return {2047u, 2047u, 0u, 0u};
    case 0x487340: return {2047u, 2047u, 0u, 0u};
    case 0x488980: return {2047u, 2047u, 0u, 0u};
    case 0x489090: return {2047u, 2047u, 0u, 0u};
    case 0x4897f0: return {2047u, 2047u, 0u, 0u};
    case 0x48b060: return {2047u, 2047u, 0u, 0u};
    case 0x48d1d0: return {2047u, 2047u, 0u, 0u};
    case 0x48e560: return {2047u, 2047u, 0u, 0u};
    case 0x492380: return {2047u, 2047u, 0u, 0u};
    case 0x493f70: return {2047u, 2047u, 0u, 0u};
    case 0x4970d0: return {2047u, 2047u, 0u, 0u};
    case 0x498160: return {2047u, 2047u, 0u, 0u};
    case 0x49f160: return {2047u, 2047u, 0u, 0u};
    case 0x49f850: return {2047u, 2047u, 0u, 0u};
    case 0x49f890: return {2047u, 2047u, 0u, 0u};
    case 0x4a01d0: return {2047u, 2047u, 0u, 0u};
    case 0x4ff951: return {2047u, 2047u, 0u, 0u};
    case 0x502405: return {2047u, 2047u, 0u, 0u};
    case 0x502426: return {2047u, 2047u, 0u, 0u};
    case 0x50245e: return {2047u, 2047u, 0u, 0u};
    case 0x502546: return {2047u, 2047u, 0u, 0u};
    case 0x5028d7: return {2047u, 2047u, 0u, 0u};
    case 0x502b00: return {2047u, 2047u, 0u, 0u};
    case 0x502b4d: return {2047u, 2047u, 0u, 0u};
    case 0x4f821d: return {2047u, 2047u, 0u, 0u};
    case 0x4f8233: return {2047u, 2047u, 0u, 0u};
    case 0x4f8271: return {2047u, 2047u, 0u, 0u};
    case 0x4f82af: return {2047u, 2047u, 0u, 0u};
    case 0x4f82ed: return {2047u, 2047u, 0u, 0u};
    case 0x502cc6: return {2047u, 2047u, 0u, 0u};
    case 0x502cfe: return {2047u, 2047u, 0u, 0u};
    case 0x502d30: return {2047u, 2047u, 0u, 0u};
    case 0x4ffce4: return {2047u, 2047u, 0u, 0u};
    case 0x4ffd07: return {2047u, 2047u, 0u, 0u};
    case 0x4b9110: return {2047u, 2047u, 0u, 0u};
    case 0x4bc0d0: return {2047u, 2047u, 0u, 0u};
    case 0x4db600: return {2047u, 2047u, 0u, 0u};
    case 0x4dbb70: return {2047u, 2047u, 0u, 0u};
    case 0x4dc160: return {2047u, 2047u, 0u, 0u};
    case 0x4dc260: return {2047u, 2047u, 0u, 0u};
    case 0x4dc380: return {2047u, 2047u, 0u, 0u};
    case 0x503813: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_initializer_wrappers_entry, owned, source_contract, body)
