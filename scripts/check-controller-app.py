"""Controller delivery/remapping through the native Release host.

Controller samples use the diagnostic physical-API provider, not hardware.
Menu navigation and Controls edits use simulated pad samples; keyboard
coexistence uses confirmed window-server delivery. Unit comparison
separately checks the original masks, thresholds, latches and internal mouse API.
"""
import argparse
import json
import os
import shutil
from pathlib import Path
from real_input import Session, build_helper

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/controller-input-check/app'
DEFAULT_KEYS = [32,17,18,16,90,49,50,51,52]
DEFAULT_BUTTONS = [1,2,4,56,0,0,64,128,0]
MAC = dict(up=126,down=125,ret=36,esc=53,ctrl=59,right=124,left=123)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=os.environ.get('CLAW_CONFIG','Release'))
    args = parser.parse_args()
    helper = build_helper(ROOT/'work/menu-controls/post-window-input')
    app = ROOT / os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst') / 'Build/Products' / f'{args.config}-maccatalyst/Claw.app'
    shutil.rmtree(WORK,ignore_errors=True);WORK.mkdir(parents=True)
    out=WORK/'session';out.mkdir()
    session=Session(out,fast=True,helper=helper)
    result=dict(check='controller-app',status='fail',steps=[],errors=[],
        controller_delivery='Diagnostic samples through the native physical API provider; not physical controller input.',
        controls_delivery='Simulated controller navigation/remapping plus confirmed real window-server keyboard events.',
        hardware_acceptance=dict(assigned_to='owner',needed='Connect a supported extended gamepad on Mac and iPad; verify D-pad/left stick, A/B/X/Y, shoulders, triggers, Menu, detach/reattach and saved remapping. Hardware and iPad acceptance remain unverified.'))
    def live():
        try:return json.loads((out/'live.json').read_text())
        except (OSError,ValueError):return {}
    def controls():return live().get('controls',{})
    def controller():return live().get('controller',{})
    def require(ok,message):
        if not ok:raise RuntimeError(message+': '+json.dumps(live()))
    def tap(key,count=1):
        for _ in range(count):session.post('key',MAC[key]);session.sleep(.2)
    def sample(buttons=0,x=32767,y=32767,connected=True,frames=1):
        # Diagnostic provider commands do not increment the frame gate's seq.
        with session.control.open('a') as stream:stream.write(f'j {int(connected)} {x} {y} {buttons}\n')
        session.run(frames)
        require(not session.failed(),'controller sample fault')
        return controller()
    def mark(name):
        snapshot=live()
        session.mark(name)
        result['steps'].append(dict(name=name,controller=snapshot.get('controller'),
            controls=snapshot.get('controls'),input_mask=snapshot.get('input_mask'),weapons=snapshot.get('weapons')))
    def pad_tap(buttons=0,x=32767,y=32767,count=1):
        for _ in range(count):
            sample();sample(buttons=buttons,x=x,y=y,frames=2);sample()
    def main_controls():
        pad_tap(y=0,count=4);pad_tap(buttons=1);pad_tap(y=65535);pad_tap(buttons=1)
        require(controls().get('open'),'main Controls did not open')
    def ingame_controls():
        pad_tap(buttons=256);pad_tap(y=65535,count=2);pad_tap(buttons=1);pad_tap(buttons=1)
        require(controls().get('open'),'in-game Controls did not open')
    def resume():
        tap('esc')
        if live().get('state_vtable')!='0x50c264':tap('esc')
        require(live().get('state_vtable')=='0x50c264','Level 1 did not resume')
    def remap_attack():
        pad_tap(y=65535);pad_tap(buttons=1)
        require(controls().get('draft_buttons',[0,0])[1]==4,'Right did not select original button mask 4')
    def save_attack():
        pad_tap(y=0,count=2);pad_tap(buttons=1)
        require(not controls().get('open'),'Save did not close Controls')
    def attack(button,name):
        sample();session.sleep(.8)
        before=live().get('weapons',{}).get('attack_sequence',0)
        sample(buttons=button,frames=6)
        current=live()
        require(current.get('input_mask',0)&2,name+' did not deliver attack binding')
        require(controller().get('binding_current',0)&2,name+' did not reach original binding mask')
        require(current.get('weapons',{}).get('attack_sequence',0)>before,name+' did not start hand attack')
        mark(name);sample();session.sleep(.8)
    try:
        session.launch(app,{},['--controller-input-check','--save-dir',str(WORK/'saves'),
            '--settings-dir',str(WORK/'settings'),'-ClawCheckDirectory',str(out)])
        session.sleep(3)
        require(not session.failed(),'startup fault')
        require(not controller().get('connected') and controller().get('available')==0,'disconnected startup advertised a controller')
        require(controller().get('raw',0)==0,'disconnected startup input was nonzero')
        mark('disconnected-startup')
        c=sample()
        require(c.get('connected') and c.get('available')==1 and c.get('mode')==2,'neutral controller attachment was unavailable')
        main_controls()
        require(controls().get('keys')==DEFAULT_KEYS and controls().get('buttons')==DEFAULT_BUTTONS,'native controller defaults missing')
        remap_attack();mark('draft-remap-cancel');pad_tap(buttons=2)
        require(controls().get('buttons')==DEFAULT_BUTTONS,'Cancel changed original live masks')
        # Options -> main -> Single Player -> New Game -> Level One.
        pad_tap(buttons=2)
        for _ in range(10):
            if live().get('menu_selected')==10001:break
            pad_tap(y=65535)
        require(live().get('menu_selected')==10001,'Single Player not selectable')
        pad_tap(buttons=1,count=3)
        require(session.wait(lambda:live().get('state_vtable')=='0x50c264' and live().get('game_ms',0)>3000,90),'Level 1 did not start')
        session.sleep(.5)
        for name,x,y,raw,binding in [('left',0,32767,0x10000000,0x1000000),
            ('right',65535,32767,0x20000000,0x2000000),('up',32767,0,0x40000000,0x4000000),
            ('down',32767,65535,0x80000000,0x8000000)]:
            c=sample(x=x,y=y)
            require(c.get('raw',0)&0xf0000000==raw,name+' source direction mask differs')
            require(c.get('binding_current',0)&0xf000000==binding,name+' binding direction mask differs')
            require(live().get('input_mask',0)&binding,name+' did not reach player input')
            mark('axis-'+name);sample()
        for button,mask,name in [(1,1,'A-jump'),(4,4,'X-projectile'),(8,8,'Y-cycle'),
                                 (16,8,'L1-cycle'),(32,8,'R1-cycle')]:
            sample(buttons=button,frames=2)
            require(live().get('input_mask',0)&mask,name+' did not reach existing player action')
            if button in (16,32):
                require(not(live().get('input_mask',0)&(0x20|0x40)),name+' also selected or threw a weapon')
            mark(name);sample();session.sleep(.4)
        attack(2,'default-button-2-attacks')
        ingame_controls();remap_attack();mark('draft-remap-save');save_attack()
        require(controls().get('buttons',[0,0])[1]==4,'Save did not publish remapped mask')
        require(controls().get('keys')==DEFAULT_KEYS,'Joystick remap changed keyboard actions')
        resume();sample(buttons=2,frames=6)
        require(not(live().get('input_mask',0)&2),'old button 2 still attacks after remapping')
        sample();attack(4,'remapped-button-3-attacks')
        session.close()
        out=WORK/'relaunch';out.mkdir()
        session=Session(out,fast=True,helper=helper)
        session.launch(app,{},['--controller-input-check','--save-dir',str(WORK/'saves'),
            '--settings-dir',str(WORK/'settings'),'-ClawCheckDirectory',str(out)])
        session.sleep(3);sample();main_controls()
        require(controls().get('buttons',[0,0])[1]==4,'saved controller remap did not survive relaunch')
        mark('remap-persists-across-relaunch')
        tap('up',3);tap('ret')
        require(controls().get('draft_buttons')==DEFAULT_BUTTONS and controls().get('draft')==DEFAULT_KEYS,'Defaults did not restore original keys and button masks')
        tap('down',2);tap('ret')
        require(controls().get('buttons')==DEFAULT_BUTTONS,'Defaults Save did not publish original masks')
        tap('esc')
        for _ in range(10):
            if live().get('menu_selected')==10001:break
            tap('down')
        tap('ret');tap('ret');tap('ret')
        require(session.wait(lambda:live().get('state_vtable')=='0x50c264' and live().get('game_ms',0)>3000,90),'Level 1 did not restart')
        attack(2,'defaults-button-2-attacks')
        # Detach while a direction and attack are held: source and binding latches
        # must clear. Keyboard remains independent of controller availability.
        sample(buttons=2,x=65535,frames=2)
        c=sample(connected=False,frames=2)
        require(not c.get('connected') and c.get('available')==0 and c.get('mode')==0,'detach did not disable controller source')
        require(c.get('raw')==0 and c.get('binding_current')==0,'detach retained source or binding held state')
        require(live().get('state_vtable')!='0x50c264','detach did not pause game')
        mark('detach-pauses');tap('esc')
        require(live().get('state_vtable')=='0x50c264','keyboard could not resume after detach')
        session.post('press',MAC['right'],'down');session.sleep(.1)
        require(live().get('input_mask',0)&0x2000000,'keyboard right failed without controller')
        mark('detach-keyboard-right');session.post('press',MAC['right'],'up');session.sleep(.1)
        c=sample()
        require(c.get('available')==1 and c.get('mode')==2 and c.get('raw')==0,'reattach retained stale controller state')
        mark('neutral-reattach')
        result['status']='pass'
    except Exception as error:result['errors'].append(str(error))
    finally:session.close()
    (WORK/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['status']=='pass' else 1

if __name__=='__main__':raise SystemExit(main())
