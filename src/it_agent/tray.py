"""System tray icon and global hotkey management."""

import threading
import os
import sys
from PIL import Image, ImageDraw
from src.it_agent.sysinfo import gather_all
from src.it_agent.screenshot import capture_screenshot


def _resource_path(relative_path):
    """Get absolute path to resource, works for PyInstaller bundled apps."""
    try:
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def load_tray_icon():
    """Load the OCP logo as the tray icon, or generate a fallback."""
    try:
        logo_path = _resource_path(os.path.join("assets", "ocp_tray.png"))
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img = img.resize((64, 64), Image.LANCZOS)
            return img
    except Exception:
        pass

    try:
        logo_path = _resource_path(os.path.join("assets", "ocp_logo.png"))
        if os.path.exists(logo_path):
            img = Image.open(logo_path).convert("RGBA")
            max_dim = max(img.width, img.height)
            square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
            square.paste(img, ((max_dim - img.width) // 2, (max_dim - img.height) // 2))
            return square.resize((64, 64), Image.LANCZOS)
    except Exception:
        pass

    img = Image.new("RGB", (64, 64), (0, 46, 86))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 54, 54], fill=(71, 143, 204))
    draw.text((14, 20), "OCP", fill=(255, 255, 255))
    return img


class TrayManager:
    """Manages the system tray icon, hotkey listener, and GUI trigger."""

    def __init__(self, app):
        self.app = app
        self._tray_icon = None
        self._hotkey_thread = None
        self._tray_thread = None
        self._running = True
        self._keyboard_module = None

    def start(self):
        """Start the system tray icon and global hotkey listener."""
        self._tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self._tray_thread.start()

        self._hotkey_thread = threading.Thread(target=self._run_hotkey, daemon=True)
        self._hotkey_thread.start()

    def _run_tray(self):
        """Run the pystray system tray icon."""
        try:
            import pystray
            from pystray import MenuItem

            icon_image = load_tray_icon()
            menu = pystray.Menu(
                MenuItem("Open (F8)", self._on_open),
                MenuItem("Quit", self._on_quit),
            )
            self._tray_icon = pystray.Icon(
                "OCP IT Helpdesk",
                icon_image,
                "OCP IT Helpdesk - Press F8",
                menu,
            )
            self._tray_icon.run()
        except Exception as e:
            print(f"[TrayManager] Could not start tray icon: {e}")

    def _run_hotkey(self):
        """Listen for the global F8 hotkey."""
        try:
            import keyboard
            self._keyboard_module = keyboard
            keyboard.add_hotkey("F8", self._on_hotkey_pressed, suppress=False)
            while self._running:
                keyboard.read_event(suppress=False)
        except ImportError:
            print("[TrayManager] 'keyboard' library not available. Hotkey disabled.")
        except Exception as e:
            if self._running:
                print(f"[TrayManager] Hotkey error: {e}")
                print("[TrayManager] Note: The 'keyboard' library requires root/admin privileges on Linux.")

    def _on_hotkey_pressed(self):
        """Handle the F8 key press: capture screenshot, then open GUI."""
        if not self._running:
            return

        try:
            screenshot_buf, screenshot_img = capture_screenshot()
        except Exception as e:
            print(f"[TrayManager] Screenshot capture failed: {e}")
            screenshot_buf, screenshot_img = None, None

        try:
            sysinfo = gather_all()
        except Exception as e:
            print(f"[TrayManager] System info gathering failed: {e}")
            sysinfo = {
                "hostname": "Unknown", "local_ip": "N/A", "public_ip": "N/A",
                "mac_address": "N/A", "username": "Unknown", "user_email": "",
                "cpu_usage": 0, "ram_usage": 0, "disk_usage": 0,
                "os_info": "Unknown", "active_window": "Unknown",
                "uptime": "N/A", "battery": "N/A",
                "total_ram": "N/A", "logical_processors": "N/A",
            }

        self.app.after(0, self.app.open_ticket_window, sysinfo, screenshot_buf, screenshot_img)

    def _on_open(self, icon=None, item=None):
        """Open the ticket window from tray menu."""
        self._on_hotkey_pressed()

    def _on_quit(self, icon=None, item=None):
        """Gracefully exit the application."""
        self._running = False
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.app.after(0, self.app.quit_app)

    def stop(self):
        """Stop the tray icon and clean up hotkey listener."""
        self._running = False

        if self._keyboard_module:
            try:
                self._keyboard_module.unhook_all()
            except Exception:
                pass

        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
