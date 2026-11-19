import os
import sys
import threading
import time
import numpy as np
import sounddevice as sd
import requests
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Sound Detector Script
# v1.0.2

def get_env_path():
    """
    Resolve the external .env file beside the script or executable.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / '.env'
    return Path(__file__).resolve().parent / '.env'

env_path = get_env_path()
load_dotenv(dotenv_path=env_path)

FIRST_DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL")
SECOND_DISCORD_WEBHOOK_URL = os.getenv("VOLUME_REPORT_URL")
FIRST_USER_ID = os.getenv("FIRST_USER_ID")

PING_COOLDOWN = 5  # seconds
NOTIF_AUTO_DELETE_DURATION = 60  # seconds
VOLUME_AUTO_DELETE_DURATION = 20  # seconds

HERTZ_RATE = 44100  # later customizable by user during an input session
NOISE_THRESHOLD = 0.1  # later customizable by user during an input session
NOISE_FLOOR = 0.01  # minimum volume level to consider
VOLUME_REPORT_COOLDOWN = 2.0

last_volume_report_time = 0
current_nyc_tz = ZoneInfo("America/New_York")
active_messages = []
messages_lock = threading.Lock()

while True:
    try:
        NOISE_THRESHOLD = float(input(f"What noise threshold would you like to consider? (default {NOISE_THRESHOLD}) "))
        HERTZ_RATE = int(input(f"What Hz rate would you like to consider? (default {HERTZ_RATE}Hz) "))
        print()
        break
    except ValueError:
        print("[ERROR] Not a valid number to consider.\n")
        NOISE_THRESHOLD = 0.1
        HERTZ_RATE = 44100
        

def date_report():
    """
    Return the current date and time in the New York timezone.

    Returns:
        str: Current date and time formatted as
            [DD-MM-YYYY HH:MM:SSAM/PM].
    """
    now = datetime.now(current_nyc_tz)
    return now.strftime("[%d-%m-%Y %I:%M:%S%p]")


def time_report():
    """
    Return the current time in the New York timezone.

    Returns:
        str: Current time formatted as [HH:MM:SS AM/PM].
    """
    now = datetime.now(current_nyc_tz)
    return now.strftime("[%I:%M:%S %p]")


def find_audio_device():
    """
    Find a suitable audio input device for detecting system audio.

    The function first searches for devices commonly associated with
    system-audio capture, such as virtual cables and stereo-mix devices.
    If none are found, it falls back to the first available input device.

    Returns:
        tuple: A tuple containing the selected device's index and
            maximum number of input channels.

    Raises:
        SystemExit: If audio devices cannot be queried or no valid
            input device is available.
    """
    try:
        devices = sd.query_devices()
    except Exception:
        print("[ERROR] Cannot query audio devices")
        sys.exit(1)

    for i, dev in enumerate(devices):
        name = dev["name"].lower()
        if dev["max_input_channels"] > 0 and (
            "cable" in name
            or "stereo mix" in name
            or "what u hear" in name
            or "loopback" in name
            or "blackhole" in name
        ):
            return i, dev["max_input_channels"]

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i, dev["max_input_channels"]

    print("[ERROR] No valid audio input device(s) found")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0


def auto_delete_msg(webhook_url: str, msg_id: str, delay: int):
    """
    Delete a Discord webhook message after a specified delay.

    The message is tracked in active_messages while waiting for
    deletion. Regardless of whether deletion succeeds, the message is
    removed from the tracking list afterward.

    Args:
        webhook_url (str): URL of the webhook that sent the message.
        msg_id (str): ID of the Discord message to delete.
        delay (int): Number of seconds to wait before deleting the
            message.
    """
    if not webhook_url or not msg_id:
        return

    with messages_lock:
        active_messages.append((webhook_url, msg_id))

    time.sleep(delay)

    try:
        requests.delete(f"{webhook_url}/messages/{msg_id}", timeout=5)
    except requests.RequestException:
        pass
    finally:
        with messages_lock:
            if (webhook_url, msg_id) in active_messages:
                active_messages.remove((webhook_url, msg_id))


def send_discord_ping(volume: float, delete_time: int):
    """
    Send a Discord notification when a sound exceeds the threshold.

    The notification mentions the configured user and includes the
    supplied sound-detection details. Successfully sent messages are
    automatically scheduled for deletion.

    Args:
        volume (float): Current normalized audio volume level.
        delete_time (int): Time it takes for a message to auto-delete.
    """
    if not FIRST_DISCORD_WEBHOOK_URL:
        return
    
    over_pct = round(((volume - NOISE_THRESHOLD) / NOISE_THRESHOLD) * 100)
    
    embed = {
        "title": "Audio Threshold Exceeded",
        "color": 0x5865F2,  # Blurple
        "fields": [
            {
                "name": "Metric",
                "value": "Live Volume\nThreshold",
                "inline": True,
            },
            {
                "name": "Value",
                "value": f"**{volume:.3f}\n{NOISE_THRESHOLD}**",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"**{over_pct}%** over Threshold\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {HERTZ_RATE}Hz - Cooldown: {PING_COOLDOWN}s"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {
        "content": f"**Sound Detected - <@{FIRST_USER_ID}>**",
        "embeds": [embed],
        "allowed_mentions": {"parse": ["users"]},
    }

    response = requests.post(
        f"{FIRST_DISCORD_WEBHOOK_URL}?wait=true", json=data
    )

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=auto_delete_msg,
            args=(
                FIRST_DISCORD_WEBHOOK_URL,
                msg_id,
                NOTIF_AUTO_DELETE_DURATION,
            ),
        ).start()


def send_volume_report(volume: float):
    """
    Send the current live volume level to a Discord webhook.

    The report includes the configured user's mention and the amount of
    time remaining before Discord automatically removes the message.

    Args:
        volume (float): Current normalized audio volume level.
    """
    if not SECOND_DISCORD_WEBHOOK_URL:
        return

    delete_time = int(time.time()) + VOLUME_AUTO_DELETE_DURATION
    status = "Loud" if volume > NOISE_THRESHOLD else "Normal"

    embed = {
        "title": f"**Live Volume Report**",
        "description": f"<@{FIRST_USER_ID}>",
        "color": 0x57F287,  # Bright green
        "fields": [
            {"name": "Metric", "value": "Volume\nFloor", "inline": True},
            {
                "name": "Level",
                "value": f"**{volume:.3f}**\n{NOISE_FLOOR}",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"{status}\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {HERTZ_RATE}Hz"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {
        "embeds": [embed],
        "allowed_mentions": {"parse": ["users"]},
    }

    response = requests.post(
        f"{SECOND_DISCORD_WEBHOOK_URL}?wait=true", json=data
    )

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=auto_delete_msg,
            args=(
                SECOND_DISCORD_WEBHOOK_URL,
                msg_id,
                VOLUME_AUTO_DELETE_DURATION,
            ),
        ).start()


def audio_callback(
    indata: np.ndarray,
    frames: int,
    time_info: sd.TimeInfo,
    status: sd.Status,
):
    """
    Process incoming audio and report significant volume levels.

    The callback calculates the normalized volume of the incoming audio
    data. Volume levels above the noise floor are printed and reported
    to Discord at the configured interval. Levels above the noise
    threshold additionally trigger a Discord sound-detection
    notification, subject to the ping cooldown.

    Args:
        indata (np.ndarray): Audio samples received from the input
            stream.
        frames (int): Number of audio frames contained in indata.
        time_info (sd.TimeInfo): Timing information provided by the
            audio stream.
        status (sd.Status): Current status information for the audio
            stream.
    """
    global last_ping_time, last_volume_report_time
    current_time = time.time()

    volume_norm = float(np.sqrt(np.mean(indata**2)))

    if volume_norm > NOISE_FLOOR:
        print(f"Volume: {volume_norm:.3f}")

        if current_time - last_volume_report_time > VOLUME_REPORT_COOLDOWN:
            send_volume_report(volume_norm)
            last_volume_report_time = current_time

    if volume_norm > NOISE_THRESHOLD:
        if current_time - last_ping_time > PING_COOLDOWN:
            print(f"*** Noise Detected! Volume Level: {volume_norm:.3f} ***")
            delete_time = int(current_time) + NOTIF_AUTO_DELETE_DURATION
            send_discord_ping(volume_norm, delete_time)
            last_ping_time = current_time

print(f"Listening on device index {DEVICE_INDEX} "
      f"(Channels: {INPUT_CHANNELS} | Sample Rate: {HERTZ_RATE}Hz)")
print(f"Noise Threshold: {NOISE_THRESHOLD} | Ping Cooldown: {PING_COOLDOWN}s")

try:
    with sd.InputStream(
        device=DEVICE_INDEX,
        callback=audio_callback,
        channels=INPUT_CHANNELS,
        samplerate=HERTZ_RATE,  # 44100 Hz is standard for any fast audio
    ):
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
