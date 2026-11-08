#!/usr/bin/env python3
"""Offline checks for get-game-data's ISO/MDF transport and cache integrity.

Optionally --disc-zip checks the pinned original CD ZIP against all three hashes.
No game code, emulator, network request or external Python package is needed.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('get_game_data', Path(__file__).with_name('get-game-data.py'))
GET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GET)


def record(name, sector, length, directory=False):
    name = name.encode('ascii')
    raw = bytearray(33+len(name)+(len(name) % 2 == 0))
    raw[0] = len(raw)
    struct.pack_into('<I', raw, 2, sector)
    struct.pack_into('<I', raw, 10, length)
    raw[25] = 2 if directory else 0
    raw[32] = len(name)
    raw[33:33+len(name)] = name
    return raw


def image(stride, skip, duplicate=False):
    # Includes a file spanning sectors and zero padding between directory records.
    data = bytearray(26*2048)
    data[16*2048:16*2048+7] = b'\x01CD001\x01'
    struct.pack_into('<H', data, 16*2048+128, 2048)
    root = record('\0', 18, 4096, True)
    data[16*2048+156:16*2048+156+len(root)] = root
    entries = record('\0', 18, 4096, True)+record('\1', 18, 4096, True)+record('DATA', 20, 2048, True)
    data[18*2048:18*2048+len(entries)] = entries
    entries = record('CLAW.REZ;1', 21, 3000)
    if duplicate:
        entries += record('CLAW.REZ;2', 21, 3000)
    data[20*2048:20*2048+len(entries)] = entries
    data[21*2048:21*2048+3000] = b'X'*3000
    raw = bytearray()
    for at in range(0, len(data), 2048):
        sector = bytearray(stride)
        sector[skip:skip+2048] = data[at:at+2048]
        raw.extend(sector)
    return bytes(raw)


class Transport(unittest.TestCase):
    def test_sector_layouts(self):
        for stride, skip in [(2048, 0), (2352, 16), (2352, 24), (2448, 16), (2448, 24)]:
            with self.subTest(stride=stride, skip=skip):
                disc = GET.DiscImage(io.BytesIO(image(stride, skip)))
                files = list(disc.files())
                self.assertEqual(files, [('DATA/CLAW.REZ', 21*2048, 3000)])
                self.assertEqual(disc.read(files[0][1], 3000), b'X'*3000)
                with self.assertRaises(ValueError):
                    disc.read(1000000, 10)

    def test_bad_image(self):
        with self.assertRaises(ValueError):
            GET.DiscImage(io.BytesIO(b'bad image'))

    def test_payload_integrity_and_duplicates(self):
        original = GET.DISC_FILES
        try:
            GET.DISC_FILES = {'DATA/CLAW.REZ': hashlib.sha256(b'X'*3000).hexdigest()}
            with tempfile.TemporaryDirectory() as t:
                root = Path(t)
                source = root/'disc.iso'
                source.write_bytes(image(2048, 0))
                self.assertEqual(GET.extract_disc(source, root/'out'), GET.DISC_FILES)
                source.write_bytes(image(2048, 0, duplicate=True))
                with self.assertRaisesRegex(ValueError, 'Duplicate'):
                    GET.extract_disc(source, root/'out')
                source.write_bytes(image(2048, 0)[:-2048])
                GET.DISC_FILES = {'DATA/CLAW.REZ': '0'*64}
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    GET.extract_disc(source, root/'out')
                GET.DISC_FILES = {'MUSIC/CLAW4.SF2': '0'*64}
                with self.assertRaisesRegex(ValueError, 'missing'):
                    GET.extract_disc(source, root/'out')
        finally:
            GET.DISC_FILES = original

    def test_cache_is_verified_without_network(self):
        with tempfile.TemporaryDirectory() as t:
            target = Path(t)/'cached'
            target.write_bytes(b'cached data')
            expected = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(GET.fetch('https://invalid.invalid/', target, expected, 100), target)
            target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'unexpected hash'):
                GET.fetch('https://invalid.invalid/', target, expected, 100)


class CommandPaths(unittest.TestCase):
    def run_main(self, argv, download_error=False, cached_error=False):
        with patch('sys.argv', ['get-game-data.py', *argv]), \
             patch.object(GET, 'original_download', side_effect=ValueError('bad hash') if cached_error else OSError('offline') if download_error else None, return_value=Path('disc.zip')) as disc, \
             patch.object(GET, 'torrent_disc', side_effect=ValueError('brew install aria2')) as torrent, \
             patch.object(GET, 'fetch', return_value=Path('package.zip')) as package, \
             patch.object(GET, 'prepare', return_value={'status': 'pass'}) as prepare, \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if cached_error:
                with self.assertRaises(SystemExit) as error:
                    GET.main()
                self.assertEqual(error.exception.code, 1)
                prepare.assert_not_called()
            else:
                GET.main()
            return disc.call_count, torrent.call_count, package.call_count, prepare.call_args

    def test_default_cd(self):
        disc, torrent, package, prepared = self.run_main([])
        self.assertEqual((disc, torrent, package), (1, 0, 0))
        self.assertEqual(prepared.args[1], GET.DISC_URL)

    def test_explicit_crazyhook(self):
        disc, torrent, package, prepared = self.run_main(['--package', 'crazyhook'])
        self.assertEqual((disc, torrent, package), (0, 0, 1))
        self.assertEqual(prepared.args[1], GET.SETUP['PACKAGE_URL'])

    def test_source_never_downloads(self):
        disc, torrent, package, prepared = self.run_main(['--source', 'CLAW.REZ'])
        self.assertEqual((disc, torrent, package), (0, 0, 0))
        self.assertEqual(prepared.args[0].source, Path('CLAW.REZ'))

    def test_network_failure_falls_back(self):
        disc, torrent, package, prepared = self.run_main([], download_error=True)
        self.assertEqual((disc, torrent, package), (1, 1, 1))

    def test_bad_hash_does_not_fall_back(self):
        disc, torrent, package, _ = self.run_main([], cached_error=True)
        self.assertEqual((disc, torrent, package), (1, 0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disc-zip', type=Path)
    args = parser.parse_args()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (Transport, CommandPaths))
    result = unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():
        return 1
    hashes = None
    if args.disc_zip:
        assert GET.SETUP['digest'](args.disc_zip) == GET.DISC_HASH
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            with zipfile.ZipFile(args.disc_zip) as archive:
                with archive.open('Claw_ISO/CLAW.mdf') as src, (root/'disc.mdf').open('wb') as dst:
                    shutil.copyfileobj(src, dst)
            hashes = GET.extract_disc(root/'disc.mdf', root/'data')
    print(json.dumps(dict(check='original-disc-data', status='pass', sector_layouts=5,
                         disc_files_sha256=hashes)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
