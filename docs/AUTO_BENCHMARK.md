# AUTO benchmark: no supervision required

## Lý do có workflow này

Mỗi lần chạy thử phải chọn thông số thủ công không phù hợp khi người dùng đi học. Workflow này được khởi chạy **một lần duy nhất** khi cập nhật tệp `docs/START_AUTO_BENCHMARK_2026-11-20.md`, hoặc có thể chạy lại bằng nút **Run workflow**.

## Quy trình tự động

1. Chờ bài benchmark thủ công hiện tại kết thúc: sử dụng cùng concurrency group `robot-seed-benchmark`, không chiếm máy song song.
2. Trên **một máy chủ tiêu chuẩn GitHub Ubuntu**, chạy theo thứ tự:
   - 480p15 / 8 samples / 100s (probe 16 frame)
   - 720p24 / 8 samples / 100s (probe 16 frame)
   - 1080p30 / 8 samples / 100s (probe 16 frame)
   - 1080p60 / 8 samples / 100s (probe 16 frame)
   - 1440p30 / 8 samples / 100s (probe 16 frame)
   - 4k24 / 8 samples / 100s (probe 16 frame)
   - 720p24 / 8 samples / 10s, mốc 150s (hoa nở)
   - 1080p30 / 16 samples / 10s, mốc 150s
   - 1080p30 / 32 samples / 10s, mốc 0s
3. Mỗi probe tối đa 8 phút, cả chuỗi tối đa 50 phút, giới hạn Blender RAM 12,5 GiB và giữ 2,5 GiB dung lượng dự trữ.
4. Tự tạo **summary.json**, **SUMMARY.md** (bảng so sánh), log từng bài. Nếu một phép thử lỗi, ghi nhận và tiếp tục.
5. Sau khi đã đo, job thứ hai tự lựa chọn **render thật 100 giây ở 480p15** nếu dự báo đủ an toàn. Nếu quá chậm, thử **1080p60 10 giây**, rồi **1080p30 10 giây**, cuối cùng **720p24 10 giây**, chỉ khi có probe thành công và dự báo dưới ngân sách.
6. Xuất artifact metrics và MP4 (nếu có). Không ghi đè bộ phim 3 phút đã có.

## Kết quả để xem khi trở lại

GitHub → Actions → **AUTO Blender stress suite (no supervision)** → lần chạy mới → Artifacts:
- `auto-blender-all-probes-...`: số đo tất cả bài và báo cáo `SUMMARY.md`.
- `auto-blender-final-decision-...`: quyết định tự động, log và MP4 nếu hoàn thành.
- `auto-sweep-summary-...`: dữ liệu JSON chuyển sang giai đoạn hai.

**Đọc trạng thái thay vì chỉ nhìn màu xanh của workflow.** `probe_ok` là phép thử 16 frame, không phải video hoàn chỉnh. `render_verified` mới là MP4 được kiểm tra FFprobe.

## Giới hạn và chi phí

Sử dụng `ubuntu-latest` runner tiêu chuẩn trên repo public. Không dùng paid runner/GPU hay token ngoài. Trigger tự động chỉ theo đúng một tệp marker để tránh khởi chạy lại sau mỗi commit. Ngân sách job 65 phút + 80 phút, script bên trong tự dừng sớm theo budget và kiểm tra tài nguyên. GitHub Actions vẫn chịu điều kiện, hạn mức và quyền truy cập của nền tảng. Nếu đang có benchmark chạy, workflow sẽ vào hàng chờ.

Chưa có phép đo mới cho loạt này trước khi GitHub thực sự chạy. Thời lượng 100 giây được thử thông qua dự báo; render thật 100 giây chỉ được tiến hành khi kết quả đo cho thấy an toàn.
