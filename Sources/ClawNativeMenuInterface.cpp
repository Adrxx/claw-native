#include "ClawNativeMenuInterface.h"
#include "ClawNativeMenuResources.h"
#include "ClawCanonicalDispatch.h"
#include "ClawNativeLevelTransport.h"
#include "ApplicationLevelProgressionRuntime.h"
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <limits>
#include <utility>

namespace {
// Join the existing credits owner to the app's shared heap and dispatch.
// Automatic pointer packets remain borrowed for one synchronous call.
uint32_t creditsDependency(ClawApplicationLevelProgressionContext *c,
                          const ClawApplicationLevelProgressionCall *e,void *user) {
    auto h=static_cast<ClawHost*>(user);
    ClawCall q{};q.function=e->function;q.receiver=e->receiver;q.argumentCount=e->argumentCount;
    if(q.argumentCount>CLAW_CALL_ARGUMENT_CAPACITY || e->bufferCount>3) {c->fault=3;return 0;}
    std::copy_n(e->arguments,q.argumentCount,q.arguments);
    uint32_t tokens[3]{},used=0;
    for(uint32_t bit=0;bit<32;++bit) if(e->localMask&(1u<<bit)) {
        if(used>=e->bufferCount || (bit!=8 && bit>=q.argumentCount)) {c->fault=3;return 0;}
        ClawCall alloc{};alloc.function=0x4f63ec;alloc.argumentCount=1;alloc.arguments[0]=e->bufferBytes[used];
        auto token=h->call(h->user,&alloc);tokens[used]=token;
        auto bytes=h->bytes(h->user,token,e->bufferBytes[used]);
        if(h->fault || !bytes) {c->fault=1;return 0;}
        std::memcpy(bytes,e->buffers[used],e->bufferBytes[used]);
        if(bit==8) q.receiver=token;else q.arguments[bit]=token;
        ++used;
    }
    if(used!=e->bufferCount) {c->fault=3;return 0;}
    auto result=h->call(h->user,&q);
    for(uint32_t i=0;i<used;++i) {
        auto bytes=h->bytes(h->user,tokens[i],e->bufferBytes[i]);
        if(bytes) std::memcpy(e->buffers[i],bytes,e->bufferBytes[i]);else c->fault=1;
        if(!h->fault) {ClawCall release{};release.function=0x4f6428;release.argumentCount=1;release.arguments[0]=tokens[i];h->call(h->user,&release);}
    }
    if(h->fault) c->fault=h->fault;
    return result;
}
uint32_t creditsEntry(uint32_t f,uint32_t self,const uint32_t *a,uint32_t n,ClawHost *h,uint32_t *out) {
    switch(f) {
    case 0x429710:case 0x4295b0:case 0x429720:case 0x429740:case 0x4295c0:case 0x4295e0:
    case 0x435840:case 0x4359f0:case 0x435e60:case 0x435a50:case 0x435af0:case 0x435d10:
    case 0x435d50:case 0x435da0:case 0x435de0:case 0x436630:case 0x4366c0:case 0x435b80:
    case 0x436590:case 0x4361c0:case 0x435f30:case 0x436340:case 0x436560:case 0x42b520:break;
    default:return 0;
    }
    ClawApplicationLevelProgressionContext c{};
    c.scene.context=h;
    c.scene.lookup=[](void *user,uint32_t token,uint32_t words) {
        auto host=static_cast<ClawHost*>(user);
        return reinterpret_cast<uint32_t*>(host->bytes(host->user,token,words*4));
    };
    c.maximumOperations=h->maximumOperations;
    auto ran=claw_application_level_progression_entry(f,self,a,n,&c,creditsDependency,h,out);
    if(c.fault && !h->fault) {h->fault=c.fault;h->faultAddress=f;}
    return ran;
}
}

