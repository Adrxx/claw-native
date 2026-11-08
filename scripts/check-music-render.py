"""Check the app's offline music renders (written with --music-render DIR).

For every render: the WAV is non-silent; every note-on the native sequencer
scheduled sits on its XMIDI event time (120 Hz clock) over the loop; the audio
onsets line up with the XMIDI note-on times within one game frame (1/60 s);
and the second pass of the loop repeats the first. Prints one JSON line last.
Usage: check-music-render.py DIR [--expect N]  (N = minimum number of renders)
"""
import array
import bisect
import json
import math
import sys
import wave
from pathlib import Path

FRAME = 1 / 60  # one game frame, seconds
HOP = 64


def song(path):
    data = Path(path).read_bytes()

    def find(start, end):
        at = start
        while at + 8 <= end:
            tag, count = data[at:at + 4], int.from_bytes(data[at + 4:at + 8], "big")
            body = at + 8
            if tag in (b"FORM", b"CAT "):
                found = find(body + 4, body + count)
                if found:
                    return found
            if tag == b"EVNT":
                return data[body:body + count]
            at = body + count + (count & 1)
        return None

    stream = find(0, len(data))
    i = tick = end = 0
    notes = []

    def vlq():
        nonlocal i
        value = 0
        while True:
            b = stream[i]
            i += 1
            value = value * 128 + (b & 127)
            if b < 128:
                return value

    while i < len(stream):
        status = stream[i]
        i += 1
        if status < 128:
            tick += status
            continue
        if status == 255:
            kind = stream[i]
            i += 1
            n = vlq()
            i += n
            if kind == 47:
                end = max(end, tick)
                break
        elif status in (240, 247):
            i += vlq()
        else:
            kind = status >> 4
            if kind in (12, 13):
                i += 1
            else:
                key, velocity = stream[i], stream[i + 1]
                i += 2
                if kind == 9:
                    length = vlq()
                    end = max(end, tick + length)
                    if velocity:
                        notes.append((tick, status & 15, key))
    return notes, max(tick, end)


def read_wav(path):
    with wave.open(str(path)) as w:
        rate, channels, frames = w.getframerate(), w.getnchannels(), w.getnframes()
        raw = array.array("h", w.readframes(frames))
    mono = raw[0::2] if channels == 1 else array.array("h", (a + b >> 1 for a, b in zip(raw[0::2], raw[1::2])))
    return rate, mono


def envelope(mono):
    """Log energy of the first difference per hop: attacks stand out."""
    out = []
    previous = 0
    for start in range(0, len(mono) - HOP, HOP):
        energy = 0
        for value in mono[start:start + HOP]:
            d = value - previous
            previous = value
            energy += d * d
        out.append(math.log10(energy / HOP + 1.0))
    return out


def onset_strength(env, back=16):
    """Rise of the log energy over the mean of the previous ~20 ms."""
    strength = [0.0] * len(env)
    for k in range(back, len(env)):
        strength[k] = max(0.0, env[k] - sum(env[k - back:k - 2]) / (back - 2))
    return strength


def sharp_strength(env):
    """Rise over the previous four hops (6 ms): used for the lag search."""
    strength = [0.0] * len(env)
    for k in range(4, len(env)):
        strength[k] = max(0.0, env[k] - max(env[k - 4:k]))
    return strength


def pick(strength, hop_s):
    """Strong onsets: local maxima above max(0.8, a quarter of the strongest),
    merged within 50 ms keeping the strongest."""
    threshold = max(0.8, 0.25 * max(strength))
    peaks = []
    for h in range(1, len(strength) - 1):
        if strength[h] > threshold and strength[h] >= strength[h - 1] and strength[h] > strength[h + 1]:
            if peaks and (h - peaks[-1]) * hop_s < 0.05:
                if strength[h] > strength[peaks[-1]]:
                    peaks[-1] = h
                continue
            peaks.append(h)
    return peaks


