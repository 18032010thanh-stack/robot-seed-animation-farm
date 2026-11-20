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

## Bản nâng cấp Blender 3D (155 giây)

Workflow mới: [In This Town — 3D Blender 155s Vietsub](https://github.com/18032010thanh-stack/robot-seed-animation-farm/actions/workflows/in-this-town-3d.yml).

- **3D thật:** tạo thị trấn, nhân vật khối, đồng hồ, phòng ngủ, người canh và bóng đen bằng Blender Python (`scripts/scene_town3d.py`); không sử dụng mô hình thương hiệu.
- **Đúng 155 giây:** giữ nguyên 31 cảnh × 5 giây, 480×854, 15 FPS, tổng 2.325 frame.
- **Phụ đề Việt:** `vietsub.srt` được chèn vào video sau render bằng FFmpeg/libass; giọng tổng hợp offline như bản 2D.
- **Pipeline:** `scripts/render_town3d.py` chia 16 đoạn (15×10 giây và đoạn cuối 5 giây), kiểm tra khung hình/codec và ghép MP4.
- **Tối ưu cloud:** bài thử 30 frame chạy trước; nếu thành công thì mới render các đoạn (tối đa 3 job cùng lúc). Không chạy workflow này trùng lặp.

Chạy thử ở môi trường có Blender và FFmpeg:

```bash
python3 scripts/render_town3d.py doctor
python3 scripts/render_town3d.py render --chunk 1 --test-frames 30 --quality fast --threads 2
```

Để render thủ công tất cả, mở Actions → *In This Town — 3D Blender 155s Vietsub* → Run workflow. Workflow cũng được thiết lập thử một lần khi thêm file cấu hình ban đầu; nếu job render hoàn tất, tải artifact `in-this-town-155s-3d-vietsub`. Chưa coi phim 3D là hoàn thành nếu chưa có job `assemble` và artifact cuối.
