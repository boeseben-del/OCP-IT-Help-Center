"""
OCP IT Helpdesk - Windows Service
===================================
Runs as a Windows Service (LocalSystem account) and launches the
OCP IT Helpdesk tray application in the active user's desktop session.

The service:
  - Auto-starts on boot
  - Monitors the tray app process and restarts it if it crashes
  - Can be managed via services.msc, sc.exe, or PDQ Connect
  - Launches the GUI in the logged-in user's session (Session 1+)

Install/Uninstall:
  OCP_IT_Helpdesk_Service.exe install
  OCP_IT_Helpdesk_Service.exe remove

Start/Stop:
  OCP_IT_Helpdesk_Service.exe start
  OCP_IT_Helpdesk_Service.exe stop

Debug (foreground):
  OCP_IT_Helpdesk_Service.exe debug
"""

import os
import sys
import time
import subprocess
import logging
import logging.handlers

try:
    import win32serviceutil
    import win32service
    import win32event
    import win32ts
    import win32security
    import win32process
    import win32profile
    import win32con
    import win32api
    import pywintypes
    import servicemanager
except ImportError:
    pass


SERVICE_NAME = "OCPITHelpdesk"
SERVICE_DISPLAY = "OCP IT Helpdesk"
SERVICE_DESC = "OCP IT Helpdesk - Background desktop agent for IT support tickets. Launches the tray application in the active user session."

RESTART_DELAY = 5
POLL_INTERVAL = 3
SESSION_WAIT = 10


def _get_install_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _setup_logging():
    log_dir = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "OCP_IT_Helpdesk")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "service.log")

    logger = logging.getLogger("OCPService")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1024 * 1024, backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


class OCPHelpdeskService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY
    _svc_description_ = SERVICE_DESC

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        self.child_process = None
        self.log = _setup_logging()

    def SvcStop(self):
        self.log.info("Service stop requested.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        self._kill_child()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.log.info("Service started.")
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self._main_loop()

    def _main_loop(self):
        install_dir = _get_install_dir()
        app_exe = os.path.join(install_dir, "OCP_IT_Helpdesk.exe")

        if not os.path.exists(app_exe):
            app_exe = os.path.join(install_dir, "main.py")
            if not os.path.exists(app_exe):
                self.log.error("Cannot find OCP_IT_Helpdesk.exe or main.py in %s", install_dir)
                return

        self.log.info("App path: %s", app_exe)

        while self.is_alive:
            session_id = self._get_active_session()
            if session_id is None:
                self.log.info("No active user session. Waiting %ds...", SESSION_WAIT)
                if self._wait(SESSION_WAIT):
                    break
                continue

            if self.child_process and self._is_process_alive():
                if self._wait(POLL_INTERVAL):
                    break
                continue

            self.log.info("Launching tray app in session %d", session_id)
            success = self._launch_in_session(app_exe, session_id)
            if not success:
                self.log.warning("Failed to launch. Retrying in %ds...", RESTART_DELAY)
                if self._wait(RESTART_DELAY):
                    break
                continue

            if self._wait(POLL_INTERVAL):
                break

        self._kill_child()
        self.log.info("Service stopped.")

    def _get_active_session(self):
        try:
            session_id = win32ts.WTSGetActiveConsoleSessionId()
            if session_id == 0xFFFFFFFF:
                return None
            return session_id
        except Exception as e:
            self.log.error("Failed to get active session: %s", e)
            return None

    def _launch_in_session(self, app_path, session_id):
        try:
            hToken = win32ts.WTSQueryUserToken(session_id)

            hTokenDup = win32security.DuplicateTokenEx(
                hToken,
                win32security.SecurityImpersonation,
                win32con.MAXIMUM_ALLOWED,
                win32security.TokenPrimary,
                None,
            )

            env = win32profile.CreateEnvironmentBlock(hTokenDup, False)

            si = win32process.STARTUPINFO()
            si.dwFlags = win32process.STARTF_USESHOWWINDOW
            si.wShowWindow = win32con.SW_HIDE
            si.lpDesktop = "winsta0\\default"

            install_dir = os.path.dirname(app_path)

            if app_path.endswith(".py"):
                cmd_line = f'pythonw.exe "{app_path}"'
            else:
                cmd_line = f'"{app_path}"'

            hProcess, hThread, dwPid, dwTid = win32process.CreateProcessAsUser(
                hTokenDup,
                None,
                cmd_line,
                None,
                None,
                False,
                win32con.CREATE_NO_WINDOW | win32con.NORMAL_PRIORITY_CLASS,
                env,
                install_dir,
                si,
            )

            self.child_process = hProcess
            self.child_pid = dwPid
            self.log.info("Launched tray app (PID %d) in session %d", dwPid, session_id)

            win32api.CloseHandle(hThread)
            win32api.CloseHandle(hToken)
            win32api.CloseHandle(hTokenDup)

            return True

        except pywintypes.error as e:
            self.log.error("CreateProcessAsUser failed: %s", e)
            return False
        except Exception as e:
            self.log.error("Unexpected error launching process: %s", e)
            return False

    def _is_process_alive(self):
        if not self.child_process:
            return False
        try:
            result = win32event.WaitForSingleObject(self.child_process, 0)
            return result == win32event.WAIT_TIMEOUT
        except Exception:
            return False

    def _kill_child(self):
        if self.child_process:
            try:
                if self._is_process_alive():
                    win32api.TerminateProcess(self.child_process, 0)
                    self.log.info("Terminated child process (PID %d)", self.child_pid)
                win32api.CloseHandle(self.child_process)
            except Exception as e:
                self.log.warning("Error terminating child: %s", e)
            self.child_process = None

    def _wait(self, seconds):
        result = win32event.WaitForSingleObject(self.hWaitStop, int(seconds * 1000))
        return result == win32event.WAIT_OBJECT_0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OCPHelpdeskService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(OCPHelpdeskService)
