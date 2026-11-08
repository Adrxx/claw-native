// Original static constructor-call thunks with genuine receiver and tail frames
//
// Physical source frames and transfers follow the original constructor thunks.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x501fc7:
        return 0;
    case 0x502278:
        return 0;
    case 0x502c9a:
        return 0;
    case 0x502880:
        return 0;
    case 0x502c5b:
        return 0;
    case 0x50372c:
        return 0;
    case 0x503752:
        return 0;
    case 0x403550:
        return 0;
    case 0x4042c0:
        return 0;
    case 0x4064d0:
        return 0;
    case 0x406ea0:
        return 0;
    case 0x4074b0:
        return 0;
    case 0x408530:
        return 0;
    case 0x409160:
        return 0;
    case 0x409ff0:
        return 0;
    case 0x40b830:
        return 0;
    case 0x40e230:
        return 0;
    case 0x40eb90:
        return 0;
    case 0x40fae0:
        return 0;
    case 0x410a30:
        return 0;
    case 0x410fe0:
        return 0;
    case 0x411490:
        return 0;
    case 0x411940:
        return 0;
    case 0x411e20:
        return 0;
    case 0x412410:
        return 0;
    case 0x412980:
        return 0;
    case 0x412e30:
        return 0;
    case 0x413610:
        return 0;
    case 0x413b30:
        return 0;
    case 0x4141a0:
        return 0;
    case 0x414d90:
        return 0;
    case 0x415420:
        return 0;
    case 0x415ab0:
        return 0;
    case 0x4212d0:
        return 0;
    case 0x4251f0:
        return 0;
    case 0x425270:
        return 0;
    case 0x4252b0:
        return 0;
    case 0x4252f0:
        return 0;
    case 0x425330:
        return 0;
    case 0x425370:
        return 0;
    case 0x4253b0:
        return 0;
    case 0x4253f0:
        return 0;
    case 0x425430:
        return 0;
    case 0x425470:
        return 0;
    case 0x4313f0:
        return 0;
    case 0x431da0:
        return 0;
    case 0x432640:
        return 0;
    case 0x433a80:
        return 0;
    case 0x434900:
        return 0;
    case 0x4368a0:
        return 0;
    case 0x4368e0:
        return 0;
    case 0x436920:
        return 0;
    case 0x437510:
        return 0;
    case 0x437560:
        return 0;
    case 0x4380b0:
        return 0;
    case 0x43acd0:
        return 0;
    case 0x43cd70:
        return 0;
    case 0x43d340:
        return 0;
    case 0x43d3f0:
        return 0;
    case 0x43d440:
        return 0;
    case 0x441280:
        return 0;
    case 0x441cb0:
        return 0;
    case 0x443360:
        return 0;
    case 0x445aa0:
        return 0;
    case 0x446620:
        return 0;
    case 0x448800:
        return 0;
    case 0x448de0:
        return 0;
    case 0x449540:
        return 0;
    case 0x449d10:
        return 0;
    case 0x44c7f0:
        return 0;
    case 0x454390:
        return 0;
    case 0x4555b0:
        return 0;
    case 0x455ab0:
        return 0;
    case 0x456290:
        return 0;
    case 0x456bd0:
        return 0;
    case 0x4576f0:
        return 0;
    case 0x458230:
        return 0;
    case 0x458750:
        return 0;
    case 0x45a3b0:
        return 0;
    case 0x4606c0:
        return 0;
    case 0x462aa0:
        return 0;
    case 0x463af0:
        return 0;
    case 0x465150:
        return 0;
    case 0x465d60:
        return 0;
    case 0x468a80:
        return 0;
    case 0x46f650:
        return 0;
    case 0x473ef0:
        return 0;
    case 0x474790:
        return 0;
    case 0x474ee0:
        return 0;
    case 0x474f30:
        return 0;
    case 0x474f70:
        return 0;
    case 0x47cd20:
        return 0;
    case 0x47dad0:
        return 0;
    case 0x47e890:
        return 0;
    case 0x47f7b0:
        return 0;
    case 0x483130:
        return 0;
    case 0x484380:
        return 0;
    case 0x484880:
        return 0;
    case 0x485910:
        return 0;
    case 0x487350:
        return 0;
    case 0x488990:
        return 0;
    case 0x4890a0:
        return 0;
    case 0x489800:
        return 0;
    case 0x48b070:
        return 0;
    case 0x48d1e0:
        return 0;
    case 0x48e570:
        return 0;
    case 0x492390:
        return 0;
    case 0x493f80:
        return 0;
    case 0x4970e0:
        return 0;
    case 0x498170:
        return 0;
    case 0x49f170:
        return 0;
    case 0x49f860:
        return 0;
    case 0x49f8a0:
        return 0;
    case 0x4a01e0:
        return 0;
    case 0x4ff95b:
        return 0;
    case 0x502430:
        return 0;
    case 0x502468:
        return 0;
    case 0x4f823d:
        return 0;
    case 0x4f827b:
        return 0;
    case 0x4f82b9:
        return 0;
    case 0x4f82f7:
        return 0;
    case 0x502cd0:
        return 0;
    case 0x502d08:
        return 0;
    case 0x502d3a:
        return 0;
    case 0x4b9120:
        return 0;
    case 0x4bc0e0:
        return 0;
    default:
        return -1;
    }
}

// 0x501fc7 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_501fc7(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x501fc7;
    return context.eax;
}

// 0x502278 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502278(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502278;
    return context.eax;
}

// 0x502c9a StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502c9a(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502c9a;
    context.ecx = 0x540708;
    context.eip = 0x502c9f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a2cf1;
    run.source_tail(0x4a2cf1, context.ecx, 0x502c9f, child);
}

// 0x502880 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502880;
    return context.eax;
}

// 0x502c5b StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502c5b(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502c5b;
    return context.eax;
}

// 0x50372c StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_50372c(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x50372c;
    return context.eax;
}

// 0x503752 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_503752(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x503752;
    return context.eax;
}

// 0x403550 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_403550(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x403550;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x403555;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40355a;
    context.ecx = 0x534820;
    context.eip = 0x40355f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x403564);
    try {
        run.source_call(0x403ad0, context.ecx, 0x403564, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x403564;
    return context.eax;
}

// 0x4042c0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4042c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4042c0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4042c5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4042ca;
    context.ecx = 0x534850;
    context.eip = 0x4042cf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4042d4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4042d4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4042d4;
    return context.eax;
}

// 0x4064d0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4064d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4064d0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4064d5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4064da;
    context.ecx = 0x534888;
    context.eip = 0x4064df;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4064e4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4064e4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4064e4;
    return context.eax;
}

// 0x406ea0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_406ea0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x406ea0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x406ea5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x406eaa;
    context.ecx = 0x5348b8;
    context.eip = 0x406eaf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x406eb4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x406eb4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x406eb4;
    return context.eax;
}

// 0x4074b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4074b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4074b0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4074b5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4074ba;
    context.ecx = 0x5348e8;
    context.eip = 0x4074bf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4074c4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4074c4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4074c4;
    return context.eax;
}

