#include "SpeechActor.h"
#include <cstring>
namespace {
int32_t signedWord(uint32_t value) {
    int32_t result;
    std::memcpy(&result, &value, sizeof result);
    return result;
}
} // namespace
extern "C" uint32_t claw_speech_actor_update(ClawSpeechActor *s, ClawSpeechContext *c, ClawSpeechHost host) {
    uint32_t *a = s->actor, *l = s->logic;
    switch (l[0x1c / 4]) {
    case 0: {
        a[0x40 / 4] |= 1;
        a[8 / 4] |= 0xc0003;
        a[0xd0 / 4] = 0x4000000;
        ClawSpeechImage image{};
        host.resolveImage(host.context, c->imageRegistryToken, 0x52c580, &image);
        a[0x170 / 4] = image.token;
        if (image.token) {
            a[0x16c / 4] = image.firstIndex;
            a[0x174 / 4] = signedWord(image.firstIndex) <= signedWord(image.lastIndex) ? image.firstFrameToken : 0;
        }
        l[0x1c / 4] = 5;
        c->registeredActorToken = c->actorToken;
        break;
    }
    case 5:
        c->busy = 0;
        a[0x40 / 4] |= 1;
        break;
    case 29:
        c->registeredActorToken = 0;
        break;
    case 1001:
        if (!a[0x184 / 4] || !c->speechEnabled) {
            l[0x1c / 4] = 5;
            a[0x184 / 4] = 0;
            break;
        }
        l[0x1c / 4] = 15;
        l[0x130 / 4] = c->queuedSoundDuration;
        if (c->managerAvailable) {
            uint32_t volume = c->speechVolume + 20;
            if (signedWord(volume) >= 100)
                volume = 100;
            host.play(host.context, c->queuedSoundPoolToken, volume, 0, 0, 0);
        }
        break;
    case 15:
        if (!c->playerPresent)
            break;
        c->busy = 1;
        a[0x40 / 4] &= ~1u;
        a[0x4c / 4] = c->playerX;
        a[0x50 / 4] = c->playerY + c->playerHeight - 30;
        if (a[0x64 / 4] != c->playerLayer + 1) {
            a[0x64 / 4] = c->playerLayer + 1;
            a[8 / 4] |= 0x20000;
        }
        if (c->playerLogicState == 5004 || c->playerLogicState == 5005)
            l[0x130 / 4] = 0;
        l[0x130 / 4] = c->stageDelta < l[0x130 / 4] ? l[0x130 / 4] - c->stageDelta : 0;
        if (!l[0x130 / 4]) {
            a[0x184 / 4] = 0;
            l[0x1c / 4] = 5;
        }
        break;
    default:
        break;
    }
    return 1;
}
