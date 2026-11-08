"""Idle menu regression: original attract/title/return, with confirmed real keys.

First refresh the original join trace with:
  work/test-env/bin/python work/main-menu-idle/trace.py --step-ms 250 --seconds 280
Run --real-time for wall-clock waits beyond each original timeout (120 seconds
on Main, 180 on child pages). The default input gate runs the same frame clock
quickly. --pages accepts a comma-separated subset for focused retries.
"""
import argparse
import json
import os
import time
from pathlib import Path
from real_input import Session, build_helper, alive

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'main': [], 'single-player': [10001], 'new-game': [10001, 11001],
    'load-game': [10001, 11002],
    'replay-movies': [10003], 'options': [10004],
    'display': [10004, 13005], 'audio': [10004, 13004], 'quit': [10006],
}
MENU, TITLE = '0x50c1e4', '0x50c2d4'


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-time', action='store_true')
    parser.add_argument('--pages', default=','.join(PAGES))
    parser.add_argument('--config', default='Release')
    parser.add_argument('--repeat', action='store_true', help='also require a second natural title cycle on Main')
    parser.add_argument('--dismiss', action='store_true', help='also dismiss Title with a confirmed Return')
    parser.add_argument('--movies', action='store_true', help='enable the original alternating idle introduction movie')
    parser.add_argument('--navigation-only', action='store_true', help='check routes before starting long wall-clock waits')
    parser.add_argument('--resume', action='store_true', help='retain completed pages from this same build and continue')
    args = parser.parse_args()
    reference = read(ROOT/'work/main-menu-idle/original.json')
    assert reference.get('status') == 'pass' and reference.get('stop') is None
    assert reference['executable_sha256'] == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
    transitions = reference['idle_transitions']
    assert [t['state']['vtable'] for t in transitions[:3]] == [MENU, TITLE, MENU]
    assert 119000 <= transitions[1]['elapsed_ms'] <= 121000
    assert 7000 <= transitions[2]['elapsed_ms']-transitions[1]['elapsed_ms'] <= 15000
    out = ROOT/'work/main-menu-idle'/(('real-time' if args.real_time else 'fast')+('-movies' if args.movies else '')+('-navigation' if args.navigation_only else ''))
    out.mkdir(parents=True, exist_ok=True)
    result = dict(check='main-menu-idle', status='fail', real_time=args.real_time, navigation_only=args.navigation_only,
                  original_transitions=transitions, pages=[], errors=[])
    if args.resume:
        result['pages'] = read(out/'result.json').get('pages', [])
    app = ROOT/os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst')/'Build/Products'/f'{args.config}-maccatalyst/Claw.app'
    helper = build_helper(ROOT/'work/main-menu-idle/post-window-input')
    session = None
    try:
        for name in args.pages.split(','):
            if any(p['name'] == name for p in result['pages']):
                continue
            route = PAGES[name]
            evidence = out/name
            evidence.mkdir(parents=True, exist_ok=True)
            for filename in ('live.json', 'real-speed.json', 'movie-state.json'):
                (evidence/filename).unlink(missing_ok=True)
            session = Session(evidence, fast=not args.real_time, helper=helper)
            enable_movies = args.movies or name == 'replay-movies'
            extra = ['--movie-unlock-check'] if name == 'replay-movies' else []
            session.launch(app, {}, ['--movie-flow-check' if enable_movies else '-ClawCheckDirectory',
                                    str(evidence), '--save-dir', str(evidence/'saves'), *extra])
            live = lambda: read(evidence/'live.json')
            def healthy():
                failure = read(evidence/'real-speed.json')
                if failure.get('status') == 'fail':
                    raise RuntimeError(failure.get('error', str(failure)))
                if session.failed() or not alive(session.pid):
                    raise RuntimeError('app stopped: '+str(session.gate()))
            def wait(predicate, seconds):
                def checked():
                    healthy()
                    return predicate()
                if not session.wait(checked, seconds, step=30):
                    raise RuntimeError(f'{name}: timeout at state {live().get("state_vtable")}, page {live().get("menu_page")}')
            def tap(code):
                session.post('key', code)
                session.sleep(.15)
                healthy()
            wait(lambda: live().get('menu_page') == 10000, 30)
            for target in route:
                for _ in range(18):
                    if live().get('menu_selected') == target:
                        break
                    tap(125)
                assert live().get('menu_selected') == target, (target, live().get('menu_selected'))
                assert not live().get('menu_selected_disabled'), f'{target} is unavailable'
                tap(36)
                wait(lambda: live().get('menu_page') == target, 10)
            initial = live()
            record = dict(name=name, page=initial['menu_page'], transitions=[], input=session.transitions())
            if args.navigation_only:
                result['pages'].append(record)
                session.close()
                session = None
                continue
            start = time.monotonic()
            # No input at all between here and the natural title return.
            for second in range(60):
                session.sleep(1)
                healthy()
                assert live().get('state_vtable') == MENU, f'{name}: attract before original timeout'
                assert live().get('menu_page') == record['page'], f'{name}: idle changed page'
            record['sixty_seconds'] = dict(wall_seconds=time.monotonic()-start, frame=live().get('frame'))
            wait(lambda: live().get('state_vtable') == TITLE or session.movie().get('playing'), 135 if route else 75)
            if session.movie().get('playing'):
                # AVPlayer advances on wall time even when the game uses the
                # fast input gate. Game-frame waits cannot time movie decoding.
                ready_until = time.monotonic()+15
                while not (session.movie().get('ready') and session.movie().get('media_seconds', 0) >= 2):
                    healthy()
                    assert time.monotonic() < ready_until, 'introduction did not advance'
                    time.sleep(.05)
                movie = session.movie()
                assert movie['movie'] == 2 and movie['silent'], {k:movie.get(k) for k in ('movie','silent','playing')}
                record['transitions'].append(dict(movie=2, wall_seconds=time.monotonic()-start,
                                                   media_seconds=movie['media_seconds']))
                tap(48)
                wait(lambda: not session.movie().get('playing') and live().get('menu_page') == record['page'], 25)
                while live().get('menu_page') != 10000:
                    tap(53)
            else:
                record['transitions'].append(dict(state=TITLE, wall_seconds=time.monotonic()-start, frame=live().get('frame')))
                session.mark('title')
                wait(lambda: live().get('state_vtable') == MENU and live().get('menu_page') == 10000, 25)
            record['transitions'].append(dict(state=MENU, wall_seconds=time.monotonic()-start, frame=live().get('frame')))
            if args.repeat or args.dismiss:
                wait(lambda: live().get('state_vtable') == TITLE or session.movie().get('playing'), 135)
                if session.movie().get('playing'):
                    assert session.movie().get('movie') == 2, session.movie()
                    record['idle_movie'] = {k:session.movie().get(k) for k in ('movie','playing','ready','silent')}
                    tap(48)
                elif args.dismiss:
                    tap(36)
                wait(lambda: live().get('state_vtable') == MENU, 25)
                record['second_cycle'] = dict(dismissed=args.dismiss, frame=live().get('frame'))
            # A title return creates a fresh Main page; a movie return keeps
            # its menu and selection. Select Single Player in either case.
            for _ in range(18):
                if live().get('menu_selected') == 10001:
                    break
                tap(125)
            assert live().get('menu_selected') == 10001
            tap(36)
            wait(lambda: live().get('menu_page') == 10001, 10)
            tap(53)
            wait(lambda: live().get('menu_page') == 10000, 10)
            record['returned_menu_input'] = session.transitions()
            record['retries'] = session.retries
            result['pages'].append(record)
            (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(record), flush=True)
            session.close()
            session = None
        result['status'] = 'pass'
    except (RuntimeError, AssertionError) as error:
        result['errors'].append(str(error))
    finally:
        if session:
            session.close()
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
