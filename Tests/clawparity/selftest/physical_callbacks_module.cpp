// Independent synthetic DialogBox caller. No original game implementation.
#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t f) { return f == 0x401000 || f == 0x401040 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff, 0x7ff, 0x472, 0}; }
uint32_t body(claw::Run &run, uint32_t f, uint32_t, const uint32_t *) {
    auto &s = run.source();
    ClawSourceContext child = s;
    uint32_t value;
    if (f == 0x401040) {
        child.esp -= 4;
        child.eip = 0x401000;
        run.put(child.esp, 0x401045);
        value = run.source_call(0x401000, 0, 0x401045, child);
    } else {
        child.esp -= 24;
        child.eip = 0x402000;
        run.put(child.esp, 0x401016);
        run.put(child.esp+4, 0x51);
        run.put(child.esp+8, 0x402080);
        run.put(child.esp+12, 0);
        run.put(child.esp+16, 0x401100);
        run.put(child.esp+20, 0);
        value = run.source_call(0x402000,0,0x401016,child,{0x51,0x402080,0,0x401100,0},0,20);
    }
    std::memcpy(&s.eax,&child.eax,11*sizeof(uint32_t));
    return value;
}
}
CLAW_SOURCE_MODULE_ENTRY(claw_physical_callbacks_source_entry,owned,contract,body)

// Isolated physical service root: unlike the synthetic callers, this root is
// stdcall5. It forwards the borrowed source request without a game epilogue.
extern "C" uint32_t claw_physical_callbacks_entry(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    if (f != 0x546d2c) return claw_physical_callbacks_source_entry(f,r,a,n,h,out);
    if (n != 5 || !h->sourceContext) return 0;
    ClawSourceContext child = *h->sourceContext;
    ClawCall call{};
    call.function=f;call.argumentCount=n;call.stackPointer=child.esp;
    for (uint32_t i=0;i<n;++i) call.arguments[i]=a[i];
    call.sourceContext=&child;call.sourceReturnPC=h->sourceReturnPC;
    *out=h->call(h->user,&call);
    if (h->fault) return 0;
    std::memcpy(&h->sourceContext->eax,&child.eax,11*sizeof(uint32_t));
    return 1;
}

namespace {
int callback_owned(uint32_t f) { return f == 0x401100 ? 4 : -1; }
uint32_t callback_body(claw::Run &run, uint32_t, uint32_t, const uint32_t *a) {
    if (a[1] == 0x110) {
        run.put(0x402044, 0x1234);
        return 1;
    }
    if (a[1] == 0x111 && a[2] <= 2) {
        run.put(0x402044, a[2]);
        run.call(0x401200, 0, {});
        run.call(0x402008, 0, {a[0],a[2]});
        return 1;
    }
    run.put(0x402044, a[2]);
    run.put(a[3], a[2]);
    return 0xabcd;
}
}
CLAW_MODULE_ENTRY(claw_physical_callback_owned_entry,callback_owned,callback_body)

extern "C" uint32_t claw_physical_callbacks_selected(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    if (f == 0x401100) return claw_physical_callback_owned_entry(f,r,a,n,h,out);
    return claw_physical_callbacks_entry(f,r,a,n,h,out);
}
extern "C" uint32_t claw_physical_callbacks_mutant(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    if (f == 0x401100 || f == 0x49b730) { *out = 1; return 1; }
    return claw_physical_callbacks_entry(f,r,a,n,h,out);
}

namespace {
uint32_t cpu_callback(claw::Run &run, uint32_t, uint32_t, const uint32_t *a) {
    auto &s = run.callback_cpu();
    auto push = [&](uint32_t v) { s.esp -= 4; run.put(s.esp,v); };
    auto pop = [&]() { auto v=run.get(s.esp);s.esp+=4;return v; };
    push(s.esi);push(s.edi);
    s.esi=0x76543210;s.edi=0x12345678;s.eax=0x99;
    push(a[2]);push(0x40111a);
    run.callback_call(0x401200,0,0x40111a,{a[2]},4);
    push(a[2]);push(0x401124);
    run.callback_call(0x402004,0,0x401124,{a[2]},4);
    s.edi=pop();s.esi=pop();s.eax=0xabcd;
    return s.eax;
}
}
CLAW_MODULE_ENTRY(claw_physical_callback_cpu_body,callback_owned,cpu_callback)
extern "C" uint32_t claw_physical_callbacks_cpu(uint32_t f, uint32_t r, const uint32_t *a,
    uint32_t n, ClawHost *h, uint32_t *out) {
    if (f != 0x401100) return claw_physical_callbacks_entry(f,r,a,n,h,out);
    claw::Run run(*h);
    static uint64_t retired = 0;
    auto *lease=h->callbackCPU;
    auto copied=*lease;
    const uint32_t attack=run.get(0x402070);
    if (attack==1) h->callbackCPU=&copied;
    if (attack==2) lease->version=2;
    if (attack==3) lease->target+=1;
    if (attack==4) lease->activation=retired;
    if (attack==5) lease->cpu.eflags=0;
    if (attack==6) lease->cpu.fsHead=0;
    if (attack==7) lease->entryStackPointer+=4;
    if (attack==8) lease->cpu.inputMask=0x5c0;
    if (attack>=9 && attack<=12) {
        auto child=lease->cpu;
        child.esp-=8;child.eip=0x401200;
        run.put(child.esp,0x40111a);run.put(child.esp+4,a[2]);
        lease->cpu=child;
        ClawCall call{};call.function=0x401200;call.argumentCount=1;call.arguments[0]=a[2];
        call.stackPointer=child.esp;call.sourceReturnPC=0x40111a;call.sourceContext=&child;
        call.callbackCPU=attack==9?&copied:lease;
        call.callbackActivation=attack==10?retired:lease->activation;
        if (attack==11) child.esi^=1;
        if (attack==12) call.callbackCPU=nullptr;
        h->call(h->user,&call);
        return 0;
    }
    retired=lease->activation;
    auto completed=claw_physical_callback_cpu_body(f,r,a,n,h,out);
    if (attack==13) lease->cpu.esi^=1;
    if (attack==14) lease->cpu.esp+=4;
    h->callbackCPU=lease;
    return completed;
}
