"""Ses tasarımı: tamamı kodla sentezlenir (dış ses kütüphanesi yok).

- Sıcak müzik altlığı (F majör, I–vi–IV–V, elektrik piyano + pad + yumuşak ritim)
- Mutfak ambiyansı (filtrelenmiş gürültü + rastgele tabak/kaşık tıkırtıları)
- Bıçak tıkırtısı ritmi, whoosh geçişleri, kart "ding"leri, tava cızırtısı, kapanış çanı
- Seslendirme varsa (ses/vo/NN.mp3) müzik altında otomatik kısma (ducking)
"""
import os
import subprocess
import wave

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def lp(x, a):
    """Tek kutuplu alçak geçiren (a: 0..1, küçük = daha koyu)."""
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x)


def bp(x, lo, hi, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def hp(x, f, order=2):
    from scipy.signal import butter, sosfilt
    sos = butter(order, f, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------- müzik
def epiano(freq, dur, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = env_exp(n, 0.9) * (1 - np.exp(-t / 0.004))
    tine = np.sin(2 * np.pi * freq * t + 1.2 * env_exp(n, 0.15) * np.sin(2 * np.pi * freq * 2 * t))
    body = 0.35 * np.sin(2 * np.pi * freq * 2 * t) * env_exp(n, 0.3)
    return vel * e * (tine + body)


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            x += np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(2 * np.pi * 2 * ff * t + 0.3)
    a = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8)
    return lp(x * a, 0.08) / (len(freqs) * 3)


def kick(n=None):
    d = 0.35
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env_exp(n, 0.12)


def shaker():
    n = int(0.08 * SR)
    return hp(RNG.standard_normal(n), 6000) * env_exp(n, 0.02) * 0.5


def music(total, bpm=100, lift_ranges=(), calm_ranges=()):
    n = int(total * SR) + SR
    out = np.zeros((n, 2))
    beat = 60 / bpm
    bar = beat * 4
    # F – Dm – Bb – C
    prog = [(53, [65, 69, 72]), (50, [62, 65, 69]), (46, [58, 62, 65]), (48, [60, 64, 67])]
    arp_pat = [0, 1, 2, 1, 0, 2, 1, 2]
    t = 0.0
    k = 0
    while t < total:
        root, chord = prog[k % 4]
        i0 = int(t * SR)
        # pad
        p = pad([midi(c - 12) for c in chord], bar + 0.8)
        seg = out[i0:i0 + len(p)]
        seg += 0.16 * p[:len(seg), None]
        # bas
        b = epiano(midi(root - 12), bar, 0.5)
        seg = out[i0:i0 + len(b)]
        seg += 0.18 * lp(b, 0.1)[:len(seg), None]
        # arpej (8'lik)
        for j, idx in enumerate(arp_pat):
            tt = t + j * beat / 2
            ii = int(tt * SR)
            note = epiano(midi(chord[idx]), 1.2, 0.55 if j % 2 else 0.75)
            pan = 0.35 if j % 2 else -0.35
            seg = out[ii:ii + len(note)]
            m = len(seg)
            seg[:, 0] += 0.09 * note[:m] * (1 - pan)
            seg[:, 1] += 0.09 * note[:m] * (1 + pan)
        # ritim (açılıştan sonra)
        if t > 8:
            for j in range(4):
                ii = int((t + j * beat) * SR)
                if j in (0, 2):
                    kk = kick()
                    seg = out[ii:ii + len(kk)]
                    seg += 0.22 * kk[:len(seg), None]
                for h in (0, 0.5):
                    ss = shaker()
                    i2 = int((t + (j + h) * beat) * SR)
                    seg = out[i2:i2 + len(ss)]
                    seg[:, 0] += 0.05 * ss[:len(seg)]
                    seg[:, 1] += 0.07 * ss[:len(seg)]
        t += bar
        k += 1
    out = out[:int(total * SR)]
    # bölüm dinamikleri
    g = np.ones(len(out)) * 0.85
    tt = np.arange(len(out)) / SR
    for a, b in lift_ranges:
        g += 0.25 * np.clip(np.minimum((tt - a) / 1.5, (b - tt) / 1.5), 0, 1)
    for a, b in calm_ranges:
        g -= 0.3 * np.clip(np.minimum((tt - a) / 1.5, (b - tt) / 1.5), 0, 1)
    g *= np.clip(tt / 1.8, 0, 1) * np.clip((total - tt) / 4.0, 0, 1)
    return out * g[:, None]


# ---------------------------------------------------------------- efektler
def clink(freq=None):
    freq = freq or RNG.uniform(2200, 4200)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * env_exp(n, d)
            for r, a, d in ((1, 1, 0.25), (2.76, 0.5, 0.12), (5.4, 0.25, 0.06)))
    return x * 0.5


def knife_tick():
    n = int(0.05 * SR)
    x = bp(RNG.standard_normal(n), 1800, 5000) * env_exp(n, 0.008)
    t = np.arange(n) / SR
    x += 0.6 * np.sin(2 * np.pi * 180 * t) * env_exp(n, 0.012)  # tahta tok sesi
    return x


def whoosh(d=0.9):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    x = RNG.standard_normal(n)
    from scipy.signal import butter, sosfilt
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        f = 400 + 3500 * np.sin(np.pi * t[i]) ** 2
        sos = butter(2, [f * 0.6, f * 1.4], btype="band", fs=SR, output="sos")
        out[i:i + blk] = sosfilt(sos, x[i:i + blk])
    return out * np.sin(np.pi * t) ** 1.5 * 0.8


def ding(freq=1568):
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) * env_exp(n, 0.5)
         + 0.4 * np.sin(2 * np.pi * freq * 2.01 * t) * env_exp(n, 0.25)
         + 0.2 * np.sin(2 * np.pi * freq * 3.0 * t) * env_exp(n, 0.12))
    return x * 0.35


