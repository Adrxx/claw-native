"""Prior-state menu-entry branches required by the batch join contract."""
import json
from Tests.NativeMenuBase import trace as reference
from Tests.NativeMenuBase.native_join import NativeJoin, WORK, physical_events, heap_digest


def exercise(host):
    host.frame_count=0
    NativeJoin.execute(host)
    host.clock_step=100
    rows=[]
    for previous in range(2,14):
        start=len(physical_events(host))
        result=host.run(0x45b3f0,host.menu,(previous,),phase=f'prior-state-{previous}')
        rows.append(dict(previous=previous,result=result,heap=heap_digest(host),
                         state=host.machine.mem_read(host.menu,0x2c8).hex(),
                         services=physical_events(host)[start:]))
    return rows


def setup_paper_startup(host, application):
    """The original startup objects absent from the default menu profile."""
    # Startup calls 0x4ebf80 at 0x426075, initializes at 0x426090 and
    # publishes app+0x44. Menu base initialization snapshots that field.
    fader = host.allocate(0x28)
    host.run(0x4ebf80, fader, phase='paper-fader-construction')
    if host.run(0x4ec010, fader, (0, 0, 0), phase='paper-fader-initialization') != 1:
        raise reference.Blocked('Paper startup fader initialization failed')
    host.put(application + 0x44, fader)
    # Original startup 0x426474/0x426489 constructs and enables the light
    # palette manager. The CLT is loaded by its real game loader on demand.
    palette = host.allocate(0x18)
    host.run(0x4c61d0, palette, phase='paper-palette-construction')
    if host.run(0x4c6260, palette, phase='paper-palette-initialization') != 1:
        raise reference.Blocked('Paper startup palette initialization failed')
    host.put(application + 0x58, palette)


def prepare_positive(host):
    """Publish authentic startup objects before menu initialization snapshots them."""
    setup_resources = host.setup_resources
    def resources(application, scene):
        setup_resources(application, scene)
        setup_paper_startup(host, application)
    host.setup_resources = resources
    host.frame_count = 0
    host.clock_step = 100
    try:
        NativeJoin.execute(host)
    finally:
        host.setup_resources = setup_resources
    host.clock_step = 100


def exercise_positive(host):
    """Real uncached initializer, then cached paper roll and alternate delay."""
    start = len(physical_events(host))
    prepare_positive(host)
    fader = host.word(host.application + 0x44)
    if host.word(host.menu + 0x10) != fader:
        raise reference.Blocked('Paper menu did not snapshot its startup fader')
    rows = []
    host.paper_reachability = {}

    def record(profile, phase, result, service_start, required):
        paper = host.word(host.menu + 0x40)
        table = host.word(host.application + 0x8c)
        if (result != 1 or not paper or not table or host.word(host.menu + 0x3c)
                or host.word(fader + 0x18)):
            raise reference.Blocked(f'Paper {profile} did not load, complete and clean up')
        if not isinstance(host, NativeJoin):
            reached = {address for address, phases in host.phases.items() if phase in phases}
            if not required <= reached:
                raise reference.Blocked(f'Paper {profile} missed original descendants: {sorted(required-reached)}')
            host.paper_reachability[profile] = [hex(address) for address in sorted(reached)]
        rows.append(dict(profile=profile, result=result, heap=heap_digest(host),
                         state=host.machine.mem_read(host.menu, 0x2c8).hex(),
                         paper=hex(paper), table=hex(table), capture_cleaned=True,
                         effect_count=host.word(fader + 0x18), milliseconds=host.milliseconds,
                         services=physical_events(host)[service_start:]))

    phase = 'menu-construction-and-initialization'
    initialized = [row for row in host.phase_results if row['phase'] == phase and row['entry'] == '0x428c40']
    if len(initialized) != 1:
        raise reference.Blocked('Paper positive initializer did not return exactly once')
    common = {0x42a4f0, 0x4ec050, 0x4ee9a0, 0x4ec600, 0x4ee8e0}
    record('initialization-uncached', phase, initialized[0]['result'], start,
           common | {0x45dc90, 0x4bc520, 0x4c7360, 0x4c7730, 0x4c7850, 0x4ec9c0, 0x4eecc0})
    for profile, bypass in (('cached', 0), ('alternate-delay', 1)):
        phase = f'paper-positive-{profile}'
        host.put(0x537238, bypass)
        start = len(physical_events(host))
        result = host.run(0x48f500, host.menu, (700,), phase=phase)
        record(profile, phase, result, start, common | {0x48f500} |
               ({0x4b8960} if bypass else {0x4ec9c0, 0x4eecc0}))
    host.put(0x537238, 0)
    return rows


