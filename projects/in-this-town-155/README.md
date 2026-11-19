# In This Town — 155s Vietnamese subtitles

This is an **original 2D block-character animation**, inspired by the premise in the user's uploaded 20-second kit. It is not affiliated with Roblox. The uploaded kit itself is **not republished here** because its redistribution license is unknown.

- 155 seconds, 31 scenes × 5 seconds, 480×854, 15 fps, 2325 total frames.
- Vietnamese subtitles burned into every frame + an exported SRT.
- Vietnamese **synthetic eSpeak** narration; no commercial music or external model assets.

## One-shot local render

Requires numpy, pillow, ffmpeg, Noto Sans fonts, espeak-ng (or espeak).

Run from this project's directory: `python3 scripts/make_animatic.py`.

## Chunked GitHub Actions render

Go to GitHub Actions → **In This Town 155s Vietsub** → Run workflow.

This renders **16 chunks** (15×10 seconds + final 5 seconds), maximum three concurrent render jobs. An assemble job verifies all clips, concatenates with FFmpeg, builds Vietnamese narration and creates artifact `in-this-town-155s-vietsub`.

Artifacts are temporary; default retention 7 days. The video is not automatically published to GitHub Releases.

This is a reusable adaptation of the established render-farm **workflow structure** but does **not** run the original kit's Blender engine. A Blender 3D upgrade is a separate production step.
