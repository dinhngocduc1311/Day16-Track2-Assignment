# Lab 16 submission — AWS

Đây là bộ nộp cho luồng CPU bắt buộc; phụ lục GPU/vLLM là tùy chọn và không nằm trong bộ nộp này.

| Checkpoint VLearn | Trạng thái | Bằng chứng chính |
|---|---|---|
| CP0 — tài khoản, công cụ, fork | Hoàn tất | [AWS Billing/plan hoạt động](evidence/account-plan-status.txt); [fork và phiên bản công cụ](evidence/source-context.txt) ở commit `55539f67d7c78b43afe334a2ec3271c4bfdbbe2d` |
| CP1 — Terraform, Bastion, SSH compute | Hoàn tất | [`infra/`](infra/), [ảnh live CP1/CP2](screenshots/environment-terminal.png), [`hostname` và `uname -m`](evidence/cp1-cp2.txt) |
| CP2 — thư viện và dataset Kaggle | Hoàn tất | [ảnh live CP1/CP2](screenshots/environment-terminal.png), [`cloud-init`, import, Kaggle CLI và dataset checks](evidence/cp1-cp2.txt) |
| CP3 — LightGBM và JSON | Hoàn tất | [`benchmark.py`](benchmark.py), [`benchmark_result.json`](benchmark_result.json), [ảnh terminal](screenshots/benchmark-terminal.png) |
| CP4 — CPU/RAM/Network và Billing | Hoàn tất | [ảnh live CPU/RAM/Network](screenshots/resources-terminal.png), [raw output](evidence/resources-terminal.txt), [CPU](screenshots/cloudwatch-cpu.png), [Network](screenshots/cloudwatch-network.png), [Billing](screenshots/billing-summary.png), [dịch vụ](screenshots/billing-services.png) |
| CP5 — tải kết quả và cleanup | Hoàn tất | [`report.md`](report.md), [`cleanup-verification.txt`](evidence/cleanup-verification.txt) |

Không có private key, `.env`, Kaggle credentials, access token, Terraform state/plan, `.terraform/` hoặc dataset trong thư mục này.

## Lưu ý khi chạy lại Terraform

`README_aws.md` được giữ nguyên như đề gốc. Source Terraform nộp bài đã siết Bastion và ALB về đúng public IPv4 `/32`, vì vậy cần khai báo biến trước `plan/apply`:

```powershell
$publicIp = (Invoke-RestMethod "https://checkip.amazonaws.com").Trim()
$env:TF_VAR_allowed_cidr = "$publicIp/32"
$env:TF_VAR_enable_gpu = "false"
```
