import copy
import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch
from Tests.clawparity import gate
from Tests.clawparity.guest_admission import evidence_errors
from Tests.clawparity.mutants import outcome

class GuestAdmissionTests(unittest.TestCase):
    def evidence(self):
        return {'outcomes':{'returned':3,'unhandled':3},'policy_verified':True,
            'factory_outcomes':{f:{'returned':1,'unhandled':1} for f in ('0x502369','0x502bde','0x502c0f')},
            'original_catch_cases':3,'native_attached_invocations':3,
            'ownership_guard':'stop-before-execution','owned_ranges_guarded':[[0x503420,0x50348b]]}

    def test_valid_bounded_evidence(self):
        self.assertEqual(evidence_errors(self.evidence()),[])

    def test_missing_or_weaker_evidence_cannot_admit(self):
        changes={'outcomes':{'returned':5},'factory_outcomes':{},'policy_verified':False,'original_catch_cases':0,
            'native_attached_invocations':2,'ownership_guard':'fallback','owned_ranges_guarded':[[0x503454,0x503464]]}
        self.assertTrue(evidence_errors(None))
        for name,value in changes.items():
            with self.subTest(name=name):
                evidence=self.evidence();evidence[name]=value
                self.assertTrue(evidence_errors(evidence))

    def test_each_factory_requires_observed_success_and_failure(self):
        for factory in ('0x502369','0x502bde','0x502c0f'):
            for kind in ('returned','unhandled'):
                evidence=self.evidence();del evidence['factory_outcomes'][factory][kind]
                self.assertTrue(evidence_errors(evidence,require_native=False))

    def test_original_only_needs_no_native_credit(self):
        evidence=self.evidence();evidence.pop('native_attached_invocations');evidence.pop('owned_ranges_guarded');evidence.pop('ownership_guard')
        self.assertEqual(evidence_errors(evidence,require_native=False),[])
        self.assertTrue(evidence_errors(evidence))

    def test_guest_differences_kill_but_harness_errors_do_not(self):
        for kind in ('guest-state','guest-outcome','guest-owned-entry'):
            self.assertEqual(outcome({'status':'fail','failures':[{'kind':kind}]},1),'killed')
        self.assertEqual(outcome({'status':'error','detail':'invalid policy'},1),'invalid')
        self.assertEqual(outcome({'status':'fail','failures':[{'kind':'harness'}]},1),'invalid')

    def test_sanitizer_preserves_actual_guest_evidence(self):
        evidence=self.evidence()
        done=SimpleNamespace(returncode=0,stdout=json.dumps({'status':'pass','cases':6,'guest_graph':evidence}),stderr='')
        with patch.object(gate.build,'sanitized_python',return_value=(['python'],{})), patch.object(gate.subprocess,'run',return_value=done):
            result=gate._sanitized('family.json',1)
        self.assertEqual(result['guest_graph'],evidence)
        self.assertEqual(evidence_errors(result['guest_graph']),[])
        self.assertEqual(result['status'],'pass')

    def test_sanitizer_cannot_invent_evidence_or_hide_failed_exit(self):
        for code,output in ((0,json.dumps({'status':'pass'})),(1,json.dumps({'status':'pass'})),(0,'broken')):
            done=SimpleNamespace(returncode=code,stdout=output,stderr='')
            with patch.object(gate.build,'sanitized_python',return_value=(['python'],{})), patch.object(gate.subprocess,'run',return_value=done):
                result=gate._sanitized('family.json',1)
            self.assertTrue(evidence_errors(result.get('guest_graph')))
            if code or output=='broken':self.assertEqual(result['status'],'error')

if __name__=='__main__': unittest.main()
