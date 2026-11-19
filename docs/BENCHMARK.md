# Blender CPU stress benchmark (2026-11-20)

## Goal

Measure **actual runner limits** for this precise Blender scene, not just theoretical GitHub hardware specifications. The proven original film remains untouched: 180 seconds / 854×480 / 15fps / Cycles 8 samples rendered across 18 jobs of 10 seconds each (GitHub Actions run [#2](https://github.com/18032010thanh-stack/robot-seed-animation-farm/actions/runs/44532366846)).

## Test ladder (one manual run at a time)

| Order | Preset | Samples | Seconds | Mode | Why |
| --- | --- | --- | --- | --- | --- |
| 1 | 720p24 | 8 | 10 | probe | Check 16 frames; establish rate |
| 2 | 720p24 | 8 | 10 | render | Verify full MP4 and artifact export |
| 3 | 1080p30 | 8 | 30 | probe | Pixel/FPS scaling |
| 4 | 1080p60 | 8 | 30 | probe | FPS stress |
| 5 | 1440p30 | 8 | 100 | probe | Long-duration estimate |
| 6 | 4k24 | 8 | 100 | probe | High-resolution limit estimate |
| 7 | Any manageable preset | 16/32 | 10 | probe | Sample-count limit |
| 8 | 1080p30 or 720p24 | 8 | 100 | render (allow_heavy) | Actual long segment if projected safe |

The profile values deliberately limit the number of configurations. They do **not** imply the runner can render them successfully.

## Understanding metric fields

- `probe.seconds` is wall time for **16 frames** plus Blender startup.
- `seconds_per_frame` includes startup; this typically overestimates full throughput. It is not a precise scaling law.
- `projected_seconds_with_margin` is `seconds_per_frame × requested_frame_count × 1.5`; a conservative go/no-go guard, not an exact forecast.
- `peak_blender_rss_gib` estimates **the Blender process**, not aggregate cgroup memory or absolute peak between polls.
- `disk_free_at_start_gib` and `disk_free_at_end_gib` describe filesystem space, not a persistent storage quota.
- `status=probe_ok`: only the probe completed; no MP4 expected.
- `status=guard_needs_allow_heavy`: more than 900 frames; user must explicitly opt in after checking the probe.
- `status=guard_projected_timeout`: estimate exceeds 50-minute render allotment after reserving time for encoding/artifact upload.
- `status=guard_projected_disk_full`: predicted JPEG frames exceed safe storage budget.
- `status=render_verified`: a full H.264 MP4 passed ffprobe dimension/FPS/frame-count checks.
- `status=error`: inspect `probe.log` or `full.log`.

Runner configuration depends on public/private repo and GitHub availability. Reference: https://docs.github.com/en/actions/reference/runners/github-hosted-runners and https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions

## Mathematical scaling, not measured performance

For constant samples and scene:

`workload_ratio ≈ (new_width × new_height / (854 × 480)) × (new_fps / 15) × (new_seconds / 10)`

At 1080p30, **10-second** CPU work is about **10.1× the baseline pixel-frame workload**. A 100-second segment would be about **101×**. This is *not* a reliable render-time prediction because scene complexity, RAM, Blender startup, and optimizations vary. Use the benchmark.

## Safety / expected behavior

- Workflow runs only by manual dispatch, with `concurrency` restricting duplicate benchmarks.
- Jobs have a 75-minute timeout; the script reserves 55 minutes for its own budget and terminates Blender when guard thresholds are exceeded.
- Failed/guarded probes still export a report artifact.
- No automatic GitHub Releases or third-party billing.
- Rendered JPEGs are not uploaded as workflow artifacts.
- Changing FPS maintains the intended storyboard time through retimed keyframes.

## Known limitations

- The stress workflow is **configured**, but must be dispatched on GitHub for any new real benchmark data.
- The script monitors Blender RSS and free disk periodically; this is a practical safeguard, **not a proof that resource exhaustion is impossible**.
- Each new workflow runner is ephemeral. The probe and render within a *single* workflow share a filesystem, but distinct workflow runs do not.
- Benchmark long-chunk videos do not automatically produce a complete 180s 1080p/60fps film. A separate full-film workflow variant would require re-rendering all parts at the same chosen settings.
