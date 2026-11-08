"""Synthetic content and tampering controls for bounded static milestone capture."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.claw import milestone as m


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class StaticMilestoneTests(unittest.TestCase):
    version = 1

    def setUp(self):
        self.spec = m.static_spec(self.version)
        maximum_registrations=max(row[5] for row in self.spec["counts"].values()) if self.version>=5 else 0
        self.check_id = m.STATIC_CHECKS[self.version-1]
        self.reference = self.spec['reference']
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / ('work/milestone/attempt/'+self.check_id)
        self.directory.mkdir(parents=True)
        source = self.root / 'Sources/test.swift'
        source.parent.mkdir(); source.write_text('synthetic input')
        frozen = self.root / Path(self.reference).parent
        frozen.mkdir(parents=True)
        producer = frozen / 'producer.py'; producer.write_text('independent producer')
        self.provenance = dict(schema=self.spec['schema'], status='PASS',
            programSha256=m.ORIGINAL_SHA256,
            producerHashes={str(producer) if self.version >= 5 else str(producer.relative_to(self.root)):m.digest(producer)}, profiles=[])
        page = bytearray(4096); page[24:28] = (0x503722).to_bytes(4,'little'); page = bytes(page); ph = hashlib.sha256(page).hexdigest()
        region = dict(name='image', address=0x522000, size=4096, sha256=ph)
        cpu=dict.fromkeys(('eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead'),0)
        sections=[dict(address=4096,depth=0,owner=0,initialized=True)]
        allocations=[dict(address=8192,requested=1,capacity=1,identity=1,live=True)]
        reference_state = dict(cpu=cpu, sections=sections, allocations=allocations, memory=dict(parent=None,pageChanges=[[0x522000,0]],ranges=[region]))
        reference = dict(pages=[dict(bytes=page.hex(),sha256=ph)],states=[reference_state])
        if self.version >= 4:
            later = copy.deepcopy(reference_state);later['memory'].update(parent=0,pageChanges=[])
            reference['states'].append(later)
            reference['entries']=[dict(function=1,returnPC=2,before=0,after=0),dict(function=0x4dbb10,returnPC=3,before=0,after=1)]
            reference['inlineFsTransitions']=[dict(address=0x4dbba5,instruction=0x4dbb9e,state=1,order=1,effect='publish-inline-FS')]
        if self.version >= 5:
            callbacks=[0x510000+i for i in range(maximum_registrations)]
            heap_page=bytearray(4096)
            for i,callback in enumerate(callbacks):heap_page[i*4:i*4+4]=callback.to_bytes(4,'little')
            heap_page=bytes(heap_page);heap_hash=hashlib.sha256(heap_page).hexdigest()
            pages=[dict(bytes=page.hex(),sha256=ph),dict(bytes=heap_page.hex(),sha256=heap_hash)]
            reference.update(pages=pages,states=[],completedRegistrations=callbacks,mode='moving')
            for count in range(maximum_registrations+1):
                gp=bytearray(4096);gp[0xfd4:0xfd8]=(0x62000000).to_bytes(4,'little');gp[0xfd0:0xfd4]=(0x62000000+4*count).to_bytes(4,'little')
                gh=hashlib.sha256(gp).hexdigest();pages.append(dict(bytes=gp.hex(),sha256=gh))
                state=copy.deepcopy(reference_state);state.update(registryBase=0x62000000,registryNext=0x62000000+4*count)
                state['memory'].update(parent=count-1 if count else None,pageChanges=[[0x545000,count+2]] if count else [[0x522000,0],[0x62000000,1],[0x545000,2]],ranges=[region,dict(name='globals',address=0x545000,size=4096,sha256=gh),dict(name='heap',address=0x62000000,size=4096,sha256=heap_hash)])
                reference['states'].append(state)
            last=copy.deepcopy(reference['states'][-1]);last['memory'].update(parent=maximum_registrations,pageChanges=[]);reference['states'].append(last)
            reference['inlineFsTransitions'][0].update(state=maximum_registrations+1,order=maximum_registrations+1)
        if self.version>=6:
            reference.update(schema=self.spec['schema'],events=[])
            for state in reference['states']:
                state.update(globalHandles=[],localAllocations=[],tlsIndices=[],tlsValues={},nextGlobalHandle=0x78000000,nextTlsIndex=0,lastError=0,sectionHistory=[])
        if self.version==8:
            for state in reference['states']:state.update(namedMessages=[],nextNamedMessage=0xc000,namedMessageHistory=[])
        self.extra_native_inputs={}
        self.references={}
        for name in self.spec['counts']:
            current=copy.deepcopy(reference)
            if self.version >= 5:
                count=self.spec['counts'][name][5];current['entries'][0].update(before=count,after=count)
                current['completedRegistrations']=current['completedRegistrations'][:count]
            if self.version>=7:
                mode4=name==('list133-string-range-zero-original-mode4' if self.version==8 else 'string-range-malloc-zero-original-mode4')
                current['declaredCallerInputs']=dict(diagnosticMode4=mode4,ebpAnchor=mode4)
            self.references[name]=current
            raw = json.dumps(current).encode()
            shard = frozen / (name+'.json.gz'); shard.write_bytes(gzip.compress(raw))
            self.provenance['profiles'].append(dict(name=name, path=shard.name, sha256=m.digest(shard),
                logicalSha256=hashlib.sha256(raw).hexdigest(), bytes=shard.stat().st_size))
        if self.version==7:
            historical={}
            for name in m.STATIC_EXTENDED_ARCHIVED_PRODUCERS:
                archived=self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/name;archived.parent.mkdir(parents=True,exist_ok=True);archived.write_text('historical original '+name)
                historical[name]=m.digest(archived)
                current=self.root/name;current.parent.mkdir(parents=True,exist_ok=True);current.write_text('current native '+name)
                self.extra_native_inputs[name]=m.digest(current)
                self.extra_native_inputs[str(Path(m.STATIC_EXTENDED_ARCHIVE_ROOT)/name)]=m.digest(archived)
            self.provenance['producerHashes'].update(historical)
            patch.object(m,'STATIC_EXTENDED_ARCHIVED_PRODUCERS',historical).start()
            manifest=dict(schema_version=1,archived_inputs=[dict(source_path=name,archive_path=m.STATIC_EXTENDED_ARCHIVE_ROOT+'/'+name,sha256=value,bytes=(self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/name).stat().st_size) for name,value in historical.items()],current_inputs=[dict(path=name,sha256=self.extra_native_inputs[name],bytes=(self.root/name).stat().st_size)for name in historical])
            write(self.root/m.STATIC_EXTENDED_ARCHIVE_MANIFEST,manifest)
            manifest_hash=m.digest(self.root/m.STATIC_EXTENDED_ARCHIVE_MANIFEST)
            self.extra_native_inputs[m.STATIC_EXTENDED_ARCHIVE_MANIFEST]=manifest_hash
            patch.object(m,'STATIC_EXTENDED_ARCHIVE_SHA256',manifest_hash).start()
        if self.version==8:
            inventory={};supplemental={};producers={}
            for index in range(84):
                name=('producer/' if index<74 else 'supplemental/')+str(index)+'.py'
                archived=frozen/'inputs'/name;archived.parent.mkdir(parents=True,exist_ok=True);archived.write_text('historical '+str(index))
                row=dict(path='inputs/'+name,sha256=m.digest(archived))
                if index<74:inventory[name]=row;producers[name]=row['sha256']
                else:supplemental[name]=row
            write(self.root/m.STATIC_LIST_SUPPLEMENTAL,supplemental)
            patch.object(m,'STATIC_LIST_SUPPLEMENTAL_SHA256',m.digest(self.root/m.STATIC_LIST_SUPPLEMENTAL)).start()
            self.provenance.update(producerHashes=producers,frozenInputInventory=inventory,liveInputsChangedAfterLoad=[])
            self.extra_native_inputs.update(m.static_list_archived_producers(self.provenance,self.root))
            for name in ('Tests/clawparity/env.py','Tests/clawparity/kernel.py','tools/claw/milestone.py'):
                path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('native input '+name)
                self.extra_native_inputs[name]=m.digest(path)
        write(self.root / self.reference, self.provenance)
        self.addCleanup(patch.stopall)
        patch.object(m,('STATIC_REFERENCE_SHA256','STATIC_THREE_REFERENCE_SHA256','STATIC_SEVEN_REFERENCE_SHA256','STATIC_FIFTEEN_REFERENCE_SHA256','STATIC_THIRTYFOUR_REFERENCE_SHA256','STATIC_APPLICATION_REFERENCE_SHA256','STATIC_EXTENDED_REFERENCE_SHA256','STATIC_LIST_REFERENCE_SHA256')[self.version-1],m.digest(self.root/self.reference)).start()
        if self.version == 5:
            interpretation=self.root/m.STATIC_THIRTYFOUR_INTERPRETATION
            write(interpretation,dict(schema='claw-original-static-row-interpretation-v1',programSha256=m.ORIGINAL_SHA256,provenanceSha256=m.static_spec(5)['digest']))
            patch.object(m,'STATIC_THIRTYFOUR_INTERPRETATION_SHA256',m.digest(interpretation)).start()
        self.spec = m.static_spec(self.version)
        self.payload = dict(status='pass', command=self.spec['command'], modes=[])
        identities, scope_identities = {}, {}
        for mode in ('sanitized','optimized'):
            asan = mode == 'sanitized'
            build = dict(inputs={'Sources/test.swift':m.digest(source),**self.extra_native_inputs}, registry=hashlib.sha256(b'registry').hexdigest(),
                cflags=['-fsanitize=address,undefined'] if asan else ['-O2'],
                sflags=['-sanitize=address'] if asan else ['-O'], original=m.ORIGINAL_SHA256,
                reference_provenance=self.spec['digest'])
            key = hashlib.sha256(json.dumps(build,sort_keys=True).encode()).hexdigest()
            cache = self.root/'work/native-static-startup-cache'/key
            write(cache/'certificate.json',build)
            (cache/'check').write_bytes(b'compiled binary')
            (cache/'binary.sha256').write_text(m.digest(cache/'check'))
            (cache/'ClawCanonicalDispatch.h').write_bytes(b'registry')
            snap = cache/'snapshot/Sources/test.swift';snap.parent.mkdir(parents=True);snap.write_bytes(source.read_bytes())
            for name in self.extra_native_inputs:
                target=cache/'snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((self.root/name).read_bytes())
            report = dict(status='pass',command='native-static-startup', sanitized=asan,optimized=not asan,
                checks=self.spec['checks'],reference_version=self.version,certificate=str(cache/'certificate.json'),native_table_walker=True,gameplay=False,
                report_path=str(self.directory/(self.spec['report_prefix']+mode+'-report.json')),profiles=[],authority_controls=[])
            for name, action in [(n,'') for n in self.spec['counts']] + [(self.spec['seed'],a) for a in self.spec['controls']]:
                counts = self.spec['counts'][name] if not action else self.spec['control_counts'][action]
                row = dict(status='pass',command='native-static-startup',profile=name,authority_control=action,
                    native_table_walker=True,gameplay=False,**dict(zip(self.spec['count_fields'],counts)))
                count = self.spec['states']-25*(len(self.spec['counts'])+len(self.spec['controls'])-1) if action == self.spec['controls'][-1] else 25
                states = [dict(cpu=copy.deepcopy(cpu),sections=copy.deepcopy(sections),allocations=copy.deepcopy(allocations),function=1,returnPC=2,returning=False,
                    completed=False,physical=False,referenceState=0,memory=dict(parent=i-1 if i else None,
                    pageChanges=[[0x522000,0]] if not i else [],ranges=[region])) for i in range(count)]
                artifact_pages = [dict(bytes=page.hex(),sha256=ph)]
                if self.version >= 5:
                    reference_id=row['registrations'];original_state=self.references[name]['states'][reference_id]
                    global_page=self.references[name]['pages'][reference_id+2]
                    artifact_pages.extend([global_page,self.references[name]['pages'][1]])
                    for index,state in enumerate(states):
                        state['referenceState']=reference_id
                        state['memory'].update(ranges=copy.deepcopy(original_state['memory']['ranges']),pageChanges=[[0x522000,0],[0x545000,1],[0x62000000,2]] if not index else [])

                if self.version>=6:
                    for state in states:
                        for field in ('globalHandles','localAllocations','tlsIndices','tlsValues','nextGlobalHandle','nextTlsIndex','lastError','sectionHistory')+(('namedMessages','nextNamedMessage','namedMessageHistory') if self.version==8 else ()):
                            state[field]=copy.deepcopy(original_state[field])
                    row['missing_native_dependency']=None
                    if self.version>=7:row['declared_caller_inputs']=copy.deepcopy(self.references[name]['declaredCallerInputs'])
                if action.endswith('-table'):
                    mutated = bytearray(page);mutated[24:28]=(0x503748).to_bytes(4,'little')
                    mutated_hash = hashlib.sha256(mutated).hexdigest()
                    artifact_pages.append(dict(bytes=mutated.hex(),sha256=mutated_hash))
                    states[-1].update(function=0x50372c,returnPC=0x503727,returning=action.startswith('return'),
                        authorityMutation=dict(m.STATIC_TABLE_MUTATION))
                    states[-1]['memory']['pageChanges']=[[0x522000,len(artifact_pages)-1]]
                    states[-1]['memory']['ranges']=[dict(region,sha256=mutated_hash)]+states[-1]['memory']['ranges'][1:]
                if self.version >= 4:
                    scope=m.static_scope_inventory(self.references[name],dict(states=states));row.update(scope)
                    scope_identities[action or name]=m.stable_hash(scope)
                identities[action or name] = m.stable_hash([[s[k] for k in ('function','returnPC','returning','completed','physical','referenceState')] for s in states])
                artifact = cache/(('authority-'+action if action else 'golden-'+name)+'.native.json')
                write(artifact,dict(schema='claw-native-static-startup-pages-v1',profile=name,result=copy.deepcopy(row),
                    pages=artifact_pages,states=states))
                row.update(native_artifact=str(artifact),native_artifact_sha256=m.digest(artifact))
                if not action:
                    row['reference_sha256']=next(r['sha256'] for r in self.provenance['profiles'] if r['name']==name)
                report['authority_controls' if action else 'profiles'].append(row)
            write(Path(report['report_path']),report)
            self.payload['modes'].append(report)
        patch.object(m,('STATIC_STATE_IDENTITIES','STATIC_THREE_STATE_IDENTITIES','STATIC_SEVEN_STATE_IDENTITIES','STATIC_FIFTEEN_STATE_IDENTITIES','STATIC_THIRTYFOUR_STATE_IDENTITIES','STATIC_APPLICATION_STATE_IDENTITIES','STATIC_EXTENDED_STATE_IDENTITIES','STATIC_LIST_STATE_IDENTITIES')[self.version-1],identities).start()
        if self.version >= 4: patch.object(m,'STATIC_LIST_SCOPE_IDENTITIES' if self.version==8 else 'STATIC_EXTENDED_SCOPE_IDENTITIES' if self.version==7 else 'STATIC_APPLICATION_SCOPE_IDENTITIES' if self.version==6 else 'STATIC_THIRTYFOUR_SCOPE_IDENTITIES' if self.version == 5 else 'STATIC_FIFTEEN_SCOPE_IDENTITIES',scope_identities).start()

    def capture(self):
        return m.static_evidence(self.payload,self.directory,self.root,capture=True)

    def test_capture_and_resume_all_durable_evidence(self):
        evidence = self.capture()
        self.assertEqual(evidence,m.static_evidence(self.payload,self.directory,self.root))
        self.assertEqual(2*(len(self.spec['counts'])+len(self.spec['controls'])),len([n for n in evidence if n.endswith('.native.json')]))
        self.assertIn(self.check_id,m.select_checks([self.check_id]))
        self.assertIn(self.spec['command'],m.command_for(self.check_id)[-1])

    def test_generic_pass_and_counter_change_rejected(self):
        with self.assertRaises(ValueError):m.validate_certificate(self.check_id,dict(status='pass'))
        malformed=copy.deepcopy(self.payload);malformed['modes']=['pass','pass']
        with self.assertRaises(ValueError):m.validate_static_certificate(malformed)
        self.payload['modes'][0]['profiles'][0]['wrappers']+=1
        with self.assertRaisesRegex(ValueError,'counters'):self.capture()

    def test_frozen_reference_and_producer_tampering_rejected(self):
        name = self.provenance['profiles'][0]['path']
        (self.root/Path(self.reference).parent/name).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'shard'):self.capture()

    def test_producer_tampering_rejected(self):
        name=next(iter(self.provenance['producerHashes']))
        (self.root/name).write_text('changed producer')
        with self.assertRaisesRegex(ValueError,'producer'):self.capture()

    def test_artifacts_valid_rechecks_retained_contents(self):
        evidence=self.capture()
        write(self.directory/'result.json',self.payload)
        (self.directory/'stdout.log').write_text(json.dumps(self.payload)+'\n')
        (self.directory/'stderr.log').write_text('')
        check=dict(id=self.check_id,status='verified',exit_code=0,certificate=self.payload,
            evidence=evidence,artifacts={name:m.digest(self.directory/(name+('.json' if name=='result' else '.log')))
                for name in ('stdout','stderr','result')})
        self.assertTrue(m.artifacts_valid(check,self.directory.parent))
        (self.directory/'sanitized/native-check').write_bytes(b'changed binary')
        self.assertFalse(m.artifacts_valid(check,self.directory.parent))

    def test_current_compiled_input_change_rejected(self):
        (self.root/'Sources/test.swift').write_text('changed')
        with self.assertRaisesRegex(ValueError,'current compiled input'):self.capture()

    def test_report_not_equal_to_certificate_rejected(self):
        path = Path(self.payload['modes'][0]['report_path']);write(path,dict(status='pass'))
        with self.assertRaisesRegex(ValueError,'publisher report'):self.capture()

    def test_artifact_rehashed_with_false_cpu_rejected(self):
        row=self.payload['modes'][0]['profiles'][0]; path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());artifact['states'][0]['cpu']['eax']=1;write(path,artifact)
        row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'state comparison'):self.capture()

    def test_rehashed_boolean_aliases_rejected(self):
        mutations = (
            ('CPU', lambda a: a['states'][0]['cpu'].__setitem__('eax', False)),
            ('allocation number', lambda a: a['states'][0]['allocations'][0].__setitem__('identity', True)),
            ('allocation flag', lambda a: a['states'][0]['allocations'][0].__setitem__('live', 1)),
            ('section number', lambda a: a['states'][0]['sections'][0].__setitem__('owner', False)),
            ('section flag', lambda a: a['states'][0]['sections'][0].__setitem__('initialized', 1)),
            ('parent', lambda a: a['states'][1]['memory'].__setitem__('parent', False)),
        )
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        original=json.loads(path.read_text())
        for name, mutate in mutations:
            with self.subTest(field=name):
                artifact=copy.deepcopy(original);mutate(artifact);write(path,artifact)
                row['native_artifact_sha256']=m.digest(path)
                write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
                with self.assertRaisesRegex(ValueError,'schema|parent'):self.capture()

    def test_rehashed_page_content_rejected(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());artifact['pages'][0]['bytes']='ff'*4096;write(path,artifact)
        row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'page hash'):self.capture()

    def test_captured_reference_binary_and_snapshot_tampering_rejected(self):
        evidence=self.capture()
        for name in ('sanitized/native-check','sanitized/snapshot/Sources/test.swift',
                     'references/'+self.reference,'sanitized/report.json'):
            with self.subTest(name=name):
                path=self.directory/name;old=path.read_bytes();path.write_bytes(b'tampered')
                try:
                    with self.assertRaises((ValueError,KeyError)):m.static_evidence(self.payload,self.directory,self.root)
                finally:path.write_bytes(old)
        self.assertEqual(evidence,m.static_evidence(self.payload,self.directory,self.root))


class StaticThreeMilestoneTests(StaticMilestoneTests):
    version = 2

    def test_reference_version_and_check_identity_cannot_alias_v1(self):
        m.validate_certificate(self.check_id, self.payload)
        for check_id in m.STATIC_CHECKS:
            if check_id != self.check_id:
                with self.subTest(check_id=check_id), self.assertRaisesRegex(ValueError, 'identity'):
                    m.validate_certificate(check_id, self.payload)
        for version in (*[v for v in (1,2,3,4,5,6) if v != self.version], True, str(self.version), None):
            malformed = copy.deepcopy(self.payload)
            malformed['modes'][0]['reference_version'] = version
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'reference version'):
                m.validate_certificate(self.check_id, malformed)

    def test_modes_profiles_and_authority_order_are_fixed(self):
        for key in ('modes', 'profiles', 'authority_controls'):
            malformed = copy.deepcopy(self.payload)
            rows = malformed[key] if key == 'modes' else malformed['modes'][0][key]
            rows.reverse()
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_certificate(self.check_id, malformed)

    def test_compiler_or_failure_boundary_identity_cannot_be_relabelled(self):
        row = self.payload['modes'][0]['profiles'][2]
        path = Path(row['native_artifact'])
        artifact = json.loads(path.read_text())
        artifact['states'][0]['function'] = 0x4a48c0
        write(path, artifact)
        row['native_artifact_sha256'] = m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']), self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError, 'observation identity'):
            self.capture()

    def test_fs_and_effect_ledger_comparison_survive_rehash(self):
        row = self.payload['modes'][0]['profiles'][3]
        path = Path(row['native_artifact'])
        original = json.loads(path.read_text())
        for field in ('fsHead', 'section'):
            artifact = copy.deepcopy(original)
            if field == 'fsHead':
                artifact['states'][0]['cpu']['fsHead'] = 0x20007ee0
            else:
                artifact['states'][0]['sections'][0]['initialized'] = False
            write(path, artifact)
            row['native_artifact_sha256'] = m.digest(path)
            write(Path(self.payload['modes'][0]['report_path']), self.payload['modes'][0])
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'state comparison'):
                self.capture()


class StaticSevenMilestoneTests(StaticThreeMilestoneTests):
    version = 3

    def test_table_control_mutation_is_exact_and_retained(self):
        self.capture()
        row = self.payload['modes'][0]['authority_controls'][-1]
        path = Path(row['native_artifact'])
        original = json.loads(path.read_text())
        mutations = (
            ('omitted', lambda a: a['states'][-1].pop('authorityMutation')),
            ('wrong slot', lambda a: a['states'][-1]['authorityMutation'].__setitem__('address',0x522014)),
            ('boolean alias', lambda a: a['states'][-1]['authorityMutation'].__setitem__('after',True)),
            ('wrong target', lambda a: a['states'][-1].__setitem__('function',0x503752)),
        )
        for label, mutate in mutations:
            artifact=copy.deepcopy(original);mutate(artifact);write(path,artifact)
            row['native_artifact_sha256']=m.digest(path)
            write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
            with self.subTest(label=label), self.assertRaisesRegex(ValueError,'authority mutation|observation identity'):
                self.capture()

    def test_table_mutation_cannot_change_an_extra_byte_or_be_repaired(self):
        row = self.payload['modes'][0]['authority_controls'][-2]
        path=Path(row['native_artifact']);original=json.loads(path.read_text())
        for repaired in (False, True):
            artifact=copy.deepcopy(original)
            pid=artifact['states'][-1]['memory']['pageChanges'][-1][1]
            page=bytearray.fromhex(artifact['pages'][pid]['bytes'])
            if repaired: page[24:28]=(0x503722).to_bytes(4,'little')
            else: page[40]=1
            ph=hashlib.sha256(page).hexdigest()
            artifact['pages'][pid]=dict(bytes=page.hex(),sha256=ph)
            artifact['states'][-1]['memory']['ranges'][0]['sha256']=ph
            write(path,artifact);row['native_artifact_sha256']=m.digest(path)
            write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
            with self.subTest(repaired=repaired), self.assertRaisesRegex(ValueError,'state comparison'):
                self.capture()

    def test_eighth_observation_cut_cannot_claim_completed_wrapper(self):
        malformed = copy.deepcopy(self.payload)
        row = malformed['modes'][0]['profiles'][-1]
        row['wrappers'] = 8
        row['honest_stops'] = 0
        with self.assertRaisesRegex(ValueError, 'counters'):
            m.validate_certificate(self.check_id, malformed)

    def test_v3_publisher_and_environment_are_explicit(self):
        command = m.command_for(self.check_id)
        self.assertIn('--v'+str(self.version), command[-1])
        self.assertNotIn('--v2', command[-1])
        environment = m.controlled_environment({'CLAW_NATIVE_STATIC_AUTHORITY':'entry-owner'}, self.directory, self.check_id)
        self.assertNotIn('CLAW_NATIVE_STATIC_AUTHORITY', environment)
        self.assertEqual(str(self.directory), environment['CLAW_NATIVE_STATIC_CHECK_DIR'])


class StaticFifteenMilestoneTests(StaticSevenMilestoneTests):
    version = 4

    def test_scope_cannot_claim_all_observed_or_omit_real_boundary(self):
        changes=(
            ('all entries observed','reference_only_entry_indices',[]),
            ('all states observed','reference_only_state_indices',[]),
            ('inline observed','reference_only_inline_fs_transitions',[]),
            ('real boundary omitted','observed_reference_boundaries',[]),
            ('wrong index','reference_only_entry_indices',[0]),
            ('boolean index','reference_only_entry_indices',[True]),
        )
        for label,field,value in changes:
            malformed=copy.deepcopy(self.payload);malformed['modes'][0]['profiles'][0][field]=value
            with self.subTest(label=label), self.assertRaisesRegex(ValueError,'scope identity'):
                m.validate_certificate(self.check_id,malformed)

    def test_scope_reconstruction_uses_real_artifact_not_report_projection(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text())
        artifact['states'][0].update(function=0x4dbb10,returnPC=3)
        with self.assertRaisesRegex(ValueError,'fabricated internal'):
            m.static_scope_inventory(dict(entries=[],states=[{}],inlineFsTransitions=[]),artifact)
        with self.assertRaisesRegex(ValueError,'fabricated inline'):
            m.static_scope_inventory(dict(entries=[],states=[{}],inlineFsTransitions=[dict(state=1)]),
                dict(states=[dict(function=1,returnPC=2,referenceState=1,returning=False)]))

    def test_suppressed_actual_capture_rejected_after_artifact_rehash(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());artifact['states'].pop()
        write(path,artifact);row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'observation identity'):
            self.capture()

    def test_scope_vectors_checked_against_immutable_original_after_rehash(self):
        for report in self.payload['modes']:
            row=report['profiles'][0];path=Path(row['native_artifact'])
            row['reference_only_entry_indices']=[0]
            artifact=json.loads(path.read_text());artifact['result']['reference_only_entry_indices']=[0]
            write(path,artifact);row['native_artifact_sha256']=m.digest(path)
            write(Path(report['report_path']),report)
        spec_hashes=copy.deepcopy(m.static_spec(self.version)['scope_identities'])
        spec_hashes[row['profile']]=m.stable_hash({field:row[field] for field in self.spec.get("scope_fields",m.STATIC_SCOPE_FIELDS)})
        with patch.object(m,'STATIC_LIST_SCOPE_IDENTITIES' if self.version==8 else 'STATIC_EXTENDED_SCOPE_IDENTITIES' if self.version==7 else 'STATIC_APPLICATION_SCOPE_IDENTITIES' if self.version==6 else 'STATIC_THIRTYFOUR_SCOPE_IDENTITIES' if self.version == 5 else 'STATIC_FIFTEEN_SCOPE_IDENTITIES',spec_hashes), self.assertRaisesRegex(ValueError,'scope reconstruction'):
            self.capture()

    def test_cut_and_allocation_failure_cannot_be_reported_completed(self):
        for profile in (('thirtyfifth-constructor-observational-prefix' if self.version == 5 else 'sixteenth-constructor-observational-prefix'),'range-allocation-failure-observational-prefix'):
            malformed=copy.deepcopy(self.payload)
            row=next(row for row in malformed['modes'][0]['profiles'] if row['profile']==profile)
            row['honest_stops']=0;row['wrappers']+=1
            with self.subTest(profile=profile), self.assertRaisesRegex(ValueError,'counters'):
                m.validate_certificate(self.check_id,malformed)


class StaticThirtyfourMilestoneTests(StaticFifteenMilestoneTests):
    version = 5

    def test_v5_absolute_producer_paths_normalize_and_reject_unsafe_aliases(self):
        original=self.provenance['producerHashes']
        absolute=next(iter(original));expected=original[absolute]
        relative=str(Path(absolute).relative_to(self.root))
        self.assertEqual({relative:expected},m.static_producer_hashes(self.provenance,self.root,5))
        # Old versions retain their original path policy, including rejection by their caller.
        self.assertEqual(original,m.static_producer_hashes(self.provenance,self.root,4))
        for name in ('/outside/repository/producer.py',str(self.root/'work/../producer.py'),'../producer.py'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError,'external|traversal'):
                m.static_producer_hashes(dict(producerHashes={name:expected}),self.root,5)
        link=self.root/'producer-link';link.symlink_to(Path(absolute).parent,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            m.static_producer_hashes(dict(producerHashes={str(link/'producer.py'):expected}),self.root,5)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            m.static_producer_hashes(dict(producerHashes={absolute:expected,relative:expected}),self.root,5)

    def test_registration_counters_keep_returned_wrappers_separate(self):
        for count in (34,True,0):
            malformed=copy.deepcopy(self.payload)
            row=next(row for row in malformed['modes'][0]['profiles'] if row['profile']=='registry-growth-first-realloc-failure')
            row['registrations']=count
            with self.subTest(count=count), self.assertRaisesRegex(ValueError,'counters'):
                m.validate_certificate(self.check_id,malformed)

    def test_corrected_interpretation_is_required_immutable_input(self):
        references=m.static_reference_inputs(self.root,5)
        self.assertEqual(m.STATIC_THIRTYFOUR_INTERPRETATION_SHA256,references[m.STATIC_THIRTYFOUR_INTERPRETATION])
        (self.root/m.STATIC_THIRTYFOUR_INTERPRETATION).write_text('{}')
        with self.assertRaisesRegex(ValueError,'interpretation'):
            self.capture()

    def test_registration_inventory_reads_actual_slots_including_retired_bytes(self):
        base=0x62000000;callbacks=[0x510000+i for i in range(32)]+[0x510021]
        gp=bytearray(4096);gp[0xfd4:0xfd8]=base.to_bytes(4,'little');gp[0xfd0:0xfd4]=(base+132).to_bytes(4,'little')
        heap=bytearray(4096)
        for i,callback in enumerate(callbacks):heap[i*4:i*4+4]=callback.to_bytes(4,'little')
        memory={0x545000:bytes(gp),base:bytes(heap)}
        original=dict(states=[dict(registryBase=base,registryNext=base+132)],completedRegistrations=callbacks)
        state=dict(referenceState=0,allocations=[dict(address=base,live=False)])
        self.assertEqual(callbacks,m.static_registration_inventory(dict(registrations=33),original,state,memory))
        with self.assertRaisesRegex(ValueError,'executed count'):
            m.static_registration_inventory(dict(registrations=34),original,state,memory)
        poisoned=bytearray(heap);poisoned[128:132]=(0x510020).to_bytes(4,'little')
        with self.assertRaisesRegex(ValueError,'callback vector'):
            m.static_registration_inventory(dict(registrations=33),original,state,dict(memory,**{})|{base:bytes(poisoned)})

    def test_rehashed_registration_counter_cannot_override_executed_memory(self):
        malformed=copy.deepcopy(self.payload)
        row=next(row for row in malformed['modes'][0]['profiles'] if row['profile']=='registry-growth-first-realloc-failure')
        self.assertEqual((34,33),(row['wrappers'],row['registrations']))
        path=Path(row['native_artifact']);artifact=json.loads(path.read_text())
        page=bytearray.fromhex(artifact['pages'][2]['bytes']);page[0]=1
        ph=hashlib.sha256(page).hexdigest();artifact['pages'][2]=dict(bytes=page.hex(),sha256=ph)
        for state in artifact['states']:state['memory']['ranges'][2]['sha256']=ph
        write(path,artifact);row['native_artifact_sha256']=m.digest(path)
        write(Path(malformed['modes'][0]['report_path']),malformed['modes'][0])
        with self.assertRaisesRegex(ValueError,'state comparison'):
            m.static_evidence(malformed,self.directory,self.root,capture=True)


if __name__ == '__main__':
    unittest.main()


class StaticApplicationMilestoneTests(StaticFifteenMilestoneTests):
    version=6

    def test_cut_and_allocation_failure_cannot_be_reported_completed(self):
        for name in ('joint59-observational-prefix','module-local-before-effect-stop','post-application-registry-growth-after-effect-stop'):
            malformed=copy.deepcopy(self.payload)
            row=next(row for row in malformed['modes'][0]['profiles'] if row['profile']==name)
            row['honest_stops']=0;row['wrappers']+=1
            with self.subTest(profile=name),self.assertRaisesRegex(ValueError,'counters'):
                m.validate_certificate(self.check_id,malformed)

    def test_registration_count_excludes_direct_jump_without_cleanup(self):
        malformed=copy.deepcopy(self.payload);malformed['modes'][0]['profiles'][0]['registrations']=58
        with self.assertRaisesRegex(ValueError,'counters'):m.validate_certificate(self.check_id,malformed)

    def test_rehashed_joint_metadata_cannot_override_reference(self):
        for field,value in (('tlsValues',{'0':1}),('nextGlobalHandle',0x78000004),('lastError',1),
                ('globalHandles',[dict(handle=0x78000000,data=0x62000000,size=256,flags=8194,locks=0)]),
                ('sectionHistory',[dict(operation='delete',address=4096,bytesPreserved=True)])):
            row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact']);saved=path.read_bytes()
            artifact=json.loads(saved);artifact['states'][0][field]=value
            write(path,artifact);row['native_artifact_sha256']=m.digest(path)
            write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'joint physical state'):self.capture()
            path.write_bytes(saved);row['native_artifact_sha256']=m.digest(path)
            write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])

    def test_joint_numeric_boolean_rejected(self):
        row=self.payload['modes'][0]['profiles'][0];artifact=json.loads(Path(row['native_artifact']).read_text())
        state=artifact['states'][0];expected=copy.deepcopy(state);state['nextTlsIndex']=False
        with self.assertRaisesRegex(ValueError,'TLS/counter schema'):m.validate_static_application_state(state,expected)

    def test_internal_empty_getter_cannot_be_invented(self):
        original=dict(schema=self.spec['schema'],states=[{}],events=[],inlineFsTransitions=[],entries=[
            dict(function=0x4f6433,returnPC=0x4f643f,before=0,after=0,observation='original-only-internal')])
        artifact=dict(states=[dict(function=0x4f6433,returnPC=0x4f643f,referenceState=0,returning=False,physical=False)])
        with self.assertRaisesRegex(ValueError,'owned internal callback'):m.static_scope_inventory(original,artifact)

    def test_unmatched_physical_prefix_report_is_rejected(self):
        row=self.payload['modes'][0]['profiles'][0];row['reference_only_physical_event_indices']=[0]
        with self.assertRaisesRegex(ValueError,'scope identity'):m.validate_certificate(self.check_id,self.payload)

    def test_rehashed_missing_dependency_claim_is_rejected(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());row['missing_native_dependency']=0x4f50fd
        artifact['result']['missing_native_dependency']=0x4f50fd
        write(path,artifact);row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'missing dependency classification'):self.capture()

    def test_owned_throw_helper_has_no_exported_receipt(self):
        original=dict(schema=self.spec['schema'],states=[{}],events=[],inlineFsTransitions=[],entries=[])
        artifact=dict(states=[dict(function=0x4a5690,returnPC=0x4f5126,referenceState=0,returning=False,physical=False)])
        with self.assertRaisesRegex(ValueError,'owned throw callback'):m.static_scope_inventory(original,artifact)


class StaticExtendedMilestoneTests(unittest.TestCase):
    version=7
    def setUp(self):
        self.spec=m.static_spec(self.version)
        if self._testMethodName in ('test_capture_and_resume_separate_version7_evidence',
                'test_foreign_version_report_rejected','test_direct_jumps_do_not_invent_registrations',
                'test_rehashed_diagnostic_input_policy_cannot_be_generalized'):
            StaticMilestoneTests.setUp(self)
    capture=StaticMilestoneTests.capture

    def test_capture_and_resume_separate_version7_evidence(self):
        evidence=self.capture()
        self.assertEqual(evidence,m.static_evidence(self.payload,self.directory,self.root))
        self.assertNotEqual(m.static_spec(6)['reference'],self.spec['reference'])
        self.assertIn('--v7',m.command_for('static_startup_extended')[-1])
        self.assertNotIn('--v7',m.command_for('static_startup_application')[-1])
        self.assertEqual(m.static_spec(),m.static_spec(1))

    def test_foreign_version_report_rejected(self):
        malformed=copy.deepcopy(self.payload);malformed['modes'][0]['reference_version']=6
        with self.assertRaises(ValueError):m.validate_certificate(self.check_id,malformed)

    def test_direct_jumps_do_not_invent_registrations(self):
        malformed=copy.deepcopy(self.payload);malformed['modes'][0]['profiles'][0]['registrations']=119
        with self.assertRaisesRegex(ValueError,'counters'):m.validate_certificate(self.check_id,malformed)

    def test_rehashed_diagnostic_input_policy_cannot_be_generalized(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());row['declared_caller_inputs']=dict(diagnosticMode4=True,ebpAnchor=True)
        artifact['result']['declared_caller_inputs']=copy.deepcopy(row['declared_caller_inputs'])
        write(path,artifact);row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'declared caller input policy'):self.capture()

    def test_caller_policy_requires_boolean_inputs(self):
        original=dict(declaredCallerInputs=dict(diagnosticMode4=False,ebpAnchor=False))
        row=dict(profile='extended119-clean',declared_caller_inputs=dict(diagnosticMode4=0,ebpAnchor=False))
        with self.assertRaisesRegex(ValueError,'declared caller input policy'):m.validate_static_extended_inputs(row,original)

    def test_exported_factory_base_edge_is_version_and_site_bounded(self):
        entry=dict(function=0x4db620,returnPC=0x4dc2a8,before=0,after=0)
        original=dict(schema=self.spec['schema'],states=[{}],entries=[entry],events=[])
        state=dict(function=0x4db620,returnPC=0x4dc2a8,referenceState=0,returning=False,physical=False)
        self.assertEqual(m.static_scope_inventory(original,dict(states=[state]))['reference_only_entry_indices'],[])
        state['returnPC']=0x4dbbb9
        with self.assertRaisesRegex(ValueError,'internal source callback'):m.static_scope_inventory(original,dict(states=[state]))
        state['returnPC']=0x4dc2a8;original['schema']=m.static_spec(6)['schema']
        with self.assertRaisesRegex(ValueError,'internal source callback'):m.static_scope_inventory(original,dict(states=[state]))

    def test_exported_array_base_edge_is_version_and_site_bounded(self):
        entry=dict(function=0x4dbb10,returnPC=0x440f63,before=0,after=0)
        original=dict(schema=self.spec['schema'],states=[{}],entries=[entry],events=[])
        state=dict(function=0x4dbb10,returnPC=0x440f63,referenceState=0,returning=False,physical=False)
        self.assertEqual(m.static_scope_inventory(original,dict(states=[state]))['reference_only_entry_indices'],[])
        state['returnPC']=0x403ae8
        with self.assertRaisesRegex(ValueError,'internal source callback'):m.static_scope_inventory(original,dict(states=[state]))
        state['returnPC']=0x440f63;original['schema']=m.static_spec(6)['schema']
        with self.assertRaisesRegex(ValueError,'internal source callback'):m.static_scope_inventory(original,dict(states=[state]))

    def test_owned_factory_helpers_and_stored_pointer_have_no_callback(self):
        original=dict(schema=self.spec['schema'],states=[{}],entries=[],events=[])
        for function in (0x4dc280,0x4dc200,0x4c96b0):
            state=dict(function=function,returnPC=0,referenceState=0,returning=False,physical=False)
            with self.subTest(function=function),self.assertRaisesRegex(ValueError,'owned factory callback'):
                m.static_scope_inventory(original,dict(states=[state]))


class StaticExtendedArchivedInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.addCleanup(patch.stopall)
        self.producers={};current=[];archived=[]
        for name in m.STATIC_EXTENDED_ARCHIVED_PRODUCERS:
            path=self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('historical '+name)
            value=m.digest(path);self.producers[name]=value
            archived.append(dict(source_path=name,archive_path=m.STATIC_EXTENDED_ARCHIVE_ROOT+'/'+name,sha256=value,bytes=path.stat().st_size))
            current.append(dict(path=name,sha256='0'*64,bytes=1))
        self.manifest=self.root/m.STATIC_EXTENDED_ARCHIVE_MANIFEST
        write(self.manifest,dict(schema_version=1,archived_inputs=archived,current_inputs=current))
        patch.object(m,'STATIC_EXTENDED_ARCHIVED_PRODUCERS',self.producers).start()
        patch.object(m,'STATIC_EXTENDED_ARCHIVE_SHA256',m.digest(self.manifest)).start()

    def test_fixed_mapping_keeps_current_source_namespace_separate(self):
        inputs=m.static_extended_archived_producers(self.producers,self.root)
        self.assertTrue(set(self.producers).isdisjoint(inputs))
        self.assertEqual(len(inputs),3)
        old=m.static_producer_hashes(dict(producerHashes=self.producers),self.root,6)
        self.assertEqual(old,self.producers)

    def test_archived_bytes_drift_rejected(self):
        path=self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/next(iter(self.producers));path.write_bytes(path.read_bytes()+b'drift')
        with self.assertRaisesRegex(ValueError,'fingerprint/path'):m.static_extended_archived_producers(self.producers,self.root)

    def test_manifest_hash_drift_rejected(self):
        self.manifest.write_bytes(self.manifest.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'fingerprint/path'):m.static_extended_archived_producers(self.producers,self.root)

    def test_rehashed_manifest_cannot_redirect_fixed_mapping(self):
        value=json.loads(self.manifest.read_text());value['archived_inputs'][0]['archive_path']='../../redirected'
        write(self.manifest,value)
        with patch.object(m,'STATIC_EXTENDED_ARCHIVE_SHA256',m.digest(self.manifest)):
            with self.assertRaisesRegex(ValueError,'manifest mapping'):m.static_extended_archived_producers(self.producers,self.root)

    def test_symlink_alias_rejected(self):
        path=self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/next(iter(self.producers));target=self.root/'other';target.write_bytes(path.read_bytes());path.unlink();path.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'fingerprint/path'):m.static_extended_archived_producers(self.producers,self.root)

    def test_retained_copy_survives_origin_drift(self):
        import shutil
        retained=self.root/'retained';shutil.copytree(self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT,retained/m.STATIC_EXTENDED_ARCHIVE_ROOT)
        path=self.root/m.STATIC_EXTENDED_ARCHIVE_ROOT/next(iter(self.producers));path.write_bytes(b'changed origin')
        self.assertEqual(len(m.static_extended_archived_producers(self.producers,retained)),3)


class StaticListPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.addCleanup(patch.stopall)
        self.base=Path(m.STATIC_LIST_REFERENCE).parent
        inventory={};producers={};supplemental={}
        for index in range(84):
            name=('producer/' if index<74 else 'supplemental/')+str(index)+'.py'
            path=self.root/self.base/'inputs'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('capture-time input '+str(index))
            row=dict(path='inputs/'+name,sha256=m.digest(path))
            if index<74:inventory[name]=row;producers[name]=row['sha256']
            else:supplemental[name]=row
        self.provenance=dict(producerHashes=producers,frozenInputInventory=inventory,liveInputsChangedAfterLoad=[])
        self.supplemental=self.root/m.STATIC_LIST_SUPPLEMENTAL
        write(self.supplemental,supplemental)
        patch.object(m,'STATIC_LIST_SUPPLEMENTAL_SHA256',m.digest(self.supplemental)).start()

    def test_version_eight_requires_explicit_selection(self):
        self.assertNotIn('static_startup_list',m.select_checks())
        self.assertEqual(m.select_checks(['static_startup_list']),['static_startup_list'])

    def test_capture_archive_survives_live_source_absence(self):
        result=m.static_producer_hashes(self.provenance,self.root,8)
        self.assertEqual(len(result),85)
        self.assertTrue(set(self.provenance['producerHashes']).isdisjoint(result))
        self.assertEqual(m.static_producer_hashes(self.provenance,self.root,6),self.provenance['producerHashes'])

    def test_archive_drift_and_symlinks_rejected(self):
        path=self.root/self.base/next(iter(self.provenance['frozenInputInventory'].values()))['path']
        raw=path.read_bytes();path.write_bytes(raw+b'drift')
        with self.assertRaisesRegex(ValueError,'archived input drift'):m.static_list_archived_producers(self.provenance,self.root)
        target=self.root/'target';target.write_bytes(raw);path.unlink();path.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'archived input drift'):m.static_list_archived_producers(self.provenance,self.root)

    def test_rehashed_mapping_cannot_redirect_or_omit_producer(self):
        for change in ('redirect','omit','hash'):
            value=copy.deepcopy(self.provenance);key=next(iter(value['frozenInputInventory']))
            if change=='redirect':value['frozenInputInventory'][key]['path']='inputs/../elsewhere'
            elif change=='omit':del value['frozenInputInventory'][key]
            else:value['producerHashes'][key]='0'*64
            with self.subTest(change=change),self.assertRaises(ValueError):m.static_list_archived_producers(value,self.root)

    def test_supplemental_hash_and_mapping_are_pinned(self):
        raw=self.supplemental.read_bytes();self.supplemental.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'archived input drift'):m.static_list_archived_producers(self.provenance,self.root)
        value=json.loads(raw);value[next(iter(value))]['path']='inputs/elsewhere';write(self.supplemental,value)
        with patch.object(m,'STATIC_LIST_SUPPLEMENTAL_SHA256',m.digest(self.supplemental)):
            with self.assertRaisesRegex(ValueError,'archived mapping'):m.static_list_archived_producers(self.provenance,self.root)

    def test_named_history_and_identifier_schema_are_independent(self):
        state=dict(namedMessages=[dict(nameHex='61',identifier=0xc000)],nextNamedMessage=0xc001,
            namedMessageHistory=[dict(nameHex='61',result=0xc000,reused=False,inserted=True,callerReturnPC=0x4f822d)])
        m.validate_static_list_state(state,copy.deepcopy(state))
        changed=copy.deepcopy(state);changed['namedMessageHistory'][0]['inserted']=False
        with self.assertRaisesRegex(ValueError,'state comparison'):m.validate_static_list_state(changed,state)
        for key,value in [('nextNamedMessage',True),('namedMessages',[dict(nameHex='6100',identifier=0xc000)]),
                ('namedMessageHistory',[dict(nameHex='61',result=0xc000,reused=True,inserted=True,callerReturnPC=0x4f822d)])]:
            malformed={**state,key:value}
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'schema'):m.validate_static_list_state(malformed,copy.deepcopy(malformed))

    def test_mode4_policy_is_explicit_and_profile_bounded(self):
        original=dict(schema='claw-original-static-startup-list-records-pages-v8',declaredCallerInputs=dict(diagnosticMode4=True,ebpAnchor=True))
        row=dict(profile='list133-string-range-zero-original-mode4',declared_caller_inputs=original['declaredCallerInputs'])
        m.validate_static_extended_inputs(row,original)
        row['profile']='list133-clean'
        with self.assertRaisesRegex(ValueError,'policy isolation'):m.validate_static_extended_inputs(row,original)

    def test_owned_scalar_and_thunk_child_have_no_native_receipt(self):
        original=dict(schema='claw-original-static-startup-list-records-pages-v8',states=[{}],entries=[],events=[])
        for function,pc in ((0x4fb15d,0x4a1400),(0x4f709b,0x50255a)):
            state=dict(function=function,returnPC=pc,referenceState=0,returning=False,physical=False)
            with self.subTest(function=function),self.assertRaisesRegex(ValueError,'owned list callback'):
                m.static_scope_inventory(original,dict(states=[state]))

    def test_exported_buffer_base_receipt_is_version_and_site_bounded(self):
        entry=dict(function=0x4f6a9a,returnPC=0x4f837a,before=0,after=0,observation='original-only-internal')
        original=dict(schema='claw-original-static-startup-list-records-pages-v8',states=[{}],entries=[entry],events=[])
        state=dict(function=entry['function'],returnPC=entry['returnPC'],referenceState=0,returning=False,physical=False)
        self.assertEqual(m.static_scope_inventory(original,dict(states=[state]))['reference_only_entry_indices'],[])
        original['schema']=m.static_spec(7)['schema']
        with self.assertRaisesRegex(ValueError,'owned internal callback'):m.static_scope_inventory(original,dict(states=[state]))


class StaticListMilestoneTests(unittest.TestCase):
    version=8
    setUp=StaticMilestoneTests.setUp
    capture=StaticMilestoneTests.capture

    def test_capture_and_resume_version8_archive_and_states(self):
        evidence=self.capture()
        self.assertEqual(evidence,m.static_evidence(self.payload,self.directory,self.root))
        self.assertIn('--v8',m.command_for('static_startup_list')[-1])
        self.assertNotIn('--v8',m.command_for('static_startup_extended')[-1])
        self.assertEqual(m.static_spec(),m.static_spec(1))
        archived=[name for name in evidence if '/frozen-v8/inputs/' in name and name.startswith('references/')]
        self.assertEqual(len(archived),84)

    def test_wrong_version_and_registration_count_rejected(self):
        for field,value in (('reference_version',7),('registrations',133)):
            payload=copy.deepcopy(self.payload)
            if field=='reference_version':payload['modes'][0][field]=value
            else:payload['modes'][0]['profiles'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.validate_certificate(self.check_id,payload)

    def test_rehashed_named_metadata_drift_rejected(self):
        row=self.payload['modes'][0]['profiles'][0];path=Path(row['native_artifact'])
        artifact=json.loads(path.read_text());artifact['states'][0]['nextNamedMessage']+=1
        write(path,artifact);row['native_artifact_sha256']=m.digest(path)
        write(Path(self.payload['modes'][0]['report_path']),self.payload['modes'][0])
        with self.assertRaisesRegex(ValueError,'named-message state comparison'):self.capture()

    def test_retained_archive_drift_rejected_after_origin_disappears(self):
        self.capture()
        archived=next(iter(self.provenance['frozenInputInventory'].values()))['path']
        origin=self.root/Path(self.reference).parent/archived;origin.unlink()
        m.static_evidence(self.payload,self.directory,self.root)
        retained=self.directory/'references'/Path(self.reference).parent/archived;retained.write_bytes(b'drift')
        with self.assertRaisesRegex(ValueError,'fingerprint|archived input drift'):m.static_evidence(self.payload,self.directory,self.root)


class StaticFinalPlatformPreparationTests(unittest.TestCase):
    def state(self):
        return dict(platformPolicyId=m.STATIC_FINAL_POLICY_SHA256,platformHistory=[],versionHistory=[],desktopDCAttempt=None,
            liveDesktopDCs=[],desktopDCHistory=[],borrowedIdentityTable={'brushes':{'15':0x7900100f,'6':0x79001006},'cursors':{'32514':0x7a007f02,'32512':0x7a007f00}},borrowedLookupHistory=[])

    def test_history_mismatch_cannot_be_hidden_by_page_equality(self):
        expected=self.state();actual=copy.deepcopy(expected)
        actual['platformHistory']=[dict(name='GetDC',returnPC=0x4fb3ed,arguments=[0],result=0x79000001)]
        with self.assertRaisesRegex(ValueError,'state comparison'):m.validate_static_final_state(actual,expected)

    def test_borrowed_identity_cannot_be_claimed_as_owned_dc(self):
        state=self.state();state['liveDesktopDCs']=[dict(handle=0x7900100f,kind='desktopDC',hwnd=0,acquireReturnPC=0x4fb3ed)]
        with self.assertRaisesRegex(ValueError,'DC lease schema'):m.validate_static_final_state(state,copy.deepcopy(state))

    def test_false_is_not_an_integer_history_result(self):
        state=self.state();state['versionHistory']=[dict(returnPC=0x502db7,result=False)]
        with self.assertRaisesRegex(ValueError,'version history schema'):m.validate_static_final_state(state,copy.deepcopy(state))

    def test_final_inputs_ignore_legacy_description_but_require_exact_new_policy(self):
        inputs=dict(version=10,processVersion=0x40000,scalarPolicy='distinct',dcPolicy='success',releasePolicy='success',borrowedPolicy='success',messagePolicy='success',messageInitial=None,capsPolicy=None,physicalStop=None)
        original=dict(schema='claw-original-static-startup-final-records-pages-v9',platformProfileInputs=inputs,declaredProfileInputs=copy.deepcopy(inputs),physicalPolicySha256=m.STATIC_FINAL_POLICY_SHA256,messageFailure=True)
        row=dict(declared_platform_inputs=copy.deepcopy(inputs),physical_policy_sha256=m.STATIC_FINAL_POLICY_SHA256)
        m.validate_static_final_inputs(row,original)
        row['declared_platform_inputs']['messagePolicy']='zero'
        with self.assertRaisesRegex(ValueError,'policy inputs'):m.validate_static_final_inputs(row,original)


class StaticFinalMilestoneTests(unittest.TestCase):
    def test_version9_is_explicit_and_older_defaults_remain(self):
        self.assertEqual(m.select_checks(['static_startup_final']), ['static_startup_final'])
        self.assertNotIn('static_startup_final', m.select_checks())
        self.assertNotIn('static_startup_list', m.select_checks())
        self.assertIn('--v9', m.command_for('static_startup_final')[-1])
        self.assertNotIn('--v9', m.command_for('static_startup_list')[-1])
        self.assertEqual(m.static_spec(), m.static_spec(1))
        self.assertEqual((len(m.static_spec(9)['counts']), len(m.static_spec(9)['controls'])), (26, 6))
        self.assertEqual((m.static_spec(9)['checks'], m.static_spec(9)['states']), (5774407, 60791))
        self.assertEqual(m.static_certificate_version({'command': 'static-startup-final'}), 9)

    def test_new_class_export_and_owned_helpers_have_distinct_scopes(self):
        entry=dict(function=0x4f709b,returnPC=0x503827,before=0,after=0)
        original=dict(schema=m.static_spec(9)['schema'],states=[{}],entries=[entry],events=[])
        state=dict(function=entry['function'],returnPC=entry['returnPC'],referenceState=0,returning=False,physical=False)
        self.assertEqual(m.static_scope_inventory(original,dict(states=[state]))['reference_only_entry_indices'], [])
        original['schema']=m.static_spec(8)['schema']
        with self.assertRaisesRegex(ValueError,'owned list callback'):
            m.static_scope_inventory(original,dict(states=[state]))
        original['schema']=m.static_spec(9)['schema']
        for function in (0x4fb3ba,0x4fb376,0x502d5a,0x502d8a,0x4dc3a0):
            with self.subTest(function=function),self.assertRaisesRegex(ValueError,'owned final helper'):
                m.static_scope_inventory(original,dict(states=[{**state,'function':function}]))

    def test_authoritative_selector_rejects_unknown_missing_and_declared_drift(self):
        inputs=dict(version=10,processVersion=0x40000,scalarPolicy='distinct',dcPolicy='success',releasePolicy='success',borrowedPolicy='success',messagePolicy='success',messageInitial=None,capsPolicy=None,physicalStop=None)
        for kind in ('unknown','missing','declared'):
            original=dict(schema=m.static_spec(9)['schema'],platformProfileInputs=copy.deepcopy(inputs),declaredProfileInputs=copy.deepcopy(inputs),physicalPolicySha256=m.STATIC_FINAL_POLICY_SHA256)
            if kind=='unknown':original['platformProfileInputs']['messageFailure']=True
            elif kind=='missing':del original['platformProfileInputs']['capsPolicy']
            else:original['declaredProfileInputs']['messagePolicy']='zero'
            row=dict(declared_platform_inputs=original['platformProfileInputs'],physical_policy_sha256=m.STATIC_FINAL_POLICY_SHA256)
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'authoritative policy inputs'):
                m.validate_static_final_inputs(row,original)
