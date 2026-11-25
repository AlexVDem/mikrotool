# Load Gtk
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

# When the application is launched…
import os
import sys
import subprocess
import json
import threading

base_dir = os.path.dirname(os.path.abspath(__file__))
api_path = os.path.join(base_dir, 'api.py')

def ensure_disconnected_icon(online_path, offline_path):
    """Ensure that the crossed-out (disconnected) icon exists."""
    if os.path.exists(offline_path):
        return
    try:
        from PIL import Image, ImageDraw
        base = Image.open(online_path).convert('RGBA')
        overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        p1 = (75, 75)
        p2 = (437, 437)

        # Draw dark outline with rounded ends
        r_out = 24
        draw.ellipse([p1[0]-r_out, p1[1]-r_out, p1[0]+r_out, p1[1]+r_out], fill=(0, 0, 0, 210))
        draw.ellipse([p2[0]-r_out, p2[1]-r_out, p2[0]+r_out, p2[1]+r_out], fill=(0, 0, 0, 210))
        draw.line([p1, p2], fill=(0, 0, 0, 210), width=48)

        # Draw red core with rounded ends
        r_in = 18
        draw.ellipse([p1[0]-r_in, p1[1]-r_in, p1[0]+r_in, p1[1]+r_in], fill=(235, 35, 35, 255))
        draw.ellipse([p2[0]-r_in, p2[1]-r_in, p2[0]+r_in, p2[1]+r_in], fill=(235, 35, 35, 255))
        draw.line([p1, p2], fill=(235, 35, 35, 255), width=36)

        result = Image.alpha_composite(base, overlay)
        result.save(offline_path)
    except Exception as e:
        print(f"Warning: could not generate disconnected icon: {e}")

def helpcomline():
    print("\nUsage: python3 /home/user/miktool/miktool.py 'Mikrotik name'\n(where 'Mikrotik name' the name of the router from 'mikrotikname' field in api.conf)")
    sys.exit(0)

class SystemTrayApp:
    def __init__(self):
        self.app_name = "Mikrotik rule switcher"
        self.router_name = sys.argv[1]
        
        self.icon_online_path = os.path.join(base_dir, "lock0.png")
        self.icon_offline_path = os.path.join(base_dir, "lock0_disconnected.png")
        ensure_disconnected_icon(self.icon_online_path, self.icon_offline_path)

        # Connection state: None initially, will become True or False
        self.is_connected = None
        self.refresh_in_progress = False

        # Initialize indicator with offline icon by default until connection is verified
        self.indicator = AppIndicator3.Indicator.new(
            self.app_name, self.icon_offline_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Get the rules and build the menu
        names = self.getconf(self.router_name)
        self.menu = Gtk.Menu()
        self.menu.connect("show", self.on_menu_show)
        self.menu_items = {}

        # Create a Gtk.CheckMenuItem for each rule (initially disabled/insensitive)
        for key, value in names.items():
            switch_item = Gtk.CheckMenuItem(label=value)
            switch_item.set_sensitive(False)
            self.menu.append(switch_item)
                
            # Connect the toggle signal to the on_toggled method
            handler_id = switch_item.connect("toggled", self.on_toggled, self.router_name, value)
            self.menu_items[value] = (switch_item, handler_id)
        
        # Add the quit menu item (always sensitive)
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Initial asynchronous connection check
        self.trigger_async_refresh()

        # Start periodic refresh every 20 seconds
        GLib.timeout_add_seconds(20, self.periodic_refresh)

    def periodic_refresh(self):
        self.trigger_async_refresh()
        return True

    def trigger_async_refresh(self):
        if self.refresh_in_progress:
            return
        self.refresh_in_progress = True
        thread = threading.Thread(target=self.background_refresh_task)
        thread.daemon = True
        thread.start()

    def background_refresh_task(self):
        try:
            statuses = self.get_all_statuses(self.router_name)
            GLib.idle_add(self.apply_statuses_to_menu, statuses)
        finally:
            self.refresh_in_progress = False

    def apply_statuses_to_menu(self, statuses):
        if statuses is not None:
            # Connection is available
            if not self.is_connected:
                self.is_connected = True
                self.indicator.set_icon_full(self.icon_online_path, "Connected")
                for name, (item, handler_id) in self.menu_items.items():
                    item.set_sensitive(True)

            # Apply rule statuses
            for name, (item, handler_id) in self.menu_items.items():
                if name in statuses:
                    is_disabled = statuses[name]
                    is_active = not is_disabled
                    
                    # Check if state changed to avoid redundant updates
                    if item.get_active() != is_active:
                        item.handler_block(handler_id)
                        item.set_active(is_active)
                        item.handler_unblock(handler_id)
        else:
            # Connection is unavailable
            if self.is_connected or self.is_connected is None:
                self.is_connected = False
                self.indicator.set_icon_full(self.icon_offline_path, "Disconnected")
                for name, (item, handler_id) in self.menu_items.items():
                    item.set_sensitive(False)

    def on_menu_show(self, widget):
        # Refresh statuses when menu is opened
        self.trigger_async_refresh()

    def on_toggled(self, menuitem, routername, manglename):
        if not self.is_connected:
            return
        thread = threading.Thread(
            target=self.background_toggle_task,
            args=(routername, manglename),
            daemon=True
        )
        thread.start()

    def background_toggle_task(self, routername, manglename):
        print(f"Toggling rule: {manglename}")
        try:
            payload = subprocess.run(
                [api_path, "sw", routername, manglename],
                capture_output=True,
                text=True,
                timeout=10
            )
            if payload.returncode != 0:
                print(f"Error: {payload.stderr}")
            else:
                print(f"Success: {payload.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Error running subprocess: {e.output}")
        except subprocess.TimeoutExpired:
            print(f"Timeout toggling rule: {manglename}")
        except Exception as e:
            print(f"Unexpected error toggling rule: {e}")

        # Refresh statuses after toggling
        self.trigger_async_refresh()

    def getconf(self, keyconf):
        try:
            payload = subprocess.run([api_path, "r", keyconf], capture_output=True, text=True, timeout=5)
            jsondata = json.loads(payload.stdout)
            rules = jsondata.get('rulecomments', {})
            return rules
        except subprocess.CalledProcessError as e:
            print(f"Error getting config: {e.output}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return {}
        except Exception as e:
            print(f"Error reading config: {e}")
            return {}

    def get_all_statuses(self, routername):
        try:
            payload = subprocess.run([api_path, "st", routername], capture_output=True, text=True, timeout=10)
            if payload.returncode != 0:
                print(f"Warning: Failed to get statuses: {payload.stderr.strip()}")
                return None
            
            status_map = json.loads(payload.stdout)
            normalized = {}
            for k, v in status_map.items():
                if isinstance(v, str):
                    normalized[k] = (v.lower() == "true")
                else:
                    normalized[k] = bool(v)
            return normalized
        except Exception as e:
            print(f"Error getting statuses: {e}")
            return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        app = SystemTrayApp()
        Gtk.main()
    else:
        helpcomline()
