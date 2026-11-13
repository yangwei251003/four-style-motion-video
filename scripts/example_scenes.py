"""Four original, deterministic animation studies with shared picture/sound timing."""

from dataclasses import dataclass
from functools import lru_cache
import math

from PIL import Image, ImageDraw, ImageFont


FPS = 30
WIDTH, HEIGHT = 768, 432
FRAMES = 150
INK = "#f0f3f4"


@dataclass(frozen=True)
class Cue:
    frame: int
    end_frame: int
    kind: str
    action: str


@dataclass(frozen=True)
class Scene:
    title: str
    light: tuple[int, int, int]
    cues: tuple[Cue, ...]

    def frame(self, kind):
        return next(cue.frame for cue in self.cues if cue.kind == kind)


SCENES = {
    "metaphor": Scene("Pressure becomes motion", (45, 42, 81), (
        Cue(12, 66, "air", "Arcs compress around the same center"),
        Cue(66, 135, "release", "Center flashes and becomes a traveling wave"),
        Cue(69, 133, "air_tail", "The released wave continues across the panel"),
    )),
    "material": Scene("One drop, two responses", (25, 58, 73), (
        Cue(15, 60, "air", "Subtle air accompanies the approach"),
        Cue(60, 72, "water_contact", "Drop reaches the surface and starts the ripple"),
        Cue(61, 118, "water_tail", "Surface and submerged bubbles settle"),
    )),
    "diagram": Scene("A shared threshold", (36, 52, 49), (
        Cue(24, 80, "scan", "Both readings progress along the same axis"),
        Cue(80, 107, "confirm", "Channel B crosses the common 60-point threshold"),
        Cue(81, 120, "glint", "Threshold marker remains visible for comparison"),
    )),
    "pixel-story": Scene("Make a route", (47, 38, 62), (
        Cue(12, 25, "step", "First footfall"),
        Cue(26, 38, "step", "Second footfall"),
        Cue(40, 52, "step", "Third footfall"),
        Cue(64, 76, "metal_contact", "Falling gear hits the catch tray"),
        Cue(75, 92, "confirm", "Inventory counter changes from zero to one"),
        Cue(98, 137, "hinge", "The unlocked lift moves with its cable"),
    )),
}


def unit(value):
    return min(1.0, max(0.0, value))


def ease(value):
    t = unit(value)
    return t * t * (3 - 2 * t)


def lerp(start, end, amount):
    return start + (end - start) * amount


@lru_cache(maxsize=16)
def font(size):
    return ImageFont.load_default(size=size)


def text(draw, at, words, size, color=INK, anchor="la"):
    draw.text(at, words, font=font(size), fill=color, anchor=anchor)


def ring(draw, x, y, rx, ry, color, width=1):
    draw.ellipse((x - rx, y - ry, x + rx, y + ry), outline=color, width=width)


def point(draw, x, y, radius, color):
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


@lru_cache(maxsize=4)
def background(light):
    small = Image.new("RGB", (90, 51))
    colors = []
    for y in range(51):
        for x in range(90):
            glow = max(0, 1 - math.hypot((x - 48) / 64, (y - 30) / 40)) ** 2
            colors.append(tuple(round(10 + channel * glow) for channel in light))
    small.putdata(colors)
    return small.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC)


def caption(draw, line, color="#c5cbd2"):
    draw.line((44, 376, 724, 376), fill="#333943", width=1)
    text(draw, (44, 391), line, 18, color)


