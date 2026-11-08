// Native composition of the v1.3 raw-object serialization interface.
//
// Producers 0x4c7930/0x4d6590 call field I/O, reverse lookup, LogicBump
// setters and the enemy child serializers. This adapter routes each of those to
// its admitted body or native service and leaves the binary stream, allocator
// and lifecycle callback with the parent. CString and MFC map operations are
// native services over the guest structures the game reads.
#include "V13RawObject.h"
#include "V13RawStreamServices.h"
#include <cstring>

extern "C" uint32_t claw_v13_raw_lifecycle_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_raw_fields_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_contact_bindings_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
namespace {
constexpr uint32_t emptyString = 0x52c668;
constexpr uint32_t allocate = 0x4fcaea, release = 0x4fcb13;
struct View {
    ClawHost &parent;
    ClawHost host;
    explicit View(ClawHost &p):parent(p),host(p) {host.user=this;host.bytes=bytes;host.call=call;}
    static uint8_t *bytes(void *user,uint32_t address,uint32_t count) {
        auto &s=*static_cast<View*>(user);
        return s.parent.bytes?s.parent.bytes(s.parent.user,address,count):nullptr;
    }
    uint32_t fail(uint32_t address) {host.fault=CLAW_FAULT_HOST;host.faultAddress=address;return 0;}
    uint32_t get(uint32_t address) {
        uint32_t value=0;auto *p=bytes(this,address,4);
        if(!p)return fail(address);
        std::memcpy(&value,p,4);return value;
    }
    void put(uint32_t address,uint32_t value) {
        auto *p=bytes(this,address,4);
        if(!p) {fail(address);return;}
        std::memcpy(p,&value,4);
    }
    uint32_t parentCall(uint32_t function,uint32_t argument) {
        ClawCall request{};request.function=function;request.argumentCount=1;request.arguments[0]=argument;
        auto result=parent.call?parent.call(parent.user,&request):fail(function);
        if(parent.fault) {host.fault=parent.fault;host.faultAddress=parent.faultAddress;}
        return result;
    }
    // CString data pointers carry {references, length, capacity} just before the text.
    uint32_t nilData() {return get(emptyString);}
    bool isNil(uint32_t data) {return data==nilData();}
    int32_t references(uint32_t data) {return int32_t(get(data-12));}
    void releaseString(uint32_t slot) {
        uint32_t data=get(slot);
        if(host.fault || isNil(data))return;
        int32_t count=references(data)-1;put(data-12,uint32_t(count));
        if(count<=0)parentCall(release,data-12);
        put(slot,nilData());
    }
    void shareString(uint32_t slot,uint32_t source) {
        if(get(slot)==source)return;
        if(isNil(source) || references(source)<0) {
            // A locked or empty source is copied, never shared.
            uint32_t length=get(source-12+4);
            releaseString(slot);
            if(!length || host.fault)return;
            uint32_t block=parentCall(allocate,length+13);
            if(!block)return;
            put(block,1);put(block+4,length);put(block+8,length);
            for(uint32_t i=0;i<=length;++i) if(auto *to=bytes(this,block+12+i,1))if(auto *from=bytes(this,source+i,1))*to=*from;
            put(slot,block+12);return;
        }
        releaseString(slot);put(slot,source);put(source-12,uint32_t(references(source)+1));
    }
    void assignText(uint32_t slot,uint32_t text) {
        uint32_t length=0;
        while(text && !host.fault) {auto *c=bytes(this,text+length,1);if(!c) {fail(text+length);break;}if(!*c)break;++length;}
        if(host.fault)return;
        if(!length) {releaseString(slot);return;}
        uint32_t data=get(slot);
        if(isNil(data) || references(data)>1 || int32_t(get(data-12+8))<int32_t(length)) {
            releaseString(slot);
            uint32_t block=parentCall(allocate,length+13);
            if(!block)return;
            put(block,1);put(block+8,length);put(slot,block+12);data=block+12;
        }
        put(data-12+4,length);
        for(uint32_t i=0;i<=length;++i) {
            auto *to=bytes(this,data+i,1);auto *from=i<length?bytes(this,text+i,1):nullptr;
            if(to)*to=from?*from:0;
        }
    }
    uint32_t equalText(uint32_t data,uint32_t text) {
        for(uint32_t i=0;;++i) {
            auto *a=bytes(this,data+i,1);auto *b=bytes(this,text+i,1);
            if(!a || !b)return fail(a?text+i:data+i);
            if(*a!=*b)return 0;
            if(!*a)return 1;
        }
    }
    // Lookups walk the same hash tables the game reads: tables at +4/+8,
    // associations {next,key,value} (pointer map) or {next,hash,key,value}.
    uint32_t lookupId(uint32_t map,uint32_t id,uint32_t output) {
        uint32_t size=get(map+8),table=get(map+4);
        if(!size || !table || host.fault)return 0;
        for(uint32_t node=get(table+((id>>4)%size)*4);node && !host.fault;node=get(node))
            if(get(node+4)==id) {put(output,get(node+8));return 1;}
        return 0;
    }
    uint32_t lookupName(uint32_t map,uint32_t text,uint32_t output) {
        uint32_t size=get(map+8),table=get(map+4);
        if(!size || !table || host.fault)return 0;
        uint32_t hash=0;
        for(uint32_t i=0;;++i) {
            auto *c=bytes(this,text+i,1);
            if(!c)return fail(text+i);
            if(!*c)break;
            hash=(hash<<5)+hash+*c;
        }
        for(uint32_t node=get(table+(hash%size)*4);node && !host.fault;node=get(node))
            if(equalText(get(node+8),text)) {put(output,get(node+12));return 1;}
        return 0;
    }
    void nextAssociation(uint32_t map,uint32_t position,uint32_t key,uint32_t value) {
        uint32_t size=get(map+8),table=get(map+4),node=get(position);
        if(host.fault)return;
        if(node==0xffffffffu) {
            node=0;
            for(uint32_t i=0;i<size && table && !node;++i)node=get(table+i*4);
        }
        if(!node || !table) {put(position,0);return;}
        uint32_t next=get(node);
        if(!next) {
            uint32_t bucket=get(node+4)%size;
            for(uint32_t i=bucket+1;i<size && !next;++i)next=get(table+i*4);
        }
        put(position,next);
        shareString(key,get(node+8));
        put(value,get(node+12));
    }
    static uint32_t call(void *user,const ClawCall *q) {
        auto &s=*static_cast<View*>(user);
        if(!q)return s.fail(0);
        const auto *a=q->arguments;uint32_t result=0;
        auto ok=[&](bool accepted) {
            if(!accepted && !s.host.fault)s.fail(q->function);
            return result;
        };
        switch(q->function) {
        case 0x4c7ab0: case 0x4c7f10: case 0x4d6680: case 0x4d6aa0: case 0x4d7010:
            return ok(claw_v13_raw_fields_entry(q->function,q->receiver,a,q->argumentCount,&s.host,&result));
        case 0x4c7690: case 0x4c7770: case 0x4c7850:
            return ok(claw_v13_contact_bindings_entry(q->function,q->receiver,a,q->argumentCount,&s.host,&result));
        case 0x4ce9b0:
            return ok(claw_v13_raw_lifecycle_entry(q->function,q->receiver,a,q->argumentCount,&s.host,&result));
        case 0x4df6f0: case 0x4df240:
            return ok(claw_v13_raw_child_native_entry(q->function,q->receiver,a,q->argumentCount,&s.host,&result));
        case 0x4fc9aa:
            if(q->argumentCount!=2)return s.fail(q->function);
            return s.lookupId(q->receiver,a[0],a[1]);
        case 0x4fc6b4:
            if(q->argumentCount!=2)return s.fail(q->function);
            return s.lookupName(q->receiver,a[0],a[1]);
        case 0x4fc525:
            if(q->argumentCount!=3)return s.fail(q->function);
            s.nextAssociation(q->receiver,a[0],a[1],a[2]);return 0;
        case 0x4fcb1e:
            if(q->argumentCount!=1)return s.fail(q->function);
            s.put(q->receiver,s.nilData());s.shareString(q->receiver,s.get(a[0]));return q->receiver;
        case 0x4fcda9:
            if(q->argumentCount)return s.fail(q->function);
            s.releaseString(q->receiver);return 0;
        case 0x4fcee6:
            if(q->argumentCount!=1)return s.fail(q->function);
            s.assignText(q->receiver,a[0]);return q->receiver;
        default: {
            if(!s.parent.call)return s.fail(q->function);
            result=s.parent.call(s.parent.user,q);
            if(s.parent.fault) {s.host.fault=s.parent.fault;s.host.faultAddress=s.parent.faultAddress;}
            return result;
        }
        }
    }
};
}
extern "C" uint32_t claw_v13_raw_object_entry(uint32_t function,uint32_t receiver,
    const uint32_t *arguments,uint32_t count,ClawHost *parent,uint32_t *result) {
    if(!parent || !parent->bytes || !parent->call || !arguments || !result || count!=4 || parent->fault)return 0;
    if(function!=0x4c7930 && function!=0x4d6590)return 0;
    View view(*parent);
    auto accepted=claw_v13_raw_lifecycle_entry(function,receiver,arguments,count,&view.host,result);
    if(view.host.fault) {parent->fault=view.host.fault;parent->faultAddress=view.host.faultAddress;return 0;}
    return accepted;
}