namespace {
// Exact native x87 primitives for the precision setting the original selects
// (control word 0x023f: 53-bit significand, round to nearest, all exceptions
// masked). Under that setting every result is the binary64 rounding of the
// exact value with an unbounded exponent, so binary64 arithmetic is exact
// whenever its result is neither infinite nor rounded in the subnormal range.
// Anything else (NaN, infinity, extended-range results, LN2/YL2X) is
// rejected, never approximated.
bool x87_to_double(const ClawX87Value &v,double &d) {
    const uint32_t exponent=v.signExponent & 0x7fff;
    if (v.reserved || v.signExponent > 0xffff || exponent == 0x7fff) return false;
    if (!exponent) {
        if (v.significand) return false;
        d=(v.signExponent & 0x8000) ? -0.0 : 0.0;return true;
    }
    if (!(v.significand >> 63) || (v.significand & 0x7ff)) return false;
    d=std::ldexp(double(v.significand),int(exponent)-16383-63);
    if (v.signExponent & 0x8000) d=-d;
    return std::isfinite(d) && std::ldexp(std::fabs(d),16383+63-int(exponent)) == double(v.significand);
}
ClawX87Value x87_from_double(double d) {
    ClawX87Value v{};
    if (d != 0) {
        int exponent=0;const double fraction=std::frexp(std::fabs(d),&exponent);
        v.significand=uint64_t(std::ldexp(fraction,64));
        v.signExponent=uint32_t(exponent+16382);
    }
    if (std::signbit(d)) v.signExponent|=0x8000;
    return v;
}
// Binary64 result r of an exact operation; false when the x87 result could
// differ. Sums never round in the subnormal range; a product or quotient there
// may have kept bits under the x87's wider exponent, so it is rejected.
bool x87_sum_ok(double r) {return std::isfinite(r);}
bool x87_product_ok(double a,double b,double r) {
    return std::isfinite(r) && (std::fabs(r) >= DBL_MIN || a == 0 || b == 0);
}
bool x87_quotient_ok(double a,double b,double r) {
    return b != 0 && std::isfinite(r) && (std::fabs(r) >= DBL_MIN || a == 0);
}
enum X87Arith {X87_ADD,X87_MUL,X87_SUB,X87_SUBR,X87_DIV,X87_DIVR};
bool x87_arith(X87Arith kind,double a,double b,double &r) {
    switch (kind) {
    case X87_ADD: r=a+b;return x87_sum_ok(r);
    case X87_SUB: r=a-b;return x87_sum_ok(r);
    case X87_SUBR: r=b-a;return x87_sum_ok(r);
    case X87_MUL: r=a*b;return x87_product_ok(a,b,r);
    case X87_DIV: r=a/b;return x87_quotient_ok(a,b,r);
    case X87_DIVR: r=b/a;return x87_quotient_ok(b,a,r);
    }
    return false;
}
// FCOM/FCOMP/FCOMPP condition codes; ordered operands only.
uint32_t x87_compare(uint32_t status,double a,double b) {
    status&=~0x4500u;
    if (a < b) status|=0x0100;
    else if (a == b) status|=0x4000;
    return status;
}
// Round an x87 register value to binary64 the way the reference x87
// (round to nearest even, normal range only) converts it.
bool x87_round_double(const ClawX87Value &v,double &d) {
    const uint32_t exponent=v.signExponent & 0x7fff;
    if (v.reserved || v.signExponent > 0xffff || exponent == 0x7fff) return false;
    if (!exponent) {
        if (v.significand) return false;
        d=(v.signExponent & 0x8000) ? -0.0 : 0.0;return true;
    }
    if (!(v.significand >> 63)) return false;
    uint64_t kept=v.significand >> 11;const uint64_t rest=v.significand & 0x7ff;
    if (rest > 0x400 || (rest == 0x400 && (kept & 1))) ++kept;
    d=std::ldexp(double(kept),int(exponent)-16383-52);
    if (v.signExponent & 0x8000) d=-d;
    return std::isfinite(d) && std::fabs(d) >= DBL_MIN;
}
uint32_t x87_step_service(const ClawCall *q,uint32_t *out) {
    ClawX87State *s=q->x87State;
    if (q->function || q->receiver || q->receiver2 || !s || s->size != sizeof(*s) ||
        s->version != CLAW_X87_VERSION || s->control != 0x023f || s->count > 8 ||
        s->popCount > s->count || s->count-s->popCount+s->pushCount > 8 ||
        s->returned || s->eax || s->edx) return 0;
    // Each live value is binary64 (v) or carried as exact extended bits (raw,
    // wide). Moves carry wide values unchanged; arithmetic reading one refuses,
    // except FYL2X, which the reference computes through binary64.
    double v[9]{};ClawX87Value raw[9]{};bool wide[9]{};
    uint32_t n=s->count;
    for (uint32_t i=0;i<n;++i) {
        raw[i]=s->slots[i];
        if (x87_to_double(s->slots[i],v[i])) continue;
        double probe=0;
        if (!x87_round_double(s->slots[i],probe)) return 0;
        wide[i]=true;
    }
    double operand=0;
    if (q->argumentCount == 2) {
        const uint64_t bits=uint64_t(q->arguments[0])|(uint64_t(q->arguments[1])<<32);
        std::memcpy(&operand,&bits,8);
        if (!std::isfinite(operand)) return 0;
    }
    uint32_t status=s->status,argc=0,pop=0,push=1,minimum=0,reads=0;uint64_t stored=0;
    const uint32_t op=q->x87Operation,form=op & ~7u,k=(op & 7u)+1;
    auto push_value=[&](double d){
        for(uint32_t i=n;i>0;--i) {v[i]=v[i-1];raw[i]=raw[i-1];wide[i]=wide[i-1];}
        v[0]=d;wide[0]=false;++n;
    };
    auto pop_value=[&]{
        for(uint32_t i=0;i+1<n;++i) {v[i]=v[i+1];raw[i]=raw[i+1];wide[i]=wide[i+1];}
        --n;v[n]=0;wide[n]=false;
    };
    auto copy_slot=[&](uint32_t to,uint32_t from){v[to]=v[from];raw[to]=raw[from];wide[to]=wide[from];};
    bool ok=true;
    switch (op) {
    case CLAW_X87_LN2: break;
    case CLAW_X87_YL2X: pop=minimum=2;break;
    case CLAW_X87_I32: argc=1;break;
    case CLAW_X87_F64: argc=2;break;
    case CLAW_X87_DIV_ST1: case CLAW_X87_ADD_ST1: pop=1;minimum=2;reads=3;break;
    case CLAW_X87_POP: pop=minimum=1;push=0;break;
    case CLAW_X87_CHS: case CLAW_X87_ROUND_F64: case CLAW_X87_SQRT: case CLAW_X87_ABS:
    case CLAW_X87_SIN: case CLAW_X87_COS:
    case CLAW_X87_ST_F64: pop=minimum=1;reads=1;break;
    case CLAW_X87_STP_F64: pop=minimum=1;push=0;reads=1;break;
    case CLAW_X87_COMPP: pop=minimum=2;push=0;reads=3;break;
    case CLAW_X87_COM_F64: minimum=1;push=0;argc=2;reads=1;break;
    case CLAW_X87_COMP_F64: pop=minimum=1;push=0;argc=2;reads=1;break;
    case CLAW_X87_SUBR_F64: case CLAW_X87_MUL_F64: case CLAW_X87_DIV_F64:
    case CLAW_X87_ADD_F64: case CLAW_X87_SUB_F64: pop=minimum=1;argc=2;reads=1;break;
    default:
        if (op < CLAW_X87_LD_ST || op > CLAW_X87_DIVP + 7) return 0;
        minimum=k;
        if (form == CLAW_X87_LD_ST) {}
        else if (form == CLAW_X87_COM_ST) {push=0;reads=1u|(1u<<(k-1));}
        else if (form == CLAW_X87_COMP_ST) {pop=1;push=0;reads=1u|(1u<<(k-1));}
        else if (form >= CLAW_X87_ADD_TO0 && form <= CLAW_X87_DIVR_TO0) {pop=1;reads=1u|(1u<<(k-1));}
        else if (form == CLAW_X87_XCH_ST || form == CLAW_X87_ST_ST) pop=push=k;
        else if (form >= CLAW_X87_ADD_TOI && form <= CLAW_X87_DIV_TOI) {pop=push=k;reads=1u|(1u<<(k-1));}
        else if (form == CLAW_X87_STP_ST) {pop=k;push=k-1;}
        else {pop=k;push=k-1;reads=1u|(1u<<(k-1));}
    }
    if (q->argumentCount != argc || n < minimum || s->popCount != pop || s->pushCount != push) return 0;
    for (uint32_t i=0;i<n;++i) if ((reads>>i & 1) && wide[i]) return 0;
    switch (op) {
    case CLAW_X87_LN2:
        // FLDLN2 under round to nearest: the extended constant, exactly.
        push_value(0);raw[0].significand=0xb17217f7d1cf79acull;raw[0].signExponent=0x3ffe;raw[0].reserved=0;wide[0]=true;
        break;
    case CLAW_X87_YL2X: {
        // Reference FYL2X: binary64 log(ST0)/log(2.0)*ST1 into ST1, then pop.
        double x=0,y=0;
        if (wide[0]) {if (!x87_round_double(raw[0],x)) return 0;} else x=v[0];
        if (wide[1]) {if (!x87_round_double(raw[1],y)) return 0;} else y=v[1];
        if (!(x > 0) || !std::isfinite(x) || !std::isfinite(y)) return 0;
        const double r=std::log(x)/std::log(2.0)*y;
        if (!std::isfinite(r) || (r != 0 && std::fabs(r) < DBL_MIN)) return 0;
        v[1]=r;wide[1]=false;pop_value();
        break;
    }
    case CLAW_X87_I32: push_value(double(int32_t(q->arguments[0])));break;
    case CLAW_X87_F64: push_value(operand);break;
    case CLAW_X87_DIV_ST1: ok=x87_arith(X87_DIV,v[0],v[1],v[0]);break;
    case CLAW_X87_ADD_ST1: ok=x87_arith(X87_ADD,v[0],v[1],v[0]);break;
    case CLAW_X87_POP: pop_value();break;
    case CLAW_X87_CHS: v[0]=-v[0];break;
    case CLAW_X87_ABS: v[0]=std::fabs(v[0]);break;
    case CLAW_X87_ROUND_F64: break;
    // FSIN/FCOS in Omar's ring motion. The finite reference profile rounds
    // the transcendental result to binary64 and clears the range flag C2.
    case CLAW_X87_SIN: case CLAW_X87_COS:
        if (std::fabs(v[0]) >= 0x1p63) return 0;
        v[0]=op == CLAW_X87_SIN ? std::sin(v[0]) : std::cos(v[0]);
        status&=~0x0400u;
        break;
    // Negative operands, including -0, set C2 in the comparison emulator; reject them.
    case CLAW_X87_SQRT: if (std::signbit(v[0])) return 0;v[0]=std::sqrt(v[0]);break;
    case CLAW_X87_ST_F64: case CLAW_X87_STP_F64:
        std::memcpy(&stored,&v[0],8);
        if (op == CLAW_X87_STP_F64) pop_value();
        break;
    case CLAW_X87_COMPP: status=x87_compare(status,v[0],v[1]);pop_value();pop_value();break;
    case CLAW_X87_COM_F64: case CLAW_X87_COMP_F64:
        status=x87_compare(status,v[0],operand);
        if (op == CLAW_X87_COMP_F64) pop_value();
        break;
    case CLAW_X87_SUBR_F64: ok=x87_arith(X87_SUBR,v[0],operand,v[0]);break;
    case CLAW_X87_MUL_F64: ok=x87_arith(X87_MUL,v[0],operand,v[0]);break;
    case CLAW_X87_DIV_F64: ok=x87_arith(X87_DIV,v[0],operand,v[0]);break;
    case CLAW_X87_ADD_F64: ok=x87_arith(X87_ADD,v[0],operand,v[0]);break;
    case CLAW_X87_SUB_F64: ok=x87_arith(X87_SUB,v[0],operand,v[0]);break;
    default: {
        const uint32_t i=k-1;
        static const X87Arith kinds[]={X87_ADD,X87_MUL,X87_SUB,X87_SUBR,X87_DIV,X87_DIVR};
        // Reverse forms on ST(i) use the Intel encoding: DC E0+i is FSUBR ST(i),ST(0).
        static const X87Arith toI[]={X87_ADD,X87_MUL,X87_SUBR,X87_SUB,X87_DIVR,X87_DIV};
        if (form == CLAW_X87_LD_ST) {push_value(0);copy_slot(0,i+1);}
        else if (form == CLAW_X87_XCH_ST) {
            const double tv=v[0];const ClawX87Value tr=raw[0];const bool tw=wide[0];
            copy_slot(0,i);v[i]=tv;raw[i]=tr;wide[i]=tw;
        }
        else if (form == CLAW_X87_ST_ST) copy_slot(i,0);
        else if (form == CLAW_X87_STP_ST) {copy_slot(i,0);pop_value();}
        else if (form == CLAW_X87_COM_ST || form == CLAW_X87_COMP_ST) {
            status=x87_compare(status,v[0],v[i]);
            if (form == CLAW_X87_COMP_ST) pop_value();
        } else if (form >= CLAW_X87_ADD_TO0 && form <= CLAW_X87_DIVR_TO0)
            ok=x87_arith(kinds[(form-CLAW_X87_ADD_TO0)/8],v[0],v[i],v[0]);
        else if (form >= CLAW_X87_ADD_TOI && form <= CLAW_X87_DIV_TOI)
            ok=x87_arith(toI[(form-CLAW_X87_ADD_TOI)/8],v[i],v[0],v[i]);
        else {
            ok=x87_arith(toI[(form-CLAW_X87_ADDP)/8],v[i],v[0],v[i]);
            pop_value();
        }
    }
    }
    if (!ok || n != s->count-pop+push) return 0;
    ClawX87State next=*s;
    std::memset(next.slots,0,sizeof(next.slots));
    for (uint32_t i=0;i<n;++i) next.slots[i]=wide[i] ? raw[i] : x87_from_double(v[i]);
    next.count=n;
    next.status=(status & ~0x3800u)|((((s->status>>11)+pop-push)&7)<<11);
    next.returned=1;next.eax=uint32_t(stored);next.edx=uint32_t(stored>>32);
    *s=next;*out=next.eax;return 1;
}
}

