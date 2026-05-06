#!/bin/bash
# AT OS - Kali Internal Setup Script

echo "[*] Updating Kali..."
apt update -y && apt upgrade -y

echo "[*] Installing all 600+ Kali tools (this will take 2-5 hours)..."
apt install -y kali-linux-everything

echo "[*] Installing Python dependencies..."
apt install -y python3 python3-pip
pip3 install requests

echo "[*] Downloading AT OS tools..."
mkdir -p /opt/at-os
wget -q https://raw.githubusercontent.com/Sourav132-o/ai/main/AT-OS/pentest-ai.py -O /opt/at-os/pentest-ai.py
wget -q https://raw.githubusercontent.com/Sourav132-o/ai/main/AT-OS/motd -O /etc/motd
wget -q https://raw.githubusercontent.com/Sourav132-o/ai/main/AT-OS/start.sh -O /opt/at-os/start.sh
chmod +x /opt/at-os/start.sh

echo "[*] Setting up auto-start..."
cat >> /root/.bashrc << 'EOF'

# AT OS Auto-start
cat /etc/motd
alias pentest-ai='python3 /opt/at-os/pentest-ai.py'
alias at-menu='/opt/at-os/start.sh'
EOF

echo ""
echo "[+] AT OS Setup Complete!"
