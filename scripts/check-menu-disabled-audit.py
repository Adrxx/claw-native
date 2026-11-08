"""Walk every visible IFC item with confirmed real keys and pointer clicks.

Uses isolated fresh profiles: locked save/level descendants are listed as
unreachable through their disabled parent. Disabled artwork must be the
original IFC disabled image, and clicks must not dispatch a command.
Native dialogs and Escape pages are walked too. No original-derived table is
tracked: the complete item table and frame evidence stay under work/.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from real_input import Session, build_helper, alive

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/menu-disabled-audit'
MAC = dict(down=125, up=126, ret=36, esc=53, left=123, right=124, space=49,
           n=45, r=15, y=16, a=0, tab=48)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    helper = build_helper(OUT / 'post-window-input')
    pointer = OUT / 'post-menu-pointer'
    subprocess.run(['xcrun','swiftc','-O',str(ROOT/'scripts/post-menu-pointer.swift'),'-o',str(pointer)],check=True)
    app = ROOT / os.environ.get('CLAW_DERIVED_DATA','work/MacCatalyst') / 'Build/Products/Release-maccatalyst/Claw.app'
    session = Session(OUT, fast=True, helper=helper)
    result = dict(check='menu-disabled-audit', status='fail', errors=[], items={}, pages=[], native=[])
    result['binary_sha256'] = hashlib.sha256((app/'Contents/MacOS/Claw').read_bytes()).hexdigest()
    initial = {}

    def live():
        return json.loads((OUT/'live.json').read_text())

    def require(value, message):
        if not value:
            raise RuntimeError(message)

    def healthy():
        require(alive(session.pid) and not session.failed() and live().get('status') != 'fail', 'app fault: '+str(session.gate()))

    def tap(key):
        # Dialog transitions can cancel UIKit's initiating press. Confirm its
        # down event, then send the physical release even if UIKit cancelled it.
        session.post('press',MAC[key],'down'); session.sleep(.07)
        session._post(('press',MAC[key],'up')); session.sleep(.3)
        healthy()

    def rows():
        return {r['id']:r for r in live().get('menu_audit',[])}

    def choose(identifier):
        for _ in range(24):
            if live().get('menu_selected') == identifier:
                return
            tap('down')
        raise RuntimeError(f'cannot select {identifier}: {live().get("menu_selected")}')

    def enter(identifier):
        choose(identifier); tap('ret')

    def record(row, state, method):
        result['items'][str(row['id'])] = dict(id=row['id'], parent=row['parent'], item=row['title'], state=state, checked=method)

    def click(row):
        x,y,w,h = row['rect']
        received = live()['input_received']
        subprocess.run([str(pointer),str(session.pid),str(x+w/2),str(y+h/2)],check=True)
        require(session.wait(lambda:session.input_state().get('received',0)>received,5), 'pointer not delivered')
        session.sleep(.6); healthy()
        mark = session.mark(f'click-{row["id"]}')
        point = (mark or {}).get('cursor_position',[])
        require(len(point)==2 and x<=point[0]<x+w and y<=point[1]<y+h,
                f'pointer missed {row["id"]}: {point}, rectangle {row["rect"]}')

    def controls():
        require(live()['controls']['open'], 'Controls did not open')
        for _ in range(9):
            tap('left');tap('right');tap('ret'); tap('esc'); tap('down')
        tap('ret')  # Defaults
        tap('down'); tap('ret')  # Cancel
        require(not live()['controls']['open'], 'Controls Cancel failed')
        tap('ret'); tap('up'); tap('ret')  # Save
        require(not live()['controls']['open'], 'Controls Save failed')
        result['native'].append(dict(item='Controls: nine bindings, Defaults, Cancel, Save, joystick choices',state='enabled',checked='real keys; capture cancelled; Defaults/Cancel/Save'))

    def players():
        require(live()['players_dialog'] == 0, 'Players did not open')
        tap('r'); require(live()['players_dialog'] == 0, 'reserved Player removal enabled')
        tap('n'); tap('ret')  # Empty form safely rejects creation.
        require(live()['players_dialog'] == 1, 'empty player creation escaped form')
        tap('a'); tap('tab'); tap('a'); tap('ret')
        require(len(live()['profiles']) == 2, 'player creation failed')
        tap('r'); tap('esc'); tap('r'); tap('y')
        require(len(live()['profiles']) == 1, 'player removal failed')
        tap('esc'); tap('ret'); tap('ret')
        require(live()['players_dialog'] == -1, 'Players OK failed')
        result['native'].append(dict(item='Players: selection, New, Name/Location/Comment, Create, Remove, confirmation, Cancel, OK',state='enabled; reserved Player Remove disabled',checked='real keys; empty Create rejected; create/remove/cancel/OK'))

    def walk(page):
        require(live()['menu_page'] == page, f'page {page} did not open')
        result['pages'].append(page)
        current = rows()
        children = [r for r in current.values() if r['parent'] == page]
        session.mark(f'page-{page}')
        for row in children:
            identifier = row['id']
            row = rows()[identifier]
            if row['disabled']:
                require(row['image'] != 0 and row['image'] == row['disabled_image'], f'{identifier}: wrong disabled artwork')
                before = live()['posted_commands']
                click(row)
                require(live()['menu_page'] == page and live()['posted_commands'] == before, f'{identifier}: disabled click dispatched')
                record(row,'disabled','real pointer; IFC disabled artwork; no command')
                continue
            choose(identifier)
            record(row,'enabled','real keys')
            # Return and destructive actions are exercised explicitly after
            # the recursive page walk, so siblings are still reachable.
            if identifier in (11101,14001,20001,22001,24001):
                continue
            if row['title'].lower() in ('back','no'):
                continue
            tap('ret')
            if live()['controls']['open']:
                controls()
            elif live()['players_dialog'] != -1:
                players()
            elif live()['custom_dialog']:
                require(not live()['custom_files'], 'scratch custom directory not empty')
                tap('ret');require(live()['custom_dialog'], 'empty Load activated')
                tap('esc')
                result['native'].append(dict(item='Custom Levels: Import, Cancel, Load',state='Import/Cancel enabled; empty Load disabled',checked='real Return no-op and Escape; file picker belongs to OS'))
            elif live().get('state_vtable') == '0x50c264':
                require(session.wait(lambda:live().get('game_ms',0)>1000,90),'loaded game did not run')
                tap('esc');enter(20005);enter(24001);session.sleep(1)
                route = []
                ancestor = page
                while ancestor != 10000:
                    route.append(ancestor);ancestor = initial[ancestor]['parent']
                for ancestor in reversed(route):
                    enter(ancestor)
            elif live()['menu_page'] == identifier and any(r['parent']==identifier for r in current.values()):
                walk(identifier)
                # Use the actual Back/No action where available.
                back = next((r['id'] for r in rows().values() if r['parent']==identifier and r['title'].lower() in ('back','no')),None)
                if back is not None:
                    enter(back)
                else:
                    tap('esc')
            elif live().get('state_vtable') not in ('0x50c1e4','0x50c044'):
                tap('esc')  # Help / Credits
            else:
                # Value controls use both directions, including disabled
                # dependants after Sound is turned off by Enter.
                tap('left'); tap('right')
            require(live()['menu_page'] == page, f'{identifier}: did not return to {page}: {live().get("menu_page")}')
        # Prove keyboard/controller-style navigation skips all disabled items.
        disabled = {r['id'] for r in rows().values() if r['parent']==page and r['disabled']}
        for _ in range(len(children)+1):
            tap('down')
            require(live()['menu_selected'] not in disabled, f'{page}: navigation selected disabled item')

    try:
        session.launch(app, {}, ['--menu-disabled-audit','--save-dir',str(OUT/'saves'),
            '--settings-dir',str(OUT/'settings'),'--custom-dir',str(OUT/'custom')])
        session.sleep(3); healthy()
        initial = rows()
        require(initial, 'missing IFC tree diagnostics')
        require(all(initial[i]['disabled'] for i in (11004,11005,12001,12002,12003)), 'unsupported service enabled')
        for code in (18,19,20):
            session.post('press',code,'down','command,shift');session.sleep(.07)
            session._post(('press',code,'up','command,shift'));session.sleep(.3)
            healthy()
        require(live()['menu_page']==10000 and not live()['save_anywhere'] and not live()['custom_checkpoint'],
                'missing checkpoint shortcut changed state')
        result['native'].append(dict(item='Checkpoint overlay: Save 1/2/custom; Load 1/2/custom',
            state='Save disabled outside play; Load absent until a record exists',
            checked='real Command-Shift-1/2/3 with absent records are no-ops; native buttons use the same guarded requests'))
        walk(10000)
        # Main menu's first disabled selection is activatable by Enter/Space
        # before navigation. Both must take IFC's original disabled callback.
        enter(10002)
        require(live()['menu_selected_disabled'], 'Racing not initially disabled')
        before = live()['posted_commands']
        tap('ret');tap('space')
        require(live()['menu_page']==10002 and live()['posted_commands']==before,'disabled key activated service')
        tap('esc')
        enter(10001);enter(11001);enter(11101)
        require(session.wait(lambda:live()['state_vtable']=='0x50c264' and live().get('game_ms',0)>1000,90),'Level 1 failed')
        tap('esc'); pause = rows(); initial.update(pause)
        walk(20000)
        # Return to Game, End Life Yes, End Game Yes are state transitions.
        enter(20001);require(live()['state_vtable']=='0x50c264','Return to Game failed')
        tap('esc');enter(20002);enter(22001);session.sleep(3)
        require(live()['state_vtable']=='0x50c264','End Life Yes failed')
        tap('esc');enter(20005);enter(24001);session.sleep(2)
        require(live()['menu_page']==10000,'End Game Yes failed')
        for identifier in (11101,14001,20001,22001,24001):
            if str(identifier) in result['items']:
                result['items'][str(identifier)]['checked']='real activation; expected state transition'
        # Unreachable descendants must have a proven disabled ancestor.
        for identifier,row in initial.items():
            if row['parent']==0 or str(identifier) in result['items']:
                continue
            ancestor = row['parent']
            while ancestor and str(ancestor) not in result['items']:
                ancestor = initial[ancestor]['parent']
            require(ancestor and result['items'][str(ancestor)]['state'] in ('disabled','unreachable'), f'unwalked item {identifier}')
            record(row,'unreachable',f'disabled ancestor {ancestor}; real input cannot enter')
        # Quit Yes last: process exit is the expected successful outcome.
        enter(10006);choose(14001)
        session.post('press',36,'down'); session._post(('press',36,'up'))
        session._command('run 120')
        deadline = time.monotonic()+10
        while alive(session.pid) and time.monotonic()<deadline:
            time.sleep(.05)
        require(not alive(session.pid),'Quit Yes did not close own app')
        result['status']='pass'
    except Exception as error:
        result['errors'].append(str(error))
    finally:
        session.close()
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    table = ['| ID | Item | State | Check |','| --- | --- | --- | --- |']
    table += [f'| {r["id"]} | {r["item"]} | {r["state"]} | {r["checked"]} |' for r in result['items'].values()]
    table += [f'| native | {r["item"]} | {r["state"]} | {r["checked"]} |' for r in result['native']]
    (OUT/'items.md').write_text('\n'.join(table)+'\n')
    print(json.dumps(dict(status=result['status'],errors=result['errors'],items=len(result['items']),pages=result['pages'],report=str(OUT/'report.json'))))
    return result['status']!='pass'


if __name__=='__main__':
    raise SystemExit(main())
