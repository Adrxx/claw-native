# README media

Captured on 7 November 2026 from the native Release app using local game data. All launches used `--mute`; the clips have no audio. These are captures of the running game, not extracted assets. The repository root README is maintained separately.

| Files | Content and capture method |
| --- | --- |
| `menu.png` | Main menu, Mac Catalyst Release. |
| `level1.png` | La Roca, Level 1, with delivered movement input. |
| `later-level.png` | The Township, Level 5, jumping. |
| `boss.png` | Katherine, Level 4, during combat with the boss meter visible. The existing diagnostic position fixture placed Claw beside the real BossStager; delivered movement activated it and delivered attack input followed. |
| `custom-level.png` | Treasure Island, the local Claw Recluse sample, selected through Single Player → Load Custom Level. |
| `crazyhook.png` | Just Keep Calm, selected through the same Load Custom Level menu with its companion files. |
| `checkpoint-slots.png` | The checkpoint overlay shared with the iPad three-finger gesture, with all three slots filled. Opened on Mac with Command+Option+Shift+3. |
| `gameplay.mp4`, `gameplay.gif` | One continuous 17.6-second retail Level 1 take: three soldiers killed with the sword, platform jumps, a broken crate, collected treasure, a pistol shot, damage taken and survival. Entered through New Game and reached this section by running and climbing; no position fixtures, teleports, checkpoint restores or cheats. |

The six full-view Mac game pictures use the app's next-presented-frame capture (`s <name>`), enlarged from 640 × 480 to 1280 × 960 with nearest-neighbor scaling, with no window chrome. The checkpoint picture is a 1280 × 960 central crop of the captured native window, focused on the chooser and excluding the macOS sharing badge; SwiftUI overlays are not part of the original game surface. No overlays or game elements were composited into the captures.

Build: `make project`, then `scripts/run-mac.sh --version-only`, using `work/MacCatalyst/Build/Products/Release-maccatalyst/Claw.app`. Input used `scripts/real_input.py` and `scripts/post-window-input.swift`, with each key transition confirmed in the app's input log. The gameplay clip samples every four game frames through the existing frame gate (15 pictures per second); it retains gameplay order and contains no cuts. FFmpeg encodes H.264/yuv420p MP4 with `-crf 24 -movflags +faststart`. The 640-pixel-wide GIF uses 15 fps, a reduced palette and GIFsicle optimization with lossy compression to stay below 6 MB. Temporary frame dumps are removed after encoding. Gameplay capture commands, reviewed contact sheets and state evidence are in ignored `work/repo-readme-video/`; earlier still-image capture evidence is in `work/readme-media/`. The full encoded take was reviewed frame by frame on contact sheets: sword defeat animations occur around 0.6, 9.5 and 15.6 seconds. Claw finishes alive with 65 health after collecting a health pickup.
