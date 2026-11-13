"""Render standalone animation studies and verify their exported timing."""

from argparse import ArgumentParser
from dataclasses import asdict
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import wave

from PIL import Image, ImageDraw

from example_audio import RATE, sample_at, tracks
from example_scenes import FPS, FRAMES, HEIGHT, SCENES, WIDTH, draw_frame, font


def binary(name, supplied):
    candidate = supplied or shutil.which(name)
    if not candidate or not Path(candidate).is_file():
        raise SystemExit(f"{name} unavailable. Supply --{name} or add it to PATH.")
    return str(Path(candidate).resolve())


def encode(ffmpeg, style, mix, target):
    args = [ffmpeg, "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS), "-i", "-", "-i", str(mix),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-threads:v", "2", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target)]
    with tempfile.TemporaryFile() as errors:
        with subprocess.Popen(args, stdin=subprocess.PIPE, stderr=errors) as job:
            try:
                for frame in range(FRAMES):
                    job.stdin.write(draw_frame(style, frame).tobytes())
                job.stdin.close()
            except BrokenPipeError:
                job.wait(timeout=10)
                errors.seek(0)
                raise RuntimeError(errors.read().decode(errors="replace")) from None
            except BaseException:
                job.kill()
                raise
            if job.wait(timeout=90):
                errors.seek(0)
                raise RuntimeError(errors.read().decode(errors="replace"))


def verify(ffmpeg, ffprobe, final, paths, samples):
    metadata = subprocess.check_output([ffprobe, "-v", "error", "-count_frames", "-show_streams", "-of", "json",
                                        str(final)], timeout=30)
    video, audio = json.loads(metadata)["streams"]
    if (video["codec_type"], video["width"], video["height"], video["avg_frame_rate"], int(video["nb_read_frames"])) != (
            "video", WIDTH, HEIGHT, f"{FPS}/1", FRAMES):
        raise ValueError("Exported video dimensions or frame count differ")
    if (audio["codec_type"], int(audio["sample_rate"]), float(audio["start_time"])) != ("audio", RATE, 0.0):
        raise ValueError("Exported audio sample rate or start time differs")
    if abs(float(audio["duration"]) - samples / RATE) > .001:
        raise ValueError("Exported audio length differs")
    for path in paths.values():
        with wave.open(str(path), "rb") as source:
            if (source.getnframes(), source.getframerate(), source.getnchannels()) != (samples, RATE, 2):
                raise ValueError(f"Stem length or format differs for {path.name}")
    subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(final), "-map", "0:v:0",
                    "-map", "0:a:0", "-f", "null", "-"], check=True, timeout=30)
    return {"dimensions": [video["width"], video["height"]], "frames": FRAMES, "fps": FPS,
            "samples": samples, "sample_rate": RATE, "decode_checked": True, "continuous_review": None}


def render(style, out, ffmpeg, ffprobe):
    scene = SCENES[style]
    out.mkdir(parents=True, exist_ok=True)
    paths, samples = tracks(out, style, scene)
    final = out / f"{style}.mp4"
    temporary = out / f"{style}.partial.mp4"
    try:
        encode(ffmpeg, style, paths["mix"], temporary)
        report = verify(ffmpeg, ffprobe, temporary, paths, samples)
        temporary.replace(final)
    finally:
        temporary.unlink(missing_ok=True)
    events = [{**asdict(cue), "at_seconds": cue.frame / FPS, "start_sample": sample_at(cue.frame),
               "end_sample": sample_at(cue.end_frame)} for cue in scene.cues]
    (out / f"{style}-timing.json").write_text(json.dumps({**report, "events": events}, indent=2) + "\n", encoding="utf-8")
    print(f"{style}: {FRAMES} frames, {samples} samples per stem, {len(events)} events", flush=True)


def preview(path, styles):
    cell = (390, 244)
    columns = min(2, len(styles))
    rows = (len(styles) + columns - 1) // columns
    board = Image.new("RGB", (columns * cell[0], rows * cell[1]), "#11151c")
    draw = ImageDraw.Draw(board)
    key_frames = {"metaphor": 93, "material": 82, "diagram": 110, "pixel-story": 113}
    for i, style in enumerate(styles):
        x, y = i % columns * cell[0], i // columns * cell[1]
        tile = draw_frame(style, key_frames[style]).resize((370, 208), Image.Resampling.LANCZOS)
        board.paste(tile, (x + 10, y + 27))
        draw.text((x + 12, y + 5), style, font=font(15), fill="#dde8ef")
    board.save(path, optimize=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=("all", *SCENES), default="all")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()
    ffmpeg, ffprobe = binary("ffmpeg", args.ffmpeg), binary("ffprobe", args.ffprobe)
    selected = list(SCENES) if args.style == "all" else [args.style]
    for style in selected:
        render(style, args.out, ffmpeg, ffprobe)
    preview(args.out / "preview.png", selected)
