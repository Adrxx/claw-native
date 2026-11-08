#!/usr/bin/env python3
"""Focused raw 0x4d32e0 boundary comparison, not family admission.

The original projection executes its own instructions. Native projection uses
its existing geometry core. All other outgoing services share deterministic
mutations, with exact tokens, stack positions, rectangle bytes and whole-heap
snapshots checked before each callback and after return.
"""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Tests.clawparity.program import claw
from original_v10 import OriginalV10
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

U = C.c_uint32
BASE, SIZE, STACK, STACK_SIZE = 0x3000000, 0x20000, 0x2000000, 0x10000
ACTOR, IMAGE, TARGET, PARENT, WORLD, PLANE, HOLDER, COMPRESSED, SURFACE, OTHER_WORLD = [BASE + i * 0x1000 for i in range(1, 11)]
ENTRY, PROJECT, COPY, BLIT, COPY_STUB = 0x4d32e0, 0x4c96d0, 0x546d58, 0x4bffa0, 0x10fd030


class Call(C.Structure):
    _fields_ = [('function', U), ('receiver', U), ('receiver2', U), ('argumentCount', U),
                ('arguments', U * 16), ('stackPointer', U), ('x87ArgumentCount', U),
                ('x87Argument', C.c_double), ('compilerContext', C.c_void_p),
                ('sourceContext', C.c_void_p), ('sourceReturnPC', U),
                ('sourceTransferVersion', U), ('sourceTransferKind', U),
                ('sourceTransferSite', U), ('sourceCallerFunction', U),
                ('sourceDisposition', C.c_void_p)]


Bytes = C.CFUNCTYPE(C.c_void_p, C.c_void_p, U, U)
Service = C.CFUNCTYPE(U, C.c_void_p, C.POINTER(Call))


class Host(C.Structure):
    _fields_ = [('user', C.c_void_p), ('bytes', Bytes), ('call', Service),
                ('maximumOperations', U), ('fault', U), ('faultAddress', U),
                ('floatResult', C.c_double), ('entryStackPointer', U),
                ('remainingOperations', C.POINTER(C.c_uint64)),
                ('compilerContext', C.c_void_p), ('sourceContext', C.c_void_p),
                ('sourceReturnPC', U), ('guestSession', C.c_void_p)]


class Projection(C.Structure):
    _fields_ = [(key, U) for key in ('flags', 'extentX', 'extentY', 'cameraX', 'cameraY',
                                   'visibleEndX', 'visibleEndY', 'screenOffsetX', 'screenOffsetY')]


