# START FULL HD 1080p30 FILM — 2026-11-20

This file is a one-time explicit trigger for:
`.github/workflows/render-fullhd.yml`.

The workflow automatically starts with this commit on `main`:
- 180-second movie in 1920×1080 at 30 FPS.
- 18 × 10-second chunks, 300 frames per chunk, 5,400 total frames.
- Up to 3 standard public GitHub-hosted runners in parallel, 4 threads per renderer.
- Cycles 8 samples, verified H.264 segments, FFmpeg assembly and checked final MP4.
- Result artifact `robot-seed-fullhd-1080p30-180s` is retained for 7 days.

The successful 480p film is unchanged. This marker must not be edited
except for an intentional one-time rerender.
