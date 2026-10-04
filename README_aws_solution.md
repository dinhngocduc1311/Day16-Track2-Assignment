# Lời giải và hướng dẫn tối ưu LAB 16 — AWS

> Đây là bản triển khai/lời giải. Đề bài gốc được giữ nguyên tại [`README_aws.md`](README_aws.md).
>
> Luồng CPU bắt buộc và toàn bộ bằng chứng Phần 1–7 đã hoàn tất. Phụ lục GPU không thực hiện vì quota G/VT vẫn là 0 vCPU và request còn `CASE_OPENED`; đây là phần tùy chọn nên không ảnh hưởng kết quả lab chính.

Chào mừng các bạn đến với Lab 16. Trong bài thực hành này, chúng ta sẽ thiết lập một môi trường Cloud AI hoàn chỉnh trên AWS bằng cách sử dụng **Terraform** (Infrastructure as Code).

**Luồng chính (bắt buộc) của bài lab:** triển khai hạ tầng bằng Terraform, khởi động một **CPU instance nhỏ** (`t3.medium`), và huấn luyện + inference một mô hình **LightGBM** (gradient boosting) thực tế trên đó — không cần GPU, không cần xin quota, không cần tài khoản Hugging Face.

Ở cuối bài có thêm **Phụ lục (Tùy chọn — bài tập nâng cao)**: nếu bạn muốn thử sức và tài khoản của mình xin được quota GPU, bạn có thể triển khai một mô hình ngôn ngữ lớn (LLM — `google/gemma-4-E2B-it`) lên máy chủ GPU (NVIDIA L4 24 GB) bằng Docker/vLLM, phục vụ qua Load Balancer. Phần này **không bắt buộc** để hoàn thành lab.

> Không có tài khoản AWS hoặc GCP? Xem [`README_other_clouds.md`](README_other_clouds.md) để làm lab này trên **Azure** hoặc **Oracle Cloud (OCI — có gói Always Free, chi phí $0)**.

---

## Phần 1: Chuẩn bị tài khoản AWS và thiết lập IAM (Least-Privilege)

Để làm việc với AWS an toàn, chúng ta không bao giờ sử dụng tài khoản Root. Thay vào đó, bạn sẽ tạo một IAM User thuộc một IAM Group với các quyền vừa đủ (least-privilege) để Terraform có thể triển khai hạ tầng.

