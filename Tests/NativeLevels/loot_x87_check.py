"""Focused loot x87 transport checks; run as Tests.NativeLevels.loot_x87_check.

Execute the real admitted BouncingGoodie constructor/refresh and motion owner
against the original with unchanged sealed setups. Nested profiles supply the
reviewed enclosing dispatch stack and a real ENTRY packet; they test borrowing
its host-owned composed state independently of the complete Level 12 route comparison.
Other game callees execute through existing declared original boundaries.
"""
import ctypes as C
import json
import random
import hashlib
from pathlib import Path
from dataclasses import replace
from Tests.NativeLevels.base_x87_check import attach, packet, proof, state_tuple
from Tests.NativeLevelOne.native_join import Call, X87, LevelOneNativeJoin
from types import SimpleNamespace
from collections import Counter
from Tests.NativeMenuBase.trace import Blocked, ROOT
TARGET=0x4dca10
FAMILIES=('level_one_player_actions_01','level_one_enemy_actions')

class LootEnv(proof.Env):
    def _reset_entry_x87(self):
        super()._reset_entry_x87()
        self.machine.set_x87_state(0x23f,self.profile,
            tuple((0x923456789abcdef0+i,0x4001+i) for i in range(self.live)))
    def _native_call(self,user,pointer):
        raw=pointer.contents
        if raw.function!=TARGET or raw.x87ArgumentCount:
            return super()._native_call(user,pointer)
        try:
            request=Call.from_buffer_copy(raw)
            before=state_tuple(self.common.x87_frames[0]["ordinary_cursor"] if self.nested else self.common.x87_ambient)
            arguments=tuple(request.arguments[:request.count])
            self.events.append((TARGET,raw.receiver,0,arguments,(),('extended-v1',*before),self._digest()))
            value=self.common.invoke(TARGET,raw.receiver,list(arguments),request.stack or self.common.child_stack())
            self.receipts.append((TARGET,before,state_tuple(self.common.x87_ambient)))
            return value
        except Exception as error:
            self.errors.append(error);self._host.fault=self._host.fault or 5
            return 0
    def _native_x87_outer(self,raw):
        request=Call.from_buffer_copy(raw)
        if self.negative and request.x87_count==5 and request.function==TARGET:
            state=X87.from_address(request.x87_state)
            if self.negative=='cw':state.control^=0x100
            elif self.negative=='slot':state.slots[0].significand^=1
            elif self.negative=='top':state.status^=0x800
            elif self.negative=='push':state.push=1
            elif self.negative=='missing-entry':self.common.x87_frames[-1]['entered']=False
            elif self.negative=='duplicate':self.common.x87_outer(request)
            else:state.status^=self.negative
        return self.common.x87_outer(request)

def configure(specs,entries):
    previous=proof.Joined
    try:
        proof.Joined=LootEnv
        env=proof.configure(specs,entries)
    finally:proof.Joined=previous
    env.whole_x87(TARGET,'thiscall',0,'loot integrate',exact=proof.EFFECT)
    return env

def refusals(specs):
    common=object.__new__(LevelOneNativeJoin)
    common.entries={int(e['address'],16):e for spec in specs for e in spec['owned']}
    common.native_error=None;common.error_stack=None
    live=packet((0x23f,0x2821,((0x923456789abcdef0,0x4001),)))
    valid_path=[0x4dc830,0x44df60,0x44e0c0,0x42df90,0x40e690]
    rejected=[]
    def reject(name,action):
        try:action()
        except Blocked:rejected.append(name);return
        raise AssertionError('accepted '+name)
    for fault in ('ancestor','path','unentered','published','missing-live','source','continuation','target'):
        common.native_functions=valid_path.copy()
        frame=dict(function=0x4dc830,entered=True,result=None,ordinary_cursor=X87.from_buffer_copy(live))
        common.x87_frames=[frame]
        source=None;continuation=0;target=TARGET
        if fault=='ancestor':frame['function']=0x4063b0
        elif fault=='path':common.native_functions[-2]=0x42df91
        elif fault=='unentered':frame['entered']=False
        elif fault=='published':frame['result']=live
        elif fault=='missing-live':frame.pop('ordinary_cursor')
        elif fault=='source':source=1
        elif fault=='continuation':continuation=1
        elif fault=='target':target=0x43dfa0
        reject(fault,lambda:common.invoke(target,0x1234,[],proof.STACK_TOP,source,continuation))
    # Invalid ordinary packets must fault before consulting the host or invoking
    # a game owner, including an unoccupied argument word carrying hidden data.
    faults=[]
    common.library=SimpleNamespace(menu_fault=lambda host,target:faults.append(target))
    common.host=None
    for field in ('stack','count','receiver2','source','return_pc','x87_argument','compiler','transfer_version',
                  'transfer_kind','transfer_site','caller','disposition','x87_state','x87_operation',
                  'callback_cpu','callback_activation','unused-argument'):
        common.native_error=None;common.error_stack=None
        request=Call(function=TARGET,receiver=0x1234)
        if field=='unused-argument':request.arguments[0]=1
        else:setattr(request,field,1)
        common.service(None,C.pointer(request))
        if not common.native_error or not common.native_error.startswith('Malformed ordinary x87'):
            raise AssertionError('accepted malformed '+field)
        rejected.append('ordinary-'+field)
    if len(faults)!=sum(name.startswith('ordinary-') for name in rejected):raise AssertionError('malformed request did not fault')
    return rejected

