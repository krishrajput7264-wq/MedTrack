#!/usr/bin/env bash
# ==============================================================================
# MedTrack AWS EC2 Automated Deployment Script for Amazon Linux 2023 / AL2
# ==============================================================================

set -e

echo "=== [1/6] Updating packages & installing system dependencies ==="
sudo dnf update -y || sudo yum update -y
sudo dnf install -y python3 python3-pip git nginx || sudo yum install -y python3 python3-pip git nginx

echo "=== [2/6] Setting up Python virtual environment ==="
cd /home/ec2-user/medtrack
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [3/6] Creating logs & uploads directories ==="
mkdir -p /home/ec2-user/medtrack/logs
mkdir -p /home/ec2-user/medtrack/uploads
mkdir -p /home/ec2-user/medtrack/data
sudo chown -R ec2-user:ec2-user /home/ec2-user/medtrack

echo "=== [4/6] Configuring Nginx reverse proxy ==="
sudo cp deploy/nginx.conf /etc/nginx/conf.d/medtrack.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "=== [5/6] Enabling & Starting MedTrack Systemd Daemon ==="
sudo cp deploy/medtrack.service /etc/systemd/system/medtrack.service
sudo systemctl daemon-reload
sudo systemctl enable medtrack
sudo systemctl restart medtrack

echo "=== [6/6] Verifying status ==="
sudo systemctl status medtrack --no-pager
echo ""
echo "=============================================================================="
echo "MedTrack is now LIVE on your AWS EC2 instance!"
echo "Access the application via your EC2 Public IPv4 address or Route 53 domain."
echo "=============================================================================="
