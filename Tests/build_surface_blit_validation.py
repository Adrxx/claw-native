from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/surface-blit-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['SurfaceBlitRuntime','PCXImageRuntime','GameImageRuntime','SpriteGeometry','PIDSurfaceRaster']
sources=[ROOT/'Sources'/f'{n}.cpp'for n in NAMES]
common=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
subprocess.run(common+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_surface_blit.cpp'),*[str(p)for p in sources],'-lz','-o',str(WORK/'exact-sized-replay')],check=True)
p=WORK/'header.c';p.write_text('#include "SurfaceBlitRuntime.h"\nint main(void){ClawSurfaceBlitContext c={0};return (int)c.fault;}\n')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(p),'-o',str(WORK/'header.o')],check=True)
(WORK/'module.modulemap').write_text('module SurfaceBlitRuntime { header "'+str(ROOT/'Sources/SurfaceBlitRuntime.h')+'" export * }\n')
p=WORK/'header.swift';p.write_text('import SurfaceBlitRuntime\nvar c = ClawSurfaceBlitContext()\nvar a = ClawSurfaceBlitArguments()\nc.maximumOperations = 65536\na.count = 5\n')
subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(p)],check=True)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[ROOT/'Sources/SurfaceBlitRuntime.h']};(WORK/'source-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS C11 header, C++17/Werror source closure, Swift import and ASAN/UBSAN build',flush=True)
