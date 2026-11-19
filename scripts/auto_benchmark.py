#!/usr/bin/env python3
"""Run a bounded, unattended Blender CPU benchmark sweep on GitHub Actions.

All profiles run sequentially on ONE standard public GitHub runner; no parallel
matrix, no paid runners, and no changes to original project.json.
The job publishes complete reports even if an individual probe fails.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "scripts" / "benchmark.py"
OUT = ROOT / "outputs" / "auto-benchmark"

# A 100-second target is an ESTIMATE, not a blind 100-second render.
# Time 150 seconds exercises flower animation where scene complexity differs.
PROFILES = [
    ("480p15",  8, 100, 0,   "original film baseline, potential 100s full render"),
    ("720p24",  8, 100, 0,   "720p baseline, 100s extrapolation"),
    ("1080p30", 8, 100, 0,   "1080p at 30 FPS, 100s extrapolation"),
    ("1080p60", 8, 100, 0,   "1080p at 60 FPS, 100s extrapolation"),
    ("1440p30", 8, 100, 0,   "1440p at 30 FPS, 100s extrapolation"),
    ("4k24",    8, 100, 0,   "4K at 24 FPS, 100s extrapolation"),
    ("720p24",  8, 10,  150, "later flower scene at 720p"),
    ("1080p30",16, 10,  150, "later flower scene, double samples"),
    ("1080p30",32, 10,  0,   "higher samples / CPU stress")
]

def write_report(entries, started, budget):
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "budget_minutes": round(budget / 60, 2),
        "wall_elapsed_seconds": round(time.monotonic() - started, 2),
        "profiles_requested": len(PROFILES),
        "profiles_finished": sum(1 for e in entries if e.get("status") == "probe_ok"),
        "entries": entries,
        "note": "Probe measurements (16 frames) and 100s projections, NOT 100-second videos.",
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    lines = [
        "# Blender benchmark — automatic sequential sweep",
        "",
        f"- Probe profiles requested: {len(PROFILES)}",
        f"- Verified probes: {summary['profiles_finished']}",
        f"- Elapsed: {summary['wall_elapsed_seconds']} seconds",
        f"- Time budget: {int(budget/60)} minutes",
        "",
        "| Profile | Target | Samples | Tested frames | Probe sec | Est. target min, ×1.5 | RAM peak GiB | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for e in entries:
        v=e.get("metrics") or {}
        probe=v.get("probe") or {}
        estimate=v.get("projected_seconds_with_margin")
        projected = f"{estimate/60:.1f}" if isinstance(estimate,(int,float)) else "—"
        sec=probe.get("seconds")
        rss=probe.get("peak_blender_rss_gib")
        lines.append(
            f"| {e['preset']} | {e['seconds']}s at t={e['start_second']}s | {e['samples']} | "
            f"{v.get('probe_frames','—')} | {sec if sec is not None else '—'} | {projected} | "
            f"{rss if rss is not None else '—'} | {e['status']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- **probe_ok** means a short 16-frame probe succeeded. No complete movie was rendered.",
        "- Estimates are conservative but subject to scene complexity and Blender startup overhead.",
        "- **timeout**, **failed**, or **skipped_budget** are suite guard outcomes, not proof of a hard GitHub platform limit.",
        "- The original full 180-second movie and its artifacts are unaffected.",
        "- Run from GitHub Actions on standard ubuntu-latest, public repo only.",
    ]
    (OUT / "SUMMARY.md").write_text("\n".join(lines)+"\n",encoding="utf8")
    # Visible summary inside GitHub Actions run.
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf8") as out:
            out.write("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)

def terminate_process_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

def measure(preset,samples,seconds,start_second,deadline,per_test_timeout):
    label=f"{preset}-s{samples}-t{start_second}-d{seconds}"
    job=ROOT/"outputs"/"benchmark"/label
    job.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,str(BENCH),
        "--preset",preset,"--samples",str(samples),
        "--seconds",str(seconds),"--start-second",str(start_second),
        "--mode","probe","--threads","4",
        "--budget-minutes","55",
        "--max-rss-gib","12.5",
        "--min-disk-free-gib","2.5"]
    timeout=min(per_test_timeout,max(0,deadline-time.monotonic()-45))
    entry={"preset":preset,"samples":samples,"seconds":seconds,
           "start_second":start_second,"status":"starting"}
    if timeout < 90:
        entry["status"]="skipped_budget"
        entry["reason"]="Insufficient time left to run this benchmark safely"
        return entry
    logfile=OUT/(label+".txt")
    with logfile.open("w",encoding="utf8") as output:
        output.write("COMMAND: "+" ".join(cmd)+"\n")
        output.flush()
        proc=subprocess.Popen(cmd,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
                              start_new_session=True)
        try:
            proc.wait(timeout=timeout)
            entry["exit_code"]=proc.returncode
        except subprocess.TimeoutExpired:
            entry["status"]="timeout"
            entry["reason"]=f"Probe exceeded {round(timeout)} seconds"
            terminate_process_group(proc)
    metricsfile=job/"metrics.json"
    if metricsfile.is_file():
        try:
            entry["metrics"]=json.loads(metricsfile.read_text(encoding="utf8"))
        except (ValueError,OSError):
            entry["reason"]="Metrics JSON unreadable"
    if entry["status"]!="timeout":
        metrics=entry.get("metrics") or {}
        entry["status"]=metrics.get("status","failed")
        if proc.returncode and entry["status"]=="probe_ok":
            entry["status"]="failed"
        if entry["status"] not in ("probe_ok","failed","error"):
            entry["reason"]=f"Unexpected status {entry['status']}"
        if proc.returncode and entry["status"]!="probe_ok":
            entry["reason"]=metrics.get("error","benchmark process failed")
    # Don't keep temporary JPEGs: this suite is about measurements only.
    frame_dir=job/"frames"
    if frame_dir.is_dir():
        import shutil
        shutil.rmtree(frame_dir)
    return entry

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget-minutes",type=int,default=50)
    ap.add_argument("--per-test-minutes",type=int,default=8)
    args=ap.parse_args()
    if not 10<=args.budget_minutes<=65 or not 2<=args.per_test_minutes<=12:
        ap.error("Budget must be 10..65m, per-test must be 2..12m")
    OUT.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    budget=args.budget_minutes*60
    deadline=start+budget
    entries=[]
    try:
        for i, (preset,samples,seconds,start_second,description) in enumerate(PROFILES,1):
            if deadline-time.monotonic()<100:
                entries.append({"preset":preset,"samples":samples,"seconds":seconds,
                    "start_second":start_second,"status":"skipped_budget",
                    "reason":"Total budget exhausted"})
                continue
            print(f"\n[{i}/{len(PROFILES)}] {description}",flush=True)
            try:
                e=measure(preset,samples,seconds,start_second,
                          deadline,args.per_test_minutes*60)
            except Exception as ex:
                e={"preset":preset,"samples":samples,"seconds":seconds,
                   "start_second":start_second,"status":"failed","reason":str(ex)}
            entries.append(e)
            write_report(entries,start,budget)
            print(f"RESULT {e['preset']} samples={samples}: {e['status']}",flush=True)
    finally:
        write_report(entries,start,budget)
    failures=sum(1 for e in entries if e["status"] not in ("probe_ok","skipped_budget"))
    if failures: print(f"WARNING: {failures} probe(s) failed; check report for reasons")
    if not any(e.get("status")=="probe_ok" for e in entries):
        sys.exit("No usable benchmarks completed: see report.")

if __name__=="__main__":main()
