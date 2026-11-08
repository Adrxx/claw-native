#!/usr/bin/env python3
"""Install hash-pinned Ghidra/JDK locally, optionally using existing archives."""
import argparse,hashlib,json,subprocess,urllib.request,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--ghidra-archive',type=Path);p.add_argument('--jdk-archive',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];spec=json.loads((root/'research/tools.json').read_text());dst=root/'work/tools';dst.mkdir(parents=True,exist_ok=True)
for name,provided in [('ghidra',a.ghidra_archive),('jdk',a.jdk_archive)]:
 item=spec[name];archive=provided or dst/('ghidra.zip' if name=='ghidra' else 'jdk.tar.gz')
 if not archive.exists():urllib.request.urlretrieve(item['url'],archive)
 if hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()!=item['sha256']:raise ValueError('Archive hash mismatch: '+name)
 installed=dst/('ghidra_12.1.4_PUBLIC' if name=='ghidra' else 'jdk-21.0.12.1+1')
 if not installed.exists():
  subprocess.run(['ditto','-xk',str(archive),str(dst)] if name=='ghidra' else ['tar','-xzf',str(archive),'-C',str(dst)],check=True)
cpp=dst/'ghidra_12.1.4_PUBLIC/Ghidra/Features/Decompiler/src/decompile/cpp'
subprocess.run(['make','-j2','ghidra_opt','OSDIR=mac_arm_64','ARCH_TYPE=-arch arm64','ADDITIONAL_FLAGS=-mmacosx-version-min=11.0 -w'],cwd=cpp,check=True)
native=dst/'ghidra_12.1.4_PUBLIC/Ghidra/Features/Decompiler/os/mac_arm_64'
native.mkdir(parents=True,exist_ok=True)
shutil.copy2(cpp/'ghidra_opt',native/'decompile')
print('export GHIDRA_INSTALL_DIR="'+str(dst/'ghidra_12.1.4_PUBLIC')+'"')
print('export JAVA_HOME="'+str(dst/'jdk-21.0.12.1+1/Contents/Home')+'"')
