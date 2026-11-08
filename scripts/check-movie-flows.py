"""Muted Release Replay Movies and level-end checks, using confirmed real window keys.

Only --movie-unlock-check seeds completed profile records for the list check;
level-end uses MPSCULLY and the game's own level/results transitions.
Usage: work/test-env/bin/python scripts/check-movie-flows.py [--mode replay|level]
"""
import argparse
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from real_input import Session, build_helper, real_time_requested
from responsiveness import check_heartbeats

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/movie-level-replay'
LEVEL, RESULTS = '0x50c264', '0x50c0c4'
CHEAT = [46, 35, 1, 8, 32, 37, 37, 16]  # MPSCULLY


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


class MovieSession(Session):
    def _received(self):
        state = read(self.out / 'movie-state.json')
        if state.get('playing'):
            return state.get('input_received'), read(self.out / 'live.json').get('frame')
        return super()._received()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['replay', 'level'], default='replay')
    parser.add_argument('--config', default='Release')
    parser.add_argument('--natural', action='store_true', help='let each replay entry finish, including Combined Cutscenes')
    parser.add_argument('--entry', type=lambda x: int(x, 0), help='one Replay Movies command ID')
    parser.add_argument('--combined-next', action='store_true', help='let the introduction finish, then skip the next queued movie')
    parser.add_argument('--real-time', action='store_true')
    parser.add_argument('--paper-timing', action='store_true',
                        help='require --real-time and compare startup paper duration with the original trace (10 percent)')
    args = parser.parse_args()
    if args.paper_timing and not args.real_time:
        parser.error('--paper-timing requires --real-time')
    os.environ["CLAW_REAL_INPUT_FOREGROUND"] = "1"
    out = WORK / (args.mode + ('-combined-next' if args.combined_next else '-natural' if args.natural else '-skip'))
    out.mkdir(parents=True, exist_ok=True)
    for name in ['live.json', 'movie-state.json', 'real-speed.json', 'result.json', 'progress.json']:
        (out / name).unlink(missing_ok=True)
    helper = build_helper(WORK / 'post-window-input')
    session = MovieSession(out, fast=not real_time_requested(args.real_time), helper=helper)
    result = {'check': 'movie-flows', 'mode': args.mode, 'natural': args.natural, 'status': 'fail', 'errors': [], 'steps': []}
    live = lambda: read(out / 'live.json')
    movie = lambda: read(out / 'movie-state.json')

    def wait(predicate, seconds=30):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            failure = read(out / 'real-speed.json')
            if failure.get('status') == 'fail':
                raise RuntimeError(failure.get('error', str(failure)))
            if movie().get('error'):
                raise RuntimeError(movie()['error'])
            if predicate():
                return
            if session.fast:
                session.run(3)
            else:
                time.sleep(.05)
        now, film = live(), movie()
        raise RuntimeError(f'timeout; state={now.get("state_vtable")}, level={now.get("level")}, page={now.get("menu_page")}, selected={now.get("menu_selected")}, movie={film.get("movie")}, playing={film.get("playing")}, media={film.get("media_seconds")}')

    def key(code):
        session.post('key', code)
        session.sleep(.15)

    def select(target):
        visited = []
        for _ in range(18):
            current = live().get('menu_selected')
            if current == target:
                return
            visited.append(current)
            key(125)  # Down
        raise RuntimeError(f'menu selection {target} absent; visited {visited}')

    def replay(entry, movie_id):
        select(entry)
        before = len(live().get('movies', []))
        prior = live()
        key(36)
        wait(lambda: movie().get('playing') and movie().get('movie') == movie_id and movie().get('media_seconds', 0) > 2)
        # Capture this instance's window, including the AVPlayer layer (the
        # indexed game screenshot does not contain the movie overlay).
        window = json.loads(subprocess.check_output([str(helper), str(session.pid), 'window'], text=True)).get('window')
        if window:
            capture = subprocess.run(['screencapture', '-x', '-l', str(window), str(out / f'movie-{entry:x}.png')], capture_output=True, text=True)
            if capture.returncode:
                result.setdefault('capture_errors', []).append(capture.stderr.strip())
        if args.combined_next:
            wait(lambda: movie().get('playing') and movie().get('movie') == 3 and movie().get('media_seconds', 0) > .3, 480)
        if not args.natural:
            key(48)  # Tab: a real key with no gameplay mapping.
        wait(lambda: len(live().get('movies', [])) > before and not movie().get('playing'), 1200)
        after = live()
        records = [m for m in after.get('movies', [])[before:] if 'file' in m]
        expected = [2, 3] if args.combined_next else list(range(2, 11)) if entry == 0x3a99 and args.natural else [movie_id]
        if [m['movie'] for m in records] != expected:
            raise RuntimeError(f'entry {entry}: movies {records}, expected {expected}')
        expected_outcomes = ['finished', 'skipped'] if args.combined_next else [('finished' if args.natural else 'skipped')] * len(records)
        if [m['outcome'] for m in records] != expected_outcomes:
            raise RuntimeError(f'entry {entry}: wrong outcomes {records}')
        if (prior.get('menu_page'), prior.get('app_state'), entry) != (after.get('menu_page'), after.get('app_state'), after.get('menu_selected')):
            raise RuntimeError(f'entry {entry} did not return to its same menu state/selection')
        if any(not m['audio'].get('isMuted') or m['audio'].get('volume') != 0 for m in records):
            raise RuntimeError('movie audio not muted')
        result['steps'].append({'entry': entry, 'movies': records, 'returned_page': after.get('menu_page'), 'returned_state': after.get('app_state'), 'same_state': prior.get('app_state') == after.get('app_state')})
        (out / 'progress.json').write_text(json.dumps(result, indent=2))

    try:
        app = ROOT / f'{os.environ.get("CLAW_DERIVED_DATA", "work/MacCatalyst")}/Build/Products/{args.config}-maccatalyst/Claw.app'
        extra = ['--movie-unlock-check'] if args.mode == 'replay' else []
        while float(subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True).split()[1]) >= 16:
            time.sleep(10)
        session.launch(app, {}, ['--movie-flow-check', str(out), '--save-dir', str(out / 'saves'), *extra])
        wait(lambda: live().get('menu_page') == 10000)
        if args.mode == 'replay':
            select(10003)
            key(36)
            wait(lambda: live().get('menu_page') == 10003)
            session.mark('replay-menu')
            entries = [0x3a99] if args.combined_next else [args.entry] if args.entry else list(range(0x3a9a, 0x3aa3)) + [0x3a99]
            for entry in entries:
                replay(entry, 2 if entry == 0x3a99 else entry - 0x3a9a + 2)
        else:
            for _ in range(3):
                key(36)
                session.sleep(2)
            wait(lambda: live().get('state_vtable') == LEVEL and live().get('level') == 1, 120)
            for level in [1, 2]:
                for code in CHEAT:
                    key(code)
                wait(lambda: live().get('state_vtable') == RESULTS or (level == 2 and movie().get('playing')), 30)
                # The results enter virtual can play the cutscene before this
                # blocked frame publishes the new state to live.json.
                if level == 2 and movie().get('playing'):
                    wait(lambda: movie().get('movie') == 3 and movie().get('media_seconds', 0) > .3)
                    key(48)
                wait(lambda: live().get('state_vtable') == RESULTS, 30)
                for n in range(10):
                    session.sleep(3)
                    if movie().get('playing') or live().get('state_vtable') != RESULTS:
                        break
                    key(36)
                if level == 2 and movie().get('playing'):
                    wait(lambda: movie().get('playing') and movie().get('movie') == 3 and movie().get('media_seconds', 0) > .3, 60)
                    key(48)
                wait(lambda: live().get('state_vtable') == LEVEL and live().get('level') == level + 1, 120)
                result['steps'].append({'finished_level': level, 'next_level': live().get('level'), 'movies': live().get('movies')})
                session.mark(f'level-{level + 1}')
        heartbeats = live().get('responsiveness', [])
        errors = check_heartbeats(heartbeats)
        if not any(r.get('scope', '').startswith('movie-') for r in heartbeats):
            errors.append('no movie heartbeat scope')
        if errors:
            raise RuntimeError('; '.join(errors))
        result['heartbeat_max_gap_ms'] = max(r['max_gap_ms'] for r in heartbeats)
        if args.paper_timing:
            reference = read(ROOT / 'work/paper-roll/reference.json')
            writes = reference.get('primary_unlocks', [])
            if reference.get('status') != 'pass' or len(writes) < 2:
                raise RuntimeError('missing original paper timing reference')
            # Include the final repeated endpoint write: 242 primary unlocks,
            # 241 distinct screens. Its physical clock brackets the unroll.
            original_ms = writes[-1]['ms'] - writes[0]['ms']
            paper = next((r for r in heartbeats if r.get('scope') == '0x4ec9c0'), None)
            if paper is None or original_ms <= 0:
                raise RuntimeError('missing startup paper duration')
            native_ms = paper['seconds'] * 1000
            relative_error = abs(native_ms / original_ms - 1)
            result['paper_timing'] = dict(original_ms=original_ms, native_ms=native_ms,
                                         relative_error=relative_error, tolerance=.1, clock='real')
            if relative_error > .1:
                raise RuntimeError(f'paper duration {native_ms:.1f} ms vs original {original_ms} ms exceeds 10 percent')

        result['status'] = 'pass' 
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        result['last_live'] = live()
        result['last_movie'] = movie()
        result['retries'] = session.retries
        session.close()
        (out / 'result.json').write_text(json.dumps(result, indent=2))
        steps = []
        for step in result['steps']:
            steps.append({k: v for k, v in step.items() if k not in ('movies', 'returned_state')} | {'movies': [
                {k: m.get(k) for k in ('movie', 'outcome', 'result')} for m in step.get('movies', []) if 'file' in m]})
        (out / 'evidence.json').write_text(json.dumps(steps, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k not in ('last_live', 'last_movie')}))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
