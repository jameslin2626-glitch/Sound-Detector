import os
import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
import requests

# Sound Detector Script
# v1.09.2

load_dotenv()

# Discord Webhook URL(s) & User ID(s) for sending notifications to the user
FIRST_DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL")
SECOND_DISCORD_WEBHOOK_URL = os.getenv("VOLUME_REPORT_URL")
FIRST_USER_ID = os.getenv("FIRST_USER_ID")

PING_COOLDOWN = 5  # seconds
NOTIF_AUTO_DELETE_DURATION = 60  # seconds
VOLUME_AUTO_DELETE_DURATION = 20  # seconds

HERTZ_RATE = 44100  # sample_rate in Hz
NOISE_THRESHOLD = 0.1  # volume threshold for sending a Discord ping
NOISE_FLOOR = 0.01  # minimum volume level to consider

current_nyc_tz = ZoneInfo("America/New_York")
active_messages = []  # Tracks messages as tuples of (webhook_url, message_id)
messages_lock = threading.Lock()


def date_report():
    """
    Reports current date/time in NYC timezone.
    
    Returns:
        str: DD/MM/YYYY HH:MM:SS AM/PM format
    """
    now = datetime.now(current_nyc_tz)
    return now.strftime("[%d-%m-%Y %I:%M:%S%p]")


def time_report():
    """
    Reports current time in NYC timezone.

    Returns:
        str: HH:MM:SS AM/PM format
    """
    now = datetime.now(current_nyc_tz)
    return now.strftime("[%I:%M:%S %p]")


def find_audio_device():
    """
    Finds the currently selected output device the user is using
    to detect device audio.
    
    Returns:
        tuple: (device_index, input_channels)
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
        ):
            return i, dev["max_input_channels"]

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i, dev["max_input_channels"]

    print("[ERROR] No valid audio input device(s) found")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0


def auto_delete_msg(webhook_url, msg_id, delay):
    """
    Auto-deletes the Webhook Bot's Discord message(s) in "delay" seconds.
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


def send_discord_ping(text):
    """
    Send a Discord mention to the User ID to their connected webhook, 
    notifying them about the detected sound's presence.
    """
    if not FIRST_DISCORD_WEBHOOK_URL:
        return

    data = {
        "content": f"<@{FIRST_USER_ID}> ***Sound Detected***\n{date_report()}",
        "embeds": [{"description": f"{text}", "color": 0x5865F2}],
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


def send_volume_report(volume):
    """
    Send a message to another connected webhook, 
    displaying the Live Volume output.
    """
    if not SECOND_DISCORD_WEBHOOK_URL:
        return

    delete_time = int(time.time()) + VOLUME_AUTO_DELETE_DURATION
    desc = (
        f"<@{FIRST_USER_ID}>\nLive Volume: {volume}\n"
        f"-# Deletes <t:{delete_time}:R>"
    )
    embed = {"description": desc, "color": 0x57F287}
    data = {"embeds": [embed]}

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


def audio_callback(indata, frames, time_info, status):
    """
    Processes the device audio, monitor volume levels, and report spikes.

    Sends a Discord notification if live volume exceeds the threshold and the
    cooldown period has elapsed.
    """
    global last_ping_time

    volume_norm = float(np.sqrt(np.mean(indata**2)))

    if volume_norm > NOISE_FLOOR:
        print(f"Volume: {volume_norm:.3f}")

        if volume_norm > NOISE_THRESHOLD:
            send_volume_report(f"***{volume_norm:.3f}***")
        else:
            send_volume_report(f"{volume_norm:.3f}")

    current_time = time.time()
    if volume_norm > NOISE_THRESHOLD:
        if current_time - last_ping_time > PING_COOLDOWN:
            print(f"*** Noise Detected! Volume Level: {volume_norm:.3f} ***")

            delete_time = int(current_time) + NOTIF_AUTO_DELETE_DURATION

            send_discord_ping(
                "***A sound was detected!***\n"
                f"Threshold: {NOISE_THRESHOLD}\n"
                f"Live Volume: ***{volume_norm:.3f}***\n"
                f"-# Deletes <t:{delete_time}:R>"
            )
            last_ping_time = current_time


print(f"Listening on device index {DEVICE_INDEX} "
      f"(Channels: {INPUT_CHANNELS} | Sample Rate: {HERTZ_RATE}Hz)")
print(f"Noise Threshold: {NOISE_THRESHOLD} | Ping Cooldown: {PING_COOLDOWN}s")

try:
    with sd.InputStream(
        device=DEVICE_INDEX,
        callback=audio_callback,
        channels=INPUT_CHANNELS,
        samplerate=HERTZ_RATE,
    ):
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
