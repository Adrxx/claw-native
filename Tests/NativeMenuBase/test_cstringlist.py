"""Focused platform controls; execute original CStringList and CString code.

Run: work/test-env/bin/python -m unittest Tests.NativeMenuBase.test_cstringlist
This is platform evidence, not game-family admission.
"""
import unittest
from Tests.NativeMenuBase.trace import (
    Blocked, MenuTrace, STACK, STOP, UC_X86_REG_EAX, UC_X86_REG_EBX,
    UC_X86_REG_ECX, UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP,
)

CONSTRUCT, HEAD, TAIL, REMOVE, CLEAR = 0x4f5249, 0x4f5382, 0x4f53b7, 0x4f53eb, 0x4f5288
PRESERVED = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)


class OriginalListTrace(MenuTrace):
    """Hash-checked original with only existing allocator/import boundaries.

    MenuTrace obtains the executable from program.claw(). No additional import
    slot patching occurs. CString, CPlex, memcpy and SEH execute original code.
    """
    def hook(self, machine, address, size, user):
        if address == STOP:
            machine.emu_stop()
        elif address in self.imports or address in (0x4f63ec, 0x4f6428):
            self.fixture(address)
        elif not any(lo <= address < hi for lo, hi in (
                (0x4f5249, 0x4f545f), (0x4f5aa8, 0x4f5ade),
                (0x4f6433, 0x4f66f3), (0x4a48c0, 0x4a48df),
                (0x4a4a80, 0x4a4da0))):
            raise Blocked(f'Unprovided control dependency at {address:#x}')


def invoke(trace, address, receiver, *arguments):
    for i, value in enumerate((STOP, *arguments)):
        trace.put(STACK + 4*i, value)
    trace.machine.reg_write(UC_X86_REG_ESP, STACK)
    trace.machine.reg_write(UC_X86_REG_EIP, address)
    trace.machine.reg_write(UC_X86_REG_ECX, receiver)
    sentinels = [0x12345000 + 17*i for i in range(4)]
    for register, value in zip(PRESERVED, sentinels):
        trace.machine.reg_write(register, value)
    exception_head = trace.word(0)
    if isinstance(trace, OriginalListTrace):
        trace.machine.emu_start(address, STOP, count=100_000)
    else:
        trace.fixture(address)
    assert trace.machine.reg_read(UC_X86_REG_EIP) == STOP, 'Return continuation'
    assert trace.machine.reg_read(UC_X86_REG_ESP) == STACK + 4*(1+len(arguments)), 'Callee-pop ABI'
    assert [trace.machine.reg_read(r) for r in PRESERVED] == sentinels, 'Preserved registers'
    assert trace.word(0) == exception_head, 'Exception chain'
    return trace.machine.reg_read(UC_X86_REG_EAX)


def raw(trace, value):
    address = trace.allocate(len(value)+5)
    trace.machine.mem_write(address, value+b'\0TAIL')
    return address


def snapshot(trace, collection):
    nodes, values, data = [], [], []
    current, previous = trace.word(collection+4), 0
    while current:
        assert current not in nodes and len(nodes) < 100, 'List cycle'
        assert trace.word(current+4) == previous, 'Backward link'
        nodes.append(current)
        pointer = trace.word(current+8)
        values.append(trace.bytestring(pointer))
        data.append(pointer)
        previous, current = current, trace.word(current)
    assert trace.word(collection+8) == previous, 'Tail'
    assert trace.word(collection+12) == len(nodes), 'Count'
    blocks, pool = [], []
    block, size = trace.word(collection+20), trace.word(collection+24)
    while block:
        assert block not in blocks and len(blocks) < 100, 'Pool cycle'
        blocks.append(block)
        assert trace.allocations.get(block) == 4+12*size, 'CPlex size'
        pool.extend(block+4+12*i for i in range(size))
        block = trace.word(block)
    unused, free = [], trace.word(collection+16)
    while free:
        assert free not in unused and free in pool and free not in nodes, 'Free node'
        unused.append(free)
        free = trace.word(free)
    assert set(nodes+unused) == set(pool), 'Pool ownership'
    return dict(values=values, nodes=nodes, data=data, blocks=blocks,
                shape=(tuple(pool.index(n) for n in nodes), tuple(pool.index(n) for n in unused)))


