"""Exercise the family runner's genuine original-only guest branch."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from Tests import test_guest_reference as reference_tests
from Tests.test_guest_contract import specification
from Tests.clawparity.cases import Case
from Tests.clawparity import runner
from Tests.clawparity.guest_admission import evidence_errors

class GuestFamilyTests(unittest.TestCase):
    def run_fixture(self,original_only):
        reference_tests.GuestReferenceTests.setUpClass()
        helper=reference_tests.GuestReferenceTests()
        env,owner,crt,depths,physical,cpu=helper.fixture()
        initial=copy.deepcopy(env._initial)
        spans,names,bump=dict(env.spans),dict(env.names),env._bump
        def setup(warm):
            def prepare(e):
                e._initial=copy.deepcopy(initial)
                e.spans,e.names,e._bump=dict(spans),dict(names),bump
                if warm:e.put(owner,crt)
                return None
            return prepare
        def cases(random):
            for warm in (False,True):
                yield Case('warm' if warm else 'failure',0x503420,setup=setup(warm),receiver=owner,
                    arguments=(0x502369,),expect='return' if warm else 'unhandled',
                    source_context=cpu,source_return_pc=0x5022b4)
        spec=specification();spec['sources']=['Tests/NativeGuestTransfer/transport.cpp','Tests/NativeGuestTransfer/funclet.cpp']
        spec['oracle']['cases']='unused'
        spec['oracle']['entry']='transport_entry'
        spec['owned'][0]['attached_entries'][0]['native_entry']='transport_catch'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'family.json';path.write_text(json.dumps(spec))
            with patch.object(runner,'Env',return_value=env),patch.object(runner,'load_cases',return_value=SimpleNamespace(cases=cases)):
                result=runner.run(path,original_only=original_only,trace=True,
                    flavor=os.environ.get('CLAW_GUEST_TEST_FLAVOR','O2'))
        return result

    def test_original_cases_publish_real_outcome_and_catch_evidence(self):
        result=self.run_fixture(True)
        self.assertEqual(result['status'],'pass',result)
        self.assertEqual(result['cases'],2)
        evidence=result['guest_graph']
        self.assertEqual(evidence['outcomes'],{'unhandled':1,'returned':1})
        self.assertEqual(evidence['original_catch_cases'],1)
        self.assertEqual(evidence['native_attached_invocations'],0)
        self.assertEqual(evidence['factory_outcomes'],{'0x502369':{'unhandled':1}})
        self.assertTrue(evidence_errors(evidence,require_native=False))
        self.assertTrue(evidence_errors(evidence))
        self.assertEqual(result['coverage']['0x503420']['owned_bytes'],107)

    def test_incomplete_native_scaffold_cannot_claim_family_parity(self):
        result=self.run_fixture(False)
        self.assertEqual(result['status'],'fail',result)
        self.assertEqual(result['failed'],2)
        self.assertTrue(all(f['kind']=='guest-outcome' for f in result['failures']),result)
        self.assertTrue(evidence_errors(result['guest_graph']))

if __name__=='__main__':unittest.main()
