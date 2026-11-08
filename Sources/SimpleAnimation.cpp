#include <cstdint>

// Initially recovered from CrazyHook-pack CLAW.exe 0x0049ca30; registration at
// 0x00401fbe. This is the callback's control flow, not its animation callee.
// Field purposes and the global tick argument are not yet fully identified.
// Pointer offsets are kept in the evidence; this interface separates storage
// from behavior so it can be integrated with a native object model later.
static int step(std::uint32_t *logicState, std::uint32_t *logicField168, std::uint32_t *actorFieldE0,
                std::uint32_t actorAddress, std::uint32_t globalArgument, std::uint32_t *invoked,
                std::uint32_t *context, std::uint32_t *argument, std::uint32_t contextOffset) {
    *invoked = 0;
    *context = 0;
    *argument = 0;
    if (*logicState == 0) {
        *logicField168 = 0;
        *actorFieldE0 = 0;
        *logicState = 5;
    } else if (*logicState == 5) {
        // Pack: 0x4c8550(actor+0x1a0, [0x5aafd8]); v1.0: 0x4c82a0(actor+0x188, [0x5430c4]).
        *invoked = 1;
        *context = actorAddress + contextOffset;
        *argument = globalArgument;
    }
    return 1;
}

extern "C" int claw_simple_animation_step(uint32_t *state, uint32_t *field, uint32_t *actorField, uint32_t actor,
                                          uint32_t tick, uint32_t *invoked, uint32_t *context, uint32_t *argument) {
    return step(state, field, actorField, actor, tick, invoked, context, argument, 0x1a0);
}
// Original v1.0 callback 0x498f40; updater 0x4c82a0; actor context +0x188.
extern "C" int claw_simple_animation_step_v10(uint32_t *state, uint32_t *field, uint32_t *actorField, uint32_t actor,
                                              uint32_t tick, uint32_t *invoked, uint32_t *context, uint32_t *argument) {
    return step(state, field, actorField, actor, tick, invoked, context, argument, 0x188);
}
