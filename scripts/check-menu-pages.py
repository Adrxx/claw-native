"""Focused main-menu acceptance, using real keys and original page captures.

--reference records the hash-pinned original locally; the default checks the app.
Only this check's muted instance and isolated storage are used.
Menu text/value regions and palettes compare exactly; animated decoration and
cursor rectangles are excluded. Help compares the entire screen.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'work/menu-pages'
MENU, HELP, CREDITS = '0x50c1e4', '0x50c11c', '0x50c174'


def pointer_helper():
    # Catalyst does not turn postToPid mouse events into UIKit touches. Route
    # mouse events through the window server, only with our own window active.
    source=OUT/'post-pointer.swift'
    code='''import AppKit
import CoreGraphics
let pid=pid_t(CommandLine.arguments[1])!
guard let app=NSRunningApplication(processIdentifier:pid) else { exit(2) }
app.activate(options:[])
usleep(200000)
guard NSWorkspace.shared.frontmostApplication?.processIdentifier==pid else { exit(3) }
let windows=CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],0) as! [[String:Any]]
let matches=windows.filter { ($0[kCGWindowOwnerPID as String] as? Int)==Int(pid) && ($0[kCGWindowLayer as String] as? Int)==0 }
let boxes=matches.compactMap { info -> CGRect? in
    guard let raw=info[kCGWindowBounds as String] as? NSDictionary else { return nil }
    return CGRect(dictionaryRepresentation:raw)
}.filter { $0.height>100 }
guard let box=boxes.max(by:{$0.width*$0.height < $1.width*$1.height}) else { exit(4) }
let scale=min(box.width/640,(box.height-28)/480)
let point=CGPoint(x:box.midX,y:box.minY+28+(box.height-28-480*scale)/2+232*scale)
let source=CGEventSource(stateID:.hidSystemState)
for type in [CGEventType.mouseMoved,.leftMouseDown,.leftMouseUp] {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier==pid else { exit(5) }
    let event=CGEvent(mouseEventSource:source,mouseType:type,mouseCursorPosition:point,mouseButton:.left)!
    event.setIntegerValueField(.mouseEventClickState,value:1)
    event.post(tap:.cghidEventTap)
    usleep(100000)
}
'''
    binary=OUT/'post-pointer'
    if not source.exists() or source.read_text()!=code or not binary.exists():
        source.write_text(code)
        subprocess.run(['xcrun','swiftc','-O',str(source),'-o',str(binary)],check=True)
    return binary


def children():
    rows = json.loads((ROOT/'work/parity/inventory.json').read_text())['items']
    nodes = [r for r in rows if r['id'].startswith('ifc:STATES/MENU/CLAW.IFC:')]
    return {r['menu_id']: [n['menu_id'] for n in nodes
                         if n['title'].rsplit(' / ', 1)[0] == r['title'] and n != r]
            for r in nodes}


def route(d):
    if getattr(d,'page_stage',0) == 0:
        d.mark('main', MENU, 10000)
        d.enter(10001); d.mark('single', MENU, 10001)
        d.enter(11001); d.mark('new-game', MENU, 11001)
        d.locked()
        d.enter(11115); d.mark('new-game-back', MENU, 10001)
        d.enter(11006)
        d.enter(10004); d.mark('options', MENU, 10004)
        d.enter(13005); d.mark('display', MENU, 13005)
        d.enter(13506); d.mark('display-back', MENU, 10004)
        d.enter(13004); d.mark('audio', MENU, 13004)
        d.enter(13405); d.mark('audio-back', MENU, 10004)
        d.enter(13006)
        d.page_stage=1
        if hasattr(d,'page_checkpoint'): d.page_checkpoint()
    if d.page_stage == 1:
        d.enter(10005); d.mark('help', HELP)
        d.tap(53); d.mark('help-return', MENU, 10000)
        d.page_stage=2
        if hasattr(d,'page_checkpoint'): d.page_checkpoint()
    if not getattr(d,'reuse_credits',False):
        d.enter(10007); d.mark('credits', CREDITS, exact=False)
        d.sleep(2); d.mark('credits-scroll', CREDITS, exact=False)
        d.tap(53)
        d.mark('credits-return', MENU, 10000)
    d.enter(10006); d.mark('quit-confirmation', MENU, 10006)
    d.enter(14002); d.mark('quit-no', MENU, 10000)
    d.pointer_single(); d.mark('pointer-single', MENU, 10001)
    d.tap(53)
    d.enter(10006); d.tap(53); d.mark('quit-escape', MENU, 10000)
    d.enter(10006); d.choose(14001); d.mark('quit-yes-selected', MENU, 10006)
    d.quit_yes()


def reference():
    from PIL import Image
    from unicorn.x86_const import UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_ECX
    from Tests.NativeMenuBase.paper_trace import PaperTrace, Complete

    class Original(PaperTrace):
        reuse_credits=True
        def hook(self,machine,address,size,user):
            super().hook(machine,address,size,user)
        def fixture(self,address):
            if address == 0x4f55e9:
                sp=self.machine.reg_read(UC_X86_REG_ESP)
                receiver=self.machine.reg_read(UC_X86_REG_ECX)
                index,count=self.word(sp+4),self.word(sp+8)
                data,size=self.word(receiver+4),self.word(receiver+8)
                assert index<=size and count<=size-index and size<=4096
                for i in range(size-index-count):
                    self.put(data+(index+i)*4,self.word(data+(index+count+i)*4))
                self.put(receiver+8,size-count)
                self.platform_call(address,'MFC CPtrArray RemoveAt')
                self.returned(0,8)
                return
            api=self.imports.get(address,(None,''))[1].split('!')[-1]
            if api == '_AIL_XMIDI_master_volume@4':
                sp=self.machine.reg_read(UC_X86_REG_ESP)
                assert self.word(sp+4) in self.midi_drivers
                self.platform_call(address,self.imports[address][1])
                self.returned(self.midi_master_volume,4)
                return
            # Native CRT services already elected by menu_claw_logic and
            # state_five: cdecl binary64 argument, one owned x87 return.
            if address in (0x4a4250,0x4a4350):
                sp=self.machine.reg_read(UC_X86_REG_ESP)
                operand=struct.unpack('<d',self.machine.mem_read(sp+4,8))[0]
                assert math.isfinite(operand)
                self.x87_result(0,float((math.ceil if address == 0x4a4250 else math.floor)(operand)))
                self.platform_call(address,'CRT ceil' if address == 0x4a4250 else 'CRT floor')
                self.returned(self.machine.reg_read(UC_X86_REG_EAX))
                return
            super().fixture(address)

        def execute_frames(self, application):
            self.application = application
            if not hasattr(self,'rows'):
                self.rows = []
                self.frame_number = 0
                self.tick()
                self.setup_navigation(application)
            # Stable-page acceptance, not a second paper-clock comparison.
            # Time queries advance one frame; the retained Credits paper
            # comparison separately checks every write on its 1 ms clock.
            self.clock_step=17
            route(self)
            raise Complete

        def page_checkpoint(self):
            self.checkpoint_path=OUT/'route.checkpoint'
            self.save_checkpoint()
            self.checkpoint_path=None

        def tick(self, key=None):
            self.frame_number += 1
            self.advance_time(self.milliseconds+17)
            # Synchronous transitions are sampled coarsely here: their exact
            # intermediate paper writes belong to check-paper-transitions.
            # Restore ordinary frame-sized queries before stable page updates.
            self.clock_step=250
            try:
                self.drain_messages(self.application)
            finally:
                self.clock_step=17
            if key is not None:
                self.run(0x429d60, self.application, (key, 1), phase='menu-page-key')
            self.run(0x428b60, self.application, phase='menu-page-frame')

        def sleep(self, seconds):
            for _ in range(round(seconds*60)):
                self.tick()

        def tap(self, code):
            key = {125:40, 36:13, 53:27}[code]
            self.pressed_keys.add(key)
            self.tick(key)
            # The real window pump can receive key-up while synchronous Help
            # entry polls for release. The trace's physical pump must publish
            # that release before delivering the queued entry command.
            self.pressed_keys.discard(key)
            for _ in range(3): self.tick()
            self.sleep(.3)

        def state(self):
            s = self.menu_state(self.application)
            s['selected'] = CHILDREN.get(s.get('menu_id'), [None])[s.get('selection', 0)] if s['vtable'] == MENU else None
            return s

        def choose(self, identifier):
            for _ in range(20):
                if self.state()['selected'] == identifier: return
                self.tap(125)
            raise AssertionError(('original cannot select',identifier,self.state()))

        def enter(self, identifier):
            self.choose(identifier); self.tap(36)

        def pointer_single(self):
            self.cursor=(320,232)
            self.pressed_keys.add(1)
            self.run(0x429d80,self.application,(1,*self.cursor),phase='menu-page-pointer-down')
            self.tick()
            self.pressed_keys.discard(1)
            self.run(0x429db0,self.application,(0,*self.cursor),phase='menu-page-pointer-up')
            self.sleep(.3)

        def mark(self, name, state, page=None, exact=True):
            s = self.state()
            assert s['vtable'] == state and (page is None or s['menu_id'] == page), (name,s)
            primary = next(o for o in self.com_objects.values() if o.get('caps') == 0x218)
            pixels = bytes(self.machine.mem_read(primary['pixels'],primary['width']*primary['height']))
            palette = bytes.fromhex(self.com_objects[primary['palette']]['entries'])
            im = Image.frombytes('P',(primary['width'],primary['height']),pixels)
            im.putpalette(bytes(c for i,c in enumerate(palette) if i%4 != 3))
            im.convert('RGB').save(OUT/'original'/f'{name}.png')
            self.rows.append(dict(name=name,state=s,exact=exact,pixels_sha256=hashlib.sha256(pixels).hexdigest(),
                                  palette_sha256=hashlib.sha256(palette).hexdigest(),frame=self.frame_number))

        def locked(self):
            visited = []
            for _ in range(4):
                self.tap(125); visited.append(self.state()['selected'])
            assert visited == [11115,11101,11115,11101], visited

        def quit_yes(self):
            self.pressed_keys.add(13)
            self.tick(13)
            # The original command is asynchronous. Deliver the command and
            # prove WM_CLOSE was posted, leaving native window teardown out.
            command = self.messages.pop(0)
            assert command[1] == 0x111, command
            target = self.word(self.word(self.application)+0x14)
            self.run(target,self.application,command[1:],phase='quit-command')
            assert (1,0x10,0,0) in self.messages, self.messages

    trace = Original()
    credits=json.loads((ROOT/'work/paper-roll/transitions/credits/comparison.json').read_text())
    assert credits['status']=='pass' and credits['paper_primary_unlocks_equal']
    error = None
    try:
        checkpoint=OUT/'route.checkpoint'
        trace.resume_checkpoint(checkpoint if checkpoint.exists() else ROOT/'work/paper-roll/transitions/startup.checkpoint')
    except Complete:
        pass
    except (Exception,KeyboardInterrupt) as caught:
        error = repr(caught)
    finally:
        for stream in trace.files.values(): stream.close()
    result = dict(status='fail' if error else 'pass',error=error,rows=getattr(trace,'rows',[]),
                  pc=hex(trace.machine.reg_read(UC_X86_REG_EIP)),phase=trace.phase,
                  credits_comparison='work/paper-roll/transitions/credits/comparison.json',
                  page_timer_query_ms=17,
                  synchronous_command_timer_query_ms=250,
                  executable_sha256=trace.program.sha256,quit_message=[1,16,0,0] if not error else None)
    (OUT/'original.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
    return bool(error)


def app_check():
    from PIL import Image, ImageChops, ImageDraw
    from real_input import Session, build_helper, alive
    ref = json.loads((OUT/'original.json').read_text())
    assert ref['status'] == 'pass', ref.get('error')
    out = OUT/'app'
    out.mkdir(exist_ok=True)
    session = Session(out, fast=False, helper=build_helper(OUT/'post-window-input'))
    pointer=pointer_helper()
    rows = []

    class App:
        def live(self): return json.loads((out/'live.json').read_text())
        def sleep(self, seconds): session.sleep(seconds)
        def tap(self, code):
            session.post('key',code); session.sleep(.3)
            assert self.live().get('status') != 'fail', self.live()
        def choose(self, identifier):
            for _ in range(20):
                if self.live().get('menu_selected') == identifier: return
                self.tap(125)
            raise AssertionError(('cannot select',identifier,self.live()))
        def enter(self, identifier): self.choose(identifier); self.tap(36)
        def pointer_single(self):
            received=self.live()['input_received']
            subprocess.run([str(pointer),str(session.pid)],check=True)
            assert session.wait(lambda:self.live().get('menu_page')==10001,5), 'real pointer did not open Single Player'
            assert self.live()['input_received']>=received+2,'pointer delivery not recorded'
        def mark(self,name,state,page=None,exact=True):
            assert session.wait(lambda:self.live().get('state_vtable') == state and
                                (page is None or self.live().get('menu_page') == page),10), (name,self.live())
            before = self.live()
            (out/f'{name}.json').unlink(missing_ok=True)
            mark = session.mark(name)
            assert mark is not None, name
            if exact:
                original_path=OUT/'original'/f'{name}.png'
                if name=='credits-return':
                    # Credits destroys/recreates the menu; Help returns to its
                    # retained menu. Use the already pixel-proven Credits
                    # terminal frame, not Help's retained selected item.
                    terminal=json.loads((ROOT/'work/paper-roll/transitions/credits/original.json').read_text())['frames'][-1]
                    assert terminal['state']['menu_id']==10000 and terminal['state']['selection']==0
                    presentation=terminal['presentations'][-1]
                    expected=presentation
                    original_path=ROOT/'work/paper-roll/transitions/credits/app/native-61.png'
                    assert before.get('menu_selected')==10001,before
                else:
                    expected = next(r for r in ref['rows'] if r['name'] == name)
                assert mark['palette_sha256']==expected['palette_sha256'],(name,'palette')
                original=Image.open(original_path).convert('RGB')
                actual=Image.open(out/f'{name}.png').convert('RGB')
                mask=Image.new('L',original.size)
                draw=ImageDraw.Draw(mask)
                # Text and value regions exclude the original animated coins,
                # logo shine and walking Claw. Full images remain retained.
                regions={10000:[(170,210,470,465)],10001:[(120,210,520,435)],
                         11001:[(35,210,620,440)],10004:[(180,210,460,410)],
                         13005:[(40,210,600,410)],13004:[(40,210,600,410)],
                         10006:[(160,185,480,255),(280,290,355,365)]}
                for rect in regions.get(page,[(0,0,639,479)]): draw.rectangle(rect,fill=255)
                if page in regions and page!=10006:
                    draw.rectangle((120,180,520,200),fill=255)
                if page is not None:
                    cursor=(320,377) if name=='credits-return' else (320,232) if name in (
                        'pointer-single','quit-escape','quit-yes-selected') else (320,240)
                    for x,y in (cursor,mark['cursor_position']):
                        draw.rectangle((x-2,y-2,x+36,y+36),fill=0)
                if page==11001: draw.rectangle((280,210,309,245),fill=0)
                if page==10001:
                    # Owner-approved unavailable custom-level action has a
                    # disabled image; its separate real-key check owns it.
                    draw.rectangle((120,294,520,331),fill=0)
                diff=ImageChops.difference(original,actual)
                channels=[ImageChops.multiply(channel,mask) for channel in diff.split()]
                bbox=Image.merge('RGB',channels).getbbox()
                if bbox: Image.merge('RGB',channels).save(out/f'{name}-diff.png')
                assert bbox is None,(name,'static page pixels',bbox)
                mark['compared_pixels']=sum(mask.histogram()[1:])
            rows.append(dict(name=name,exact=exact,state=before['state_vtable'],page=before.get('menu_page'),
                             pixels_sha256=mark['pixels_sha256'],palette_sha256=mark['palette_sha256'],
                             compared_pixels=mark.get('compared_pixels'),full_pixels_equal=exact and mark['pixels_sha256']==expected['pixels_sha256']))
            if name in ('quit-no','quit-escape'):
                assert not (out/'quit.json').exists(),name+' posted WM_CLOSE'
        def locked(self):
            visited=[]
            for _ in range(4):
                self.tap(125); visited.append(self.live().get('menu_selected'))
            assert visited == [11115,11101,11115,11101], visited
        def quit_yes(self):
            # A tap's held-frame wait cannot finish once the window closes.
            # Confirm key-down arrival, then observe only this process exit.
            expected=session.transitions().get('13:down',0)+1
            (out/'quit.json').unlink(missing_ok=True)
            session._post(['press',36,'down'])
            assert session.wait(lambda:not alive(session.pid),15), 'Quit Yes did not close its instance'
            quit=json.loads((out/'quit.json').read_text())
            assert quit['status']=='pass' and quit['message']==16 and quit['input'].get('13:down',0)>=expected,quit

    error = None
    try:
        app = ROOT/os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst')/'Build/Products/Release-maccatalyst/Claw.app'
        (out/'quit.json').unlink(missing_ok=True)
        session.launch(app,{},['--save-dir',str(out/'saves'),'--settings-dir',str(out/'settings')])
        session.sleep(3)
        route(App())
        assert rows[-1]['name'] == 'quit-yes-selected'
        hashes = {r['name']:r['pixels_sha256'] for r in rows}
        assert hashes['credits'] != hashes['credits-scroll'], 'Credits did not scroll'
    except Exception as caught:
        error = repr(caught)
    finally:
        session.close()
    result=dict(check='menu-pages',status='fail' if error else 'pass',error=error,rows=rows,
                input=session.transitions(),retries=session.retries,quit_exited=not error)
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return bool(error)


def coverage():
    """Map commands to scoped checks; keep inherited acceptance dated/scoped."""
    inventory=json.loads((ROOT/'work/parity/inventory.json').read_text())
    queue=json.loads((ROOT/'tools/queue.json').read_text())
    tasks={t['id']:t for t in queue['tasks']}
    commands={
        'parity-menu-pages':'work/test-env/bin/python scripts/check-menu-pages.py',
        'parity-save-load-profiles':'work/test-env/bin/python work/save-load/check-round-trip.py',
        'parity-pause-gameover':'work/test-env/bin/python scripts/check-pause-gameover.py',
        'parity-audio-switches-output':'work/test-env/bin/python scripts/check-live-audio.py',
        'app-movies-level-and-replay':'work/test-env/bin/python scripts/check-movie-flows.py',
        'parity-display-modes':'work/test-env/bin/python scripts/check-display-modes.py',
        'menu-options-controls-fault':'work/test-env/bin/python scripts/check-menu-controls.py --config Release',
    }
    current=json.loads((OUT/'comparison.json').read_text())
    assert current['status']=='pass',current.get('error')
    rows=[]
    for item in inventory['items']:
        if not item['id'].startswith('ifc:') or not item.get('in_scope'): continue
        owner=item['follow_up'][0]
        assert owner in commands, (item['id'],owner)
        task=tasks[owner]
        assert owner=='parity-menu-pages' or task['state']=='done',(owner,task['state'])
        row=dict(id=item['id'],title=item['title'],menu_id=item['menu_id'],check=commands[owner],
                 evidence='work/menu-pages/comparison.json' if owner=='parity-menu-pages' else task['result'],
                 scope='fresh focused page check' if owner=='parity-menu-pages' else 'retained acceptance from completed task')
        if '/New Game / Level ' in item['title']:
            row['scope']='fresh-profile Level 1 enabled; Levels 2-14 locked and skipped; level gameplay belongs to level joins'
        if 'GAME/GAMEOVER.IFC' in item['id']:
            row['scope']='retail original never constructs Nani state 12; game-over returns to menu (parity-pause-gameover)'
        if 'GAME/INGAME.IFC' in item['id'] and owner=='parity-pause-gameover':
            row['remaining_original_reference']='pause-gameover-newgame-tail-reference'
            assert tasks['pause-gameover-newgame-tail-reference']['state'] in ('open','taken','blocked','done')
        rows.append(row)
    dialogs=[]
    dialog_checks={
        'CONFIGCONTROLS':commands['menu-options-controls-fault'],
        'EDITPLAYERS':commands['parity-save-load-profiles'],
        'USERNEW':commands['parity-save-load-profiles'],
        'USERREMOVECONFIRM':commands['parity-save-load-profiles'],
    }
    for item in inventory['items']:
        if not item['id'].startswith('dialog:'): continue
        name=item['title']
        dialogs.append(dict(id=item['id'],check=dialog_checks.get(name),
                            scope='reachable native sheet' if name in dialog_checks else
                            'not opened by the scoped retail main-menu route; resource presence alone does not establish reachability'))
    result=dict(status='pass',single_player_ifc_nodes=len(rows),rows=rows,dialogs=dialogs,
                unavailable_policy='work/unavailable-menu-items/check/real-time/report.json',
                credits_paper='work/paper-roll/transitions/credits/comparison.json',
                limitations=['Retained other-task checks are not rerun or broadened to all levels/profiles.',
                             'Menu comparisons cover declared static text/value regions and exact palettes; Help compares the full screen.',
                             'Credits uses the elected native physical font, not Windows font parity.',
                             'Main-menu Quit is an IFC confirmation page, not a PE dialog.'])
    (OUT/'coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','dialogs')}))
    return 0


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',action='store_true')
    parser.add_argument('--coverage',action='store_true')
    args=parser.parse_args()
    CHILDREN=children()
    (OUT/'original').mkdir(parents=True,exist_ok=True)
    raise SystemExit(reference() if args.reference else coverage() if args.coverage else app_check())
