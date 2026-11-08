"""Content-addressed, sequential build of the finite native resource graph."""
import hashlib
import re
import subprocess
from .compare import ROOT

def main():
 names=('ClawNativeMenuResources','ResourceArchiveLoadingCanonical','ResourceNamespaceCanonicalRuntime',
        'ClawMenuResourceTableOwner','ResourceDataCanonical','ApplicationStartupZeroHookRuntime',
        'ClawMenuAudioListOwner','MenuPaperTransitionRuntime')
 compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip()
 sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
 common=subprocess.check_output([compiler,'--version'])+sdk.encode()
 for p in sorted((ROOT/'Sources').glob('*.h'))+sorted((ROOT/'Sources').glob('*.hpp')):common+=p.read_bytes()
 flags=['-std=c++17','-O0','-ffp-contract=off','-isysroot',sdk,'-I',str(ROOT/'Sources')]
 for name in names:
  source=ROOT/'Sources'/f'{name}.cpp';data=source.read_bytes()
  included=b''.join((source.parent/m.decode()).read_bytes() for m in re.findall(rb'^#include "([^"/]+\.cpp)"',data,re.M))
  key=hashlib.sha256(common+data+included+' '.join(flags).encode()).hexdigest()[:24]
  directory=ROOT/'work/build/native-menu-resources'/key;directory.mkdir(parents=True,exist_ok=True)
  obj=directory/f'{name}.o'
  if not obj.exists():
   temporary=obj.with_suffix('.tmp.o')
   subprocess.run([compiler,*flags,'-c',str(source),'-o',str(temporary)],check=True)
   temporary.replace(obj)
  print(obj)
if __name__=='__main__':main()
