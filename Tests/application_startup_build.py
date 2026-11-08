"""Current frozen source closure; no saved prebuilt library is used."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work/application-startup-agent';WORK.mkdir(parents=True,exist_ok=True)
SOURCES=set()
for file,name in [('build_scene_startup_composition_validation.py','SOURCES'),('player_startup_runtime_helpers.py','SOURCES'),('light_palette_runtime_helpers.py','SOURCES'),('resource_archive_loading_helpers.py','sources')]:
 for node in ast.parse((ROOT/'Tests'/file).read_text()).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in node.targets):
   SOURCES.update(x if x.startswith('Sources/')else 'Sources/'+x+'.cpp'for x in ast.literal_eval(node.value))
SOURCES.update('Sources/'+x+'.cpp'for x in ['ApplicationStartupRuntime','PlayerCacheApplicationRuntime','SaveFileRuntime','SaveLoadRuntime','MusicRuntime','SpecialCommandRuntime','CRTRandomRuntime','WorldLootRuntime'])
SOURCES=sorted(SOURCES)
COMMON=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
def shared():
 subprocess.run(COMMON+['-O2','-dynamiclib',*[str(ROOT/p)for p in SOURCES],'-o',str(WORK/'libStartup.dylib')],check=True)
def gates():
 c=WORK/'header.c';c.write_text('#include "ApplicationStartupRuntime.h"\nint main(void){ClawApplicationStartupContext c={0};return (int)c.fault;}\n')
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(c),'-o',str(WORK/'header.o')],check=True)
 (WORK/'module.modulemap').write_text('module ApplicationStartupRuntime { header "'+str(ROOT/'Sources/ApplicationStartupRuntime.h')+'" export * }\n')
 s=WORK/'header.swift';s.write_text('import ApplicationStartupRuntime\nvar c = ClawApplicationStartupContext()\nc.maximumOperations = 1000000\nlet scratchBytes = CLAW_APPLICATION_STARTUP_AUTOMATIC_BYTES\n')
 subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(s)],check=True)
 (WORK/'source-sha256.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES+['Sources/ApplicationStartupRuntime.h']},indent=2)+'\n')
def sanitizer():
 subprocess.run(COMMON+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_application_startup.cpp'),*[str(ROOT/p)for p in SOURCES],'-lz','-o',str(WORK/'exact-sized-replay')],check=True)
if __name__=='__main__':shared();gates();print('PASS strict C11/C++17/Swift current source closure',len(SOURCES),flush=True)