// 0x408530 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_408530(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x408530;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x408535;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40853a;
    context.ecx = 0x534910;
    context.eip = 0x40853f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x408544);
    try {
        run.source_call(0x403ad0, context.ecx, 0x408544, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x408544;
    return context.eax;
}

// 0x409160 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_409160(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x409160;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x409165;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40916a;
    context.ecx = 0x534948;
    context.eip = 0x40916f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x409174);
    try {
        run.source_call(0x403ad0, context.ecx, 0x409174, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x409174;
    return context.eax;
}

// 0x409ff0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_409ff0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x409ff0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x409ff5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x409ffa;
    context.ecx = 0x534978;
    context.eip = 0x409fff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x40a004);
    try {
        run.source_call(0x403ad0, context.ecx, 0x40a004, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x40a004;
    return context.eax;
}

// 0x40b830 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_40b830(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x40b830;
    context.esp -= 0x4;
    run.put(context.esp, 0x534938);
    context.eip = 0x40b835;
    context.ecx = 0x53499c;
    context.eip = 0x40b83a;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f65f2;
    child.esp -= 0x4;
    run.put(child.esp, 0x40b83f);
    try {
        run.source_call(0x4f65f2, context.ecx, 0x40b83f, child, {0x534938}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x40b83f;
    return context.eax;
}

// 0x40e230 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_40e230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x40e230;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x40e235;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40e23a;
    context.ecx = 0x5349b8;
    context.eip = 0x40e23f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x40e244);
    try {
        run.source_call(0x403ad0, context.ecx, 0x40e244, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x40e244;
    return context.eax;
}

// 0x40eb90 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_40eb90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x40eb90;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x40eb95;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40eb9a;
    context.ecx = 0x5349e0;
    context.eip = 0x40eb9f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x40eba4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x40eba4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x40eba4;
    return context.eax;
}

// 0x40fae0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_40fae0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x40fae0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x40fae5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x40faea;
    context.ecx = 0x534a10;
    context.eip = 0x40faef;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x40faf4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x40faf4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x40faf4;
    return context.eax;
}

// 0x410a30 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_410a30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x410a30;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x410a35;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x410a3a;
    context.ecx = 0x534ab0;
    context.eip = 0x410a3f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x410a44);
    try {
        run.source_call(0x403ad0, context.ecx, 0x410a44, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x410a44;
    return context.eax;
}

// 0x410fe0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_410fe0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x410fe0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x410fe5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x410fea;
    context.ecx = 0x534ba0;
    context.eip = 0x410fef;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x410ff4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x410ff4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x410ff4;
    return context.eax;
}

// 0x411490 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_411490(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x411490;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x411495;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41149a;
    context.ecx = 0x534a38;
    context.eip = 0x41149f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4114a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4114a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4114a4;
    return context.eax;
}

// 0x411940 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_411940(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x411940;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x411945;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41194a;
    context.ecx = 0x534b00;
    context.eip = 0x41194f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x411954);
    try {
        run.source_call(0x403ad0, context.ecx, 0x411954, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x411954;
    return context.eax;
}

// 0x411e20 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_411e20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x411e20;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x411e25;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x411e2a;
    context.ecx = 0x534ad8;
    context.eip = 0x411e2f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x411e34);
    try {
        run.source_call(0x403ad0, context.ecx, 0x411e34, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x411e34;
    return context.eax;
}

// 0x412410 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_412410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x412410;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x412415;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41241a;
    context.ecx = 0x534b28;
    context.eip = 0x41241f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x412424);
    try {
        run.source_call(0x403ad0, context.ecx, 0x412424, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x412424;
    return context.eax;
}

// 0x412980 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_412980(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x412980;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x412985;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41298a;
    context.ecx = 0x534bc8;
    context.eip = 0x41298f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x412994);
    try {
        run.source_call(0x403ad0, context.ecx, 0x412994, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x412994;
    return context.eax;
}

// 0x412e30 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_412e30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x412e30;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x412e35;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x412e3a;
    context.ecx = 0x534a88;
    context.eip = 0x412e3f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x412e44);
    try {
        run.source_call(0x403ad0, context.ecx, 0x412e44, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x412e44;
    return context.eax;
}

// 0x413610 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_413610(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x413610;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x413615;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41361a;
    context.ecx = 0x534b78;
    context.eip = 0x41361f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x413624);
    try {
        run.source_call(0x403ad0, context.ecx, 0x413624, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x413624;
    return context.eax;
}

// 0x413b30 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_413b30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x413b30;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x413b35;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x413b3a;
    context.ecx = 0x534b50;
    context.eip = 0x413b3f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x413b44);
    try {
        run.source_call(0x403ad0, context.ecx, 0x413b44, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x413b44;
    return context.eax;
}

// 0x4141a0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4141a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4141a0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4141a5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4141aa;
    context.ecx = 0x534bf8;
    context.eip = 0x4141af;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4141b4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4141b4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4141b4;
    return context.eax;
}

// 0x414d90 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_414d90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x414d90;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x414d95;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x414d9a;
    context.ecx = 0x534c28;
    context.eip = 0x414d9f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x414da4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x414da4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x414da4;
    return context.eax;
}

// 0x415420 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_415420(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x415420;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x415425;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x41542a;
    context.ecx = 0x534c58;
    context.eip = 0x41542f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x415434);
    try {
        run.source_call(0x403ad0, context.ecx, 0x415434, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x415434;
    return context.eax;
}

// 0x415ab0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_415ab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x415ab0;
    context.eax = run.get(0x513e10);
    context.eip = 0x415ab5;
    context.ecx = run.get(0x513e14);
    context.eip = 0x415abb;
    context.edx = run.get(0x513e18);
    context.eip = 0x415ac1;
    run.put(0x534e10, context.eax);
    context.eip = 0x415ac6;
    context.eax = run.get(0x513e1c);
    context.eip = 0x415acb;
    run.put(0x534e14, context.ecx);
    context.eip = 0x415ad1;
    context.ecx = run.get(0x513e10);
    context.eip = 0x415ad7;
    run.put(0x534e28, context.edx);
    context.eip = 0x415add;
    context.edx = run.get(0x513e14);
    context.eip = 0x415ae3;
    run.put(0x534e2c, context.eax);
    context.eip = 0x415ae8;
    context.eax = run.get(0x513e18);
    context.eip = 0x415aed;
    run.put(0x534e18, context.ecx);
    context.eip = 0x415af3;
    context.ecx = run.get(0x513e1c);
    context.eip = 0x415af9;
    run.put(0x534e1c, context.edx);
    context.eip = 0x415aff;
    context.edx = run.get(0x513e10);
    context.eip = 0x415b05;
    run.put(0x534e30, context.eax);
    context.eip = 0x415b0a;
    context.eax = run.get(0x513e14);
    context.eip = 0x415b0f;
    run.put(0x534e34, context.ecx);
    context.eip = 0x415b15;
    context.ecx = run.get(0x513e18);
    context.eip = 0x415b1b;
    run.put(0x534e20, context.edx);
    context.eip = 0x415b21;
    context.edx = run.get(0x513e1c);
    context.eip = 0x415b27;
    run.put(0x534e24, context.eax);
    context.eip = 0x415b2c;
    run.put(0x534e38, context.ecx);
    context.eip = 0x415b32;
    context.eax = context.ecx;
    context.eip = 0x415b34;
    run.put(0x534e3c, context.edx);
    context.eip = 0x415b3a;
    context.ecx = context.edx;
    context.eip = 0x415b3c;
    run.put(0x534e78, context.eax);
    context.eip = 0x415b41;
    context.edx = context.eax;
    context.eip = 0x415b43;
    run.put(0x534e7c, context.ecx);
    context.eip = 0x415b49;
    context.eax = context.ecx;
    context.eip = 0x415b4b;
    run.put(0x534e80, context.edx);
    context.eip = 0x415b51;
    context.ecx = context.edx;
    context.eip = 0x415b53;
    run.put(0x534e84, context.eax);
    context.eip = 0x415b58;
    context.edx = context.eax;
    context.eip = 0x415b5a;
    run.put(0x534e88, context.ecx);
    context.eip = 0x415b60;
    context.eax = context.ecx;
    context.eip = 0x415b62;
    run.put(0x534e8c, context.edx);
    context.eip = 0x415b68;
    context.ecx = context.edx;
    context.eip = 0x415b6a;
    run.put(0x534e90, context.eax);
    context.eip = 0x415b6f;
    context.edx = context.eax;
    context.eip = 0x415b71;
    run.put(0x534e94, context.ecx);
    context.eip = 0x415b77;
    context.eax = context.ecx;
    context.eip = 0x415b79;
    run.put(0x534e98, context.edx);
    context.eip = 0x415b7f;
    context.ecx = context.edx;
    context.eip = 0x415b81;
    context.edx = context.eax;
    context.eip = 0x415b83;
    run.put(0x534df8, 0);
    context.eip = 0x415b8d;
    run.put(0x534dfc, 0);
    context.eip = 0x415b97;
    run.put(0x534e00, 0);
    context.eip = 0x415ba1;
    run.put(0x534e04, 0);
    context.eip = 0x415bab;
    run.put(0x534e08, 0);
    context.eip = 0x415bb5;
    run.put(0x534e0c, 0);
    context.eip = 0x415bbf;
    run.put(0x534de0, 0);
    context.eip = 0x415bc9;
    run.put(0x534de4, 0);
    context.eip = 0x415bd3;
    run.put(0x534de8, 0);
    context.eip = 0x415bdd;
    run.put(0x534dec, 0);
    context.eip = 0x415be7;
    run.put(0x534df0, 0);
    context.eip = 0x415bf1;
    run.put(0x534df4, 0);
    context.eip = 0x415bfb;
    run.put(0x534dc8, 0);
    context.eip = 0x415c05;
    run.put(0x534dcc, 0);
    context.eip = 0x415c0f;
    run.put(0x534dd0, 0);
    context.eip = 0x415c19;
    run.put(0x534dd4, 0);
    context.eip = 0x415c23;
    run.put(0x534dd8, 0);
    context.eip = 0x415c2d;
    run.put(0x534ddc, 0);
    context.eip = 0x415c37;
    run.put(0x534db8, 0);
    context.eip = 0x415c41;
    run.put(0x534dbc, 0);
    context.eip = 0x415c4b;
    run.put(0x534dc0, 0);
    context.eip = 0x415c55;
    run.put(0x534dc4, 0);
    context.eip = 0x415c5f;
    run.put(0x534e60, 0);
    context.eip = 0x415c69;
    run.put(0x534e64, 0);
    context.eip = 0x415c73;
    run.put(0x534e68, 0);
    context.eip = 0x415c7d;
    run.put(0x534e6c, 0);
    context.eip = 0x415c87;
    run.put(0x534e70, 0);
    context.eip = 0x415c91;
    run.put(0x534e74, 0);
    context.eip = 0x415c9b;
    run.put(0x534e58, 0);
    context.eip = 0x415ca5;
    run.put(0x534e9c, context.eax);
    context.eip = 0x415caa;
    run.put(0x534ea0, context.ecx);
    context.eip = 0x415cb0;
    run.put(0x534ea4, context.edx);
    context.eip = 0x415cb6;
    return context.eax;
}

