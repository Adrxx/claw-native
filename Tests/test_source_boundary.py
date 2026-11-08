"""Opt-in caller observations expose transient CALL/RET PCs without effects."""
import ctypes as C
from pathlib import Path
import struct
import unittest
from Tests.clawparity import build
from Tests.clawparity.env import Env, NativeHost, Side, U32, HarnessError
from Tests.clawparity.kernel import ContextFault, STACK_TOP
from Tests.clawparity.program import Program, Section
from Tests.clawparity.selftest.source_context import context

ROOT = Path(__file__).resolve().parents[1]


def program():
    code = bytearray(b'\xcc' * 0x120)
    # PUSH callback; CALL cdecl child; POP ECX; RET.
    code[:12] = b'\x68' + struct.pack('<I',0x401100) + b'\xe8' + struct.pack('<i',0x401080-0x40100a) + b'\x59\xc3'
    code[0x20:0x2e] = b'\x68' + struct.pack('<I',0x401100) + b'\xe8' + struct.pack('<i',0x401080-0x40102a) + bytes.fromhex('83c404 c3')
    code[0x80:0x85] = bytes.fromhex('8b442404 c3')
    return Program('authored-source-boundary','',0x400000,0x3000,
        [Section('.text',0x401000,len(code),bytes(code)),Section('.data',0x402000,0x1000,bytes(0x1000))],
        (0x401000,0x401120),{})


class SourceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT/'work/pilot/source_boundary_selftest';directory.mkdir(parents=True,exist_ok=True)
        source = directory/'module.cpp'
        source.write_text('''#include "ClawRuntime.hpp"
namespace {
int owned(uint32_t f) { return f == 0x401000 || f == 0x401020 ? 0 : -1; }
ClawSourceContract contract(uint32_t) { return {0x7ff,0x7ff,0x472,0}; }
uint32_t body(claw::Run &run,uint32_t f,uint32_t,const uint32_t*) {
 auto &s=run.source();s.esp-=4;
#ifndef DROP_PUSH
 run.put(s.esp,0x401100);
#endif
 s.eip=f+5+CALL_SHIFT;
 auto child=s;child.esp-=4;child.eip=0x401080;
 run.put(child.esp,f+10);
 run.source_call(0x401080,0,f+10,child,{0x401100});s=child;
 if (f==0x401000) { s.ecx=run.get(s.esp);s.esp+=4;s.eip=f+11+RET_SHIFT; }
 else { uint32_t a=s.esp,r=a+4;s.esp=r;
  uint32_t flags=(!__builtin_parity(r&255)?4:0)|(r==0?64:0)|(r&0x80000000?128:0)|
    (((a^4^r)&16)?16:0)|(r<a?1:0)|((~(a^4)&(a^r)&0x80000000)?2048:0);
  s.eflags=(s.eflags&~0x8d5u)|flags;s.eip=f+13+RET_SHIFT; }
 return s.eax;
}}
CLAW_SOURCE_MODULE_ENTRY(boundary_entry,owned,contract,body)
''')
        cls.modules={}
        for label,defines in [('baseline',()),('call_pc',('CALL_SHIFT=1',)),('ret_pc',('RET_SHIFT=1',)),('push',('DROP_PUSH=1',))]:
            defines=(*defines,*(() if any(x.startswith('CALL_SHIFT') for x in defines) else ('CALL_SHIFT=0',)),
                     *(() if any(x.startswith('RET_SHIFT') for x in defines) else ('RET_SHIFT=0',)))
            lib=C.CDLL(str(build.library('source-boundary-'+label,[source],defines=defines)))
            entry=lib.boundary_entry;entry.argtypes=[U32,U32,C.POINTER(U32),U32,C.POINTER(NativeHost),C.POINTER(U32)];entry.restype=U32
            cls.modules[label]=(lib,entry)

    def run_pair(self,label,observe=True,function=0x401000):
        env=Env(program());env.source_callees[0x401080]=dict(kind='whole',convention='cdecl',argc=1,returns='u32',
            source_context=dict(input_mask=0x7ff,output_mask=0x7ff,preserve_mask=0x472))
        env._begin_case(None)
        if observe:env.observe_source_boundary(function,function+5,function+10,function+(11 if function==0x401000 else 13))
        env._freeze()
        n,o=context(function),context(function)
        native=env.run_native(self.modules[label][1],function,0,(),source_context=n,source_return_pc=0x401110)
        original=env.run_original_context(function,o,source_return_pc=0x401110)
        return env,native,original,n,o

    def test_valid_observations_match_and_do_not_change_execution(self):
        env,n,o,nc,oc=self.run_pair('baseline')
        self.assertIsNone(env.compare(n,o,True,STACK_TOP+4))
        self.assertEqual(bytes(nc),bytes(oc))
        self.assertEqual([x[1] for x in n.source_boundaries],['call','ret'])
        self.assertEqual([x[2][8] for x in n.source_boundaries],[0x401005,0x40100b])
        _,plain,_,plainc,_=self.run_pair('baseline',False)
        self.assertEqual((n.events,n.heap,n.image,bytes(nc)),(plain.events,plain.heap,plain.image,bytes(plainc)))
        self.assertEqual(plain.source_boundaries,[])

    def test_call_and_ret_pc_mutants_are_observable_on_valid_inputs(self):
        for label in ('call_pc','ret_pc'):
            env,n,o,nc,oc=self.run_pair(label)
            self.assertTrue(n.completed and o.completed)
            self.assertEqual(bytes(nc),bytes(oc))
            self.assertEqual(env.compare(n,o,True,STACK_TOP+4)['kind'],'source-boundary')

    def test_add_cleanup_ret_pc_is_observable(self):
        env,n,o,nc,oc=self.run_pair('baseline',function=0x401020)
        self.assertEqual(bytes(nc),bytes(oc))
        self.assertIsNone(env.compare(n,o,True,STACK_TOP+4))
        env,n,o,nc,oc=self.run_pair('ret_pc',function=0x401020)
        self.assertTrue(n.completed and o.completed)
        self.assertEqual(bytes(nc),bytes(oc))
        self.assertEqual(env.compare(n,o,True,STACK_TOP+4)['kind'],'source-boundary')

    def test_bad_push_is_native_violation_not_invalid_original(self):
        env,n,o,_,_=self.run_pair('push')
        self.assertEqual(n.fault,5);self.assertTrue(o.completed);self.assertEqual(o.errors,[])
        self.assertEqual(env.compare(n,o,True,STACK_TOP+4)['kind'],'native-fault')

    def test_classification_does_not_credit_unproven_or_original_errors(self):
        env=Env(program());valid=Side(completed=True,stack_pointer=STACK_TOP+4)
        native=Side(fault=5,errors=[ContextFault('native bad frame')])
        self.assertEqual(env.compare(native,valid,False,STACK_TOP+4)['kind'],'native-fault')
        for original in (Side(),Side(errors=[ContextFault('original bad frame')]),Side(completed=True,fault=5)):
            self.assertEqual(env.compare(native,original,False,STACK_TOP+4)['kind'],'harness')
        self.assertEqual(env.compare(Side(fault=5,errors=[HarnessError('bad case')]),valid,False,STACK_TOP+4)['kind'],'harness')

    def test_sites_require_original_instruction_identity_and_no_duplicates(self):
        env=Env(program())
        for sites in [(0x401000,0x401006,0x40100a,0x40100b),(0x401000,0x401005,0x401009,0x40100b),
                      (0x401000,0x401005,0x40100a,0x40100a)]:
            with self.assertRaises(ContextFault):env.observe_source_boundary(*sites)
        env.observe_source_boundary(0x401000,0x401005,0x40100a,0x40100b)
        with self.assertRaises(ContextFault):env.observe_source_boundary(0x401000,0x401005,0x40100a,0x40100b)
        env._begin_case(None)
        self.assertEqual(env._boundary_specs,{})


if __name__=='__main__':unittest.main()
