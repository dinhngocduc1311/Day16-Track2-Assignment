#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting user_data setup for CPU LightGBM benchmark node"

export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=5 -o Acquire::ForceIPv4=true update -y
apt-get -o Acquire::Retries=5 -o Acquire::ForceIPv4=true install -y python3 python3-pip libgomp1

python3 -m pip install --retries 5 --upgrade pip
python3 -m pip install --retries 5 lightgbm scikit-learn pandas numpy kaggle

mkdir -p /home/ubuntu/ml-benchmark
chown ubuntu:ubuntu /home/ubuntu/ml-benchmark

echo "CPU environment ready: lightgbm, scikit-learn, pandas, numpy, kaggle installed system-wide."
