"""Strict inactive singleton contract; original bytes come only from pinned loader."""
from dataclasses import FrozenInstanceError
import copy
import unittest
from Tests.clawparity.guest_contract import normalize_guest_contract,guest_contract_errors,GuestContractError,GuestDependency


def specification():
    masks={'input_mask':0x7ff,'output_mask':0x7ff,'preserve_mask':0}
    route={'address':'0x503454','kind':'eh-funclet','native_entry':'native_catch',
        'handler':'0x508bf8','func_info':'0x51ebc0','handler_table':'0x51ec08',
        'call_site':'0x4a8f25','return_pc':'0x4a8f27','frame_delta_ebp':12,
        'cpu':{'input_mask':0x7ff,'output_mask':0x7ff},'normal_return':False}
    dependencies={}
    signatures={0x4a48c0:('compiler-context',0,'context'),0x502e95:('stdcall',1,'void'),
        0x502f05:('stdcall',1,'void'),0x4a5690:('stdcall',2,'void'),
        0x502369:('cdecl',0,'u32'),0x502bde:('cdecl',0,'u32'),0x502c0f:('cdecl',0,'u32')}
    for address,(convention,argc,returns) in signatures.items():
        declaration={'kind':'whole','convention':convention,'argc':argc,'returns':returns}
        if convention=='compiler-context': declaration['compiler_context']={'input_mask':0x7ff,'output_mask':0x7ff}
        else: declaration['source_context']=copy.deepcopy(masks)
        if address == 0x502369: declaration['source_context']['preserve_mask']=0x472
        dependencies[hex(address)]=declaration
    for address,name in ((0x546958,'RaiseException'),(0x546a38,'RtlUnwind')):
        dependencies[hex(address)]={'kind':'guest-service','name':name,'convention':'stdcall',
            'argc':4,'arguments':['u32']*4,'returns':'void','reason':'Physical nonlocal transfer'}
    return {'id':'singleton_contract_test','abi':'canonical','owned':[{
        'address':'0x503420','convention':'thiscall','argc':1,'returns':'u32','source_context':masks,
        'body_ranges':[{'start':'0x503420','end':'0x50348b',
            'sha256':'20ff5fcf52ab88830c763c3a660763af742d480ec55bb7a587e7a51992258b5b'}],
        'attached_entries':[route]}],'callees':dependencies,'oracle':{'kind':'clawparity','entry':'claw_singleton_contract_test_entry','guest_graph':{
            'version':1,'allowed_handlers':['0x508539','0x5089cd','0x508bf8','0x4a3260','0x4a9348','0x4a3490'],
            'factory_call_site':'0x50344d','allowed_factories':['0x502369','0x502bde','0x502c0f'],
            'required_outcomes':['returned','unhandled'],'require_native_attached_entries':True}}}

class GuestContractTests(unittest.TestCase):
    def test_valid_contract_retains_whole_body_and_immutable_evidence(self):
        plan=normalize_guest_contract(specification())
        self.assertEqual(plan.owned_ranges,((0x503420,0x50348b),))
        self.assertEqual(plan.attached_entry.entry_pc,0x503454)
        self.assertEqual(len(plan.allowed_factories),3)
        self.assertGreater(sum(len(data) for address,data in plan.immutable_regions),1000000)

    def test_dependencies_retain_exact_immutable_contracts(self):
        plan=normalize_guest_contract(specification())
        self.assertIs(type(plan.dependencies),tuple)
        self.assertEqual(len(plan.dependencies),7)
        for dependency in plan.dependencies:
            self.assertIs(type(dependency),GuestDependency)
            self.assertEqual((dependency.input_mask,dependency.output_mask),(0x7ff,0x7ff))
            self.assertEqual(dependency.preserve_mask,
                None if dependency.address==0x4a48c0 else 0x472 if dependency.address==0x502369 else 0)
            with self.assertRaises(FrozenInstanceError): dependency.argc=9
            self.assertFalse(hasattr(dependency,'__dict__'))

    def test_dependency_manifest_contract_mutations_fail(self):
        for address in ('0x4a48c0','0x502e95','0x502f05','0x4a5690','0x502369','0x502bde','0x502c0f'):
            for field,value in (('convention','fastcall'),('argc',8),('returns','double'),('kind','fixture')):
                with self.subTest(address=address,field=field):
                    spec=specification();spec['callees'][address][field]=value
                    with self.assertRaises(GuestContractError):normalize_guest_contract(spec)
            channel='compiler_context' if address=='0x4a48c0' else 'source_context'
            mutations=[lambda d:d.pop(channel),lambda d:d[channel].pop('input_mask'),
                lambda d:d[channel].update(input_mask=0x5c0),lambda d:d[channel].update(output_mask=0x581),
                lambda d:d[channel].update(preserve_mask=0 if address=='0x502369' else 0x472)]
            for mutation in mutations:
                with self.subTest(address=address,mutation=mutation):
                    spec=specification();mutation(spec['callees'][address])
                    with self.assertRaises(GuestContractError):normalize_guest_contract(spec)
        spec=specification();spec['callees']['0x00502369']=copy.deepcopy(spec['callees']['0x502369'])
        with self.assertRaises(GuestContractError):normalize_guest_contract(spec)

    def test_unknown_fields_and_omitted_obligations_fail(self):
        mutations=[lambda s:s['oracle']['guest_graph'].update(unknown=True),
            lambda s:s['oracle']['guest_graph'].update(require_native_attached_entries=False),
            lambda s:s['oracle']['guest_graph'].update(required_outcomes=['returned']),
            lambda s:s['oracle']['guest_graph']['allowed_factories'].pop(),
            lambda s:s['owned'][0]['source_context'].update(optional=True),
            lambda s:s['owned'][0]['attached_entries'][0].update(normal_return=True),
            lambda s:s['owned'][0]['attached_entries'][0].update(handler_table='0x51ec0c'),
            lambda s:s['owned'][0]['body_ranges'][0].update(end='0x503454'),
            lambda s:s['callees']['0x546958'].update(kind='fixture'),
            lambda s:s['callees'].update({'0x503454':{'kind':'fixture'}}),
            lambda s:s['callees']['0x4a5690'].update(convention='cdecl')]
        for index,mutation in enumerate(mutations):
            with self.subTest(index=index):
                spec=specification();mutation(spec)
                with self.assertRaises(GuestContractError): normalize_guest_contract(spec)

    def test_partial_guest_declaration_is_not_treated_as_ordinary(self):
        self.assertEqual(guest_contract_errors({'owned':[],'oracle':{},'callees':{}}),[])
        self.assertTrue(guest_contract_errors({'owned':[{'attached_entries':[]}],'oracle':{},'callees':{}}))

    def test_manifest_schema_and_semantics_accept_complete_contract_only(self):
        from tools.claw.manifest import validate
        spec=specification()
        spec.update(schema=1,title='Bounded singleton contract',sources=[],
            evidence={'level':'none'},integration={'level':'source-only'})
        self.assertEqual(validate(spec),[])
        spec['owned'][0]['attached_entries'][0]['normal_return']=True
        self.assertTrue(any('invalid guest contract' in error for error in validate(spec)))

if __name__=='__main__':unittest.main()
