#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work/boss-stager-player-reset
# Retained APIs share translation units with other gameplay. Link their real
# providers too; no unresolved-symbol bypass or guest implementation is used.
sources=(
  Sources/BossStagerPlayerResetRuntime.cpp
  Sources/BossStagerPlayerResetOwner.cpp
  Sources/LiftThrowRuntime.cpp
  Sources/PowerupObjectRuntime.cpp
  Sources/RauxRuntime.cpp
  Sources/RatBombCanonical.cpp
  Sources/ActorAnimationRuntime.cpp
  Sources/AnimationEngine.cpp
  Sources/AnimationOperations.cpp
  Tests/boss_stager_player_reset_owner.cpp
  Sources/ActorResourceBindings.cpp
  Sources/ActorWrapperRuntime.cpp
  Sources/CommonEnemyEntries.cpp
  Sources/EnemyMotionAux.cpp
  Sources/GenericEnemy.cpp
  Sources/ItemPickupRuntime.cpp
  Sources/PlayerPhysics.cpp
  Sources/PickupPointsRuntime.cpp
  Sources/PlayerLocomotion.cpp
  Sources/PlayerDamage.cpp
  Sources/PlayerPowerupRuntime.cpp
  Sources/PlayerAttackInput.cpp
  Sources/SceneActorRuntime.cpp
  Sources/WorldLootRuntime.cpp
  Sources/GenericEnemyStates.cpp
  Sources/HumanEnemy.cpp
  Sources/PlayerEngine.cpp
  Sources/PlayerInputDispatch.cpp
  Sources/SpriteGeometry.cpp
  Sources/GameTiming.cpp
  Sources/WorldObjectRuntime.cpp
  Sources/TileCollision.cpp
 )
flavor="${1:-O2}"
flags=(-O2)
if [[ "$flavor" == "sanitize" ]]; then
  flags=(-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer)
elif [[ "$flavor" != "O2" ]]; then
  echo "usage: $0 [O2|sanitize]" >&2
  exit 2
fi
clang++ -std=c++17 -I Sources "${flags[@]}" "${sources[@]}" -o "work/boss-stager-player-reset/owner-$flavor"
"work/boss-stager-player-reset/owner-$flavor"
