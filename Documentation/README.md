# Run "ifconfig" to check if wireless adapter is properly connected to machine & to check adapter name. 
In my case it's (wlan0).
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-12-38.png">

# Followed by "iwconfig" to check what mode your wireless adapeter is in
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-16-01.png">

# "ifconfig wlan0 down", "sudo network check kill" - to drop wlan0 conection and kill all network process connected to machine respectively.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-17-23.png">

# "iwconfig wlan0 mode monitor", "ifconfig wlan0 up" - turn on monitor mode on wireless adapter and bring up wlan0 connection.
<img src="https://github.com/DghostNinja/Wifi_hacking/blob/main/Documentation/Camera%20Roll/Screenshot%20from%202023-08-17%2011-18-09.png">



