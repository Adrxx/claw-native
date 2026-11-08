"""Real Catalyst key releases survive UIPress cancellation when focus changes.

Both muted instances belong to this check. Every release must reach input.json
exactly once at its planned paused frame, with no retry. Also exercise ordinary
foreground releases to catch duplicate AppKit/UIKit delivery.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

from real_input import Session, build_helper, MAC_TO_VK

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'work/key-up-boundary/check')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    helper = build_helper(ROOT / 'work/key-up-boundary/post-window-input')
    derived = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT / 'work/MacCatalyst'))
    app = derived / 'Build/Products/Release-maccatalyst/Claw.app'
    sessions = []
    result = {'check': 'key-up-boundary', 'status': 'fail', 'steps': [], 'errors': [], 'cancellations': []}

    def launch(name):
        folder = out / name
        folder.mkdir()
        session = Session(folder, helper=helper)
        sessions.append(session)
        session.launch(app, {}, ['--menu-live-check', str(folder), '-ClawCheckDirectory', str(folder)])
        return session

    def close(session):
        session.close()
        session.pid = None

    def release(first, code, unfocus):
        before = first.input_state()
        frame = first.gate()['frame']
        first.post('press', code, 'up')
        after = first.input_state()
        name = f'{MAC_TO_VK[code]}:up'
        assert after['transitions'].get(name, 0) == before['transitions'].get(name, 0) + 1
        assert after['frame'] == frame == first.gate()['frame']
        first.run(0)
        assert first.transitions() == after['transitions'], 'duplicate release'
        assert not first.retries, first.retries
        result['steps'].append({'key': MAC_TO_VK[code], 'unfocused': unfocus, 'frame': frame,
                                'up_count': after['transitions'][name]})

    try:
        codes = (11, 14, 53, 59) * 2  # B, E, Escape and Control
        first = launch('foreground')
        for code in codes:
            first.post('press', code, 'down')
            first.run(4)
            release(first, code, False)
        close(first)
        for index, code in enumerate(codes):
            # Launching another owned window deterministically cancels the
            # first window's UIPress, exactly as an external focus change does.
            first = launch(f'cancel-{index}-first')
            first.post('press', code, 'down')
            first.run(4)
            second = launch(f'cancel-{index}-second')
            release(first, code, True)
            events = json.loads((first.out / 'input-boundary.json').read_text())
            cancelled = [e for e in events if e.get('boundary') == 'cancelled' and MAC_TO_VK[code] in e.get('keys', [])]
            assert cancelled, 'focus probe did not cancel the held UIPress'
            result['cancellations'].extend(cancelled)
            close(first)
            close(second)
        for s in sessions:
            counts = s.transitions()
            assert all(counts.get(k.replace(':down', ':up'), 0) == n for k, n in counts.items() if k.endswith(':down'))
        result['status'] = 'pass'
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        for s in sessions:
            s.close()
    (out / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return result['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