def build():
    compiler = shutil.which('clang++')
    assert compiler, 'clang++ is required'
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']
    sources = [str(ROOT / 'Sources' / name) for name in
               ('GameImageRawRuntime.cpp', 'SpriteGeometry.cpp')]
    # Discover and hash compiler inputs without inspecting implementation text.
    dependency_output = subprocess.check_output([compiler, *flags, '-MM', *sources], text=True)
    dependencies = {ROOT / 'Sources/ClawRuntime.h'}
    for rule in dependency_output.replace('\\\n', '').splitlines():
        dependencies.update(Path(path) for path in shlex.split(rule.split(':', 1)[1]))
    probe = '#include "ClawRuntime.h"\n#include <stddef.h>\n'
    for name, structure in (('call', Call), ('host', Host)):
        native_name = 'Claw' + name.title()
        offsets = ', '.join(f'offsetof({native_name}, {field})' for field, _ in structure._fields_)
        probe += (f'extern "C" size_t claw_raw_test_{name}_size() {{ return sizeof({native_name}); }}\n'
                  f'extern "C" size_t claw_raw_test_{name}_offset(unsigned index) {{\n'
                  f'  const size_t offsets[] = {{{offsets}}};\n'
                  '  return index < sizeof(offsets) / sizeof(offsets[0]) ? offsets[index] : (size_t)-1;\n}\n')
    compiler_identity = subprocess.check_output([compiler, '--version'], text=True)
    cache_inputs = {'compiler': str(Path(compiler).resolve()), 'identity': compiler_identity,
                    'flags': flags + ['-dynamiclib', '-I', str(ROOT / 'Sources')],
                    'sources': sources, 'abiProbe': probe,
                    'dependencies': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in sorted(dependencies)}}
    key = hashlib.sha256(json.dumps(cache_inputs, sort_keys=True).encode()).hexdigest()
    directory = ROOT / 'work/build/game-image-raw' / key
    directory.mkdir(parents=True, exist_ok=True)
    library = directory / 'libGameImageRaw.dylib'
    if not library.exists():
        probe_path = directory / 'abi-probe.cpp'
        probe_path.write_text(probe)
        temporary_library = directory / f'libGameImageRaw.{os.getpid()}.dylib'
        subprocess.run([compiler, *flags, '-dynamiclib', *sources, str(probe_path),
                        '-I', str(ROOT / 'Sources'), '-o', str(temporary_library)], check=True)
        temporary_library.replace(library)
    lib = C.CDLL(str(library))
    for name, structure in (('call', Call), ('host', Host)):
        native_size = getattr(lib, f'claw_raw_test_{name}_size')
        native_size.argtypes, native_size.restype = [], C.c_size_t
        assert native_size() == C.sizeof(structure), (name, 'ABI size', native_size(), C.sizeof(structure))
        native_offset = getattr(lib, f'claw_raw_test_{name}_offset')
        native_offset.argtypes, native_offset.restype = [U], C.c_size_t
        for index, (field, _) in enumerate(structure._fields_):
            assert native_offset(index) == getattr(structure, field).offset, (name, field, 'ABI offset')
    lib.claw_game_image_raw_entry.argtypes = [U, U, C.POINTER(U), U, C.POINTER(Host), C.POINTER(U)]
    lib.claw_sprite_project.argtypes = [C.POINTER(Projection), C.POINTER(U), C.POINTER(U)]
    return lib


