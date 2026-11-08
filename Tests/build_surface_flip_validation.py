from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/surface-flip-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['SurfaceFlipRuntime','SurfaceBlitRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster']
sources=[ROOT/'Sources'/f'{n}.cpp'for n in NAMES]
common=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
subprocess.run(common+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_surface_flip.cpp'),*[str(p)for p in sources],'-lz','-o',str(WORK/'exact-sized-replay')],check=True)
p=WORK/'header.c';p.write_text('#include "SurfaceFlipRuntime.h"\nint main(void){ClawSurfaceFlipContext c={0};return (int)c.fault;}\n')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(p),'-o',str(WORK/'header.o')],check=True)
(WORK/'module.modulemap').write_text('module SurfaceFlipRuntime { header "'+str(ROOT/'Sources/SurfaceFlipRuntime.h')+'" export * }\n')
p=WORK/'header.swift';p.write_text('import SurfaceFlipRuntime\nvar c = ClawSurfaceFlipContext()\nvar q = ClawSurfaceFlipCall()\nc.maximumOperations = 65536\nq.argumentCount = 3\n')
subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(p)],check=True)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[ROOT/'Sources/SurfaceFlipRuntime.h']};(WORK/'source-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS C11 header, C++17/Werror source closure, Swift import and ASAN/UBSAN build',flush=True)
