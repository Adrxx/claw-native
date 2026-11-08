"""Exercise AVFoundation background timing, clock wrap, EOF and reopening offline."""
from pathlib import Path
import hashlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT/'Sources/ClawNativeMoviePlayback.swift', ROOT/'scripts/check-movie-background.swift']

def main():
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in SOURCES)).hexdigest()[:16]
    binary = ROOT/'work/level-fourteen-boss'/('background-controls-'+digest)
    if not binary.exists():
        subprocess.run(['xcrun', 'swiftc', '-O', *map(str, SOURCES), '-o', str(binary)], check=True)
    subprocess.run([str(binary), str(ROOT/'App/GameData/MOVIES')], check=True)

if __name__ == '__main__': main()
