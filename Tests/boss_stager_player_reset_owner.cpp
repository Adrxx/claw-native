// Native shared-heap composition checks. The reference comparison is the
// separately gated root family; this executable never executes guest code.
#include "BossStagerPlayerResetOwner.h"
#include <array>
#include <cassert>
#include <cstring>
#include <cstdio>
#include <map>
#include <vector>
namespace {
struct Heap {
    std::map<uint32_t, std::vector<uint32_t>> blocks;
    uint32_t next = 0x11000000, player = 0, input = 0, ani = 0;
    bool found = false, mutate = false;
    unsigned resources = 0, allocations = 0, fallback = 0;
    uint32_t allocated = 0;
    uint32_t add(uint32_t count) {
        const auto token = next;
        next += count * 4 + 64;
        blocks[token] = std::vector<uint32_t>(count, 0xa5a5a5a5);
        return token;
    }
    uint32_t *lookup(uint32_t token, uint32_t words) {
        auto it = blocks.upper_bound(token);
        if (it == blocks.begin())
            return nullptr;
        --it;
        const uint64_t offset = uint64_t(token) - it->first;
        if (offset % 4 || offset + uint64_t(words) * 4 > it->second.size() * 4)
            return nullptr;
        return it->second.data() + offset / 4;
    }
    uint32_t &word(uint32_t token) {
        auto *p = lookup(token, 1);
        if (!p) std::fprintf(stderr, "missing token %x\n", token);
        assert(p);
        return *p;
    }
};
uint8_t *memory(void *user, uint32_t token, uint32_t size) {
    if (size % 4)
        return nullptr;
    return reinterpret_cast<uint8_t *>(static_cast<Heap *>(user)->lookup(token, size / 4));
}
uint32_t *lookup(void *user, uint32_t token, uint32_t words) {
    return static_cast<Heap *>(user)->lookup(token, words);
}
uint32_t allocate(void *user, uint32_t bytes) {
    auto &h = *static_cast<Heap *>(user);
    ++h.allocations;
    if (h.mutate) {
        const auto primary = h.word(h.player + 0x6c);
        h.word(h.word(primary + 0x14)) = 0;
    }
    h.allocated = h.add((bytes + 3) / 4);
    return h.allocated;
}
uint32_t service(void *user, ClawSceneActorCall call) {
    auto &h = *static_cast<Heap *>(user);
    // This is a native resource provider, not a gameplay callback. ANI records
    // themselves are consumed by the existing animation owner over shared spans.
    assert(call.function == 0x4f6286 && call.argumentCount == 1);
    assert(call.arguments[0] == 0x5246d0);
    ++h.resources;
    return h.found ? h.ani : 0;
}
uint32_t forbidden(void *user, const ClawCall *) {
    ++static_cast<Heap *>(user)->fallback;
    assert(false && "no guest or generic gameplay fallback is elected");
    return 0;
}
void profile(uint32_t facing, uint32_t capacity, uint32_t restore, bool found, bool mutate) {
    Heap h;
    h.blocks[0x530000] = std::vector<uint32_t>(0x10000 / 4, 0xdeadbeef);
    h.player = h.add(128);
    const auto primary = h.add(8), priv = h.add(78), input = h.add(4), world = h.add(12), registry = h.add(12);
    h.input = input;
    h.ani = h.add(8);
    const auto table = h.add(1), record = h.add(12);
    std::memset(h.lookup(record, 12), 0, 48);
    h.word(h.player + 0x170) = 0;
    h.word(h.ani + 12) = table;
    h.word(h.ani + 16) = 1;
    h.word(table) = record;
    h.word(record + 28) = 0x10000;
    h.word(h.player + 0x6c) = primary;
    h.word(h.player + 0xc) = world;
    h.word(world + 0x2c) = registry;
    h.word(h.player + 0x18c) = h.player;
    h.word(primary + 0x14) = priv;
    h.word(primary + 0x1c) = 7;
    h.word(priv) = facing;
    h.word(priv + 4) = restore;
    h.word(priv + 0x124) = h.ani;
    h.word(priv + 0x12c) = 0;
    h.word(0x537e88) = h.player;
    h.word(0x537204) = input;
    uint32_t enemy = 0, bits = 0;
    if (capacity != 0xffffffff) {
        const auto carried = h.add(28), cp = h.add(8);
        enemy = h.add(194);
        h.word(priv + 0x12c) = carried;
        h.word(carried + 0x6c) = cp;
        h.word(cp + 0x18) = enemy;
        h.word(enemy + 0x20) = 1;
        h.word(enemy + 0x2fc) = capacity;
        bits = capacity > 32 ? h.add(2) : enemy + 0x300;
        h.word(bits) = 0x24680000;
        if (capacity > 32)
            h.word(enemy + 0x300) = bits;
    }
    h.found = found;
    h.mutate = mutate;
    ClawHost host{};
    host.user = &h;
    host.bytes = memory;
    host.call = forbidden;
    ClawSceneActorHost scene{&h, lookup, allocate, nullptr, service, nullptr};
    ClawActorAnimationGlobals animation{};
    uint32_t fault = 0;
    const auto completed = claw_boss_stager_player_reset_source(&host, scene, &animation, &fault);
    if (!completed) std::fprintf(stderr, "profile facing%u capacity%u restore%u found%u fault%u resources%u\n", facing, capacity, restore, found, fault, h.resources);
    assert(completed == 1);
    assert(!fault && !host.fault && !h.fallback);
    assert(h.word(primary + 0x1c) == 0x1391);
    assert(h.word(input + 12) == (0xa5a5a5a5 & 0xfcffffff));
    assert(h.word(priv) == 1 && h.word(priv + 4) == 0 && h.word(priv + 0x12c) == 0);
    assert(h.word(priv + 0xfc) == 650 && h.word(priv + 0x114) == 1500);
    assert(h.word(priv + 0x120) == 15000 && h.word(priv + 0x118) == 0);
    assert(h.word(h.player + 0x1b0) == 0x3f800000);
    assert(h.word(h.player + 0x104) == 0 && h.word(h.player + 0x148) == 0 && h.word(h.player + 0x14c) == 0);
    assert(h.word(h.player + 0x118) == uint32_t(-16) && h.word(h.player + 0x120) == 16);
    const bool mirrored = !facing || (capacity == 0 && mutate);
    assert(h.word(h.player + 0x128) == uint32_t(-22));
    assert(h.word(h.player + 0x130) == 15);
    assert(h.word(h.player + 0x138) == (mirrored ? 0x5a5a5a5b : 0xa5a5a5a5));
    for (uint32_t i = 0; i < 6; ++i)
        assert(h.word(0x534e60 + 4 * i) == 0);
    if (enemy) {
        assert(h.word(enemy + 0x14) == 0x4207a0);
        if (!capacity) {
            // Original growth to32 stores the allocation in the inline slot;
            // SetBit then ORs that slot, preserving the original odd pointer.
            assert(h.word(enemy + 0x300) == (h.allocated | 1));
            assert(h.word(h.allocated) == 0x24680000);
        } else {
            assert(h.word(bits) == 0x24680001);
        }
    }
    assert(h.allocations == (capacity == 0 ? 1u : 0u));
    assert(h.resources == 1);
    // Reset is idempotent: no second resource resolution or allocation.
    assert(claw_boss_stager_player_reset_source(&host, scene, &animation, &fault) == 1);
    assert(h.resources == 1);
    h.word(0x537e88) = 0;
    assert(claw_boss_stager_player_reset_source(&host, scene, &animation, &fault) == 1);
    assert(h.resources == 1);
}
}
extern "C" uint32_t claw_boss_stager_player_reset_owner_check() {
    // Early returns must not demand an input or private-state mapping.
    Heap early;
    early.blocks[0x537e88] = {0};
    ClawHost host{};
    host.user = &early;
    host.bytes = memory;
    host.call = forbidden;
    ClawSceneActorHost scene{&early, lookup, allocate, nullptr, service, nullptr};
    ClawActorAnimationGlobals animation{};
    uint32_t fault = 0;
    assert(claw_boss_stager_player_reset_source(&host, scene, &animation, &fault) == 1);
    const auto player = early.add(28), primary = early.add(8);
    early.word(0x537e88) = player;
    early.word(player + 0x6c) = primary;
    early.word(primary + 0x1c) = 0x1391;
    assert(claw_boss_stager_player_reset_source(&host, scene, &animation, &fault) == 1);
    early.word(player + 0x6c) = 0x12340000;
    assert(claw_boss_stager_player_reset_source(&host, scene, &animation, &fault) == 0);
    assert(fault && !early.fallback);
    unsigned count = 0;
    for (auto facing : {0u, 1u})
        for (auto capacity : {0xffffffffu, 0u, 1u, 32u, 33u})
            for (auto restore : {0u, 1u})
                for (auto found : {false, true}) {
                    profile(facing, capacity, restore, found, capacity == 0);
                    ++count;
                }
    return count;
}

int main() {
    const auto count = claw_boss_stager_player_reset_owner_check();
    std::printf("{\"command\":\"boss-stager-player-reset-owner\",\"profiles\":%u,\"root_invocations\":%u,\"guest_calls\":0,\"status\":\"pass\"}\n", count, count * 3 + 3);
}