class CStringListControls(unittest.TestCase):
    def pair(self, size=2):
        pair = []
        for cls in (OriginalListTrace, MenuTrace):
            trace = cls()
            collection = trace.allocate(28)
            self.assertEqual(invoke(trace, CONSTRUCT, collection, size), collection)
            pair.append((trace, collection))
        return pair

    def same(self, pair):
        a, b = [snapshot(t, c) for t, c in pair]
        self.assertEqual(a['values'], b['values'])
        self.assertEqual(a['shape'], b['shape'])

    def test_mixed_insertion_raw_copy_pool_growth(self):
        pair = self.pair()
        for op, value in ((TAIL, b'tail'), (HEAD, b'head'), (TAIL, b'\xe9\xff'),
                          (HEAD, b'x'*257), (TAIL, b'fifth')):
            for trace, collection in pair:
                source = raw(trace, value)
                before = set(snapshot(trace, collection)['nodes'])
                node = invoke(trace, op, collection, source)
                state = snapshot(trace, collection)
                self.assertEqual(set(state['nodes'])-before, {node})
                self.assertEqual(state['nodes'][0 if op == HEAD else -1], node)
                self.assertNotEqual(trace.word(node+8), source)
                trace.machine.mem_write(source, b'Z')
                self.assertEqual(trace.bytestring(trace.word(node+8)), value)
                self.assertIn(source, trace.allocations)
            self.same(pair)

    def test_empty_null_and_lifecycle(self):
        pair = self.pair(1)
        for op, value in ((TAIL, None), (HEAD, b''), (TAIL, b'after')):
            for trace, collection in pair:
                invoke(trace, op, collection, 0 if value is None else raw(trace, value))
            self.same(pair)
        for trace, collection in pair:
            invoke(trace, CLEAR, collection)
            self.assertEqual(trace.word(collection), 0x510224)
            self.assertEqual(trace.word(collection+24), 1)
        self.same(pair)

    def test_remove_hidden_return_reuse_and_owned_lifetime(self):
        pair, outputs = self.pair(), []
        for trace, collection in pair:
            for value in (b'first', b'second', b'third'):
                invoke(trace, TAIL, collection, raw(trace, value))
            before = snapshot(trace, collection)
            removed, pointer = before['nodes'][0], before['data'][0]
            output = trace.allocate(4)
            self.assertEqual(invoke(trace, REMOVE, collection, output), output)
            self.assertEqual(trace.word(output), pointer)
            self.assertEqual(trace.word(pointer-12), 1)
            self.assertEqual(trace.word(collection+16), removed)
            self.assertEqual(invoke(trace, TAIL, collection, raw(trace, b'reused')), removed)
            outputs.append((trace, pointer))
        self.same(pair)
        for trace, collection in pair:
            owned = snapshot(trace, collection)
            invoke(trace, CLEAR, collection)
            self.assertTrue(all(b not in trace.allocations for b in owned['blocks']))
            self.assertTrue(all(p-12 not in trace.allocations for p in owned['data']))
            self.assertEqual([trace.word(collection+o) for o in (4,8,12,16,20)], [0]*5)
        self.same(pair)
        for trace, pointer in outputs:
            self.assertIn(pointer-12, trace.allocations)
            self.assertEqual(trace.bytestring(pointer), b'first')

    def test_last_remove_and_repopulation(self):
        pair = self.pair(3)
        for trace, collection in pair:
            node = invoke(trace, TAIL, collection, raw(trace, b'only'))
            pointer, pool = trace.word(node+8), trace.word(collection+20)
            output = trace.allocate(4)
            self.assertEqual(invoke(trace, REMOVE, collection, output), output)
            self.assertEqual(trace.word(output), pointer)
            self.assertNotIn(pool, trace.allocations)
            self.assertIn(pointer-12, trace.allocations)
            invoke(trace, CLEAR, collection)
            self.assertEqual(trace.bytestring(pointer), b'only')
            self.assertEqual(trace.word(collection), 0x510224)
            self.assertEqual(trace.word(collection+24), 3)
            invoke(trace, HEAD, collection, raw(trace, b'again'))
        self.same(pair)

    def test_derived_vtable_preserved_by_nonvirtual_operations(self):
        pair = self.pair(3)
        for trace, collection in pair:
            vtable = trace.allocate(16)
            trace.machine.mem_write(vtable, b'derived-vtable!!')
            trace.put(collection, vtable)
            for operation, value in ((TAIL, b'tail'), (HEAD, b'head')):
                invoke(trace, operation, collection, raw(trace, value))
                self.assertEqual(trace.word(collection), vtable)
            output = trace.allocate(4)
            invoke(trace, REMOVE, collection, output)
            self.assertEqual(trace.bytestring(trace.word(output)), b'head')
            self.assertEqual(trace.word(collection), vtable)
            invoke(trace, CLEAR, collection)
            self.assertEqual(trace.word(collection), vtable)
            self.assertEqual(trace.word(collection+24), 3)
            self.assertEqual(bytes(trace.machine.mem_read(vtable, 16)), b'derived-vtable!!')
        self.same(pair)

    def test_remove_all_decrements_shared_string_reference(self):
        pair = self.pair()
        for trace, collection in pair:
            node = invoke(trace, TAIL, collection, raw(trace, b'shared'))
            pointer = trace.word(node+8)
            # A second CString owner retains this buffer. Sharing increments
            # the header count; RemoveAll must release only the list's owner.
            owner = trace.allocate(4)
            trace.put(owner, pointer)
            trace.put(pointer-12, 2)
            invoke(trace, CLEAR, collection)
            self.assertEqual(trace.word(pointer-12), 1)
            self.assertIn(pointer-12, trace.allocations)
            self.assertEqual(trace.bytestring(trace.word(owner)), b'shared')
        self.same(pair)

    def test_aliasing_input_then_remove_across_pool_blocks(self):
        pair, retained = self.pair(2), []
        value = b'prefix:\xe9\xff-suffix'
        for trace, collection in pair:
            first = invoke(trace, TAIL, collection, raw(trace, value))
            source = trace.word(first+8)
            # LPCSTR inputs may point at or inside a live list element. The
            # suffix insertion also exhausts the first two-node CPlex block.
            invoke(trace, TAIL, collection, source)
            invoke(trace, TAIL, collection, source+7)
            state = snapshot(trace, collection)
            self.assertEqual(state['values'], [value, value, value[7:]])
            self.assertEqual(len(set(state['data'])), 3)
            self.assertEqual(len(state['blocks']), 2)
            self.assertEqual([trace.word(p-12) for p in state['data']], [1]*3)
            owner = trace.allocate(4)
            trace.put(owner, source)
            trace.put(source-12, 2)
            retained.append((trace, owner, state['blocks'], []))
        self.same(pair)
        for remaining, expected in ((2, value), (1, value), (0, value[7:])):
            for (trace, collection), (_, owner, blocks, outputs) in zip(pair, retained):
                before = snapshot(trace, collection)
                pointer = before['data'][0]
                references = trace.word(pointer-12)
                output = trace.allocate(4)
                self.assertEqual(invoke(trace, REMOVE, collection, output), output)
                self.assertEqual(trace.word(output), pointer)
                self.assertEqual(trace.bytestring(pointer), expected)
                self.assertEqual(trace.word(pointer-12), references)
                self.assertIn(pointer-12, trace.allocations)
                self.assertEqual(trace.word(collection+12), remaining)
                self.assertEqual([b in trace.allocations for b in blocks], [bool(remaining)]*2)
                self.assertEqual(trace.bytestring(trace.word(owner)), value)
                outputs.append((output, expected))
            self.same(pair)
        for (trace, collection), (_, owner, _, outputs) in zip(pair, retained):
            invoke(trace, CLEAR, collection)
            self.assertEqual(trace.word(trace.word(owner)-12), 2)
            for output, expected in outputs:
                pointer = trace.word(output)
                self.assertIn(pointer-12, trace.allocations)
                self.assertEqual(trace.bytestring(pointer), expected)
        self.same(pair)

    def test_withheld_services_preserve_storage(self):
        for operation in (CONSTRUCT, HEAD, TAIL, REMOVE, CLEAR):
            trace, collection = self.pair()[1]
            invoke(trace, TAIL, collection, raw(trace, b'keep'))
            argument = trace.allocate(4) if operation == REMOVE else raw(trace, b'new')
            before = bytes(trace.machine.mem_read(0x61000000, trace.heap_next-0x61000000))
            allocations = dict(trace.allocations)
            trace.deny_platform = operation
            with self.assertRaises(Blocked):
                invoke(trace, operation, collection, *(() if operation == CLEAR else (argument,)))
            self.assertEqual(bytes(trace.machine.mem_read(0x61000000, trace.heap_next-0x61000000)), before)
            self.assertEqual(trace.allocations, allocations)

    def test_unknown_still_blocks(self):
        with self.assertRaises(Blocked):
            invoke(MenuTrace(), 0x4f0000, 0)

    def test_malformed_storage_fails_before_mutation(self):
        for corruption in ('count', 'backward', 'pool', 'free', 'string'):
            trace = MenuTrace()
            collection = trace.allocate(28)
            invoke(trace, CONSTRUCT, collection, 2)
            node = invoke(trace, TAIL, collection, raw(trace, b'keep'))
            if corruption == 'count':
                trace.put(collection+12, 2)
            elif corruption == 'backward':
                trace.put(node+4, node)
            elif corruption == 'pool':
                trace.put(collection+20, node)
            elif corruption == 'free':
                trace.put(collection+16, node)
            else:
                trace.put(trace.word(node+8)-12, 0)
            before = bytes(trace.machine.mem_read(0x61000000, trace.heap_next-0x61000000))
            allocations = dict(trace.allocations)
            with self.assertRaises(Blocked):
                invoke(trace, CLEAR, collection)
            self.assertEqual(bytes(trace.machine.mem_read(0x61000000, trace.heap_next-0x61000000)), before)
            self.assertEqual(trace.allocations, allocations)

    def test_neighboring_cstring_and_object_list(self):
        trace = MenuTrace()
        text, copy = trace.allocate(4), trace.allocate(4)
        invoke(trace, 0x4f65f2, text, raw(trace, b'neighbor'))
        invoke(trace, 0x4f6449, copy, text)
        invoke(trace, 0x4f6584, text)
        self.assertEqual(trace.bytestring(trace.word(copy)), b'neighbor')
        self.assertEqual(trace.word(text), trace.empty_string)
        collection, value = trace.allocate(28), trace.allocate(8)
        trace.machine.mem_write(value, b'payload!')
        invoke(trace, 0x4f5133, collection, 2)
        first = invoke(trace, 0x4f51c5, collection, value)
        second = invoke(trace, 0x4f51c5, collection, copy)
        self.assertEqual(trace.word(first), second)
        self.assertEqual(trace.word(second+4), first)
        invoke(trace, 0x4f5212, collection, first)
        invoke(trace, 0x4f5172, collection)
        self.assertIn(value, trace.allocations)
        self.assertEqual(bytes(trace.machine.mem_read(value, 8)), b'payload!')


if __name__ == '__main__':
    unittest.main()
