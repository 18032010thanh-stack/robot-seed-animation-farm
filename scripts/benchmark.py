#!/usr/bin/env python3
"""Resource-capped Blender benchmark. Standard-library only; optional render of a 10–100 s clip.

The 180 s story stays unchanged. Output FPS retimes keyframes to preserve motion.
Reports are written even if a test fails or is refused by safety guards.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "scene_robot_seed.py"
BASE = ROOT / "project.json"
PRESETS = {
    "480p15": (854, 480, 15),
    "720p24": (1280, 720, 24),
    "1080p30": (1920, 1080, 30),
    "1080p60": (1920, 1080, 60),
    "1440p30": (2560, 1440, 30),
    "4k24": (3840, 2160, 24),
}

def profile(preset, samples, seconds, start_second):
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    if samples not in (8, 16, 32):
        raise ValueError("Samples must be 8, 16, or 32")
    if seconds not in (10, 30, 100):
        raise ValueError("Only 10/30/100-second segments allowed")
    if start_second not in (0, 60, 120, 150):
        raise ValueError("Start second must be 0/60/120/150")
    if start_second + seconds > 180:
        raise ValueError("Segment exceeds the 180-second film")
    w, h, fps = PRESETS[preset]
    c = json.loads(BASE.read_text(encoding="utf8"))
    c.update(width=w, height=h, fps=fps, samples=samples)
    start = start_second * fps + 1
    count = seconds * fps
    return c, start, start + count - 1

def free_gib(path):
    return shutil.disk_usage(path).free / 2**30

def rss_gib(pid):
    # Blender is one process for standard CPU rendering; monitor its VmRSS.
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf8").splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / (1024**2)
    except (OSError, ValueError, IndexError):
        pass
    return 0.0

def terminate_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

def render_range(config_path, frames, start, end, threads, logfile,
                 time_limit, min_disk_free, max_rss):
    cmd = ["blender", "-b", "-t", str(threads), "--python", str(SOURCE), "--",
           "--config", str(config_path), "--start", str(start),
           "--end", str(end), "--frames", str(frames)]
    start_wall = time.monotonic()
    max_seen = 0.0
    error = None
    with open(logfile, "w", encoding="utf8") as log:
        log.write("Command: " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        while proc.poll() is None:
            elapsed = time.monotonic() - start_wall
            max_seen = max(max_seen, rss_gib(proc.pid))
            if elapsed >= time_limit:
                error = "timeout"
            elif free_gib(frames) < min_disk_free:
                error = "disk_reserve_reached"
            elif max_seen >= max_rss:
                error = "ram_guard_reached"
            if error:
                log.write(f"\nGUARD TRIPPED: {error}; elapsed={elapsed:.1f}s, RSS={max_seen:.2f} GiB\n")
                log.flush()
                terminate_group(proc)
                break
            time.sleep(1.5)
        return_code = proc.wait()
    return {
        "seconds": round(time.monotonic() - start_wall, 2),
        "peak_blender_rss_gib": round(max_seen, 3),
        "return_code": return_code,
        "error": error,
        "log": logfile.name,
    }

def ffprobe(path):
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_frames,duration",
        "-of", "json", str(path)], text=True, timeout=30)
    streams = json.loads(raw)["streams"]
    if len(streams) != 1:
        raise RuntimeError("Expected one video stream")
    return streams[0]

def encode(frames, start, count, output, cfg):
    temp = output.with_suffix(".partial.mp4")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-xerror", "-y",
        "-framerate", str(cfg["fps"]), "-start_number", str(start),
        "-i", str(frames / "f_%06d.jpg"), "-frames:v", str(count),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(cfg["crf"]),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp)
    ], check=True, timeout=240)
    info = ffprobe(temp)
    nom, den = map(int, info["avg_frame_rate"].split("/"))
    if not (info["codec_name"] == "h264" and
            info["width"] == cfg["width"] and info["height"] == cfg["height"] and
            nom == cfg["fps"] * den and int(info.get("nb_frames", 0)) == count):
        raise RuntimeError("FFprobe validation failed: " + json.dumps(info))
    temp.replace(output)
    return info

def report(directory, data):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metrics.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    lines = [
        "# Benchmark Blender / GitHub Actions",
        "",
        f"- **Trạng thái:** {data.get('status', 'unknown')}",
        f"- **Preset:** {data['preset']}, samples {data['samples']}",
        f"- **Đoạn phim:** {data['start_second']}–{data['start_second']+data['seconds']} s",
        f"- **Runner:** {data.get('cpu_count')} CPU, RAM tổng {data.get('mem_total_gib')} GiB",
        f"- **Disk trống lúc bắt đầu:** {data.get('disk_free_at_start_gib')} GiB",
        f"- **Probe:** {data.get('probe')}",
        f"- **Thời gian mỗi frame (đo):** {data.get('seconds_per_frame')} s/frame",
        f"- **Dự báo toàn đoạn (có hệ số an toàn):** {data.get('projected_seconds_with_margin')} s",
        f"- **Full run:** {data.get('full_run')}",
        f"- **MP4:** {data.get('video')}",
        f"- **Lỗi/giới hạn:** {data.get('error', 'none')}",
        "",
        "Đây là số đo trong lần chạy cụ thể, không phải giới hạn tuyệt đối của dịch vụ.",
    ]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines), flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preset", choices=PRESETS, default="720p24")
    p.add_argument("--samples", type=int, choices=(8,16,32), default=8)
    p.add_argument("--seconds", type=int, choices=(10,30,100), default=10)
    p.add_argument("--start-second", type=int, choices=(0,60,120,150), default=0)
    p.add_argument("--mode", choices=("probe","render"), default="probe")
    p.add_argument("--allow-heavy", action="store_true")
    p.add_argument("--threads", type=int, choices=(2,4), default=4)
    p.add_argument("--budget-minutes", type=int, default=55)
    p.add_argument("--max-rss-gib", type=float, default=12.5)
    p.add_argument("--min-disk-free-gib", type=float, default=2.5)
    args = p.parse_args()
    cfg, start, end = profile(args.preset, args.samples, args.seconds, args.start_second)
    if args.budget_minutes < 10 or args.budget_minutes > 70:
        p.error("Budget must be between 10 and 70 minutes")
    if args.max_rss_gib < 3 or args.max_rss_gib > 14:
        p.error("RAM guard must be within 3..14 GiB")
    frames_needed = end-start+1
    profile_name = f"{args.preset}-s{args.samples}-t{args.start_second}-d{args.seconds}"
    directory = ROOT / "outputs" / "benchmark" / profile_name
    directory.mkdir(parents=True, exist_ok=True)
    frame_dir = directory / "frames"
    frame_dir.mkdir(exist_ok=True)
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    mem_total = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total = round(int(line.split()[1]) / (1024**2), 2)
    except (OSError, ValueError):
        pass
    data = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "initialized", "preset": args.preset, "samples": args.samples,
        "seconds": args.seconds, "start_second": args.start_second,
        "frames_requested": frames_needed, "output_fps": cfg["fps"],
        "resolution": [cfg["width"], cfg["height"]], "mode": args.mode,
        "threads": args.threads, "cpu_count": os.cpu_count(),
        "mem_total_gib": mem_total,
        "disk_free_at_start_gib": round(free_gib(directory), 2),
        "safety_budget_minutes": args.budget_minutes,
        "max_rss_gib": args.max_rss_gib,
        "min_disk_free_gib": args.min_disk_free_gib,
    }
    try:
        for name in ("blender","ffmpeg","ffprobe"):
            if shutil.which(name) is None:
                raise RuntimeError(name + " is not installed")
        if free_gib(directory) < args.min_disk_free_gib + 1:
            raise RuntimeError("Insufficient disk space to begin")
        probe_count = min(frames_needed, 16)
        probe_end = start + probe_count - 1
        probe = render_range(
            config_path, frame_dir, start, probe_end, args.threads,
            directory / "probe.log", min(600, args.budget_minutes*60/3),
            args.min_disk_free_gib, args.max_rss_gib)
        data["probe"] = probe
        if probe["return_code"] != 0 or probe["error"]:
            raise RuntimeError("Blender probe failed: " + str(probe))
        for f in range(start, probe_end+1):
            if not (frame_dir / f"f_{f:06d}.jpg").is_file():
                raise RuntimeError("Missing probe frame " + str(f))
        measured = probe["seconds"] / probe_count
        # Conservative estimate: startup overhead makes this a safe approximation.
        estimate = measured * frames_needed * 1.5
        data["seconds_per_frame"] = round(measured, 4)
        data["projected_seconds_with_margin"] = round(estimate, 1)
        data["probe_frames"] = probe_count
        data["status"] = "probe_ok"
        if args.mode == "probe":
            return
        if frames_needed > 900 and not args.allow_heavy:
            data["status"] = "guard_needs_allow_heavy"
            data["error"] = "More than 900 frames: set allow_heavy only after reading probe metrics"
            return
        # Leave 5 minutes for FFmpeg, artifact upload, and setup variation.
        safe_budget = args.budget_minutes*60 - 300
        if estimate > safe_budget:
            data["status"] = "guard_projected_timeout"
            data["error"] = "Full segment predicted too slow for the selected safety budget"
            return
        # Predict frame storage from JPEG probe. Leave a disk reserve and margin.
        probe_bytes = sum((frame_dir/f"f_{f:06d}.jpg").stat().st_size
                          for f in range(start,probe_end+1))
        expected_jpeg_gib = probe_bytes / probe_count * frames_needed * 1.8 / 2**30
        data["estimated_jpeg_disk_gib_with_margin"] = round(expected_jpeg_gib,3)
        if expected_jpeg_gib > free_gib(directory) - args.min_disk_free_gib:
            data["status"] = "guard_projected_disk_full"
            data["error"] = "JPEG frame storage exceeds safe free-disk estimate"
            return
        # Keep the probe images; Blender script detects and skips those frames.
        full = render_range(
            config_path, frame_dir, start, end, args.threads,
            directory / "full.log", safe_budget - probe["seconds"],
            args.min_disk_free_gib, args.max_rss_gib)
        data["full_run"] = full
        if full["return_code"] != 0 or full["error"]:
            raise RuntimeError("Full render failed: " + str(full))
        for f in range(start, end+1):
            if not (frame_dir / f"f_{f:06d}.jpg").is_file():
                raise RuntimeError("Missing final frame " + str(f))
        video = directory / "segment.mp4"
        info = encode(frame_dir, start, frames_needed, video, cfg)
        data["video"] = {
            "name": video.name, "bytes": video.stat().st_size,
            "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
            "ffprobe": info,
        }
        data["status"] = "render_verified"
        # The MP4 survives; JPEGs are omitted from the artifact to save storage.
        shutil.rmtree(frame_dir)
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as e:
        data["status"] = "error"
        data["error"] = str(e)
        raise
    finally:
        data["disk_free_at_end_gib"] = round(free_gib(directory), 2)
        report(directory, data)

if __name__ == "__main__":
    main()
