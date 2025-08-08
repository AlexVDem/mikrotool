Mikrotool - small CLI and GUI tool to switch ON/OFF mangle rules on Mikrotik routers.

If you want to use this tool, just complete steps:
1. Allow API access on Mikrotik router: open WinBox, connect to router, open IP Service List (IP -> Services) and enable API service with 8728 port. If you don't see that rule - this is a bug, just reboot router and repeat step 1. Note: API - SSL not supporter yet (in development).
2. If you are Linux Gnome user, and want to use GUI tool to get mangle switcher in system tray, you have to install GUI library. Open console and give command: 'sudo apt update -y && sudo apt install gir1.2-appindicator3-0.1 -y' 
3. Edit api.conf file (nano api.conf) and change credentials of your routers: names, IPs, passwords. Do not change file structure, just credentials.

CLI tool usage:
python3 /home/user/miktool/api.py OPTIONS [Router] [Mangle]
OPTIONS: c [onfig] will show api.conf config with all settings,
		 r [outer config] will show api.conf for specific router, works only with [Router] name from api.conf,
		 sw [itch] ON/OFF mangle rules, works only with [Router] name and [Mangle] rule name from api.conf
		 Example: python3 /home/user/miktool/api.py sw Mikrotik0 'VPN for User1'\n(will switch mangle with 'VPN for User1' name ON or OFF on Mikrotik0 router)")

GUI tool usage:
python3 /home/user/miktool/miktool.py 'Mikrotik name'
where 'Mikrotik name' the name of the router from 'mikrotikname' field in api.conf