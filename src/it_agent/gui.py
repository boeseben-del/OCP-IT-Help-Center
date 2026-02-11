"""CustomTkinter GUI for OCP IT Helpdesk."""

import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime
from src.it_agent.screenshot import image_to_thumbnail
from src.it_agent.api import send_ticket
import threading
import io


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TicketWindow(ctk.CTkToplevel):
    """The OCP IT Helpdesk popup window."""

    def __init__(self, master, sysinfo, screenshot_buf, screenshot_img):
        super().__init__(master)
        self.title("OCP IT Helpdesk")
        self.geometry("600x780")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.sysinfo = sysinfo
        self.screenshot_buf = screenshot_buf
        self.screenshot_img = screenshot_img
        self.screenshot_removed = False
        self._tk_thumb = None

        self._build_ui()
        self.after(100, lambda: self.focus_force())

    def _build_ui(self):
        pad = {"padx": 20, "pady": (5, 5)}

        header = ctk.CTkLabel(
            self, text="OCP IT Helpdesk",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        header.pack(pady=(20, 5))

        sub = ctk.CTkLabel(
            self,
            text=f"{self.sysinfo['hostname']}  |  {self.sysinfo['username']}  |  {self.sysinfo['os_info']}",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        sub.pack(pady=(0, 10))

        sysframe = ctk.CTkFrame(self, fg_color="transparent")
        sysframe.pack(fill="x", **pad)

        row1 = ctk.CTkFrame(sysframe, fg_color="transparent")
        row1.pack(fill="x")
        info_text_1 = (
            f"CPU: {self.sysinfo['cpu_usage']}%   "
            f"RAM: {self.sysinfo['ram_usage']}% ({self.sysinfo.get('total_ram', 'N/A')})   "
            f"Disk: {self.sysinfo['disk_usage']}%"
        )
        ctk.CTkLabel(row1, text=info_text_1, font=ctk.CTkFont(size=11), text_color="gray").pack()

        row2 = ctk.CTkFrame(sysframe, fg_color="transparent")
        row2.pack(fill="x")
        info_text_2 = (
            f"IP: {self.sysinfo['local_ip']}   "
            f"MAC: {self.sysinfo['mac_address']}   "
            f"Uptime: {self.sysinfo.get('uptime', 'N/A')}"
        )
        ctk.CTkLabel(row2, text=info_text_2, font=ctk.CTkFont(size=11), text_color="gray").pack()

        if self.screenshot_img is not None:
            self.screenshot_frame = ctk.CTkFrame(self)
            self.screenshot_frame.pack(fill="x", **pad)

            ctk.CTkLabel(
                self.screenshot_frame, text="Screenshot Preview:",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=10, pady=(5, 2))

            thumb = image_to_thumbnail(self.screenshot_img, max_height=150)
            self._tk_thumb = ImageTk.PhotoImage(thumb)
            self.thumb_label = ctk.CTkLabel(self.screenshot_frame, image=self._tk_thumb, text="")
            self.thumb_label.pack(padx=10, pady=(0, 5))

            self.remove_ss_var = ctk.BooleanVar(value=False)
            self.remove_ss_check = ctk.CTkCheckBox(
                self.screenshot_frame,
                text="Remove screenshot (sensitive info)",
                variable=self.remove_ss_var,
                command=self._toggle_screenshot,
                font=ctk.CTkFont(size=11),
            )
            self.remove_ss_check.pack(anchor="w", padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text="Subject:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20, pady=(8, 2))
        default_subject = f"Support Request from {self.sysinfo['username']} on {self.sysinfo['hostname']}"
        self.subject_entry = ctk.CTkEntry(self, width=540, placeholder_text="Subject line...")
        self.subject_entry.insert(0, default_subject)
        self.subject_entry.pack(**pad)

        ctk.CTkLabel(self, text="Description:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20, pady=(8, 2))
        self.desc_text = ctk.CTkTextbox(self, width=540, height=140)
        self.desc_text.insert("1.0", "")
        self.desc_text.pack(**pad)

        ctk.CTkLabel(self, text="Priority:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20, pady=(8, 2))
        self.priority_var = ctk.StringVar(value="Medium")
        priority_frame = ctk.CTkFrame(self, fg_color="transparent")
        priority_frame.pack(fill="x", padx=20, pady=(0, 5))
        for val in ("Low", "Medium", "High"):
            ctk.CTkRadioButton(
                priority_frame, text=val, variable=self.priority_var, value=val,
            ).pack(side="left", padx=(0, 20))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(15, 20))

        self.status_label = ctk.CTkLabel(
            footer, text="", font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.submit_btn = ctk.CTkButton(
            footer, text="Submit Request", width=200, height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1a73e8",
            hover_color="#1557b0",
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
            self.status_label.configure(text="Subject is required.", text_color="red")
            return
        if not description:
            self.status_label.configure(text="Description is required.", text_color="red")
            return

        self.submit_btn.configure(state="disabled")
        self.status_label.configure(text="Sending...", text_color="orange")

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
            self.status_label.configure(text=message, text_color="green")
            self.after(2000, self._on_close)
        else:
            self.status_label.configure(text=message, text_color="red")
            self.submit_btn.configure(state="normal")

    def _on_close(self):
        self.destroy()
