#!/usr/bin/env python3
"""Prepare a player build: python3 scripts/setup-game-data.py /path/to/CLAW.REZ

A folder is searched recursively for CLAW.REZ and optional CLAW.FEC and CLAW4.SF2.
The pinned CLAW-1.4.5.4.zip from The Claw Recluse is also supported.
CrazyHook helpers are included. Movies need ffmpeg and ffprobe on PATH. No EXE is read.
All generated game assets stay in ignored App/GameData by default.
"""
import argparse
import hashlib
from fractions import Fraction
import json
import re
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REZ_HASH = 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
FEC_HASH = '9c87c82aaec3c73aa6c9eb268da9db8601aa10f75af35060bff4f1edcfbb80d8'
PACKAGE_HASH = '046a5e909c6183de30f6634031716f1c45d1c14453ded360d93d406db2e87b8d'
PACKAGE_REZ_HASH = '24da719bb0c18a306ecac7059c748ea8acdcde5f4f830723df449f234635249f'
PACKAGE_URL = 'https://captainclaw.net/dl/CLAW-1.4.5.4.zip'
SOURCE_PAGE = 'https://captainclaw.net/en/downloads.html'
PACKAGE_NOTE = ('Community data: modified credits; Level 9 removes BehindCrate 9720 and Seagull 9798; '
                'Level 14 removes TigerGuard 2314 and reorders existing objects. '
                'Windows-mod-only extra assets are omitted; native CrazyHook helpers are included. '
                'Use the original disc CLAW.REZ for unchanged levels.')


def community_extension(name):
    """The 221 added Windows-mod files, absent from the retail resource surface.

    In particular its FRAME570 exports can cross PID row boundaries and fail
    the original image decoder during bulk registration. None are required by
    the retail worlds/animations. Native custom features use our bundled helpers.
    The research check verifies this selection equals exactly the ZIP extras.
    """
    prefixes = ('GAME/MODULES/', 'GAME/LOGICS/', 'GAME/IMAGES/EXPLOS/PLASMA/',
                'GAME/IMAGES/POWERUPS/NEWPLASMASWORD/', 'GAME/IMAGES/PROJECTILES/PLASMASWORD/',
                'STATES/MENU/ANIS/CRAZYHOOK/', 'STATES/MENU/IMAGES/CRAZYHOOK/',
                'STATES/MENU/SOUNDS/CRAZYHOOK/')
    singles = ('CLAW/SOUNDS/PLASMASWORD.WAV', 'GAME/ANIS/PLASDEATH.ANI', 'GAME/ANIS/PLASMASWORD.ANI',
               'GAME/ANIS/PLASSWORDEXPLOSION.ANI', 'GAME/IMAGES/HEALTH/BANANAS/BANANAS1.PID',
               'LEVEL12/SOUNDS/AMBIENT/WINDWHISTLING.WAV', 'LEVEL14/TILES/FRONT/013.PID',
               'STATES/BOOTY/IMAGES/PERFECTC/001.PID', 'STATES/BOOTY/SOUNDS/PERFECTC.WAV',
               'STATES/DIALOGS/IMAGES/CUSTOMWORLD/REC.ICO', 'STATES/DIALOGS/IMAGES/CUSTOMWORLD/REC2.ICO')
    trigger_ids = ('1000', '1001', '1002', '1003', '1007', '1010', '1011', '1013', '1014', '1016',
                   '1017', '1021', '1022', '1023', '1024', '1025', '1027', '1028', '1032', '1038',
                   '1040', '1043', '1049', '1052', '1110010', '1110013', '1110015', '1110016',
                   '1110017', '1110018', '1110019')
    return (name.startswith(prefixes) or name.endswith('/FRAME570.PID') or name in singles or
            name in ('LEVEL12/SOUNDS/TRIGGER/' + n + '.WAV' for n in trigger_ids))


