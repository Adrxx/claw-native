"""Hash-verified CLAW.REZ entry reader shared by connection comparisons."""
import hashlib
import struct

from Tests.clawparity.program import ROOT

REZ = ROOT / 'Original/claw-disc/files/DATA/CLAW.REZ'
REZ_SHA256 = 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'


def verify_assets():
    """Authenticate the disc backing the native WWD/resource snapshots."""
    with REZ.open('rb') as source:
        found = hashlib.file_digest(source, 'sha256').hexdigest()
    if found != REZ_SHA256:
        raise ValueError(f'CLAW.REZ hash mismatch: {found}')
    return found


def entries():
    """Yield (path, payload) for every file in the verified archive."""
    verify_assets()
    data = REZ.read_bytes()
    def word(offset):
        return struct.unpack_from('<I', data, offset)[0]
    def walk(offset, size, prefix=''):
        end = offset + size
        while offset < end:
            kind, target, count = word(offset), word(offset+4), word(offset+8)
            start = offset + (16 if kind else 28)
            stop = data.index(0, start, end)
            name = data[start:stop].decode('ascii')
            if kind:
                yield from walk(target, count, prefix + name + '/')
                offset = stop + 1
            else:
                ext = data[offset+20:offset+24].split(b'\0')[0][::-1].decode('ascii')
                yield prefix + name + '.' + ext, data[target:target+count]
                offset = stop + 2
    yield from walk(word(131), word(135))


def materialize(required):
    """required maps archive path -> (target Path, write). write=False checks
    that an existing native physical input equals the original disc bytes."""
    pending = dict(required)
    for name, payload in entries():
        if name in pending:
            target, write = pending.pop(name)
            if write:
                target.write_bytes(payload)
            elif target.read_bytes() != payload:
                raise RuntimeError('Native physical input differs from original disc: ' + name)
    if pending:
        raise RuntimeError('Missing reference assets: ' + str(sorted(pending)))
