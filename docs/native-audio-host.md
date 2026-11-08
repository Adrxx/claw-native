# Native original-PCM effects

ClawNativeAudio composes recovered AudioPCMTransfer, AudioResourceRuntime and
AudioEvents with a native output host. Original disc WAVs are loaded through
the recovered mapped-file/PCM transfer path and voice-list routines. The local
app includes170 original Claw/Game/Level1 sound files; all seven PCM formats
found among the disc's1,147 WAVs are supported, including22255Hz mono8-bit.
These files remain ignored inputs, outside the source license/deliverables.

Player resource sound calls and animation sound events now dispatch through
this host. Resource name strings are recovered from the fingerprinted EXE;
32-bit sound/voice identities never cast native pointers. Duplicate voices
share decoded source samples but retain separate cursors, pitch, volume and
pan. Voice availability/status, stopped reuse, looping and lifetime follow
the recovered resource routines. Native audio renders stereo Float samples
through AVAudioSourceNode and CoreAudio.

Offline native checks pass for PCM decoding/rendering, natural completion,
reuse, overlapping voices, loop/stop, pitch and pan. The separate native output
check rendered10,752 callback frames,10,516 with nonzero original PCM. This is
output-path evidence; physical listening remains distinct. The coordinator also
independently reran the PCM suite, including144 real-disc cases across12WAVs
and all seven formats, plus the resource and routing suites.

The output replacement uses linear Float resampling, millibel gains and
clipping. DirectSound mixer/resampling and CoreAudio/Windows timing identity
are unproven. Master volume100 is an explicit host setting; current spatial
reference uses player X/world width until original camera/audio configuration
is recovered. Registry receiver resolution is limited by the player dependency
ABI. Stop-all is a native reset adapter. Speech actor ordering/creation, MIDI
music, movie audio and full audio configuration are still unconnected.
