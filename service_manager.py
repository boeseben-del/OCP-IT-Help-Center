"""
OCP IT Helpdesk - Service Manager
====================================
Helper script to install, uninstall, start, stop, and check the
OCP IT Helpdesk Windows Service.

Usage:
    service_manager.py install    - Install the service
    service_manager.py uninstall  - Remove the service
    service_manager.py start      - Start the service
    service_manager.py stop       - Stop the service
    service_manager.py restart    - Stop then start the service
    service_manager.py status     - Check service status

Must be run as Administrator.
"""

import sys
import os
import subprocess
import ctypes


SERVICE_NAME = "OCPITHelpdesk"
SERVICE_DISPLAY = "OCP IT Helpdesk"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_service_exe():
    base = os.path.dirname(os.path.abspath(__file__))
    exe = os.path.join(base, "OCP_IT_Helpdesk_Service.exe")
    if os.path.exists(exe):
        return exe
    py = os.path.join(base, "src", "it_agent", "service.py")
    if os.path.exists(py):
        return py
    return None


def run_sc(*args):
    cmd = ["sc.exe"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def install_service():
    exe = get_service_exe()
    if not exe:
        print("ERROR: Cannot find service executable.")
        return False

    if exe.endswith(".py"):
        cmd = [sys.executable, exe, "install"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(["sc.exe", "config", SERVICE_NAME, "start=", "auto"], capture_output=True)
            subprocess.run(
                ["sc.exe", "failure", SERVICE_NAME,
                 "reset=", "86400",
                 "actions=", "restart/5000/restart/10000/restart/30000"],
                capture_output=True,
            )
            print(f"Service '{SERVICE_DISPLAY}' installed successfully.")
            print("  - Set to auto-start on boot")
            print("  - Configured automatic restart on failure")
            return True
        else:
            print(f"ERROR: {result.stdout} {result.stderr}")
            return False
    else:
        code, out, err = run_sc(
            "create", SERVICE_NAME,
            f"binPath={exe}",
            f"DisplayName={SERVICE_DISPLAY}",
            "start=auto",
        )
        if code == 0:
            run_sc("description", SERVICE_NAME,
                   "OCP IT Helpdesk - Background desktop agent for IT support tickets.")
            run_sc("failure", SERVICE_NAME,
                   "reset=86400", "actions=restart/5000/restart/10000/restart/30000")
            print(f"Service '{SERVICE_DISPLAY}' installed successfully.")
            print("  - Set to auto-start on boot")
            print("  - Configured automatic restart on failure")
            return True
        else:
            print(f"ERROR: {out} {err}")
            return False


def uninstall_service():
    stop_service()
    exe = get_service_exe()
    if exe and exe.endswith(".py"):
        result = subprocess.run([sys.executable, exe, "remove"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Service '{SERVICE_DISPLAY}' removed.")
            return True
        else:
            print(f"ERROR: {result.stdout} {result.stderr}")
            return False
    else:
        code, out, err = run_sc("delete", SERVICE_NAME)
        if code == 0:
            print(f"Service '{SERVICE_DISPLAY}' removed.")
            return True
        else:
            print(f"ERROR: {out} {err}")
            return False


def start_service():
    code, out, err = run_sc("start", SERVICE_NAME)
    if code == 0:
        print(f"Service '{SERVICE_DISPLAY}' started.")
        return True
    else:
        print(f"ERROR starting service: {out} {err}")
        return False


def stop_service():
    code, out, err = run_sc("stop", SERVICE_NAME)
    if code == 0:
        print(f"Service '{SERVICE_DISPLAY}' stopped.")
        return True
    else:
        if "1062" in out or "1062" in err:
            print(f"Service '{SERVICE_DISPLAY}' is not running.")
            return True
        print(f"ERROR stopping service: {out} {err}")
        return False


def restart_service():
    stop_service()
    import time
    time.sleep(2)
    return start_service()


def status_service():
    code, out, err = run_sc("query", SERVICE_NAME)
    if code == 0:
        print(out)
    else:
        print(f"Service '{SERVICE_DISPLAY}' is not installed.")


def main():
    if len(sys.argv) < 2:
        print("OCP IT Helpdesk Service Manager")
        print("================================")
        print("Usage: service_manager.py <command>")
        print()
        print("Commands:")
        print("  install    - Install the service (auto-start on boot)")
        print("  uninstall  - Remove the service")
        print("  start      - Start the service")
        print("  stop       - Stop the service")
        print("  restart    - Restart the service")
        print("  status     - Check service status")
        print()
        print("Must be run as Administrator.")
        return

    if not is_admin():
        print("ERROR: This script must be run as Administrator.")
        print("Right-click Command Prompt -> Run as administrator")
        sys.exit(1)

    command = sys.argv[1].lower()

    actions = {
        "install": install_service,
        "uninstall": uninstall_service,
        "remove": uninstall_service,
        "start": start_service,
        "stop": stop_service,
        "restart": restart_service,
        "status": status_service,
    }

    if command in actions:
        actions[command]()
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: install, uninstall, start, stop, restart, status")


if __name__ == "__main__":
    main()