def cursor_witnesses(specs):
    # Host election probes only. These do not replace game bodies in any
    # original/native comparison above: the callback checks cursor creation.
    common=object.__new__(LevelOneNativeJoin)
    common.entries={int(e['address'],16):e for spec in specs for e in spec['owned']}
    common.x87_frames=[];common.native_functions=[];common.native_error=None
    common.x87_environments=Counter();common.child_stack=lambda:proof.STACK_TOP
    rows=[];observed=[]
    def publish(address,receiver,arguments,stack):
        observed.append('ordinary_cursor' in common.x87_frames[-1])
        common.native_functions=[address]
        raw=X87(size=C.sizeof(X87),version=1)
        common.x87_outer(Call(function=address,x87_count=4,x87_state=C.addressof(raw)))
        raw.returned=0
        common.x87_outer(Call(function=address,x87_count=5,x87_state=C.addressof(raw)))
        common.native_functions=[]
        return 1
    common._invoke=publish
    for owner,target,tracked,expected in ((0x4dc830,0x44df60,0,True),(0x4dc830,0x44df61,0,False),
        (0x4063b0,0x40f2a0,0,True),(0x4063b0,0x40f2a1,0,False),(0x4063b0,0x40f2a0,1,False)):
        actor,holder,logic,vtable=0x1000,0x2000,0x3000,0x4000
        words={actor+0x6c:holder,holder+0x18:logic,logic:vtable,logic+0x14:tracked,
               vtable+0x14:target,vtable+0x24:target}
        common.word=words.__getitem__
        request=Call(function=owner,receiver=0 if owner==0x4dc830 else logic,count=1)
        request.arguments[0]=actor if owner==0x4dc830 else 0
        common.environment_call(request,packet((0x23f,0x21,())))
        if observed[-1]!=expected:raise AssertionError(('wrong cursor witness',hex(owner),target,tracked))
        rows.append(dict(owner=hex(owner),target=hex(target),tracked=tracked,cursor=observed[-1]))
    return rows

