"""HappyFox API integration for ticket submission."""

import requests
import json
import os

HAPPYFOX_ENDPOINT = os.environ.get(
    "HAPPYFOX_ENDPOINT",
    "https://example.happyfox.com/api/1.1/json/tickets/"
)
HAPPYFOX_API_KEY = os.environ.get("HAPPYFOX_API_KEY", "")
HAPPYFOX_AUTH_CODE = os.environ.get("HAPPYFOX_AUTH_CODE", "")


def send_ticket(data, screenshot_bytes=None):
    """Submit an IT support ticket to HappyFox.
    
    The ticket is created on behalf of the currently logged-in user.
    The user's name and email (gathered from system info) are passed
    as the contact for the ticket, so HappyFox associates it with
    that user.
    
    Args:
        data: dict with keys: subject, description, priority, name, email,
              hostname, local_ip, public_ip, mac_address, cpu_usage,
              ram_usage, disk_usage, os_info, active_window
        screenshot_bytes: BytesIO buffer with PNG screenshot, or None
    
    Returns:
        (success: bool, message: str)
    """
    priority_map = {"Low": 1, "Medium": 2, "High": 3}

    user_name = data.get("name", data.get("username", "User"))
    user_email = data.get("email", "")

    if not user_email or "@" not in user_email:
        user_email = os.environ.get("HAPPYFOX_DEFAULT_EMAIL", "")
    if not user_email:
        return False, "Could not determine your email address. Please contact IT support directly."

    body = {
        "subject": data.get("subject", "OCP IT Help Center Request"),
        "text": _build_description(data),
        "priority": priority_map.get(data.get("priority", "Medium"), 2),
        "name": user_name,
        "email": user_email,
        "category": 1,
    }

    files = None
    if screenshot_bytes is not None:
        screenshot_bytes.seek(0)
        files = [("attachments", ("screenshot.png", screenshot_bytes, "image/png"))]

    try:
        response = requests.post(
            HAPPYFOX_ENDPOINT,
            auth=(HAPPYFOX_API_KEY, HAPPYFOX_AUTH_CODE),
            data=body,
            files=files,
            timeout=30,
        )

        if response.status_code in (200, 201):
            return True, "Ticket submitted successfully!"
        else:
            return False, f"Server returned status {response.status_code}: {response.text[:200]}"
    except requests.exceptions.ConnectionError:
        return False, "Connection error. Check your network and HappyFox endpoint URL."
    except requests.exceptions.Timeout:
        return False, "Request timed out. Please try again."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def _build_description(data):
    """Build a formatted description string with system info appended."""
    user_desc = data.get("description", "No description provided.")

    system_block = (
        f"\n\n--- System Information ---\n"
        f"Hostname: {data.get('hostname', 'N/A')}\n"
        f"Username: {data.get('username', 'N/A')}\n"
        f"Local IP: {data.get('local_ip', 'N/A')}\n"
        f"Public IP: {data.get('public_ip', 'N/A')}\n"
        f"MAC Address: {data.get('mac_address', 'N/A')}\n"
        f"OS: {data.get('os_info', 'N/A')}\n"
        f"CPU Usage: {data.get('cpu_usage', 'N/A')}%\n"
        f"RAM Usage: {data.get('ram_usage', 'N/A')}%\n"
        f"Disk Usage: {data.get('disk_usage', 'N/A')}%\n"
        f"Active Window: {data.get('active_window', 'N/A')}\n"
    )

    return user_desc + system_block
