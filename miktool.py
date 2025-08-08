# Load Gtk
import gi
gi.require_version('Gtk', '3.0')
gi.require_version ('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3

# When the application is launched…
import os
import sys
import subprocess
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
api_path = os.path.join(base_dir, 'api.py')

def helpcomline():
    print("\nUsage: python3 /home/user/miktool/miktool.py 'Mikrotik name'\n(where 'Mikrotik name' the name of the router from 'mikrotikname' field in api.conf)")
    sys.exit(0)

class SystemTrayApp:
    def __init__(self):
        self.app_name = "Mikrotik rule switcher"
        self.icon_path = os.path.join(os.path.dirname(__file__), "lock0.png")
        self.indicator = AppIndicator3.Indicator.new(
            self.app_name, self.icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Get the rules and build the menu
        names = self.getconf(sys.argv[1])
        self.menu = Gtk.Menu()
        
        # Create a Gtk.CheckMenuItem
        for key, value in names.items():
            manglestatus = self.getmanglestatus(sys.argv[1], value)     
            switch_item = Gtk.CheckMenuItem(label=value)
            self.menu.append(switch_item)
            if not manglestatus:
                switch_item.set_active(True)
            # Connect the toggle signal to the on_toggled method
            switch_item.connect("toggled", self.on_toggled, sys.argv[1], value)
        
        # Add the quit menu item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def on_toggled(self, menuitem, routername, manglename):
        # The 'sw' command should toggle the state regardless of whether the option is on or off
        print(f"Toggling rule: {manglename}")
        try:
            payload = subprocess.run([api_path, "sw", routername, manglename], capture_output=True, text=True)
            if payload.returncode != 0:
                print(f"Error: {payload.stderr}")
            else:
                print(f"Success: {payload.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Error running subprocess: {e.output}")

    def getconf(self, keyconf):
        try:
            payload = subprocess.run([api_path, "r", keyconf], capture_output=True, text=True)
            jsondata = json.loads(payload.stdout)
            rules = jsondata['rulecomments']
            return rules
        except subprocess.CalledProcessError as e:
            print(f"Error getting config: {e.output}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return {}

    def getmanglestatus(self, routername, manglename):
        try:
            payload = subprocess.run([api_path, "st", routername, manglename], capture_output=True, text=True)
            jsondata = json.loads(payload.stderr)
            return jsondata
        except subprocess.CalledProcessError as e:
            print(f"Error getting mangle status: {e.output}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return False

if __name__ == "__main__" and len(sys.argv) > 1:
    app = SystemTrayApp()
    Gtk.main()
else:
    helpcomline()