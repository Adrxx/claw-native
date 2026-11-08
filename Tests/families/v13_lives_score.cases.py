"""Actual v1.3 inventory and score callback cases, derived from original ASM."""
import struct
from clawparity.cases import Case
from clawparity.fixtures import allocate

NEW_GAME, RESTORE, SCORE = 0x416DD0, 0x46F840, 0x493E90
LOOKUP, NEW = 0x4FC6B4, 0x4FCAEA


def seed_globals(env, words):
    env.put(0x532BF4, words[0])
    env.put(0x532BF8, *words)
    env.put(0x532D30, *words[:4])
    env.put(0x53B130, words[-1])


def new_game(easy, words, selected):
    def setup(env):
        seed_globals(env, words)
        env.put(0x535990, easy)
        env.put(0x52ABE4, selected)
    return setup


def score_setup(score=500000, threshold=500000, lives=7, state=5,
                old_score=None, digits=0, align=(1, 3), viewport=(11, 19, 652, 498),
                camera=1, old_camera=-99, camera_limit=99, camera_dirty=0,
                sound='disabled', now=200, last=100, interval=50, animation=True, image=False, mutate_lookup=False, progress=0, actor_fill=0, allocation_fill=0):
    def setup(env):
        actor = env.object(0x200, 'score actor', fill=actor_fill)
        data = env.object(0x80, 'actor data', fill=0)
        display = env.object(0x60, 'score display', fill=0)
        world = env.object(0x80, 'world', fill=0)
        engine = env.object(0x80, 'engine', fill=0)
        sound_manager = env.object(0x50, 'sound manager', fill=0)
        resource_manager = env.object(0x40, 'resources', fill=0)
        resource = env.object(0x70, 'extra life resource', fill=0)
        sample = env.object(0x20, 'sample', fill=0)
        sample_state = env.object(0x80, 'sample state', fill=0)
        player = env.object(0x200, 'player', fill=0)
        player_data = env.object(0x40, 'player data', fill=0)
        inventory = env.object(0x100, 'inventory', fill=0)
        view = env.object(0x80, 'view', fill=0)
        published = env.object(0x80, 'publication log', fill=0)
        table = env.object(0x24, 'view methods', fill=0)
        env.put(actor + 0x7C, data)
        env.put(actor + 0xC, world)
        env.put(actor + 0x118, threshold)
        env.put(actor + 0x198, 0)
        if progress:
            env.put(actor + 0x1B4, 1)
            env.put(actor + 0x1C0, progress, 1)
            env.put(actor + 0x1D0, 0x11223344, 0x55667788)
        env.put(data + 0x18, display if animation else 0)
        env.put(data + 0x1C, state)
        env.put(display + 4, align[0], 17, align[1], 23, old_camera, camera_limit)
        env.put(display + 0x1C, 0x66554433, 0x22117788)
        env.put(display + 0x24, actor, 0, score if old_score is None else old_score, digits)
        env.put(world + 0xC, view, resource_manager)
        env.put(world + 0x14, resource_manager)
        env.put(world + 0x28, sound_manager)
        env.put(world + 0x2C, resource_manager)
        env.put(view, table)
        def publish(e, call):
            e.put(published, call.receiver, *call.arguments)
            e.put(published + 0x20, e.get(actor + 0x5C), e.get(actor + 0x60),
                  e.get(display + 0x14), e.get(display + 0x20))
            # Constructor position publication occurs before the new display is
            # installed in actor data. Keep that observable even when both
            # stores would otherwise converge to the same final heap.
            e.put(published + 0x30, e.get(data + 0x18), e.get(data + 0x1C))
            return 0xB6D5E4F3
        env.put(table + 0x20, env.stub('publish score position', 'thiscall', 4, publish))
        env.put(player + 0x114, score)
        env.put(player + 0x7C, player_data)
        env.put(player_data + 0x14, inventory)
        env.put(inventory + 0x7C, lives)
        env.put(engine + 0x68, camera, camera_dirty)
        env.put(sound_manager + 0x30, 1 if sound == 'disabled' else 0)
        env.put(resource + 0x10, sample, last, interval)
        env.put(sample + 0x10, sample_state)
        env.put(0x53B134, actor)
        env.put(0x535910, engine)
        env.put(0x5365D4, player if sound != 'no-player' else 0)
        env.put(0x535840, *viewport)
        env.put(0x53098C, 0 if sound == 'no-device' else 1, 73)
        env.put(0x5AAFD8, 11, now)
        for i in range(digits):
            digit = env.object(0x200, f'digit {i}', fill=0)
            digit_data = env.object(0x80, f'digit state {i}', fill=0)
            frames = env.object(0x70, f'digit frames {i}', fill=0)
            frame_list = env.object(40, f'digit frame list {i}',
                                    words=[0x11770000 + i * 0x100 + n for n in range(10)])
            env.put(digit + 0x7C, digit_data)
            env.put(digit + 0x194, frames)
            env.put(frames + 0x14, frame_list)
            env.put(frames + 0x64, 0, 9)
            env.put(display + 0x34 + 4*i, digit)
        image_frames = env.object(0x70, 'score image frames', fill=0)
        image_list = env.object(4, 'score image list', words=[resource])
        env.put(image_frames + 0x14, image_list)
        env.put(image_frames + 0x64, 0, 0)
        if state == 0:
            env.put(resource + 0x18, 39, 10, 7)
        def lookup(e, call):
            result = 0 if sound == 'missing' else resource
            if state == 0:
                result = image_frames if image and e.calls_so_far(LOOKUP) == 1 else 0
            e.put(call.arguments[1], result)
            if mutate_lookup:
                e.put(actor + 0x118, 1750000)
                e.put(inventory + 0x7C, 42)
                e.put(published + 0x40, e.get(actor + 0x118), e.get(inventory + 0x7C))
            return int(bool(result))
        env.override(LOOKUP, lookup)
        def allocate_pattern(e, call):
            return e.object(call.arguments[0], 'allocation', fill=allocation_fill)
        env.override(NEW, allocate_pattern)
        return {'actor': actor}
    return setup


