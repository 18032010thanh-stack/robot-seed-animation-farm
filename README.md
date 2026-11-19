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
