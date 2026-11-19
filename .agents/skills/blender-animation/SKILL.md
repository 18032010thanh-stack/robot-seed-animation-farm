---
name: blender-animation
description: Dựng, render và ghép phim hoạt hình 3D bằng Blender Python, GitHub Actions và FFmpeg trên máy yếu; hỗ trợ chia đoạn, chạy song song, kiểm tra artifact, xuất MP4 và khắc phục lỗi.
---

# Blender Animation Farm — SKILL

## Mục tiêu

Tự động hóa việc làm hoạt hình 3D bằng Blender headless và mã Python; chia video thành các đoạn độc lập, render trên GitHub Actions, kiểm chứng MP4, tải artifact và ghép video bằng FFmpeg. Ưu tiên chi phí bổ sung thấp, sử dụng tài nguyên hợp lệ, không yêu cầu PC mạnh.

**Bằng chứng thực tế:** Repo mẫu https://github.com/18032010thanh-stack/robot-seed-animation-farm — GitHub Actions run #2 (ID 44532366846), ngày 19/11/2026: 18/18 đoạn thành công, job ghép thành công, xuất artifact robot-seed-180-seconds chứa phim 180 giây. Đây là bài kiểm chứng cho *dự án mẫu*, không bảo đảm tốc độ render với mọi cảnh.

## Kích hoạt khi

- Người dùng muốn làm video/hoạt hình 3D bằng Blender nhưng máy yếu.
- Người dùng muốn thiết kế pipeline render phân đoạn, GitHub Actions, FFmpeg, cloud.
- Người dùng gửi link GitHub Actions để kiểm tra tiến độ, lỗi, artifact.
- Người dùng muốn tái sử dụng pipeline này cho phim mới dài 2–3 phút hoặc hơn.

## Nguyên tắc bắt buộc

1. Đọc AGENTS.md, project.json, scripts/, .github/workflows/ và trạng thái repository trước khi chỉnh sửa. Không ghi đè file không liên quan.
2. Viết storyboard → mô hình 3D bằng bpy → keyframe trên timeline **toàn cục** → benchmark ngắn → render phân đoạn → ghép → kiểm tra.
3. Không chạy toàn bộ 18 đoạn trước khi kiểm tra một clip thật có hình, codec, FPS đúng và xuất ra được.
4. Không để *.mp4, frames/, outputs/, cache/, node_modules/, .env vào Git; dùng GitHub Artifacts hoặc Releases.
5. **Không trộn frame cũ của một phiên bản cảnh với frame của phiên bản mới.** Kiểm tra fingerprint script/cấu hình; chia đoạn phải dùng cùng góc máy, ánh sáng, seed ngẫu nhiên.
6. Không coi Plus/Codex Cloud là render farm miễn phí không giới hạn; GitHub Actions là hệ thống **riêng của GitHub** với hạn mức, chính sách, thời gian chạy và điều khoản.
7. Không tự công khai phim: giữ publish=false trừ khi người dùng muốn đưa MP4 lên GitHub Releases công khai.
8. Không đưa GitHub token vào repo, log hoặc prompt. Workflow dùng GITHUB_TOKEN và permissions đủ dùng.
9. Kiểm tra xem đã có một full workflow đang chạy trước khi kích hoạt thêm; tránh render trùng và tốn tài nguyên.

## Cấu trúc repo nên có

~~~text
project/
├── AGENTS.md
├── project.json
├── .gitignore
├── .agents/skills/blender-animation/SKILL.md
├── scripts/
│   ├── scene_robot_seed.py
│   └── pipeline.py
├── .github/workflows/
│   ├── render.yml          # thử 1/vài đoạn
│   └── render-full.yml     # render toàn bộ, ghép tự động
└── docs/
    ├── STORYBOARD.md
    └── CODEX_PROMPT.md
~~~

AGENTS.md ngắn; SKILL.md chứa quy trình. Không để agent đọc toàn bộ video để tiết kiệm token.

.gitignore tối thiểu:

~~~gitignore
*.mp4
frames/
outputs/
cache/
node_modules/
__pycache__/
.env
~~~

## Thông số mẫu đã chạy thành công

~~~json
{
  "duration_seconds": 180,
  "fps": 15,
  "width": 854,
  "height": 480,
  "chunk_seconds": 10,
  "render_engine": "CYCLES",
  "samples": 8,
  "crf": 24
}
~~~

= 2700 frame / 18 đoạn x 150 frame; đoạn 1 lấy frame 1–150, đoạn 18 lấy 2551–2700. Với dự án khác, phải **tính lại** số chunk từ cấu hình, không giả định luôn bằng 18.

CPU-first: low-poly, ánh sáng đơn giản, tránh fluid/cloth/particles, reuse vật liệu/mesh. Chỉ thử Eevee nếu môi trường hỗ trợ; pipeline mẫu đã kiểm chứng với Cycles CPU và Blender 5.0.1.

## Thao tác

### 1) Kiểm tra

