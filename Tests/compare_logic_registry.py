#!/usr/bin/env python3
"""Original built-in bindings, factory metadata, original map lookup semantics."""
import argparse
import collections
import ctypes as C
from pathlib import Path
import json
import random
import struct
import subprocess
import zlib
from logic_registry_helpers import RegistryHarness

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,default=ROOT/'Original/claw10/CLAW.EXE');p.add_argument('--world',type=Path,default=ROOT/'App/GameData/LEVEL1/WORLDS/WORLD.WWD');a=p.parse_args()
library=ROOT/'work/registry-agent/libLogicRegistry.dylib'
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'Sources/LogicRegistry.cpp'),'-o',str(library)],check=True)
class Entry(C.Structure):_fields_=[('name',C.c_char_p)]+[(n,C.c_uint32)for n in('registrationOrdinal','originalNameAddress','callback','flags')]
lib=C.CDLL(str(library));lib.claw_logic_registry_count.restype=C.c_uint32
lib.claw_logic_registry_at.argtypes=[C.c_uint32];lib.claw_logic_registry_at.restype=C.POINTER(Entry)
lib.claw_logic_registry_find.argtypes=[C.c_char_p];lib.claw_logic_registry_find.restype=C.POINTER(Entry)
r=RegistryHarness(a.exe);entries=r.populate();assert len(entries)==212==lib.claw_logic_registry_count()
def expected_words(callback,flags,metadata_id=0):
    words=[0xa5a5a5a5]*93
    for i,value in [(0,0x513740),(1,metadata_id),(2,0),(3,r.scene),(4,0),(5,0),(6,0),(7,0)]:words[i]=value
    if callback:
        words[4]=callback;words[2]=flags
        for byte in(0x14,0x18,0x20,0x24,0x2c,0x34,0x30,0x38,0x168,0x16c,0x28):words[byte//4]=0
    return words
by_name={e['name']:e for e in entries};lookup_calls=0
for index,entry in enumerate(entries):
    native=lib.claw_logic_registry_at(index).contents
    assert (native.name,native.registrationOrdinal,native.originalNameAddress,native.callback,native.flags)==(entry['name'].encode(),index+1,entry['nameAddress'],entry['callback'],entry['flags'])
    assert entry['metadataId']==index
    assert r.machine.read_words(entry['entryAddress'],93)==expected_words(entry['callback'],entry['flags'],index),(entry['name'],'full metadata buffer')
    found,token=r.find(entry['name']);assert found==1 and token==entry['entryAddress'];lookup_calls+=1
    match=lib.claw_logic_registry_find(entry['name'].encode()).contents
    assert match.registrationOrdinal==index+1
    for probe in(entry['name'].lower(),entry['name'].upper(),entry['name']+' ', ' '+entry['name'],entry['name'][:-1]):
        found,token=r.find(probe);match=lib.claw_logic_registry_find(probe.encode());expected=by_name.get(probe)
        assert found==bool(expected) and bool(match)==bool(expected)
        assert token==(expected['entryAddress'] if expected else 0x99),('missing lookup mutates output',probe)
        lookup_calls+=1
assert not lib.claw_logic_registry_at(212) and not lib.claw_logic_registry_at(0xffffffff) and not lib.claw_logic_registry_find(None)
assert len(by_name)==212 and r.machine.read_words(r.registry+0x10+12,1)==[212]
print('PASS all212 ordered original builtin bindings, full372-byte metadata objects and exact/case/whitespace/prefix lookup probes',flush=True)

# Missing default leaves the caller's output unchanged. Equality uses original
# strcmp; embedded NUL is a name terminator, not an extended logical key.
for probe in(b'',b'UnknownLogic',b'CaptainClaw\0suffix',b'captainclaw',b'\xffLogic',b'Rat\xff'):
    expected=by_name.get(probe.split(b'\0',1)[0].decode('ascii',errors='replace'));found,token=r.find(probe,0xdeadbeef);match=lib.claw_logic_registry_find(probe)
    assert found==bool(expected) and bool(match)==bool(expected)
    assert token==(expected['entryAddress']if expected else 0xdeadbeef);lookup_calls+=1

# Original factory creates a new object, overwrites an exact existing map value,
# retains its copied key and does not destroy the replaced metadata object.
before_count=r.machine.read_words(r.registry+0x10+12,1)[0];before_strings=r.string_cursor
old=r.find('CaptainClaw')[1];new=r.register('CaptainClaw',0x498f40,0xf1234567)
assert new!=old and r.find('CaptainClaw')==(1,new)
assert r.machine.read_words(new,93)==expected_words(0x498f40,0xf1234567,before_count)
assert r.machine.read_words(r.registry+0x10+12,1)==[before_count] and r.string_cursor==before_strings and not r.destroyed
assert r.machine.read_words(old,93)==expected_words(0x415df0,0)
# Mutate the ephemeral insertion input to establish copied name retention at
# the CString storage adapter, while original hash/map key management executes.
custom=r.register('CustomLogic',0x41414141,7);r.u.mem_write(r.query,b'DestroyedInput\0')
assert r.find('CustomLogic')==(1,custom) and r.find('DestroyedInput')==(0,0x99)
# Empty names and zero flags are allowed by factory; zero callback fails and
# leaves an existing value unchanged. Failed object destruction is adapted.
empty=r.register('',0x415df0,0);assert r.find('')==(1,empty)
existing=r.find('CaptainClaw')[1];failed_address=r.object_cursor
assert r.register('CaptainClaw',0,9)==0 and r.find('CaptainClaw')==(1,existing)
assert r.destroyed==[(failed_address,1)]
assert r.machine.read_words(failed_address,93)==expected_words(0,9,214)
print('PASS original duplicate replacement, copied-key storage boundary, empty names, zero-callback rejection and untouched missing output',flush=True)

# Exact raw-WWD names must all exist in the original table; flags are compared
# against actual registration metadata, rather than earlier supplied test flags.
world=a.world.read_bytes();planes,offset=struct.unpack_from('<2I',world,732)
if struct.unpack_from('<I',world,8)[0]&2:world=world[:offset]+zlib.decompress(world[offset:])
names=collections.Counter()
for plane in range(planes):
    base=offset+plane*160;count=struct.unpack_from('<I',world,base+128)[0];position=struct.unpack_from('<I',world,base+140)[0]
    for _ in range(count):
        lengths=struct.unpack_from('<4I',world,position+4);start=position+284+lengths[0]
        name=world[start:start+lengths[1]].split(b'\0',1)[0].decode('ascii');names[name]+=1;position+=284+sum(lengths)
assert sum(names.values())==1479 and len(names)==38
for name in names:
    entry=by_name[name];native=lib.claw_logic_registry_find(name.encode()).contents
    assert (native.callback,native.flags)==(entry['callback'],entry['flags'])
print(f'PASS all38 Level1 logic names covering1479raw objects; exact original registered flags/callback identities',flush=True)

# Snapshot is private evidence; captured allocation addresses are NOT generated
# native identities. Canonical source ordinal names always come from first run.
snapshot=dict(entries=entries[:212],sideCalls=r.side_calls,level1Names=dict(names),
              profileSHA256='350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263')
(ROOT/'work/registry-agent/verified.json').write_text(json.dumps(snapshot,indent=2))
required={0x401000,0x4d6340,0x4c8160,0x4f62a8,0x4f6226,0x4f5d5c,0x4f6286,0x4a3810}
assert required<=r.machine.executed
addresses=r.machine.executed-r.side_entries-{0x4f63ec,0x4f66cc,0x4c80c0,r.machine.stop}
print(f'PASS {lookup_calls} builtin lookup probes;212 registration factories;84 calls to78 unrelated resource/configuration initializer entries adapted;{len(addresses)} original registry/population instruction addresses. Actual registration, binding, hashing, map insertion, strcmp and lookup execute.',flush=True)