// 0x4212d0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4212d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4212d0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4212d5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4212da;
    context.ecx = 0x534ed0;
    context.eip = 0x4212df;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4212e4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4212e4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4212e4;
    return context.eax;
}

// 0x4251f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4251f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4251f0;
    context.esp -= 0x4;
    run.put(context.esp, 0x524eec);
    context.eip = 0x4251f5;
    context.ecx = 0x537008;
    context.eip = 0x4251fa;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x50257f;
    child.esp -= 0x4;
    run.put(child.esp, 0x4251ff);
    try {
        run.source_call(0x50257f, context.ecx, 0x4251ff, child, {0x524eec}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4251ff;
    return context.eax;
}

// 0x425270 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_425270(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425270;
    context.ecx = 0x5371ec;
    context.eip = 0x425275;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x425275, child);
}

// 0x4252b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4252b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4252b0;
    context.ecx = 0x5371f0;
    context.eip = 0x4252b5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4252b5, child);
}

// 0x4252f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4252f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4252f0;
    context.ecx = 0x5371f4;
    context.eip = 0x4252f5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4252f5, child);
}

// 0x425330 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_425330(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425330;
    context.ecx = 0x5371f8;
    context.eip = 0x425335;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x425335, child);
}

// 0x425370 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_425370(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425370;
    context.ecx = 0x5371dc;
    context.eip = 0x425375;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x425375, child);
}

// 0x4253b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4253b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4253b0;
    context.ecx = 0x5371e0;
    context.eip = 0x4253b5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4253b5, child);
}

// 0x4253f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4253f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4253f0;
    context.ecx = 0x5371e4;
    context.eip = 0x4253f5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4253f5, child);
}

// 0x425430 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_425430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425430;
    context.ecx = 0x5371e8;
    context.eip = 0x425435;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x425435, child);
}

// 0x425470 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_425470(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x425470;
    context.ecx = 0x5371d8;
    context.eip = 0x425475;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x425475, child);
}

// 0x4313f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4313f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4313f0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4313f5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4313fa;
    context.ecx = 0x537278;
    context.eip = 0x4313ff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x431404);
    try {
        run.source_call(0x403ad0, context.ecx, 0x431404, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x431404;
    return context.eax;
}

// 0x431da0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_431da0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x431da0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x431da5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x431daa;
    context.ecx = 0x5372a8;
    context.eip = 0x431daf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x431db4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x431db4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x431db4;
    return context.eax;
}

// 0x432640 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_432640(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x432640;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x432645;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43264a;
    context.ecx = 0x5372d8;
    context.eip = 0x43264f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x432654);
    try {
        run.source_call(0x403ad0, context.ecx, 0x432654, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x432654;
    return context.eax;
}

// 0x433a80 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_433a80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x433a80;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x433a85;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x433a8a;
    context.ecx = 0x537308;
    context.eip = 0x433a8f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x433a94);
    try {
        run.source_call(0x403ad0, context.ecx, 0x433a94, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x433a94;
    return context.eax;
}

// 0x434900 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_434900(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x434900;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x434905;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43490a;
    context.ecx = 0x537338;
    context.eip = 0x43490f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x434914);
    try {
        run.source_call(0x403ad0, context.ecx, 0x434914, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x434914;
    return context.eax;
}

// 0x4368a0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4368a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4368a0;
    context.ecx = 0x537568;
    context.eip = 0x4368a5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4368a5, child);
}

// 0x4368e0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4368e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4368e0;
    context.ecx = 0x537570;
    context.eip = 0x4368e5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x4368e5, child);
}

// 0x436920 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_436920(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x436920;
    context.ecx = 0x53756c;
    context.eip = 0x436925;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x436925, child);
}

// 0x437510 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_437510(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x437510;
    context.esp -= 0x4;
    run.put(context.esp, 0x534938);
    context.eip = 0x437515;
    context.ecx = 0x537588;
    context.eip = 0x43751a;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f65f2;
    child.esp -= 0x4;
    run.put(child.esp, 0x43751f);
    try {
        run.source_call(0x4f65f2, context.ecx, 0x43751f, child, {0x534938}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43751f;
    return context.eax;
}

// 0x437560 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_437560(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x437560;
    context.esp -= 0x4;
    run.put(context.esp, 0x534938);
    context.eip = 0x437565;
    context.ecx = 0x53758c;
    context.eip = 0x43756a;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f65f2;
    child.esp -= 0x4;
    run.put(child.esp, 0x43756f);
    try {
        run.source_call(0x4f65f2, context.ecx, 0x43756f, child, {0x534938}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43756f;
    return context.eax;
}

// 0x4380b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4380b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4380b0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4380b5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4380ba;
    context.ecx = 0x537598;
    context.eip = 0x4380bf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4380c4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4380c4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4380c4;
    return context.eax;
}

// 0x43acd0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_43acd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x43acd0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x43acd5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43acda;
    context.ecx = 0x5375d8;
    context.eip = 0x43acdf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x43ace4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x43ace4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43ace4;
    return context.eax;
}

