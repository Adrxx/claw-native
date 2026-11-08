"""Compare all original 640x480 viewport layouts using confirmed physical +/- keys.

Requires the default and low-detail original.json and original-*.png captures
under work/parity-display from the hash-pinned original probe. Retains exact
indexed border/HUD, detail and foreground crops, native Display page settings
and screenshots. --real-time uses the display timer.
Platform-only DirectDraw choices are scoped in work/parity-display/matrix.json.
"""
import argparse
import json
import os
import sys
import time
import subprocess
import shutil
from pathlib import Path
from PIL import Image
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/parity-display'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--real-time', action='store_true')
    ap.add_argument('--lifecycle-only', action='store_true')
    ap.add_argument('--low-detail', action='store_true')
    a = ap.parse_args()
    reference_dir = WORK/('low-detail' if a.low_detail else '')
    out = WORK / ('check-low-detail' if a.low_detail else 'lifecycle' if a.lifecycle_only else 'realtime' if a.real_time else 'check')
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    ref = json.loads((reference_dir/'original.json').read_text())
    assert ref['status'] == 'pass' and ref['original_sha256'] == '350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263'
    menu_reference={r['mark']:r['settings'] for r in ref.get('menu_rows',[])}
    rows = {r['accepted']:r for r in ref['rows'] if r['requested'] == r['accepted']}
    helper = build_helper(WORK/'post-window-input')
    session = Session(out, fast=not (a.real_time or a.lifecycle_only), helper=helper)
    app = Path(os.environ.get('CLAW_DERIVED_DATA', ROOT/'work/MacCatalyst'))/'Build/Products/Release-maccatalyst/Claw.app'
    errors, samples, route, pixel_checks = [], [], [], []
    def compare_crop(label, native, original, box):
        if native.mode != 'P' or native.size != original.size or native.size != (640,480):
            raise RuntimeError(label+': expected 640x480 indexed native screenshot')
        x,y=original.crop(box).tobytes(),native.crop(box).tobytes()
        differences=sum(i!=j for i,j in zip(x,y))
        pixel_checks.append(dict(mark=label,box=box,pixels=len(x),differences=differences))
        if differences:errors.append(f'{label}: pixel differences {differences}')
    def read(name):
        try:return json.loads((out/name).read_text())
        except (ValueError,OSError):return {}
    def key(code):
        session.post('key',code); session.sleep(.2)
        live=read('live.json');route.append(dict(key=code,page=live.get('menu_page'),index=live.get('menu_index'),frame=live.get('frame')))
    def mark(name, setting=None):
        r = session.mark(name)
        if not r:raise RuntimeError('missing mark '+name)
        for offset,value in menu_reference.get(name,{}).items():
            if r['application_words'][int(offset,16)//4] != value:errors.append(f'{name}: {offset} differs from original')
        if setting:
            field,want=setting
            if r['application_words'][field//4]!=want:errors.append(f'{name}: setting +{field:x} != {want}')
        if read('live-state.json').get('status')!='running':errors.append(name+': not running')
        return r
    def finish():
        result=dict(check='display-modes',status='pass' if not errors else 'fail',real_time=a.real_time or a.lifecycle_only,lifecycle_only=a.lifecycle_only,low_detail=a.low_detail,samples=samples,pixel_checks=pixel_checks,route=route,errors=errors,retries=session.retries)
        (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return bool(errors)
    try:
        session.launch(app, {}, ['--save-dir',str(out/'saves'),'--menu-live-check',str(out),'-ClawCheckDirectory',str(out),'--stationary-cursor'])
        if not session.wait(lambda: read('live.json').get('menu_page')==10000,40):raise RuntimeError('main menu not ready')
        session.sleep(1)
        if a.lifecycle_only:
            api = WORK/'window-api'
            source = ROOT/'scripts/display-window-api.swift'
            if not api.exists() or api.stat().st_mtime < source.stat().st_mtime:
                subprocess.run(['xcrun','swiftc','-O',str(source),'-o',str(api)],check=True)
            def window(action):
                r=json.loads(subprocess.check_output([str(api),str(session.pid),action],text=True))
                samples.append(dict(action=action,window=r));return r
            for context,want_state in [('menu','0x50c1e4'),('game','0x50c264')]:
                if context=='game':
                    key(36);key(36);key(36)
                    if not session.wait(lambda: read('live-state.json').get('state_vtable')=='50c264',90):raise RuntimeError('lifecycle Level 1 not ready')
                    for _ in range(10):key(27)
                for action,restore in [('hide','show'),('minimize','restore')]:
                    # Hold across each loss; lifecycle cleanup, without an up event, must release it.
                    session.post('press',124,'down');session.sleep(.15)
                    before=mark(context+'-'+action+'-before')
                    state=window(action)
                    if action=='hide' and not state['hidden']:raise RuntimeError('test app did not hide')
                    if action=='minimize' and not any(state['minimized']):raise RuntimeError('test window did not minimize')
                    if not session.wait(lambda: read('activation.json').get('active') is False,5):raise RuntimeError(action+': no native inactive observation')
                    time.sleep(.7)
                    stopped=read('live.json').get('frame')
                    clock=read('live.json').get('game_ms')
                    time.sleep(1.2)
                    if read('live.json').get('frame') != stopped or read('live.json').get('game_ms')!=clock:errors.append(action+': game advanced while inactive')
                    state=window(restore)
                    if not state['active']:raise RuntimeError(restore+': test app did not activate')
                    if not session.wait(lambda: read('activation.json').get('active') is True,5):raise RuntimeError(restore+': no native active observation')
                    if not session.wait(lambda: read('live.json').get('frame',0)>stopped+5,10):errors.append(restore+': frames did not resume')
                    r=mark(context+'-'+restore)
                    if r['state_vtable']!=want_state:errors.append(restore+': game state changed')
                    if r['display_viewport']!=before['display_viewport']:errors.append(restore+': viewport changed')
                    if 39 in read('live.json').get('weapons',{}).get('held_keys',[]):errors.append(restore+': arrow remained held')
                    samples.append(dict(context=context,action=action,paused_frame=stopped,resumed_frame=r['frame']))
                    # UIKit cancels the held press on deactivation, so its later OS key-up
                    # need not produce pressesEnded. Clear the OS event, then require a fresh pair.
                    session._post(['press',124,'up'])
                    key(124)
            return finish()
        # Fresh profile has no replayable movies; arrows skip the unavailable Replay Movies row.
        key(125);key(125);key(36);key(125);key(125);key(36)
        if read('live.json').get('menu_page')!=13005:raise RuntimeError('Display page not reached: '+str(route))
        mark('detail-default',(0x124,1));key(36);mark('detail-off',(0x124,0));key(36);mark('detail-on',(0x124,1))
        if a.low_detail:key(36)
        key(125);key(36);mark('front-off',(0x128,0));key(36);mark('front-on',(0x128,1))
        key(125)
        for _ in range(10):key(123)
        mark('main-area-min',(0x68,1))
        for _ in range(10):key(124)
        mark('main-area-max',(0x68,10))
        key(125);key(36);mark('movies-on',(0x120,1));key(36);mark('movies-off',(0x120,0))
        # Escape pops Display, Options; choose Single Player > New Game > Level One.
        key(53);key(53);key(126);key(126);key(36);key(36);key(36)
        if not session.wait(lambda: read('live-state.json').get('state_vtable')=='50c264',90):raise RuntimeError('Level 1 not ready')
        session.sleep(.3)
        detail=mark('level-detail',(0x124,0 if a.low_detail else 1))
        if detail.get('display_detail_entities')!=ref.get('detail_entities'):
            errors.append(f'detail entities {detail.get("display_detail_entities")} != original {ref.get("detail_entities")}')
        for front in [0,1]:
            for code in [53,125,125,36,125,36,36,125,125,125,36,53]:key(code)
            r=mark(f'play-front-{front}',(0x128,front))
            want=next(e['flags'] for e in ref['front_rows'] if e['front']==front)
            if r.get('display_plane_flags')!=want:errors.append(f'front {front}: plane flags {r.get("display_plane_flags")} != {want}')
            # Static foreground terrain, below the animated actors. The original
            # on/off captures must differ here, so matching flags alone cannot pass.
            box=(0,416,128,448)
            original=Image.open(reference_dir/f'original-front-{front}.png')
            other=Image.open(reference_dir/f'original-front-{1-front}.png')
            if original.crop(box).tobytes()==other.crop(box).tobytes():
                raise RuntimeError('front-layer reference has no visible witness')
            compare_crop(f'play-front-{front}',Image.open(out/f'play-front-{front}.png'),original,box)
        for n in list(range(10,0,-1))+list(range(2,11)):
            if samples:key(27 if n<samples[-1]['layout'] else 24)
            r = mark(f'layout-{len(samples):02d}-{n}',(0x68,n))
            if r.get('display_viewport')!=rows[n]['rect']:errors.append(f'layout {n}: viewport {r.get("display_viewport")} != {rows[n]["rect"]}')
            native = Image.open(out/f'layout-{len(samples):02d}-{n}.png')
            original = Image.open(reference_dir/f'original-layout-{n}.png')
            if native.mode!='P':raise RuntimeError('native screenshot is not indexed')
            # Static border pixels outside the original inclusive gameplay rectangle.
            top,bottom=rows[n]['rect'][1],rows[n]['rect'][3]
            regions=[(0,0,640,top),(0,bottom+1,640,480)] if top else []
            diffs=[]
            for box in regions:
                x,y=original.crop(box).tobytes(),native.crop(box).tobytes()
                diffs.append(sum(i!=j for i,j in zip(x,y)))
            if any(diffs):errors.append(f'layout {n}: border pixel differences {diffs}')
            # This stationary scenery region changes with High Detail in the
            # original and stays within every viewport. Compare exact indices;
            # animated objects elsewhere have deliberately different frame times.
            box=(384,256,416,320)
            other_dir=WORK/('' if a.low_detail else 'low-detail')
            other=Image.open(other_dir/f'original-layout-{n}.png')
            if original.crop(box).tobytes()==other.crop(box).tobytes():
                raise RuntimeError('detail reference has no visible witness')
            compare_crop(f'layout-{n}-detail',native,original,box)
            # HUD digits remain exact through both directions of every size
            # transition. Exclude the independently animated treasure/heart icons.
            for label,box in [('score',(30,0,117,30)),('health',(580,0,616,30)),
                              ('ammo',(594,40,610,52))]:
                compare_crop(f'layout-{n}-hud-{label}',native,original,box)
            samples.append(dict(layout=n,viewport=r.get('display_viewport'),border_pixel_differences=diffs))
        key(24);mark('upper-clamp',(0x68,10))
        for _ in range(10):key(27)
        mark('lower-clamp',(0x68,1))
        key(53);paused=mark('pause-small',(0x68,1));key(53);resumed=mark('resume-small',(0x68,1))
        if paused['state_vtable']!='0x50c044' or resumed['state_vtable']!='0x50c264':errors.append('small viewport pause/resume state differs')
    except Exception as e:
        fault=read('live-state.json').get('error','')
        errors.append(str(e)+((': '+fault) if fault else ''))
    finally:session.close()
    return finish()
if __name__=='__main__':sys.exit(main())
