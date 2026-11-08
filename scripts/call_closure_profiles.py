"""Version-qualified call closure for the app's mixed v1.3 composition.

Admission, address correspondence and production routing are separate evidence.
Candidate binary matches never prove either execution or non-execution. Adapter
probes compile the production adapters, replacing recovered destinations with
nonexecuting recorders, and then use the ordinary production transport probe.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from call_closure_shapes import SourceShapes, integer

ADAPTERS = ('Sources/V13EnemyLifecycleAdapter.cpp', 'Sources/V13CheatNativeAdapter.cpp',
            'Sources/V13ContactAdapter.cpp', 'Sources/V13ProfilesAdapter.cpp')


def adapter_probe(root, digest, heavy_lock, wait_load):
    """Observe entry election and outgoing remapping without executing game code."""
    harness = r'''
#include "ClawRuntime.h"
#include "V13Contact.h"
#include "V13Profiles.h"
#include <cstdio>
#include <map>
#include <array>
#include <cstring>
extern "C" uint32_t claw_v13_enemy_lifecycle_compat_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
extern "C" uint32_t claw_v13_cheat_native_entry(uint32_t,uint32_t,const uint32_t*,uint32_t,ClawHost*,uint32_t*);
static uint32_t entered, destination, deliveredCount, deliveredReceiver, local, injection, firstArgument, count, receiver;
static uint32_t requestedEntry, callbackFault;
static std::map<uint32_t,std::array<uint8_t,4096>> pages;
static uint8_t *bytes(void *,uint32_t a,uint32_t n) {
    if (n>4096-(a&4095)) return nullptr;
    return pages[a&~4095u].data()+(a&4095);
}
static uint32_t parent(void *,const ClawCall *q) {
    destination=q->function;deliveredCount=q->argumentCount;deliveredReceiver=q->receiver;return 0;
}
static uint32_t record(uint32_t f,ClawHost *h,uint32_t *out) {
    if (!entered) {
        entered=f;
        if (injection) {
            ClawCall q{};q.function=injection;q.receiver=receiver;q.argumentCount=count;
            q.arguments[0]=firstArgument;
            h->call(h->user,&q);
            callbackFault |= h->fault;
        }
    } else {destination=f;local=1;}
    *out=0;return 1;
}
#define STUB(name) extern "C" uint32_t name(uint32_t f,uint32_t,const uint32_t*,uint32_t,ClawHost *h,uint32_t *o) {return record(f,h,o);}
STUB(claw_cut_throat_entry)
STUB(claw_v13_enemy_lifecycle_entry)
STUB(claw_v13_raw_lifecycle_entry)
STUB(claw_level_one_claw_states_01_entry)
STUB(claw_v13_enemy_death_compat_entry)
STUB(claw_level_one_player_actions_02_entry)
STUB(claw_level_one_player_actions_03_entry)
STUB(claw_v13_cheat_pegs_entry)
STUB(claw_v13_profiles_entry)
STUB(claw_v13_contact_entry)
extern "C" uint32_t claw_v13_contact_dispatch_entry(uint32_t f,uint32_t r,const uint32_t *a,uint32_t n,ClawHost *h,uint32_t *o) {
    if(requestedEntry==0x4d7860) {
        ClawCall q{};q.function=requestedEntry;q.receiver=r;q.argumentCount=n;
        std::memcpy(q.arguments,a,n*4);h->call(h->user,&q);*o=0;return 1;
    }
    return record(f,h,o);
}
extern "C" uint32_t claw_collision_response_helper(uint32_t f,const ClawCollisionWorld *,ClawCollisionActor *,uint32_t,uint32_t,uint32_t) {
    destination=f;local=2;return 0;
}
extern "C" uint32_t claw_world_point_attribute(const uint32_t *,const uint32_t *,int32_t,int32_t,uint32_t,uint32_t,const ClawTileDescription *,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t) {
    destination=0x421ad0;local=2;return 0;
}
extern "C" uint32_t claw_tile_attribute(const ClawTileDescription *,int32_t,int32_t) {destination=0x72000000;local=2;return 0;}
extern "C" uint32_t claw_collision_move_with_resolver(const ClawCollisionWorld *,ClawCollisionActor *,uint32_t,uint32_t,uint32_t,ClawCollisionResolver,void *) {return 0;}
int main() {
    uint32_t adapter, f;
    while(std::scanf("%u %u %u %u %u %u",&adapter,&f,&injection,&receiver,&count,&firstArgument)==6) {
        pages.clear();entered=destination=deliveredCount=deliveredReceiver=local=callbackFault=0;
        ClawHost h{};h.bytes=bytes;h.call=parent;
        uint32_t a[4]={0x61000000,0,0,0},out=0;
        requestedEntry=f;
        uint32_t ok=0;
        if(adapter==0)ok=claw_v13_enemy_lifecycle_compat_entry(f,0,a,1,&h,&out);
        else if(adapter==1)ok=claw_v13_cheat_native_entry(f,0,a,1,&h,&out);
        else if(adapter==2) {
            uint32_t cells[1]{},rows[1]{};ClawTileDescription descriptions[1]{};
            ClawCollisionWorld world{};world.cells=cells;world.rowOffsets=rows;
            world.width=world.height=1;world.descriptions=descriptions;world.descriptionCount=1;
            ClawV13ContactActor actor{};actor.actor.token=0x61000000;
            claw_v13_collision_resolve(&world,4,&actor,1,0,0,0,0,nullptr,nullptr,&h.fault);
            ok=entered!=0;
        } else if(adapter==3) {claw_v13_profile_close_result(f==0x425a40);ok=entered!=0;}
        std::printf("{\"accepted\":%u,\"entered\":%u,\"destination\":%u,\"argc\":%u,\"receiver\":%u,\"local\":%u,\"fault\":%u}\n",
                    ok,entered,destination,deliveredCount,deliveredReceiver,local,h.fault|callbackFault);
    }
}
'''
    inputs = {p: digest(root/p) for p in (*ADAPTERS, 'Sources/ClawRuntime.h', 'Sources/ClawRuntime.hpp',
        'Sources/V13Contact.h','Sources/V13Profiles.h','Sources/CollisionResponse.h',
        'Sources/TileCollision.h','Sources/PlayerEngine.h','Sources/ClawGuestTransfer.h')}
    key = hashlib.sha256((json.dumps(inputs,sort_keys=True)+harness).encode()).hexdigest()[:24]
    folder = root/'work/build/call-closure-profiles'/key
    folder.mkdir(parents=True,exist_ok=True)
    binary = folder/'probe'
    if not binary.exists():
        with heavy_lock():
            if not binary.exists():
                wait_load()
                (folder/'probe.cpp').write_text(harness)
                subprocess.run(['xcrun','clang++','-std=c++17','-O1','-I'+str(root/'Sources'),
                    str(folder/'probe.cpp'),*[str(root/p) for p in ADAPTERS],'-o',str(binary)],check=True)
    return binary, inputs


def run_adapter(binary, queries):
    if not queries:return []
    data=''.join(' '.join(str(q[k]) for k in ('adapter','app_entry','target','receiver','argc','argument0'))+'\n' for q in queries)
    process=subprocess.run([str(binary)],input=data,text=True,capture_output=True,check=True,
        env={**os.environ,'CLAW_GAME_VERSION':'1.3','CLAW_LIVES_BOSS_PROFILE':'claw-v1.3'})
    answers=[json.loads(line) for line in process.stdout.splitlines()]
    if len(answers)!=len(queries):raise ValueError('Profile adapter probe lost a request')
    return answers


def production_routes(root, binary, inputs, inventory, owners):
    text=(root/ADAPTERS[0]).read_text()
    table=text.split('constexpr Route routes[] = {',1)[1].split('};',1)[0]
    routes=[]
    for row in re.findall(r'\{([^{}]+)\}',table):
        values=[int(v.strip(),16) for v in row.split(',')]
        if len(values)!=6:raise ValueError('Lifecycle route schema changed')
        old,new,old_ctor,new_ctor,old_table,size=values
        routes.append(dict(adapter=0,app_entry=old,original_entry=new,allocation_size=size,
            constructor=dict(original=new_ctor,app=old_ctor),source=ADAPTERS[0]))
    # These are explicit composition entrances, not inferred binary matches.
    # Each expected address is checked against compiled production selection.
    for old,new in ((0x49d330,0x4a0f30),(0x49d620,0x4a1230),(0x49d860,0x4a1430),(0x49e4e0,0x4a2080)):
        routes.append(dict(adapter=1,app_entry=old,original_entry=new,source=ADAPTERS[1]))
    for address in (0x4cc920,0x4d7860):
        routes.append(dict(adapter=2,app_entry=address,original_entry=address,source=ADAPTERS[2],
            native_entrance='claw_v13_collision_resolve',caller_source='Sources/ClawCollision.swift',
            caller_witness='let entry = split ? claw_v13_collision_move : claw_v13_collision_resolve'))
    for address in (0x425a20,0x425a40):
        routes.append(dict(adapter=3,app_entry=address,original_entry=address,source=ADAPTERS[3],
            native_entrance='claw_v13_profile_close_result',caller_source='Sources/ClawNativeMenuInterface.swift',
            caller_witness='claw_v13_profile_close_result(cancelled ? 1:0)'))
    queries=[dict(r,target=0,receiver=0,argc=0,argument0=0) for r in routes]
    for route,answer in zip(routes,run_adapter(binary,queries)):
        if not answer['accepted'] or answer['fault'] or answer['entered']!=route['original_entry']:
            raise ValueError(f'Production v1.3 entrance changed: {route}')
        declared=owners.get(('claw-v1.3',route['original_entry']))
        entry=inventory.get(route['app_entry']) if route['adapter']<2 else None
        expected='claw_v13_enemy_lifecycle_compat_entry' if route['adapter']==0 else 'claw_v13_cheat_native_entry'
        if not declared or (route['adapter']<2 and (not entry or entry['entry']!=expected)):
            raise ValueError(f'Profile entrance has no admitted owner/dispatch election: {route}')
        if route.get('caller_source'):
            if route['caller_witness'] not in (root/route['caller_source']).read_text():
                raise ValueError(f'Native profile caller changed: {route}')
            inputs[route['caller_source']]=hashlib.sha256((root/route['caller_source']).read_bytes()).hexdigest()
        route.update(owner=declared[0]['id'],dispatch=entry,entrance_probe=answer,
                     source_sha256=inputs[route['source']])
    if not routes:raise ValueError('Empty production profile adapter inventory')
    return routes


def regression_tests(root, binary, routes, inventory, owners, inputs, transport_binary):
    """Exercise wrong allocation contracts, unmapped entries and stale elections."""
    queries=[];expected=[]
    for route in routes:
        if route['adapter']!=0:continue
        for target,argc,argument,forward,fault in (
            (0x4fcaea,1,route['allocation_size'],0x4f63ec,False),
            (0x4fcaea,0,route['allocation_size'],0,True),
            (0x4fcaea,1,route['allocation_size']+4,0,True),
            (route['constructor']['original'],1,0,route['constructor']['app'],False),
            (0x4def40,1,0,0x4dc870,False),
            (0x4ce9b0,0,0,0x4ce9b0,False)):
            queries.append(dict(route,target=target,receiver=0x61000000,argc=argc,argument0=argument))
            expected.append((forward,fault))
    for adapter in (0,1):
        queries.append(dict(adapter=adapter,app_entry=0, target=0,receiver=0,argc=0,argument0=0))
        expected.append((0,False))
    # The isolated contact owner must fail closed on an unknown callback.
    queries.append(dict(adapter=2,app_entry=0x4cc920,target=0x70000001,receiver=0,argc=0,argument0=0))
    expected.append((0,True))
    answers=run_adapter(binary,queries)
    for query,answer,(target,fault) in zip(queries,answers,expected):
        if answer['destination']!=target or bool(answer['fault'])!=fault:
            raise ValueError(f'Profile adapter malformed-input regression: {query}, {answer}')
        if not query['app_entry'] and (answer['accepted'] or answer['entered']):
            raise ValueError('Unmapped profile entrance was accepted')
    # A stale registry cannot be replaced with an admitted family or a same-
    # valued address in the other binary's namespace.
    missing=dict(inventory);missing.pop(routes[0]['app_entry'])
    try:production_routes(root,binary,dict(inputs),missing,owners)
    except ValueError:pass
    else:raise ValueError('Missing production dispatch election was accepted')
    missing=dict(owners);missing.pop(('claw-v1.3',routes[0]['original_entry']))
    try:production_routes(root,binary,dict(inputs),inventory,missing)
    except ValueError:pass
    else:raise ValueError('Missing version-qualified owner was accepted')
    transport=[]
    for route in routes:
        if route['adapter']!=0:continue
        target=route['constructor']['app'];entry=inventory.get(target)
        if not entry:raise ValueError('Retained constructor disappeared from app registry')
        transport.append(dict(caller=route['app_entry'],target=target,receiver=0x61000000,argc=entry['argc']+1))
    malformed=json.loads(subprocess.run([str(transport_binary)],input=json.dumps(transport),text=True,
        capture_output=True,check=True,env={**os.environ,'CLAW_GAME_VERSION':'1.3'}).stdout)
    if len(malformed)!=len(transport) or any(a['outcome']!='refused' for a in malformed):
        raise ValueError('Malformed mapped constructor call reached transport')
    return dict(status='pass',adapter_controls=len(queries),missing_elections_rejected=2,
        malformed_transport_rejected=len(malformed),
        contract='Recorder destinations, allocation and isolated-contact refusals, stale election rejection and production transport argument-count refusal. No recovered game body executes.')


def audit(root, graph, inventory, owners, transport_binary, digest, heavy_lock, wait_load):
    adapter_binary,inputs=adapter_probe(root,digest,heavy_lock,wait_load)
    inputs['Sources/ClawCanonicalDispatch.h']=digest(root/'Sources/ClawCanonicalDispatch.h')
    inputs['scripts/call_closure_profiles.py']=digest(Path(__file__))
    routes=production_routes(root,adapter_binary,inputs,inventory,owners)
    by_original={r['original_entry']:r for r in routes}
    readers={};rows=[];pending=[];queries=[]
    prepared={}
    for edge in graph.edges:
        declared=owners.get(('claw-v1.3',edge['caller']))
        if not declared:continue
        manifest,owned=declared;family=manifest['id']
        if family not in readers:readers[family]=SourceShapes(root,manifest,import_slots=graph.program.imports)
        ins=next(graph.decoder.disasm(graph.bytes(edge['site'],15),edge['site'],count=1))
        prepared[(edge['caller'],edge['site'],edge['target'])]=(ins,readers[family].edge(edge,owned,ins.size))
    # Admitted local calls keep the same host adapter. Derive this closure from
    # the emitted caller, never from all addresses merely sharing a family.
    changed=True
    while changed:
        changed=False
        for edge in graph.edges:
            if edge['caller'] not in by_original or edge['target'] in by_original:continue
            item=prepared.get((edge['caller'],edge['site'],edge['target']))
            if not item or not item[1] or not item[1][0].get('local'):continue
            declared=owners.get(('claw-v1.3',edge['target']))
            if not declared:continue
            parent=by_original[edge['caller']]
            by_original[edge['target']]=dict(parent,original_entry=edge['target'],owner=declared[0]['id'],
                local_parent=edge['caller'],local_evidence=item[1][1])
            changed=True
    mapping=[]
    for (program,address),(manifest,owned) in sorted(owners.items()):
        if program!='claw-v1.3':continue
        path=f'Tests/families/{manifest["id"]}.json'
        inputs[path]=digest(root/path)
        for p in manifest['sources']:inputs[p]=digest(root/p)
        route=by_original.get(address)
        mapping.append(dict(original_entry=address,owner=manifest['id'],contract=owned,
            production_route=route,execution_status='production-adapter' if route else 'composition-unresolved'))
    for edge in graph.edges:
        row=dict(edge,outcome='profile-adapter-unresolved')
        declared=owners.get(('claw-v1.3',edge['caller']))
        if not declared:
            row['execution_status']='unknown'
            rows.append(row);continue
        manifest,owned=declared;family=manifest['id']
        row['admitted_owner']=family
        if family not in readers:readers[family]=SourceShapes(root,manifest,import_slots=graph.program.imports)
        ins,proof=prepared[(edge['caller'],edge['site'],edge['target'])]
        row['original_site']=dict(edge,profile=graph.program.name,sha256=graph.program.sha256,
            size=ins.size,bytes_sha256=hashlib.sha256(ins.bytes).hexdigest())
        if proof:
            row['caller_shape'],row['shape_evidence']=proof
            row['shape_status']='proved'
        else:row['shape_status']='unresolved'
        route=by_original.get(edge['caller'])
        if not route:
            row['execution_status']='composition-unresolved'
            rows.append(row);continue
        row['profile_mapping']=route;row['execution_status']='production-adapter'
        if not proof:
            row['outcome']='call-shape-unresolved';rows.append(row);continue
        shape=row['caller_shape']
        if shape.get('local'):
            row['outcome']='served-local';rows.append(row);continue
        row['outcome']='profile-transport-unresolved'
        for variant in shape.get('variants',[shape]):
            if any(variant.get(k) for k in ('source','compiler','tail','x87','x87_scalar','direct_entry')):
                continue  # Preserve the obligation; this recorder models ordinary calls only.
            expressions=variant.get('argument_expressions',[])
            first=integer(expressions[0]) if expressions else 0
            query=dict(route,target=edge['target'],receiver=variant.get('receiver',0),
                       argc=variant['argc'],argument0=first if first is not None else 0x61001000)
            pending.append((row,variant,query));queries.append(query)
        rows.append(row)
    transport=[];transport_pending=[]
    for (row,shape,query),answer in zip(pending,run_adapter(adapter_binary,queries)):
        observation=dict(request=query,answer=answer)
        row.setdefault('adapter_probes',[]).append(observation)
        if not answer['accepted'] or answer['fault'] or not answer['destination']:
            observation['outcome']='adapter-refused';continue
        if answer['local']==2:
            observation['outcome']='native-adapter-transport-only'
            continue
        if answer['local']:
            observation['outcome']='adapter-local' if ('claw-v1.3',answer['destination']) in owners else 'adapter-owner-unresolved'
            continue
        if answer['destination']==query['target']:
            # The two binaries reuse numeric addresses. A forwarding fallback
            # does not establish a counterpart even if the old ABI accepts it.
            observation['outcome']='profile-target-mapping-unresolved'
            continue
        mapped=dict(shape,caller=query['app_entry'],target=answer['destination'],
                    receiver=answer['receiver'],argc=answer['argc'],site=row['site'])
        transport.append(mapped);transport_pending.append(observation)
    if transport:
        answers=json.loads(subprocess.run([str(transport_binary)],input=json.dumps(transport),text=True,
            capture_output=True,check=True,env={**os.environ,'CLAW_GAME_VERSION':'1.3'}).stdout)
        if len(answers)!=len(transport):raise ValueError('Profile transport probe lost a request')
        for observation,query,answer in zip(transport_pending,transport,answers):
            observation['transport_probe']=dict(request=query,answer=answer)
            observation['outcome']=answer['outcome']
    for row in rows:
        probes=row.get('adapter_probes',[])
        if not probes:continue
        variants=row['caller_shape'].get('variants',[row['caller_shape']])
        outcomes={p['outcome'] for p in probes}
        if len(probes)!=len(variants):row['outcome']='profile-transport-unresolved'
        elif outcomes=={'adapter-local'}:row['outcome']='transport-only'  # Admission is not adapter execution proof.
        elif 'adapter-refused' in outcomes or 'refused' in outcomes:row['outcome']='transport-refused'
        elif outcomes<={'transport-only','provider-unresolved','native-adapter-transport-only'}:
            row['outcome']='provider-unresolved' if 'provider-unresolved' in outcomes else 'transport-only'
    # A candidate table is not proof of a live receiver. Keep every row and
    # attach only version-qualified ownership; numeric equality is insufficient.
    for table,words in graph.tables.items():
        for slot,target in enumerate(words):
            owner=owners.get(('claw-v1.3',target))
            rows.append(dict(caller=0,site=table+slot*4,target=target,kind='vtable-candidate',table=table,
                admitted_owner=owner[0]['id'] if owner else None,profile_mapping=by_original.get(target),
                outcome='receiver-provenance-unresolved'))
    unresolved=[dict(caller=r['caller'],site=r['site'],target=r['target'],execution_status=r['execution_status'])
                for r in rows if r['outcome']=='profile-adapter-unresolved']
    active_failures=[dict(caller=r['caller'],site=r['site'],target=r['target'],outcome=r['outcome'])
        for r in rows if r.get('execution_status')=='production-adapter'
        and r['outcome'] not in ('transport-only','provider-unresolved','served-local')]
    proof=dict(mapping=mapping,production_routes=routes,source_inputs=inputs,
        admitted_families=len({m['owner'] for m in mapping}),admitted_entries=len(mapping),
        production_families=len({m['owner'] for m in mapping if m['production_route']}),
        production_entries=len(routes),local_entries=len(by_original)-len(routes),
        adapter_probe_count=len(pending),transport_probe_count=len(transport),
        execution_unresolved=unresolved,active_failures=active_failures,
        completion_obligation_met=not unresolved and not active_failures,
        excluded_functions=[],
        contract='Compiled production adapter entrance and outgoing address/count/receiver routing with zero-filled memory fixtures and nonexecuting recovered entries. Ordinary mapped requests use the production level transport with CLAW_GAME_VERSION=1.3. No adapter memory/value or semantic equivalence proof; admission alone does not establish composition. No function is excluded for lacking a mapping.',
        prerequisite='plan-v13-semantic-closure: verified correspondences and composition coverage for the remaining original functions; candidate matches cannot establish non-execution.')
    proof['regressions']=regression_tests(root,adapter_binary,routes,inventory,owners,inputs,transport_binary)
    if len(rows)!=len(graph.edges)+sum(len(words) for words in graph.tables.values()):
        raise ValueError('Profile adapter audit lost original direct edges or receiver rows')
    proof['regressions']['retained_direct_edges']=len(graph.edges)
    proof['regressions']['retained_receiver_rows']=sum(len(words) for words in graph.tables.values())
    for path,expected in inputs.items():
        if digest(root/path)!=expected:raise ValueError(f'Profile input changed during audit: {path}; rerun the focused check')
    return rows,proof
