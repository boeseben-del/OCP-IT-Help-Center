"""System information gathering utilities."""

import socket
import platform
import os
import uuid
import psutil
import requests as req_lib


def get_hostname():
    return socket.gethostname()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def get_public_ip():
    try:
        response = req_lib.get("https://api.ipify.org", timeout=3)
        return response.text
    except Exception:
        return "N/A"


def get_mac_address():
    try:
        mac = uuid.getnode()
        mac_str = ':'.join(f'{(mac >> i) & 0xFF:02x}' for i in range(40, -1, -8))
        return mac_str.upper()
    except Exception:
        return "N/A"


def get_current_user():
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME", os.environ.get("USER", "Unknown"))


def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)


def get_ram_usage():
    return psutil.virtual_memory().percent


def get_disk_usage():
    try:
        disk = psutil.disk_usage('/')
        if platform.system() == "Windows":
            disk = psutil.disk_usage('C:\\')
        return disk.percent
    except Exception:
        return 0.0


def get_os_info():
    system = platform.system()
    if system == "Windows":
        try:
            version_str = platform.version()
            build = int(version_str.split('.')[-1])
            if build >= 22000:
                return "Windows 11"
            else:
                return f"Windows {platform.release()}"
        except (ValueError, IndexError, AttributeError):
            return f"Windows {platform.release()}"
    return f"{system} {platform.release()}"


def get_active_window_title():
    """Get the title of the currently active window (Windows-specific)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value if buf.value else "Unknown"
    except Exception:
        try:
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=2
            )
            return result.stdout.strip() if result.stdout.strip() else "Unknown"
        except Exception:
            return "Unknown"


def get_user_email():
    """Attempt to get the logged-in user's email from Windows."""
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Office\\16.0\\Common\\Identity' -Name 'ADUserName' -ErrorAction SilentlyContinue).ADUserName"],
            capture_output=True, text=True, timeout=5
        )
        email = result.stdout.strip()
        if email and "@" in email:
            return email
    except Exception:
        pass

    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)"],
            capture_output=True, text=True, timeout=5
        )
        identity = result.stdout.strip()
        if identity:
            return identity
    except Exception:
        pass

    return ""


def gather_all():
    """Gather all system information into a dictionary."""
    return {
        "hostname": get_hostname(),
        "local_ip": get_local_ip(),
        "public_ip": get_public_ip(),
        "mac_address": get_mac_address(),
        "username": get_current_user(),
        "user_email": get_user_email(),
        "cpu_usage": get_cpu_usage(),
        "ram_usage": get_ram_usage(),
        "disk_usage": get_disk_usage(),
        "os_info": get_os_info(),
        "active_window": get_active_window_title(),
    }
