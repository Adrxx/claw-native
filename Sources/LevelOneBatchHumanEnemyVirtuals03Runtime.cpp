// Level 1 human enemies: shared Soldier and Officer virtuals, batch 3
//
// Generated skeleton. Each stub below faults until someone implements it from
// the decompile and the disassembly in the task packet.
#include "ClawRuntime.hpp"

namespace {

using claw::Run;
using claw::s32;

// Stack-argument count of each owned function, or -1.
int owned(uint32_t function) {
    switch (function) {
    case 0x44dbb0:
        return 0;
    case 0x44de30:
        return 0;
    case 0x44df10:
        return 0;
    case 0x4407d0:
        return 0;
    case 0x4409d0:
        return 0;
    case 0x440b20:
        return 0;
    case 0x440c90:
        return 0;
    case 0x440410:
        return 0;
    case 0x440120:
        return 0;
    case 0x440420:
        return 0;
    default:
        return -1;
    }
}

// Entity fields used here: +0x0c player, +0x10 state object (+0x1c string id),
// +0x18 callback, +0x1c saved id, +0x20 mode, +0x24 previous id, +0x12c hero
// (+0x08 flags, +0xd0 mode, +0x118..0x124 rect, +0x188 animation player,
// +0x190 current frame), +0x134 current frame copy.
const uint32_t kStringTable = 0x537668;

uint32_t lookupString(Run &run, uint32_t text) {
    return run.call(0x4dba00, kStringTable, {text});
}

// Common prologue: previous id, string lookup, state id store.
void selectAnimation(Run &run, uint32_t entity, uint32_t slot) {
    uint32_t hero = run.get(entity + 0x12c);
    run.put(entity + 0x134, run.get(hero + 0x190));
    hero = run.get(entity + 0x12c);
    uint32_t animation = run.get(entity + slot);
    run.call(0x4c8220, hero + 0x188, {animation});
}

void orHeroFlags(Run &run, uint32_t entity, uint32_t bits) {
    uint32_t hero = run.get(entity + 0x12c);
    uint32_t flags = run.get(hero + 0x08);
    flags = flags | bits;
    run.put(hero + 0x08, flags);
}

void notifyAttached(Run &run, uint32_t entity, uint32_t slot) {
    uint32_t attached = run.get(entity + slot);
    if (attached == 0)
        return;
    uint32_t enabled = run.get(0x532c0c);
    uint32_t argument = run.get(0x532c10);
    if (enabled == 0)
        return;
    uint32_t target = run.get(attached + 0x10);
    run.call(0x4b45f0, target, {argument, 0, 0, 0});
}

// 0x440120. Thrown state.
uint32_t function_440120(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entity = receiver;
    run.put(entity + 0x20, 1);
    run.put(entity + 0x18, 0x440350);
    uint32_t state = run.get(entity + 0x10);
    run.put(entity + 0x1c, run.get(state + 0x1c));
    selectAnimation(run, entity, 0x380);
    state = run.get(entity + 0x10);
    run.put(entity + 0x24, run.get(state + 0x1c));
    uint32_t id = lookupString(run, 0x5271cc);
    state = run.get(entity + 0x10);
    run.put(state + 0x1c, id);
    uint32_t player = run.get(entity + 0x0c);
    run.put(player + 0xcc, 8);
    orHeroFlags(run, entity, 4);
    uint32_t hero = run.get(entity + 0x12c);
    run.put(hero + 0xd0, 0x10);
    run.put(entity + 0x50, 0);
    run.put(entity + 0x58, 0);
    run.put(entity + 0x60, 0);
    run.put(entity + 0x54, 0);
    run.put(entity + 0x5c, 0);
    run.put(entity + 0x64, 0);
    run.put(entity + 0xc8, 0);
    uint32_t scale = run.get(entity + 0x1ac);
    uint32_t horizontal;
    uint32_t factor;
    if (run.get(0x537224) != 0) {
        factor = 0x14;
        horizontal = (scale + 2) * 100;
    } else {
        horizontal = scale * 3 + 200;
        factor = 2;
    }
    uint32_t scene = run.get(0x537e88);
    uint32_t middle = run.get(scene + 0x6c);
    uint32_t cell = run.get(middle + 0x14);
    uint32_t vertical = 0xfffffda8u - factor * scale;
    if (run.get(cell) == 0)
        horizontal = 0u - horizontal;
    run.putd(entity + 0x50, double(s32(horizontal)));
    run.putd(entity + 0x58, double(s32(vertical)));
    run.put(entity + 0x60, 0);
    run.put(entity + 0x64, 0);
    return 0;
}

// 0x440420. Lifted state.
uint32_t function_440420(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entity = receiver;
    run.put(entity + 0x20, 1);
    uint32_t state = run.get(entity + 0x10);
    run.put(entity + 0x24, run.get(state + 0x1c));
    uint32_t id = lookupString(run, 0x5271d8);
    state = run.get(entity + 0x10);
    run.put(state + 0x1c, id);
    run.put(entity + 0x18, 0x440710);
    state = run.get(entity + 0x10);
    run.put(entity + 0x1c, run.get(state + 0x1c));
    uint32_t player = run.get(entity + 0x0c);
    run.put(player + 0xcc, 7);
    ClawX87State fp{};
    fp.size = sizeof(fp);
    fp.version = CLAW_X87_VERSION;
    fp.control = 0x023f;
    run.x87_step(CLAW_X87_F64, fp, {run.get(entity + 0x70), run.get(entity + 0x74)});
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(0x50dba8), run.get(0x50dbac)});
    uint64_t argument = run.x87_step(CLAW_X87_STP_F64, fp);
    fp.popCount = 0;
    fp.pushCount = 1;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    run.call_x87_exact(0x420b60, entity + 0x28, fp, {uint32_t(argument), uint32_t(argument >> 32)});
    uint64_t result = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(entity + 0x58, uint32_t(result));
    run.put(entity + 0x5c, uint32_t(result >> 32));
    run.x87_step(CLAW_X87_F64, fp, {run.get(entity + 0x70), run.get(entity + 0x74)});
    run.x87_step(CLAW_X87_SUB_F64, fp, {run.get(0x50dba8), run.get(0x50dbac)});
    run.put(entity + 0xb8, 0);
    run.put(entity + 0xbc, 0xbff00000);
    uint64_t lowered = run.x87_step(CLAW_X87_STP_F64, fp);
    run.put(entity + 0x70, uint32_t(lowered));
    run.put(entity + 0x74, uint32_t(lowered >> 32));
    uint32_t low = run.get(0x513e10);
    uint32_t high = run.get(0x513e14);
    run.put(entity + 0x80, low);
    run.put(entity + 0x84, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(entity + 0x98, low);
    run.put(entity + 0x9c, high);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(entity + 0x88, low);
    run.put(entity + 0x8c, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(entity + 0xa0, low);
    run.put(entity + 0xa4, high);
    low = run.get(0x513e10);
    high = run.get(0x513e14);
    run.put(entity + 0x90, low);
    run.put(entity + 0x94, high);
    low = run.get(0x513e18);
    high = run.get(0x513e1c);
    run.put(entity + 0xa8, low);
    run.put(entity + 0xac, high);
    run.put(entity + 0xc8, 1);
    orHeroFlags(run, entity, 2);
    run.put(entity + 0x2cc, 0);
    run.x87_step(CLAW_X87_F64, fp, {run.get(entity + 0x70), run.get(entity + 0x74)});
    fp.popCount = 1;
    fp.pushCount = 0;
    fp.returned = 0;
    fp.eax = 0;
    fp.edx = 0;
    uint32_t truncated = run.call_x87_exact(0x4a30e0, 0, fp);
    player = run.get(entity + 0x0c);
    run.put(entity + 0x284, truncated + run.get(player + 0x124));
    orHeroFlags(run, entity, 4);
    player = run.get(entity + 0x0c);
    run.icall(0x546d58, {entity + 0x270, player + 0x118});
    uint32_t hero;
    uint32_t bottom = run.get(entity + 0x26c);
    uint32_t right = run.get(entity + 0x268);
    uint32_t top = run.get(entity + 0x264);
    hero = run.get(entity + 0x12c);
    uint32_t left = run.get(entity + 0x260);
    run.put(hero + 0x11c, top);
    run.put(hero + 0x118, left);
    run.put(hero + 0x120, right);
    run.put(hero + 0x124, bottom);
    return 0;
}

// 0x44dbb0. Hit counter state machine.
uint32_t function_44dbb0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entity = receiver;
    uint32_t counter = run.get(entity + 0x424);
    counter = counter + 1;
    run.put(entity + 0x424, counter);
    if (counter == 1) {
        uint32_t attached = run.get(entity + 0x408);
        if (attached != 0) {
            uint32_t enabled = run.get(0x532c0c);
            uint32_t argument = run.get(0x532c10);
            if (enabled != 0) {
                uint32_t target = run.get(attached + 0x10);
                run.call(0x4b45f0, target, {argument, 0, 0, 0});
            }
        }
    }
    if (s32(run.get(entity + 0x424)) <= 2) {
        run.call(0x43fe60, entity);
        return 0;
    }
    run.put(entity + 0x50, 0);
    run.put(entity + 0x54, 0);
    if (run.get(entity + 0x424) == 3) {
        run.vcall(entity, 0x90, {500});
        return 0;
    }
    run.vcall(entity, 0xa8);
    uint32_t player = run.get(entity + 0x0c);
    if (s32(run.get(player + 0x10c)) <= 0) {
        run.vcall(entity, 0x5c, {1});
        return 0;
    }
    run.put(entity + 0x424, 0);
    uint32_t hero = run.get(entity + 0x12c);
    run.put(hero + 0xd0, 4);
    hero = run.get(entity + 0x12c);
    uint32_t flags = run.get(hero + 0x08);
    flags = flags & 0xfffffffb;
    run.put(hero + 0x08, flags);
    uint32_t rect = entity + 0x270;
    uint32_t left = run.get(rect);
    player = run.get(entity + 0x0c);
    uint32_t top = run.get(rect + 4);
    uint32_t delta = run.get(player + 0x124);
    uint32_t right = run.get(rect + 8);
    uint32_t bottom = run.get(rect + 0xc);
    delta = delta - bottom;
    uint32_t accumulated = run.get(player + 0x50);
    accumulated = accumulated + delta;
    run.put(player + 0x50, accumulated);
    hero = run.get(entity + 0x12c);
    run.put(hero + 0x118, left);
    run.put(hero + 0x11c, top);
    run.put(hero + 0x120, right);
    run.put(hero + 0x124, bottom);
    hero = run.get(entity + 0x12c);
    flags = run.get(hero + 0x08);
    flags = flags & 0xfffffffd;
    run.put(hero + 0x08, flags);
    hero = run.get(entity + 0x12c);
    uint32_t animation = run.get(entity + 0x344);
    uint32_t frame = run.get(hero + 0x190);
    uint32_t player8 = hero + 0x188;
    run.put(entity + 0x134, frame);
    run.call(0x4c8220, player8, {animation});
    uint32_t value = run.get(0x5430c4);
    run.call(0x4c82a0, player8, {value});
    run.vcall(entity, 0x44);
    run.put(entity + 0x20, 2);
    run.put(entity + 0x444, 0x5dc);
    uint32_t stamp = run.get(0x537210);
    run.put(entity + 0x440, stamp);
    return 0;
}

