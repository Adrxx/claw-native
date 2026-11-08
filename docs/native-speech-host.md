# Native shared dialog host

ClawNativeSpeech owns the nine shared EnemySpeechRuntime globals and creates
both registered dialog actors through the verified source named creator profile
(id0,x0,y0,z1000,flags40000). Registration occurs on their scheduled state0
callbacks; there is no eager replacement tick. Claw48c630 and NPC48cc60 remain
separate source profiles. Source speech queue/cancel/equality/death calls route
through this one scope, including cancellation from ordinary actor destruction.

The scene scheduler supplies the actual stage delta. Actor, primary, settings,
speaker and player fields remain raw heap views. Player callbacks publish the
borrowed actor/state for speech gating without re-entering Swift's runtime cache.
Source queues and controllers preserve busy/force gates, sound replacement,
follow/depth writes and sound-pool duration. Voice requests retain the exact
4b45f0 parameters and enter the existing native audio transport.

The audio host exposes only sound+10 and pool+28 metadata spans, using its actual
loaded resource/pool tokens and source-loaded durations. CoreAudio buffers and
backend pointer graphs stay private. Native PCM/resampling/mixing remains a
platform adapter; hearing and original DirectSound timing identity are unproved.

Integration found42 nested Level1 WAVs excluded by the previous flat filesystem
loader. Canonical nested names such as LEVEL_OFFICER_00340014 now resolve their
original WAV files. This is explicit filesystem namespace transport, not a claim
that the whole original sound-registry enumerator has been connected. The native
host currently loads170 CLAW/GAME/Level1 WAVs; other levels are not instantiated.

Root independently reran EnemySpeechRuntime:1256 complete original calls,
3057 ordered full snapshots and3684 instruction addresses, including all42
original humanoid caller histories and48 source CRT RNG steps. Native ASAN
integration visits all42 real WWD humanoids through ordinary frames; those
positions and invulnerability are synthetic. It observes15 actual NPC queue
calls and7 scheduled voice requests, with no unresolved humanoid/speech services.
An explicit forced Claw name request separately reaches the scheduled player
profile and actual WAV duration. This does not prove every original sound trigger
or all in-level dialog events. Source game startup/settings initialization,
remaining sound/ambient trigger actors, music and whole-game acceptance remain.

A separate native progression test begins at the actual spawn and uses only
walk, jump and Up input through ordinary frames. It enters the actual Level1
ladder at x1408..1471, observes states4/27/24 and ascends from y4794 to y4291.
No placement, forced climbing state or direct climb call is used in that test.
Simulator climbing acceptance remains separate from this headless evidence.
