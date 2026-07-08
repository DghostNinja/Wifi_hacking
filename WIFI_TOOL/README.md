<p align="center">
  <img src="https://img.shields.io/badge/WiFi_Security_Toolkit-v2.0-8A2BE2?style=for-the-badge&logo=wifi" alt="WiFi Toolkit">
  <img src="https://img.shields.io/badge/License-MIT-2563EB?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10%2B-059669?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Linux-FCC624?style=for-the-badge&logo=linux" alt="Linux">
</p>

<h1 align="center">🔓 WiFi Security Testing Toolkit</h1>

<p align="center">
  <b>A curses-based TUI + CLI toolkit for wireless security auditing.</b><br>
  Monitor mode management | Deauth | Evil Twin | WPS | PMKID | Beacon Flood | MAC Spoofing
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| **📡 Multi-Adapter Safe** | Detects and protects the default system adapter; targets only test adapters |
| **📶 Monitor Mode** | One-click enable/disable with automatic interface detection |
| **🔍 Network Scan** | Real-time airodump-ng with parsed CSV summary (BSSID, CH, encryption, clients) |
| **⚔️ Deauth Attack** | Broadcast or directed deauthentication with auto-channel switching |
| **🏴 Evil Twin AP** | Clone any SSID with `airbase-ng` to capture WPA handshakes |
| **🔐 WPS PIN Attack** | Brute-force WPS PINs using `reaver` |
| **🔑 PMKID Capture** | Capture PMKID hashes for offline cracking (`hcxdumptool` + `hcxpcapngtool`) |
| **📶 Beacon Flood** | Flood the area with fake APs using `mdk4` |
| **🔧 MAC Spoofing** | Randomize or set a custom MAC address |
| **📦 Auto-Install** | Detects and installs missing dependencies via `apt` |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/yourname/wifi-toolkit && cd wifi-toolkit

# Launch TUI (interactive menu)
sudo python3 wifitool.py

# Or use CLI directly
python3 wifitool.py list                          # List adapters
sudo python3 wifitool.py monitor -i wlan0         # Enable monitor mode
sudo python3 wifitool.py scan -i wlan0mon         # Scan networks
sudo python3 wifitool.py deauth -a AP_MAC         # Deauth all clients
```

> ⚠️ Most operations require **root privileges** for raw socket access.

---

## 🖥️ TUI Usage

```
┌─────────────────────────────────────────────────────┐
│            WiFi Security Testing Tool                │
├─────────────────────────────────────────────────────┤
│  📡  List Adapters                                   │
│  📶  Enable Monitor Mode                             │
│  📡  Restore Managed Mode                            │
│  🔍  Scan Networks                                   │
│  💾  Packet Capture                                   │
│  ⚔️  Deauth Attack                                   │
│  🏴  Evil Twin AP                                   │
│  🔐  WPS PIN Attack                                  │
│  🔑  PMKID Capture                                   │
│  📶  Beacon Flood                                    │
│  🔧  Spoof MAC Address                               │
│  🔓  Crack Handshake                                 │
│  ─────────────────────────────────────                │
│  ✅  Check Dependencies                              │
│  📦  Install Dependencies                            │
│  🚪  Exit                                           │
├─────────────────────────────────────────────────────┤
│  ↑↓ Navigate  |  Enter Select  |  ESC Back  |  q Quit │
└─────────────────────────────────────────────────────┘
```

| Key | Action |
|---|---|
| `↑` / `↓` or `j` / `k` | Navigate menu |
| `Enter` / `Space` | Select option |
| `ESC` | Go back to previous menu |
| `q` | Quit TUI |

---

## 📖 CLI Reference

### `list`
List all wireless adapters with mode, MAC, and default route status.

```bash
python3 wifitool.py list
```

### `monitor`
Put a wireless adapter into monitor mode.

```bash
sudo wifitool.py monitor -i wlan0
```

Prompts interactively if no `-i` is given. **Warns if the adapter is the default system interface.**

### `managed`
Restore an adapter to managed (normal) mode.

```bash
sudo wifitool.py managed -i wlan0mon
```

### `scan`
Scan for nearby access points and connected clients.

```bash
sudo wifitool.py scan -i wlan0mon -b abg -t 30
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-b` | `abg` | Band: `a`, `b`, `g`, or `abg` |
| `-c` | all | Channel filter |
| `--bssid` | — | Filter by BSSID |
| `-o` | auto | Output file prefix |
| `-t` | `30` | Scan duration (seconds) |

After scanning, displays a parsed summary:
```
  ACCESS POINTS
  BSSID               CH   PWR   ENC    SSID
  ------------------------------------------------------------
  0C:61:F9:17:2D:B4   1    -42   WPA2   Nifemi
  B8:D4:BC:BB:F5:0F   11   -31   WPA2   LEGION

  STATIONS (clients)
  Station MAC          BSSID                Probed SSIDs
  ------------------------------------------------------------
  F2:D7:87:03:6B:94   0C:61:F9:17:2D:B3
```

### `capture`
Capture packets from a target AP to a `.cap` file.

```bash
sudo wifitool.py capture -i wlan0mon -c 6 --bssid AA:BB:CC:DD:EE:FF -t 60
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-c` | `1` | Channel |
| `--bssid` | — | Filter by BSSID |
| `-o` | auto | Output file prefix |
| `-t` | `30` | Capture duration (seconds) |

### `deauth`
Send deauthentication packets to disconnect clients.

```bash
# Broadcast deauth — kicks all clients
sudo wifitool.py deauth -i wlan0mon -a AA:BB:CC:DD:EE:FF -C 11 -n 50