def positive_controls(library, entries):
    results = {}
    for name, owner, platform in (('missing-paper-owner', 0x48f500, None),
                                  ('missing-table-owner', 0x4c76f0, None),
                                  ('missing-memory-read', None, 0x4ff79f),
                                  ('missing-acos', None, 0x4f2400),
                                  ('missing-resource-archive', None, None)):
        probe = NativeJoin(library, entries, frame_count=0,
                           missing_resource=name == 'missing-resource-archive')
        try:
            probe.deny_owner, probe.deny_platform = owner, platform
            prepare_positive(probe)
            probe.run(0x48f500, probe.menu, (700,), phase=f'paper-control-{name}')
        except reference.Blocked as error:
            expected = ('Original archive open failed; resource root is unavailable'
                        if name == 'missing-resource-archive' else
                        f'deliberately withheld: {owner:#x}' if owner else 'deliberately withheld')
            if expected not in str(error):
                raise reference.Blocked(f'Paper {name} stopped at the wrong boundary: {error}') from error
            if platform and not probe.platform[platform]:
                raise reference.Blocked(f'Paper {name} did not reach its withheld physical service')
            if name == 'missing-resource-archive' and not any(event.get('missing') for event in probe.physical_events):
                raise reference.Blocked('Paper resource control did not withhold archive bytes')
            results[name] = dict(status='blocked-as-required', error=str(error))
        else:
            raise reference.Blocked(f'Paper {name} unexpectedly completed')
        finally:
            probe.close()
    return results


def compare(library,entries):
    original=reference.MenuTrace();native=NativeJoin(library,entries,frame_count=0)
    report=dict(status='blocked')
    try:
        expected=exercise(original)
        (WORK/'transitions-original.json').write_text(json.dumps(expected,indent=2)+'\n')
        actual=exercise(native)
        (WORK/'transitions-native.json').write_text(json.dumps(actual,indent=2)+'\n')
        checks={a['previous']:a==b for a,b in zip(expected,actual)}
        report['comparisons']=checks
        if not all(checks.values()):
            raise reference.Blocked('Menu prior-state branch comparison mismatch')
        native.close()
        for stream in original.files.values():stream.close()
        # Three full-size paper animations exceed the idle-menu instruction
        # budget. Reuse the bounded budget of the original positive profile.
        original=reference.MenuTrace(instruction_limit=220_000_000)
        native=NativeJoin(library,entries,frame_count=0)
        expected=exercise_positive(original)
        (WORK/'transitions-positive-original.json').write_text(json.dumps(expected,indent=2)+'\n')
        report['original_positive_reachability']=original.paper_reachability
        report['original_positive_instructions']=original.instructions
        actual=exercise_positive(native)
        (WORK/'transitions-positive-native.json').write_text(json.dumps(actual,indent=2)+'\n')
        checks={a['profile']:a==b for a,b in zip(expected,actual)}
        report['positive_comparisons']=checks
        if not all(checks.values()):
            raise reference.Blocked('Menu positive paper transition comparison mismatch')
        report['positive_controls']=positive_controls(library,entries)
        report['status']='compared'
    except Exception as error:
        report.update(error=str(error),native_calls=list(native.native_calls),
                      original_transfer=original.last_transfer,original_stop=original.stop,
                      original_functions={hex(k):sorted(v) for k,v in original.phases.items()
                                          if any(p.startswith(('prior-state-', 'paper-')) for p in v)})
    finally:
        native.close()
        for stream in original.files.values():stream.close()
    (WORK/'transitions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ('native_calls','original_functions','original_positive_reachability')}))
    return 0 if report['status']=='compared' else 2
