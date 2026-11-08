#!/usr/bin/env python3
"""Check the native Win32 auxiliary-process boundary; no process is launched."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('closure', ROOT/'scripts/check-call-closure.py')
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


def main():
    program = closure.profile('claw-v1.0')
    formats = {}
    for address in (0x525f74, 0x525f78, 0x525f80):
        section = next(s for s in program.sections if s.address <= address < s.address+s.size)
        formats[address] = section.data[address-section.address:].split(b'\0', 1)[0]
    assert list(formats.values()) == [b'%s', b'%s\\%s', b'%s%s']
    binary = closure.probe_build()
    native = closure.call_closure_native.build(ROOT, binary, closure.body, closure.digest,
                                               closure.heavy_lock, closure.wait_load)
    queries, expected = [], []
    for command, directory in [(b'helper.exe', None), (b'helper.exe', b''),
                               (b'helper.exe', b'C:\\Claw'), (b'helper.exe', b'C:\\Claw\\'),
                               (b'', b'\\'), (b'with spaces.exe', b'D:\\Claw data'),
                               (b'\xff.exe', b'\xe9'), (b'x'*255, None)]:
        args = [0x61001000, 0 if directory is None else 0x61002000]
        strings = {str(args[0]): list(command+b'\0')}
        if directory is not None:
            strings[str(args[1])] = list(directory+b'\0')
        queries.append(dict(target=0x42beb0, argc=2, arguments=args, strings=strings))
        fmt = formats[0x525f74 if not directory else 0x525f80 if directory.endswith(b'\\') else 0x525f78]
        output = fmt % (command if not directory else (directory, command))
        expected.append((list(output), args[1] if directory else 0))
    for row, (command, directory) in zip(closure.call_closure_native.run(native, queries), expected):
        assert row['outcome'] == 'served-native-route' and row['fault'] == 0 and row['result'] == 0, row
        assert row['command_event']['command_bytes'] == command, row
        assert row['command_event']['directory'] == directory, row
    bad = [dict(queries[0], argc=1, arguments=[0x61001000]),
           dict(queries[0], strings={}), dict(queries[0], closed=1),
           dict(queries[0], strings={str(0x61001000): [120]*256+[0]})]
    for row in closure.call_closure_native.run(native, bad):
        assert row['outcome'] == 'refused' and row['fault'] == 0x42beb0, row
    result = dict(check='native-windows-command', status='pass', cases=len(queries)+len(bad),
                  original_sha256=program.sha256, probe=str(native),
                  source_sha256=closure.digest(ROOT/'Sources/ClawNativeMenuResources.swift'),
                  contract='Original format bytes and compiled production selection; native Win32 process launch returns failure. No Windows program or runtime/device acceptance.')
    path = ROOT/'work/call-closure/windows-command.json'
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