Từ gốc repository (máy có Blender, ffmpeg và ffprobe trong PATH):

~~~bash
python3 scripts/pipeline.py doctor
python3 scripts/pipeline.py run --chunk 1 --test-frames 30 --threads 2
ffprobe -v error -show_entries stream=codec_name,width,height,avg_frame_rate,nb_frames -of default=noprint_wrappers=1 outputs/test/part_001.mp4
~~~

30 frame / 15 FPS = 2 giây. Xem clip để phát hiện thiếu camera, đen màn hình, sai bố cục, ánh sáng hoặc chuyển động. Nếu không có Blender cục bộ, thiết lập benchmark trên GitHub Actions hoặc Codex môi trường đủ quyền, rồi **xác nhận log thật**.

### 2) Render từng đoạn và tiếp tục khi lỗi

~~~bash
python3 scripts/pipeline.py run --chunk 1 --threads 2
python3 scripts/pipeline.py run --chunk 2 --threads 2
python3 scripts/pipeline.py status
~~~

Pipeline tạo JPEG theo số frame toàn cục vào outputs/frames/part_NNN/, sau đó mã hóa outputs/part_NNN.mp4 (H.264), kiểm tra bằng ffprobe và ghi checksum. Nếu cùng workspace còn frame và fingerprint không đổi thì có thể bỏ qua frame đã render. **GitHub-hosted runners không bảo đảm giữ frame giữa các lần chạy**, phải thiết kế artifact/cache riêng nếu muốn tiếp tục trên một runner mới.

### 3) Chạy trọn phim bằng GitHub Actions

Workflow của repo mẫu:

https://github.com/18032010thanh-stack/robot-seed-animation-farm/actions/workflows/render-full.yml

Thao tác: Actions → Render complete 3-minute Blender film → Run workflow → branch main → publish=false.

- Matrix 18 chunk; tối đa **3 job song song**, mỗi job render 10 giây bằng 2 thread.
- Mỗi job xuất artifact part-N.
- Job assemble chỉ chạy sau khi các job đều thành công; tải đủ 18 part và chạy pipeline merge.
- Artifact đầu ra **robot-seed-180-seconds** chứa final_film.mp4, retention trong workflow mẫu là **7 ngày** (chính sách có thể thay đổi).
- Bật publish=true chỉ khi muốn video cuối được công khai trên Releases.
- Workflow full **render lại part 1**, không tự động lấy part từ một lần chạy trước.

### 4) Ghép và xác minh

~~~bash
python3 scripts/pipeline.py merge
ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,width,height,avg_frame_rate,nb_frames -of json outputs/final_film.mp4
~~~

Điều kiện: MP4 có cùng codec, fps, kích thước; đúng tổng frame; xem khung hình đầu/giữa/cuối và đoạn nối 10s/20s/… Đừng dùng FFmpeg -c copy khi thông số không thống nhất.

### 5) Giải quyết các lỗi đã gặp

- **Workflow invalid:** run 44532029356 bị lỗi do dùng biểu thức inputs.publish trong permissions.contents. Ở cấp workflow dùng contents: read; tại job assemble dùng contents: write; điều kiện publish để ở step.
- **Node.js 20 deprecated:** bản cũ dùng checkout@v4, upload-artifact@v4. Bản full đã cập nhật checkout@v6, upload-artifact@v6, download-artifact@v7. Luôn kiểm tra action versions/compatibility hiện tại.
- **Status Waiting:** có thể do concurrency chặn full workflow thứ hai; kiểm tra run đang render trước. Không coi chờ là render lỗi. Hủy run dư thay vì chạy song song trùng phim.
- **Run Success nhưng không thấy video:** mở jobs, kiểm tra job assemble, tên artifact, retention và bước upload. Không khẳng định thành công chỉ dựa badge.
- **Hết RAM hoặc quá lâu:** giảm samples, polygon, độ phân giải hoặc thời lượng chunk, giới hạn parallel; benchmark lại trước full.
- **Artifact hết hạn:** tải và sao lưu video trước ngày hết hạn, không trông chờ GitHub Actions giữ file vĩnh viễn.

## Phản hồi chuẩn cho người dùng

Báo trạng thái đã kiểm chứng (repo, run ID, job, artifact), số đoạn thành công, video đã ghép hay chưa, lỗi cụ thể, và **một bước tiếp theo** với link trực tiếp. Không tự nhận đã render/upload/đăng video nếu chưa có log hoặc file chứng minh. Không tự động bật workflow tốn tài nguyên hay public asset khi người dùng chưa yêu cầu rõ.

## Checklist hoàn tất

- [ ] Script Blender dựng lại được scene không cần assets bên ngoài.
- [ ] Clip benchmark phát được; fps, codec, frame count đúng.
- [ ] Các đoạn dùng chung timeline và animation nhất quán.
- [ ] 100% chunk job thành công, mọi part có artifact.
- [ ] Assemble job thành công, final_film.mp4 hợp lệ.
- [ ] Người dùng có link/download video và hiểu thời hạn lưu.
