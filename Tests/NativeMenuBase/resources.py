"""A real failed archive open, its game retry owner, and game destruction."""
from Tests.NativeMenuBase import trace as reference
from Tests.NativeMenuBase.native_join import NativeJoin, physical_events


def exercise(host):
    archive=host.allocate(0x48)
    path=host.cstring(b'CLAW.REZ')
    host.run(0x4b7210,archive,phase='missing-archive-construction')
    before=host.allocations.copy()
    result=host.run(0x4b72e0,archive,(path,1,0),phase='missing-archive-open')
    if result or host.word(archive+8) or host.word(archive+0xc) or host.word(archive+0x24):
        raise reference.Blocked('Missing archive unexpectedly opened')
    if not host.word(archive+0x44):
        raise reference.Blocked('Failed-open archive path ownership was not exercised')
    failed=host.machine.mem_read(archive,0x48).hex()
    host.run(0x4b7250,archive,phase='missing-archive-destruction')
    after=host.allocations.copy()
    if before!=after or host.files or host.word(archive+0x44):
        raise reference.Blocked('Recovered failed-archive destructor leaked its path/file')
    return dict(result=result,failed=failed,destroyed=host.machine.mem_read(archive,0x48).hex(),
                allocations=after,services=physical_events(host))


def compare(library,entries):
    original=reference.MenuTrace(missing_resource=True)
    native=NativeJoin(library,entries,missing_resource=True,frame_count=0)
    try:
        expected=exercise(original);actual=exercise(native)
        if expected!=actual:
            raise reference.Blocked('Failed archive native/original state, services or cleanup mismatch')
        if native.native_counts[0x42a680]!=1:
            raise reference.Blocked('Failed archive did not reach its admitted retry owner')
        return dict(status='compared',retry_owner='0x42a680',destructor='0x4b7250',
                    allocated_path_released=True,state_and_services=True)
    finally:
        native.close()
        for stream in original.files.values():stream.close()
