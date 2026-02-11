# IT Support Agent

## Overview
A Windows Desktop Agent built in Python that captures screenshots and creates IT support tickets via a global hotkey (F8). The app runs silently in the system tray and pops up a modern ticket form when triggered.

**Target Platform:** Windows (designed for PyInstaller packaging)  
**Development Environment:** Replit (Linux) - GUI runs in console/VNC mode for testing

## Project Architecture

### Directory Structure
```
main.py                     # Entry point - ITAgentApp class
src/
  it_agent/
    __init__.py
    sysinfo.py              # System info gathering (hostname, IP, CPU, RAM, etc.)
    screenshot.py           # Screenshot capture and thumbnail utilities
    gui.py                  # CustomTkinter ticket form UI (TicketWindow)
    tray.py                 # System tray icon and F8 hotkey listener (TrayManager)
    api.py                  # HappyFox API integration for ticket submission
```

### Key Libraries
- **customtkinter** - Modern themed Tkinter GUI (DarkBlue theme)
- **pystray** - System tray icon management
- **keyboard** - Global hotkey listener (F8)
- **pyautogui / PIL** - Screenshot capture
- **requests** - HTTP API calls to HappyFox
- **psutil** - CPU/RAM usage monitoring

### Flow
1. App starts silently → minimizes to system tray
2. User presses F8 → screenshot captured immediately → ticket form opens
3. Form auto-fills system info, shows screenshot thumbnail
4. User fills description, sets priority, submits
5. Ticket sent to HappyFox API with screenshot attachment

### API Configuration
- HappyFox endpoint and credentials are placeholder values in `src/it_agent/api.py`
- Must be updated before production use

### Building for Windows
```
pyinstaller --noconsole --onefile --name "IT_Agent" main.py
```

## Recent Changes
- 2026-02-11: Initial project creation with full architecture

## User Preferences
- Modern dark theme UI (DarkBlue)
- Professional, clean layout
- Windows-focused deployment
