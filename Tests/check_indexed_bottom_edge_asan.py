"""ASAN/UBSAN exact-buffer replays; generate with compare_indexed_bottom_edge.py first."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1];work=root/'work/indexed-bottom-edge-agent'
subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic-errors','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'Sources'),str(root/'Tests/indexed_bottom_edge_exact_replay.cpp'),*[str(root/'Sources'/f'{n}.cpp')for n in('NativeIndexedPresentation','EffectPIDBlitter','LightPIDBlitter','PIDBlitter')],'-o',str(work/'smoke')],check=True)
subprocess.run([str(work/'smoke'),str(work)],check=True)
print('PASS25 source-captured exact full/tight framebuffer replays (50 adapter checks), ASAN+UBSAN')
