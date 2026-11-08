"""Build the frozen composition dependency closure and check its public ABI.
Run from the repo root; artifacts remain in ignored work/scene-startup-validation.
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/scene-startup-validation'
WORK.mkdir(parents=True,exist_ok=True)
SOURCES=['Sources/ActorAnimationRuntime.cpp', 'Sources/ActorDestruction.cpp', 'Sources/ActorResourceBindings.cpp', 'Sources/ActorWrapperRuntime.cpp', 'Sources/AmbientAudioBackendRuntime.cpp', 'Sources/AnimationEngine.cpp', 'Sources/AnimationOperations.cpp', 'Sources/AudioEvents.cpp', 'Sources/AudioManagerLifecycleRuntime.cpp', 'Sources/BootyProgressionRuntime.cpp', 'Sources/MovieStateCleanupRuntime.cpp', 'Sources/BootyResultsRuntime.cpp', 'Sources/CArrayRuntime.cpp', 'Sources/CheckpointTimerRuntime.cpp', 'Sources/EnemySpeechRuntime.cpp', 'Sources/GameImageRuntime.cpp', 'Sources/GameTiming.cpp', 'Sources/GraphicsManagerConstructionRuntime.cpp', 'Sources/GraphicsManagerLifecycleRuntime.cpp', 'Sources/ImageRegistryRuntime.cpp', 'Sources/PIDSurfaceRaster.cpp', 'Sources/PaletteResourceRuntime.cpp', 'Sources/PickupPointsRuntime.cpp', 'Sources/SceneActorRuntime.cpp', 'Sources/SceneCameraRuntime.cpp', 'Sources/SceneDisplayRuntime.cpp', 'Sources/SceneLifecycleRuntime.cpp', 'Sources/SceneStartupCompositionRuntime.cpp', 'Sources/SimpleAnimation.cpp', 'Sources/SinglePlayerSceneRuntime.cpp', 'Sources/SoundTriggerLogicRuntime.cpp', 'Sources/SpatialGridRuntime.cpp', 'Sources/SpeechActor.cpp', 'Sources/SpriteGeometry.cpp', 'Sources/StackedActorLifecycleRuntime.cpp', 'Sources/WorldFileRuntime.cpp', 'Sources/WorldObjectRuntime.cpp', 'Sources/WorldPlaneRuntime.cpp']
common=['clang++','-std=c++17','-Wall','-Wextra','-Werror','-ffp-contract=off','-I',str(ROOT/'Sources')]
sources=[str(ROOT/p)for p in SOURCES]
support=[s for s in sources if not s.endswith('/SceneStartupCompositionRuntime.cpp')]
subprocess.run(common+['-O2','-dynamiclib']+support+['-o',str(WORK/'libOrdinarySupport.dylib')],check=True)
subprocess.run(common+['-O2','-c',str(ROOT/'Sources/SceneStartupCompositionRuntime.cpp'),'-o',str(WORK/'composition.o')],check=True)
subprocess.run(common+['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(ROOT/'Tests/exact_sized_scene_startup_composition.cpp')]+sources+['-lz','-o',str(WORK/'exact-sized-replay')],check=True)
header=WORK/'header-check.c';header.write_text('#include "SceneStartupCompositionRuntime.h"\nint main(void){ClawSceneStartupCompositionContext c={0};return (int)c.fault;}\n')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'Sources'),'-c',str(header),'-o',str(WORK/'header-check.o')],check=True)
module=WORK/'module.modulemap';module.write_text('module SceneStartupCompositionRuntime { header "'+str(ROOT/'Sources/SceneStartupCompositionRuntime.h')+'" export * }\n')
swift=WORK/'header-check.swift';swift.write_text('import SceneStartupCompositionRuntime\nvar c = ClawSceneStartupCompositionContext()\nc.maximumOperations = 1000000\n')
subprocess.run(['swiftc','-typecheck','-I',str(WORK),str(swift)],check=True)
manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES}
manifest['Sources/SceneStartupCompositionRuntime.h']=hashlib.sha256((ROOT/'Sources/SceneStartupCompositionRuntime.h').read_bytes()).hexdigest()
(WORK/'source-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS C11 header, C++17/Werror source, Swift public import, current '+str(len(SOURCES))+'-source ASAN/UBSAN closure',flush=True)
