"""Real-window-key acceptance for the ten v1.3 additions, always muted.

Source admission remains the separate v13_cheat_* gates. This checks the app
join, command delivery, mode reset, movement, palette and music requests.
"""
import argparse
import json
import os
from pathlib import Path
from real_input import Session, build_helper, MAC_TO_VK

ROOT = Path(__file__).resolve().parents[1]
KEYS = {chr(v):k for k,v in MAC_TO_VK.items() if 65 <= v <= 90}
MENU = [{'ms':ms+d,'key':13,'down':1-d//80} for ms in (3000,5000,7000) for d in (0,80)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir',type=Path,required=True)
    args = p.parse_args()
    out = args.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'menu.json').write_text(json.dumps(MENU))
    session = Session(out,helper=build_helper(ROOT/'work/cheat-codes/post-window-input'))
    report = {'check':'v13-cheats','status':'fail','commands':[]}
    def live():
        try:return json.loads((out/'live.json').read_text())
        except (ValueError,OSError):return {}
    def wait(predicate,seconds=15):
        assert session.wait(lambda:predicate(live()) or session.failed(),seconds),live()
        assert not session.failed(),live()
    def type_cheat(name,command):
        before = len(live().get('posted_commands',[]))
        for letter in name:session.post('key',KEYS[letter])
        wait(lambda s:hex(command) in s.get('posted_commands',[])[before:])
        session.sleep(.15)
        report['commands'].append({'name':name,'command':hex(command),'flags':live()['v13_cheats']})
    try:
        app = ROOT/Path(os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
        session.launch(app,{'CLAW_REAL_SPEED_KEYS':out/'menu.json'},['--save-dir',str(out/'saves'),'-ClawCheckDirectory',str(out)])
        wait(lambda s:s.get('state_vtable')=='0x50c264' and s.get('game_ms',0)>1000,120)
        flags = live()['v13_cheats']
        assert all(flags[k]==0 for k in ('long_range','easy','turbo','bounce','cheated')),flags
        for name,command,field in [('MPWILDWACKY',0x80b4,'sprite_flags'),('MPGLOOMY',0x80ad,'palette_gray'),
                                   ('MPBOUNCECOUNT',0x80b3,'bounce'),('MPLONGRANGE',0x80b2,'long_range'),
                                   ('MPEASYMODE',0x80b5,'easy'),('MPTWINTURBO',0x80b6,'turbo')]:
            for enabled in (True,False):
                type_cheat(name,command)
                value = live()['v13_cheats'][field]
                assert bool(value&4 if field=='sprite_flags' else value)==enabled,(name,enabled,live()['v13_cheats'])
                if name=='MPGLOOMY':
                    from PIL import Image,ImageChops
                    frame=(live()['frame']//300+1)*300
                    session.run(frame-live()['frame']+2)
                    path=out/f'frame-{frame:05d}.png'
                    image=Image.open(path).convert('RGB');r,g,b=image.split()
                    gray=ImageChops.difference(r,g).getbbox() is None and ImageChops.difference(g,b).getbbox() is None
                    assert gray==enabled,(path,gray,enabled)
                    report.setdefault('screenshots',[]).append(str(path))
                if name=='MPTWINTURBO':
                    for key,sign in [(124,1),(123,-1)]:
                        session.post('press',key,'down');session.sleep(.2)
                        speed = live()['v13_cheats']['velocity_x']
                        if enabled:assert speed==sign*450,(name,sign,speed,live())
                        else:assert abs(speed) in (225,285,300),(name,speed,live())
                        session.post('press',key,'up');session.sleep(.1)
        type_cheat('MPNOISE',0x80ae);first = live()['v13_cheats']['noise_cursor']
        type_cheat('MPNOISE',0x80ae);assert live()['v13_cheats']['noise_cursor']!=first
        for name,command,tempo,ms in [('MPMAESTRO',0x80af,150,2500),('MPLANGSAM',0x80b0,75,2500),('MPNORMALMUSIC',0x80b1,100,1000)]:
            type_cheat(name,command)
            events = live()['v13_cheats'].get('music_services',[])
            assert any(e.get('service')=='AIL_set_sequence_tempo' and e.get('tempo')==tempo and e.get('milliseconds')==ms for e in events),events[-5:]
        report['status'] = 'pass'
    except (AssertionError,RuntimeError,KeyError) as e:report['error'] = str(e)
    finally:session.close()
    (out/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report));return report['status']!='pass'


if __name__=='__main__':raise SystemExit(main())