def package_assets(source, destination):
    """Extract Assets only, ignoring sibling Windows executables and plugins."""
    if digest(source) != PACKAGE_HASH:
        raise ValueError('Unsupported community ZIP: SHA-256 must be ' + PACKAGE_HASH)
    prefix = 'CLAW-1.4.5.4/Assets/'
    with zipfile.ZipFile(source) as archive:
        seen = set()
        for item in archive.infolist():
            if not item.filename.startswith(prefix) or item.is_dir():
                continue
            name = item.filename[len(prefix):].upper()
            parts = name.split('/')
            if any(not p or p in ('.', '..') or '\\' in p or ':' in p for p in parts) or name in seen:
                raise ValueError('Unsafe or duplicate package path')
            seen.add(name)
            if community_extension(name):
                continue
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    # These two dialog WAVs are omitted in LEVEL12 but are byte-identical to
    # the disc payloads under LEVEL11. Verify before restoring their paths.
    restored = {}
    for name, expected in [('1005', 'bcee1ad259fbaff75d1a45f886fcd292e9296028f57e78fc8b58bdbc77414d39'),
                           ('1044', '8900dcc443a6ca5f19478a13a508b33b3cf9e4ed0af01a27191c3f86d5633c24')]:
        original = destination / ('LEVEL11/SOUNDS/TRIGGER/' + name + '.WAV')
        if digest(original) != expected:
            raise ValueError('Missing original dialog payload: ' + name)
        target = destination / ('LEVEL12/SOUNDS/TRIGGER/' + name + '.WAV')
        shutil.copyfile(original, target)
        restored[str(target.relative_to(destination))] = str(original.relative_to(destination))
    return restored


def assemble_rez(assets, target):
    """Local REZ v1 container; payloads stay unchanged, IDs follow numeric stems.

    Same directory records/header as ClawCustomAssets.archive(). The native
    resource graph can then keep using its existing read-only REZ transport.
    """
    with target.open('w+b') as stream:
        stream.write(bytes(168))
        def emit(folder):
            records = bytearray()
            for path in sorted(folder.iterdir()):
                if path.is_dir():
                    offset, length = emit(path)
                    records.extend(struct.pack('<4I', 1, offset, length, 0))
                    records.extend(path.name.encode('ascii') + b'\0')
                else:
                    raw = path.read_bytes()
                    offset = stream.tell()
                    stream.write(raw)
                    stem, dot, ext = path.name.rpartition('.')
                    if not dot:
                        stem, ext = path.name, ''
                    if len(ext) > 4:
                        raise ValueError('Unsupported REZ extension: ' + path.name)
                    number = re.search(r'[0-9]+', stem)
                    identity = int(number[0]) if number else 0
                    tag = int.from_bytes(ext.encode('ascii'), 'big')
                    records.extend(struct.pack('<7I', 0, offset, len(raw), 0, identity, tag, 0))
                    records.extend(stem.encode('ascii') + b'\0\0')
            offset = stream.tell()
            stream.write(records)
            return offset, len(records)
        offset, length = emit(assets)
        total = stream.tell()
        for at, value in [(127, 1), (131, offset), (135, length), (143, total),
                          (147, 1), (151, 1), (155, 1), (159, 1), (163, 1)]:
            stream.seek(at)
            stream.write(struct.pack('<I', value))
        stream.seek(167)
        stream.write(b'\1')


def digest(path):
    # Chunked so the macOS system Python 3.9 works (no hashlib.file_digest).
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            value.update(chunk)
    return value.hexdigest()


ICON_SIZES = [('ipad', 20, (1, 2)), ('ipad', 29, (1, 2)), ('ipad', 40, (1, 2)), ('ipad', 76, (1, 2)),
              ('ipad', 83.5, (2,)), ('ios-marketing', 1024, (1,))] + [('mac', n, (1, 2)) for n in (16, 32, 128, 256, 512)]


