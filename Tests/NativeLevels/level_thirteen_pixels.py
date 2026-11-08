"""Stop the native Level 13 join at its first retained presentation mismatch."""
import argparse
import hashlib
import json
from Tests.NativeLevels.level_thirteen_join import (Native, OUT, REFERENCE, LEVEL,
    shared, validate_independent, reference_controls)
from Tests.NativeLevels.storage import read_trace, fingerprint
from Tests.NativeLevels import output_dir
from Tests.NativeLevels.trace import Blocked


FIRST_BOUNDARY = ('level-13-jump-right', 106731)


class BoundaryAgrees(Exception):
    """The focused replay reached and compared the formerly divergent Flip."""


class PixelProbe(Native):
    def invoke(self, address, receiver, arguments, stack, source=None, return_pc=0):
        capture = (getattr(self, 'capture_profile', False) and address == 0x4c25b0
            and (self.phase, self.milliseconds) == FIRST_BOUNDARY)
        if capture:
            def word(pointer):
                return int.from_bytes(self.machine.mem_read(pointer, 4), 'little')
            origin, surface, clip = arguments
            palette = word(receiver+0x1c)
            if word(receiver+0x14) != 50 or word(palette+4) != 512:
                raise Blocked('Changed focused PID rank-table profile')
            physical = self.com_objects[word(surface+8)]
            pixels = physical['pixels']
            size = physical['pitch']*physical['height']
            regions = {receiver:40, origin:16, surface:64, clip:16,
                word(receiver+0x0c):word(receiver+0x10), palette:16,
                word(palette+8):512, 0x542bb0:256, pixels:size}
            profile = dict(address=address, receiver=receiver, arguments=list(arguments),
                stack=stack, source=source, return_pc=return_pc, pixels=pixels,
                phase=self.phase, milliseconds=self.milliseconds,
                object=[word(receiver+4*i) for i in range(10)],
                origin=[word(origin+4*i) for i in range(4)],
                surface=[word(surface+4*i) for i in range(16)],
                clip=[word(clip+4*i) for i in range(4)],
                memory={hex(p):bytes(self.machine.mem_read(p,n)).hex()
                        for p,n in regions.items()})
        result = super().invoke(address, receiver, arguments, stack, source, return_pc)
        if capture:
            profile['after'] = {hex(p):bytes(self.machine.mem_read(p,n)).hex()
                               for p,n in ((pixels,size),(0x542bb0,256))}
            profile['original_blit_pixels_sha256'] = self.expected_blit
            (OUT/'pid-profile-native.json').write_text(json.dumps(profile)+'\n')
            self.checked_blit = hashlib.sha256(bytes.fromhex(profile['after'][hex(pixels)])).hexdigest()
            if self.checked_blit != self.expected_blit:
                raise Blocked('Focused PID Unlock pixels differ from the original')
        return result

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        # Stop outside the native call/service transport, after its enclosing
        # frame returned successfully. A deliberate stop must not mask a fault.
        if getattr(self, 'boundary_result', None) and not self.native_functions:
            if self.native_error:
                raise Blocked(self.native_error)
            raise BoundaryAgrees()
        return result

    def com_fixture(self, address):
        method = self.com_methods.get(address)
        result = super().com_fixture(address)
        if method != ('IDirectDrawSurface', 'Flip'):
            return result
        event = self.presentations[-1]
        if not event['phase'].startswith('level-13-'):
            return result
        key = (event['phase'], event['milliseconds'])
        expected = self.expected.get(key)
        if expected is None:
            raise Blocked('Missing independent Level 13 presentation reference')
        self.compared_presentations = getattr(self, 'compared_presentations', 0)+1
        if event['pixels_sha256'] == expected:
            if getattr(self, 'through_first', False) and key == FIRST_BOUNDARY:
                self.boundary_result = dict(status='boundary-agrees', phase=key[0],
                    milliseconds=key[1], pixels_sha256=expected,
                    compared_presentations=self.compared_presentations,
                    blit_pixels_sha256=getattr(self, 'checked_blit', None),
                    guest_execution=False)
            return result
        batch = [dict(e) for e in self.physical_events
                 if (e.get('phase'), e.get('milliseconds')) == key]
        for e in batch:
            token = e.get('source')
            if token is None:
                continue
            surface = self.com_objects.get(int(token,16))
            if surface and 'pixels' in surface:
                e['source_surface'] = dict(width=surface['width'],height=surface['height'],pitch=surface['pitch'],
                    sha256=hashlib.sha256(self.machine.mem_read(surface['pixels'],surface['pitch']*surface['height'])).hexdigest())
        (OUT/'native-first-divergent-services.json').write_text(json.dumps(batch,indent=2)+'\n')
        (OUT/'first-pixel-probe.json').write_text(json.dumps(dict(phase=key[0],milliseconds=key[1],
            expected=expected,actual=event['pixels_sha256'],guest_execution=False,
            source_stack=[hex(a) for a in self.native_functions]),indent=2)+'\n')
        raise Blocked('Focused Level 13 first-pixel mismatch captured')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through-first', action='store_true',
        help='Stop after the formerly first divergent presentation agrees')
    parser.add_argument('--capture-profile', action='store_true',
        help='Retain local PID inputs including shared scratch at that boundary')
    args = parser.parse_args()
    if args.capture_profile:
        (OUT/'pid-profile-native.json').unlink(missing_ok=True)
    for name in ('first-pixel-probe.json', 'native-first-divergent-services.json',
                 'focused-pixel-result.json'):
        (OUT/name).unlink(missing_ok=True)
    route = json.loads((output_dir(LEVEL)/'plan.json').read_text())
    reference = read_trace(REFERENCE)
    validate_independent(reference, route)
    checked_reference = reference_controls(reference, route)
    events = [e for e in reference['physical_events']
              if (e.get('phase'),e.get('milliseconds')) == FIRST_BOUNDARY]
    if (len(events) <= 198 or events[197]['service'] != 'IDirectDrawSurface::Lock'
            or events[197].get('caller',{}).get('target') != '0x4c25b0'
            or events[198]['service'] != 'IDirectDrawSurface::Unlock'):
        raise Blocked('Changed focused original PID service boundary')
    PixelProbe.expected_blit = events[198]['pixels_sha256']
    record = shared.records(reference)
    PixelProbe.expected = {(p[0],p[1]):p[2] for p in record['presentations']}
    library, entries = shared.build(LEVEL)
    probe = PixelProbe(library,entries,route)
    probe.through_first = args.through_first
    probe.capture_profile = args.capture_profile
    try:
        probe.execute()
    except BoundaryAgrees:
        with open(library._name, 'rb') as stream:
            probe.boundary_result['native_library_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        probe.boundary_result.update(independent_original_sha256=fingerprint(REFERENCE),
            frame_completed=True, native_error=None, reference_controls=checked_reference,
            rank_sort_reference=reference['rank_sort_reference'])
        (OUT/'focused-pixel-result.json').write_text(json.dumps(probe.boundary_result,indent=2)+'\n')
        print(json.dumps(probe.boundary_result))
        return 0
    except Blocked as error:
        captured = (OUT/'first-pixel-probe.json').exists()
        print(json.dumps(dict(status='captured' if captured else 'blocked',
            error=probe.native_error or str(error),phase=probe.phase)))
        return 0 if captured and not args.through_first else 2
    else:
        if args.through_first:
            raise Blocked('Formerly divergent Level 13 presentation was not reached')
        count = sum(p[0].startswith('level-13-') for p in record['presentations'])
        if getattr(probe, 'compared_presentations', 0) != count or probe.played_ms != 60010:
            raise Blocked('Incomplete focused Level 13 presentation replay')
        print(json.dumps(dict(status='no-divergence',compared_presentations=count,
                              played_ms=probe.played_ms,guest_execution=False)))
        return 0
    finally:
        probe.close()


if __name__ == '__main__':
    raise SystemExit(main())