// 0x43cd70 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_43cd70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x43cd70;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x43cd75;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43cd7a;
    context.ecx = 0x537608;
    context.eip = 0x43cd7f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x43cd84);
    try {
        run.source_call(0x403ad0, context.ecx, 0x43cd84, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43cd84;
    return context.eax;
}

// 0x43d340 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d340(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x43d340;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x43d342;
    context.ecx = 0x537668;
    context.eip = 0x43d347;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x440ee0;
    child.esp -= 0x4;
    run.put(child.esp, 0x43d34c);
    try {
        run.source_call(0x440ee0, context.ecx, 0x43d34c, child, {0x0}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43d34c;
    return context.eax;
}

// 0x43d3f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d3f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x43d3f0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x43d3f5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43d3fa;
    context.ecx = 0x537698;
    context.eip = 0x43d3ff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x440f30;
    child.esp -= 0x4;
    run.put(child.esp, 0x43d404);
    try {
        run.source_call(0x440f30, context.ecx, 0x43d404, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43d404;
    return context.eax;
}

// 0x43d440 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_43d440(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x43d440;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x43d445;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x43d44a;
    context.ecx = 0x537638;
    context.eip = 0x43d44f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x43d454);
    try {
        run.source_call(0x403ad0, context.ecx, 0x43d454, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x43d454;
    return context.eax;
}

// 0x441280 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_441280(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x441280;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x441285;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44128a;
    context.ecx = 0x5376c8;
    context.eip = 0x44128f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x441294);
    try {
        run.source_call(0x403ad0, context.ecx, 0x441294, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x441294;
    return context.eax;
}

// 0x441cb0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_441cb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x441cb0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x441cb5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x441cba;
    context.ecx = 0x5376f8;
    context.eip = 0x441cbf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x441cc4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x441cc4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x441cc4;
    return context.eax;
}

// 0x443360 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_443360(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x443360;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x443365;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44336a;
    context.ecx = 0x537728;
    context.eip = 0x44336f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x443374);
    try {
        run.source_call(0x403ad0, context.ecx, 0x443374, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x443374;
    return context.eax;
}

// 0x445aa0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_445aa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x445aa0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x445aa5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x445aaa;
    context.ecx = 0x537758;
    context.eip = 0x445aaf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x445ab4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x445ab4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x445ab4;
    return context.eax;
}

// 0x446620 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_446620(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x446620;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x446625;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44662a;
    context.ecx = 0x537788;
    context.eip = 0x44662f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x446634);
    try {
        run.source_call(0x403ad0, context.ecx, 0x446634, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x446634;
    return context.eax;
}

// 0x448800 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_448800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x448800;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x448805;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44880a;
    context.ecx = 0x5377b8;
    context.eip = 0x44880f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x448814);
    try {
        run.source_call(0x403ad0, context.ecx, 0x448814, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x448814;
    return context.eax;
}

// 0x448de0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_448de0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x448de0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x448de5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x448dea;
    context.ecx = 0x5377e8;
    context.eip = 0x448def;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x448df4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x448df4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x448df4;
    return context.eax;
}

// 0x449540 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_449540(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x449540;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x449545;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44954a;
    context.ecx = 0x537818;
    context.eip = 0x44954f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x449554);
    try {
        run.source_call(0x403ad0, context.ecx, 0x449554, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x449554;
    return context.eax;
}

// 0x449d10 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_449d10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x449d10;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x449d15;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x449d1a;
    context.ecx = 0x537848;
    context.eip = 0x449d1f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x449d24);
    try {
        run.source_call(0x403ad0, context.ecx, 0x449d24, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x449d24;
    return context.eax;
}

// 0x44c7f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_44c7f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x44c7f0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x44c7f5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x44c7fa;
    context.ecx = 0x537878;
    context.eip = 0x44c7ff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x44c804);
    try {
        run.source_call(0x403ad0, context.ecx, 0x44c804, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x44c804;
    return context.eax;
}

// 0x454390 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_454390(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x454390;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x454395;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x45439a;
    context.ecx = 0x537980;
    context.eip = 0x45439f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4543a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4543a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4543a4;
    return context.eax;
}

// 0x4555b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4555b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4555b0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4555b5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4555ba;
    context.ecx = 0x5379d0;
    context.eip = 0x4555bf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4555c4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4555c4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4555c4;
    return context.eax;
}

// 0x455ab0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_455ab0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x455ab0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x455ab5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x455aba;
    context.ecx = 0x537a00;
    context.eip = 0x455abf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x455ac4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x455ac4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x455ac4;
    return context.eax;
}

// 0x456290 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_456290(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x456290;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x456295;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x45629a;
    context.ecx = 0x537a30;
    context.eip = 0x45629f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4562a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4562a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4562a4;
    return context.eax;
}

// 0x456bd0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_456bd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x456bd0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x456bd5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x456bda;
    context.ecx = 0x537a60;
    context.eip = 0x456bdf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x456be4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x456be4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x456be4;
    return context.eax;
}

// 0x4576f0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4576f0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4576f0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4576f5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4576fa;
    context.ecx = 0x537a90;
    context.eip = 0x4576ff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x457704);
    try {
        run.source_call(0x403ad0, context.ecx, 0x457704, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x457704;
    return context.eax;
}

// 0x458230 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_458230(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x458230;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x458235;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x45823a;
    context.ecx = 0x537ac0;
    context.eip = 0x45823f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x458244);
    try {
        run.source_call(0x403ad0, context.ecx, 0x458244, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x458244;
    return context.eax;
}

// 0x458750 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_458750(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x458750;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x458755;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x45875a;
    context.ecx = 0x537af0;
    context.eip = 0x45875f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x458764);
    try {
        run.source_call(0x403ad0, context.ecx, 0x458764, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x458764;
    return context.eax;
}

// 0x45a3b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_45a3b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x45a3b0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x45a3b5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x45a3ba;
    context.ecx = 0x537b20;
    context.eip = 0x45a3bf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x45a3c4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x45a3c4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x45a3c4;
    return context.eax;
}

// 0x4606c0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4606c0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4606c0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4606c5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4606ca;
    context.ecx = 0x537b68;
    context.eip = 0x4606cf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4606d4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4606d4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4606d4;
    return context.eax;
}

// 0x462aa0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_462aa0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x462aa0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x462aa5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x462aaa;
    context.ecx = 0x537ba0;
    context.eip = 0x462aaf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x462ab4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x462ab4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x462ab4;
    return context.eax;
}

// 0x463af0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_463af0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x463af0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x463af5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x463afa;
    context.ecx = 0x537bd0;
    context.eip = 0x463aff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x463b04);
    try {
        run.source_call(0x403ad0, context.ecx, 0x463b04, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x463b04;
    return context.eax;
}

// 0x465150 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_465150(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x465150;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x465155;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x46515a;
    context.ecx = 0x537c00;
    context.eip = 0x46515f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x465164);
    try {
        run.source_call(0x403ad0, context.ecx, 0x465164, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x465164;
    return context.eax;
}

// 0x465d60 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_465d60(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x465d60;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x465d65;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x465d6a;
    context.ecx = 0x537c30;
    context.eip = 0x465d6f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x465d74);
    try {
        run.source_call(0x403ad0, context.ecx, 0x465d74, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x465d74;
    return context.eax;
}

// 0x468a80 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_468a80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x468a80;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x468a85;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x468a8a;
    context.ecx = 0x537c60;
    context.eip = 0x468a8f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x468a94);
    try {
        run.source_call(0x403ad0, context.ecx, 0x468a94, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x468a94;
    return context.eax;
}

// 0x46f650 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_46f650(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x46f650;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x46f655;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x46f65a;
    context.ecx = 0x537ea0;
    context.eip = 0x46f65f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x46f664);
    try {
        run.source_call(0x403ad0, context.ecx, 0x46f664, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x46f664;
    return context.eax;
}

// 0x473ef0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_473ef0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x473ef0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x473ef5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x473efa;
    context.ecx = 0x538428;
    context.eip = 0x473eff;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x473f04);
    try {
        run.source_call(0x403ad0, context.ecx, 0x473f04, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x473f04;
    return context.eax;
}

// 0x474790 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_474790(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x474790;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x474795;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x47479a;
    context.ecx = 0x538458;
    context.eip = 0x47479f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4747a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4747a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4747a4;
    return context.eax;
}

