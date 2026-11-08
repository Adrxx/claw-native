"""Real events prove that the fast input gate ignores unrelated keys/directions."""
import json
import os
from pathlib import Path
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/real-input-gate'
OUT.mkdir(parents=True, exist_ok=True)
session = Session(OUT, helper=build_helper(OUT / 'post-window-input'))
result = {'check': 'real-input-gate', 'status': 'fail'}
try:
    session.launch(ROOT / os.environ.get('CLAW_DERIVED_DATA', 'work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app', {},
                   ['-ClawCheckDirectory', str(OUT)])
    frame = session.frames
    sequence = session.seq
    session._command('await 66 up 1')
    # B down is the wrong direction; A down/up is the wrong key.
    for event in [('press', 11, 'down'), ('press', 0, 'down'), ('press', 0, 'up')]:
        session._post(event)
    gate = session.gate()
    assert gate['seq'] == sequence and gate['frame'] == frame, gate
    assert session.transitions().get('66:down') == 1, session.transitions()
    assert session.transitions().get('65:up') == 1, session.transitions()
    session._post(('press', 11, 'up'))
    gate = session._gate_wait(5)
    assert gate['seq'] == sequence + 1 and gate['frame'] == frame, gate
    session.run(3)
    assert session.frames == frame + 3
    result.update(status='pass', paused_frame=frame, resumed_frame=session.frames,
                  transitions=session.transitions())
finally:
    session.close()
    (OUT / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