class Comparison:
    def __init__(self, lib):
        self.lib = lib
        claw()  # Verify the mandated reference before the original runner reads it.
        self.original = OriginalV10(ROOT / 'Original/claw10/CLAW.EXE')
        self.u = self.original.u
        self.u.mem_map(BASE, SIZE)
        self.original.write_words(COPY, [COPY_STUB])
        self.heap = (C.c_uint8 * SIZE)()
        self.stack = (C.c_uint8 * STACK_SIZE)()
        self.native = True
        self.events = []
        self.errors = []
        self.policy = ''
        self.fail_service = 0
        self.lookup = Bytes(self.resolve)
        self.service = Service(self.invoke)
        self.host = Host(bytes=self.lookup, call=self.service, entryStackPointer=self.original.stack)
        self.u.hook_add(UC_HOOK_CODE, self.hook)
        self.calls = self.event_count = 0
        self.rng = random.Random(ENTRY)

    def resolve(self, _, token, count):
        for start, size, array in ((BASE, SIZE, self.heap), (STACK, STACK_SIZE, self.stack)):
            if start <= token and token + count <= start + size:
                return C.addressof(array) + token - start
        return None

    def read(self, token, count):
        if not self.native:
            return bytes(self.u.mem_read(token, count))
        address = self.resolve(None, token, count)
        assert address, ('unmapped read', hex(token), count)
        return C.string_at(address, count)

    def write(self, token, data):
        if not self.native:
            self.u.mem_write(token, data)
        else:
            address = self.resolve(None, token, len(data))
            assert address, ('unmapped write', hex(token), len(data))
            C.memmove(address, data, len(data))

    def words(self, token, count=1):
        return list(struct.unpack('<' + 'I' * count, self.read(token, count * 4)))

    def put(self, token, words):
        self.write(token, struct.pack('<' + 'I' * len(words), *[x & 0xffffffff for x in words]))

    def snapshot(self):
        return hashlib.sha256(self.read(BASE, SIZE)).hexdigest()

    def record(self, fn, receiver, args, sp):
        if fn == PROJECT:
            spans = [(arg, self.read(arg, 4).hex()) for arg in args]
        elif fn == COPY:
            spans = [(args[1], self.read(args[1], 16).hex())]
        else:
            spans = [(args[i], self.read(args[i], 16).hex()) for i in (0, 2)]
        self.events.append((fn, receiver, tuple(args), sp, tuple(spans), self.snapshot()))

    def projection_mutation(self):
        if self.policy == 'project-dimensions':
            self.put(IMAGE + 0x10, [57, 43])
        elif self.policy == 'project-target-path':
            self.put(ACTOR + 8, [0])
            self.put(ACTOR + 0x54, [0x80000000])
            self.put(TARGET + 0x10, [170, 130])
        elif self.policy == 'project-world':
            self.put(PARENT + 0x24, [OTHER_WORLD])
            self.put(OTHER_WORLD + 0x10, [91, 61, 143, 117])

    def effect(self, fn, args):
        if fn == COPY:
            self.write(args[0], self.read(args[1], 16))
            if self.policy == 'copy-reload':
                self.put(IMAGE + 0x30, [COMPRESSED + 0x100])
                self.put(TARGET + 0x2c, [SURFACE + 0x100])
                self.put(IMAGE + 0x10, [1, 2])
                self.put(ACTOR + 0x4c, [900, 901])
                self.put(args[0], [95, 65, 140, 110])
                self.put(WORLD + 0x10, [300, 300, 301, 301])
            return 0
        assert fn == BLIT
        if self.policy == 'blit-stores':
            self.put(ACTOR + 0x18, [0xdeadbeef] * 9)
            self.put(ACTOR + 0x4c, [600, 601])
            self.put(args[0], [3, 5, 17, 23])
            self.put(args[2], [0, 1, 2, 3])
        return 0x88760001  # Deliberately nonzero; raw void helper must ignore it.

    def invoke(self, _, pointer):
        try:
            c = pointer.contents
            fn, args = c.function, list(c.arguments[:c.argumentCount])
            assert fn in (PROJECT, COPY, BLIT), hex(fn)
            assert not c.receiver2 and not c.x87ArgumentCount
            self.record(fn, c.receiver, args, c.stackPointer)
            if fn == self.fail_service:
                self.host.fault = 2
                self.host.faultAddress = fn
                return 0
            if fn == PROJECT:
                p = Projection(self.words(c.receiver + 8)[0], *self.words(c.receiver + 0x30, 2),
                               *self.words(c.receiver + 0x40, 6))
                x, y = U(self.words(args[0])[0]), U(self.words(args[1])[0])
                self.lib.claw_sprite_project(C.byref(p), C.byref(x), C.byref(y))
                self.put(args[0], [x.value])
                self.put(args[1], [y.value])
                self.projection_mutation()
                return 0
            return self.effect(fn, args)
        except Exception as error:
            self.errors.append(error)
            self.host.fault = 6
            return 0

    def hook(self, _, address, size, user):
        if address == 0x4d333d:
            self.projection_mutation()
            return
        if address not in (PROJECT, COPY_STUB, BLIT):
            return
        sp = self.u.reg_read(UC_X86_REG_ESP)
        fn = COPY if address == COPY_STUB else address
        args = self.words(sp + 4, 5 if fn == BLIT else 2)
        receiver = 0 if fn == COPY else self.u.reg_read(UC_X86_REG_ECX)
        self.record(fn, receiver, args, sp)
        if fn == PROJECT:
            return  # Keep the original projection instructions in the baseline.
        result = self.effect(fn, args)
        ret = self.words(sp)[0]
        self.u.reg_write(UC_X86_REG_EAX, result)
        self.u.reg_write(UC_X86_REG_ESP, sp + 4 + 4 * len(args))
        self.u.reg_write(UC_X86_REG_EIP, ret)

    def reset(self, path, flags=0, x=130, y=100, policy='', projection_flags=0):
        self.native = True
        self.events, self.errors, self.policy = [], [], policy
        self.host.fault = self.host.faultAddress = 0
        self.host.call = self.service
        self.fail_service = 0
        self.write(BASE, self.rng.randbytes(SIZE))
        self.write(STACK, bytes([0xa5]) * STACK_SIZE)
        self.put(IMAGE, [0x513a70, 42, 0, PARENT, 80, 60, 40, 30, -7, 9, 0x11, SURFACE, COMPRESSED])
        self.put(ACTOR + 8, [0x40000 if path == 'world' else 0])
        self.put(ACTOR + 0x10, [3, -4])
        self.put(ACTOR + 0x3c, [HOLDER, flags, 18, 50, x, y])
        self.put(ACTOR + 0x54, [0x80000000, 0, 0, 0] if path != 'actor' else [90, 60, 145, 115])
        self.put(HOLDER + 0x5c, [PLANE])
        self.put(PARENT + 0x24, [WORLD])
        self.put(WORLD + 0x10, [85, 55, 150, 120])
        self.put(TARGET + 0x10, [160, 125])
        self.put(TARGET + 0x2c, [SURFACE])
        self.put(PLANE + 8, [projection_flags])
        self.put(PLANE + 0x30, [512, 256, 64, 64, 0, 0, 511, 255, 0, 0])

    def run_native(self):
        result = U(0xaabbccdd)
        ok = self.lib.claw_game_image_raw_entry(ENTRY, IMAGE, (U * 2)(ACTOR, TARGET), 2,
                                               C.byref(self.host), C.byref(result))
        assert not self.errors, self.errors
        return ok

    def compare(self, label):
        before, stack = self.read(BASE, SIZE), self.read(STACK, STACK_SIZE)
        assert self.run_native() == 1 and not self.host.fault, (label, self.host.fault, hex(self.host.faultAddress))
        native_events, native_heap = list(self.events), self.read(BASE, SIZE)
        self.native = False
        self.u.mem_write(BASE, before)
        self.u.mem_write(STACK, stack)
        self.events = []
        self.original.call(ENTRY, IMAGE, struct.pack('<II', ACTOR, TARGET))
        assert self.events == native_events, (label, 'ordered services', self.events, native_events)
        original_heap = self.read(BASE, SIZE)
        assert original_heap == native_heap, (label, 'heap differences',
            [(hex(BASE + i), original_heap[i:i+4].hex(), native_heap[i:i+4].hex())
             for i in range(0, SIZE, 4) if original_heap[i:i+4] != native_heap[i:i+4]])
        self.calls += 1
        self.event_count += len(self.events)
        self.native = True