def cases(random_source):
    for easy in (0, 1, 2, 0xFFFFFFFF):
        for selected in (0, 0x12345678, 0xFFFFFFFF):
            words = [random_source.getrandbits(32) | 1 for _ in range(0x4E)]
            yield Case(f'new game easy={easy} selection={selected}', NEW_GAME,
                       new_game(easy, words, selected))
    for score in (-1000001, -500000, -1, 0, 499999, 500000, 1000000, 0x7FFFFFFF):
        for image in (False, True):
            def init(env, score=score, image=image):
                t = score_setup(state=0, image=image)(env)
                env.put(0x532C3C, score)
                return t
            yield Case(f'score initialization score {score} image {image}', SCORE,
                       init, arguments=(lambda t: t['actor'],))
    for camera in (0, 1, 23, 99, 100, 0xFFFFFFFF):
        for progress in (1, 11, 12, 71, 0xFFFFFFFF):
            yield Case(f'score progressing animation {progress} camera {camera}', SCORE,
                       score_setup(progress=progress, camera=camera, camera_limit=99,
                                   actor_fill=0x57, viewport=(17, 31, 928, 703)),
                       arguments=(lambda t: t['actor'],))
    for fill in (0x19, 0xA5, 0xFF):
        for camera in (0, 7, 99):
            for image in (False, True):
                yield Case(f'score initialized dirty heap {fill} camera {camera} image {image}', SCORE,
                           score_setup(state=0, image=image, actor_fill=fill,
                                       allocation_fill=fill, camera=camera),
                           arguments=(lambda t: t['actor'],))
    for state in (1, 4, 6, 0xFFFFFFFF):
        yield Case(f'score ignored state {state}', SCORE, score_setup(state=state),
                   arguments=(lambda t: t['actor'],))
    yield Case('score missing animation', SCORE, score_setup(animation=False),
               arguments=(lambda t: t['actor'],))
    for remaining, elapsed, timed in ((12, 11, 1), (11, 11, 1),
                                    (1, 11, 1), (12, 0, 1),
                                    (12, 11, 0), (0xFFFFFFFF, 11, 1)):
        def countdown(env, remaining=remaining, elapsed=elapsed, timed=timed):
            tokens = score_setup(animation=False)(env)
            actor = tokens['actor']
            sequence = env.object(0x20, 'active score animation', fill=0x69)
            env.put(actor + 0x1B4, sequence)
            env.put(actor + 0x1C0, remaining, timed, 1)
            env.put(actor + 0x1D0, 0x11223344, 0x55667788)
            env.put(0x5AAFD8, elapsed)
            return tokens
        yield Case(f'score animation countdown {remaining} elapsed {elapsed} timed {timed}',
                   SCORE, countdown, arguments=(lambda t: t['actor'],))
    for threshold in (0, 500000, 1000000, 2000000, 0x7FFFFFFF):
        for difference in (-1, 0, 1, 1500000):
            score = (threshold + difference) & 0xFFFFFFFF
            for lives in (0, 9, 10, 11):
                yield Case(f'score threshold {threshold} delta {difference} lives {lives}', SCORE,
                           score_setup(score=score, threshold=threshold, lives=lives),
                           arguments=(lambda t: t['actor'],))
    yield Case('score resource callback changes threshold and lives before publication', SCORE,
               score_setup(sound='played', mutate_lookup=True),
               arguments=(lambda t: t['actor'],))
    for n in range(24):
        score = random_source.randrange(0, 100000000)
        threshold = random_source.randrange(0, 100000000)
        lives = random_source.randrange(-3, 14)
        yield Case(f'random score {n}: {score}/{threshold}/{lives}', SCORE,
                   score_setup(score=score, threshold=threshold, lives=lives,
                               old_score=random_source.getrandbits(32), digits=8),
                   arguments=(lambda t: t['actor'],))
    for sound in ('missing', 'no-device', 'played', 'disabled', 'no-player'):
        for now in (149, 150, 200, 99):
            yield Case(f'score sound {sound} tick {now}', SCORE,
                       score_setup(sound=sound, now=now), arguments=(lambda t: t['actor'],))
    for align_x in (0, 1, 2, 3, 4):
        for align_y in (0, 3, 4, 5, 6):
            for viewport in ((11, 19, 652, 498), (652, 498, 11, 19)):
                yield Case(f'score alignment {align_x},{align_y} viewport {viewport}', SCORE,
                           score_setup(align=(align_x, align_y), viewport=viewport),
                           arguments=(lambda t: t['actor'],))
    for camera, old, limit, dirty in ((1, 1, 99, 0), (1, 1, 99, 1),
                                     (100, 0, 99, 0), (0, 1, 99, 0),
                                     (0xFFFFFFFF, 1, 99, 0)):
        yield Case(f'score camera {camera}/{old} limit {limit} dirty {dirty}', SCORE,
                   score_setup(camera=camera, old_camera=old, camera_limit=limit,
                               camera_dirty=dirty), arguments=(lambda t: t['actor'],))
    for score in (0, 1, 499999, 500000, 500001, 123456789, 0x7FFFFFFF, 0xFFFFFFFF):
        for digits in (0, 1, 4, 8):
            yield Case(f'score digits {digits} value {score}', SCORE,
                       score_setup(score=score, old_score=0xDEADBEEF, digits=digits),
                       arguments=(lambda t: t['actor'],))
    for enabled, profile, level, stage, valid in ((0, True, 2, 1, True),
            (1, False, 2, 1, True), (1, True, 0, 1, True),
            (1, True, -1, 1, True), (1, True, 2, 3, True),
            (1, True, 1, 0, True), (1, True, 15, 1, True),
            (1, True, 2, 1, False)):
        yield Case(f'restore rejects {enabled},{profile},{level},{stage},{valid}', RESTORE,
                   restore_setup(enabled=enabled, profile=profile, level=level,
                                 stage=stage, valid=valid), receiver=lambda t: t['actor'])
    for level, stage in ((2, 0), (1, 1), (7, 2), (14, 2)):
        for x, y in ((0, 0), (0, 73), (31, 0), (-1, 73), (31, -1),
                     (-1, -2), (31, 73)):
            for layer_mode in (0, 1, 2):
                values = [random_source.getrandbits(32) for _ in range(44)]
                yield Case(f'restore level {level} stage {stage} xy {x},{y} layers {layer_mode}',
                           RESTORE, restore_setup(level=level, stage=stage, x=x, y=y,
                             layer_mode=layer_mode, values=values), receiver=lambda t: t['actor'])
    for score in (-1000001, -1000000, -500001, -500000, -1, 0, 499999,
                  500000, 500001, 999999, 1000000, 0x7FFFFFFF, -0x80000000):
        yield Case(f'restore threshold score {score}', RESTORE,
                   restore_setup(score=score), receiver=lambda t: t['actor'])


