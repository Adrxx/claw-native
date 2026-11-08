#!/usr/bin/env python3
"""Compare native child storage/streams against retained joined original runs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/v13-raw-children-check'
REFERENCE = ROOT / 'work/v13/raw-child-original-reference.json'
PROGRAM = '8f5069541a1c7d3f62896fb935ba591efa6fbfa4450798b96fe6f48f9cf396a0'
SOURCE = r'''
#include "V13RawStreamServices.h"
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
constexpr uint32_t base=0x10000000,child=base,owner=base+0x2000,logic=base+0x2400,stream=base+0x3000,table=base+0x3100;
constexpr uint32_t reader=0x71000000,writer=0x71000004;
struct Profile {
 const char *name;uint32_t function,count;
 std::vector<uint32_t> bits;std::vector<uint64_t> values;
 uint32_t integer;std::vector<uint32_t> tail,baseWords;uint32_t global,readBitCount;std::vector<uint32_t> readBitWords;
 std::vector<uint8_t> output;
 std::vector<uint32_t> sizes,readSizes;uint32_t consumed;
 std::vector<uint64_t> numericAfter;
 uint32_t integerAfter;std::vector<uint32_t> tailAfter,baseAfter;
 uint32_t globalAfter,bitCountAfter;std::vector<uint32_t> bitWordsAfter;
};
const std::vector<Profile> profiles={PROFILES};
const std::vector<uint32_t> offsets={OFFSETS};
struct Host {
 ClawHost host{};
 std::vector<uint8_t> memory=std::vector<uint8_t>(0x40000),stack=std::vector<uint8_t>(CLAW_STACK_END-CLAW_STACK_BASE);
 uint32_t global=0,next=base+0x4000;bool input=false,failAllocation=false,failBinary=false;
 size_t cursor=0;std::vector<uint8_t> payload;std::vector<uint32_t> sizes,allocations,frees;
 Host() {host.user=this;host.bytes=bytes;host.call=call;put(owner+0x7c,logic);put(stream,table);put(table+0x2c,reader);put(table+0x30,writer);}
 static uint8_t *bytes(void *u,uint32_t a,uint32_t n) {
  auto &s=*static_cast<Host*>(u);
  if(a>=base && uint64_t(a-base)+n<=s.memory.size())return s.memory.data()+a-base;
  if(a>=CLAW_STACK_BASE && uint64_t(a-CLAW_STACK_BASE)+n<=s.stack.size())return s.stack.data()+a-CLAW_STACK_BASE;
  if(a>=0x5acd54 && uint64_t(a-0x5acd54)+n<=4)return reinterpret_cast<uint8_t*>(&s.global)+a-0x5acd54;
  return nullptr;
 }
 uint32_t get(uint32_t a) {uint32_t v;auto *p=bytes(this,a,4);assert(p);std::memcpy(&v,p,4);return v;}
 uint64_t get64(uint32_t a) {uint64_t v;auto *p=bytes(this,a,8);assert(p);std::memcpy(&v,p,8);return v;}
 void put(uint32_t a,uint32_t v) {auto *p=bytes(this,a,4);assert(p);std::memcpy(p,&v,4);}
 void put64(uint32_t a,uint64_t v) {auto *p=bytes(this,a,8);assert(p);std::memcpy(p,&v,8);}
 static uint32_t call(void *u,const ClawCall *q) {
  auto &s=*static_cast<Host*>(u);
  if(q->function==reader || q->function==writer) {
   assert(q->receiver==stream && q->argumentCount==2);
   if(s.failBinary) {s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=q->function;return 0;}
   assert((q->function==reader)==s.input);
   uint32_t address=q->arguments[0],n=q->arguments[1];auto *p=bytes(u,address,n);assert(p || !n);
   s.sizes.push_back(n);
   if(s.input) {assert(s.cursor+n<=s.payload.size());if(n)std::memcpy(p,s.payload.data()+s.cursor,n);s.cursor+=n;}
   else if(n)s.payload.insert(s.payload.end(),p,p+n);
   return n;
  }
  if(q->function==0x4fcaea) {
   assert(q->argumentCount==1);
   if(s.failAllocation) {s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=q->function;return 0;}
   uint32_t n=q->arguments[0],p=s.next;s.next+=(std::max(1u,n)+15)&~15u;
   assert(s.next<base+s.memory.size());s.allocations.push_back(p);return p;
  }
  if(q->function==0x4fcb13) {assert(q->argumentCount==1);s.frees.push_back(q->arguments[0]);return 0;}
  s.host.fault=CLAW_FAULT_HOST;s.host.faultAddress=q->function;return 0;
 }
 void setup(const Profile &p,bool reading) {
  input=reading;global=reading?0x98765432:p.global;
  uint32_t count=reading?p.readBitCount:p.count;
  put(child+0x20,count);uint32_t bits=count<=32?child+0x24:base+0x3200;
  if(count>32)put(child+0x24,bits);
  if(reading)for(size_t i=0;i<p.readBitWords.size();++i)put(bits+uint32_t(i)*4,p.readBitWords[i]);
  else for(auto i:p.bits)put(bits+(i/32)*4,get(bits+(i/32)*4)|(1u<<(i%32)));
  for(size_t i=0;i<offsets.size();++i) {
   uint64_t value=p.values[i%p.values.size()];
   if(reading) {double d=-123.456789-double(i);std::memcpy(&value,&d,8);}
   put64(child+0x38+offsets[i],value);
  }
  put(child+0xf0,reading?0x87654321:p.integer);
  const uint32_t rt[]={0xa1a1a1a1,0xb2b2b2b2,0xc3c3c3c3,0xd4d4d4d4};
  for(unsigned i=0;i<4;++i)put(child+0x140+i*4,reading?rt[i]:p.tail[i]);
  const uint32_t rb[]={0x11111111,0x22222222,0x33333333};
  for(unsigned i=0;i<3;++i)put(child+(i==2?0x30:0x28+i*4),reading?rb[i]:p.baseWords[i]);
  const uint32_t os[]={4,8,12,16,20},vs[]={0x44444444,0x88888888,0xcccccccc,0x10101010,0x14141414};
  for(unsigned i=0;i<5;++i)put(child+os[i],vs[i]);
 }
 uint32_t run(uint32_t f,uint32_t op,uint32_t target=stream) {
  uint32_t a[]={target,op,0x12345678,owner},result=0xdeadbeef;
  auto accepted=claw_v13_raw_child_native_entry(f,child,a,4,&host,&result);
  assert(accepted==(host.fault?0u:1u));return result;
 }
 static void require(bool condition,const std::string &message) {if(!condition)throw std::runtime_error(message);}
 void compare(const Profile &p) {
  for(size_t i=0;i<offsets.size();++i)if(get64(child+0x38+offsets[i])!=p.numericAfter[i]) {
   throw std::runtime_error("numeric offset "+std::to_string(offsets[i])+" native "+std::to_string(get64(child+0x38+offsets[i]))+" original "+std::to_string(p.numericAfter[i]));
  }
  require(get(child+0xf0)==p.integerAfter,"integer field");
  for(unsigned i=0;i<4;++i)require(get(child+0x140+i*4)==p.tailAfter[i],"tail field "+std::to_string(i));
  const uint32_t os[]={4,8,12,16,20,0x28,0x2c,0x30};
  for(unsigned i=0;i<8;++i) {
   uint32_t expected=p.baseAfter[i];if(expected==0xffff0001)expected=owner;if(expected==0xffff0002)expected=logic;
   require(get(child+os[i])==expected,"base offset "+std::to_string(os[i])+" native "+std::to_string(get(child+os[i]))+" original "+std::to_string(expected));
  }
  require(global==p.globalAfter,"global word");require(get(child+0x20)==p.bitCountAfter,"bit count");
  uint32_t bits=p.bitCountAfter<=32?child+0x24:get(child+0x24);
  // The original growth stores its first block's address in the inline slot and
  // later copies that slot as bit data. Physical addresses differ, so word 0 must
  // be the first bitset block address (after the text buffer) with bit 31 set, as in the original.
  bool pointerWord=std::string(p.name).rfind("grow-bitset",0)==0;
  for(size_t i=0;i<p.bitWordsAfter.size();++i) {
   if(i==0 && pointerWord) {
    require((p.bitWordsAfter[0]&0x80000000u)!=0 && allocations.size()>1,"pointer word shape");
    require(get(bits)==(allocations[allocations.size()-2]|0x80000000u),"pointer word");
    continue;
   }
   require(get(bits+uint32_t(i)*4)==p.bitWordsAfter[i],"bit word "+std::to_string(i));
  }
 }
};
int main() {
 unsigned failures=0;
 for(const auto &p:profiles) {
  try {
  Host out;out.setup(p,false);Host::require(out.run(p.function,4)==1 && !out.host.fault,"write call failed");
  if(out.payload!=p.output) {
   size_t i=0;while(i<out.payload.size() && i<p.output.size() && out.payload[i]==p.output[i])++i;
   throw std::runtime_error("output mismatch at "+std::to_string(i)+", native bytes "+std::to_string(out.payload.size())+", original bytes "+std::to_string(p.output.size()));
  }
  Host::require(out.sizes==p.sizes,"output chunk order");
  Host in;in.setup(p,true);in.payload=p.output;Host::require(in.run(p.function,7)==1 && !in.host.fault,"read call failed");
  in.compare(p);Host::require(in.cursor==p.consumed,"input consumed bytes");Host::require(in.sizes==p.readSizes,"input chunk order");
  std::cout<<p.name<<": pass\n";
  } catch(const std::exception &e) {++failures;std::cerr<<p.name<<": "<<e.what()<<"\n";}
 }
 for(uint32_t f:{0x4df6f0u,0x4df240u}) {
  for(uint32_t op:{0u,1u,3u,5u,6u,8u,0xffffffffu}) {Host s;assert(s.run(f,op)==1 && !s.host.fault && s.sizes.empty() && s.allocations.empty());}
  Host nullStream;assert(nullStream.run(f,7,0)==0 && !nullStream.host.fault && nullStream.sizes.empty());
  Host failWrite;failWrite.failBinary=true;failWrite.run(f,4);assert(failWrite.host.fault==CLAW_FAULT_HOST && failWrite.host.faultAddress==writer);
  Host unknown;unknown.put(table+0x30,0x7100ffff);unknown.run(f,4);assert(unknown.host.fault==CLAW_FAULT_HOST && unknown.host.faultAddress==0x7100ffff);
  Host failNew;failNew.failAllocation=true;failNew.input=true;failNew.payload={0,0,0,0};failNew.run(f,7);assert(failNew.host.fault==CLAW_FAULT_HOST && failNew.host.faultAddress==0x4fcaea);
 }
 if(failures) {std::cerr<<failures<<" original joined profiles failed\n";return 1;}
 std::cout<<"native joined child profiles and negative controls pass\n";
}
'''


def cpp_values(values, suffix='u'):
    return '{' + ','.join(hex(v) + suffix for v in values) + '}'


def bits(value):
    import struct
    return int.from_bytes(struct.pack('<d', value), 'little')


def profile_source(row):
    p, after = row['profile'], row['read']['after']
    base_after = [0xffff0001 if v == after['restored_owner'] else
                  0xffff0002 if v == after['restored_logic'] else v for v in after['base_words']]
    values = [json.dumps(row['id'] + '-' + row['function']), row['function'], str(p['count']),
              cpp_values(p['bits']), cpp_values([bits(v) for v in p['values']], 'ull'),
              hex(p['integer'] & 0xffffffff) + 'u', cpp_values(p['tail']), cpp_values(p['base']),
              hex(p['global_word']) + 'u', str(row['read']['initial']['bitset']['count']),
              cpp_values(row['read']['initial']['bitset']['words']), cpp_values(bytes.fromhex(row['write']['bytes_hex'])),
              cpp_values([e['size'] for e in row['write']['stream_events']]),
              cpp_values([e['size'] for e in row['read']['stream_events']]), str(row['read']['consumed']),
              cpp_values([int.from_bytes(bytes.fromhex(v), 'little') for v in after['numeric_hex']], 'ull'),
              hex(after['integer_word']) + 'u', cpp_values(after['tail_words']), cpp_values(base_after),
              hex(after['global_word']) + 'u', str(after['bitset']['count']), cpp_values(after['bitset']['words'])]
    return '{' + ','.join(values) + '}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
        raise SystemExit('Wait until load is below 16')
    reference = json.loads(REFERENCE.read_text())
    assert reference['schema'] == 1 and reference['status'] == 'pass'
    assert reference['program_sha256'] == PROGRAM
    expected = {(name, function) for name in ('zero-empty', 'negative-decimals-inline', 'exponents-heap33',
                                              'signed-zero-heap40', 'grow-bitset-two-to33')
                for function in ('0x4df6f0', '0x4df240')}
    assert len(reference['rows']) == len(expected) and {(r['id'], r['function']) for r in reference['rows']} == expected
    assert all(r['status'] == 'pass' for r in reference['rows'])
    assert reference.get('input_sha256'), 'Original child reference must identify its producer inputs'
    for path, expected in reference['input_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Stale original child reference: ' + path
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'check.json').unlink(missing_ok=True)
    source = OUT / 'check.cpp'
    source.write_text(SOURCE.replace('PROFILES', ',\n'.join(profile_source(r) for r in reference['rows']))
                      .replace('OFFSETS', ','.join(str(o) for o in reference['numeric_offsets'])))
    binary = OUT / 'check'
    subprocess.run(['clang++', '-std=c++17', '-O2', '-I', str(ROOT / 'Sources'), str(source),
                    str(ROOT / 'Sources/V13RawStreamServices.cpp'), str(ROOT / 'Sources/V13RawChildrenRuntime.cpp'),
                    '-o', str(binary)], check=True)
    checked = subprocess.run([str(binary)], capture_output=True, text=True)
    (OUT / 'check.log').write_text(checked.stdout + checked.stderr)
    print(checked.stdout, end='')
    print(checked.stderr, end='')
    result = dict(status='pass' if checked.returncode == 0 else 'fail', check='v13_raw_children_native_services', original_profiles=len(reference['rows']),
                  returncode=checked.returncode,
                  reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                  native_inputs_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                      'Sources/V13RawStreamServices.cpp', 'Sources/V13RawStreamServices.h',
                      'Sources/V13RawChildrenRuntime.cpp', 'Sources/ClawRuntime.h', 'Sources/ClawRuntime.hpp')},
                  scope='Joined child serializer and physical streams/storage only; family admission and app caller are separate.')
    (OUT / 'check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if checked.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
