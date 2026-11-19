# Robot Seed Animation Farm 🎬

Một dự án Blender Python tái dựng hoạt hình **Robot nhỏ và hạt mầm cuối cùng**. Kịch bản: 0–60s robot khám phá hành tinh; 60–120s robot tìm và chăm sóc hạt mầm; 120–180s cây lớn, hoa nở, robot hạnh phúc.

## Cấu hình
- 180 giây; 15 FPS; 854×480; 18 đoạn × 10 giây.
- Blender headless, Cycles CPU; hình khối low-poly; không cần tải texture hoặc model.
- FFmpeg ghép các đoạn sau khi render.
- Không được coi GitHub Actions/Codex Plus là render farm không giới hạn.

## Kiểm tra trước khi render hàng loạt

```bash
python3 scripts/pipeline.py doctor
python3 scripts/pipeline.py run --chunk 1 --test-frames 30
```

Đo tốc độ và xác nhận tải được `outputs/test/part_001.mp4` về máy trước khi render dài. Cần Blender và FFmpeg có trong PATH. Trên Ubuntu có thể dùng `sudo apt-get install blender ffmpeg`.

## Chạy thật

```bash
python3 scripts/pipeline.py run --chunk 1
python3 scripts/pipeline.py run --chunk 2
# ... chunk 18
python3 scripts/pipeline.py status
python3 scripts/pipeline.py merge
```

Kết quả `outputs/final_film.mp4`. Mỗi đoạn có 150 frame và MP4 được xuất từ frame JPEG; có thể tiếp tục sau khi task ngắt nếu cùng thư mục còn tồn tại.

## Không có Blender trên PC?
Vào GitHub → **Actions** → **Render Blender chunks (manual)** → **Run workflow**, chọn `[1]` trước. Sau khi chạy thành công, tải workflow artifact rồi ghép bằng FFmpeg hoặc OpenCode trên PC. Chọn publish=true chỉ sau khi thử thành công và chấp nhận file MP4 public trong GitHub Releases.

## Quyền riêng tư và chi phí
Repository là Public. GitHub Actions trên repo public có thể chạy runner tiêu chuẩn không thu phí theo chính sách GitHub hiện hành; không đồng nghĩa không có giới hạn. Không lưu token trong source; workflow dùng `GITHUB_TOKEN`.

Bộ ZIP mở rộng từ phiên ChatGPT còn có storyboard, animatic và các script hỗ trợ bổ sung. Repo này chứa pipeline dựng/render cốt lõi, để chạy thử trước.


## 🎬 Render toàn bộ phim chỉ với một workflow

1. Vào **Actions → Render complete 3-minute Blender film → Run workflow**.
2. Để `publish = false` nếu chỉ muốn tải riêng bản video.
3. Workflow dựng 18 đoạn song song tối đa 3 job, kiểm tra từng MP4, ghép tự động thành `final_film.mp4`.
4. Khi thành công, tải artifact `robot-seed-180-seconds` (lưu 7 ngày).

Lưu ý: workflow này **sẽ render lại cả đoạn 1** để 18 đoạn đều nằm trong cùng một run. Bạn đã có bản thử `part_001.mp4` từ run #1. GitHub Actions là dịch vụ của GitHub, không trừ tài nguyên Codex Plus. Nếu chọn publish=true, video cuối được đưa lên GitHub Releases ở repository công khai.


## ⚡ Stress benchmark Blender (manual, isolated)

[Open benchmark workflow](https://github.com/18032010thanh-stack/robot-seed-animation-farm/actions/workflows/benchmark.yml). This is a **separate** workflow: it does not change the existing 180-second film or overwrite `project.json`.

1. Run **720p24**, **8 samples**, **10 seconds**, **mode=probe**. This renders only 16 frames and reports measured time/frame.
2. Inspect the `blender-benchmark-...` artifact: `metrics.json`, `report.md` and `probe.log`. If the estimate fits the budget, rerun with **mode=render** to produce a verified H.264 MP4.
3. Step up to **1080p30**, **1080p60**, **1440p30** and **4k24** (probes first); test **30s** and **100s** only after prior probes pass. For runs exceeding 900 frames, explicitly enable **allow_heavy**; guards can still refuse expensive runs.

The workflow defaults to **probe**, is manual-only, one benchmark at a time, `timeout-minutes: 75`, render budget 55 minutes, RAM kill guard 12.5 GiB, disk reserve 2.5 GiB, predicted runtime safety margin ×1.5. It uploads a 7-day report artifact even if the render fails. A green workflow **does not mean full MP4 exists**: a safety guard may return `probe_ok` or `guard_projected_timeout`; check `metrics.json.status == "render_verified"` for a successful full render.

**FPS retiming:** movie actions are originally scripted at 15 FPS. The `scene_robot_seed.py` keyframing layer now scales keyframe positions to output FPS, preserving the story's 180-second duration at 24/30/60 FPS.

**Important:** A 100-second segment does not increase overall movie runtime: it changes the size of a single 180-second film chunk. Higher resolution/FPS/samples cost substantially more CPU. For 100s at 1080p30 or 1080p60, use **mode=probe** first and read the estimate before enabling heavy mode. Standard public GitHub-hosted runners are not unlimited computing resources.

See [full benchmark procedure](docs/BENCHMARK.md).