def restore_setup(enabled=1, profile=True, level=2, stage=1, valid=True,
                  x=31, y=73, layer_mode=0, values=None, score=1234567):
    def setup(env):
        actor = env.object(0x180, 'restored actor', fill=0xB3)
        context = env.object(0x180, 'restore context', fill=0)
        records = env.object(0x2200, 'saved profiles', fill=0)
        world = env.object(0x40, 'restore world', fill=0)
        view = env.object(0x80, 'restore view', fill=0)
        camera = env.object(0x90, 'restore camera', fill=0)
        layers = env.object(12, 'layers', fill=0)
        env.put(actor + 4, context)
        env.put(actor + 0xC, world)
        env.put(actor + 0x14, level)
        env.put(context + 0xAC, enabled)
        env.put(context + 0x64, records if profile else 0)
        env.put(context + 0x158, stage)
        env.put(world + 0x24, view)
        env.put(view + 0x38, layers, 3 if layer_mode else 0)
        env.put(view + 0x5C, camera, 1 if layer_mode == 2 else 9)
        for i, camera_object in enumerate([camera] + [env.object(0x90, f'layer {n}', fill=0) for n in range(3)]):
            env.put(camera_object + 8, (i + layer_mode) & 1)
            env.write(camera_object + 0x18, struct.pack('<ff', 0.75 + i / 4, 1.25 + i / 4))
            env.put(camera_object + 0x30, 20000, 20000)
            env.put(camera_object + 0x70, 641, 479, 5, 7)
            if i:
                env.put(layers + (i-1)*4, camera_object)
        chosen_level = level - 1 if stage == 0 else level
        chosen_stage = 3 if stage == 0 else stage
        if 0 <= chosen_level < 15 and 1 <= chosen_stage <= 3:
            record = records + (0x2D4, 0xD24, 0x1774)[chosen_stage-1] + 176*chosen_level
            content = list(values) if values is not None else [0xAB000001 + 0x10203*n for n in range(44)]
            env.put(record, *content)
            env.put(record, 2 if valid else 0)
            env.put(record + 4, x, y)
            env.put(record + 0x10, score, 0xDD884411)
        env.put(0x532C14, *[0xFE000001 + n * 0x123 for n in range(64)])
        env.put(0x534D94, 0x66778899)
        env.put(0x535928, 0x11223344)
        env.override(LOOKUP, lambda e, c: 0)
        env.override(NEW, allocate())
        return {'actor': actor}
    return setup
