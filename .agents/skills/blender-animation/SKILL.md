---
name: blender-animation
description: Create and render low-poly Blender animations reliably on limited CPU/memory, with deterministic global frames.
---
# Blender animation render skill

Read AGENTS.md and project.json before editing. Make geometry with bpy; avoid external assets. Every segment uses global frames to keep continuity. Run:
```bash
python3 scripts/pipeline.py doctor
python3 scripts/pipeline.py run --chunk 1 --test-frames 30
```
Never launch all 18 chunks before a small export test. Keep JSON config as the single FPS/resolution source. FFmpeg validates and merges completed MP4s. Do not commit output media or credentials.
