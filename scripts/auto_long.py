#!/usr/bin/env python3
"""Unattended second stage: choose one safe actual render from sweep measurements.

Prefer a real 100-second 480p15 clip when projected feasible.
Otherwise try a higher-resolution 10-second clip. Refuse unmeasured jobs.
No manual input or quota/billing changes.
"""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SWEEP=ROOT/"downloaded-sweep"/"summary.json"
OUT=ROOT/"outputs"/"auto-long"
BENCH=ROOT/"scripts"/"benchmark.py"

def decision():
    sweep=json.loads(SWEEP.read_text(encoding="utf8"))
    verified={(e["preset"],e["samples"],e["seconds"],e["start_second"]):e
              for e in sweep.get("entries",[]) if e.get("status")=="probe_ok"}
    candidates=[
        ("480p15",8,100,0), # user wanted 100s segments
        ("1080p60",8,10,0), # 10s high motion sample, if 100s too slow
        ("1080p30",8,10,0),
        ("720p24",8,10,0),
    ]
    reasons=[]
    for preset,samples,seconds,start in candidates:
        # For quality 10s samples, use the 100s probe from the same t=0
        probe=verified.get((preset,samples,100,0))
        if probe is None:
            reasons.append(f"{preset}: no verified probe, refused")
            continue
        metrics=probe.get("metrics") or {}
        estimate=metrics.get("projected_seconds_with_margin")
        if not isinstance(estimate,(int,float)):
            reasons.append(f"{preset}: missing runtime projection")
            continue
        # Multiply baseline 100s prediction proportionally for the 10s candidate.
        estimate_for_target=estimate*seconds/100
        # The next job has 65 min Blender budget, with separate setup/encoder.
        if estimate_for_target<=3150:
            return {"preset":preset,"samples":samples,"seconds":seconds,
                    "start_second":start,"projected_seconds":round(estimate_for_target,1),
                    "decision":"execute","alternatives":reasons}
        reasons.append(f"{preset}: predicted {estimate_for_target:.0f}s > 3150s")
    return {"decision":"skip","alternatives":reasons,
            "reason":"No measured candidate fits the safety budget"}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={"time_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        chosen=decision()
        report.update(chosen)
        if chosen["decision"]=="skip":
            return
        cmd=[sys.executable,str(BENCH),
             "--preset",chosen["preset"],
             "--samples",str(chosen["samples"]),
             "--seconds",str(chosen["seconds"]),
             "--start-second",str(chosen["start_second"]),
             "--mode","render",
             "--allow-heavy",
             "--threads","4",
             "--budget-minutes","65",
             "--max-rss-gib","12.5",
             "--min-disk-free-gib","2.5"]
        t0=time.monotonic()
        logfile=OUT/"render.log"
        with logfile.open("w",encoding="utf8") as fh:
            proc=subprocess.run(cmd,cwd=ROOT,stdout=fh,stderr=subprocess.STDOUT,
                                timeout=4200)
        report["return_code"]=proc.returncode
        report["render_wall_seconds"]=round(time.monotonic()-t0,2)
        name=f"{chosen['preset']}-s{chosen['samples']}-t{chosen['start_second']}-d{chosen['seconds']}"
        metrics=ROOT/"outputs"/"benchmark"/name/"metrics.json"
        if metrics.exists():
            report["metrics"]=json.loads(metrics.read_text(encoding="utf8"))
        report["status"]="render_verified" if (
            proc.returncode==0 and (report.get("metrics") or {}).get("status")=="render_verified"
        ) else "render_failed_or_guarded"
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as ex:
        report["status"]="error"
        report["error"]=str(ex)
    finally:
        (OUT/"decision.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        lines=["# Automatic render after benchmark", "",
               f"- Decision: {report.get('decision','error')}",
               f"- Preset: {report.get('preset','none')}",
               f"- Length: {report.get('seconds','none')}s",
               f"- Status: {report.get('status','skip')}",
               f"- Projected time: {report.get('projected_seconds','none')} s",
               f"- Actual time: {report.get('render_wall_seconds','none')} s",
               f"- Error/guard: {report.get('error', 'none')}",
               "", "The MP4 is only valid if metrics.status is render_verified."]
        (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf8")
        print("\n".join(lines),flush=True)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf8") as fh:
                fh.write("\n".join(lines)+"\n")
        # A rendered MP4 is stored under outputs/benchmark/.../segment.mp4.
        # The separate workflow artifact upload collects only that verified MP4.
    if report.get("status")=="error":
        sys.exit(1)

if __name__=="__main__": main()
