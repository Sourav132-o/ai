#!/bin/bash
# ╔══════════════════════════════════════════════════╗
# ║           AT OS - TERMUX INSTALLER              ║
# ║        Kali Linux Custom Environment            ║
# ╚══════════════════════════════════════════════════╝

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║              AT OS - INSTALLER                  ║"
echo "║         Powered by Kali Linux + Termux          ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}[*] Updating Termux packages...${NC}"
pkg update -y && pkg upgrade -y

echo -e "${YELLOW}[*] Installing required packages...${NC}"
pkg install -y proot-distro wget curl git python3 openssh

echo -e "${YELLOW}[*] Installing Kali Linux...${NC}"
proot-distro install kali

echo -e "${YELLOW}[*] Running AT OS setup inside Kali...${NC}"

proot-distro login kali -- bash -c "
apt update -y && apt upgrade -y

echo '[*] Installing core tools...'
apt install -y python3 python3-pip curl wget git

echo '[*] Installing all Kali tools (this takes 2-5 hours)...'
apt install -y kali-linux-everything 2>/dev/null || apt install -y kali-linux-large

pip3 install requests 2>/dev/null

mkdir -p /opt/at-os

# pentest-ai tool
cat > /opt/at-os/pentest-ai.py << 'PYEOF'
import requests, subprocess, os, re

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'llama3'

def query_ollama(task):
    try:
        res = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': f'Kali Linux command engine. Output ONLY the raw command. No notes.\nTask: {task}',
            'stream': False,
            'options': {'temperature': 0.0}
        }, timeout=120).json()['response'].strip()
        res = re.sub(r'\`\`\`[a-z]*\n|\`\`\`', '', res)
        return res.split('\n')[0].split('|')[0].strip().rstrip(' -.,')
    except:
        return None

def main():
    os.system('clear')
    print('╔══════════════════════════════════════════╗')
    print('║       AT OS - PENTEST AI ENGINE          ║')
    print('║     Type task or full command            ║')
    print('║     Type "menu" to go back               ║')
    print('╚══════════════════════════════════════════╝')
    while True:
        try:
            user_input = input('\n[AT OS] > ').strip()
            if not user_input: continue
            if user_input.lower() in ['exit','quit','menu']: break
            cmd = user_input if len(user_input.split()) > 1 else query_ollama(user_input)
            if not cmd:
                print('[!] AI unavailable. Type full command.')
                continue
            print(f'\n[CMD] {cmd}')
            if input('Run? (y/n): ').lower() == 'y':
                subprocess.run(cmd, shell=True)
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    main()
PYEOF

# main menu
cat > /opt/at-os/menu.sh << 'MENUEOF'
#!/bin/bash
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

while true; do
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║             AT OS - MAIN MENU               ║"
    echo "╠══════════════════════════════════════════════╣"
    echo -e "║  ${GREEN}1.${NC} Pentest AI (God Mode)                   ║"
    echo -e "║  ${GREEN}2.${NC} Nmap - Network Scanner                  ║"
    echo -e "║  ${GREEN}3.${NC} SQLMap - SQL Injection                  ║"
    echo -e "║  ${GREEN}4.${NC} Nikto - Web Scanner                     ║"
    echo -e "║  ${GREEN}5.${NC} Hydra - Brute Force                     ║"
    echo -e "║  ${GREEN}6.${NC} WPScan - WordPress Scanner              ║"
    echo -e "║  ${GREEN}7.${NC} Gobuster - Directory Scanner            ║"
    echo -e "║  ${GREEN}8.${NC} Metasploit Framework                    ║"
    echo -e "║  ${GREEN}9.${NC} Custom Command                          ║"
    echo -e "║  ${RED}0.${NC} Exit                                     ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
    read -p "  Select > " choice
    case \$choice in
        1) python3 /opt/at-os/pentest-ai.py ;;
        2) read -p "Target IP/Domain: " t; nmap -A -v "\$t" ;;
        3) read -p "Target URL: " u; sqlmap -u "\$u" --batch --level=3 ;;
        4) read -p "Target URL: " u; nikto -h "\$u" ;;
        5) read -p "Target IP: " t; read -p "Username: " u; hydra -l "\$u" -P /usr/share/wordlists/rockyou.txt "\$t" ssh ;;
        6) read -p "Target URL: " u; wpscan --url "\$u" --enumerate ;;
        7) read -p "Target URL: " u; gobuster dir -u "\$u" -w /usr/share/wordlists/dirb/common.txt ;;
        8) msfconsole ;;
        9) read -p "Command: " cmd; bash -c "\$cmd" ;;
        0) exit ;;
        *) echo 'Invalid.' ;;
    esac
    echo ''
    read -p 'Press Enter to continue...'
done
MENUEOF

chmod +x /opt/at-os/menu.sh

# MOTD / Banner
cat > /etc/motd << 'MOTDEOF'

╔══════════════════════════════════════════════════╗
║                                                  ║
║               AT OS - GOD MODE                  ║
║          All Kali Tools Ready                   ║
║                                                  ║
║   pentest-ai  →  AI Command Engine              ║
║   at-menu     →  Main Tool Menu                 ║
║                                                  ║
╚══════════════════════════════════════════════════╝

MOTDEOF

# Aliases
cat >> /root/.bashrc << 'BASHEOF'
alias pentest-ai='python3 /opt/at-os/pentest-ai.py'
alias at-menu='bash /opt/at-os/menu.sh'
cat /etc/motd
BASHEOF

echo ''
echo '✓ AT OS Setup Complete!'
"

# Termux shortcut
cat > "$HOME/.shortcuts/AT-OS" << 'EOF'
#!/bin/bash
proot-distro login kali
EOF
chmod +x "$HOME/.shortcuts/AT-OS" 2>/dev/null || true

echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║          AT OS INSTALLED SUCCESSFULLY!          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  Kali তে ঢুকতে:                                ║"
echo "║    proot-distro login kali                      ║"
echo "║                                                  ║"
echo "║  Tools চালাতে:                                  ║"
echo "║    at-menu       → Main Menu                    ║"
echo "║    pentest-ai    → AI Engine                    ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