// Finite native mathematical transport for the menu's binary64 precision mode.
// Reject extended-precision operands instead of silently rounding them.
uint32_t claw_native_menu_math_service(const ClawCall *q,uint32_t *out) {
    if (!q || !out || q->receiver || q->receiver2 || q->compilerContext || q->sourceContext) return 0;
    if (q->x87ArgumentCount == CLAW_X87_STEP) return x87_step_service(q,out);
    if (q->x87ArgumentCount == 1 && q->function == 0x4a30e0) {
        const double v=q->x87Argument;
        if (!std::isfinite(v) || v < -0x1p63 || v >= 0x1p63) return 0;
        *out=uint32_t(int64_t(std::trunc(v)));return 1;
    }
    auto *s=q->x87State;
    if (!s || (q->x87ArgumentCount != CLAW_X87_STEP && q->x87ArgumentCount != CLAW_X87_EXACT)
        || s->size != sizeof(*s) || s->version != CLAW_X87_VERSION || s->control != 0x023f
        || s->count > 8 || s->popCount > s->count || s->pushCount > 1
        || s->count-s->popCount+s->pushCount > 8) return 0;
    double values[8]{};
    for (uint32_t i=0;i<s->count;++i) {
        const auto &v=s->slots[i];
        if (v.reserved || (v.signExponent & 0x7fff) == 0x7fff || (v.significand & 0x7ff)) return 0;
        values[i]=std::ldexp(double(v.significand),int(v.signExponent & 0x7fff)-16383-63);
        if (v.signExponent & 0x8000) values[i]=-values[i];
        if (!std::isfinite(values[i])) return 0;
    }
    double operand=0,result=0;uint32_t eax=0,edx=0;bool produced=false;
    if (q->argumentCount == 2) {uint64_t bits=uint64_t(q->arguments[0])|(uint64_t(q->arguments[1])<<32);std::memcpy(&operand,&bits,8);}
    if (q->function == 0x4a30e0) {
        if (!s->count || values[0] < -0x1p63 || values[0] >= 0x1p63 || s->popCount!=1 || s->pushCount) return 0;
        const uint64_t integer=uint64_t(int64_t(std::trunc(values[0])));eax=uint32_t(integer);edx=uint32_t(integer>>32);
    } else if (q->function == 0x4a4250) {
        // CRT ceil(double): the menu's moving Claw rounds each pixel step up.
        // The argument is on the C stack and the result is pushed onto x87.
        if (q->argumentCount!=2 || s->popCount || s->pushCount!=1 || !std::isfinite(operand)) return 0;
        result=std::ceil(operand);produced=true;
    } else if (q->function == 0x4a4350) {
        // CRT floor(double), same convention: the audio options page rounds
        // the music volume down to its slider step.
        if (q->argumentCount!=2 || s->popCount || s->pushCount!=1 || !std::isfinite(operand)) return 0;
        result=std::floor(operand);produced=true;
    } else if (q->function == 0x4f1b30) {
        if (s->count<2 || s->popCount!=2 || s->pushCount!=1) return 0;
        result=std::pow(values[1],values[0]);produced=true;
    } else if (q->function == 0x4f2400) {
        if (!s->count || s->popCount!=1 || s->pushCount!=1 || values[0]<-1 || values[0]>1) return 0;
        result=std::acos(values[0]);produced=true;
    } else return 0;
    if (s->pushCount && (!produced || !std::isfinite(result))) return 0;
    ClawX87Value slots[8]{};
    if (s->pushCount && result != 0) {
        int exponent=0;const double fraction=std::frexp(std::fabs(result),&exponent);
        slots[0].significand=uint64_t(std::ldexp(fraction,64));
        slots[0].signExponent=uint32_t(exponent+16382)|(std::signbit(result)?0x8000:0);
    } else if (s->pushCount && std::signbit(result)) slots[0].signExponent=0x8000;
    for(uint32_t i=s->popCount;i<s->count;++i) slots[s->pushCount+i-s->popCount]=s->slots[i];
    std::memcpy(s->slots,slots,sizeof(slots));s->count=s->count-s->popCount+s->pushCount;
    s->status=(s->status & ~0x3800u)|((((s->status>>11)+s->popCount-s->pushCount)&7)<<11);
    s->returned=1;s->eax=eax;s->edx=edx;*out=eax;return 1;
}
extern "C" {
uint32_t claw_palette_fade_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_application_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_application_state_factory_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_popup_input_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_popup_lifecycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_popup_construction_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_popup_surface_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_display_resize_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_diagnostic_policy_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_movie_state_cleanup_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_game_image_raw_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_game_image_flips_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_pid_blitter_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_ani_cycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_static_extended_records_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_special_command_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_plane_renderer_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_game_frame_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_game_timing_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_graphics_manager_lifecycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_graphics_record_constructor_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_cleanup_services_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_application_archive_path_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_movie_selection_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_checkpoint_logic_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_world_object_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_palette_resource_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_world_file_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_spatial_grid_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_application_input_configuration_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_application_bootstrap_managers_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_scene_display_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_surface_blit_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_surface_fill_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_surface_flip_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_scene_camera_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_player_cache_application_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_game_launch_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_pickup_points_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_player_startup_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_v13_player_startup_compat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_booty_results_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_simple_animation_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_booty_progression_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_booty_story_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_actor_animation_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_scene_actor_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_scene_startup_composition_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_startup_logic_registration_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_scenery_logic_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_claw_logic_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_sparkle_logic_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_music_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_save_load_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_menu_application_services_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_native_menu_actor_destruction_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_image_registry_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_interface_file_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_state_five_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_menu_input_dispatch_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_player_fade_blend_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_game_image_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_image_resource_lifecycle_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_scene_lifecycle_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
uint32_t claw_single_player_scene_canonical_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
}
// Join adapter for original cdecl callees that read no stack argument (checked
// against the original bodies: no ESP- or EBP-relative reads), whose admitted
// declaration and an admitted caller disagree on the pushed count. A cdecl caller
// pops its own pushes, so the callee receives exactly its declared count; missing
// words are never read. Closed list: every row was checked by hand.
namespace {
struct ClawCdeclUnreadArguments { uint32_t function, declared; };
constexpr ClawCdeclUnreadArguments clawCdeclUnreadArguments[] = {
    {0x420480,0}, // level_one_claw_states_02; 0x419030 pushes three words
    {0x43fd10,0}, {0x43fdc0,0}, // level_one_batch_enemy_states_01 (thiscall, argc 0); 0x47d470 calls with ECX only
    {0x43ff60,0}, // level_one_batch_enemy_states_02 (thiscall, argc 0); 0x44de22 calls with ECX only
    {0x44da20,0}, // level_one_batch_human_enemies_01 (thiscall, argc 0); callers set ECX only
    {0x4bb030,0}, // booty_progression; 0x416ab7 and 0x419e50 push one word
    {0x4bc110,0}, // interface_file; a bare RET, callers push one word or none
    {0x4c96b0,0}, // bare RET; bird movement callers push three words
};
}
uint32_t claw_native_menu_argument_count(uint32_t function,uint32_t count) {
    for (const auto &row : clawCdeclUnreadArguments)
        if (row.function == function) return row.declared;
    return count;
}
uint32_t claw_native_menu_interface_entry(uint32_t f,uint32_t self,const uint32_t *a,uint32_t n,ClawHost *h,uint32_t *out) {
    if(creditsEntry(f,self,a,n,h,out)) return 1;
    if(h->fault) return 0;
    const uint32_t normalized = claw_native_menu_argument_count(f,n);
    if (normalized != n) {
        uint32_t words[CLAW_CALL_ARGUMENT_CAPACITY] = {};
        for (uint32_t i = 0; i < normalized && i < n; ++i) words[i] = a[i];
        return claw_native_menu_interface_entry(f,self,words,normalized,h,out);
    }
    if (f == 0x428c40) return claw_application_state_factory_entry(f,self,a,n,h,out);
    if (f == 0x438c40 || f == 0x4399d0 || f == 0x4236c0 || f == 0x423840 ||
        f == 0x424b90 || f == 0x424ca0)
        return claw_menu_popup_construction_entry(f,self,a,n,h,out);
    if (f == 0x4299b0 || f == 0x438e10 || f == 0x438e90 || f == 0x438f10 ||
        f == 0x438fa0 || f == 0x4390c0 || f == 0x439130 || f == 0x43a7f0)
        return claw_menu_popup_lifecycle_entry(f,self,a,n,h,out);
    if (f == 0x4392d0 || f == 0x439390 || f == 0x4393c0 || f == 0x439400 || f == 0x439440 ||
        f == 0x42bfd0 || f == 0x42bff0 || f == 0x42c010)
        return claw_menu_popup_input_entry(f,self,a,n,h,out);
    if (f == 0x439480 || f == 0x439590 || f == 0x439630 || f == 0x4396f0 ||
        f == 0x43a6e0 || f == 0x43a720 || f == 0x43a760 || f == 0x4cab10 ||
        f == 0x452ae0 || f == 0x452af0 || f == 0x45fdc0 || f == 0x45fdd0)
        return claw_menu_popup_surface_entry(f,self,a,n,h,out);
    if (f == 0x4bd260 || f == 0x4b4ed0) return claw_menu_diagnostic_policy_entry(f,self,a,n,h,out);
    if (f == 0x4efcd0 || f == 0x4efd00) return claw_movie_state_cleanup_entry(f,self,a,n,h,out);
    if (f == 0x45acb0) return claw_static_extended_records_entry(f,self,a,n,h,out);
    if (f == 0x4d32e0) return claw_game_image_raw_entry(f,self,a,n,h,out);
    if (f == 0x4d3790 || f == 0x4d3550 || f == 0x4d3a00 ||
        f == 0x4d2bb0 || f == 0x4d2e10 || f == 0x4d3080)
        return claw_game_image_flips_entry(f,self,a,n,h,out);
    if (f == 0x4c00b0) return claw_pid_blitter_entry(f,self,a,n,h,out);
    const ClawEntry frameEntries[] = {claw_palette_fade_canonical_entry,claw_menu_application_entry,claw_menu_display_resize_entry,claw_native_menu_special_command_entry,claw_native_menu_plane_renderer_entry,claw_ani_cycle_entry};
    for (auto entry : frameEntries) {
        if (entry(f,self,a,n,h,out)) return 1;
        if (h->fault) return 0;
    }
    if (f == 0x429d60 || f == 0x429d80 || f == 0x429db0 || f == 0x429de0)
        return claw_menu_input_dispatch_entry(f,self,a,n,h,out);
    if (f == 0x428b60) return claw_game_frame_canonical_entry(f,self,a,n,h,out);
    if (f == 0x4b82f0 || f == 0x4b83f0) return claw_game_timing_canonical_entry(f,self,a,n,h,out);
    const ClawEntry entries[] = {claw_native_menu_graphics_manager_lifecycle_entry, claw_native_menu_graphics_record_constructor_entry, claw_native_menu_menu_cleanup_services_entry, claw_native_menu_application_archive_path_entry, claw_native_menu_menu_movie_selection_entry, claw_native_menu_checkpoint_logic_entry, claw_native_menu_world_object_entry, claw_native_menu_palette_resource_entry, claw_native_menu_world_file_entry, claw_native_menu_spatial_grid_entry, claw_native_menu_application_input_configuration_entry, claw_native_menu_application_bootstrap_managers_entry, claw_native_menu_scene_display_entry, claw_native_menu_surface_blit_entry, claw_native_menu_surface_fill_entry, claw_native_menu_surface_flip_entry, claw_native_menu_scene_camera_entry, claw_native_menu_player_cache_application_entry, claw_native_menu_menu_game_launch_entry, claw_native_menu_pickup_points_entry, claw_v13_player_startup_compat_entry, claw_native_menu_booty_results_entry, claw_native_menu_simple_animation_entry, claw_native_menu_booty_progression_entry, claw_native_menu_booty_story_entry, claw_native_menu_actor_animation_entry, claw_native_menu_scene_actor_entry, claw_native_menu_scene_startup_composition_entry, claw_native_menu_startup_logic_registration_entry, claw_native_menu_scenery_logic_entry, claw_native_menu_menu_claw_logic_entry, claw_native_menu_menu_sparkle_logic_entry, claw_native_menu_music_entry, claw_native_menu_save_load_entry, claw_native_menu_menu_application_services_entry, claw_native_menu_actor_destruction_entry, claw_image_registry_canonical_entry, claw_interface_file_canonical_entry, claw_state_five_canonical_entry, claw_player_fade_blend_canonical_entry, claw_game_image_canonical_entry, claw_image_resource_lifecycle_canonical_entry, claw_scene_lifecycle_canonical_entry, claw_single_player_scene_canonical_entry};
    for (auto entry : entries) {
        if (entry(f,self,a,n,h,out)) return 1;
        if (h->fault) return 0;
    }
    // New Game and Level 1: admitted canonical owners from the generated
    // registry, the same family entries the native Level 1 join elects.
    if (const ClawCanonicalEntry *owner = claw_canonical_lookup(f))
        return owner->entry(f,self,a,n,h,out);
    return 0;
}

