#!/usr/bin/env python3
"""Focused native RTTI/string providers and their source-context entrances.

String behavior is compared with the system C library. RTTI inputs are taken
from the hash-checked original's metadata; no recovered game body executes.
This is a native service check, not a family admission or full call closure.
"""
import ctypes as C
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def check():
    closure=module('closure',ROOT/'scripts/check-call-closure.py')
    shared=module('transports',ROOT/'scripts/check-level-one-transports.py')
    with closure.heavy_lock():
        closure.wait_load()
        lib=shared.build()
    u32=C.c_uint32
    regions=[];reads=[]
    def memory(user,address,size):
        reads.append((address,size))
        for base,buffer in regions:
            if base<=address and address+size<=base+C.sizeof(buffer):
                return C.addressof(buffer)+address-base
        return None
    lookup=C.CFUNCTYPE(C.c_void_p,C.c_void_p,u32,u32)(memory)
    host=shared.Host();host.bytes=C.cast(lookup,C.c_void_p)
    provider_binary,_,_=closure.call_closure_providers.build(
        ROOT,closure.body,closure.digest,closure.heavy_lock,closure.wait_load)
    providers=C.CDLL(str(provider_binary.parent/'providers.dylib'))
    search=providers.claw_native_menu_byte_search
    search.argtypes=[C.POINTER(shared.Host),u32,u32,u32,C.POINTER(u32)]
    libc_search=C.CDLL(None)
    search_cases=0
    for last,name in ((0,'strchr'),(1,'strrchr')):
        expected=getattr(libc_search,name);expected.argtypes=[C.c_void_p,C.c_int];expected.restype=C.c_void_p
        for value in (b'',b'claw',b'banana',b'\xff\x80\xff',b'a\0ignored'):
            source=C.create_string_buffer(value);regions[:]=[(0x61000000,source)]
            for character in (0,ord('a'),ord('z'),128,255,0x161,0xffffffff):
                out=u32(0xdeadbeef)
                assert search(C.byref(host),0x61000000,character,last,C.byref(out))==1
                pointer=expected(source,C.c_int(character).value)
                assert out.value==(0x61000000+pointer-C.addressof(source) if pointer else 0)
                search_cases+=1
    out=u32(0xdeadbeef);regions.clear()
    assert search(C.byref(host),0xdeadbeef,1,0,C.byref(out))==0 and out.value==0xdeadbeef
    source=C.create_string_buffer(b'ab',2);regions[:]=[(0x61000000,source)]
    assert search(C.byref(host),0x61000000,ord('b'),1,C.byref(out))==0
    # An early strchr match need not read past it. strrchr needs the NUL.
    assert search(C.byref(host),0x61000000,ord('b'),0,C.byref(out))==1 and out.value==0x61000001
    regions[:]=[(0xffffffff,C.create_string_buffer(b'a',1))]
    assert search(C.byref(host),0xffffffff,ord('z'),1,C.byref(out))==0
    substring=providers.claw_native_menu_substring
    substring.argtypes=[C.POINTER(shared.Host),u32,u32,C.POINTER(u32)]
    libc_search.strstr.argtypes=[C.c_void_p,C.c_void_p];libc_search.strstr.restype=C.c_void_p
    substring_cases=0
    for text in (b'',b'banana',b'\xff\x80\xff',b'claw-claw',b'abc\0later'):
        for pattern in (b'',b'a',b'ana',b'claw',b'\xff',b'zzzzzzzzzz'):
            source=C.create_string_buffer(text);needle=C.create_string_buffer(pattern)
            regions[:]=[(0x61000000,source),(0x62000000,needle)]
            assert substring(C.byref(host),0x61000000,0x62000000,C.byref(out))==1
            pointer=libc_search.strstr(source,needle)
            assert out.value==(0x61000000+pointer-C.addressof(source) if pointer else 0)
            substring_cases+=1
    regions.clear();out=u32(0xdeadbeef)
    assert substring(C.byref(host),0x61000000,0x62000000,C.byref(out))==0 and out.value==0xdeadbeef
    effect_queries=[dict(effect=1,target=t,argc=n,token=p) for t,n,p in (
        (0x4a49b0,1,0x61000000),(0x4f6428,1,0x61000000),(0x4a49b0,1,0),
        (0x4a49b0,2,0),(0x4a7920,1,0),(0x4a7920,1,0x61000000),
        (0x4a7920,1,0xdeadbeef),(0x4a7920,0,0),(0x4f5192,0,0),(0x4f5192,1,0))]
    effects=json.loads(subprocess.run([str(provider_binary)],input=json.dumps(effect_queries),text=True,capture_output=True,check=True).stdout)
    assert effects[0]==effects[1] and effects[0]['released']==[0x61000000]
    assert effects[2]['accepted'] and effects[2]['released']==[] and not effects[3]['accepted']
    assert all(effects[i]['accepted'] for i in (4,5)) and all(not effects[i]['accepted'] for i in (6,7,9))
    assert effects[8]['accepted'] and effects[8]['released']==[0x61000000,0x61000010]
    assert not effects[8]['list_retained'] and effects[8]['vtable']==0x50becc and effects[8]['count']==0
    seek_queries=[dict(file_seek=1,initial=5,arguments=a) for a in (
        [3,0],[0xfffffffe,1],[0xfffffffd,2],[0xffffffec,2],[1,3],[1],
        [0,2],[0x7fffffff,0],[0x80000000,0])]
    seeks=json.loads(subprocess.run([str(provider_binary)],input=json.dumps(seek_queries),text=True,capture_output=True,check=True).stdout)
    for index,position in ((0,3),(1,3),(2,13),(6,16),(7,0x7fffffff)):
        assert seeks[index]==dict(accepted=True,value=position,position=position)
    assert all(seeks[i]==dict(accepted=False,value=0xffffffff,position=5) for i in (3,4,5,8))
    lib.claw_level_native_strncat.argtypes=[C.POINTER(shared.Host),u32,u32,u32,C.POINTER(u32)]
    lib.claw_level_native_type_info.argtypes=[C.POINTER(shared.Host),u32,C.POINTER(u32)]
    libc=C.CDLL(None);libc.strncat.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t];libc.strncat.restype=C.c_void_p
    string_cases=0
    for left in (b'',b'claw',b'\xff\x80',b'error: '):
        for right in (b'',b'abc',b'\x80\xffz',b'abcdefghijklmnopqrstuvwxyz'):
            for count in sorted({0,1,2,len(right),len(right)+1,79}):
                destination=C.create_string_buffer(bytes([0xa5])*128,128)
                expected=C.create_string_buffer(bytes([0xa5])*128,128)
                for value in (destination,expected):C.memmove(value,left+b'\0',len(left)+1)
                source=C.create_string_buffer(right)
                regions[:]=[(0x61000000,destination),(0x62000000,source)]
                out=u32(0xdeadbeef)
                assert lib.claw_level_native_strncat(C.byref(host),0x61000000,0x62000000,count,C.byref(out))==1
                libc.strncat(expected,source,count)
                assert destination.raw==expected.raw and out.value==0x61000000
                string_cases+=1
    regions.clear();reads.clear();out=u32()
    assert lib.claw_level_native_strncat(C.byref(host),0xdeadbeef,0xffffffff,0,C.byref(out))==1
    assert out.value==0xdeadbeef and not reads
    assert lib.claw_level_native_strncat(C.byref(host),0xdeadbeef,0xffffffff,1,C.byref(out))==0
    # No space for the required final NUL, and missing source storage.
    destination=C.create_string_buffer(b'a\0',2);source=C.create_string_buffer(b'b')
    regions[:]=[(0x61000000,destination),(0x62000000,source)]
    assert lib.claw_level_native_strncat(C.byref(host),0x61000000,0x62000000,1,C.byref(out))==0
    destination=C.create_string_buffer(b'\0',1);regions[:]=[(0x61000000,destination)]
    assert lib.claw_level_native_strncat(C.byref(host),0x61000000,0x62000000,1,C.byref(out))==0

    from Tests.clawparity.program import claw
    original=claw();graph=closure.Graph(original,set());graph.census_tables()
    images=[(s.address,C.create_string_buffer(s.data,len(s.data))) for s in original.sections if s.data]
    metadata=[]
    for table in graph.tables:
        locator=graph.word(table-4)
        descriptor=graph.word(locator+12) if locator else None
        if not descriptor or len(graph.bytes(descriptor,8))!=8:continue
        obj=C.create_string_buffer(table.to_bytes(4,'little'),4)
        regions[:]=images+[(0x61000000,obj)]
        assert lib.claw_level_native_type_info(C.byref(host),0x61000000,C.byref(out))==1
        assert out.value==descriptor
        metadata.append(dict(table=table,locator=locator,descriptor=descriptor))
    assert len(metadata)>100, 'Lost original RTTI metadata census'
    # The provider must not turn bad_typeid/bad_cast storage into success.
    for missing in (0,0x61000000,0xffffffff):
        regions.clear()
        assert lib.claw_level_native_type_info(C.byref(host),missing,C.byref(out))==0
    for size in (0,7,8):
        obj=C.create_string_buffer((0x62000004).to_bytes(4,'little'),4)
        table=C.create_string_buffer((0x63000000).to_bytes(4,'little'),4)
        locator=C.create_string_buffer(bytes(12)+(0x64000000).to_bytes(4,'little'),16)
        descriptor=C.create_string_buffer(max(1,size))
        regions[:]=[(0x61000000,obj),(0x62000000,table),(0x63000000,locator)]
        if size:regions.append((0x64000000,descriptor))
        assert lib.claw_level_native_type_info(C.byref(host),0x61000000,C.byref(out))==int(size==8)
    for target,count,expected in ((0x4f63ec,1,0),(0x4a36f0,1,0),(0x4f2060,3,0),
                                  (0x546d2c,5,20),(0x546d50,4,16)):
        pop=u32(99)
        assert lib.claw_level_physical_source_pop(u32(target),u32(count),C.byref(pop))==1 and pop.value==expected
        assert lib.claw_level_physical_source_pop(u32(target),u32(count+1),C.byref(pop))==0
    # Reconstruct each regression from the hash-checked original and current
    # caller source. No previous audit artifact is needed to run this check.
    owners=closure.manifests();requests=[];edges=[]
    for caller,site,target in ((0x4141f0,0x4142f3,0x4a36f0),(0x49f1c0,0x49f2c3,0x4a36f0),
                               (0x423450,0x42346b,0x4f63ec),(0x4db4d0,0x4db556,0x4f2060)):
        instruction=next(graph.decoder.disasm(graph.bytes(site,15),site,count=1))
        assert instruction.mnemonic=='call' and instruction.op_str==hex(target)
        manifest,owned=owners[('claw-v1.0',caller)]
        edge=dict(caller=caller,site=site,target=target,kind='call')
        shape,evidence=closure.SourceShapes(ROOT,manifest).edge(edge,owned,instruction.size)
        assert shape['source']==1 and shape['return_pc']==site+instruction.size
        requests.append(dict(shape,caller=caller,site=site,target=target))
        edges.append(dict(original_site=dict(edge,size=instruction.size,
            bytes_sha256=hashlib.sha256(instruction.bytes).hexdigest()),shape_evidence=evidence))
    binary=closure.probe_build()
    run=lambda rows:json.loads(subprocess.run([str(binary)],input=json.dumps(rows),text=True,capture_output=True,
                env={**os.environ,'CLAW_GAME_VERSION':'1.0'},check=True).stdout)
    answers=run(requests)
    for request,answer in zip(requests,answers):
        assert answer['outcome']=='provider-unresolved' and answer['route']=='source-physical'
        assert answer['source_eip']==request['return_pc'] and answer['source_esp']==0x2000004
    malformed=run([dict(q,argc=q['argc']+1) for q in requests])
    assert all(a['outcome']=='refused' for a in malformed)
    return dict(check='call-closure-native-providers',status='pass',string_libc_cases=string_cases,
                byte_search_libc_cases=search_cases,substring_libc_cases=substring_cases,provider_effect_probes=effects,
                native_file_seek_probes=seeks,
                original_sha256=original.sha256,rtti_tables=len(metadata),rtti_metadata=metadata,
                source_edges=len(edges),
                original_source_edges=[dict(site=e['original_site'],source=e['shape_evidence']['path'],answer=a)
                                       for e,a in zip(edges,answers)],malformed_source_shapes=malformed,
                scope='Native provider behavior and source pop; full call closure remains separate.')


if __name__=='__main__':
    output=ROOT/'work/call-closure/native-providers.json'
    try:result=check()
    except Exception as error:result=dict(check='call-closure-native-providers',status='fail',error=str(error))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rtti_metadata','original_source_edges','malformed_source_shapes')}))
    sys.exit(result['status']!='pass')
