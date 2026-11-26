"""FFmpeg render engine — produces REAL playable MP4 files.

Composition (locked studio format):
- 9:16 → 1080x1920, footage window y 503..1418, black bars top/bottom.
- 16:9 → 1920x1080, footage window y 300..1080 under a 300px top bar.
- Titles live ONLY in the top bar: L1 white from 0s, L2 gold fading in
  around 7s, L3 typewriter from ~15.5s. Title lines are measured with PIL
  textbbox and stacked from their real glyph boxes with clear gaps —
  never fake-bolded with stroke, never placed from guessed positions.
"""
import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .. import config, database
from ..utils import jobs
from ..utils.files import slugify
from . import archive_service

log = logging.getLogger("hark.render")

GOLD = (232, 199, 102, 255)
WHITE = (255, 255, 255, 255)
L3_COLOUR = (216, 210, 192, 255)
L2_FADE_START, L2_FADE_END = 6.7, 7.4
L3_START = 15.5
L3_CHARS_PER_SEC = 14
OVERLAY_FPS = 10


class RenderError(Exception):
    pass


# ---------------- fonts ----------------

def pick_font():
    """Returns (path, label). Anton is bundled; fallbacks are honest."""
    anton = config.FONTS_DIR / "Anton-Regular.ttf"
    if anton.exists():
        return anton, "Anton (bundled)"
    lib = config.FONTS_DIR / "LiberationSans-Bold.ttf"
    if lib.exists():
        return lib, "Liberation Sans Bold (bundled fallback — Anton missing)"
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "C:\\Windows\\Fonts\\arialbd.ttf"):
        if Path(p).exists():
            return Path(p), f"{Path(p).name} (system fallback — Anton missing)"
    raise RenderError("No usable title font found (Anton / Liberation / DejaVu).")


# ---------------- title layout ----------------

def _wrap(draw, text, font, max_w, max_lines):
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines


def _fit(draw, text, base_size, max_w, max_lines, font_path):
    size = base_size
    while size >= 36:
        font = ImageFont.truetype(str(font_path), size)
        lines = _wrap(draw, text, font, max_w, max_lines)
        if lines and all(draw.textlength(l, font=font) <= max_w for l in lines):
            return font, size, lines
        size -= 6
    font = ImageFont.truetype(str(font_path), 36)
    return font, 36, _wrap(draw, text, font, max_w, max_lines)


def compute_layout(topic, hook, date, canvas_w, bar_h, font_path):
    """Measure every line's real glyph box and stack with clear gaps.
    Returns a layout dict used for drawing + verification."""
    probe = Image.new("RGBA", (canvas_w, bar_h))
    draw = ImageDraw.Draw(probe)
    max_w = canvas_w - 100
    # Font scale follows the canvas width AND the bar height, so the stack
    # always fits inside the top bar (a 16:9 bar is far shorter than 9:16's).
    s = min(canvas_w / 1080.0, (bar_h / 503.0) * 1.15)
    groups, total_bottom = [], 0
    for _attempt in range(30):
        base = {"l1": max(30, int(150 * s)), "l2": max(24, int(96 * s)),
                "l3": max(20, int(64 * s))}
        top0 = max(12, int(48 * s))
        gap_after_l1, gap_after_l2 = int(34 * s), int(38 * s)
        groups = []
        cursor = top0
        for key, text in (("l1", topic), ("l2", hook), ("l3", date)):
            if not text:
                continue
            font, size, lines = _fit(draw, text, base[key], max_w, 2, font_path)
            line_gap = int(size * 0.14)
            items = []
            for ln in lines:
                bbox = draw.textbbox((0, 0), ln, font=font)
                gh = bbox[3] - bbox[1]
                items.append({"text": ln, "top": cursor, "height": gh,
                              "bbox_top": bbox[1], "width": draw.textlength(ln, font=font)})
                cursor += gh + line_gap
            cursor -= line_gap  # no trailing gap inside the group
            groups.append({"key": key, "font": font, "size": size, "lines": items})
            cursor += gap_after_l1 if key == "l1" else gap_after_l2
        total_bottom = (groups[-1]["lines"][-1]["top"] + groups[-1]["lines"][-1]["height"]
                        if groups else 0)
        if total_bottom <= bar_h - 16:
            break
        s *= 0.92
    return {"groups": groups, "bottom": total_bottom, "bar_h": bar_h}


