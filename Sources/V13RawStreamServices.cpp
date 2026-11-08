#include "V13RawStreamServices.h"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>
#include <string>
#include <vector>

extern "C" uint32_t claw_v13_raw_children_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
// Synthetic native platform headers never replace an allocation in the parent.
constexpr uint32_t platformBase = 0x7ef00000;
struct Stream {
    uint32_t object=0, descriptor=0, buffer=0, capacity=0, used=0;
    bool reading=false, failed=false, destroyed=false;
    std::string input;
    std::array<uint8_t,32> header{};
};
struct Services {
    ClawHost &parent;
    ClawHost host;
    std::map<uint32_t,Stream> streams;
    std::array<uint32_t,2> virtualBase{};
    uint32_t nextDescriptor=platformBase+0x100;
    uint32_t binary,operation;
    // The original number scanner fills a 28-byte stack buffer and terminates it
    // in place, so a full token zeroes the low byte of the caller's saved frame
    // pointer. The derived serializer keeps its operation in that register.
    uint32_t *derivedOperation=nullptr;
    Services(ClawHost &p,uint32_t b,uint32_t op):parent(p),host(p),binary(b),operation(op) {
        host.user=this; host.bytes=bytes; host.call=call;
    }
    uint32_t fail(uint32_t address) {
        host.fault=CLAW_FAULT_HOST; host.faultAddress=address; return 0;
    }
    static uint8_t *bytes(void *u,uint32_t address,uint32_t count) {
        auto &s=*static_cast<Services*>(u);
        if(address>=platformBase && uint64_t(address-platformBase)+count<=sizeof(s.virtualBase))
            return reinterpret_cast<uint8_t*>(s.virtualBase.data())+address-platformBase;
        for(auto &[key,v]:s.streams)
            if(address>=v.descriptor && uint64_t(address-v.descriptor)+count<=v.header.size())
                return v.header.data()+address-v.descriptor;
        return s.parent.bytes?s.parent.bytes(s.parent.user,address,count):nullptr;
    }
    uint8_t *span(uint32_t address,uint32_t count) {
        if(host.fault)return nullptr;
        auto *p=bytes(this,address,count);
        if(!p && count) fail(address);
        return p;
    }
    uint32_t get(uint32_t address) {
        uint32_t v=0; if(auto *p=span(address,4))std::memcpy(&v,p,4); return v;
    }
    void put(uint32_t address,uint32_t v) {
        if(auto *p=span(address,4))std::memcpy(p,&v,4);
    }
    uint32_t physical(const ClawCall &q) {
        if(host.fault)return 0;
        bool allocation=(q.function==0x4fcaea || q.function==0x4fcb13) &&
            q.receiver==0 && q.argumentCount==1;
        bool transfer=binary && (operation==4 || operation==7) && q.receiver==binary &&
            q.argumentCount==2 && q.function==get(get(binary)+(operation==4?0x30:0x2c));
        if(host.fault)return 0;
        if(!allocation && !transfer)return fail(q.function);
        if(!parent.call)return fail(q.function);
        auto result=parent.call(parent.user,&q);
        if(parent.fault) {host.fault=parent.fault;host.faultAddress=parent.faultAddress;}
        return result;
    }
    Stream *stream(uint32_t object) {
        auto it=streams.find(object);
        if(it==streams.end() || it->second.destroyed) {fail(object);return nullptr;}
        return &it->second;
    }
    void append(Stream &s,const std::string &text) {
        if(s.reading || s.failed)return;
        auto n=std::min<size_t>(text.size(),s.capacity-s.used);
        if(n)if(auto *p=span(s.buffer+s.used,uint32_t(n)))std::memcpy(p,text.data(),n);
        s.used+=uint32_t(n);s.failed=n!=text.size();
        put(s.descriptor+0x1c,s.buffer+s.used);
    }
    static std::string decimal(double value) {
        if(std::isnan(value))return std::signbit(value)?"-1.#QNAN":"1.#QNAN";
        if(std::isinf(value))return std::signbit(value)?"-1.#INF":"1.#INF";
        if(value==0)return "0";
        std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(6)<<value;
        auto text=out.str();auto e=text.find('e');
        if(e!=std::string::npos && text.size()-e-2<3)text.insert(e+2,3-(text.size()-e-2),'0');
        return text;
    }
    template<class T> bool extract(Stream &s,T &value) {
        if(!s.reading || s.failed)return false;
        std::istringstream in(s.input.substr(s.used));in.imbue(std::locale::classic());
        T parsed{};in>>parsed;
        if(in.fail()) {s.failed=true;return false;}
        auto consumed=in.tellg();s.used=consumed<0?uint32_t(s.input.size()):s.used+uint32_t(consumed);
        value=parsed;return true;
    }
    // Number token grammar of the original extractor: optional sign, digits,
    // one point and a marked exponent, at most 28 characters. A token without
    // mantissa digits, or one that fills the buffer, sets the fail state but is
    // still converted and stored. Out-of-range values convert without error.
    bool extractDouble(Stream &s,double &value) {
        if(!s.reading || s.failed)return false;
        size_t at=s.used;
        while(at<s.input.size() && std::isspace(static_cast<unsigned char>(s.input[at])))++at;
        constexpr size_t capacity=28;
        std::string token;uint32_t mantissa=0,exponent=0,point=0;
        while(token.size()<capacity && at<s.input.size()) {
            char c=s.input[at];
            if((token.empty() || exponent==1) && (c=='-' || c=='+')) {}
            else if(c=='.' && exponent==0 && point==0) point=1;
            else if((c=='e' || c=='E') && exponent==0) {++point;exponent=1;}
            else if(c>='0' && c<='9') {if(exponent)++exponent;else ++mantissa;}
            else break;
            token.push_back(c);++at;
        }
        if(exponent==1 && !token.empty()) {token.pop_back();--at;}
        s.used=uint32_t(at);
        bool full=token.size()==capacity;
        if(full && derivedOperation)*derivedOperation&=~0xffu;
        if(!mantissa || full)s.failed=true;
        if(token.empty())return false;
        errno=0;value=std::strtod(token.c_str(),nullptr);
        if(errno==ERANGE && value==0)value=0.0;
        return true;
    }
    // Mirrors the original growth: the count rounds up to whole words, and a
    // block of up to one word is still read from the inline slot, so the pointer
    // stored by the first growth is later treated as bit storage.
    bool setBit(uint32_t object,int32_t index) {
        if(index<0 || index>=0x100000) {fail(object);return false;}
        uint32_t count=get(object+8);
        if(host.fault)return false;
        if(uint32_t(index)>=count) {
            uint32_t words=(uint32_t(index)+32)/32,oldWords=(count+31)/32;
            ClawCall allocate{};allocate.function=0x4fcaea;allocate.argumentCount=1;allocate.arguments[0]=words*4;
            uint32_t storage=physical(allocate);if(!storage) {fail(allocate.function);return false;}
            auto *target=span(storage,words*4);if(!target)return false;
            std::memset(target,0,words*4);
            if(count>32) {
                uint32_t old=get(object+12);auto *source=span(old,std::min(oldWords,words)*4);if(!source)return false;
                std::memcpy(target,source,std::min(oldWords,words)*4);
                for(uint32_t i=count/32;i<words;++i)std::memset(target+i*4,0,4);
                ClawCall release{};release.function=0x4fcb13;release.argumentCount=1;release.arguments[0]=old;physical(release);
            } else {
                uint32_t inlineWord=get(object+12);std::memcpy(target,&inlineWord,4);
            }
            put(object+12,storage);put(object+8,words*32);
            count=words*32;
        }
        uint32_t bits=count<=32?object+12:get(object+12);
        uint32_t word=bits+(uint32_t(index)/32)*4;put(word,get(word)|(1u<<(uint32_t(index)%32)));return !host.fault;
    }
    uint32_t service(const ClawCall &q) {
        const auto *a=q.arguments;
        switch(q.function) {
        case 0x4f9463: case 0x4f9398: {
            bool input=q.function==0x4f9398;
            if(q.argumentCount!=(input?3u:4u) || (input?a[2]!=1:(a[2]!=2 || a[3]!=1)))return fail(q.function);
            if(streams.count(q.receiver))return fail(q.function);
            Stream s;s.object=q.receiver;s.descriptor=nextDescriptor;nextDescriptor+=0x40;
            s.buffer=a[0];s.capacity=a[1];s.reading=input;
            if(parent.bytes && (parent.bytes(parent.user,platformBase,8) || parent.bytes(parent.user,s.descriptor,32)))return fail(q.function);
            if(input && a[1]) {auto *p=span(a[0],a[1]);if(!p)return 0;s.input.assign(reinterpret_cast<char*>(p),a[1]);}
            streams.emplace(q.receiver,std::move(s));
            put(q.receiver,platformBase);put(q.receiver+4,streams.at(q.receiver).descriptor);
            put(streams.at(q.receiver).descriptor+0x18,a[0]);put(streams.at(q.receiver).descriptor+0x1c,a[0]);
            return q.receiver;
        }
        case 0x4f90c7:
            if(q.argumentCount)return fail(q.function);
            for(auto &[key,s]:streams)if(s.descriptor==q.receiver && !s.reading && !s.destroyed)return s.buffer;
            return fail(q.function);
        case 0x4f9511: case 0x4f9425: case 0x4f959e: {
            if(q.argumentCount)return fail(q.function);
            for(auto it=streams.begin();it!=streams.end();++it) {
                auto &s=it->second;
                if(q.receiver==s.object+(s.reading?12u:8u)) {
                    if(q.function==0x4f959e) {if(!s.destroyed)return fail(q.function);streams.erase(it);}
                    else {if(s.destroyed || (q.function==0x4f9425)!=s.reading)return fail(q.function);s.destroyed=true;}
                    return 0;
                }
            }
            return fail(q.function);
        }
        case 0x4f8db1: case 0x4f8d00: {
            if(q.argumentCount!=(q.function==0x4f8db1?2u:1u))return fail(q.function);
            auto *s=stream(q.receiver);if(!s || s->reading)return fail(q.function);
            if(q.function==0x4f8db1) {double d;std::memcpy(&d,a,8);append(*s,decimal(d));}
            else append(*s,std::to_string(int32_t(a[0])));
            return q.receiver;
        }
        case 0x4f8f70: case 0x4f8ed3: {
            if(q.argumentCount!=1)return fail(q.function);
            auto *s=stream(q.receiver);if(!s || !s->reading)return fail(q.function);
            if(q.function==0x4f8f70) {double d;if(extractDouble(*s,d))if(auto *p=span(a[0],8))std::memcpy(p,&d,8);}
            else {int32_t n;if(extract(*s,n))put(a[0],uint32_t(n));}
            return q.receiver;
        }
        case 0x4fa4f0: {
            if(q.argumentCount!=2)return fail(q.function);
            auto *s=stream(a[0]);if(!s || s->reading)return fail(q.function);
            uint32_t count=get(a[1]+8),bits=count<=32?a[1]+12:get(a[1]+12);
            if(count>0x100000)return fail(q.function);
            std::string text="[";bool first=true;
            for(uint32_t i=0;i<count;++i)if(get(bits+(i/32)*4)&(1u<<(i%32))) {
                if(!first)text+=' ';text+=std::to_string(i);first=false;
            }
            append(*s,text+"]");return a[0];
        }
        case 0x4fa5a0: {
            if(q.argumentCount!=2)return fail(q.function);
            auto *s=stream(a[0]);if(!s || !s->reading)return fail(q.function);
            auto white=[&]() {while(s->used<s->input.size() && (s->input[s->used]==' ' || s->input[s->used]=='\t' || s->input[s->used]=='\n' || s->input[s->used]=='\r'))++s->used;};
            // Extraction adds indices to the existing bitset, including its
            // prior count and bits. It is not a replacement assignment.
            white();bool bracket=s->used<s->input.size() && s->input[s->used]=='[';
            if(bracket)++s->used;
            while(!s->failed) {
                white();
                if(bracket && s->used<s->input.size() && s->input[s->used]==']') {++s->used;break;}
                int32_t index;if(!extract(*s,index))break;
                if(bracket && index==-1)break;
                if(!setBit(a[1],index))return 0;
                if(!bracket)break;
                white();if(s->used<s->input.size() && s->input[s->used]==',')++s->used;
            }
            return a[0];
        }
        // The remaining game and binary stream operations belong to the
        // elected parent. No unknown platform request is accepted as success.
        default:return physical(q);
        }
    }
    static uint32_t call(void *u,const ClawCall *q) {
        auto &s=*static_cast<Services*>(u);if(!q)return s.fail(0);return s.service(*q);
    }
};
}
extern "C" uint32_t claw_v13_raw_child_native_entry(uint32_t function,uint32_t receiver,
    const uint32_t *arguments,uint32_t count,ClawHost *parent,uint32_t *result) {
    if(!parent || !parent->bytes || !parent->call || !arguments || count!=4 ||
        (function!=0x4df6f0 && function!=0x4df240))return 0;
    Services services(*parent,arguments[0],arguments[1]);
    uint32_t local[4]={arguments[0],arguments[1],arguments[2],arguments[3]};
    if(function==0x4df6f0 && arguments[1]==7)services.derivedOperation=&local[1];
    auto accepted=claw_v13_raw_children_entry(function,receiver,local,count,&services.host,result);
    if(services.host.fault) {parent->fault=services.host.fault;parent->faultAddress=services.host.faultAddress;}
    return accepted;
}
