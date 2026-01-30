# Load Gtk
import gi
gi.require_version('Gtk', '3.0')
gi.require_version ('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

# When the application is launched…
import os
import sys
import subprocess
import json
import threading

base_dir = os.path.dirname(os.path.abspath(__file__))
api_path = os.path.join(base_dir, 'api.py')

def helpcomline():
    print("\nUsage: python3 /home/user/miktool/pythtray.py 'Mikrotik name'\n(where 'Mikrotik name' the name of the router from 'mikrotikname' field in api.conf)")
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
        self.menu.connect("show", self.on_menu_show)
        self.menu_items = {}
        
        # Initial statuses
        statuses = self.get_all_statuses(sys.argv[1])
        if statuses is None:
             self.show_connection_error()
             statuses = {}

        # Create a Gtk.CheckMenuItem
        for key, value in names.items():
            # Default to disabled (True) if status unknown
            manglestatus = statuses.get(value, True)
            
            switch_item = Gtk.CheckMenuItem(label=value)
            self.menu.append(switch_item)
            
            # If manglestatus is False (Enabled), set active (Checked)
            if not manglestatus:
                switch_item.set_active(True)
                
            # Connect the toggle signal to the on_toggled method
            handler_id = switch_item.connect("toggled", self.on_toggled, sys.argv[1], value)
            self.menu_items[value] = (switch_item, handler_id)
        
        # Add the quit menu item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Start periodic refresh every 10 seconds
        GLib.timeout_add_seconds(10, self.periodic_refresh)

    def periodic_refresh(self):
        self.trigger_async_refresh()
        return True

    def trigger_async_refresh(self):
        thread = threading.Thread(target=self.background_refresh_task)
        thread.daemon = True
        thread.start()

    def background_refresh_task(self):
        statuses = self.get_all_statuses(sys.argv[1])
        if statuses is not None:
            GLib.idle_add(self.apply_statuses_to_menu, statuses)

    def apply_statuses_to_menu(self, statuses):
        for name, (item, handler_id) in self.menu_items.items():
            if name in statuses:
                is_disabled = statuses[name]
                is_active = not is_disabled
                
                # Check if state changed to avoid redundant updates
                if item.get_active() != is_active:
                    item.handler_block(handler_id)
                    item.set_active(is_active)
                    item.handler_unblock(handler_id)

    def on_menu_show(self, widget):
        # Refresh statuses when menu is opened
        self.trigger_async_refresh()

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

    def get_all_statuses(self, routername):
        try:
            payload = subprocess.run([api_path, "st", routername], capture_output=True, text=True)
            if payload.returncode != 0:
                # Fallback or error
                print(f"Warning: Failed to get statuses: {payload.stderr}")
                return None
            
            status_map = json.loads(payload.stdout)
            # Normalize map values to boolean
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

    def show_connection_error(self):
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Ошибка подключения"
        )
        dialog.format_secondary_text(
            "Не удалось подключиться к роутеру.\n"
            "Пожалуйста, проверьте пароль, убедитесь, что порт открыт и доступ к API разрешен."
        )
        dialog.run()
        dialog.destroy()
        sys.exit(1)

if __name__ == "__main__" and len(sys.argv) > 1:
    app = SystemTrayApp()
    Gtk.main()
else:
    helpcomline()