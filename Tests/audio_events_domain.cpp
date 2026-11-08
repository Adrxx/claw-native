#include "ClawRuntime.h"
#include <cstdio>

extern "C" uint32_t claw_audio_events_entry(uint32_t, uint32_t, const uint32_t *,
                                            uint32_t, ClawHost *, uint32_t *);

// Invalid words have no claimed original equivalent. Exercise only the native
// safety boundary; all 101 permitted values are compared by the family gate.
int main() {
    const uint32_t invalid[] = {0xffffffffu, 101u, 0x80000000u, 0x7fffffffu};
    for (uint32_t word : invalid) {
        ClawHost host{};
        uint32_t result = 0xa56c3e91u;
        const uint32_t completed = claw_audio_events_entry(0x4b3b90, 0, &word, 1, &host, &result);
        if (completed || host.fault != CLAW_FAULT_ABI || host.faultAddress != 0x4b3b90 || result != 0xa56c3e91u) {
            std::fprintf(stderr, "volume domain rejection failed for %08x\n", word);
            return 1;
        }
    }
    std::puts("{\"status\":\"pass\",\"rejected_words\":4,\"original_equivalence\":false}");
}
