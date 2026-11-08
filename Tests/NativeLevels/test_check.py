"""Queue classification controls for generated discovery batches."""
import unittest

from Tests.NativeLevels.check import closure_batches


class BatchClassificationTests(unittest.TestCase):
    def batch(self):
        return dict(id='level-six-batch-vents-01', addresses=['0x1']*5,
                    depends_on=[], scope='At most 600 cases')

    def test_integration_follow_up_is_not_a_function_batch(self):
        batch = self.batch()
        follow_up = dict(id='level-six-batch-enemy-internal-x87-dispatch',
                         depends_on=[], scope='Check the owned dispatch boundary')
        self.assertEqual(closure_batches([follow_up, batch], 'level-six'), [batch])
        self.assertEqual(closure_batches([batch], 'level-eight'), [])

    def test_malformed_generated_batches_still_fail(self):
        batch = self.batch()
        del batch['addresses']
        with self.assertRaises(KeyError):
            closure_batches([batch], 'level-six')
        for field, value in (('addresses', ['0x1']*4), ('scope', 'No case limit')):
            batch = self.batch()
            batch[field] = value
            with self.assertRaises(AssertionError):
                closure_batches([batch], 'level-six')
        batch = self.batch()
        batch['id'] = 'level-six-batch-manual'
        self.assertEqual(closure_batches([batch], 'level-six'), [batch])


if __name__ == '__main__':
    unittest.main()