// 0x44de30. Thrown wrapper.
uint32_t function_44de30(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x42c, 2000);
    uint32_t stamp = run.get(0x537210);
    run.put(receiver + 0x428, stamp);
    function_440120(run, receiver, nullptr);
    return 0;
}

// 0x44df10. Random lift wrapper.
uint32_t function_44df10(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t random = run.call(0x4a3050, 0);
    if (s32(random) % 100 < 0x21) {
        uint32_t hero = run.get(receiver + 0x12c);
        uint32_t token = run.get(receiver + 0x410);
        if (run.get(hero + 0x38) != 0xffffffffu) {
            uint32_t player = run.get(receiver + 0x0c);
            run.call(0x48ce40, 0, {player, token, 0});
        }
    }
    function_440420(run, receiver, nullptr);
    return 0;
}

// 0x4407d0. Flailing state.
uint32_t function_4407d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entity = receiver;
    uint32_t hero = run.get(entity + 0x12c);
    uint32_t animation = run.get(entity + 0x37c);
    uint32_t frame = run.get(hero + 0x190);
    run.put(entity + 0x134, frame);
    run.call(0x4c8220, hero + 0x188, {animation});
    uint32_t state = run.get(entity + 0x10);
    run.put(entity + 0x24, run.get(state + 0x1c));
    uint32_t id = lookupString(run, 0x527170);
    state = run.get(entity + 0x10);
    run.put(state + 0x1c, id);
    uint32_t scene = run.get(0x537e88);
    uint32_t middle = run.get(scene + 0x6c);
    uint32_t cell = run.get(middle + 0x14);
    uint32_t sum;
    if (run.get(cell) == 0) {
        sum = run.get(entity + 0x2b4) + run.get(scene + 0x4c);
    } else {
        sum = run.get(entity + 0x2b8) + run.get(scene + 0x4c);
    }
    run.putd(entity + 0x68, double(s32(sum)));
    scene = run.get(0x537e88);
    uint32_t vertical = run.get(entity + 0x2bc) + run.get(scene + 0x50);
    run.putd(entity + 0x70, double(s32(vertical)));
    return 0;
}

