"""Compare the Mac app's level loading screen with the original's.

Original: work/level-one-map/trace.json (the Level 1 trace), phase command-807f: the
launch command that fades out the menu, flips the loading screen, fades it in and out
around the level load, then flips to Level 1.
App:   work/loading-screen/run.sh  (Debug app, --new-game-clock, join navigation schedule)
Check: work/test-env/bin/python scripts/check-loading-screen.py

The screen of an eight-bit display is the front buffer seen through the attached
palette, so it changes on every Flip, SetPalette and SetEntries of the attached
palette. The app records those screen states for the tick that ran the launch
command; they must equal the original's, in order, with consecutive repeats
collapsed, followed by Level 1's first frame, which the same tick runs. The pixels before the command's first Flip are the menu's last frame,
whose cursor animation depends on menu timing, so only palettes are compared there.

The level loader also writes the primary surface itself between Flips (its progress
bar: color fills on the front surface). Each such write is a screen state too. The
trace records what each write did (rectangle and fill color), not the pixels after it,
so the expected front is rebuilt: the app saves the front its first write started from,
whose SHA-256 must equal the original's front at that point, and the original's writes
are replayed on it in order. Paper startup also locks and writes the primary
surface; compare the complete original pixel hash at every paired Unlock,
including its preceding front hash, without rebuilding those pixels.
"""
import hashlib
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.NativeLevels.storage import read_trace
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, default=ROOT / 'work/loading-screen/run')
parser.add_argument('--trace', type=Path, default=ROOT / 'work/level-one-map/trace.json')
args = parser.parse_args()


def original_screens(trace, base=None, geometry=None):
    """Screen states of the launch command, and the primary-surface writes in order."""
    attached, entries, front, screens, writes = None, {}, None, [], []
    flips = iter(p for p in trace['presentations'] if p['phase'] == 'command-807f')
    primary = next(e['object'] for e in trace['physical_events']
                   if e.get('phase') == 'command-807f' and e.get('service') == 'IDirectDrawSurface::Flip')
    pixels = None  # the original's front surface bytes, once rebuilt from the app's base
    locked = False
    for event in trace['physical_events']:
        service, phase = event.get('service'), event.get('phase')
        if service == 'IDirectDraw::CreatePalette':
            entries[event['palette']] = event['entries_sha256']
        elif service == 'IDirectDrawSurface::SetPalette':
            attached = event['palette']
        elif service in ('IDirectDrawPalette::SetEntries', 'IDirectDrawPalette::GetEntries'):
            entries[event['object']] = event['entries_sha256']
            if attached is None and phase == 'command-807f':
                attached = event['object']  # the menu palette, attached before tracing began
        if phase != 'command-807f':
            continue
        if service == 'IDirectDrawSurface::Flip':
            assert not locked, 'flip while the primary surface is locked'
            flip = next(flips)
            front, pixels = flip['pixels_sha256'], None
            screen = [front, flip['palette_sha256']]
        elif event.get('object') == primary and service == 'IDirectDrawSurface::Lock':
            assert not locked, 'nested primary surface lock'
            locked = True
            continue
        elif event.get('object') == primary and service == 'IDirectDrawSurface::Unlock':
            assert locked, 'primary surface unlock without a lock'
            locked = False
            # Paper startup writes the primary pixels directly. The original
            # already records the complete surface hash at each Unlock.
            writes.append(dict(service=service, before_sha256=front,
                               pixels_sha256=event['pixels_sha256']))
            front, pixels = event['pixels_sha256'], None
            screen = [front, entries.get(attached)]
        elif event.get('object') == primary and service != 'IDirectDrawSurface::SetPalette' and \
                service not in ('IDirectDrawSurface::GetSurfaceDesc', 'IDirectDrawSurface::Release',
                                'IDirectDrawSurface::SetColorKey', 'IDirectDrawSurface::GetAttachedSurface'):
            # Every remaining primary write must be a color fill.
            if service != 'IDirectDrawSurface::Blt' or 'source' in event or 'fill_color' not in event:
                raise AssertionError(f'unsupported primary-surface write {service}')
            writes.append(dict(service=service, rectangle=event.get('rectangle'), fill_color=event['fill_color']))
            if base is None:
                screen = [f'primary-write-{len(writes)}', entries.get(attached)]
            else:
                width, height, stride = geometry
                if pixels is None:
                    if hashlib.sha256(base).hexdigest() != front:
                        raise AssertionError('app base front differs from the original front before its first primary write')
                    pixels = bytearray(base)
                left, top, right, bottom = event.get('rectangle') or [0, 0, width, height]
                for row in range(top, bottom):
                    pixels[row * stride + left:row * stride + right] = bytes([event['fill_color']]) * (right - left)
                front = hashlib.sha256(pixels).hexdigest()
                screen = [front, entries.get(attached)]
        elif (service == 'IDirectDrawPalette::SetEntries' and event['object'] == attached) or \
                service == 'IDirectDrawSurface::SetPalette':
            screen = [front, entries.get(attached)]
        else:
            continue
        if not screens or screens[-1] != screen:
            screens.append(screen)
    assert not locked, 'launch command left the primary surface locked'
    return screens, writes


