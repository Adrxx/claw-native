#include "ClawNativeMenuInterface.h"
#include <cassert>
#include <cmath>
#include <cstring>
#include <limits>
#include <initializer_list>
#include <cstdio>

static ClawX87State state() {
    ClawX87State value{};
    value.size=sizeof(value);value.version=CLAW_X87_VERSION;value.control=0x023f;
    value.count=1;value.pushCount=1;value.status=7<<11;
    // An existing 1.0 below the new result must survive the CRT call.
    value.slots[0].significand=uint64_t(1)<<63;value.slots[0].signExponent=16383;
    return value;
}
static ClawCall call(double input,ClawX87State &fp) {
    ClawCall value{};value.function=0x4a4250;value.argumentCount=2;
    value.x87ArgumentCount=CLAW_X87_EXACT;value.x87State=&fp;
    uint64_t bits=0;std::memcpy(&bits,&input,8);
    value.arguments[0]=uint32_t(bits);value.arguments[1]=uint32_t(bits>>32);
    return value;
}
int main() {
    for(double input:{-2.5,-1.0,-0.2,-0.0,0.0,0.2,1.0,1.2,16.999,500.0}) {
        auto fp=state();const auto tail=fp.slots[0];auto request=call(input,fp);uint32_t out=99;
        assert(claw_native_menu_math_service(&request,&out)==1);
        assert(out==0 && fp.returned==1 && fp.count==2 && fp.status==(6<<11));
        assert(std::memcmp(&tail,&fp.slots[1],sizeof(tail))==0);
        const auto &slot=fp.slots[0];
        double result=std::ldexp(double(slot.significand),int(slot.signExponent&0x7fff)-16383-63);
        if(slot.signExponent&0x8000) result=-result;
        assert(result==std::ceil(input) && std::signbit(result)==std::signbit(std::ceil(input)));
    }
    for(double input:{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) {
        auto fp=state();auto request=call(input,fp);uint32_t out=99;
        assert(claw_native_menu_math_service(&request,&out)==0 && fp.returned==0);
    }
    for(unsigned invalid=0;invalid<3;++invalid) {
        auto fp=state();auto request=call(1.2,fp);uint32_t out=99;
        if(invalid==0) request.argumentCount=1;
        if(invalid==1) fp.popCount=1;
        if(invalid==2) fp.pushCount=0;
        assert(claw_native_menu_math_service(&request,&out)==0 && fp.returned==0);
    }
    // Independent x87 CPU reference: FLDCW 0x023f, FLD binary64,
    // FSIN/FCOS, FSTP binary64. Include representative Omar ring angles.
    struct Trig {uint32_t op;uint64_t input,expected;};
    const Trig trig[]={
        {22,0x0000000000000000ull,0x0000000000000000ull},
        {22,0x8000000000000000ull,0x8000000000000000ull},
        {22,0x3fe0c152382d7365ull,0x3fdfffffffffffffull},
        {22,0x3ff921fb54442d18ull,0x3ff0000000000000ull},
        {22,0x400921fb54442d18ull,0x3ca1a62633145c07ull},
        {22,0x401921fb54442d18ull,0xbcb1a62633145c07ull},
        {22,0xbff0c152382d7365ull,0xbfebb67ae8584caaull},
        {22,0x3fe26e40d7653223ull,0x3fe16daed770771dull},
        {22,0x4014bc08f251d867ull,0xbfec83201d3d2c6dull},
        {23,0x0000000000000000ull,0x3ff0000000000000ull},
        {23,0x8000000000000000ull,0x3ff0000000000000ull},
        {23,0x3fe0c152382d7365ull,0x3febb67ae8584cabull},
        {23,0x3ff921fb54442d18ull,0x3c91a62633145c07ull},
        {23,0x400921fb54442d18ull,0xbff0000000000000ull},
        {23,0x401921fb54442d18ull,0x3ff0000000000000ull},
        {23,0xbff0c152382d7365ull,0x3fe0000000000001ull},
        {23,0x3fe26e40d7653223ull,0x3fead663a8ae2fdcull},
        {23,0x4014bc08f251d867ull,0x3fdd0e2e2b44ddfeull},
    };
    for (const auto &fixture:trig) {
        double input;std::memcpy(&input,&fixture.input,8);
        auto fp=state();fp.count=2;fp.popCount=fp.pushCount=1;fp.status=(6<<11)|0x400;
        fp.slots[1]=fp.slots[0];const auto tail=fp.slots[1];
        auto &slot=fp.slots[0];slot={};
        if(input!=0) {int exponent;const double part=std::frexp(std::fabs(input),&exponent);
            slot.significand=uint64_t(std::ldexp(part,64));slot.signExponent=exponent+16382;}
        if(std::signbit(input)) slot.signExponent|=0x8000;
        ClawCall request{};request.x87ArgumentCount=CLAW_X87_STEP;request.x87Operation=fixture.op;request.x87State=&fp;
        uint32_t out=99;assert(claw_native_menu_math_service(&request,&out)==1);
        double actual=std::ldexp(double(fp.slots[0].significand),int(fp.slots[0].signExponent&0x7fff)-16383-63);
        if(fp.slots[0].signExponent&0x8000) actual=-actual;
        uint64_t bits;std::memcpy(&bits,&actual,8);assert(bits==fixture.expected);
        assert(fp.count==2 && fp.status==(6<<11) && fp.returned==1 && fp.control==0x023f);
        assert(std::memcmp(&tail,&fp.slots[1],sizeof(tail))==0);
    }
    std::puts("PASS native Omar sin/cos: 18 CPU-reference results, signed zero, tail, TOP and C2");
    std::puts("PASS native menu ceil: values, signed zero, preserved x87 tail/TOP and invalid-call rejection");
}
