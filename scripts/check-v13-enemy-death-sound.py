#!/usr/bin/env python3
"""Focused native-overlay checks. The separate v1.3 admission gate proves originals.

This check loads the app's actual C++ adapters with a small memory host and
explicit native-boundary service implementations. It exercises consecutive
requests over persistent memory without playing sound or launching an app.
"""
import ctypes as C
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tests'))
from clawparity.env import NativeHost, CALLBACK, BYTES_CALLBACK, U32  # noqa: E402

WORK = ROOT / 'work' / 'v13-integration-check'
OVERLAY = 'claw_v13_native_overlay_entry'
DEATH = 'claw_v13_enemy_death_compat_entry'
LEGACY = 'claw_level_one_batch_enemy_callee_03_entry'


class Host:
    def __init__(self, library):
        self.library = library
        self.regions = [(0x400000, C.create_string_buffer(0x150000)),
                        (0x1ff0000, C.create_string_buffer(0x20000)),
                        (0x3000000, C.create_string_buffer(0x40000))]
        self.next = 0x3000000
        self.calls = []
        self.play_result = 1
        self.resource = 0
        self.load_result = 1
        self.alloc_fail = False
        self.mutate_create = False
        self.named_resource = 0
        self.manager = 0
        self.on_call = None
        self.callback_error = None
        self.bytes_cb = BYTES_CALLBACK(self.bytes)
        self.call_cb = CALLBACK(self.call)
        self.host = NativeHost()
        self.host.bytes = C.cast(self.bytes_cb, C.c_void_p)
        self.host.call = self.call_cb

    def bytes(self, _user, token, size):
        for base, buffer in self.regions:
            if base <= token and token + size <= base + C.sizeof(buffer):
                return C.addressof(buffer) + token - base
        return None

    def put(self, token, *words):
        data = struct.pack('<' + 'I' * len(words), *(v & 0xffffffff for v in words))
        destination = self.bytes(None, token, len(data))
        assert destination, f'write outside host memory: {token:x}'
        C.memmove(destination, data, len(data))

    def get(self, token):
        source = self.bytes(None, token, 4)
        assert source, f'read outside host memory: {token:x}'
        return struct.unpack('<I', C.string_at(source, 4))[0]

    def alloc(self, size, fill=0):
        result = self.next
        self.next += (size + 15) & ~15
        C.memset(self.bytes(None, result, size), fill, size)
        return result

    def invoke(self, symbol, function, receiver, *arguments):
        entry = getattr(self.library, symbol)
        entry.argtypes = [U32, U32, C.POINTER(U32), U32, C.POINTER(NativeHost), C.POINTER(U32)]
        entry.restype = U32
        result = U32()
        args = (U32 * len(arguments))(*arguments)
        accepted = entry(function, receiver, args, len(args), C.byref(self.host), C.byref(result))
        assert not self.callback_error, self.callback_error
        assert accepted and not self.host.fault, (symbol, hex(function), self.host.fault, hex(self.host.faultAddress))
        return result.value

    def call(self, _user, pointer):
        try:
            call = pointer.contents
            args = tuple(call.arguments[:call.argumentCount])
            self.calls.append((call.function, call.receiver, args))
            if self.on_call:
                self.on_call(call.function, call.receiver, args)
            if call.function == 0x4b45f0:
                # Backend sees the published timestamp, even on playback failure.
                assert self.get(self.resource + 0x14) == self.get(0x537210)
                return self.play_result
            if call.function == 0x4f6286:
                assert self.get(args[1]) == 0
                self.put(args[1], self.named_resource)
                return int(bool(self.named_resource))
            if call.function == 0x4f63ec:
                assert args == (28,), args
                if self.alloc_fail:
                    return 0
                self.resource = self.alloc(args[0], 0xa7)
                if self.mutate_create:
                    self.put(self.manager + 0x1c, 0x7351)
                    self.put(self.manager + 0xc, 0x43210)
                return self.resource
            if call.function == 0x4c8850:
                assert call.receiver == self.resource
                assert [self.get(self.resource + o) for o in (8, 0x10, 0x14, 0x18)] == [0, 0, 0, 0]
                assert self.get(self.resource) == 0x5138b0
                assert self.get(self.resource + 4) == self.get(self.manager + 0x1c)
                assert self.get(self.resource + 0xc) == self.get(self.manager + 0xc)
                self.put(self.resource + 0x10, 0x735000)
                return self.load_result
            if call.function == 0x4f62a8:
                # Insertion can change the manager interval; copy happens after it.
                assert self.get(self.resource + 0x18) == 0
                if self.mutate_create:
                    self.put(self.manager + 0x34, 91)
                return self.slot
            if call.function == 0x4ca670:
                assert args == (1,) and call.receiver == self.resource
                return 0
            if call.function == 0x4dba00:
                return 0xD34D
            if call.function == 0x43e9c0:
                return 0
            if call.function == 0x4a3050:
                return 25
            if call.function == 0x420a10:
                return 0
            if call.function == 0x4208e0:
                return self.invoke(OVERLAY, call.function, call.receiver, *args)
            raise AssertionError(f'unexpected native boundary {call.function:x}')
        except Exception as error:
            self.callback_error = repr(error)
            self.host.fault = 6
            return 0

    def sound(self, last=100, interval=10):
        self.resource = self.alloc(28, 0x6b)
        self.put(self.resource + 0x10, 0x76543, last, interval)
        self.put(0x532c0c, 1)
        self.put(0x532c10, 67)
        return self.resource

    def plays(self):
        return [c for c in self.calls if c[0] == 0x4b45f0]