// 0x474ee0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_474ee0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x474ee0;
    context.ecx = 0x53abd8;
    context.eip = 0x474ee5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f54ea;
    run.source_tail(0x4f54ea, context.ecx, 0x474ee5, child);
}

// 0x474f30 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_474f30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x474f30;
    context.ecx = 0x53beb4;
    context.eip = 0x474f35;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x474f35, child);
}

// 0x474f70 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_474f70(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x474f70;
    context.ecx = 0x5384ac;
    context.eip = 0x474f75;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x474f75, child);
}

// 0x47cd20 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_47cd20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x47cd20;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x47cd25;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x47cd2a;
    context.ecx = 0x53c0e8;
    context.eip = 0x47cd2f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x47cd34);
    try {
        run.source_call(0x403ad0, context.ecx, 0x47cd34, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x47cd34;
    return context.eax;
}

// 0x47dad0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_47dad0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x47dad0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x47dad5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x47dada;
    context.ecx = 0x53c118;
    context.eip = 0x47dadf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x47dae4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x47dae4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x47dae4;
    return context.eax;
}

// 0x47e890 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_47e890(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x47e890;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x47e895;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x47e89a;
    context.ecx = 0x53c148;
    context.eip = 0x47e89f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x47e8a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x47e8a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x47e8a4;
    return context.eax;
}

// 0x47f7b0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_47f7b0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x47f7b0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x47f7b5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x47f7ba;
    context.ecx = 0x53c178;
    context.eip = 0x47f7bf;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x47f7c4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x47f7c4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x47f7c4;
    return context.eax;
}

// 0x483130 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_483130(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x483130;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x483135;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48313a;
    context.ecx = 0x53c1a8;
    context.eip = 0x48313f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x483144);
    try {
        run.source_call(0x403ad0, context.ecx, 0x483144, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x483144;
    return context.eax;
}

// 0x484380 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_484380(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x484380;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x484385;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48438a;
    context.ecx = 0x53c1d8;
    context.eip = 0x48438f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x484394);
    try {
        run.source_call(0x403ad0, context.ecx, 0x484394, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x484394;
    return context.eax;
}

// 0x484880 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_484880(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x484880;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x484885;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48488a;
    context.ecx = 0x53c208;
    context.eip = 0x48488f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x484894);
    try {
        run.source_call(0x403ad0, context.ecx, 0x484894, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x484894;
    return context.eax;
}

// 0x485910 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_485910(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x485910;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x485915;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48591a;
    context.ecx = 0x53c238;
    context.eip = 0x48591f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x485924);
    try {
        run.source_call(0x403ad0, context.ecx, 0x485924, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x485924;
    return context.eax;
}

// 0x487350 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_487350(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x487350;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x487355;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48735a;
    context.ecx = 0x53c270;
    context.eip = 0x48735f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x487364);
    try {
        run.source_call(0x403ad0, context.ecx, 0x487364, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x487364;
    return context.eax;
}

// 0x488990 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_488990(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x488990;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x488995;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48899a;
    context.ecx = 0x53c2a0;
    context.eip = 0x48899f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4889a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4889a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4889a4;
    return context.eax;
}

// 0x4890a0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4890a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4890a0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4890a5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4890aa;
    context.ecx = 0x53c2c8;
    context.eip = 0x4890af;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4890b4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4890b4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4890b4;
    return context.eax;
}

// 0x489800 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_489800(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x489800;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x489805;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48980a;
    context.ecx = 0x53c2f8;
    context.eip = 0x48980f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x489814);
    try {
        run.source_call(0x403ad0, context.ecx, 0x489814, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x489814;
    return context.eax;
}

// 0x48b070 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_48b070(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x48b070;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x48b075;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48b07a;
    context.ecx = 0x53c328;
    context.eip = 0x48b07f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x48b084);
    try {
        run.source_call(0x403ad0, context.ecx, 0x48b084, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x48b084;
    return context.eax;
}

// 0x48d1e0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_48d1e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x48d1e0;
    context.ecx = 0x53c9bc;
    context.eip = 0x48d1e5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x48d1e5, child);
}

// 0x48e570 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_48e570(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x48e570;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x48e575;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x48e57a;
    context.ecx = 0x53c9d0;
    context.eip = 0x48e57f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x48e584);
    try {
        run.source_call(0x403ad0, context.ecx, 0x48e584, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x48e584;
    return context.eax;
}

// 0x492390 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_492390(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x492390;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x492395;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x49239a;
    context.ecx = 0x53ca08;
    context.eip = 0x49239f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4923a4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4923a4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4923a4;
    return context.eax;
}

// 0x493f80 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_493f80(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x493f80;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x493f85;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x493f8a;
    context.ecx = 0x53ca40;
    context.eip = 0x493f8f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x493f94);
    try {
        run.source_call(0x403ad0, context.ecx, 0x493f94, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x493f94;
    return context.eax;
}

// 0x4970e0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4970e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4970e0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4970e5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4970ea;
    context.ecx = 0x53ca70;
    context.eip = 0x4970ef;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4970f4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4970f4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4970f4;
    return context.eax;
}

// 0x498170 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_498170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x498170;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x498175;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x49817a;
    context.ecx = 0x53caa0;
    context.eip = 0x49817f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x498184);
    try {
        run.source_call(0x403ad0, context.ecx, 0x498184, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x498184;
    return context.eax;
}

// 0x49f170 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f170(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x49f170;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x49f175;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x49f17a;
    context.ecx = 0x53ec00;
    context.eip = 0x49f17f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x49f184);
    try {
        run.source_call(0x403ad0, context.ecx, 0x49f184, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x49f184;
    return context.eax;
}

// 0x49f860 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f860(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x49f860;
    context.ecx = 0x53ec30;
    context.eip = 0x49f865;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x49f865, child);
}

// 0x49f8a0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_49f8a0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x49f8a0;
    context.ecx = 0x53ec48;
    context.eip = 0x49f8a5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f6439;
    run.source_tail(0x4f6439, context.ecx, 0x49f8a5, child);
}

// 0x4a01e0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4a01e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4a01e0;
    context.esp -= 0x4;
    run.put(context.esp, 0x7da);
    context.eip = 0x4a01e5;
    context.esp -= 0x4;
    run.put(context.esp, 0x7d0);
    context.eip = 0x4a01ea;
    context.ecx = 0x53ec68;
    context.eip = 0x4a01ef;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x403ad0;
    child.esp -= 0x4;
    run.put(child.esp, 0x4a01f4);
    try {
        run.source_call(0x403ad0, context.ecx, 0x4a01f4, child, {0x7d0, 0x7da}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4a01f4;
    return context.eax;
}

// 0x4ff95b StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4ff95b(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4ff95b;
    return context.eax;
}

