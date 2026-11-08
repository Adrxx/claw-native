"""Included CrazyHook helper assets and maintainer-only release extraction."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = '046a5e909c6183de30f6634031716f1c45d1c14453ded360d93d406db2e87b8d'
HELPERS = {
    'HELPERANIS/PLASSWORDEXPLOSION.ANI': 'GAME/ANIS/PLASSWORDEXPLOSION.ANI',
    'HELPERSOUNDS/PLASMASWORD.WAV': 'CLAW/SOUNDS/PLASMASWORD.WAV',
    **{f'HELPERIMAGES/{group}/FRAME{i:03}.PID': f'GAME/IMAGES/{group}/FRAME{i:03}.PID'
       for group, count in [('EXPLOS/PLASMA', 17), ('PROJECTILES/PLASMASWORD', 8)]
       for i in range(1, count + 1)},
}


def check_helpers(source, readme=False):
    """Require precisely the supported assets and their release hashes."""
    manifest = json.loads((source / 'manifest.json').read_text())
    if manifest['archive_sha256'] != ARCHIVE_SHA256 or set(manifest['files']) != set(HELPERS):
        raise ValueError('Invalid CrazyHook helper manifest')
    expected = set(HELPERS) | {'manifest.json'} | ({'README.md'} if readme else set())
    if {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()} != expected:
        raise ValueError('Unexpected or missing CrazyHook helper files')
    for name, digest in manifest['files'].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'CrazyHook helper hash mismatch: {name}')
    return manifest


def copy_helpers(destination):
    source = ROOT / 'App/CrazyHookHelpers'
    check_helpers(source, readme=True)
    for name in [*HELPERS, 'manifest.json']:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        content = (source / name).read_bytes()
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)


def prepare_crazyhook_helpers(archive, destination):
    """Bundle the local release's plasma assets, never its Lua or Windows code."""
    import zipfile
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError('CrazyHook helper archive hash mismatch')
    files = {}
    with zipfile.ZipFile(archive) as release:
        prefix = 'CLAW-1.4.5.4/Assets/'
        entries = {name.upper(): name for name in release.namelist()}
        for target, path in HELPERS.items():
            data = release.read(entries[(prefix + path).upper()])
            output = destination / target
            output.parent.mkdir(parents=True, exist_ok=True)
            if not output.exists() or output.read_bytes() != data:
                output.write_bytes(data)
            files[target] = hashlib.sha256(data).hexdigest()
    if len(files) != 27:
        raise ValueError('Incomplete CrazyHook plasma assets')
    (destination / 'manifest.json').write_text(json.dumps(dict(archive_sha256=digest, files=files), sort_keys=True)+'\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='Maintainer copy of CLAW-1.4.5.4.zip')
    parser.add_argument('--output', type=Path, default=ROOT / 'App/CrazyHookHelpers')
    args = parser.parse_args()
    prepare_crazyhook_helpers(args.archive, args.output)
    print(json.dumps(dict(status='pass', helper_files=len(HELPERS), output=str(args.output))))