def check(render, xmi, wav):
    notes, ticks = song(xmi)
    rate, loop_frames, total = render["sample_rate"], render["loop_frames"], render["frames"]
    result = {"render": wav.name, "notes_per_loop": len(notes), "loop_seconds": round(ticks / 120, 3),
              "rendered_seconds": round(total / rate, 3), "game_loops": render.get("game_loops")}
    # 1. Scheduling: every expected note-on, every loop pass, exact frame.
    expected = []
    k = 0
    while k * loop_frames < total:
        for tick, channel, key in notes:
            frame = math.floor(tick * rate / 120 + 0.5) + k * loop_frames
            if frame < total:
                expected.append((frame, channel, key))
        k += 1
    logged = [tuple(x) for x in render["note_on_frames"]]
    exact = sum(1 for a, b in zip(sorted(expected), sorted(logged)) if a == b)
    result["scheduled"] = {"expected": len(expected), "logged": len(logged), "exact": exact, "loop_passes": k}
    # 2. Non-silence.
    rate_wav, mono = read_wav(wav)
    peak = max(abs(v) for v in mono) / 32768
    windows = [mono[i:i + rate_wav // 10] for i in range(0, len(mono) - rate_wav // 10, rate_wav // 10)]
    loud = sum(1 for w in windows if math.sqrt(sum(v * v for v in w[::8]) / len(w[::8])) / 32768 > 0.001)
    result["audio"] = {"peak": round(peak, 4), "audible_tenths": loud, "tenths": len(windows)}
    # 3. Audio onsets against the XMIDI note-on times.
    env = envelope(mono)
    strength = onset_strength(env)
    hop_s = HOP / rate_wav
    expected_s = sorted({f / rate for f, _, _ in expected})
    sharp = sharp_strength(env)
    train = sorted({int(t / hop_s) for t in expected_s if int(t / hop_s) < len(strength)})
    best, scores = None, {}
    for lag in range(-int(0.3 / hop_s), int(0.3 / hop_s) + 1):
        score = sum(sharp[h + lag] for h in train if 0 <= h + lag < len(sharp))
        scores[lag] = score
        if best is None or score > scores[best]:
            best = lag
    ordered = sorted(scores.values())
    median = ordered[len(ordered) // 2] or 1e-9
    pruned = pick(strength, hop_s)
    def near(t):
        i = bisect.bisect_left(expected_s, t)
        return min([abs(t - expected_s[j]) for j in (i - 1, i) if 0 <= j < len(expected_s)] or [9])
    matched = sum(1 for h in pruned if near(h * hop_s) <= FRAME)
    result["onsets"] = {"best_lag_ms": round(best * hop_s * 1000, 2), "peak_to_median": round(scores[best] / median, 2),
                        "detected": len(pruned), "within_one_frame": matched,
                        "precision": round(matched / max(1, len(pruned)), 3)}
    # 4. Loop: the second pass repeats the first (envelope correlation).
    loop_hops, span = int(loop_frames / rate * rate_wav / HOP), int(min(5.0, ticks / 120) / hop_s)
    a, b = env[:span], env[loop_hops:loop_hops + span]
    if len(b) == span and span > 10:
        ma, mb = sum(a) / span, sum(b) / span
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) or 1e-9
        corr = num / den
    else:
        corr = None
    result["loop"] = {"envelope_correlation": corr and round(corr, 4), "compared_seconds": round(span * hop_s, 2)}
    ok = (exact == len(expected) == len(logged) and k >= 2 and peak > 0.01 and loud > len(windows) // 2
          and abs(best * hop_s) <= FRAME and scores[best] / median > 1.5 and matched / max(1, len(pruned)) >= 0.8
          and corr is not None and corr > 0.9)
    result["status"] = "pass" if ok else "fail"
    return result


def main():
    directory = Path(sys.argv[1])
    minimum = int(sys.argv[sys.argv.index("--expect") + 1]) if "--expect" in sys.argv else 1
    results = []
    for log in sorted(directory.glob("*.json")):
        render = json.loads(log.read_text())
        if "start" not in render and render.get("status") != "fail":
            continue
        if render.get("status") != "done":
            results.append({"render": log.name, "status": "fail", "error": render.get("error", "incomplete")})
            continue
        results.append(check(render, log.with_suffix(".xmi"), log.with_suffix(".wav")))
    status = "pass" if len(results) >= minimum and all(r["status"] == "pass" for r in results) else "fail"
    for r in results:
        print(json.dumps(r))
    print(json.dumps({"check": "music-render", "directory": str(directory), "renders": len(results), "status": status}))


if __name__ == "__main__":
    main()