def check_sound(library):
    for named in (False, True):
        h = Host(library)
        sound = h.sound()
        manager = h.alloc(56)
        h.named_resource = sound
        function = 0x420910 if named else 0x4208e0
        receiver = manager if named else sound
        args = (0x7000,) if named else (23, 0x80000000, 37, 1)
        for tick, expected, count, timestamp in ((109, 0, 0, 100), (110, 1, 1, 110),
                (110, 0, 1, 110), (119, 0, 1, 110), (120, 1, 2, 120)):
            h.put(0x537210, tick)
            assert h.invoke(OVERLAY, function, receiver, *args) == expected
            assert len(h.plays()) == count and h.get(sound + 0x14) == timestamp
        assert h.plays()[0][2] == ((67, 0, 0, 0) if named else args)
        h.put(0x532c0c, 0)
        h.put(0x537210, 130)
        assert h.invoke(OVERLAY, function, receiver, *args) == 0
        assert h.get(sound + 0x14) == 120 and len(h.plays()) == 2
        h.put(0x532c0c, 1)
        h.play_result = 0
        assert h.invoke(OVERLAY, function, receiver, *args) == 0
        assert h.get(sound + 0x14) == 130 and len(h.plays()) == 3
        h.put(sound + 0x14, 0xfffffffe, 4)
        h.put(0x537210, 1)
        assert h.invoke(OVERLAY, function, receiver, *args) == 0
        assert h.get(sound + 0x14) == 0xfffffffe
        h.put(0x537210, 2)
        h.play_result = 1
        assert h.invoke(OVERLAY, function, receiver, *args) == 1
        assert h.get(sound + 0x14) == 2
        h.put(sound + 0x18, 0)
        assert h.invoke(OVERLAY, function, receiver, *args) == 1
        assert h.invoke(OVERLAY, function, receiver, *args) == 1
        if named:
            h.put(manager + 0x30, 1)
            before = len(h.calls)
            assert h.invoke(OVERLAY, function, receiver, *args) == 0 and len(h.calls) == before
            h.put(manager + 0x30, 0)
            h.named_resource = 0
            before = len(h.plays())
            assert h.invoke(OVERLAY, function, receiver, *args) == 0 and len(h.plays()) == before


