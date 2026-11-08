"""Private current-source build; never mutates a shared support library."""
from application_startup_build import ROOT,SOURCES as STARTUP_SOURCES
from pathlib import Path
import hashlib,json,subprocess
WORK=ROOT/'work/application-resource-bootstrap-agent';WORK.mkdir(parents=True,exist_ok=True)
SOURCES=sorted((set(STARTUP_SOURCES)-{'Sources/ApplicationStartupRuntime.cpp'})|{'Sources/ApplicationArchivePathRuntime.cpp','Sources/CStringAssignmentRuntime.cpp'})
COMMON=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
def shared():subprocess.run(COMMON+['-O2','-dynamiclib',*[str(ROOT/p)for p in SOURCES],'-o',str(WORK/'libArchivePath.dylib')],check=True)
def sanitizer():subprocess.run(COMMON+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_application_archive_path.cpp'),*[str(ROOT/p)for p in SOURCES],'-lz','-o',str(WORK/'exact-sized-replay')],check=True)
def gates():
 p=WORK/'header.c';p.write_text('#include "ApplicationArchivePathRuntime.h"\nint main(void){ClawApplicationArchivePathContext c={0};return (int)c.fault;}\n')
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(p),'-o',str(WORK/'header.o')],check=True)
 (WORK/'module.modulemap').write_text('module ApplicationArchivePathRuntime { header "'+str(ROOT/'Sources/ApplicationArchivePathRuntime.h')+'" export * }\n')
 p=WORK/'header.swift';p.write_text('import ApplicationArchivePathRuntime\nvar c = ClawApplicationArchivePathContext()\nc.maximumOperations = 1000000\n')
 subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(p)],check=True)
 (WORK/'source-sha256.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES+['Sources/ApplicationArchivePathRuntime.h']},indent=2)+'\n')
if __name__=='__main__':shared();gates();print('PASS strict C11/C++17/Swift current private closure',len(SOURCES),flush=True)