def main():
    comparison = Comparison(build())
    for path in ('world', 'actor', 'target'):
        for flags in (0, 1, 2, 4, 6, 8, 0x10000000, 0x1000000e, 0xffffffff):
            for x, y in ((130, 100), (90, 60), (180, 150), (-100, -100), (130, 1000)):
                comparison.reset(path, flags, x, y)
                comparison.compare(f'{path}/flags-{flags:x}/position-{x}-{y}')
    for policy in ('project-dimensions', 'project-target-path', 'project-world', 'copy-reload', 'blit-stores'):
        comparison.reset('world', 0xffffffff, policy=policy)
        comparison.compare(policy)
    for flags in (4, 8, 12):
        for x, y in ((-20, -10), (530, 280), (130, 100)):
            comparison.reset('world', 0xffffffff, x, y, projection_flags=flags)
            comparison.compare(f'projection-wrap/{flags}/{x}/{y}')
    comparison.host.entryStackPointer = 0
    comparison.reset('world', policy='blit-stores')
    comparison.compare('default-stack')
    # Use another entry stack to catch hard-coded local tokens.
    comparison.original.stack = comparison.host.entryStackPointer = 0x2009000
    comparison.reset('world', policy='copy-reload')
    comparison.compare('relocated-stack')
    controls = 0
    for service in (PROJECT, COPY, BLIT):
        comparison.reset('world')
        before = comparison.read(ACTOR + 0x18, 36)
        comparison.fail_service = service
        assert not comparison.run_native() and comparison.host.fault == 2
        assert comparison.read(ACTOR + 0x18, 36) == before, ('continued after service fault', hex(service))
        assert comparison.events[-1][0] == service
        controls += 1
    comparison.reset('world')
    before = comparison.read(BASE, SIZE)
    comparison.host.call = Service()
    assert not comparison.run_native() and comparison.host.fault
    assert comparison.read(BASE, SIZE) == before
    controls += 1
    print(json.dumps({'rawActorComparisons': comparison.calls, 'orderedFullHeapEvents': comparison.event_count,
                      'missingServiceControls': controls, 'heapBytes': SIZE,
                      'originalProjectionExecuted': True, 'familyAdmission': False}))


if __name__ == '__main__':
    main()
