#include "GraphicsManagerConstructionRuntime.h"
#include "SoundTriggerLogicRuntime.h"
#include <initializer_list>
uint32_t claw_graphics_string_array_construct(uint32_t t, ClawSceneActorHost h, uint32_t *fault, uint32_t *result) {
    if (result)
        *result = 0;
    auto *p = h.lookup ? h.lookup(h.context, t, 5) : nullptr;
    if (!p) {
        if (fault)
            *fault = 1;
        return 0;
    }
    p[0] = 0x51079c;
    p[1] = p[4] = p[3] = p[2] = 0;
    if (result)
        *result = t;
    return 1;
}
uint32_t claw_graphics_manager_construct(uint32_t t, ClawSceneActorHost h, uint32_t *fault, uint32_t *result) {
    if (result)
        *result = 0;
    auto *p = h.lookup ? h.lookup(h.context, t, 545) : nullptr;
    if (!p) {
        if (fault)
            *fault = 1;
        return 0;
    }
    ClawEnemySpeechGlobals globals{};
    ClawSoundTriggerContext c{};
    c.scene = h;
    c.globals = &globals;
    ClawSoundTriggerArguments args{};
    args.count = 1;
    args.words[0] = 10;
    uint32_t ignored = 0;
    for (uint32_t offset : {0x3b8u, 0x3d4u}) {
        if (!claw_sound_trigger_entry(0x4f5133, t + offset, args, &c, nullptr, nullptr, &ignored) || c.fault) {
            if (fault)
                *fault = c.fault ? c.fault : 1;
            return 0;
        }
    }
    if (!claw_graphics_string_array_construct(t + 0x3f0, h, fault, &ignored))
        return 0;
    p[0] = 0;
    p[0x470 / 4] = 0;
    p[0x474 / 4] = 0;
    p[0x878 / 4] = 0;
    p[0x87c / 4] = 0;
    p[0x880 / 4] = 0;
    if (result)
        *result = t;
    return 1;
}
