// Focused adapter for the existing portable contact binder, not an app election.
#include "ActorResourceBindings.h"
#include "ClawRuntime.hpp"
#include "LogicRegistry.h"

namespace {
struct Binding {
    claw::Run &run;
    uint32_t actor;
    uint32_t name;
    uint32_t contact = 0;
};
uint32_t dependency(ClawActorResourceBindings *state, ClawActorBindingContext *context,
                    const ClawActorBindingCall *event, void *user) {
    auto &binding = *static_cast<Binding *>(user);
    auto &run = binding.run;
    if (event->function == 0x4f6286) {
        uint32_t out = run.automatic(-4);
        run.put(out, 0);
        uint32_t world = run.get(binding.actor + 0x0c);
        uint32_t registry = run.get(world + 0x14);
        run.call(0x4f6286, registry + 0x10, {binding.name, out});
        uint32_t metadata = run.get(out);
        if (metadata) {
            const auto *entry = claw_logic_registry_find(event->name);
            if (!entry || run.get(metadata + 0x10) != entry->callback)
                run.fail(CLAW_FAULT_ABI, metadata);
            context->metadataCallback = entry->callback;
            context->metadataFlags = entry->flags;
        }
        return metadata;
    }
    if (event->function == 0x4f63ec) {
        binding.contact = run.call(0x4f63ec, 0, {event->argument});
        if (binding.contact) {
            for (uint32_t i = 0; i < 93; ++i)
                state->secondary[i] = run.get(binding.contact + i * 4);
        }
        return binding.contact;
    }
    if (event->function == 0x4f6428)
        return run.call(0x4f6428, 0, {event->argument});
    run.fail(CLAW_FAULT_UNIMPLEMENTED, event->function);
}
int owned(uint32_t function) { return function == 0x4c8060 ? 1 : -1; }
uint32_t body(claw::Run &run, uint32_t, uint32_t receiver, const uint32_t *arguments) {
    ClawActorResourceBindings state{};
    for (uint32_t i = 0; i < 128; ++i)
        state.actor[i] = run.get(receiver + i * 4);
    Binding binding{run, receiver, arguments[0], state.actor[0x78 / 4]};
    if (binding.contact) {
        for (uint32_t i = 0; i < 93; ++i)
            state.secondary[i] = run.get(binding.contact + i * 4);
    }
    char name[64]{};
    for (uint32_t i = 0; i < sizeof(name) - 1; ++i) {
        name[i] = char(run.get8(arguments[0] + i));
        if (!name[i])
            break;
    }
    ClawActorBindingContext context{};
    uint32_t result = claw_actor_bind_contact_logic_name(&state, &context, name, dependency, &binding);
    for (uint32_t i = 0; i < 128; ++i)
        run.put(receiver + i * 4, state.actor[i]);
    if (binding.contact) {
        for (uint32_t i = 0; i < 93; ++i)
            run.put(binding.contact + i * 4, state.secondary[i]);
    }
    return result;
}
}
CLAW_MODULE_ENTRY(claw_boss_stager_binding_test_entry, owned, body)