// 0x4409d0. Dropped state.
uint32_t function_4409d0(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    uint32_t entity = receiver;
    uint32_t state = run.get(entity + 0x10);
    run.put(entity + 0x20, 1);
    run.put(entity + 0x24, run.get(state + 0x1c));
    uint32_t id = lookupString(run, 0x5271b4);
    state = run.get(entity + 0x10);
    run.put(state + 0x1c, id);
    uint32_t player = run.get(entity + 0x0c);
    run.put(player + 0xcc, 8);
    orHeroFlags(run, entity, 4);
    orHeroFlags(run, entity, 1);
    run.put(entity + 0xc8, 0);
    run.put(entity + 0x3f4, 1000);
    uint32_t stamp = run.get(0x537210);
    run.put(entity + 0x3f0, stamp);
    return 0;
}

// Shared body of the two block states (0x440b20 high, 0x440c90 low).
uint32_t blockState(Run &run, uint32_t entity, uint32_t text, uint32_t animationSlot, uint32_t attachedSlot) {
    uint32_t state = run.get(entity + 0x10);
    run.put(entity + 0x20, 1);
    run.put(entity + 0x18, 0x440c70);
    run.put(entity + 0x1c, run.get(state + 0x1c));
    run.put(entity + 0x24, run.get(state + 0x1c));
    uint32_t id = lookupString(run, text);
    state = run.get(entity + 0x10);
    run.put(state + 0x1c, id);
    uint32_t hero = run.get(entity + 0x12c);
    uint32_t animation = run.get(entity + animationSlot);
    uint32_t frame = run.get(hero + 0x190);
    run.put(entity + 0x134, frame);
    run.call(0x4c8220, hero + 0x188, {animation});
    notifyAttached(run, entity, attachedSlot);
    orHeroFlags(run, entity, 4);
    uint32_t kind = run.get(entity + 0x18c);
    run.put(entity + 0x50, 0);
    if (kind == 3) {
        run.put(entity + 0x54, 0x40690000);
        return 0;
    }
    run.put(entity + 0x54, 0xc0690000);
    return 0;
}

