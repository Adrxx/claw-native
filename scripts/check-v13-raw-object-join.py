#!/usr/bin/env python3
"""Run the native raw-object composition against retained original join runs.

The reference (work/v13/original-raw-object-join-reference.py) executes the
original producers, field I/O, id map, reverse names and a real Rat child
serializer. This check loads the same object images at the same addresses into a
native host and compares stream traffic, callback order and final memory.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/v13-raw-object-join-check'
REFERENCE = ROOT / 'work/v13/raw-object-join-original-reference.json'
PROGRAM = '8f5069541a1c7d3f62896fb935ba591efa6fbfa4450798b96fe6f48f9cf396a0'
SOURCE = r'''
#include "V13RawObject.h"
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
constexpr uint32_t arena=0x03000000,imageBase=0x500000,reader=0x71000000,writer=0x71000004,callback=0x71000010;
struct Object {const char *name;uint32_t address,size;const char *before,*after;};
struct Event {int kind;uint32_t size,event,peer,serial;const char *bytes;uint32_t index,receiver,argc,arg0;};
struct Binding {uint32_t logic,methods;};
struct Run {
 const char *label;uint32_t entry,operation,result,consumed,globalBefore,globalAfter,nil;
 const char *payload,*output;
 uint32_t raw,logic,stream,child,other;
 std::vector<Object> objects;std::vector<Event> events;std::vector<Binding> bindings;
};
const std::vector<Run> runs={RUNS};
std::vector<uint8_t> unhex(const std::string &text) {
 std::vector<uint8_t> out;
 for(size_t i=0;i+1<text.size();i+=2)out.push_back(uint8_t(std::stoul(text.substr(i,2),nullptr,16)));
 return out;
}
struct Host {
 ClawHost host{};
 std::vector<uint8_t> memory=std::vector<uint8_t>(0x40000),image=std::vector<uint8_t>(0xb0000),stack=std::vector<uint8_t>(CLAW_STACK_END-CLAW_STACK_BASE);
 uint32_t next=arena+0x20000;
 const Run *run=nullptr;std::vector<uint8_t> payload,output;size_t cursor=0;
 struct Seen {int kind;uint32_t size,event,peer,serial;std::vector<uint8_t> bytes;uint32_t index=0,receiver=0,argc=0,arg0=0;};
 std::vector<Seen> seen;
 Host() {host.user=this;host.bytes=bytes;host.call=call;}
 static uint8_t *bytes(void *u,uint32_t a,uint32_t n) {
  auto &s=*static_cast<Host*>(u);
  if(a>=arena && uint64_t(a-arena)+n<=s.memory.size())return s.memory.data()+a-arena;
  if(a>=imageBase && uint64_t(a-imageBase)+n<=s.image.size())return s.image.data()+a-imageBase;
  if(a>=CLAW_STACK_BASE && uint64_t(a-CLAW_STACK_BASE)+n<=s.stack.size())return s.stack.data()+a-CLAW_STACK_BASE;
  return nullptr;
 }
 uint32_t get(uint32_t a) {uint32_t v;auto *p=bytes(this,a,4);assert(p);std::memcpy(&v,p,4);return v;}
 void put(uint32_t a,uint32_t v) {auto *p=bytes(this,a,4);assert(p);std::memcpy(p,&v,4);}
 static uint32_t call(void *u,const ClawCall *q) {
  auto &s=*static_cast<Host*>(u);
  if(q->function==reader || q->function==writer) {
   assert(q->argumentCount==2 && q->receiver==s.run->stream);
   bool input=q->function==reader;uint32_t address=q->arguments[0],n=q->arguments[1];
   auto *p=bytes(u,address,n);assert(p || !n);
   if(input) {
    assert(s.cursor+n<=s.payload.size());if(n)std::memcpy(p,s.payload.data()+s.cursor,n);s.cursor+=n;
   } else if(n)s.output.insert(s.output.end(),p,p+n);
   s.seen.push_back({input?1:0,n,0,0,0,std::vector<uint8_t>(p,p+n)});return n;
  }
  if(q->function==callback) {
   assert(q->argumentCount==1 && q->arguments[0]==s.run->raw);
   uint32_t logic=s.get(s.run->raw+0x7c);
   s.seen.push_back({2,0,s.get(logic+0x1c),s.get(s.run->raw+0x98),s.get(s.run->raw+0x184),{}});return 0;
  }
  if(q->function>=0x71000100 && q->function<0x71000110) {
   uint32_t index=(q->function-0x71000100)/2;
   assert(index<s.run->bindings.size());
   Seen e{3,0,0,0,0,{},index,q->receiver,q->argumentCount,q->argumentCount?q->arguments[0]:0};
   s.seen.push_back(e);
   if(q->argumentCount)s.put(s.run->bindings[index].logic+0x10,q->arguments[0]);
   return 1;
  }
  if(q->function==0x4fcaea) {
   assert(q->argumentCount==1);uint32_t p=s.next;s.next+=(std::max(1u,q->arguments[0])+15)&~15u;
   assert(s.next<arena+s.memory.size());return p;
  }
  if(q->function==0x4fcb13) {assert(q->argumentCount==1);return 0;}
  s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=q->function;return 0;
 }
 void load(const Run &r) {
  run=&r;
  for(const auto &o:r.objects) {auto data=unhex(o.before);assert(data.size()==o.size);std::memcpy(bytes(this,o.address,o.size),data.data(),o.size);}
  // Platform slots: the original used its own stub addresses.
  uint32_t vt=get(r.stream);put(vt+0x2c,reader);put(vt+0x30,writer);put(r.logic+0x10,callback);
  for(size_t i=0;i<r.bindings.size();++i) {uint32_t m=r.bindings[i].methods;put(m+0x14,0x71000100+uint32_t(i)*2);put(m+0x1c,0x71000101+uint32_t(i)*2);}
  put(0x52c668,r.nil);put(r.nil-12,0xffffffffu);
  put(0x5acd54,r.globalBefore);put(0x510ac4+4,0x4df6f0); // installed child serializer slot
  payload=unhex(r.payload);
 }
};
template<class T> void require(bool c,const T &message) {if(!c)throw std::runtime_error(message);}
int main() {
 unsigned failures=0;
 for(const auto &r:runs) {
  try {
   Host h;h.load(r);
   uint32_t args[]={r.stream,r.operation,0x12345678,0},result=0xdeadbeef;
   args[3]=0; // owner is only used by the read path below
   for(const auto &o:r.objects) if(std::string(o.name)=="owner")args[3]=o.address;
   uint32_t target=r.entry==0x4c7930?r.raw:r.logic;
   auto accepted=claw_v13_raw_object_entry(r.entry,target,args,4,&h.host,&result);
   require(accepted==1 && !h.host.fault,"entry rejected, fault "+std::to_string(h.host.fault)+" at "+std::to_string(h.host.faultAddress));
   require(result==r.result,"result");
   require(h.seen.size()==r.events.size(),"event count native "+std::to_string(h.seen.size())+" original "+std::to_string(r.events.size()));
   for(size_t i=0;i<r.events.size();++i) {
    const auto &e=r.events[i];const auto &n=h.seen[i];
    require(e.kind==n.kind,"event kind "+std::to_string(i));
    if(e.kind==3) require(e.index==n.index && e.receiver==n.receiver && e.argc==n.argc && e.arg0==n.arg0,"binding call "+std::to_string(i));
    else if(e.kind==2) require(e.event==n.event && e.peer==n.peer && e.serial==n.serial,"callback state "+std::to_string(i));
    else require(e.size==n.size && n.bytes==unhex(e.bytes),"stream event "+std::to_string(i));
   }
   require(h.output==unhex(r.output),"output bytes");
   require(h.cursor==r.consumed,"consumed bytes");
   require(h.get(0x5acd54)==r.globalAfter,"global word");
   for(const auto &o:r.objects) {
    auto expected=unhex(o.after);auto *actual=Host::bytes(&h,o.address,o.size);
    uint32_t vt=h.get(r.stream);
    for(uint32_t i=0;i<o.size;i+=4) {
     uint32_t at=o.address+i,want;std::memcpy(&want,expected.data()+i,4);
     // Platform stub addresses are the only intentionally different words.
     if(at==vt+0x2c)want=reader;else if(at==vt+0x30)want=writer;else if(at==r.logic+0x10)want=callback;
     else for(size_t b=0;b<r.bindings.size();++b) {if(at==r.bindings[b].methods+0x14)want=0x71000100+uint32_t(b)*2;if(at==r.bindings[b].methods+0x1c)want=0x71000101+uint32_t(b)*2;}
     uint32_t have;std::memcpy(&have,actual+i,4);
     require(have==want,std::string(o.name)+" word at +"+std::to_string(i)+" native "+std::to_string(have)+" original "+std::to_string(want));
    }
   }
   std::cout<<r.label<<": pass\n";
  } catch(const std::exception &e) {++failures;std::cerr<<r.label<<": "<<e.what()<<"\n";}
 }
 if(failures) {std::cerr<<failures<<" original joined runs failed\n";return 1;}
 std::cout<<"native raw-object join matches "<<runs.size()<<" original runs\n";
}
'''


def q(text):
    return json.dumps(text)


def run_source(row, op):
    run = row[op]
    entry = int(row['entry'], 16)
    after = {o['name']: o for o in run['after']['layout']}
    objects = ','.join('{%s,%d,%d,%s,%s}' % (q(o['name']), o['address'], o['size'], q(o['hex']), q(after[o['name']]['hex']))
                       for o in run['before']['layout'])
    events = ','.join('{%d,%d,%d,%d,%d,%s,%d,%d,%d,%d}' % (
        {'read': 1, 'write': 0, 'callback': 2, 'binding': 3}[e['kind']], e.get('size', 0), e.get('event', 0), e.get('peer', 0),
        e.get('serial', 0), q(e.get('bytes_hex', '')), e.get('index', 0), e.get('receiver', 0), len(e.get('args', [])),
        (e.get('args') or [0])[0]) for e in run['events'])
    bindings = ','.join('{%d,%d}' % (b['logic'], b['methods']) for b in run.get('bindings', []))
    a = run['addresses']
    label = '%s-%s-peer%d-lookup%d-names%d-%s' % (row['entry'], op, row['peer'], row['lookup'], row['names'], 'raw' if entry == 0x4c7930 else 'logic')
    payload = row['op4']['bytes_hex'] if op == 'op7' else ''
    return '{%s,%d,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d,%d,%d,%d,{%s},{%s},{%s}}' % (
        q(label), entry, int(op[2:]), run['result'], run['consumed'], run['before']['global_word'],
        run['after']['global_word'], run['before']['nil_pointer'], q(payload), q(run['bytes_hex']),
        a['raw'], a['logic'], a['stream'], a['child'], a['other'], objects, events, bindings)


def main():
    if float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        raise SystemExit('Wait until load is below 16')
    reference = json.loads(REFERENCE.read_text())
    assert reference['schema'] == 1 and reference['status'] == 'pass' and reference['program_sha256'] == PROGRAM
    for path, expected in reference['input_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Stale original join reference: ' + path
    OUT.mkdir(parents=True, exist_ok=True)
    runs = ',\n'.join(run_source(row, op) for row in reference['rows'] for op in ('op3', 'op8', 'op4', 'op7'))
    source = OUT / 'check.cpp'
    source.write_text(SOURCE.replace('RUNS', runs))
    binary = OUT / 'check'
    subprocess.run(['clang++', '-std=c++17', '-O1', '-I', str(ROOT / 'Sources'), str(source),
                    *[str(ROOT / 'Sources' / n) for n in (
                        'V13RawObjectAdapter.cpp', 'V13RawLifecycleRuntime.cpp', 'V13RawFieldsRuntime.cpp',
                        'V13ContactBindingsRuntime.cpp', 'V13RawChildrenRuntime.cpp', 'V13RawStreamServices.cpp')],
                    '-o', str(binary)], check=True)
    checked = subprocess.run([str(binary)], capture_output=True, text=True)
    (OUT / 'check.log').write_text(checked.stdout + checked.stderr)
    print(checked.stdout, end='')
    print(checked.stderr, end='')
    result = dict(status='pass' if checked.returncode == 0 else 'fail', check='v13_raw_object_native_join',
                  original_runs=sum(4 for _ in reference['rows']),
                  reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                  scope='Native composition of producer, field I/O, id map, reverse names, child serializer, CString and map services over original join runs. '
                        'The original has no shipped caller; app reachability and the v1.0 layout projection are separate.')
    print(json.dumps(result))
    return 0 if checked.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