def check_creation(library):
    for interval in (0, 1, 0xffffffff):
        for mutate in (False, True):
            h = Host(library)
            h.manager = h.alloc(56)
            h.slot = h.alloc(4)
            h.put(h.manager + 0xc, 0x43200)
            h.put(h.manager + 0x1c, 0x23)
            h.put(h.manager + 0x34, interval)
            h.put(0x5138b4, 0x4ca670)
            h.mutate_create = mutate
            result = h.invoke(OVERLAY, 0x4ca3b0, h.manager, 0x7010, 0x7020)
            assert result == h.resource == h.get(h.slot)
            assert h.get(result + 0x18) == (91 if mutate else interval)
            h.put(h.manager + 0x34, 51)
            assert h.get(result + 0x18) == (91 if mutate else interval)
    for mode in ('disabled', 'allocation-fails', 'load-fails'):
        h = Host(library)
        h.manager = h.alloc(56)
        h.put(0x5138b4, 0x4ca670)
        h.alloc_fail = mode == 'allocation-fails'
        h.load_result = int(mode != 'load-fails')
        h.put(h.manager + 0x30, int(mode == 'disabled'))
        assert h.invoke(OVERLAY, 0x4ca3b0, h.manager, 0x7010, 0x7020) == 0
        assert any(c[0] == 0x4ca670 for c in h.calls) == (mode == 'load-fails')
        assert not any(c[0] == 0x4f62a8 for c in h.calls)


def check_death(library):
    for count in (5, 32, 33):
        for initial in (0, 1, 0x8a45ab11):
            for symbol in (DEATH, LEGACY):
                h = Host(library)
                enemy = h.alloc(0x420)
                owner, record, sprite = h.alloc(0x100), h.alloc(0x40), h.alloc(0x1c0)
                h.put(enemy + 0xc, owner, record)
                h.put(enemy + 0x12c, sprite)
                h.put(enemy + 0x2fc, count)
                bits = h.alloc(8) if count > 32 else enemy + 0x300
                if count > 32:
                    h.put(enemy + 0x300, bits)
                h.put(bits, initial)
                for index in range(2):
                    assert h.invoke(symbol, 0x43f120, enemy, 0) == 0
                    expected = (initial & ~1) if symbol == DEATH else initial ^ (1 if index == 0 else 0)
                    assert h.get(bits) == expected | 0x10


GENERIC_BRIDGE = r"""
#include "GenericEnemyStates.h"
#include <cstring>
#include <initializer_list>
namespace {
struct Observations { uint32_t expectedAudio = 0, audioCalls = 0, bad = 0; };
uint64_t dependency(ClawGenericEnemy *, ClawGenericEnemyContext *, const ClawGenericEnemyCall *call, void *user) {
    auto &seen = *static_cast<Observations *>(user);
    switch (call->function) {
    case 0x4dba00:
        if (!call->name || std::strcmp(call->name, "LS_DEAD")) seen.bad = 1;
        return 7;
    case 0x4a3050: return 25;
    case 0x420a10: return 0;
    case 0x4208e0:
    case 0x4b45f0:
        if (call->function != seen.expectedAudio || call->argumentCount != 4 || call->arguments[0] != 67) seen.bad = 2;
        ++seen.audioCalls;
        return 1;
    default: seen.bad = 3; return 0;
    }
}
uint32_t exercise(bool selected) {
    for (uint32_t count : {5u, 32u, 33u}) {
        for (uint32_t initial : {0u, 1u, 0x8a45ab11u}) {
            ClawGenericEnemy enemy{};
            ClawGenericEnemyContext context{};
            ClawGenericEnemyStatesContext extra{};
            uint32_t words[2] = {initial, 0x12345678};
            context.bitWords = words;
            context.bitWordCount = 2;
            context.tick = 127;
            enemy.enemy[0x2fc / 4] = count;
            enemy.enemy[0x300 / 4] = initial;
            Observations observations{};
            for (uint32_t iteration = 0; iteration < 2; ++iteration) {
                if (!claw_generic_enemy_state_entry(&enemy, &context, &extra, 0x43f120, 0, dependency, &observations)) return 1;
                const uint32_t expected = (selected ? initial & ~1u : initial ^ (iteration ? 0u : 1u)) | 0x10u;
                const uint32_t actual = count <= 32 ? enemy.enemy[0x300 / 4] : words[0];
                if (actual != expected || observations.bad) return 2;
            }
            ClawGenericEnemyStateResource resource{0x6000, 0x7000};
            extra.resources = &resource;
            extra.resourceCount = 1;
            extra.audioEnabled = 1;
            extra.audioPosition = 67;
            enemy.enemy[0x3b0 / 4] = resource.token;
            observations.expectedAudio = selected ? 0x4208e0 : 0x4b45f0;
            if (!claw_generic_enemy_state_entry(&enemy, &context, &extra, 0x43f120, 1, dependency, &observations)) return 3;
            if (observations.audioCalls != 1 || observations.bad) return 4;
        }
    }
    return 0;
}
}
extern "C" uint32_t check_generic_process_selector() {
    const uint32_t legacy = exercise(false);
    if (legacy) return 100 + legacy;
    claw_generic_enemy_states_use_v13();
    const uint32_t selected = exercise(true);
    return selected ? 200 + selected : 0;
}
"""


