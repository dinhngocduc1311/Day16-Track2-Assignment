# Báo cáo ngắn Lab 16 — AWS CPU

1. Tôi benchmark lúc `2026-10-04 23:51:39 +07:00` trên AWS `us-east-1`, EC2 `t3.medium` (2 vCPU, 4 GiB RAM, `x86_64`), từ source commit `55539f67d7c78b43afe334a2ec3271c4bfdbbe2d`.
2. Dataset gốc có 284.807 dòng, 492 fraud; chia train/validation/test là 199.364/28.481/56.962 với seed 42 và stratify.
3. Load dữ liệu mất 2,510 giây; training mất 6,450 giây; LightGBM early-stop tại iteration 149.
4. Test đạt AUC-ROC 0,976085, Accuracy 0,999491, F1 0,841530, Precision 0,905882 và Recall 0,785714; ngưỡng 0,372876 chỉ được chọn trên validation.
5. Latency một dòng median 0,668 ms (p95 1,352 ms, 200 lần sau warm-up); batch 1.000 dòng đạt 169.428,22 dòng/giây (20 lần sau warm-up).
6. Lúc `23:52:44 +07:00` khi benchmark đang chạy, `top` ghi nhận Python 101,0% CPU và RES 188.584 KiB; hệ thống dùng 370 MiB RAM, còn 3,1 GiB available; `ens5` ghi nhận RX 279.833.939 byte/TX 891.974 byte tích lũy.
7. Lúc 22:22 ngày 2026-10-04, Cost Explorer trả về UnblendedCost tạm tính `$1.528809`; Billing Console làm tròn thành `$1.53`, nhóm theo Service. Tài khoản ở gói `PAID/ACTIVE`, credit `$0.00`; chi phí vòng chạy cuối có thể chưa xuất hiện do độ trễ Billing.
8. Tôi đã tải kết quả về laptop và destroy 27 tài nguyên; kiểm tra lúc 23:56 ngày 2026-10-04 xác nhận Terraform state, EC2, NAT, ALB, EIP, EBS rời, VPC, key pair và IAM của lab đều bằng 0.

## Checklist nộp bài

- [x] Ảnh terminal benchmark 4.4 và `benchmark_result.json`.
- [x] Ảnh CPU/RAM/Network 5.1.
- [x] Dữ liệu Cost Explorer API thực tế và ảnh bằng chứng bổ sung.
- [x] Ảnh giao diện AWS Billing thật: tổng chi phí và Cost breakdown theo Service tại `evidence/5.2-aws-console.png` và `evidence/5.2-aws-console-services.png`.
- [x] Mã nguồn Terraform, báo cáo ngắn và bằng chứng cleanup.
- [x] Bộ nộp VLearn tại `submission/`: code benchmark, JSON, report 8 dòng, ảnh và source Terraform sạch.
- [ ] Phụ lục GPU/5.3 — tùy chọn, không tính vào hoàn thành lab chính; hiện bị chặn bởi quota.
