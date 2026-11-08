"""Continuous original startup through actual configuration, disc and text calls.

Only physical imports and allocation are serviced. Data output belongs under
ignored work/. Pinned image reads always originate in program.claw().
The only intercepted game/CRT entries are explicit observation HALTs at the
first missing callee; neither receives an invented result.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
from Tests.clawparity.kernel import Machine, STACK_TOP
from Tests.clawparity.program import claw
from unicorn import UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

CONFIG_ARITY = {0x4b5c50: 6, 0x4b5db0: 1, 0x4b5e90: 4, 0x4b5f30: 2, 0x4b5fb0: 3}
GLOBALS = [0x525510, 0x525514, 0x525518, *range(0x537234, 0x53725c, 4),
           0x52c6e4, 0x52c6e8, 0x52c6ec, 0x527134, 0x527130, 0x527138]

TEXT = [0x5256a8,0x5256a0,0x525698,0x525690,0x52568c,0x525684,0x52567c,0x525674]
PROFILES = {
    'empty': (b'', None),
    'options': (b'play racing menu noshell ipx 8bit 16bit', None),
    'user': (b'xxuser:Ada_Lovelace+Two tail user:ignored', b'Stored\0'),
    'empty-user': (b'user:', b'Stored\0'),
    'bytes': (bytes(range(128,256))+b' azAZ09[]`{', None),
    'boundaries': (b'@az[`{Z'+b'x'*292, None),
}

class Reached(Exception):
    pass


def reference(profile):
    command_bytes, stored_user = PROFILES[profile]
    present = True
    current_directory = b'D:\\CLAW'
    disc_root = b'D:\\' if present else None
    program = claw()
    machine = Machine(program, 0x3000000, 0x10000)
    bump = 0x3000000
    spans, tls, handles = {}, {}, {}
    clocks = iter([100, 125, 200, 225, 250])
    cursor, last_error, phase = 2, 0, 'constructor'
    events, imports, returns, executed = [], [], {}, set()
    nested, physical = [], []
    disc_active = False
    active_text = None
    strings = {0x532474, 0x534938, 0x525ec4, 0x524f08, *TEXT}
    reverse = {v:k for k,v in machine.import_stub.items()}
    initial_globals = {str(a): machine.words(a, 1)[0] for a in GLOBALS}

    def put(address, *words):
        machine.write(address, struct.pack('<' + 'I' * len(words), *words))
    def allocate(size):
        nonlocal bump
        pointer = bump
        bump = (bump + size + 15) & ~15
        assert bump <= 0x3010000
        spans[pointer] = size
        machine.write(pointer, bytes(size))
        return pointer
    def string(pointer):
        data = bytearray()
        while machine.read(pointer + len(data), 1) != b'\0':
            data += machine.read(pointer + len(data), 1)
            assert len(data) < 4096
        return bytes(data)
    def snapshot(function, receiver, args):
        return dict(function=function, receiver=receiver, arguments=list(args),
                    stackPointer=machine.register(UC_X86_REG_ESP), result=None,
                    applicationWords=list(machine.words(app, 77)),
                    clockWords=list(machine.words(0x541328, 5)))
    app, outer, window, command = allocate(0x134), allocate(0x254), allocate(12), allocate(len(command_bytes)+1)
    machine.write(command,command_bytes+b'\0')
    assert machine.words(0x540e88,1)[0] == 0
    put(outer, 0x50bbdc, window, app, 0x77000001)
    put(window, 0x50c37c, 0x77000002, outer)

    def observe_return(m, address):
        nonlocal active_text
        event = returns.pop(address)
        event['result'] = m.register(UC_X86_REG_EAX)
        if event['function'] in (0x4f21e0,0x4a3990):
            event['afterBytes'] = m.read(event['arguments'][0],300).hex()
            active_text = None
        if event['function'] == 0x42b020:
            nonlocal disc_active
            disc_active = False
    def observe_config(m, address):
        executed.add(address)
        esp = m.register(UC_X86_REG_ESP)
        args = m.words(esp + 4, CONFIG_ARITY[address])
        receiver = m.register(UC_X86_REG_ECX) if address != 0x4b5fb0 else 0
        event = snapshot(address, receiver, args)
        if address in (0x4b5c50, 0x4b5e90, 0x4b5f30):
            (nested if disc_active else events).append(event)
            ret = m.words(esp, 1)[0]
            assert ret not in returns
            returns[ret] = event
            m.observe(ret, observe_return)
        if address == 0x4b5c50:
            strings.update(args[:3])
        if address in (0x4b5e90, 0x4b5f30):
            strings.add(args[0])
    for address in CONFIG_ARITY:
        machine.observe(address, observe_config)
    def observe_disc(m, address):
        nonlocal disc_active
        disc_active = True
        executed.add(address)
        event = snapshot(address, m.register(UC_X86_REG_ECX), ())
        events.append(event)
        ret = m.words(m.register(UC_X86_REG_ESP), 1)[0]
        returns[ret] = event
        m.observe(ret, observe_return)
    machine.observe(0x42b020, observe_disc)
    def observe_text(m,address):
        nonlocal active_text
        executed.add(address)
        esp = m.register(UC_X86_REG_ESP)
        args = m.words(esp+4,1 if address == 0x4f21e0 else 2)
        event = snapshot(address,0,args)
        event['beforeBytes'] = m.read(args[0],300).hex()
        event['reads'] = []
        active_text = event
        events.append(event)
        ret = m.words(esp,1)[0]
        assert ret not in returns
        returns[ret] = event
        m.observe(ret,observe_return)
    def text_read(uc,access,address,size,value,user):
        if active_text is None: return
        base = active_text['arguments'][0]
        if base <= address < base+300:
            active_text['reads'].append(dict(pc=machine.register(UC_X86_REG_EIP),offset=address-base,count=size))
    machine.uc.hook_add(UC_HOOK_MEM_READ,text_read)
    machine.observe(0x4f21e0,observe_text)
    machine.observe(0x4a3990,observe_text)
    def srand(m, address):
        if phase == 'startup':
            event = snapshot(address,0,m.words(m.register(UC_X86_REG_ESP)+4,1))
            event['result'] = 0
            events.append(event)
    machine.observe(0x4a3040,srand)
    signatures = {0x546df0:0, 0x546a24:0, 0x546d54:1, 0x546aa4:1, 0x546a90:0,
                  0x546a84:2, 0x5469c0:0, 0x546b0c:0, 0x546a7c:1, 0x546ab8:1,
                  0x546834:9, 0x54682c:6, 0x546a28:2, 0x546a2c:1}
    for address in (0x4f63ec, 0x4adf50, 0x42a680, 0x4a3920):
        machine.intercept(address)
    def external(m, address):
        nonlocal last_error, cursor
        function = reverse.get(address, address)
        argc = signatures.get(function, {0x4f63ec:1, 0x4adf50:2, 0x42a680:0, 0x4a3920:3}.get(function))
        assert argc is not None, hex(function)
        args = m.words(m.register(UC_X86_REG_ESP)+4, argc)
        receiver = m.register(UC_X86_REG_ECX) if function in (0x42a680,) else 0
        event = snapshot(function, receiver, args)
        if function in (0x42a680, 0x4a3920):
            (nested if disc_active else events).append(event)
            raise Reached
        if function == 0x546df0: value = next(clocks)
        elif function == 0x546a24: value = 400
        elif function == 0x546d54:
            cursor += 1 if args[0] else -1
            value = cursor & 0xffffffff
        elif function == 0x4f63ec:
            assert args == (540,)
            value = allocate(args[0])
        elif function == 0x4adf50: value = allocate(args[0]*args[1])
        elif function == 0x546aa4: value = 0
        elif function == 0x546a90: value = 0
        elif function == 0x546a84:
            tls[args[0]] = args[1]; value = 1
        elif function == 0x5469c0: value = 123
        elif function == 0x546b0c: value = last_error
        elif function == 0x546a7c:
            value = tls[args[0]]; last_error = 0
        elif function == 0x546ab8:
            last_error = args[0]; value = 0
        elif function == 0x546834:
            parent, name, reserved, klass, options, access, security, output, disposition = args
            assert reserved == options == security == 0 and access == 0xf003f and klass == 0x534938
            event['subkeyHex'] = string(name).hex()
            event['classHex'] = string(klass).hex()
            value = 0
            if value == 0:
                handle = 0x78000000 + len(handles)*4
                handles[handle] = (parent, string(name))
                put(output, handle); put(disposition, 1)
                event['handle'] = handle
                event['disposition'] = 1
        elif function == 0x54682c:
            handle, name, reserved, type_out, data_out, size_out = args
            assert handle in handles and reserved == 0
            cap = machine.words(size_out,1)[0]
            event['nameHex'] = string(name).hex(); event['capacity'] = cap
            # Input settings keyed by original source-name address: spelling is
            # read from the image, never reconstructed from UI text.
            record = (1,stored_user) if name == 0x525714 and stored_user is not None else None
            value = 2
            if record is not None:
                kind,data = record
                put(type_out,kind); put(size_out,len(data))
                value = 0 if len(data) <= cap else 234
                if value == 0: machine.write(data_out,data)
            event['outputType'] = machine.words(type_out,1)[0]
            event['outputSize'] = machine.words(size_out,1)[0]
            event['outputBytes'] = machine.read(data_out,cap).hex()
        elif function == 0x546a28:
            cap, output = args
            assert cap == 255
            value = len(current_directory)
            machine.write(output,current_directory+b'\0')
            event['outputBytes'] = (current_directory+b'\0').hex()
        elif function == 0x546a2c:
            root = string(args[0])
            event['rootHex'] = root.hex()
            value = 5 if disc_root is not None and root.upper() == disc_root else 3 if root.upper() == b'C:\\' else 1
        else: raise AssertionError(hex(function))
        event['result'] = value
        if function in (0x546834,0x54682c): imports.append(event)
        elif function in (0x546a28,0x546a2c): physical.append(event)
        elif phase == 'startup' and function in (0x546df0,0x546a24,0x546d54,0x4f63ec): events.append(event)
        m.return_from_external(value, 4*argc if function in signatures else 0)
    machine.on_external = external
    def live(address, size, write, instruction):
        assert any(base <= address and address+size <= base+count for base,count in spans.items()), hex(address)
    machine.watch_heap(live)
    assert machine.call(0x4254a0, app).completed
    phase = 'crt'
    assert machine.call(0x4a7d40).eax == 1
    phase = 'startup'
    fault = None
    initial_user_command = machine.read(STACK_TOP-0x138,300).hex()
    try:
        machine.call(0x425730, app, arguments=(window,command))
        raise AssertionError('Startup returned unexpectedly')
    except Reached: pass
    stop = nested[-1] if nested and nested[-1]['result'] is None else events[-1]
    assert stop['function'] == 0x42a680
    assert {0x42b020,0x4f21e0,0x4a3990}.issubset(executed)
    assert machine.words(0x540e88,1)[0] == 0
    assert sum(e['function'] == 0x4f21e0 for e in events) == 1
    assert sum(e['function'] == 0x4a3990 for e in events) == (9 if b'user:' in command_bytes else 8)
    assert len(imports) == 37
    assert len(physical) == 2
    config = machine.words(app+0x38,1)[0]
    assert all(machine.words(app+off,1)[0] == 0 for off in (0x2c,0x30,0x34))
    # Store original-derived catalog only in the caller's ignored output.
    image_strings = {str(a):(string(a)+b'\0').hex() for a in sorted(strings)}
    return dict(name=profile,sha256=program.sha256,app=app,outer=outer,window=window,config=config,
                commandHex=command_bytes.hex(), storedUserHex=stored_user.hex() if stored_user is not None else None,
                initialUserCommandBytes=initial_user_command,
                commandBytes=machine.read(STACK_TOP-0x42c,300).hex(), userCommandBytes=machine.read(STACK_TOP-0x138,300).hex(),
                textInitialGlobals={str(0x540e88):0}, textGlobals={str(0x540e88):machine.words(0x540e88,1)[0]},
                startupStack=STACK_TOP,events=events,imports=imports,nested=nested,physical=physical,
                currentDirectory=current_directory.decode(),present=present,stop=stop,executed=sorted(executed),fault=fault,
                applicationWords=list(machine.words(app,77)),clockWords=list(machine.words(0x541328,5)),
                configBytes=machine.read(config,540).hex() if config else None,
                initialGlobals=initial_globals,globals={str(a):machine.words(a,1)[0] for a in GLOBALS},
                strings=image_strings,userBytes=machine.read(STACK_TOP-0x4b0,32).hex(),
                userLength=machine.words(STACK_TOP-0x4c4,1)[0])

if __name__ == '__main__':
    output = Path(sys.argv[1]).resolve()
    assert Path('work').resolve() in output.parents, 'Derived references must remain under ignored work/'
    assets = [(Path('Original/claw-disc/files/DATA/CLAW.REZ'),'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'),
              (Path('work/media/source/CLAW.FEC'),'9c87c82aaec3c73aa6c9eb268da9db8601aa10f75af35060bff4f1edcfbb80d8')]
    for path, digest in assets:
        with path.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest() == digest
    cases = [reference(profile) for profile in PROFILES]
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(cases,indent=2)+'\n')
    print('PASS six continuous original startup/configuration/disc/text profiles; genuine first missing call42a680')
