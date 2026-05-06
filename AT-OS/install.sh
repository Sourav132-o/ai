#!/bin/bash
# AT OS - One Command Installer for Termux
# Usage: bash install.sh

clear
echo "╔══════════════════════════════════════════╗"
echo "║          AT OS - INSTALLER               ║"
echo "║     Powered by Kali Linux + Termux       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "[*] Installing required packages..."
pkg update -y && pkg upgrade -y
pkg install -y proot-distro wget curl python3 git

echo ""
echo "[*] Installing Kali Linux..."
proot-distro install kali

echo ""
echo "[*] Setting up AT OS inside Kali..."
proot-distro login kali -- bash /root/kali-setup.sh 2>/dev/null || true

# Copy setup script into Kali
proot-distro login kali -- bash -c "
apt update -y
apt install -y wget curl
wget -q https://raw.githubusercontent.com/Sourav132-o/ai/main/AT-OS/kali-setup.sh -O /tmp/kali-setup.sh
bash /tmp/kali-setup.sh
"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        AT OS INSTALLED SUCCESSFULLY      ║"
echo "║     Type: proot-distro login kali        ║"
echo "╚══════════════════════════════════════════╝"
