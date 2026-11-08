from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/palette-fade-setup-agent';WORK.mkdir(parents=True,exist_ok=True)
NAMES=['PaletteFadeRuntime','PaletteResourceRuntime','AmbientAudioBackendRuntime','AudioEvents'];sources=[ROOT/'Sources'/f'{n}.cpp'for n in NAMES]
common=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
subprocess.run(common+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_palette_schedule_admission.cpp'),*[str(p)for p in sources],'-lz','-o',str(WORK/'exact-sized-replay')],check=True)
p=WORK/'header.c';p.write_text('#include "PaletteFadeRuntime.h"\nint main(void){ClawPaletteFadeContext c={0};ClawPaletteResourceContext p={0};c.palette=&p;return (int)c.fault;}\n');subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(p),'-o',str(WORK/'header.o')],check=True)
(WORK/'module.modulemap').write_text('module PaletteFadeRuntime { header "'+str(ROOT/'Sources/PaletteFadeRuntime.h')+'" export * }\n');p=WORK/'header.swift';p.write_text('import PaletteFadeRuntime\nvar c = ClawPaletteFadeContext()\nvar p = ClawPaletteResourceContext()\nc.maximumOperations = 1000000\n');subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(p)],check=True)
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources+[ROOT/'Sources/PaletteFadeRuntime.h',ROOT/'Sources/PaletteResourceRuntime.h']};(WORK/'source-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS existing owner ABI C11/C++17/Werror/Swift and exact-source ASAN/UBSAN build')