def app_icon(data):
    """Write App/GeneratedIcons.xcassets, which the Xcode project expects.

    With Pillow installed the full generator draws the icon from the game data;
    without it, macOS sips resizes the tracked compass fallback."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        target = ROOT / 'App/GeneratedIcons.xcassets/AppIcon.appiconset'
        target.mkdir(parents=True, exist_ok=True)
        entries = []
        for idiom, points, scales in ICON_SIZES:
            for scale in scales:
                pixels = int(points * scale)
                name = f'{idiom}-{pixels}.png'
                subprocess.run(['sips', '-s', 'format', 'png', '-z', str(pixels), str(pixels),
                                str(ROOT / 'App/IconFallback.png'), '--out', str(target / name)],
                               check=True, stdout=subprocess.DEVNULL)
                entries.append(dict(idiom=idiom, size=f'{points:g}x{points:g}', scale=f'{scale}x', filename=name))
        (target / 'Contents.json').write_text(json.dumps(dict(images=entries, info=dict(author='xcode', version=1)), indent=2) + '\n')
        (target.parent / 'Contents.json').write_text('{"info":{"author":"xcode","version":1}}\n')
        return 'compass fallback (install Pillow for the game-art icon)'
    runpy.run_path(str(ROOT / 'scripts/prepare-app-icon.py'))['generate'](data=data)
    return 'generated from game data'


def find(folder, name):
    matches = [p for p in folder.rglob('*') if p.is_file() and p.name.upper() == name.upper()]
    if len(matches) > 1:
        raise ValueError(f'Multiple {name} files; supply a folder with one copy or an explicit option')
    return matches[0] if matches else None


def movies(source, output):
    if digest(source) != FEC_HASH:
        raise ValueError('CLAW.FEC differs from the original disc movie archive')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('Optional movies require ffmpeg and ffprobe; install ffmpeg or omit CLAW.FEC')
    output.mkdir(parents=True)
    entries = []
    with source.open('rb') as stream:
        header = stream.read(15)
        if header[:3] != b'FEC' or struct.unpack_from('<I', header, 11)[0] != 12:
            raise ValueError('Invalid movie archive')
        position = 15
        for movie in range(1, 13):
            stream.seek(position)
            record = stream.read(268)
            number = struct.unpack_from('<I', record)[0]
            marker, length = struct.unpack_from('<HI', record, 262)
            if number != movie or marker < 696:
                raise ValueError('Invalid movie record')
            offset = position + marker - 428
            stream.seek(offset)
            payload = stream.read(length)
            if len(payload) != length or payload[:4] not in (b'SMK2', b'SMK4'):
                raise ValueError('Invalid movie payload')
            # A single temporary Smacker file, removed after conversion.
            smk = output / 'source.smk'
            smk.write_bytes(payload)
            target = output / f'movie-{movie:02d}.mp4'
            subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-threads', '1',
                '-i', str(smk), '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264',
                '-threads', '1', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p',
                '-fps_mode', 'passthrough', '-enc_time_base', 'demux', '-video_track_timescale', '100000',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(target)], check=True)
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_streams', '-of', 'json', str(target)]))['streams'][0]
            width, height, frames = struct.unpack_from('<III', payload, 4)
            if (probe['width'], probe['height'], int(probe['nb_frames'])) != (width, height, frames):
                raise ValueError('Movie conversion changed resolution or frame count')
            def presentation(path):
                info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=time_base:packet=pts,duration', '-of', 'json', str(path)]))
                scale = Fraction(info['streams'][0]['time_base'])
                return sorted((int(p['pts'])*scale, int(p['duration'])*scale) for p in info['packets'])
            if presentation(smk) != presentation(target):
                raise ValueError('Movie conversion changed presentation cadence')
            entries.append(dict(movieID=movie, file=target.name, width=width, height=height,
                sha256=digest(target), originalPayloadSHA256=hashlib.sha256(payload).hexdigest()))
            smk.unlink()
            position = offset + length
            print(f'Prepared movie {movie}/12', file=sys.stderr, flush=True)
    (output / 'movies.json').write_text(json.dumps(dict(schema=1, originalMovieCount=12,
        originalContainerSHA256=FEC_HASH, entries=entries), indent=2) + '\n')


def setup(args):
    source = args.source.resolve()
    folder = source if source.is_dir() else source.parent
    community = source.suffix.lower() == '.zip' and source.is_file()
    rez = find(folder, 'CLAW.REZ') if source.is_dir() else source
    if rez is None or not rez.is_file():
        raise ValueError('Supply the original disc CLAW.REZ or a folder containing it')
    actual = digest(rez)
    if actual != (PACKAGE_HASH if community else REZ_HASH):
        if community:
            raise ValueError(f'Unsupported community ZIP: SHA-256 {actual}; expected {PACKAGE_HASH}')
        raise ValueError(f'Unsupported CLAW.REZ: SHA-256 {actual}; expected original disc {REZ_HASH}. '
                         'Modified or other-release archives are not supported; use your original disc DATA/CLAW.REZ.')
    fec = args.movies or (None if community else find(folder, 'CLAW.FEC'))
    if fec and (not shutil.which('ffmpeg') or not shutil.which('ffprobe')):
        # Cutscenes are optional: skip them rather than fail the whole setup.
        print('Skipping cutscenes: install ffmpeg (brew install ffmpeg) and run setup again to add them.', file=sys.stderr)
        fec = None
    bank = args.soundfont or (None if community else find(folder, 'CLAW4.SF2'))
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.game-data-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'GameData'
        restored = {}
        archive = rez
        if community:
            restored = package_assets(source, stage)
            archive = Path(temporary) / 'CLAW.REZ'
            assemble_rez(stage, archive)
            if digest(archive) != PACKAGE_REZ_HASH:
                raise ValueError('Local archive differs from the app-supported deterministic package; restore the setup script')
            print(f'The Claw Recluse: {SOURCE_PAGE}\n{PACKAGE_NOTE}', file=sys.stderr)
        else:
            subprocess.run([sys.executable, str(ROOT / 'scripts/extract-rez.py'), str(rez), str(stage), '--all'],
                           check=True, stdout=subprocess.DEVNULL)
        # Existing native app paths, including the original loose worlds.
        for name in ('IMAGES', 'ANIS'):
            shutil.copytree(stage / 'CLAW' / name, stage / name)
        shutil.copyfile(stage / 'LEVEL1/PALETTES/MAIN.PAL', stage / 'MAIN.PAL')
        menu = stage / 'MENU'
        shutil.copytree(stage / 'STATES/MENU', menu / 'STATES/MENU')
        shutil.copyfile(archive, menu / 'CLAW.REZ')
        runpy.run_path(str(ROOT / 'scripts/prepare-menu-assets.py'))['prepare'](stage)
        if bank:
            shutil.copyfile(bank, menu / 'CLAW4.SF2')
        if fec:
            movies(fec, stage / 'MOVIES')
        (stage / 'source.json').write_text(json.dumps(dict(
            source='claw-recluse' if community else 'disc', sha256=actual,
            url=PACKAGE_URL if community else None, note=PACKAGE_NOTE if community else None,
            restored_paths=restored), indent=2) + '\n')
        # Replace rather than merge: omitting extras removes old optional packs.
        if destination.exists():
            shutil.rmtree(destination)
        stage.rename(destination)
    icon = app_icon(destination) if destination == ROOT / 'App/GameData' else 'not written (custom output)'
    return dict(status='pass', source='claw-recluse' if community else 'disc',
                source_sha256=actual, rez_sha256=digest(destination / 'MENU/CLAW.REZ'), output=str(destination), icon=icon,
                movies=bool(fec), original_music=bool(bank), crazyhook_helpers=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--movies', type=Path)
    parser.add_argument('--soundfont', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'App/GameData')
    try:
        print(json.dumps(setup(parser.parse_args())))
    except (ValueError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f'setup-game-data: {error}\n')


if __name__ == '__main__':
    main()
