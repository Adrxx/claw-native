# Reproducible local research

All generated tools, original binaries/assets and build products are ignored.
The source checkout no longer needs the previous chat's research directory.
Use Xcode command line tools, Node/npm, Python 3, `make`, `git`, `curl`, `unzip`
and 7-Zip (`7zz`) on macOS ARM64. Python requirements pin Unicorn, Capstone and
CMake; npm's lockfile pins REA 6.3.0 and its dependency graph.

```sh
xcrun clang++ -std=c++17 -c Sources/PIDRaster.cpp -o work/PIDRaster.o
xcrun clang++ -std=c++17 -c Sources/PIDSurfaceRaster.cpp -o work/PIDSurfaceRaster.o
./scripts/bootstrap-research.sh
python3 scripts/bootstrap-tools.py
export GHIDRA_INSTALL_DIR="$PWD/work/tools/ghidra_12.1.4_PUBLIC"
export JAVA_HOME="$PWD/work/tools/jdk-21.0.12.1+1/Contents/Home"
./scripts/rea.sh doctor --provider ghidra --json
```

`research/tools.json` pins archive URLs and SHA-256 checksums for Ghidra 12.1.4
and Temurin JDK 21.0.12.1+1. The installer verifies archives before extraction
and builds Ghidra's decompiler for macOS ARM64 with two jobs. To reuse downloaded
archives, pass `--ghidra-archive PATH --jdk-archive PATH`; these are explicit
inputs, not hardcoded dependencies. REA's local bounded PE-detection fix is
applied and regression-checked by scripts/patch-rea.mjs after npm installation.
It preserves the PE signature fix recorded in docs/rea-short-dos-header.patch.

## Original references

The source pages and downloaded archive hashes are in
`docs/original-reference-manifest.json`. Retrieve references only for local
research; do not upload or commit the resulting executables or assets.

```sh
mkdir -p Original
curl -fL https://captainclaw.net/dl/claw10.zip -o Original/claw10.zip
unzip -n Original/claw10.zip -d Original/claw10
curl -fL https://captainclaw.net/dl/claw_rip.zip -o Original/claw_rip.zip
unzip -n Original/claw_rip.zip -d Original/claw-rip
7zz x -y -oOriginal/claw-rip/installer Original/claw-rip/setup.exe
./scripts/bootstrap-unshield.sh
work/unshield-build/src/unshield -d Original/claw-rip/files x Original/claw-rip/installer/Disk1/data1.cab
# Canonical original-disc REZ, separately recovered and fingerprinted below:
python3 scripts/extract-rez.py Original/claw-disc/files/DATA/CLAW.REZ Original/cd-assets --all > work/cd-asset-manifest.json
python3 scripts/prepare-reference-assets.py Original/cd-assets
```

The legacy rip extraction above is a historical reference. The current canonical
asset input is Original/claw-disc/files/DATA/CLAW.REZ, SHA256
b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596
(118033115 bytes). See original-disc-provenance.json for the disc archive,
sector conversion and comparison. Obtain/extract that disc input before running
the canonical extraction command; the legacy rip does not produce that path.
The two inputs differ outside the active Level1/shared gameplay assets.

The extractor reads REZ directory records and validates bounds and filenames.
Without --all it extracts only CLAW and LEVEL1; the native scene also requires
the GAME images/ANI/audio, so use --all in the recipe above. The preparation
script copies those shared resources and Level1 by default; --all-levels also
prepares all14 retail levels for broader integration, which remains unfinished.
The format was consulted in OpenClaw libwap at
commit 5ee5740ca98377c76b13b50c84f610b0066a4717 (GPL-3.0); this is asset-reference
work, not recovered game code. WWD uses the same reference for header/plane
layout, with native Swift zlib decompression and bounded reads. Optional source
checkout: `git clone https://github.com/pjasicek/OpenClaw.git work/openclaw-reference`,
then check out the pinned commit. No gameplay source has been integrated.

The CD rip EXE has a small .text and large .rsrc section, unlike v1.0's engine
image. Its engine layout has not been established; do not reuse v1.0 addresses
on it. Its REZ assets are a separate reference, not proven v1.0 asset identity.

## Differential and asset checks

```sh
xcrun clang++ -std=c++17 -dynamiclib Sources/SimpleAnimation.cpp -o work/libClawLogic.dylib
work/test-env/bin/python Tests/compare_simple_animation.py Original/claw10/CLAW.EXE work/libClawLogic.dylib
xcrun clang++ -std=c++17 -dynamiclib Sources/AnimationOperations.cpp -o work/libAnimationOperations.dylib
work/test-env/bin/python Tests/compare_animation_operations.py Original/claw10/CLAW.EXE work/libAnimationOperations.dylib
xcrun clang++ -std=c++17 -dynamiclib Sources/AnimationEngine.cpp -o work/libAnimationEngine.dylib
work/test-env/bin/python Tests/compare_animation_engine.py Original/claw10/CLAW.EXE work/libAnimationEngine.dylib --assets Original/cd-assets
xcrun clang++ -std=c++17 -c Sources/AnimationEngine.cpp -o work/AnimationEngine.o
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h Sources/ClawAssets.swift Tests/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o -lc++ -o work/asset-tests
work/asset-tests Original/cd-assets
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h Sources/ClawAssets.swift Sources/ClawAnimationPlayback.swift Tests/Animation/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o -lc++ -o work/animation-tests
work/animation-tests Original/cd-assets
xcrun clang++ -std=c++17 -c Sources/TileCollision.cpp -o work/TileCollision.o
xcrun clang++ -std=c++17 -c Sources/CollisionResponse.cpp -o work/CollisionResponse.o
xcrun swiftc -import-objc-header Sources/Claw-Bridging-Header.h Sources/ClawAssets.swift Sources/ClawWorld.swift Sources/ClawCollision.swift Tests/World/main.swift work/AnimationEngine.o work/PIDRaster.o work/PIDSurfaceRaster.o work/TileCollision.o work/CollisionResponse.o -lc++ -lz -o work/world-tests
work/world-tests Original/cd-assets
```

Full recovered physics, target-velocity and movement comparisons are reproduced
in docs/collision-and-player.md. Tests/original_v10.py rejects unmatched binaries,
executes the original CRT precision initializer and verifies function return;
it does not replace original gameplay callees.

Use `--reference crazyhook` explicitly for the previous input; default is v1.0.
`inspect-pe.py` produces fingerprints/mapped sections and bounded disassembly:
`work/test-env/bin/python scripts/inspect-pe.py Original/claw10/CLAW.EXE --start 0x4c82a0 --size 0x260`.
