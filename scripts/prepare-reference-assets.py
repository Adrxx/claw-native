#!/usr/bin/env python3
"""Prepare app resources from an extracted original REZ, not the CrazyHook pack."""
import argparse,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('assets',type=Path);p.add_argument('--all-levels',action='store_true',help='Prepare all14 retail level assets for broader native integration');p.add_argument('--level',type=int,choices=range(1,15),help='Prepare one retail level');a=p.parse_args()
dst=Path(__file__).resolve().parents[1]/'App/GameData'
levels=range(1,15) if a.all_levels else [a.level or 1]
for rel in ['CLAW/IMAGES','CLAW/ANIS','GAME/IMAGES','GAME/ANIS','GAME/SOUNDS']+[f'LEVEL{level}/{kind}' for level in levels for kind in ['TILES','WORLDS','PALETTES']]:
 if not (a.assets/rel).is_dir():p.error('Missing '+rel)
for source,target in [('CLAW/IMAGES','IMAGES'),('CLAW/ANIS','ANIS'),('GAME','GAME')]+[(f'LEVEL{level}',f'LEVEL{level}') for level in levels]:
 shutil.copytree(a.assets/source,dst/target,dirs_exist_ok=True)
shutil.copy2(a.assets/'LEVEL1/PALETTES/MAIN.PAL',dst/'MAIN.PAL')
print('Prepared original reference assets:',dst)
