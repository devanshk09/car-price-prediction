#!/bin/bash
# Paste this into "Advanced details -> User data" when launching the EC2 instance
# (Ubuntu Server 24.04 LTS, t3.micro). It runs once, as root, on first boot.
set -euxo pipefail

apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip wget curl

# t3.micro has only 1 GB RAM; 1 GB of swap stops pip installs from running out of memory.
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Install the CodeDeploy agent (v2) for whichever region this instance runs in.
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
cd /home/ubuntu
wget "https://aws-codedeploy-${REGION}.s3.${REGION}.amazonaws.com/latestv2/install"
chmod +x ./install
./install auto
systemctl enable --now codedeploy-agent
