#!/bin/bash
# AT OS - Main Menu

while true; do
    clear
    echo "╔══════════════════════════════════════════╗"
    echo "║           AT OS - MAIN MENU              ║"
    echo "╠══════════════════════════════════════════╣"
    echo "║  1. Pentest AI (God Mode)                ║"
    echo "║  2. Nmap Scanner                         ║"
    echo "║  3. SQLMap                               ║"
    echo "║  4. Metasploit                           ║"
    echo "║  5. Hydra Brute Force                    ║"
    echo "║  6. Nikto Web Scanner                    ║"
    echo "║  7. WPScan                               ║"
    echo "║  8. Custom Command                       ║"
    echo "║  0. Exit                                 ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    read -p "[AT OS] > " choice

    case $choice in
        1) python3 /opt/at-os/pentest-ai.py ;;
        2) read -p "Target: " t; nmap -A "$t" ;;
        3) read -p "URL: " u; sqlmap -u "$u" --batch ;;
        4) msfconsole ;;
        5) read -p "Target: " t; read -p "User: " u; hydra -l "$u" -P /usr/share/wordlists/rockyou.txt "$t" ssh ;;
        6) read -p "URL: " u; nikto -h "$u" ;;
        7) read -p "URL: " u; wpscan --url "$u" ;;
        8) read -p "Command: " cmd; bash -c "$cmd" ;;
        0) break ;;
        *) echo "Invalid option" ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