# Directed deauth — kick a specific client
sudo wifitool.py deauth -i wlan0mon -a AA:BB:CC:DD:EE:FF -c 11:22:33:44:55:66 -n 10
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-a` | **required** | Target AP BSSID |
| `-C` | current | AP channel (switches adapter before attack) |
| `-c` | broadcast | Target client MAC |
| `-n` | `10` | Number of deauth packets |
| `-t` | infinite | Timeout (seconds) |

> ⚡ The AP **channel must match** the adapter's current channel. Use `-C` to switch automatically.

### `eviltwin`
Create a rogue access point to capture handshakes.

```bash
sudo wifitool.py eviltwin -i wlan0mon -e "Free WiFi" -c 6 -w handshake
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-e` | `Free WiFi` | SSID for the fake AP |
| `-c` | `1` | Channel |
| `-w` | — | Capture handshakes to file |
| `-t` | infinite | Duration (seconds) |

### `wps`
Brute-force the WPS PIN of a target AP.

```bash
sudo wifitool.py wps -i wlan0mon -a AA:BB:CC:DD:EE:FF -c 1 -t 120
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-a` | **required** | Target AP BSSID |
| `-c` | `1` | AP channel |
| `-t` | `120` | Attack duration (seconds) |

> Requires `reaver`. Install with `sudo wifitool.py install` or `sudo apt install reaver`.

### `pmkid`
Capture PMKID hashes for offline WPA/WPA2 cracking.

```bash
sudo wifitool.py pmkid -i wlan0mon -t 45
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-o` | auto | Output file prefix |
| `-t` | `30` | Capture duration (seconds) |

Outputs a `.hc22000` file compatible with **hashcat** (`-m 22000`).

> Uses `hcxdumptool` + `hcxpcapngtool` if available; falls back to `airodump-ng`.

### `beaconflood`
Flood the area with beacon frames from fake access points.

```bash
# Random SSIDs
sudo wifitool.py beaconflood -i wlan0mon -c 500 -t 30

# Custom SSIDs
sudo wifitool.py beaconflood -i wlan0mon -s "Nifemi,LEGION,Test,FreeWiFi" -c 200 -t 15
```

| Flag | Default | Description |
|---|---|---|
| `-i` | first monitor | Interface |
| `-s` | random | Comma-separated SSID list |
| `-c` | `500` | Packets per SSID |
| `-t` | `30` | Duration (seconds) |

> Requires `mdk4`. Install with `sudo wifitool.py install` or `sudo apt install mdk4`.

### `spoofmac`
Change the MAC address of a wireless adapter.

```bash
# Random MAC
sudo wifitool.py spoofmac -i wlan0

# Custom MAC
sudo wifitool.py spoofmac -i wlan0 -m 00:11:22:33:44:55
```

| Flag | Default | Description |
|---|---|---|
| `-i` | prompts | Interface |
| `-m` | random | Custom MAC address |

Uses `macchanger` if available; falls back to `ip link` natively.

### `crack`
Crack a WPA/WPA2 handshake from a captured `.cap` file.

```bash
sudo wifitool.py crack -c capture-01.cap -w /usr/share/wordlists/rockyou.txt
```

| Flag | Default | Description |
|---|---|---|
| `-c` | **required** | Path to `.cap` file |
| `-w` | **required** | Path to wordlist |
| `--bssid` | all | Filter by BSSID |

### `check`
Verify that all required tools are installed.

```bash
python3 wifitool.py check
```

### `install`
Automatically install missing dependencies via `apt`.

```bash
sudo wifitool.py install
```

Installs: `aircrack-ng`, `iw`, `wireless-tools`, `reaver`, `mdk4`, `hcxdumptool`, `hcxtools`, `macchanger`.

---

## 🛡️ Multi-Adapter Safety

The toolkit **automatically detects** the adapter used for the default route (your main system WiFi). When switching to monitor mode:

- ✅ **Other adapters** — switched without confirmation
- ⚠️ **Default adapter** — shows a warning and requires `y/N` confirmation
- ❌ **Never affects** adapters you don't select

Use a **dedicated USB WiFi adapter** (e.g., Alfa AWUS036ACH, Panda PAU09) for testing to keep your main connection active.

---

## 📦 Dependencies

| Tool | Purpose | Package |
|---|---|---|
| `airmon-ng` | Monitor mode management | `aircrack-ng` |
| `airodump-ng` | Network scanning & capture | `aircrack-ng` |
| `aireplay-ng` | Packet injection | `aircrack-ng` |
| `airbase-ng` | Fake AP / Evil Twin | `aircrack-ng` |
| `aircrack-ng` | WPA handshake cracking | `aircrack-ng` |
| `iw` / `iwconfig` | Wireless config | `iw`, `wireless-tools` |
| `reaver` | WPS PIN attack | `reaver` |
| `mdk4` | Beacon flood | `mdk4` |
| `hcxdumptool` | PMKID capture | `hcxdumptool` |
| `hcxpcapngtool` | PMKID conversion | `hcxtools` |
| `macchanger` | MAC spoofing | `macchanger` |

---

## 📝 License

MIT

---

<p align="center">
  <sub>Built for legitimate security auditing and educational purposes only.</sub><br>
  <sub>Unauthorized use against networks you do not own is illegal.</sub>
</p>