### Bước 1.1: Truy cập AWS Console
1. Đăng nhập vào [AWS Management Console](https://console.aws.amazon.com/) bằng tài khoản Root hoặc tài khoản Admin của bạn.
2. Trên thanh tìm kiếm, gõ **IAM** và chọn dịch vụ **IAM (Identity and Access Management)**.

### Bước 1.2: Tạo IAM Group và gắn quyền (Policies)
1. Trong menu bên trái của IAM, chọn **User groups** -> click **Create group**.
2. Đặt tên nhóm: `AI-Lab-Group`.
3. Trong phần **Attach permissions policies**, bạn cần tìm và tick chọn các quyền (roles) sau. **Giải thích tại sao cần:**
   - `AmazonEC2FullAccess`: Cần thiết để Terraform tạo máy chủ ảo (Bastion Host, Compute Node), Key Pairs, và Security Groups.
   - `AmazonVPCFullAccess`: Cần thiết để Terraform tạo môi trường mạng (VPC, Subnets, Internet Gateway, NAT Gateway, Route Tables).
   - `ElasticLoadBalancingFullAccess`: Cần thiết để tạo Application Load Balancer (ALB) — hạ tầng này vẫn được triển khai trong luồng chính để bạn thực hành, dù chỉ thực sự được dùng để phục vụ API khi làm Phụ lục GPU + LLM.
   - `IAMFullAccess`: Bắt buộc vì Terraform script của chúng ta sẽ tạo một IAM Role và Instance Profile (gắn vào compute node để cấp quyền cho node nếu cần tương tác với AWS services sau này).
4. Click **Create user group**.

### Bước 1.3: Tạo IAM User và lấy Access Keys
1. Trong menu bên trái, chọn **Users** -> click **Create user**.
2. Đặt tên user: `ai-lab-user`. Click Next.
3. Chọn **Add user to group**, tick chọn nhóm `AI-Lab-Group` vừa tạo. Click Next -> **Create user**.
4. Bấm vào tên user `ai-lab-user` vừa tạo. Chuyển sang tab **Security credentials**.
5. Kéo xuống phần **Access keys**, click **Create access key**.
6. Chọn **Command Line Interface (CLI)** -> Check đồng ý -> Next -> **Create access key**.
7. **LƯU Ý:** Copy `Access key ID` và `Secret access key` lưu vào nơi an toàn. Bạn sẽ không thể xem lại Secret key sau khi đóng cửa sổ này.

> **Về GPU Quota:** Luồng chính của bài lab này **không cần** xin tăng quota GPU. Nếu bạn muốn làm thêm Phụ lục (tùy chọn) ở cuối bài để triển khai LLM trên GPU, quy trình xin quota được hướng dẫn riêng ở đó.

---

## Phần 2: Cài đặt và cấu hình môi trường Local

Trên máy tính cá nhân của bạn, mở Terminal/Command Prompt.

### Bước 2.1: Cấu hình AWS CLI
Đảm bảo bạn đã cài đặt [AWS CLI](https://aws.amazon.com/cli/). Gõ lệnh sau để cấu hình tài khoản vừa tạo:
```bash
aws configure
```
Nhập các thông tin:
- **AWS Access Key ID**: (Dán Access key ID của bạn)
- **AWS Secret Access Key**: (Dán Secret access key của bạn)
- **Default region name**: `us-east-1` (Bắt buộc dùng us-east-1 cho lab này)
- **Default output format**: `json`

### Bước 2.2: Tạo SSH Key Pair cho Terraform
Terraform cần một public key có sẵn để tạo Key Pair trên AWS (dùng để SSH vào Bastion Host và Compute Node). Trong thư mục `terraform`, chạy:
```bash
cd terraform
ssh-keygen -t rsa -b 4096 -f lab-key -N ""
```
Lệnh này tạo ra hai file: `lab-key` (private key, giữ bí mật) và `lab-key.pub` (public key, Terraform sẽ đọc file này). Cả hai đã nằm trong `.gitignore` nên sẽ không bị commit nhầm.

*(Nếu bạn định làm Phụ lục GPU + LLM ở cuối bài, phần đó cần thêm một Hugging Face Token — sẽ được hướng dẫn lấy ngay tại đó, không cần chuẩn bị trước.)*

---

## Phần 3: Triển khai Hạ tầng với Terraform

Terraform là công cụ giúp chúng ta khởi tạo hạ tầng AWS hoàn toàn tự động bằng code. Kiến trúc bao gồm:
- Mạng **Private VPC** cách ly hoàn toàn với bên ngoài.
- **Bastion Host** (t3.micro) ở Public Subnet: Dùng làm trạm trung chuyển an toàn để SSH vào Compute Node.
- **Compute Node** (`t3.medium` — 2 vCPU / 4 GB RAM) ở Private Subnet: Đây là nơi bạn sẽ cài đặt và chạy LightGBM. Instance này **mặc định là CPU**; hạ tầng đã được viết sẵn để chuyển sang GPU (`g6.xlarge`) nếu bạn làm Phụ lục ở cuối bài, thông qua biến `enable_gpu`.
- **NAT Gateway**: Cho phép Private Subnet tải package/dataset từ internet.
- **Application Load Balancer (ALB)**: Mở cổng 80 (HTTP), trỏ vào cổng 8000 của Compute Node. Ở luồng CPU mặc định sẽ chưa có gì lắng nghe cổng 8000 nên **health check của ALB sẽ hiển thị "unhealthy" — đây là điều bình thường**, bạn không cần xử lý gì cả trừ khi làm Phụ lục GPU + LLM.

### Bước 3.1: Khởi tạo Terraform
Di chuyển vào thư mục code Terraform (nếu bạn chưa ở đó từ Bước 2.2):
```bash
cd terraform
terraform init
```

### Bước 3.2: Triển khai (Apply)
Giới hạn SSH vào Bastion và HTTP vào ALB theo đúng IPv4 public hiện tại của laptop, sau đó kiểm tra plan trước khi apply. Trên PowerShell:
```powershell
$env:TF_VAR_allowed_cidr = "$((Invoke-RestMethod 'https://checkip.amazonaws.com').Trim())/32"
terraform plan -out=cpu.tfplan
terraform apply cpu.tfplan
```
Nếu dùng WSL/Bash, export cùng giá trị dưới dạng `TF_VAR_allowed_cidr="<IPV4_PUBLIC>/32"`. Khi đổi Wi-Fi/VPN, lấy lại IPv4 trước lần apply tiếp theo. Quá trình tạo tài nguyên thường dành phần lớn thời gian cho NAT Gateway.

*Mẹo: Các bạn hãy bắt đầu bấm giờ (benchmark) từ lúc gõ `yes` ở bước này nhé!*

---

## Phần 4: Kết nối và Huấn luyện mô hình LightGBM trên CPU Node

Khi `terraform apply` chạy xong, màn hình terminal sẽ in ra các thông số quan trọng (Outputs). Trông sẽ giống thế này:
```text
Outputs:

alb_dns_name = "ai-inference-alb-xxxxxx.us-east-1.elb.amazonaws.com"
bastion_public_ip = "100.x.x.x"
endpoint_url = "http://ai-inference-alb-xxxxxx.us-east-1.elb.amazonaws.com/v1/completions"
gpu_private_ip = "10.0.1x.x"
```
`gpu_private_ip` chính là IP private của Compute Node (CPU) bạn vừa tạo — tên biến giữ nguyên từ hạ tầng dùng chung với phần GPU tùy chọn. `endpoint_url`/`alb_dns_name` chỉ có ý nghĩa nếu bạn làm Phụ lục GPU + LLM ở cuối bài; ở luồng CPU bạn có thể bỏ qua hai giá trị này.

### Bước 4.1: SSH vào Compute Node qua Bastion Host
```bash
# SSH vào Bastion Host
ssh -i lab-key ubuntu@<BASTION_PUBLIC_IP>

# Từ Bastion, SSH vào Compute Node (dùng IP private ở trên)
ssh ubuntu@<CPU_PRIVATE_IP>
```

### Bước 4.2: Kiểm tra môi trường ML
Terraform đã tự động cài sẵn Python, LightGBM, scikit-learn, pandas, numpy và Kaggle CLI cho bạn qua `user_data`. Đợi khoảng 1-2 phút sau khi instance chạy xong rồi kiểm tra:
```bash
python3 -c "import lightgbm, sklearn, pandas, numpy; print('OK')"
```
Nếu chưa thấy `OK` (do user_data còn đang chạy), xem log cài đặt bằng:
```bash
sudo tail -f /var/log/user-data.log
```

### Bước 4.3: Tải Dataset từ Kaggle

Chúng ta sẽ dùng **Credit Card Fraud Detection** — bộ dữ liệu chuẩn cho benchmark ML với 284,807 giao dịch thực.

**Lấy Kaggle API Key:**
1. Đăng nhập [kaggle.com](https://www.kaggle.com) -> **Settings** -> **API** -> **Create New Token** -> tải về `kaggle.json`.
2. Copy nội dung file vào máy EC2:

```bash
mkdir -p ~/.kaggle
# Tạo file credentials (thay YOUR_USERNAME và YOUR_KEY):
cat > ~/.kaggle/kaggle.json << 'EOF'
{"username": "YOUR_KAGGLE_USERNAME", "key": "YOUR_KAGGLE_API_KEY"}
EOF
chmod 600 ~/.kaggle/kaggle.json

mkdir -p ~/ml-benchmark
kaggle datasets download -d mlg-ulb/creditcardfraud --unzip -p ~/ml-benchmark/
```

### Bước 4.4: Huấn luyện và Inference với LightGBM

File [`terraform/benchmark.py`](terraform/benchmark.py) đã triển khai benchmark hoàn chỉnh và tối ưu cho `t3.medium`:

- Ép feature về `float32` để giảm gần một nửa RAM so với `float64`.
- Chia dữ liệu có `stratify` thành train/validation/test (70%/10%/20%). Validation dùng cho early stopping và chọn ngưỡng F1; test chỉ dùng để báo cáo kết quả cuối, tránh data leakage.
- Chọn decision threshold tối ưu F1 trên validation và bổ sung PR-AUC vì Accuracy dễ gây hiểu nhầm với dữ liệu gian lận rất lệch lớp.
- Giới hạn LightGBM ở 2 thread đúng với 2 vCPU của `t3.medium`.
- Warm-up rồi đo 200 lần cho latency 1 dòng; đo 20 batch cho throughput 1000 dòng để giảm nhiễu.
- Cố định seed và ghi cấu hình, metrics, confusion matrix, latency vào `benchmark_result.json`.

Từ **terminal local**, tại thư mục gốc của project, copy script thẳng vào Compute Node qua Bastion (thay hai IP bằng output Terraform):

```bash
scp -i terraform/lab-key -o IdentitiesOnly=yes -o "ProxyCommand=ssh -i terraform/lab-key -o IdentitiesOnly=yes -W %h:%p ubuntu@<BASTION_PUBLIC_IP>" terraform/benchmark.py ubuntu@<CPU_PRIVATE_IP>:~/ml-benchmark/
```

Trên **Compute Node**, chạy self-test nhỏ rồi chạy benchmark thật:

```bash
cd ~/ml-benchmark
python3 benchmark.py --self-test
python3 benchmark.py
```

Script mặc định đọc `~/ml-benchmark/creditcard.csv`, in bảng kết quả ra terminal và tạo `~/ml-benchmark/benchmark_result.json`. Nếu tên/vị trí file khác, truyền rõ đường dẫn:

```bash
python3 benchmark.py --data /path/to/creditcard.csv --output benchmark_result.json
```

Kết quả lượt chạy đã kiểm chứng trên `t3.medium` (thời gian có thể dao động nhẹ giữa các lần chạy):

| Metric | Kết quả |
|---|---|
| Thời gian load data | 2.484 s |
| Thời gian training | 6.369 s |
| Best iteration | 149 |
| Decision threshold | 0.372876 |
| AUC-ROC | 0.976085 |
| PR-AUC | 0.868317 |
| Accuracy | 0.999491 |
| F1-Score | 0.841530 |
| Precision | 0.905882 |
| Recall | 0.785714 |
| Inference latency (1 row, median) | 0.648 ms |
| Inference throughput (batch 1000) | 170,145.23 rows/s |

Bằng chứng terminal của lần chạy lại ngày 2026-10-04: [ảnh output benchmark](evidence/4.4-benchmark-terminal.png) và [raw SSH output](evidence/4.4-benchmark-terminal.txt).

Sau khi chụp màn hình terminal, có thể tải file kết quả về máy local để nộp bài:

```bash
scp -i terraform/lab-key -o IdentitiesOnly=yes -o "ProxyCommand=ssh -i terraform/lab-key -o IdentitiesOnly=yes -W %h:%p ubuntu@<BASTION_PUBLIC_IP>" ubuntu@<CPU_PRIVATE_IP>:~/ml-benchmark/benchmark_result.json .
```

---

## Phần 5: Kiểm tra Tài nguyên và Chi phí

Thực hiện ngay sau benchmark; không cần chờ 1 giờ. EC2 basic monitoring và Billing có thể cập nhật chậm, vì vậy ưu tiên số đo trực tiếp trên Compute Node rồi bổ sung ảnh Console khi dữ liệu xuất hiện.

### 5.1: CPU, RAM và Network usage

Trên **Compute Node**, chạy lại benchmark với GNU `time` để đo peak RAM và CPU của đúng tiến trình:

```bash
cd ~/ml-benchmark
/usr/bin/time -v python3 benchmark.py 2>&1 | tee benchmark_resource.txt

free -h
df -h /
ip -s link show ens5
top -b -n 1 | head -n 15
```

- `Percent of CPU this job got`: Linux tính 100% cho mỗi vCPU; `t3.medium` có 2 vCPU nên tiến trình đa luồng có thể gần 200%.
- `Maximum resident set size (kbytes)`: peak RAM của Python, chính xác hơn `free -h` chụp sau khi tiến trình đã thoát.
- `Elapsed (wall clock) time`: thời gian end-to-end của script.
- `RX/TX bytes`: network tích lũy từ lúc boot, không phải riêng một benchmark.
- `free -h` và `df -h /`: RAM và disk còn khả dụng.

Kết quả đã kiểm chứng trên Compute Node hiện tại:

| Chỉ số | Kết quả quan sát |
|---|---:|
| vCPU | 2 |
| CPU tức thời của process trong lúc benchmark | 101.0% |
| RES của process trong snapshot `top` | 188,584 KiB (~184 MiB) |
| RAM trong lúc benchmark | 370 MiB used / 3.1 GiB available |
| Swap | 0 B |
| Network tích lũy | RX 279,833,939 bytes / TX 891,974 bytes |

Chụp màn hình có `Percent of CPU`, `Elapsed`, `Maximum resident set size`, `free -h` và `ip -s link show ens5`.

Bộ bằng chứng 5.1 đã tạo từ lần chạy thật:

- [Ảnh live CPU/RAM/Network trong cửa sổ PowerShell/SSH](evidence/5.1-terminal-resources.png)
- [Raw SSH gốc](evidence/5.1-terminal-resources.txt)
- [Biểu đồ CloudWatch CPU và CPU credit](evidence/5.1-cloudwatch-cpu.png)
- [Biểu đồ CloudWatch NetworkIn/NetworkOut](evidence/5.1-cloudwatch-network.png)
- [Raw CloudWatch UTF-8](evidence/5.1-cloudwatch-metrics.txt)

#### Đối chiếu trên EC2 Monitoring

Vào **EC2 Console → Instances → AI-CPU-LightGBM-Node → Monitoring**, chọn time range **1 hour**, period **5 minutes**. Chụp `CPUUtilization`, `NetworkIn`, `NetworkOut`; có thể thêm `CPUCreditBalance`, `CPUSurplusCreditsCharged` và `StatusCheckFailed`.

Basic monitoring có điểm dữ liệu 5 phút. Benchmark khoảng 11 giây bị làm phẳng trong cửa sổ này; biểu đồ không lên gần 100% là bình thường. Lần kiểm chứng hiện tại ghi nhận `CPUUtilization` max 15.29%, `CPUCreditBalance` 423.08, `CPUSurplusCreditsCharged` 0 và `StatusCheckFailed` 0. CloudWatch mặc định không có RAM/disk-used nếu chưa cài CloudWatch Agent.

### 5.2: Billing / Cost Dashboard

Nếu `ai-lab-user` bị `AccessDeniedException`, tài khoản Admin/Root cấp quyền đọc:

```bash
aws iam attach-user-policy --user-name ai-lab-user --policy-arn arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess
```

Để IAM user mở Billing Console, Root vào **Account → IAM user and role access to Billing information → Edit → Activate IAM access → Update**. Không cần cấp quyền chỉnh sửa Billing.

1. Mở [AWS Billing Console](https://console.aws.amazon.com/billing/) → **Bills** hoặc **Cost Explorer**.
2. Chọn từ ngày tạo lab đến ngày mai, granularity **Daily**, metric **Unblended cost**, **Group by: Service**.
3. Chụp bảng theo service. Compute thường nằm trong `Amazon Elastic Compute Cloud - Compute`; NAT Gateway/EBS/data transfer có thể nằm trong `EC2 - Other`; ALB nằm trong `Elastic Load Balancing`.
4. Nếu chi phí mới chưa xuất hiện, chụp trạng thái hiện tại và dùng bảng ước tính dưới đây. Không giữ hạ tầng chạy để chờ Billing.

Kiểm tra bằng AWS CLI trên PowerShell:

```powershell
$start = (Get-Date).ToString("yyyy-MM-dd")
$end = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
aws ce get-cost-and-usage --time-period Start=$start,End=$end --granularity DAILY --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE
```

Ước tính cố định cho hạ tầng CPU hiện tại tại `us-east-1`:

| Tài nguyên | Cách tính | Chi phí ước tính |
|---|---|---:|
| Compute Node | `t3.medium` | $0.041800/h |
| Bastion Host | `t3.micro` | $0.010400/h |
| NAT Gateway | 1 gateway | $0.045000/h |
| Application Load Balancer | phí nền, chưa gồm LCU | $0.022500/h |
| Public IPv4 | 4 × $0.005/h | $0.020000/h |
| EBS | 30 GiB gp3 + 8 GiB gp2, quy đổi 730 h/tháng | ~$0.004384/h |
| **Tổng cố định** | chưa gồm phí biến đổi | **~$0.144084/h** |
| **Khoảng 2.5 giờ** | $0.144084 × 2.5 | **~$0.360210** |

Chưa tính NAT data processing, ALB LCU, data transfer ra Internet và thuế.

Bằng chứng hỗ trợ đã tạo:

- [Inventory tài nguyên AWS đang chạy](evidence/5.2-resource-inventory.txt)
- [Lỗi quyền Cost Explorer ban đầu](evidence/5.2-cost-explorer-access.txt)
- [Trạng thái Cost Explorer sau khi cấp quyền](evidence/5.2-cost-explorer-status.txt)
- [Ảnh trạng thái Cost Explorer](evidence/5.2-cost-explorer-status.png) — dữ liệu đang được AWS ingest, không phải ảnh chi phí đã phát sinh.
- [Phép tính chi phí dạng text](evidence/5.2-cost-estimate.txt)
- [Ảnh phép tính chi phí](evidence/5.2-cost-estimate.png) — được gắn rõ **ESTIMATE ONLY**, không thay thế ảnh Billing Console.
- [Dữ liệu Cost Explorer thực tế theo service](evidence/5.2-cost-explorer-actual.txt)
- [Ảnh render từ dữ liệu Cost Explorer API thực tế](evidence/5.2-cost-explorer-actual.png) — bằng chứng API bổ sung, không thay thế ảnh giao diện Console.
- [Ảnh AWS Billing Console — tổng chi phí $1,53](evidence/5.2-aws-console.png)
- [Ảnh AWS Billing Console — Cost breakdown theo Service](evidence/5.2-aws-console-services.png)

Tiêu chí **Screenshot AWS Billing/Cost Dashboard** đã hoàn tất bằng hai ảnh Console thật ở trên. Ảnh tổng quan ghi nhận month-to-date cost `$1.53`; ảnh breakdown dùng `Group costs by: Service` và hiển thị `EC2 - Other`, `Amazon Elastic Compute Cloud - Compute`, `Amazon Elastic Load Balancing`, `Amazon Virtual Private Cloud`, `AWS Cost Explorer` và `Others`. Các con số này nhất quán với dữ liệu Cost Explorer API `$1.528809` (khác biệt chỉ do Console làm tròn).

Chỉ sang Phần 7 và chạy `terraform destroy` sau khi đã lưu đủ ảnh Billing và, nếu làm phụ lục, đủ bằng chứng GPU.

### 5.3: GPU usage (Tùy chọn)

Chỉ làm sau khi hoàn thành **Phụ lục A.1–A.4**, container vLLM đang chạy và target ALB đã healthy. Trên GPU Node:

```bash
nvidia-smi
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv
```

Để bắt được utilization thay vì 0% lúc idle, mở một cửa sổ SSH:

```bash
watch -n 1 nvidia-smi
```

Giữ cửa sổ này mở rồi gọi API từ local theo A.4. Chụp khi Python/vLLM xuất hiện trong Processes và VRAM đang dùng. Nếu chỉ làm luồng CPU, bỏ qua 5.3; `nvidia-smi: command not found` là đúng.

---

## Phần 6: Tiêu chí nộp bài (Deliverables)

Để hoàn thành Lab 16, sinh viên cần thu thập và nộp các kết quả sau:
1. **Screenshot terminal** chạy `python3 benchmark.py` với toàn bộ output kết quả.
2. **File `benchmark_result.json`** chứa metrics đầy đủ (training time, AUC, inference latency, throughput...).
3. **Screenshot tài nguyên**: `top`/`free -h` (hoặc EC2 Monitoring tab) thể hiện CPU/RAM/Network usage.
4. **Screenshot AWS Billing/Cost Dashboard** thể hiện các dịch vụ đang phát sinh chi phí (EC2, NAT Gateway).
5. **Mã nguồn:** Nén thư mục `terraform/` đã chạy thành công.
6. **Báo cáo ngắn** (5-10 dòng): nhận xét về kết quả training time, AUC, inference speed trên CPU.

Toàn bộ deliverable bắt buộc đã được gom sạch tại [`submission/`](submission/); xem [manifest đối chiếu CP0–CP5](submission/README.md).

*(Nếu bạn làm thêm Phụ lục GPU + LLM, có thêm các mục nộp bài riêng — xem cuối Phụ lục.)*

---

## Phần 7: Dọn dẹp tài nguyên (CỰC KỲ QUAN TRỌNG)

NAT Gateway tính phí theo giờ ngay cả khi dùng CPU instance nhỏ. Ngay sau khi test thành công và chụp ảnh nộp bài, bạn **BẮT BUỘC** phải xóa toàn bộ tài nguyên để tránh mất tiền.

Giữ `TF_VAR_allowed_cidr` như lúc apply (hoặc khai báo lại IPv4 public `/32` nếu mở terminal mới), rồi chạy trong thư mục `terraform`:
```powershell
$env:TF_VAR_allowed_cidr = "$((Invoke-RestMethod 'https://checkip.amazonaws.com').Trim())/32"
terraform destroy
terraform state list
```
Gõ `yes` khi được hỏi, đợi `Destroy complete!`, rồi xác nhận `terraform state list` không trả về tài nguyên nào. Cuối cùng đối chiếu EC2, NAT Gateway, ALB, EIP và EBS trên Console.

**Trạng thái mới nhất (2026-10-04 23:56 +07:00):** hạ tầng CPU được dựng lại tạm thời để thu bộ bằng chứng live đồng bộ, sau đó destroy thành công: `Destroy complete! Resources: 27 destroyed.` Terraform state, EC2, NAT Gateway, lab ALB, EIP, EBS rời, VPC, key pair và IAM role/profile của lab đều bằng 0. GPU quota vẫn là 0 vCPU với trạng thái `CASE_OPENED`. Xem [xác minh cleanup cuối](evidence/final-cleanup-verification.txt).

---

## Phụ lục (Tùy chọn — Bài tập nâng cao): Triển khai GPU + LLM Inference (vLLM)

> Không bắt buộc. Chỉ thực hiện khi tài khoản AWS đã được duyệt GPU quota; phần này không ảnh hưởng yêu cầu chính của Lab 16.

Mục tiêu: chạy `google/gemma-4-E2B-it` bằng Docker/vLLM trên GPU Node trong Private Subnet, nhận request qua ALB và thu thập bằng chứng cho mục 5.3.

> **Sửa cấu hình quan trọng:** không dùng `g4dn.xlarge`/T4 16 GB. Recipe chính thức của vLLM yêu cầu Gemma 4 E2B ở BF16 có ít nhất một NVIDIA GPU 24 GB, nên Terraform mặc định dùng `g6.xlarge` với NVIDIA L4 24 GB. Xem [vLLM Gemma 4 recipe](https://docs.vllm.ai/projects/recipes/en/stable/Google/Gemma4.html) và [AWS EC2 G6](https://aws.amazon.com/ec2/instance-types/g6/).

### A.1: Kiểm tra và tăng GPU quota

`g6.xlarge` cần 4 vCPU thuộc quota **Running On-Demand G and VT instances** tại `us-east-1`.

1. Mở **Service Quotas → AWS services → Amazon EC2**.
2. Tìm **Running On-Demand G and VT instances**.
3. Nếu **Applied account-level quota value** dưới 4, chọn **Request quota increase**, nhập ít nhất **4**.
4. Chờ request thành **Approved**. Quota theo Region; duyệt ở Region khác không áp dụng cho `us-east-1`.
5. Trong **EC2 → Instance types**, kiểm tra `g6.xlarge` được offer tại `us-east-1`. Quota được duyệt không đảm bảo capacity ở mọi Availability Zone.

`VcpuLimitExceeded` nghĩa là quota chưa đủ. `InsufficientInstanceCapacity` nghĩa là tạm thiếu capacity; thử lại sau hoặc đặt `TF_VAR_gpu_instance_type=g5.xlarge` — vẫn có GPU 24 GB nhưng là thế hệ trước.

Trạng thái lần triển khai hiện tại: AWS đã nhận yêu cầu tăng từ 0 lên 4 vCPU và chuyển sang `CASE_OPENED`; chưa chạy `terraform apply` khi applied quota vẫn là 0. Xem [raw quota](evidence/A.1-gpu-quota.txt) và [ảnh trạng thái quota](evidence/A.1-gpu-quota.png).

### A.2: Kiểm tra quyền Hugging Face và lưu token an toàn

Tại thời điểm kiểm chứng ngày 2026-10-03, API Hugging Face báo `google/gemma-4-E2B-it` là public (`private=false`, `gated=false`) với license `apache-2.0`. Vì vậy trang model **không có nút Accept license/Request access**; đây là hành vi đúng, không phải lỗi tài khoản.

Token `Read` hoặc fine-grained token chỉ còn là tùy chọn để download có xác thực/rate limit tốt hơn. Lưu token ở `.env` local đã được `.gitignore`, không đặt vào `terraform.tfvars`, `TF_VAR_hf_token`, Git, screenshot, EC2 user data hay Terraform state.

Kiểm tra trạng thái public mà không lộ token:

```powershell
$model = Invoke-RestMethod 'https://huggingface.co/api/models/google/gemma-4-E2B-it'
$model | Select-Object id, private, gated, disabled
```

### A.3: Chuyển Compute Node sang GPU

Bảo đảm `benchmark_result.json` và ảnh CPU đã về local vì CPU Node sẽ bị thay thế. Trên **PowerShell**, tại thư mục `terraform`:

```powershell
$envPath = Resolve-Path ..\.env
Get-Content $envPath | ForEach-Object {
  if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
    Set-Item -Path "Env:$($matches[1].Trim())" -Value $matches[2]
  }
}

$startedAt = Get-Date
$env:TF_VAR_allowed_cidr = "$((Invoke-RestMethod 'https://checkip.amazonaws.com').Trim())/32"

terraform fmt -check
terraform validate
terraform plan -out gpu.tfplan
terraform apply gpu.tfplan
```

`allowed_cidr` giới hạn ALB và Bastion cho public IP hiện tại; Terraform từ chối GPU mode nếu vẫn là `0.0.0.0/0`. Nếu đổi Wi-Fi/VPN, lấy lại IP rồi apply lại.

```powershell
terraform output
terraform state show aws_instance.gpu_node
```

Kỳ vọng: `instance_type = "g6.xlarge"`, tag `AI-GPU-Inference-Node`, root EBS 150 GiB đã mã hóa. VPC, NAT, Bastion và ALB được giữ nếu vẫn còn trong state.

> Không apply lại hạ tầng CPU chỉ để thử thay đổi. Apply khi quota đã duyệt và bạn thực sự sẵn sàng chuyển GPU, vì instance/root disk sẽ bị thay.

### A.4: Khởi động vLLM và kiểm tra endpoint

#### A.4.1: SSH và chờ bootstrap

Tại thư mục `terraform` trên PowerShell:

```powershell
$bastionIp = terraform output -raw bastion_public_ip
$gpuIp = terraform output -raw gpu_private_ip
ssh -i lab-key -o IdentitiesOnly=yes -o "ProxyCommand=ssh -i lab-key -o IdentitiesOnly=yes -W %h:%p ubuntu@$bastionIp" ubuntu@$gpuIp
```

Trên GPU Node:

```bash
cloud-init status --wait
sudo tail -n 50 /var/log/user-data.log
nvidia-smi
sudo docker image inspect vllm/vllm-openai:gemma4 >/dev/null && echo "vLLM image ready"
```

Bootstrap chỉ bật Docker và tải image `vllm/vllm-openai:gemma4`; chưa chứa token và chưa mở model server.

#### A.4.2: Nhập API key ẩn và chạy server

```bash
read -rsp "vLLM API key từ .env local: " VLLM_API_KEY; echo

sudo docker rm -f vllm 2>/dev/null || true
sudo docker run -d --name vllm \
  --gpus all \
  --restart unless-stopped \
  --volume /opt/huggingface:/root/.cache/huggingface \
  --publish 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:gemma4 \
  --model google/gemma-4-E2B-it \
  --max-model-len 2048 \
  --limit-mm-per-prompt image=0,audio=0 \
  --gpu-memory-utilization 0.90 \
  --api-key "$VLLM_API_KEY" \
  --host 0.0.0.0 \
  --port 8000

unset VLLM_API_KEY
sudo docker logs -f vllm
```

API key lấy từ `VLLM_API_KEY` trong `.env` local và được nhập bằng prompt ẩn; không đưa nó vào ảnh. Cờ `--limit-mm-per-prompt image=0,audio=0` tắt multimodal không dùng để tiết kiệm VRAM. `Ctrl+C` chỉ thoát log, không dừng container.

Nếu model đổi lại thành gated trong tương lai, kiểm tra trạng thái API ở A.2 rồi mới cấp `HF_TOKEN` cho container. `CUDA out of memory`: xác nhận đúng `g6.xlarge` và hai cờ giới hạn. Xem lỗi:

```bash
sudo docker ps -a
sudo docker logs --tail 200 vllm
```

#### A.4.3: Gọi API qua ALB

Trở lại PowerShell local:

```powershell
$alb = terraform output -raw alb_dns_name
$apiKey = $env:VLLM_API_KEY
if (-not $apiKey) { throw "VLLM_API_KEY chưa được load từ .env" }

curl.exe -i "http://$alb/health"

$body = @{
  model = "google/gemma-4-E2B-it"
  messages = @(
    @{ role = "system"; content = "Bạn là một trợ lý AI hữu ích." }
    @{ role = "user"; content = "Hãy giải thích Bastion Host trong AWS là gì?" }
  )
  max_tokens = 150
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Method Post `
  -Uri "http://$alb/v1/chat/completions" `
  -Headers @{ Authorization = "Bearer $apiKey" } `
  -ContentType "application/json" `
  -Body $body

$response.choices[0].message.content
(Get-Date) - $startedAt
```

`/health` phải trả HTTP 200. Nếu 503, đợi target group healthy rồi kiểm tra `docker logs` và cổng 8000. Cold start tính từ `$startedAt` trước apply đến response đầu tiên; ghi thời gian thực tế, không giả định dưới 15 phút.

ALB lab dùng HTTP nhưng đã giới hạn source IP và API có Bearer key. Production phải dùng HTTPS/ACM cùng cơ chế xác thực/quản lý secret phù hợp.

### A.5: Đo GPU usage cho mục 5.3

Mở hai terminal:

- SSH trên GPU Node: chạy `watch -n 1 nvidia-smi`.
- Local: gọi lại request A.4 với `max_tokens = 512` để inference đủ lâu cho ảnh chụp.

Sau request:

```bash
nvidia-smi --query-gpu=name,driver_version,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv
sudo docker stats --no-stream vllm
```

Ảnh nên thấy NVIDIA L4, VRAM đang dùng và process Python/vLLM. Utilization có thể về 0% ngay sau khi sinh xong token, nên ảnh `watch` trong lúc request có giá trị hơn ảnh idle.

### A.6: Tiêu chí nộp bài và dọn dẹp

1. Screenshot API response thành công; che API key và mọi token.
2. Cold start time thực tế từ trước apply đến response đầu tiên.
3. Screenshot `nvidia-smi` trong lúc inference, có GPU, utilization, VRAM và process vLLM.
4. Nếu lỗi, kèm 20–30 dòng cuối của `docker logs` và cách xử lý.

Sau khi đủ bằng chứng:

```powershell
terraform destroy
Remove-Item Env:TF_VAR_enable_gpu -ErrorAction SilentlyContinue
Remove-Item Env:TF_VAR_allowed_cidr -ErrorAction SilentlyContinue
```

Xác nhận `Destroy complete!`, kiểm tra EC2/NAT Gateway/ALB không còn, rồi revoke Hugging Face token nếu chỉ tạo cho lab. GPU, NAT, ALB, EBS và public IPv4 vẫn tính phí tới khi tài nguyên bị xóa.
