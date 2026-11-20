import os
import sys
import threading
import time
import numpy as np
import sounddevice as sd
import requests
import json
from typing import Any
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import InvalidOperation
from dotenv import load_dotenv

# Sound Detector Script
# v1.2.1

env_template = (
    "# Discord Webhook URL for loud sound alerts (required)\n"
    'NOTIFY_USER_URL=\n\n'
    "# Discord Webhook URL for live volume reports (optional)\n"
    'VOLUME_REPORT_URL=\n\n'
    "# Your Discord User ID (numbers only, required)\n"
    'FIRST_USER_ID=\n'
)


def get_env_path():
    """
    Resolve the external .env file beside the script or executable.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / '.env'
    return Path(__file__).resolve().parent / '.env'

env_path = get_env_path()
    
if not env_path.exists():
    print("[WARNING] No .env file was created in the user directory")
    print("A .env file is required to recieve Discord pings and live volume tracking.")
    create_env = input("Do you want to create a new .env file "
                       "with all required details inside? (Y/N) ").upper().strip()
    
    if create_env == "Y":
        print("237 INFO: Creating file for user because .env is non-existent")

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_template)
            time.sleep(0.5)
            print("288 INFO: Created local .env file in user workspace directory")
            print("[INSTRUCTIONS] Fill out the details inside of the .env file "
                  "in order to be mentioned through Discord.")
        sys.exit(1)
elif env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    view_env = input("Do you want to view your .env data? (Y/N) ").upper().strip()
    
    if view_env == "Y":
        print()
        print('=' * 79)
        print("\n" + env_path.read_text(encoding="utf-8"))
        print("Double check that your .env data is up to date and meets utf-8 standards.\n")
        print('=' * 79)
        print()

CONFIG_FILE = "config.json"
FIRST_DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL")
SECOND_DISCORD_WEBHOOK_URL = os.getenv("VOLUME_REPORT_URL")
FIRST_USER_ID = os.getenv("FIRST_USER_ID")

notif_auto_delete_duration = 60  # seconds
volume_auto_delete_duration = 20  # seconds

noise_threshold = 0.1
noise_floor = 0.01
hertz_rate = 44100
ping_cooldown = 5.0
volume_report_cooldown = 2.0
ping_user_on_alert = True

DEFAULT_CONFIG = {  # config.json
    "noise_threshold": 0.1,
    "noise_floor": 0.01,
    "sample_rate_hz": 44100,
    "ping_cooldown": 5.0,
    "volume_report_cooldown": 2.0,
    "ping_user_on_alert": True
}

last_volume_report_time = 0
current_nyc_tz = ZoneInfo("America/New_York")
active_messages = []
messages_lock = threading.Lock()


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def get_valid_number(prompt: str, data_type=int, default=None):
    """
    Prompt continuously until valid numeric input is provided.

    Args:
        prompt (str): Text prompt displayed to the user.
        data_type (type, optional): Numeric class (int, float, Decimal).
        default (Any, optional): Value returned if input is left blank.

    Returns:
        int | float | Decimal: Cast numeric value or default.
    """
    while True:
        user_input = input(prompt).strip()
        if not user_input and default is not None:
            return default
        try:
            return data_type(user_input)
        except (ValueError, InvalidOperation):
            print(
                f"[ERROR] Invalid input. "
                f"Please enter a valid {data_type.__name__}."
            )
            print()

config = load_config()
noise_threshold = config["noise_threshold"]
noise_floor = config["noise_floor"]
hertz_rate = config["sample_rate_hz"]
ping_cooldown = config["ping_cooldown"]
volume_report_cooldown = config["volume_report_cooldown"]
ping_user_on_alert = config["ping_user_on_alert"]

print("\nTo keep the values as they are, just hit Enter on the blank line to not change it.")
print("Your settings will automatically save from your previous inputs.")

noise_threshold = get_valid_number(f"Noise Threshold? [{noise_threshold}] ", float, noise_threshold)
noise_floor = get_valid_number(f"Noise Floor? [{noise_floor}] ", float, noise_floor)
hertz_rate = get_valid_number(f"Hertz Rate? [{hertz_rate}] ", int, hertz_rate)
ping_cooldown = get_valid_number(f"Ping Cooldown? (seconds) [{ping_cooldown}] ", float, ping_cooldown)
volume_report_cooldown = get_valid_number(f"Volume Report Cooldown? (seconds) [{volume_report_cooldown}] ", float, volume_report_cooldown)

print("\nIf you want to reset all settings back to the original, enter 'RESET_ALL'.")
reset_settings = input("Reset settings back to original? (ONLY DO THIS AFTER YOU'VE "
                       "PERMANENTLY CHANGED YOUR SETTINGS ALREADY) ").upper().strip()

if reset_settings == "RESET_ALL":
    noise_threshold = 0.1
    noise_floor = 0.01
    hertz_rate = 44100
    ping_cooldown = 5.0
    volume_report_cooldown = 2.0
    print("\nSettings were successfully changed to their original states.")
else:
    print("\nSettings weren't changed.")

print()
config["noise_threshold"] = noise_threshold
config["noise_floor"] = noise_floor
config["sample_rate_hz"] = hertz_rate
config["volume_report_cooldown"] = volume_report_cooldown
config["ping_cooldown"] = ping_cooldown

save_config(config)


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
    
    over_pct = round(((volume - noise_threshold) / noise_threshold) * 100)
    
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
                "value": f"**{volume:.3f}\n{noise_threshold}**",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"**{over_pct}%** over Threshold\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {hertz_rate}Hz - Cooldown: {ping_cooldown}s"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {
        "content": f"**Sound Detected - <@{FIRST_USER_ID}>**" if ping_user_on_alert else "**Sound Detected**",
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
                notif_auto_delete_duration,
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

    delete_time = int(time.time()) + volume_auto_delete_duration
    status = "Loud" if volume > noise_threshold else "Normal"

    embed = {
        "title": f"**Live Volume Report**",
        "description": f"<@{FIRST_USER_ID}>",
        "color": 0x57F287,  # Bright green
        "fields": [
            {"name": "Metric", "value": "Volume\nFloor", "inline": True},
            {
                "name": "Level",
                "value": f"**{volume:.3f}**\n{noise_floor}",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"{status}\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {hertz_rate}Hz"},
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
                volume_auto_delete_duration,
            ),
        ).start()


def audio_callback(
    indata: np.ndarray,
    frames: int,
    time_info: Any,
    status: Any,
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
        time_info (Any): Timing information provided by the
            audio stream.
        status (Any): Current status information for the audio
            stream.
    """
    global last_ping_time, last_volume_report_time
    current_time = time.time()

    volume_norm = float(np.sqrt(np.mean(indata**2)))

    if volume_norm > noise_floor:
        print(f"Volume: {volume_norm:.3f}")

        if current_time - last_volume_report_time > volume_report_cooldown:
            send_volume_report(volume_norm)
            last_volume_report_time = current_time

    if volume_norm > noise_threshold:
        if current_time - last_ping_time > ping_cooldown:
            print(f"*** Noise Detected! Volume Level: {volume_norm:.3f} ***")
            delete_time = int(current_time) + notif_auto_delete_duration
            send_discord_ping(volume_norm, delete_time)
            last_ping_time = current_time

print(f"Listening on device index {DEVICE_INDEX} "
      f"(Channels: {INPUT_CHANNELS} | Sample Rate: {hertz_rate}Hz)")
print(f"Noise Threshold: {noise_threshold} | Ping Cooldown: {ping_cooldown}s")

try:
    with sd.InputStream(
        device=DEVICE_INDEX,
        callback=audio_callback,
        channels=INPUT_CHANNELS,
        samplerate=hertz_rate,  # 44100 Hz is standard for any fast audio
    ):
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
