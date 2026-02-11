"""System tray icon and global hotkey management."""

import threading
import os
from PIL import Image, ImageDraw
from src.it_agent.sysinfo import gather_all
from src.it_agent.screenshot import capture_screenshot


def create_tray_icon_image(size=64, color=(0, 122, 204)):
    """Generate a simple colored square icon for the system tray."""
    img = Image.new("RGB", (size, size), color)
    draw = ImageDraw.Draw(img)
    margin = size // 6
    draw.rectangle(
        [margin, margin, size - margin, size - margin],
        fill=(255, 255, 255),
    )
    draw.text(
        (size // 4, size // 6),
        "IT",
        fill=color,
    )
    return img


def _resource_path(relative_path):
    """Get absolute path to resource, works for PyInstaller bundled apps."""
    try:
        import sys
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


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

            icon_image = create_tray_icon_image()
            menu = pystray.Menu(
                MenuItem("Open (F8)", self._on_open),
                MenuItem("Quit", self._on_quit),
            )
            self._tray_icon = pystray.Icon(
                "IT Agent",
                icon_image,
                "IT Support Agent - Press F8",
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
                "username": "Unknown", "cpu_usage": 0, "ram_usage": 0,
                "os_info": "Unknown", "active_window": "Unknown",
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
