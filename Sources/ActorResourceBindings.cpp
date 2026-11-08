#include "ActorResourceBindings.h"
#include <initializer_list>

namespace {
uint32_t call(ClawActorBindingDependency dependency, void *user, ClawActorResourceBindings *state,
              ClawActorBindingContext *context, uint32_t function, uint32_t receiver, uint32_t argument = 0,
              const char *name = nullptr) {
    if (!dependency)
        return 0;
    const ClawActorBindingCall event{function, receiver, argument, name};
    return dependency(state, context, &event, user);
}
uint32_t image(ClawActorResourceBindings *state, ClawActorBindingContext *c, const char *name, int32_t index,
               bool useDefault, ClawActorBindingDependency dependency, void *user) {
    if (!state || !c || !name)
        return 0;
    c->image.token = call(dependency, user, state, c, 0x4f6286, c->imageRegistryToken, 0, name);
    uint32_t selected = 0;
    if (c->image.token) {
        if (useDefault)
            index = c->image.minimum;
        if (index >= c->image.minimum && index <= c->image.maximum) {
            const int64_t offset = int64_t(index) - c->image.firstImageIndex;
            if (!c->image.images || offset < 0 || uint64_t(offset) >= c->image.imageCount)
                return 0;
            selected = c->image.images[offset];
        }
    }
    state->actor[0x170 / 4] = c->image.token;
    if (c->image.token) {
        state->actor[0x16c / 4] = uint32_t(index);
        state->actor[0x174 / 4] = selected;
    }
    return 1;
}
} // namespace
uint32_t claw_actor_bind_indexed_image(ClawActorResourceBindings *state, ClawActorBindingContext *c, const char *name,
                                       int32_t index, ClawActorBindingDependency dependency, void *user) {
    return image(state, c, name, index, false, dependency, user);
}
uint32_t claw_actor_bind_default_image(ClawActorResourceBindings *state, ClawActorBindingContext *c, const char *name,
                                       ClawActorBindingDependency dependency, void *user) {
    return image(state, c, name, 0, true, dependency, user);
}
void claw_actor_reset_secondary_logic(ClawActorResourceBindings *state, ClawActorBindingContext *c,
                                      ClawActorBindingDependency dependency, void *user) {
    if (!state || !c)
        return;
    auto *s = state->secondary;
    s[0x10 / 4] = 0;
    if (s[0x14 / 4]) {
        call(dependency, user, state, c, 0x4f6428, 0, s[0x14 / 4]);
        s[0x14 / 4] = 0;
    }
    if (s[0x18 / 4]) {
        call(dependency, user, state, c, c->associatedDestructor, s[0x18 / 4], 1);
        s[0x18 / 4] = 0;
    }
}
namespace {
uint32_t bindLogic(ClawActorResourceBindings *state, ClawActorBindingContext *c, ClawActorBindingDependency dependency,
                   void *user, size_t actorOffset) {
    if (!state || !c || !c->metadataToken)
        return 0;
    auto *a = state->actor;
    auto *s = state->secondary;
    if (a[actorOffset / 4])
        claw_actor_reset_secondary_logic(state, c, dependency, user);
    else {
        const uint32_t token = call(dependency, user, state, c, 0x4f63ec, 0, 0x174);
        if (token) {
            s[0] = 0x513740;
            s[1] = a[1];
            s[2] = 0;
            s[3] = a[3];
            s[4] = s[5] = s[6] = s[7] = 0;
        }
        a[actorOffset / 4] = token;
    }
    if (!a[actorOffset / 4])
        return 0;
    // Complete original4c8160 with explicit flags0, not metadata flags.
    if (!c->metadataCallback)
        return 0;
    s[0x10 / 4] = c->metadataCallback;
    for (size_t offset : {0x14u, 0x18u, 0x20u, 0x24u, 0x2cu, 0x34u, 0x30u, 0x38u, 0x168u, 0x16cu, 0x28u})
        s[offset / 4] = 0;
    s[2] = 0;
    return 1;
}
} // namespace
uint32_t claw_actor_bind_secondary_logic(ClawActorResourceBindings *state, ClawActorBindingContext *c,
                                         ClawActorBindingDependency dependency, void *user) {
    return bindLogic(state, c, dependency, user, 0x70);
}
uint32_t claw_actor_bind_contact_logic(ClawActorResourceBindings *state, ClawActorBindingContext *c,
                                       ClawActorBindingDependency dependency, void *user) {
    return bindLogic(state, c, dependency, user, 0x78);
}
uint32_t claw_actor_bind_secondary_logic_name(ClawActorResourceBindings *state, ClawActorBindingContext *c,
                                              const char *name, ClawActorBindingDependency dependency, void *user) {
    if (!state || !c || !name)
        return 0;
    c->metadataToken = call(dependency, user, state, c, 0x4f6286, c->logicRegistryToken, 0, name);
    return claw_actor_bind_secondary_logic(state, c, dependency, user);
}
uint32_t claw_actor_bind_contact_logic_name(ClawActorResourceBindings *state, ClawActorBindingContext *c,
                                            const char *name, ClawActorBindingDependency dependency, void *user) {
    if (!state || !c || !name)
        return 0;
    c->metadataToken = call(dependency, user, state, c, 0x4f6286, c->logicRegistryToken, 0, name);
    return claw_actor_bind_contact_logic(state, c, dependency, user);
}
