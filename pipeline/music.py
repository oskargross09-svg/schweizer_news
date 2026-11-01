"""Original background music bed: calm chord pad + soft pulse (synthesised, no licence issues)."""
import numpy as np

SR = 48000
PROGRESSIONS = [
    [[110.0, 164.81, 220.0, 261.63], [87.31, 130.81, 174.61, 220.0], [130.81, 196.0, 261.63, 329.63], [98.0, 146.83, 196.0, 246.94]],
    [[146.83, 220.0, 293.66, 349.23], [116.54, 174.61, 233.08, 293.66], [87.31, 130.81, 174.61, 220.0], [130.81, 196.0, 261.63, 329.63]],
    [[98.0, 146.83, 196.0, 233.08], [130.81, 196.0, 261.63, 311.13], [116.54, 174.61, 233.08, 293.66], [87.31, 130.81, 174.61, 220.0]],
]


def bed(total, seed=0, morning=False):
    rng = np.random.default_rng(seed)
    chords = PROGRESSIONS[seed % len(PROGRESSIONS)]
    bpm = 112 if morning else 118
    t = np.arange(int(total * SR)) / SR
    beat = 60 / bpm
    bar = beat * 4
    out = np.zeros_like(t)
    i = 0
    while i * bar < total:
        s0 = i * bar
        m = (t >= s0) & (t < s0 + bar + 0.3)
        tt = t[m] - s0
        env = np.minimum(1, tt / 0.25) * np.exp(-tt * 0.35)
        for f in chords[i % len(chords)]:
            out[m] += 0.06 * env * np.sin(2 * np.pi * f * tt) + 0.02 * env * np.sin(2 * np.pi * 2 * f * tt)
        i += 1
    n = int(0.12 * SR)
    tt = np.arange(n) / SR
    for k in range(int(total / (beat / 2))):
        i0 = int(k * beat / 2 * SR)
        if i0 + n > len(t):
            break
        out[i0:i0 + n] += (0.05 if k % 2 == 0 else 0.025) * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 30)
        out[i0:i0 + n] += 0.008 * rng.standard_normal(n) * np.exp(-tt * 80)
    return out.astype(np.float32)
