#include "AudioEvents.h"
#include <cstring>
namespace {
int64_t signedWord(uint32_t x) {
    return x < 0x80000000u ? int64_t(x) : int64_t(x) - 0x100000000LL;
}
uint32_t ftolLow(double value) {
    uint64_t bits;
    std::memcpy(&bits, &value, 8);
    int exponent = int((bits >> 52) & 0x7ff) - 1023;
    if (exponent < 0 || exponent >= 63)
        return 0;
    uint64_t magnitude = (bits & 0x000fffffffffffffULL) | 0x0010000000000000ULL;
    magnitude = exponent >= 52 ? magnitude << (exponent - 52) : magnitude >> (52 - exponent);
    return bits >> 63 ? 0u - uint32_t(magnitude) : uint32_t(magnitude);
}
uint32_t scaledVolume(uint32_t volume) {
    if (volume == 100)
        return 100;
    volatile double first = double(signedWord(volume)) * double(0.01f);
    volatile double final = first * 100.;
    return ftolLow(final);
}

uint32_t call(ClawAudioBackend backend, uint32_t buffer, uint32_t method, uint32_t a, uint32_t b = 0, uint32_t c = 0) {
    return backend.directSound(backend.context, buffer, method, a, b, c);
}
void report(ClawAudioBackend backend, uint32_t code, uint32_t result) {
    if (backend.report)
        backend.report(backend.context, code, result);
}
} // namespace

extern "C" uint32_t claw_audio_play_direct(const ClawAudioRouting *routing, const ClawAudioSound *sound,
                                           ClawAudioRequest request, ClawAudioHost host) {
    if (!routing->managerAvailable)
        return 0;
    return host.play(host.context, sound->voicePoolToken, request);
}
extern "C" uint32_t claw_audio_play_name(const ClawAudioRouting *routing, ClawAudioRegistry registry, uint32_t name,
                                         ClawAudioHost host) {
    if (registry.disabled)
        return 0;
    ClawAudioSound sound{};
    host.resolve(host.context, registry.token, name, &sound);
    if (!sound.resourceToken || !routing->managerAvailable)
        return 0;
    return host.play(host.context, sound.voicePoolToken, {routing->masterVolume, 0, 0, 0});
}
extern "C" uint32_t claw_audio_play_spatial(const ClawAudioRouting *routing, const ClawAudioSound *sound,
                                            uint32_t sourceX, uint32_t referenceX, uint32_t clampDistance,
                                            uint32_t panDistance, ClawAudioHost host, uint32_t *fault) {
    if (fault)
        *fault = 0;
    if (!routing->managerAvailable)
        return 0;
    if (signedWord(referenceX) <= 0)
        referenceX = routing->defaultReferenceX;
    if (signedWord(clampDistance) <= 0)
        clampDistance = routing->sceneWidth << 2;
    if (signedWord(panDistance) <= 0)
        panDistance = uint32_t(signedWord(routing->sceneWidth) / 3);
    uint32_t offset = sourceX - referenceX;
    if (signedWord(offset) < 0) {
        uint32_t magnitude = 0u - offset;
        if (signedWord(magnitude) >= signedWord(clampDistance) || signedWord(magnitude) >= signedWord(panDistance))
            offset = 0u - (signedWord(clampDistance) < signedWord(panDistance) ? clampDistance : panDistance);
    } else if (signedWord(offset) >= signedWord(clampDistance) || signedWord(offset) >= signedWord(panDistance))
        offset = signedWord(clampDistance) < signedWord(panDistance) ? clampDistance : panDistance;
    int64_t numerator = signedWord(offset * 100u), denominator = signedWord(panDistance);
    if (!denominator) {
        if (fault)
            *fault = 1;
        return 0;
    }
    if (numerator == -2147483648LL && denominator == -1) {
        if (fault)
            *fault = 2;
        return 0;
    }
    uint32_t pan = uint32_t(numerator / denominator);
    return host.play(host.context, sound->voicePoolToken, {scaledVolume(routing->masterVolume), pan, 0, 0});
}
extern "C" uint32_t claw_audio_queue_speech(ClawAudioRouting *routing, uint32_t sound, uint32_t force) {
    if (!sound || !routing->speechActorPresent || (!force && routing->speechBusy) || !routing->speechLogicPresent)
        return 0;
    if (!force && routing->playerPresent &&
        (routing->playerLogicState == 28 || routing->playerLogicState == 5005 || routing->playerLogicState == 5004))
        return 0;
    routing->queuedSpeechToken = sound;
    routing->speechLogicState = 1001;
    return 1;
}
extern "C" uint32_t claw_audio_queue_speech_name(ClawAudioRouting *routing, uint32_t name, uint32_t force,
                                                 ClawAudioHost host) {
    if (!name || !routing->speechActorPresent)
        return 0;
    ClawAudioSound sound{};
    host.resolve(host.context, routing->speechRegistryToken, name, &sound);
    if (!sound.resourceToken)
        return 0;
    return claw_audio_queue_speech(routing, sound.resourceToken, force);
}
extern "C" int32_t claw_audio_volume_table(uint32_t index) {
    return claw_audio_volume_table_value(index);
}
extern "C" uint32_t claw_audio_play_pool(ClawAudioPool pool, ClawAudioRequest request, ClawAudioBackend backend) {
    if (!pool.deviceAvailable)
        return 0;
    ClawAudioVoice *voice = backend.selectVoice(backend.context, pool.token);
    if (!voice)
        return 0;
    // Original table reads are unchecked. Reject invalid indices explicitly in
    // the portable API; parity applies to the stated original table domain.
    if (request.volume > 100 || signedWord(request.pan) < -100 || signedWord(request.pan) > 100)
        return 0;
    uint32_t buffer = voice->words[3];
    uint32_t error = call(backend, buffer, 0x3c, uint32_t(claw_audio_volume_table_value(request.volume)));
    bool volumeOK = !error;
    if (error)
        report(backend, 0xaf, 1);
    uint32_t magnitude = request.pan < 0x80000000u ? request.pan : 0u - request.pan;
    uint32_t mappedPan = uint32_t(claw_audio_volume_table_value(100 - magnitude));
    if (request.pan < 0x80000000u)
        mappedPan = 0u - mappedPan;
    error = call(backend, buffer, 0x40, mappedPan);
    bool panOK = !error;
    if (error)
        report(backend, 0xf6, 1);
    uint32_t frequency = uint32_t(signedWord(request.pitchPercent * voice->words[6]) / 100) + voice->words[6];
    if (frequency > 99999)
        frequency = 99999;
    if (frequency < 101)
        frequency = 101;
    error = call(backend, buffer, 0x44, frequency);
    bool frequencyOK = !error;
    if (error)
        report(backend, 0x12a, error);
    else
        voice->words[9] = frequency;
    voice->words[5] = request.looping ? voice->words[5] | 1u : voice->words[5] & 0xfffffffeu;
    error = call(backend, buffer, 0x30, 0, 0, voice->words[5]);
    bool playOK = !error;
    if (error)
        report(backend, 0x5f, 1);
    return volumeOK && panOK && frequencyOK && playOK;
}
