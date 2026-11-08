"""Build membership and dispatch contract checks; no recovered game execution."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.claw import gen_project as project


class ProjectMembershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Sources').mkdir()
        self.real_runtime = (project.ROOT / project.RUNTIME_PATH).read_text()
        (self.root / project.RUNTIME_PATH).write_text(self.real_runtime)
        self.patch = patch.object(project, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        # These keyword defaults captured ROOT when the generator was imported.
        # Keep source validation in the same temporary checkout as the inventory.
        for function in (project.checked_source, project.canonical_inventory):
            defaults = patch.dict(function.__kwdefaults__, root=self.root)
            defaults.start()
            self.addCleanup(defaults.stop)
        self.family = {
            'id': 'example', 'abi': 'canonical', 'sources': ['Sources/Example.cpp'],
            'owned': [{'address': '0x401000', 'convention': 'cdecl', 'argc': 1, 'returns': 'u32'}],
            'oracle': {'kind': 'clawparity', 'entry': 'claw_example_entry'},
            'evidence': {'level': 'admitted'},
        }
        (self.root / 'Sources/Example.cpp').write_text('// inventory fixture\n')
        # Membership fixtures deliberately have no executable cases or gate.
        # Admission fingerprint validation has its own tests.
        admission = patch('Tests.clawparity.build_inputs.admission_errors', return_value=[])
        admission.start()
        self.addCleanup(admission.stop)

    def inventory(self, families=None, tracked=(), extras=(), exclusions=()):
        return project.source_inventory(tracked, families or [self.family], extras, exclusions)

    def test_untracked_admitted_and_runtime_included_without_staging(self):
        compiled, headers, registry = self.inventory(tracked=['Sources/Legacy.cpp'])
        self.assertEqual(compiled, ['Sources/Example.cpp', 'Sources/Legacy.cpp'])
        self.assertIn(project.RUNTIME_PATH, headers)
        self.assertIn(project.DISPATCH_PATH, headers)
        self.assertEqual(registry[0]['entry'], 'claw_example_entry')
        self.assertEqual(project.gate_sources_text(compiled), 'Example\nLegacy\n')

    def test_nonadmitted_stub_excluded_even_if_tracked(self):
        self.family['evidence']['level'] = 'provisional'
        self.assertEqual(self.inventory(tracked=['Sources/Example.cpp'])[0], [])
        (self.root / 'Sources/UnlistedStub.cpp').write_text('// no manifest\n')
        self.assertEqual(self.inventory()[0], [])

    def test_duplicate_address_signature_entry_and_source_fail(self):
        for field in ('address', 'signature', 'entry', 'source'):
            with self.subTest(field=field):
                second = copy.deepcopy(self.family)
                second['id'] = 'other'
                second['sources'] = ['Sources/Other.cpp']
                (self.root / 'Sources/Other.cpp').write_text('// fixture\n')
                second['oracle']['entry'] = 'claw_other_entry'
                second['owned'][0]['address'] = '0x402000'
                if field in ('address', 'signature'):
                    second['owned'][0]['address'] = '0x00401000'
                    if field == 'signature':
                        second['owned'][0]['argc'] = 2
                if field == 'entry':
                    second['oracle']['entry'] = self.family['oracle']['entry']
                if field == 'source':
                    second['sources'] = self.family['sources'][:]
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    self.inventory([self.family, second])
        self.family['owned'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.inventory()

    def test_named_layout_families_share_only_reviewed_header_inputs(self):
        second = copy.deepcopy(self.family)
        second.update(id='other', sources=['Sources/Other.cpp'])
        second['oracle']['entry'] = 'claw_other_entry'
        second['owned'][0]['address'] = '0x402000'
        (self.root / 'Sources/Other.cpp').write_text('// fixture\n')
        headers = ['Sources/ClawRecoveredLayout.h', 'Sources/ClawRecoveredNames.h']
        for header in headers:
            (self.root / header).write_text('// shared header fixture\n')
        for family in (self.family, second):
            family['mutation'] = 'named-layout'
            family['sources'] += headers
        compiled, included, registry = self.inventory([self.family, second])
        self.assertEqual(compiled, ['Sources/Example.cpp', 'Sources/Other.cpp'])
        self.assertTrue(all(included.count(header) == 1 for header in headers))
        self.assertEqual(len(registry), 2)
        second.pop('mutation')
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            self.inventory([self.family, second])
        second['mutation'] = 'named-layout'
        second['sources'].append('Sources/Example.cpp')
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            self.inventory([self.family, second])
        second['sources'].pop()
        for family in (self.family, second):
            family['sources'].append('Sources/OtherHeader.h')
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            self.inventory([self.family, second])

    def test_alternate_profile_compiles_without_replacing_v10_dispatch(self):
        alternate = copy.deepcopy(self.family)
        alternate.update(id='alternate', program='claw-v1.3', sources=['Sources/Alternate.cpp'])
        alternate['oracle']['entry'] = 'claw_alternate_entry'
        alternate['owned'][0]['interval_end'] = '0x401020'
        (self.root / 'Sources/Alternate.cpp').write_text('// v1.3 fixture\n')
        # Isolate membership from admission fingerprint validation.
        with patch('Tests.clawparity.build_inputs.admission_errors', return_value=[]):
            compiled, _, registry = self.inventory([self.family, alternate])
            self.assertEqual(compiled, ['Sources/Alternate.cpp', 'Sources/Example.cpp'])
            self.assertEqual([r['family'] for r in registry], ['example'])
            alternate['owned'] *= 2
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                self.inventory([self.family, alternate])

    def test_nonadmitted_alternate_profile_is_not_compiled(self):
        self.family.update(program='claw-v1.3', evidence={'level': 'none'})
        compiled, _, registry = self.inventory(tracked=['Sources/Example.cpp'])
        self.assertEqual(compiled, [])
        self.assertEqual(registry, [])

    def test_missing_file_unsafe_path_and_malformed_entry_fail(self):
        for path in ('Sources/Missing.cpp', 'Sources/../Outside.cpp', '/tmp/Outside.cpp'):
            with self.subTest(path=path):
                manifest = copy.deepcopy(self.family)
                manifest['sources'] = [path]
                with self.assertRaises(ValueError):
                    self.inventory([manifest])
        (self.root / 'Sources/Link.cpp').symlink_to(self.root / 'Sources/Example.cpp')
        self.family['sources'] = ['Sources/Link.cpp']
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.inventory()
        self.family['sources'] = ['Sources/Example.cpp']
        self.family['oracle']['entry'] = 'not_a_c_symbol();'
        with self.assertRaisesRegex(ValueError, 'entry'):
            self.inventory()

    def test_wide_owned_argument_counts_survive_inventory(self):
        for count in (0, 16, 17, 31, 32):
            with self.subTest(count=count):
                self.family["owned"][0]["argc"] = count
                self.assertEqual(self.inventory()[2][0]["argc"], count)

    def test_unsupported_owned_abi_fails_before_generating(self):
        for field, value in (('argc', None), ('argc', True), ('argc', 33), ('argc', -1),
                             ('convention', 'unknown'),
                             ('returns', 'f64'), ('returns', 'x87'), ('x87_args', 1)):
            with self.subTest(field=field, value=value):
                manifest = copy.deepcopy(self.family)
                manifest['owned'][0][field] = value
                with self.assertRaisesRegex(ValueError, 'unsupported owned ABI|x87_result requires'):
                    self.inventory([manifest])

    def test_x87_result_requires_balanced_single_push_ordinary_entry(self):
        signature = self.family['owned'][0]
        signature.update(returns='x87', x87_result={'pop': 0, 'push': 1})
        self.assertEqual(self.inventory()[2][0]['returns'], 'x87')
        for change in ({'x87_result': {'pop': 1, 'push': 1}}, {'x87_result': {'pop': 0, 'push': 0}},
                       {'convention': 'fastcall'}, {'source_context': {'input_mask': 0, 'output_mask': 0, 'preserve_mask': 0}}):
            with self.subTest(change=change):
                manifest = copy.deepcopy(self.family)
                manifest['owned'][0].update(change)
                with self.assertRaisesRegex(ValueError, 'unsupported owned ABI|x87_result requires'):
                    self.inventory([manifest])

    def test_generated_dispatch_transports_x87_result_exactly(self):
        clang = shutil.which('clang')
        if not clang:
            self.skipTest('clang unavailable')
        self.family['owned'][0].update(argc=0, returns='x87', x87_result={'pop': 0, 'push': 1})
        (self.root / project.DISPATCH_PATH).write_text(project.canonical_dispatch_text(self.inventory()[2]))
        source = self.root / 'x87.c'
        source.write_text(r'''
#include "ClawCanonicalDispatch.h"
#include <assert.h>
#include <string.h>
static int mode, steps;
static int outerUser;
static const ClawX87Value LN2 = {0xb17217f7d1cf79acull, 0x3ffe, 0};
static uint32_t outward(void *user, const ClawCall *c) {
    ClawX87State *s = c->x87State;
    uint32_t i;
    assert(user == &outerUser && c->x87ArgumentCount == CLAW_X87_STEP && !c->function);
    for (i = s->count; i > 0; --i) s->slots[i] = s->slots[i - 1];
    s->slots[0] = LN2; s->count++;
    s->status = (s->status & ~0x3800u) | ((((s->status >> 11) + 7u) & 7u) << 11);
    s->returned = 1; steps++;
    return 0;
}
static uint32_t outer(ClawHost *host, ClawCall *c) { return host->call(host->user, c); }
uint32_t claw_example_entry(uint32_t fn, uint32_t receiver, const uint32_t *args,
    uint32_t argc, ClawHost *host, uint32_t *result) {
    ClawX87State s; ClawCall c, q;
    memset(&s, 0, sizeof(s)); s.size = sizeof(s); s.version = CLAW_X87_VERSION;
    memset(&c, 0, sizeof(c)); c.function = fn; c.x87ArgumentCount = CLAW_X87_ENTRY; c.x87State = &s;
    if (mode == 3) c.function = fn + 1;
    if (outer(host, &c) || host->fault) return 0;
    assert(s.returned == 1 && s.count == 1 && s.control == 0x023f && (s.status >> 11) == 3);
    s.returned = 0; s.pushCount = 1;
    memset(&q, 0, sizeof(q)); q.x87ArgumentCount = CLAW_X87_STEP; q.x87Operation = CLAW_X87_LN2; q.x87State = &s;
    outer(host, &q);
    if (host->fault) return 0;
    *result = 7;
    if (mode == 1) return 1;
    s.returned = 0; s.popCount = 0; s.pushCount = 1;
    c.x87ArgumentCount = CLAW_X87_RESULT;
    outer(host, &c);
    if (host->fault) return 0;
    assert(s.returned == 1);
    if (mode == 2) { s.returned = 0; outer(host, &c); if (host->fault) return 0; }
    return 1;
}
static ClawX87State request(void) {
    ClawX87State s;
    memset(&s, 0, sizeof(s)); s.size = sizeof(s); s.version = CLAW_X87_VERSION;
    s.control = 0x023f; s.status = 3u << 11; s.count = 1; s.pushCount = 1;
    s.slots[0].significand = 0x8000000000000000ull; s.slots[0].signExponent = 0x3fff;
    return s;
}
int main(void) {
    ClawHost host; ClawCall call; ClawX87State s = request(); uint32_t result = 99;
    memset(&host, 0, sizeof(host)); memset(&call, 0, sizeof(call));
    host.call = outward; host.user = &outerUser;
    assert(claw_canonical_lookup(0x401000)->returnKind == CLAW_CANONICAL_RETURN_X87);
    call.function = 0x401000; call.x87ArgumentCount = CLAW_X87_EXACT; call.x87State = &s;
    assert(claw_canonical_dispatch(&call, &host, &result) == 1 && result == 7 && steps == 1);
    assert(s.count == 2 && !memcmp(&s.slots[0], &LN2, sizeof(LN2)) && s.slots[1].signExponent == 0x3fff);
    assert((s.status >> 11) == 2 && s.returned == 1 && s.eax == 7 && !s.popCount && s.pushCount == 1);
    for (mode = 1; mode <= 3; ++mode) {
        host.fault = 0; s = request(); result = 99;
        assert(!claw_canonical_dispatch(&call, &host, &result) && host.fault == CLAW_FAULT_ABI);
        assert(result == 99 && s.count == 1 && !s.returned);
    }
    mode = 0;
    for (int invalid = 0; invalid < 4; ++invalid) {
        ClawCall bad = call; host.fault = 0; s = request(); result = 99;
        if (invalid == 0) bad.x87ArgumentCount = 0;
        if (invalid == 1) s.pushCount = 0;
        if (invalid == 2) s.count = 8;
        if (invalid == 3) bad.x87Operation = CLAW_X87_LN2;
        assert(!claw_canonical_dispatch(&bad, &host, &result) && host.fault == CLAW_FAULT_ABI && result == 99);
    }
    host.fault = 0;
    assert(!claw_canonical_dispatch_context(&call, &host, CLAW_CANONICAL_SOURCE_GRAPH, &result) &&
           host.fault == CLAW_FAULT_ABI);
    return 0;
}
''')
        executable = self.root / 'x87'
        subprocess.run([clang, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-I', str(self.root / 'Sources'), str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True)

    def test_x87_environment_requires_balanced_ordinary_entry(self):
        signature = self.family['owned'][0]
        signature['x87_environment'] = {'pop': 0, 'push': 0}
        self.assertIn('x87_environment', self.inventory()[2][0])
        for change in ({'x87_environment': {'pop': 1, 'push': 1}},
                       {'x87_environment': {'pop': 0, 'push': 1}}, {'returns': 'context'},
                       {'convention': 'fastcall'}):
            original = dict(signature)
            signature.update(change)
            try:
                with self.assertRaises(ValueError):
                    self.inventory()
            finally:
                signature.clear()
                signature.update(original)

    def test_generated_dispatch_transports_x87_environment(self):
        clang = shutil.which('clang')
        if not clang:
            self.skipTest('clang unavailable')
        self.family['owned'][0].update(argc=0, x87_environment={'pop': 0, 'push': 0})
        registry = self.inventory()[2]
        self.assertEqual(registry[0]['x87_environment'], {'pop': 0, 'push': 0})
        (self.root / project.DISPATCH_PATH).write_text(project.canonical_dispatch_text(registry))
        source = self.root / 'environment.c'
        source.write_text(r'''#include "ClawCanonicalDispatch.h"
#include <assert.h>
static int mode;
uint32_t claw_example_entry(uint32_t fn, uint32_t receiver, const uint32_t *args,
    uint32_t argc, ClawHost *host, uint32_t *result) {
    ClawX87State s = {0}; ClawCall c = {0};
    s.size = sizeof(s); s.version = CLAW_X87_VERSION;
    c.function = fn; c.x87ArgumentCount = CLAW_X87_ENTRY; c.x87State = &s;
    if (mode == 3) c.function++;
    host->call(host->user, &c);
    if (host->fault) return 0;
    assert(s.returned && !s.popCount && !s.pushCount);
    s.returned = 0;
    s.status = (s.status & ~0x4700u) | 0x100u;
    *result = 17;
    if (mode == 1) return 1;
    if (mode == 4) s.slots[0].significand++;
    if (mode == 5) s.status ^= 0x800;
    if (mode == 6) s.control ^= 0x400;
    if (mode == 7) s.pushCount = 1;
    c.x87ArgumentCount = CLAW_X87_RESULT;
    host->call(host->user, &c);
    if (mode == 2 && !host->fault) { s.returned = 0; host->call(host->user, &c); }
    return !host->fault;
}
static ClawX87State request(unsigned count, unsigned status) {
    ClawX87State s = {0}; s.size = sizeof(s); s.version = CLAW_X87_VERSION;
    s.control = 0x23f; s.status = status | (3u << 11); s.count = count;
    for (unsigned i = 0; i < count; ++i) { s.slots[i].significand = 0x8000000000000000ull+i; s.slots[i].signExponent = 0x3fff; }
    return s;
}
int main(void) {
    ClawCall c = {0}; ClawHost h = {0}; ClawX87State s; uint32_t result;
    c.function = 0x401000; c.x87ArgumentCount = CLAW_X87_EXACT; c.x87State = &s;
    assert(claw_canonical_lookup(c.function)->x87Environment);
    for (unsigned count = 0; count <= 8; ++count) {
        for (unsigned flags = 0; flags < 64; ++flags) {
            s = request(count, flags | 0x4500); ClawX87State before = s;
            h.fault = 0; result = 99;
            assert(claw_canonical_dispatch(&c, &h, &result) && result == 17);
            assert(s.status == ((3u << 11) | flags | 0x100u) && s.control == before.control);
            assert(s.count == count && s.returned == 1 && s.eax == 17 && !s.pushCount);
            assert(!memcmp(s.slots, before.slots, sizeof(s.slots)));
        }
    }
    for (mode = 1; mode <= 7; ++mode) {
        s = request(1, 0x21); ClawX87State before = s; h.fault = 0; result = 99;
        assert(!claw_canonical_dispatch(&c, &h, &result) && h.fault == CLAW_FAULT_ABI);
        assert(result == 99 && !memcmp(&s, &before, sizeof(s)));
    }
    mode = 0;
    for (unsigned invalid = 0; invalid < 8; ++invalid) {
        ClawCall bad = c; s = request(1, 0); h.fault = 0; result = 99;
        if (invalid == 0) bad.x87ArgumentCount = 0;
        if (invalid == 1) s.pushCount = 1;
        if (invalid == 2) s.popCount = 1;
        if (invalid == 3) s.returned = 1;
        if (invalid == 4) s.count = 9;
        if (invalid == 5) s.reserved0 = 1;
        if (invalid == 6) bad.x87Operation = CLAW_X87_LN2;
        if (invalid == 7) bad.sourceReturnPC = 1;
        assert(!claw_canonical_dispatch(&bad, &h, &result) && h.fault == CLAW_FAULT_ABI && result == 99);
    }
    return 0;
}
''')
        executable = self.root / 'environment'
        subprocess.run([clang, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-I', str(self.root / 'Sources'), str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True)

    def test_fastcall_source_capability_is_preserved_in_registry(self):
        signature=self.family['owned'][0]
        signature['convention']='fastcall'
        signature['source_context']={'input_mask':0x7ff,'output_mask':0x7ff,'preserve_mask':0}
        registry=self.inventory()[2]
        self.assertEqual(registry[0]['convention'],'fastcall')
        self.assertEqual(registry[0]['source_context'],signature['source_context'])

    def test_owned_coverage_interval_only_registers_entry_address(self):
        self.family['owned'][0]['interval_end'] = '0x401010'
        registry = self.inventory()[2]
        self.assertEqual([row['address'] for row in registry], [0x401000])
        self.family['owned'][0]['interval_end'] = '0x400000'
        with self.assertRaisesRegex(ValueError, 'malformed owned interval'):
            self.inventory()

    def test_explicit_app_inventory_is_narrow_and_validated(self):
        (self.root / 'Sources/NewHost.swift').write_text('// fixture\n')
        extras = [{'path': 'Sources/NewHost.swift', 'reason': 'Native host'}]
        self.assertIn('Sources/NewHost.swift', self.inventory(extras=extras)[0])
        for bad in (extras * 2, [{'path': 'Sources/Example.cpp', 'reason': 'bypass'}],
                    [{'path': 'Sources/NewHost.swift'}]):
            with self.assertRaises(ValueError):
                self.inventory(extras=bad)

    def test_exclusions_disable_family_and_preserve_bridging_role(self):
        exclusion = [{'path': 'Sources/Example.cpp', 'reason': 'not supported'}]
        compiled, _, registry = self.inventory(exclusions=exclusion)
        self.assertEqual(compiled, [])
        self.assertEqual(registry, [])
        headers = ['Sources/Legacy.h', project.RUNTIME_PATH]
        entries = [{'path': 'Sources/Legacy.h', 'role': 'bridging', 'reason': 'C++'}]
        with patch.object(project, 'parses_as_c', return_value=True):
            self.assertEqual(project.bridgeable_headers(headers, entries), [project.RUNTIME_PATH])
        self.assertEqual(project.membership(headers, entries)[1], sorted(headers))

    def test_dispatch_is_deterministic_and_uses_original_entry_name(self):
        self.family['oracle']['entry'] = 'claw_custom_name_entry'
        registry = self.inventory()[2]
        text = project.canonical_dispatch_text(registry)
        self.assertEqual(text, project.canonical_dispatch_text(registry))
        self.assertIn('claw_custom_name_entry', text)
        self.assertNotIn('claw_example_entry', text)

    def test_app_alias_preserves_legacy_and_registers_admitted_wrapper_once(self):
        wrapper = self.root / 'Sources/ExampleOwner.cpp'
        wrapper.write_text('// alias only\n#define claw_example_entry claw_native_menu_example_entry\n#include "Example.cpp"\n')
        with patch.dict(project.APP_CANONICAL_ALIASES,
                        {'example': ('Example', 'ExampleOwner', 'example')}, clear=True):
            selected, registry = project.app_canonical_aliases(
                {'Sources/Example.cpp', 'Sources/Legacy.cpp', 'Sources/ExampleOwner.cpp'},
                [{'family': 'example', 'entry': 'claw_example_entry', 'address': 0x401000}])
            self.assertEqual(selected, {'Sources/Legacy.cpp', 'Sources/ExampleOwner.cpp'})
            self.assertEqual(registry[0]['entry'], 'claw_native_menu_example_entry')
            self.assertEqual(registry[0]['address'], 0x401000)
            self.assertIn('claw_native_menu_example_entry', project.canonical_dispatch_text([
                dict(registry[0], convention='cdecl', argc=0, returns='u32')]))
            with self.assertRaisesRegex(ValueError, 'requires admitted source'):
                project.app_canonical_aliases(set(), registry)
            wrapper.write_text(wrapper.read_text() + 'int changed_behavior;\n')
            with self.assertRaisesRegex(ValueError, 'only rename and include'):
                project.app_canonical_aliases({'Sources/Example.cpp'}, [
                    {'family': 'example', 'entry': 'claw_example_entry'}])

    def test_generated_dispatch_runs_c_abi_checks_and_preserves_outbound_envelope(self):
        clang = shutil.which('clang')
        if not clang:
            self.skipTest('clang unavailable')
        registry = self.inventory()[2]
        (self.root / project.DISPATCH_PATH).write_text(project.canonical_dispatch_text(registry))
        source = self.root / 'dispatch.c'
        source.write_text(r'''
#include "ClawCanonicalDispatch.h"
#include <assert.h>
#include <string.h>
static int calls;
static uint32_t expectedFrame;
static uint32_t outward(void *user, const ClawCall *c) {
    assert(c->receiver2 == 73 && c->stackPointer == 91);
    assert(c->x87ArgumentCount == 1 && c->x87Argument == 2.5);
    assert(c->argumentCount == 1 && c->arguments[0] == 55);
    return 42;
}
uint32_t claw_example_entry(uint32_t fn, uint32_t receiver, const uint32_t *args,
    uint32_t argc, ClawHost *host, uint32_t *result) {
    ClawCall outbound = {0};
    calls++;
    assert(host->entryStackPointer == expectedFrame);
    assert(fn == 0x401000 && receiver == 0 && argc == 1 && args[0] == 55);
    outbound.receiver2 = 73; outbound.stackPointer = 91;
    outbound.x87ArgumentCount = 1; outbound.x87Argument = 2.5;
    outbound.argumentCount = argc; outbound.arguments[0] = args[0];
    *result = host->call(host->user, &outbound);
    return 1;
}
int main(void) {
    ClawHost host = {0}; ClawCall call = {0}; uint32_t result = 99;
    host.call = outward;
    assert(claw_canonical_entry_count() == 1);
    assert(claw_canonical_lookup(0x401000)->argumentCount == 1);
    assert(!claw_canonical_lookup(0x402000));
    call.function = 0x401000; call.argumentCount = 1; call.arguments[0] = 55;
    assert(claw_canonical_dispatch(&call, &host, &result) == 1 && result == 42 && calls == 1);
    for (int invalid = 0; invalid < 7; invalid++) {
        ClawCall bad = call; host.fault = 0; result = 99;
        if (invalid == 0) bad.argumentCount = 0;
        if (invalid == 1) bad.argumentCount = 17;
        if (invalid == 2) bad.receiver = 1;
        if (invalid == 3) bad.receiver2 = 1;
        if (invalid == 4) bad.stackPointer = 1;
        if (invalid == 5) bad.x87ArgumentCount = 1;
        if (invalid == 6) bad.function = 0x402000;
        assert(!claw_canonical_dispatch(&bad, &host, &result));
        assert(result == 99 && calls == 1 && host.faultAddress == bad.function);
        assert(host.fault == (invalid == 6 ? CLAW_CANONICAL_FAULT_UNKNOWN_ADDRESS : CLAW_FAULT_ABI));
    }
    host.fault = CLAW_FAULT_MEMORY; host.faultAddress = 123;
    assert(!claw_canonical_dispatch(&call, &host, &result));
    assert(host.fault == CLAW_FAULT_MEMORY && host.faultAddress == 123);
    host.fault = 0;
    assert(!claw_canonical_dispatch(NULL, &host, &result) && host.fault == CLAW_FAULT_ABI);
    host.fault = 0;
    assert(!claw_canonical_dispatch(&call, &host, NULL) && host.fault == CLAW_FAULT_ABI);
    /* A number alone cannot authorize a non-default frame. */
    host.fault = 0; result = 99; call.stackPointer = CLAW_STACK_TOP - 64;
    assert(!claw_canonical_dispatch(&call, &host, &result) && result == 99 && calls == 1);
    host.fault = 0; host.entryStackPointer = call.stackPointer - 4;
    assert(!claw_canonical_dispatch(&call, &host, &result) && calls == 1);
    const uint32_t badFrames[] = {CLAW_STACK_BASE - 4, CLAW_STACK_TOP - 1,
                                  CLAW_STACK_END - 4, CLAW_STACK_END, 0xfffffffcu};
    for (unsigned i = 0; i < sizeof(badFrames)/sizeof(badFrames[0]); ++i) {
        host.fault = 0; host.entryStackPointer = call.stackPointer = badFrames[i];
        assert(!claw_canonical_dispatch(&call, &host, &result));
        assert(result == 99 && calls == 1 && host.fault == CLAW_FAULT_ABI);
    }
    /* The owner has prepared a valid frame. The dispatcher transports it. */
    host.fault = 0;
    expectedFrame = host.entryStackPointer = call.stackPointer = CLAW_STACK_BASE;
    assert(claw_canonical_dispatch(&call, &host, &result) && result == 42 && calls == 2);
    expectedFrame = host.entryStackPointer = call.stackPointer = CLAW_STACK_END - 8;
    assert(claw_canonical_dispatch(&call, &host, &result) && calls == 3);
    host.fault = 0; result = 99; call.stackPointer = 0;
    assert(!claw_canonical_dispatch(&call, &host, &result) && result == 99 && calls == 3);
    host.fault = 0; expectedFrame = host.entryStackPointer = CLAW_STACK_TOP;
    assert(claw_canonical_dispatch(&call, &host, &result) && calls == 4);
    return 0;
}
''')
        executable = self.root / 'dispatch'
        subprocess.run([clang, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-I', str(self.root / 'Sources'), str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
        subprocess.run([clang, '-x', 'c++', '-std=c++17', '-fsyntax-only', '-I',
                        str(self.root / 'Sources'), str(source)], check=True)


class ProjectRewriteTests(unittest.TestCase):
    def test_deterministic_rewrite_preserves_nonmembership_bytes(self):
        original = project.PROJECT.read_text()
        # Add an unrelated source entry to the phase: generator must retain it.
        lines = original.splitlines(keepends=True)
        first, _ = project.phase_files_range(lines)
        extra = '\t\t\t\tAAAAAAAAAAAAAAAAAAAAAAAA /* external source */,\n'
        lines.insert(first, extra)
        original = ''.join(lines)
        compiled = ['App/ClawApp.swift', 'Sources/Example.cpp']
        headers = [project.RUNTIME_PATH]
        rewritten = project.rewrite_project(original, compiled, headers)
        self.assertEqual(rewritten, project.rewrite_project(rewritten, compiled, headers))
        self.assertIn(extra, rewritten)
        self.assertEqual(project.compiled_paths_in_project(rewritten), set(compiled))
        self.assertEqual(project.referenced_paths_in_project(rewritten), set(compiled + headers))
        # Removing all generator-owned membership from both files produces
        # byte-identical projects, including resources and build settings.
        self.assertEqual(project.rewrite_project(original, [], []),
                         project.rewrite_project(rewritten, [], []))


if __name__ == '__main__':
    unittest.main()
