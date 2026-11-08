#!/usr/bin/env python3
"""Download and prepare original disc data (system Python 3.9, no packages).

Use --source /path/to/CLAW.REZ to prefer your original disc without downloading.
Disc ZIP, ISO/MDF, folders and the pinned community ZIP also work offline.
Default: original CD (including music and movies); --package crazyhook opts out.
No game files are hosted by this project. Movies require ffmpeg/ffprobe.
"""
import argparse
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parents[1]
SETUP = runpy.run_path(str(ROOT / 'scripts/setup-game-data.py'))
USER_AGENT = 'claw-ipad/1.0 (+https://github.com/Adrxx/claw-ipad)'
# The Recluse's current pages offer CrazyHook and a DVD torrent, not the CD.
# archive.html (including text after character 100000) links a dead Dropbox DVD
# ISO. The live alternative below is the exact owner's CD ZIP, not a mirror
# hosted by this project. Resolve its ordinary session redirect on each download.
DISC_PAGE = 'https://www.myabandonware.com/game/claw-a39'
DISC_URL = 'https://www.myabandonware.com/download/lvmi-claw'
DISC_HASH = 'adeacf7744be8f8cf87b07e506cdcc83d5d2857bbd1aa82b5b8f52276dd57be7'
TORRENT_URL = 'https://captainclaw.net/dl/claw_dvd.torrent'
TORRENT_HASH = 'bacae5797d99301bbf9791d72c9ad2311cf68712a4af00d403a628fcdd6fa832'
# The torrent contains one 1395419136-byte DVD ISO plus a 47-byte text file.
DVD_NAME = 'Captain Claw ENG PL DVD Version with Extras [TEO PHiL]'
DISC_FILES = {'DATA/CLAW.REZ': SETUP['REZ_HASH'], 'MOVIES/CLAW.FEC': SETUP['FEC_HASH'],
              'MUSIC/CLAW4.SF2': 'e71ade72b30bea21beb649fbd29cc72539079474e0068648a8cc2b81b67401f8'}
MOVIE_PAGE = 'https://www.mediafire.com/file/9yfncm88b9pjewk/CLAW.FEC'


def fetch(url, target, expected, maximum, opener=None):
    """Verify both cache hits and temporary downloads before publishing them."""
    if target.exists():
        if SETUP['digest'](target) != expected:
            raise ValueError('Cached file has an unexpected hash; remove it and retry: ' + str(target))
        print('Using verified cache: ' + str(target), file=sys.stderr)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.download-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with (opener or urlopen)(request, timeout=45) as response:
                if urlparse(response.geturl()).scheme != 'https':
                    raise ValueError('Download redirected away from HTTPS')
                total = 0
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > maximum:
                        raise ValueError('Download exceeds expected size bound')
                    stream.write(chunk)
            stream.flush()
            if SETUP['digest'](temporary) != expected:
                raise ValueError('Downloaded file failed SHA-256 verification: ' + url)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


class MovieLink(HTMLParser):
    def __init__(self):
        super().__init__()
        self.url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('id') == 'downloadButton':
            self.url = attrs.get('href')


def cutscenes(cache):
    try:
        target = cache / 'CLAW.FEC'
        if target.exists():
            return fetch(MOVIE_PAGE, target, SETUP['FEC_HASH'], 500 << 20)
        with urlopen(Request(MOVIE_PAGE, headers={'User-Agent': USER_AGENT}), timeout=20) as response:
            page = response.read(2 << 20).decode('utf-8', errors='replace')
        parser = MovieLink()
        parser.feed(page)
        host = urlparse(parser.url or '').hostname or ''
        if not parser.url or urlparse(parser.url).scheme != 'https' or not host.endswith('.mediafire.com'):
            raise ValueError('No direct HTTPS download available')
        return fetch(parser.url, target, SETUP['FEC_HASH'], 500 << 20)
    except (OSError, ValueError) as error:
        print(f'Optional cutscenes unavailable: {error}\nDownload manually: {MOVIE_PAGE}\n'
              f'Only original CLAW.FEC SHA-256 {SETUP["FEC_HASH"]} is accepted; '
              'then use --movies /path/to/CLAW.FEC.', file=sys.stderr)
        return None