def _draw_group(base_img, group, colour, alpha=255):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ln in group["lines"]:
        x = (base_img.size[0] - ln["width"]) / 2
        d.text((x, ln["top"] - ln["bbox_top"]), ln["text"], font=group["font"], fill=colour)
    if alpha < 255:
        a = layer.getchannel("A").point(lambda v: v * alpha // 255)
        layer.putalpha(a)
    base_img.alpha_composite(layer)


def build_overlay_frames(project, layout, total_dur, canvas_w, canvas_h, out_dir: Path):
    groups = {g["key"]: g for g in layout["groups"]}
    n_frames = int(math.ceil(total_dur * OVERLAY_FPS)) + 1
    topic_date = project.get("date", "")
    for i in range(n_frames):
        t = i / OVERLAY_FPS
        img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        if "l1" in groups:
            _draw_group(img, groups["l1"], WHITE, 255)
        if "l2" in groups:
            if t >= L2_FADE_END:
                _draw_group(img, groups["l2"], GOLD, 255)
            elif t > L2_FADE_START:
                a = int(255 * (t - L2_FADE_START) / (L2_FADE_END - L2_FADE_START))
                _draw_group(img, groups["l2"], GOLD, a)
        if "l3" in groups and t >= L3_START and topic_date:
            n_chars = min(len(topic_date), int((t - L3_START) * L3_CHARS_PER_SEC))
            if n_chars > 0:
                partial = dict(groups["l3"])
                probe = Image.new("RGBA", (canvas_w, 10))
                pd = ImageDraw.Draw(probe)
                font = groups["l3"]["font"]
                text = topic_date[:n_chars]
                bbox = pd.textbbox((0, 0), text, font=font)
                partial["lines"] = [{"text": text, "top": groups["l3"]["lines"][0]["top"],
                                     "height": bbox[3] - bbox[1], "bbox_top": bbox[1],
                                     "width": pd.textlength(text, font=font)}]
                _draw_group(img, partial, L3_COLOUR, 255)
        img.save(out_dir / f"{i:04d}.png")
    return n_frames


# ---------------- segments ----------------

def _run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        tail = (r.stderr or "")[-1200:]
        raise RenderError(f"ffmpeg failed ({cmd[0]}): {tail}")
    return r


def _build_segment(ff, scene, media_row, media_path: Path, out_path: Path,
                   geom, use_clip_audio, clip_volume):
    dur = float(scene.get("duration") or 4)
    trim = float(scene.get("trimStart") or 0)
    kind = media_row["kind"]
    cw, ch, wx, wy, ww, wh = geom
    fade_out_st = max(0.0, dur - 0.3)
    if kind == "image":
        frames = max(1, int(dur * 30))
        vf = (f"scale={ww * 2}:{wh * 2}:force_original_aspect_ratio=increase,"
              f"crop={ww * 2}:{wh * 2},"
              f"zoompan=z='min(1+0.12*on/{frames},1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={ww}x{wh}:fps=30,"
              f"pad={cw}:{ch}:0:{wy}:black,fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_st}:d=0.3,"
              f"setsar=1,format=yuv420p")
        cmd = [ff, "-y", "-i", str(media_path), "-f", "lavfi", "-i",
               "anullsrc=r=48000:cl=stereo", "-vf", vf, "-map", "0:v", "-map", "1:a",
               "-t", f"{dur}", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(out_path)]
    else:
        probe = archive_service.probe_file(media_path)
        vf = (f"scale={ww}:{wh}:force_original_aspect_ratio=increase,crop={ww}:{wh},"
              f"fps=30,pad={cw}:{ch}:0:{wy}:black,fade=t=in:st=0:d=0.25,"
              f"fade=t=out:st={fade_out_st}:d=0.3,setsar=1,format=yuv420p")
        cmd = [ff, "-y", "-stream_loop", "-1", "-ss", f"{trim}", "-i", str(media_path)]
        if use_clip_audio and probe.get("audio_codec"):
            cmd += ["-vf", vf, "-map", "0:v", "-map", "0:a:0",
                    "-af", f"aresample=48000,volume={clip_volume},apad,atrim=0:{dur}"]
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", vf, "-map", "0:v", "-map", "1:a"]
        cmd += ["-t", f"{dur}", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(out_path)]
    _run(cmd, timeout=1200)


# ---------------- main render ----------------

def render_project(job_id: str, project: dict, settings: dict) -> dict:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RenderError("FFmpeg was not found on PATH. Install FFmpeg and restart the backend.")
    orientation = settings.get("orientation", "9:16")
    if orientation == "16:9":
        geom = (1920, 1080, 1920, 300, 1920, 780)  # cw, ch, ww, wy, ww2, wh
        cw, ch, bar_h = 1920, 1080, 300
    else:
        geom = (1080, 1920, 1080, 503, 1080, 915)
        cw, ch, bar_h = 1080, 1920, 503

    scenes = project.get("scenes", [])
    if not scenes:
        raise RenderError("Project has no scenes.")
    missing, resolved = [], []
    for sc in scenes:
        mid = sc.get("mediaId")
        row = database.get_media(mid) if mid else None
        if not row:
            missing.append(sc.get("n", "?"))
            resolved.append(None)
            continue
        path = config.MEDIA_DIR / row["rel_path"]
        if not path.exists():
            missing.append(sc.get("n", "?"))
            resolved.append(None)
            continue
        resolved.append((row, path))
    if missing:
        raise RenderError(
            "Scenes missing media: " + ", ".join(str(m) for m in missing) +
            ". Upload footage for every scene, then export again.")

    total_dur = sum(float(sc.get("duration") or 4) for sc in scenes)
    font_path, font_label = pick_font()
    layout = compute_layout(project.get("topic", ""), project.get("hook", ""),
                            project.get("date", ""), cw, bar_h, font_path)

    tmp = Path(tempfile.mkdtemp(prefix="hark_render_"))
    try:
        jobs.update(job_id, status="running", progress=2, message="Building scene segments…")
        seg_paths = []
        for i, sc in enumerate(scenes):
            row, path = resolved[i]
            seg = tmp / f"seg_{i:02d}.mp4"
            _build_segment(ff, sc, row, path, seg, geom,
                           settings.get("use_clip_audio", True),
                           float(settings.get("clip_volume", 1.0)))
            seg_paths.append(seg)
            jobs.update(job_id, progress=2 + int(53 * (i + 1) / len(scenes)),
                        message=f"Segment {i + 1}/{len(scenes)} done")

        list_file = tmp / "concat.txt"
        list_file.write_text("".join(f"file '{p}'\n" for p in seg_paths), encoding="utf-8")
        base = tmp / "base.mp4"
        _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
              "-c", "copy", str(base)], timeout=600)

        jobs.update(job_id, progress=58, message="Building title overlay…")
        frames_dir = tmp / "frames"
        frames_dir.mkdir()
        build_overlay_frames(project, layout, total_dur, cw, ch, frames_dir)

        slug = slugify(project.get("topic", "reel"))
        from ..utils.files import new_id
        export_id = new_id("e")
        out_name = f"{slug}_{export_id[-6:]}.mp4"
        out_path = config.EXPORTS_DIR / out_name

        inputs = ["-i", str(base), "-framerate", str(OVERLAY_FPS), "-i", str(frames_dir / "%04d.png")]
        extra_inputs = []
        narr_path = music_path = None
        if settings.get("narration_media_id"):
            row = database.get_media(settings["narration_media_id"])
            if row:
                narr_path = config.MEDIA_DIR / row["rel_path"]
                extra_inputs += ["-i", str(narr_path)]
        if settings.get("music_media_id"):
            row = database.get_media(settings["music_media_id"])
            if row:
                music_path = config.MEDIA_DIR / row["rel_path"]
                extra_inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        inputs += extra_inputs

        fc = ["[0:v][1:v]overlay=0:0:eof_action=pass,format=yuv420p[vout]"]
        audio_parts = ["[0:a]aresample=48000[a0]"]
        labels = ["[a0]"]
        idx = 2
        if narr_path:
            audio_parts.append(f"[{idx}:a]aresample=48000,volume={float(settings.get('narration_volume', 1.0))}[an]")
            labels.append("[an]")
            idx += 1
        if music_path:
            audio_parts.append(f"[{idx}:a]aresample=48000,volume={float(settings.get('music_volume', 0.3))}[am]")
            labels.append("[am]")
            idx += 1
        if len(labels) > 1:
            fc.append(";".join(audio_parts) + ";" + "".join(labels) +
                      f"amix=inputs={len(labels)}:duration=first:normalize=0[aout]")
        else:
            fc.append("[0:a]aresample=48000[aout]")
        filter_complex = ";".join(fc) if len(labels) > 1 else fc[0] + ";" + fc[1]

        cmd = [ff, "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(out_path)]

        jobs.update(job_id, progress=62, message="Final encode…")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        total_us = total_dur * 1_000_000
        for line in proc.stdout:
            if line.startswith("out_time_ms="):
                try:
                    done_us = int(line.split("=", 1)[1])
                    pct = 62 + int(36 * min(1.0, done_us / total_us))
                    jobs.update(job_id, progress=pct, message="Final encode…")
                except ValueError:
                    pass
        proc.wait()
        if proc.returncode != 0:
            err = (proc.stderr.read() or "")[-1200:]
            raise RenderError(f"Final encode failed: {err}")
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RenderError("Render produced no output file.")

        export = database.insert_export({
            "id": export_id, "project_id": project.get("id"),
            "filename": out_name, "rel_path": out_name,
            "settings": {**settings, "font": font_label, "orientation": orientation,
                         "duration": total_dur},
            "status": "done",
        })
        jobs.update(job_id, status="done", progress=100, message="Render complete",
                    result={"export_id": export_id, "filename": out_name,
                            "download_url": f"/api/exports/{export_id}/download",
                            "duration": total_dur, "font": font_label,
                            "title_layout": {"bottom": layout["bottom"], "bar_h": layout["bar_h"]}})
        return export
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
