"""CustomTkinter GUI for OCP IT Helpdesk."""

import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime
from src.it_agent.screenshot import image_to_thumbnail
from src.it_agent.api import send_ticket
import threading
import io
import os
import sys

OCP_NAVY = "#002E56"
OCP_BLUE = "#478FCC"
OCP_CYAN = "#5FC8EB"
OCP_SILVER = "#A6A8AB"
OCP_DARK_BG = "#0A1929"
OCP_CARD_BG = "#112240"
OCP_INPUT_BG = "#1A3050"
OCP_TEXT = "#E0E8F0"
OCP_TEXT_DIM = "#8899AA"

ctk.set_appearance_mode("dark")


def _resource_path(relative_path):
    """Get absolute path to resource, works for PyInstaller bundled apps."""
    try:
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


class TicketWindow(ctk.CTkToplevel):
    """The OCP IT Helpdesk popup window."""

    def __init__(self, master, sysinfo, screenshot_buf, screenshot_img):
        super().__init__(master)
        self.title("OCP IT Helpdesk")
        self.geometry("620x820")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.configure(fg_color=OCP_DARK_BG)

        self.sysinfo = sysinfo
        self.screenshot_buf = screenshot_buf
        self.screenshot_img = screenshot_img
        self.screenshot_removed = False
        self._tk_thumb = None
        self._tk_logo = None

        self._build_ui()
        self.after(100, lambda: self.focus_force())

    def _build_ui(self):
        pad = {"padx": 20, "pady": (5, 5)}

        header_frame = ctk.CTkFrame(self, fg_color=OCP_NAVY, corner_radius=0, height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(expand=True, fill="both", padx=20)

        try:
            logo_path = _resource_path(os.path.join("assets", "ocp_logo.png"))
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_height = 50
                ratio = logo_height / logo_img.height
                logo_width = int(logo_img.width * ratio)
                logo_img = logo_img.resize((logo_width, logo_height), Image.LANCZOS)
                self._tk_logo = ImageTk.PhotoImage(logo_img)
                logo_label = ctk.CTkLabel(header_inner, image=self._tk_logo, text="")
                logo_label.pack(side="left", pady=15)
        except Exception:
            pass

        title_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_frame.pack(side="right", pady=15)

        ctk.CTkLabel(
            title_frame, text="IT Helpdesk",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(anchor="e")

        ctk.CTkLabel(
            title_frame, text="Support Ticket",
            font=ctk.CTkFont(size=12),
            text_color=OCP_CYAN,
        ).pack(anchor="e")

        accent_bar = ctk.CTkFrame(self, fg_color=OCP_BLUE, height=3, corner_radius=0)
        accent_bar.pack(fill="x")

        scroll_frame = ctk.CTkFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        info_card = ctk.CTkFrame(scroll_frame, fg_color=OCP_CARD_BG, corner_radius=8)
        info_card.pack(fill="x", padx=20, pady=(15, 8))

        info_header = ctk.CTkFrame(info_card, fg_color="transparent")
        info_header.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(
            info_header, text="System Information",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OCP_CYAN,
        ).pack(side="left")

        info_grid = ctk.CTkFrame(info_card, fg_color="transparent")
        info_grid.pack(fill="x", padx=15, pady=(0, 10))

        left_col = ctk.CTkFrame(info_grid, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True)
        right_col = ctk.CTkFrame(info_grid, fg_color="transparent")
        right_col.pack(side="right", fill="x", expand=True)

        left_items = [
            f"Host: {self.sysinfo['hostname']}",
            f"User: {self.sysinfo['username']}",
            f"OS: {self.sysinfo['os_info']}",
            f"IP: {self.sysinfo['local_ip']}",
        ]
        right_items = [
            f"CPU: {self.sysinfo['cpu_usage']}%  |  RAM: {self.sysinfo['ram_usage']}% ({self.sysinfo.get('total_ram', 'N/A')})",
            f"Disk: {self.sysinfo['disk_usage']}%  |  Cores: {self.sysinfo.get('logical_processors', 'N/A')}",
            f"Uptime: {self.sysinfo.get('uptime', 'N/A')}",
            f"Battery: {self.sysinfo.get('battery', 'N/A')}",
        ]

        for text in left_items:
            ctk.CTkLabel(left_col, text=text, font=ctk.CTkFont(size=11), text_color=OCP_TEXT_DIM, anchor="w").pack(anchor="w", pady=1)
        for text in right_items:
            ctk.CTkLabel(right_col, text=text, font=ctk.CTkFont(size=11), text_color=OCP_TEXT_DIM, anchor="w").pack(anchor="w", pady=1)

        if self.screenshot_img is not None:
            ss_card = ctk.CTkFrame(scroll_frame, fg_color=OCP_CARD_BG, corner_radius=8)
            ss_card.pack(fill="x", padx=20, pady=(8, 8))

            ss_header = ctk.CTkFrame(ss_card, fg_color="transparent")
            ss_header.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(
                ss_header, text="Screenshot",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=OCP_CYAN,
            ).pack(side="left")

            thumb = image_to_thumbnail(self.screenshot_img, max_height=130)
            self._tk_thumb = ImageTk.PhotoImage(thumb)

            thumb_container = ctk.CTkFrame(ss_card, fg_color=OCP_INPUT_BG, corner_radius=6)
            thumb_container.pack(padx=15, pady=(0, 5))
            self.thumb_label = ctk.CTkLabel(thumb_container, image=self._tk_thumb, text="")
            self.thumb_label.pack(padx=5, pady=5)

            self.remove_ss_var = ctk.BooleanVar(value=False)
            self.remove_ss_check = ctk.CTkCheckBox(
                ss_card,
                text="Remove screenshot (sensitive info)",
                variable=self.remove_ss_var,
                command=self._toggle_screenshot,
                font=ctk.CTkFont(size=11),
                text_color=OCP_TEXT_DIM,
                fg_color=OCP_BLUE,
                hover_color=OCP_NAVY,
                border_color=OCP_SILVER,
            )
            self.remove_ss_check.pack(anchor="w", padx=15, pady=(0, 10))

        form_card = ctk.CTkFrame(scroll_frame, fg_color=OCP_CARD_BG, corner_radius=8)
        form_card.pack(fill="x", padx=20, pady=(8, 8))

        ctk.CTkLabel(
            form_card, text="Subject",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OCP_TEXT,
        ).pack(anchor="w", padx=15, pady=(12, 4))

        default_subject = f"Support Request from {self.sysinfo['username']} on {self.sysinfo['hostname']}"
        self.subject_entry = ctk.CTkEntry(
            form_card, width=550, height=36,
            placeholder_text="Subject line...",
            fg_color=OCP_INPUT_BG,
            border_color=OCP_BLUE,
            text_color=OCP_TEXT,
            placeholder_text_color=OCP_TEXT_DIM,
        )
        self.subject_entry.insert(0, default_subject)
        self.subject_entry.pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(
            form_card, text="Description",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OCP_TEXT,
        ).pack(anchor="w", padx=15, pady=(8, 4))

        self.desc_text = ctk.CTkTextbox(
            form_card, width=550, height=120,
            fg_color=OCP_INPUT_BG,
            border_color=OCP_BLUE,
            text_color=OCP_TEXT,
            border_width=1,
        )
        self.desc_text.pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(
            form_card, text="Priority",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=OCP_TEXT,
        ).pack(anchor="w", padx=15, pady=(8, 4))

        self.priority_var = ctk.StringVar(value="Medium")
        priority_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        priority_frame.pack(fill="x", padx=15, pady=(0, 12))

        priority_colors = {"Low": OCP_CYAN, "Medium": OCP_BLUE, "High": "#E74C3C"}
        for val in ("Low", "Medium", "High"):
            ctk.CTkRadioButton(
                priority_frame, text=val,
                variable=self.priority_var, value=val,
                font=ctk.CTkFont(size=12),
                text_color=OCP_TEXT,
                fg_color=priority_colors[val],
                border_color=OCP_SILVER,
                hover_color=priority_colors[val],
            ).pack(side="left", padx=(0, 25))

        footer = ctk.CTkFrame(self, fg_color=OCP_DARK_BG, height=65)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            footer_inner, text="", font=ctk.CTkFont(size=12),
            text_color=OCP_TEXT_DIM,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.submit_btn = ctk.CTkButton(
            footer_inner, text="Submit Request", width=200, height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=OCP_BLUE,
            hover_color=OCP_NAVY,
            text_color="white",
            corner_radius=6,
            command=self._on_submit,
        )
        self.submit_btn.pack(side="right")

    def _toggle_screenshot(self):
        if self.remove_ss_var.get():
            self.thumb_label.configure(image=None, text="[Screenshot removed]")
            self.screenshot_removed = True
        else:
            if self._tk_thumb:
                self.thumb_label.configure(image=self._tk_thumb, text="")
            self.screenshot_removed = False

    def _on_submit(self):
        subject = self.subject_entry.get().strip()
        description = self.desc_text.get("1.0", "end").strip()

        if not subject:
            self.status_label.configure(text="Subject is required.", text_color="#E74C3C")
            return
        if not description:
            self.status_label.configure(text="Description is required.", text_color="#E74C3C")
            return

        self.submit_btn.configure(state="disabled")
        self.status_label.configure(text="Sending...", text_color=OCP_CYAN)

        data = {
            "subject": subject,
            "description": description,
            "priority": self.priority_var.get(),
            "name": self.sysinfo.get("username", "User"),
            "email": self.sysinfo.get("user_email", ""),
            **self.sysinfo,
        }

        ss_buf = None
        if not self.screenshot_removed and self.screenshot_buf is not None:
            ss_buf = io.BytesIO(self.screenshot_buf.getvalue())

        thread = threading.Thread(target=self._submit_thread, args=(data, ss_buf), daemon=True)
        thread.start()

    def _submit_thread(self, data, ss_buf):
        success, message = send_ticket(data, ss_buf)
        self.after(0, self._on_submit_result, success, message)

    def _on_submit_result(self, success, message):
        if success:
            self.status_label.configure(text=message, text_color="#2ECC71")
            self.after(2000, self._on_close)
        else:
            self.status_label.configure(text=message, text_color="#E74C3C")
            self.submit_btn.configure(state="normal")

    def _on_close(self):
        self.destroy()