class DiscImage:
    """Read ISO 9660 user data from cooked ISO or raw Mode 1/2 MDF sectors."""
    def __init__(self, stream):
        self.stream = stream
        stream.seek(0, 2)
        self.size = stream.tell()
        for self.stride, self.skip in ((2048, 0), (2352, 16), (2352, 24), (2448, 16), (2448, 24)):
            stream.seek(16 * self.stride + self.skip)
            if stream.read(7) == b'\x01CD001\x01':
                break
        else:
            raise ValueError('No ISO 9660 primary volume in 2048/2352/2448-byte sectors')
        pvd = self.read(16 * 2048, 2048)
        if struct.unpack_from('<H', pvd, 128)[0] != 2048:
            raise ValueError('Unsupported ISO logical block size')
        self.root = self.record(pvd[156:156+pvd[156]])

    def read(self, offset, length):
        if offset < 0 or length < 0 or (offset + length + 2047)//2048*self.stride > self.size:
            raise ValueError('ISO extent outside image')
        result = bytearray()
        while length:
            sector, within = divmod(offset, 2048)
            count = min(length, 2048-within)
            self.stream.seek(sector*self.stride+self.skip+within)
            raw = self.stream.read(count)
            if len(raw) != count:
                raise ValueError('Truncated ISO extent')
            result.extend(raw)
            offset += count
            length -= count
        return bytes(result)

    @staticmethod
    def record(raw):
        if len(raw) < 34 or 33+raw[32] > len(raw):
            raise ValueError('Invalid ISO directory record')
        return (raw[33:33+raw[32]].decode('ascii').split(';')[0].upper(),
                struct.unpack_from('<I', raw, 2)[0]*2048,
                struct.unpack_from('<I', raw, 10)[0], raw[25])

    def files(self):
        pending, seen = [('', self.root)], set()
        while pending:
            parent, (_, offset, length, _) = pending.pop()
            if offset in seen or len(seen) > 4096 or length > 16 << 20:
                raise ValueError('Cyclic or oversized ISO directory')
            seen.add(offset)
            data, at = self.read(offset, length), 0
            while at < len(data):
                size = data[at]
                if not size:
                    at = (at//2048+1)*2048
                    continue
                raw = data[at:at+size]
                at += size
                if len(raw) != size:
                    raise ValueError('Truncated ISO directory record')
                name, start, count, flags = entry = self.record(raw)
                if name in ('\x00', '\x01'):
                    continue
                path = parent + name
                if flags & 0x80:
                    raise ValueError('Multi-extent ISO files are unsupported')
                if flags & 2:
                    pending.append((path+'/', entry))
                else:
                    yield path, start, count


def extract_disc(source, destination):
    """Select only three verified payloads; never extract archive paths."""
    destination.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as stream:
        image = DiscImage(stream)
        found = {}
        for path, offset, length in image.files():
            for wanted, expected in DISC_FILES.items():
                if path != wanted and not path.endswith('/'+wanted):
                    continue
                if wanted in found:
                    raise ValueError('Duplicate disc payload: '+wanted)
                target = destination / Path(wanted).name
                with target.open('wb') as output:
                    for at in range(0, length, 1 << 20):
                        output.write(image.read(offset+at, min(1 << 20, length-at)))
                if SETUP['digest'](target) != expected:
                    raise ValueError('Disc payload SHA-256 mismatch: '+path)
                found[wanted] = expected
        if set(found) != set(DISC_FILES):
            raise ValueError('Disc is missing: '+', '.join(set(DISC_FILES)-set(found)))
    return found


def original_download(cache):
    target = cache / 'claw-original-disc.zip'
    print(f'Original CD source: {DISC_PAGE}\nDownload: {DISC_URL}\n'
          f'The Claw Recluse reference: {SETUP["SOURCE_PAGE"]}', file=sys.stderr)
    if target.exists():
        return fetch(DISC_URL, target, DISC_HASH, 520 << 20)
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with opener.open(Request(DISC_PAGE, headers={'User-Agent': USER_AGENT}), timeout=45) as response:
        response.read(1 << 20)
    def download(request, timeout):
        request.add_header('Referer', DISC_PAGE)
        return opener.open(request, timeout=timeout)
    return fetch(DISC_URL, target, DISC_HASH, 520 << 20, download)


def torrent_disc(cache):
    if not shutil.which('aria2c'):
        raise ValueError('The Claw Recluse DVD needs aria2c: brew install aria2')
    torrent = fetch(TORRENT_URL, cache/'claw_dvd.torrent', TORRENT_HASH, 1 << 20)
    print('DVD source: '+TORRENT_URL, file=sys.stderr)
    subprocess.run(['aria2c', '--seed-time=0', '--check-integrity=true', '--select-file=1',
                    '--max-overall-download-limit=8M', '--bt-stop-timeout=60', '--stop=600',
                    '--user-agent='+USER_AGENT, '--dir='+str(cache.resolve()), str(torrent)],
                   check=True, timeout=660)
    image = cache / DVD_NAME / (DVD_NAME+'.iso')
    if not image.is_file() or image.stat().st_size != 1395419136:
        raise ValueError('DVD torrent did not complete')
    return image


def prepare(args, source_url):
    source = args.source
    is_disc_zip = source.suffix.lower() == '.zip' and SETUP['digest'](source) == DISC_HASH
    if is_disc_zip or source.suffix.lower() in ('.iso', '.mdf'):
        with tempfile.TemporaryDirectory(prefix='claw-disc-') as temporary:
            folder = Path(temporary)
            if is_disc_zip:
                with zipfile.ZipFile(source) as archive:
                    item = archive.getinfo('Claw_ISO/CLAW.mdf')
                    if item.file_size != 607713552:
                        raise ValueError('Unexpected CD image size')
                    image = folder/'CLAW.mdf'
                    with archive.open(item) as src, image.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
            else:
                image = source
            hashes = extract_disc(image, folder/'data')
            args.source = folder/'data'
            result = SETUP['setup'](args)
            result['disc_files_sha256'] = hashes
            if is_disc_zip:
                result['disc_zip_sha256'] = DISC_HASH
    else:
        if args.cutscenes and not args.movies:
            args.movies = cutscenes(args.cache_dir)
        result = SETUP['setup'](args)
    result['source_url'] = source_url
    if not result['original_music']:
        result['music_note'] = 'No original CLAW4.SF2 obtained; supply --soundfont from your disc.'
    provenance = args.output.resolve()/'source.json'
    info = json.loads(provenance.read_text())
    info['url'] = source_url or info.get('url')
    provenance.write_text(json.dumps(info, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Disc REZ/folder, ISO/MDF, pinned CD/community ZIP; no download')
    parser.add_argument('--package', choices=('original', 'crazyhook'), default='original')
    parser.add_argument('--cache-dir', type=Path, default=Path.home() / 'Library/Caches/claw-ipad')
    parser.add_argument('--output', type=Path, default=ROOT / 'App/GameData')
    parser.add_argument('--movies', type=Path)
    parser.add_argument('--soundfont', type=Path)
    parser.add_argument('--cutscenes', action='store_true', help='Also fetch optional movies for CrazyHook')
    args = parser.parse_args()
    source_url = None
    try:
        if args.source is None:
            if args.package == 'original':
                try:
                    args.source = original_download(args.cache_dir)
                    source_url = DISC_URL
                except OSError as error:
                    print(f'CD unavailable: {error}', file=sys.stderr)
                    try:
                        args.source = torrent_disc(args.cache_dir)
                        source_url = TORRENT_URL
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        print(f'DVD unavailable: {error}\nFalling back to CrazyHook; '
                              'original music is unavailable unless supplied with --soundfont.', file=sys.stderr)
            if args.source is None:
                source_url = SETUP['PACKAGE_URL']
                print('CrazyHook source: '+source_url, file=sys.stderr)
                args.source = fetch(source_url, args.cache_dir / 'CLAW-1.4.5.4.zip',
                                    SETUP['PACKAGE_HASH'], 100 << 20)
        try:
            result = prepare(args, source_url)
        except ValueError as error:
            if source_url != TORRENT_URL:
                raise
            print(f'DVD lacks the verified original CD payloads: {error}\n'
                  'Falling back to CrazyHook.', file=sys.stderr)
            source_url = SETUP['PACKAGE_URL']
            args.source = fetch(source_url, args.cache_dir / 'CLAW-1.4.5.4.zip',
                                SETUP['PACKAGE_HASH'], 100 << 20)
            result = prepare(args, source_url)
        print(json.dumps(result))
    except (ValueError, OSError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(1, f'get-game-data: {error}\n')


if __name__ == '__main__':
    main()
