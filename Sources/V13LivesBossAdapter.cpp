// App composition over the retained v1.0 layout and canonical exports.
#include "ClawRuntime.hpp"
#include "V13LivesBoss.h"
#include <cmath>
#include <cstdlib>
#include <cstring>
extern "C" {
uint32_t claw_native_menu_player_startup_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_two_raux_core_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_four_katherine_core_springboard_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_six_wolvington_core_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_twelve_aquatis_core_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_eight_gabriel_bomb_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_six_wolvington_states_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_thirteen_red_tail_attacks_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_level_one_hud_timers_01_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
}
extern "C" uint32_t claw_v13_lives_boss_enabled(void) {
    if (std::getenv("CLAW_GAME_VERSION")) return claw_native_v13_enabled();
    const char *profile = std::getenv("CLAW_LIVES_BOSS_PROFILE");
    return !profile || std::strcmp(profile, "claw-v1.0") != 0;
}
extern "C" void claw_v13_player_construct_defaults(ClawPlayerLocomotion *player, ClawPlayerInitializationContext *context) {
    claw_player_construct_defaults(player, context);
    if (!claw_v13_lives_boss_enabled()) return;
    context->defaults[0x7c / 4] = claw_v13_starting_lives(context->difficulty);
    context->defaults[0xec / 4] = claw_v13_next_life_threshold(0);
}
namespace {
using claw::Run;
int startupOwned(uint32_t function) {
    switch (function) {
    case 0x415ce0: case 0x46c790: case 0x46d8e0: return 0;
    case 0x49af30: case 0x49af90: case 0x4222a0: case 0x422370: return 2;
    case 0x42af70: return 1;
    default: return -1;
    }
}
uint32_t startupBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    uint32_t result = 0;
    if (!claw_native_menu_player_startup_entry(function, receiver, arguments, uint32_t(startupOwned(function)), &run.host, &result))
        run.fail(CLAW_FAULT_ABI, function);
    if (!claw_v13_lives_boss_enabled()) return result;
    if (function == 0x415ce0) {
        run.put(0x534cfc, claw_v13_starting_lives(run.get(0x53725c)));
        run.put(0x534d6c, claw_v13_next_life_threshold(0));
    } else if (function == 0x46d8e0 && result) {
        run.put(0x534d6c, claw_v13_next_life_threshold(run.get(0x534cc4)));
    }
    return result;
}
int scoreOwned(uint32_t function) { return function == 0x4908b0 ? 1 : -1; }
uint32_t scoreBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    if (!claw_v13_lives_boss_enabled()) {
        uint32_t result = 0;
        if (!claw_level_one_hud_timers_01_entry(function, receiver, arguments, 1, &run.host, &result))
            run.fail(CLAW_FAULT_ABI, function);
        return result;
    }
    uint32_t actor = arguments[0];
    uint32_t state = run.get(run.get(actor + 0x6c) + 0x1c);
    uint32_t threshold = run.get(actor + 0xfc);
    uint32_t result = 0;
    if (!claw_level_one_hud_timers_01_entry(function, receiver, arguments, 1, &run.host, &result))
        run.fail(CLAW_FAULT_ABI, function);
    if (state == 0) {
        run.put(actor + 0xfc, claw_v13_next_life_threshold(run.get(0x534cc4)));
    } else if (state == 5 && run.get(actor + 0xfc) == threshold + 1000000u) {
        // Keep the retained one-award callback and cap effects, changing only
        // the observed interval increment.
        run.put(actor + 0xfc, threshold + 500000u);
    }
    return result;
}
struct Route { ClawEntry entry; uint32_t site; bool constructor; bool projectile; };
Route route(uint32_t function) {
    switch (function) {
    case 0x47e210: case 0x47e2d0: return {claw_level_two_raux_core_entry,0x48111e,function==0x47e2d0,false};
    case 0x453d30: case 0x453df0: return {claw_level_four_katherine_core_springboard_01_entry,0x455ba7,function==0x453df0,false};
    case 0x49fb30: case 0x49fbf0: return {claw_level_six_wolvington_core_01_entry,0x4a3cea,function==0x49fbf0,false};
    case 0x4041f0: case 0x404990: return {claw_level_twelve_aquatis_core_01_entry,0x40508e,function==0x404990,false};
    case 0x4459d0: case 0x445ef0: return {claw_level_eight_gabriel_bomb_01_entry,0x4474f1,function==0x445ef0,false};
    case 0x4a0cf0: return {claw_level_six_wolvington_states_01_entry,0x4a4941,false,true};
    case 0x480c40: return {claw_level_thirteen_red_tail_attacks_01_entry,0x483521,false,true};
    default: return {nullptr,0,false,false};
    }
}
int damageOwned(uint32_t function) { auto selected = route(function); return selected.entry ? (selected.projectile ? 0 : 1) : -1; }
// Keep the original physical request and memory owner. Publish the reviewed
// projectile constant before the actual child logic initializer consumes it.
struct ProjectileScope {
    Run &run;
    uint32_t site;
    decltype(ClawHost::call) previous;
    ProjectileScope *parent;
    static thread_local ProjectileScope *active;
    static uint32_t call(void *user, const ClawCall *request) {
        auto *scope = active;
        if (!scope || !scope->previous) return 0;
        try {
            if (request->receiver == 0 && request->argumentCount == 1) {
                uint32_t actor = request->arguments[0];
                auto *bytes = scope->run.host.bytes(scope->run.host.user, actor, 0x108);
                if (bytes) {
                    uint32_t logic;
                    std::memcpy(&logic, bytes + 0x6c, 4);
                    auto *record = scope->run.host.bytes(scope->run.host.user, logic, 0x14);
                    uint32_t callback = 0;
                    if (record) std::memcpy(&callback, record + 0x10, 4);
                    if (callback == request->function)
                        scope->run.put(actor + 0x104, claw_v13_boss_damage(scope->site, scope->run.get(actor + 0x104), 0));
                }
            }
        } catch (claw::Failure &) { return 0; }
        auto *provider = scope;
        while (provider->previous == call && provider->parent) provider = provider->parent;
        return provider->previous(user, request);
    }
    ProjectileScope(Run &run, uint32_t site) : run(run),site(site),previous(run.host.call),parent(active) {
        active = this;
        run.host.call = call;
    }
    ~ProjectileScope() { run.host.call = previous; active = parent; }
};
thread_local ProjectileScope *ProjectileScope::active = nullptr;
uint32_t damageBody(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    auto selected = route(function);
    if (!claw_v13_lives_boss_enabled()) {
        uint32_t result = 0;
        if (!selected.entry(function, receiver, arguments, uint32_t(damageOwned(function)), &run.host, &result))
            run.fail(CLAW_FAULT_ABI, function);
        return result;
    }
    // Both callbacks and constructors receive the owning actor explicitly.
    // A fresh constructor has not installed its receiver +0x0c pointer yet.
    uint32_t actor = selected.projectile ? 0 : arguments[0];
    bool initializing = selected.constructor || (!selected.projectile && run.get(run.get(actor + 0x6c) + 0x1c) == 0);
    uint32_t supplied = initializing ? run.get(actor + 0x104) : 0;
    uint32_t result = 0;
    if (selected.projectile) {
        ProjectileScope scope(run, selected.site);
        if (!selected.entry(function, receiver, arguments, 0, &run.host, &result))
            run.fail(CLAW_FAULT_ABI, function);
    } else {
        if (!selected.entry(function, receiver, arguments, 1, &run.host, &result))
            run.fail(CLAW_FAULT_ABI, function);
        if (initializing) {
            uint32_t value = claw_v13_boss_damage(selected.site, supplied, 0);
            if (selected.site != 0x4474f1) {
                double scaled = double(claw::s32(value)) * double(run.getf(0x5262b0));
                value = std::isfinite(scaled) && scaled >= -2147483648.0 && scaled < 2147483648.0
                    ? uint32_t(int32_t(scaled)) : 0x80000000u;
            }
            run.put(actor + 0x104, value);
        }
    }
    return result;
}
}
CLAW_MODULE_ENTRY(claw_v13_player_startup_compat_entry, startupOwned, startupBody)
CLAW_MODULE_ENTRY(claw_v13_score_compat_entry, scoreOwned, scoreBody)
CLAW_MODULE_ENTRY(claw_v13_lives_boss_compat_entry, damageOwned, damageBody)
