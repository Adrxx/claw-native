"""Exact declared-span replays; first run capture_pcx_image_spans.py.

Generated original input/pixel bytes stay private. Reachable seeded file tails
are explicit fixture data; tight-file faults compare source prefixes separately.
"""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
work=root/'work/root-pcx-spans'
subprocess.run(['clang++','-std=c++17','-O1','-g','-ffp-contract=off','-Wall',
                '-Wextra','-Werror','-pedantic-errors','-fsanitize=address,undefined',
                '-fno-omit-frame-pointer','-I',str(root/'Sources'),
                str(root/'Tests/pcx_image_exact_replay.cpp'),
                *[str(root/'Sources'/f'{n}.cpp') for n in
                  ('PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster')],
                '-o',str(work/'exact-replay')],check=True)
subprocess.run([str(work/'exact-replay'),str(work)],check=True)
