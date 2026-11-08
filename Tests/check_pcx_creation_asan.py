"""Exact declared-span replays; first run capture_pcx_image_spans.py.

Generated original input/pixel bytes stay private; same-depth creation uses the measured decoder spans. Reachable seeded file tails
are explicit fixture data; tight-file faults compare source prefixes separately.
"""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
work=root/'work/root-pcx-spans'
subprocess.run(['clang++','-std=c++17','-O1','-g','-ffp-contract=off','-Wall',
                '-Wextra','-Werror','-pedantic-errors','-fsanitize=address,undefined',
                '-fno-omit-frame-pointer','-I',str(root/'Sources'),
                str(root/'Tests/pcx_creation_exact_replay.cpp'),
                *[str(root/'Sources'/f'{n}.cpp') for n in
                  ('PCXCreationRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster')],
                '-o',str(work/'creation-exact-replay')],check=True)
subprocess.run([str(work/'creation-exact-replay'),str(work),str(root/'work/pcx-creation-root')],check=True)