// 0x502430 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502430(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502430;
    context.esp -= 0x4;
    run.put(context.esp, 0xf022);
    context.eip = 0x502435;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x502437;
    context.ecx = 0x53ed40;
    context.eip = 0x50243c;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a13f4;
    child.esp -= 0x4;
    run.put(child.esp, 0x502441);
    try {
        run.source_call(0x4a13f4, context.ecx, 0x502441, child, {0x0, 0xf022}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x502441;
    return context.eax;
}

// 0x502468 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502468(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502468;
    context.esp -= 0x4;
    run.put(context.esp, 0xf024);
    context.eip = 0x50246d;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x50246f;
    context.ecx = 0x53eca8;
    context.eip = 0x502474;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a141e;
    child.esp -= 0x4;
    run.put(child.esp, 0x502479);
    try {
        run.source_call(0x4a141e, context.ecx, 0x502479, child, {0x0, 0xf024}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x502479;
    return context.eax;
}

// 0x4f823d StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f823d(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4f823d;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x4f823f;
    context.ecx = 0x540600;
    context.eip = 0x4f8244;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f8371;
    child.esp -= 0x4;
    run.put(child.esp, 0x4f8249);
    try {
        run.source_call(0x4f8371, context.ecx, 0x4f8249, child, {0x0}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4f8249;
    return context.eax;
}

// 0x4f827b StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f827b(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4f827b;
    context.esp -= 0x4;
    run.put(context.esp, 0x1);
    context.eip = 0x4f827d;
    context.ecx = 0x5406c0;
    context.eip = 0x4f8282;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f8371;
    child.esp -= 0x4;
    run.put(child.esp, 0x4f8287);
    try {
        run.source_call(0x4f8371, context.ecx, 0x4f8287, child, {0x1}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4f8287;
    return context.eax;
}

// 0x4f82b9 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f82b9(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4f82b9;
    context.esp -= 0x4;
    run.put(context.esp, 0xffffffff);
    context.eip = 0x4f82bb;
    context.ecx = 0x540640;
    context.eip = 0x4f82c0;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f8371;
    child.esp -= 0x4;
    run.put(child.esp, 0x4f82c5);
    try {
        run.source_call(0x4f8371, context.ecx, 0x4f82c5, child, {0xffffffff}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4f82c5;
    return context.eax;
}

// 0x4f82f7 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4f82f7(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4f82f7;
    context.esp -= 0x4;
    run.put(context.esp, 0xfffffffe);
    context.eip = 0x4f82f9;
    context.ecx = 0x540680;
    context.eip = 0x4f82fe;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f8371;
    child.esp -= 0x4;
    run.put(child.esp, 0x4f8303);
    try {
        run.source_call(0x4f8371, context.ecx, 0x4f8303, child, {0xfffffffe}, 0, 0x4);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x4f8303;
    return context.eax;
}

// 0x502cd0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502cd0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502cd0;
    context.esp -= 0x4;
    run.put(context.esp, 0xf023);
    context.eip = 0x502cd5;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x502cd7;
    context.ecx = 0x540748;
    context.eip = 0x502cdc;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a2e53;
    child.esp -= 0x4;
    run.put(child.esp, 0x502ce1);
    try {
        run.source_call(0x4a2e53, context.ecx, 0x502ce1, child, {0x0, 0xf023}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x502ce1;
    return context.eax;
}

// 0x502d08 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502d08(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502d08;
    context.esp -= 0x4;
    run.put(context.esp, 0xf021);
    context.eip = 0x502d0d;
    context.esp -= 0x4;
    run.put(context.esp, 0x0);
    context.eip = 0x502d0f;
    context.ecx = 0x5407e0;
    context.eip = 0x502d14;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4a2e7d;
    child.esp -= 0x4;
    run.put(child.esp, 0x502d19);
    try {
        run.source_call(0x4a2e7d, context.ecx, 0x502d19, child, {0x0, 0xf021}, 0, 0x8);
    } catch (const claw::Failure &) {
        std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
        throw;
    }
    std::memcpy(&context.eax, &child.eax, 11 * sizeof(uint32_t));
    context.eip = 0x502d19;
    return context.eax;
}

// 0x502d3a StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_502d3a(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x502d3a;
    context.ecx = 0x540878;
    context.eip = 0x502d3f;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x502dac;
    run.source_tail(0x502dac, context.ecx, 0x502d3f, child);
}

// 0x4b9120 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4b9120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4b9120;
    context.ecx = 0x541348;
    context.eip = 0x4b9125;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f54ea;
    run.source_tail(0x4f54ea, context.ecx, 0x4b9125, child);
}

// 0x4bc0e0 StaticConstructorThunk. cdecl, 0 stack argument(s), returns void.
uint32_t function_4bc0e0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)receiver;
    (void)arguments;
    auto &context = run.source();
    context.eip = 0x4bc0e0;
    context.ecx = 0x541378;
    context.eip = 0x4bc0e5;
    auto child = context;
    child.inputMask = 0x7ff;
    child.outputMask = 0x7ff;
    child.preserveMask = 0;
    child.eip = 0x4f54ea;
    run.source_tail(0x4f54ea, context.ecx, 0x4bc0e5, child);
}


uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x501fc7:
        return function_501fc7(run, receiver, arguments);
    case 0x502278:
        return function_502278(run, receiver, arguments);
    case 0x502c9a:
        return function_502c9a(run, receiver, arguments);
    case 0x502880:
        return function_502880(run, receiver, arguments);
    case 0x502c5b:
        return function_502c5b(run, receiver, arguments);
    case 0x50372c:
        return function_50372c(run, receiver, arguments);
    case 0x503752:
        return function_503752(run, receiver, arguments);
    case 0x403550:
        return function_403550(run, receiver, arguments);
    case 0x4042c0:
        return function_4042c0(run, receiver, arguments);
    case 0x4064d0:
        return function_4064d0(run, receiver, arguments);
    case 0x406ea0:
        return function_406ea0(run, receiver, arguments);
    case 0x4074b0:
        return function_4074b0(run, receiver, arguments);
    case 0x408530:
        return function_408530(run, receiver, arguments);
    case 0x409160:
        return function_409160(run, receiver, arguments);
    case 0x409ff0:
        return function_409ff0(run, receiver, arguments);
    case 0x40b830:
        return function_40b830(run, receiver, arguments);
    case 0x40e230:
        return function_40e230(run, receiver, arguments);
    case 0x40eb90:
        return function_40eb90(run, receiver, arguments);
    case 0x40fae0:
        return function_40fae0(run, receiver, arguments);
    case 0x410a30:
        return function_410a30(run, receiver, arguments);
    case 0x410fe0:
        return function_410fe0(run, receiver, arguments);
    case 0x411490:
        return function_411490(run, receiver, arguments);
    case 0x411940:
        return function_411940(run, receiver, arguments);
    case 0x411e20:
        return function_411e20(run, receiver, arguments);
    case 0x412410:
        return function_412410(run, receiver, arguments);
    case 0x412980:
        return function_412980(run, receiver, arguments);
    case 0x412e30:
        return function_412e30(run, receiver, arguments);
    case 0x413610:
        return function_413610(run, receiver, arguments);
    case 0x413b30:
        return function_413b30(run, receiver, arguments);
    case 0x4141a0:
        return function_4141a0(run, receiver, arguments);
    case 0x414d90:
        return function_414d90(run, receiver, arguments);
    case 0x415420:
        return function_415420(run, receiver, arguments);
    case 0x415ab0:
        return function_415ab0(run, receiver, arguments);
    case 0x4212d0:
        return function_4212d0(run, receiver, arguments);
    case 0x4251f0:
        return function_4251f0(run, receiver, arguments);
    case 0x425270:
        return function_425270(run, receiver, arguments);
    case 0x4252b0:
        return function_4252b0(run, receiver, arguments);
    case 0x4252f0:
        return function_4252f0(run, receiver, arguments);
    case 0x425330:
        return function_425330(run, receiver, arguments);
    case 0x425370:
        return function_425370(run, receiver, arguments);
    case 0x4253b0:
        return function_4253b0(run, receiver, arguments);
    case 0x4253f0:
        return function_4253f0(run, receiver, arguments);
    case 0x425430:
        return function_425430(run, receiver, arguments);
    case 0x425470:
        return function_425470(run, receiver, arguments);
    case 0x4313f0:
        return function_4313f0(run, receiver, arguments);
    case 0x431da0:
        return function_431da0(run, receiver, arguments);
    case 0x432640:
        return function_432640(run, receiver, arguments);
    case 0x433a80:
        return function_433a80(run, receiver, arguments);
    case 0x434900:
        return function_434900(run, receiver, arguments);
    case 0x4368a0:
        return function_4368a0(run, receiver, arguments);
    case 0x4368e0:
        return function_4368e0(run, receiver, arguments);
    case 0x436920:
        return function_436920(run, receiver, arguments);
    case 0x437510:
        return function_437510(run, receiver, arguments);
    case 0x437560:
        return function_437560(run, receiver, arguments);
    case 0x4380b0:
        return function_4380b0(run, receiver, arguments);
    case 0x43acd0:
        return function_43acd0(run, receiver, arguments);
    case 0x43cd70:
        return function_43cd70(run, receiver, arguments);
    case 0x43d340:
        return function_43d340(run, receiver, arguments);
    case 0x43d3f0:
        return function_43d3f0(run, receiver, arguments);
    case 0x43d440:
        return function_43d440(run, receiver, arguments);
    case 0x441280:
        return function_441280(run, receiver, arguments);
    case 0x441cb0:
        return function_441cb0(run, receiver, arguments);
    case 0x443360:
        return function_443360(run, receiver, arguments);
    case 0x445aa0:
        return function_445aa0(run, receiver, arguments);
    case 0x446620:
        return function_446620(run, receiver, arguments);
    case 0x448800:
        return function_448800(run, receiver, arguments);
    case 0x448de0:
        return function_448de0(run, receiver, arguments);
    case 0x449540:
        return function_449540(run, receiver, arguments);
    case 0x449d10:
        return function_449d10(run, receiver, arguments);
    case 0x44c7f0:
        return function_44c7f0(run, receiver, arguments);
    case 0x454390:
        return function_454390(run, receiver, arguments);
    case 0x4555b0:
        return function_4555b0(run, receiver, arguments);
    case 0x455ab0:
        return function_455ab0(run, receiver, arguments);
    case 0x456290:
        return function_456290(run, receiver, arguments);
    case 0x456bd0:
        return function_456bd0(run, receiver, arguments);
    case 0x4576f0:
        return function_4576f0(run, receiver, arguments);
    case 0x458230:
        return function_458230(run, receiver, arguments);
    case 0x458750:
        return function_458750(run, receiver, arguments);
    case 0x45a3b0:
        return function_45a3b0(run, receiver, arguments);
    case 0x4606c0:
        return function_4606c0(run, receiver, arguments);
    case 0x462aa0:
        return function_462aa0(run, receiver, arguments);
    case 0x463af0:
        return function_463af0(run, receiver, arguments);
    case 0x465150:
        return function_465150(run, receiver, arguments);
    case 0x465d60:
        return function_465d60(run, receiver, arguments);
    case 0x468a80:
        return function_468a80(run, receiver, arguments);
    case 0x46f650:
        return function_46f650(run, receiver, arguments);
    case 0x473ef0:
        return function_473ef0(run, receiver, arguments);
    case 0x474790:
        return function_474790(run, receiver, arguments);
    case 0x474ee0:
        return function_474ee0(run, receiver, arguments);
    case 0x474f30:
        return function_474f30(run, receiver, arguments);
    case 0x474f70:
        return function_474f70(run, receiver, arguments);
    case 0x47cd20:
        return function_47cd20(run, receiver, arguments);
    case 0x47dad0:
        return function_47dad0(run, receiver, arguments);
    case 0x47e890:
        return function_47e890(run, receiver, arguments);
    case 0x47f7b0:
        return function_47f7b0(run, receiver, arguments);
    case 0x483130:
        return function_483130(run, receiver, arguments);
    case 0x484380:
        return function_484380(run, receiver, arguments);
    case 0x484880:
        return function_484880(run, receiver, arguments);
    case 0x485910:
        return function_485910(run, receiver, arguments);
    case 0x487350:
        return function_487350(run, receiver, arguments);
    case 0x488990:
        return function_488990(run, receiver, arguments);
    case 0x4890a0:
        return function_4890a0(run, receiver, arguments);
    case 0x489800:
        return function_489800(run, receiver, arguments);
    case 0x48b070:
        return function_48b070(run, receiver, arguments);
    case 0x48d1e0:
        return function_48d1e0(run, receiver, arguments);
    case 0x48e570:
        return function_48e570(run, receiver, arguments);
    case 0x492390:
        return function_492390(run, receiver, arguments);
    case 0x493f80:
        return function_493f80(run, receiver, arguments);
    case 0x4970e0:
        return function_4970e0(run, receiver, arguments);
    case 0x498170:
        return function_498170(run, receiver, arguments);
    case 0x49f170:
        return function_49f170(run, receiver, arguments);
    case 0x49f860:
        return function_49f860(run, receiver, arguments);
    case 0x49f8a0:
        return function_49f8a0(run, receiver, arguments);
    case 0x4a01e0:
        return function_4a01e0(run, receiver, arguments);
    case 0x4ff95b:
        return function_4ff95b(run, receiver, arguments);
    case 0x502430:
        return function_502430(run, receiver, arguments);
    case 0x502468:
        return function_502468(run, receiver, arguments);
    case 0x4f823d:
        return function_4f823d(run, receiver, arguments);
    case 0x4f827b:
        return function_4f827b(run, receiver, arguments);
    case 0x4f82b9:
        return function_4f82b9(run, receiver, arguments);
    case 0x4f82f7:
        return function_4f82f7(run, receiver, arguments);
    case 0x502cd0:
        return function_502cd0(run, receiver, arguments);
    case 0x502d08:
        return function_502d08(run, receiver, arguments);
    case 0x502d3a:
        return function_502d3a(run, receiver, arguments);
    case 0x4b9120:
        return function_4b9120(run, receiver, arguments);
    case 0x4bc0e0:
        return function_4bc0e0(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

static ClawSourceContract source_contract(uint32_t function) {
    switch (function) {
    case 0x501fc7: return {2047u, 2047u, 0u, 0u};
    case 0x502278: return {2047u, 2047u, 0u, 0u};
    case 0x502c9a: return {2047u, 2047u, 0u, 0u};
    case 0x502880: return {2047u, 2047u, 0u, 0u};
    case 0x502c5b: return {2047u, 2047u, 0u, 0u};
    case 0x50372c: return {2047u, 2047u, 0u, 0u};
    case 0x503752: return {2047u, 2047u, 0u, 0u};
    case 0x403550: return {2047u, 2047u, 0u, 0u};
    case 0x4042c0: return {2047u, 2047u, 0u, 0u};
    case 0x4064d0: return {2047u, 2047u, 0u, 0u};
    case 0x406ea0: return {2047u, 2047u, 0u, 0u};
    case 0x4074b0: return {2047u, 2047u, 0u, 0u};
    case 0x408530: return {2047u, 2047u, 0u, 0u};
    case 0x409160: return {2047u, 2047u, 0u, 0u};
    case 0x409ff0: return {2047u, 2047u, 0u, 0u};
    case 0x40b830: return {2047u, 2047u, 0u, 0u};
    case 0x40e230: return {2047u, 2047u, 0u, 0u};
    case 0x40eb90: return {2047u, 2047u, 0u, 0u};
    case 0x40fae0: return {2047u, 2047u, 0u, 0u};
    case 0x410a30: return {2047u, 2047u, 0u, 0u};
    case 0x410fe0: return {2047u, 2047u, 0u, 0u};
    case 0x411490: return {2047u, 2047u, 0u, 0u};
    case 0x411940: return {2047u, 2047u, 0u, 0u};
    case 0x411e20: return {2047u, 2047u, 0u, 0u};
    case 0x412410: return {2047u, 2047u, 0u, 0u};
    case 0x412980: return {2047u, 2047u, 0u, 0u};
    case 0x412e30: return {2047u, 2047u, 0u, 0u};
    case 0x413610: return {2047u, 2047u, 0u, 0u};
    case 0x413b30: return {2047u, 2047u, 0u, 0u};
    case 0x4141a0: return {2047u, 2047u, 0u, 0u};
    case 0x414d90: return {2047u, 2047u, 0u, 0u};
    case 0x415420: return {2047u, 2047u, 0u, 0u};
    case 0x415ab0: return {2047u, 2047u, 0u, 0u};
    case 0x4212d0: return {2047u, 2047u, 0u, 0u};
    case 0x4251f0: return {2047u, 2047u, 0u, 0u};
    case 0x425270: return {2047u, 2047u, 0u, 0u};
    case 0x4252b0: return {2047u, 2047u, 0u, 0u};
    case 0x4252f0: return {2047u, 2047u, 0u, 0u};
    case 0x425330: return {2047u, 2047u, 0u, 0u};
    case 0x425370: return {2047u, 2047u, 0u, 0u};
    case 0x4253b0: return {2047u, 2047u, 0u, 0u};
    case 0x4253f0: return {2047u, 2047u, 0u, 0u};
    case 0x425430: return {2047u, 2047u, 0u, 0u};
    case 0x425470: return {2047u, 2047u, 0u, 0u};
    case 0x4313f0: return {2047u, 2047u, 0u, 0u};
    case 0x431da0: return {2047u, 2047u, 0u, 0u};
    case 0x432640: return {2047u, 2047u, 0u, 0u};
    case 0x433a80: return {2047u, 2047u, 0u, 0u};
    case 0x434900: return {2047u, 2047u, 0u, 0u};
    case 0x4368a0: return {2047u, 2047u, 0u, 0u};
    case 0x4368e0: return {2047u, 2047u, 0u, 0u};
    case 0x436920: return {2047u, 2047u, 0u, 0u};
    case 0x437510: return {2047u, 2047u, 0u, 0u};
    case 0x437560: return {2047u, 2047u, 0u, 0u};
    case 0x4380b0: return {2047u, 2047u, 0u, 0u};
    case 0x43acd0: return {2047u, 2047u, 0u, 0u};
    case 0x43cd70: return {2047u, 2047u, 0u, 0u};
    case 0x43d340: return {2047u, 2047u, 0u, 0u};
    case 0x43d3f0: return {2047u, 2047u, 0u, 0u};
    case 0x43d440: return {2047u, 2047u, 0u, 0u};
    case 0x441280: return {2047u, 2047u, 0u, 0u};
    case 0x441cb0: return {2047u, 2047u, 0u, 0u};
    case 0x443360: return {2047u, 2047u, 0u, 0u};
    case 0x445aa0: return {2047u, 2047u, 0u, 0u};
    case 0x446620: return {2047u, 2047u, 0u, 0u};
    case 0x448800: return {2047u, 2047u, 0u, 0u};
    case 0x448de0: return {2047u, 2047u, 0u, 0u};
    case 0x449540: return {2047u, 2047u, 0u, 0u};
    case 0x449d10: return {2047u, 2047u, 0u, 0u};
    case 0x44c7f0: return {2047u, 2047u, 0u, 0u};
    case 0x454390: return {2047u, 2047u, 0u, 0u};
    case 0x4555b0: return {2047u, 2047u, 0u, 0u};
    case 0x455ab0: return {2047u, 2047u, 0u, 0u};
    case 0x456290: return {2047u, 2047u, 0u, 0u};
    case 0x456bd0: return {2047u, 2047u, 0u, 0u};
    case 0x4576f0: return {2047u, 2047u, 0u, 0u};
    case 0x458230: return {2047u, 2047u, 0u, 0u};
    case 0x458750: return {2047u, 2047u, 0u, 0u};
    case 0x45a3b0: return {2047u, 2047u, 0u, 0u};
    case 0x4606c0: return {2047u, 2047u, 0u, 0u};
    case 0x462aa0: return {2047u, 2047u, 0u, 0u};
    case 0x463af0: return {2047u, 2047u, 0u, 0u};
    case 0x465150: return {2047u, 2047u, 0u, 0u};
    case 0x465d60: return {2047u, 2047u, 0u, 0u};
    case 0x468a80: return {2047u, 2047u, 0u, 0u};
    case 0x46f650: return {2047u, 2047u, 0u, 0u};
    case 0x473ef0: return {2047u, 2047u, 0u, 0u};
    case 0x474790: return {2047u, 2047u, 0u, 0u};
    case 0x474ee0: return {2047u, 2047u, 0u, 0u};
    case 0x474f30: return {2047u, 2047u, 0u, 0u};
    case 0x474f70: return {2047u, 2047u, 0u, 0u};
    case 0x47cd20: return {2047u, 2047u, 0u, 0u};
    case 0x47dad0: return {2047u, 2047u, 0u, 0u};
    case 0x47e890: return {2047u, 2047u, 0u, 0u};
    case 0x47f7b0: return {2047u, 2047u, 0u, 0u};
    case 0x483130: return {2047u, 2047u, 0u, 0u};
    case 0x484380: return {2047u, 2047u, 0u, 0u};
    case 0x484880: return {2047u, 2047u, 0u, 0u};
    case 0x485910: return {2047u, 2047u, 0u, 0u};
    case 0x487350: return {2047u, 2047u, 0u, 0u};
    case 0x488990: return {2047u, 2047u, 0u, 0u};
    case 0x4890a0: return {2047u, 2047u, 0u, 0u};
    case 0x489800: return {2047u, 2047u, 0u, 0u};
    case 0x48b070: return {2047u, 2047u, 0u, 0u};
    case 0x48d1e0: return {2047u, 2047u, 0u, 0u};
    case 0x48e570: return {2047u, 2047u, 0u, 0u};
    case 0x492390: return {2047u, 2047u, 0u, 0u};
    case 0x493f80: return {2047u, 2047u, 0u, 0u};
    case 0x4970e0: return {2047u, 2047u, 0u, 0u};
    case 0x498170: return {2047u, 2047u, 0u, 0u};
    case 0x49f170: return {2047u, 2047u, 0u, 0u};
    case 0x49f860: return {2047u, 2047u, 0u, 0u};
    case 0x49f8a0: return {2047u, 2047u, 0u, 0u};
    case 0x4a01e0: return {2047u, 2047u, 0u, 0u};
    case 0x4ff95b: return {2047u, 2047u, 0u, 0u};
    case 0x502430: return {2047u, 2047u, 0u, 0u};
    case 0x502468: return {2047u, 2047u, 0u, 0u};
    case 0x4f823d: return {2047u, 2047u, 0u, 0u};
    case 0x4f827b: return {2047u, 2047u, 0u, 0u};
    case 0x4f82b9: return {2047u, 2047u, 0u, 0u};
    case 0x4f82f7: return {2047u, 2047u, 0u, 0u};
    case 0x502cd0: return {2047u, 2047u, 0u, 0u};
    case 0x502d08: return {2047u, 2047u, 0u, 0u};
    case 0x502d3a: return {2047u, 2047u, 0u, 0u};
    case 0x4b9120: return {2047u, 2047u, 0u, 0u};
    case 0x4bc0e0: return {2047u, 2047u, 0u, 0u};
    default: return {};
    }
}
CLAW_SOURCE_MODULE_ENTRY(claw_static_constructor_thunks_entry, owned, source_contract, body)