def main():
    specs=[json.loads((ROOT/'Tests/families'/f'{name}.json').read_text()) for name in FAMILIES]
    library=C.CDLL(str(proof.build.library('loot-x87-join',[ROOT/p for s in specs for p in s['sources']],'O2')))
    entries=[]
    for spec in specs:
        entry=getattr(library,spec['oracle']['entry'])
        entry.argtypes=[proof.U32,proof.U32,C.POINTER(proof.U32),proof.U32,C.POINTER(proof.NativeHost),C.POINTER(proof.U32)]
        entry.restype=proof.U32;entries.append(entry)
    cases=[c for c in proof.runner.load_cases(specs[0]).cases(random.Random(0))
           if c.function==0x40e690 and c.label.startswith('begin state zero')]
    if len(cases)!=4:raise AssertionError('missing sealed begin-zero profiles')
    refresh=[c for c in proof.runner.load_cases(specs[0]).cases(random.Random(0))
              if c.function==0x40f2a0 and c.label in ('update without trie hit=False','update without trie hit=True')]
    if len(refresh)!=2:raise AssertionError('missing sealed refresh profiles')
    cases+=refresh
    # Exercise both low fractional clock scaling and the unsigned high bit.
    # Only the copied setup is extended; sealed family cases stay untouched.
    first=cases[0]
    for clock in (1,0xffffffff):
        def setup_clock(env,clock=clock):
            tokens=first.setup(env)
            env.put(0x537210,clock)
            return tokens
        cases.append(replace(first,label=f'begin state zero clock {clock:#x}',setup=setup_clock))
    rows=[];negatives=[]
    for case in cases:
        signature=next(e for e in specs[0]['owned'] if int(e['address'],16)==case.function)
        compare_result=signature.get('returns')!='void'
        for sw in (0,0x20,0x21,0x200,0x4500):
            profiles=((0,False),(1,False),(3,False),(0,True),(1,True),(3,True)) if case.function==0x40e690 else ((0,False),(1,False),(0,True),(1,True))
            for live,nested in profiles:
                env=configure(specs,entries);common=attach(env,specs,entries)
                env.profile=sw|(0x2800 if live else 0);env.live=live;env.nested=nested;env.parent_corrupt=0
                env._begin_case(random.Random(17));tokens=case.setup(env)
                env.initial_stack(proof.resolve(case.initial_stack,tokens));env._freeze()
                arguments=tuple(proof.resolve(a,tokens)&0xffffffff for a in case.arguments)
                receiver=proof.resolve(case.receiver,tokens)
                def joined(function,receiver,words,count,host,out):
                    common.x87_ambient=packet(env.machine.x87_state())
                    common.native_functions=[];common.x87_frames=[]
                    if nested:
                        ancestor=0x4dc830 if function==0x40e690 else 0x4063b0
                        entry=packet(env.machine.x87_state())
                        frame=dict(function=ancestor,caller=entry,entered=False,result=None,push=0,ordinary_cursor=X87.from_buffer_copy(entry))
                        common.x87_frames=[frame];common.native_functions=[ancestor]
                        live_state=X87(size=C.sizeof(X87),version=1)
                        common.x87_outer(Call(function=ancestor,x87_count=4,x87_state=C.addressof(live_state)))
                        common.native_functions=([ancestor,0x44df60,0x44e0c0,0x42df90] if function==0x40e690 else [ancestor])
                        # Ambient is unrelated. The cursor is owned by the host; no ENTRY pointer survives.
                        common.x87_ambient=packet((0x23f,0x4500,()))
                    value=common.invoke(function,receiver,list(words[:count]) if count else [],proof.STACK_TOP)
                    if nested:
                        if state_tuple(frame['ordinary_cursor'])!=state_tuple(common.x87_ambient):
                            raise AssertionError('post-child cursor lost')
                        # The wrapper's by-value native packet is still ENTRY.
                        # Its host publication must compose the checked child SW.
                        raw_result=X87.from_buffer_copy(entry)
                        raw_result.status^=env.parent_corrupt
                        unchanged=state_tuple(raw_result)
                        common.native_functions=[ancestor]
                        common.x87_outer(Call(function=ancestor,x87_count=5,x87_state=C.addressof(raw_result)))
                        if state_tuple(raw_result)!=unchanged:
                            raise AssertionError('RESULT packet architectural fields changed')
                        if state_tuple(frame['result'])!=state_tuple(common.x87_ambient):
                            raise AssertionError('wrapper dropped child environment')
                        common.native_functions=[];common.x87_frames=[]
                    C.cast(out,C.POINTER(proof.U32))[0]=value
                    return 1
                try:native=env.run_native(joined,case.function,receiver,arguments)
                except Blocked:
                    print(json.dumps(dict(failed_case=case.label,sw=env.profile,live=live,nested=nested)),flush=True)
                    raise
                native=replace(native,x87=state_tuple(common.x87_ambient));receipts=list(env.receipts)
                original=env.run_original(case.function,receiver,arguments)
                original=replace(original,x87=env.machine.x87_state())
                difference=env.compare(native,original,compare_result,proof.STACK_TOP+4)
                if difference or not native.completed or native.x87!=original.x87:
                    raise AssertionError((case.label,env.profile,live,difference,native.errors,native.x87,original.x87))
                if len(receipts)!=1:raise AssertionError(('missing loot boundary',receipts))
                rows.append(dict(label=case.label,clock=env.get(0x537210),incoming=env.profile,live=live,nested=nested,native=native.x87,original=original.x87,receipts=receipts))
                for corruption in ('cw','slot','top','push','missing-entry','duplicate',0x20,0x100):
                    env.negative=corruption;env.receipts=[]
                    try:
                        wrong=env.run_native(joined,case.function,receiver,arguments)
                        wrong=replace(wrong,x87=state_tuple(common.x87_ambient))
                        if env.compare(wrong,original,compare_result,proof.STACK_TOP+4) is None and wrong.x87==original.x87:
                            raise AssertionError(('surviving corruption',corruption))
                    except Blocked:pass
                    negatives.append(dict(label=case.label,incoming=env.profile,live=live,nested=nested,corruption=str(corruption)))
                if nested:
                    env.negative=None;env.parent_corrupt=0x20
                    try:
                        env.run_native(joined,case.function,receiver,arguments)
                    except Blocked:
                        negatives.append(dict(label=case.label,incoming=env.profile,live=live,nested=True,corruption='parent-status'))
                    else:raise AssertionError('accepted changed pass-through RESULT')

    rejected=refusals(specs)
    evidence=ROOT/'work/native-loot-x87-check.json'
    evidence.write_text(json.dumps(dict(status='pass',original_sha256=proof.claw().sha256,
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__).resolve(),ROOT/'Tests/NativeLevelOne/native_join.py',*[ROOT/p for s in specs for p in s['sources']]]},
        rows=rows,negative_controls=negatives,refusals=rejected,cursor_witnesses=cursor_witnesses(specs)),indent=2)+'\n')
    print(json.dumps(dict(status='pass',comparisons=len(rows),negative_controls=len(negatives),refusals=len(rejected),evidence=str(evidence))))

if __name__=='__main__':main()