def metaphor(draw, frame, scene):
    trigger = scene.frame("release")
    charge = ease((frame - 12) / (trigger - 12))
    after = max(0, (frame - trigger) / FPS)
    center_x = WIDTH // 2
    center_y = 212
    radius = lerp(103, 16, charge)
    if frame < trigger:
        for i in range(5):
            r = radius + 11 * i
            start = i * 47 + frame * (1.1 + 2.0 * charge)
            draw.arc((center_x - r, center_y - r, center_x + r, center_y + r), start, start + 117,
                     fill=(113 + 21 * i, 110 + 10 * i, 204 + 9 * i), width=3)
        for i in range(24):
            angle = i * math.tau / 24 + frame * .017
            d = radius + (i % 4) * 9
            point(draw, center_x + math.cos(angle) * d, center_y + math.sin(angle) * d,
                  1 + i % 2, "#ac9ee2")
    else:
        for i in range(5):
            spread = 15 + 112 * (after - i * .08)
            if 0 < spread < 255:
                bright = round(220 * math.exp(-.88 * after) / (1 + i * .23))
                ring(draw, center_x, center_y, spread, 10 + spread * .53, (bright, bright + 15, 235), 2)
        for i in range(34):
            angle = i * 2.39996
            d = (46 + 4 * (i % 13)) * after
            x = center_x + math.cos(angle) * d * 1.54
            y = center_y + math.sin(angle) * d * .68 + 11 * after ** 2
            point(draw, x, y, 1 + i % 2, "#ffd791" if i % 3 else "#a2deef")
    point(draw, center_x, center_y, 7 + 7 * math.exp(-9 * after), "#ffe1a9" if frame >= trigger else "#e9d0ff")
    caption(draw, "The same center holds the pressure, then carries the release.")


def material(draw, frame, scene):
    contact = scene.frame("water_contact")
    water_y = 238
    elapsed = max(0, (frame - contact) / FPS)
    center = WIDTH // 2
    draw.rounded_rectangle((center - 147, 131, center + 147, 320), radius=23, fill="#102934", outline="#60828b", width=2)
    draw.rounded_rectangle((center - 136, water_y, center + 136, 310), radius=13, fill="#194756")
    draw.line((center - 135, water_y, center + 135, water_y), fill="#6fb7bc", width=2)
    draw.line((center - 134, 151, center - 134, 215), fill="#b1ced0", width=3)
    draw.line((center + 133, 170, center + 133, 222), fill="#496a75", width=2)
    if 15 <= frame < contact:
        t = (frame - 15) / (contact - 15)
        y = lerp(115, water_y - 8, t * t)
        draw.ellipse((center - 8, y - 13, center + 8, y + 8), fill="#89d4e4", outline="#d1f0ed", width=2)
    if frame >= contact:
        for n in range(3):
            radius = 5 + (elapsed - n * .15) * 115
            if 0 < radius < 130:
                light = round(200 * math.exp(-.83 * elapsed))
                ring(draw, center, water_y, radius, max(2, radius * .16), (43, light, min(245, light + 43)), 2)
        for i in range(8):
            speed = 15 + i * 3
            y = water_y + 24 + i % 3 * 11 - elapsed * speed
            if water_y + 1 < y < 304:
                ring(draw, center + math.sin(i + 3 * elapsed) * (8 + i * 2), y, 2 + i % 3, 2 + i % 3, "#80c9ca")
    caption(draw, "The surface reacts at contact. Bubbles and the ripple follow.")


def diagram(draw, frame, scene):
    origin, span = 144, 467
    threshold = scene.frame("confirm")
    meter_b = 60 * unit((frame - 24) / (threshold - 24))
    if frame > threshold:
        meter_b += 23 * ease((frame - threshold) / 34)
    meter_a = 47 * ease((frame - 24) / 58)
    limit_x = origin + .60 * span
    for amount in range(0, 101, 20):
        x = origin + span * amount / 100
        draw.line((x, 134, x, 304), fill="#334344", width=1)
        text(draw, (x, 315), str(amount), 15, "#9caca9", "mt")
    for value, y, label, color in ((meter_a, 180, "A", "#92bec8"), (meter_b, 254, "B", "#f7bf77")):
        text(draw, (96, y), label, 27, color, "mm")
        draw.rounded_rectangle((origin, y - 13, origin + span, y + 13), radius=12, fill="#25363a")
        end = origin + span * value / 100
        draw.rounded_rectangle((origin, y - 13, max(origin + 2, end), y + 13), radius=12, fill=color)
        text(draw, (end + 12, y), f"{round(value)}", 19, color, "lm")
    color = "#ffe3a4" if frame >= threshold else "#9eaaa9"
    for y in range(130, 297, 14):
        draw.line((limit_x, y, limit_x, y + 7), fill=color, width=2)
    text(draw, (limit_x, 116), "THRESHOLD", 14, color, "mm")
    caption(draw, "A shared scale makes the different outcomes visible.")


