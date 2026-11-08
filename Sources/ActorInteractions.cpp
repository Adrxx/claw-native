#include "ActorInteractions.h"
#include <limits>

namespace {
int32_t coordinate(uint32_t offset, uint32_t position) {
    return int32_t(offset + position);
}
void invoke(ClawInteractionActor *actors, size_t count, size_t receiver, size_t peer, bool contact,
            ClawActorInteractionDependency dependency, void *user) {
    auto &r = actors[receiver];
    const uint32_t logic = r.actor[(contact ? 0x78 : 0x70) / 4];
    if (!logic)
        return;
    r.actor[(contact ? 0x7c : 0x74) / 4] = actors[peer].token;
    const uint32_t function = (contact ? r.contact : r.secondary)[0x10 / 4];
    const ClawActorInteractionCall event{function, r.token, actors[peer].token, logic, contact ? 1u : 0u};
    if (dependency)
        dependency(actors, count, &event, user);
}
void hurt(ClawInteractionActor *actors, size_t count, size_t defender, size_t attacker,
          ClawActorInteractionDependency dependency, void *user) {
    auto &d = actors[defender];
    if (d.actor[2] & 8) {
        d.actor[0x10c / 4] -= actors[attacker].actor[0x104 / 4];
        if (int32_t(d.actor[0x10c / 4]) <= 0)
            d.primary[0x1c / 4] = 28;
    } else
        invoke(actors, count, defender, attacker, false, dependency, user);
}
} // namespace

uint32_t claw_actor_interaction_overlap(const ClawInteractionActor *defender, const ClawInteractionActor *attacker) {
    if (!defender || !attacker)
        return 0;
    const auto *d = defender->actor;
    const auto *a = attacker->actor;
    if (a[0x138 / 4] == 0x80000000 || d[0x128 / 4] == 0x80000000)
        return 0;
    const int32_t dl = coordinate(d[0x128 / 4], d[0x4c / 4]), dr = coordinate(d[0x130 / 4], d[0x4c / 4]);
    const int32_t dt = coordinate(d[0x12c / 4], d[0x50 / 4]), db = coordinate(d[0x134 / 4], d[0x50 / 4]);
    const int32_t al = coordinate(a[0x138 / 4], a[0x4c / 4]), ar = coordinate(a[0x140 / 4], a[0x4c / 4]);
    const int32_t at = coordinate(a[0x13c / 4], a[0x50 / 4]), ab = coordinate(a[0x144 / 4], a[0x50 / 4]);
    return dl <= ar && dr >= al && dt <= ab && db >= at;
}

uint32_t claw_actor_interaction_hurt(ClawInteractionActor *actors, size_t count, uint32_t defender, uint32_t attacker,
                                     ClawActorInteractionDependency dependency, void *user) {
    if (!actors || defender >= count || attacker >= count)
        return 0;
    hurt(actors, count, defender, attacker, dependency, user);
    return 1;
}

uint32_t claw_actor_interactions(ClawInteractionActor *actors, size_t count, ClawActorInteractionDependency dependency,
                                 void *user) {
    if ((!actors && count) || count > std::numeric_limits<uint32_t>::max())
        return 0;
    for (size_t first = 0; first < count; ++first) {
        // Original tests outer actor flag1 once, not before every inner pair.
        if (actors[first].actor[2] & 1)
            continue;
        for (size_t second = first + 1; second < count; ++second) {
            auto *a = actors[first].actor;
            auto *b = actors[second].actor;
            const uint32_t flagsB = b[2];
            if (flagsB & 1 || ((flagsB ^ a[2]) & 0x40000))
                continue;
            if (!(a[2] & 4) && !(flagsB & 0x80)) {
                // These masks are cached across the contact callback exactly as
                // in the original inline forward-direction branch.
                const uint32_t hitMask = a[0xd4 / 4] & b[0xd0 / 4];
                const uint32_t contactMask = a[0xd0 / 4] & b[0xd8 / 4];
                if ((hitMask || contactMask) && claw_actor_interaction_overlap(&actors[first], &actors[second])) {
                    if (contactMask)
                        invoke(actors, count, second, first, true, dependency, user);
                    if (hitMask)
                        hurt(actors, count, first, second, dependency, user);
                }
            }
            // Reverse direction rereads flags and masks after forward callbacks;
            // original flag1/space checks are not repeated at this point.
            if (!(b[2] & 4) && !(a[2] & 0x80)) {
                const uint32_t hitMask = a[0xd0 / 4] & b[0xd4 / 4];
                const uint32_t contactMask = a[0xd8 / 4] & b[0xd0 / 4];
                if ((hitMask || contactMask) && claw_actor_interaction_overlap(&actors[second], &actors[first])) {
                    if (contactMask)
                        invoke(actors, count, first, second, true, dependency, user);
                    if (hitMask)
                        hurt(actors, count, second, first, dependency, user);
                }
            }
        }
    }
    return 1;
}
