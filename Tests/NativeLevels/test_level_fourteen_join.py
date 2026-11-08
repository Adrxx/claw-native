"""Level 14 reference and strict route-comparison rejection controls."""
import copy
import ctypes as C
import unittest
from collections import Counter
from Tests.NativeLevelOne.native_join import Source, X87, SOURCE_PRESERVABLE
from Tests.NativeLevels import level_fourteen_join as join


def route_record():
    frames = []
    for i in range(3531):
        action = ('stand', 'walk-right', 'jump-right', 'attack')[i % 4]
        if 10 <= i < 30:
            action = 'climb-up'
        frames.append([i * 17, action, dict(level=14, x=100 if i < 30 else 101,
            y=200-i, logic_state=27, input_mask=0x4000000)])
    return dict(level_frames=frames, level_pickups=[dict(frame=100, increment=1)],
        level_lives=[], level_complete_posted=True, level_two_loaded=True,
        level_loaded=True, level_played_ms=60010, level_game_ms=60011,
        navigation=[dict(wparam=0x8036)]*13,
        completions=[dict(level=i) for i in range(2,14)],
        state_transitions=[dict(vtable='0x50c0c4', level=14)],
        presentations=[['level-14-stand',17,'pixels','palette',1]],
        level_services=[dict(service=join.shared.GRID_SERVICES[0], count=73728),
                        dict(service='IDirectDrawSurface::Blt', mirror=1)],
        string_comparisons=[])


class ComparisonTests(unittest.TestCase):
    def test_source_dispatch_retains_checked_environment_transport(self):
        host = object.__new__(join.shared.LevelNativeJoin)
        host.entries = {0x4879a0:dict(convention='thiscall',argc=0,returns='u32',
            x87_environment=dict(pop=0,push=0))}
        host.x87_ambient = X87(size=C.sizeof(X87),version=1,control=0x023f,status=0x4100)
        host.source_ordinary_calls = Counter()
        host.word = lambda address:0x487469
        calls = []
        def environment(request, state):
            calls.append((request.function,request.receiver,state.control,state.status))
            state.status = 0x100
            return 17
        host.environment_call = environment
        cpu = Source(esp=0x2000,ecx=0x3000,ebx=123,esi=456,edi=789,
            preserve_mask=SOURCE_PRESERVABLE)
        self.assertEqual(host.invoke(0x4879a0,0x3000,[],0x2000,C.addressof(cpu),0x487469),17)
        self.assertEqual((cpu.eax,cpu.eip,cpu.esp,cpu.ebx,cpu.esi,cpu.edi),
            (17,0x487469,0x2004,123,456,789))
        self.assertEqual(calls,[(0x4879a0,0x3000,0x023f,0x4100)])
        self.assertEqual(host.x87_ambient.status,0x100)
        for field,value in (('esp',0x2004),('ecx',0x3004),('preserve_mask',0xffffffff)):
            changed = Source(esp=0x2000,ecx=0x3000,preserve_mask=SOURCE_PRESERVABLE)
            setattr(changed,field,value)
            with self.assertRaises(join.Blocked):
                host.invoke(0x4879a0,0x3000,[],0x2000,C.addressof(changed),0x487469)
        self.assertEqual(len(calls),1)
        # A source CALL must not borrow an enclosing owner's unpublished x87
        # ENTRY packet or silently replace it with the ambient environment.
        host.x87_frames = [dict(function=0x403b40)]
        changed = Source(esp=0x2000,ecx=0x3000,preserve_mask=SOURCE_PRESERVABLE)
        with self.assertRaises(join.Blocked):
            host.invoke(0x4879a0,0x3000,[],0x2000,C.addressof(changed),0x487469)
        self.assertEqual(len(calls),1)

    def test_complete_route_and_actual_climb(self):
        record = route_record()
        self.assertTrue(join.compare(copy.deepcopy(record), record)['passed'])
        self.assertGreaterEqual(join.shared.climbs(record['level_frames']), 10)

    def test_identical_short_or_label_only_route_is_insufficient(self):
        for mutate in (
            lambda r:r.update(level_game_ms=59999),
            lambda r:r['level_frames'].pop(),
            lambda r:[f[2].update(y=200) for f in r['level_frames']],
            lambda r:r['completions'].pop(),
            lambda r:r['level_pickups'].clear(),
        ):
            with self.subTest(mutate=mutate):
                record = route_record()
                mutate(record)
                self.assertFalse(join.compare(copy.deepcopy(record), record)['passed'])

    def test_native_frame_services_and_pixels_are_strict(self):
        reference = route_record()
        for mutate in (
            lambda r:r['level_frames'][20][2].update(x=999),
            lambda r:r['level_pickups'].clear(),
            lambda r:r['level_services'].reverse(),
            lambda r:r['presentations'][0].__setitem__(2, 'wrong'),
        ):
            changed = copy.deepcopy(reference)
            mutate(changed)
            self.assertFalse(join.compare(changed, reference)['passed'])

    def test_discovery_pixels_are_separate_from_independent_truth(self):
        original = route_record()
        retained = copy.deepcopy(original)
        retained['presentations'][0][2] = 'discovery-sort-pixels'
        self.assertFalse(join.compare(original, retained)['passed'])
        self.assertTrue(join.compare_discovery(original, retained)['passed'])
        retained['presentations'][0][3] = 'wrong-palette'
        self.assertFalse(join.compare_discovery(original, retained)['passed'])

    def test_observer_prefix_and_shared_transport_are_rejected(self):
        route = [dict(start_ms=0,end_ms=60010,action='stand',keys=[])]
        reference = dict(status='pass',stop=None,level=14,plan=route,played_ms=60010,
            executable_sha256=join.EXE_SHA256,
            **{field:join.digest(path) for field,path in join.TRACE_INPUTS.items()},
            observer_transport_sha256=join.digest('Tests/NativeLevels/level_thirteen_join.py'),
            independent_runner_sha256=join.digest(join.RUNNER),
            rank_sort_reference=dict(algorithm='unchanged original CRT 0x4f1e20',completed=1,active=False),
            resources=dict(sha256=join.REZ_SHA256,archive=str(join.REZ_PATH.relative_to(join.ROOT))),
            xmidi_clock_adapter=dict(version=join.shared.CLOCK_VERSION,hz=120,
                sha256=join.digest('Tests/NativeLevels/xmidi_clock.py')))
        join.validate_independent(reference,route)
        self.assertEqual(len(join.reference_controls(reference,route)),14)


if __name__ == '__main__':
    unittest.main()