PIXEL_PERSON = (
    "..hhhh...", ".hhhhhh..", ".hssss..h", ".hssssss.", "..ssskss.", "..sssss..", "...tt....",
    "..tttt...", ".stttts..", ".stttts..", "..tttt...", "..dd.d...", "..dd.d...", "..d..dd..",
)
PERSON_PALETTE = {"h": "#592f44", "s": "#f1b68b", "k": "#252b37", "t": "#6ccabf", "d": "#354966"}


def pixel_story(image, draw, frame, scene):
    pixel = Image.new("RGB", (256, 93), "#1c2133")
    low = ImageDraw.Draw(pixel)
    low.rectangle((0, 60, 255, 92), fill="#2a3044")
    for x in range(5, 253, 19):
        low.rectangle((x, 20 + x % 12, x + 8, 76), fill="#252b3e")
        low.point((x + 3, 17 + (x * 17) % 21), fill="#71878e")
    low.rectangle((15, 68, 181, 75), fill="#5b5169", outline="#9c8b9e")
    lift = scene.frame("hinge")
    rising = ease((frame - lift) / 38)
    platform_y = round(68 - 33 * rising)
    low.line((177, 15, 177, 69), fill="#b2a695", width=2)
    low.line((206, 15, 206, 69), fill="#b2a695", width=2)
    low.line((191, 10, 191, platform_y), fill="#7e7684", width=2)
    low.rectangle((175, platform_y, 208, platform_y + 6), fill="#e0a466", outline="#ffdb9e")
    walk = unit((frame - 12) / 41)
    x = round(37 + 81 * walk + 68 * ease((frame - 82) / 16))
    base_y = platform_y if frame >= lift else 68
    step = (frame - scene.frame("step")) // 7 if 12 <= frame < 52 else 0
    for row, line in enumerate(PIXEL_PERSON):
        for col, color in enumerate(line):
            if color in PERSON_PALETTE:
                bounce = int(row < 11 and step % 2)
                stride = (1 if col < 4 else -1) * int(row > 10 and step % 2)
                low.point((x + col + stride, base_y - 14 + row - bounce), PERSON_PALETTE[color])
    hit = scene.frame("metal_contact")
    low.line((133, 66, 155, 66), fill="#d5a26e", width=2)
    if frame < hit:
        y = round(14 + 49 * unit((frame - 36) / (hit - 35)) ** 2)
        low.rectangle((141, y - 3, 148, y + 3), fill="#e7bd75")
        low.rectangle((143, y - 1, 146, y + 1), fill="#413549")
    elif frame < scene.frame("confirm"):
        low.rectangle((141, 62, 148, 65), fill="#e7bd75")
        for i in range(6):
            age = (frame - hit) * .7
            low.point((145 + math.cos(i) * age, 64 - abs(math.sin(i) * age)), "#ffdd9e")
    image.paste(pixel.resize((WIDTH, 279), Image.Resampling.NEAREST), (0, 66))
    count = int(frame >= scene.frame("confirm"))
    draw.rounded_rectangle((510, 87, 665, 120), radius=8, fill="#30344b", outline="#957a91")
    text(draw, (587, 104), f"GEAR {count:02d} / 01", 17, "#ffe0a3", "mm")
    caption(draw, "Catch the gear, confirm the inventory, then move the lift.")


DRAW = {"metaphor": metaphor, "material": material, "diagram": diagram}


def draw_frame(style, frame):
    scene = SCENES[style]
    image = background(scene.light).copy()
    draw = ImageDraw.Draw(image)
    if style == "pixel-story":
        pixel_story(image, draw, frame, scene)
    else:
        DRAW[style](draw, frame, scene)
    text(draw, (44, 25), scene.title, 29)
    return image
