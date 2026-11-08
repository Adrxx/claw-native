#include "ClawGuestTransfer.h"
#include <atomic>
#include <cstring>
#include <mutex>
#include <thread>
#include <unordered_set>
#include <vector>

namespace {
struct Lease {
    const ClawCall *address;
    ClawCall call;
    ClawSourceContext cpu;
    ClawSourceContext *parent;
    ClawSourceContext parentCPU;
};
std::mutex registryMutex;
std::unordered_set<ClawGuestSession *> registry;
std::atomic<uint64_t> generations{1};
}
struct ClawGuestSession {
    ClawHost *host;
    ClawGuestConfig config;
    std::thread::id thread = std::this_thread::get_id();
    uint64_t generation;
    bool active = false, used = false, pending = false, capturing = false;
    ClawHost rootScope{}; // Bound at graph entry, before any callback can replace borrowed pointers.
    ClawGuestEHContract ehContract{};
    ClawGuestEHEntry ehEntry = nullptr;
    ClawGuestEHInvocation invocation{};
    ClawGuestEHInvocation invocationWitness{};
    bool ehActive = false, ehPrepared = false;
    uint64_t lastInvocation = 0;
    std::vector<Lease> leases;
    ClawGuestOutcome outcome{};
};
namespace {
bool owned(ClawGuestSession *s, ClawHost *h) {
    std::lock_guard<std::mutex> lock(registryMutex);
    return registry.count(s) && s->host == h && s->thread == std::this_thread::get_id();
}
uint32_t fault(ClawHost *h, uint32_t kind = CLAW_FAULT_ABI) {
    if (h && !h->fault) h->fault = kind;
    return 0;
}
bool inText(const ClawGuestConfig &c, uint32_t pc) { return pc >= c.textBegin && pc < c.textEnd; }
bool borrowedScope(const ClawHost *h, const ClawHost &before) {
    return h->user == before.user && h->bytes == before.bytes &&
        h->call == before.call && h->maximumOperations == before.maximumOperations &&
        h->entryStackPointer == before.entryStackPointer &&
        h->remainingOperations == before.remainingOperations &&
        h->sourceContext == before.sourceContext && h->compilerContext == before.compilerContext &&
        h->sourceReturnPC == before.sourceReturnPC;
}
bool rootScope(const ClawGuestSession *s, const ClawHost *h) {
    return h->guestSession == s && borrowedScope(h, s->rootScope);
}
bool ehWitness(const ClawGuestSession *s) {
    if (!s->ehActive) return true;
    const auto &cpu = s->invocation.cpu;
    const auto &before = s->invocationWitness.cpu;
    return !std::memcmp(&s->invocation, &s->invocationWitness, offsetof(ClawGuestEHInvocation, cpu)) &&
        cpu.size == before.size && cpu.version == before.version && cpu.inputMask == before.inputMask &&
        cpu.outputMask == before.outputMask && cpu.preserveMask == before.preserveMask &&
        cpu.reserved0 == before.reserved0 && cpu.reserved1 == before.reserved1;
}
bool sameLease(const Lease &a, const ClawCall *call) {
    // Compare the pointer-containing call before dereferencing its retained context.
    return a.address == call && !std::memcmp(call, &a.call, sizeof(*call)) &&
        !std::memcmp(a.call.sourceContext, &a.cpu, sizeof(a.cpu));
}
bool sameParent(const Lease &a, const ClawHost *h) {
    return h->sourceContext == a.parent &&
        (!a.parent || !std::memcmp(a.parent, &a.parentCPU, sizeof(a.parentCPU)));
}
bool stackSpan(uint32_t a, uint32_t n) {
    return !(a & 3) && a >= CLAW_STACK_BASE && uint64_t(a) + n <= CLAW_STACK_END;
}
void restoreScope(ClawHost *h, const ClawHost &before) {
    h->user = before.user; h->bytes = before.bytes; h->call = before.call;
    h->maximumOperations = before.maximumOperations;
    h->entryStackPointer = before.entryStackPointer; h->remainingOperations = before.remainingOperations;
    h->compilerContext = before.compilerContext; h->sourceContext = before.sourceContext;
    h->sourceReturnPC = before.sourceReturnPC; h->guestSession = before.guestSession;
}
bool physical(const ClawGuestConfig &c, const ClawGuestPhysicalEvent &e) {
    const auto &v = e.cpu;
    return e.size == sizeof(e) && e.version == 1 && e.kind == CLAW_GUEST_RAISE &&
        e.slot == c.raiseSlot && e.stub == c.raiseStub && e.flags == 1 && e.count <= 15 &&
        inText(c, e.returnPC) && v.size == sizeof(v) && v.version == 1 &&
        v.inputMask == CLAW_CONTEXT_ALL && v.outputMask == CLAW_CONTEXT_ALL &&
        !v.preserveMask && !v.reserved0 && !v.reserved1 && v.eip == e.stub &&
        stackSpan(v.esp, 20) && (v.eflags & 2) && !(v.eflags & ~0x8d7u) &&
        (v.fsHead == 0xffffffffu || (v.fsHead >= v.esp && stackSpan(v.fsHead, 12)));
}
}
extern "C" {
ClawGuestSession *claw_guest_create(ClawHost *h, const ClawGuestConfig *c) noexcept {
    if (!h || !c || c->size != sizeof(*c) || c->version != 1 || c->textBegin >= c->textEnd ||
        !inText(*c, c->rootFunction) || !c->raiseSlot || !c->raiseStub || h->guestSession) return nullptr;
    try {
        auto s = new ClawGuestSession{};
        s->host = h; s->config = *c; s->generation = generations++;
        try { std::lock_guard<std::mutex> lock(registryMutex); registry.insert(s); }
        catch (...) { delete s; throw; }
        return s;
    } catch (...) { fault(h, CLAW_FAULT_HOST); return nullptr; }
}
uint64_t claw_guest_generation(ClawGuestSession *s, ClawHost *h) noexcept {
    return owned(s, h) ? s->generation : 0;
}
uint32_t claw_guest_destroy(ClawGuestSession *s, ClawHost *h, uint64_t generation) noexcept {
    if (!owned(s, h) || s->generation != generation || s->active || s->capturing) return 0;
    { std::lock_guard<std::mutex> lock(registryMutex); registry.erase(s); }
    delete s;
    return 1;
}
uint32_t claw_guest_status(ClawHost *h) noexcept {
    if (!h) return 2;
    if (!h->guestSession) return 0;
    auto s = h->guestSession;
    if (!owned(s, h) || !s->active || s->capturing || !rootScope(s, h) || !ehWitness(s)) { fault(h); return 2; }
    return s->pending ? 1 : 0;
}
uint32_t claw_guest_lease_enter(ClawHost *h, const ClawCall *call) noexcept {
    if (!h || !h->guestSession || h->fault || claw_guest_status(h)) return fault(h);
    auto s = h->guestSession;
    if (!call || !call->sourceContext || call->compilerContext || call->x87ArgumentCount ||
        call->sourceTransferVersion || call->sourceTransferKind || call->sourceTransferSite ||
        call->sourceCallerFunction || call->sourceDisposition ||
        call->argumentCount > CLAW_CALL_ARGUMENT_CAPACITY || !inText(s->config, call->function)) return fault(h);
    try {
        s->leases.push_back({call, *call, *call->sourceContext, h->sourceContext,
                            h->sourceContext ? *h->sourceContext : ClawSourceContext{}});
        return 1;
    }
    catch (...) { return fault(h, CLAW_FAULT_HOST); }
}
void claw_guest_lease_leave(ClawHost *h, const ClawCall *call) noexcept {
    if (!h || !owned(h->guestSession, h)) { fault(h); return; }
    auto s = h->guestSession;
    if (s->leases.empty() || s->leases.back().address != call) { fault(h); return; }
    s->leases.pop_back();
}
uint32_t claw_guest_capture_original(ClawGuestSession *s, ClawHost *h, uint64_t generation,
    const ClawCall *call, const ClawGuestPhysicalEvent *event, uint64_t payload) noexcept {
    try {
        if (!owned(s, h) || s->generation != generation || !s->active || s->pending || s->capturing ||
            !rootScope(s, h) || !ehWitness(s) || h->fault || s->leases.empty() || !event || !payload) return fault(h);
        const auto lease = s->leases.back();
        if (!sameLease(lease, call) || !sameParent(lease, h) || !physical(s->config, *event)) return fault(h);
        const auto retainedEvent = *event;
        const auto retainedHost = *h;
        const auto retainedRootCPU = h->sourceContext ? *h->sourceContext : ClawSourceContext{};
        const auto retainedCompilerCPU = h->compilerContext ? *h->compilerContext : ClawCompilerContext{};
        const auto retainedDepth = s->leases.size();
        s->capturing = true;
        auto bytes = h->bytes ? h->bytes(h->user, CLAW_STACK_BASE, CLAW_STACK_END - CLAW_STACK_BASE) : nullptr;
        // Reject pointer/authority mutations before touching retained borrowed objects.
        const bool authority = owned(s, h) && s->generation == generation && s->active && s->capturing &&
            !s->pending && h->guestSession == s && !h->fault && s->leases.size() == retainedDepth &&
            !s->leases.empty() && s->leases.back().address == lease.address &&
            !std::memcmp(h, &retainedHost, sizeof(*h));
        const bool unchanged = authority && ehWitness(s) && sameLease(lease, call) && sameParent(lease, h) &&
            !std::memcmp(event, &retainedEvent, sizeof(*event)) &&
            (!retainedHost.sourceContext ||
             !std::memcmp(retainedHost.sourceContext, &retainedRootCPU, sizeof(retainedRootCPU))) &&
            (!retainedHost.compilerContext ||
             !std::memcmp(retainedHost.compilerContext, &retainedCompilerCPU, sizeof(retainedCompilerCPU)));
        s->capturing = false;
        if (!bytes || !unchanged || !physical(s->config, retainedEvent)) return fault(h);
        auto word = [&](uint32_t a) { uint32_t v; std::memcpy(&v, bytes + a - CLAW_STACK_BASE, 4); return v; };
        const auto &e = retainedEvent;
        const auto sp = e.cpu.esp;
        if (word(sp) != e.returnPC || word(sp + 4) != e.code || word(sp + 8) != e.flags ||
            word(sp + 12) != e.count) return fault(h);
        const auto info = word(sp + 16);
        if (e.count && (info < sp || !stackSpan(info, e.count * 4))) return fault(h);
        for (uint32_t i = 0; i < e.count; ++i)
            if (word(info + i * 4) != e.information[i]) return fault(h);
        s->outcome = {sizeof(ClawGuestOutcome), 1, CLAW_GUEST_TRANSFER, 0, generation, payload, e};
        s->pending = true;
        return 1;
    } catch (...) { if (owned(s, h)) s->capturing = false; return fault(h, CLAW_FAULT_HOST); }
}
uint32_t claw_guest_run(ClawGuestSession *s, ClawHost *h, uint64_t generation, ClawEntry entry,
    uint32_t function, uint32_t receiver, const uint32_t *args, uint32_t count,
    uint32_t *result, ClawGuestOutcome *out) noexcept {
    if (!owned(s, h) || s->generation != generation || s->active || s->used || s->ehPrepared || h->guestSession ||
        h->fault || !entry || !result || !out || function != s->config.rootFunction) return fault(h);
    const auto retainedHost = *h;
    s->rootScope = retainedHost;
    s->active = s->used = true;
    h->guestSession = s;
    uint32_t kind = CLAW_GUEST_FAULT;
    try {
        auto completed = entry(function, receiver, args, count, h, result);
        if (h->guestSession != s || h->user != retainedHost.user || h->bytes != retainedHost.bytes ||
            h->call != retainedHost.call || h->sourceContext != retainedHost.sourceContext ||
            h->compilerContext != retainedHost.compilerContext || h->sourceReturnPC != retainedHost.sourceReturnPC ||
            h->entryStackPointer != retainedHost.entryStackPointer ||
            h->remainingOperations != retainedHost.remainingOperations || !s->leases.empty()) fault(h);
        if (!h->fault) {
            if (completed == 1 && !s->pending) kind = CLAW_GUEST_RETURNED;
            else if (!completed && s->pending) kind = CLAW_GUEST_TRANSFER;
            else fault(h);
        }
        if (kind == CLAW_GUEST_TRANSFER) *out = s->outcome;
        else *out = {sizeof(ClawGuestOutcome), 1, kind, 0, generation, 0, {}};
    } catch (...) { fault(h, CLAW_FAULT_HOST); }
    // Do not roll back faults, output values or the consumed shared counter.
    restoreScope(h, retainedHost);
    s->active = s->pending = false; s->leases.clear();
    return kind;
}
uint32_t claw_guest_bind_eh(ClawGuestSession *s, ClawHost *h, uint64_t generation,
    const ClawGuestEHContract *contract, ClawGuestEHEntry entry) noexcept {
    if (!owned(s, h) || s->generation != generation || s->active || s->used || s->ehEntry ||
        !contract || !entry || contract->size != sizeof(*contract) || contract->version != 1 ||
        contract->ownerEntry != s->config.rootFunction || !inText(s->config, contract->entryPC) ||
        !inText(s->config, contract->handler) || !inText(s->config, contract->callSite) ||
        !inText(s->config, contract->returnPC)) return fault(h);
    s->ehContract = *contract; s->ehEntry = entry;
    return 1;
}
uint32_t claw_guest_validate_eh(ClawHost *h, const ClawGuestEHInvocation *invocation) noexcept {
    if (!h || !owned(h->guestSession, h)) return fault(h);
    auto s = h->guestSession;
    if (!s->active || !s->ehActive || s->pending || !rootScope(s, h) || !ehWitness(s) ||
        invocation != &s->invocation || h->sourceContext != &s->invocation.cpu ||
        invocation->serial != s->lastInvocation || invocation->entryPC != s->ehContract.entryPC ||
        invocation->ownerEntry != s->ehContract.ownerEntry) return fault(h);
    return 1;
}
uint32_t claw_guest_prepare_eh(ClawGuestSession *s, ClawHost *h, uint64_t generation,
    const ClawGuestEHInvocation *input) noexcept {
    if (!owned(s, h) || s->generation != generation || s->active || !s->ehEntry || h->guestSession ||
        s->ehPrepared || s->capturing || h->fault || !input || input->size != sizeof(*input) || input->version != 1 ||
        input->ownerEntry != s->ehContract.ownerEntry || input->entryPC != s->ehContract.entryPC ||
        input->serial != s->lastInvocation + 1) return fault(h);
    const auto cpu = input->cpu;
    if (cpu.size != sizeof(cpu) || cpu.version != 1 || cpu.inputMask != CLAW_CONTEXT_ALL ||
        cpu.outputMask != CLAW_CONTEXT_ALL || cpu.preserveMask || cpu.reserved0 || cpu.reserved1 ||
        cpu.eip != input->entryPC || cpu.eax != input->entryPC ||
        uint64_t(input->establisher) + 12 != cpu.ebp || !stackSpan(input->establisher, 12) ||
        !stackSpan(cpu.esp, 4) || input->establisher < cpu.esp ||
        !stackSpan(input->exceptionRecord, 80) || !stackSpan(input->contextRecord, 716) ||
        (cpu.eflags & ~0x8d7u) || !(cpu.eflags & 2) ||
        (cpu.fsHead != 0xffffffffu && (!stackSpan(cpu.fsHead, 12) || cpu.fsHead < cpu.esp))) return fault(h);
    const auto before = *h;
    s->invocation = *input;
    s->active = true;
    s->rootScope = *h; h->guestSession = s;
    try {
        const auto retainedInvocation = s->invocation;
        const auto retainedInput = *input;
        s->capturing = true;
        auto bytes = h->bytes ? h->bytes(h->user, CLAW_STACK_BASE, CLAW_STACK_END - CLAW_STACK_BASE) : nullptr;
        s->capturing = false;
        if (!bytes || !rootScope(s, h) || h->fault ||
            std::memcmp(&s->invocation, &retainedInvocation, sizeof(retainedInvocation)) ||
            std::memcmp(input, &retainedInput, sizeof(retainedInput))) fault(h);
        else {
            auto word = [&](uint32_t a) { uint32_t v; std::memcpy(&v, bytes + a - CLAW_STACK_BASE, 4); return v; };
            if (word(cpu.esp) != s->ehContract.returnPC ||
                word(retainedInvocation.establisher + 4) != s->ehContract.handler ||
                word(retainedInvocation.establisher + 8) != 1) fault(h);
            else s->ehPrepared = true;
        }
    } catch (...) { fault(h, CLAW_FAULT_HOST); }
    restoreScope(h, before);
    s->active = s->capturing = false;
    if (h->fault) s->ehPrepared = false;
    return s->ehPrepared ? 1 : 0;
}
uint32_t claw_guest_run_eh(ClawGuestSession *s, ClawHost *h, uint64_t generation,
    const ClawGuestEHInvocation *input, ClawGuestOutcome *out) noexcept {
    if (!owned(s, h) || s->generation != generation || s->active || !s->ehEntry || !s->ehPrepared ||
        h->guestSession || !borrowedScope(h, s->rootScope) || h->fault || !input || !out ||
        std::memcmp(input, &s->invocation, sizeof(*input))) return fault(h);
    const auto before = *h;
    s->ehPrepared = false; s->lastInvocation = input->serial;
    s->invocationWitness = s->invocation;
    s->active = s->used = s->ehActive = true;
    h->sourceContext = &s->invocation.cpu; h->compilerContext = nullptr;
    h->sourceReturnPC = s->ehContract.returnPC; h->entryStackPointer = s->invocation.cpu.esp;
    s->rootScope = *h; h->guestSession = s;
    uint32_t kind = CLAW_GUEST_FAULT;
    try {
        // No external callback between consuming the prepared invocation and
        // entering its native body. Python validates the full frozen state
        // after prepare_eh's memory callback and before this operation.
        const auto completed = s->ehEntry(&s->invocation, h);
        if (!rootScope(s, h) || !ehWitness(s) || !s->leases.empty()) fault(h);
        if (!h->fault && !completed && s->pending) { *out = s->outcome; kind = CLAW_GUEST_TRANSFER; }
        else if (!h->fault) fault(h);
    } catch (...) { fault(h, CLAW_FAULT_HOST); }
    if (kind != CLAW_GUEST_TRANSFER) *out = {sizeof(ClawGuestOutcome), 1, 0, 0, generation, 0, {}};
    restoreScope(h, before);
    s->active = s->pending = s->capturing = s->ehActive = false; s->leases.clear();
    return kind;
}
size_t claw_guest_sizeof(uint32_t kind) noexcept {
    switch (kind) { case 0: return sizeof(ClawGuestConfig); case 1: return sizeof(ClawGuestPhysicalEvent);
        case 2: return sizeof(ClawGuestOutcome); case 3: return sizeof(ClawGuestEHContract);
        case 4: return sizeof(ClawGuestEHInvocation); default: return 0; }
}
size_t claw_guest_offset(uint32_t kind, uint32_t field) noexcept {
#define OFFSET(T, F) offsetof(T, F)
    static const size_t config[] = {OFFSET(ClawGuestConfig,size),OFFSET(ClawGuestConfig,version),
        OFFSET(ClawGuestConfig,rootFunction),OFFSET(ClawGuestConfig,textBegin),OFFSET(ClawGuestConfig,textEnd),
        OFFSET(ClawGuestConfig,raiseSlot),OFFSET(ClawGuestConfig,raiseStub)};
    static const size_t event[] = {OFFSET(ClawGuestPhysicalEvent,size),OFFSET(ClawGuestPhysicalEvent,version),
        OFFSET(ClawGuestPhysicalEvent,kind),OFFSET(ClawGuestPhysicalEvent,slot),OFFSET(ClawGuestPhysicalEvent,stub),
        OFFSET(ClawGuestPhysicalEvent,code),OFFSET(ClawGuestPhysicalEvent,flags),OFFSET(ClawGuestPhysicalEvent,count),
        OFFSET(ClawGuestPhysicalEvent,returnPC),OFFSET(ClawGuestPhysicalEvent,cpu),OFFSET(ClawGuestPhysicalEvent,information)};
    static const size_t outcome[] = {OFFSET(ClawGuestOutcome,size),OFFSET(ClawGuestOutcome,version),
        OFFSET(ClawGuestOutcome,kind),OFFSET(ClawGuestOutcome,reserved),OFFSET(ClawGuestOutcome,generation),
        OFFSET(ClawGuestOutcome,payload),OFFSET(ClawGuestOutcome,event)};
    static const size_t contract[] = {OFFSET(ClawGuestEHContract,size),OFFSET(ClawGuestEHContract,version),
        OFFSET(ClawGuestEHContract,ownerEntry),OFFSET(ClawGuestEHContract,entryPC),OFFSET(ClawGuestEHContract,handler),
        OFFSET(ClawGuestEHContract,funcInfo),OFFSET(ClawGuestEHContract,handlerTable),OFFSET(ClawGuestEHContract,callSite),
        OFFSET(ClawGuestEHContract,returnPC)};
    static const size_t invocation[] = {OFFSET(ClawGuestEHInvocation,size),OFFSET(ClawGuestEHInvocation,version),
        OFFSET(ClawGuestEHInvocation,ownerEntry),OFFSET(ClawGuestEHInvocation,entryPC),OFFSET(ClawGuestEHInvocation,establisher),
        OFFSET(ClawGuestEHInvocation,exceptionRecord),OFFSET(ClawGuestEHInvocation,contextRecord),
        OFFSET(ClawGuestEHInvocation,serial),OFFSET(ClawGuestEHInvocation,cpu)};
#undef OFFSET
    if (kind == 0 && field < sizeof(config)/sizeof(*config)) return config[field];
    if (kind == 1 && field < sizeof(event)/sizeof(*event)) return event[field];
    if (kind == 2 && field < sizeof(outcome)/sizeof(*outcome)) return outcome[field];
    if (kind == 3 && field < sizeof(contract)/sizeof(*contract)) return contract[field];
    if (kind == 4 && field < sizeof(invocation)/sizeof(*invocation)) return invocation[field];
    return size_t(-1);
}
}
