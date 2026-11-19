# START AUTO BENCHMARK — 2026-11-20

This is a **one-time trigger marker** for `.github/workflows/auto-benchmark.yml`.

The automatic workflow measures 480p15, 720p24, 1080p30, 1080p60, 1440p30, 4k24, and 16/32 Cycles samples **sequentially**. It then makes an adaptive decision whether to render a 100-second 480p15 segment or a higher-resolution 10-second sample.

- It waits behind any active `robot-seed-benchmark` run.
- Standard GitHub-hosted Ubuntu runner, public repository, no paid runner.
- Controlled per-test and overall time budgets, memory and disk guards.
- Final report and MP4 (when feasible) available as GitHub Actions artifacts.
- Do not change this marker: changing it again is an explicit rerun.

See `docs/AUTO_BENCHMARK.md` for instructions and guard details.