// The blocking palette transition uses the separately compiled canonical owner.

// Registry facts the Level 1 transports read (ClawNativeLevelTransport.h).
uint32_t claw_level_owner(uint32_t f,ClawLevelOwner *owner) {
    *owner=ClawLevelOwner{};
    const ClawCanonicalEntry *entry=claw_canonical_lookup(f);
    if (!entry) return 0;
    owner->owned=1;owner->sourceCapability=entry->sourceCapability;
    owner->inputMask=entry->sourceInputMask;owner->outputMask=entry->sourceOutputMask;
    owner->preserveMask=entry->sourcePreserveMask;
    owner->returnsX87=entry->returnKind == CLAW_CANONICAL_RETURN_X87;
    return 1;
}
uint32_t claw_level_owner_abi(uint32_t f,uint32_t *convention,uint32_t *argumentCount) {
    const ClawCanonicalEntry *entry=claw_canonical_lookup(f);
    if (!entry) return 0;
    *convention=entry->convention;*argumentCount=entry->argumentCount;
    return 1;
}
// Registry entry for an owned x87 result or environment (with the caller's exact stack).
ClawEntry claw_level_x87_entry(uint32_t f) {
    const ClawCanonicalEntry *entry=claw_canonical_lookup(f);
    return entry && (entry->returnKind == CLAW_CANONICAL_RETURN_X87 || entry->x87Environment) ? entry->entry : nullptr;
}
uint32_t claw_level_x87_environment(uint32_t f) {
    const ClawCanonicalEntry *entry=claw_canonical_lookup(f);
    return entry ? entry->x87Environment : 0;
}
