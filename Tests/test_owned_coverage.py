"""Coverage must expose omitted bytes rather than shrink whole-body claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from Tests.clawparity.runner import coverage_report, run

class OwnedCoverageTests(unittest.TestCase):
    def test_owned_exempt_and_required_bytes_are_separate(self):
        spec={'owned':[{'address':'0x503420'}], 'oracle':{'coverage_exempt':[
            {'start':'0x503464','end':'0x50346d'}]}}
        with patch('Tests.clawparity.runner.owned_ranges',return_value={0x503420:[(0x503420,0x50348b)]}):
            result=coverage_report(spec,{(0x503420,0x34),(0x50346d,0x1e)},{0x503420:1})['0x503420']
        self.assertEqual(result['owned_bytes'],107)
        self.assertEqual(result['exempt_bytes'],9)
        self.assertEqual(result['required_bytes'],98)
        self.assertEqual(result['bytes'],98)
        self.assertEqual(result['executed'],82)
        self.assertEqual(result['never_executed'],[['0x503454','0x503464']])
        self.assertLess(result['fraction'],1)

    def test_overlapping_exemptions_count_bytes_once(self):
        spec={'owned':[{'address':'0x401000'}], 'oracle':{'coverage_exempt':[
            {'start':'0x401001','end':'0x401005'}, {'start':'0x401003','end':'0x401008'}]}}
        with patch('Tests.clawparity.runner.owned_ranges',return_value={0x401000:[(0x401000,0x401010)]}):
            result=coverage_report(spec,{(0x401000,16)},{})['0x401000']
        self.assertEqual((result['owned_bytes'],result['exempt_bytes'],result['required_bytes']),(16,7,9))
        self.assertEqual(result['executed'],9)
        self.assertEqual(result['fraction'],1)

    def test_guest_spec_cannot_silently_use_ordinary_runner(self):
        base={'id':'unsupported_guest','owned':[{'address':'0x503420'}],'oracle':{},'callees':{}}
        variants=[]
        candidate=copy.deepcopy(base); candidate['oracle']['guest_graph']={}; variants.append(candidate)
        candidate=copy.deepcopy(base); candidate['owned'][0]['attached_entries']=[]; variants.append(candidate)
        candidate=copy.deepcopy(base); candidate['callees']['0x546958']={'kind':'guest-service'}; variants.append(candidate)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'spec.json'
            for candidate in variants:
                path.write_text(json.dumps(candidate))
                for original_only in (False,True):
                    result=run(path,original_only=original_only)
                    self.assertEqual(result['status'],'error')
                    self.assertIn('GuestContractError',result['detail'])

if __name__=='__main__': unittest.main()