def chime():
    x = np.zeros(int(3.0 * SR))
    for k, f in enumerate((midi(77), midi(81), midi(84), midi(89))):
        d = ding(f)
        i = int(k * 0.16 * SR)
        x[i:i + len(d)] += d[:len(x) - i]
    return x * 0.8


def sizzle(d):
    n = int(d * SR)
    base = hp(RNG.standard_normal(n), 3500) * 0.15
    crack = (RNG.random(n) < 0.0009) * RNG.standard_normal(n)
    crack = bp(crack, 1500, 9000) * 2.5
    t = np.arange(n) / SR
    a = np.minimum(1, t / 1.0) * np.minimum(1, (d - t) / 1.0)
    return (base + crack) * a


def ambience(total):
    n = int(total * SR)
    x = lp(RNG.standard_normal(n), 0.02) * 0.6  # oda uğultusu
    x += bp(RNG.standard_normal(n), 300, 1200) * 0.05
    # rastgele uzak tıkırtılar
    t = 1.0
    while t < total - 1:
        c = clink() * RNG.uniform(0.08, 0.2)
        i = int(t * SR)
        x[i:i + len(c)] += c[:n - i]
        t += RNG.uniform(1.2, 3.5)
    return x


def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(sig), len(buf) - i)
    buf[i:i + m, 0] += gain * sig[:m] * (1 - pan)
    buf[i:i + m, 1] += gain * sig[:m] * (1 + pan)


def load_vo(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le",
                                   "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def build_mix(tl, transitions, card_times, out_wav, vo_paths=None):
    total = tl["total"]
    n = int(total * SR)
    lifts = [(s["start"], s["end"]) for s in tl["scenes"] if s.get("lift")]
    calms = [(s["start"], s["end"]) for s in tl["scenes"] if s.get("calm")]
    mus = music(total, lift_ranges=lifts, calm_ranges=calms)
    fx = np.zeros((n, 2))
    amb = ambience(total)
    amb_env = np.clip(np.arange(n) / SR / 2.0, 0, 1) * np.clip((total - np.arange(n) / SR) / 3, 0, 1)
    fx[:, 0] += 0.12 * amb * amb_env
    fx[:, 1] += 0.12 * np.roll(amb, 2400) * amb_env

    for s in tl["scenes"]:
        if s.get("ticks"):  # açılış bıçak ritmi
            t = s["start"] + 0.05
            for j in range(16):
                place(fx, knife_tick(), t + j * 0.163 + RNG.uniform(-0.01, 0.01), 0.55,
                      RNG.uniform(-0.2, 0.2))
        if s.get("sizzle"):
            place(fx, sizzle(s["end"] - s["start"]), s["start"], 0.35, 0.15)
        if s.get("endcard"):
            place(fx, chime(), s["start"] + 0.4, 0.55)
    for t in transitions:
        place(fx, whoosh(), max(0, t - 0.45), 0.45, RNG.uniform(-0.3, 0.3))
    for t in card_times:
        place(fx, ding(RNG.choice([1397, 1568, 1760])), t, 0.30)

    voice = np.zeros(n)
    if vo_paths:
        for at, p in vo_paths:
            v = load_vo(p)
            i = int(at * SR)
            m = min(len(v), n - i)
            voice[i:i + m] += v[:m]
    # ducking: ses varken müzik -9 dB
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    act = maximum_filter1d((np.abs(voice) > 0.01).astype(float), int(0.25 * SR))
    duck = 1 - 0.65 * uniform_filter1d(act, int(0.3 * SR))
    mix = mus * duck[:, None] + fx + voice[:, None] * 0.95
    peak = np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix / peak * 1.1) * 0.89  # yumuşak limitleme
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav
