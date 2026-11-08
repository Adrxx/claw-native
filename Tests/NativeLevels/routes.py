"""Physical key schedules for retained discovery routes (no game-state writes)."""
from Tests.NativeLevelTwo.trace import PLAN as LEVEL_TWO_PLAN


def route_for(level):
    if level != 3:
        return LEVEL_TWO_PLAN
    route = [dict(start_ms=0, end_ms=1000, action='stand', keys=[])]
    # Cross the starting gap and two raised platforms; release jump and sword
    # between presses. The original supplies enemy hits, health and treasure.
    for start in range(1000, 14450, 1200):
        for lo, hi, action, keys in (
            (0, 600, 'jump-right', [0x27, 0x20]),
            (600, 900, 'attack', [0x11]),
            (900, 1200, 'walk-right', [0x27]),
        ):
            if start+lo < 14450:
                route.append(dict(start_ms=start+lo, end_ms=min(start+hi, 14450), action=action, keys=keys))
    # Drop onto the first ladder, then repeatedly climb both ways. The interval
    # is an exact number of 17 ms frames, so successive cycles do not drift.
    route.append(dict(start_ms=14450, end_ms=15980, action='climb-down', keys=[0x28]))
    start = 15980
    while start < 60000:
        for action, keys in (('climb-up', [0x26]), ('climb-down', [0x28])):
            if start < 60000:
                route.append(dict(start_ms=start, end_ms=min(start+612, 60000), action=action, keys=keys))
                start += 612
    return route
