# Lab 16 evidence status

Collected on 2026-10-03 and refreshed on 2026-10-04 (Asia/Bangkok).

## Completed

- 4.4 authentic benchmark terminal output: `4.4-benchmark-terminal.txt`
- 4.4 screenshot captured directly from the live PowerShell/SSH terminal: `4.4-benchmark-terminal.png`
- CP1/CP2 live terminal screenshot and raw checks: `cp1-cp2-terminal.png`, `final-cp1-cp2.txt`
- 5.1 screenshot captured directly from the live PowerShell/SSH terminal while the benchmark was running: `5.1-terminal-resources.png`
- 5.1 original SSH output: `5.1-terminal-resources.txt`
- 5.1 authentic CloudWatch CPU/credit chart: `5.1-cloudwatch-cpu.png`
- 5.1 authentic CloudWatch network chart: `5.1-cloudwatch-network.png`
- 5.1 clean UTF-8 raw CloudWatch data: `5.1-cloudwatch-metrics.txt`
- 5.2 live AWS resource inventory: `5.2-resource-inventory.txt`
- 5.2 historical Cost Explorer access-denied result: `5.2-cost-explorer-access.txt`
- 5.2 current Cost Explorer status after permission was granted: `5.2-cost-explorer-status.txt`
- 5.2 rendered Cost Explorer ingestion status: `5.2-cost-explorer-status.png`
- 5.2 deterministic cost calculation: `5.2-cost-estimate.txt`
- 5.2 rendered estimate, explicitly marked as not Billing evidence: `5.2-cost-estimate.png`
- 5.2 authentic Cost Explorer API cost data grouped by service: `5.2-cost-explorer-actual.txt`
- 5.2 rendered image from the authentic Cost Explorer API data: `5.2-cost-explorer-actual.png`
- 5.2 authenticated AWS Billing Console cost summary: `5.2-aws-console.png`
- 5.2 authenticated AWS Billing Console breakdown grouped by service: `5.2-aws-console-services.png`
- A.1 authentic GPU quota/request status: `A.1-gpu-quota.txt`
- A.1 rendered GPU quota/request status: `A.1-gpu-quota.png`
- A.2 authentic Hugging Face model/token status with the token omitted: `A.2-huggingface-status.txt`
- A.3 verified GPU replacement plan: `A.3-terraform-plan.txt`
- Final Terraform destroy log: `final-destroy.log`
- 7.3 AWS account plan and Free Tier credit status: `7.3-free-tier-status.txt`
- 7.4 final verification after the temporary CPU rebuild: `final-cleanup-verification.txt`

## Blocked

- Appendix/5.3 GPU evidence: the G/VT quota increase to 4 vCPU is `CASE_OPENED`; applied quota remains 0.

## Remaining optional work

- Optional appendix only: API response, measured cold-start duration and the 5.3 `nvidia-smi` screenshot remain blocked by the 0-vCPU GPU quota.

The CPU infrastructure was temporarily recreated on 2026-10-04 to capture the missing 4.4 evidence, then all 27 managed resources were destroyed. The final verification found no active EC2, NAT Gateway, lab ALB, EIP or available EBS volume. Recreate GPU infrastructure only after the applied quota reaches at least 4 vCPU.