def check_generic_selector(library):
    entry = library.check_generic_process_selector
    entry.argtypes = []
    entry.restype = U32
    result = entry()
    assert result == 0, f'legacy process profile selector check failed: {result}'


def check_registry():
    text = (ROOT / 'Sources' / 'ClawCanonicalDispatch.h').read_text()
    for address, symbol in ((0x43f120, "claw_v13_cheat_native_entry"), (0x4208e0, OVERLAY), (0x420910, OVERLAY), (0x4ca3b0, OVERLAY)):
        row = re.search(r'\{0x0*' + f'{address:x}' + r'u,[^\n]+', text)
        assert row and symbol in row.group(0), f'generated dispatch does not elect {address:x} -> {symbol}'


def main():
    result = {'check': 'v13-enemy-death-sound', 'status': 'fail', 'errors': []}
    try:
        load = subprocess.check_output(['sysctl', '-n', 'vm.loadavg'], text=True)
        assert float(load.strip('{} ').split()[0]) < 16, 'load is at least 16; retry after it drops'
        WORK.mkdir(parents=True, exist_ok=True)
        library_path = WORK / 'overlay.dylib'
        bridge = WORK / 'generic-bridge.cpp'
        bridge.write_text(GENERIC_BRIDGE)
        subprocess.run(['clang++', '-std=c++17', '-O2', '-dynamiclib', '-I', str(ROOT / 'Sources'),
                        str(ROOT / 'Sources' / 'V13NativeOverlay.cpp'),
                        str(ROOT / 'Sources' / 'LevelOneBatchEnemyCallee03Runtime.cpp'),
                        str(ROOT / 'Sources' / 'GenericEnemyStates.cpp'),
                        str(ROOT / 'Sources' / 'GenericEnemy.cpp'),
                        str(ROOT / 'Sources' / 'PlayerPhysics.cpp'), str(bridge),
                        '-o', str(library_path)], check=True)
        library = C.CDLL(str(library_path))
        check_sound(library)
        check_creation(library)
        check_death(library)
        check_generic_selector(library)
        check_registry()
        result.update(status='pass', checked=['repeated-direct-and-named', 'unsigned-wrap',
                      'guard-timestamps-and-backend-failure', 'resource-creation-and-interval-copy',
                      'death-inline-and-heap-idempotence', 'legacy-xor-retained', 'legacy-process-profile-selector', 'generated-registry'])
    except Exception as error:
        result['errors'].append(str(error))
    print(json.dumps(result))
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
