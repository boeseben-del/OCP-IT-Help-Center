"""
OCP IT Helpdesk - Windows Desktop Background Agent
======================================================
Captures screenshots and IT support tickets via a global hotkey (F8).
Runs silently in the system tray until activated.

Designed for Windows deployment via PyInstaller.
"""

import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.it_agent.gui import TicketWindow
from src.it_agent.tray import TrayManager


class ITAgentApp(ctk.CTk):
    """Main application - hidden root window that hosts the tray and ticket popups."""

    def __init__(self):
        super().__init__()
        self.title("OCP IT Helpdesk")
        self.geometry("1x1+0+0")
        self.attributes("-alpha", 0)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        self._ticket_window = None
        self._tray = TrayManager(self)

        self.after(500, self._start_background)

    def _start_background(self):
        """Start the tray icon and hotkey listener after the main loop begins."""
        self._tray.start()
        self.withdraw()
        print("[OCP IT Helpdesk] Running in background. Press F8 to open a support ticket.")
        print("[OCP IT Helpdesk] Right-click the system tray icon to quit.")

    def open_ticket_window(self, sysinfo, screenshot_buf, screenshot_img):
        """Open the ticket window (called from the hotkey/tray thread via .after)."""
        if self._ticket_window is not None and self._ticket_window.winfo_exists():
            self._ticket_window.focus_force()
            return

        self._ticket_window = TicketWindow(self, sysinfo, screenshot_buf, screenshot_img)

    def quit_app(self):
        """Gracefully shut down the application."""
        print("[OCP IT Helpdesk] Shutting down...")
        try:
            self._tray.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)


def main():
    print("=" * 50)
    print("  OCP IT Helpdesk")
    print("  Press F8 to open a support ticket")
    print("  The app runs silently in the system tray")
    print("=" * 50)
    app = ITAgentApp()
    app.mainloop()


if __name__ == "__main__":
    main()


# =====================================================================
# PyInstaller Build Command
# =====================================================================
# To compile this into a standalone Windows executable, run:
#
#   pyinstaller --noconsole --onefile --name "OCP_IT_Helpdesk" main.py
#
# Options:
#   --noconsole : Hide the console window (runs as a background app)
#   --onefile   : Package everything into a single .exe
#   --name      : Name the output executable "OCP_IT_Helpdesk.exe"
#
# The resulting executable will be in the `dist/` folder.
# =====================================================================