// 0x440b20. Block high state.
uint32_t function_440b20(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return blockState(run, receiver, 0x527188, 0x384, 0x3c0);
}

// 0x440c90. Block low state.
uint32_t function_440c90(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    return blockState(run, receiver, 0x52717c, 0x388, 0x3bc);
}

// 0x440410. Sets the +0x2cc flag.
uint32_t function_440410(Run &run, uint32_t receiver, const uint32_t *arguments) {
    (void)arguments;
    run.put(receiver + 0x2cc, 1);
    return 0;
}

uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x44dbb0:
        return function_44dbb0(run, receiver, arguments);
    case 0x44de30:
        return function_44de30(run, receiver, arguments);
    case 0x44df10:
        return function_44df10(run, receiver, arguments);
    case 0x4407d0:
        return function_4407d0(run, receiver, arguments);
    case 0x4409d0:
        return function_4409d0(run, receiver, arguments);
    case 0x440b20:
        return function_440b20(run, receiver, arguments);
    case 0x440c90:
        return function_440c90(run, receiver, arguments);
    case 0x440410:
        return function_440410(run, receiver, arguments);
    case 0x440120:
        return function_440120(run, receiver, arguments);
    case 0x440420:
        return function_440420(run, receiver, arguments);
    default:
        run.fail(CLAW_FAULT_ABI, function);
    }
}

} // namespace

CLAW_MODULE_ENTRY(claw_level_one_batch_human_enemy_virtuals_03_entry, owned, body)
