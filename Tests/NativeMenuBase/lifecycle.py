"""Recovered menu teardown and resource-failure comparisons on the joined host."""
import json
from Tests.NativeMenuBase import trace as reference
from Tests.NativeMenuBase.native_join import NativeJoin, WORK, physical_events, heap_digest


def snapshot(host):
    return dict(menu=host.machine.mem_read(host.menu,0x2c8).hex(),
                active_menu=host.word(0x537b58),allocations=host.allocations.copy(),
                live_heap=heap_digest(host),
                physical_references={hex(k):v['references'] for k,v in host.com_objects.items()},
                services=physical_events(host))


def exercise(host):
    host.frame_count=1
    NativeJoin.execute(host)
    return cleanup(host)


def cleanup(host):
    before=snapshot(host)
    host.run(0x45b050,host.menu,phase='menu-cleanup')
    after=snapshot(host)
    if after['active_menu']:
        raise reference.Blocked('Recovered menu cleanup left the active menu published')
    if len(after['allocations'])>=len(before['allocations']):
        raise reference.Blocked('Recovered menu cleanup released no allocations')
    if any(actor in host.allocations for actor in host.menu_sparkles):
        raise reference.Blocked('Recovered menu cleanup retained a sparkle actor')
    host.run(0x45b050,host.menu,phase='menu-cleanup-repeat')
    repeated=snapshot(host)
    return dict(before=before,after=after,repeated=repeated)


def compare(library,entries):
    report=dict(status='blocked')
    original=reference.MenuTrace();native=NativeJoin(library,entries,frame_count=1)
    try:
        expected=exercise(original)
        (WORK/'lifecycle-original.json').write_text(json.dumps(expected,indent=2)+'\n')
        actual=exercise(native)
        (WORK/'lifecycle-native.json').write_text(json.dumps(actual,indent=2)+'\n')
        report['comparisons']={k:expected[k]==actual[k] for k in expected}
        if not all(report['comparisons'].values()):
            raise reference.Blocked('Recovered menu cleanup mismatch')
        report['status']='compared'
    except Exception as error:
        report.update(error=str(error),native_calls=list(native.native_calls),
                      original_recent=[hex(x) for x in original.recent],
                      original_transfer=original.last_transfer,original_stop=original.stop,
                      original_functions={hex(k):v for k,v in original.functions.items()
                                          if 'menu-cleanup' in original.phases.get(k,set())})
    finally:
        native.close()
        for stream in original.files.values():stream.close()
    (WORK/'lifecycle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_calls','original_recent','original_functions')}))
    return 0 if report['status']=='compared' else 2


def controls(library,entries):
    results={}
    for name,owner,service in [('missing-actor-removal',0x4c92f0,None),
                                ('missing-map-iteration',None,0x4f5e1e),
                                ('missing-list-release',None,0x4f5172)]:
        host=NativeJoin(library,entries,frame_count=0)
        try:
            host.execute()
            host.deny_owner=owner;host.deny_platform=service
            try:
                host.run(0x45b050,host.menu,phase=name)
            except reference.Blocked as error:
                if 'deliberately withheld' not in str(error):raise
                results[name]=str(error)
            else:
                raise reference.Blocked(f'{name} incorrectly completed menu cleanup')
        finally:
            host.close()
    return results