def main():
    report = dict(check='loading-screen', evidence=str(args.evidence))
    try:
        app = json.loads((args.evidence / 'app-menu.json').read_text())
        if app.get('status') != 'pass':
            raise AssertionError('app run did not complete')
        loads = [m for m in app.get('multi_flip_frames', []) if len(m['flips']) > 2]
        if len(loads) != 1:
            raise AssertionError(f'expected one launch-command tick, found {len(loads)}')
        actual = loads[0]['screens']
        trace = read_trace(args.trace)
        app_writes = loads[0].get('primary_writes', [])
        base = geometry = None
        if app_writes and app_writes[0].get('base'):
            base = (args.evidence / app_writes[0]['base']).read_bytes()
            geometry = (app_writes[0]['width'], app_writes[0]['height'], app_writes[0]['stride'])
        reference, original_writes = original_screens(trace, base, geometry)
        if len(app_writes) != len(original_writes):
            raise AssertionError(f'primary-surface writes: original {len(original_writes)}, app {len(app_writes)}')
        for index, (o, a) in enumerate(zip(original_writes, app_writes)):
            fields=('before_sha256','pixels_sha256') if o['service'].endswith('::Unlock') else ('fill_color','rectangle')
            if (o['service'] != a.get('service','IDirectDrawSurface::Blt')
                    or any(o[k] != a.get(k) for k in fields)):
                raise AssertionError(f'primary-surface write {index + 1} differs: original {o}, app {a}')
        report.update(primary_writes=len(original_writes),
                      progress_screenshots=[w['png'] for w in app_writes])
        flipped, matched, divergence = False, 0, None
        for index, (a, b) in enumerate(zip(reference, actual)):
            flipped = flipped or a[0] is not None
            same = a[1] == b[1] and (not flipped or a[0] == b[0])
            if not same:
                divergence = dict(index=index, original=a, app=b)
                break
            matched += 1
        loading = [s for s in reference if s[0] == '39159a881423ef4b22c848743bbbfb49d16b7f7570d51bdaf1dbf345539f604d']
        report.update(frame=loads[0]['frame'], original_screens=len(reference), app_screens=len(actual),
                      matched_screens=matched, divergence=divergence,
                      loading_image_screens=len(loading), flips=len(loads[0]['flips']),
                      screenshots=sorted(p.name for p in args.evidence.glob('screen-*.png'))[:3] + ['...'])
        # The same tick then runs Level 1's first frame (the original's play phase).
        first_play = next(p for p in trace['presentations'] if p['phase'].startswith('play-'))
        tail = actual[len(reference):]
        report.update(after_command=tail)
        if divergence or tail != [[first_play['pixels_sha256'], first_play['palette_sha256']]]:
            raise AssertionError('screen sequences differ')
        report['status'] = 'pass'
    except (AssertionError, OSError, KeyError, StopIteration, json.JSONDecodeError) as error:
        report.update(status='fail', error=str(error) or type(error).__name__)
    print(json.dumps(report))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
