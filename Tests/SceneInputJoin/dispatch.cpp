// Focused comparison host: actual canonical owners share memory, stack and fault.
// This is a test composition, not a shipping app owner election.
#include "ClawRuntime.h"

extern "C" uint32_t claw_scene_camera_canonical_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);
extern "C" uint32_t claw_application_input_configuration_entry(uint32_t, uint32_t, const uint32_t *, uint32_t, ClawHost *, uint32_t *);

namespace {
bool input(uint32_t f) {
    switch (f) {
    case 0x430d30: case 0x430d80: case 0x430ec0: case 0x431300:
    case 0x4b3430: case 0x4b3490: case 0x4b3ab0: return true;
    default: return false;
    }
}
struct Graph {
    ClawHost *host;
    uint32_t (*outside)(void *, const ClawCall *);
    bool missing;
};
thread_local Graph *active = nullptr;

uint32_t fault(ClawHost *host, uint32_t code, uint32_t address) {
    if (!host->fault) {
        host->fault = code;
        host->faultAddress = address;
    }
    return 0;
}

uint32_t route(void *user, const ClawCall *call) {
    auto &graph = *active;
    auto *host = graph.host;
    if (!input(call->function)) return graph.outside(user, call);
    if (graph.missing) return fault(host, CLAW_FAULT_UNIMPLEMENTED, call->function);
    const auto parent = host->entryStackPointer ? host->entryStackPointer : CLAW_STACK_TOP;
    if (!call->stackPointer || call->stackPointer >= parent ||
        call->stackPointer < CLAW_STACK_BASE || (call->stackPointer & 3) ||
        call->receiver2 || call->x87ArgumentCount || call->compilerContext ||
        call->sourceContext || call->sourceReturnPC || call->sourceTransferVersion)
        return fault(host, CLAW_FAULT_ABI, call->function);
    const auto saved = host->entryStackPointer;
    host->entryStackPointer = call->stackPointer;
    uint32_t value = 0;
    const auto handled = claw_application_input_configuration_entry(
        call->function, call->receiver, call->arguments, call->argumentCount, host, &value);
    host->entryStackPointer = saved;
    if (!handled && !host->fault) fault(host, CLAW_FAULT_UNIMPLEMENTED, call->function);
    return value;
}

uint32_t enter(uint32_t function, uint32_t receiver, const uint32_t *arguments,
               uint32_t count, ClawHost *host, uint32_t *result, bool missing) {
    if (!host || !result || host->fault) return 0;
    if (active || !host->call) return fault(host, CLAW_FAULT_ABI, function);
    Graph graph{host, host->call, missing};
    auto *savedBudget = host->remainingOperations;
    uint64_t budget = host->maximumOperations ? host->maximumOperations : 200000000;
    if (!savedBudget) host->remainingOperations = &budget;
    active = &graph;
    host->call = route;
    uint32_t handled = 0;
    if (input(function)) {
        if (missing) fault(host, CLAW_FAULT_UNIMPLEMENTED, function);
        else handled = claw_application_input_configuration_entry(function, receiver, arguments, count, host, result);
    } else {
        handled = claw_scene_camera_canonical_entry(function, receiver, arguments, count, host, result);
    }
    host->call = graph.outside;
    host->remainingOperations = savedBudget;
    active = nullptr;
    if (!handled && !host->fault) fault(host, CLAW_FAULT_UNIMPLEMENTED, function);
    return host->fault ? 0 : handled;
}
}

extern "C" uint32_t claw_scene_input_join_entry(uint32_t f, uint32_t r, const uint32_t *a,
                                               uint32_t n, ClawHost *h, uint32_t *v) {
    return enter(f, r, a, n, h, v, false);
}
extern "C" uint32_t claw_scene_input_join_missing_entry(uint32_t f, uint32_t r, const uint32_t *a,
                                                       uint32_t n, ClawHost *h, uint32_t *v) {
    return enter(f, r, a, n, h, v, true);
}
