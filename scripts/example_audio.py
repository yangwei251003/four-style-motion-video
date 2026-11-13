"""Make three sample-aligned WAV stems for the original examples."""

import math
import wave

import numpy as np

from example_scenes import FPS, FRAMES


RATE = 48000


def sample_at(frame):
    return round(frame * RATE / FPS)


def time_axis(samples):
    return np.arange(samples, dtype=np.float32) / RATE


def tone(t, frequency):
    return np.sin(2 * np.pi * frequency * t)


def strike(t, modes, decay):
    partials = sum(tone(t, hz) * weight for hz, weight in modes)
    return partials * (1 - np.exp(-t / .0009)) * np.exp(-t / decay)


def texture(rng, n, width):
    white = rng.uniform(-1, 1, n + width - 1).astype(np.float32)
    return np.convolve(white, np.full(width, 1 / math.sqrt(width), np.float32), mode="valid")


def movement(t, rng, base, end, width, pitch_mix):
    phase = t / (len(t) / RATE)
    swell = np.sin(np.pi * phase) ** .7
    pitch = np.sin(2 * np.pi * (base * t + (end - base) * t * phase / 2))
    return swell * (texture(rng, len(t), width) * (1 - pitch_mix) + pitch * pitch_mix)


def water_contact(t, rng):
    click = .46 * texture(rng, len(t), 3) * (1 - np.exp(-t / .0008)) * np.exp(-t / .009)
    click += strike(t, ((480, .28),), .012)
    delay = round(.012 * RATE)
    if delay < len(t):
        click[delay:] += strike(t[:-delay], ((1450, .51), (1820, .08)), .031)
    return click


def hinge(t, rng):
    friction = movement(t, rng, 82, 128, 38, .24)
    phase = np.cumsum(np.linspace(5, 13, len(t), dtype=np.float32)) / RATE
    teeth = np.exp(-24 * np.mod(phase, 1))
    return friction * (.45 + .55 * teeth)


CONTINUOUS = {
    "air": (85, 136, 36, .08, .105),
    "air_tail": (147, 82, 28, .25, .130),
    "water_tail": (310, 180, 19, .07, .065),
    "scan": (190, 350, 21, .27, .080),
    "glint": (540, 570, 12, .48, .065),
}

CONTACT = {
    "release": (((63, .68), (105, .19), (246, .13)), .29, .40),
    "metal_contact": (((230, .42), (930, .37), (1710, .17)), .085, .27),
    "confirm": (((510, .50), (792, .30), (1050, .11)), .074, .20),
    "step": (((95, .54), (181, .16), (311, .13)), .043, .17),
}

ROOM = {
    "metaphor": ((71, 113), .046, 111),
    "material": ((86, 139), .029, 86),
    "diagram": ((107, 161), .035, 58),
    "pixel-story": ((53, 94), .042, 77),
}


def cue_wave(cue, rng):
    length = sample_at(cue.end_frame) - sample_at(cue.frame)
    t = time_axis(length)
    if cue.kind == "water_contact":
        return water_contact(t, rng) * .32
    if cue.kind == "hinge":
        return hinge(t, rng) * .16
    if cue.kind in CONTINUOUS:
        base, end, width, pitch, gain = CONTINUOUS[cue.kind]
        return movement(t, rng, base, end, width, pitch) * gain
    modes, decay, gain = CONTACT[cue.kind]
    body = strike(t, modes, decay)
    impulse = texture(rng, len(t), 9) * (1 - np.exp(-t / .0013)) * np.exp(-t / .015)
    return (body + .23 * impulse) * gain


def fade(data, entrance, tail):
    if entrance:
        data[:entrance] *= np.sin(np.linspace(0, np.pi / 2, entrance)) ** 2
    if tail:
        data[-tail:] *= np.cos(np.linspace(0, np.pi / 2, tail)) ** 2
    return data


def write_pcm(path, data):
    pcm = np.rint(data * 32767).astype("<i2")
    with wave.open(str(path), "wb") as target:
        target.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        target.writeframes(pcm.tobytes())


def tracks(out, style, scene):
    samples = sample_at(FRAMES)
    t = time_axis(samples)
    rng = np.random.default_rng(821 + sum(ord(c) for c in style))
    action = np.zeros((samples, 2), dtype=np.float32)
    for index, cue in enumerate(scene.cues):
        left, right = sample_at(cue.frame), sample_at(cue.end_frame)
        signal = cue_wave(cue, rng)
        fade(signal, 0, min(1200, len(signal) // 4))
        pan = [-.16, .10, .16, 0][index % 4]
        action[left:right] += signal[:, None] * np.sqrt(np.array([1 - pan, 1 + pan], np.float32))
    (base, high), gain, width = ROOM[style]
    air = texture(rng, samples, width)
    room = np.zeros_like(action)
    envelope = .80 + .20 * tone(t, .44)
    for i in range(2):
        note = tone(t + .0007 * i, base) * .32 + tone(t + .0002 * i, high) * .17
        room[:, i] = fade((air * .65 + note) * envelope * gain, 10000, 26000)
    master = action + room
    peak = float(np.max(np.abs(master)))
    gain = min(1.0, .70 / max(peak, 1e-9))
    paths = {name: out / f"{style}-{name}.wav" for name in ("action", "ambience", "mix")}
    for kind, data in (("action", action), ("ambience", room), ("mix", master)):
        write_pcm(paths[kind], data * gain)
    return paths, samples
