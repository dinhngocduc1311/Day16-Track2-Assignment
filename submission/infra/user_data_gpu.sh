#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Preparing GPU node for vLLM"

# Ensure docker is running (pre-installed on DL AMI)
systemctl enable --now docker
install -d -m 700 /opt/huggingface

# The token is supplied interactively after SSH, never through Terraform/user data.
docker pull vllm/vllm-openai:gemma4

echo "GPU node ready; start vLLM with the command documented in README_aws.md"
